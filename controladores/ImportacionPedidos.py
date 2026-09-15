import pandas as pd
import peewee

from PyQt5.QtWidgets import QApplication, QMessageBox
from modelos.Clientes import Cliente, CodigoClienteProveedor, LugarEntrega
from modelos.Documentos import (
    asegurar_esquema_documentos,
    buscar_hoja_legacy_sin_vincular,
    huella_linea_importada,
    identidad_linea_importada,
    normalizar_numero_documento,
    obtener_o_crear_detalle,
    obtener_o_crear_documento,
    vincular_hoja_ruta,
    vinculo_existente_de_detalle,
)
from modelos.HojaRuta import HojaDeRuta
import modelos.ModeloBase as modelo_base
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from modelos.Proveedores import ProcesoLista, Proveedor
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones, openFileNameDialog
from utiles.importacion_proveedores_excel import (
    METODO_COLUMNAS,
    normalizar_archivo_pedidos,
)
from utiles.importacion_tremblay_excel import procesar_archivo_tremblay_excel
from utiles.importacion_tremblay_pdf import procesar_pdf_despacho
from utiles.importacion_informe_tremblay import procesar_informe_tremblay
from utiles.importacion_guiada import (
    ACCION_CORREGIR,
    ResumenImportacion,
    ayuda_proveedor,
)
from vistas.ImportacionPedidos import ImportacionPedidosView


ERRORES_CONEXION_DB = (peewee.OperationalError, peewee.InterfaceError)

COLUMNAS_NORMALIZADAS = {
    "Cliente": "codigo_cliente",
    "Nombre_Cliente": "detalle_cliente",
    "Comprobante": "comprobante",
    "Producto": "producto",
    "Cantidad": "cantidad",
    "KG": "kilos",
    "Bultos": "bultos",
    "Observaciones": "observaciones",
}


class ImportacionPedidosController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = ImportacionPedidosView()
        self.msg_box = None
        self.resumen_actual = ResumenImportacion()
        self.archivo_normalizado = False
        self.conectarWidgets()

    def run(self):
        """Muestra el importador maximizado y al frente de la ventana principal."""
        self.view.showMaximized()
        self.view.raise_()
        self.view.activateWindow()

    def conectarWidgets(self):
        self.view.btn_examinar.clicked.connect(self.seleccionar_archivo)
        self.view.btn_importar.clicked.connect(self.importar_pedidos)
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_grabar.clicked.connect(self.on_click_btn_grabar)
        self.view.btn_siguiente.clicked.connect(self.ir_siguiente_paso)

    def _actualizar_ayuda_proveedor(self):
        self.view.mostrar_ayuda_proveedor(
            ayuda_proveedor(self._metodo_importacion_proveedor())
        )

    def _actualizar_avance_preprocesamiento(self, porcentaje):
        self.view.avance.actualizar(porcentaje, "Normalizando archivo del proveedor")

    def _metodo_importacion_proveedor(self):
        proveedor_id = self.view.empresa_proveedora.valor()
        if not proveedor_id:
            return None
        try:
            proveedor = self._leer_db_con_reintento(
                lambda: Proveedor.get_by_id(proveedor_id),
                "lectura del método de importación del proveedor",
            )
        except peewee.DoesNotExist:
            return None
        return str(proveedor.metodo_importacion or METODO_COLUMNAS).strip().upper()


    def _reconectar_db_para_lectura(self):
        """Descarta un socket muerto y abre uno nuevo para repetir un SELECT seguro."""
        try:
            if not modelo_base.db.is_closed():
                modelo_base.db.close()
        except Exception:
            pass
        modelo_base.db.connect(reuse_if_open=True)

    def _leer_db_con_reintento(self, operacion, descripcion="lectura"):
        """Reintenta una sola vez una lectura segura ante pérdida de conexión.

        Solo debe utilizarse para SELECTs o búsquedas que no escriben. Las
        escrituras se mantienen fuera de este helper para evitar duplicados si
        el servidor alcanzó a ejecutar el SQL antes de perderse la respuesta.
        """
        try:
            return operacion()
        except ERRORES_CONEXION_DB as exc:
            print("[DB] {} interrumpida: {}. Reconectando y reintentando una vez...".format(
                descripcion, exc
            ))
            self._reconectar_db_para_lectura()
            return operacion()

    def _cargar_columnas_proveedor(self, proveedor):
        """Obtiene el mapeo del proveedor o el contrato común ya normalizado."""
        if self.archivo_normalizado:
            return dict(COLUMNAS_NORMALIZADAS)

        filas = self._leer_db_con_reintento(
            lambda: list(
                ProcesoLista.select().where(ProcesoLista.proveedor == proveedor)
            ),
            "lectura de configuración del importador",
        )
        return {str(fila.codigo): fila.columna for fila in filas}

    def _resolver_cliente_lugar(self, proveedor, codigo, nombre_cliente):
        """Resuelve Cliente + Lugar sin abrir modales durante la importación."""
        codigo_cliente = self._leer_db_con_reintento(
            lambda: CodigoClienteProveedor.get_or_none(
                (CodigoClienteProveedor.codigo == codigo) &
                (CodigoClienteProveedor.proveedor == proveedor)
            ),
            "búsqueda de cliente por código de proveedor",
        )
        cliente_obj = None
        if codigo_cliente is not None and codigo_cliente.cliente_id not in (None, 1):
            cliente_obj = codigo_cliente.cliente
        else:
            nombre = str(nombre_cliente or "").strip()
            if nombre and nombre.lower() != "nan":
                cliente_obj = self._leer_db_con_reintento(
                    lambda: Cliente.get_or_none(
                        peewee.fn.LOWER(Cliente.razon_social) == nombre.lower()
                    ),
                    "búsqueda exacta de cliente por razón social",
                )

        if cliente_obj is None:
            return None, None

        principal = self._leer_db_con_reintento(
            lambda: LugarEntrega.principal_cliente(cliente_obj.id),
            "búsqueda de lugar de entrega principal",
        )
        if principal is not None:
            return cliente_obj, principal

        lugares = self._leer_db_con_reintento(
            lambda: list(LugarEntrega.activos_cliente(cliente_obj.id)),
            "búsqueda de lugares de entrega",
        )
        if len(lugares) == 1:
            return cliente_obj, lugares[0]
        return cliente_obj, None

    def _marcar_interrupcion_conexion(self, procesados, total, exc):
        """Deja la pantalla en un estado claro cuando una escritura queda incierta."""
        detalle = (
            "La conexión con la base de datos se interrumpió al grabar. "
            "Se procesaron {} de {} registros. RND detuvo la importación para "
            "evitar repetir una escritura cuyo resultado podría ser incierto."
        ).format(procesados, total)
        self.view.avance.marcar_error(
            "Importación interrumpida ({}/{})".format(procesados, total)
        )
        self.view.lbl_resultado_titulo.setText("Importación interrumpida")
        self.view.lbl_resultado_detalle.setText(detalle)
        self.view.btn_siguiente.setEnabled(False)
        showAlert(
            "Conexión interrumpida",
            detalle + "\n\nDetalle técnico: {}".format(exc),
        )

    @inicializar_y_capturar_excepciones
    def seleccionar_archivo(self, *args, **kwargs):
        """Selecciona el archivo, lo normaliza si corresponde y prepara sus hojas."""
        self._actualizar_ayuda_proveedor()
        if not self.view.empresa_proveedora.valor():
            showAlert("Sistema", "Primero seleccione el proveedor / origen de los pedidos")
            return

        cArchivo = openFileNameDialog(
            title="Seleccionar archivo de pedidos",
            files="Archivos importacion (*.xlsx;*.xls)",
        )
        if not cArchivo:
            return

        self.archivo_normalizado = False
        self.view.avance.iniciar("Analizando archivo")
        self.view.txt_archivo.setText(cArchivo)

        metodo = self._metodo_importacion_proveedor()
        try:
            archivo_normalizado = normalizar_archivo_pedidos(
                cArchivo,
                progreso=self._actualizar_avance_preprocesamiento,
                metodo=metodo,
            )
        except ValueError as exc:
            self.view.avance.marcar_error("Formato de archivo incorrecto")
            showAlert("Sistema", str(exc))
            return

        if archivo_normalizado:
            self.archivo_normalizado = True
            cArchivo = archivo_normalizado
            self.view.txt_archivo.setText(cArchivo)
            self.view.avance.finalizar("Archivo normalizado")
        else:
            self.view.avance.finalizar("Archivo seleccionado")

        xls = pd.ExcelFile(cArchivo)
        self.view.cbo_hoja.CargaDatos(list(xls.sheet_names))
        self.view.lbl_previa.setText(
            "Archivo seleccionado. Presione ‘Cargar vista previa’ para revisar los pedidos."
        )

    @inicializar_y_capturar_excepciones
    def importar_pedidos(self, *args, **kwargs):
        """Carga una vista previa sin grabar aún hojas de ruta."""
        self.view.grid_datos.limpiarGrilla()
        self._actualizar_ayuda_proveedor()
        if not self.view.txt_archivo.text():
            showAlert("Sistema", "Debe seleccionar un archivo para importar")
            return

        self.view.avance.iniciar("Leyendo archivo")
        archivo = self.view.txt_archivo.text()
        hoja = self.view.cbo_hoja.text()
        try:
            df = pd.read_excel(archivo, sheet_name=hoja, header=None)
        except Exception as exc:
            self.resumen_actual = ResumenImportacion(errores=1)
            self.view.mostrar_resultado(self.resumen_actual)
            self.view.avance.marcar_error("No se pudo leer el archivo")
            showAlert("Sistema", "No se pudo leer el archivo: {}".format(exc))
            return

        if df.empty:
            self.resumen_actual = ResumenImportacion(errores=1)
            self.view.mostrar_resultado(self.resumen_actual)
            self.view.avance.marcar_error("Archivo sin datos")
            showAlert("Sistema", "La hoja seleccionada no contiene datos")
            return

        texto_fila_inicio = self.view.txt_fila_inicio.text().strip()
        texto_fila_fin = self.view.txt_fila_fin.text().strip()
        if texto_fila_inicio:
            try:
                fila_cabeceras = int(texto_fila_inicio) - 1
            except ValueError:
                self.view.avance.marcar_error("Fila de inicio inválida")
                showAlert("Sistema", "La fila de inicio debe ser un número válido")
                return
        else:
            fila_cabeceras = 0

        if fila_cabeceras >= len(df) or fila_cabeceras < 0:
            self.view.avance.marcar_error("Fila de inicio fuera de rango")
            showAlert("Sistema", "La fila de inicio especificada está fuera del rango")
            return

        cabeceras = ["Importa"] + df.iloc[fila_cabeceras].tolist()
        inicio_datos = fila_cabeceras + 1
        df_datos = df.iloc[inicio_datos:].reset_index(drop=True)
        df_datos.columns = df.iloc[fila_cabeceras]
        self.view.grid_datos.ArmaCabeceras(cabeceras=cabeceras)

        idx_inicio = 0
        idx_fin = len(df_datos)
        if texto_fila_fin:
            try:
                fila_fin = int(texto_fila_fin) - 1
            except ValueError:
                self.view.avance.marcar_error("Fila final inválida")
                showAlert("Sistema", "La fila de fin debe ser un número válido")
                return
            if fila_fin < inicio_datos:
                self.view.avance.marcar_error("Rango de filas inválido")
                showAlert("Sistema", "Rango de filas no válido")
                return
            idx_fin = min(len(df_datos), fila_fin - inicio_datos + 1)

        if idx_fin <= idx_inicio:
            self.view.avance.marcar_error("Sin filas para importar")
            showAlert("Sistema", "No hay filas de datos para importar en el rango seleccionado")
            return

        total_filas = idx_fin - idx_inicio
        for avance, i in enumerate(range(idx_inicio, idx_fin), start=1):
            self.view.avance.actualizar(
                avance / total_filas * 100,
                "Cargando vista previa {}/{}".format(avance, total_filas),
            )
            row = df_datos.iloc[i]
            item = [True]
            item.extend("" if pd.isna(valor) else valor for valor in row.tolist())
            self.view.grid_datos.AgregaItem(item)

        self.view.avance.finalizar("Vista previa lista")
        self.view.grid_datos.setSortingEnabled(True)
        self.view.grid_datos.resizeColumnsToContents()
        self.view.grid_datos.resizeRowsToContents()
        self.resumen_actual = ResumenImportacion(leidos=total_filas)
        self.view.mostrar_previa(total_filas)
        self.view.lbl_resultado_titulo.setText("Vista previa cargada")
        self.view.lbl_resultado_detalle.setText(
            "Revise los {} registros y presione ‘Grabar pedidos’ para incorporarlos al reparto.".format(total_filas)
        )

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_grabar(self, *args, **kwargs):
        """Graba pedidos con retry solo de SELECTs y frena escrituras inciertas."""
        proveedor = self.view.empresa_proveedora.valor()
        if not proveedor:
            showAlert("Sistema", "Debe seleccionar un proveedor / origen")
            return

        total = self.view.grid_datos.rowCount()
        if total <= 0:
            showAlert("Sistema", "Primero cargue la vista previa del archivo")
            return

        self.view.avance.iniciar("Preparando importación")
        try:
            columnas = self._cargar_columnas_proveedor(proveedor)
            columna_cliente = columnas.get("Cliente")
            columna_nombre = columnas.get("Nombre_Cliente")
            if not columna_cliente or not columna_nombre:
                self.view.avance.marcar_error("Configuración incompleta")
                showAlert(
                    "Sistema",
                    "No están configuradas las columnas Cliente/Nombre_Cliente para este proveedor.",
                )
                return

            responsable_generico = self._leer_db_con_reintento(
                lambda: ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23"),
                "lectura de empleado genérico",
            )
            camion_generico = self._leer_db_con_reintento(
                lambda: ParamSist.ObtenerParametro("CAMION_GENERICO", "1"),
                "lectura de camión genérico",
            )
            asegurar_esquema_documentos()
        except ERRORES_CONEXION_DB as exc:
            self._marcar_interrupcion_conexion(0, total, exc)
            return

        importados = 0
        omitidos = 0
        reimportados = 0
        pendientes = 0
        errores = 0
        procesados = 0
        ocurrencias_linea = {}

        for row in range(total):
            self.view.avance.actualizar(
                (row + 1) / total * 100,
                "Grabando pedido {}/{}".format(row + 1, total),
            )
            importa = self.view.grid_datos.ObtenerItem(fila=row, col="Importa")
            if not importa:
                omitidos += 1
                procesados += 1
                continue

            cliente = self.view.grid_datos.ObtenerItem(fila=row, col=columna_cliente)
            nombre_cliente = self.view.grid_datos.ObtenerItem(fila=row, col=columna_nombre)

            try:
                cliente_obj, lugar_entrega = self._resolver_cliente_lugar(
                    proveedor, cliente, nombre_cliente
                )

                columna_producto = columnas.get("Producto")
                if not columna_producto:
                    raise ValueError("No está configurada la columna Producto")
                producto = self.view.grid_datos.ObtenerItem(
                    fila=row,
                    col=columna_producto,
                )

                columna_comprobante = columnas.get("Comprobante")
                comprobante = ""
                if columna_comprobante:
                    comprobante = self.view.grid_datos.ObtenerItem(
                        fila=row,
                        col=columna_comprobante,
                    )
                comprobante = normalizar_numero_documento(comprobante)

                observaciones = columnas.get("Observaciones")
                valor_observaciones = ""
                if observaciones:
                    valor_observaciones = self.view.grid_datos.ObtenerItem(
                        fila=row, col=observaciones
                    )
                    if pd.isna(valor_observaciones):
                        valor_observaciones = ""

                cantidad = self.view.grid_datos.ObtenerItem(
                    fila=row, col=columnas.get("Cantidad")
                )
                kilos = self.view.grid_datos.ObtenerItem(
                    fila=row, col=columnas.get("KG")
                )
                bultos = self.view.grid_datos.ObtenerItem(
                    fila=row, col=columnas.get("Bultos")
                )

                documento, _ = obtener_o_crear_documento(
                    proveedor=proveedor,
                    cliente=cliente_obj,
                    fecha_documento=self.view.fecha_reparto.valor(),
                    numero_factura=comprobante,
                    comprobante_origen=comprobante,
                    origen="importacion-pedidos",
                )

                huella = huella_linea_importada(
                    producto, cantidad, kilos, bultos, valor_observaciones
                )
                clave_ocurrencia = (documento.id, huella)
                ocurrencias_linea[clave_ocurrencia] = (
                    ocurrencias_linea.get(clave_ocurrencia, 0) + 1
                )
                linea_origen = identidad_linea_importada(
                    producto,
                    cantidad,
                    kilos,
                    bultos,
                    valor_observaciones,
                    ocurrencias_linea[clave_ocurrencia],
                )
                detalle, _ = obtener_o_crear_detalle(
                    documento=documento,
                    linea_origen=linea_origen,
                    producto=producto,
                    cantidad=cantidad,
                    kg=kilos,
                    bultos=bultos,
                    observaciones=valor_observaciones,
                )

                vinculo_existente = vinculo_existente_de_detalle(
                    detalle, self.view.fecha_reparto.valor()
                )
                if vinculo_existente:
                    reimportados += 1
                    procesados += 1
                    print(
                        "[ImportacionPedidos] Documento {} línea {} ya importada; "
                        "se conserva la hoja de ruta #{}.".format(
                            comprobante or "(sin factura)",
                            linea_origen,
                            vinculo_existente.hoja_ruta_id,
                        )
                    )
                    continue

                hoja_ruta = None
                if cliente_obj is not None:
                    hoja_ruta = buscar_hoja_legacy_sin_vincular(
                        cliente_obj.id,
                        self.view.fecha_reparto.valor(),
                        producto,
                        comprobante,
                    )
                if hoja_ruta is None:
                    hoja_ruta = HojaDeRuta()
                    hoja_ruta.fecha = self.view.fecha_reparto.valor()

                hoja_ruta.cliente = cliente_obj
                hoja_ruta.lugar_entrega = lugar_entrega
                hoja_ruta.observaciones = valor_observaciones
                if lugar_entrega is not None:
                    hoja_ruta.ruta = lugar_entrega.ruta_reparto_id or (
                        cliente_obj.ruta_reparto_id if cliente_obj is not None else None
                    )
                else:
                    hoja_ruta.ruta = None
                hoja_ruta.nombre_cliente = "" if pd.isna(nombre_cliente) else str(nombre_cliente)
                hoja_ruta.responsable = responsable_generico
                hoja_ruta.equipo_asignado = camion_generico
                hoja_ruta.comprobante = comprobante
                hoja_ruta.producto = producto
                hoja_ruta.cantidad = cantidad
                hoja_ruta.kg = kilos
                hoja_ruta.cantidad_bultos = bultos

                if cliente_obj is None or lugar_entrega is None:
                    pendientes += 1

                # save() es escritura. Si la conexión se pierde aquí no se repite:
                # el servidor podría haberla ejecutado aunque no haya llegado respuesta.
                hoja_ruta.save()
                vincular_hoja_ruta(detalle, hoja_ruta)
                importados += 1
                procesados += 1
            except ERRORES_CONEXION_DB as exc:
                self._marcar_interrupcion_conexion(procesados, total, exc)
                return
            except Exception as exc:
                print("[ImportacionPedidos] Error en fila {}: {}".format(row + 1, exc))
                errores += 1
                procesados += 1

        self.resumen_actual = ResumenImportacion(
            leidos=total,
            importados=importados,
            omitidos=omitidos,
            reimportados=reimportados,
            pendientes=pendientes,
            errores=errores,
        )
        self.view.mostrar_resultado(self.resumen_actual)
        self.view.avance.finalizar("Importación finalizada")

    def ir_siguiente_paso(self):
        """Continúa a la bandeja operativa o devuelve al operador a corregir."""
        if self.resumen_actual.siguiente_accion == ACCION_CORREGIR:
            self.view.txt_archivo.setFocus()
            return
        from controladores.BandejaPedidos import BandejaPedidosController

        self.ventana_siguiente = BandejaPedidosController(
            fecha_inicial=self.view.fecha_reparto.valor()
        )
        self.ventana_siguiente.run()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def obtener_proceso_list(self, proveedor, columna):
        if self.archivo_normalizado:
            return COLUMNAS_NORMALIZADAS.get(columna)
        try:
            return ProcesoLista.get(
                ProcesoLista.proveedor == proveedor,
                ProcesoLista.codigo == columna,
            ).columna
        except peewee.DoesNotExist:
            return None

    def importa_pdf_tremblay(self):
        if not self.view.txt_archivo.text():
            showAlert("Sistema", "Debe seleccionar un archivo PDF para importar")
            return
        archivo_procesado = procesar_pdf_despacho(self.view.txt_archivo.valor())
        if not archivo_procesado:
            showAlert("Sistema", "No se pudo procesar el archivo PDF")
            return
        self.view.txt_archivo.setText(archivo_procesado)
        QApplication.processEvents()

    def mostrar_mensaje_procesando(self):
        self.msg_box = QMessageBox(self.view)
        self.msg_box.setIcon(QMessageBox.Information)
        self.msg_box.setText("Procesando archivo, por favor espere...")
        self.msg_box.setWindowTitle("Procesando")
        self.msg_box.setStandardButtons(QMessageBox.NoButton)
        self.msg_box.show()

    def cerrar_mensaje_procesando(self):
        if self.msg_box:
            self.msg_box.close()
            self.msg_box = None

    def importa_tremblay(self):
        if not self.view.txt_archivo.text():
            showAlert("Sistema", "Debe seleccionar un archivo para importar")
            return
        path = self.view.txt_archivo.valor()
        ext = path.lower().rsplit(".", 1)[-1] if "." in path else ""
        try:
            if ext == "xls":
                archivo_procesado = procesar_informe_tremblay(path)
            else:
                archivo_procesado = procesar_archivo_tremblay_excel(path)
        except (ValueError, FileNotFoundError) as exc:
            self.resumen_actual = ResumenImportacion(errores=1)
            self.view.mostrar_resultado(self.resumen_actual)
            self.view.avance.marcar_error("No se pudo procesar el archivo")
            showAlert("Sistema", "No se pudo procesar el archivo: {}".format(exc))
            return
        if not archivo_procesado:
            self.resumen_actual = ResumenImportacion(errores=1)
            self.view.mostrar_resultado(self.resumen_actual)
            self.view.avance.marcar_error("No se pudo procesar el archivo")
            showAlert("Sistema", "No se pudo procesar el archivo")
            return
        self.view.txt_archivo.setText(archivo_procesado)
        QApplication.processEvents()

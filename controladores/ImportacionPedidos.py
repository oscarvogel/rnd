import pandas as pd
import peewee

from PyQt5.QtWidgets import QApplication, QMessageBox
from modelos.Clientes import BuscadorCliente, CodigoClienteProveedor
from modelos.HojaRuta import HojaDeRuta
import modelos.ModeloBase as modelo_base
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from modelos.Proveedores import ProcesoLista
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones, openFileNameDialog
from utiles.importacion_proveedores_excel import normalizar_archivo_pedidos
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

    def conectarWidgets(self):
        self.view.btn_examinar.clicked.connect(self.seleccionar_archivo)
        self.view.btn_importar.clicked.connect(self.importar_pedidos)
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_grabar.clicked.connect(self.on_click_btn_grabar)
        self.view.btn_siguiente.clicked.connect(self.ir_siguiente_paso)

    def _actualizar_ayuda_proveedor(self):
        self.view.mostrar_ayuda_proveedor(
            ayuda_proveedor(self.view.empresa_proveedora.valor())
        )

    def _actualizar_avance_preprocesamiento(self, porcentaje):
        self.view.avance.actualizar(porcentaje, "Normalizando archivo del proveedor")

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

        archivo_normalizado = normalizar_archivo_pedidos(
            cArchivo,
            progreso=self._actualizar_avance_preprocesamiento,
        )
        if archivo_normalizado:
            self.archivo_normalizado = True
            cArchivo = archivo_normalizado
            self.view.txt_archivo.setText(cArchivo)
            self.view.avance.finalizar("Archivo normalizado")
        elif self.view.empresa_proveedora.valor() == "15":
            self.importa_tremblay()
            cArchivo = self.view.txt_archivo.text()
            if not cArchivo:
                return
            self.view.avance.finalizar("Archivo Tremblay procesado")
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
            item.extend(row.tolist())
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
        except ERRORES_CONEXION_DB as exc:
            self._marcar_interrupcion_conexion(0, total, exc)
            return

        importados = 0
        omitidos = 0
        pendientes = 0
        errores = 0
        procesados = 0

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
                try:
                    codigo_cliente = self._leer_db_con_reintento(
                        lambda cliente=cliente: CodigoClienteProveedor.get(
                            CodigoClienteProveedor.codigo == cliente,
                            CodigoClienteProveedor.proveedor == proveedor,
                        ),
                        "búsqueda de cliente",
                    )
                    busqueda = codigo_cliente.cliente_id == 1
                except peewee.DoesNotExist:
                    codigo_cliente = None
                    busqueda = True

                if busqueda:
                    buscador_cliente = BuscadorCliente()
                    buscador_cliente.valor_busqueda = nombre_cliente
                    # Puede crear un Cliente (#45): no envolver en retry automático.
                    buscador_cliente.buscar(self.view)
                    if buscador_cliente.lRetval:
                        # get_or_create/save pueden escribir: no se reintentan automáticamente.
                        codigo_cliente, _ = CodigoClienteProveedor.get_or_create(
                            codigo=cliente,
                            proveedor=proveedor,
                            defaults={"cliente": buscador_cliente.valorRetorno},
                        )
                        codigo_cliente.cliente = buscador_cliente.valorRetorno
                        codigo_cliente.save()
                    else:
                        codigo_cliente = None

                if not codigo_cliente or codigo_cliente.cliente_id == 1:
                    pendientes += 1
                    procesados += 1
                    continue

                columna_producto = columnas.get("Producto")
                if not columna_producto:
                    raise ValueError("No está configurada la columna Producto")
                producto = self.view.grid_datos.ObtenerItem(
                    fila=row,
                    col=columna_producto,
                )
                try:
                    hoja_ruta = self._leer_db_con_reintento(
                        lambda: HojaDeRuta.get(
                            HojaDeRuta.cliente == codigo_cliente.cliente_id,
                            HojaDeRuta.fecha == self.view.fecha_reparto.valor(),
                            HojaDeRuta.producto == producto,
                        ),
                        "búsqueda de hoja de ruta existente",
                    )
                except peewee.DoesNotExist:
                    hoja_ruta = HojaDeRuta()
                    hoja_ruta.cliente = codigo_cliente.cliente
                    hoja_ruta.fecha = self.view.fecha_reparto.valor()

                observaciones = columnas.get("Observaciones")
                if observaciones:
                    valor_observaciones = self.view.grid_datos.ObtenerItem(
                        fila=row, col=observaciones
                    )
                    hoja_ruta.observaciones = (
                        "" if pd.isna(valor_observaciones) else valor_observaciones
                    )

                hoja_ruta.ruta = codigo_cliente.cliente.ruta_reparto_id
                hoja_ruta.nombre_cliente = nombre_cliente
                hoja_ruta.responsable = responsable_generico
                hoja_ruta.equipo_asignado = camion_generico

                columna_comprobante = columnas.get("Comprobante")
                if columna_comprobante:
                    comprobante = self.view.grid_datos.ObtenerItem(
                        fila=row,
                        col=columna_comprobante,
                    )
                    if pd.isna(comprobante):
                        comprobante = ""
                    hoja_ruta.comprobante = str(comprobante or "").replace(".", "")
                else:
                    hoja_ruta.comprobante = ""

                hoja_ruta.producto = producto
                hoja_ruta.cantidad = self.view.grid_datos.ObtenerItem(
                    fila=row, col=columnas.get("Cantidad")
                )
                hoja_ruta.kg = self.view.grid_datos.ObtenerItem(
                    fila=row, col=columnas.get("KG")
                )
                hoja_ruta.cantidad_bultos = self.view.grid_datos.ObtenerItem(
                    fila=row, col=columnas.get("Bultos")
                )

                # save() es escritura. Si la conexión se pierde aquí no se repite:
                # el servidor podría haberla ejecutado aunque no haya llegado respuesta.
                hoja_ruta.save()
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

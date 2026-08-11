import pandas as pd
import peewee

from PyQt5.QtWidgets import QApplication, QMessageBox
from modelos.Clientes import BuscadorCliente, CodigoClienteProveedor
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from modelos.Proveedores import ProcesoLista
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones, openFileNameDialog
from utiles.importacion_tremblay_excel import procesar_archivo_tremblay_excel
from utiles.importacion_tremblay_pdf import procesar_pdf_despacho
from utiles.importacion_informe_tremblay import procesar_informe_tremblay
from utiles.importacion_guiada import (
    ACCION_CORREGIR,
    ResumenImportacion,
    ayuda_proveedor,
)
from vistas.ImportacionPedidos import ImportacionPedidosView


class ImportacionPedidosController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = ImportacionPedidosView()
        self.msg_box = None
        self.resumen_actual = ResumenImportacion()
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

    @inicializar_y_capturar_excepciones
    def seleccionar_archivo(self, *args, **kwargs):
        """Selecciona el archivo y prepara sus hojas para la vista previa."""
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

        self.view.txt_archivo.setText(cArchivo)
        if self.view.empresa_proveedora.valor() == "15":
            self.importa_tremblay()
            cArchivo = self.view.txt_archivo.text()
            if not cArchivo:
                return

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

        archivo = self.view.txt_archivo.text()
        hoja = self.view.cbo_hoja.text()
        try:
            df = pd.read_excel(archivo, sheet_name=hoja, header=None)
        except Exception as exc:
            self.resumen_actual = ResumenImportacion(errores=1)
            self.view.mostrar_resultado(self.resumen_actual)
            showAlert("Sistema", "No se pudo leer el archivo: {}".format(exc))
            return

        if df.empty:
            self.resumen_actual = ResumenImportacion(errores=1)
            self.view.mostrar_resultado(self.resumen_actual)
            showAlert("Sistema", "La hoja seleccionada no contiene datos")
            return

        texto_fila_inicio = self.view.txt_fila_inicio.text().strip()
        texto_fila_fin = self.view.txt_fila_fin.text().strip()
        if texto_fila_inicio:
            try:
                fila_cabeceras = int(texto_fila_inicio) - 1
            except ValueError:
                showAlert("Sistema", "La fila de inicio debe ser un número válido")
                return
        else:
            fila_cabeceras = 0

        if fila_cabeceras >= len(df) or fila_cabeceras < 0:
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
                showAlert("Sistema", "La fila de fin debe ser un número válido")
                return
            if fila_fin < inicio_datos:
                showAlert("Sistema", "Rango de filas no válido")
                return
            idx_fin = min(len(df_datos), fila_fin - inicio_datos + 1)

        if idx_fin <= idx_inicio:
            showAlert("Sistema", "No hay filas de datos para importar en el rango seleccionado")
            return

        total_filas = idx_fin - idx_inicio
        for avance, i in enumerate(range(idx_inicio, idx_fin), start=1):
            QApplication.processEvents()
            self.view.avance.actualizar(avance / total_filas * 100)
            row = df_datos.iloc[i]
            item = [True]
            item.extend(row.tolist())
            self.view.grid_datos.AgregaItem(item)

        self.view.avance.actualizar(100)
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
        """Graba los pedidos y construye un resultado operativo comprensible."""
        proveedor = self.view.empresa_proveedora.valor()
        if not proveedor:
            showAlert("Sistema", "Debe seleccionar un proveedor / origen")
            return

        total = self.view.grid_datos.rowCount()
        if total <= 0:
            showAlert("Sistema", "Primero cargue la vista previa del archivo")
            return

        importados = 0
        omitidos = 0
        pendientes = 0
        errores = 0

        for row in range(total):
            self.view.avance.actualizar((row + 1) / total * 100)
            QApplication.processEvents()
            importa = self.view.grid_datos.ObtenerItem(fila=row, col="Importa")
            if not importa:
                omitidos += 1
                continue

            try:
                columna_cliente = ProcesoLista.get(
                    ProcesoLista.proveedor == proveedor,
                    ProcesoLista.codigo == "Cliente",
                ).columna
            except peewee.DoesNotExist:
                errores += 1
                continue

            cliente = self.view.grid_datos.ObtenerItem(fila=row, col=columna_cliente)
            nombre_cliente = self.view.grid_datos.ObtenerItem(
                fila=row,
                col=self.obtener_proceso_list(proveedor, "Nombre_Cliente"),
            )

            try:
                codigo_cliente = CodigoClienteProveedor.get(
                    CodigoClienteProveedor.codigo == cliente,
                    CodigoClienteProveedor.proveedor == proveedor,
                )
                busqueda = codigo_cliente.cliente_id == 1
            except peewee.DoesNotExist:
                codigo_cliente = None
                busqueda = True

            if busqueda:
                buscador_cliente = BuscadorCliente()
                buscador_cliente.valor_busqueda = nombre_cliente
                buscador_cliente.buscar(self.view)
                if buscador_cliente.lRetval:
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
                continue

            try:
                producto = self.view.grid_datos.ObtenerItem(
                    fila=row,
                    col=self.obtener_proceso_list(proveedor, "Producto"),
                )
                try:
                    hoja_ruta = HojaDeRuta.get(
                        HojaDeRuta.cliente == codigo_cliente.cliente_id,
                        HojaDeRuta.fecha == self.view.fecha_reparto.valor(),
                        HojaDeRuta.producto == producto,
                    )
                except peewee.DoesNotExist:
                    hoja_ruta = HojaDeRuta()
                    hoja_ruta.cliente = codigo_cliente.cliente
                    hoja_ruta.fecha = self.view.fecha_reparto.valor()

                observaciones = self.obtener_proceso_list(proveedor, "Observaciones")
                if observaciones:
                    hoja_ruta.observaciones = self.view.grid_datos.ObtenerItem(fila=row, col=observaciones)
                hoja_ruta.ruta = codigo_cliente.cliente.ruta_reparto_id
                hoja_ruta.nombre_cliente = nombre_cliente
                hoja_ruta.responsable = ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23")
                hoja_ruta.equipo_asignado = ParamSist.ObtenerParametro("CAMION_GENERICO", "1")
                hoja_ruta.comprobante = self.view.grid_datos.ObtenerItem(
                    fila=row,
                    col=self.obtener_proceso_list(proveedor, "Comprobante"),
                )
                hoja_ruta.comprobante = str(hoja_ruta.comprobante).replace(".", "")
                hoja_ruta.producto = producto
                hoja_ruta.cantidad = self.view.grid_datos.ObtenerItem(
                    fila=row, col=self.obtener_proceso_list(proveedor, "Cantidad")
                )
                hoja_ruta.kg = self.view.grid_datos.ObtenerItem(
                    fila=row, col=self.obtener_proceso_list(proveedor, "KG")
                )
                hoja_ruta.cantidad_bultos = self.view.grid_datos.ObtenerItem(
                    fila=row, col=self.obtener_proceso_list(proveedor, "Bultos")
                )
                hoja_ruta.save()
                importados += 1
            except Exception:
                errores += 1

        self.resumen_actual = ResumenImportacion(
            leidos=total,
            importados=importados,
            omitidos=omitidos,
            pendientes=pendientes,
            errores=errores,
        )
        self.view.mostrar_resultado(self.resumen_actual)
        self.view.avance.actualizar(100)

    def ir_siguiente_paso(self):
        """Continúa al reparto o devuelve al operador a corregir la importación."""
        if self.resumen_actual.siguiente_accion == ACCION_CORREGIR:
            self.view.txt_archivo.setFocus()
            return
        from controladores.VerHojaRuta import VerHojaRutaController

        self.ventana_siguiente = VerHojaRutaController(
            fecha_inicial=self.view.fecha_reparto.valor()
        )
        self.ventana_siguiente.run()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def obtener_proceso_list(self, proveedor, columna):
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
            showAlert("Sistema", "No se pudo procesar el archivo: {}".format(exc))
            return
        if not archivo_procesado:
            self.resumen_actual = ResumenImportacion(errores=1)
            self.view.mostrar_resultado(self.resumen_actual)
            showAlert("Sistema", "No se pudo procesar el archivo")
            return
        self.view.txt_archivo.setText(archivo_procesado)
        QApplication.processEvents()

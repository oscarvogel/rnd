import pandas as pd
import peewee
import pdfplumber
import pandas as pd
import re

from PyQt5.QtWidgets import QApplication, QMessageBox
from modelos.Clientes import BuscadorCliente, Cliente, CodigoClienteProveedor
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from modelos.Proveedores import ProcesoLista
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import getFileName, inicializar_y_capturar_excepciones, openFileNameDialog
from utiles.importacion_tremblay_excel import procesar_archivo_tremblay_excel
from utiles.importacion_tremblay_pdf import procesar_pdf_despacho
from utiles.importacion_informe_tremblay import procesar_informe_tremblay
from vistas.ImportacionPedidos import ImportacionPedidosView


class ImportacionPedidosController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = ImportacionPedidosView()
        self.msg_box = None  # Atributo para almacenar el cuadro de diálogo
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btn_examinar.clicked.connect(self.seleccionar_archivo)
        self.view.btn_importar.clicked.connect(self.importar_pedidos)
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_grabar.clicked.connect(self.on_click_btn_grabar)

    @inicializar_y_capturar_excepciones
    def seleccionar_archivo(self, *args, **kwargs):
        """Abre un diálogo para seleccionar un archivo de Excel y carga las hojas disponibles."""
        if not self.view.empresa_proveedora.valor():
            showAlert("Sistema", "Debe seleccionar una empresa proveedora")
            return
        
        cArchivo = openFileNameDialog(
            title='Importar',
            files="Archivos importacion (*.xlsx;*.xls)")
        if cArchivo:
            self.view.txt_archivo.setText(cArchivo)
            if self.view.empresa_proveedora.valor() == "15":
                self.importa_tremblay()
                cArchivo = self.view.txt_archivo.text()
            # Crear objeto ExcelFile para manejar múltiples hojas
            xls = pd.ExcelFile(cArchivo)
            # Obtener lista de todas las hojas disponibles
            hojas_disponibles = xls.sheet_names
            # Recorrer cada hoja
            hojas = []
            for nombre_hoja in hojas_disponibles:
                hojas.append(nombre_hoja)
            self.view.cbo_hoja.CargaDatos(hojas)


    @inicializar_y_capturar_excepciones
    def importar_pedidos(self, *args, **kwargs):
        self.view.grid_datos.limpiarGrilla()
        if not self.view.txt_archivo.text():
            showAlert("Sistema", "Debe seleccionar un archivo para importar")
            return

        archivo = self.view.txt_archivo.text()
        hoja = self.view.cbo_hoja.text()

        # Leer sin cabecera para tener control total
        df = pd.read_excel(archivo, sheet_name=hoja, header=None)

        # Obtener número de fila que contiene las cabeceras (supongamos que viene de un campo o es fijo)
        try:
            fila_cabeceras = int(self.view.txt_fila_inicio.text()) - 1  # Restamos 1 por índice 0
        except ValueError:
            showAlert("Sistema", "La fila de cabeceras debe ser un número válido")
            return

        if fila_cabeceras >= len(df) or fila_cabeceras < 0:
            showAlert("Sistema", "La fila de cabeceras especificada está fuera del rango")
            return

        # Extraer las cabeceras desde la fila indicada
        cabeceras = df.iloc[fila_cabeceras].tolist()  # Lista de nombres de columnas
        cabeceras = ['Importa'] + cabeceras  # Añadir la columna personalizada al inicio

        # Definir desde dónde empiezan los datos (después de la fila de cabeceras)
        inicio_datos = fila_cabeceras + 1
        df_datos = df.iloc[inicio_datos:].reset_index(drop=True)

        # Renombrar columnas del DataFrame de datos para facilitar el acceso (opcional)
        df_datos.columns = df.iloc[fila_cabeceras]

        # Configurar la grilla con las nuevas cabeceras
        self.view.grid_datos.ArmaCabeceras(cabeceras=cabeceras)

        # Rango de filas a importar (basado en UI)
        try:
            fila_inicio = int(self.view.txt_fila_inicio.text()) - 1  # Convertir a índice base 0
            fila_fin = int(self.view.txt_fila_fin.text()) - 1
        except ValueError:
            showAlert("Sistema", "Las filas de inicio y fin deben ser números válidos")
            return

        # Validar rango
        if fila_inicio < 0 or fila_fin < fila_inicio:
            showAlert("Sistema", "Rango de filas no válido")
            return

        # Ajustar índices respecto al df_datos (que empieza en `inicio_datos`)
        # Suponiendo que `txt_fila_inicio` y `txt_fila_fin` se refieren al número de fila absoluto en el Excel
        idx_inicio = max(0, fila_inicio - inicio_datos)
        idx_fin = min(len(df_datos), fila_fin - inicio_datos + 1)

        # Progreso
        avance = 0
        total_filas = idx_fin - idx_inicio

        for i in range(idx_inicio, idx_fin):
            QApplication.processEvents()
            avance += 1
            self.view.avance.actualizar(avance / total_filas * 100)

            row = df_datos.iloc[i]
            item = [True]  # Columna 'Importa'
            item.extend(row.tolist())  # Añadir cada celda de la fila
            self.view.grid_datos.AgregaItem(item)

        self.view.avance.actualizar(100)
        self.view.grid_datos.setSortingEnabled(True)
        self.view.grid_datos.resizeColumnsToContents()
        self.view.grid_datos.resizeRowsToContents()

        showAlert("Sistema", "Importación realizada correctamente")
    
    
    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_grabar(self, *args, **kwargs):
        if not self.view.empresa_proveedora.valor():
            showAlert("Sistema", "Debe seleccionar un valor para Empleado, Camion y Empresa Proveedora")
            return
        
        total = self.view.grid_datos.rowCount()
        avance = 0
        for row in range(self.view.grid_datos.rowCount()):
            avance += 1
            self.view.avance.actualizar(avance / total * 100)
            QApplication.processEvents()
            
            importa = self.view.grid_datos.ObtenerItem(fila=row, col='Importa')
            if not importa:
                continue
            try:
                columna_cliente = ProcesoLista.get(ProcesoLista.proveedor == self.view.empresa_proveedora.valor(), ProcesoLista.codigo == 'Cliente').columna
            except peewee.DoesNotExist:
                showAlert("Sistema", "Columna de clientes no se encuentra y no se puede importar")
                continue
            cliente = self.view.grid_datos.ObtenerItem(fila=row, col=columna_cliente)
            nombre_cliente = self.view.grid_datos.ObtenerItem(fila=row, col=self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'Nombre_Cliente'))
            
            try:
                codigo_cliente = CodigoClienteProveedor.get(CodigoClienteProveedor.codigo == cliente)
                busqueda = False
            except peewee.DoesNotExist:
                showAlert("Sistema", f"No tenemos codigo para el cliente seleccionado {nombre_cliente}")
                busqueda = True
            
            if busqueda or codigo_cliente.cliente_id == 1:
                # Buscar cliente por nombre
                buscador_cliente = BuscadorCliente()
                buscador_cliente.valor_busqueda = nombre_cliente
                buscador_cliente.buscar(self.view)
                if buscador_cliente.lRetval:
                    # cliente = buscador_cliente.valorRetorno
                    try:
                        codigo_cliente = CodigoClienteProveedor.get(
                            CodigoClienteProveedor.codigo == cliente,
                            CodigoClienteProveedor.proveedor == self.view.empresa_proveedora.valor()
                        )
                        codigo_cliente.cliente = buscador_cliente.valorRetorno
                        codigo_cliente.save()
                    except peewee.DoesNotExist:
                        codigo_cliente = CodigoClienteProveedor.get_or_create(
                            codigo=cliente,
                            cliente=buscador_cliente.valorRetorno,
                            proveedor=self.view.empresa_proveedora.valor()
                        )
                    codigo_cliente = CodigoClienteProveedor.get(CodigoClienteProveedor.codigo == cliente)
                else:
                    codigo_cliente = None
                    
            if not codigo_cliente:
                showAlert("Sistema", f"No tenemos codigo para el cliente seleccionado {cliente}")
                continue
            
            if codigo_cliente.cliente_id == 1:
                showAlert("Sistema", f"No podemos asignar el pedido a un cliente generico {cliente}. No se grabará el pedido")
                continue
            
            producto = self.view.grid_datos.ObtenerItem(fila=row, col=self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'Producto'))
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
            
            observaciones = self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'Observaciones')
            if observaciones:
                hoja_ruta.observaciones = self.view.grid_datos.ObtenerItem(fila=row, col=observaciones)
            
            hoja_ruta.ruta = codigo_cliente.cliente.ruta_reparto_id
            hoja_ruta.nombre_cliente = self.view.grid_datos.ObtenerItem(fila=row,
                                col=self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'Nombre_Cliente'))
            hoja_ruta.responsable = ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23")
            hoja_ruta.equipo_asignado = ParamSist.ObtenerParametro("CAMION_GENERICO", "1")
            hoja_ruta.comprobante = self.view.grid_datos.ObtenerItem(fila=row,
                                col=self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'Comprobante'))
            hoja_ruta.comprobante = str(hoja_ruta.comprobante).replace('.', '')
            hoja_ruta.producto = producto
            hoja_ruta.cantidad = self.view.grid_datos.ObtenerItem(fila=row,
                                col=self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'Cantidad'))
            hoja_ruta.kg = self.view.grid_datos.ObtenerItem(fila=row,
                                col=self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'KG'))
            hoja_ruta.cantidad_bultos = self.view.grid_datos.ObtenerItem(fila=row,
                                col=self.obtener_proceso_list(self.view.empresa_proveedora.valor(), 'Bultos'))
            hoja_ruta.save()
        showAlert("Sistema", "Pedidos importados correctamente")
    
    
    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def obtener_proceso_list(self, proveedor, columna):
        try:
            return ProcesoLista.get(ProcesoLista.proveedor == proveedor, ProcesoLista.codigo == columna).columna
        except peewee.DoesNotExist:
            showAlert("Sistema", f"La columna {columna} no se encuentra en el proveedor {proveedor}")

    def importa_pdf_tremblay(self):
        """Importa pedidos desde un PDF de Tremblay.""" 
        if not self.view.txt_archivo.text():
            showAlert("Sistema", "Debe seleccionar un archivo PDF para importar")
            return
        # self.mostrar_mensaje_procesando()
        archivo_procesado = procesar_pdf_despacho(self.view.txt_archivo.valor())
        # self.cerrar_mensaje_procesando()
        if not archivo_procesado:
            showAlert("Sistema", "No se pudo procesar el archivo PDF")
            return
        self.view.txt_archivo.setText(archivo_procesado)
        QApplication.processEvents()

    def mostrar_mensaje_procesando(self):
        """Muestra un cuadro de diálogo no modal que informa sobre el procesamiento."""
        self.msg_box = QMessageBox(self.view)
        self.msg_box.setIcon(QMessageBox.Information)
        self.msg_box.setText("Procesando archivo PDF, por favor espere...")
        self.msg_box.setWindowTitle("Procesando")
        self.msg_box.setStandardButtons(QMessageBox.NoButton)  # Sin botones
        self.msg_box.show()

    def cerrar_mensaje_procesando(self):
        """Cierra el cuadro de diálogo de procesamiento si está abierto."""
        if self.msg_box:
            self.msg_box.close()
            self.msg_box = None

    def importa_tremblay(self):
        """Importa pedidos desde un archivo de Tremblay (.xls o .xlsx).

        - .xls: informe de despacho por cliente (layout nuevo) - usa
          `procesar_informe_tremblay`.
        - .xlsx: pedidos en formato viejo (layout MISIONES-tremblay) - usa
          `procesar_archivo_tremblay_excel`.

        En ambos casos devuelve la ruta de un xlsx temporal que el resto
        del controller trata como un pedido estandar.
        """
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
            showAlert("Sistema", f"No se pudo procesar el archivo: {exc}")
            return
        if not archivo_procesado:
            showAlert("Sistema", "No se pudo procesar el archivo")
            return
        self.view.txt_archivo.setText(archivo_procesado)
        QApplication.processEvents()
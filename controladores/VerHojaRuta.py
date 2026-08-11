from datetime import date
import peewee
from PyQt5.QtWidgets import QApplication

from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from vistas.VerHojaRuta import ModificaHojaDeRutaView, VerHojaRutaView


class VerHojaRutaController(ControladorBase):
    def __init__(self, fecha_inicial=None):
        super().__init__()
        self.view = VerHojaRutaView()
        if fecha_inicial is not None:
            self.view.fecha_reparto.setFecha(fecha_inicial)
        self.conectarWidgets()
    
    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_cargar.clicked.connect(self.on_click_btn_cargar)
        self.view.btn_grabar.clicked.connect(self.on_click_btn_grabar)
        self.view.btn_borrar.clicked.connect(self.on_click_btn_borrar)
        self.view.btn_imprimir.clicked.connect(self.on_click_btn_imprimir)
        self.view.btn_agregar.clicked.connect(self.on_click_btn_agregar)
        self.view.btn_modificar.clicked.connect(self.on_click_btn_modificar)
    
    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_cargar(self, *args, **kwargs):
        self.view.grilla_datos.limpiarGrilla()
        hoja_ruta = HojaDeRuta.select().where(
            HojaDeRuta.fecha == self.view.fecha_reparto.valor(),
            HojaDeRuta.ruta == self.view.cbo_ruta_reparto.valor(),
        )
        if self.view.equipo.lineEditCodigo.valor():
            hoja_ruta = hoja_ruta.where(
                HojaDeRuta.equipo_asignado == self.view.equipo.lineEditCodigo.valor()
            )
        if self.view.empleado.lineEditCodigo.valor():
            hoja_ruta = hoja_ruta.where(
                HojaDeRuta.responsable == self.view.empleado.lineEditCodigo.valor()
            )

        total = len(hoja_ruta)
        avance = 0
        self.view.equipo.lineEditCodigo.setText(hoja_ruta[0].equipo_asignado.id if total > 0 and hoja_ruta[0].equipo_asignado else 0)
        self.view.empleado.lineEditCodigo.setText(hoja_ruta[0].responsable.id if total > 0 and hoja_ruta[0].responsable else 0)
        self.view.empleado.lineEditCodigo.valida()
        self.view.equipo.lineEditCodigo.valida()
        for h in hoja_ruta:
            avance += 1
            self.view.avance.actualizar(avance / total * 100)
            QApplication.processEvents()
            seleccionado = False
            #si el equipo asignado o el empleado asignado a la hoja de ruta conincide con lo seleccionado marca como que esta seleccionado
            if h.equipo_asignado.id == int(self.view.equipo.lineEditCodigo.text()) or h.responsable.id == int(self.view.empleado.lineEditCodigo.text()):
                seleccionado = True

            # Verificar si el equipo o el responsable son genéricos
            if self.view.equipo.lineEditCodigo.valor() == ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or h.responsable.id == ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23"):
                seleccionado = False
            
            item = [
                seleccionado, h.nombre_cliente, h.comprobante, h.producto, h.cantidad, h.kg, h.cantidad_bultos, h.observaciones, h.id, h.cliente.id
            ]
            self.view.grilla_datos.AgregaItem(item)
        self.view.grilla_datos.setSortingEnabled(True)
        self.view.grilla_datos.resizeColumnsToContents()
        self.view.grilla_datos.resizeRowsToContents()
        self.view.avance.actualizar(100)
    
    @inicializar_y_capturar_excepciones
    def on_click_btn_grabar(self, *args, **kwargs):
        if not self.view.empleado.valor() or not self.view.equipo.valor():
            showAlert("Sistema", "Debe seleccionar un valor para Empleado y Camion")
        
        HojaDeRuta.update(
            responsable=ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23"),
            equipo_asignado=ParamSist.ObtenerParametro("CAMION_GENERICO", "1")
        ).where(
            (HojaDeRuta.fecha == self.view.fecha_reparto.valor()) &
            (HojaDeRuta.ruta == self.view.cbo_ruta_reparto.valor())
        ).execute()
        total = self.view.grilla_datos.rowCount()
        avance = 0
        for row in range(self.view.grilla_datos.rowCount()):
            avance += 1
            self.view.avance.actualizar(avance / total * 100)
            QApplication.processEvents()
            if not self.view.grilla_datos.ObtenerItem(fila=row, col='Selecciona'):
                continue
            id = self.view.grilla_datos.ObtenerItemNumerico(fila=row, col='id')
            try:
                hoja_ruta = HojaDeRuta.get_by_id(id)
            except peewee.DoesNotExist:
                hoja_ruta = HojaDeRuta()
            hoja_ruta.cliente = self.view.grilla_datos.ObtenerItem(fila=row, col='codigo_cliente')
            if hoja_ruta.cliente == 1:
                showAlert("Sistema", "No podemos asignar un cliente generico a la hoja de ruta")
                continue
            hoja_ruta.fecha = self.view.fecha_reparto.valor()
            hoja_ruta.ruta = self.view.cbo_ruta_reparto.valor()
            hoja_ruta.nombre_cliente = self.view.grilla_datos.ObtenerItem(fila=row, col='Cliente')
            hoja_ruta.responsable = self.view.empleado.valor()
            hoja_ruta.equipo_asignado = self.view.equipo.valor()
            hoja_ruta.comprobante = self.view.grilla_datos.ObtenerItem(fila=row, col='Comprobante')
            hoja_ruta.producto = self.view.grilla_datos.ObtenerItem(fila=row, col='Producto')
            hoja_ruta.cantidad = self.view.grilla_datos.ObtenerItem(fila=row, col='Cantidad')
            hoja_ruta.kg = self.view.grilla_datos.ObtenerItem(fila=row, col='KG')
            hoja_ruta.cantidad_bultos = self.view.grilla_datos.ObtenerItem(fila=row, col='Bultos')
            hoja_ruta.observaciones = self.view.grilla_datos.ObtenerItem(fila=row, col='Observaciones')
            hoja_ruta.save()
        showAlert("Sistema", "Hoja de ruta actualizada correctamente")

    
    @inicializar_y_capturar_excepciones
    def on_click_btn_borrar(self, *args, **kwargs):
        row = self.view.grilla_datos.currentRow()
        if row == -1:
            showAlert("ERROR", "Debe seleccionar un registro para borrar")
            return
        hoja_ruta = HojaDeRuta.get_by_id(self.view.grilla_datos.ObtenerItemNumerico(fila=row, col='ID'))
        hoja_ruta.delete_instance()
        self.on_click_btn_cargar()
    
    @inicializar_y_capturar_excepciones
    def on_click_btn_imprimir(self, *args, **kwargs):
        from utiles.Reportes import GeneradorPDFHojaRuta
        from tkinter import messagebox

        fecha = self.view.fecha_reparto.valor()
        ruta = self.view.cbo_ruta_reparto.valor()
        # Obtener responsable y equipo desde la vista
        # Asumo que el .valor() devuelve el ID y .labelNombre.text() el nombre.
        responsable = self.view.empleado.textNombre.text()
        equipo = self.view.equipo.textNombre.text()

        if not all([fecha, ruta, responsable, equipo]):
            messagebox.showwarning("Datos incompletos", "Por favor, seleccione fecha, ruta, responsable y equipo.")
            return

        try:
            hoja_ruta_query = HojaDeRuta.select().where(
                HojaDeRuta.fecha == fecha,
                HojaDeRuta.ruta == ruta
            )

            if not hoja_ruta_query.exists():
                messagebox.showinfo("Sin Datos", "No se encontraron registros para la fecha y ruta seleccionadas.")
                return
            if not responsable:
                responsable = hoja_ruta_query[0].responsable.nombre if hoja_ruta_query[0].responsable else "N/A"
            if not equipo:
                equipo = hoja_ruta_query[0].equipo_asignado.nombre if hoja_ruta_query[0].equipo_asignado else "N/A"
            # Instanciar y generar el reporte con los datos adicionales
            pdf = GeneradorPDFHojaRuta()
            pdf.generar_reporte(
                hoja_ruta_query=hoja_ruta_query, 
                fecha_reporte=fecha, 
                nombre_ruta=ruta,
                responsable=responsable,
                equipo=equipo
            )

        except Exception as e:
            messagebox.showerror("Error", f"Ocurrió un error al generar el reporte: {e}")
    
    @inicializar_y_capturar_excepciones
    def on_click_btn_agregar(self, *args, **kwargs):
        controlador = MdoficaHojaRutaController()
        controlador.ruta_id = self.view.cbo_ruta_reparto.valor()
        controlador.exec_()
        self.on_click_btn_cargar()

    @inicializar_y_capturar_excepciones
    def on_click_btn_modificar(self, *args, **kwargs):
        row = self.view.grilla_datos.currentRow()
        if row == -1:
            showAlert("ERROR", "Debe seleccionar un registro para modificar")
            return
        controlador = MdoficaHojaRutaController()
        controlador.hoja_ruta_id = self.view.grilla_datos.ObtenerItemNumerico(fila=row, col='id')
        controlador.ruta_id = self.view.cbo_ruta_reparto.valor()
        controlador.CargaDatos()
        controlador.exec_()
        self.on_click_btn_cargar()

class MdoficaHojaRutaController(ControladorBase):
    
    hoja_ruta_id = 0
    ruta_id = 0

    def __init__(self):
        super().__init__()
        self.view = ModificaHojaDeRutaView()
        self.conectarWidgets()
    
    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_grabar.clicked.connect(self.on_click_btn_grabar)
    
    @inicializar_y_capturar_excepciones
    def on_click_btn_grabar(self, *args, **kwargs):
        try:
            hoja_ruta = HojaDeRuta.get_by_id(self.hoja_ruta_id)
        except peewee.DoesNotExist:
            hoja_ruta = HojaDeRuta()
            hoja_ruta.fecha = date.today()
            
        hoja_ruta.cliente = self.view.cliente.valor()
        hoja_ruta.comprobante = self.view.text_comprobante.valor()
        hoja_ruta.producto = self.view.text_producto.valor()
        hoja_ruta.cantidad = self.view.text_cantidad.valor()
        hoja_ruta.kg = self.view.text_kg.valor()
        hoja_ruta.cantidad_bultos = self.view.text_bultos.valor()
        hoja_ruta.observaciones = self.view.text_observaciones.valor()
        hoja_ruta.responsable = self.view.layout_empleado.valor() if self.view.layout_empleado.valor() else ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23")
        hoja_ruta.equipo_asignado = self.view.layout_equipo.valor() if self.view.layout_equipo.valor() else ParamSist.ObtenerParametro("CAMION_GENERICO", "1")
        hoja_ruta.ruta = self.ruta_id
        hoja_ruta.nombre_cliente = self.view.cliente.labelNombre.text()
        hoja_ruta.save()

        self.view.Cerrar()
        
    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def CargaDatos(self, *args, **kwargs):
        if self.hoja_ruta_id == 0:
            return
        hoja_ruta = HojaDeRuta.get_by_id(self.hoja_ruta_id)
        self.view.cliente.lineEditCodigo.setText(hoja_ruta.cliente.id if hoja_ruta.cliente else 0)
        self.view.cliente.lineEditCodigo.valida()
        self.view.text_comprobante.setText(hoja_ruta.comprobante)
        self.view.text_producto.setText(hoja_ruta.producto)
        self.view.text_cantidad.setValue(hoja_ruta.cantidad)
        self.view.text_kg.setValue(hoja_ruta.kg)
        self.view.text_bultos.setValue(hoja_ruta.cantidad_bultos)
        self.view.text_observaciones.setText(hoja_ruta.observaciones if hoja_ruta.observaciones else "")
        self.view.layout_empleado.lineEditCodigo.setText(hoja_ruta.responsable.id if hoja_ruta.responsable else 0)
        self.view.layout_empleado.lineEditCodigo.valida()
        self.view.layout_equipo.lineEditCodigo.setText(hoja_ruta.equipo_asignado.id if hoja_ruta.equipo_asignado else 0)
        self.view.layout_equipo.lineEditCodigo.valida()

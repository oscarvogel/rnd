from datetime import date
import peewee
from PyQt5.QtWidgets import QApplication

from modelos.HojaRuta import HojaDeRuta
from modelos.EstadoHojaRuta import EstadoHojaRuta
from modelos.Empleados import Empleado
from modelos.Equipos import Equipos
from modelos.Documentos import actualizar_remito_de_hoja, referencias_por_hojas
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from vistas.VerHojaRuta import ModificaHojaDeRutaView, VerHojaRutaView


class VerHojaRutaController(ControladorBase):
    def __init__(self, fecha_inicial=None, ruta_inicial=0, permitir_continuar=True):
        super().__init__()
        self.view = VerHojaRutaView()
        self.ruta_inicial = int(ruta_inicial or 0)
        self.permitir_continuar = bool(permitir_continuar)
        if fecha_inicial is not None:
            self.view.fecha_reparto.setFecha(fecha_inicial)
        self._seleccionar_ruta_inicial()
        self.conectarWidgets()
        self.view.showMaximized()
        if self.ruta_inicial:
            self.on_click_btn_cargar()

    def _seleccionar_ruta_inicial(self):
        if not self.ruta_inicial:
            return
        combo = self.view.cbo_ruta_reparto
        if hasattr(combo, "setValor"):
            try:
                combo.setValor(self.ruta_inicial)
                return
            except Exception:
                pass
        if hasattr(combo, "setCurrentIndex") and hasattr(combo, "count") and hasattr(combo, "itemData"):
            for idx in range(combo.count()):
                if int(combo.itemData(idx) or 0) == self.ruta_inicial:
                    combo.setCurrentIndex(idx)
                    return
        for nombre in ("combo", "comboBox", "cbo"):
            interno = getattr(combo, nombre, None)
            if interno is None or not hasattr(interno, "count"):
                continue
            for idx in range(interno.count()):
                if int(interno.itemData(idx) or 0) == self.ruta_inicial:
                    interno.setCurrentIndex(idx)
                    return
    
    @staticmethod
    def _fk_id(registro, atributo):
        """Devuelve el id crudo de una FK sin forzar a Peewee a cargar la fila relacionada."""
        return int(getattr(registro, "{}_id".format(atributo), 0) or 0)

    @staticmethod
    def _limpiar_validador(validador):
        validador.lineEditCodigo.setText("")
        nombre = getattr(validador, "textNombre", None)
        if nombre is not None and hasattr(nombre, "setText"):
            nombre.setText("")

    def _cargar_recurso(self, validador, modelo, recurso_id, generico_id):
        """Carga un recurso real y deja en blanco los placeholders o referencias huérfanas."""
        recurso_id = int(recurso_id or 0)
        generico_id = int(generico_id or 0)
        if not recurso_id or recurso_id == generico_id:
            self._limpiar_validador(validador)
            return False

        if modelo.get_or_none(modelo.id == recurso_id) is None:
            self._limpiar_validador(validador)
            return False

        validador.lineEditCodigo.setText(str(recurso_id))
        validador.lineEditCodigo.valida()
        return True

    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_cargar.clicked.connect(self.on_click_btn_cargar)
        self.view.btn_grabar.clicked.connect(self.on_click_btn_grabar)
        self.view.btn_borrar.clicked.connect(self.on_click_btn_borrar)
        self.view.btn_imprimir.clicked.connect(self.on_click_btn_imprimir)
        self.view.btn_agregar.clicked.connect(self.on_click_btn_agregar)
        self.view.btn_modificar.clicked.connect(self.on_click_btn_modificar)
        self.view.btn_continuar.clicked.connect(self.ir_validacion)
    
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
        estado_registro = EstadoHojaRuta.get_or_none(
            (EstadoHojaRuta.fecha == self.view.fecha_reparto.valor()) &
            (EstadoHojaRuta.ruta == self.view.cbo_ruta_reparto.valor())
        )
        estado_operativo = (
            estado_registro.estado
            if estado_registro is not None
            else EstadoHojaRuta.EN_PREPARACION
        )
        kg_total = sum((h.kg or 0) for h in hoja_ruta) if total else 0
        bultos_total = sum((h.cantidad_bultos or 0) for h in hoja_ruta) if total else 0
        self.view.mostrar_estado_operativo(
            estado_operativo,
            total,
            kg_total,
            bultos_total,
            permitir_continuar=self.permitir_continuar,
        )
        fecha_txt = self.view.fecha_reparto.valor().strftime("%d/%m/%Y")
        ruta_txt = str(self.view.cbo_ruta_reparto.currentText()) if hasattr(self.view.cbo_ruta_reparto, "currentText") else str(self.view.cbo_ruta_reparto.valor())
        self.view.lbl_titulo_hoja.setText("Hoja de ruta - {} - {}".format(fecha_txt, ruta_txt))
        referencias = referencias_por_hojas([h.id for h in hoja_ruta]) if total else {}
        avance = 0
        empleado_generico = int(ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 0)
        camion_generico = int(ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 0)
        responsable_id = self._fk_id(hoja_ruta[0], "responsable") if total else 0
        equipo_id = self._fk_id(hoja_ruta[0], "equipo_asignado") if total else 0
        self._cargar_recurso(self.view.empleado, Empleado, responsable_id, empleado_generico)
        self._cargar_recurso(self.view.equipo, Equipos, equipo_id, camion_generico)

        responsable_seleccionado = int(self.view.empleado.lineEditCodigo.valor() or 0)
        equipo_seleccionado = int(self.view.equipo.lineEditCodigo.valor() or 0)
        for h in hoja_ruta:
            avance += 1
            self.view.avance.actualizar(avance / total * 100)
            QApplication.processEvents()
            h_equipo_id = self._fk_id(h, "equipo_asignado")
            h_responsable_id = self._fk_id(h, "responsable")
            seleccionado = (
                (equipo_seleccionado and h_equipo_id == equipo_seleccionado)
                or (responsable_seleccionado and h_responsable_id == responsable_seleccionado)
            )

            # Los IDs genéricos representan "pendiente"; no deben validarse ni
            # obligar a Peewee a buscar una fila que puede no existir.
            if h_equipo_id == camion_generico or h_responsable_id == empleado_generico:
                seleccionado = False
            
            referencia = referencias.get(h.id, {})
            item = [
                seleccionado, h.nombre_cliente, h.comprobante,
                referencia.get("factura") or h.comprobante or "",
                referencia.get("remito") or "",
                h.producto, h.cantidad, h.kg, h.cantidad_bultos,
                h.observaciones, h.id, int(getattr(h, "cliente_id", 0) or 0)
            ]
            self.view.grilla_datos.AgregaItem(item)
        self.view.grilla_datos.setSortingEnabled(True)
        self.view.grilla_datos.resizeColumnsToContents()
        self.view.grilla_datos.resizeRowsToContents()
        self.view.avance.actualizar(100)
        self.view.btn_imprimir.setEnabled(total > 0)
        if total:
            responsable_txt = self.view.empleado.textNombre.text() or "Chofer pendiente"
            equipo_txt = self.view.equipo.textNombre.text() or "Camión pendiente"
            self.view.lbl_estado_hoja.setText(
                "{} pedidos · Chofer: {} · Camión: {}".format(total, responsable_txt, equipo_txt)
            )
        else:
            self.view.lbl_estado_hoja.setText(
                "No hay datos para esta fecha y ruta. Revise la fecha, la ruta, la asignación de chofer/camión y que existan pedidos organizados."
            )
    
    def ir_validacion(self):
        ruta_id = int(self.view.cbo_ruta_reparto.valor() or 0)
        if not ruta_id:
            showAlert("Sistema", "Seleccione una ruta antes de continuar.")
            return
        from controladores.ValidacionHojaRuta import ValidacionHojaRutaController

        self.ventana_validacion = ValidacionHojaRutaController(
            fecha_inicial=self.view.fecha_reparto.valor(),
            ruta_inicial=ruta_id,
        )
        self.ventana_validacion.run()
        self.view.close()

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

        fecha = self.view.fecha_reparto.valor()
        ruta = self.view.cbo_ruta_reparto.valor()
        # Obtener responsable y equipo desde la vista
        # Asumo que el .valor() devuelve el ID y .labelNombre.text() el nombre.
        responsable = self.view.empleado.textNombre.text()
        equipo = self.view.equipo.textNombre.text()

        if not all([fecha, ruta, responsable, equipo]):
            showAlert("Datos incompletos", "Seleccione fecha, ruta, responsable y equipo antes de imprimir.")
            return

        try:
            hoja_ruta_query = HojaDeRuta.select().where(
                HojaDeRuta.fecha == fecha,
                HojaDeRuta.ruta == ruta
            )

            if not hoja_ruta_query.exists():
                showAlert("Sin datos", "No se encontraron registros para la fecha y ruta seleccionadas.")
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
            showAlert("Error", "Ocurrió un error al generar el reporte: {}".format(e))
    
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
        if hoja_ruta.id:
            actualizar_remito_de_hoja(hoja_ruta.id, self.view.text_remito.valor())

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
        referencia = referencias_por_hojas([hoja_ruta.id]).get(hoja_ruta.id, {})
        self.view.text_factura.setText(referencia.get("factura") or hoja_ruta.comprobante or "")
        self.view.text_remito.setText(referencia.get("remito") or "")
        self.view.text_producto.setText(hoja_ruta.producto)
        self.view.text_cantidad.setValue(hoja_ruta.cantidad)
        self.view.text_kg.setValue(hoja_ruta.kg)
        self.view.text_bultos.setValue(hoja_ruta.cantidad_bultos)
        self.view.text_observaciones.setText(hoja_ruta.observaciones if hoja_ruta.observaciones else "")
        self._cargar_recurso(
            self.view.layout_empleado,
            Empleado,
            self._fk_id(hoja_ruta, "responsable"),
            int(ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 0),
        )
        self._cargar_recurso(
            self.view.layout_equipo,
            Equipos,
            self._fk_id(hoja_ruta, "equipo_asignado"),
            int(ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 0),
        )

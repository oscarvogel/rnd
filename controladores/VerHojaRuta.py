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
        self.responsable_actual = "Chofer pendiente"
        self.equipo_actual = "Camión pendiente"
        self.recursos_completos_actual = False
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
        self.view.btn_recursos.clicked.connect(self.modificar_recursos)
        self.view.btn_borrar.clicked.connect(self.on_click_btn_borrar)
        self.view.btn_imprimir.clicked.connect(self.on_click_btn_imprimir)
        self.view.btn_agregar.clicked.connect(self.on_click_btn_agregar)
        self.view.btn_modificar.clicked.connect(self.on_click_btn_modificar)
        self.view.btn_continuar.clicked.connect(self.ir_validacion)
    
    def _nombre_responsable(self, recurso_id, generico_id):
        recurso_id = int(recurso_id or 0)
        if not recurso_id or recurso_id == int(generico_id or 0):
            return "Chofer pendiente"
        registro = Empleado.get_or_none(Empleado.id == recurso_id)
        return registro.nombre_completo if registro is not None else "Chofer #{}".format(recurso_id)

    def _nombre_equipo(self, recurso_id, generico_id):
        recurso_id = int(recurso_id or 0)
        if not recurso_id or recurso_id == int(generico_id or 0):
            return "Camión pendiente"
        registro = Equipos.get_or_none(Equipos.id == recurso_id)
        return str(registro) if registro is not None else "Camión #{}".format(recurso_id)

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_cargar(self, *args, **kwargs):
        self.view.grilla_datos.limpiarGrilla()
        registros = list(
            HojaDeRuta.select().where(
                HojaDeRuta.fecha == self.view.fecha_reparto.valor(),
                HojaDeRuta.ruta == self.view.cbo_ruta_reparto.valor(),
            )
        )

        total = len(registros)
        empleado_generico = int(
            ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 0
        )
        camion_generico = int(
            ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 0
        )

        responsables = {
            self._fk_id(registro, "responsable")
            for registro in registros
        }
        equipos = {
            self._fk_id(registro, "equipo_asignado")
            for registro in registros
        }
        responsable_id = next(iter(responsables)) if len(responsables) == 1 else 0
        equipo_id = next(iter(equipos)) if len(equipos) == 1 else 0
        recursos_uniformes = len(responsables) == 1 and len(equipos) == 1
        recursos_completos = bool(total) and recursos_uniformes and (
            responsable_id not in (0, empleado_generico)
            and equipo_id not in (0, camion_generico)
        )

        if total and not recursos_uniformes:
            responsable_txt = "Asignación mixta"
            equipo_txt = "Asignación mixta"
        else:
            responsable_txt = self._nombre_responsable(
                responsable_id, empleado_generico
            )
            equipo_txt = self._nombre_equipo(equipo_id, camion_generico)

        self.responsable_actual = responsable_txt
        self.equipo_actual = equipo_txt
        self.recursos_completos_actual = recursos_completos
        self.view.mostrar_recursos(responsable_txt, equipo_txt)

        estado_registro = EstadoHojaRuta.get_or_none(
            (EstadoHojaRuta.fecha == self.view.fecha_reparto.valor()) &
            (EstadoHojaRuta.ruta == self.view.cbo_ruta_reparto.valor())
        )
        estado_operativo = (
            estado_registro.estado
            if estado_registro is not None
            else EstadoHojaRuta.EN_PREPARACION
        )
        kg_total = sum((h.kg or 0) for h in registros) if total else 0
        bultos_total = sum((h.cantidad_bultos or 0) for h in registros) if total else 0
        self.view.mostrar_estado_operativo(
            estado_operativo,
            total,
            kg_total,
            bultos_total,
            permitir_continuar=self.permitir_continuar,
            recursos_completos=recursos_completos,
        )

        fecha_txt = self.view.fecha_reparto.valor().strftime("%d/%m/%Y")
        ruta_txt = (
            str(self.view.cbo_ruta_reparto.currentText())
            if hasattr(self.view.cbo_ruta_reparto, "currentText")
            else str(self.view.cbo_ruta_reparto.valor())
        )
        self.view.lbl_titulo_hoja.setText(
            "Hoja de ruta - {} - {}".format(fecha_txt, ruta_txt)
        )

        referencias = referencias_por_hojas([h.id for h in registros]) if total else {}
        for avance, h in enumerate(registros, start=1):
            self.view.avance.actualizar(avance / total * 100)
            QApplication.processEvents()
            referencia = referencias.get(h.id, {})
            item = [
                False, h.nombre_cliente, h.comprobante,
                referencia.get("factura") or h.comprobante or "",
                referencia.get("remito") or "",
                h.producto, h.cantidad, h.kg, h.cantidad_bultos,
                h.observaciones, h.id, int(getattr(h, "cliente_id", 0) or 0)
            ]
            self.view.grilla_datos.AgregaItem(item)

        self.view.grilla_datos.setSortingEnabled(True)
        self.view.grilla_datos.resizeColumnsToContents()
        self.view.grilla_datos.resizeRowsToContents()
        self.view.avance.actualizar(100 if total else 0)

        if total and recursos_completos:
            self.view.lbl_estado_hoja.setText(
                "{} pedidos · Chofer: {} · Camión: {}".format(
                    total, responsable_txt, equipo_txt
                )
            )
        elif total:
            self.view.lbl_estado_hoja.setText(
                "{} pedidos · Falta corregir la asignación de chofer/camión.".format(
                    total
                )
            )
        else:
            self.view.lbl_estado_hoja.setText(
                "No hay datos para esta fecha y ruta. Revise la fecha, la ruta, "
                "la asignación de chofer/camión y que existan pedidos organizados."
            )

    def modificar_recursos(self):
        ruta_id = int(self.view.cbo_ruta_reparto.valor() or 0)
        if not ruta_id:
            showAlert("Sistema", "Seleccione una ruta antes de modificar recursos.")
            return
        from controladores.AsignacionRecursos import AsignacionRecursosController

        self.ventana_recursos = AsignacionRecursosController(
            fecha_inicial=self.view.fecha_reparto.valor(),
            ruta_inicial=ruta_id,
        )
        self.ventana_recursos.run()
        self.view.close()
    
    def ir_validacion(self):
        ruta_id = int(self.view.cbo_ruta_reparto.valor() or 0)
        if not ruta_id:
            showAlert("Sistema", "Seleccione una ruta antes de continuar.")
            return
        if not self.recursos_completos_actual:
            showAlert(
                "Sistema",
                "Asigne un chofer y un camión válidos antes de continuar.",
            )
            return
        from controladores.ValidacionHojaRuta import ValidacionHojaRutaController

        self.ventana_validacion = ValidacionHojaRutaController(
            fecha_inicial=self.view.fecha_reparto.valor(),
            ruta_inicial=ruta_id,
        )
        self.ventana_validacion.run()
        self.view.close()

    
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
        responsable = self.responsable_actual
        equipo = self.equipo_actual

        if not self.recursos_completos_actual:
            showAlert(
                "Datos incompletos",
                "Asigne un chofer y un camión válidos antes de generar el PDF.",
            )
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
        controlador.fecha = self.view.fecha_reparto.valor()
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
        controlador.fecha = self.view.fecha_reparto.valor()
        controlador.CargaDatos()
        controlador.exec_()
        self.on_click_btn_cargar()

class MdoficaHojaRutaController(ControladorBase):
    
    hoja_ruta_id = 0
    ruta_id = 0
    fecha = None

    @staticmethod
    def _fk_id(registro, atributo):
        if registro is None:
            return 0
        return int(getattr(registro, "{}_id".format(atributo), 0) or 0)

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
            hoja_ruta.fecha = self.fecha or date.today()
            
        hoja_ruta.cliente = self.view.cliente.valor()
        hoja_ruta.comprobante = self.view.text_comprobante.valor()
        hoja_ruta.producto = self.view.text_producto.valor()
        hoja_ruta.cantidad = self.view.text_cantidad.valor()
        hoja_ruta.kg = self.view.text_kg.valor()
        hoja_ruta.cantidad_bultos = self.view.text_bultos.valor()
        hoja_ruta.observaciones = self.view.text_observaciones.valor()
        # Chofer y camión se administran únicamente desde Asignar recursos.
        # En altas nuevas se heredan de la hoja/ruta existente para no crear
        # asignaciones mixtas por renglón.
        if not getattr(hoja_ruta, "responsable_id", None) or not getattr(
            hoja_ruta, "equipo_asignado_id", None
        ):
            referencia_recursos = (
                HojaDeRuta.select()
                .where(
                    (HojaDeRuta.ruta == self.ruta_id) &
                    (HojaDeRuta.fecha == hoja_ruta.fecha)
                )
                .order_by(HojaDeRuta.id)
                .first()
            )
            hoja_ruta.responsable = (
                self._fk_id(referencia_recursos, "responsable")
                if referencia_recursos is not None
                else ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23")
            )
            hoja_ruta.equipo_asignado = (
                self._fk_id(referencia_recursos, "equipo_asignado")
                if referencia_recursos is not None
                else ParamSist.ObtenerParametro("CAMION_GENERICO", "1")
            )
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
        self.view.text_observaciones.setText(
            hoja_ruta.observaciones if hoja_ruta.observaciones else ""
        )

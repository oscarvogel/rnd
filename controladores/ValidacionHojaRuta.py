# coding=utf-8
from datetime import date, datetime

from PyQt5.QtCore import QDate

from modelos.Clientes import RutaReparto
from modelos.EstadoHojaRuta import EstadoHojaRuta
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import LeerConf, inicializar_y_capturar_excepciones
from utiles.validacion_hoja_ruta import puede_transicionar, validar_hoja
from vistas.ValidacionHojaRuta import ValidacionHojaRutaView


class ValidacionHojaRutaController(ControladorBase):
    def __init__(self, fecha_inicial=None, ruta_inicial=0):
        super().__init__()
        self.view = ValidacionHojaRutaView()
        self.empleado_generico = int(ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 23)
        self.camion_generico = int(ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 1)
        self.ruta_inicial = int(ruta_inicial or 0)
        inicial = fecha_inicial or date.today()
        self.view.fecha.setDate(QDate(inicial.year, inicial.month, inicial.day))
        self.resultado_actual = validar_hoja([], inicial, self.ruta_inicial, self.empleado_generico, self.camion_generico)
        self.estado_actual = EstadoHojaRuta.EN_PREPARACION
        self.conectarWidgets()
        self.cargar_rutas()
        if self.ruta_inicial:
            self.cargar()

    def conectarWidgets(self):
        self.view.btn_cargar.clicked.connect(self.cargar)
        self.view.cbo_ruta.currentIndexChanged.connect(self.cargar)
        self.view.btn_lista.clicked.connect(lambda: self.cambiar_estado(EstadoHojaRuta.LISTA))
        self.view.btn_despachar.clicked.connect(lambda: self.cambiar_estado(EstadoHojaRuta.DESPACHADA))
        self.view.btn_asignar.clicked.connect(self.resolver_recursos)
        self.view.btn_cerrar.clicked.connect(self.view.close)

    def fecha_actual(self):
        qdate = self.view.fecha.date()
        return date(qdate.year(), qdate.month(), qdate.day())

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar_rutas(self, *args, **kwargs):
        rutas = RutaReparto.select().where(RutaReparto.activo == True).order_by(RutaReparto.descripcion)
        self.view.cargar_rutas([(r.id, r.descripcion) for r in rutas], self.ruta_inicial)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar(self, *args, **kwargs):
        ruta_id = self.view.ruta_id()
        fecha = self.fecha_actual()
        if not ruta_id:
            self.resultado_actual = validar_hoja([], fecha, 0, self.empleado_generico, self.camion_generico)
            self.estado_actual = EstadoHojaRuta.EN_PREPARACION
            self.view.mostrar(self.resultado_actual, self.estado_actual)
            return

        registros = list(HojaDeRuta.select().where((HojaDeRuta.fecha == fecha) & (HojaDeRuta.ruta == ruta_id)))
        self.resultado_actual = validar_hoja(registros, fecha, ruta_id, self.empleado_generico, self.camion_generico)
        estado = EstadoHojaRuta.get_or_none(
            (EstadoHojaRuta.fecha == fecha) & (EstadoHojaRuta.ruta == ruta_id)
        )
        self.estado_actual = estado.estado if estado else EstadoHojaRuta.EN_PREPARACION
        self.view.mostrar(self.resultado_actual, self.estado_actual)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cambiar_estado(self, destino):
        ruta_id = self.view.ruta_id()
        if not ruta_id:
            showAlert("Sistema", "Seleccione una ruta")
            return
        permitido, mensaje = puede_transicionar(self.estado_actual, destino, self.resultado_actual)
        if not permitido:
            showAlert("Sistema", mensaje)
            return

        estado, _ = EstadoHojaRuta.get_or_create(
            fecha=self.fecha_actual(),
            ruta=ruta_id,
            defaults={"estado": EstadoHojaRuta.EN_PREPARACION},
        )
        estado.estado = destino
        estado.actualizado_en = datetime.now()
        estado.actualizado_por = LeerConf("usuario") or ""
        estado.save()
        showAlert("Sistema", "Hoja de ruta actualizada a {}".format(destino))
        self.cargar()

    def resolver_recursos(self):
        from controladores.AsignacionRecursos import AsignacionRecursosController
        self.ventana_siguiente = AsignacionRecursosController(
            fecha_inicial=self.fecha_actual(),
            ruta_inicial=self.view.ruta_id(),
        )
        self.ventana_siguiente.run()

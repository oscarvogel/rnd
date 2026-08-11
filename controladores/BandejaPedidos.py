# coding=utf-8
from datetime import date

from PyQt5.QtCore import QDate

from modelos.Clientes import RutaReparto
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from utiles.bandeja_pedidos import PedidoBandeja, totales_seleccion, validar_reasignacion
from vistas.BandejaPedidos import BandejaPedidosView


class BandejaPedidosController(ControladorBase):
    def __init__(self, fecha_inicial=None):
        super().__init__()
        self.view = BandejaPedidosView()
        self._pedidos = []
        self.empleado_generico = ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23")
        self.camion_generico = ParamSist.ObtenerParametro("CAMION_GENERICO", "1")
        inicial = fecha_inicial or date.today()
        self.view.fecha.setDate(QDate(inicial.year, inicial.month, inicial.day))
        self.view.on_selection_changed = self.actualizar_totales
        self.conectarWidgets()
        self.cargar_rutas()
        self.cargar_pedidos()

    def conectarWidgets(self):
        self.view.btn_actualizar.clicked.connect(self.cargar_pedidos)
        self.view.solo_pendientes.toggled.connect(self.cargar_pedidos)
        self.view.btn_organizar.clicked.connect(self.organizar_seleccion)
        self.view.btn_siguiente.clicked.connect(self.ir_asignacion)

    def fecha_actual(self):
        qdate = self.view.fecha.date()
        return date(qdate.year(), qdate.month(), qdate.day())

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar_rutas(self, *args, **kwargs):
        rutas = RutaReparto.select().where(RutaReparto.activo == True).order_by(RutaReparto.descripcion)
        self.view.cargar_rutas([(r.id, r.descripcion) for r in rutas])

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar_pedidos(self, *args, **kwargs):
        query = (
            HojaDeRuta.select(HojaDeRuta, RutaReparto)
            .join(RutaReparto)
            .where(HojaDeRuta.fecha == self.fecha_actual())
            .order_by(HojaDeRuta.ruta, HojaDeRuta.nombre_cliente, HojaDeRuta.id)
        )
        pedidos = [self._convertir(h) for h in query]
        if self.view.solo_pendientes.isChecked():
            pedidos = [
                p for p in pedidos
                if p.estado(self.empleado_generico, self.camion_generico) != "organizado"
            ]
        self._pedidos = pedidos
        self.view.cargar_pedidos(pedidos, self.empleado_generico, self.camion_generico)
        self.actualizar_totales()

    def _convertir(self, h):
        return PedidoBandeja(
            id=h.id,
            cliente=h.nombre_cliente or "",
            comprobante=h.comprobante or "",
            producto=h.producto or "",
            cantidad=h.cantidad or 0,
            kg=h.kg or 0,
            bultos=h.cantidad_bultos or 0,
            observaciones=h.observaciones or "",
            ruta_id=h.ruta_id or 0,
            ruta=h.ruta.descripcion if h.ruta_id else "Sin ruta",
            responsable_id=h.responsable_id or 0,
            equipo_id=h.equipo_asignado_id or 0,
        )

    def pedidos_seleccionados(self):
        ids = set(self.view.ids_seleccionados())
        return [p for p in self._pedidos if p.id in ids]

    def actualizar_totales(self):
        totales = totales_seleccion(self.pedidos_seleccionados())
        self.view.set_totales(totales["pedidos"], totales["kg"], totales["bultos"])

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def organizar_seleccion(self, *args, **kwargs):
        pedidos = self.pedidos_seleccionados()
        ruta_id = self.view.ruta_destino()
        valido, mensaje = validar_reasignacion(pedidos, ruta_id)
        if not valido:
            showAlert("Sistema", mensaje)
            return

        ids = [p.id for p in pedidos]
        actualizados = (
            HojaDeRuta.update(ruta=ruta_id)
            .where((HojaDeRuta.id.in_(ids)) & (HojaDeRuta.fecha == self.fecha_actual()))
            .execute()
        )
        if actualizados != len(ids):
            showAlert("Sistema", "No se pudieron actualizar todos los pedidos seleccionados")
            return

        self.view.btn_siguiente.setEnabled(True)
        showAlert("Sistema", "Pedidos organizados correctamente. El siguiente paso es asignar chofer y camión.")
        self.cargar_pedidos()

    def ir_asignacion(self):
        from controladores.VerHojaRuta import VerHojaRutaController
        self.ventana_siguiente = VerHojaRutaController(fecha_inicial=self.fecha_actual())
        self.ventana_siguiente.run()

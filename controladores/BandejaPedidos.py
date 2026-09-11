# coding=utf-8
from datetime import date

from PyQt5.QtCore import QDate

from modelos.Clientes import RutaReparto
from modelos.HojaRuta import HojaDeRuta
from modelos.Documentos import referencias_por_hojas
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
        self._ultima_ruta_organizada = 0
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
        hojas = list(query)
        referencias = referencias_por_hojas([h.id for h in hojas])
        pedidos = [self._convertir(h, referencias.get(h.id, {})) for h in hojas]
        if self.view.solo_pendientes.isChecked():
            pedidos = [
                p for p in pedidos
                if p.estado(self.empleado_generico, self.camion_generico) != "organizado"
            ]
        self._pedidos = pedidos
        self.view.cargar_pedidos(pedidos, self.empleado_generico, self.camion_generico)
        self.actualizar_totales()

    def _convertir(self, h, referencia=None):
        referencia = referencia or {}
        return PedidoBandeja(
            id=h.id,
            cliente=h.nombre_cliente or "",
            comprobante=h.comprobante or "",
            producto=h.producto or "",
            factura=referencia.get("factura") or h.comprobante or "",
            remito=referencia.get("remito") or "",
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

        try:
            ruta = RutaReparto.get_by_id(ruta_id)
            ruta_nombre = ruta.descripcion
        except Exception:
            ruta_nombre = "ruta #{}".format(ruta_id)

        ids = [p.id for p in pedidos]
        actualizados = (
            HojaDeRuta.update(ruta=ruta_id)
            .where((HojaDeRuta.id.in_(ids)) & (HojaDeRuta.fecha == self.fecha_actual()))
            .execute()
        )
        if actualizados != len(ids):
            showAlert("Sistema", "No se pudieron actualizar todos los pedidos seleccionados")
            return

        # Verificación real contra la base antes de informar éxito. Evita continuar
        # a una ruta distinta de la efectivamente grabada.
        verificados = (
            HojaDeRuta.select()
            .where(
                (HojaDeRuta.id.in_(ids)) &
                (HojaDeRuta.fecha == self.fecha_actual()) &
                (HojaDeRuta.ruta == ruta_id)
            )
            .count()
        )
        if verificados != len(ids):
            showAlert(
                "Sistema",
                "La ruta no quedó grabada correctamente en todos los pedidos. "
                "No se continuará a asignar chofer y camión.",
            )
            self.view.btn_siguiente.setEnabled(False)
            return

        self._ultima_ruta_organizada = int(ruta_id)
        self.view.btn_siguiente.setEnabled(True)
        showAlert(
            "Sistema",
            "{} pedidos organizados en {}. El siguiente paso es asignar chofer y camión.".format(
                len(ids), ruta_nombre
            ),
        )
        self.cargar_pedidos()

    def ir_asignacion(self):
        from controladores.AsignacionRecursos import AsignacionRecursosController

        # La asignación debe abrir exactamente la última ruta que se acaba de
        # organizar, no una selección posterior del combo.
        ruta_id = int(self._ultima_ruta_organizada or self.view.ruta_destino() or 0)
        if not ruta_id:
            showAlert("Sistema", "Seleccione y organice pedidos en una ruta antes de continuar.")
            return

        self.ventana_siguiente = AsignacionRecursosController(
            fecha_inicial=self.fecha_actual(),
            ruta_inicial=ruta_id,
        )
        self.ventana_siguiente.run()

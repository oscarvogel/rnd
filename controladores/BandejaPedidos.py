# coding=utf-8
from datetime import date

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout
from peewee import JOIN

from modelos.Clientes import Cliente, LugarEntrega, RutaReparto
from modelos.HojaRuta import HojaDeRuta
from modelos.Documentos import DocumentoPedido, DocumentoPedidoDetalle, DocumentoPedidoHojaRuta, referencias_por_hojas
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from utiles.bandeja_pedidos import PedidoBandeja, expandir_seleccion_por_factura, totales_seleccion, validar_reasignacion
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
        self.view.btn_cliente_lugar.clicked.connect(self.asignar_cliente_lugar)
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
            .join(RutaReparto, JOIN.LEFT_OUTER)
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
        cliente_nombre = h.nombre_cliente or ""
        if h.cliente_id:
            try:
                cliente_nombre = h.cliente.razon_social or cliente_nombre
            except Exception:
                pass
        lugar_nombre = ""
        if h.lugar_entrega_id:
            try:
                lugar_nombre = h.lugar_entrega.nombre or ""
            except Exception:
                pass
        return PedidoBandeja(
            id=h.id,
            cliente=cliente_nombre,
            cliente_id=h.cliente_id or 0,
            lugar_entrega=lugar_nombre,
            lugar_entrega_id=h.lugar_entrega_id or 0,
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
    def asignar_cliente_lugar(self, *args, **kwargs):
        seleccionados = self.pedidos_seleccionados()
        if not seleccionados:
            showAlert("Sistema", "Seleccione al menos un pedido para asignar cliente y lugar de entrega")
            return
        pedidos = expandir_seleccion_por_factura(self._pedidos, seleccionados)

        dialogo = QDialog(self.view)
        dialogo.setWindowTitle("Asignar cliente y lugar de entrega")
        dialogo.setMinimumWidth(520)
        layout = QVBoxLayout(dialogo)
        facturas = sorted({str(p.factura or p.comprobante or "").strip() for p in pedidos if str(p.factura or p.comprobante or "").strip()})
        layout.addWidget(QLabel(
            "La asignación se aplicará a {} línea(s) de {} factura(s).".format(
                len(pedidos), len(facturas) or 1
            )
        ))

        fila_cliente = QHBoxLayout()
        fila_cliente.addWidget(QLabel("Cliente:"))
        cbo_cliente = QComboBox()
        cbo_cliente.setMinimumWidth(340)
        fila_cliente.addWidget(cbo_cliente, 1)
        layout.addLayout(fila_cliente)

        fila_lugar = QHBoxLayout()
        fila_lugar.addWidget(QLabel("Lugar de entrega:"))
        cbo_lugar = QComboBox()
        cbo_lugar.setMinimumWidth(340)
        fila_lugar.addWidget(cbo_lugar, 1)
        layout.addLayout(fila_lugar)

        btn_gestionar = QPushButton("Crear / editar clientes y lugares")
        layout.addWidget(btn_gestionar)

        clientes = list(Cliente.select().where(Cliente.activo == True).order_by(Cliente.razon_social))
        cbo_cliente.addItem("Seleccione un cliente", 0)
        for cliente in clientes:
            cbo_cliente.addItem(cliente.razon_social, cliente.id)

        def cargar_lugares():
            cbo_lugar.clear()
            cliente_id = int(cbo_cliente.currentData() or 0)
            if not cliente_id:
                cbo_lugar.addItem("Seleccione primero un cliente", 0)
                return
            lugares = list(LugarEntrega.activos_cliente(cliente_id))
            if not lugares:
                cbo_lugar.addItem("Este cliente no tiene lugares activos", 0)
                return
            cbo_lugar.addItem("Seleccione un lugar de entrega", 0)
            for lugar in lugares:
                texto = lugar.nombre
                if lugar.direccion:
                    texto += " — {}".format(lugar.direccion)
                cbo_lugar.addItem(texto, lugar.id)
            principal = next((x for x in lugares if x.principal), None)
            elegido = principal or (lugares[0] if len(lugares) == 1 else None)
            if elegido is not None:
                idx = cbo_lugar.findData(elegido.id)
                if idx >= 0:
                    cbo_lugar.setCurrentIndex(idx)

        cbo_cliente.currentIndexChanged.connect(cargar_lugares)
        cargar_lugares()

        cliente_ids = {p.cliente_id for p in pedidos if p.cliente_id}
        if len(cliente_ids) == 1:
            cliente_id = next(iter(cliente_ids))
            idx = cbo_cliente.findData(cliente_id)
            if idx >= 0:
                cbo_cliente.setCurrentIndex(idx)
                lugares_actuales = {p.lugar_entrega_id for p in pedidos if p.lugar_entrega_id}
                if len(lugares_actuales) == 1:
                    idx_lugar = cbo_lugar.findData(next(iter(lugares_actuales)))
                    if idx_lugar >= 0:
                        cbo_lugar.setCurrentIndex(idx_lugar)

        def gestionar_clientes():
            from controladores.ABMClientes import ABMClientesController
            self.gestor_clientes = ABMClientesController()
            self.gestor_clientes.run()

        btn_gestionar.clicked.connect(gestionar_clientes)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)
        if dialogo.exec_() != QDialog.Accepted:
            return

        cliente_id = int(cbo_cliente.currentData() or 0)
        lugar_id = int(cbo_lugar.currentData() or 0)
        if not cliente_id or not lugar_id:
            showAlert("Sistema", "Debe seleccionar un cliente y un lugar de entrega")
            return

        lugar = LugarEntrega.get_or_none(
            (LugarEntrega.id == lugar_id) &
            (LugarEntrega.cliente == cliente_id) &
            (LugarEntrega.activo == True)
        )
        if lugar is None:
            showAlert("Sistema", "El lugar de entrega seleccionado ya no está disponible")
            return

        cliente = Cliente.get_by_id(cliente_id)
        ruta_id = lugar.ruta_reparto_id or cliente.ruta_reparto_id
        ids = [p.id for p in pedidos]
        actualizados = (
            HojaDeRuta.update(
                cliente=cliente_id,
                lugar_entrega=lugar_id,
                ruta=ruta_id,
                nombre_cliente=cliente.razon_social,
            )
            .where(HojaDeRuta.id.in_(ids))
            .execute()
        )
        if actualizados != len(ids):
            showAlert("Sistema", "No se pudieron actualizar todos los pedidos seleccionados")
            return

        documentos = (
            DocumentoPedido.select()
            .join(DocumentoPedidoDetalle)
            .join(DocumentoPedidoHojaRuta)
            .where(DocumentoPedidoHojaRuta.hoja_ruta.in_(ids))
        )
        DocumentoPedido.update(cliente=cliente_id).where(
            DocumentoPedido.id.in_([doc.id for doc in documentos])
        ).execute()

        showAlert(
            "Sistema",
            "Cliente y lugar de entrega asignados a {} línea(s).".format(len(ids)),
        )
        self.cargar_pedidos()

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

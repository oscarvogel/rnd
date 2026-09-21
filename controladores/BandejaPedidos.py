# coding=utf-8
from datetime import date
import re
import unicodedata

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import QComboBox, QCompleter, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout
from peewee import JOIN

from modelos.Clientes import Cliente, LugarEntrega, RutaReparto
from modelos.HojaRuta import HojaDeRuta
from modelos.Documentos import DocumentoPedido, DocumentoPedidoDetalle, DocumentoPedidoHojaRuta, actualizar_remito_de_hoja, referencias_por_hojas
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
        self.view.btn_editar_pedido.clicked.connect(self.editar_pedido_actual)
        self.view.tabla.doubleClicked.connect(self.editar_pedido_actual)
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
    def editar_pedido_actual(self, *args, **kwargs):
        hoja_id = int(self.view.id_fila_actual() or 0)
        if not hoja_id:
            showAlert("Sistema", "Seleccione una fila para editar")
            return

        hoja = HojaDeRuta.get_by_id(hoja_id)
        referencias = referencias_por_hojas([hoja_id]).get(hoja_id, {})

        dialogo = QDialog(self.view)
        dialogo.setWindowTitle("Editar pedido")
        dialogo.setMinimumWidth(620)
        layout = QVBoxLayout(dialogo)
        form = QFormLayout()
        layout.addLayout(form)

        clientes = list(
            Cliente.select()
            .where(Cliente.activo == True)
            .order_by(Cliente.razon_social)
        )

        cbo_cliente = QComboBox()
        cbo_cliente.setEditable(True)
        cbo_cliente.setInsertPolicy(QComboBox.NoInsert)
        cbo_cliente.lineEdit().setPlaceholderText("Buscar cliente...")
        cbo_cliente.addItem("", 0)
        for cliente in clientes:
            cbo_cliente.addItem(cliente.razon_social, cliente.id)

        completer = QCompleter(cbo_cliente.model(), cbo_cliente)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        cbo_cliente.setCompleter(completer)

        cbo_lugar = QComboBox()
        cbo_ruta = QComboBox()
        cbo_ruta.addItem("Sin ruta", 0)
        for ruta in RutaReparto.select().where(RutaReparto.activo == True).order_by(RutaReparto.descripcion):
            cbo_ruta.addItem(ruta.descripcion, ruta.id)

        txt_producto = QLineEdit(hoja.producto or "")
        sp_cantidad = QDoubleSpinBox()
        sp_cantidad.setDecimals(2)
        sp_cantidad.setMaximum(999999999)
        sp_cantidad.setValue(float(hoja.cantidad or 0))

        sp_kg = QDoubleSpinBox()
        sp_kg.setDecimals(3)
        sp_kg.setMaximum(999999999)
        sp_kg.setValue(float(hoja.kg or 0))

        sp_bultos = QDoubleSpinBox()
        sp_bultos.setDecimals(2)
        sp_bultos.setMaximum(999999999)
        sp_bultos.setValue(float(hoja.cantidad_bultos or 0))

        txt_remito = QLineEdit(str(referencias.get("remito") or ""))
        txt_observaciones = QLineEdit(hoja.observaciones or "")

        def normalizar(valor):
            texto = str(valor or "").strip().upper()
            texto = "".join(
                ch for ch in unicodedata.normalize("NFD", texto)
                if unicodedata.category(ch) != "Mn"
            )
            texto = re.sub(r"[^A-Z0-9]+", " ", texto)
            return " ".join(texto.split())

        def resolver_cliente_id():
            data = int(cbo_cliente.currentData() or 0)
            texto = str(cbo_cliente.currentText() or "").strip()
            if data and texto:
                return data
            clave = normalizar(texto)
            for cliente in clientes:
                if normalizar(cliente.razon_social) == clave:
                    idx = cbo_cliente.findData(cliente.id)
                    if idx >= 0:
                        cbo_cliente.setCurrentIndex(idx)
                    return int(cliente.id)
            return 0

        def cargar_lugares(*_):
            cbo_lugar.clear()
            cliente_id = resolver_cliente_id()
            if not cliente_id:
                cbo_lugar.addItem("Sin asignar", 0)
                return
            lugares = list(LugarEntrega.activos_cliente(cliente_id))
            cbo_lugar.addItem("Sin asignar", 0)
            for lugar in lugares:
                texto = lugar.nombre
                if lugar.direccion:
                    texto += " — {}".format(lugar.direccion)
                cbo_lugar.addItem(texto, lugar.id)

        def cliente_completado(texto):
            clave = normalizar(texto)
            for cliente in clientes:
                if normalizar(cliente.razon_social) == clave:
                    idx = cbo_cliente.findData(cliente.id)
                    if idx >= 0:
                        cbo_cliente.setCurrentIndex(idx)
                    break
            cargar_lugares()

        cbo_cliente.currentIndexChanged.connect(cargar_lugares)
        completer.activated[str].connect(cliente_completado)

        # Precarga cliente actual o, si está pendiente, el nombre importado.
        if hoja.cliente_id:
            idx = cbo_cliente.findData(hoja.cliente_id)
            if idx >= 0:
                cbo_cliente.setCurrentIndex(idx)
        elif hoja.nombre_cliente:
            cbo_cliente.setEditText(hoja.nombre_cliente)
            cliente_completado(hoja.nombre_cliente)
        else:
            cargar_lugares()

        if hoja.lugar_entrega_id:
            idx = cbo_lugar.findData(hoja.lugar_entrega_id)
            if idx >= 0:
                cbo_lugar.setCurrentIndex(idx)

        if hoja.ruta_id:
            idx = cbo_ruta.findData(hoja.ruta_id)
            if idx >= 0:
                cbo_ruta.setCurrentIndex(idx)

        form.addRow("Cliente:", cbo_cliente)
        form.addRow("Lugar de entrega:", cbo_lugar)
        form.addRow("Ruta:", cbo_ruta)
        form.addRow("Producto:", txt_producto)
        form.addRow("Cantidad:", sp_cantidad)
        form.addRow("KG:", sp_kg)
        form.addRow("Bultos:", sp_bultos)
        form.addRow("Remito:", txt_remito)
        form.addRow("Observaciones:", txt_observaciones)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)

        if dialogo.exec_() != QDialog.Accepted:
            return

        cliente_id = resolver_cliente_id()
        lugar_id = int(cbo_lugar.currentData() or 0)
        ruta_id = int(cbo_ruta.currentData() or 0) or None

        cliente = Cliente.get_by_id(cliente_id) if cliente_id else None
        if lugar_id:
            lugar = LugarEntrega.get_or_none(
                (LugarEntrega.id == lugar_id) &
                (LugarEntrega.activo == True)
            )
            if lugar is None:
                showAlert("Sistema", "El lugar de entrega seleccionado ya no está disponible")
                return
            if cliente_id and lugar.cliente_id != cliente_id:
                showAlert("Sistema", "El lugar de entrega no corresponde al cliente seleccionado")
                return
            if ruta_id is None:
                ruta_id = lugar.ruta_reparto_id or (
                    cliente.ruta_reparto_id if cliente is not None else None
                )
        elif cliente is not None and ruta_id is None:
            ruta_id = cliente.ruta_reparto_id or None

        # Datos de cabecera/documento: Cliente + Lugar + Ruta se aplican a
        # TODA la factura. Los datos físicos/comerciales de la línea quedan
        # restringidos al renglón que el operador está editando.
        pedido_actual = self._convertir(hoja, referencias)
        ids_factura, documento_ids = self._ids_factura_completa([pedido_actual])
        if not ids_factura:
            ids_factura = [hoja_id]

        HojaDeRuta.update(
            cliente=cliente_id or None,
            nombre_cliente=(cliente.razon_social if cliente is not None else cbo_cliente.currentText().strip()),
            lugar_entrega=lugar_id or None,
            ruta=ruta_id,
        ).where(HojaDeRuta.id.in_(ids_factura)).execute()

        HojaDeRuta.update(
            producto=txt_producto.text().strip(),
            cantidad=sp_cantidad.value(),
            kg=sp_kg.value(),
            cantidad_bultos=sp_bultos.value(),
            observaciones=txt_observaciones.text().strip(),
        ).where(HojaDeRuta.id == hoja_id).execute()

        # Remito es dato del documento: actualizar todas las líneas vinculadas
        # al mismo DocumentoPedido a través del propio documento.
        if documento_ids:
            DocumentoPedido.update(
                numero_remito=txt_remito.text().strip()
            ).where(DocumentoPedido.id.in_(documento_ids)).execute()
        else:
            actualizar_remito_de_hoja(hoja_id, txt_remito.text().strip())

        showAlert(
            "Sistema",
            "Pedido actualizado. Cliente, lugar y ruta se aplicaron a toda la factura ({} línea(s)).".format(
                len(ids_factura)
            ),
        )
        self.cargar_pedidos()

    def _ids_factura_completa(self, pedidos):
        """Devuelve todas las hojas asociadas a las facturas seleccionadas.

        Prioriza el documento importado real, de modo que una selección parcial
        actualice toda la factura aunque algunas líneas no estén visibles en la
        bandeja por filtros. Para registros legacy sin DocumentoPedido conserva
        el fallback por número de factura/comprobante.
        """
        ids_seleccionados = [int(p.id) for p in pedidos if getattr(p, "id", 0)]
        if not ids_seleccionados:
            return [], []

        vinculos = list(
            DocumentoPedidoHojaRuta.select(
                DocumentoPedidoHojaRuta,
                DocumentoPedidoDetalle,
            )
            .join(DocumentoPedidoDetalle)
            .where(DocumentoPedidoHojaRuta.hoja_ruta.in_(ids_seleccionados))
        )
        documento_ids = sorted({
            int(v.detalle.documento_id)
            for v in vinculos
            if getattr(v.detalle, "documento_id", None)
        })

        if documento_ids:
            todos = (
                DocumentoPedidoHojaRuta.select(
                    DocumentoPedidoHojaRuta,
                    DocumentoPedidoDetalle,
                )
                .join(DocumentoPedidoDetalle)
                .where(DocumentoPedidoDetalle.documento.in_(documento_ids))
            )
            ids = sorted({int(v.hoja_ruta_id) for v in todos})
            if ids:
                return ids, documento_ids

        # Fallback legacy: expande con los datos ya cargados de la fecha actual.
        expandidos = expandir_seleccion_por_factura(self._pedidos, pedidos)
        return sorted({int(p.id) for p in expandidos}), []

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def asignar_cliente_lugar(self, *args, **kwargs):
        seleccionados = self.pedidos_seleccionados()
        if not seleccionados:
            showAlert("Sistema", "Seleccione al menos un pedido para asignar cliente y lugar de entrega")
            return

        ids, documento_ids = self._ids_factura_completa(seleccionados)
        if not ids:
            showAlert("Sistema", "No se pudieron identificar las líneas de la factura seleccionada")
            return

        pedidos = [p for p in self._pedidos if p.id in set(ids)]
        facturas = sorted({
            str(p.factura or p.comprobante or "").strip()
            for p in expandir_seleccion_por_factura(self._pedidos, seleccionados)
            if str(p.factura or p.comprobante or "").strip()
        })

        dialogo = QDialog(self.view)
        dialogo.setWindowTitle("Asignar cliente y lugar de entrega")
        dialogo.setMinimumWidth(560)
        layout = QVBoxLayout(dialogo)
        layout.addWidget(QLabel(
            "La asignación se aplicará a {} línea(s) de {} factura(s).".format(
                len(ids), len(facturas) or 1
            )
        ))

        fila_cliente = QHBoxLayout()
        fila_cliente.addWidget(QLabel("Cliente:"))
        cbo_cliente = QComboBox()
        cbo_cliente.setEditable(True)
        cbo_cliente.setInsertPolicy(QComboBox.NoInsert)
        cbo_cliente.setMinimumWidth(380)
        cbo_cliente.lineEdit().setPlaceholderText("Escriba parte del nombre del cliente")
        fila_cliente.addWidget(cbo_cliente, 1)
        layout.addLayout(fila_cliente)

        fila_lugar = QHBoxLayout()
        fila_lugar.addWidget(QLabel("Lugar de entrega:"))
        cbo_lugar = QComboBox()
        cbo_lugar.setMinimumWidth(380)
        fila_lugar.addWidget(cbo_lugar, 1)
        layout.addLayout(fila_lugar)

        btn_gestionar = QPushButton("Crear / editar clientes y lugares")
        layout.addWidget(btn_gestionar)

        clientes = list(
            Cliente.select()
            .where(Cliente.activo == True)
            .order_by(Cliente.razon_social)
        )
        cbo_cliente.addItem("", 0)
        for cliente in clientes:
            cbo_cliente.addItem(cliente.razon_social, cliente.id)

        completer = QCompleter(cbo_cliente.model(), cbo_cliente)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        cbo_cliente.setCompleter(completer)

        def normalizar_nombre_cliente(valor):
            texto = str(valor or "").strip().upper()
            texto = "".join(
                ch for ch in unicodedata.normalize("NFD", texto)
                if unicodedata.category(ch) != "Mn"
            )
            texto = re.sub(r"[^A-Z0-9]+", " ", texto)
            return " ".join(texto.split())

        def resolver_cliente_id():
            data = int(cbo_cliente.currentData() or 0)
            texto = str(cbo_cliente.currentText() or "").strip()
            if data and texto:
                return data
            if not texto:
                return 0
            texto_normalizado = normalizar_nombre_cliente(texto)
            for cliente in clientes:
                if normalizar_nombre_cliente(cliente.razon_social) == texto_normalizado:
                    idx = cbo_cliente.findData(cliente.id)
                    if idx >= 0:
                        cbo_cliente.setCurrentIndex(idx)
                    return int(cliente.id)
            return 0

        def cargar_lugares(*_):
            cbo_lugar.clear()
            cliente_id = resolver_cliente_id()
            if not cliente_id:
                cbo_lugar.addItem("Seleccione un cliente", 0)
                return

            lugares = list(LugarEntrega.activos_cliente(cliente_id))
            if not lugares:
                cbo_lugar.addItem("Sin lugar de entrega — puede asignarlo después", 0)
                return

            cbo_lugar.addItem("Dejar lugar pendiente", 0)
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

        def on_cliente_completado(texto):
            texto = str(texto or "").strip().lower()
            for cliente in clientes:
                if str(cliente.razon_social or "").strip().lower() == texto:
                    idx = cbo_cliente.findData(cliente.id)
                    if idx >= 0:
                        cbo_cliente.setCurrentIndex(idx)
                    break
            cargar_lugares()

        cbo_cliente.currentIndexChanged.connect(cargar_lugares)
        cbo_cliente.lineEdit().editingFinished.connect(cargar_lugares)
        completer.activated[str].connect(on_cliente_completado)

        # Precarga SIEMPRE el cliente visible de la factura. El nombre importado
        # es contexto útil aunque todavía no tenga FK resuelto.
        nombres_factura = {
            str(getattr(p, "cliente", "") or "").strip()
            for p in pedidos
            if str(getattr(p, "cliente", "") or "").strip()
        }
        if len(nombres_factura) == 1:
            nombre_actual = next(iter(nombres_factura))
        elif seleccionados:
            nombre_actual = str(
                getattr(seleccionados[0], "cliente", "") or ""
            ).strip()
        else:
            nombre_actual = ""

        cliente_ids = {p.cliente_id for p in pedidos if p.cliente_id}
        cliente_id_actual = 0
        if len(cliente_ids) == 1:
            cliente_id_actual = next(iter(cliente_ids))
        elif seleccionados:
            cliente_id_actual = int(getattr(seleccionados[0], "cliente_id", 0) or 0)

        if not cliente_id_actual and nombre_actual:
            nombre_normalizado = normalizar_nombre_cliente(nombre_actual)
            cliente_nombre = next(
                (
                    cli for cli in clientes
                    if normalizar_nombre_cliente(cli.razon_social)
                    == nombre_normalizado
                ),
                None,
            )
            if cliente_nombre is not None:
                cliente_id_actual = int(cliente_nombre.id)

        if cliente_id_actual:
            idx = cbo_cliente.findData(cliente_id_actual)
            if idx >= 0:
                cbo_cliente.setCurrentIndex(idx)
            elif nombre_actual:
                cbo_cliente.setEditText(nombre_actual)
                cargar_lugares()
            else:
                cargar_lugares()
        else:
            if nombre_actual:
                cbo_cliente.setEditText(nombre_actual)
            cargar_lugares()

        # Si toda la factura ya tiene un lugar común, también lo dejamos
        # seleccionado después de cargar los lugares del cliente.
        lugares_actuales = {
            p.lugar_entrega_id for p in pedidos if p.lugar_entrega_id
        }
        if len(lugares_actuales) == 1:
            idx_lugar = cbo_lugar.findData(next(iter(lugares_actuales)))
            if idx_lugar >= 0:
                cbo_lugar.setCurrentIndex(idx_lugar)

        def recargar_clientes(*_):
            """Refresca clientes/lugares al volver del ABM sin perder la selección."""
            cliente_id_previo = int(cbo_cliente.currentData() or 0)
            texto_previo = str(cbo_cliente.currentText() or "").strip()

            cbo_cliente.blockSignals(True)
            try:
                clientes[:] = list(
                    Cliente.select()
                    .where(Cliente.activo == True)
                    .order_by(Cliente.razon_social)
                )
                cbo_cliente.clear()
                cbo_cliente.addItem("", 0)
                for cliente in clientes:
                    cbo_cliente.addItem(cliente.razon_social, cliente.id)

                idx = cbo_cliente.findData(cliente_id_previo) if cliente_id_previo else -1
                if idx >= 0:
                    cbo_cliente.setCurrentIndex(idx)
                elif texto_previo:
                    cbo_cliente.setEditText(texto_previo)
            finally:
                cbo_cliente.blockSignals(False)
            cargar_lugares()

        def gestionar_clientes():
            from controladores.ABMClientes import ABMClientesController

            gestor_actual = getattr(self, "gestor_clientes", None)
            if gestor_actual is not None:
                try:
                    if gestor_actual.view.isVisible():
                        gestor_actual.view.raise_()
                        gestor_actual.view.activateWindow()
                        return
                except RuntimeError:
                    self.gestor_clientes = None

            gestor = ABMClientesController()
            self.gestor_clientes = gestor

            # El diálogo de asignación está ejecutándose con exec_() y es modal.
            # Hacemos al ABM una ventana hija de ese diálogo para que Qt no lo
            # bloquee ni lo mande detrás de la ventana modal.
            gestor.view.setParent(dialogo, Qt.Window)
            gestor.view.setAttribute(Qt.WA_DeleteOnClose, True)

            def al_cerrar_abm(*_):
                self.gestor_clientes = None
                recargar_clientes()
                dialogo.raise_()
                dialogo.activateWindow()

            gestor.view.destroyed.connect(al_cerrar_abm)
            gestor.run()
            gestor.view.raise_()
            gestor.view.activateWindow()

        btn_gestionar.clicked.connect(gestionar_clientes)
        botones = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)

        if dialogo.exec_() != QDialog.Accepted:
            return

        cliente_id = resolver_cliente_id()
        if not cliente_id:
            showAlert(
                "Sistema",
                "Seleccione un cliente válido de la lista. Puede escribir parte del nombre para buscarlo.",
            )
            return

        lugar_id = int(cbo_lugar.currentData() or 0)
        cliente = Cliente.get_by_id(cliente_id)
        lugar = None

        if lugar_id:
            lugar = LugarEntrega.get_or_none(
                (LugarEntrega.id == lugar_id) &
                (LugarEntrega.cliente == cliente_id) &
                (LugarEntrega.activo == True)
            )
            if lugar is None:
                showAlert("Sistema", "El lugar de entrega seleccionado ya no está disponible")
                return

        ruta_id = (
            (lugar.ruta_reparto_id if lugar is not None else None)
            or cliente.ruta_reparto_id
            or None
        )

        # Cliente obligatorio; lugar puede quedar pendiente. La validación de
        # cierre/despacho seguirá bloqueando mientras falte el lugar.
        actualizados = (
            HojaDeRuta.update(
                cliente=cliente_id,
                lugar_entrega=(lugar.id if lugar is not None else None),
                ruta=ruta_id,
                nombre_cliente=cliente.razon_social,
            )
            .where(HojaDeRuta.id.in_(ids))
            .execute()
        )

        # Verificación real contra DB. No dependemos del rowcount de SQLite/MySQL,
        # porque puede variar cuando algunos valores ya coincidían.
        verificados = (
            HojaDeRuta.select()
            .where(
                (HojaDeRuta.id.in_(ids)) &
                (HojaDeRuta.cliente == cliente_id)
            )
            .count()
        )
        if verificados != len(ids):
            showAlert(
                "Sistema",
                "El cliente no quedó grabado correctamente en todas las líneas de la factura.",
            )
            return

        if documento_ids:
            DocumentoPedido.update(cliente=cliente_id).where(
                DocumentoPedido.id.in_(documento_ids)
            ).execute()

        if lugar is None:
            mensaje = (
                "Cliente asignado a {} línea(s) de la factura. "
                "El lugar de entrega queda pendiente."
            ).format(len(ids))
        else:
            mensaje = (
                "Cliente y lugar de entrega asignados a {} línea(s) de la factura."
            ).format(len(ids))

        showAlert("Sistema", mensaje)
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

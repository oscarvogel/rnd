# coding=utf-8
from datetime import date
import re
import unicodedata

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import QAbstractItemView, QComboBox, QCompleter, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout
from peewee import JOIN

from modelos.Clientes import Cliente, LugarEntrega, RutaReparto
from modelos.HojaRuta import HojaDeRuta
from modelos.Documentos import DocumentoPedido, DocumentoPedidoDetalle, DocumentoPedidoHojaRuta, actualizar_remito_de_hoja, referencias_por_hojas
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from utiles.bandeja_pedidos import FacturaBandeja, PedidoBandeja, agrupar_pedidos_por_factura, expandir_seleccion_por_factura, totales_facturas, validar_reasignacion
from vistas.BandejaPedidos import BandejaPedidosView


class BandejaPedidosController(ControladorBase):
    def __init__(self, fecha_inicial=None):
        super().__init__()
        self.view = BandejaPedidosView()
        self._pedidos = []
        self._facturas = []
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
        self.view.btn_editar_factura.clicked.connect(self.editar_factura_actual)
        self.view.btn_productos.clicked.connect(self.editar_productos_actual)
        self.view.tabla.doubleClicked.connect(self.editar_factura_actual)
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
        self._pedidos = pedidos
        facturas = agrupar_pedidos_por_factura(pedidos)
        if self.view.solo_pendientes.isChecked():
            facturas = [
                f for f in facturas
                if f.estado(self.empleado_generico, self.camion_generico) != "organizado"
            ]
        self._facturas = facturas
        self.view.cargar_facturas(facturas, self.empleado_generico, self.camion_generico)
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
            documento_id=int(referencia.get("documento_id") or 0),
        )

    def facturas_seleccionadas(self):
        claves = set(self.view.claves_seleccionadas())
        return [f for f in self._facturas if f.clave in claves]

    def factura_actual(self):
        clave = self.view.clave_fila_actual()
        return next((f for f in self._facturas if f.clave == clave), None)

    def pedidos_de_factura(self, factura):
        ids = set(getattr(factura, "hoja_ids", ()) or ())
        return [p for p in self._pedidos if p.id in ids]

    def actualizar_totales(self):
        totales = totales_facturas(self.facturas_seleccionadas())
        self.view.set_totales(totales["facturas"], totales["kg"], totales["bultos"])

    def _normalizar_nombre(self, valor):
        texto = str(valor or "").strip().upper()
        texto = "".join(
            ch for ch in unicodedata.normalize("NFD", texto)
            if unicodedata.category(ch) != "Mn"
        )
        texto = re.sub(r"[^A-Z0-9]+", " ", texto)
        return " ".join(texto.split())

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def editar_factura_actual(self, *args, **kwargs):
        factura = self.factura_actual()
        if factura is None:
            showAlert("Sistema", "Seleccione una factura para editar")
            return

        ids = list(factura.hoja_ids)
        hojas = list(HojaDeRuta.select().where(HojaDeRuta.id.in_(ids)).order_by(HojaDeRuta.id))
        if not hojas:
            showAlert("Sistema", "La factura no tiene líneas operativas")
            return

        primera = hojas[0]
        dialogo = QDialog(self.view)
        dialogo.setWindowTitle("Editar factura {}".format(factura.factura))
        dialogo.setMinimumWidth(640)
        layout = QVBoxLayout(dialogo)
        form = QFormLayout()
        layout.addLayout(form)

        clientes = list(Cliente.select().where(Cliente.activo == True).order_by(Cliente.razon_social))
        cbo_cliente = QComboBox()
        cbo_cliente.setEditable(True)
        cbo_cliente.setInsertPolicy(QComboBox.NoInsert)
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

        txt_remito = QLineEdit(factura.remito or "")
        txt_observaciones = QLineEdit(factura.observaciones or "")

        def resolver_cliente_id():
            data = int(cbo_cliente.currentData() or 0)
            texto = str(cbo_cliente.currentText() or "").strip()
            if data and texto:
                return data
            clave = self._normalizar_nombre(texto)
            for cliente in clientes:
                if self._normalizar_nombre(cliente.razon_social) == clave:
                    idx = cbo_cliente.findData(cliente.id)
                    if idx >= 0:
                        cbo_cliente.setCurrentIndex(idx)
                    return int(cliente.id)
            return 0

        def cargar_lugares(*_):
            actual = int(cbo_lugar.currentData() or 0)
            cbo_lugar.clear()
            cliente_id = resolver_cliente_id()
            cbo_lugar.addItem("Sin asignar", 0)
            if not cliente_id:
                return
            lugares = list(LugarEntrega.activos_cliente(cliente_id))
            for lugar in lugares:
                texto = lugar.nombre
                if lugar.direccion:
                    texto += " — {}".format(lugar.direccion)
                cbo_lugar.addItem(texto, lugar.id)
            if actual:
                idx = cbo_lugar.findData(actual)
                if idx >= 0:
                    cbo_lugar.setCurrentIndex(idx)

        def cliente_completado(texto):
            clave = self._normalizar_nombre(texto)
            for cliente in clientes:
                if self._normalizar_nombre(cliente.razon_social) == clave:
                    idx = cbo_cliente.findData(cliente.id)
                    if idx >= 0:
                        cbo_cliente.setCurrentIndex(idx)
                    break
            cargar_lugares()

        cbo_cliente.currentIndexChanged.connect(cargar_lugares)
        completer.activated[str].connect(cliente_completado)

        if factura.cliente_id:
            idx = cbo_cliente.findData(factura.cliente_id)
            if idx >= 0:
                cbo_cliente.setCurrentIndex(idx)
        elif factura.cliente:
            cbo_cliente.setEditText(factura.cliente)
            cliente_completado(factura.cliente)
        else:
            cargar_lugares()

        if factura.lugar_entrega_id:
            idx = cbo_lugar.findData(factura.lugar_entrega_id)
            if idx >= 0:
                cbo_lugar.setCurrentIndex(idx)

        if factura.ruta_id:
            idx = cbo_ruta.findData(factura.ruta_id)
            if idx >= 0:
                cbo_ruta.setCurrentIndex(idx)

        form.addRow("Factura:", QLabel(factura.factura))
        form.addRow("Cliente:", cbo_cliente)
        form.addRow("Lugar de entrega:", cbo_lugar)
        form.addRow("Ruta:", cbo_ruta)
        form.addRow("Remito:", txt_remito)
        form.addRow("Observación general:", txt_observaciones)
        form.addRow("Productos:", QLabel(str(factura.productos)))
        form.addRow("KG total:", QLabel(str(factura.kg)))
        form.addRow("Bultos total:", QLabel(str(factura.bultos)))

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)
        if dialogo.exec_() != QDialog.Accepted:
            return

        cliente_id = resolver_cliente_id()
        if not cliente_id:
            showAlert("Sistema", "Seleccione un cliente válido")
            return
        cliente = Cliente.get_by_id(cliente_id)

        lugar_id = int(cbo_lugar.currentData() or 0)
        lugar = None
        if lugar_id:
            lugar = LugarEntrega.get_or_none(
                (LugarEntrega.id == lugar_id) &
                (LugarEntrega.cliente == cliente_id) &
                (LugarEntrega.activo == True)
            )
            if lugar is None:
                showAlert("Sistema", "El lugar seleccionado no corresponde al cliente")
                return

        ruta_id = int(cbo_ruta.currentData() or 0) or None
        if ruta_id is None:
            ruta_id = (
                (lugar.ruta_reparto_id if lugar is not None else None)
                or cliente.ruta_reparto_id
                or None
            )

        HojaDeRuta.update(
            cliente=cliente_id,
            nombre_cliente=cliente.razon_social,
            lugar_entrega=(lugar.id if lugar else None),
            ruta=ruta_id,
        ).where(HojaDeRuta.id.in_(ids)).execute()

        if factura.documento_id:
            DocumentoPedido.update(
                cliente=cliente_id,
                numero_remito=txt_remito.text().strip(),
                observaciones=txt_observaciones.text().strip(),
            ).where(DocumentoPedido.id == factura.documento_id).execute()
        else:
            for hoja_id in ids:
                actualizar_remito_de_hoja(hoja_id, txt_remito.text().strip())

        showAlert("Sistema", "Factura actualizada correctamente")
        self.cargar_pedidos()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def editar_productos_actual(self, *args, **kwargs):
        factura = self.factura_actual()
        if factura is None:
            showAlert("Sistema", "Seleccione una factura para revisar sus productos")
            return

        hojas = list(
            HojaDeRuta.select()
            .where(HojaDeRuta.id.in_(list(factura.hoja_ids)))
            .order_by(HojaDeRuta.id)
        )
        if not hojas:
            return

        dialogo = QDialog(self.view)
        dialogo.setWindowTitle("Productos de factura {}".format(factura.factura))
        dialogo.resize(980, 560)
        layout = QVBoxLayout(dialogo)
        layout.addWidget(QLabel(
            "{} — {} — {} línea(s)".format(
                factura.cliente or "Sin cliente",
                factura.lugar_entrega or "Sin lugar",
                len(hojas),
            )
        ))

        tabla = QTableWidget(len(hojas), 6)
        tabla.setHorizontalHeaderLabels(
            ["Producto", "Cantidad", "KG", "Bultos", "Observaciones", "ID"]
        )
        tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabla.setColumnHidden(5, True)

        for row, hoja in enumerate(hojas):
            tabla.setItem(row, 0, QTableWidgetItem(str(hoja.producto or "")))
            tabla.setItem(row, 1, QTableWidgetItem(str(hoja.cantidad or 0)))
            tabla.setItem(row, 2, QTableWidgetItem(str(hoja.kg or 0)))
            tabla.setItem(row, 3, QTableWidgetItem(str(hoja.cantidad_bultos or 0)))
            tabla.setItem(row, 4, QTableWidgetItem(str(hoja.observaciones or "")))
            tabla.setItem(row, 5, QTableWidgetItem(str(hoja.id)))

        tabla.resizeColumnsToContents()
        layout.addWidget(tabla)

        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)
        if dialogo.exec_() != QDialog.Accepted:
            return

        def numero(texto, campo):
            try:
                return float(str(texto or "0").replace(",", "."))
            except ValueError:
                raise ValueError("{} debe ser numérico".format(campo))

        try:
            for row in range(tabla.rowCount()):
                hoja_id = int(tabla.item(row, 5).text())
                producto = tabla.item(row, 0).text().strip()
                cantidad = numero(tabla.item(row, 1).text(), "Cantidad")
                kg = numero(tabla.item(row, 2).text(), "KG")
                bultos = numero(tabla.item(row, 3).text(), "Bultos")
                observaciones = tabla.item(row, 4).text().strip()
                if not producto:
                    raise ValueError("Producto no puede quedar vacío")
                HojaDeRuta.update(
                    producto=producto,
                    cantidad=cantidad,
                    kg=kg,
                    cantidad_bultos=bultos,
                    observaciones=observaciones,
                ).where(HojaDeRuta.id == hoja_id).execute()
        except ValueError as exc:
            showAlert("Sistema", str(exc))
            return

        showAlert("Sistema", "Productos actualizados correctamente")
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
    def organizar_seleccion(self, *args, **kwargs):
        facturas = self.facturas_seleccionadas()
        ruta_id = self.view.ruta_destino()
        if not facturas:
            showAlert("Sistema", "Seleccione al menos una factura")
            return
        if not ruta_id:
            showAlert("Sistema", "Seleccione una ruta de reparto")
            return

        try:
            ruta = RutaReparto.get_by_id(ruta_id)
            ruta_nombre = ruta.descripcion
        except Exception:
            ruta_nombre = "ruta #{}".format(ruta_id)

        ids = sorted({
            hoja_id
            for factura in facturas
            for hoja_id in factura.hoja_ids
        })
        HojaDeRuta.update(ruta=ruta_id).where(
            (HojaDeRuta.id.in_(ids)) &
            (HojaDeRuta.fecha == self.fecha_actual())
        ).execute()

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
            "{} factura(s) organizadas en {}. El siguiente paso es asignar chofer y camión.".format(
                len(facturas), ruta_nombre
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

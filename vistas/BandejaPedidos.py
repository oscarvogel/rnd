# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class BandejaPedidosView(QWidget):
    COLUMNAS = ["Sel.", "Estado", "Cliente", "Ruta", "Comprobante", "Producto", "Cantidad", "KG", "Bultos", "Observaciones"]
    COLUMNA_COMPROBANTE = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pedidos para organizar")
        self.resize(1180, 680)
        self._build_ui()
        # Esta pantalla necesita ancho para revisar pedidos/productos y normalmente
        # se usa como paso principal del armado de hojas de ruta.
        self.setWindowState(self.windowState() | Qt.WindowMaximized)

    def _build_ui(self):
        raiz = QVBoxLayout(self)
        titulo = QLabel("Pedidos para organizar")
        titulo.setObjectName("bandejaPedidosTitulo")
        raiz.addWidget(titulo)
        raiz.addWidget(QLabel("Revise los pedidos importados, seleccione los que desea agrupar y defina su ruta antes de asignar chofer y camión."))

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Fecha:"))
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("dd/MM/yyyy")
        filtros.addWidget(self.fecha)
        self.solo_pendientes = QCheckBox("Priorizar pendientes")
        self.solo_pendientes.setChecked(True)
        filtros.addWidget(self.solo_pendientes)
        self.btn_actualizar = QPushButton("Actualizar")
        filtros.addWidget(self.btn_actualizar)

        filtros.addWidget(QLabel("Factura:"))
        self.txt_comprobante = QLineEdit()
        self.txt_comprobante.setPlaceholderText("Buscar por comprobante / factura")
        self.txt_comprobante.setClearButtonEnabled(True)
        self.txt_comprobante.setMinimumWidth(230)
        self.txt_comprobante.textChanged.connect(self.aplicar_filtro_comprobante)
        filtros.addWidget(self.txt_comprobante)

        self.btn_seleccionar_factura = QPushButton("Seleccionar factura")
        self.btn_seleccionar_factura.setToolTip(
            "Selecciona todos los renglones de la factura mostrada por el filtro"
        )
        self.btn_seleccionar_factura.setEnabled(False)
        self.btn_seleccionar_factura.clicked.connect(self.seleccionar_factura_visible)
        filtros.addWidget(self.btn_seleccionar_factura)

        self.btn_seleccionar_todo = QPushButton("Seleccionar todo")
        self.btn_seleccionar_todo.setToolTip("Seleccionar o deseleccionar todos los pedidos visibles")
        self.btn_seleccionar_todo.clicked.connect(self.alternar_seleccion_todos)
        filtros.addWidget(self.btn_seleccionar_todo)
        filtros.addStretch(1)
        raiz.addLayout(filtros)

        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.itemChanged.connect(self._emitir_totales)
        raiz.addWidget(self.tabla)

        pie = QHBoxLayout()
        self.lbl_totales = QLabel("Seleccionados: 0 · KG: 0 · Bultos: 0")
        pie.addWidget(self.lbl_totales)
        pie.addStretch(1)
        pie.addWidget(QLabel("Ruta destino:"))
        self.cbo_ruta = QComboBox()
        self.cbo_ruta.setMinimumWidth(220)
        pie.addWidget(self.cbo_ruta)
        self.btn_organizar = QPushButton("Organizar seleccionados")
        self.btn_organizar.setProperty("role", "primary")
        pie.addWidget(self.btn_organizar)
        self.btn_siguiente = QPushButton("Asignar chofer y camión")
        self.btn_siguiente.setEnabled(False)
        pie.addWidget(self.btn_siguiente)
        raiz.addLayout(pie)

    def cargar_rutas(self, rutas):
        self.cbo_ruta.clear()
        self.cbo_ruta.addItem("Seleccione una ruta", 0)
        for ruta_id, descripcion in rutas:
            self.cbo_ruta.addItem(descripcion, ruta_id)

    def cargar_pedidos(self, pedidos, empleado_generico, camion_generico):
        self.tabla.blockSignals(True)
        self.tabla.setRowCount(0)
        for pedido in pedidos:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            chk.setCheckState(Qt.Unchecked)
            chk.setData(Qt.UserRole, pedido.id)
            self.tabla.setItem(row, 0, chk)
            valores = [
                pedido.estado(empleado_generico, camion_generico), pedido.cliente,
                pedido.ruta, pedido.comprobante, pedido.producto, str(pedido.cantidad),
                str(pedido.kg), str(pedido.bultos), pedido.observaciones or "",
            ]
            for col, valor in enumerate(valores, start=1):
                self.tabla.setItem(row, col, QTableWidgetItem(str(valor)))
        self.tabla.blockSignals(False)
        self.tabla.resizeColumnsToContents()
        self.aplicar_filtro_comprobante()
        self._actualizar_texto_seleccionar_todo()
        self._emitir_totales()

    def _filas_visibles(self):
        return [
            row for row in range(self.tabla.rowCount())
            if not self.tabla.isRowHidden(row)
        ]

    def aplicar_filtro_comprobante(self, *args):
        texto = self.txt_comprobante.text().strip().casefold()
        coincidencias = 0

        for row in range(self.tabla.rowCount()):
            item = self.tabla.item(row, self.COLUMNA_COMPROBANTE)
            comprobante = item.text().strip().casefold() if item else ""
            visible = not texto or texto in comprobante
            self.tabla.setRowHidden(row, not visible)
            if visible:
                coincidencias += 1

        self.btn_seleccionar_factura.setEnabled(bool(texto) and coincidencias > 0)
        self._actualizar_texto_seleccionar_todo()

    def seleccionar_factura_visible(self):
        if not self.txt_comprobante.text().strip():
            return

        filas = self._filas_visibles()
        if not filas:
            return

        self.tabla.blockSignals(True)
        try:
            for row in filas:
                item = self.tabla.item(row, 0)
                if item:
                    item.setCheckState(Qt.Checked)
        finally:
            self.tabla.blockSignals(False)

        self._actualizar_texto_seleccionar_todo()
        self._emitir_totales()

    def alternar_seleccion_todos(self):
        filas = self._filas_visibles()
        if not filas:
            return

        seleccionados_visibles = sum(
            1 for row in filas
            if self.tabla.item(row, 0)
            and self.tabla.item(row, 0).checkState() == Qt.Checked
        )
        nuevo_estado = Qt.Unchecked if seleccionados_visibles == len(filas) else Qt.Checked

        self.tabla.blockSignals(True)
        try:
            for row in filas:
                item = self.tabla.item(row, 0)
                if item:
                    item.setCheckState(nuevo_estado)
        finally:
            self.tabla.blockSignals(False)

        self._actualizar_texto_seleccionar_todo()
        self._emitir_totales()

    def ids_seleccionados(self):
        ids = []
        for row in range(self.tabla.rowCount()):
            item = self.tabla.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                ids.append(int(item.data(Qt.UserRole)))
        return ids

    def ruta_destino(self):
        return int(self.cbo_ruta.currentData() or 0)

    def set_totales(self, cantidad, kg, bultos):
        self.lbl_totales.setText("Seleccionados: {} · KG: {} · Bultos: {}".format(cantidad, kg, bultos))
        self._actualizar_texto_seleccionar_todo()

    def _actualizar_texto_seleccionar_todo(self):
        filas = self._filas_visibles()
        seleccionados = sum(
            1 for row in filas
            if self.tabla.item(row, 0)
            and self.tabla.item(row, 0).checkState() == Qt.Checked
        )
        if filas and seleccionados == len(filas):
            self.btn_seleccionar_todo.setText("Deseleccionar todo")
        else:
            self.btn_seleccionar_todo.setText("Seleccionar todo")

    def _emitir_totales(self, *args):
        self._actualizar_texto_seleccionar_todo()
        # El controlador conecta esta referencia para recalcular con objetos reales.
        callback = getattr(self, "on_selection_changed", None)
        if callback:
            callback()

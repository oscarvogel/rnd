# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class BandejaPedidosView(QWidget):
    COLUMNAS = ["Sel.", "Estado", "Cliente", "Ruta", "Comprobante", "Producto", "Cantidad", "KG", "Bultos", "Observaciones"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pedidos para organizar")
        self.resize(1180, 680)
        self._build_ui()

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

    def _emitir_totales(self, *args):
        # El controlador conecta esta referencia para recalcular con objetos reales.
        callback = getattr(self, "on_selection_changed", None)
        if callback:
            callback()

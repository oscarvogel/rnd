# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)


class PendientesEntregaView(QWidget):
    COLUMNAS = [
        "Sel.", "Factura", "Cliente", "Lugar", "Producto",
        "Cantidad factura", "Entregado acumulado", "Pendiente",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pendientes de entrega")
        self.resize(1180, 680)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(18, 16, 18, 16)
        raiz.setSpacing(10)

        titulo = QLabel("Pendientes de entrega")
        titulo.setObjectName("pendientesEntregaTitulo")
        raiz.addWidget(titulo)

        ayuda = QLabel(
            "Muestra mercadería facturada que todavía no fue entregada completamente. "
            "Estos saldos quedan disponibles para el próximo reparto."
        )
        ayuda.setWordWrap(True)
        raiz.addWidget(ayuda)

        barra = QHBoxLayout()
        barra.setSpacing(8)
        self.lbl_resumen = QLabel("Calculando pendientes…")
        barra.addWidget(self.lbl_resumen)
        barra.addStretch(1)
        self.btn_agregar_reparto = QPushButton("Agregar al reparto de hoy")
        self.btn_agregar_reparto.setProperty("role", "primary")
        barra.addWidget(self.btn_agregar_reparto)
        self.btn_actualizar = QPushButton("Actualizar")
        self.btn_actualizar.setProperty("role", "secondary")
        barra.addWidget(self.btn_actualizar)
        raiz.addLayout(barra)

        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setObjectName("dataGrid")
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSortingEnabled(True)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setDefaultSectionSize(36)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        raiz.addWidget(self.tabla)

    def cargar(self, filas):
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(0)
        total_pendiente = 0
        facturas = set()
        for fila in filas:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)

            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            chk.setCheckState(Qt.Unchecked)
            chk.setData(Qt.UserRole, int(fila["detalle_id"]))
            self.tabla.setItem(row, 0, chk)

            valores = [
                fila["factura"],
                fila["cliente"],
                fila["lugar"],
                fila["producto"],
                fila["cantidad_original"],
                fila["entregado"],
                fila["pendiente"],
            ]
            for col, valor in enumerate(valores, start=1):
                self.tabla.setItem(row, col, QTableWidgetItem(str(valor)))
            total_pendiente += float(fila["pendiente"] or 0)
            facturas.add(fila["factura"])
        self.tabla.setSortingEnabled(True)
        self.tabla.resizeColumnsToContents()
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.lbl_resumen.setText(
            "{} factura(s) · {} línea(s) · {} unidad(es) pendientes".format(
                len(facturas), len(filas), round(total_pendiente, 2)
            )
        )

    def detalles_seleccionados(self):
        ids = []
        for row in range(self.tabla.rowCount()):
            item = self.tabla.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                ids.append(int(item.data(Qt.UserRole)))
        return ids

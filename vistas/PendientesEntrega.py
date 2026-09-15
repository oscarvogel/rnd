# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)


class PendientesEntregaView(QWidget):
    COLUMNAS = [
        "Factura", "Cliente", "Lugar", "Producto",
        "Cantidad factura", "Entregado acumulado", "Pendiente",
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pendientes de entrega")
        self.resize(1180, 680)
        self.setWindowState(self.windowState() | Qt.WindowMaximized)
        raiz = QVBoxLayout(self)

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
        self.lbl_resumen = QLabel("Calculando pendientes…")
        barra.addWidget(self.lbl_resumen)
        barra.addStretch(1)
        self.btn_actualizar = QPushButton("Actualizar")
        barra.addWidget(self.btn_actualizar)
        raiz.addLayout(barra)

        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        raiz.addWidget(self.tabla)

    def cargar(self, filas):
        self.tabla.setRowCount(0)
        total_pendiente = 0
        facturas = set()
        for fila in filas:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            valores = [
                fila["factura"],
                fila["cliente"],
                fila["lugar"],
                fila["producto"],
                fila["cantidad_original"],
                fila["entregado"],
                fila["pendiente"],
            ]
            for col, valor in enumerate(valores):
                self.tabla.setItem(row, col, QTableWidgetItem(str(valor)))
            total_pendiente += float(fila["pendiente"] or 0)
            facturas.add(fila["factura"])
        self.tabla.resizeColumnsToContents()
        self.tabla.horizontalHeader().setStretchLastSection(True)
        self.lbl_resumen.setText(
            "{} factura(s) · {} línea(s) · {} unidad(es) pendientes".format(
                len(facturas), len(filas), round(total_pendiente, 2)
            )
        )

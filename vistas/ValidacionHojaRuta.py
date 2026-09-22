# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


class ValidacionHojaRutaView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Validar hoja de ruta")
        self.resize(820, 620)
        self._build_ui()

    def _build_ui(self):
        raiz = QVBoxLayout(self)
        titulo = QLabel("Validar hoja de ruta")
        titulo.setObjectName("validacionHojaTitulo")
        raiz.addWidget(titulo)
        raiz.addWidget(QLabel("Revise el checklist antes de dejar la hoja lista para despacho."))

        filtros = QHBoxLayout()
        filtros.addWidget(QLabel("Fecha:"))
        self.fecha = QDateEdit()
        self.fecha.setCalendarPopup(True)
        self.fecha.setDisplayFormat("dd/MM/yyyy")
        filtros.addWidget(self.fecha)
        filtros.addWidget(QLabel("Ruta:"))
        self.cbo_ruta = QComboBox()
        self.cbo_ruta.setMinimumWidth(260)
        filtros.addWidget(self.cbo_ruta)
        self.btn_cargar = QPushButton("Revisar")
        filtros.addWidget(self.btn_cargar)
        filtros.addStretch(1)
        raiz.addLayout(filtros)

        resumen = QGridLayout()
        self.lbl_estado = QLabel("Estado: EN_PREPARACION")
        self.lbl_pedidos = QLabel("Pedidos: 0")
        self.lbl_kg = QLabel("KG: 0")
        self.lbl_bultos = QLabel("Bultos: 0")
        resumen.addWidget(self.lbl_estado, 0, 0)
        resumen.addWidget(self.lbl_pedidos, 0, 1)
        resumen.addWidget(self.lbl_kg, 1, 0)
        resumen.addWidget(self.lbl_bultos, 1, 1)
        raiz.addLayout(resumen)

        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["Estado", "Requisito", "Detalle"])
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setToolTip(
            "Doble clic en un requisito PENDIENTE para ir a corregirlo."
        )
        raiz.addWidget(self.tabla)

        self.lbl_ayuda = QLabel(
            "Doble clic en un requisito PENDIENTE para corregirlo."
        )
        self.lbl_ayuda.setObjectName("validacionHojaAyuda")
        raiz.addWidget(self.lbl_ayuda)

        self.lbl_mensaje = QLabel("")
        self.lbl_mensaje.setWordWrap(True)
        raiz.addWidget(self.lbl_mensaje)

        acciones = QHBoxLayout()
        self.btn_asignar = QPushButton("Resolver chofer / camión")
        acciones.addWidget(self.btn_asignar)
        acciones.addStretch(1)
        self.btn_lista = QPushButton("Marcar LISTA")
        self.btn_lista.setProperty("role", "primary")
        acciones.addWidget(self.btn_lista)
        self.btn_hoja = QPushButton("Ver / imprimir hoja")
        self.btn_hoja.setEnabled(False)
        acciones.addWidget(self.btn_hoja)
        self.btn_despachar = QPushButton("Marcar DESPACHADA")
        acciones.addWidget(self.btn_despachar)
        self.btn_cerrar = QPushButton("Cerrar")
        acciones.addWidget(self.btn_cerrar)
        raiz.addLayout(acciones)

    def cargar_rutas(self, rutas, ruta_inicial=0):
        self.cbo_ruta.clear()
        self.cbo_ruta.addItem("Seleccione una ruta", 0)
        indice = 0
        for ruta_id, descripcion in rutas:
            self.cbo_ruta.addItem(descripcion, ruta_id)
            if int(ruta_id) == int(ruta_inicial or 0):
                indice = self.cbo_ruta.count() - 1
        self.cbo_ruta.setCurrentIndex(indice)

    def ruta_id(self):
        return int(self.cbo_ruta.currentData() or 0)

    def codigo_fila(self, row):
        if row < 0 or row >= self.tabla.rowCount():
            return ""
        item = self.tabla.item(row, 0)
        return str(item.data(Qt.UserRole) or "") if item else ""

    def mostrar(self, resultado, estado):
        self.lbl_estado.setText("Estado: {}".format(estado))
        self.lbl_pedidos.setText("Pedidos: {}".format(resultado.pedidos))
        self.lbl_kg.setText("KG: {}".format(resultado.kg))
        self.lbl_bultos.setText("Bultos: {}".format(resultado.bultos))
        self.tabla.setRowCount(0)
        for item in resultado.items:
            row = self.tabla.rowCount()
            self.tabla.insertRow(row)
            estado_item = QTableWidgetItem("OK" if item.cumplido else "PENDIENTE")
            estado_item.setData(Qt.UserRole, item.codigo)
            requisito_item = QTableWidgetItem(item.descripcion)
            detalle_item = QTableWidgetItem(item.detalle or "")
            if not item.cumplido:
                tooltip = "Doble clic para corregir este requisito."
                estado_item.setToolTip(tooltip)
                requisito_item.setToolTip(tooltip)
                detalle_item.setToolTip(tooltip)
            self.tabla.setItem(row, 0, estado_item)
            self.tabla.setItem(row, 1, requisito_item)
            self.tabla.setItem(row, 2, detalle_item)
        self.tabla.resizeColumnsToContents()
        self.btn_lista.setEnabled(estado != "DESPACHADA" and resultado.valida)
        self.btn_hoja.setEnabled(estado in ("LISTA", "DESPACHADA") and resultado.pedidos > 0)
        self.btn_despachar.setEnabled(estado == "LISTA" and resultado.valida)
        self.btn_asignar.setEnabled(any(i.codigo in ("chofer", "camion") and not i.cumplido for i in resultado.items))
        if estado == "LISTA":
            mensaje = "Hoja validada. Genere o revise el PDF y luego marque el despacho."
        elif estado == "DESPACHADA":
            mensaje = "Hoja despachada. El circuito operativo está finalizado."
        elif resultado.valida:
            mensaje = "La hoja cumple todos los requisitos. Puede marcarla como LISTA."
        else:
            mensaje = "Complete los requisitos pendientes antes de marcar la hoja como LISTA."
        self.lbl_mensaje.setText(mensaje)

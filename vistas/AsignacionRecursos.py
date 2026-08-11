# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QDateEdit, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)


class AsignacionRecursosView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asignar chofer y camión")
        self.resize(760, 520)
        self._build_ui()

    def _build_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        raiz.setSpacing(16)

        titulo = QLabel("Asignar chofer y camión")
        titulo.setObjectName("asignacionRecursosTitulo")
        raiz.addWidget(titulo)
        detalle = QLabel("Seleccione la fecha y la ruta. RND aplicará ambos recursos a todos los pedidos de esa hoja de ruta en una sola operación.")
        detalle.setWordWrap(True)
        raiz.addWidget(detalle)

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
        self.btn_cargar = QPushButton("Cargar hoja")
        filtros.addWidget(self.btn_cargar)
        filtros.addStretch(1)
        raiz.addLayout(filtros)

        resumen = QGroupBox("Resumen de la hoja")
        form_resumen = QFormLayout(resumen)
        self.lbl_pedidos = QLabel("0")
        self.lbl_kg = QLabel("0")
        self.lbl_bultos = QLabel("0")
        self.lbl_actual = QLabel("Sin asignación")
        self.lbl_actual.setWordWrap(True)
        form_resumen.addRow("Pedidos:", self.lbl_pedidos)
        form_resumen.addRow("Peso total:", self.lbl_kg)
        form_resumen.addRow("Bultos:", self.lbl_bultos)
        form_resumen.addRow("Asignación actual:", self.lbl_actual)
        raiz.addWidget(resumen)

        recursos = QGroupBox("Recursos")
        form_recursos = QFormLayout(recursos)
        self.cbo_responsable = QComboBox()
        self.cbo_equipo = QComboBox()
        form_recursos.addRow("Chofer / responsable:", self.cbo_responsable)
        form_recursos.addRow("Camión / equipo:", self.cbo_equipo)
        raiz.addWidget(recursos)

        self.lbl_estado = QLabel("Seleccione una hoja de ruta para continuar.")
        self.lbl_estado.setWordWrap(True)
        raiz.addWidget(self.lbl_estado)

        acciones = QHBoxLayout()
        acciones.addStretch(1)
        self.btn_guardar = QPushButton("Guardar asignación")
        self.btn_guardar.setProperty("role", "primary")
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.setEnabled(False)
        acciones.addWidget(self.btn_guardar)
        self.btn_siguiente = QPushButton("Validar hoja de ruta")
        self.btn_siguiente.setEnabled(False)
        acciones.addWidget(self.btn_siguiente)
        self.btn_cerrar = QPushButton("Cerrar")
        acciones.addWidget(self.btn_cerrar)
        raiz.addLayout(acciones)

    def cargar_rutas(self, rutas, seleccion=0):
        self.cbo_ruta.clear()
        self.cbo_ruta.addItem("Seleccione una ruta", 0)
        indice = 0
        for i, (ruta_id, descripcion) in enumerate(rutas, start=1):
            self.cbo_ruta.addItem(descripcion, ruta_id)
            if int(ruta_id) == int(seleccion or 0):
                indice = i
        self.cbo_ruta.setCurrentIndex(indice)

    def cargar_responsables(self, responsables):
        self.cbo_responsable.clear()
        self.cbo_responsable.addItem("Seleccione un chofer", 0)
        for empleado_id, nombre in responsables:
            self.cbo_responsable.addItem(nombre, empleado_id)

    def cargar_equipos(self, equipos):
        self.cbo_equipo.clear()
        self.cbo_equipo.addItem("Seleccione un camión", 0)
        for equipo_id, descripcion in equipos:
            self.cbo_equipo.addItem(descripcion, equipo_id)

    def seleccionar_recursos(self, responsable_id, equipo_id):
        for combo, valor in ((self.cbo_responsable, responsable_id), (self.cbo_equipo, equipo_id)):
            idx = combo.findData(int(valor or 0))
            combo.setCurrentIndex(idx if idx >= 0 else 0)

    def set_resumen(self, resumen, texto_actual):
        self.lbl_pedidos.setText(str(resumen.pedidos))
        self.lbl_kg.setText(str(resumen.kg))
        self.lbl_bultos.setText(str(resumen.bultos))
        self.lbl_actual.setText(texto_actual)
        self.btn_guardar.setEnabled(not resumen.vacia)

    def ruta_id(self):
        return int(self.cbo_ruta.currentData() or 0)

    def responsable_id(self):
        return int(self.cbo_responsable.currentData() or 0)

    def equipo_id(self):
        return int(self.cbo_equipo.currentData() or 0)

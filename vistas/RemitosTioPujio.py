# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.utiles import imagen
from utiles.remitos_tio_pujio import (
    ESTADO_ASIGNADO,
    ESTADO_AMBIGUO,
    ESTADO_SIN_PEDIDO,
    ESTADO_YA_TENIA_REMITO,
)


ESTADOS_TEXTO = {
    ESTADO_ASIGNADO: "Asignado",
    ESTADO_AMBIGUO: "Revisar",
    ESTADO_SIN_PEDIDO: "Sin pedido",
    ESTADO_YA_TENIA_REMITO: "Ya tenía remito",
}

COLORES_ESTADO = {
    ESTADO_ASIGNADO: QColor("#dcfce7"),
    ESTADO_AMBIGUO: QColor("#fef3c7"),
    ESTADO_SIN_PEDIDO: QColor("#fee2e2"),
    ESTADO_YA_TENIA_REMITO: QColor("#ffedd5"),
}

COLOR_YA_ASOCIADO = QColor("#e0f2fe")

COLORES_MENSAJE = {
    "info": ("#e0f2fe", "#075985"),
    "pendiente": ("#fef3c7", "#92400e"),
    "ok": ("#dcfce7", "#166534"),
    "error": ("#fee2e2", "#991b1b"),
}


class RemitosTioPujioView(VistaBase):
    COLUMNAS = [
        "Fecha",
        "Remito",
        "Código",
        "Cliente",
        "Total",
        "PED",
        "Estado",
        "Motivo",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Importar remitos de Tío Pujio")
        self.resize(1180, 700)

        raiz = QVBoxLayout(self)
        raiz.setSpacing(10)

        titulo = QLabel("Cruce de remitos")
        titulo.setObjectName("importacionTitulo")
        titulo.setProperty("role", "title")
        raiz.addWidget(titulo)

        bajada = QLabel(
            "Seleccioná el Control de Pedidos que ya importaste y el Informe de "
            "Remitos del mismo período. RND cruza por código de cliente y te "
            "muestra qué remito va a cada PED antes de grabar."
        )
        bajada.setWordWrap(True)
        bajada.setObjectName("importacionBajada")
        raiz.addWidget(bajada)

        grupo_archivos = QGroupBox("1. Archivos")
        layout_archivos = QVBoxLayout(grupo_archivos)

        fila_pedidos = QHBoxLayout()
        fila_pedidos.addWidget(QLabel("Control de Pedidos:"))
        self.txt_pedidos = QLineEdit()
        self.txt_pedidos.setReadOnly(True)
        self.txt_pedidos.setPlaceholderText(
            "Excel del Control de Pedidos usado para importar..."
        )
        fila_pedidos.addWidget(self.txt_pedidos, stretch=1)
        self.btn_pedidos = Boton(
            texto="Seleccionar Excel",
            imagen=imagen("79354_excel_icon.png"),
            tooltip="Seleccionar el Control de Pedidos del período",
        )
        fila_pedidos.addWidget(self.btn_pedidos)
        layout_archivos.addLayout(fila_pedidos)

        fila_remitos = QHBoxLayout()
        fila_remitos.addWidget(QLabel("Informe de Remitos:"))
        self.txt_remitos = QLineEdit()
        self.txt_remitos.setReadOnly(True)
        self.txt_remitos.setPlaceholderText(
            "Excel del Informe de Remitos de Tío Pujio..."
        )
        fila_remitos.addWidget(self.txt_remitos, stretch=1)
        self.btn_remitos = Boton(
            texto="Seleccionar Excel",
            imagen=imagen("79354_excel_icon.png"),
            tooltip="Seleccionar el Informe de Remitos del período",
        )
        fila_remitos.addWidget(self.btn_remitos)
        layout_archivos.addLayout(fila_remitos)

        nota = QLabel(
            "Los pedidos tienen que estar importados y grabados. Si falta algún "
            "pedido, el remito queda como «Sin pedido» y no se graba."
        )
        nota.setWordWrap(True)
        nota.setObjectName("importacionNotaTecnica")
        layout_archivos.addWidget(nota)
        raiz.addWidget(grupo_archivos)

        fila_acciones = QHBoxLayout()
        self.btn_cruzar = Boton(
            texto="Leer y cruzar",
            imagen=imagen("search.png"),
            tooltip="Leer los dos Excel y mostrar el cruce antes de grabar",
        )
        self.btn_cruzar.setProperty("role", "primary")
        fila_acciones.addWidget(self.btn_cruzar)
        self.lbl_resumen = QLabel("Todavía no se cruzaron los archivos.")
        self.lbl_resumen.setWordWrap(True)
        fila_acciones.addWidget(self.lbl_resumen, stretch=1)
        raiz.addLayout(fila_acciones)

        self.lbl_estado = QLabel("")
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setObjectName("remitosEstado")
        raiz.addWidget(self.lbl_estado)
        self.set_estado(
            "Seleccioná los dos archivos y presioná «Leer y cruzar».",
            "info",
        )

        self.tabla = QTableWidget(0, len(self.COLUMNAS))
        self.tabla.setObjectName("dataGrid")
        self.tabla.setHorizontalHeaderLabels(self.COLUMNAS)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.verticalHeader().setDefaultSectionSize(32)
        cabecera = self.tabla.horizontalHeader()
        cabecera.setSectionResizeMode(QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(3, QHeaderView.Stretch)
        cabecera.setSectionResizeMode(7, QHeaderView.Stretch)
        raiz.addWidget(self.tabla, stretch=1)

        botones = QHBoxLayout()
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"))
        self.btn_grabar = Boton(
            texto="Grabar remitos",
            imagen=imagen("save.png"),
            tooltip="Asociar los remitos asignados a los pedidos",
        )
        self.btn_grabar.setProperty("role", "primary")
        self.btn_grabar.setEnabled(False)
        botones.addWidget(self.btn_cerrar)
        botones.addStretch(1)
        botones.addWidget(self.btn_grabar)
        raiz.addLayout(botones)

    def set_archivo_pedidos(self, ruta):
        self.txt_pedidos.setText(str(ruta or ""))

    def set_archivo_remitos(self, ruta):
        self.txt_remitos.setText(str(ruta or ""))

    def archivo_pedidos(self):
        return self.txt_pedidos.text().strip()

    def archivo_remitos(self):
        return self.txt_remitos.text().strip()

    def set_resumen(self, texto):
        self.lbl_resumen.setText(str(texto or ""))

    def set_estado(self, texto, tipo="info"):
        fondo, color = COLORES_MENSAJE.get(tipo, COLORES_MENSAJE["info"])
        self.lbl_estado.setText(str(texto or ""))
        self.lbl_estado.setStyleSheet(
            "QLabel { background-color: %s; color: %s; padding: 8px 10px; "
            "border-radius: 4px; }" % (fondo, color)
        )

    def set_grabar_habilitado(self, habilitado, texto=None, tooltip=None):
        self.btn_grabar.setEnabled(bool(habilitado))
        self.btn_grabar.setText(texto or "Grabar remitos")
        if tooltip is not None:
            self.btn_grabar.setToolTip(tooltip)

    def limpiar_resultados(self):
        self.tabla.setRowCount(0)

    def cargar_resultados(self, resultados):
        self.limpiar_resultados()
        for resultado in resultados:
            fila = self.tabla.rowCount()
            self.tabla.insertRow(fila)
            remito = resultado.remito
            pedido = (
                resultado.pedido.numero_pedido if resultado.pedido else ""
            )
            valores = [
                self._fecha_texto(remito.fecha),
                remito.numero_remito,
                remito.codigo_cliente,
                remito.nombre_cliente,
                self._importe_texto(remito.importe_total),
                pedido,
                ESTADOS_TEXTO.get(resultado.estado, resultado.estado),
                resultado.motivo,
            ]
            color = COLORES_ESTADO.get(resultado.estado, QColor("#ffffff"))
            if (
                resultado.estado == ESTADO_ASIGNADO
                and resultado.motivo == "ya estaba asociado"
            ):
                color = COLOR_YA_ASOCIADO
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setBackground(color)
                if columna == 7 and resultado.motivo:
                    item.setToolTip(resultado.motivo)
                self.tabla.setItem(fila, columna, item)

    @staticmethod
    def _fecha_texto(valor):
        return valor.strftime("%d/%m/%Y") if valor else ""

    @staticmethod
    def _importe_texto(valor):
        if valor is None:
            return ""
        return "{:,.2f}".format(abs(float(valor)))

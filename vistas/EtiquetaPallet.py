import os
import tempfile

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QVBoxLayout,
)
from pyqt5libs.libs.vistas.VistaBase import VistaBase


class EtiquetaPalletDialog(VistaBase):
    """Etiqueta con QR y consulta de composicion por codigo."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pallet_id = 0
        self._qr_png = ""
        self.initUi(self)

    def initUi(self, parent):
        self.resize(480, 620)
        self.setWindowTitle("Etiqueta del pallet")
        layout = QVBoxLayout(parent)

        fila_consulta = QHBoxLayout()
        fila_consulta.addWidget(QLabel("Código:"))
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("Ingrese o escanee el código")
        self.txt_codigo.returnPressed.connect(self._consultar_desde_texto)
        fila_consulta.addWidget(self.txt_codigo, 1)
        self.btn_ver = self.CreaBoton("Ver", imagen_str="search.png")
        self.btn_ver.clicked.connect(self._consultar_desde_texto)
        fila_consulta.addWidget(self.btn_ver)
        layout.addLayout(fila_consulta)

        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("etiquetaPalletError")
        self.lbl_error.setWordWrap(True)
        layout.addWidget(self.lbl_error)

        self.lbl_codigo = QLabel("—")
        self.lbl_codigo.setObjectName("etiquetaPalletCodigo")
        fuente = QFont()
        fuente.setPointSize(28)
        fuente.setBold(True)
        self.lbl_codigo.setFont(fuente)
        self.lbl_codigo.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_codigo)

        self.lbl_qr = QLabel()
        self.lbl_qr.setObjectName("etiquetaPalletQr")
        self.lbl_qr.setAlignment(Qt.AlignCenter)
        self.lbl_qr.setMinimumHeight(230)
        layout.addWidget(self.lbl_qr)

        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setObjectName("etiquetaPalletResumen")
        self.lbl_resumen.setWordWrap(True)
        self.lbl_resumen.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.lbl_resumen)

        self.lbl_destinos = QLabel("")
        self.lbl_destinos.setObjectName("etiquetaPalletDestinos")
        self.lbl_destinos.setWordWrap(True)
        layout.addWidget(self.lbl_destinos)
        layout.addStretch(1)

        botones = QHBoxLayout()
        botones.addStretch(1)
        self.btn_pdf = self.CreaBoton("Vista previa PDF", imagen_str="printing.png")
        self.btn_cerrar = self.CreaBoton("Cerrar", imagen_str="close.png")
        botones.addWidget(self.btn_pdf)
        botones.addWidget(self.btn_cerrar)
        layout.addLayout(botones)

    def mostrar_pallet(self, pallet):
        """Carga un pallet (id u objeto). Devuelve False si no existe."""
        from modelos.Pallet import (
            buscar_por_codigo, totales_pallet, totales_por_destino,
        )
        from utiles.etiqueta_pallet import generar_qr_png

        if isinstance(pallet, str):
            pallet = buscar_por_codigo(pallet)
        else:
            from modelos.Pallet import Pallet
            pallet = Pallet.get_or_none(
                Pallet.id == getattr(pallet, "id", pallet)
            )
        if pallet is None:
            self.lbl_error.setText(
                "No se encontró ningún pallet con ese código."
            )
            return False
        self.lbl_error.setText("")
        self._pallet_id = pallet.id
        self.txt_codigo.setText(pallet.codigo)
        self.lbl_codigo.setText(pallet.codigo)

        try:
            self._qr_png = generar_qr_png(pallet.codigo)
            pixmap = QPixmap(self._qr_png)
            if not pixmap.isNull():
                self.lbl_qr.setPixmap(
                    pixmap.scaledToWidth(220, Qt.SmoothTransformation)
                )
            else:
                self.lbl_qr.setText("(QR no disponible)")
        except Exception:
            self.lbl_qr.setText("(QR no disponible)")
            self._qr_png = ""

        total = totales_pallet(pallet.id)
        destinos = totales_por_destino(pallet.id)
        self.lbl_resumen.setText(
            "{} líneas · {} cant · {} KG · {} bultos".format(
                total["lineas"], total["cantidad"],
                total["kg"], total["bultos"],
            )
        )
        self.lbl_destinos.setText("\n".join(
            "{} / {}: {} cant".format(
                d.get("cliente") or "Sin cliente",
                d.get("lugar_entrega") or "Sin lugar",
                d.get("cantidad", 0),
            )
            for d in destinos
        ) or "Pallet vacío.")
        return True

    def pallet_actual_id(self):
        return int(self._pallet_id or 0)

    def qr_actual(self):
        return str(self._qr_png or "")

    def _consultar_desde_texto(self):
        self.mostrar_pallet(self.txt_codigo.text())

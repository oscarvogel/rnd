# coding=utf-8
"""Login corporativo RND Logística + Vogel Consultoría.

La pantalla usa el mockup visual aprobado como fondo y superpone únicamente
los controles interactivos reales de PyQt5. Así se conserva el diseño visual
sin sacrificar la autenticación existente.
"""

import base64
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QLabel, QPushButton

from modelos.Usuarios import CboUsuario
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.EntradaTexto import Password


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "login"
MOCKUP_B64 = ASSET_DIR / "rnd_login_mockup.b64"

# Coordenadas relativas al mockup 1280 x 720.
REF_W = 1280.0
REF_H = 720.0


class LoginView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mockup = QPixmap()
        self.setupUi(self)

    def _load_mockup(self):
        try:
            raw = base64.b64decode(MOCKUP_B64.read_text(encoding="ascii").strip())
            self._mockup.loadFromData(raw, "JPG")
        except Exception:
            self._mockup = QPixmap()

    def setupUi(self, Form):
        self.setWindowTitle("RND Logística - Inicio de sesión")
        Form.resize(1280, 720)
        Form.setMinimumSize(1024, 576)
        Form.setObjectName("rndLogin")

        self._load_mockup()

        self.background = QLabel(Form)
        self.background.setObjectName("loginBackground")
        self.background.setScaledContents(True)
        if not self._mockup.isNull():
            self.background.setPixmap(self._mockup)

        # Solo el área de texto del usuario se vuelve un control real.
        # El icono, bordes y etiqueta permanecen en el mockup.
        self.cboUsuario = CboUsuario(Form)
        self.cboUsuario.setObjectName("loginUsuario")
        self.cboUsuario.setStyleSheet("""
            QComboBox {
                background: rgba(248, 251, 254, 245);
                border: none;
                padding: 0 10px;
                color: #17334f;
                font-family: "Segoe UI";
                font-size: 17px;
            }
            QComboBox:focus {
                background: rgba(255, 255, 255, 250);
            }
            QComboBox::drop-down {
                border: none;
                width: 22px;
            }
            QComboBox::down-arrow {
                image: none;
            }
        """)

        self.textPass = Password(Form)
        self.textPass.setObjectName("loginPassword")
        self.textPass.setPlaceholderText("")
        self.textPass.setStyleSheet("""
            QLineEdit {
                background: rgba(248, 251, 254, 245);
                border: none;
                padding: 0 10px;
                color: #17334f;
                font-family: "Segoe UI";
                font-size: 17px;
            }
            QLineEdit:focus {
                background: rgba(255, 255, 255, 250);
            }
        """)

        # Los botones son zonas interactivas reales sobre el diseño aprobado.
        # En reposo son transparentes para que se vea exactamente el mockup.
        self.btnIngresar = QPushButton("", Form)
        self.btnIngresar.setObjectName("loginIngresar")
        self.btnIngresar.setCursor(Qt.PointingHandCursor)
        self.btnIngresar.setDefault(True)
        self.btnIngresar.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 24);
            }
            QPushButton:pressed {
                background: rgba(0, 55, 120, 35);
            }
        """)

        self.btnCerrar = QPushButton("", Form)
        self.btnCerrar.setObjectName("loginCerrar")
        self.btnCerrar.setCursor(Qt.PointingHandCursor)
        self.btnCerrar.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 30);
            }
            QPushButton:pressed {
                background: rgba(30, 80, 120, 25);
            }
        """)

        self.textPass.proximoWidget = self.btnIngresar
        self._position_overlays()

    @staticmethod
    def _scaled_rect(x, y, w, h, width, height):
        sx = width / REF_W
        sy = height / REF_H
        return (
            int(round(x * sx)),
            int(round(y * sy)),
            int(round(w * sx)),
            int(round(h * sy)),
        )

    def _position_overlays(self):
        w = max(1, self.width())
        h = max(1, self.height())

        self.background.setGeometry(0, 0, w, h)

        # Área editable del combo dentro del campo visual del mockup.
        self.cboUsuario.setGeometry(
            *self._scaled_rect(493, 296, 343, 48, w, h)
        )
        self.textPass.setGeometry(
            *self._scaled_rect(493, 368, 343, 47, w, h)
        )

        # Zonas clickeables coinciden con los botones ya dibujados.
        self.btnIngresar.setGeometry(
            *self._scaled_rect(438, 432, 401, 53, w, h)
        )
        self.btnCerrar.setGeometry(
            *self._scaled_rect(438, 494, 401, 49, w, h)
        )

        self.background.lower()
        self.cboUsuario.raise_()
        self.textPass.raise_()
        self.btnIngresar.raise_()
        self.btnCerrar.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_overlays()

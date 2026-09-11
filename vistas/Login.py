# coding=utf-8
"""Login corporativo RND Logística + Vogel Consultoría.

El fondo usa el mockup aprobado como imagen completa y PyQt5 solo superpone
los controles interactivos reales.
"""

import base64
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPainter, QPixmap
from PyQt5.QtWidgets import QPushButton

from modelos.Usuarios import CboUsuario
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.EntradaTexto import Password


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "login"
MOCKUP_B64 = ASSET_DIR / "rnd_login_mockup.b64"

REF_W = 1280.0
REF_H = 720.0


class LoginView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mockup = QPixmap()
        self._mockup_ok = False
        self.setupUi(self)

    def _load_mockup(self):
        self._mockup_ok = False
        try:
            raw = base64.b64decode(MOCKUP_B64.read_text(encoding="ascii").strip())
            image = QImage.fromData(raw)
            if not image.isNull():
                self._mockup = QPixmap.fromImage(image)
                self._mockup_ok = not self._mockup.isNull()
        except Exception as exc:
            print("LOGIN_MOCKUP_ERROR:", repr(exc))

        if not self._mockup_ok:
            print("LOGIN_MOCKUP_ERROR: no se pudo cargar", MOCKUP_B64)

    def setupUi(self, Form):
        self.setWindowTitle("RND Logística - Inicio de sesión")
        Form.resize(1280, 720)
        Form.setMinimumSize(1024, 576)
        Form.setObjectName("rndLogin")
        Form.setAttribute(Qt.WA_OpaquePaintEvent, True)

        self._load_mockup()

        self.cboUsuario = CboUsuario(Form)
        self.cboUsuario.setObjectName("loginUsuario")
        self.cboUsuario.setStyleSheet("""
            QComboBox {
                background: rgba(249, 252, 254, 248);
                border: 1px solid #9eb8ca;
                border-radius: 10px;
                padding: 0 12px;
                color: #17334f;
                font-family: "Segoe UI";
                font-size: 16px;
            }
            QComboBox:focus {
                border: 2px solid #00a7e1;
                background: white;
            }
        """)

        self.textPass = Password(Form)
        self.textPass.setObjectName("loginPassword")
        self.textPass.setPlaceholderText("Ingresá tu contraseña")
        self.textPass.setStyleSheet("""
            QLineEdit {
                background: rgba(249, 252, 254, 248);
                border: 1px solid #9eb8ca;
                border-radius: 10px;
                padding: 0 12px;
                color: #17334f;
                font-family: "Segoe UI";
                font-size: 16px;
            }
            QLineEdit:focus {
                border: 2px solid #00a7e1;
                background: white;
            }
        """)

        self.btnIngresar = QPushButton("Ingresar", Form)
        self.btnIngresar.setObjectName("loginIngresar")
        self.btnIngresar.setCursor(Qt.PointingHandCursor)
        self.btnIngresar.setDefault(True)
        self.btnIngresar.setStyleSheet("""
            QPushButton {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10a9df,
                    stop:1 #0b67ae
                );
                color: white;
                border: none;
                border-radius: 11px;
                font: 700 16px "Segoe UI";
            }
            QPushButton:hover {
                background: #0b85c5;
            }
        """)

        self.btnCerrar = QPushButton("Cerrar", Form)
        self.btnCerrar.setObjectName("loginCerrar")
        self.btnCerrar.setCursor(Qt.PointingHandCursor)
        self.btnCerrar.setStyleSheet("""
            QPushButton {
                background: rgba(255,255,255,235);
                color: #18364d;
                border: 1px solid #94b4c9;
                border-radius: 11px;
                font: 600 15px "Segoe UI";
            }
            QPushButton:hover {
                background: #f3f8fb;
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

        self.cboUsuario.setGeometry(
            *self._scaled_rect(748, 264, 315, 45, w, h)
        )
        self.textPass.setGeometry(
            *self._scaled_rect(748, 346, 315, 45, w, h)
        )
        self.btnIngresar.setGeometry(
            *self._scaled_rect(748, 423, 315, 54, w, h)
        )
        self.btnCerrar.setGeometry(
            *self._scaled_rect(748, 487, 315, 55, w, h)
        )

        self.cboUsuario.raise_()
        self.textPass.raise_()
        self.btnIngresar.raise_()
        self.btnCerrar.raise_()

    def paintEvent(self, event):
        painter = QPainter(self)
        if self._mockup_ok:
            scaled = self._mockup.scaled(
                self.size(),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            painter.drawPixmap(0, 0, scaled)
        else:
            painter.fillRect(self.rect(), Qt.white)

        painter.end()
        super().paintEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_overlays()
        self.update()

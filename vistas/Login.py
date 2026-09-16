# coding=utf-8
"""Login corporativo RND Logística + Vogel Consultoría.

La escena logística es un asset PNG real. Los controles que consume el
controlador permanecen como widgets PyQt5 sobre una tarjeta translúcida.
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtWidgets import QFrame, QLabel, QPushButton

from modelos.Usuarios import CboUsuario
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.EntradaTexto import Password


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "login"
BACKGROUND_ASSET = ASSET_DIR / "rnd_login_background.png"
RND_LOGO_ASSET = ASSET_DIR / "rnd_logo.svg"
VOGEL_LOGO_ASSET = ASSET_DIR / "vogel_logo.svg"

REF_W = 1280.0
REF_H = 720.0


class LoginView(VistaBase):
    """Ventana de acceso RND con escena de logística y tarjeta central."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._background_pixmap = QPixmap(str(BACKGROUND_ASSET))
        self.setupUi(self)

    def setupUi(self, Form):
        self.setWindowTitle("RND Logística - Inicio de sesión")
        Form.resize(1280, 720)
        Form.setMinimumSize(1024, 576)
        Form.setObjectName("rndLogin")

        self.background = QLabel(Form)
        self.background.setObjectName("loginBackground")
        self.background.setAlignment(Qt.AlignCenter)
        self.background.setStyleSheet("background: #0b4776;")

        self.loginCard = QFrame(Form)
        self.loginCard.setObjectName("loginCard")
        self.loginCard.setStyleSheet("""
            QFrame#loginCard {
                background: rgba(249, 253, 255, 218);
                border: 1px solid rgba(255, 255, 255, 225);
                border-radius: 25px;
            }
        """)

        self.rndLogo = QSvgWidget(str(RND_LOGO_ASSET), self.loginCard)
        self.rndLogo.setObjectName("rndLogo")

        self.lblClaim = self._label(
            "RUTAS   •   PERSONAS   •   RESULTADOS", 13, 700, "#093a79"
        )
        self.lblClaim.setParent(self.loginCard)
        self.lblClaim.setAlignment(Qt.AlignCenter)
        self.lblClaim.setStyleSheet(self.lblClaim.styleSheet() + "letter-spacing: 3px;")

        self.lblUsuario = self._label("Usuario", 13, 600, "#0b3975")
        self.lblUsuario.setParent(self.loginCard)

        self.cboUsuario = CboUsuario(self.loginCard)
        # ComboSQL legacy descarta el parent recibido en su constructor.
        # Reasignarlo lo mantiene dentro de la tarjeta y visible al abrirse.
        self.cboUsuario.setParent(self.loginCard)
        self.cboUsuario.setObjectName("loginUsuario")
        self.cboUsuario.setStyleSheet(self._field_style("QComboBox"))

        self.lblPassword = self._label("Contraseña", 13, 600, "#0b3975")
        self.lblPassword.setParent(self.loginCard)

        self.textPass = Password(self.loginCard)
        self.textPass.setObjectName("loginPassword")
        self.textPass.setPlaceholderText("Ingresá tu contraseña")
        self.textPass.setStyleSheet(self._field_style("QLineEdit"))

        self.btnIngresar = QPushButton("Ingresar", self.loginCard)
        self.btnIngresar.setObjectName("loginIngresar")
        self.btnIngresar.setCursor(Qt.PointingHandCursor)
        self.btnIngresar.setDefault(True)
        self.btnIngresar.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #13b7e8, stop:1 #0866c8);
                color: white;
                border: 0;
                border-radius: 11px;
                font: 700 17px "Segoe UI";
            }
            QPushButton:hover { background: #087dce; }
            QPushButton:pressed { background: #07529f; }
        """)

        self.btnCerrar = QPushButton("Cerrar", self.loginCard)
        self.btnCerrar.setObjectName("loginCerrar")
        self.btnCerrar.setCursor(Qt.PointingHandCursor)
        self.btnCerrar.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 150);
                color: #0a3d80;
                border: 1px solid #0c6ac1;
                border-radius: 11px;
                font: 600 16px "Segoe UI";
            }
            QPushButton:hover { background: rgba(255, 255, 255, 225); }
            QPushButton:pressed { background: #e6f2fc; }
        """)

        self.lblDeveloped = self._label("Desarrollado por", 11, 400, "#3b6495")
        self.lblDeveloped.setParent(self.loginCard)
        self.lblDeveloped.setAlignment(Qt.AlignCenter)

        self.vogelLogo = QSvgWidget(str(VOGEL_LOGO_ASSET), self.loginCard)
        self.vogelLogo.setObjectName("vogelLogo")

        self.lblWebsite = self._label("vogelconsultoria.com.ar", 10, 600, "#245989")
        self.lblWebsite.setParent(self.loginCard)
        self.lblWebsite.setAlignment(Qt.AlignCenter)

        self.textPass.proximoWidget = self.btnIngresar
        self._position_widgets()

    @staticmethod
    def _label(text, size, weight, color):
        label = QLabel(text)
        label.setStyleSheet(
            'color: {}; font: {} {}px "Segoe UI"; background: transparent;'.format(
                color, weight, size
            )
        )
        return label

    @staticmethod
    def _field_style(selector):
        return """
            {} {{
                background: rgba(255, 255, 255, 238);
                border: 1px solid #82a9d3;
                border-radius: 10px;
                padding: 0 12px;
                color: #0b3677;
                font: 16px "Segoe UI";
            }}
            {}:focus {{ border: 2px solid #13a9e0; background: white; }}
        """.format(selector, selector)

    @staticmethod
    def _scaled_rect(x, y, width, height, window_width, window_height):
        return (
            int(round(x * window_width / REF_W)),
            int(round(y * window_height / REF_H)),
            int(round(width * window_width / REF_W)),
            int(round(height * window_height / REF_H)),
        )

    def _position_widgets(self):
        width, height = self.width(), self.height()
        self.background.setGeometry(0, 0, width, height)
        if not self._background_pixmap.isNull():
            self.background.setPixmap(
                self._background_pixmap.scaled(
                    width, height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation
                )
            )

        self.loginCard.setGeometry(
            *self._scaled_rect(384, 34, 512, 625, width, height)
        )
        card_width, card_height = self.loginCard.width(), self.loginCard.height()
        scale_x = card_width / 512.0
        scale_y = card_height / 625.0

        def card_rect(x, y, widget_width, widget_height):
            return (
                int(round(x * scale_x)),
                int(round(y * scale_y)),
                int(round(widget_width * scale_x)),
                int(round(widget_height * scale_y)),
            )

        self.rndLogo.setGeometry(*card_rect(104, 36, 304, 105))
        self.lblClaim.setGeometry(*card_rect(48, 155, 416, 28))
        self.lblUsuario.setGeometry(*card_rect(70, 204, 372, 24))
        self.cboUsuario.setGeometry(*card_rect(70, 225, 372, 49))
        self.lblPassword.setGeometry(*card_rect(70, 293, 372, 24))
        self.textPass.setGeometry(*card_rect(70, 314, 372, 49))
        self.btnIngresar.setGeometry(*card_rect(70, 387, 372, 55))
        self.btnCerrar.setGeometry(*card_rect(70, 455, 372, 54))
        self.lblDeveloped.setGeometry(*card_rect(80, 529, 352, 20))
        self.vogelLogo.setGeometry(*card_rect(118, 550, 276, 58))
        self.lblWebsite.setGeometry(*card_rect(80, 600, 352, 18))

        self.background.lower()
        self.loginCard.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_widgets()

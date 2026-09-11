# coding=utf-8
"""Login corporativo RND Logística + Vogel Consultoría."""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from modelos.Usuarios import CboUsuario
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.EntradaTexto import Password


ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "login"


class SvgImageLabel(QLabel):
    """Etiqueta para recursos SVG escalables manteniendo proporción."""

    def __init__(self, filename, parent=None):
        super().__init__(parent)
        self.filename = str(ASSET_DIR / filename)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        pixmap = QPixmap(self.filename)
        if not pixmap.isNull():
            self.setPixmap(
                pixmap.scaled(
                    self.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )


class LoginView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    @staticmethod
    def _shadow(widget, blur=40, offset_y=10, alpha=55):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset_y)
        shadow.setColor(QColor(0, 38, 65, alpha))
        widget.setGraphicsEffect(shadow)

    def setupUi(self, Form):
        self.setWindowTitle("RND Logística - Inicio de sesión")
        Form.resize(1220, 720)
        Form.setMinimumSize(1060, 640)
        Form.setObjectName("rndLogin")
        Form.setStyleSheet("""
            #rndLogin {
                background: #eaf2f7;
            }
            QFrame#heroFrame {
                background: #0a557f;
                border-radius: 28px;
            }
            QFrame#loginCard {
                background: rgba(255,255,255,248);
                border: 1px solid #d7e3ea;
                border-radius: 28px;
            }
            QLabel#fieldLabel {
                color: #17364d;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#supportText {
                color: #7b91a2;
                font-family: "Segoe UI";
                font-size: 11px;
            }
            QComboBox, QLineEdit {
                min-height: 48px;
                background: #fbfdfe;
                border: 1px solid #b8ccd9;
                border-radius: 12px;
                padding: 0 14px;
                color: #17364d;
                font-family: "Segoe UI";
                font-size: 14px;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 2px solid #12a7dd;
                background: white;
            }
            QPushButton#primaryButton {
                min-height: 52px;
                border: 0;
                border-radius: 12px;
                color: white;
                font-family: "Segoe UI";
                font-size: 16px;
                font-weight: 700;
                background: qlineargradient(
                    x1:0,y1:0,x2:1,y2:0,
                    stop:0 #11a8df,
                    stop:1 #0a5ea5
                );
            }
            QPushButton#primaryButton:hover {
                background: qlineargradient(
                    x1:0,y1:0,x2:1,y2:0,
                    stop:0 #1db8ef,
                    stop:1 #0b6fbd
                );
            }
            QPushButton#secondaryButton {
                min-height: 48px;
                border: 1px solid #9db5c5;
                border-radius: 12px;
                color: #17364d;
                font-family: "Segoe UI";
                font-size: 14px;
                font-weight: 600;
                background: #ffffff;
            }
            QPushButton#secondaryButton:hover {
                background: #f1f7fa;
            }
        """)

        root = QHBoxLayout(Form)
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(26)

        # Panel visual: recurso gráfico profesional, no dibujo manual de widgets.
        hero_frame = QFrame()
        hero_frame.setObjectName("heroFrame")
        hero_frame.setMinimumWidth(580)
        hero_layout = QVBoxLayout(hero_frame)
        hero_layout.setContentsMargins(0, 0, 0, 0)
        self.hero = SvgImageLabel("rnd_hero.svg")
        hero_layout.addWidget(self.hero)
        self._shadow(hero_frame, blur=36, offset_y=8, alpha=40)
        root.addWidget(hero_frame, 3)

        right = QWidget()
        right.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(0)
        right_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))

        card = QFrame()
        card.setObjectName("loginCard")
        card.setMinimumWidth(410)
        card.setMaximumWidth(470)
        self._shadow(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(42, 32, 42, 30)
        card_layout.setSpacing(10)

        self.rndLogo = SvgImageLabel("rnd_logo.svg")
        self.rndLogo.setMinimumHeight(118)
        self.rndLogo.setMaximumHeight(130)
        card_layout.addWidget(self.rndLogo)

        strap = QLabel("RUTAS   •   PERSONAS   •   RESULTADOS")
        strap.setAlignment(Qt.AlignCenter)
        strap.setStyleSheet(
            "color:#315d78; font-family:'Segoe UI'; font-size:10px;"
            "font-weight:700; letter-spacing:2px;"
        )
        card_layout.addWidget(strap)
        card_layout.addSpacing(16)

        lbl_usuario = QLabel("Usuario")
        lbl_usuario.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_usuario)

        self.cboUsuario = CboUsuario()
        card_layout.addWidget(self.cboUsuario)

        card_layout.addSpacing(5)
        lbl_pass = QLabel("Contraseña")
        lbl_pass.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_pass)

        self.textPass = Password()
        self.textPass.setPlaceholderText("Ingresá tu contraseña")
        card_layout.addWidget(self.textPass)

        card_layout.addSpacing(12)
        self.btnIngresar = QPushButton("Ingresar")
        self.btnIngresar.setObjectName("primaryButton")
        self.btnIngresar.setCursor(Qt.PointingHandCursor)
        self.btnIngresar.setDefault(True)
        card_layout.addWidget(self.btnIngresar)

        self.btnCerrar = QPushButton("Cerrar")
        self.btnCerrar.setObjectName("secondaryButton")
        self.btnCerrar.setCursor(Qt.PointingHandCursor)
        card_layout.addWidget(self.btnCerrar)

        card_layout.addSpacing(14)

        developer = QLabel("Desarrollado por")
        developer.setObjectName("supportText")
        developer.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(developer)

        self.vogelLogo = SvgImageLabel("vogel_logo.svg")
        self.vogelLogo.setMinimumHeight(62)
        self.vogelLogo.setMaximumHeight(72)
        card_layout.addWidget(self.vogelLogo)

        soluciones = QLabel("SOLUCIONES INTEGRALES  ·  vogelconsultoria.com.ar")
        soluciones.setObjectName("supportText")
        soluciones.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(soluciones)

        right_layout.addWidget(card, 0, Qt.AlignCenter)
        right_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))
        root.addWidget(right, 2)

        self.textPass.proximoWidget = self.btnIngresar

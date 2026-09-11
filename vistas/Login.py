# coding=utf-8
"""Login corporativo RND Logística + Vogel Consultoría.

La autenticación sigue siendo responsabilidad del controlador existente.
Esta vista únicamente moderniza la presentación y mantiene los mismos
atributos públicos (cboUsuario, textPass, btnIngresar y btnCerrar).
"""

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
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


AZUL = "#0B4A7E"
AZUL_OSCURO = "#08345B"
CIAN = "#18A8E0"
VERDE_RND = "#009540"
ROJO_RND = "#E30613"
GRIS_RND = "#55575A"
TEXTO = "#16324A"
TEXTO_SUAVE = "#6E879B"


class RNDLogoWidget(QWidget):
    """Logo vectorial basado en la identidad real provista por RND."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(112)
        self.setMaximumHeight(126)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        left = rect.left() + 8
        top = rect.top() + 2

        font = QFont("Segoe UI", 42)
        font.setBold(True)
        font.setItalic(True)
        painter.setFont(font)
        painter.setPen(QColor(GRIS_RND))
        painter.drawText(left, top + 58, "R N D")

        stripe_x = left + 182
        stripe_y = top + 14
        stripe_w = min(150, max(110, rect.width() - stripe_x - 20))
        stripe_h = 17

        def stripe_path(y, width):
            path = QPainterPath()
            radius = 8
            path.moveTo(stripe_x, y)
            path.lineTo(stripe_x + width, y)
            path.quadTo(stripe_x + width, y + stripe_h, stripe_x + width - radius, y + stripe_h)
            path.lineTo(stripe_x, y + stripe_h)
            path.closeSubpath()
            return path

        painter.fillPath(stripe_path(stripe_y, stripe_w), QColor(VERDE_RND))
        painter.fillPath(stripe_path(stripe_y + 25, stripe_w * 0.80), QColor(ROJO_RND))
        painter.fillPath(stripe_path(stripe_y + 50, stripe_w * 0.58), QColor(VERDE_RND))

        subtitle = QFont("Segoe UI", 14)
        subtitle.setItalic(True)
        painter.setFont(subtitle)
        painter.setPen(QColor(GRIS_RND))
        painter.drawText(left + 2, top + 88, "Logística y Distribución")


class LogisticsHero(QWidget):
    """Panel ilustrado en Qt: mapa, rutas, camión y depósito.

    Se dibuja en tiempo real para evitar depender de una imagen conceptual y
    conseguir un resultado consistente tanto en demo como en el instalador.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(520)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        r = QRectF(self.rect())

        gradient = QLinearGradient(r.topLeft(), r.bottomRight())
        gradient.setColorAt(0.0, QColor("#063A64"))
        gradient.setColorAt(0.45, QColor("#0A5D8F"))
        gradient.setColorAt(1.0, QColor("#D6EBF6"))
        painter.fillRect(r, gradient)

        # Halo claro hacia la zona del depósito.
        glow = QLinearGradient(QPointF(r.width() * 0.45, 0), QPointF(r.width(), 0))
        glow.setColorAt(0, QColor(255, 255, 255, 0))
        glow.setColorAt(1, QColor(255, 255, 255, 145))
        painter.fillRect(r, glow)

        # Mapa / red logística.
        painter.setPen(QPen(QColor(185, 233, 255, 90), 1))
        for i in range(8):
            y = 85 + i * 34
            painter.drawLine(35, y, int(r.width() * 0.54), y + (i % 2) * 9)
        for i in range(6):
            x = 60 + i * 58
            painter.drawLine(x, 48, x - 30, 330)

        route_pen = QPen(QColor("#72E6FF"), 3)
        route_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(route_pen)
        points = [
            QPointF(75, 190),
            QPointF(165, 128),
            QPointF(255, 205),
            QPointF(335, 112),
            QPointF(420, 185),
        ]
        path = QPainterPath(points[0])
        for idx in range(1, len(points)):
            p0 = points[idx - 1]
            p1 = points[idx]
            mid = QPointF((p0.x() + p1.x()) / 2.0, min(p0.y(), p1.y()) - 36)
            path.quadTo(mid, p1)
        painter.drawPath(path)

        for p in points:
            painter.setBrush(QColor("#EAFBFF"))
            painter.setPen(QPen(QColor(CIAN), 3))
            painter.drawEllipse(p, 7, 7)

        # Textos de apoyo.
        painter.setPen(QColor("#FFFFFF"))
        font = QFont("Segoe UI", 17)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(48, 74, "RUTAS MÁS EFICIENTES")
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(49, 98, "Planificar  •  Optimizar  •  Entregar")

        # Camión geométrico.
        truck_y = r.height() - 205
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#F6FAFD"))
        painter.drawRoundedRect(QRectF(66, truck_y, 250, 86), 8, 8)
        painter.setBrush(QColor("#C8DAE5"))
        painter.drawRoundedRect(QRectF(50, truck_y + 20, 76, 66), 8, 8)
        painter.setBrush(QColor(AZUL_OSCURO))
        painter.drawRect(QRectF(64, truck_y + 31, 42, 27))
        painter.setBrush(QColor("#18232B"))
        painter.drawEllipse(QPointF(98, truck_y + 91), 20, 20)
        painter.drawEllipse(QPointF(275, truck_y + 91), 20, 20)
        painter.setBrush(QColor("#DCEAF1"))
        painter.drawRect(QRectF(130, truck_y + 13, 170, 10))

        # Depósito simplificado al fondo.
        warehouse_x = r.width() * 0.62
        warehouse_y = r.height() - 285
        painter.setBrush(QColor(230, 239, 245, 210))
        painter.drawRect(QRectF(warehouse_x, warehouse_y, r.width() - warehouse_x, 250))
        painter.setBrush(QColor("#274E68"))
        for i in range(3):
            x = warehouse_x + 24 + i * 80
            painter.drawRect(QRectF(x, warehouse_y + 98, 56, 112))
            painter.setPen(QColor("#FFFFFF"))
            painter.setFont(QFont("Segoe UI", 10, QFont.Bold))
            painter.drawText(QRectF(x, warehouse_y + 110, 56, 20), Qt.AlignCenter, "0{}".format(i + 1))
            painter.setPen(Qt.NoPen)

        # Tarjeta de estado.
        painter.setBrush(QColor(255, 255, 255, 42))
        painter.setPen(QPen(QColor(255, 255, 255, 90), 1))
        painter.drawRoundedRect(QRectF(46, 320, 190, 78), 14, 14)
        painter.setPen(QColor("#FFFFFF"))
        painter.setFont(QFont("Segoe UI", 11, QFont.Bold))
        painter.drawText(QRectF(66, 336, 150, 22), Qt.AlignLeft, "FLOTA CONECTADA")
        painter.setFont(QFont("Segoe UI", 9))
        painter.drawText(QRectF(66, 360, 150, 20), Qt.AlignLeft, "Operaciones en tiempo real")

        painter.setPen(QColor(255, 255, 255, 230))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(
            QRectF(44, r.height() - 54, r.width() - 88, 30),
            Qt.AlignLeft | Qt.AlignVCenter,
            "MOVEMOS OPORTUNIDADES   •   CONECTAMOS TU NEGOCIO",
        )


class LoginView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    @staticmethod
    def _shadow(widget, blur=34, offset_y=8, alpha=65):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(blur)
        shadow.setOffset(0, offset_y)
        shadow.setColor(QColor(0, 39, 74, alpha))
        widget.setGraphicsEffect(shadow)

    def setupUi(self, Form):
        self.setWindowTitle("RND Logística - Inicio de sesión")
        Form.resize(1180, 680)
        Form.setMinimumSize(980, 600)
        Form.setObjectName("rndLogin")
        Form.setStyleSheet("""
            #rndLogin {
                background: #EAF3F8;
            }
            QFrame#loginCard {
                background: rgba(255, 255, 255, 242);
                border: 1px solid rgba(202, 221, 233, 210);
                border-radius: 24px;
            }
            QLabel#sectionTitle {
                color: #16324A;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#supportText {
                color: #6E879B;
                font-family: "Segoe UI";
                font-size: 11px;
            }
            QPushButton#primaryButton {
                min-height: 52px;
                border: none;
                border-radius: 12px;
                color: white;
                font-family: "Segoe UI";
                font-size: 16px;
                font-weight: 700;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #18A8E0,
                    stop:1 #075BA7
                );
            }
            QPushButton#primaryButton:hover {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #27B9EF,
                    stop:1 #0B6DC2
                );
            }
            QPushButton#secondaryButton {
                min-height: 48px;
                border: 1px solid #8EABC0;
                border-radius: 12px;
                color: #16324A;
                font-family: "Segoe UI";
                font-size: 15px;
                font-weight: 600;
                background: rgba(255,255,255,220);
            }
            QPushButton#secondaryButton:hover {
                background: #EEF6FA;
            }
        """)

        root = QHBoxLayout(Form)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(0)

        hero = LogisticsHero()
        hero.setObjectName("heroPanel")
        root.addWidget(hero, 13)

        shell = QWidget()
        shell.setStyleSheet("background: transparent;")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(28, 24, 28, 24)
        shell_layout.setSpacing(0)
        shell_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))

        card = QFrame()
        card.setObjectName("loginCard")
        card.setMaximumWidth(470)
        card.setMinimumWidth(390)
        self._shadow(card)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 26, 36, 26)
        card_layout.setSpacing(10)

        logo = RNDLogoWidget()
        card_layout.addWidget(logo)

        strap = QLabel("RUTAS   •   PERSONAS   •   RESULTADOS")
        strap.setAlignment(Qt.AlignCenter)
        strap.setStyleSheet(
            "color:#274E68; font-family:'Segoe UI'; font-size:10px; "
            "font-weight:600; letter-spacing:2px;"
        )
        card_layout.addWidget(strap)
        card_layout.addSpacing(12)

        lbl_usuario = QLabel("Usuario")
        lbl_usuario.setObjectName("sectionTitle")
        card_layout.addWidget(lbl_usuario)

        self.cboUsuario = CboUsuario()
        self.cboUsuario.setMinimumHeight(46)
        self.cboUsuario.setStyleSheet("""
            QComboBox {
                background: #F9FCFE;
                border: 1px solid #AFC7D8;
                border-radius: 10px;
                padding: 8px 12px;
                color: #16324A;
                font-family: "Segoe UI";
                font-size: 14px;
            }
            QComboBox:focus { border: 2px solid #18A8E0; }
        """)
        card_layout.addWidget(self.cboUsuario)

        lbl_pass = QLabel("Contraseña")
        lbl_pass.setObjectName("sectionTitle")
        card_layout.addWidget(lbl_pass)

        self.textPass = Password()
        self.textPass.setMinimumHeight(46)
        self.textPass.setPlaceholderText("Ingresá tu contraseña")
        self.textPass.setStyleSheet("""
            QLineEdit {
                background: #F9FCFE;
                border: 1px solid #AFC7D8;
                border-radius: 10px;
                padding: 8px 12px;
                color: #16324A;
                font-family: "Segoe UI";
                font-size: 14px;
            }
            QLineEdit:focus { border: 2px solid #18A8E0; }
        """)
        card_layout.addWidget(self.textPass)
        card_layout.addSpacing(10)

        self.btnIngresar = QPushButton("  Ingresar")
        self.btnIngresar.setObjectName("primaryButton")
        self.btnIngresar.setCursor(Qt.PointingHandCursor)
        self.btnIngresar.setDefault(True)
        card_layout.addWidget(self.btnIngresar)

        self.btnCerrar = QPushButton("Cerrar")
        self.btnCerrar.setObjectName("secondaryButton")
        self.btnCerrar.setCursor(Qt.PointingHandCursor)
        card_layout.addWidget(self.btnCerrar)

        card_layout.addSpacing(10)
        developer = QLabel("Desarrollado por")
        developer.setObjectName("supportText")
        developer.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(developer)

        vogel = QLabel("◉  V O G E L   CONSULTORÍA")
        vogel.setAlignment(Qt.AlignCenter)
        vogel.setStyleSheet(
            "color:#0B4A7E; font-family:'Segoe UI'; font-size:14px; font-weight:700;"
        )
        card_layout.addWidget(vogel)

        soluciones = QLabel("SOLUCIONES INTEGRALES  ·  vogelconsultoria.com.ar")
        soluciones.setObjectName("supportText")
        soluciones.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(soluciones)

        shell_layout.addWidget(card, 0, Qt.AlignCenter)
        shell_layout.addItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))

        root.addWidget(shell, 10)

        self.textPass.proximoWidget = self.btnIngresar

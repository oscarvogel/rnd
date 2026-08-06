# coding=utf-8
"""Tarjetas reutilizables del dashboard operativo (issue #4).

Hay dos tipos:

* ``TarjetaHero``: bloque principal, alta jerarquia visual, pensado
  para "Hojas de ruta del dia".
* ``TarjetaDashboard``: tarjeta secundaria (compacta) con titulo,
  valor principal, etiqueta y estados de carga/vacio/error.

Ambas exponen ``objectName`` estables para que el QSS global
(issue #5) las pueda tematizar.
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)


class _BaseTarjeta(QFrame):
    """Funcionalidad comun: estados y senal de click."""

    clicked = pyqtSignal()

    def __init__(self, titulo, parent=None):
        super().__init__(parent)
        self._titulo = titulo
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    # Qt reenvia mouseReleaseEvent como click generico
    def mousePressEvent(self, event):
        try:
            if event.button() == Qt.LeftButton:
                self.clicked.emit()
        except (TypeError, AttributeError):
            # En tests usamos mocks para ``event``; dejamos pasar
            # sin propagar para no romper la emulacion de clicks.
            return
        try:
            super().mousePressEvent(event)
        except TypeError:
            # ``super()`` requiere un ``QMouseEvent`` real; si nos
            # llega un mock en tests lo ignoramos.
            pass

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.clicked.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class TarjetaHero(_BaseTarjeta):
    """Bloque principal: alta jerarquia visual."""

    def __init__(self, titulo, parent=None):
        super().__init__(titulo, parent)
        self.setObjectName("dashboardTarjetaHero")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(8)

        self._etiqueta_titulo = QLabel(titulo)
        self._etiqueta_titulo.setObjectName("dashboardHeroTitulo")
        layout.addWidget(self._etiqueta_titulo)

        self._etiqueta_valor = QLabel("--")
        self._etiqueta_valor.setObjectName("dashboardHeroValor")
        self._etiqueta_valor.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._etiqueta_valor)

        self._etiqueta_detalle = QLabel("")
        self._etiqueta_detalle.setObjectName("dashboardHeroDetalle")
        layout.addWidget(self._etiqueta_detalle)

        self._etiqueta_estado = QLabel("")
        self._etiqueta_estado.setObjectName("dashboardHeroEstado")
        self._etiqueta_estado.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self._etiqueta_estado)

        self._barra = QProgressBar()
        self._barra.setObjectName("dashboardHeroBarra")
        self._barra.setRange(0, 0)  # Indeterminado mientras carga
        self._barra.setVisible(False)
        layout.addWidget(self._barra)

        self._boton_reintentar = QPushButton("Reintentar")
        self._boton_reintentar.setObjectName("dashboardHeroBotonReintentar")
        self._boton_reintentar.setProperty("role", "secondary")
        self._boton_reintentar.setVisible(False)
        layout.addWidget(self._boton_reintentar, alignment=Qt.AlignRight)

    def mostrar_cargando(self):
        self._etiqueta_valor.setText("...")
        self._etiqueta_detalle.setText("Cargando...")
        self._etiqueta_estado.setText("")
        self._barra.setVisible(True)
        self._boton_reintentar.setVisible(False)

    def mostrar_ok(self, cantidad, detalle=""):
        self._barra.setVisible(False)
        self._boton_reintentar.setVisible(False)
        self._etiqueta_valor.setText(str(cantidad))
        self._etiqueta_detalle.setText(detalle)
        self._etiqueta_estado.setText("OK")

    def mostrar_vacio(self, detalle=""):
        self._barra.setVisible(False)
        self._boton_reintentar.setVisible(False)
        self._etiqueta_valor.setText("0")
        self._etiqueta_detalle.setText(detalle or "Sin registros para hoy")
        self._etiqueta_estado.setText("Vacio")

    def mostrar_error(self, detalle=""):
        self._barra.setVisible(False)
        self._boton_reintentar.setVisible(True)
        self._etiqueta_valor.setText("--")
        self._etiqueta_detalle.setText(
            detalle or "No se pudo cargar el indicador"
        )
        self._etiqueta_estado.setText("Error")

    def conectar_reintentar(self, slot):
        self._boton_reintentar.clicked.connect(slot)


class TarjetaDashboard(_BaseTarjeta):
    """Tarjeta secundaria compacta."""

    def __init__(self, titulo, parent=None):
        super().__init__(titulo, parent)
        self.setObjectName("dashboardTarjetaSecundaria")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)

        self._etiqueta_titulo = QLabel(titulo)
        self._etiqueta_titulo.setObjectName("dashboardSecTitulo")
        layout.addWidget(self._etiqueta_titulo)

        self._etiqueta_valor = QLabel("--")
        self._etiqueta_valor.setObjectName("dashboardSecValor")
        self._etiqueta_valor.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self._etiqueta_valor)

        self._etiqueta_detalle = QLabel("")
        self._etiqueta_detalle.setObjectName("dashboardSecDetalle")
        layout.addWidget(self._etiqueta_detalle)

        self._barra = QProgressBar()
        self._barra.setObjectName("dashboardSecBarra")
        self._barra.setRange(0, 0)
        self._barra.setVisible(False)
        layout.addWidget(self._barra)

        self._boton_reintentar = QPushButton("Reintentar")
        self._boton_reintentar.setObjectName("dashboardSecBotonReintentar")
        self._boton_reintentar.setProperty("role", "secondary")
        self._boton_reintentar.setVisible(False)
        self._boton_reintentar.setCursor(Qt.PointingHandCursor)
        layout.addWidget(self._boton_reintentar, alignment=Qt.AlignRight)

    def mostrar_cargando(self):
        self._etiqueta_valor.setText("...")
        self._etiqueta_detalle.setText("Cargando...")
        self._barra.setVisible(True)
        self._boton_reintentar.setVisible(False)

    def mostrar_ok(self, cantidad, detalle=""):
        self._barra.setVisible(False)
        self._boton_reintentar.setVisible(False)
        self._etiqueta_valor.setText(str(cantidad))
        self._etiqueta_detalle.setText(detalle)

    def mostrar_vacio(self, detalle=""):
        self._barra.setVisible(False)
        self._boton_reintentar.setVisible(False)
        self._etiqueta_valor.setText("0")
        self._etiqueta_detalle.setText(detalle or "Sin registros")

    def mostrar_error(self, detalle=""):
        self._barra.setVisible(False)
        self._boton_reintentar.setVisible(True)
        self._etiqueta_valor.setText("--")
        self._etiqueta_detalle.setText(
            detalle or "No se pudo cargar el indicador"
        )

    def conectar_reintentar(self, slot):
        self._boton_reintentar.clicked.connect(slot)

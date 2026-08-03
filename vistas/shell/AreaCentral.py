# coding=utf-8
"""Area central del shell moderno de RND.

Es un ``QStackedWidget`` que permite incrustar el dashboard (issue #4)
y futuras vistas embebidas. Por ahora expone una pagina de
``placeholder`` para que la ventana principal pueda mostrar algo
significativo aun antes de tener contenido real.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class PaginaPlaceholder(QWidget):
    """Placeholder visible mientras no hay un modulo seleccionado."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("areaCentralPlaceholder")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        self.etiqueta = QLabel(
            "Bienvenido a RND.\n\n"
            "Selecciona una opcion del menu lateral para comenzar."
        )
        self.etiqueta.setObjectName("areaCentralPlaceholderTexto")
        self.etiqueta.setAlignment(Qt.AlignCenter)
        self.etiqueta.setWordWrap(True)
        layout.addWidget(self.etiqueta)


class AreaCentralView(QStackedWidget):
    """Area central que aloja dashboard y vistas embebidas."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("areaCentralShell")
        self._paginas = {}
        self.placeholder = PaginaPlaceholder()
        self.addWidget(self.placeholder)
        self._paginas["placeholder"] = self.placeholder
        self.setCurrentWidget(self.placeholder)

    def registrar_pagina(self, clave, widget):
        """Registra (o reemplaza) una pagina accesible por clave."""
        if clave in self._paginas:
            self.removeWidget(self._paginas[clave])
        self._paginas[clave] = widget
        self.addWidget(widget)
        return widget

    def mostrar(self, clave):
        if clave not in self._paginas:
            return False
        self.setCurrentWidget(self._paginas[clave])
        return True

    def mostrar_placeholder(self):
        self.setCurrentWidget(self.placeholder)

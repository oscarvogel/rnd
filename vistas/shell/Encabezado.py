# coding=utf-8
"""Encabezado superior del shell moderno de RND.

Muestra la identidad de la aplicacion, el usuario activo, el servidor
y la base en uso, el estado de conexion y la version. Incluye ademas
una accion de salida clara y accesible.

La apariencia definitiva (colores, tipografia, espaciado) se aplica
desde el QSS global (issue #5); aqui solo se define la estructura y
los objectName estables.
"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
)


class EncabezadoView(QFrame):
    """Barra superior con identidad, contexto de sesion y salida."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("encabezadoShell")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(16)

        self.brand = QLabel("Vogel Consultoría")
        self.brand.setObjectName("encabezadoBrand")
        layout.addWidget(self.brand)

        layout.addStretch(1)

        self._info_labels = {}
        for clave, object_name in (
            ("usuario", "encabezadoUsuario"),
            ("servidor", "encabezadoServidor"),
            ("estado", "encabezadoEstado"),
            ("version", "encabezadoVersion"),
        ):
            etiqueta = QLabel("")
            etiqueta.setObjectName(object_name)
            etiqueta.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(etiqueta)
            self._info_labels[clave] = etiqueta

        self.boton_salir = QPushButton("Salir")
        self.boton_salir.setObjectName("encabezadoBotonSalir")
        self.boton_salir.setCursor(Qt.PointingHandCursor)
        self.boton_salir.setToolTip("Cerrar la sesion y salir de RND")
        layout.addWidget(self.boton_salir)

        self.actualizar(usuario="", servidor="", base="",
                        estado="Sin sesion", version="")

    def actualizar(self, usuario="", servidor="", base="",
                   estado="Conectado", version=""):
        """Actualiza los textos visibles del encabezado."""
        self._info_labels["usuario"].setText(
            "Usuario: {}".format(usuario) if usuario else ""
        )
        partes = []
        if servidor:
            partes.append("Servidor: {}".format(servidor))
        if base:
            partes.append("Base: {}".format(base))
        self._info_labels["servidor"].setText(" | ".join(partes))
        self._info_labels["estado"].setText("Estado: {}".format(estado))
        self._info_labels["version"].setText(
            "v{}".format(version) if version else ""
        )

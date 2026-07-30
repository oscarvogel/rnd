"""Diálogos reutilizables para aplicaciones PyQt5.

El objetivo de este módulo es ofrecer una API pública simple y consistente
para mostrar mensajes y pedir confirmaciones sin repetir llamadas directas a
`QMessageBox` en cada pantalla.
"""

from PyQt5.QtWidgets import QMessageBox

DEFAULT_TITLE = "Sistema"


def show_info(message, title=DEFAULT_TITLE, parent=None):
    """Muestra un mensaje informativo."""
    return QMessageBox.information(parent, title, message)


def show_warning(message, title=DEFAULT_TITLE, parent=None):
    """Muestra una advertencia."""
    return QMessageBox.warning(parent, title, message)


def show_error(message, title=DEFAULT_TITLE, parent=None):
    """Muestra un mensaje de error."""
    return QMessageBox.critical(parent, title, message)


def ask_yes_no(message, title=DEFAULT_TITLE, parent=None, default=QMessageBox.No):
    """Pregunta Sí/No y devuelve True si el usuario elige Sí."""
    result = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.Yes | QMessageBox.No,
        default,
    )
    return result == QMessageBox.Yes


def confirm(message, title=DEFAULT_TITLE, parent=None):
    """Alias semántico para confirmaciones de acciones."""
    return ask_yes_no(message=message, title=title, parent=parent)


__all__ = [
    "DEFAULT_TITLE",
    "show_info",
    "show_warning",
    "show_error",
    "ask_yes_no",
    "confirm",
]

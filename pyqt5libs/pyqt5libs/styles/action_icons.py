"""Iconos vectoriales livianos para acciones de ABM.

Se generan con QPainter para evitar depender de archivos PNG/SVG externos y
mantener consistencia visual en la UI Fluent.
"""

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_DEFAULT_COLOR = "#374151"
_PRIMARY_COLOR = "#ffffff"
_DANGER_COLOR = "#b91c1c"


def _icon_pixmap(color=_DEFAULT_COLOR, size=20):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(size / 20, size / 20)
    pen = QPen(QColor(color), 1.8)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    return pixmap, painter


def _finish(pixmap, painter):
    painter.end()
    return QIcon(pixmap)


def icon_new(color=_PRIMARY_COLOR, size=20):
    pixmap, painter = _icon_pixmap(color, size)
    painter.drawLine(10, 4, 10, 16)
    painter.drawLine(4, 10, 16, 10)
    return _finish(pixmap, painter)


def icon_edit(color=_DEFAULT_COLOR, size=20):
    pixmap, painter = _icon_pixmap(color, size)
    painter.drawLine(6, 14, 14, 6)
    painter.drawLine(12, 4, 16, 8)
    painter.drawLine(5, 15, 4, 17)
    painter.drawLine(4, 17, 6, 16)
    return _finish(pixmap, painter)


def icon_remove(color=_DANGER_COLOR, size=20):
    pixmap, painter = _icon_pixmap(color, size)
    painter.drawLine(6, 7, 14, 7)
    painter.drawLine(8, 7, 8, 16)
    painter.drawLine(12, 7, 12, 16)
    painter.drawLine(7, 7, 7, 16)
    painter.drawLine(13, 7, 13, 16)
    painter.drawLine(8, 5, 12, 5)
    return _finish(pixmap, painter)


def icon_export(color=_DEFAULT_COLOR, size=20):
    pixmap, painter = _icon_pixmap(color, size)
    painter.drawRect(5, 5, 10, 11)
    painter.drawLine(8, 9, 12, 9)
    painter.drawLine(8, 12, 12, 12)
    painter.drawLine(10, 3, 10, 8)
    painter.drawLine(8, 6, 10, 8)
    painter.drawLine(12, 6, 10, 8)
    return _finish(pixmap, painter)


def icon_close(color=_DEFAULT_COLOR, size=20):
    pixmap, painter = _icon_pixmap(color, size)
    painter.drawLine(6, 6, 14, 14)
    painter.drawLine(14, 6, 6, 14)
    return _finish(pixmap, painter)


def icon_save(color=_PRIMARY_COLOR, size=20):
    pixmap, painter = _icon_pixmap(color, size)
    painter.drawRoundedRect(QRectF(5, 4, 10, 12), 1.5, 1.5)
    painter.drawLine(7, 4, 13, 4)
    painter.drawLine(7, 13, 13, 13)
    painter.drawLine(8, 7, 12, 7)
    return _finish(pixmap, painter)


def icon_cancel(color=_DEFAULT_COLOR, size=20):
    return icon_close(color, size)


def icon_refresh(color=_DEFAULT_COLOR, size=20):
    pixmap, painter = _icon_pixmap(color, size)
    painter.drawArc(QRectF(5, 5, 10, 10), 30 * 16, 280 * 16)
    painter.drawLine(14, 5, 15, 9)
    painter.drawLine(14, 5, 11, 6)
    return _finish(pixmap, painter)


def apply_action_icon(button, action_name):
    """Aplica un icono moderno a un botón si la acción es conocida."""
    icons = {
        "new": icon_new,
        "edit": icon_edit,
        "remove": icon_remove,
        "export": icon_export,
        "close": icon_close,
        "save": icon_save,
        "cancel": icon_cancel,
        "refresh": icon_refresh,
    }
    factory = icons.get(action_name)
    if not factory:
        return button
    icon_size = button.iconSize()
    size = max(icon_size.width(), icon_size.height(), 20)
    button.setIcon(factory(size=size))
    button.setIconSize(icon_size)
    return button


__all__ = [
    "apply_action_icon",
    "icon_new",
    "icon_edit",
    "icon_remove",
    "icon_export",
    "icon_close",
    "icon_save",
    "icon_cancel",
    "icon_refresh",
]

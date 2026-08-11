# coding=utf-8
"""Carga y aplica el tema QSS global de RND (issue #5).

El archivo de tema vive en ``temas/<nombre>.qss`` dentro de la carpeta
de inicio del sistema. Si el archivo no existe o no puede leerse, la
funcion retorna ``False`` y la aplicacion arranca con el estilo
default de Qt (fallback seguro, requisito de #5).
"""

import logging
import os

from pyqt5libs.pyqt5libs.utiles import ubicacion_sistema


log = logging.getLogger(__name__)

# Nombre del tema activo. El QSS vive en ``temas/vogel2026.qss``.
TEMA_ACTIVO = "vogel2026"

# Listado de temas disponibles para descubrimiento/utilidades externas.
TEMAS_DISPONIBLES = (TEMA_ACTIVO,)


def _ruta_qss(nombre):
    """Devuelve la ruta absoluta del QSS dentro de la carpeta de inicio."""
    return os.path.join(ubicacion_sistema(), "temas", "{}.qss".format(nombre))


def cargar_qss(nombre=TEMA_ACTIVO):
    """Lee el contenido del QSS desde el filesystem.

    Retorna ``""`` si el archivo no existe o no se puede leer
    (fallback seguro). Nunca lanza excepciones para no bloquear el
    inicio de la aplicacion.
    """
    ruta = _ruta_qss(nombre)
    if not os.path.exists(ruta):
        log.warning("Tema QSS '%s' no encontrado en %s", nombre, ruta)
        return ""
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            return archivo.read()
    except OSError as exc:
        log.warning("No se pudo leer el tema QSS '%s': %s", ruta, exc)
        return ""


def aplicar_tema(qapp, nombre=TEMA_ACTIVO):
    """Aplica el QSS al ``QApplication``.

    Retorna ``True`` si se aplico, ``False`` si se uso el fallback
    (sin tema). En cualquier caso la aplicacion sigue siendo
    utilizable: el objetivo es no bloquear el arranque si el QSS
    falta.
    """
    if qapp is None:
        return False
    qapp.setProperty("rnd_tema_global", False)
    qss = cargar_qss(nombre)
    if not qss:
        return False
    try:
        qapp.setStyleSheet(qss)
    except Exception as exc:  # pragma: no cover - defensivo
        log.warning("Fallo al aplicar QSS '%s': %s", nombre, exc)
        return False
    qapp.setProperty("rnd_tema_global", True)
    return True

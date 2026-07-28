"""Utilidades y componentes reutilizables para aplicaciones PyQt5.

Este paquete expone una API pública estable de forma gradual. Los módulos
históricos ubicados en `libs/` se mantienen por compatibilidad y serán
ordenados progresivamente en módulos públicos dentro de `pyqt5libs`.
"""

import importlib
import sys

__version__ = "0.1.0"
__all__ = ["__version__"]

# Compatibilidad con imports históricos usados por los módulos legacy:
# `pyqt5libs.pyqt5libs.*` apunta a este paquete y `pyqt5libs.libs.*` al
# paquete top-level `libs` cuando se ejecuta desde el checkout.
sys.modules.setdefault(__name__ + ".pyqt5libs", sys.modules[__name__])
try:
    sys.modules.setdefault(__name__ + ".libs", importlib.import_module("libs"))
except ModuleNotFoundError:
    pass

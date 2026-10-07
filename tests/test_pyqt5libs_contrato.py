# coding=utf-8
"""Contrato de la libreria compartida pyqt5libs (submodulo).

RND depende de pyqt5libs como submodulo, asi que ese codigo puede cambiar sin
que el repositorio de RND muestre un solo archivo modificado en el working tree.
Este archivo fija el comportamiento del que RND depende, para que una
regresion en la libreria falle acá y no en produccion.

El contrato es uno solo: `exec_()` tiene que devolver el codigo del dialogo
(Accepted / Rejected). Cuando devolvia None, todo el codigo que comparaba el
retorno con `Accepted` salia antes de guardar, sin error ni aviso. Ese fue el
motivo de que tildar los pallets y presionar Guardar no guardara nada en
Validar carga.
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QDialog


_QT_APP = QApplication.instance() or QApplication([])


def _dialogo():
    """Un formulario real de RND, derivado de VistaBase -> Formulario."""
    from vistas.ValidarCarga import ValidarCargaDialog

    return ValidarCargaDialog()


def test_exec_devuelve_accepted_cuando_se_acepta():
    dialogo = _dialogo()

    QTimer.singleShot(0, dialogo.accept)
    resultado = dialogo.exec_()

    assert resultado == QDialog.Accepted, (
        "exec_() devolvio {!r}. Si devuelve None, cualquier comparacion con "
        "Accepted corta el flujo antes de guardar.".format(resultado)
    )
    dialogo.Cerrar()


def test_exec_devuelve_rejected_cuando_se_cancela():
    dialogo = _dialogo()

    QTimer.singleShot(0, dialogo.reject)
    resultado = dialogo.exec_()

    assert resultado == QDialog.Rejected, (
        "exec_() devolvio {!r} en vez de Rejected.".format(resultado)
    )
    dialogo.Cerrar()


def test_exec_no_devuelve_none():
    """Guardia explicita: el sintoma del bug era exactamente None."""
    dialogo = _dialogo()

    QTimer.singleShot(0, dialogo.accept)
    assert dialogo.exec_() is not None

    dialogo.Cerrar()


def test_result_y_exec_coinciden():
    """`result()` y el retorno de `exec_()` tienen que decir lo mismo.

    El controlador de Validar carga lee `result()` porque es la API de Qt que
    no depende de como este reescrito `exec_()`. El test obliga a que las dos
    coincidan, para que cambiar de una a otra no altere el resultado.
    """
    dialogo = _dialogo()

    QTimer.singleShot(0, dialogo.accept)
    desde_exec = dialogo.exec_()

    assert desde_exec == dialogo.result() == QDialog.Accepted
    dialogo.Cerrar()
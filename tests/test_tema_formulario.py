# coding=utf-8
"""Tests de regresion del conflicto de temas en formularios (issue #15).

El estilo de RND se aplica a nivel de QApplication. Los formularios no deben
volver a cargar CSS legacy por su cuenta, aun cuando no exista QSS global; en
ese caso deben conservar el estilo nativo de Qt.
"""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from pyqt5libs.pyqt5libs.Formulario import Formulario


class _AppFixture:
    _app = None

    @classmethod
    def get(cls):
        if cls._app is None:
            cls._app = QApplication.instance() or QApplication([])
        return cls._app


class EstablecerTemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = _AppFixture.get()

    def setUp(self):
        self.app.setStyleSheet("")
        self.app.setProperty("rnd_tema_global", False)
        self.addCleanup(lambda: self.app.setProperty("rnd_tema_global", False))

    def test_con_stylesheet_global_no_aplica_css_del_formulario(self):
        self.app.setStyleSheet("/* Vogel 2026 */ QDialog { background-color: #F8FAFC; }")
        self.app.setProperty("rnd_tema_global", True)
        form = Formulario()
        try:
            self.assertEqual(
                form.styleSheet(),
                "",
                "Con tema global activo, el formulario no debe pisarlo con un CSS propio",
            )
        finally:
            form.close()

    def test_sin_tema_global_no_aplica_css_legacy(self):
        self.app.setProperty("rnd_tema_global", False)
        with patch.object(Formulario, "setStyleSheet", create=True) as mock_set:
            form = Formulario()
            form.close()
            mock_set.assert_not_called()

    def test_no_crashea_sin_qapplication(self):
        with patch.object(QApplication, "instance", return_value=None):
            form = Formulario()
            form.close()


if __name__ == "__main__":
    unittest.main()

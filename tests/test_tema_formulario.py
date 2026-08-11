# coding=utf-8
"""Tests de regresion del conflicto de temas en formularios (issue del tema).

Historia:
  El formulario hereda de ``pyqt5libs.Formulario`` y su ``EstablecerTema()``
  leia el parametro ``TEMA`` de la DB y aplicaba un CSS viejo por-formulario
  (qdark/darkblue, fondo azul oscuro). Ese fallback podia activarse cuando el
  QSS global no estaba disponible y dejaba el formulario ilegible.

  Fix: ``EstablecerTema`` ya no aplica CSS legado; con o sin QSS global, el
  formulario hereda el tema de QApplication o conserva el estilo nativo de Qt.
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

    def test_con_stylesheet_global_no_aplica_css_del_formulario(self):
        # Simula el arranque real: main.py aplico vogel2026.qss a la app.
        self.app.setStyleSheet("/* Vogel 2026 */ QDialog { background-color: #F8FAFC; }")
        form = Formulario()
        try:
            self.assertEqual(
                form.styleSheet(),
                "",
                "Con tema global activo, el formulario NO debe pisarlo con un CSS propio",
            )
        finally:
            form.close()

    def test_sin_stylesheet_global_no_aplica_css_legacy(self):
        # Sin tema global, el formulario debe conservar el estilo nativo de
        # Qt. El fallback oscuro leido desde TEMA es la causa del contraste
        # roto y no debe volver a aplicarse automaticamente.
        with patch.object(
            Formulario, "setStyleSheet", create=True
        ) as mock_set:
            form = Formulario()
            form.close()
            mock_set.assert_not_called()

    def test_no_crashea_sin_qapplication(self):
        with patch.object(QApplication, "instance", return_value=None):
            form = Formulario()
            form.close()


if __name__ == "__main__":
    unittest.main()

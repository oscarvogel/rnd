# coding=utf-8
"""Tests de regresion del conflicto de temas en formularios (issue del tema).

Historia:
  El formulario hereda de ``pyqt5libs.Formulario`` y su ``EstablecerTema()``
  leia el parametro ``TEMA`` de la DB y aplicaba un CSS viejo por-formulario
  (qdark/darkblue, fondo azul oscuro). Ese fallback podia activarse cuando el
  QSS global no estaba disponible y dejaba el formulario ilegible.

  Fix: cuando ``main.py`` aplica el tema global, marca la QApplication con la
  propiedad ``rnd_tema_global``. ``Formulario`` usa esa propiedad para evitar
  aplicar un stylesheet propio y pisar el QSS global.

  Estos tests no deben depender de una conexion MySQL real. El parametro TEMA
  se simula para mantener la prueba enfocada exclusivamente en el comportamiento
  visual del formulario.
"""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from modelos.ParametrosSistema import ParamSist
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
        self.param_tema = patch.object(
            ParamSist,
            "ObtenerParametro",
            return_value="forestal_moderno.css",
        )
        self.param_tema.start()
        self.addCleanup(self.param_tema.stop)
        self.addCleanup(lambda: self.app.setProperty("rnd_tema_global", False))

    def test_con_stylesheet_global_no_aplica_css_del_formulario(self):
        # Simula el arranque real: main.py aplica el QSS y marca que existe
        # un tema global activo para que los formularios no lo pisen.
        self.app.setStyleSheet("/* Vogel 2026 */ QDialog { background-color: #F8FAFC; }")
        self.app.setProperty("rnd_tema_global", True)
        form = Formulario()
        try:
            self.assertEqual(
                form.styleSheet(),
                "",
                "Con tema global activo, el formulario NO debe pisarlo con un CSS propio",
            )
        finally:
            form.close()

    def test_sin_tema_global_puede_aplicar_tema_configurado(self):
        # Sin el flag global, Formulario mantiene su comportamiento legacy:
        # puede resolver y aplicar el tema configurado localmente.
        self.app.setProperty("rnd_tema_global", False)
        with patch.object(Formulario, "setStyleSheet", create=True) as mock_set:
            form = Formulario()
            form.close()
            mock_set.assert_called_once()

    def test_no_crashea_sin_qapplication(self):
        with patch.object(QApplication, "instance", return_value=None):
            form = Formulario()
            form.close()


if __name__ == "__main__":
    unittest.main()

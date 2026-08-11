# coding=utf-8
"""Tests del tema QSS moderno de RND (issue #5).

Cubre tres aspectos:

* **Carga y aplicacion**: el QSS existe, se lee y se aplica al
  ``QApplication`` sin lanzar excepciones.
* **Fallback seguro**: si el archivo falta, la aplicacion sigue
  funcionando y la funcion retorna ``False``.
* **Empaquetado estatico**: el QSS y la carpeta ``temas/`` quedan
  referenciados en ``main.spec`` e ``installer/RND.iss`` para que
  el ejecutable distribuido los incluya.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

# Forzar plataforma offscreen antes de importar PyQt5 widgets.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtGui import QColor, QImage, QPalette
from PyQt5.QtWidgets import QApplication, QWidget


ROOT = Path(__file__).resolve().parents[1]


class _AppFixture:
    """Crea un ``QApplication`` una sola vez para los tests de UI."""

    _app = None

    @classmethod
    def get(cls):
        if cls._app is None:
            cls._app = QApplication.instance() or QApplication([])
        return cls._app


class CargaQSSTests(unittest.TestCase):
    """Carga, validacion y aplicacion del QSS."""

    @classmethod
    def setUpClass(cls):
        cls.app = _AppFixture.get()

    def setUp(self):
        # Forzamos ``ubicacion_sistema()`` al directorio del proyecto
        # para que ``utiles.tema`` encuentre el QSS en los tests.
        # Patcheamos en el modulo que la importa (``utiles.tema``)
        # porque ahi queda el nombre vinculado.
        from utiles import tema
        self._patcher = patch.object(
            tema, "ubicacion_sistema", return_value=str(ROOT)
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_archivo_qss_existe_y_no_esta_vacio(self):
        from utiles.tema import TEMA_ACTIVO, _ruta_qss
        ruta = Path(_ruta_qss(TEMA_ACTIVO))
        self.assertTrue(
            ruta.is_file(),
            "No existe el QSS {}".format(ruta),
        )
        contenido = ruta.read_text(encoding="utf-8")
        self.assertGreater(len(contenido), 100)
        # El QSS debe declarar objectNames usados por el shell (#3)
        for object_name in (
            "encabezadoShell",
            "barraLateralShell",
            "menuLateralArbol",
            "areaCentralShell",
            "dashboardRoot",
            "dashboardContenido",
            "dashboardCabecera",
            "dashboardTitulo",
            "dashboardSubtitulo",
            "dashboardBotonRecargar",
            "dashboardTarjetaHero",
            "dashboardHeroTitulo",
            "dashboardHeroValor",
            "dashboardTarjetaSecundaria",
            "dashboardSecTitulo",
            "dashboardSecValor",
        ):
            with self.subTest(object_name=object_name):
                self.assertIn(object_name, contenido)

    def test_cargar_qss_retorna_contenido(self):
        from utiles.tema import TEMA_ACTIVO, cargar_qss
        contenido = cargar_qss(TEMA_ACTIVO)
        self.assertIsInstance(contenido, str)
        self.assertGreater(len(contenido), 0)

    def test_aplicar_tema_retorna_true_y_aplica_qss(self):
        from utiles.tema import TEMA_ACTIVO, aplicar_tema
        exito = aplicar_tema(self.app, TEMA_ACTIVO)
        self.assertTrue(exito)
        # El QSS queda en el stylesheet de la app
        self.assertIn("Vogel 2026", self.app.styleSheet())
        self.assertTrue(self.app.property("rnd_tema_global"))

    def test_aplicar_tema_usa_nombre_por_defecto(self):
        # No pasamos nombre -> debe usar TEMA_ACTIVO
        from utiles.tema import aplicar_tema
        exito = aplicar_tema(self.app)
        self.assertTrue(exito)

    def test_aplicar_tema_con_qapp_none_no_falla(self):
        from utiles.tema import aplicar_tema
        self.assertFalse(aplicar_tema(None))

    def test_carga_falla_si_archivo_no_existe(self):
        from utiles import tema
        with patch.object(tema, "_ruta_qss",
                          return_value=str(ROOT / "temas" / "_no_existe.qss")):
            contenido = tema.cargar_qss("inexistente")
        self.assertEqual(contenido, "")

    def test_aplicar_falla_y_retorna_false_si_no_hay_qss(self):
        from utiles import tema
        with patch.object(tema, "_ruta_qss",
                          return_value=str(ROOT / "temas" / "_no_existe.qss")):
            exito = tema.aplicar_tema(self.app, "inexistente")
        self.assertFalse(exito)
        # La app no queda con un stylesheet vacio inducido por la falla
        self.assertNotIn("Vogel 2026", self.app.styleSheet())

    def test_aplicar_tolera_excepcion_al_setStyleSheet(self):
        from utiles import tema
        with patch.object(tema, "cargar_qss", return_value="/* ok */"), \
             patch.object(self.app, "setStyleSheet",
                          side_effect=RuntimeError("boom")):
            exito = tema.aplicar_tema(self.app, "vogel2026")
        self.assertFalse(exito)


class PackagingEstaticoTests(unittest.TestCase):
    """Verifica que el QSS queda empaquetado en el instalador."""

    def test_pyinstaller_spec_incluye_temas(self):
        spec = (ROOT / "main.spec").read_text(encoding="utf-8")
        self.assertIn("('temas', 'temas')", spec)

    def test_qss_presente_en_carpeta_temas(self):
        # El recurso debe existir en el filesystem para que PyInstaller
        # lo empaquete; lo verificamos ademas del spec.
        qss = ROOT / "temas" / "vogel2026.qss"
        self.assertTrue(qss.is_file(), "Falta {}".format(qss))

    def test_inno_setup_incluye_carpeta_temas_via_dist(self):
        # El installer toma ``..\dist\main\*``, que incluye ``temas/``
        # porque main.spec lo declara. Verificamos que el bloque
        # ``[Files]`` no excluye la carpeta.
        installer = (ROOT / "installer" / "RND.iss").read_text(
            encoding="utf-8"
        )
        self.assertIn('Source: "..\\dist\\main\\*"', installer)


class SmokeVisualTests(unittest.TestCase):
    """Smoke visual: el shell completo se construye con el QSS aplicado.

    Complementa la lista de comprobacion visual de pantallas
    representativas de #5: si la ventana principal no rompe al
    aplicar el QSS, el resto de los modulos (que reutilizan los
    mismos selectores) tampoco deberia.
    """

    @classmethod
    def setUpClass(cls):
        cls.app = _AppFixture.get()

    def setUp(self):
        from utiles import tema
        self._patcher = patch.object(
            tema, "ubicacion_sistema", return_value=str(ROOT)
        )
        self._patcher.start()
        # Aplicamos el tema antes de construir la vista.
        from utiles.tema import aplicar_tema
        aplicar_tema(self.app)

    def tearDown(self):
        self._patcher.stop()

    def test_shell_con_qss_se_construye_sin_excepciones(self):
        from unittest.mock import patch
        with patch("modelos.Formula.MenuLateral.Cabeceras") as cab, \
             patch("modelos.Accesos.Acceso.AccesoUsuario") as acc:
            cab.return_value = []
            acc.return_value = True
            from vistas.Main import MainView
            view = MainView()
            view.actualizar_encabezado("u", "s", "b", "Conectado", "1.0")
            view.showMaximized()
            try:
                # El QSS debe estar aplicado
                self.assertIn("Vogel 2026", self.app.styleSheet())
            finally:
                view.close()
                view.deleteLater()

    def test_formularios_no_sobrescriben_el_tema_global(self):
        from pyqt5libs.pyqt5libs.Formulario import Formulario

        self.app.setProperty("rnd_tema_global", True)
        with patch.object(Formulario, "EstablecerTema") as tema_local:
            formulario = Formulario()
            try:
                tema_local.assert_not_called()
            finally:
                formulario.close()
                formulario.deleteLater()

    def test_formulario_legacy_renderiza_fondo_claro_con_tema_global(self):
        from pyqt5libs.pyqt5libs.Formulario import Formulario

        formulario = Formulario()
        formulario.resize(320, 160)
        formulario.show()
        self.app.processEvents()
        try:
            captura = formulario.grab().toImage().convertToFormat(
                QImage.Format_RGB32
            )
            self.assertEqual(
                captura.pixelColor(5, 5).name().lower(),
                "#f8fafc",
            )
        finally:
            formulario.close()
            formulario.deleteLater()

    def test_widget_base_no_expone_la_paleta_oscura_del_sistema(self):
        """El tema debe pintar su fondo, aunque Windows use modo oscuro.

        Un ``background-color: transparent`` global deja que una paleta
        nativa oscura reaparezca en formularios y contenedores sin un
        selector particular. Esa es exactamente la regresion que se ve en
        los formularios legacy.
        """
        paleta_original = self.app.palette()
        paleta_oscura = QPalette(paleta_original)
        paleta_oscura.setColor(QPalette.Window, QColor("#000000"))
        self.app.setPalette(paleta_oscura)

        widget = QWidget()
        widget.resize(240, 120)
        widget.show()
        self.app.processEvents()
        try:
            captura = widget.grab().toImage().convertToFormat(
                QImage.Format_RGB32
            )
            self.assertEqual(
                captura.pixelColor(5, 5).name().lower(),
                "#f8fafc",
            )
        finally:
            widget.close()
            widget.deleteLater()
            self.app.setPalette(paleta_original)


if __name__ == "__main__":
    unittest.main()

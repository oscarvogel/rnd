# coding=utf-8
"""Tests del shell moderno de RND (issue #3).

Dos niveles de cobertura:

* **Smoke** de la ventana principal: ``MainView`` se construye sin
  excepciones y expone los tres componentes del shell (encabezado,
  barra lateral y area central). Verifica tambien que el ``QToolBox``
  del shell anterior ya no se crea.
* **Permisos**: la barra lateral filtra los items segun
  ``Acceso.AccesoUsuario`` y oculta las secciones vacias.

Los tests mockean las consultas a la base de datos porque no
requerimos MySQL para validar la logica de UI del shell.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

# Forzar plataforma offscreen antes de importar PyQt5 widgets.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QFrame, QStackedWidget, QTreeWidget


class _StubCabecera:
    """Suplanta un registro de ``MenuLateral`` usado como cabecera."""

    def __init__(self, id_, nombre):
        self.id = id_
        self.nombre = nombre


class _StubItem:
    """Suplanta un registro de ``MenuLateral`` usado como item hijo."""

    def __init__(self, id_, nombre, for_id=1, for_imag="", for_nomb=""):
        self.id = id_
        self.nombre = nombre
        self.for_id = MagicMock()
        self.for_id.for_id = for_id
        self.for_id.for_imag = for_imag
        self.for_id.for_nomb = for_nomb


class ShellModernoSmokeTests(unittest.TestCase):
    """Verifica que ``MainView`` monta el shell moderno correctamente."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.cabeceras_patcher = patch(
            "modelos.Formula.MenuLateral.Cabeceras"
        )
        self.acceso_patcher = patch(
            "modelos.Accesos.Acceso.AccesoUsuario"
        )
        self.mock_cabeceras = self.cabeceras_patcher.start()
        self.mock_acceso = self.acceso_patcher.start()
        self.mock_cabeceras.return_value = []
        self.mock_acceso.return_value = True

    def tearDown(self):
        self.cabeceras_patcher.stop()
        self.acceso_patcher.stop()

    def test_main_view_compone_shell_sin_toolbox(self):
        from vistas.Main import MainView

        view = MainView()

        # Los tres componentes del shell existen
        self.assertIsInstance(view.encabezado, QFrame)
        self.assertIsInstance(view.barra_lateral, QFrame)
        self.assertIsInstance(view.area_central, QStackedWidget)

        # El QToolBox del shell anterior ya no se crea
        self.assertFalse(hasattr(view, "toolBox"))

        # La ventana se maximiza sin geometrias absolutas
        self.assertTrue(view.isMaximized())

        view.close()
        view.deleteLater()

    def test_encabezado_expone_etiquetas_y_boton_salir(self):
        from vistas.Main import MainView

        view = MainView()
        enc = view.encabezado
        self.assertEqual(enc.brand.text(), "Vogel Consultoría")
        self.assertEqual(enc.boton_salir.text(), "Salir")
        for clave in ("usuario", "servidor", "estado", "version"):
            self.assertIn(clave, enc._info_labels)
        view.close()
        view.deleteLater()

    def test_area_central_arranca_con_placeholder(self):
        from vistas.Main import MainView

        view = MainView()
        try:
            self.assertTrue(view.area_central.mostrar("placeholder"))
            self.assertFalse(view.area_central.mostrar("inexistente"))
        finally:
            view.close()
            view.deleteLater()

    def test_actualizar_encabezado_refleja_los_valores(self):
        from vistas.Main import MainView

        view = MainView()
        try:
            view.actualizar_encabezado(
                usuario="oscar",
                servidor="srv",
                base="rnd",
                estado="Conectado",
                version="1.2.3",
            )
            enc = view.encabezado
            self.assertEqual(enc._info_labels["usuario"].text(), "Usuario: oscar")
            self.assertIn("Servidor: srv", enc._info_labels["servidor"].text())
            self.assertIn("Base: rnd", enc._info_labels["servidor"].text())
            self.assertEqual(enc._info_labels["estado"].text(), "Estado: Conectado")
            self.assertEqual(enc._info_labels["version"].text(), "v1.2.3")
        finally:
            view.close()
            view.deleteLater()

    def test_seleccionar_menu_resuelve_controladores_heredados(self):
        """El nuevo shell debe conservar los destinos guardados en Formula."""
        from vistas.Main import MainView
        from modelos.ParametrosSistema import ParamSist

        controlador = MagicMock()
        with patch.object(
            ParamSist,
            "ObtenerParametro",
            return_value="ARG",
        ), patch(
                "controladores.ABMClientes.ABMClientesController",
                return_value=controlador,
        ):
            view = MainView()
            try:
                view.SeleccionaMenu(
                    1,
                    "ABMClientes.ABMClientesController()",
                )
                controlador.run.assert_called_once_with()
            finally:
                view.close()
                view.deleteLater()


class BarraLateralPermisosTests(unittest.TestCase):
    """Filtrado del menu lateral por permisos."""

    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.cabeceras_patcher = patch(
            "modelos.Formula.MenuLateral.Cabeceras"
        )
        self.acceso_patcher = patch(
            "modelos.Accesos.Acceso.AccesoUsuario"
        )
        self.select_patcher = patch(
            "modelos.Formula.MenuLateral.select"
        )
        self.mock_cabeceras = self.cabeceras_patcher.start()
        self.mock_acceso = self.acceso_patcher.start()
        self.mock_select = self.select_patcher.start()

    def tearDown(self):
        self.cabeceras_patcher.stop()
        self.acceso_patcher.stop()
        self.select_patcher.stop()

    def _cargar(self, cabeceras, items, permiso_por_id):
        self.mock_cabeceras.return_value = cabeceras
        mock_chain = MagicMock()
        mock_chain.join.return_value.where.return_value.order_by.return_value = (
            items
        )
        self.mock_select.return_value = mock_chain
        self.mock_acceso.side_effect = lambda **kw: permiso_por_id.get(
            kw.get("for_id"), False
        )

        from vistas.shell.BarraLateral import BarraLateralView
        barra = BarraLateralView()
        visibles = barra.cargar(usu_id=1)
        return barra, visibles

    def test_solo_se_muestran_items_con_permiso(self):
        cab_ventas = _StubCabecera(1, "Ventas")
        item_clientes = _StubItem(1, "Clientes", for_id=10)
        item_proveedores = _StubItem(2, "Proveedores", for_id=20)
        barra, visibles = self._cargar(
            cabeceras=[cab_ventas],
            items=[item_clientes, item_proveedores],
            permiso_por_id={10: True, 20: False},
        )
        self.assertEqual(visibles, 1)
        self.assertIsNotNone(barra.item_por_menu_id(1))
        self.assertIsNone(barra.item_por_menu_id(2))
        barra.close()
        barra.deleteLater()

    def test_seccion_sin_items_visibles_se_oculta(self):
        cab_vacia = _StubCabecera(1, "Vacia")
        item = _StubItem(1, "A", for_id=10)
        barra, visibles = self._cargar(
            cabeceras=[cab_vacia],
            items=[item],
            permiso_por_id={10: False},
        )
        self.assertEqual(visibles, 0)
        padre = barra.arbol.topLevelItem(0)
        self.assertTrue(padre.isHidden())
        barra.close()
        barra.deleteLater()

    def test_usuario_admin_ve_todos_los_items(self):
        cab = _StubCabecera(1, "Todo")
        item1 = _StubItem(1, "A", for_id=10)
        item2 = _StubItem(2, "B", for_id=20)
        # Cuando todos los permisos son True
        barra, visibles = self._cargar(
            cabeceras=[cab],
            items=[item1, item2],
            permiso_por_id={10: True, 20: True},
        )
        self.assertEqual(visibles, 2)
        self.assertFalse(barra.arbol.topLevelItem(0).isHidden())
        barra.close()
        barra.deleteLater()

    def test_arbol_es_qtreewidget_con_qframe_como_contenedor(self):
        cab = _StubCabecera(1, "X")
        item = _StubItem(1, "A", for_id=10)
        barra, _ = self._cargar(
            cabeceras=[cab],
            items=[item],
            permiso_por_id={10: True},
        )
        self.assertIsInstance(barra, QFrame)
        self.assertIsInstance(barra.arbol, QTreeWidget)
        self.assertEqual(barra.arbol.objectName(), "menuLateralArbol")
        barra.close()
        barra.deleteLater()


if __name__ == "__main__":
    unittest.main()

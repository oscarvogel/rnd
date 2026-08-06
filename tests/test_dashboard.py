# coding=utf-8
"""Tests del dashboard operativo de RND (issue #4).

Cubre:

* **Permisos**: si el usuario no tiene acceso al modulo, el
  servicio retorna ``sin_permiso`` y la tarjeta correspondiente
  queda oculta (sin ejecutar query ni revelar el conteo).
* **Fechas**: la fecha por default es ``date.today()``; se puede
  fijar una fecha explicita.
* **Estados**: ok, vacio y error se reflejan en la tarjeta.
* **Errores**: una excepcion en la query no rompe la carga del
  dashboard; la tarjeta muestra el fallback.
* **Navegacion**: las tarjetas emiten la clave de navegacion
  esperada al hacer click.
"""

import os
import unittest
from datetime import date
from unittest.mock import MagicMock, patch

# Forzar plataforma offscreen antes de importar PyQt5 widgets.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication


class _AppFixture:
    _app = None

    @classmethod
    def get(cls):
        if cls._app is None:
            cls._app = QApplication.instance() or QApplication([])
        return cls._app


def _prevenir_conexion_mysql():
    """Evita que el cuerpo de las clases de ``modelos`` abra MySQL.

    ``modelos.Proveedores.Proveedor`` ejecuta
    ``ParamSist.ObtenerParametro(...)`` en el class body, lo cual
    intenta conectar a la base al solo importar. Para que los
    tests no dependan de un server MySQL accesible, parcheamos
    ese metodo a devolver "ARG" antes de cualquier import de
    modelos. Idem para cualquier otra llamada a la BD en el
    class body.
    """
    from modelos import ParametrosSistema
    # patch a nivel modulo ya que ``ObtenerParametro`` se llama
    # desde class body, no desde la instancia.
    return patch.object(
        ParametrosSistema.ParamSist,
        "ObtenerParametro",
        return_value="ARG",
    )


class ServiciosDashboardTests(unittest.TestCase):
    """Capa de datos del dashboard: permisos, fechas y errores."""

    _p_param = None

    @classmethod
    def setUpClass(cls):
        # Se aplica una vez por clase para mantener el patch
        # durante todos los tests (importar el modulo tambien
        # reabre la conexion).
        cls._p_param = _prevenir_conexion_mysql()
        cls._p_param.start()

    @classmethod
    def tearDownClass(cls):
        if cls._p_param is not None:
            cls._p_param.stop()

    def setUp(self):
        # Importamos las clases para patchearlas via ``patch.object``;
        # la ruta dotted completa (``modelos.HojaRuta.HojaDeRuta.select``)
        # falla porque ``HojaRuta`` es un submodulo y no un atributo
        # directo del paquete ``modelos``.
        from modelos.Accesos import Acceso
        from modelos.HojaRuta import HojaDeRuta
        self._p_perm = patch.object(
            Acceso, "ValidaMenu", return_value=True
        )
        self._p_hoja_select = patch.object(HojaDeRuta, "select")
        self._p_venc = patch(
            "vistas.dashboard.servicios.get_vencimientos_proximos"
        )
        self.mock_perm = self._p_perm.start()
        self.mock_hoja = self._p_hoja_select.start()
        self.mock_venc = self._p_venc.start()

    def tearDown(self):
        self._p_perm.stop()
        self._p_hoja_select.stop()
        self._p_venc.stop()

    def test_hojas_ruta_del_dia_sin_permiso_retorna_sin_permiso(self):
        self.mock_perm.return_value = False
        from vistas.dashboard import servicios
        resultado = servicios.hojas_ruta_del_dia(usu_id=1, fecha=date(2026, 1, 1))
        self.assertEqual(resultado.estado, "sin_permiso")
        self.assertFalse(resultado.es_visible)
        # No se ejecuto la query
        self.mock_hoja.assert_not_called()

    def test_hojas_ruta_del_dia_ok_con_cantidad(self):
        # Mock count() -> 7
        mock_query = MagicMock()
        mock_query.where.return_value.count.return_value = 7
        self.mock_hoja.return_value = mock_query
        from vistas.dashboard import servicios
        resultado = servicios.hojas_ruta_del_dia(
            usu_id=1, fecha=date(2026, 1, 1)
        )
        self.assertEqual(resultado.estado, "ok")
        self.assertEqual(resultado.cantidad, 7)
        self.assertEqual(resultado.fecha, date(2026, 1, 1))

    def test_hojas_ruta_del_dia_vacio(self):
        mock_query = MagicMock()
        mock_query.where.return_value.count.return_value = 0
        self.mock_hoja.return_value = mock_query
        from vistas.dashboard import servicios
        resultado = servicios.hojas_ruta_del_dia(usu_id=1, fecha=date.today())
        self.assertEqual(resultado.estado, "vacio")
        self.assertTrue(resultado.es_vacio)
        self.assertFalse(resultado.es_ok)

    def test_hojas_ruta_del_dia_captura_excepcion_como_error(self):
        mock_query = MagicMock()
        mock_query.where.return_value.count.side_effect = RuntimeError("BD caida")
        self.mock_hoja.return_value = mock_query
        from vistas.dashboard import servicios
        resultado = servicios.hojas_ruta_del_dia(usu_id=1)
        self.assertEqual(resultado.estado, "error")
        self.assertTrue(resultado.es_error)
        self.assertIn("BD caida", resultado.detalle)

    def test_vencimientos_sin_permiso_no_ejecuta_query(self):
        self.mock_perm.return_value = False
        from vistas.dashboard import servicios
        resultado = servicios.vencimientos_proximos(usu_id=1)
        self.assertEqual(resultado.estado, "sin_permiso")
        self.mock_venc.assert_not_called()

    def test_vencimientos_ok(self):
        self.mock_venc.return_value = [MagicMock(), MagicMock(), MagicMock()]
        from vistas.dashboard import servicios
        resultado = servicios.vencimientos_proximos(usu_id=1)
        self.assertEqual(resultado.estado, "ok")
        self.assertEqual(resultado.cantidad, 3)

    def test_vencimientos_error_se_captura(self):
        self.mock_venc.side_effect = RuntimeError("timeout")
        from vistas.dashboard import servicios
        resultado = servicios.vencimientos_proximos(usu_id=1)
        self.assertEqual(resultado.estado, "error")
        self.assertIn("timeout", resultado.detalle)


class DashboardViewTests(unittest.TestCase):
    """UI del dashboard: tarjetas, estados, navegacion y errores."""

    @classmethod
    def setUpClass(cls):
        cls.app = _AppFixture.get()
        # Mismo workaround que ServiciosDashboardTests para que
        # el import de los modelos no abra MySQL.
        cls._p_param = _prevenir_conexion_mysql()
        cls._p_param.start()

    @classmethod
    def tearDownClass(cls):
        if cls._p_param is not None:
            cls._p_param.stop()

    def setUp(self):
        # Forzamos "sin permiso" para HojaDeRuta y Equipos; los
        # tests especificos lo cambian.
        from modelos.Accesos import Acceso
        from modelos.HojaRuta import HojaDeRuta
        from vistas.dashboard import servicios
        self._p_perm = patch.object(Acceso, "ValidaMenu", return_value=False)
        self._p_hoja = patch.object(HojaDeRuta, "select")
        self._p_venc = patch.object(
            servicios, "get_vencimientos_proximos"
        )
        self.mock_perm = self._p_perm.start()
        self.mock_hoja = self._p_hoja.start()
        self.mock_venc = self._p_venc.start()

    def tearDown(self):
        self._p_perm.stop()
        self._p_hoja.stop()
        self._p_venc.stop()

    def test_sin_permisos_todas_las_tarjetas_quedan_ocultas(self):
        from vistas.dashboard.dashboard_view import DashboardView
        d = DashboardView(usu_id=1)
        d.cargar()
        # ``isVisible`` requiere que los padres esten mostrados;
        # sin ventana padre usamos ``isHidden`` que refleja la
        # decision explicita de la tarjeta.
        self.assertTrue(d.hero.isHidden())
        self.assertTrue(d.tarjeta_vencimientos.isHidden())
        d.deleteLater()

    def test_hero_visible_con_ok_si_hay_permiso_y_datos(self):
        self.mock_perm.return_value = True
        mock_q = MagicMock()
        mock_q.where.return_value.count.return_value = 5
        self.mock_hoja.return_value = mock_q
        from vistas.dashboard.dashboard_view import DashboardView
        d = DashboardView(usu_id=1)
        d.cargar()
        self.assertFalse(d.hero.isHidden())
        self.assertEqual(d.hero._etiqueta_valor.text(), "5")
        self.assertEqual(d.hero._etiqueta_estado.text(), "OK")
        d.deleteLater()

    def test_hero_muestra_estado_vacio(self):
        self.mock_perm.return_value = True
        mock_q = MagicMock()
        mock_q.where.return_value.count.return_value = 0
        self.mock_hoja.return_value = mock_q
        from vistas.dashboard.dashboard_view import DashboardView
        d = DashboardView(usu_id=1)
        d.cargar()
        self.assertFalse(d.hero.isHidden())
        self.assertEqual(d.hero._etiqueta_valor.text(), "0")
        self.assertEqual(d.hero._etiqueta_estado.text(), "Vacio")
        d.deleteLater()

    def test_hero_muestra_estado_error_y_boton_reintentar(self):
        self.mock_perm.return_value = True
        mock_q = MagicMock()
        mock_q.where.return_value.count.side_effect = RuntimeError("boom")
        self.mock_hoja.return_value = mock_q
        from vistas.dashboard.dashboard_view import DashboardView
        d = DashboardView(usu_id=1)
        d.cargar()
        self.assertFalse(d.hero.isHidden())
        self.assertFalse(d.hero._boton_reintentar.isHidden())
        self.assertEqual(d.hero._etiqueta_estado.text(), "Error")
        d.deleteLater()

    def test_error_en_hero_no_impide_cargar_vencimientos(self):
        # El hero falla, pero el de vencimientos debe quedar visible
        # y mostrar ok si hay permiso.
        self.mock_perm.return_value = True
        # hoja -> error
        mock_hoja_q = MagicMock()
        mock_hoja_q.where.return_value.count.side_effect = RuntimeError(
            "BD caida"
        )
        self.mock_hoja.return_value = mock_hoja_q
        # venc -> 2
        self.mock_venc.return_value = [MagicMock(), MagicMock()]
        from vistas.dashboard.dashboard_view import DashboardView
        d = DashboardView(usu_id=1)
        d.cargar()
        self.assertFalse(d.hero.isHidden())
        self.assertFalse(d.hero._boton_reintentar.isHidden())
        self.assertFalse(d.tarjeta_vencimientos.isHidden())
        self.assertEqual(d.tarjeta_vencimientos._etiqueta_valor.text(), "2")
        d.deleteLater()

    def test_click_en_hero_emite_senal_de_navegacion(self):
        self.mock_perm.return_value = True
        mock_q = MagicMock()
        mock_q.where.return_value.count.return_value = 1
        self.mock_hoja.return_value = mock_q
        from vistas.dashboard.dashboard_view import (
            NAV_HOJAS_RUTA_DIA,
            DashboardView,
        )
        d = DashboardView(usu_id=1)
        d.cargar()
        capturados = []
        d.navegar.connect(lambda c: capturados.append(c))
        # Simulamos click izquierdo sobre la tarjeta
        evento = MagicMock()
        evento.button.return_value = Qt.LeftButton
        d.hero.mousePressEvent(evento)
        self.assertEqual(capturados, [NAV_HOJAS_RUTA_DIA])
        d.deleteLater()

    def test_click_en_secundaria_emite_senal_vencimientos(self):
        self.mock_perm.return_value = True
        self.mock_venc.return_value = [MagicMock()]
        from vistas.dashboard.dashboard_view import (
            NAV_VENCIMIENTOS,
            DashboardView,
        )
        d = DashboardView(usu_id=1)
        d.cargar()
        capturados = []
        d.navegar.connect(lambda c: capturados.append(c))
        evento = MagicMock()
        evento.button.return_value = Qt.LeftButton
        d.tarjeta_vencimientos.mousePressEvent(evento)
        self.assertEqual(capturados, [NAV_VENCIMIENTOS])
        d.deleteLater()

    def test_recargar_repite_consultas(self):
        self.mock_perm.return_value = True
        mock_q = MagicMock()
        mock_q.where.return_value.count.return_value = 3
        self.mock_hoja.return_value = mock_q
        from vistas.dashboard.dashboard_view import DashboardView
        d = DashboardView(usu_id=1)
        d.cargar()
        d.recargar()
        # El servicio de hoja se llamo al menos dos veces
        self.assertGreaterEqual(mock_q.where.return_value.count.call_count, 2)
        d.deleteLater()

    def test_objetos_expuestos_con_objectName_para_qss(self):
        from vistas.dashboard.dashboard_view import DashboardView
        d = DashboardView(usu_id=1)
        self.assertEqual(d.objectName(), "dashboardRoot")
        self.assertEqual(d.hero.objectName(), "dashboardTarjetaHero")
        self.assertEqual(
            d.tarjeta_vencimientos.objectName(), "dashboardTarjetaSecundaria"
        )
        d.deleteLater()


if __name__ == "__main__":
    unittest.main()

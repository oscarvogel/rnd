from types import SimpleNamespace
from unittest.mock import Mock

from PyQt5.QtCore import Qt

import modelos.ModeloBase as modelo_base
import vistas.Main as main_view


class DummySelf:
    pass


def test_leer_opcion_menu_recicla_conexion_stale_antes_de_consultar(monkeypatch):
    db = modelo_base.RecycledMySQLDatabase("test")
    monkeypatch.setattr(modelo_base, "db", db)
    monkeypatch.setattr(db, "connection_is_stale", lambda: True)
    monkeypatch.setattr(db, "connect", Mock())

    formula = SimpleNamespace(for_valid="CLIENTES", for_arch="ABMClientes.ABMClientesController()")
    dato_menu = SimpleNamespace(for_id=formula)
    get_by_id = Mock(return_value=dato_menu)
    valida_menu = Mock(return_value=True)

    monkeypatch.setattr(main_view.MenuLateral, "get_by_id", get_by_id)
    monkeypatch.setattr(main_view.Acceso, "ValidaMenu", valida_menu)
    monkeypatch.setattr(main_view, "LeerConf", lambda _clave: "1")

    resultado, permitido = main_view.MainView._leer_opcion_menu(DummySelf(), 7)

    assert resultado is dato_menu
    assert permitido is True
    db.connect.assert_called_once_with(reuse_if_open=True)
    get_by_id.assert_called_once_with(7)


def test_click_menu_contiene_error_conexion_y_no_lo_propaga():
    class Item:
        def data(self, columna, rol):
            assert columna == 0
            assert rol == Qt.UserRole
            return 9

    class VistaDummy:
        def __init__(self):
            self.error_mostrado = None

        def _leer_opcion_menu(self, _menu_id):
            raise ConnectionError("socket MySQL muerto")

        def _mostrar_error_menu(self, target, exc):
            self.error_mostrado = (target, exc)

    vista = VistaDummy()

    main_view.MainView.onClickItemMenu(vista, Item(), 0)

    assert vista.error_mostrado is not None
    target, exc = vista.error_mostrado
    assert "id 9" in target
    assert isinstance(exc, ConnectionError)

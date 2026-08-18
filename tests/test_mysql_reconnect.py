from unittest.mock import Mock

import pytest
from peewee import OperationalError

import modelos.ModeloBase as modelo_base


class Dummy:
    pass


def test_nameerror_no_debe_convertirse_en_connectionerror(monkeypatch):
    fake_db = Mock()
    fake_db.is_closed.return_value = False
    monkeypatch.setattr(modelo_base, "db", fake_db)
    monkeypatch.setattr(modelo_base.time, "sleep", lambda _segundos: None)

    @modelo_base.reconnect_if_needed
    def operacion(self):
        raise NameError("Cliente no definido")

    with pytest.raises(NameError, match="Cliente no definido"):
        operacion(Dummy())


def test_conexion_stale_debe_reciclarse_antes_de_operar(monkeypatch):
    db = modelo_base.RecycledMySQLDatabase("test")
    db._stale_timeout = 300
    db._connected_at = 100.0

    monkeypatch.setattr(modelo_base.time, "monotonic", lambda: 500.0)
    monkeypatch.setattr(db, "is_closed", lambda: False)
    monkeypatch.setattr(modelo_base, "db", db)

    connect = Mock()
    monkeypatch.setattr(db, "connect", connect)

    @modelo_base.reconnect_if_needed
    def operacion(self):
        return "ok"

    assert operacion(Dummy()) == "ok"
    connect.assert_called_once_with(reuse_if_open=True)


def test_error_db_durante_escritura_no_debe_repetir_operacion(monkeypatch):
    fake_db = Mock()
    fake_db.is_closed.return_value = False
    monkeypatch.setattr(modelo_base, "db", fake_db)
    monkeypatch.setattr(modelo_base.time, "sleep", lambda _segundos: None)
    llamadas = []

    @modelo_base.reconnect_if_needed
    def escritura(self):
        llamadas.append(1)
        raise OperationalError(2013, "Lost connection during query")

    with pytest.raises(OperationalError):
        escritura(Dummy())

    assert len(llamadas) == 1

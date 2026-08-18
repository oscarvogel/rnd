import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication
from peewee import OperationalError

import controladores.ImportacionPedidos as importacion
from vistas.ImportacionPedidos import BarraProgresoImportacion


def test_lectura_segura_reconecta_y_reintenta_una_sola_vez(monkeypatch):
    controller = importacion.ImportacionPedidosController.__new__(
        importacion.ImportacionPedidosController
    )
    fake_db = Mock()
    fake_db.is_closed.return_value = False
    monkeypatch.setattr(importacion.modelo_base, "db", fake_db)

    operacion = Mock(
        side_effect=[OperationalError(2013, "Lost connection during query"), "ok"]
    )

    assert controller._leer_db_con_reintento(operacion, "SELECT de prueba") == "ok"
    assert operacion.call_count == 2
    fake_db.close.assert_called_once_with()
    fake_db.connect.assert_called_once_with(reuse_if_open=True)


def test_barra_de_importacion_permanece_visible_y_llega_a_100():
    app = QApplication.instance() or QApplication([])
    barra = BarraProgresoImportacion()

    assert not barra.isHidden()
    assert barra.isTextVisible()

    barra.iniciar("Preparando importación")
    barra.actualizar(42, "Grabando pedido 42/100")
    assert barra.value() == 42
    assert not barra.isHidden()
    assert "Grabando pedido 42/100" in barra.format()

    barra.finalizar("Importación finalizada")
    assert barra.value() == 100
    assert not barra.isHidden()
    assert "Importación finalizada" in barra.format()

    barra.close()
    app.processEvents()


def test_controlador_no_envuelve_save_en_retry_de_lectura():
    """Regresión: las escrituras inciertas deben seguir sin retry automático."""
    source = open("controladores/ImportacionPedidos.py", encoding="utf-8").read()
    assert "hoja_ruta.save()" in source
    assert "self._leer_db_con_reintento(\n                    lambda: hoja_ruta.save()" not in source

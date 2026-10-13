# coding=utf-8
"""La ficha del proveedor aceptaba cualquier texto en método de importación
("pujio") y después la importación fallaba con "desconocido: PUJIO".

- La ficha ofrece sólo los métodos habilitados en un combo.
- Los valores históricos se normalizan (alias) para no romper lo cargado.
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt5.QtWidgets import QApplication, QComboBox

_APP = QApplication.instance() or QApplication([])

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_importacion_proveedores_excel import _crear_tio_pujio
from utiles.importacion_proveedores_excel import (
    METODOS_IMPORTACION,
    normalizar_archivo_pedidos,
    normalizar_metodo_importacion,
)


def test_normalizar_acepta_canonicos_y_variantes():
    assert normalizar_metodo_importacion("COLUMNAS") == "COLUMNAS"
    assert normalizar_metodo_importacion("tremblay") == "TREMBLAY"
    assert normalizar_metodo_importacion("  Tio Pujio ") == "TIO_PUJIO"
    assert normalizar_metodo_importacion("tio-pujio") == "TIO_PUJIO"
    assert normalizar_metodo_importacion("detalle_ventas") == "DETALLE_VENTAS"


def test_normalizar_resuelve_alias_historico():
    # Dato real de producción: proveedor 16 con "pujio" guardado a mano.
    assert normalizar_metodo_importacion("pujio") == "TIO_PUJIO"
    assert normalizar_metodo_importacion("PUJIO") == "TIO_PUJIO"


def test_normalizar_rechaza_desconocidos():
    assert normalizar_metodo_importacion("XYZ") == ""
    assert normalizar_metodo_importacion("") == ""
    assert normalizar_metodo_importacion(None) == ""


def test_dispatcher_acepta_alias_pujio(tmp_path):
    entrada = tmp_path / "tio_alias.xlsx"
    _crear_tio_pujio(entrada)

    salida = normalizar_archivo_pedidos(str(entrada), metodo="pujio")
    assert salida is not None

    import pandas as pd

    df = pd.read_excel(salida)
    assert len(df) == 2
    assert df.iloc[0]["codigo_cliente"] == 10333


def test_dispatcher_sigue_rechazando_desconocidos(tmp_path):
    entrada = tmp_path / "tio.xlsx"
    _crear_tio_pujio(entrada)

    with pytest.raises(ValueError, match="desconocido"):
        normalizar_archivo_pedidos(str(entrada), metodo="XYZ")


def _vista_proveedores():
    from vistas.ABMProveedores import ABMProveedoresView

    return ABMProveedoresView()


def test_ficha_ofrece_solo_metodos_habilitados():
    vista = _vista_proveedores()
    combo = vista.controles["metodo_importacion"]

    assert isinstance(combo, QComboBox)
    assert not combo.isEditable()
    assert [combo.itemData(i) for i in range(combo.count())] == [
        codigo for codigo, _etiqueta in METODOS_IMPORTACION
    ]
    assert combo.count() == 4


def test_ficha_muestra_alias_historico_en_su_opcion():
    vista = _vista_proveedores()
    combo = vista.controles["metodo_importacion"]

    vista.CargaDatos([{"metodo_importacion": "pujio"}])

    assert combo.currentData() == "TIO_PUJIO"
    assert combo.valor() == "TIO_PUJIO"


def test_ficha_carga_canonico_en_minusculas():
    vista = _vista_proveedores()
    combo = vista.controles["metodo_importacion"]

    vista.CargaDatos([{"metodo_importacion": "detalle_ventas"}])

    assert combo.currentData() == "DETALLE_VENTAS"
    # Lo que se guarda es el código canónico, no el texto visible.
    assert combo.valor() == "DETALLE_VENTAS"

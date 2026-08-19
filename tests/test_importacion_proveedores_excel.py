"""Tests de los normalizadores agregados por el issue #47."""
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.importacion_proveedores_excel import (  # noqa: E402
    COLUMNAS_NORMALIZADAS,
    normalizar_archivo_pedidos,
    procesar_detalle_ventas,
    procesar_tio_pujio,
)


def _crear_tio_pujio(path):
    filas = [[""] * 17 for _ in range(10)]
    filas.append(["", "Fecha", "", "Tipo", "Comprobante", "", "", "", "Hormas", "", "Kilos", "", "", "", "", "", ""])

    cliente = [""] * 17
    cliente[0] = "Cliente :"
    cliente[2] = 10333
    cliente[4] = "CLIENTE PRUEBA"
    filas.append(cliente)

    pedido = [""] * 17
    pedido[1] = "18/08/2026"
    pedido[3] = "PED"
    pedido[5] = "N0001-00115811"
    filas.append(pedido)

    producto1 = [""] * 17
    producto1[1] = 2
    producto1[2] = "QUESO TYBO"
    producto1[7] = 8
    producto1[10] = 31.82
    filas.append(producto1)

    producto2 = [""] * 17
    producto2[1] = 22
    producto2[2] = "RICOTTA"
    producto2[7] = 16
    producto2[10] = 56.78
    filas.append(producto2)

    subtotal = [""] * 17
    subtotal[2] = "SubTotales :"
    subtotal[7] = 24
    subtotal[10] = 88.6
    filas.append(subtotal)

    pd.DataFrame(filas).to_excel(path, index=False, header=False)


def _crear_detalle_ventas(path):
    filas = [
        ["Ventas Provincia Misiones desde fecha 10/08/2026 hasta fecha 16/08/2026", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        ["Tipo Operacion", "ciudad", "Cliente", "Codigo", "DescripcionProducto", "", "Unidades", "Kilos", "Total"],
        ["Chacinados", "ELDORADO", "ALMUZARA DIEGO", 12311, "FIAMBRE COCIDO", "", 12, 52.25, 264468.6],
        ["Chacinados", "POSADAS", "CLIENTE DOS", 15718, "SALAME TIPO ESPAÑOL", "", 10, 13.09, 146372.38],
    ]
    pd.DataFrame(filas).to_excel(path, index=False, header=False)


def test_tio_pujio_emite_solo_lineas_de_producto(tmp_path):
    entrada = tmp_path / "tio_pujio.xlsx"
    _crear_tio_pujio(entrada)

    salida = procesar_tio_pujio(str(entrada))
    df = pd.read_excel(salida)

    assert list(df.columns) == COLUMNAS_NORMALIZADAS
    assert len(df) == 2
    assert df.iloc[0]["codigo_cliente"] == 10333
    assert df.iloc[0]["detalle_cliente"] == "CLIENTE PRUEBA"
    assert df.iloc[0]["comprobante"] == "N0001-00115811"
    assert df.iloc[0]["producto"] == "QUESO TYBO"
    assert df.iloc[0]["bultos"] == 8
    assert df.iloc[0]["kilos"] == pytest.approx(31.82)
    assert not df["producto"].str.contains("SubTotales", case=False).any()


def test_detalle_ventas_detecta_encabezado_y_no_confunde_codigo(tmp_path):
    entrada = tmp_path / "detalle.xlsx"
    _crear_detalle_ventas(entrada)

    salida = procesar_detalle_ventas(str(entrada))
    df = pd.read_excel(salida)

    assert list(df.columns) == COLUMNAS_NORMALIZADAS
    assert len(df) == 2
    assert df.iloc[0]["detalle_cliente"] == "ALMUZARA DIEGO"
    assert df.iloc[0]["codigo_cliente"].startswith("NOMBRE:ALMUZARA DIEGO")
    assert df.iloc[0]["codigo_cliente"] != "12311"
    assert df.iloc[0]["destino"] == "ELDORADO"
    assert df.iloc[0]["producto"] == "FIAMBRE COCIDO"
    assert df.iloc[0]["comprobante"] == ""
    assert "Producto: 12311" in df.iloc[0]["observaciones"]


def test_dispatcher_detecta_ambos_formatos(tmp_path):
    tio = tmp_path / "tio.xlsx"
    detalle = tmp_path / "detalle.xlsx"
    _crear_tio_pujio(tio)
    _crear_detalle_ventas(detalle)

    assert normalizar_archivo_pedidos(str(tio))
    assert normalizar_archivo_pedidos(str(detalle))


def test_dispatcher_no_interfiere_con_archivo_desconocido(tmp_path):
    entrada = tmp_path / "otro.xlsx"
    pd.DataFrame([["A", "B"], [1, 2]]).to_excel(entrada, index=False, header=False)
    assert normalizar_archivo_pedidos(str(entrada)) is None


def test_detalle_sin_encabezado_falla(tmp_path):
    entrada = tmp_path / "mal.xlsx"
    pd.DataFrame([["Cliente", "Producto"], ["A", "B"]]).to_excel(
        entrada, index=False, header=False
    )
    with pytest.raises(ValueError, match="encabezado"):
        procesar_detalle_ventas(str(entrada))

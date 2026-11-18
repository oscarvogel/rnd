# coding=utf-8
"""Importacion de facturas PDF de Recreo."""
from pathlib import Path
import sys

import pandas as pd
import pytest
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.importacion_factura_recreo import procesar_factura_recreo  # noqa: E402
from utiles.importacion_proveedores_excel import (  # noqa: E402
    COLUMNAS_NORMALIZADAS,
    normalizar_archivo_pedidos,
)


def _crear_factura(path, unidades="12", kilos="56.89", bultos="3"):
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(0)
    pdf.add_page()
    pdf.set_font("Helvetica", size=8)
    lineas = [
        "INDUSTRIAS FRIGORIFICAS",
        "Nro 001100285259",
        "RECREO S.A.I.C.",
        "Fecha:11/11/2026",
        "Cliente: 296329 R.N.D. SOC DE RESP. LIMITADA CUIT: 30711132747 Responsable Inscripto",
        "Entregar en: RIO GALLEGOS 1682 POSADAS, Misiones, Argentina",
        "ARTICULO Descripcion Bultos UNI CANTIDAD P.U Dtos % Total",
        "12101 JAMON COCIDO SIN CUERO -CUADRADO- 1 4 21.59 3,871.14 0 83,577.89",
        "12311 FIAMBRE COCIDO DE PATA DE CERDO CUADRADO 2 8 35.3 2,400.58 0 84,740.44",
        "X 4,4 Kgs.",
        "OBS.: SubTotal $ 1,039,463.06",
        "Unidades {}".format(unidades),
        "Peso Neto Total {}".format(kilos),
        "Cant. Bultos {}".format(bultos),
    ]
    y = 15
    for linea in lineas:
        pdf.text(15, y, linea)
        y += 6
    pdf.output(str(path))


def test_parsea_factura_recreo(tmp_path):
    archivo = tmp_path / "recreo.pdf"
    _crear_factura(archivo)
    advertencias = []

    salida = procesar_factura_recreo(str(archivo), advertencias=advertencias)

    df = pd.read_excel(salida, dtype=str)
    assert list(df.columns) == COLUMNAS_NORMALIZADAS
    assert len(df) == 2
    assert advertencias == []
    assert df.iloc[0]["codigo_cliente"] == "30711132747"
    assert df.iloc[0]["detalle_cliente"] == "R.N.D. SOC DE RESP. LIMITADA"
    assert df.iloc[0]["comprobante"] == "001100285259"
    assert df.iloc[0]["destino"] == "POSADAS"
    assert df.iloc[0]["producto"] == "JAMON COCIDO SIN CUERO -CUADRADO-"
    assert df.iloc[0]["cantidad"] == "4"
    assert float(df.iloc[0]["bultos"]) == 1
    assert float(df.iloc[0]["kilos"]) == pytest.approx(21.59)
    assert "Cod. 12101" in df.iloc[0]["observaciones"]

    segundo = df.iloc[1]
    assert segundo["producto"] == "FIAMBRE COCIDO DE PATA DE CERDO CUADRADO X 4,4 Kgs."
    assert float(segundo["cantidad"]) == 8
    assert float(segundo["bultos"]) == 2
    assert float(segundo["kilos"]) == pytest.approx(35.3)


def test_dispatcher_detalle_ventas_acepta_pdf_recreo(tmp_path):
    archivo = tmp_path / "recreo.pdf"
    _crear_factura(archivo)

    salida = normalizar_archivo_pedidos(str(archivo), metodo="DETALLE_VENTAS")

    assert salida is not None
    assert len(pd.read_excel(salida, dtype=str)) == 2


def test_advierte_totales_de_factura_descuadrados(tmp_path):
    archivo = tmp_path / "recreo.pdf"
    _crear_factura(archivo, unidades="99", kilos="999", bultos="99")
    advertencias = []

    procesar_factura_recreo(str(archivo), advertencias=advertencias)

    assert any("totales de la factura no coinciden" in texto for texto in advertencias)
    assert any("Unidades" in texto for texto in advertencias)


def test_pdf_que_no_es_factura_recreo_falla(tmp_path):
    archivo = tmp_path / "otro.pdf"
    pdf = FPDF(unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.text(20, 20, "Documento sin formato de factura")
    pdf.output(str(archivo))

    with pytest.raises(ValueError):
        procesar_factura_recreo(str(archivo))

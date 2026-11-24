# coding=utf-8
"""Importacion de facturas PDF de Recreo."""
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import pandas as pd
import pytest
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.importacion_factura_recreo import (  # noqa: E402
    procesar_factura_recreo,
    procesar_facturas_recreo_zip,
)
from utiles.importacion_proveedores_excel import (  # noqa: E402
    COLUMNAS_NORMALIZADAS,
    normalizar_archivo_pedidos,
)


def _crear_factura(path, unidades="12", kilos="56.89", bultos="3", numero="001100285259"):
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(0)
    pdf.add_page()
    pdf.set_font("Helvetica", size=8)
    lineas = [
        "INDUSTRIAS FRIGORIFICAS",
        "Nro {}".format(numero),
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


def _crear_zip_facturas(destino, facturas):
    with ZipFile(destino, "w", ZIP_DEFLATED) as contenedor:
        for nombre, archivo in facturas:
            contenedor.write(str(archivo), nombre)


def test_importa_zip_con_varias_facturas_recreo(tmp_path):
    primera = tmp_path / "285680.pdf"
    segunda = tmp_path / "315266.pdf"
    _crear_factura(primera, numero="001100285680")
    _crear_factura(segunda, numero="001500315266")
    lote = tmp_path / "WhatsApp Unknown.zip"
    _crear_zip_facturas(lote, [("285680.pdf", primera), ("315266.pdf", segunda)])
    advertencias = []

    salida = procesar_facturas_recreo_zip(str(lote), advertencias=advertencias)

    df = pd.read_excel(salida, dtype=str)
    assert list(df.columns) == COLUMNAS_NORMALIZADAS
    assert len(df) == 4
    assert set(df["comprobante"]) == {"001100285680", "001500315266"}
    assert advertencias == []


def test_zip_recreo_desde_dispatcher_detalle_ventas(tmp_path):
    factura = tmp_path / "285680.pdf"
    _crear_factura(factura, numero="001100285680")
    lote = tmp_path / "facturas.zip"
    _crear_zip_facturas(lote, [("285680.pdf", factura)])

    salida = normalizar_archivo_pedidos(str(lote), metodo="DETALLE_VENTAS")

    assert salida is not None
    assert len(pd.read_excel(salida, dtype=str)) == 2


def test_zip_ignora_factura_repetida(tmp_path):
    factura = tmp_path / "285680.pdf"
    _crear_factura(factura, numero="001100285680")
    lote = tmp_path / "facturas.zip"
    _crear_zip_facturas(
        lote,
        [("285680.pdf", factura), ("copia/285680.pdf", factura)],
    )
    advertencias = []

    salida = procesar_facturas_recreo_zip(str(lote), advertencias=advertencias)

    assert len(pd.read_excel(salida, dtype=str)) == 2
    assert any("ya estaba en el ZIP" in texto for texto in advertencias)


def test_zip_sin_pdf_falla(tmp_path):
    lote = tmp_path / "vacio.zip"
    _crear_zip_facturas(lote, [])

    with pytest.raises(ValueError):
        procesar_facturas_recreo_zip(str(lote))


def test_zip_con_archivo_ilegible_informa_y_sigue(tmp_path):
    factura = tmp_path / "285680.pdf"
    _crear_factura(factura, numero="001100285680")
    roto = tmp_path / "roto.pdf"
    roto.write_bytes(b"no es un pdf")
    lote = tmp_path / "facturas.zip"
    _crear_zip_facturas(lote, [("285680.pdf", factura), ("roto.pdf", roto)])
    advertencias = []

    salida = procesar_facturas_recreo_zip(str(lote), advertencias=advertencias)

    assert len(pd.read_excel(salida, dtype=str)) == 2
    assert any("roto.pdf" in texto for texto in advertencias)
    assert any("Se importaron 1 de 2" in texto for texto in advertencias)

# coding=utf-8
"""Seed y PDF de muestra de Tacural para el DEMO."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.generador_pdf_tacural import generar_pdf_muestra_tacural  # noqa: E402
from utiles.seed_tacural import (  # noqa: E402
    CLIENTES_TACURAL,
    FACTURAS_MUESTRA,
)


def test_los_clientes_del_seed_cuadran_con_las_facturas_de_muestra():
    assert len(CLIENTES_TACURAL) == len(FACTURAS_MUESTRA)

    cuits_clientes = {cliente["cuit"] for cliente in CLIENTES_TACURAL}
    for factura in FACTURAS_MUESTRA:
        assert factura["cuit"] in cuits_clientes


def test_el_total_de_kilos_de_cada_factura_cierra_con_sus_lineas():
    for factura in FACTURAS_MUESTRA:
        suma = round(sum(item["kg"] for item in factura["items"]), 2)
        assert suma == pytest.approx(factura["total_kilos"])


def test_el_importe_de_cada_linea_es_el_peso_por_el_precio():
    for factura in FACTURAS_MUESTRA:
        for item in factura["items"]:
            assert item["importe"] == pytest.approx(item["kg"] * item["punit"], rel=0.01)


def test_hay_una_factura_escaneada_de_lado():
    giradas = [factura for factura in FACTURAS_MUESTRA if factura.get("girada")]
    assert len(giradas) == 1


def test_genera_un_pdf_con_una_pagina_apaisada(tmp_path):
    import fitz

    destino = tmp_path / "05_proveedor_tacural.pdf"
    generar_pdf_muestra_tacural(str(destino))

    assert destino.exists()
    documento = fitz.open(str(destino))
    try:
        assert documento.page_count == len(FACTURAS_MUESTRA)
        apaisadas = [
            pagina for pagina in documento
            if pagina.rect.width > pagina.rect.height
        ]
        assert len(apaisadas) == 1
    finally:
        documento.close()


def test_los_datos_del_demo_no_son_cuits_de_clientes_reales():
    """El PDF del demo se dibuja con CUITs de DEMO, no de clientes reales."""
    for cliente in CLIENTES_TACURAL:
        assert cliente["cuit"].startswith("30-700000")
        assert cliente["codigo_cuit"].startswith("30700000")

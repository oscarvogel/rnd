# coding=utf-8
"""Importacion del Reporte de viaje (Lario) en PDF."""
from pathlib import Path
import sys

import pandas as pd
import pytest
from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.importacion_proveedores_excel import (  # noqa: E402
    COLUMNAS_NORMALIZADAS,
    normalizar_archivo_pedidos,
    normalizar_metodo_importacion,
)
from utiles.importacion_reporte_viaje import (  # noqa: E402
    _cuit_valido,
    _normalizar_filas,
    procesar_reporte_viaje,
)


X = [10, 45, 55, 70, 82, 95, 108, 130, 145, 165, 175, 190, 202, 218, 232, 246, 260]
HEADERS = [
    "Punto de Descarga",
    "Zona comercial",
    "Pedido de Venta",
    "Albaran",
    "Tipo de producto",
    "Cuenta",
    "Socio",
    "C.U.I.T",
    "Calle",
    "Ciudad",
    "C.P",
    "Cajas",
    "Subtotal",
    "Peso neto",
    "Peso bruto",
    "Peso congelado",
]

# El export nuevo de Lario agrega "Estado" (done/cancel) entre "Tipo de
# producto" y "Cuenta": 17 columnas en lugar de 16.
X_ESTADO = [
    10, 40, 50, 63, 75, 87, 99, 111, 133,
    148, 168, 179, 193, 205, 221, 235, 249, 263,
]
HEADERS_ESTADO = HEADERS[:5] + ["Estado"] + HEADERS[5:]
ROW_CARNE = [
    "DEPOSITO RND (BONDA)", "", "226SO172960", "00901-00024732", "Carne",
    "829", "SUPERMERCADOS NELSON S.R.L.", "30715692577", "AV ZAPIOLA 5957",
    "POSADAS", "330000", "30", "3778688,89", "599,75", "629,75", "599,75",
]
ROW_FIAMBRE = [
    "DEPOSITO RND (BONDA)", "", "160SO172948", "00901-00024734", "Fiambre",
    "1885", "RANKING S.R.L.", "30716359820", "AV. REP. ARGENTINA 26",
    "PUERTO IGUAZU", "337000", "15", "3516480", "362,25", "377,25", "",
]
ROW_WR_OUT = [
    "DEPOSITO RND (BONDA)", "", "307SO172931", "WR/OUT/35697", "Carne",
    "1957", "CANTERO MARGARITA OFELIA", "27246316169",
    "DE LAS AMERICA Y VENEZUELA", "GARUPA", "330400", "", "", "", "",
]


def _crear_pdf(path, total_cajas="45", total_neto="962", con_estado=False):
    x = X_ESTADO if con_estado else X
    headers = HEADERS_ESTADO if con_estado else HEADERS

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(0)
    pdf.add_page()
    pdf.set_font("Helvetica", size=3.2)
    for indice, header in enumerate(headers):
        pdf.rect(x[indice], 10, x[indice + 1] - x[indice], 5)
        pdf.text(x[indice] + 0.4, 13, header)

    filas = [ROW_CARNE, ROW_FIAMBRE, ROW_WR_OUT]
    if con_estado:
        estados = ["done", "done", "cancel"]
        filas = [
            fila[:5] + [estado] + fila[5:]
            for fila, estado in zip(filas, estados)
        ]
    for indice, fila in enumerate(filas):
        y = 17 + indice * 6
        for columna, valor in enumerate(fila):
            if valor:
                pdf.text(x[columna] + 0.4, y, valor)

    total = [""] * len(headers)
    total[headers.index("Ciudad")] = "TOTAL"
    total[headers.index("C.P")] = "0"
    total[headers.index("Cajas")] = total_cajas
    total[headers.index("Peso neto")] = total_neto
    y = 17 + len(filas) * 6
    for columna, valor in enumerate(total):
        if valor:
            pdf.text(x[columna] + 0.4, y, valor)
    pdf.output(str(path))


def test_parsea_reporte_de_viaje(tmp_path):
    archivo = tmp_path / "reporte.pdf"
    _crear_pdf(archivo)
    advertencias = []

    salida = procesar_reporte_viaje(str(archivo), advertencias=advertencias)

    df = pd.read_excel(salida)
    assert list(df.columns) == COLUMNAS_NORMALIZADAS
    assert len(df) == 3
    assert advertencias == [
        "Hay 1 remito(s) marcados REVISAR (WR/OUT o sin cajas). "
        "Quedan desmarcados en la vista previa."
    ]

    carne = df.iloc[0]
    assert str(carne["codigo_cliente"]) == "30715692577"
    assert carne["detalle_cliente"] == "SUPERMERCADOS NELSON S.R.L."
    assert carne["comprobante"] == "00901-00024732"
    assert carne["producto"] == "Carne"
    assert carne["cantidad"] == 30
    assert carne["bultos"] == 30
    assert carne["kilos"] == pytest.approx(599.75)
    assert carne["destino"] == "POSADAS"
    assert "Cta 829" in carne["observaciones"]
    assert "REVISAR" not in carne["observaciones"]

    fiambre = df.iloc[1]
    assert fiambre["producto"] == "Fiambre"
    assert fiambre["comprobante"] == "00901-00024734"

    wr_out = df.iloc[2]
    assert wr_out["comprobante"] == "WR/OUT/35697"
    assert wr_out["cantidad"] == 0
    assert wr_out["kilos"] == 0
    assert "REVISAR" in wr_out["observaciones"]


def test_parsea_reporte_de_viaje_con_columna_estado(tmp_path):
    """El export nuevo trae 17 columnas: "Estado" entre "Tipo" y "Cuenta".

    Si los indices quedan fijos los valores se corren y el archivo no se puede
    preparar ("no tiene las 16 columnas esperadas").
    """
    archivo = tmp_path / "reporte_estado.pdf"
    _crear_pdf(archivo, con_estado=True)
    advertencias = []

    salida = procesar_reporte_viaje(str(archivo), advertencias=advertencias)

    df = pd.read_excel(salida)
    assert len(df) == 3
    assert advertencias == [
        "Hay 1 remito(s) marcados REVISAR (WR/OUT o sin cajas). "
        "Quedan desmarcados en la vista previa."
    ]

    carne = df.iloc[0]
    assert str(carne["codigo_cliente"]) == "30715692577"
    assert carne["detalle_cliente"] == "SUPERMERCADOS NELSON S.R.L."
    assert carne["comprobante"] == "00901-00024732"
    assert carne["producto"] == "Carne"
    assert carne["cantidad"] == 30
    assert carne["kilos"] == pytest.approx(599.75)
    assert "REVISAR" not in carne["observaciones"]

    fiambre = df.iloc[1]
    assert fiambre["comprobante"] == "00901-00024734"
    assert fiambre["cantidad"] == 15

    wr_out = df.iloc[2]
    assert wr_out["comprobante"] == "WR/OUT/35697"
    assert "REVISAR" in wr_out["observaciones"]


def test_un_remito_cancelado_se_marca_revisar():
    fila = {
        "pedido": "226SO177616",
        "albaran": "00901-00025515",
        "tipo": "Carne",
        "estado": "cancel",
        "cuenta": "845",
        "socio": "BARREYRO CAROLINA",
        "cuit": "30715692577",
        "calle": "SARMIENTO 1420",
        "ciudad": "POSADAS",
        "cp": "330000",
        "cajas": 3,
        "subtotal": 352080.0,
        "neto": 65.2,
        "bruto": 68.2,
        "congelado": 65.2,
    }

    (normalizada,) = _normalizar_filas([fila])

    assert "REVISAR: remito cancelado en el reporte" in normalizada["observaciones"]


def test_advierte_total_descuadrado(tmp_path):
    archivo = tmp_path / "reporte.pdf"
    _crear_pdf(archivo, total_cajas="99", total_neto="9999")
    advertencias = []

    procesar_reporte_viaje(str(archivo), advertencias=advertencias)

    assert any("TOTAL del PDF no coincide" in texto for texto in advertencias)
    assert any("Cajas: PDF 99 vs filas 45" in texto for texto in advertencias)


def test_dispatcher_usa_metodo_reporte_viaje(tmp_path):
    archivo = tmp_path / "reporte.pdf"
    _crear_pdf(archivo)

    salida = normalizar_archivo_pedidos(str(archivo), metodo="REPORTE_VIAJE")

    assert salida is not None
    assert len(pd.read_excel(salida)) == 3


def test_metodo_acepta_alias_lario():
    assert normalizar_metodo_importacion("lario") == "REPORTE_VIAJE"
    assert normalizar_metodo_importacion("Reporte de viaje") == "REPORTE_VIAJE"
    assert normalizar_metodo_importacion("REPORTE_VIAJE") == "REPORTE_VIAJE"


def test_pdf_sin_el_formato_falla(tmp_path):
    archivo = tmp_path / "otro.pdf"
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    pdf.text(20, 20, "Documento sin la tabla del reporte")
    pdf.output(str(archivo))

    with pytest.raises(ValueError):
        procesar_reporte_viaje(str(archivo))


def test_cuit_valido():
    assert _cuit_valido("30715692577")
    assert _cuit_valido("30612865333")
    assert _cuit_valido("30607371799")
    assert not _cuit_valido("30715692578")
    assert not _cuit_valido("123")

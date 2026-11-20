# coding=utf-8
"""Tests del generador del Reporte de viaje de muestra (caso Lario).

Los casos salen del archivo real de Lario (Reporte_de_viaje_RT-46586), que es
un export de Crystal Report: 16 columnas, una fila por remito, los CUIT en
otro color y una fila TOTAL al pie.
"""
from pathlib import Path

import pandas as pd
import pytest

from utiles.generador_pdf_lario import generar_pdf_muestra_lario
from utiles.importacion_reporte_viaje import _cuit_valido, procesar_reporte_viaje


def _fila(**cambios):
    fila = {
        "punto": "DEPOSITO RND (BONDA)",
        "zona": "226 SO172960",
        "pedido": "226 SO172960",
        "albaran": "00901-00024732",
        "tipo": "Carne",
        "cuenta": "5808",
        "socio": "SUPERMERCADO LOS DOS S.R.L.",
        "cuit": "30700000113",
        "calle": "AV. CENTRAL 1234",
        "ciudad": "POSADAS",
        "cp": "330000",
        "cajas": 30,
        "subtotal": 3778688.89,
        "neto": 599.75,
        "bruto": 629.75,
        "congelado": 599.75,
    }
    fila.update(cambios)
    return fila


def _importar(ruta):
    advertencias = []
    salida = procesar_reporte_viaje(str(ruta), advertencias=advertencias)
    return pd.read_excel(salida, dtype=str), advertencias


def test_el_pdf_de_muestra_se_importa_completo(tmp_path):
    ruta = tmp_path / "lario.pdf"
    generar_pdf_muestra_lario(ruta)

    df, advertencias = _importar(ruta)

    assert len(df) == 10
    assert df["detalle_cliente"].nunique() == 4
    # Un WR/OUT y un remito sin cajas: quedan marcados para revisar.
    revisar = int(df["observaciones"].fillna("").str.contains("REVISAR").sum())
    assert revisar == 2
    # El TOTAL del PDF tiene que cuadrar con la suma de las filas.
    assert not [a for a in advertencias if "TOTAL" in a]


def test_el_cuit_del_cliente_se_recupera_y_es_valido(tmp_path):
    ruta = tmp_path / "lario.pdf"
    generar_pdf_muestra_lario(ruta)

    df, _ = _importar(ruta)

    for cuit in df["codigo_cliente"].dropna().unique():
        digitos = "".join(c for c in str(cuit) if c.isdigit())
        assert len(digitos) == 11
        assert _cuit_valido(digitos), "CUIT de demo sin digito verificador: {}".format(cuit)


def test_el_cp_no_arrastra_letras_de_la_ciudad(tmp_path):
    """El export solapa el C.P. con el final de la ciudad: "PUERTO IGUAZU" + 337000.

    En el archivo real el C.P. salia como "3U37000" (con una letra de la
    ciudad pegada). El C.P. es numerico, asi que se queda con los digitos.
    """
    ruta = tmp_path / "lario_cp.pdf"
    generar_pdf_muestra_lario(
        ruta,
        filas=[
            _fila(
                ciudad="PUERTO IGUAZU",
                cp="337000",
                calle="AV. REP. ARGENTINA 26",
                albaran="00901-00024734",
            )
        ],
    )

    df, _ = _importar(ruta)

    observaciones = df.iloc[0]["observaciones"]
    assert "CP 3370" in observaciones
    assert "U" not in observaciones.split("CP ")[1].split(" |")[0]


def test_la_ciudad_se_lee_casi_completa_aunque_espase_la_columna(tmp_path):
    """La ciudad se lee por rango de caracteres: entra lo que este en la celda.

    Igual que en el archivo real, la ultima letra puede quedar del lado del
    C.P.; lo que no puede pasar es que el C.P. quede con letras pegadas.
    """
    ruta = tmp_path / "lario_ciudad.pdf"
    generar_pdf_muestra_lario(
        ruta,
        filas=[_fila(ciudad="PUERTO IGUAZU", cp="337000")],
    )

    df, _ = _importar(ruta)

    assert df.iloc[0]["destino"].startswith("PUERTO IG")
    assert "CP 3370" in df.iloc[0]["observaciones"]


def test_el_importador_detecta_las_columnas_sin_rectangulos(tmp_path):
    """El export de Lario dibuja celdas; otros exportadores dibujan poligonos.

    El importador tiene que servir con las dos formas.
    """
    import pdfplumber

    ruta = tmp_path / "lario.pdf"
    generar_pdf_muestra_lario(ruta)

    with pdfplumber.open(str(ruta)) as pdf:
        pagina = pdf.pages[0]
        assert len(pagina.rects) == 0
        assert len(pagina.curves) >= 16

    df, _ = _importar(ruta)
    assert len(df) == 10


def test_un_cuit_invalido_cae_en_la_cuenta(tmp_path):
    """Si el CUIT no pasa el digito verificador, se usa la cuenta del socio."""
    ruta = tmp_path / "lario_cuit_malo.pdf"
    generar_pdf_muestra_lario(
        ruta,
        filas=[_fila(cuit="30700000119", cuenta="5808")],
    )

    df, _ = _importar(ruta)

    assert df.iloc[0]["codigo_cliente"] == "5808"

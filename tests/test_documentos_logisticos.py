# coding=utf-8
from datetime import date

from modelos.Documentos import (
    clave_documento_importado,
    normalizar_numero_documento,
)


def test_normaliza_numero_documento_legacy():
    assert normalizar_numero_documento(None) == ""
    assert normalizar_numero_documento(float("nan")) == ""
    assert normalizar_numero_documento("001.000123") == "001000123"
    assert normalizar_numero_documento("123.0") == "123"


def test_clave_con_factura_no_depende_del_producto():
    clave_a = clave_documento_importado(15, 99, "A-0001", date(2026, 9, 9))
    clave_b = clave_documento_importado(15, 99, "A-0001", date(2026, 9, 10))
    assert clave_a == clave_b == "P15|FA-0001"


def test_clave_sin_factura_separa_cliente_y_fecha():
    a = clave_documento_importado(15, 99, "", date(2026, 9, 9))
    b = clave_documento_importado(15, 100, "", date(2026, 9, 9))
    c = clave_documento_importado(15, 99, "", date(2026, 9, 10))
    assert a != b
    assert a != c


def test_huella_linea_es_estable_y_ocurrencia_distingue_duplicados():
    from modelos.Documentos import huella_linea_importada, identidad_linea_importada

    huella_a = huella_linea_importada("Producto", 2, 10, 1, "Obs")
    huella_b = huella_linea_importada("Producto", 2, 10, 1, "Obs")
    assert huella_a == huella_b
    assert identidad_linea_importada("Producto", 2, 10, 1, "Obs", 1) != identidad_linea_importada(
        "Producto", 2, 10, 1, "Obs", 2
    )

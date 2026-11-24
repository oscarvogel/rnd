# coding=utf-8
"""Seed de Noalsa para el DEMO (remitos escaneados por IA)."""
from utiles.seed_noalsa import (
    CLIENTES_NOALSA,
    MAPEO_COLUMNAS_NORMALIZADAS,
    PROVEEDOR_NOALSA,
)


def test_seed_noalsa_define_el_cliente_del_pdf():
    assert len(CLIENTES_NOALSA) == 1
    cliente = CLIENTES_NOALSA[0]

    assert cliente["codigo"] == "000564"
    assert cliente["razon_social"] == "NEGIAR S.R.L."
    assert cliente["codigo_cuit"] == "30708054840"
    assert cliente["localidad"] == "Posadas"


def test_seed_noalsa_registra_todas_las_formas_de_resolver_el_cliente():
    cliente = CLIENTES_NOALSA[0]

    # El lector por IA puede devolver el codigo de cliente, el CUIT o el
    # nombre; cualquiera de los tres debe encontrar al cliente en la previa.
    assert cliente["codigo"] in cliente["codigos"]
    assert cliente["codigo_cuit"] in cliente["codigos"]
    assert cliente["cuit"] in cliente["codigos"]
    assert any(codigo.startswith("NOMBRE:") for codigo in cliente["codigos"])


def test_proveedor_noalsa_usa_el_lector_generico_de_pdf_ia():
    assert PROVEEDOR_NOALSA["razon_social"] == "Noalsa"
    assert PROVEEDOR_NOALSA["cuit"] == "30-64806084-6"
    assert PROVEEDOR_NOALSA["metodo_importacion"] == "COLUMNAS"

    mapping = dict(MAPEO_COLUMNAS_NORMALIZADAS)
    assert mapping["Cliente"] == "codigo_cliente"
    assert mapping["Nombre_Cliente"] == "detalle_cliente"
    assert mapping["Comprobante"] == "comprobante"
    assert mapping["Producto"] == "producto"
    assert mapping["Cantidad"] == "cantidad"
    assert mapping["KG"] == "kilos"
    assert mapping["Bultos"] == "bultos"
    assert mapping["Observaciones"] == "observaciones"

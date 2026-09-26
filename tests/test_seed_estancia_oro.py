# coding=utf-8
from utiles.seed_estancia_oro import (
    CLIENTES_ESTANCIA_ORO,
    MAPEO_COLUMNAS_NORMALIZADAS,
    PROVEEDOR_ESTANCIA_ORO,
)


def test_seed_estancia_oro_tiene_ocho_clientes_y_codigos_unicos():
    assert len(CLIENTES_ESTANCIA_ORO) == 8
    codigos = [fila["codigo"] for fila in CLIENTES_ESTANCIA_ORO]
    assert len(codigos) == len(set(codigos))
    assert set(codigos) == {
        "1956", "1941", "1994", "1909", "2387", "2373", "1945", "1944"
    }


def test_seed_estancia_oro_datos_clave_del_pdf():
    por_codigo = {fila["codigo"]: fila for fila in CLIENTES_ESTANCIA_ORO}

    assert por_codigo["1956"]["razon_social"] == "MARTINEZ CARLA CHAVELY"
    assert por_codigo["1956"]["localidad"] == "Garupa"
    assert por_codigo["1941"]["razon_social"] == "CEFERINO RODRIGUEZ SUPERMERCADOS SRL"
    assert por_codigo["1941"]["localidad"] == "San Vicente"
    assert por_codigo["1994"]["localidad"] == "Aristobulo del Valle"
    assert por_codigo["1909"]["localidad"] == "Puerto Iguazu"
    assert por_codigo["2373"]["localidad"] == "Puerto Libertad"
    assert por_codigo["1945"]["localidad"] == "Montecarlo"


def test_proveedor_y_mapeo_quedan_listos_para_normalizado_pdf():
    assert PROVEEDOR_ESTANCIA_ORO["razon_social"] == "LA ESTANCIA DE ORO S.A."
    assert PROVEEDOR_ESTANCIA_ORO["cuit"] == "30-71573241-2"
    assert PROVEEDOR_ESTANCIA_ORO["metodo_importacion"] == "COLUMNAS"

    mapping = dict(MAPEO_COLUMNAS_NORMALIZADAS)
    assert mapping["Cliente"] == "codigo_cliente"
    assert mapping["Nombre_Cliente"] == "detalle_cliente"
    assert mapping["Comprobante"] == "comprobante"
    assert mapping["Producto"] == "producto"
    assert mapping["Cantidad"] == "cantidad"
    assert mapping["KG"] == "kilos"
    assert mapping["Bultos"] == "bultos"
    assert mapping["Observaciones"] == "observaciones"

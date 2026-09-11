# coding=utf-8
from decimal import Decimal

from utiles.bandeja_pedidos import (
    ESTADO_OBSERVADO, ESTADO_ORGANIZADO, ESTADO_PENDIENTE,
    PedidoBandeja, expandir_seleccion_por_factura, totales_seleccion, validar_reasignacion,
)


def pedido(**kwargs):
    base = dict(
        id=1, cliente="Cliente", cliente_id=10, lugar_entrega="Central", lugar_entrega_id=20, comprobante="A1", producto="Producto",
        cantidad=1, kg=100, bultos=2, ruta_id=1, ruta="Centro",
        responsable_id=23, equipo_id=1,
    )
    base.update(kwargs)
    return PedidoBandeja(**base)


def test_pedido_generico_queda_pendiente():
    assert pedido().estado("23", "1") == ESTADO_PENDIENTE


def test_pedido_con_observacion_queda_observado():
    assert pedido(observaciones="Revisar domicilio").estado("23", "1") == ESTADO_OBSERVADO


def test_pedido_con_recursos_reales_queda_organizado():
    assert pedido(responsable_id=7, equipo_id=9).estado("23", "1") == ESTADO_ORGANIZADO


def test_totales_de_seleccion():
    datos = [pedido(id=1, kg="100.50", bultos=2), pedido(id=2, kg=50, bultos="3")]
    total = totales_seleccion(datos)
    assert total["pedidos"] == 2
    assert total["kg"] == Decimal("150.50")
    assert total["bultos"] == Decimal("5")


def test_reasignacion_requiere_seleccion_y_ruta():
    assert validar_reasignacion([], 1)[0] is False
    assert validar_reasignacion([pedido()], 0)[0] is False
    assert validar_reasignacion([pedido()], 2) == (True, "")


def test_reasignacion_rechaza_ids_duplicados():
    duplicados = [pedido(id=5), pedido(id=5)]
    valido, mensaje = validar_reasignacion(duplicados, 2)
    assert valido is False
    assert "duplicados" in mensaje.lower()


def test_pedido_sin_cliente_o_lugar_queda_observado():
    assert pedido(cliente_id=0, lugar_entrega_id=0).estado("23", "1") == ESTADO_OBSERVADO
    assert pedido(lugar_entrega_id=0).estado("23", "1") == ESTADO_OBSERVADO


def test_expandir_seleccion_incluye_toda_la_factura():
    todos = [
        pedido(id=1, factura="F-100", producto="A"),
        pedido(id=2, factura="F-100", producto="B"),
        pedido(id=3, factura="F-200", producto="C"),
    ]
    resultado = expandir_seleccion_por_factura(todos, [todos[0]])
    assert [p.id for p in resultado] == [1, 2]


def test_expandir_sin_factura_no_arrastra_otros():
    todos = [pedido(id=1, factura="", comprobante=""), pedido(id=2, factura="", comprobante="")]
    resultado = expandir_seleccion_por_factura(todos, [todos[0]])
    assert [p.id for p in resultado] == [1]

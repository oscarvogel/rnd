# coding=utf-8
from decimal import Decimal

from utiles.bandeja_pedidos import (
    ESTADO_OBSERVADO, ESTADO_ORGANIZADO, ESTADO_PENDIENTE,
    PedidoBandeja, totales_seleccion, validar_reasignacion,
)


def pedido(**kwargs):
    base = dict(
        id=1, cliente="Cliente", comprobante="A1", producto="Producto",
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

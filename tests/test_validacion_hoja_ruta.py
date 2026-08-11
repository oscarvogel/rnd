# coding=utf-8
from types import SimpleNamespace

from modelos.EstadoHojaRuta import EstadoHojaRuta
from utiles.validacion_hoja_ruta import puede_transicionar, validar_hoja


def pedido(cliente=10, comprobante="A-1", cantidad=1, kg=100, bultos=5, responsable=7, equipo=8):
    return SimpleNamespace(
        cliente_id=cliente,
        comprobante=comprobante,
        cantidad=cantidad,
        kg=kg,
        cantidad_bultos=bultos,
        responsable_id=responsable,
        equipo_asignado_id=equipo,
    )


def test_hoja_completa_puede_quedar_lista():
    resultado = validar_hoja([pedido(), pedido(comprobante="A-2")], object(), 3, 23, 1)
    assert resultado.valida is True
    permitido, mensaje = puede_transicionar(EstadoHojaRuta.EN_PREPARACION, EstadoHojaRuta.LISTA, resultado)
    assert permitido is True
    assert mensaje == ""


def test_sin_pedidos_no_puede_quedar_lista():
    resultado = validar_hoja([], object(), 3, 23, 1)
    assert resultado.valida is False
    permitido, mensaje = puede_transicionar(EstadoHojaRuta.EN_PREPARACION, EstadoHojaRuta.LISTA, resultado)
    assert permitido is False
    assert "incompleta" in mensaje


def test_recurso_generico_bloquea_validacion():
    resultado = validar_hoja([pedido(responsable=23, equipo=1)], object(), 3, 23, 1)
    faltantes = {item.codigo for item in resultado.pendientes}
    assert "chofer" in faltantes
    assert "camion" in faltantes


def test_asignacion_mixta_bloquea_validacion():
    resultado = validar_hoja([
        pedido(responsable=7, equipo=8),
        pedido(comprobante="A-2", responsable=9, equipo=8),
    ], object(), 3, 23, 1)
    assert any(item.codigo == "chofer" and not item.cumplido for item in resultado.items)


def test_pedido_con_cantidad_invalida_es_bloqueante():
    resultado = validar_hoja([pedido(cantidad=0)], object(), 3, 23, 1)
    assert any(item.codigo == "datos" and not item.cumplido for item in resultado.items)


def test_solo_lista_puede_pasarse_a_despachada():
    resultado = validar_hoja([pedido()], object(), 3, 23, 1)
    permitido, _ = puede_transicionar(EstadoHojaRuta.EN_PREPARACION, EstadoHojaRuta.DESPACHADA, resultado)
    assert permitido is False
    permitido, _ = puede_transicionar(EstadoHojaRuta.LISTA, EstadoHojaRuta.DESPACHADA, resultado)
    assert permitido is True


def test_despachada_no_retrocede_automaticamente():
    resultado = validar_hoja([pedido()], object(), 3, 23, 1)
    permitido, mensaje = puede_transicionar(EstadoHojaRuta.DESPACHADA, EstadoHojaRuta.LISTA, resultado)
    assert permitido is False
    assert "no puede retroceder" in mensaje

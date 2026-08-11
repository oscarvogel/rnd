from utiles.dashboard_flujo import (
    ACCION_ASIGNAR,
    ACCION_COMPLETO,
    ACCION_DESPACHAR,
    ACCION_IMPORTAR,
    ACCION_ORGANIZAR,
    ACCION_REVISAR,
    ACCION_VALIDAR,
    EstadoFlujoDashboard,
)


def test_sin_pedidos_recomienda_importar():
    estado = EstadoFlujoDashboard()
    assert estado.accion == ACCION_IMPORTAR


def test_importacion_con_errores_prioriza_revision():
    estado = EstadoFlujoDashboard(pedidos=10, errores_importacion=1)
    assert estado.accion == ACCION_REVISAR


def test_pedidos_sin_ruta_priorizan_organizacion():
    estado = EstadoFlujoDashboard(pedidos=10, sin_ruta=2, incompletos_recursos=1)
    assert estado.accion == ACCION_ORGANIZAR


def test_hoja_sin_recursos_recomienda_asignar():
    estado = EstadoFlujoDashboard(pedidos=10, incompletos_recursos=1, ruta_recomendada=4)
    assert estado.accion == ACCION_ASIGNAR
    assert estado.ruta_recomendada == 4


def test_hoja_completa_en_preparacion_recomienda_validar():
    estado = EstadoFlujoDashboard(pedidos=10, en_preparacion_completos=1)
    assert estado.accion == ACCION_VALIDAR


def test_hoja_lista_recomienda_despachar():
    estado = EstadoFlujoDashboard(pedidos=10, listas=1)
    assert estado.accion == ACCION_DESPACHAR


def test_todo_despachado_indica_circuito_completo():
    estado = EstadoFlujoDashboard(pedidos=10, despachadas=2)
    assert estado.accion == ACCION_COMPLETO


def test_progreso_marca_atencion_en_revision():
    estado = EstadoFlujoDashboard(pedidos=5, pendientes_importacion=1)
    pasos = dict(estado.pasos())
    assert pasos["1. Importar"] == "completo"
    assert pasos["2. Revisar"] == "atencion"

# coding=utf-8
from datetime import date

import pandas as pd
import pytest

from utiles.remitos_tio_pujio import (
    ESTADO_AMBIGUO,
    ESTADO_ASIGNADO,
    ESTADO_SIN_PEDIDO,
    ESTADO_YA_TENIA_REMITO,
    PedidoCruce,
    RemitoImportado,
    cruzar_remitos,
    es_control_pedidos,
    es_informe_remitos,
    procesar_control_pedidos_para_cruce,
    procesar_informe_remitos,
    resumen_cruce,
)


def _crear_informe_remitos(path):
    filas = [
        ["LACTEOS TIO PUJIO S.R.L.", "", "", "", "", "", "", "", "", "", ""],
        ["", "", "Informe :", "Informe de Remitos", "", "", "", "", "", "", ""],
        ["", "", "Zona :", "TODAS", "", "", "", "", "", "", ""],
        ["", "Fecha", "Tipo Comprobante", "", "", "Comprobante", "", "Cliente", "", "Vence", "Total"],
        ["", "08/09/2026", "REMITO DE ENVIO", "", "", "R0003-00073508", "", 757, "GAUZE SRL", "23/09/2026", -866895.06],
        ["", "08/09/2026", "REMITO DE ENVIO", "", "", "R0003-00073507", "", 10148, "DUOMO S.A", "23/09/2026", -13506700],
        ["", "08/09/2026", "REMITO DE ENVIO", "", "", "R0003-00073509", "", 715.0, "MILICICH NICOLAS EMANUEL", "23/09/2026", -624032.69],
        ["", "", "21/10/2026", "", "08:37:01", "", "Usuario: LUCRECIA", "", "", "Pagina 1", ""],
        ["", "", "", "", "", "", "", "", "", "", -75879196.85],
    ]
    pd.DataFrame(filas).to_excel(path, index=False, header=False)


def _crear_control_pedidos(path):
    filas = [[""] * 18 for _ in range(10)]
    filas[1][7] = "Informe :"
    filas[1][8] = "CONTROL DE PEDIDOS"
    header = [""] * 18
    header[2] = "Fecha"
    header[5] = "Tipo"
    header[6] = "Comprobante"
    header[10] = "Hormas"
    header[11] = "Kilos"
    header[16] = "Tot.Final"
    filas.append(header)

    cliente_duomo = [""] * 18
    cliente_duomo[0] = "Cliente :"
    cliente_duomo[4] = 10148
    cliente_duomo[6] = "DUOMO S.A"
    filas.append(cliente_duomo)

    pedido_duomo = [""] * 18
    pedido_duomo[1] = "07/09/2026"
    pedido_duomo[5] = "PED"
    pedido_duomo[7] = "N0001-00116570"
    pedido_duomo[11] = 13179925
    filas.append(pedido_duomo)

    producto_duomo = [""] * 18
    producto_duomo[1] = 69
    producto_duomo[3] = "CREMA X 10"
    producto_duomo[9] = 250
    producto_duomo[11] = 2500
    producto_duomo[16] = 13179925
    filas.append(producto_duomo)

    subtotal_duomo = [""] * 18
    subtotal_duomo[3] = "SubTotales :"
    subtotal_duomo[9] = 250
    subtotal_duomo[11] = 2500
    subtotal_duomo[16] = 13179925
    filas.append(subtotal_duomo)

    cliente_gauze = [""] * 18
    cliente_gauze[0] = "Cliente :"
    cliente_gauze[4] = 757
    cliente_gauze[6] = "GAUZE SRL"
    filas.append(cliente_gauze)

    pedido_gauze = [""] * 18
    pedido_gauze[1] = "08/09/2026"
    pedido_gauze[5] = "PED"
    pedido_gauze[7] = "N0001-00116681"
    pedido_gauze[11] = 823928.23
    filas.append(pedido_gauze)

    producto_gauze_1 = [""] * 18
    producto_gauze_1[3] = "QUESO HOLANDA"
    producto_gauze_1[9] = 8
    producto_gauze_1[11] = 35.28
    producto_gauze_1[16] = 447271.90
    filas.append(producto_gauze_1)

    producto_gauze_2 = [""] * 18
    producto_gauze_2[3] = "QUESO TYBO"
    producto_gauze_2[9] = 12
    producto_gauze_2[11] = 46.80
    producto_gauze_2[16] = 376656.32
    filas.append(producto_gauze_2)

    subtotal_gauze = [""] * 18
    subtotal_gauze[3] = "SubTotales :"
    subtotal_gauze[9] = 20
    subtotal_gauze[11] = 82.08
    subtotal_gauze[16] = 823928.22
    filas.append(subtotal_gauze)

    pd.DataFrame(filas).to_excel(path, index=False, header=False)


def test_procesar_informe_remitos_lee_solo_filas_de_remito(tmp_path):
    entrada = tmp_path / "informe_remitos.xlsx"
    _crear_informe_remitos(entrada)

    remitos = procesar_informe_remitos(str(entrada))

    assert len(remitos) == 3
    primero = remitos[0]
    assert primero.numero_remito == "R0003-00073508"
    assert primero.codigo_cliente == "757"
    assert primero.nombre_cliente == "GAUZE SRL"
    assert primero.fecha == date(2026, 9, 8)
    assert primero.vencimiento == date(2026, 9, 23)
    assert primero.importe_total == pytest.approx(-866895.06)
    assert remitos[1].importe_total == pytest.approx(-13506700.0)
    assert remitos[2].codigo_cliente == "715"


def test_informe_remitos_detecta_titulo(tmp_path):
    entrada = tmp_path / "informe_remitos.xlsx"
    _crear_informe_remitos(entrada)
    df = pd.read_excel(entrada, sheet_name=0, header=None)
    assert es_informe_remitos(df) is True
    assert es_informe_remitos(pd.DataFrame([["A", "B"]])) is False


def test_informe_remitos_sin_encabezado_falla(tmp_path):
    entrada = tmp_path / "sin_encabezado.xlsx"
    pd.DataFrame([["LACTEOS TIO PUJIO S.R.L."], ["Informe de Remitos"]]).to_excel(
        entrada, index=False, header=False
    )
    with pytest.raises(ValueError, match="encabezado"):
        procesar_informe_remitos(str(entrada))


def test_archivo_que_no_es_informe_remitos_falla(tmp_path):
    entrada = tmp_path / "otro.xlsx"
    pd.DataFrame([["A", "B"], [1, 2]]).to_excel(entrada, index=False, header=False)
    with pytest.raises(ValueError, match="Informe de Remitos"):
        procesar_informe_remitos(str(entrada))


def test_procesar_control_pedidos_extrae_cliente_ped_y_total(tmp_path):
    entrada = tmp_path / "control_pedidos.xlsx"
    _crear_control_pedidos(entrada)

    pedidos = procesar_control_pedidos_para_cruce(str(entrada))

    assert len(pedidos) == 2
    duomo, gauze = pedidos
    assert duomo.numero_pedido == "N0001-00116570"
    assert duomo.codigo_cliente == "10148"
    assert duomo.nombre_cliente == "DUOMO S.A"
    assert duomo.fecha == date(2026, 9, 7)
    assert duomo.importe_total == pytest.approx(13179925.0)
    assert gauze.numero_pedido == "N0001-00116681"
    assert gauze.codigo_cliente == "757"
    assert gauze.fecha == date(2026, 9, 8)
    assert gauze.importe_total == pytest.approx(823928.22)


def test_control_pedidos_detecta_formato(tmp_path):
    entrada = tmp_path / "control_pedidos.xlsx"
    _crear_control_pedidos(entrada)
    df = pd.read_excel(entrada, sheet_name=0, header=None)
    assert es_control_pedidos(df) is True
    assert es_control_pedidos(pd.DataFrame([["A", "B"]])) is False


def _pedido(numero, codigo, total, remito_actual=""):
    return PedidoCruce(
        numero_pedido=numero,
        codigo_cliente=codigo,
        importe_total=total,
        remito_actual=remito_actual,
    )


def _remito(numero, codigo, total):
    return RemitoImportado(
        numero_remito=numero,
        codigo_cliente=codigo,
        importe_total=total,
    )


def test_cruce_uno_a_uno_asigna_por_codigo_de_cliente():
    pedido = _pedido("N0001-00116681", "757", 823928.22)
    remito = _remito("R0003-00073508", "757", 866895.06)

    resultados = cruzar_remitos([pedido], [remito])

    assert len(resultados) == 1
    assert resultados[0].estado == ESTADO_ASIGNADO
    assert resultados[0].pedido == pedido
    assert resultados[0].motivo == ""


def test_cruce_varios_pedidos_ordena_por_importe():
    pedidos = [
        _pedido("N0001-00116705", "1892", 319606.71),
        _pedido("N0001-00116690", "1892", 807388.25),
        _pedido("N0001-00116736", "1892", 876760.50),
        _pedido("N0001-00116687", "1892", 982029.69),
        _pedido("N0001-00116699", "1892", 1332981.87),
        _pedido("N0001-00116697", "1892", 1951932.02),
    ]
    remitos = [
        _remito("R0003-00073514", "1892", 1033321.49),
        _remito("R0003-00073517", "1892", 849492.57),
        _remito("R0003-00073524", "1892", 2053722.86),
        _remito("R0003-00073526", "1892", 1402495.22),
        _remito("R0003-00073532", "1892", 327530.84),
        _remito("R0003-00073563", "1892", 922562.63),
    ]

    resultados = cruzar_remitos(pedidos, remitos)

    assert len(resultados) == 6
    assert all(resultado.estado == ESTADO_ASIGNADO for resultado in resultados)
    asignaciones = {
        resultado.remito.numero_remito: resultado.pedido.numero_pedido
        for resultado in resultados
    }
    assert asignaciones == {
        "R0003-00073532": "N0001-00116705",
        "R0003-00073517": "N0001-00116690",
        "R0003-00073563": "N0001-00116736",
        "R0003-00073514": "N0001-00116687",
        "R0003-00073526": "N0001-00116699",
        "R0003-00073524": "N0001-00116697",
    }


def test_cruce_cantidades_distintas_queda_ambiguo():
    pedidos = [
        _pedido("N0001-00116681", "757", 823928.22),
        _pedido("N0001-00116682", "757", 593103.09),
    ]
    remito = _remito("R0003-00073508", "757", 866895.06)

    resultados = cruzar_remitos(pedidos, [remito])

    assert resultados[0].estado == ESTADO_AMBIGUO
    assert "2 pedido(s) y 1 remito(s)" in resultados[0].motivo
    assert len(resultados[0].candidatos) == 2


def test_cruce_sin_pedido():
    remito = _remito("R0003-00073599", "9999", 100.0)
    resultados = cruzar_remitos([], [remito])
    assert resultados[0].estado == ESTADO_SIN_PEDIDO


def test_cruce_no_pisa_remito_existente():
    pedido = _pedido(
        "N0001-00116681",
        "757",
        823928.22,
        remito_actual="R0003-00070000",
    )
    remito = _remito("R0003-00073508", "757", 866895.06)

    resultados = cruzar_remitos([pedido], [remito])

    assert resultados[0].estado == ESTADO_YA_TENIA_REMITO
    assert "R0003-00070000" in resultados[0].motivo


def test_cruce_es_idempotente_si_ya_estaba_asociado():
    pedido = _pedido(
        "N0001-00116681",
        "757",
        823928.22,
        remito_actual="R0003-00073508",
    )
    remito = _remito("R0003-00073508", "757", 866895.06)

    resultados = cruzar_remitos([pedido], [remito])

    assert resultados[0].estado == ESTADO_ASIGNADO
    assert resultados[0].motivo == "ya estaba asociado"


def test_cruce_importes_repetidos_queda_ambiguo():
    pedidos = [
        _pedido("N0001-00116681", "757", 100.0),
        _pedido("N0001-00116682", "757", 100.0),
    ]
    remitos = [
        _remito("R0003-00073508", "757", 105.215),
        _remito("R0003-00073509", "757", 105.215),
    ]

    resultados = cruzar_remitos(pedidos, remitos)

    assert all(resultado.estado == ESTADO_AMBIGUO for resultado in resultados)
    assert "importes repetidos" in resultados[0].motivo


def test_cruce_total_fuera_de_rango_queda_ambiguo():
    pedido = _pedido("N0001-00116681", "757", 100.0)
    remito = _remito("R0003-00073508", "757", 200.0)

    resultados = cruzar_remitos([pedido], [remito])

    assert resultados[0].estado == ESTADO_AMBIGUO
    assert "ratio" in resultados[0].motivo


def test_cruce_sin_importes_asigna_con_advertencia():
    pedido = _pedido("N0001-00116681", "757", None)
    remito = _remito("R0003-00073508", "757", None)

    resultados = cruzar_remitos([pedido], [remito])

    assert resultados[0].estado == ESTADO_ASIGNADO
    assert resultados[0].motivo == "sin importe para validar"


def test_cruce_normaliza_codigo_de_cliente():
    pedido = _pedido("N0001-00116681", "00123", 100.0)
    remito = _remito("R0003-00073508", "123", 105.215)

    resultados = cruzar_remitos([pedido], [remito])

    assert resultados[0].estado == ESTADO_ASIGNADO


def test_resumen_cruce_cuenta_estados():
    pedidos = [
        _pedido("N0001-00116681", "757", 823928.22),
        _pedido("N0001-00116682", "715", 593103.09),
    ]
    remitos = [
        _remito("R0003-00073508", "757", 866895.06),
        _remito("R0003-00073509", "715", 624032.69),
        _remito("R0003-00073599", "9999", 100.0),
    ]

    resumen = resumen_cruce(cruzar_remitos(pedidos, remitos))

    assert resumen[ESTADO_ASIGNADO] == 2
    assert resumen[ESTADO_SIN_PEDIDO] == 1
    assert resumen["total"] == 3

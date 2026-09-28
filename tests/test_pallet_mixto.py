# coding=utf-8
"""Issue #66: pallet multi-cliente/multi-destino con parciales (Epic #58)."""

from datetime import date
from decimal import Decimal

import pytest
from peewee import SqliteDatabase

from utiles.pallets import (
    agrupar_por_cliente_destino,
    a_decimal,
    prefijo_codigo,
    saldo_disponible,
    totales,
    validar_agregado,
)


def test_a_decimal_trata_vacios_como_cero():
    assert a_decimal(None) == Decimal("0")
    assert a_decimal("") == Decimal("0")
    assert a_decimal("nan") == Decimal("0")
    assert a_decimal("10.5") == Decimal("10.5")


def test_prefijo_codigo_diario():
    assert prefijo_codigo(date(2026, 9, 28)) == "PLT-20260928"


def test_saldo_nunca_negativo():
    assert saldo_disponible(10, 4) == Decimal("6")
    assert saldo_disponible(10, 10) == Decimal("0")
    assert saldo_disponible(10, 99) == Decimal("0")


def test_validar_agregado_rechaza_exceso():
    ok, mensaje = validar_agregado(10, 100, 5, 11, 0, 0)
    assert not ok and "saldo" in mensaje.lower()
    ok, _ = validar_agregado(10, 100, 5, 10, 100, 5)
    assert ok


def test_validar_agregado_rechaza_cero():
    ok, _ = validar_agregado(10, 100, 5, 0, 0, 0)
    assert not ok


def test_totales_suman_lineas():
    total = totales([
        {"cantidad": 2, "kg": 10, "bultos": 1},
        {"cantidad": 3, "kg": 20, "bultos": 2},
    ])
    assert total == {"lineas": 2, "cantidad": Decimal("5"),
                     "kg": Decimal("30"), "bultos": Decimal("3")}


def test_agrupar_por_cliente_destino():
    grupos = agrupar_por_cliente_destino([
        {"cliente_id": 1, "cliente": "A", "lugar_entrega_id": 10,
         "lugar_entrega": "X", "cantidad": 2, "kg": 5, "bultos": 1},
        {"cliente_id": 2, "cliente": "B", "lugar_entrega_id": 20,
         "lugar_entrega": "Y", "cantidad": 3, "kg": 7, "bultos": 1},
        {"cliente_id": 1, "cliente": "A", "lugar_entrega_id": 10,
         "lugar_entrega": "X", "cantidad": 1, "kg": 2, "bultos": 0},
    ])
    assert len(grupos) == 2
    grupo_a = next(g for g in grupos if g["cliente_id"] == 1)
    assert grupo_a["cantidad"] == Decimal("3")
    assert grupo_a["lineas"] == 2


# --- Integracion con modelos (SQLite en memoria, sin tocar la DB real) ---

_TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture()
def base_pallets():
    from modelos.Clientes import (
        Cliente, Localidades, LugarEntrega, RutaReparto,
    )
    from modelos.Empleados import ConceptoLiquidacion, Empleado
    from modelos.Equipos import Equipos
    from modelos.HojaRuta import HojaDeRuta
    from modelos.ModeloBase import Auditoria
    from modelos.ModeloBase import db as db_real
    from modelos.Pallet import Pallet, PalletDetalle
    from modelos.Tablas import TipoDeMovil

    modelos = [
        Auditoria, ConceptoLiquidacion, TipoDeMovil, RutaReparto,
        Localidades, Cliente, LugarEntrega, Empleado, Equipos,
        HojaDeRuta, Pallet, PalletDetalle,
    ]
    _TEST_DB.bind(modelos)
    _TEST_DB.connect()
    _TEST_DB.create_tables(modelos)
    try:
        yield {
            "Pallet": Pallet, "PalletDetalle": PalletDetalle,
            "HojaDeRuta": HojaDeRuta, "Cliente": Cliente,
            "LugarEntrega": LugarEntrega,
        }
    finally:
        _TEST_DB.drop_tables(modelos)
        _TEST_DB.close()
        db_real.bind(modelos)


def _linea(HojaDeRuta, comprobante, producto, cantidad, kg, bultos,
           cliente=None, lugar=None, nombre=""):
    return HojaDeRuta.create(
        fecha=date(2026, 9, 28),
        cliente=cliente,
        nombre_cliente=nombre,
        lugar_entrega=lugar,
        comprobante=comprobante,
        producto=producto,
        cantidad=cantidad,
        kg=kg,
        cantidad_bultos=bultos,
        observaciones="",
        equipo_asignado=1,
        responsable=1,
    )


def test_pallet_mixto_multi_cliente_con_parciales(base_pallets):
    from modelos.Pallet import (
        agregar_detalle, composicion_pallet, crear_pallet, saldo_linea,
        totales_pallet, totales_por_destino,
    )

    HojaDeRuta = base_pallets["HojaDeRuta"]
    Cliente = base_pallets["Cliente"]

    cliente_a = Cliente.create(razon_social="Cinco Hermanos Test")
    cliente_b = Cliente.create(razon_social="Ceferino Test")
    linea_a = _linea(HojaDeRuta, "F-100", "Tablas 2x4", 10, 100, 5,
                     cliente=cliente_a, nombre="Cinco Hermanos")
    linea_b = _linea(HojaDeRuta, "F-200", "Tirantes", 4, 40, 2,
                     cliente=cliente_b, nombre="Ceferino")

    pallet = crear_pallet(observaciones="Pallet mixto prueba")
    assert pallet.codigo.startswith("PLT-2026")

    # Parcial de A + total de B en el mismo pallet (mixto permitido).
    agregar_detalle(pallet, linea_a, cantidad=6, kg=60, bultos=3)
    agregar_detalle(pallet, linea_b)  # None = todo el saldo

    assert saldo_linea(linea_a.id) == {
        "cantidad": Decimal("4"), "kg": Decimal("40"),
        "bultos": Decimal("2"),
    }

    # El resto de A va a otro pallet (linea dividida entre pallets).
    otro = crear_pallet()
    assert otro.codigo != pallet.codigo
    agregar_detalle(otro, linea_a)
    assert saldo_linea(linea_a.id)["cantidad"] == Decimal("0")

    total = totales_pallet(pallet)
    assert total["lineas"] == 2
    assert total["cantidad"] == Decimal("10")

    grupos = totales_por_destino(pallet)
    assert len(grupos) == 2

    composicion = composicion_pallet(pallet)
    assert {c["producto"] for c in composicion} == {"Tablas 2x4", "Tirantes"}


def test_agregar_mas_que_el_saldo_falla(base_pallets):
    from modelos.Pallet import agregar_detalle, crear_pallet

    HojaDeRuta = base_pallets["HojaDeRuta"]
    linea = _linea(HojaDeRuta, "F-300", "Machihembre", 5, 50, 5)

    pallet = crear_pallet()
    with pytest.raises(ValueError):
        agregar_detalle(pallet, linea, cantidad=6, kg=60, bultos=6)


def test_fijar_detalle_permite_edicion_sin_exceder(base_pallets):
    from modelos.Pallet import agregar_detalle, fijar_detalle, saldo_linea

    HojaDeRuta = base_pallets["HojaDeRuta"]
    linea = _linea(HojaDeRuta, "F-400", "Vigas", 10, 100, 10)

    from modelos.Pallet import crear_pallet
    pallet = crear_pallet()
    agregar_detalle(pallet, linea, cantidad=8, kg=80, bultos=8)
    fijar_detalle(pallet, linea, cantidad=5, kg=50, bultos=5)
    assert saldo_linea(linea.id)["cantidad"] == Decimal("5")
    with pytest.raises(ValueError):
        fijar_detalle(pallet, linea, cantidad=99, kg=99, bultos=99)

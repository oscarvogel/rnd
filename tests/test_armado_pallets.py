# coding=utf-8
"""Issue #67: pantalla guiada para armar y editar pallets (Epic #58)."""

import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from peewee import SqliteDatabase
from PyQt5.QtWidgets import QApplication


_QT_APP = QApplication.instance() or QApplication([])


_TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture()
def base_armado():
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
            "RutaReparto": RutaReparto, "HojaDeRuta": HojaDeRuta,
            "Pallet": Pallet, "Empleado": Empleado, "Equipos": Equipos,
        }
    finally:
        _TEST_DB.drop_tables(modelos)
        _TEST_DB.close()
        db_real.bind(modelos)


@pytest.fixture()
def parche_referencias(monkeypatch):
    monkeypatch.setattr(
        "controladores.ArmadoPallets.referencias_por_hojas",
        lambda ids: {},
    )


def _controlador(fecha, ruta_id):
    from controladores.ArmadoPallets import ArmadoPalletsController
    from vistas.ArmadoPallets import ArmadoPalletsView

    controller = ArmadoPalletsController.__new__(ArmadoPalletsController)
    controller.view = ArmadoPalletsView()
    controller.ruta_inicial = int(ruta_id)
    controller.hojas_actuales = []
    controller.view.fecha_reparto.setFecha(fecha)
    controller.view.cbo_ruta_reparto.CargaDatos()
    controller._seleccionar_ruta_inicial()
    return controller


def test_vista_carga_pendientes_y_lee_seleccion(base_armado):
    from vistas.ArmadoPallets import ArmadoPalletsView

    view = ArmadoPalletsView()
    assert view.windowTitle() == "Armado de pallets"
    assert view.btn_agregar.text() == "Agregar selección al pallet"
    assert view.btn_parcial.text() == "Agregar parcial…"
    assert view.btn_quitar.text() == "Quitar del pallet"
    assert view.btn_confirmar.text() == "Confirmar preparación"
    view.cargar_pendientes([
        {"hoja_ruta_id": 10, "cliente": "Cinco Hermanos",
         "comprobante": "F-1", "factura": "F-1", "producto": "Bebidas",
         "total": Decimal("24"), "asignado": Decimal("0"),
         "saldo": Decimal("24"), "saldo_kg": Decimal("300"),
         "saldo_bultos": Decimal("24")},
        {"hoja_ruta_id": 11, "cliente": "Ceferino",
         "comprobante": "F-2", "factura": "F-2", "producto": "Alimentos",
         "total": Decimal("4"), "asignado": Decimal("1"),
         "saldo": Decimal("3"), "saldo_kg": Decimal("30"),
         "saldo_bultos": Decimal("3")},
    ])
    assert view.grilla_pendientes.rowCount() == 2
    assert view.grilla_pendientes.isColumnHidden(9)

    view.grilla_pendientes.selectRow(1)
    assert view.ids_pendientes_seleccionados() == [11]

    view.mostrar_estado("Faltan 2 líneas por paletizar.")
    assert "Faltan 2" in view.lbl_estado.text()

    view.cargar_pallets([(5, "PLT-20260928-001")], seleccionado=5)
    assert view.pallet_actual_id() == 5
    assert view.cantidad_pallets() == 1
    assert view.selector_pallets.botones[5].isChecked()

    view.cargar_contenido([
        {"hoja_ruta_id": 10, "producto": "Bebidas",
         "cliente": "Cinco Hermanos", "comprobante": "F-1",
         "cantidad": Decimal("24"), "kg": Decimal("300"),
         "bultos": Decimal("24")},
    ])
    assert view.grilla_contenido.rowCount() == 1
    view.mostrar_totales(
        {"lineas": 1, "cantidad": Decimal("24"),
         "kg": Decimal("300"), "bultos": Decimal("24")},
        [{"cliente": "Cinco Hermanos", "lugar_entrega": "Central",
          "cantidad": Decimal("24")}],
    )
    assert "1 líneas" in view.lbl_totales.text()
    assert "Cinco Hermanos" in view.lbl_destinos.text()
    view.close()


def test_selector_pallets_cambia_activo_con_click(base_armado):
    from vistas.ArmadoPallets import ArmadoPalletsView

    view = ArmadoPalletsView()
    view.cargar_pallets([
        (10, "PLT-20261006-001"),
        (11, "PLT-20261006-002"),
        (12, "PLT-20261006-003"),
    ], seleccionado=10)

    assert view.pallet_actual_id() == 10
    view.selector_pallets.botones[12].click()
    assert view.pallet_actual_id() == 12
    assert view.selector_pallets.botones[12].isChecked()
    assert not view.selector_pallets.botones[10].isChecked()
    view.close()


def test_pallets_se_filtran_por_contexto_de_carga(base_armado):
    from modelos.Pallet import Pallet, pallets_para_carga

    RutaReparto = base_armado["RutaReparto"]
    Empleado = base_armado["Empleado"]
    Equipos = base_armado["Equipos"]

    ruta_centro = RutaReparto.create(descripcion="CENTRO")
    ruta_norte = RutaReparto.create(descripcion="NORTE")
    chofer_a = Empleado.create(nombre="Juan", apellido="Perez")
    chofer_b = Empleado.create(nombre="Pedro", apellido="Gomez")
    camion = Equipos.create(descripcion="Camion 1")

    esperado = Pallet.create(
        codigo="PLT-20261006-001", fecha_reparto=date(2026, 10, 6),
        ruta=ruta_centro, responsable=chofer_a, equipo=camion,
    )
    Pallet.create(
        codigo="PLT-20261006-002", fecha_reparto=date(2026, 10, 6),
        ruta=ruta_norte, responsable=chofer_a, equipo=camion,
    )
    Pallet.create(
        codigo="PLT-20261006-003", fecha_reparto=date(2026, 10, 6),
        ruta=ruta_centro, responsable=chofer_b, equipo=camion,
    )

    encontrados = pallets_para_carga(
        date(2026, 10, 6), ruta_centro.id, chofer_a.id, camion.id
    )
    assert [p.id for p in encontrados] == [esperado.id]


def test_filas_pendientes_calculan_asignado():
    from types import SimpleNamespace

    from controladores.ArmadoPallets import ArmadoPalletsController

    hojas = [
        SimpleNamespace(id=1, nombre_cliente="A", comprobante="F-1",
                        producto="P", cantidad=Decimal("10")),
    ]
    filas = ArmadoPalletsController.filas_pendientes(
        hojas, {}, {1: {"cantidad": 4, "kg": 40, "bultos": 2}}
    )
    assert filas[0]["asignado"] == Decimal("6")
    assert filas[0]["saldo"] == Decimal("4")


def test_cargar_mercaderia_y_agregar_end_to_end(
    base_armado, parche_referencias
):
    RutaReparto = base_armado["RutaReparto"]
    HojaDeRuta = base_armado["HojaDeRuta"]

    ruta = RutaReparto.create(descripcion="CENTRO")
    hoja_a = HojaDeRuta.create(
        fecha=date(2026, 9, 28), nombre_cliente="Cinco Hermanos",
        comprobante="F-100", producto="Bebidas", cantidad=10, kg=100,
        cantidad_bultos=10, observaciones="", equipo_asignado=1,
        responsable=1, ruta=ruta.id,
    )
    HojaDeRuta.create(
        fecha=date(2026, 9, 28), nombre_cliente="Ceferino",
        comprobante="F-200", producto="Alimentos", cantidad=4, kg=40,
        cantidad_bultos=4, observaciones="", equipo_asignado=1,
        responsable=1, ruta=ruta.id,
    )

    controller = _controlador(date(2026, 9, 28), ruta.id)
    assert controller._ruta_seleccionada() == ruta.id
    assert controller.cargar_mercaderia() is True
    assert controller.view.grilla_pendientes.rowCount() == 2
    assert "Faltan 2" in controller.view.lbl_estado.text()

    agregados, errores = controller.agregar_lineas([hoja_a.id])
    assert (agregados, errores) == (1, [])
    controller.refrescar_contenido()
    controller.cargar_mercaderia_sin_alertas()
    assert controller.view.grilla_contenido.rowCount() == 1
    assert "Toda la mercadería ya está paletizada" not in controller.view.lbl_estado.text()

    # Sin saldo: reporta error sin romper.
    agregados, errores = controller.agregar_lineas([hoja_a.id])
    assert agregados == 0 and len(errores) == 1
    controller.view.close()


def test_quitar_devuelve_saldo(base_armado, parche_referencias):
    from modelos.Pallet import Pallet, saldo_linea

    RutaReparto = base_armado["RutaReparto"]
    HojaDeRuta = base_armado["HojaDeRuta"]

    ruta = RutaReparto.create(descripcion="NORTE")
    hoja = HojaDeRuta.create(
        fecha=date(2026, 9, 28), nombre_cliente="A",
        comprobante="F-1", producto="P", cantidad=6, kg=60,
        cantidad_bultos=6, observaciones="", equipo_asignado=1,
        responsable=1, ruta=ruta.id,
    )
    controller = _controlador(date(2026, 9, 28), ruta.id)
    controller.cargar_mercaderia()

    agregados, _ = controller.agregar_lineas([hoja.id])
    assert agregados == 1
    pallet_id = controller.view.pallet_actual_id()
    assert Pallet.select().count() == 1

    controller.refrescar_contenido()
    controller.view.grilla_contenido.selectRow(0)
    assert controller.view.id_contenido_seleccionado() == hoja.id

    from modelos.Pallet import quitar_detalle
    quitar_detalle(pallet_id, hoja.id)
    assert saldo_linea(hoja.id)["cantidad"] == Decimal("6")
    controller.view.close()

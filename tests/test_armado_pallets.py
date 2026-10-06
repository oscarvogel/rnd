# coding=utf-8
"""Issue #67: pantalla guiada para armar y editar pallets (Epic #58)."""

import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from peewee import SqliteDatabase
from PyQt5.QtWidgets import QApplication, QSizePolicy

from utiles.pallets import a_decimal


_QT_APP = QApplication.instance() or QApplication([])
_TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture()
def base_armado():
    from modelos.Clientes import Cliente, Localidades, LugarEntrega, RutaReparto
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
            "RutaReparto": RutaReparto,
            "HojaDeRuta": HojaDeRuta,
            "Pallet": Pallet,
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
    controller.contexto_carga = None
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


def test_selector_muestra_20_pallets_sin_scroll_y_grilla_expandible(base_armado):
    from vistas.ArmadoPallets import ArmadoPalletsView

    view = ArmadoPalletsView()
    pallets = [
        (i, "PLT-20261006-{:03d}".format(i))
        for i in range(1, 21)
    ]
    view.cargar_pallets(pallets, seleccionado=1)

    assert view.cantidad_pallets() == 20
    assert len(view.selector_pallets.botones) == 20
    assert view.selector_pallets.columnas_por_fila == 5
    assert view.selector_pallets._layout.itemAtPosition(3, 4).widget().text() == "20"
    # La grilla usa el alto disponible: ya no lleva el tope fijo de 300px que
    # limitaba el contenido a un fragmento de la pantalla (aab4a4c).
    assert view.grilla_contenido.maximumHeight() > 10000
    assert view.grilla_contenido.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    assert view.lbl_pallet_actual.text() == "PALLET ACTUAL: 1"

    view.selector_pallets.botones[15].click()
    assert view.lbl_pallet_actual.text() == "PALLET ACTUAL: 15"
    view.close()


def test_pallets_se_filtran_por_contexto_de_carga(base_armado):
    from modelos.Pallet import Pallet, pallets_para_carga

    RutaReparto = base_armado["RutaReparto"]
    ruta_centro = RutaReparto.create(descripcion="CENTRO")
    ruta_norte = RutaReparto.create(descripcion="NORTE")

    esperado = Pallet.create(
        codigo="PLT-20261006-001",
        fecha_reparto=date(2026, 10, 6),
        ruta_id=ruta_centro.id,
        responsable_id=101,
        equipo_id=501,
    )
    Pallet.create(
        codigo="PLT-20261006-002",
        fecha_reparto=date(2026, 10, 6),
        ruta_id=ruta_norte.id,
        responsable_id=101,
        equipo_id=501,
    )
    Pallet.create(
        codigo="PLT-20261006-003",
        fecha_reparto=date(2026, 10, 6),
        ruta_id=ruta_centro.id,
        responsable_id=102,
        equipo_id=501,
    )
    Pallet.create(
        codigo="PLT-20261006-004",
        fecha_reparto=date(2026, 10, 6),
        ruta_id=ruta_centro.id,
        responsable_id=101,
        equipo_id=502,
    )

    encontrados = pallets_para_carga(
        date(2026, 10, 6), ruta_centro.id, 101, 501
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


def test_cargar_mercaderia_y_agregar_end_to_end(base_armado, parche_referencias):
    RutaReparto = base_armado["RutaReparto"]
    HojaDeRuta = base_armado["HojaDeRuta"]
    Pallet = base_armado["Pallet"]

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
    pallet = Pallet.get_by_id(controller.view.pallet_actual_id())
    assert pallet.fecha_reparto == date(2026, 9, 28)
    assert pallet.ruta_id == ruta.id
    assert pallet.responsable_id == 1
    assert pallet.equipo_id == 1

    controller.refrescar_contenido()
    controller.cargar_mercaderia_sin_alertas()
    assert controller.view.grilla_contenido.rowCount() == 1
    assert "Toda la mercadería ya está paletizada" not in controller.view.lbl_estado.text()

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


def _vista_con_pallets(*ids):
    from vistas.ArmadoPallets import ArmadoPalletsView

    view = ArmadoPalletsView()
    view.cargar_pallets(
        [(i, "PLT-20261006-{:03d}".format(i)) for i in ids], seleccionado=ids[0]
    )
    return view


def _totales(kg, lineas=1, cantidad=None):
    kg = a_decimal(kg)
    return {
        "lineas": lineas,
        "cantidad": a_decimal(cantidad) if cantidad is not None else kg,
        "kg": kg,
        "bultos": Decimal("1") if lineas else Decimal("0"),
    }


def test_kpi_peso_muestra_kg_como_principal_y_mantiene_resumen(base_armado):
    view = _vista_con_pallets(10)

    assert view.kpi_peso.lbl_titulo.text() == "KG ACTUALES"
    view.mostrar_totales(_totales(Decimal("115.62"), cantidad=Decimal("24")), [])

    assert view.kpi_peso.texto_peso_actual() == "115.62 KG"
    assert view.kg_pallet_actual() == Decimal("115.62")
    # Sin límite configurado no se inventa ninguna línea de límite.
    assert view.kpi_peso.texto_limite() == ""
    # El resumen de abajo sigue completo, sólo deja de ser la única fuente.
    assert "líneas" in view.lbl_totales.text()
    assert "cant" in view.lbl_totales.text()
    assert "KG" in view.lbl_totales.text()
    assert "bultos" in view.lbl_totales.text()
    view.close()


def test_kpi_peso_cambia_al_cambiar_de_chip(base_armado):
    view = _vista_con_pallets(10, 12)

    view.mostrar_totales(_totales(Decimal("115.62")), [])
    assert view.kpi_peso.texto_peso_actual() == "115.62 KG"

    view.selector_pallets.botones[12].click()
    assert view.pallet_actual_id() == 12
    assert view.kpi_peso.texto_peso_actual() == "0 KG"

    view.mostrar_totales(_totales(Decimal("40")), [])
    assert view.kpi_peso.texto_peso_actual() == "40 KG"

    # Volver al primer pallet recupera su propio peso, no el del último.
    view.selector_pallets.botones[10].click()
    assert view.pallet_actual_id() == 10
    assert view.kpi_peso.texto_peso_actual() == "115.62 KG"
    view.close()


def test_kpi_peso_de_pallet_vacio_muestra_0_kg(base_armado):
    view = _vista_con_pallets(10)

    view.mostrar_totales(
        {"lineas": 0, "cantidad": Decimal("0"), "kg": Decimal("0"), "bultos": Decimal("0")},
        [],
    )

    assert view.kpi_peso.texto_peso_actual() == "0 KG"
    assert view.kg_pallet_actual() == Decimal("0")
    assert "Pallet vacío" in view.lbl_destinos.text()
    view.close()


def test_kpi_peso_muestra_exceso_y_disponible_cuando_hay_limite(base_armado):
    view = _vista_con_pallets(10)

    view.mostrar_totales(_totales(Decimal("115.62")), [], limite_kg=Decimal("100"))
    assert view.kpi_peso.texto_peso_actual() == "115.62 KG"
    assert view.kpi_peso.texto_limite() == "Límite: 100 KG · Exceso 15.62 KG"
    assert "15803d" not in view.kpi_peso.lbl_valor.styleSheet()
    assert "b91c1c" in view.kpi_peso.lbl_valor.styleSheet()

    view.mostrar_totales(_totales(Decimal("80")), [], limite_kg=Decimal("100"))
    assert view.kpi_peso.texto_limite() == "Límite: 100 KG · Disponible 20 KG"
    assert "15803d" in view.kpi_peso.lbl_valor.styleSheet()
    assert "b91c1c" not in view.kpi_peso.lbl_valor.styleSheet()
    view.close()


def test_kpi_peso_sin_pallet_seleccionado_no_muestra_limite(base_armado):
    from vistas.ArmadoPallets import ArmadoPalletsView

    view = ArmadoPalletsView()

    assert view.lbl_pallet_actual.text() == "PALLET ACTUAL: -"
    view.mostrar_totales(_totales(Decimal("0"), lineas=0), [], limite_kg=Decimal("100"))

    # Sin pallet no hay contra qué límite compararse: sólo el KG actual.
    assert view.kpi_peso.texto_peso_actual() == "0 KG"
    assert view.kpi_peso.texto_limite() == ""
    view.close()


def test_kpi_peso_conserva_el_peso_al_recargar_pallets(base_armado):
    view = _vista_con_pallets(10, 12)

    view.mostrar_totales(_totales(Decimal("130.45")), [])
    assert view.kpi_peso.texto_peso_actual() == "130.45 KG"

    # El controlador recarga el selector al crear/seleccionar otro pallet. Si
    # esa recarga borrara lo que se sabía, el chip 1 volvería a pintar 0 KG.
    view.selector_pallets.botones[12].click()
    view.mostrar_totales(_totales(Decimal("25.17")), [])
    assert view.kpi_peso.texto_peso_actual() == "25.17 KG"
    view.cargar_pallets(
        [(10, "PLT-20261006-010"), (12, "PLT-20261006-012")], seleccionado=12
    )
    view.selector_pallets.botones[10].click()
    assert view.kpi_peso.texto_peso_actual() == "130.45 KG"

    # Un pallet de otra carga sí se descarta del histórico.
    view.cargar_pallets([(99, "PLT-20261006-099")], seleccionado=99)
    assert view.kpi_peso.texto_peso_actual() == "0 KG"
    view.close()


def test_controlador_actualiza_el_kpi_al_cambiar_de_chip(base_armado, monkeypatch, parche_referencias):
    RutaReparto = base_armado["RutaReparto"]
    HojaDeRuta = base_armado["HojaDeRuta"]

    ruta = RutaReparto.create(descripcion="CENTRO")
    for nombre, kg in (("Cinco Hermanos", 90.45), ("Ceferino", 40.00)):
        HojaDeRuta.create(
            fecha=date(2026, 10, 6), nombre_cliente=nombre, comprobante="F-1",
            producto="P", cantidad=6, kg=kg, cantidad_bultos=6, observaciones="",
            equipo_asignado=1, responsable=1, ruta=ruta.id,
        )
    controller = _controlador(date(2026, 10, 6), ruta.id)
    controller.conectarWidgets()
    assert controller.cargar_mercaderia() is True

    hojas = list(HojaDeRuta.select())
    controller.agregar_lineas([hojas[0].id])
    controller.refrescar_contenido()
    assert controller.view.kpi_peso.texto_peso_actual() == "90.45 KG"

    from modelos.Pallet import crear_pallet
    segundo = crear_pallet(**controller.contexto_carga)
    controller.refrescar_pallets(seleccionado=segundo.id)
    controller.agregar_lineas([hojas[1].id])
    controller.refrescar_contenido()
    assert controller.view.kpi_peso.texto_peso_actual() == "40 KG"

    # Clic real en el chip del primer pallet: el controlador recarga el
    # contenido y el KPI tiene que seguir al pallet, no quedar en 0.
    primero = min(controller.view.selector_pallets.botones)
    controller.view.selector_pallets.botones[primero].click()
    assert controller.view.pallet_actual_id() == primero
    assert controller.view.kpi_peso.texto_peso_actual() == "90.45 KG"
    controller.view.close()


def test_controlador_pasa_el_limite_configurado_al_kpi(base_armado, monkeypatch):
    RutaReparto = base_armado["RutaReparto"]
    Pallet = base_armado["Pallet"]

    ruta = RutaReparto.create(descripcion="CENTRO")
    pallet = Pallet.create(
        codigo="PLT-20261006-001", fecha_reparto=date(2026, 10, 6),
        ruta_id=ruta.id, responsable_id=1, equipo_id=1,
    )
    controller = _controlador(date(2026, 10, 6), ruta.id)
    controller.contexto_carga = {
        "fecha_reparto": date(2026, 10, 6), "ruta_id": ruta.id,
        "responsable_id": 1, "equipo_id": 1,
    }

    monkeypatch.setattr(
        "controladores.ArmadoPallets.limite_kg_pallet", lambda: Decimal("100")
    )
    controller.view.cargar_pallets([(pallet.id, pallet.codigo)], seleccionado=pallet.id)
    controller.refrescar_contenido()
    assert controller.view.kpi_peso.texto_peso_actual() == "0 KG"
    assert controller.view.kpi_peso.texto_limite() == "Límite: 100 KG · Disponible 100 KG"

    monkeypatch.setattr("controladores.ArmadoPallets.limite_kg_pallet", lambda: None)
    controller.refrescar_contenido()
    assert controller.view.kpi_peso.texto_limite() == ""
    controller.view.close()


def test_limite_kg_pallet_no_crea_el_parametro(base_armado):
    from controladores.ArmadoPallets import PARAM_KG_LIMITE_PALLET, limite_kg_pallet
    from modelos.ModeloBase import db as db_real
    from modelos.ParametrosSistema import ParamSist

    # `ObtenerParametro` inserta el parámetro cuando falta. Leer el límite no
    # debe escribir en la tabla de parámetros en cada refresco de pantalla.
    _TEST_DB.bind([ParamSist])
    _TEST_DB.connect(reuse_if_open=True)
    _TEST_DB.create_tables([ParamSist])
    try:
        assert limite_kg_pallet() is None
        assert ParamSist.select().count() == 0

        ParamSist.create(parametro=PARAM_KG_LIMITE_PALLET, valor="100")
        assert limite_kg_pallet() == Decimal("100")
        assert ParamSist.select().count() == 1
    finally:
        # No se cierra la conexión: es la del fixture, que cierra al terminar.
        _TEST_DB.drop_tables([ParamSist])
        db_real.bind([ParamSist])


def test_formato_kg_omite_decimales_en_pesos_enteros():
    from utiles.pallets import formato_kg

    assert formato_kg(Decimal("0")) == "0"
    assert formato_kg(Decimal("115.62")) == "115.62"
    assert formato_kg(Decimal("300")) == "300"
    assert formato_kg(Decimal("115.625")) == "115.62"
    assert formato_kg(None) == "0"


def test_estado_limite_kg_sin_limite_configurado():
    from utiles.pallets import estado_limite_kg, limite_kg_configurable

    assert estado_limite_kg(Decimal("115.62"), None) is None
    assert estado_limite_kg(Decimal("115.62"), "") is None
    assert estado_limite_kg(Decimal("115.62"), "0") is None
    assert limite_kg_configurable("abc") is None
    assert limite_kg_configurable("100") == Decimal("100")

    texto, excede = estado_limite_kg(Decimal("100"), Decimal("100"))
    assert texto == "Límite: 100 KG · Disponible 0 KG"
    assert excede is False

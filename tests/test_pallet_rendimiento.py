# coding=utf-8
"""Rendimiento del armado de pallets contra el MySQL remoto.

Cada artículo movido recalculaba saldos con 2 queries POR HOJA (get_by_id
+ SUM), la composición 3 veces por refresco y los conteos con la
composición completa de cada pallet. Con el día cargado eran cientos de
roundtrips por artículo (~5 segundos).

Los batch deben dar el MISMO resultado con un puñado de queries, y la
recarga automática del dashboard al recuperar el foco debe limitarse a
una por intervalo (antes eran 5 consultas remotas por cada diálogo
cerrado o alt-tab).
"""
import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from peewee import SqliteDatabase
from PyQt5.QtWidgets import QApplication

_APP = QApplication.instance() or QApplication([])

_TEST_DB = SqliteDatabase(":memory:")


class ContadorSQL:
    """Cuenta execute_sql sobre una base durante el test."""

    def __init__(self, bd, monkeypatch):
        self.n = 0
        original = bd.execute_sql

        def contar(*args, **kwargs):
            self.n += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(bd, "execute_sql", contar)


@pytest.fixture()
def base_pallets():
    from modelos.Clientes import (
        Cliente, Localidades, LugarEntrega, RutaReparto,
    )
    from modelos.Documentos import (
        DocumentoPedido, DocumentoPedidoDetalle, DocumentoPedidoHojaRuta,
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
        DocumentoPedido, DocumentoPedidoDetalle, DocumentoPedidoHojaRuta,
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
        fecha=date(2026, 10, 13),
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


def _escenario(base_pallets):
    from modelos.Pallet import agregar_detalle, crear_pallet

    HojaDeRuta = base_pallets["HojaDeRuta"]
    Cliente = base_pallets["Cliente"]
    LugarEntrega = base_pallets["LugarEntrega"]

    cliente = Cliente.create(razon_social="Cliente Rendimiento")
    lugar = LugarEntrega.create(
        cliente=cliente, nombre="Depósito", direccion="Calle 1",
    )
    hojas = [
        _linea(HojaDeRuta, "F-{}".format(i), "Prod-{}".format(i),
               10 + i, 100 + i * 10, 5 + i,
               cliente=cliente, lugar=lugar, nombre="Cliente Rendimiento")
        for i in range(6)
    ]
    pallet_a = crear_pallet(observaciones="A")
    pallet_b = crear_pallet(observaciones="B")
    agregar_detalle(pallet_a, hojas[0], cantidad=4, kg=40, bultos=2)
    agregar_detalle(pallet_a, hojas[1])
    agregar_detalle(pallet_b, hojas[0], cantidad=2, kg=20, bultos=1)
    return hojas, pallet_a, pallet_b


def test_lineas_con_saldo_equivale_al_calculo_individual(base_pallets):
    from modelos.Pallet import lineas_con_saldo, saldo_linea

    HojaDeRuta = base_pallets["HojaDeRuta"]
    hojas, _pa, _pb = _escenario(base_pallets)
    ids = [h.id for h in hojas] + [99999]

    esperado = {h.id: saldo_linea(h.id) for h in hojas}
    assert lineas_con_saldo(ids) == esperado
    assert 99999 not in lineas_con_saldo(ids)
    assert lineas_con_saldo([]) == {}


def test_lineas_con_saldo_en_un_punado_de_queries(base_pallets, monkeypatch):
    from modelos.Pallet import lineas_con_saldo

    HojaDeRuta = base_pallets["HojaDeRuta"]
    hojas, _pa, _pb = _escenario(base_pallets)

    contador = ContadorSQL(_TEST_DB, monkeypatch)
    lineas_con_saldo([h.id for h in hojas])
    # GROUP BY de asignados + IN de hojas. Antes: 2 por hoja (12).
    assert contador.n <= 3, "se emitieron {} queries".format(contador.n)


def test_lineas_por_pallet_cuenta_y_ceros(base_pallets, monkeypatch):
    from modelos.Pallet import lineas_por_pallet

    _hojas, pallet_a, pallet_b = _escenario(base_pallets)

    contador = ContadorSQL(_TEST_DB, monkeypatch)
    conteo = lineas_por_pallet([pallet_a.id, pallet_b.id, 99999])
    assert contador.n <= 2, "se emitieron {} queries".format(contador.n)
    assert conteo == {pallet_a.id: 2, pallet_b.id: 1, 99999: 0}
    assert lineas_por_pallet([]) == {}


def test_composicion_pallet_contenido_y_queries(base_pallets, monkeypatch):
    from modelos.Pallet import composicion_pallet

    _hojas, pallet_a, _pb = _escenario(base_pallets)

    contador = ContadorSQL(_TEST_DB, monkeypatch)
    filas = composicion_pallet(pallet_a.id)
    # Detalles+JOIN y lugares. Antes el JOIN se ejecutaba dos veces.
    assert contador.n <= 3, "se emitieron {} queries".format(contador.n)

    assert [f["producto"] for f in filas] == ["Prod-0", "Prod-1"]
    assert filas[0]["cantidad"] == Decimal("4")
    assert filas[1]["cantidad"] == Decimal("11")
    assert {f["lugar_entrega"] for f in filas} == {"Depósito"}
    assert all(f["cliente"] == "Cliente Rendimiento" for f in filas)

    contador_vacio = ContadorSQL(_TEST_DB, monkeypatch)
    assert composicion_pallet(99999) == []
    assert contador_vacio.n <= 2


def test_asegurar_documentos_solo_verifica_una_vez(base_pallets, monkeypatch):
    import modelos.Documentos as documentos_mod

    monkeypatch.setattr(documentos_mod, "db", _TEST_DB)
    cache = documentos_mod._ESQUEMA_DOCUMENTOS_VERIFICADO
    respaldo = list(cache)
    cache.clear()
    try:
        contador = ContadorSQL(_TEST_DB, monkeypatch)
        documentos_mod.asegurar_esquema_documentos()
        primera = contador.n
        assert primera > 0
        documentos_mod.asegurar_esquema_documentos()
        documentos_mod.asegurar_esquema_documentos()
        assert contador.n == primera, (
            "la verificación repetida debe costar 0 queries, costó {}".format(
                contador.n - primera
            )
        )
    finally:
        cache[:] = respaldo


def test_recarga_auto_dashboard_limitada_por_intervalo():
    from unittest.mock import Mock

    from vistas.Main import MainView

    vista = MainView()
    try:
        tablero = Mock()
        tablero.isVisible.return_value = True
        vista.dashboard = tablero

        vista._recargar_dashboard_si_visible()
        vista._recargar_dashboard_si_visible()
        vista._recargar_dashboard_si_visible()
        assert tablero.recargar.call_count == 1

        vista._ultima_recarga_auto_dashboard -= 61
        vista._recargar_dashboard_si_visible()
        assert tablero.recargar.call_count == 2
    finally:
        vista.close()
        vista.deleteLater()


def test_recarga_auto_no_dispara_si_dashboard_oculto():
    from unittest.mock import Mock

    from vistas.Main import MainView

    vista = MainView()
    try:
        tablero = Mock()
        tablero.isVisible.return_value = False
        vista.dashboard = tablero

        vista._recargar_dashboard_si_visible()
        assert tablero.recargar.call_count == 0
    finally:
        vista.close()
        vista.deleteLater()


def test_recarga_solo_si_hubo_modulo_o_paso_intervalo():
    from unittest.mock import Mock

    from vistas.Main import MainView

    vista = MainView()
    try:
        tablero = Mock()
        tablero.isVisible.return_value = True
        vista.dashboard = tablero

        # Recién recalculado y sin módulos abiertos: focos/diálogos no
        # deben disparar nada.
        vista._dashboard_sucio = False
        vista._ultima_recarga_auto_dashboard = __import__("time").monotonic()
        vista._recargar_dashboard_si_visible()
        assert tablero.recargar.call_count == 0

        # Abrir un módulo marca sucio y la vuelta recalcula una vez.
        vista.marcar_dashboard_sucio()
        vista._recargar_dashboard_si_visible()
        assert tablero.recargar.call_count == 1
        assert vista._dashboard_sucio is False
        vista._recargar_dashboard_si_visible()
        assert tablero.recargar.call_count == 1
    finally:
        vista.close()
        vista.deleteLater()


def test_abrir_modulo_lateral_marca_dashboard_sucio():
    from unittest.mock import Mock

    from vistas.Main import MainView

    vista = MainView()
    try:
        vista._dashboard_sucio = False
        item = Mock()
        item.data.return_value = 123
        vista._leer_opcion_menu = Mock(
            return_value=(Mock(for_id=Mock(for_arch="x", for_valid="v")), True)
        )
        abierta = []

        class FakeModulo:
            def run(self):
                abierta.append(True)

        vista._resolver_clase_menu = Mock(return_value=FakeModulo)
        vista.onClickItemMenu(item, 0)

        assert abierta == [True]
        assert vista._dashboard_sucio is True
    finally:
        vista.close()
        vista.deleteLater()


def test_navegar_desde_dashboard_marca_sucio(monkeypatch):
    from unittest.mock import Mock

    from controladores.Main import NAV_IMPORTAR_PEDIDOS, MainController

    vista = Mock()
    controlador = MainController.__new__(MainController)
    controlador.view = vista
    abierta = []

    class FakeModulo:
        def run(self):
            abierta.append(True)

    monkeypatch.setattr(
        "controladores.ImportacionPedidos.ImportacionPedidosController",
        FakeModulo,
    )
    controlador._navegar_desde_dashboard(NAV_IMPORTAR_PEDIDOS)

    assert abierta == [True]
    vista.marcar_dashboard_sucio.assert_called_once_with()

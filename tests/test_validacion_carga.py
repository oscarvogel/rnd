# coding=utf-8
"""Issue #69: validacion de carga y bloqueo de despacho (Epic #58)."""

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from peewee import SqliteDatabase
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import QApplication


_QT_APP = QApplication.instance() or QApplication([])


_TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture()
def base_carga():
    from modelos.Clientes import (
        Cliente, Localidades, LugarEntrega, RutaReparto,
    )
    from modelos.Empleados import ConceptoLiquidacion, Empleado
    from modelos.Equipos import Equipos
    from modelos.EstadoHojaRuta import EstadoHojaRuta
    from modelos.HojaRuta import HojaDeRuta
    from modelos.ModeloBase import Auditoria
    from modelos.ModeloBase import db as db_real
    from modelos.Pallet import Pallet, PalletDetalle
    from modelos.Tablas import TipoDeMovil

    modelos = [
        Auditoria, ConceptoLiquidacion, TipoDeMovil, RutaReparto,
        Localidades, Cliente, LugarEntrega, Empleado, Equipos,
        HojaDeRuta, Pallet, PalletDetalle, EstadoHojaRuta,
    ]
    _TEST_DB.bind(modelos)
    _TEST_DB.connect()
    _TEST_DB.create_tables(modelos)
    try:
        yield {
            "RutaReparto": RutaReparto, "HojaDeRuta": HojaDeRuta,
            "Pallet": Pallet, "PalletDetalle": PalletDetalle,
            "EstadoHojaRuta": EstadoHojaRuta,
        }
    finally:
        _TEST_DB.drop_tables(modelos)
        _TEST_DB.close()
        db_real.bind(modelos)


def _hoja(HojaDeRuta, fecha, ruta_id, comprobante="F-1"):
    return HojaDeRuta.create(
        fecha=fecha, nombre_cliente="A", comprobante=comprobante,
        producto="P", cantidad=5, kg=50, cantidad_bultos=5,
        observaciones="", equipo_asignado=1, responsable=1,
        ruta=ruta_id,
    )


# --- Reglas puras ---

def test_progreso_y_faltantes():
    from utiles.carga_camion import faltantes, progreso_carga, texto_progreso

    pallets = [
        {"codigo": "PLT-1", "cargado": True},
        {"codigo": "PLT-2", "cargado": False},
    ]
    assert progreso_carga(pallets) == (1, 2)
    assert faltantes(pallets) == ["PLT-2"]
    assert "1/2" in texto_progreso(pallets)
    assert "no requiere" in texto_progreso([])


def test_mensaje_bloqueo_accionable():
    from utiles.carga_camion import mensaje_bloqueo

    assert mensaje_bloqueo([]) == ""
    mensaje = mensaje_bloqueo(["PLT-001"])
    assert "PLT-001" in mensaje and "Validar carga" in mensaje


def test_resultado_sin_pallets_informa_sin_bloquear():
    from utiles.carga_camion import resultado_con_carga
    from utiles.validacion_hoja_ruta import ItemChecklist, ResultadoValidacion

    base = ResultadoValidacion(items=(ItemChecklist("x", "X", True),))
    resultado = resultado_con_carga(base, [])
    assert len(resultado.items) == 2
    assert resultado.items[1].codigo == "carga"
    assert resultado.items[1].cumplido
    assert resultado.valida


def test_resultado_con_faltan_asignacion_frena():
    from utiles.carga_camion import resultado_con_carga
    from utiles.validacion_hoja_ruta import ItemChecklist, ResultadoValidacion

    base = ResultadoValidacion(items=(ItemChecklist("x", "X", True),))
    resultado = resultado_con_carga(
        base, [{"codigo": "PLT-1", "cargado": False}],
        faltan_asignacion=2, total_lineas=5,
    )
    assert resultado.items[1].codigo == "carga"
    assert not resultado.items[1].cumplido
    assert "2 de 5" in resultado.items[1].detalle
    assert not resultado.valida


def test_resultado_con_pallets_anexa_carga():
    from utiles.carga_camion import resultado_con_carga
    from utiles.validacion_hoja_ruta import ItemChecklist, ResultadoValidacion

    base = ResultadoValidacion(items=(ItemChecklist("x", "X", True),))
    con_carga = resultado_con_carga(
        base, [{"codigo": "PLT-1", "cargado": False}]
    )
    assert len(con_carga.items) == 2
    assert con_carga.items[1].codigo == "carga"
    assert not con_carga.valida


# --- Modelo ---

def test_marcar_y_desmarcar_registran_quien_cuando(base_carga):
    from modelos.Pallet import (
        ESTADO_ARMADO, ESTADO_CARGADO, crear_pallet, desmarcar_cargado,
        marcar_cargado,
    )

    pallet = crear_pallet()
    marcar_cargado(pallet.id, "demo")
    pallet = base_carga["Pallet"].get_by_id(pallet.id)
    assert pallet.estado == ESTADO_CARGADO
    assert pallet.cargado_por == "demo"
    assert pallet.cargado_en is not None

    desmarcar_cargado(pallet.id)
    pallet = base_carga["Pallet"].get_by_id(pallet.id)
    assert pallet.estado == ESTADO_ARMADO
    assert pallet.cargado_por == ""


def test_puede_despachar_bloquea_solo_con_pallets_pendientes(base_carga):
    from modelos.Pallet import (
        PalletDetalle, crear_pallet, marcar_cargado, puede_despachar,
    )

    fecha = date(2026, 9, 28)
    ruta = base_carga["RutaReparto"].create(descripcion="CENTRO")
    assert puede_despachar(fecha, ruta.id) == (True, [], "")

    hoja = _hoja(base_carga["HojaDeRuta"], fecha, ruta.id)
    pallet = crear_pallet()
    PalletDetalle.create(pallet=pallet.id, hoja_ruta=hoja.id,
                         cantidad=5, kg=50, bultos=5)

    ok, pendientes, mensaje = puede_despachar(fecha, ruta.id)
    assert not ok and pendientes == [pallet.codigo]
    assert pallet.codigo in mensaje

    marcar_cargado(pallet.id, "demo")
    assert puede_despachar(fecha, ruta.id) == (True, [], "")


def test_puede_despachar_frena_si_falta_asignar(base_carga):
    from modelos.Pallet import (
        PalletDetalle, crear_pallet, puede_despachar,
    )

    fecha = date(2026, 9, 28)
    ruta = base_carga["RutaReparto"].create(descripcion="CENTRO")
    hoja_a = _hoja(base_carga["HojaDeRuta"], fecha, ruta.id, "FA")
    _hoja(base_carga["HojaDeRuta"], fecha, ruta.id, "FB")
    pallet = crear_pallet()
    PalletDetalle.create(pallet=pallet.id, hoja_ruta=hoja_a.id,
                         cantidad=5, kg=50, bultos=5)

    ok, _pendientes, mensaje = puede_despachar(fecha, ruta.id)
    assert not ok
    assert "asignar" in mensaje.lower()


def test_pallets_de_hoja_filtra_fecha_ruta(base_carga):
    from modelos.Pallet import PalletDetalle, crear_pallet, pallets_de_hoja

    fecha = date(2026, 9, 28)
    ruta_a = base_carga["RutaReparto"].create(descripcion="A")
    ruta_b = base_carga["RutaReparto"].create(descripcion="B")
    hoja_a = _hoja(base_carga["HojaDeRuta"], fecha, ruta_a.id, "FA")
    _hoja(base_carga["HojaDeRuta"], fecha, ruta_b.id, "FB")
    pallet = crear_pallet()
    PalletDetalle.create(pallet=pallet.id, hoja_ruta=hoja_a.id)

    assert [p.id for p in pallets_de_hoja(fecha, ruta_a.id)] == [pallet.id]
    assert pallets_de_hoja(fecha, ruta_b.id) == []


# --- Dialogo ---

def test_dialogo_validar_carga():
    from vistas.ValidarCarga import ValidarCargaDialog

    dialogo = ValidarCargaDialog()
    dialogo.cargar_pallets([
        {"id": 1, "codigo": "PLT-001", "cargado": True, "lineas": 2},
        {"id": 2, "codigo": "PLT-002", "cargado": False, "lineas": 1},
    ])
    assert "1/2" in dialogo.lbl_progreso.text()
    assert dialogo.seleccion() == {1: True, 2: False}

    assert dialogo.marcar_codigo("plt-002") is True
    assert dialogo.seleccion() == {1: True, 2: True}
    assert dialogo.marcar_codigo("PLT-999") is False
    dialogo.close()


def test_marcar_todos_tilda_la_lista_completa():
    from vistas.ValidarCarga import ValidarCargaDialog

    dialogo = ValidarCargaDialog()
    dialogo.cargar_pallets([
        {"id": 1, "codigo": "PLT-001", "cargado": True, "lineas": 2},
        {"id": 2, "codigo": "PLT-002", "cargado": False, "lineas": 1},
        {"id": 3, "codigo": "PLT-003", "cargado": False, "lineas": 1},
    ])
    assert dialogo.cantidad_sin_tildar() == 2

    dialogo.marcar_todos()

    assert dialogo.cantidad_sin_tildar() == 0
    assert dialogo.seleccion() == {1: True, 2: True, 3: True}
    assert "3/3" in dialogo.lbl_progreso.text()
    dialogo.close()


def test_marcar_todos_no_hace_nada_si_no_falta_ninguno():
    """Con la lista ya tildada no se pregunta nada, para no molestar."""
    from vistas.ValidarCarga import ValidarCargaDialog

    dialogo = ValidarCargaDialog()
    dialogo.cargar_pallets([
        {"id": 1, "codigo": "PLT-001", "cargado": True, "lineas": 1},
        {"id": 2, "codigo": "PLT-002", "cargado": True, "lineas": 1},
    ])
    assert dialogo.cantidad_sin_tildar() == 0
    dialogo.close()


# --- Gate de despacho en el controlador ---

def _controlador(base_carga, fecha, ruta_id):
    from controladores.ValidacionHojaRuta import ValidacionHojaRutaController
    from vistas.ValidacionHojaRuta import ValidacionHojaRutaView
    from utiles.validacion_hoja_ruta import ItemChecklist, ResultadoValidacion

    controller = ValidacionHojaRutaController.__new__(
        ValidacionHojaRutaController
    )
    controller.view = ValidacionHojaRutaView()
    controller.empleado_generico = 23
    controller.camion_generico = 1
    controller.view.fecha.setDate(QDate(fecha.year, fecha.month, fecha.day))
    controller.view.cargar_rutas([(ruta_id, "RUTA")], ruta_id)
    controller.resultado_actual = ResultadoValidacion(
        items=(ItemChecklist("pedidos", "Pedidos", True),)
    )
    controller.estado_actual = "LISTA"
    controller.pallets_actuales = []
    return controller


def test_cambiar_estado_bloquea_despacho_con_pallet_sin_cargar(
    base_carga, monkeypatch
):
    from modelos.EstadoHojaRuta import EstadoHojaRuta
    from modelos.Pallet import PalletDetalle, crear_pallet, marcar_cargado

    avisos = []
    monkeypatch.setattr(
        "controladores.ValidacionHojaRuta.showAlert",
        lambda titulo, mensaje: avisos.append(mensaje),
    )

    fecha = date(2026, 9, 28)
    ruta = base_carga["RutaReparto"].create(descripcion="CENTRO")
    hoja = _hoja(base_carga["HojaDeRuta"], fecha, ruta.id)
    pallet = crear_pallet()
    from modelos.Pallet import agregar_detalle
    agregar_detalle(pallet.id, hoja.id)

    controller = _controlador(base_carga, fecha, ruta.id)
    cambiar = (controller.cambiar_estado.__wrapped__.__wrapped__)

    cambiar(controller, EstadoHojaRuta.DESPACHADA)
    assert any(pallet.codigo in aviso for aviso in avisos)
    assert EstadoHojaRuta.select().count() == 0

    marcar_cargado(pallet.id, "demo")
    cambiar(controller, EstadoHojaRuta.DESPACHADA)
    estado = EstadoHojaRuta.get(
        (EstadoHojaRuta.fecha == fecha) & (EstadoHojaRuta.ruta == ruta.id)
    )
    assert estado.estado == EstadoHojaRuta.DESPACHADA


def test_checklist_muestra_item_carga(base_carga):
    from controladores.ValidacionHojaRuta import ValidacionHojaRutaController  # noqa
    from utiles.carga_camion import resultado_con_carga
    from utiles.validacion_hoja_ruta import ItemChecklist, ResultadoValidacion
    from vistas.ValidacionHojaRuta import ValidacionHojaRutaView

    view = ValidacionHojaRutaView()
    base = ResultadoValidacion(items=(ItemChecklist("x", "X", True),))
    resultado = resultado_con_carga(
        base, [{"codigo": "PLT-001", "cargado": False}]
    )
    view.mostrar(resultado, "LISTA")
    codigos = [
        view.codigo_fila(row) for row in range(view.tabla.rowCount())
    ]
    assert "carga" in codigos
    assert not view.btn_despachar.isEnabled()
    view.close()


def test_guardar_carga_pasa_los_pallets_a_cargado(base_carga):
    """Reproduce el reporte del operador: tildar y Guardar no cambiaba nada.

    El diálogo se cerraba pero el controlador nunca llegaba a guardar: la
    comprobación comparaba contra el retorno de ``exec_()``, y ese retorno
    vale ``None`` en los formularios de pyqt5libs.
    """
    from PyQt5.QtCore import QTimer

    from modelos.Pallet import (
        ESTADO_CARGADO, agregar_detalle, crear_pallet, puede_despachar,
    )

    fecha = date(2026, 9, 28)
    ruta = base_carga["RutaReparto"].create(descripcion="CENTRO")
    hoja = _hoja(base_carga["HojaDeRuta"], fecha, ruta.id)
    pallet = crear_pallet()
    agregar_detalle(pallet.id, hoja.id)

    controller = _controlador(base_carga, fecha, ruta.id)
    abrir = controller.abrir_validar_carga.__wrapped__.__wrapped__

    capturados = {}
    dialogo_carga_real = controller.dialogo_carga

    def capturar_dialogo():
        dialogo = dialogo_carga_real()
        capturados["dialogo"] = dialogo
        return dialogo

    def operador_presiona_guardar():
        """Lo que hace el operador en la pantalla: tildar todo y Guardar."""
        dialogo = capturados["dialogo"]
        for indice in range(dialogo.lst_pallets.count()):
            dialogo.lst_pallets.item(indice).setCheckState(Qt.Checked)
        dialogo.btn_guardar.click()

    controller.dialogo_carga = capturar_dialogo
    QTimer.singleShot(0, operador_presiona_guardar)
    abrir(controller)

    guardado = base_carga["Pallet"].get_by_id(pallet.id)
    assert guardado.estado == ESTADO_CARGADO, (
        "el operador tildó el pallet y presionó Guardar, pero quedó en {}".format(
            guardado.estado
        )
    )
    assert guardado.cargado_en is not None

    ok, pendientes, _mensaje = puede_despachar(fecha, ruta.id)
    assert ok and not pendientes, "con el pallet cargado la hoja debería despachar"


def test_cancelar_carga_no_guarda_nada(base_carga):
    """Contraprueba: con Cancelar el pallet tiene que seguir ARMADO.

    Corrige en la dirección opuesta a la anterior: cambiar la comprobación
    por result() no debe convertir a Cancelar en un guardado.
    """
    from PyQt5.QtCore import QTimer

    from modelos.Pallet import ESTADO_ARMADO, agregar_detalle, crear_pallet

    fecha = date(2026, 9, 28)
    ruta = base_carga["RutaReparto"].create(descripcion="CENTRO")
    hoja = _hoja(base_carga["HojaDeRuta"], fecha, ruta.id)
    pallet = crear_pallet()
    agregar_detalle(pallet.id, hoja.id)

    controller = _controlador(base_carga, fecha, ruta.id)
    abrir = controller.abrir_validar_carga.__wrapped__.__wrapped__

    capturados = {}
    dialogo_carga_real = controller.dialogo_carga

    def capturar_dialogo():
        dialogo = dialogo_carga_real()
        capturados["dialogo"] = dialogo
        return dialogo

    def operador_presiona_cancelar():
        dialogo = capturados["dialogo"]
        for indice in range(dialogo.lst_pallets.count()):
            dialogo.lst_pallets.item(indice).setCheckState(Qt.Checked)
        dialogo.btn_cancelar.click()

    controller.dialogo_carga = capturar_dialogo
    QTimer.singleShot(0, operador_presiona_cancelar)
    abrir(controller)

    guardado = base_carga["Pallet"].get_by_id(pallet.id)
    assert guardado.estado == ESTADO_ARMADO, (
        "con Cancelar no se debe guardar nada, pero quedó en {}".format(
            guardado.estado
        )
    )


def test_marcar_todos_respondiendo_que_no_no_tilda(base_carga):
    """Si el operador dice que no, la lista queda como estaba."""
    from modelos.Pallet import agregar_detalle, crear_pallet

    fecha = date(2026, 9, 28)
    ruta = base_carga["RutaReparto"].create(descripcion="CENTRO")
    hoja = _hoja(base_carga["HojaDeRuta"], fecha, ruta.id)
    pallet = crear_pallet()
    agregar_detalle(pallet.id, hoja.id)

    controller = _controlador(base_carga, fecha, ruta.id)
    controller._preguntar_marcar_todos = lambda *args: False
    dialogo = controller.dialogo_carga()

    controller.confirmar_marcar_todos(dialogo)

    assert dialogo.cantidad_sin_tildar() == 1
    assert dialogo.seleccion() == {pallet.id: False}
    dialogo.Cerrar()


def test_marcar_todos_y_guardar_deja_la_carga_lista(base_carga):
    """Flujo completo del atajo: Marcar todos -> Guardar -> CARGADO.

    Es el camino que va a usar el operador cuando el camión ya está cargado
    de corrido, en lugar de veinte tildadas o veinte escaneos.
    """
    from PyQt5.QtCore import QTimer

    from modelos.Pallet import (
        ESTADO_CARGADO, agregar_detalle, crear_pallet, puede_despachar,
    )

    fecha = date(2026, 9, 28)
    ruta = base_carga["RutaReparto"].create(descripcion="CENTRO")
    hoja = _hoja(base_carga["HojaDeRuta"], fecha, ruta.id)
    pallets = [crear_pallet() for _ in range(3)]
    # Reparte la línea completa entre los tres pallets (5 cant / 50 KG /
    # 5 bultos): con saldo sin asignar el despacho frena por otro motivo.
    for pallet, (cantidad, kg, bultos) in zip(
        pallets, [(1, 10, 1), (1, 10, 1), (3, 30, 3)]
    ):
        agregar_detalle(pallet.id, hoja.id, cantidad, kg, bultos)

    controller = _controlador(base_carga, fecha, ruta.id)
    controller._preguntar_marcar_todos = lambda *args: True
    abrir = controller.abrir_validar_carga.__wrapped__.__wrapped__

    capturados = {}
    dialogo_carga_real = controller.dialogo_carga

    def capturar_dialogo():
        dialogo = dialogo_carga_real()
        capturados["dialogo"] = dialogo
        return dialogo

    def operador_carga_el_camion():
        dialogo = capturados["dialogo"]
        dialogo.btn_todos.click()      # atajo, sin tildar uno por uno
        dialogo.btn_guardar.click()

    controller.dialogo_carga = capturar_dialogo
    QTimer.singleShot(0, operador_carga_el_camion)
    abrir(controller)

    for pallet in pallets:
        guardado = base_carga["Pallet"].get_by_id(pallet.id)
        assert guardado.estado == ESTADO_CARGADO, (
            "el pallet {} quedó en {}".format(pallet.codigo, guardado.estado)
        )
        assert guardado.cargado_en is not None

    ok, pendientes, _mensaje = puede_despachar(fecha, ruta.id)
    assert ok and not pendientes


def test_doble_clic_carga_navega_segun_faltante(base_carga, monkeypatch):
    from vistas.ValidacionHojaRuta import ValidacionHojaRutaView
    from utiles.carga_camion import resultado_con_carga
    from utiles.validacion_hoja_ruta import ItemChecklist, ResultadoValidacion
    from controladores.ValidacionHojaRuta import ValidacionHojaRutaController

    destinos = []
    monkeypatch.setattr(
        ValidacionHojaRutaController, "ir_armado",
        lambda self: destinos.append("armado"),
    )
    monkeypatch.setattr(
        ValidacionHojaRutaController, "abrir_validar_carga",
        lambda self, *a, **k: destinos.append("dialogo"),
    )

    controller = ValidacionHojaRutaController.__new__(
        ValidacionHojaRutaController
    )
    controller.view = ValidacionHojaRutaView()

    base = ResultadoValidacion(items=(ItemChecklist("x", "X", True),))
    controller.resultado_actual = resultado_con_carga(
        base, [{"codigo": "PLT-1", "cargado": False}],
        faltan_asignacion=1, total_lineas=2,
    )
    controller.faltan_asignacion = 1
    controller.view.mostrar(controller.resultado_actual, "LISTA")
    fila = next(
        row for row in range(controller.view.tabla.rowCount())
        if controller.view.codigo_fila(row) == "carga"
    )
    controller.resolver_pendiente(fila, 0)
    assert destinos == ["armado"]

    controller.faltan_asignacion = 0
    controller.resolver_pendiente(fila, 0)
    assert destinos == ["armado", "dialogo"]
    controller.view.close()

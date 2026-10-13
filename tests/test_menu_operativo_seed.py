# coding=utf-8
"""El menú del shell moderno es DATA (formula/menu_lateral), no código.

Producción nunca recibió el seed (sólo existía en demo_seed), así que
mostraba la navegación vieja con el código nuevo. El seed compartido
(utiles.menu_operativo) debe ser idempotente, aditivo (no toca filas
legacy) y reparar derivas. Se prueba contra SQLite en memoria con el
patrón habitual de bind/create/drop.
"""
import pytest
from peewee import SqliteDatabase

_TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture()
def base_menu():
    from modelos.Formula import Formula, MenuLateral
    from modelos.ModeloBase import Auditoria
    from modelos.ModeloBase import db as db_real

    modelos = [Auditoria, Formula, MenuLateral]
    _TEST_DB.bind(modelos)
    _TEST_DB.connect()
    _TEST_DB.create_tables(modelos)
    try:
        yield {"Formula": Formula, "MenuLateral": MenuLateral}
    finally:
        _TEST_DB.drop_tables(modelos)
        _TEST_DB.close()
        db_real.bind(modelos)


def _contar(modelo):
    return modelo.select().count()


def test_seed_crea_cabeceras_y_opciones(base_menu):
    from utiles.menu_operativo import OPCIONES_OPERATIVAS, asegurar_menu_operativo

    asegurar_menu_operativo(sis_id=1)

    Formula = base_menu["Formula"]
    MenuLateral = base_menu["MenuLateral"]

    cabeceras = list(
        MenuLateral.select().where(MenuLateral.for_pare == 0).order_by(MenuLateral.nombre)
    )
    assert [c.nombre for c in cabeceras] == ["MAESTROS", "OPERACIONES"]

    items = list(MenuLateral.select().where(MenuLateral.for_pare != 0))
    assert len(items) == len(OPCIONES_OPERATIVAS)

    for _cab, nombre, archivo, valid, _orden, _imag in OPCIONES_OPERATIVAS:
        formula = Formula.get(
            Formula.for_nomb == nombre,
            Formula.sis_id == 1,
            Formula.for_valid == valid,
        )
        assert formula.for_arch == archivo
        item = MenuLateral.get(MenuLateral.nombre == nombre)
        assert item.for_id.for_id == formula.for_id


def test_seed_es_idempotente(base_menu):
    from utiles.menu_operativo import asegurar_menu_operativo

    Formula = base_menu["Formula"]
    MenuLateral = base_menu["MenuLateral"]

    asegurar_menu_operativo(sis_id=1)
    n_formulas = _contar(Formula)
    n_items = _contar(MenuLateral)

    asegurar_menu_operativo(sis_id=1)
    asegurar_menu_operativo(sis_id=1)

    assert _contar(Formula) == n_formulas
    assert _contar(MenuLateral) == n_items


def test_seed_no_toca_filas_legacy(base_menu):
    """Una fórmula legacy homónima con otro valid no se secuestra."""
    from utiles.menu_operativo import asegurar_menu_operativo

    Formula = base_menu["Formula"]
    MenuLateral = base_menu["MenuLateral"]

    legacy = Formula.create(
        for_nomb="Clientes", sis_id=1, tfo_id=1, for_orde=99,
        for_pare=1234, for_arch="Legado.OtraCosa()", for_imag="",
        gfo_id=0, for_valid="LEGADO",
    )

    asegurar_menu_operativo(sis_id=1)

    legacy_recargado = Formula.get_by_id(legacy.for_id)
    assert legacy_recargado.for_arch == "Legado.OtraCosa()"
    assert legacy_recargado.for_pare == 1234

    nueva = Formula.get(
        Formula.for_nomb == "Clientes",
        Formula.sis_id == 1,
        Formula.for_valid == "ABM_CLIENTES",
    )
    assert nueva.for_id != legacy.for_id


def test_seed_repara_deriva_sin_duplicar(base_menu):
    from utiles.menu_operativo import asegurar_menu_operativo

    Formula = base_menu["Formula"]
    MenuLateral = base_menu["MenuLateral"]

    asegurar_menu_operativo(sis_id=1)
    n_formulas = _contar(Formula)
    n_items = _contar(MenuLateral)

    formula = Formula.get(
        Formula.for_nomb == "Importar pedidos",
        Formula.for_valid == "IMPORTAR_PEDIDOS",
    )
    formula.for_arch = "Roto.NoExiste()"
    formula.save()

    asegurar_menu_operativo(sis_id=1)

    assert _contar(Formula) == n_formulas
    assert _contar(MenuLateral) == n_items
    assert (
        Formula.get_by_id(formula.for_id).for_arch
        == "ImportacionPedidos.ImportacionPedidosController"
    )


def test_seed_demo_agrega_seccion_demo(base_menu):
    from utiles.menu_operativo import asegurar_menu_operativo

    MenuLateral = base_menu["MenuLateral"]

    asegurar_menu_operativo(sis_id=1, incluir_demo=True)

    assert (
        MenuLateral.select()
        .where(MenuLateral.nombre == "DEMO", MenuLateral.for_pare == 0)
        .count()
    ) == 1
    assert (
        MenuLateral.select()
        .where(MenuLateral.nombre == "Restablecer datos demo")
        .count()
    ) == 1


def test_fase_menu_operativo_no_aborta_el_login_si_falla(monkeypatch):
    """El seed de menú no debe voltear el arranque (como los backfills)."""
    import controladores.Migraciones as modulo_migraciones

    def _romper():
        raise RuntimeError("formula caída")

    monkeypatch.setattr(
        modulo_migraciones, "asegurar_menu_operativo", _romper
    )

    migracion = modulo_migraciones.MigracionBaseDatos.__new__(
        modulo_migraciones.MigracionBaseDatos
    )
    # No debe propagar la excepción.
    migracion._fase_menu_operativo()


def test_gfo_hereda_grupo_de_cabeceras_existentes(base_menu):
    """Producción tiene FK formula.gfo_id -> gruform: el 0 no sirve (1452)."""
    from utiles.menu_operativo import _gfo_valido, asegurar_menu_operativo

    Formula = base_menu["Formula"]

    Formula.create(
        for_nomb="Archivo", sis_id=1, tfo_id=1, for_orde=1,
        for_pare=0, for_arch="", for_imag="", gfo_id=3, for_valid="",
    )

    assert _gfo_valido(1) == 3

    asegurar_menu_operativo(sis_id=1)

    grupos = {
        fila.for_nomb: fila.gfo_id
        for fila in Formula.select().where(
            Formula.for_nomb.in_(["Operaciones", "Importar pedidos"])
        )
    }
    assert grupos == {"Operaciones": 3, "Importar pedidos": 3}


def test_gfo_usa_gruform_si_no_hay_cabeceras(base_menu):
    from utiles.menu_operativo import _gfo_valido, asegurar_menu_operativo

    Formula = base_menu["Formula"]

    _TEST_DB.execute_sql("CREATE TABLE gruform (gfo_id INTEGER PRIMARY KEY)")
    try:
        _TEST_DB.execute_sql("INSERT INTO gruform (gfo_id) VALUES (9)")

        assert _gfo_valido(1) == 9

        asegurar_menu_operativo(sis_id=1)

        formula = Formula.get(
            Formula.for_nomb == "Operaciones", Formula.for_valid == ""
        )
        assert formula.gfo_id == 9
    finally:
        _TEST_DB.execute_sql("DROP TABLE gruform")


def test_gfo_fallback_cero_sin_grupo(base_menu):
    """Sin cabeceras ni gruform (SQLite demo) se mantiene el 0 histórico."""
    from utiles.menu_operativo import _gfo_valido, asegurar_menu_operativo

    Formula = base_menu["Formula"]

    assert _gfo_valido(1) == 0

    asegurar_menu_operativo(sis_id=1)

    formula = Formula.get(
        Formula.for_nomb == "Operaciones", Formula.for_valid == ""
    )
    assert formula.gfo_id == 0

from types import SimpleNamespace

from peewee import SqliteDatabase

from demo_seed import _asegurar_lugares_entrega_multi_direccion
from utiles.lugares_entrega import (
    clave_duplicado,
    mismo_destino,
    resolver_lugar_entrega,
)


def lugar(nombre, localidad="", direccion="", activo=True):
    return SimpleNamespace(
        nombre=nombre,
        direccion=direccion,
        localidad=SimpleNamespace(descripcion=localidad) if localidad else None,
        activo=activo,
    )


def test_unico_lugar_se_autoselecciona_sin_observaciones():
    unico = lugar("Puerto Rico", "Puerto Rico")
    assert resolver_lugar_entrega("", [unico]) is unico


def test_resuelve_por_localidad_en_observaciones():
    puerto_rico = lugar("Sucursal Puerto Rico", "Puerto Rico")
    san_vicente = lugar("Sucursal San Vicente", "San Vicente")
    assert resolver_lugar_entrega(
        "Entregar mercadería en SAN VICENTE",
        [puerto_rico, san_vicente],
    ) is san_vicente


def test_resuelve_ignorando_tildes_y_mayusculas():
    obere = lugar("Oberá", "Oberá")
    apostoles = lugar("Apóstoles", "Apóstoles")
    assert resolver_lugar_entrega("ENTREGA EN OBERA", [obere, apostoles]) is obere


def test_ambiguedad_no_asigna_lugar():
    uno = lugar("Depósito Norte", "Posadas")
    dos = lugar("Sucursal Posadas", "Posadas")
    assert resolver_lugar_entrega("Entregar en Posadas", [uno, dos]) is None


def test_sin_match_queda_pendiente():
    uno = lugar("Puerto Rico", "Puerto Rico")
    dos = lugar("San Vicente", "San Vicente")
    assert resolver_lugar_entrega("Entregar en obra", [uno, dos]) is None


def test_clave_duplicado_prioriza_comprobante():
    clave_a = clave_duplicado(10, "2026-09-09", "Tablas 2x4", "A-001")
    clave_b = clave_duplicado(10, "2026-09-09", "Tablas 2x4", "A-002")
    assert clave_a != clave_b


def test_clave_duplicado_sin_comprobante_mantiene_compatibilidad():
    clave = clave_duplicado(10, "2026-09-09", "Tablas 2x4", "")
    assert clave == ("10", "2026-09-09", "tablas 2x4")



def test_misma_referencia_con_otra_direccion_no_es_duplicado():
    assert not mismo_destino(
        "Palmesano",
        "Los Campos",
        "Palmesano",
        "Ruta 12 Km 8",
    )


def test_mismo_nombre_y_misma_direccion_si_es_duplicado():
    assert mismo_destino(
        "  PALMESANO ",
        "Los Campos 123",
        "Palmesano",
        "los campos 123",
    )


def test_demo_migra_unique_legacy_y_permite_mismo_nombre_otra_direccion():
    db = SqliteDatabase(":memory:")
    db.connect()
    try:
        db.execute_sql(
            "CREATE TABLE lugares_entrega ("
            "id INTEGER PRIMARY KEY, "
            "cliente_id INTEGER NOT NULL, "
            "nombre TEXT NOT NULL, "
            "direccion TEXT)"
        )
        db.execute_sql(
            "CREATE UNIQUE INDEX legacy_lugar_nombre "
            "ON lugares_entrega(cliente_id, nombre)"
        )

        _asegurar_lugares_entrega_multi_direccion(db)

        db.execute_sql(
            "INSERT INTO lugares_entrega(cliente_id, nombre, direccion) "
            "VALUES (1, 'Palmesano', 'Los Campos')"
        )
        db.execute_sql(
            "INSERT INTO lugares_entrega(cliente_id, nombre, direccion) "
            "VALUES (1, 'Palmesano', 'Ruta 12 Km 8')"
        )

        filas = db.execute_sql(
            "SELECT COUNT(*) FROM lugares_entrega "
            "WHERE cliente_id = 1 AND nombre = 'Palmesano'"
        ).fetchone()
        assert filas[0] == 2
    finally:
        db.close()

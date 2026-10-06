# coding=utf-8
"""Compatibilidad de esquema para pallets en la base SQLite del demo."""


def asegurar_contexto_pallet_demo(db) -> None:
    """Agrega en forma idempotente las columnas de contexto a ``pallet``.

    ``create_tables(..., safe=True)`` no altera tablas SQLite ya existentes.
    Por eso un demo creado antes de incorporar el contexto operativo de pallets
    puede conservar el esquema viejo aunque el modelo Peewee ya tenga los campos.
    """
    try:
        columnas = {col.name for col in db.get_columns("pallet")}
    except Exception:
        return

    migraciones = (
        ("cargado_por", "VARCHAR(100) NOT NULL DEFAULT ''"),
        ("cargado_en", "DATETIME"),
        ("fecha_reparto", "DATE"),
        ("ruta_id", "INTEGER"),
        ("responsable_id", "INTEGER"),
        ("equipo_id", "INTEGER"),
    )
    for nombre, definicion in migraciones:
        if nombre in columnas:
            continue
        db.execute_sql(
            "ALTER TABLE pallet ADD COLUMN {} {}".format(nombre, definicion)
        )
        columnas.add(nombre)

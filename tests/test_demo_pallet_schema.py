from peewee import SqliteDatabase

from utiles.demo_pallet_schema import asegurar_contexto_pallet_demo


def test_agrega_columnas_contexto_a_pallet_legacy():
    db = SqliteDatabase(":memory:")
    db.connect()
    try:
        db.execute_sql(
            "CREATE TABLE pallet ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "codigo VARCHAR(40) NOT NULL UNIQUE, "
            "estado VARCHAR(30) NOT NULL DEFAULT 'ARMADO', "
            "observaciones TEXT, "
            "creado DATE"
            ")"
        )

        asegurar_contexto_pallet_demo(db)
        asegurar_contexto_pallet_demo(db)

        columnas = {col.name for col in db.get_columns("pallet")}
        assert {
            "cargado_por",
            "cargado_en",
            "fecha_reparto",
            "ruta_id",
            "responsable_id",
            "equipo_id",
        }.issubset(columnas)
    finally:
        db.close()

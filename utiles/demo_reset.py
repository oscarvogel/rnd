# coding=utf-8
"""Reset seguro de la base local de RND DEMO.

Solo opera cuando:
- RND_DEMO_MODE=1
- la base activa es SQLite
- el archivo activo es sistema.db

Nunca toca MySQL ni otra base local.
"""

import os
from pathlib import Path

from peewee import SqliteDatabase


class DemoResetError(RuntimeError):
    pass


def validar_reset_demo(db) -> Path:
    if os.getenv("RND_DEMO_MODE") != "1":
        raise DemoResetError("El restablecimiento solo está disponible en RND DEMO.")

    if not isinstance(db, SqliteDatabase):
        raise DemoResetError("El restablecimiento solo está permitido sobre SQLite.")

    database = str(getattr(db, "database", "") or "").strip()
    if not database:
        raise DemoResetError("No se pudo identificar la base SQLite del demo.")

    ruta = Path(database)
    if ruta.name.lower() != "sistema.db":
        raise DemoResetError(
            "Por seguridad solo se puede restablecer la base sistema.db del demo."
        )
    return ruta.resolve()


def _vaciar_esquema_sqlite(db) -> None:
    """Elimina todas las tablas de la SQLite DEMO para volver a cero real."""
    try:
        db.connect(reuse_if_open=True)
        db.execute_sql("PRAGMA foreign_keys = OFF")
        filas = db.execute_sql(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

        with db.atomic():
            for (nombre,) in filas:
                seguro = str(nombre).replace('"', '""')
                db.execute_sql('DROP TABLE IF EXISTS "{}"'.format(seguro))

        db.execute_sql("PRAGMA foreign_keys = ON")
    except Exception as exc:
        raise DemoResetError(
            "No se pudo limpiar completamente la base DEMO."
        ) from exc
    finally:
        try:
            if not db.is_closed():
                db.close()
        except Exception:
            pass


def resetear_datos_demo() -> Path:
    """Vacía toda la SQLite DEMO, recrea schema+seed y devuelve su ruta."""
    from modelos.ModeloBase import db
    from demo_seed import prepare_demo_database

    ruta = validar_reset_demo(db)
    _vaciar_esquema_sqlite(db)

    # El seed es la única fuente de datos posterior al reset.
    prepare_demo_database()
    return ruta

# coding=utf-8
"""Reset seguro de la base local de RND DEMO.

Esta utilidad solo puede operar cuando:
- RND_DEMO_MODE=1
- la base activa es SQLite
- el archivo activo es sistema.db

Nunca debe borrar ni tocar una base MySQL de producción.
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


def resetear_datos_demo() -> Path:
    """Borra la SQLite demo, regenera el seed y devuelve la ruta recreada."""
    from modelos.ModeloBase import db
    from demo_seed import prepare_demo_database

    ruta = validar_reset_demo(db)

    try:
        if not db.is_closed():
            db.close()
    except Exception as exc:
        raise DemoResetError(
            "No se pudo cerrar la base DEMO antes de restablecerla."
        ) from exc

    for archivo in (
        ruta,
        Path(str(ruta) + "-wal"),
        Path(str(ruta) + "-shm"),
    ):
        try:
            if archivo.exists():
                archivo.unlink()
        except OSError as exc:
            raise DemoResetError(
                "No se pudo borrar {}. Cierre otras ventanas de RND DEMO e intente nuevamente.".format(
                    archivo.name
                )
            ) from exc

    prepare_demo_database()
    return ruta

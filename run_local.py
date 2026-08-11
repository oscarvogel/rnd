# coding=utf-8
"""Launcher exclusivo para desarrollo local de RND.

Produccion sigue arrancando con ``python main.py`` y usa ``sistema.ini``.
Este launcher fuerza un INI y una credencial DPAPI independientes.
"""

import os
import shutil
import sys
from pathlib import Path


LOCAL_PROFILE = "local"
LOCAL_INI = "sistema.local.ini"
LOCAL_TEMPLATE = "sistema.local.ini.example"


def _prepare_local_config(base_dir: Path) -> bool:
    target = base_dir / LOCAL_INI
    if target.exists():
        return True

    template = base_dir / LOCAL_TEMPLATE
    if not template.exists():
        print("ERROR: falta {}.".format(template), file=sys.stderr)
        return False

    shutil.copyfile(str(template), str(target))
    print("Se creo {} desde la plantilla.".format(target))
    print("Revise host, base de datos y usuario y vuelva a ejecutar python run_local.py.")
    return False


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    if not _prepare_local_config(base_dir):
        return 2

    # Aisla la credencial local de la credencial historica de produccion.
    os.environ["RND_CREDENTIAL_PROFILE"] = LOCAL_PROFILE
    os.environ["RND_ENV"] = "local"

    print("=" * 66)
    print("RND - ENTORNO LOCAL / DESARROLLO")
    print("Configuracion: {}".format(base_dir / LOCAL_INI))
    print("La configuracion y credencial de PRODUCCION no se modifican.")
    print("=" * 66)

    import main as rnd_main

    return rnd_main.inicio(["-i", str(base_dir), "-a", LOCAL_INI])


if __name__ == "__main__":
    sys.exit(main())

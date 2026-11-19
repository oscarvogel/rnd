# coding=utf-8
r"""Carga manual del seed Tacural sobre RND DEMO.

Uso:
    .\.venv\Scripts\python.exe .\scripts\seed_tacural_demo.py

El script fuerza sistema.demo.ini / SQLite y no toca MySQL.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["RND_DEMO_MODE"] = "1"
os.environ["RND_CREDENTIAL_PROFILE"] = "demo"
sys.argv = [sys.argv[0], "-a", "sistema.demo.ini"]


def main() -> int:
    from pyqt5libs.pyqt5libs.utiles import BorrarConf, GrabaConf

    BorrarConf()
    GrabaConf(clave="iniciosistema", valor=str(ROOT) + os.sep)
    GrabaConf(clave="archivoini", valor="sistema.demo.ini")
    GrabaConf(clave="DEBUG", valor=True)
    GrabaConf(clave="Reconecta", valor=True)
    GrabaConf(clave="usuario", valor="demo")

    # Asegura que el schema base del DEMO exista.
    from demo_seed import prepare_demo_database
    from utiles.seed_tacural import seed_tacural

    prepare_demo_database()
    resumen = seed_tacural()

    print("[RND DEMO] Seed Tacural OK")
    print("  Proveedor: {} (id={})".format(
        resumen["proveedor"], resumen["proveedor_id"]
    ))
    print("  Clientes: {}".format(resumen["clientes"]))
    print("  Codigos proveedor: {}".format(resumen["codigos"]))
    print("  Localidades: {}".format(resumen["localidades"]))
    print("")
    print("Ya puede abrir .\\demo.ps1 e importar el PDF seleccionando:")
    print("  CHACINADOS TACURAL SRL")
    print("  (archivo: demo_importaciones\\05_proveedor_tacural.pdf)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

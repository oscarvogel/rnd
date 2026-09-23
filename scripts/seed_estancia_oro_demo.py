# coding=utf-8
"""Carga manual del seed La Estancia de Oro sobre RND DEMO.

Uso:
    .\.venv\Scripts\python.exe .\scripts\seed_estancia_oro_demo.py

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
    from utiles.seed_estancia_oro import seed_estancia_oro

    prepare_demo_database()
    resumen = seed_estancia_oro()

    print("[RND DEMO] Seed La Estancia de Oro OK")
    print("  Proveedor: {} (id={})".format(
        resumen["proveedor"], resumen["proveedor_id"]
    ))
    print("  Clientes: {}".format(resumen["clientes"]))
    print("  Codigos proveedor: {}".format(resumen["codigos"]))
    print("  Localidades: {}".format(resumen["localidades"]))
    print("")
    print("Ya puede abrir .\\demo.ps1 e importar el PDF seleccionando:")
    print("  LA ESTANCIA DE ORO S.A.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

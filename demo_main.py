# coding=utf-8
"""Entrypoint aislado para RND DEMO.

No solicita credenciales MySQL. Configura RND contra SQLite local,
crea el schema necesario y carga datos de demostracion idempotentes.
"""

import os
import sys
from pathlib import Path


def _app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def main() -> int:
    root = _app_root()
    os.chdir(root)
    os.environ["RND_DEMO_MODE"] = "1"
    os.environ["RND_CREDENTIAL_PROFILE"] = "demo"
    # LeerIni() elige el INI por CLI (-a/--archivo) o FGPY_CONFIG; no lee
    # GrabaConf("archivoini"). Sin esto el demo caeria en sistema.ini (mysql).
    sys.argv = [sys.argv[0], "-a", "sistema.demo.ini"]

    from pyqt5libs.pyqt5libs.utiles import (
        BorrarConf,
        GrabaConf,
        LeerIni,
        icono_sistema,
        initialize_logger,
    )

    BorrarConf()
    GrabaConf(clave="iniciosistema", valor=str(root) + os.sep)
    GrabaConf(clave="archivoini", valor="sistema.demo.ini")
    GrabaConf(clave="DEBUG", valor=True)
    GrabaConf(clave="Reconecta", valor=True)
    GrabaConf(clave="usuario", valor="demo")

    from demo_seed import prepare_demo_database

    prepare_demo_database()

    from PyQt5.QtWidgets import QApplication
    from utiles.tema import aplicar_tema
    from controladores.Main import MainController

    initialize_logger(LeerIni("iniciosistema", carpeta=str(root) + os.sep))
    app = QApplication([])
    app.setWindowIcon(icono_sistema())
    aplicar_tema(app)

    controller = MainController()
    if controller.login():
        controller.run()
        return app.exec_()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
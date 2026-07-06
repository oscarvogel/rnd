# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

#Punto de Inicio del sistema
import argparse
import configparser
import logging
import os
import sys
from pathlib import Path

from pyqt5libs.pyqt5libs.utiles import BorrarConf, GrabaConf, LeerIni, initialize_logger

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2025"
__license__ = "GPL 3.0"
__version__ = "0.1"

def _build_arg_parser():
    analizador = argparse.ArgumentParser(description='Sistema.')
    analizador.add_argument("-i", "--inicio", default=os.getcwd(), help="Carpeta de Inicio de sistema.")
    analizador.add_argument("-a", "--archivo", default="sistema.ini", help="Archivo de Configuracion de sistema.")
    analizador.add_argument(
        "--startup-check",
        action="store_true",
        help="Valida configuracion y recursos sin abrir la interfaz.",
    )
    return analizador


def _validate_startup(inicio, archivo):
    carpeta_inicio = Path(inicio).resolve()
    archivo_ini = carpeta_inicio / archivo
    required_paths = [
        archivo_ini,
        carpeta_inicio / "imagenes",
        carpeta_inicio / "temas",
        carpeta_inicio / "sistema.ini",
        carpeta_inicio / "rnd.ini",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        return False, "faltan recursos requeridos: {}".format(", ".join(missing))

    config = configparser.ConfigParser()
    if not config.read(archivo_ini, encoding="utf-8"):
        return False, "no se pudo leer {}".format(archivo_ini)
    if not config.has_section("param"):
        return False, "{} no tiene la seccion [param]".format(archivo_ini)

    required_keys = ["host", "basedatos", "port", "icono", "logo", "iniciosistema"]
    missing_keys = [
        key for key in required_keys
        if not config.get("param", key, fallback="").strip()
    ]
    if missing_keys:
        return False, "{} no tiene parametros requeridos: {}".format(
            archivo_ini,
            ", ".join(missing_keys),
        )

    media_paths = [
        carpeta_inicio / "imagenes" / config.get("param", "icono"),
        carpeta_inicio / "imagenes" / config.get("param", "logo"),
    ]
    missing_media = [str(path) for path in media_paths if not path.exists()]
    if missing_media:
        return False, "faltan archivos de marca: {}".format(", ".join(missing_media))

    return True, "inicio={} archivo={}".format(carpeta_inicio, archivo_ini)


def inicio(argv=None):
    BorrarConf()
    argumento = _build_arg_parser().parse_args(argv)
    carpeta = argumento.inicio + "\\"
    GrabaConf(clave="iniciosistema", valor=carpeta)
    GrabaConf(clave="archivoini", valor=argumento.archivo)

    if argumento.startup_check:
        ok, message = _validate_startup(argumento.inicio, argumento.archivo)
        if ok:
            print("STARTUP_CHECK_OK {}".format(message))
            return 0
        print("STARTUP_CHECK_ERROR {}".format(message), file=sys.stderr)
        return 1

    from PyQt5.QtWidgets import QApplication
    from controladores.Main import MainController
    from pyqt5libs.pyqt5libs.utiles import icono_sistema

    # print("PATH del archivo {}".format(sys.argv[1]))

    # carpeta, archivo = os.path.split(os.path.abspath(__file__))
    # print(len(sys.argv))
    # if len(sys.argv) > 1:
    #     carpeta = sys.argv[1] + "\\"
    #     GrabaConf(clave="iniciosistema", valor=sys.argv[1] + "\\")
    # else:
    #     carpeta = ""
    initialize_logger(LeerIni("iniciosistema", carpeta=carpeta))
    logging.basicConfig()
    logging.debug("carpeta inicio{} archivo de inicio {}".format(argumento.inicio, argumento.archivo))
    print("carpeta inicio{} archivo de inicio {}".format(argumento.inicio, argumento.archivo))
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    sys.path.insert(0, LeerIni("iniciosistema", carpeta=carpeta))
    # if len(sys.argv) > 1:
    #     logging.debug("inicio de sistema {}".format(sys.argv[1]))
    GrabaConf(clave="DEBUG", valor=True)
    GrabaConf(clave="Reconecta", valor=True)
    GrabaConf(clave="usuario", valor=os.getenv("RND_DB_USER", LeerIni("user") or ""))
    db_password = os.getenv("RND_DB_PASSWORD") or os.getenv("MYSQL_PASSWORD")
    if db_password:
        GrabaConf(clave="password", valor=db_password)

    # ModeloBase().init()
    args = []
    #args = ['', '-style', 'Cleanlooks']
    # myStyle = MyProxyStyle('Fusion')
    app = QApplication(args)
    app.setWindowIcon(icono_sistema())
    # app.setStyle(myStyle)
    ex = MainController()
    # ex.view.ImagenFondo()
    if ex.login():
        ex.run()
        return app.exec_()
    return 0

if __name__ == "__main__":
    sys.exit(inicio())

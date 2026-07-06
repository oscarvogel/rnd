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
import logging
import os
import sys

from PyQt5.QtWidgets import QApplication

from controladores.Main import MainController
from pyqt5libs.pyqt5libs.utiles import BorrarConf, GrabaConf, LeerIni, icono_sistema, initialize_logger

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2025"
__license__ = "GPL 3.0"
__version__ = "0.1"

def inicio():
    BorrarConf()
    # print("PATH del archivo {}".format(sys.argv[1]))

    # carpeta, archivo = os.path.split(os.path.abspath(__file__))
    # print(len(sys.argv))
    analizador = argparse.ArgumentParser(description='Sistema.')
    analizador.add_argument("-i", "--inicio", default=os.getcwd(), help="Carpeta de Inicio de sistema.")
    analizador.add_argument("-a", "--archivo", default="sistema.ini", help="Archivo de Configuracion de sistema.")
    argumento = analizador.parse_args()
    carpeta = argumento.inicio + "\\"
    GrabaConf(clave="iniciosistema", valor=carpeta)
    GrabaConf(clave="archivoini", valor=argumento.archivo)
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
        sys.exit(app.exec_())

if __name__ == "__main__":
    inicio()

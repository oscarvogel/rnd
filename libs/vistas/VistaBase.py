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

#Vista base del cual derivan todos las vistas del sistema


__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2021 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.Formulario import Formulario
from pyqt5libs.pyqt5libs.utiles import icono_sistema, imagen


class VistaBase(Formulario):

    LanzarExcepciones = False
    HuboError = False  # se usa para indicar si ocurrio un error o no

    def __init__(self, *args, **kwargs):
        Formulario.__init__(self)
        self.setWindowIcon(icono_sistema())

    def initUi(self):
        pass

    def cerrarformulario(self):
        self.close()

    def CreaBoton(self, texto, tooltip=None, imagen_str=None):
        """_summary_

        Args:
            texto (str): Texto a mostrar en el botón.
            tooltip (_type_str, optional): Tooltip del boton. Defaults to None.
            imagen (str, optional): Imagen para mostrar en el boton. Defaults to None.

        Returns:
            boton: Retorna un objeto Boton configurado con el texto, tooltip e imagen proporcionados.
        """
        boton = Boton(texto=texto, tooltip=tooltip, imagen=imagen(imagen_str))
        return boton
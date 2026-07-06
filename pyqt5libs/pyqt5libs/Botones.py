# coding=utf-8
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtWidgets import QPushButton, QToolButton

from .utiles import LeerIni, imagen


class Boton(QPushButton):

    def __init__(self, *args, **kwargs):
        QPushButton.__init__(self, *args)

        texto = ''
        if 'texto' in kwargs:
            texto = kwargs['texto']

        self.setText(texto)

        if 'imagen' in kwargs:
            icono = QIcon(kwargs['imagen'])
            self.setIcon(icono)

            if 'tamanio' in kwargs:
                if kwargs['tamanio'] and isinstance(kwargs['tamanio'], QSize):
                    self.setIconSize(kwargs['tamanio'])
            else:
                self.setIconSize(QSize(32, 32))

        if 'tooltip' in kwargs:
            self.setToolTip(kwargs['tooltip'])

        if 'autodefault' in kwargs:
            self.setAutoDefault(kwargs['autodefault'])
        else:
            self.setAutoDefault(True)
        self.setDefault(False)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])


class BotonMain(Boton):

    def __init__(self, *args, **kwargs):
        Boton.__init__(self, *args, **kwargs)
        self.setMinimumHeight(100)
        self.setIconSize(QSize(48, 48))


class BotonAceptar(Boton):

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '&Aceptar'
        if 'imagen' not in kwargs:
            kwargs['imagen'] = LeerIni("iniciosistema") + 'imagenes/aceptar.png'
        kwargs['tamanio'] = QSize(32, 32)
        Boton.__init__(self, *args, **kwargs)


class BotonCerrarFormulario(Boton):

    def __init__(self, *args, **kwargs):
        kwargs['texto'] = kwargs['textoBoton'] if 'textoBoton' in kwargs else '&Cerrar'
        kwargs['imagen'] = kwargs.get("imagen", imagen('close.png'))
        kwargs['tamanio'] = QSize(32, 32)
        Boton.__init__(self, *args, **kwargs)
        self.setDefault(False)

class ToolButton(QToolButton):

    texto = '...'
    tamanio = 12

    def __init__(self, *args, **kwargs):
        super().__init__()

        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']

        if 'texto' in kwargs:
            self.texto = kwargs['texto']

        self.setText(self.texto)
        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)

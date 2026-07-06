
# coding=utf-8
import os

from PyQt5 import QtCore, QtGui
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QLabel

from .utiles import openFileNameDialog, getFileName


class Etiqueta(QLabel):

    def __init__(self, parent=None, texto='', *args, **kwargs) -> object:
        QLabel.__init__(self, *args)
        self.setText(texto)
        font = QFont()
        if 'tamanio' in kwargs:
            font.setPointSizeF(kwargs['tamanio'])
        else:
            font.setPointSizeF(10)

        if 'alineacion' in kwargs:
            if kwargs['alineacion'].upper() == 'DERECHA':
                self.setAlignment(QtCore.Qt.AlignRight)
            elif kwargs['alineacion'].upper() == 'IZQUIERDA':
                self.setAlignment(QtCore.Qt.AlignLeft)
            elif kwargs['alineacion'].upper() == 'CENTRO':
                self.setAlignment(QtCore.Qt.AlignCenter)

        self.setFont(font)

class EtiquetaTitulo(Etiqueta):

    def __init__(self, parent=None, texto='', *args, **kwargs):
        Etiqueta.__init__(self, parent, texto, *args, **kwargs)
        self.setStyleSheet("* {color: qlineargradient(spread:pad, x1:0 y1:0, x2:1 y2:0, stop:0 rgba(0, 0, 0, 255), "
                            "stop:1 rgba(255, 255, 255, 255));"
                            "background: qlineargradient( x1:0 y1:0, x2:1 y2:0, stop:0 blue, stop:1 cyan);}")

class EtiquetaRoja(Etiqueta):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setStyleSheet("color: red;")


class Imagen(QLabel):

    clicked = pyqtSignal()
    blob_data = ''
    path_image = ''
    alto = 150
    ancho = 150
    mysql = True #indica si graba la imagen en la base de datos

    def __init__(self):
        super().__init__()

    def EstablecerImagen(self, imagen=''):
        if imagen:
            pixmap = QPixmap(os.path.abspath(imagen)).scaled(
                self.alto, self.ancho, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(pixmap)

    def mousePressEvent(self, ev: QtGui.QMouseEvent) -> None:
        archivo = openFileNameDialog(
            title='Importar',
            files="Image Files (*.png)",
        )
        if archivo:
            self.path_image = archivo
            with open(archivo, 'rb') as f:
                self.blob_data = f.read()
            self.EstablecerImagen(imagen=archivo)
        self.clicked.emit()

    def valor(self):
        if self.mysql:
            return self.blob_data
        else:
            return self.path_image

    def setText(self, blob_data: str) -> None:
        # data1 = base64.b64decode(blob_data)
        if self.mysql:
            nombre_imagen = f'{getFileName(filename="marca")}'
            imagen = open(nombre_imagen, 'wb')
            imagen.write(blob_data)
            imagen.close()
            self.path_image = nombre_imagen
            self.blob_data = blob_data
            self.EstablecerImagen(imagen=nombre_imagen)
        else:
            self.EstablecerImagen(blob_data)

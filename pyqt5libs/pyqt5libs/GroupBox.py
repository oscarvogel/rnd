# coding=utf-8
from PyQt5.QtWidgets import QGroupBox, QRadioButton


class Agrupacion(QGroupBox):

    def __init__(self, parent=None, *args, **kwargs):
        QGroupBox.__init__(self, *args)
        if 'tamanio' in kwargs:
            self.setStyleSheet('font-size: ' + str(kwargs['tamanio']) + 'px;')
        # else:
        #     self.setStyleSheet('font-size: 12px;')

        if 'titulo' in kwargs:
            self.setTitle(kwargs['titulo'])


class BotonRadio(QRadioButton):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)
        if 'tamanio' in kwargs:
            self.setStyleSheet('font-size: ' + str(kwargs['tamanio']) + 'px;')

        if 'texto' in kwargs:
            self.setText(kwargs['texto'])

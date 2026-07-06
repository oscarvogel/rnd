# coding=utf-8
from PyQt5.QtWidgets import QProgressBar


class Avance(QProgressBar):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)

        if 'inicial' in kwargs:
            self.actualizar(kwargs['inicial'])

    def actualizar(self, valor=0):
        if isinstance(valor, float):
            valor = int(valor)
        self.setValue(valor)

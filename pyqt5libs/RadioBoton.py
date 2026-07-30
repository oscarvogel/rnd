# coding=utf-8
from PyQt5.QtWidgets import QRadioButton


class RadioBoton(QRadioButton):

    valor = ''
    def __init__(self, *args, **kwargs):
        super().__init__()
        if 'texto' in kwargs:
            self.setText(kwargs['texto'])

        if 'checked' in kwargs:
            self.setChecked(kwargs['checked'])

        if 'valor' in kwargs:
            self.valor = kwargs['valor']
        else:
            self.valor = self.text()
from PyQt5.QtWidgets import QAction


class Accion(QAction):
    controlador = None
    menu = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

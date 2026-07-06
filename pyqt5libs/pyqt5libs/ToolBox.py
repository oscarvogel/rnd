from PyQt5.QtWidgets import QToolBox


class ToolBox(QToolBox):

    def __init__(self, flags, *args, **kwargs):
        super().__init__(flags, *args, **kwargs)
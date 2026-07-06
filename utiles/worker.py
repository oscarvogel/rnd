from PyQt5.QtCore import QThread, pyqtSignal
from utiles.importacion_tremblay_pdf import procesar_pdf_despacho

class Worker(QThread):
    finished = pyqtSignal(str)

    def __init__(self, archivo_pdf):
        super().__init__()
        self.archivo_pdf = archivo_pdf

    def run(self):
        resultado = procesar_pdf_despacho(self.archivo_pdf)
        self.finished.emit(resultado)

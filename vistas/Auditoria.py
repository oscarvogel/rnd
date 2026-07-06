from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.EntradaTexto import TextEdit
from pyqt5libs.pyqt5libs.Etiquetas import EtiquetaTitulo
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.utiles import imagen, inicializar_y_capturar_excepciones


class AuditoriaView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        
    @inicializar_y_capturar_excepciones
    def setupUi(self, Form, *args, **kwargs):
        self.setWindowTitle("Registro de auditoria")
        layout_ppal = QVBoxLayout(Form)
        self.resize(800, 500)
        
        self.label_titulo = EtiquetaTitulo(texto="Historial de cambios")
        layout_ppal.addWidget(self.label_titulo)
        
        self.gridDatos = Grilla()
        cabeceras = ["Fecha", "Acción", "Antes", "Después", "id"]
        self.gridDatos.ArmaCabeceras(cabeceras)
        layout_ppal.addWidget(self.gridDatos)
        
        layout_antes_despues = QHBoxLayout()
        self.datos_antes = TextEdit()
        self.datos_despues = TextEdit()
        layout_antes_despues.addWidget(self.datos_antes)
        layout_antes_despues.addWidget(self.datos_despues)
        layout_ppal.addLayout(layout_antes_despues)
        
        layout_botones = QHBoxLayout()
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"))
        layout_botones.addWidget(self.btn_cerrar)
        layout_ppal.addLayout(layout_botones)
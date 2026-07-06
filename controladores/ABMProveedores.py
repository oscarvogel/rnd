from modelos.Proveedores import Proveedor
from pyqt5libs.libs.controladores.ControladorBaseABM import ControladorBaseABM
from vistas.ABMProveedores import ABMProveedoresView


class ABMProveedoresController(ControladorBaseABM):
    model = Proveedor
    campoclave = Proveedor.id.name
    id_formulario = 667
    
    def __init__(self):
        super().__init__()
        self.view = ABMProveedoresView()
        self.conectarWidgets()
        
    def conectarWidgets(self):
        super().conectarWidgets()

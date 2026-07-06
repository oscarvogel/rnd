from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout

from modelos.Proveedores import Proveedor
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.libs.vistas.ABM import ABM
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.EntradaTexto import TextEdit
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.utiles import imagen, inicializar_y_capturar_excepciones


class ABMProveedoresView(ABM):
    model = Proveedor
    camposAMostrar = [Proveedor.id, Proveedor.razon_social, Proveedor.direccion, Proveedor.telefono, Proveedor.cuit, Proveedor.contacto, Proveedor.activo]
    ordenBusqueda = [Proveedor.razon_social]
    campoClave = Proveedor.id
    titulo = "Tabla de Fabricantes y Proveedores"
    autoincremental = True
    dynamicBackColor = {Proveedor.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        layout_codigo = self.ArmaEntrada(Proveedor.id)
        self.ArmaEntrada(Proveedor.razon_social, layout_codigo)
        direccion = self.ArmaEntrada(Proveedor.direccion)
        self.ArmaEntrada(Proveedor.telefono, boxlayout=direccion)
        cuit = self.ArmaEntrada(Proveedor.cuit, boxlayout=direccion)
        self.ArmaEntrada(Proveedor.contacto, boxlayout=cuit)
        self.ArmaEntrada(Proveedor.observaciones, control=TextEdit())

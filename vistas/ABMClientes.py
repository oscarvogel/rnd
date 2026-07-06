from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from modelos.Clientes import Cliente, cboRutaReparto
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.libs.vistas.ABM import ABM
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.EntradaTexto import TextEdit
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.utiles import imagen, inicializar_y_capturar_excepciones


class ABMClientesView(ABM):
    model = Cliente
    camposAMostrar = [Cliente.id, Cliente.razon_social, Cliente.direccion, Cliente.telefono, Cliente.cuit, Cliente.contacto, Cliente.activo]
    ordenBusqueda = [Cliente.razon_social]
    campoClave = Cliente.id
    titulo = "Tabla de Clientes"
    autoincremental = True
    dynamicBackColor = {Cliente.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        layout_codigo = self.ArmaEntrada(Cliente.id)
        self.ArmaEntrada(Cliente.razon_social, layout_codigo)
        direccion = self.ArmaEntrada(Cliente.direccion)
        self.ArmaEntrada(Cliente.telefono, boxlayout=direccion)
        self.ArmaEntrada(Cliente.cuit, boxlayout=direccion)
        contacto = self.ArmaEntrada(Cliente.contacto)
        self.ArmaEntrada(Cliente.ruta_reparto, boxlayout=contacto, control=cboRutaReparto())
        self.ArmaEntrada(Cliente.observaciones, control=TextEdit())
    
    @inicializar_y_capturar_excepciones
    def BotonesAdicionales(self):
        self.btn_codigo = self.CreaBoton(texto="Codigo", imagen_str="proveedor.png")
        self.horizontalLayout.addWidget(self.btn_codigo)

class CodigoClienteProveedorView(VistaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi(self)
    
    def initUi(self, parent):
        self.resize(400, 300)
        layout_ppal = QVBoxLayout(parent)
        self.setWindowTitle("Códigos de Clientes y Proveedores")
        
        self.grilla = Grilla()
        self.grilla.ArmaCabeceras(["Razón Social", "Codigo Cliente", "ID", "id_proveedor"])
        self.grilla.columnasHabilitadas = [1,]
        self.grilla.permiteagregar = False
        layout_ppal.addWidget(self.grilla)
        
        layout_botones = QHBoxLayout()
        self.btn_guardar = self.CreaBoton("Guardar", imagen_str="save.png")
        self.btn_agregar = self.CreaBoton("Agregar", imagen_str="new.png")
        self.btn_borrar = self.CreaBoton("Borrar", imagen_str="delete.png")
        self.btn_salir = self.CreaBoton("Salir", imagen_str="close.png")
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_agregar)
        layout_botones.addWidget(self.btn_borrar)
        layout_botones.addWidget(self.btn_salir)
        layout_ppal.addLayout(layout_botones)
        

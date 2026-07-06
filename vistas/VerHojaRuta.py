from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout
from modelos.Clientes import ValidaCliente, cboRutaReparto
from modelos.Empleados import ValidaEmpleado
from modelos.Equipos import ValidaEquipo
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.ProgressBar import Avance
from pyqt5libs.pyqt5libs.Spinner import Spinner


class VerHojaRutaView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Ver Hoja de Ruta")
        self.resize(1000, 650)
        layoutPpal = QVBoxLayout(self)
        
        self.avance = Avance()
        layoutPpal.addWidget(self.avance)
        
        layout_fechas = QHBoxLayout()
        lbl_fecha = Etiqueta(texto="Fecha de reparto:")
        self.fecha_reparto = Fecha()
        layout_fechas.addWidget(lbl_fecha)
        layout_fechas.addWidget(self.fecha_reparto)
        lbl_ruta = Etiqueta(texto="Ruta de reparto:")
        layout_fechas.addWidget(lbl_ruta)
        self.cbo_ruta_reparto = cboRutaReparto()
        layout_fechas.addWidget(self.cbo_ruta_reparto)
        layoutPpal.addLayout(layout_fechas)
                
        layout_equipo = QHBoxLayout()
        self.equipo = ValidaEquipo(texto="Camion Asignado:")
        layout_equipo.addLayout(self.equipo)
        self.empleado = ValidaEmpleado(texto="Chofer Responsable:")
        layout_equipo.addLayout(self.empleado)
        layoutPpal.addLayout(layout_equipo)
        
        self.grilla_datos = Grilla()
        cabeceras = [
            "Selecciona", "Cliente", "Comprobante", "Producto", "Cantidad", "KG", "Bultos", "Observaciones", "id", "codigo_cliente"
        ]
        self.grilla_datos.ArmaCabeceras(cabeceras=cabeceras)
        self.grilla_datos.columnasHabilitadas = [0,]
        layoutPpal.addWidget(self.grilla_datos)
        
        layout_botones = QHBoxLayout()
        self.btn_cargar = self.CreaBoton("Cargar", imagen_str="search.png")
        self.btn_agregar = self.CreaBoton("Agregar", imagen_str="new.png")
        self.btn_modificar = self.CreaBoton("Modificar", imagen_str="edit.png")
        self.btn_grabar = self.CreaBoton("Grabar", imagen_str="save.png")
        self.btn_borrar = self.CreaBoton("Borrar", imagen_str="delete.png")
        self.btn_imprimir = self.CreaBoton("Imprimir", imagen_str="printing.png")
        self.btn_cerrar = self.CreaBoton("Cerrar", imagen_str="close.png")
        layout_botones.addWidget(self.btn_cargar)
        layout_botones.addWidget(self.btn_agregar)
        layout_botones.addWidget(self.btn_modificar)
        layout_botones.addWidget(self.btn_grabar)
        layout_botones.addWidget(self.btn_borrar)
        layout_botones.addWidget(self.btn_imprimir)
        layout_botones.addWidget(self.btn_cerrar)
        layoutPpal.addLayout(layout_botones)


class ModificaHojaDeRutaView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        
    def setupUi(self, Form):
        self.resize(600, 400)
        self.setWindowTitle("Modificar Hoja de Ruta")
        layout_ppal = QVBoxLayout(Form)
        
        layout_datos = QFormLayout()
        self.cliente = ValidaCliente()
        layout_datos.addRow(self.cliente)
        
        self.layout_empleado = ValidaEmpleado()
        layout_datos.addRow(self.layout_empleado)
        
        self.layout_equipo = ValidaEquipo()
        layout_datos.addRow(self.layout_equipo)
        
        lbl_comprobante = Etiqueta(texto="Comprobante:")
        self.text_comprobante = EntradaTexto()
        layout_datos.addRow(lbl_comprobante, self.text_comprobante)
        
        lbl_producto = Etiqueta(texto="Producto:")
        self.text_producto = EntradaTexto()
        layout_datos.addRow(lbl_producto, self.text_producto)
        
        lbl_cantidad = Etiqueta(texto="Cantidad:")
        self.text_cantidad = Spinner()
        layout_datos.addRow(lbl_cantidad, self.text_cantidad)
        
        lbl_kg = Etiqueta(texto="KG:")
        self.text_kg = Spinner()
        layout_datos.addRow(lbl_kg, self.text_kg)
        
        lbl_bultos = Etiqueta(texto="Bultos:")
        self.text_bultos = Spinner()
        layout_datos.addRow(lbl_bultos, self.text_bultos)
        
        lbl_observaciones = Etiqueta(texto="Observaciones:")
        self.text_observaciones = EntradaTexto()
        layout_datos.addRow(lbl_observaciones, self.text_observaciones)
        
        layout_ppal.addLayout(layout_datos)
        
        layout_botones = QHBoxLayout()
        self.btn_grabar = self.CreaBoton("Grabar", imagen_str="save.png")
        self.btn_cerrar = self.CreaBoton("Cerrar", imagen_str="close.png")
        layout_botones.addWidget(self.btn_grabar)
        layout_botones.addWidget(self.btn_cerrar)
        layout_ppal.addLayout(layout_botones)
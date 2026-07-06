
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QColor
from modelos.Empleados import ValidaEmpleado
from modelos.Equipos import ChoferEquipo, Equipos, ValidaEquipoConTexto
from modelos.ModeloBase import reconnect_if_needed
from modelos.Tablas import cboTipoMovil
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.libs.vistas.ABM import ABM
from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.EntradaTexto import TextEdit
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha, RangoFechas
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.utiles import LeerIni, imagen, inicializar_y_capturar_excepciones


class ABMEquiposView(ABM):
    model = Equipos
    ordenBusqueda = [Equipos.descripcion, Equipos.patente]
    campoClave = Equipos.id
    titulo = "Tabla de Equipos"
    autoincremental = True
    if LeerIni("basedatos") == "fg":
        dynamicBackColor = {Equipos.baja.name: {'valor': True, 'color': QColor(128, 128, 128)}}
        camposAMostrar = [Equipos.id, Equipos.descripcion, Equipos.patente, Equipos.baja]
    else:
        dynamicBackColor = {Equipos.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}
        camposAMostrar = [Equipos.id, Equipos.descripcion, Equipos.patente, Equipos.activo]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def ArmaCarga(self):
        layout_codigo = self.ArmaEntrada(Equipos.id)
        self.ArmaEntrada(Equipos.descripcion, layout_codigo)
        self.ArmaEntrada(Equipos.patente, layout_codigo)
        numeros = self.ArmaEntrada(Equipos.nro_chasis)
        self.ArmaEntrada(Equipos.nro_motor, boxlayout=numeros)
        self.ArmaEntrada(Equipos.capacidad_tanque, boxlayout=numeros)
        fecha = self.ArmaEntrada(Equipos.fecha_adquisicion, control=Fecha())
        self.ArmaEntrada(Equipos.tipo_movil, boxlayout=fecha, control=cboTipoMovil())
        layout_equipo = self.ArmaEntrada(Equipos.movil_asociado, control=ValidaEquipoConTexto(texto=""), layout=True)
        self.chofer_asignado = ValidaEmpleado(texto="Chofer Asignado", solo_numeros=True, ancho=50)
        layout_equipo.addLayout(self.chofer_asignado)
        self.ArmaEntrada(Equipos.observaciones, control=TextEdit())
        
    def BotonesAdicionales(self):
        self.btn_vencimientos = self.CreaBoton("Vencimientos", imagen_str="vencimiento.png")
        self.horizontalLayout.addWidget(self.btn_vencimientos)
    
    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def PostClickModifica(self):
        chofer_asignado = ChoferEquipo.ultimo_chofer(self.idtabla)
        if chofer_asignado:
            self.chofer_asignado.setText(chofer_asignado.empleado.id)
        else:
            self.chofer_asignado.setText("")

class MovimientosEquiposView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        
    @inicializar_y_capturar_excepciones
    def setupUi(self, Form, *args, **kwargs):
        layout_ppal = QVBoxLayout(Form)
        self.setWindowTitle("Movimientos por equipo")
        self.resize(1200, 500)
        
        self.layout_fechas = RangoFechas()
        layout_ppal.addLayout(self.layout_fechas)
        self.layout_fechas.desde_fecha.setFecha(-90)
        
        self.grid_produccion = Grilla()
        cabecera = [
            'Funcionario',
            'Periodo',
            'Fecha',
            'Hora Inicio',
            'Hora Fin',
            'Horas Trabajadas',
            'Tipo de Operación',
            'Producción',
            'Unidad de Producción',
            'Observaciones',
            'Empresa',
            'Predio',
            'Prod/Hr',
            'Lts/Hr',
        ]
        self.grid_produccion.ArmaCabeceras(cabeceras=cabecera)
        layout_ppal.addWidget(self.grid_produccion)
        
        self.grid_combustible = Grilla()
        cabecera = [
            'Fecha', 'Tipo de Combustible', 'Km/Hora', 'Precio por Litro',
            'Ingreso', 'Egreso', 'Consumo', 'Unidad de Negocio', 'Paniol', 'Remito', 'ID'
        ]
        self.grid_combustible.ArmaCabeceras(cabeceras=cabecera)
        layout_ppal.addWidget(self.grid_combustible)
        
        layout_totales = QHBoxLayout()
        lbl_total_combustible = Etiqueta(texto="Total combustible")
        self.total_combustible = EntradaTexto()
        layout_totales.addWidget(lbl_total_combustible)
        layout_totales.addWidget(self.total_combustible)
        
        lbl_total_produccion = Etiqueta(texto="Total produccion")
        self.total_produccion = EntradaTexto()
        layout_totales.addWidget(lbl_total_produccion)
        layout_totales.addWidget(self.total_produccion)
        
        lbl_lts_produccion = Etiqueta(texto="LTs / Prod")
        self.lts_produccion = EntradaTexto()
        layout_totales.addWidget(lbl_lts_produccion)
        layout_totales.addWidget(self.lts_produccion)
        
        layout_ppal.addLayout(layout_totales)

        layout_promedios = QHBoxLayout()
        lbl_produccion_hr = Etiqueta(texto="Prod/Hr")
        self.text_prod_hr = EntradaTexto()
        layout_promedios.addWidget(lbl_produccion_hr)
        layout_promedios.addWidget(self.text_prod_hr)
        
        lbl_ltrs_hr = Etiqueta(texto="Lts/Hr")
        self.text_ltr_hr = EntradaTexto()
        layout_promedios.addWidget(lbl_ltrs_hr)
        layout_promedios.addWidget(self.text_ltr_hr)
        
        layout_ppal.addLayout(layout_promedios)
        
        layout_botones = QHBoxLayout()
        self.btn_exporta = Boton(texto="Exportar", imagen=imagen("79354_excel_icon.png"))
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"))
        layout_botones.addWidget(self.btn_exporta)
        layout_botones.addWidget(self.btn_cerrar)
        layout_ppal.addLayout(layout_botones)
        
class VencimientosView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        
    @inicializar_y_capturar_excepciones
    def setupUi(self, Form):
        self.resize(600, 350)
        self.setWindowTitle(f"Vencimientos de ")
        layout_ppal = QVBoxLayout(Form)
        
        self.grid_datos = Grilla()
        self.grid_datos.ArmaCabeceras([
            'Fecha', 'Detalle', 'id'
        ])
        self.grid_datos.columnasHabilitadas = [0, 1]
        layout_ppal.addWidget(self.grid_datos)
        
        layout_botones = QHBoxLayout()
        self.btn_grabar = self.CreaBoton("Guardar", imagen_str="save.png")
        self.btn_borrar = self.CreaBoton("Borrar", imagen_str="delete.png")
        self.btn_cerrar = self.CreaBoton("Salir", imagen_str="close.png")
        layout_botones.addWidget(self.btn_grabar)
        layout_botones.addWidget(self.btn_borrar)
        layout_botones.addWidget(self.btn_cerrar)
        layout_ppal.addLayout(layout_botones)
        
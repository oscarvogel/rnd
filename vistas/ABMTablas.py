from PyQt5.QtGui import QColor

from modelos.Combustible import Panioles, TipoCombustible
from modelos.Empleados import ConceptoLiquidacion
from modelos.ParametrosSistema import ParamSist
from modelos.Tablas import Monedas, TipoDeMovil, TipoOperacion, cboUnidadNegocio, UnidadMedida
from modelos.Clientes import RutaReparto, Localidades
from pyqt5libs.libs.vistas.ABM import ABM
from pyqt5libs.pyqt5libs.Checkbox import CheckBox
from pyqt5libs.pyqt5libs.Fechas import Fecha
from pyqt5libs.pyqt5libs.Spinner import Spinner
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones


class ABMTipoDeMovilView(ABM):
    model = TipoDeMovil
    camposAMostrar = [TipoDeMovil.id, TipoDeMovil.descripcion, TipoDeMovil.activo]
    ordenBusqueda = TipoDeMovil.descripcion
    campoClave = TipoDeMovil.id
    titulo = "Tabla de Tipos de Moviles"
    autoincremental = True
    dynamicBackColor = {TipoDeMovil.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_codigo = self.ArmaEntrada(TipoDeMovil.id)
        self.ArmaEntrada(TipoDeMovil.descripcion, layout_codigo)


class ABMMonedasView(ABM):
    model = Monedas
    camposAMostrar = [Monedas.id, Monedas.descripcion, Monedas.cambio, Monedas.simbolo, Monedas.activo]
    ordenBusqueda = Monedas.descripcion
    campoClave = Monedas.id
    titulo = "Tabla de Monedas"
    autoincremental = True
    dynamicBackColor = {Monedas.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_codigo = self.ArmaEntrada(Monedas.id)
        self.ArmaEntrada(Monedas.descripcion, layout_codigo)
        layout_simbolo = self.ArmaEntrada(Monedas.simbolo)
        self.ArmaEntrada(Monedas.cambio, layout_simbolo, control=Spinner())
        self.ArmaEntrada(Monedas.activo, layout_simbolo, control=CheckBox())
        
class ABMConceptosLiquidacionView(ABM):
    model = ConceptoLiquidacion
    camposAMostrar = [ConceptoLiquidacion.id, ConceptoLiquidacion.descripcion, ConceptoLiquidacion.monto, ConceptoLiquidacion.activo]
    ordenBusqueda = ConceptoLiquidacion.descripcion
    campoClave = ConceptoLiquidacion.id
    titulo = "Tabla de Conceptos de Liquidacion"
    autoincremental = True
    dynamicBackColor = {ConceptoLiquidacion.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_codigo = self.ArmaEntrada(ConceptoLiquidacion.id)
        self.ArmaEntrada(ConceptoLiquidacion.descripcion, layout_codigo)
        layout_monto = self.ArmaEntrada(ConceptoLiquidacion.monto, layout_codigo, control=Spinner())
        self.ArmaEntrada(ConceptoLiquidacion.activo, layout_monto, control=CheckBox(checked=True))

class ABMParametrosSistemaView(ABM):
    model = ParamSist
    camposAMostrar = [ParamSist.id, ParamSist.parametro, ParamSist.valor]
    ordenBusqueda = ParamSist.valor
    campoClave = ParamSist.id
    titulo = "Tabla de Parámetros del Sistema"
    autoincremental = True
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        self.ArmaEntrada(ParamSist.id)
        self.ArmaEntrada(ParamSist.parametro)
        self.ArmaEntrada(ParamSist.valor)

class ABMPaniolesView(ABM):
    model = Panioles
    camposAMostrar = [Panioles.id, Panioles.descripcion, Panioles.activo]
    ordenBusqueda = Panioles.descripcion
    campoClave = Panioles.id
    titulo = "Tabla de Panioles"
    autoincremental = True
    dynamicBackColor = {Panioles.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_id = self.ArmaEntrada(Panioles.id)
        self.ArmaEntrada(Panioles.descripcion, boxlayout=layout_id)
        self.ArmaEntrada(Panioles.activo, layout_id, control=CheckBox(checked=True))
        self.ArmaEntrada(Panioles.unidad_negocio, control=cboUnidadNegocio())

class ABMTipoCombustiblesView(ABM):
    model = TipoCombustible
    camposAMostrar = [TipoCombustible.id, TipoCombustible.descripcion, TipoCombustible.precio, TipoCombustible.ultima_actualizacion, TipoCombustible.activo]
    ordenBusqueda = TipoCombustible.descripcion
    campoClave = TipoCombustible.id
    titulo = "Tabla de Tipos de Combustible"
    autoincremental = True
    dynamicBackColor = {TipoCombustible.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_id = self.ArmaEntrada(TipoCombustible.id)
        self.ArmaEntrada(TipoCombustible.descripcion, boxlayout=layout_id)
        layout_precio = self.ArmaEntrada(TipoCombustible.precio, control=Spinner())
        self.ArmaEntrada(TipoCombustible.ultima_actualizacion, boxlayout=layout_precio, control=Fecha())
        self.ArmaEntrada(TipoCombustible.activo, layout_precio, control=CheckBox(checked=True))

class ABMTipoOperacionView(ABM):
    model = TipoOperacion
    camposAMostrar = [TipoOperacion.id, TipoOperacion.descripcion, TipoOperacion.coeficiente, TipoOperacion.activo]
    ordenBusqueda = TipoOperacion.descripcion
    campoClave = TipoOperacion.id
    titulo = "Tabla de Tipos de Operacion"
    autoincremental = True
    dynamicBackColor = {TipoOperacion.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        layout_id = self.ArmaEntrada(TipoOperacion.id)
        self.ArmaEntrada(TipoOperacion.descripcion, boxlayout=layout_id)
        layout_coeficiente = self.ArmaEntrada(TipoOperacion.coeficiente, control=Spinner())
        self.ArmaEntrada(TipoOperacion.activo, layout_coeficiente, control=CheckBox(checked=True))
        
        
class ABMUnidadMedidaView(ABM):
    model = UnidadMedida
    camposAMostrar = [UnidadMedida.id, UnidadMedida.descripcion]
    ordenBusqueda = UnidadMedida.descripcion
    campoClave = UnidadMedida.id
    titulo = "Tabla de Unidades de Medida"
    autoincremental = True
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_id = self.ArmaEntrada(UnidadMedida.id)
        self.ArmaEntrada(UnidadMedida.descripcion, boxlayout=layout_id)
        
class ABMRutaRepartoView(ABM):
    model = RutaReparto
    camposAMostrar = [RutaReparto.id, RutaReparto.descripcion, RutaReparto.activo]
    ordenBusqueda = RutaReparto.descripcion
    campoClave = RutaReparto.id
    titulo = "Tabla de Rutas de Reparto"
    autoincremental = True
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_id = self.ArmaEntrada(RutaReparto.id)
        self.ArmaEntrada(RutaReparto.descripcion, boxlayout=layout_id)        
        self.ArmaEntrada(RutaReparto.activo, control=CheckBox(checked=True))
        
class ABMLocalidadesView(ABM):
    model = Localidades
    camposAMostrar = [Localidades.id, Localidades.descripcion]
    ordenBusqueda = Localidades.descripcion
    campoClave = Localidades.id
    titulo = "Tabla de Localidades"
    autoincremental = True
    
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_id = self.ArmaEntrada(Localidades.id)
        self.ArmaEntrada(Localidades.descripcion, boxlayout=layout_id)        

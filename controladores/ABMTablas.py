from modelos.Clientes import Localidades
from modelos.Combustible import Panioles, TipoCombustible
from modelos.Empleados import ConceptoLiquidacion
from modelos.ParametrosSistema import ParamSist
from modelos.Tablas import Monedas, TipoDeMovil, TipoOperacion, UnidadMedida
from modelos.Clientes import RutaReparto
from pyqt5libs.libs.controladores.ControladorBaseABM import ControladorBaseABM
from vistas.ABMTablas import ABMConceptosLiquidacionView, ABMLocalidadesView, ABMMonedasView, ABMPaniolesView, ABMParametrosSistemaView, ABMRutaRepartoView, ABMTipoCombustiblesView, ABMTipoDeMovilView, ABMTipoOperacionView, \
    ABMUnidadMedidaView


class ABMTipoDeMovilController(ControladorBaseABM):
    model = TipoDeMovil
    campoclave = TipoDeMovil.id.name
    id_formulario = 662
    
    def __init__(self):
        super().__init__()
        self.view = ABMTipoDeMovilView()
        self.view.btnBorrar.setText("Baja")
        self.conectarWidgets()

class ABMMonedasController(ControladorBaseABM):
    model = Monedas
    campoclave = Monedas.id.name
    id_formulario = 663
    
    def __init__(self):
        super().__init__()
        self.view = ABMMonedasView()
        self.conectarWidgets()
        
class ABMConceptosLiquidacionController(ControladorBaseABM):
    model = ConceptoLiquidacion
    campoclave = ConceptoLiquidacion.id.name
    id_formulario = 664
    
    def __init__(self):
        super().__init__()
        self.view = ABMConceptosLiquidacionView()
        self.conectarWidgets()
        
        
class ABMParametrosSistemaController(ControladorBaseABM):
    model = ParamSist
    campoclave = ParamSist.id.name
    id_formulario = 665
    
    def __init__(self):
        super().__init__()
        self.view = ABMParametrosSistemaView()
        self.conectarWidgets()
        
class ABMPaniolesController(ControladorBaseABM):
    model = Panioles
    campoclave = Panioles.id.name
    id_formulario = 666
    
    def __init__(self):
        super().__init__()
        self.view = ABMPaniolesView()
        self.conectarWidgets()
        
class ABMTipoCombustiblesController(ControladorBaseABM):
    model = TipoCombustible
    campoclave = TipoCombustible.id.name
    id_formulario = 667
    
    def __init__(self):
        super().__init__()
        self.view = ABMTipoCombustiblesView()
        self.conectarWidgets()

class ABMTipoOperacionController(ControladorBaseABM):
    model = TipoOperacion
    campoclave = TipoOperacion.id.name
    id_formulario = 668
    
    def __init__(self):
        super().__init__()
        self.view = ABMTipoOperacionView()
        self.conectarWidgets()
        
class ABMUnidadMedidaController(ControladorBaseABM):
    model = UnidadMedida
    campoclave = UnidadMedida.id.name
    id_formulario = 681

    def __init__(self):
        super().__init__()
        self.view = ABMUnidadMedidaView()
        self.conectarWidgets()        

class ABMRutaRepartoController(ControladorBaseABM):
    model = RutaReparto
    campoclave = RutaReparto.id.name
    id_formulario = 681

    def __init__(self):
        super().__init__()
        self.view = ABMRutaRepartoView()
        self.conectarWidgets()                

class ABMLocalidadesController(ControladorBaseABM):
    model = Localidades
    campoclave = Localidades.id.name
    id_formulario = 681

    def __init__(self):
        super().__init__()
        self.view = ABMLocalidadesView()
        self.conectarWidgets()                        
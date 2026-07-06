import datetime
from email.policy import default
import peewee
from modelos.ModeloBase import ModeloBase
from modelos.Tablas import Monedas
from pyqt5libs.libs.vistas.Busqueda import Buscador
from pyqt5libs.pyqt5libs.Validaciones import ValidaConTexto
from pyqt5libs.pyqt5libs.utiles import LeerConf, LeerIni

class ConceptoLiquidacion(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True)
    monto = peewee.DecimalField(max_digits=10, decimal_places=2, null=False, verbose_name='Monto')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')
    
    class Meta:
        db_table = 'conceptoliquidacion'

class Empleado(ModeloBase):
    
    nombre = peewee.CharField(max_length=100, null=False, unique=True)
    if LeerIni("basedatos") != "fg":
        apellido = peewee.CharField(max_length=50, null=False, unique=True)
        id = peewee.AutoField(primary_key=True)
        email = peewee.CharField(max_length=100, null=False, unique=True)
        direccion = peewee.CharField(max_length=255, null=True)
        fecha_contratacion = peewee.DateField(null=False, verbose_name='Fecha de Contratación')
        fecha_baja = peewee.DateField(null=True, verbose_name='Fecha de Baja')
        documento = peewee.CharField(max_length=15, null=True)
        observaciones = peewee.TextField(null=True)
        porcentaje = peewee.FloatField(default=0, verbose_name="Porcentaje")
    else:
        id = peewee.AutoField(primary_key=True, column_name="idPersonal")
        direccion = peewee.CharField(max_length=255, null=True, column_name = 'domicilio')
        fecha_contratacion = peewee.DateField(null=False, verbose_name='Fecha de Contratación', column_name='fechaalta')
        fecha_baja = peewee.DateField(null=True, verbose_name='Fecha de Baja', column_name='fechabaja')
        documento = peewee.CharField(max_length=15, null=True, column_name='cuit')

    telefono = peewee.CharField(max_length=80, null=True)
    fecha_nacimiento = peewee.DateField(null=True, verbose_name='Fecha de Nacimiento')
    activo = peewee.BooleanField(default=True)
    concepto_liquidacion = peewee.ForeignKeyField(model=ConceptoLiquidacion, backref='empleados', verbose_name='Concepto de Liquidación', default=1, column_name='concepto_liquidacion')
    
    class Meta:
        if LeerIni("basedatos") == 'fg':
            db_table = 'personal'
        else:
            db_table = 'empleados'
    
    @property
    def nombre_completo(self):
        if LeerIni("basedatos") != "fg":
            return f"{self.nombre} {self.apellido}"
        else:
            return self.nombre
        
    def __str__(self):
        if LeerIni("basedatos") != "fg":
            return f"{self.nombre} {self.apellido}"
        else:
            return self.nombre


class ValidaConceptos(ValidaConTexto):
    modelo = ConceptoLiquidacion
    nombre = ConceptoLiquidacion.descripcion
    codigo = ConceptoLiquidacion.id
    campos = [ConceptoLiquidacion.id.name, ConceptoLiquidacion.descripcion.name]
    largo = 3
    ancho = 80        

class FichaPersonal(ModeloBase):
    
    id = peewee.AutoField(primary_key=True)
    empleado = peewee.ForeignKeyField(model=Empleado, backref='ficha_personal', verbose_name='Empleado')
    fecha = peewee.DateField(null=False, verbose_name='Fecha')
    detalle = peewee.CharField(max_length=255, null=False, verbose_name='Detalle', default='')
    debe = peewee.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name='Debe', default=0.00)
    haber = peewee.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name='Haber', default=0.00)
    periodo = peewee.CharField(max_length=6, null=False, verbose_name='Periodo')
    usuario_grabacion = peewee.CharField(max_length=50, null=False, verbose_name='Usuario de Grabación', default=LeerConf('usuario'))
    fecha_grabacion = peewee.DateTimeField(null=False, verbose_name='Fecha de Grabación', default=datetime.datetime.now())
    activo = peewee.BooleanField(default=True, verbose_name='Activo')
    cambio = peewee.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name='Cambio')
    moneda = peewee.ForeignKeyField(model=Monedas, backref='ficha_personal', verbose_name='Moneda', column_name='moneda_id')
    concepto_liquidacion = peewee.ForeignKeyField(model=ConceptoLiquidacion, backref='ficha_personal', verbose_name='Concepto de Liquidación')
    
    class Meta:
        db_table = 'ficha_personal'
        
class ValidaEmpleado(ValidaConTexto):
    modelo = Empleado
    if LeerIni("basedatos") == "fg":
        nombre = [Empleado.nombre]
        campos_busqueda = [Empleado.nombre.column_name]
        campos = [Empleado.id.name, Empleado.nombre.name]
    else:
        nombre = [Empleado.nombre, Empleado.apellido]
        campos_busqueda = [Empleado.nombre.column_name, Empleado.apellido.column_name]
        campos = [Empleado.id.name, Empleado.nombre.name, Empleado.apellido.name]
    condiciones = [Empleado.activo == True]
    codigo = Empleado.id
    ancho = 80
    textoEtiqueta = "Empleado"

class ExportacionProduccionEmpleado(ModeloBase):
    
    id = peewee.AutoField(primary_key=True)
    empleado = peewee.ForeignKeyField(model=Empleado, backref='exportacion_produccion_empleado', verbose_name='Empleado')
    columna = peewee.CharField(max_length=100, null=False)
    nombre_encabezado = peewee.CharField(max_length=100, null=False)
    tipo = peewee.CharField(max_length=50, null=False)
    formula = peewee.CharField(max_length=100, null=True)
    
    class Meta:
        db_table = 'exportacion_produccion_empleado'

class BuscaEmpleado(Buscador):
    modelo = Empleado
    nombre = Empleado.nombre_completo
    codigo = Empleado.id
    if LeerIni("basedatos") == "fg":
        campos = [Empleado.id.name, Empleado.nombre.name]
        campos_busqueda = [Empleado.nombre.name]
    else:
        campos = [Empleado.id.name, Empleado.apellido.column_name, Empleado.nombre.name]
        campos_busqueda = [Empleado.apellido.column_name, Empleado.nombre.name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Buscar Planificaciones"
    valorRetorno = None
    lRetval = False  # indica si presiono en aceptar o cancelar        
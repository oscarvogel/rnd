import peewee
from modelos.Clientes import Cliente
from modelos.ModeloBase import ModeloBase
from pyqt5libs.pyqt5libs.ComboBox import ComboSQL
from pyqt5libs.pyqt5libs.utiles import LeerIni


class UnidadNegocio(ModeloBase):
    if LeerIni("basedatos") == "fg":
        id = peewee.AutoField(primary_key=True, column_name = 'idunidadnegocio')
        descripcion = peewee.TextField(null=True, column_name = "nombre")
    else:
        id = peewee.AutoField(primary_key=True)
        descripcion = peewee.TextField(null=True)
    prefijo = peewee.CharField(max_length=10, null=True)
    activo = peewee.BooleanField(default=True)
    # paniol = peewee.ForeignKeyField(model=Panioles, backref='unidades_produccion', verbose_name='Paniol')

    class Meta:
        if LeerIni("basedatos") == "fg":
            db_table = 'unidadnegocio'
        else:
            db_table = 'unidades_negocio'

    def __str__(self):
        return self.descripcion
    
class Panioles(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Descripción')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')
    unidad_negocio = peewee.ForeignKeyField(model=UnidadNegocio, verbose_name="Unidad de negocio")

    class Meta:
        db_table = 'panioles'

    def __str__(self):
        return self.descripcion
    
class TipoDeMovil(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    if LeerIni("basedatos") == "fg":
        descripcion = peewee.CharField(max_length=100, null=False, unique=True, column_name="detalle")
    else:
        descripcion = peewee.CharField(max_length=100, null=False, unique=True)
    activo = peewee.BooleanField(default=True)

    class Meta:
        if LeerIni("basedatos") == "fg":
            db_table = 'tipodemovil'
        else:
            db_table = 'tipos_movil'
    
    def __str__(self):
        return self.descripcion

class TipoOperacion(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True)
    activo = peewee.BooleanField(default=True)
    coeficiente = peewee.FloatField(null=False, default=1.0)

    class Meta:
        db_table = 'tipos_operacion'
        
    def __str__(self):
        return self.descripcion

class Monedas(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True)
    simbolo = peewee.CharField(max_length=10, null=False, unique=True)
    cambio = peewee.DecimalField(max_digits=10, decimal_places=4, null=False, default=1.0)
    activo = peewee.BooleanField(default=True)

    class Meta:
        db_table = 'monedas'

    def __str__(self):
        return self.descripcion
    
class UnidadProduccion(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True)
    unidad = peewee.CharField(max_length=10, null=False, unique=True)
    detalle_produccion = peewee.CharField(max_length=100, null=True)
    activo = peewee.BooleanField(default=True)

    class Meta:
        db_table = 'unidades_produccion'
    
    def __str__(self):
        return self.descripcion

class Predio(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Descripción')
    cliente = peewee.ForeignKeyField(model=Cliente, backref='predios', verbose_name='Cliente')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'predios'
        
    def __str__(self):
        return self.descripcion

class ObjetivoPeriodo(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    periodo = peewee.CharField(max_length=6, null=False)
    objetivo = peewee.DecimalField(max_digits=10, decimal_places=2, null=False)
    tipo_operacion = peewee.ForeignKeyField(model=TipoOperacion, backref='objetivos_periodo', verbose_name='Tipo de Operación')
    unidad_negocio = peewee.ForeignKeyField(model=UnidadNegocio, backref='objetivos_periodo', verbose_name='Unidad de Negocio')
    activo = peewee.BooleanField(default=True)
    
    class Meta:
        db_table = 'objetivos_periodo'

class TipoCombustible(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Descripción')
    precio = peewee.DecimalField(max_digits=10, decimal_places=2, null=False, verbose_name='Precio')
    ultima_actualizacion = peewee.DateTimeField(null=False, verbose_name='Ultima Actualización')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'tipos_combustible'
        
    def __str__(self):
        return self.descripcion

class UnidadMedida(ModeloBase):
    id = peewee.AutoField()
    descripcion = peewee.CharField(max_length=80)
    
    def __str__(self):
        return self.descripcion

    
class cboTipoMovil(ComboSQL):
    modelo = TipoDeMovil
    cOrden = TipoDeMovil.descripcion.name
    campovalor = TipoDeMovil.id.name
    campo1 = TipoDeMovil.descripcion.name

class cboUnidadNegocio(ComboSQL):
    modelo = UnidadNegocio
    cOrden = UnidadNegocio.descripcion
    campovalor = UnidadNegocio.id.name
    campo1 = UnidadNegocio.descripcion.name
    condicion = UnidadNegocio.activo == True
    agrega_todos = True
    
class cboMonedas(ComboSQL):
    modelo = Monedas
    cOrden = Monedas.descripcion.name
    campovalor = Monedas.id.name
    campo1 = Monedas.descripcion.name
    condicion = Monedas.activo == True    

class cboTipoOperacion(ComboSQL):
    modelo = TipoOperacion
    cOrden = TipoOperacion.descripcion.name
    campovalor = TipoOperacion.id.name
    campo1 = TipoOperacion.descripcion.name
    condicion = TipoOperacion.activo == True
    
class cboUnidadProduccion(ComboSQL):
    modelo = UnidadProduccion
    cOrden = UnidadProduccion.descripcion.name
    campovalor = UnidadProduccion.id.name
    campo1 = UnidadProduccion.unidad.name
    condicion = UnidadProduccion.activo == True    

class cboPaniol(ComboSQL):
    modelo = Panioles
    cOrden = Panioles.descripcion.name
    campovalor = Panioles.id.name
    campo1 = Panioles.descripcion.name
    condicion = Panioles.activo == True
    agrega_todos = True
    
class cboTipoCombustible(ComboSQL):
    modelo = TipoCombustible
    cOrden = TipoCombustible.descripcion.name
    campovalor = TipoCombustible.id.name
    campo1 = TipoCombustible.descripcion.name
    condicion = TipoCombustible.activo == True    

class cboUnidadesMedida(ComboSQL):
    modelo = UnidadMedida
    cOrden = UnidadMedida.descripcion.name
    campovalor = UnidadMedida.id.name
    campo1 = UnidadMedida.descripcion.name



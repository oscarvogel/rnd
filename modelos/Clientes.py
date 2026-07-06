import peewee
from modelos.ModeloBase import ModeloBase
from modelos.ParametrosSistema import ParamSist
from modelos.Proveedores import Proveedor
from pyqt5libs.libs.vistas.Busqueda import Buscador
from pyqt5libs.pyqt5libs.ComboBox import ComboSQL
from pyqt5libs.pyqt5libs.Validaciones import ValidaConTexto


class RutaReparto(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Descripción')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'rutas_reparto'
    
    def __str__(self):
        return self.descripcion
        
class Localidades(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True)
    provincia = peewee.CharField(max_length=100, null=False)

    class Meta:
        db_table = 'localidades'
    
    def __str__(self):
        return self.descripcion
    
class Cliente(ModeloBase):
    
    id = peewee.AutoField(primary_key=True)
    razon_social = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Razón Social')
    direccion = peewee.CharField(max_length=100, null=True, verbose_name='Dirección')
    telefono = peewee.CharField(max_length=20, null=True, verbose_name='Teléfono')
    cuit = peewee.CharField(
        max_length=20,
        null=True,
        unique=True,
        verbose_name='CUIT' if ParamSist.ObtenerParametro("NACIONALIDAD_EMPRESA", "ARG") == "ARG" else 'RUC'
    )
    contacto = peewee.CharField(max_length=100, null=True, verbose_name='Contacto')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')
    observaciones = peewee.TextField(null=True, verbose_name='Observaciones')
    ruta_reparto = peewee.ForeignKeyField(
        model=RutaReparto,
        backref='clientes',
        null=True,
        verbose_name='Ruta de Reparto', default=1
    )
    localidad = peewee.ForeignKeyField(
        model=Localidades,
        backref='clientes',
        null=True,
        verbose_name='Localidad'
    )

    class Meta:
        db_table = 'cliente'
    
    def __str__(self):
        return self.razon_social

class CodigoClienteProveedor(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    codigo = peewee.CharField(max_length=100, null=False, verbose_name='Código')
    cliente = peewee.ForeignKeyField(
        model=Cliente,
        backref='codigos',
        null=False,
        verbose_name='Cliente'
    )
    proveedor = peewee.ForeignKeyField(
        model=Proveedor,
        backref='codigos',
        null=True,
        verbose_name='Proveedor'
    )


    class Meta:
        db_table = 'codigos_clientes_proveedores'
    
    def __str__(self):
        return self.codigo


class ValidaCliente(ValidaConTexto):
    modelo = Cliente
    nombre = Cliente.razon_social
    codigo = Cliente.id
    campos = [Cliente.id.name, Cliente.razon_social.name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Clientes"
    condiciones = [Cliente.activo == True]
    campos_busqueda = [Cliente.razon_social.column_name]

class cboRutaReparto(ComboSQL):
    modelo = RutaReparto
    cOrden = RutaReparto.descripcion
    campovalor = RutaReparto.id.name
    campo1 = RutaReparto.descripcion.name
    condicion = RutaReparto.activo == True


class BuscadorCliente(Buscador):
    modelo = Cliente
    nombre = Cliente.razon_social
    codigo = Cliente.id
    campos = [Cliente.id.name, Cliente.razon_social.name]
    campos_busqueda = [Cliente.razon_social.column_name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Buscar Clientes"
    valorRetorno = None
    lRetval = False  # indica si presiono en aceptar o cancelar        
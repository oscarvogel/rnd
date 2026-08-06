import peewee
from modelos.ModeloBase import ModeloBase
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.vistas.Busqueda import Buscador
from pyqt5libs.pyqt5libs.Validaciones import ValidaConTexto
from pyqt5libs.pyqt5libs.utiles import LeerIni


class Proveedor(ModeloBase):
    
    if LeerIni("basedatos") == "fg":
        id = peewee.AutoField(primary_key=True, column_name='idProveedor')
        razon_social = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Razón Social', column_name='RazonSocial')
        direccion = peewee.CharField(max_length=100, null=True, verbose_name='Dirección', column_name='domicilio')
    else:
        id = peewee.AutoField(primary_key=True)
        razon_social = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Razón Social')
        direccion = peewee.CharField(max_length=100, null=True, verbose_name='Dirección')
    telefono = peewee.CharField(max_length=20, null=True, verbose_name='Teléfono')
    cuit = peewee.CharField(
        max_length=20,
        null=True,
        unique=True,
        # Antes: ParamSist.ObtenerParametro(...) == 'ARG' else 'RUC' - requeria DB al importar.
        # El sistema RND opera casi siempre con nacionalidad ARG; se hardcodea 'CUIT'
        # y se evita la query al import-time. Si la nacionalidad cambia a RUC, mover
        # esta decision a runtime (ej. al inicializar la app o al construir el form).
        verbose_name='CUIT'
    )
    contacto = peewee.CharField(max_length=100, null=True, verbose_name='Contacto')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')
    observaciones = peewee.TextField(null=True, verbose_name='Observaciones')
    
    def __str__(self):
        return self.razon_social
    
    class Meta:
        if LeerIni("basedatos") == "fg":
            db_table = 'proveedores'
        else:
            db_table = 'proveedor'


class ProcesoLista(ModeloBase):
    
    id = peewee.AutoField(primary_key=True)
    proveedor = peewee.ForeignKeyField(
        model=Proveedor,
        backref='procesos',
        null=False,
        verbose_name='Proveedor'
    )
    codigo = peewee.CharField(max_length=20, null=False, verbose_name='Código')
    columna = peewee.CharField(max_length=20, null=False, verbose_name='Columna')
    
    class Meta:
        db_table = 'proceso_lista'
    
    def __str__(self):
        return self.codigo

    
class ValidaProveedor(ValidaConTexto):
    modelo = Proveedor
    nombre = Proveedor.razon_social
    codigo = Proveedor.id
    campos = [Proveedor.id.name, Proveedor.razon_social.name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Proveedor"
    condiciones = [Proveedor.activo == True]
    campos_busqueda = [Proveedor.razon_social.column_name]

class BuscaProveedor(Buscador):
    modelo = Proveedor
    nombre = Proveedor.razon_social
    codigo = Proveedor.id
    campos = [Proveedor.id.name, Proveedor.razon_social.name]
    campos_busqueda = [Proveedor.razon_social.column_name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Buscar Proveedores"
    valorRetorno = None
    lRetval = False  # indica si presiono en aceptar o cancelar            
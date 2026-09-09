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
        # Antes: ParamSist.ObtenerParametro(...) == 'ARG' else 'RUC' - requeria DB al importar.
        # El sistema RND opera casi siempre con nacionalidad ARG; se hardcodea 'CUIT'
        # y se evita la query al import-time. Si la nacionalidad cambia a RUC, mover
        # esta decision a runtime (ej. al inicializar la app o al construir el form).
        verbose_name='CUIT'
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


class LugarEntrega(ModeloBase):
    """Destino operativo asociado a un cliente.

    Los campos direccion/localidad/ruta existentes en Cliente se conservan por
    compatibilidad con instalaciones anteriores. Los nuevos flujos deben usar
    este modelo para permitir múltiples destinos por cliente.
    """

    id = peewee.AutoField(primary_key=True)
    cliente = peewee.ForeignKeyField(
        model=Cliente,
        backref='lugares_entrega',
        null=False,
        on_update='CASCADE',
        on_delete='CASCADE',
        verbose_name='Cliente',
    )
    nombre = peewee.CharField(max_length=100, null=False, verbose_name='Nombre / Referencia')
    direccion = peewee.CharField(max_length=150, null=True, verbose_name='Dirección')
    localidad = peewee.ForeignKeyField(
        model=Localidades,
        backref='lugares_entrega',
        null=True,
        on_update='CASCADE',
        on_delete='RESTRICT',
        verbose_name='Localidad',
    )
    ruta_reparto = peewee.ForeignKeyField(
        model=RutaReparto,
        backref='lugares_entrega',
        null=True,
        on_update='CASCADE',
        on_delete='RESTRICT',
        verbose_name='Ruta de Reparto',
    )
    principal = peewee.BooleanField(default=False, verbose_name='Principal')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')
    observaciones = peewee.TextField(null=True, verbose_name='Observaciones')

    class Meta:
        db_table = 'lugares_entrega'
        indexes = (
            (('cliente', 'nombre'), True),
        )

    def __str__(self):
        return self.nombre

    @classmethod
    def activos_cliente(cls, cliente_id):
        return cls.select().where(
            (cls.cliente == cliente_id) & (cls.activo == True)
        ).order_by(cls.principal.desc(), cls.nombre)

    @classmethod
    def principal_cliente(cls, cliente_id):
        return cls.get_or_none(
            (cls.cliente == cliente_id) &
            (cls.principal == True) &
            (cls.activo == True)
        )

    def save(self, *args, **kwargs):
        with self._meta.database.atomic():
            resultado = super().save(*args, **kwargs)
            if self.principal:
                (LugarEntrega
                 .update(principal=False)
                 .where(
                     (LugarEntrega.cliente == self.cliente_id) &
                     (LugarEntrega.id != self.id) &
                     (LugarEntrega.principal == True)
                 )
                 .execute())
            return resultado


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

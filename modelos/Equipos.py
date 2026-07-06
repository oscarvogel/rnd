import peewee
from datetime import date, timedelta

from modelos.Empleados import Empleado
from modelos.ModeloBase import ModeloBase
from modelos.Tablas import TipoDeMovil
from pyqt5libs.libs.vistas.Busqueda import UiBusqueda
from pyqt5libs.pyqt5libs.Validaciones import ValidaConTexto
from pyqt5libs.pyqt5libs.utiles import LeerIni


class Equipos(ModeloBase):
    if LeerIni("basedatos") == "fg":
        id = peewee.AutoField(primary_key=True, column_name = 'idMovil')
        descripcion = peewee.CharField(max_length=100, null=False, column_name = 'detalle')
        fecha_adquisicion = peewee.DateField(null=True, verbose_name = 'Fecha de Adquisición', column_name='fecha_alta')
        fecha_baja = peewee.DateField(null=True, verbose_name='Fecha de Baja', column_name='FechaBaja')
        tipo_movil = peewee.ForeignKeyField(model=TipoDeMovil, verbose_name='Tipo de Movil', column_name='tipo_movil')
        baja = peewee.BooleanField()
    else:
        id = peewee.AutoField(primary_key=True)
        descripcion = peewee.CharField(max_length=100, null=False)
        fecha_adquisicion = peewee.DateField(null=True, verbose_name = 'Fecha de Adquisición')
        fecha_baja = peewee.DateField(null=True, verbose_name='Fecha de Baja')
        tipo_movil = peewee.ForeignKeyField(model=TipoDeMovil, verbose_name='Tipo de Movil')
    observaciones = peewee.TextField(null=True)
    capacidad_tanque = peewee.DecimalField(max_digits=10, decimal_places=2, null=True, verbose_name='Capacidad Tanque')
    activo = peewee.BooleanField(default=True)
    patente = peewee.CharField(max_length=10, null=False)
    nro_chasis = peewee.CharField(max_length=30, null=False, unique=True, verbose_name='Nro. Chasis')
    nro_motor = peewee.CharField(max_length=30, null=False, unique=True, verbose_name='Nro. Motor')
    movil_asociado = peewee.IntegerField(null=True, verbose_name='Movil Asociado')

    class Meta:
        if LeerIni("basedatos") == "fg":
            db_table = "moviles"
        else:
            db_table = 'equipos'
    
    def __str__(self):
        return f"{self.descripcion} ({self.patente})"

class Vencimientos(ModeloBase):
    
    id = peewee.AutoField(primary_key=True)
    personal = peewee.ForeignKeyField(model=Empleado, null=True, backref='vencimientos')
    movil = peewee.ForeignKeyField(model=Equipos, null=True, backref='vencimientos')
    fecha_vencimiento = peewee.DateField()
    descripcion = peewee.CharField(max_length=30)

class ChoferEquipo(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    empleado = peewee.ForeignKeyField(model=Empleado, null=False, backref='choferes_equipo')
    movil = peewee.ForeignKeyField(model=Equipos, null=False, backref='choferes_equipo')
    fecha_inicio = peewee.DateField(null=False)
    fecha_fin = peewee.DateField(null=True)

    class Meta:
        db_table = 'choferes_equipos'
        
    @classmethod
    def ultimo_chofer(cls, movil_id):
        """
        Obtiene el último chofer asignado a un equipo.
        """
        return (
            cls.select()
            .where(cls.movil == movil_id)
            .order_by(cls.fecha_inicio.desc())
            .first()
        )
        
class ValidaEquipo(ValidaConTexto):
    modelo = Equipos
    nombre = Equipos.descripcion
    codigo = Equipos.id
    campos = [Equipos.id.name, Equipos.patente.name, Equipos.descripcion.name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Unidad Movil"
    condiciones = [Equipos.activo == True]
    campos_busqueda = [Equipos.patente.name, Equipos.descripcion.name]
    campoNombre = [Equipos.descripcion, Equipos.patente]


class BuscaEquipos(UiBusqueda):
    
    def ArmaBusqueda(self, rows):
        if isinstance(self.campoBusqueda, list):
            rows = rows.where(Equipos.patente.contains(self.lineEdit.text()) | Equipos.descripcion.contains(self.lineEdit.text()))
        else:
            rows = rows.where(self.campoBusqueda.contains(self.lineEdit.text()))
        return rows
    
    
class ValidaEquipoConTexto(ValidaConTexto):
    """
    Clase para validar equipos con un campo de texto.
    Utiliza la clase ValidaConTexto para realizar la validación.
    """
    modelo = Equipos
    nombre = Equipos.descripcion
    codigo = Equipos.id
    campos = [Equipos.id.name, Equipos.patente.name, Equipos.descripcion.name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Unidad Movil"
    condiciones = [Equipos.activo == True]
    campos_busqueda = [Equipos.patente.column_name, Equipos.descripcion.column_name]
    clasebusqueda = BuscaEquipos
    campoNombre = [Equipos.descripcion, Equipos.patente]
    

def get_vencimientos_proximos():
    hoy = date.today()
    limite = hoy + timedelta(days=10)
    
    return (
        Vencimientos.select()
        .where(Vencimientos.fecha_vencimiento.between(hoy, limite))
        .order_by(Vencimientos.fecha_vencimiento)
    )
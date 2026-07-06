import peewee
from modelos.Clientes import Cliente, RutaReparto
from modelos.Empleados import Empleado
from modelos.Equipos import Equipos
from modelos.ModeloBase import ModeloBase


class HojaDeRuta(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    fecha = peewee.DateField()
    cliente = peewee.ForeignKeyField(Cliente, backref="hoja_ruta", on_update='CASCADE', on_delete='RESTRICT')
    nombre_cliente = peewee.CharField(max_length=100, default='')
    ruta = peewee.ForeignKeyField(RutaReparto, backref="hoja_ruta", on_update='CASCADE', on_delete='RESTRICT')
    comprobante = peewee.CharField(max_length=20)
    producto = peewee.CharField(max_length=100)
    cantidad = peewee.DecimalField(max_digits=16, decimal_places=2)
    kg = peewee.DecimalField(max_digits=16, decimal_places=2)
    cantidad_bultos = peewee.DecimalField(max_digits=16, decimal_places=2)
    observaciones = peewee.CharField(max_length=100)
    equipo_asignado = peewee.ForeignKeyField(Equipos, backref="hoja_ruta", on_update='CASCADE', on_delete='RESTRICT')
    responsable = peewee.ForeignKeyField(Empleado, backref="hoja_ruta", on_update='CASCADE', on_delete='RESTRICT')
    
    class Meta:
        db_table = 'hoja_de_ruta'
    
    def __str__(self):
        return self.comprobante
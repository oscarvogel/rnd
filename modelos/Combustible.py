from datetime import datetime
from email.policy import default
import peewee
from modelos.Equipos import Equipos
from modelos.ModeloBase import ModeloBase
from modelos.Proveedores import Proveedor
from modelos.Tablas import Panioles, TipoCombustible, UnidadNegocio
from pyqt5libs.pyqt5libs.ComboBox import ComboSQL
from pyqt5libs.pyqt5libs.utiles import LeerConf, LeerIni


class MovimientoCombustible(ModeloBase):
    
    if LeerIni("basedatos") == "fg":
        id = peewee.AutoField(primary_key=True, column_name='idCargaComb')
        equipo = peewee.ForeignKeyField(model=Equipos, backref='movimiento_combustible', verbose_name='Equipo', column_name='idMovil')
        km_hora = peewee.FloatField(null=False, verbose_name='Km/Hora', column_name='KM')
        remito = peewee.CharField(max_length=12, null=False, verbose_name='Remito', column_name='comprobante')
        fecha_grabacion = peewee.DateTimeField(null=False, verbose_name='Fecha Grabación', default=datetime.now(), column_name='_fecha')
    else:
        id = peewee.AutoField(primary_key=True)
        tipo_combustible = peewee.ForeignKeyField(model=TipoCombustible, backref='movimiento_combustible', verbose_name='Tipo de Combustible')
        equipo = peewee.ForeignKeyField(model=Equipos, backref='movimiento_combustible', verbose_name='Equipo')
        km_hora = peewee.FloatField(null=False, verbose_name='Km/Hora')
        precio_litro = peewee.DecimalField(max_digits=10, decimal_places=2, null=False, verbose_name='Precio por Litro')
        ingreso = peewee.FloatField(null=False, verbose_name='Cantidad')
        egreso = peewee.FloatField(null=False, verbose_name='Egreso')
        unidad_negocio = peewee.ForeignKeyField(model=UnidadNegocio, backref='movimiento_combustible', verbose_name='Unidad de Negocio')
        paniol = peewee.ForeignKeyField(model=Panioles, backref='movimiento_combustible', verbose_name='Paniol')
        remito = peewee.CharField(max_length=12, null=False, verbose_name='Remito')
        idtabla = peewee.IntegerField(null=False, verbose_name='ID Tabla')
        tabla = peewee.CharField(max_length=30, null=False, verbose_name='Tabla')
        usuario = peewee.CharField(max_length=30, null=False, verbose_name='Usuario', default=LeerConf('usuario'))
        fecha_grabacion = peewee.DateTimeField(null=False, verbose_name='Fecha Grabación', default=datetime.now())
        observaciones = peewee.TextField(null=True, verbose_name='Observaciones')
        proveedor = peewee.ForeignKeyField(Proveedor, default=1)
        periodo = peewee.CharField(max_length=6)
    
    fecha = peewee.DateField(null=False, verbose_name='Fecha')

    class Meta:
        if LeerIni("basedatos") == "fg":
            db_table = 'cargacomb'
        else:
            db_table = 'movimientocombustible'
            
        
    @classmethod
    def obtener_ultima_km_hora(cls, equipo_id, fecha_consulta=datetime.now().date()):
        """
        Obtiene el último valor de 'km_hora' para un equipo en una fecha específica.
        
        :param equipo_id: ID del equipo.
        :param fecha_consulta: Fecha a consultar (datetime.date).
        :return: Valor de km_hora o 0 si no hay registros.
        """
        try:
            registro = cls.select().where(
                cls.equipo == equipo_id,
                cls.fecha < fecha_consulta
            ).order_by(cls.fecha_grabacion.desc()).get()

            return registro.km_hora
        except cls.DoesNotExist:
            return 0
        
    @classmethod
    def existe_remito(cls, numero_remito):
        """
        Verifica si existe un registro con el número de remito dado.
        
        :param numero_remito: Número de remito a buscar (str).
        :return: True si existe, False si no.
        """
        return cls.select().where(cls.remito == numero_remito).exists()

    @classmethod
    def obtener_saldo_combustible(cls, fecha_hasta, paniol_id=None, equipo_id=None, unidad_negocio_id=None):
        """
        Calcula el saldo de combustible hasta una fecha determinada, con filtros opcionales.
        
        :param fecha_hasta: Fecha hasta la cual calcular el saldo (datetime.date)
        :param paniol_id: ID del paniol (opcional)
        :param equipo_id: ID del equipo (opcional)
        :param unidad_negocio_id: ID de la unidad de negocio (opcional)
        :return: Diccionario con saldos por tipo de combustible
        """
        query = cls.select(
            cls.tipo_combustible,
            peewee.fn.SUM(cls.ingreso).alias('total_ingreso'),
            peewee.fn.SUM(cls.egreso).alias('total_egreso')
        ).where(
            cls.fecha < fecha_hasta
        ).group_by(cls.tipo_combustible)

        if paniol_id:
            query = query.where(cls.paniol == paniol_id)
        if equipo_id:
            query = query.where(cls.equipo == equipo_id)
        if unidad_negocio_id:
            query = query.where(cls.unidad_negocio == unidad_negocio_id)

        saldos = {}
        for resultado in query:
            saldo = float(resultado.total_ingreso or 0) - float(resultado.total_egreso or 0)
            saldos[resultado.tipo_combustible.id] = {
                'tipo_combustible': resultado.tipo_combustible.descripcion,
                'saldo': saldo,
                'total_ingreso': float(resultado.total_ingreso or 0),
                'total_egreso': float(resultado.total_egreso or 0)
            }

        return saldos

    def get_registro_inicial(equipo_id, fecha_inicio):
        return (MovimientoCombustible
                .select()
                .where(
                    (MovimientoCombustible.equipo == equipo_id) &
                    (MovimientoCombustible.fecha <= fecha_inicio) &
                    (MovimientoCombustible.egreso > 0)
                )
                .order_by(MovimientoCombustible.fecha.desc(), MovimientoCombustible.km_hora.desc())
                .first())    
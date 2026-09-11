import logging
import sys
import traceback
import threading
import peewee

from modelos.Clientes import CodigoClienteProveedor, LugarEntrega, Cliente
from modelos.Empleados import ConceptoLiquidacion
from modelos.EstadoHojaRuta import EstadoHojaRuta
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import Auditoria, db
from playhouse.migrate import MySQLMigrator, CharField, migrate, DecimalField, IntegerField, BooleanField, FloatField, TextField, TimeField

from modelos.Clientes import Localidades
from modelos.Proveedores import ProcesoLista, Proveedor
from pyqt5libs.pyqt5libs.utiles import LeerIni

class MigracionBaseDatos:
    
    migraciones = []
    colentero = IntegerField(default=0)
    colentero1 = IntegerField(default=1)
    colfloat = FloatField(default=0)
    
    def __init__(self):
        database = db
        self.migraciones = []
        self.migrator = MySQLMigrator(database)
        self.thread = None
        self.Migrar()

    def MigrarVersion(self):
        migrator = self.migrator        
        observaciones = CharField(max_length=200, default='')
        orden_servicio = CharField(max_length=12, default='')
        self.migraciones.append(migrator.add_column('cliente', 'ruta_reparto_id', self.colentero))
        self.migraciones.append(migrator.add_foreign_key_constraint('cliente', 'ruta_reparto_id', 'rutas_reparto', 'id',
                                   on_delete='RESTRICT', on_update='CASCADE'))
        self.migraciones.append(migrator.add_column('cliente', 'localidad_id', self.colentero))
        self.migraciones.append(migrator.add_foreign_key_constraint('cliente', 'localidad_id', 'localidades', 'id',
                                   on_delete='RESTRICT', on_update='CASCADE'))        
        self.migraciones.append(migrator.add_column('hoja_de_ruta', 'nombre_cliente', CharField(max_length=100, default='')))
        self.RealizaMigraciones()

        modelos = [
            (CodigoClienteProveedor, "CodigoClienteProveedor"),
            (Localidades, "Localidades"),
            (LugarEntrega, "LugarEntrega"),
            (HojaDeRuta, "HojaDeRuta"),
            (ProcesoLista, "ProcesoLista"),
            (ConceptoLiquidacion, "ConceptoLiquidacion"),
            (EstadoHojaRuta, "EstadoHojaRuta"),
        ]
        for modelo, nombre in modelos:
            try:
                modelo().create_table()
            except peewee.OperationalError:
                logging.debug("Tabla %s ya existe, no se crea de nuevo", nombre)

        # El FK se agrega después de crear lugares_entrega para instalaciones existentes.
        migraciones_lugares = [
            migrator.add_column(
                'hoja_de_ruta',
                'lugar_entrega_id',
                IntegerField(null=True),
            ),
            migrator.add_foreign_key_constraint(
                'hoja_de_ruta',
                'lugar_entrega_id',
                'lugares_entrega',
                'id',
                on_delete='RESTRICT',
                on_update='CASCADE',
            ),
        ]
        self.migraciones = migraciones_lugares
        self.RealizaMigraciones()

        # #89: la importación puede dejar pedidos pendientes de resolver sin
        # interrumpir al operador. Cliente y ruta deben aceptar NULL hasta la
        # revisión previa al cierre de la hoja de ruta.
        self.migraciones = [
            migrator.alter_column_type(
                'hoja_de_ruta',
                'cliente_id',
                IntegerField(null=True),
            ),
            migrator.alter_column_type(
                'hoja_de_ruta',
                'ruta_id',
                IntegerField(null=True),
            ),
        ]
        self.RealizaMigraciones()

        # #92: cada proveedor define explícitamente cómo se importa su archivo.
        self.migraciones = [
            migrator.add_column(
                'proveedor',
                'importador',
                CharField(max_length=30, default='AUTO'),
            ),
        ]
        self.RealizaMigraciones()
        self._crear_lugares_iniciales()

    def _crear_lugares_iniciales(self):
        """Preserva dirección/ruta actuales creando un destino principal inicial.

        Es idempotente: sólo crea el lugar cuando el cliente aún no posee destinos.
        No intenta fusionar clientes duplicados porque esa decisión requiere revisión
        humana y no debe ocurrir automáticamente en una migración.
        """
        try:
            for cliente in Cliente.select():
                if LugarEntrega.select().where(LugarEntrega.cliente == cliente.id).exists():
                    continue
                if not (cliente.direccion or cliente.localidad_id or cliente.ruta_reparto_id):
                    continue
                nombre = "Principal"
                if cliente.localidad_id:
                    try:
                        nombre = cliente.localidad.descripcion
                    except Exception:
                        pass
                LugarEntrega.create(
                    cliente=cliente,
                    nombre=nombre,
                    direccion=cliente.direccion,
                    localidad=cliente.localidad_id,
                    ruta_reparto=cliente.ruta_reparto_id,
                    principal=True,
                    activo=True,
                )
        except Exception:
            logging.exception("No se pudieron crear los lugares de entrega iniciales")
                    
    def RealizaMigraciones(self):
        IGNORAR = {1060, 1022, 1061, 1091}
        for m in self.migraciones:
            try:
                migrate(m)
            except Exception as e:
                code = None
                if hasattr(e, "args") and e.args:
                    code = e.args[0]
                if code in IGNORAR:
                    logging.debug(f"Migracion ya aplicada (mysql {code}): {e}")
                    continue
                ex = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
                self.Traceback = ''.join(ex)
                logging.debug(self.Traceback)
                print(self.Traceback)

    def _run_in_thread(self):
        self.MigrarVersion()

    def Migrar(self):
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run_in_thread)
            self.thread.daemon = True
            self.thread.start()
        else:
            print("Ya hay una migración en curso")

    def esperar_migracion(self):
        if self.thread and self.thread.is_alive():
            self.thread.join()

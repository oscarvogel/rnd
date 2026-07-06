import logging
import sys
import traceback
import threading
import peewee

from modelos.Clientes import CodigoClienteProveedor
from modelos.Empleados import ConceptoLiquidacion
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import Auditoria, db
from playhouse.migrate import MySQLMigrator, CharField, migrate, DecimalField, IntegerField, BooleanField, FloatField, TextField, TimeField

from modelos.Clientes import Localidades
from modelos.Proveedores import ProcesoLista
from pyqt5libs.pyqt5libs.utiles import LeerIni

class MigracionBaseDatos:
    
    migraciones = []
    colentero = IntegerField(default=0)
    colentero1 = IntegerField(default=1)
    colfloat = FloatField(default=0)
    
    def __init__(self):
        database = db  # Asegúrate de que 'db' está definido en algún lugar
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

        try:
            CodigoClienteProveedor().create_table()
        except peewee.OperationalError:
            logging.debug("Tabla CodigoClienteProveedor ya existe, no se crea de nuevo")

        try:
            Localidades().create_table()
        except peewee.OperationalError:
            logging.debug("Tabla Localidades ya existe, no se crea de nuevo")

        try:
            HojaDeRuta().create_table()
        except peewee.OperationalError:
            logging.debug("Tabla HojaDeRuta ya existe, no se crea de nuevo")
        
        try:
            ProcesoLista().create_table()
        except peewee.OperationalError:
            logging.debug("Tabla ProcesoLista ya existe, no se crea de nuevo")
        
        try:
            ConceptoLiquidacion().create_table()
        except peewee.OperationalError:
            logging.debug("Tabla ProcesoLista ya existe, no se crea de nuevo")
                    
    def RealizaMigraciones(self):
        for m in self.migraciones:
            try:
                migrate(m)
            except Exception as e:
                ex = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
                self.Traceback = ''.join(ex)
                logging.debug(self.Traceback)
                print(self.Traceback)

    def _run_in_thread(self):
        """Método interno que ejecuta las migraciones en el thread"""
        self.MigrarVersion()

    def Migrar(self):
        """Inicia la migración en un thread separado"""
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run_in_thread)
            self.thread.daemon = True  # Opcional: hace que el thread no impida la salida del programa
            self.thread.start()
        else:
            print("Ya hay una migración en curso")

    def esperar_migracion(self):
        """Espera a que la migración termine (opcional)"""
        if self.thread and self.thread.is_alive():
            self.thread.join()
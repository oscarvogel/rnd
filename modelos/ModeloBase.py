# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
from datetime import datetime, date, time
from decimal import Decimal
import json
import mongoengine
import os
from peewee import Model, CharField, TextField, DateTimeField, ForeignKeyField
from peewee import SQL

#Modelo base del cual derivan todos los modelos del sistema
import pyodbc
from mongoengine import Document, DynamicDocument
from peewee import SqliteDatabase, MySQLDatabase, Model, BooleanField, Proxy, OperationalError
from functools import wraps
import time
from peewee import OperationalError, InterfaceError, DoesNotExist

MAX_REINTENTOS = int(os.getenv('RND_DB_MAX_REINTENTOS', '5'))
RETRY_BASE_DELAY = float(os.getenv('RND_DB_RETRY_BASE_DELAY', '1'))
# Backoff exponencial cap: 60s entre reintentos para no esperar infinito en
# una red muy lenta.
RETRY_MAX_DELAY = float(os.getenv('RND_DB_RETRY_MAX_DELAY', '60'))

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

# database_proxy = Proxy()  # Create a proxy for our db.
from pyqt5libs.pyqt5libs.utiles import LeerConf, LeerIni

db = None

dbsqlite = SqliteDatabase(':memory:', pragmas={'journal_mode': 'wal'})

def _env_secret(*names):
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ''

def _mysql_password():
    return _env_secret('RND_DB_PASSWORD', 'MYSQL_PASSWORD', 'DB_PASSWORD')

if LeerIni(clave='base') == 'sqlite':
    db = SqliteDatabase('sistema.db')
    # db = SqliteExtDatabase('sistema.db')
    # db = SqlCipherDatabase('sistema.db', passphrase='Femag#SanAberto2019', pragmas={
    #     'cipher_page_size': 1024 * 16,
    #     'cache_size': 10000})  # 10,000 16KB pages, or 160MB.
else:
    if LeerIni(clave='debug') == 'S':
        db = MySQLDatabase(LeerIni("basedatos"),
                        user=LeerIni("user"),
                        password=_mysql_password(),
                        host=LeerIni("host"),
                        port=int(LeerIni("port") or '3306'),
                        connect_timeout=10)
    elif LeerIni(clave='host') == 'srv1723.hstgr.io':
        db = MySQLDatabase(LeerIni("basedatos"),
                        user=LeerIni("user"),
                        password=_mysql_password(),
                        host=LeerIni("host"),
                        port=int(LeerIni("port") or '3306'))
    else:
        db = MySQLDatabase(LeerIni("basedatos"),
                           user=LeerIni("user"),
                           password=_mysql_password(),
                           host=LeerIni("host"),
                           port=int(LeerIni("port") or '3306'))

def model_to_dict(instance):
    data = {}
    for field in instance._meta.fields:
        value = getattr(instance, field)
        if isinstance(value, (datetime, date)):
            value = value.isoformat()  # Convierte a cadena ISO: "2025-04-05" o "2025-04-05T12:30:00"
        elif isinstance(value, Model):  # Si es una clave foránea
            value = value._pk  # Solo guarda la PK
        data[field] = value
    return data

def default_serializer(obj):
    if isinstance(obj, (Decimal, int, float)):
        return str(obj)  # O float(obj) si prefieres que se vea como número
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, (bool)):
        return 'Si' if obj else 'No'
    raise TypeError(f"Object of type {obj} is not JSON serializable")


def reconnect_if_needed(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        for intento in range(1, MAX_REINTENTOS + 1):
            try:
                # Verificar si la conexión está cerrada y reconectar si es necesario
                if db.is_closed():
                    print(f"[Intento {intento}] La conexión a la base de datos está cerrada. Reconectando...")
                    db.connect(reuse_if_open=True)

                # Ejecutar el método original
                return method(self, *args, **kwargs)

            except (OperationalError, InterfaceError, ConnectionError, Exception) as e:
                print(f"Error al conectarse a la base de datos: {e}")
                db.close()  # Cerramos la conexión rota si existe

                if intento < MAX_REINTENTOS:
                    # Backoff exponencial: 1s, 2s, 4s, 8s, ... capeado por RETRY_MAX_DELAY.
                    delay = min(RETRY_BASE_DELAY * (2 ** (intento - 1)), RETRY_MAX_DELAY)
                    print(f"Reintentando en {delay:.1f} segundo(s)...")
                    time.sleep(delay)
                else:
                    raise ConnectionError("No se pudo restablecer la conexión después de varios intentos.")
        return None
    return wrapper

class ModeloBase(Model):

    def __init__(self, *args, **kwargs):
        super(ModeloBase, self).__init__(*args, **kwargs)

    def getDb(self):
        return db

    def connect(self):
        db.connect(reuse_if_open=True)

    def close(self):
        db.close()

    """A base model that will use our MySQL database"""
    class Meta:
        database = db
    
    def save(self, *args, **kwargs):
        # Obtener la clave primaria (PK)
        pk_value = self.id  # Ajusta esto si tu PK tiene otro nombre como 'uuid', etc.
        action = "crear" if pk_value is None else "editar"
        old_data = None

        if pk_value is not None:
            try:
                old_instance = type(self).get_by_id(pk_value)
                old_data = model_to_dict(old_instance)
            except type(self).DoesNotExist:
                pass

        result = super(ModeloBase, self).save(*args, **kwargs)

        if pk_value is not None:
            new_data = model_to_dict(self)

            # Auditoria.create(
            #     modelo=self.__class__.__name__,
            #     accion=action,
            #     registro_id=str(pk_value) if pk_value is not None else str(self.id),  # después de guardar, puede haber cambiado
            #     datos_antiguos=json.dumps(old_data, default=default_serializer),
            #     datos_nuevos=json.dumps(new_data, default=default_serializer),
            #     usuario=LeerConf("usuario")  # Puedes reemplazar esto por el usuario autenticado
            # )            
            Auditoria.create(
                modelo=self.__class__.__name__,
                accion=action,
                registro_id=str(pk_value) if pk_value is not None else str(self.id),  # después de guardar, puede haber cambiado
                datos_antiguos=old_data,
                datos_nuevos=new_data,
                usuario=LeerConf("usuario")  # Puedes reemplazar esto por el usuario autenticado
            )            
            

        return result

    def delete_instance(self, *args, **kwargs):
        old_data = model_to_dict(self)
        result = super(ModeloBase, self).delete_instance(*args, **kwargs)

        # Auditoria.create(
        #     modelo=self.__class__.__name__,
        #     accion="borrar",
        #     registro_id=str(self.id),
        #     datos_antiguos=json.dumps(old_data, default=default_serializer),
        #     usuario=LeerConf("usuario")  # Reemplaza si tienes sistema de usuarios
        # )
        Auditoria.create(
            modelo=self.__class__.__name__,
            accion="borrar",
            registro_id=str(self.id),
            datos_antiguos=old_data,
            usuario=LeerConf("usuario")  # Reemplaza si tienes sistema de usuarios
        )

        return result        

class Auditoria(Model):
    modelo = CharField()         # Nombre del modelo afectado (ej: "Usuario")
    accion = CharField()         # Acción realizada: "crear", "editar", "borrar"
    registro_id = CharField()    # ID del registro afectado
    datos_antiguos = TextField(null=True)   # Valores antes del cambio (en JSON)
    datos_nuevos = TextField(null=True)     # Valores después del cambio (en JSON)
    fecha = DateTimeField(constraints=[SQL("DEFAULT CURRENT_TIMESTAMP")])  # Fecha automática
    usuario = CharField(null=True)  # Si usas autenticación, puedes registrar al usuario
    
    class Meta:
        database = db

def obtener_historial(modelo_nombre, registro_id):
    logs = Auditoria.select().where(
        (Auditoria.modelo == modelo_nombre) &
        (Auditoria.registro_id == int(registro_id))
    ).order_by(Auditoria.fecha.asc())

    historial = []

    for log in logs:
        try:
            old_data = json.loads(log.datos_antiguos) if log.datos_antiguos else {}
        except json.JSONDecodeError:
            old_data = {}

        try:
            new_data = json.loads(log.datos_nuevos) if log.datos_nuevos else {}
        except json.JSONDecodeError:
            new_data = {}

        # Detectar diferencias entre campos
        historial.append({
                    "fecha": log.fecha.strftime("%Y-%m-%d %H:%M"),
                    "accion": log.accion,
                    "antes": "\n".join([f"{k}: {v}" for k, v in old_data.items()]),
                    "despues": "\n".join([f"{k}: {v}" for k, v in new_data.items()]),
                    "id": log.id,
                })

    return historial
    
# database_proxy = Proxy()  # Create a proxy for our db.
#
# db = None
# dbsqlite = SqliteDatabase(':memory:', pragmas={'journal_mode': 'wal'})
#
# def inicializadb():
#     if LeerIni(clave='base') == 'sqlite':
#         db = SqliteDatabase('sistema.db')
#     else:
#         db = MySQLDatabase(LeerIni("basedatos"),
#                            user='root',
#                            password='<DB_PASSWORD>',
#                            host=LeerIni("ServerDB"),
#                            port=int(LeerIni("port")))
#     database_proxy.initialize(db)
#
# class ModeloBase(Model):
#
#     def __init__(self, *args, **kwargs):
#         super(ModeloBase, self).__init__(*args, **kwargs)
#
#     @classmethod
#     def getDb(cls):
#         if not db:
#             inicializadb()
#         return db
#
#     def connect(self):
#         if not db:
#             inicializadb()
#         db.connect(reuse_if_open=True)
#
#     def close(self):
#         if not db:
#             inicializadb()
#         db.close()
#
#     """A base model that will use our MySQL database"""
#     class Meta:
#         if not db:
#             inicializadb()
#
#         database = database_proxy


class BitBooleanField(BooleanField):
    field_type = 'Bit'

    def db_value(self, value):
        if isinstance(db, SqliteDatabase):
            return value == 1
        return value

    def python_value(self, value):
        if isinstance(db, SqliteDatabase):
            return value == 1
        return value == b'\01'

class ModeloBaseSQLite(Model):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getDb(self):
        return dbsqlite

    def connect(self):
        dbsqlite.connect(reuse_if_open=True)

    def close(self):
        dbsqlite.close()

    """A base model that will use our MySQL database"""
    class Meta:
        database = dbsqlite

def executeScriptsFromFile(filename):
    # if not db:
    #     inicializadb()

    database = db
    # Open and read the file as a single buffer
    fd = open(filename, 'r')
    sqlFile = fd.read()
    fd.close()

    # all SQL commands (split on ';')
    sqlCommands = sqlFile.split(';')

    # Execute every command from the input file
    for command in sqlCommands:
        # This will skip and report errors
        # For example, if the tables do not yet exist, this will skip over
        # the DROP TABLE commands
        try:
            database.execute_sql(command)
        except OperationalError as msg:
            print("Command skipped: ", msg)
        except:
            pass

class ModeloBaseSQLServer:
    conexion = None
    tabla = ""
    campo_id = ""
    server = LeerIni("ServerDBRoble")
    base_datos = LeerIni("basedatosql")

    def __init__(self, servidor='', base_datos=''):
        if servidor:
            self.server = servidor
        if base_datos:
            self.base_datos = base_datos

    def connect(self):
        sql_user = os.getenv('RND_SQLSERVER_USER', 'sa')
        sql_password = os.getenv('RND_SQLSERVER_PASSWORD', '')
        self.conexion = pyodbc.connect('DRIVER={SQL Server};'
                                       'SERVER=' + self.server + ';'
                                       'DATABASE=' + self.base_datos + ';'
                                       'UID=' + sql_user + ';PWD=' + sql_password)
        return self.conexion

    def close(self):
        self.getConexion().close()

    def getConexion(self):
        if not self.conexion:
            self.connect()
        return self.conexion

    def getCursor(self):
        cursor = self.getConexion().cursor()
        return cursor

    def ejecutar(self, query, params=None):
        cursor = self.getCursor()
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        query_result = [dict(line) for line in
                        [zip([column[0] for column in cursor.description], row) for row in cursor.fetchall()]]
        return query_result

    def get_by_id(self, id=''):
        query = f"""
            select *
                from {self.tabla}
                where {self.campo_id } = ?
        """
        dato = self.ejecutar(query, [id,])
        return dato[0] if dato else {}

    def get(self, query, params=None):
        dato = self.ejecutar(query, params)
        return dato[0]

db_mongo = mongoengine.connect(
    os.getenv('RND_MONGO_DB', 'formhub'),
    username=os.getenv('RND_MONGO_USER') or None,
    password=os.getenv('RND_MONGO_PASSWORD') or None,
    authentication_source=os.getenv('RND_MONGO_AUTH_SOURCE', 'admin')
)

class ModeloBaseMongoDB(DynamicDocument):
    meta = {"allow_inheritance": True}  # Habilita la herencia
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def getDb(self):
        return db_mongo

    def connect(self):
        db_mongo.connect(reuse_if_open=True)

    def close(self):
        db_mongo.disconnect()

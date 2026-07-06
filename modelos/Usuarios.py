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
from peewee import AutoField, CharField, ForeignKeyField, DoesNotExist, BooleanField

from modelos.ModeloBase import ModeloBase
from pyqt5libs.pyqt5libs.ComboBox import ComboSQL
from pyqt5libs.pyqt5libs.utiles import GrabaConf, LeerConf



class Usuario(ModeloBase):

    usu_id = AutoField(primary_key=True, db_column='usu_id')
    usuario = CharField(max_length=30)
    nombre = CharField(max_length=30)
    apellido = CharField(max_length=30)
    clave = CharField(max_length=30)
    user_level = CharField(max_length=2)
    usuario_activo = BooleanField(default=0, db_column='activo')

    class Meta:
        table_name = "usuarios"

    def ValidaPassword(self, usuario='', password=''):
        usu = Usuario.get_by_id(usuario)
        if usu.clave == password.upper():
            GrabaConf(valor=usu.usuario, clave="usuario")
            GrabaConf(valor=password.upper(), clave="password")
            return True
        else:
            return False

    def IsAdmin(self, usu_id=0):
        usu = Usuario.get_by_id(usu_id)
        if usu.user_level == '01':
            return True
        else:
            return False

    @classmethod
    def getUsuario(cls):
        return LeerConf('idUsuario')

    @classmethod
    def UsuarioVendedor(cls):
        try:
            usu = Usuario.get_by_id(LeerConf('idUsuario'))
            vendedor = usu.vendedor
        except DoesNotExist:
            vendedor = None
        return vendedor

class CboUsuario(ComboSQL):
    modelo = Usuario
    condicion = Usuario.usuario_activo == True
    cOrden = Usuario.usuario
    campovalor = Usuario.usu_id.column_name
    campo1 = Usuario.usuario.column_name
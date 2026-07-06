# coding=utf-8
from peewee import AutoField, ForeignKeyField, DateTimeField

from modelos.Formula import Formula
from modelos.ModeloBase import ModeloBase
from modelos.Usuarios import Usuario
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import LeerConf


class Acceso(ModeloBase):
    acc_id = AutoField(primary_key=True, db_column='acc_id')
    usu_id = ForeignKeyField(Usuario)
    for_id = ForeignKeyField(Formula)
    acc_fech = DateTimeField()

    class Meta:
        table_name = "accesos"

    def AccesoUsuario(self, for_id=1, usu_id=1, for_valid=''):
        if not usu_id:
            usu_id = 1
        if Usuario().IsAdmin(usu_id):
            return True
        else:
            if for_valid:
                formula = Formula.get(Formula.for_valid == '')
                try:
                    for_id = formula.for_id
                except:
                    pass
            data = self.select().where(Acceso.for_id == for_id,
                                       Acceso.usu_id == usu_id)
            if data.count() > 0:
                return True
            else:
                return False

    @classmethod
    def ValidaMenu(cls, for_valid = '', usu_id=1):
        if Usuario().IsAdmin(LeerConf('idUsuario')):
            return True
        else:
            try:
                formula = Formula.get(Formula.for_valid == for_valid)
            except:
                Ventanas.showAlert("Sistema", "{} no establecido".format(for_valid))
                return False
            data = cls.select().where(Acceso.for_id == formula.for_id,
                                      Acceso.usu_id == usu_id)
            if data.count() > 0:
                return True
            else:
                return False

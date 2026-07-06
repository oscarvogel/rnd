# coding=utf-8
import peewee
from peewee import AutoField, CharField, SmallIntegerField, IntegerField


from modelos.ModeloBase import ModeloBase, BitBooleanField
from pyqt5libs.pyqt5libs import Constantes
from pyqt5libs.pyqt5libs.utiles import LeerIni


class Formula(ModeloBase):
    for_id = AutoField(primary_key=True, db_column='for_id')
    for_nomb = CharField(max_length=150)
    sis_id = SmallIntegerField()
    tfo_id = SmallIntegerField()
    for_orde = IntegerField()
    for_pare = IntegerField()
    for_arch = CharField(max_length=50)
    for_imag = CharField(max_length=5)
    gfo_id = SmallIntegerField()
    for_valid = CharField(max_length=50)

    class Meta:
        table_name = "formula"

class MenuLateral(ModeloBase):

    id = peewee.AutoField()
    nombre = peewee.CharField(max_length=50)
    for_id = peewee.ForeignKeyField(Formula, db_column='for_id')
    for_pare = peewee.IntegerField(default=0)
    activo = BitBooleanField(default=True)

    class Meta:
        table_name = 'menu_lateral'

    @classmethod
    def Cabeceras(cls):
        sistema = LeerIni('sistema') or Constantes.IDSISTEMA
        datos = MenuLateral.select().join(Formula).\
            where(
                MenuLateral.for_pare == 0,
                Formula.sis_id == sistema,
                MenuLateral.activo == True
        )

        return datos
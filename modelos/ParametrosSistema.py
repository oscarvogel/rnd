# coding=utf-8
import peewee

from modelos.ModeloBase import ModeloBase


class ParamSist(ModeloBase):

    id = peewee.AutoField(db_column='idparamsist')
    parametro = peewee.CharField(unique=True, max_length=100, default='')
    valor = peewee.CharField(max_length=100, default='')

    @classmethod
    def ObtenerParametro(cls, parametro: object = '', default = '') -> object:
        if not parametro:
            return  ''

        try:
            retorno = ParamSist.select().where(ParamSist.parametro == parametro).get()
            valor = retorno.valor
        except ParamSist.DoesNotExist:
            param = ParamSist()
            param.parametro = parametro
            param.valor = default
            param.save()
            valor = parametro

        return valor

    @classmethod
    def GuardarParametro(cls, parametro='', valor=''):

        try:
            param = ParamSist.select().where(ParamSist.parametro == parametro).get()
        except ParamSist.DoesNotExist:
            param = ParamSist()

        param.parametro = parametro
        param.valor = valor
        param.save()

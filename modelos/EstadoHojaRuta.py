# coding=utf-8
from datetime import datetime

import peewee

from modelos.Clientes import RutaReparto
from modelos.ModeloBase import ModeloBase


class EstadoHojaRuta(ModeloBase):
    EN_PREPARACION = "EN_PREPARACION"
    LISTA = "LISTA"
    DESPACHADA = "DESPACHADA"

    id = peewee.AutoField(primary_key=True)
    fecha = peewee.DateField(index=True)
    ruta = peewee.ForeignKeyField(
        RutaReparto,
        backref="estados_hoja_ruta",
        on_update="CASCADE",
        on_delete="RESTRICT",
    )
    estado = peewee.CharField(max_length=20, default=EN_PREPARACION)
    actualizado_en = peewee.DateTimeField(default=datetime.now)
    actualizado_por = peewee.CharField(max_length=100, default="")

    class Meta:
        db_table = "estado_hoja_ruta"
        indexes = ((('fecha', 'ruta'), True),)

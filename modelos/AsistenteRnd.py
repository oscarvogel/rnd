# coding=utf-8
"""Persistencia compartida del Asistente RND en la base operativa."""
from datetime import datetime

import peewee

from modelos.ModeloBase import ModeloBase


class AsistenteConocimiento(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    clave = peewee.CharField(max_length=100, unique=True)
    titulo = peewee.CharField(max_length=200)
    contexto = peewee.CharField(max_length=250, default="")
    contenido = peewee.TextField()
    activo = peewee.BooleanField(default=True)
    actualizado = peewee.DateTimeField(default=datetime.now)

    class Meta:
        db_table = "asistente_conocimiento"


class AsistenteConsultaNoResuelta(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    fecha = peewee.DateTimeField(default=datetime.now)
    usuario = peewee.CharField(max_length=100, default="")
    pantalla = peewee.CharField(max_length=250, default="")
    pregunta = peewee.TextField()
    origen = peewee.CharField(max_length=50, default="assistant")
    estado = peewee.CharField(max_length=30, default="pending")

    class Meta:
        db_table = "asistente_consulta_no_resuelta"

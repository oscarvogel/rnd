# coding=utf-8
"""Dashboard operativo de RND (issue #4).

Agrupa los widgets que componen el panel de inicio despues del
login: tarjetas con indicadores, hero card de hojas de ruta del
dia y estados visibles para carga, vacio y error. La carga de
datos se delega a ``servicios.py`` para no duplicar reglas de
negocio ni queries de los modelos existentes.
"""

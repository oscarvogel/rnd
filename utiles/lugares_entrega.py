# coding=utf-8
"""Utilidades puras para resolver destinos de entrega durante la importación."""

import re
import unicodedata


def normalizar_texto(valor):
    texto = "" if valor is None else str(valor)
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower().strip()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def _terminos_lugar(lugar):
    terminos = []
    for valor in (
        getattr(lugar, "nombre", None),
        getattr(lugar, "direccion", None),
        getattr(getattr(lugar, "localidad", None), "descripcion", None),
    ):
        termino = normalizar_texto(valor)
        if len(termino) >= 3 and termino not in terminos:
            terminos.append(termino)
    return terminos


def resolver_lugar_entrega(observaciones, lugares):
    """Devuelve el lugar inequívoco detectado o ``None``.

    Reglas:
    - si hay un solo lugar activo, se autoselecciona;
    - con varios lugares, se buscan nombre/referencia, localidad o dirección
      dentro de Observaciones;
    - si dos o más destinos coinciden, se considera ambiguo y devuelve None.
    """
    lugares = [l for l in lugares if getattr(l, "activo", True)]
    if not lugares:
        return None
    if len(lugares) == 1:
        return lugares[0]

    texto = normalizar_texto(observaciones)
    if not texto:
        return None

    coincidencias = []
    for lugar in lugares:
        if any(termino in texto for termino in _terminos_lugar(lugar)):
            coincidencias.append(lugar)

    if len(coincidencias) == 1:
        return coincidencias[0]
    return None


def clave_duplicado(cliente_id, fecha, producto, comprobante=""):
    """Construye una clave estable priorizando el comprobante si existe."""
    comprobante = normalizar_texto(comprobante).replace(" ", "")
    base = (str(cliente_id), str(fecha), normalizar_texto(producto))
    if comprobante:
        return base + (comprobante,)
    return base

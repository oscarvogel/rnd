# coding=utf-8
"""Reglas puras de pallets (Issue #66, Epic #58).

Toda la aritmetica vive aca para poder testearse sin base de datos.
La persistencia esta en ``modelos/Pallet.py`` y delega en estas funciones.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation


ESTADO_ARMADO = "ARMADO"


def a_decimal(valor) -> Decimal:
    """Convierte a Decimal tratando None/''/'nan' como cero."""
    if valor is None:
        return Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return Decimal("0")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return Decimal("0")


def prefijo_codigo(fecha=None) -> str:
    """Prefijo diario del codigo de pallet: PLT-AAAAMMDD."""
    if fecha is None:
        fecha = date.today()
    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)
    return "PLT-{}".format(fecha.strftime("%Y%m%d"))


def saldo_disponible(total_linea, ya_asignado) -> Decimal:
    """Saldo nunca negativo de una linea."""
    saldo = a_decimal(total_linea) - a_decimal(ya_asignado)
    return saldo if saldo > 0 else Decimal("0")


def validar_agregado(saldo_cantidad, saldo_kg, saldo_bultos,
                     cantidad, kg, bultos):
    """Valida cantidades a paletizar contra el saldo disponible.

    Devuelve (ok, mensaje). Cantidades None significan 'todo el saldo'.
    """
    cantidad = a_decimal(cantidad) if cantidad is not None else a_decimal(saldo_cantidad)
    kg = a_decimal(kg) if kg is not None else a_decimal(saldo_kg)
    bultos = a_decimal(bultos) if bultos is not None else a_decimal(saldo_bultos)

    if cantidad <= 0 and kg <= 0 and bultos <= 0:
        return False, "Debe indicar una cantidad mayor a cero."
    if cantidad > a_decimal(saldo_cantidad):
        return False, "La cantidad supera el saldo disponible de la línea."
    if kg > a_decimal(saldo_kg):
        return False, "Los KG superan el saldo disponible de la línea."
    if bultos > a_decimal(saldo_bultos):
        return False, "Los bultos superan el saldo disponible de la línea."
    return True, ""


def totales(lineas) -> dict:
    """Suma cantidad/kg/bultos de una lista de dicts u objetos con esos attrs."""
    cantidad = Decimal("0")
    kg = Decimal("0")
    bultos = Decimal("0")
    n = 0
    for linea in lineas:
        if isinstance(linea, dict):
            cantidad += a_decimal(linea.get("cantidad"))
            kg += a_decimal(linea.get("kg"))
            bultos += a_decimal(linea.get("bultos"))
        else:
            cantidad += a_decimal(getattr(linea, "cantidad", 0))
            kg += a_decimal(getattr(linea, "kg", 0))
            bultos += a_decimal(getattr(linea, "bultos", 0))
        n += 1
    return {"lineas": n, "cantidad": cantidad, "kg": kg, "bultos": bultos}


def agrupar_por_cliente_destino(filas) -> list:
    """Agrupa filas (dicts con cliente_id, lugar_entrega_id, ...) sumando.

    No deriva datos: solo agrega lo que ya trae cada fila.
    """
    grupos = {}
    for fila in filas:
        clave = (fila.get("cliente_id"), fila.get("lugar_entrega_id"))
        grupo = grupos.setdefault(clave, {
            "cliente_id": fila.get("cliente_id"),
            "cliente": fila.get("cliente"),
            "lugar_entrega_id": fila.get("lugar_entrega_id"),
            "lugar_entrega": fila.get("lugar_entrega"),
            "cantidad": Decimal("0"),
            "kg": Decimal("0"),
            "bultos": Decimal("0"),
            "lineas": 0,
        })
        grupo["cantidad"] += a_decimal(fila.get("cantidad"))
        grupo["kg"] += a_decimal(fila.get("kg"))
        grupo["bultos"] += a_decimal(fila.get("bultos"))
        grupo["lineas"] += 1
    return sorted(
        grupos.values(),
        key=lambda g: (str(g["cliente"] or ""), str(g["lugar_entrega"] or "")),
    )

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


def formato_kg(valor) -> str:
    """Texto de un peso para mostrar en pantalla.

    Dos decimales como maximo y se omiten cuando el peso es entero:
    ``115.62`` se ve como ``115.62`` pero un pallet vacio tiene que
    mostrarse como ``0`` y no como ``0.00``.
    """
    cantidad = a_decimal(valor)
    if cantidad == cantidad.to_integral_value():
        return "{:d}".format(int(cantidad))
    return "{:.2f}".format(cantidad)


def limite_kg_configurable(valor):
    """Normaliza el limite de KG por pallet configurado.

    Devuelve ``None`` cuando no hay limite cargado, esta vacio o no es
    positivo: en ese caso el KPI muestra solamente el KG actual.
    """
    if valor is None or valor == "":
        return None
    limite = a_decimal(valor)
    return limite if limite > 0 else None


def estado_limite_kg(kg, limite_kg):
    """Estado del peso frente al limite configurado.

    Devuelve ``(texto, excede)`` o ``None`` si todavia no hay limite.
    ``texto`` ya viene listo para mostrar, por ejemplo
    ``"Límite: 100 KG · Exceso 15.62 KG"``.
    """
    limite = limite_kg_configurable(limite_kg)
    if limite is None:
        return None
    peso = a_decimal(kg)
    diferencia = limite - peso
    if diferencia < 0:
        return (
            "Límite: {} KG · Exceso {} KG".format(
                formato_kg(limite), formato_kg(abs(diferencia))
            ),
            True,
        )
    return (
        "Límite: {} KG · Disponible {} KG".format(
            formato_kg(limite), formato_kg(diferencia)
        ),
        False,
    )


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

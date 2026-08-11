# coding=utf-8
"""Logica pura para clasificar y totalizar pedidos de la bandeja operativa."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

ESTADO_PENDIENTE = "pendiente"
ESTADO_OBSERVADO = "observado"
ESTADO_ORGANIZADO = "organizado"


def _decimal(valor):
    try:
        return Decimal(str(valor or 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")


@dataclass(frozen=True)
class PedidoBandeja:
    id: int
    cliente: str
    comprobante: str
    producto: str
    cantidad: object = 0
    kg: object = 0
    bultos: object = 0
    observaciones: str = ""
    ruta_id: int = 0
    ruta: str = ""
    responsable_id: int = 0
    equipo_id: int = 0

    def estado(self, empleado_generico, camion_generico):
        incompleto = not self.ruta_id or not self.cliente or not self.producto
        if incompleto or (self.observaciones or "").strip():
            return ESTADO_OBSERVADO
        if str(self.responsable_id) == str(empleado_generico) or str(self.equipo_id) == str(camion_generico):
            return ESTADO_PENDIENTE
        return ESTADO_ORGANIZADO


def totales_seleccion(pedidos):
    pedidos = list(pedidos)
    return {
        "pedidos": len(pedidos),
        "kg": sum((_decimal(p.kg) for p in pedidos), Decimal("0")),
        "bultos": sum((_decimal(p.bultos) for p in pedidos), Decimal("0")),
    }


def validar_reasignacion(pedidos, ruta_id):
    if not pedidos:
        return False, "Seleccione al menos un pedido"
    if not ruta_id:
        return False, "Seleccione una ruta de reparto"
    ids = [p.id for p in pedidos]
    if len(ids) != len(set(ids)):
        return False, "La selección contiene pedidos duplicados"
    return True, ""

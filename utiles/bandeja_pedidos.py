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
    cliente_id: int = 0
    lugar_entrega: str = ""
    lugar_entrega_id: int = 0
    comprobante: str = ""
    producto: str = ""
    cantidad: object = 0
    kg: object = 0
    bultos: object = 0
    observaciones: str = ""
    ruta_id: int = 0
    ruta: str = ""
    responsable_id: int = 0
    equipo_id: int = 0

    def estado(self, empleado_generico, camion_generico):
        incompleto = (not self.ruta_id or not self.cliente_id or not self.cliente or not self.lugar_entrega_id or not self.producto)
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


def clave_factura(pedido):
    """Identifica una factura dentro de la bandeja sin depender del producto."""
    comprobante = str(getattr(pedido, "comprobante", "") or "").strip()
    cliente = str(getattr(pedido, "cliente", "") or "").strip().casefold()
    if not comprobante:
        return None
    return comprobante, cliente


def expandir_seleccion_por_factura(pedidos, seleccionados):
    """Incluye todas las líneas/productos de las facturas seleccionadas.

    Basta seleccionar una línea de una factura para que la operación se aplique
    a todas sus líneas. Los registros sin comprobante se mantienen sólo si
    fueron seleccionados explícitamente.
    """
    pedidos = list(pedidos or [])
    seleccionados = list(seleccionados or [])
    ids_explicitos = {p.id for p in seleccionados}
    claves = {clave_factura(p) for p in seleccionados}
    claves.discard(None)
    return [
        p for p in pedidos
        if p.id in ids_explicitos or clave_factura(p) in claves
    ]

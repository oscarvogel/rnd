# coding=utf-8
"""Logica pura para clasificar y totalizar pedidos de la bandeja operativa."""

from dataclasses import dataclass
from collections import OrderedDict
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
    factura: str = ""
    remito: str = ""
    cantidad: object = 0
    kg: object = 0
    bultos: object = 0
    observaciones: str = ""
    ruta_id: int = 0
    ruta: str = ""
    responsable_id: int = 0
    equipo_id: int = 0
    documento_id: int = 0

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
    comprobante = str(getattr(pedido, "factura", "") or getattr(pedido, "comprobante", "") or "").strip()
    if not comprobante:
        return None
    return comprobante


def expandir_seleccion_por_factura(pedidos, seleccionados):
    pedidos = list(pedidos or [])
    seleccionados = list(seleccionados or [])
    ids_explicitos = {p.id for p in seleccionados}
    claves = {clave_factura(p) for p in seleccionados}
    claves.discard(None)
    return [p for p in pedidos if p.id in ids_explicitos or clave_factura(p) in claves]


@dataclass(frozen=True)
class FacturaBandeja:
    clave: str
    documento_id: int
    factura: str
    cliente: str
    cliente_id: int
    lugar_entrega: str
    lugar_entrega_id: int
    ruta: str
    ruta_id: int
    remito: str
    productos: int
    cantidad: object
    kg: object
    bultos: object
    observaciones: str
    hoja_ids: tuple
    responsable_ids: tuple
    equipo_ids: tuple

    def estado(self, empleado_generico, camion_generico):
        incompleta = (
            not self.cliente_id
            or not self.cliente
            or not self.lugar_entrega_id
            or not self.ruta_id
            or self.productos <= 0
        )
        if incompleta or (self.observaciones or "").strip():
            return ESTADO_OBSERVADO
        recursos_genericos = any(
            str(x) == str(empleado_generico) for x in self.responsable_ids
        ) or any(
            str(x) == str(camion_generico) for x in self.equipo_ids
        )
        return ESTADO_PENDIENTE if recursos_genericos else ESTADO_ORGANIZADO


def agrupar_pedidos_por_factura(pedidos):
    """Agrupa líneas operativas en una sola fila lógica por factura/documento."""
    grupos = OrderedDict()
    for pedido in list(pedidos or []):
        if pedido.documento_id:
            clave = "D{}".format(pedido.documento_id)
        else:
            clave = "F{}".format(clave_factura(pedido) or "HOJA{}".format(pedido.id))

        grupos.setdefault(clave, []).append(pedido)

    resultado = []
    for clave, lineas in grupos.items():
        primera = lineas[0]
        cliente_ids = {x.cliente_id for x in lineas if x.cliente_id}
        lugares = {x.lugar_entrega_id for x in lineas if x.lugar_entrega_id}
        rutas = {x.ruta_id for x in lineas if x.ruta_id}
        clientes_nombre = {str(x.cliente or "").strip() for x in lineas if str(x.cliente or "").strip()}
        lugares_nombre = {str(x.lugar_entrega or "").strip() for x in lineas if str(x.lugar_entrega or "").strip()}
        rutas_nombre = {str(x.ruta or "").strip() for x in lineas if str(x.ruta or "").strip()}

        resultado.append(
            FacturaBandeja(
                clave=clave,
                documento_id=int(primera.documento_id or 0),
                factura=str(primera.factura or primera.comprobante or ""),
                cliente=(next(iter(clientes_nombre)) if len(clientes_nombre) == 1 else "⚠ Clientes distintos"),
                cliente_id=(next(iter(cliente_ids)) if len(cliente_ids) == 1 else 0),
                lugar_entrega=(next(iter(lugares_nombre)) if len(lugares_nombre) == 1 else ""),
                lugar_entrega_id=(next(iter(lugares)) if len(lugares) == 1 else 0),
                ruta=(next(iter(rutas_nombre)) if len(rutas_nombre) == 1 else "Sin ruta"),
                ruta_id=(next(iter(rutas)) if len(rutas) == 1 else 0),
                remito=str(primera.remito or ""),
                productos=len(lineas),
                cantidad=sum((_decimal(x.cantidad) for x in lineas), Decimal("0")),
                kg=sum((_decimal(x.kg) for x in lineas), Decimal("0")),
                bultos=sum((_decimal(x.bultos) for x in lineas), Decimal("0")),
                observaciones="; ".join(
                    sorted({
                        str(x.observaciones or "").strip()
                        for x in lineas
                        if str(x.observaciones or "").strip()
                    })
                ),
                hoja_ids=tuple(x.id for x in lineas),
                responsable_ids=tuple(x.responsable_id for x in lineas),
                equipo_ids=tuple(x.equipo_id for x in lineas),
            )
        )
    return resultado


def totales_facturas(facturas):
    facturas = list(facturas or [])
    return {
        "facturas": len(facturas),
        "kg": sum((_decimal(f.kg) for f in facturas), Decimal("0")),
        "bultos": sum((_decimal(f.bultos) for f in facturas), Decimal("0")),
    }

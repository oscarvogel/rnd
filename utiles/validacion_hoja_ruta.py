# coding=utf-8
from dataclasses import dataclass
from decimal import Decimal

from modelos.EstadoHojaRuta import EstadoHojaRuta


@dataclass(frozen=True)
class ItemChecklist:
    codigo: str
    descripcion: str
    cumplido: bool
    detalle: str = ""


@dataclass(frozen=True)
class ResultadoValidacion:
    items: tuple
    pedidos: int = 0
    kg: Decimal = Decimal("0")
    bultos: Decimal = Decimal("0")

    @property
    def valida(self):
        return bool(self.items) and all(item.cumplido for item in self.items)

    @property
    def pendientes(self):
        return tuple(item for item in self.items if not item.cumplido)


def _decimal(valor):
    try:
        return Decimal(str(valor or 0))
    except Exception:
        return Decimal("0")


def validar_hoja(registros, fecha, ruta_id, empleado_generico, camion_generico):
    registros = list(registros or [])
    pedidos = len(registros)
    kg = sum((_decimal(r.kg) for r in registros), Decimal("0"))
    bultos = sum((_decimal(r.cantidad_bultos) for r in registros), Decimal("0"))

    tiene_pedidos = pedidos > 0
    tiene_fecha = fecha is not None
    tiene_ruta = bool(ruta_id)

    responsables = {int(getattr(r, "responsable_id", 0) or 0) for r in registros}
    equipos = {int(getattr(r, "equipo_asignado_id", 0) or 0) for r in registros}
    chofer_ok = tiene_pedidos and len(responsables) == 1 and empleado_generico not in responsables and 0 not in responsables
    camion_ok = tiene_pedidos and len(equipos) == 1 and camion_generico not in equipos and 0 not in equipos

    datos_ok = True
    detalle_datos = ""
    for r in registros:
        if not getattr(r, "cliente_id", 0) or not str(getattr(r, "comprobante", "") or "").strip():
            datos_ok = False
            detalle_datos = "Hay pedidos sin cliente o comprobante."
            break
        if _decimal(getattr(r, "cantidad", 0)) <= 0:
            datos_ok = False
            detalle_datos = "Hay pedidos con cantidad inválida."
            break

    items = (
        ItemChecklist("pedidos", "Tiene al menos un pedido válido", tiene_pedidos),
        ItemChecklist("fecha", "Tiene fecha de reparto", tiene_fecha),
        ItemChecklist("ruta", "Tiene ruta / zona", tiene_ruta),
        ItemChecklist("chofer", "Tiene un único chofer asignado", chofer_ok),
        ItemChecklist("camion", "Tiene un único camión asignado", camion_ok),
        ItemChecklist("datos", "No contiene errores operativos bloqueantes", datos_ok and tiene_pedidos, detalle_datos),
    )
    return ResultadoValidacion(items=items, pedidos=pedidos, kg=kg, bultos=bultos)


def puede_transicionar(estado_actual, estado_destino, resultado):
    if estado_actual == EstadoHojaRuta.DESPACHADA:
        return False, "Una hoja despachada no puede retroceder automáticamente."
    if estado_destino == EstadoHojaRuta.LISTA:
        if not resultado.valida:
            faltantes = ", ".join(i.descripcion for i in resultado.pendientes)
            return False, "La hoja está incompleta: {}".format(faltantes)
        return True, ""
    if estado_destino == EstadoHojaRuta.DESPACHADA:
        if estado_actual != EstadoHojaRuta.LISTA:
            return False, "Sólo una hoja en estado LISTA puede marcarse como DESPACHADA."
        if not resultado.valida:
            return False, "La hoja dejó de cumplir los requisitos de validación."
        return True, ""
    return False, "Transición de estado no permitida."

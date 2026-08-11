# coding=utf-8
"""Reglas puras para la asignación guiada de chofer y camión."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ResumenRuta:
    pedidos: int = 0
    kg: Decimal = Decimal("0")
    bultos: Decimal = Decimal("0")
    responsable_id: int = 0
    equipo_id: int = 0
    asignacion_mixta: bool = False

    @property
    def vacia(self):
        return self.pedidos <= 0

    def recursos_completos(self, empleado_generico, camion_generico):
        return (
            not self.vacia
            and not self.asignacion_mixta
            and int(self.responsable_id or 0) not in (0, int(empleado_generico))
            and int(self.equipo_id or 0) not in (0, int(camion_generico))
        )


def construir_resumen(registros):
    registros = list(registros)
    if not registros:
        return ResumenRuta()

    responsables = {int(getattr(r, "responsable_id", 0) or 0) for r in registros}
    equipos = {int(getattr(r, "equipo_asignado_id", 0) or 0) for r in registros}
    return ResumenRuta(
        pedidos=len(registros),
        kg=sum((Decimal(str(getattr(r, "kg", 0) or 0)) for r in registros), Decimal("0")),
        bultos=sum((Decimal(str(getattr(r, "cantidad_bultos", 0) or 0)) for r in registros), Decimal("0")),
        responsable_id=next(iter(responsables)) if len(responsables) == 1 else 0,
        equipo_id=next(iter(equipos)) if len(equipos) == 1 else 0,
        asignacion_mixta=len(responsables) > 1 or len(equipos) > 1,
    )


def validar_asignacion(resumen, responsable_id, equipo_id, empleado_generico, camion_generico):
    if resumen.vacia:
        return False, "La ruta seleccionada no tiene pedidos para asignar"
    if not responsable_id or int(responsable_id) == int(empleado_generico):
        return False, "Debe seleccionar un chofer / responsable válido"
    if not equipo_id or int(equipo_id) == int(camion_generico):
        return False, "Debe seleccionar un camión / equipo válido"
    return True, ""

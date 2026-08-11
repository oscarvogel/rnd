# coding=utf-8
"""Utilidades puras para el flujo guiado de importación de pedidos."""

from dataclasses import dataclass


ACCION_REVISAR = "revisar_pendientes"
ACCION_CONTINUAR = "continuar_reparto"
ACCION_CORREGIR = "corregir_importacion"


@dataclass(frozen=True)
class ResumenImportacion:
    leidos: int = 0
    importados: int = 0
    omitidos: int = 0
    pendientes: int = 0
    errores: int = 0

    @property
    def parcial(self):
        return self.importados > 0 and (self.omitidos > 0 or self.pendientes > 0 or self.errores > 0)

    @property
    def exitosa(self):
        return self.importados > 0 and not (self.omitidos or self.pendientes or self.errores)

    @property
    def fallida(self):
        return self.importados == 0 and self.errores > 0

    @property
    def siguiente_accion(self):
        if self.errores and self.importados == 0:
            return ACCION_CORREGIR
        if self.pendientes or self.omitidos or self.errores:
            return ACCION_REVISAR
        return ACCION_CONTINUAR

    @property
    def titulo(self):
        if self.fallida:
            return "La importación necesita corrección"
        if self.parcial:
            return "Importación completada con pendientes"
        if self.exitosa:
            return "Importación completada"
        return "Archivo preparado para revisar"

    @property
    def detalle(self):
        return (
            "Registros leídos: {0} · Pedidos importados: {1} · "
            "Omitidos: {2} · Pendientes: {3} · Errores: {4}"
        ).format(self.leidos, self.importados, self.omitidos, self.pendientes, self.errores)


def ayuda_proveedor(proveedor_id):
    """Texto breve y operativo según el importador seleccionado."""
    proveedor = str(proveedor_id or "").strip()
    if proveedor == "15":
        return (
            "Tremblay: seleccione el Excel de pedidos o informe de despacho. "
            "RND lo normaliza automáticamente antes de mostrar la vista previa."
        )
    if proveedor:
        return (
            "Seleccione el archivo Excel entregado por este proveedor. "
            "RND usará el mapeo de columnas configurado para ese origen."
        )
    return "Primero seleccione el proveedor/origen para saber qué archivo corresponde importar."

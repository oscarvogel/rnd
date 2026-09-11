# coding=utf-8
"""Utilidades puras para el flujo guiado de importación de pedidos."""

from dataclasses import dataclass
from datetime import date


ACCION_REVISAR = "revisar_pendientes"
ACCION_CONTINUAR = "continuar_reparto"
ACCION_CORREGIR = "corregir_importacion"

_ULTIMA_IMPORTACION_POR_FECHA = {}


@dataclass(frozen=True)
class ResumenImportacion:
    leidos: int = 0
    importados: int = 0
    omitidos: int = 0
    reimportados: int = 0
    pendientes: int = 0
    errores: int = 0

    def __post_init__(self):
        # Mantiene disponible en memoria el último estado operativo del día.
        # Esto permite que el dashboard (#4/#24) lo consulte sin duplicar
        # lógica ni tocar los importadores existentes.
        if any((self.leidos, self.importados, self.omitidos, self.reimportados, self.pendientes, self.errores)):
            _ULTIMA_IMPORTACION_POR_FECHA[date.today()] = self

    @property
    def parcial(self):
        return (self.importados + self.reimportados) > 0 and (self.omitidos > 0 or self.pendientes > 0 or self.errores > 0)

    @property
    def exitosa(self):
        return (self.importados + self.reimportados) > 0 and not (self.omitidos or self.pendientes or self.errores)

    @property
    def fallida(self):
        return (self.importados + self.reimportados) == 0 and self.errores > 0

    @property
    def siguiente_accion(self):
        if self.errores and (self.importados + self.reimportados) == 0:
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
            "Ya existentes: {2} · Omitidos: {3} · Pendientes: {4} · Errores: {5}"
        ).format(
            self.leidos, self.importados, self.reimportados,
            self.omitidos, self.pendientes, self.errores
        )


def registrar_resultado_dia(resumen, fecha=None):
    """Conserva el último resultado del día para el dashboard de esta sesión."""
    clave = fecha or date.today()
    _ULTIMA_IMPORTACION_POR_FECHA[clave] = resumen
    return resumen


def obtener_resultado_dia(fecha=None):
    """Devuelve el último resumen registrado para la fecha solicitada."""
    return _ULTIMA_IMPORTACION_POR_FECHA.get(fecha or date.today())


def limpiar_resultados_dia():
    """Helper para tests y reinicios controlados."""
    _ULTIMA_IMPORTACION_POR_FECHA.clear()


def ayuda_proveedor(metodo_importacion):
    """Texto breve y operativo según el método configurado en el proveedor."""
    metodo = str(metodo_importacion or "").strip().upper()
    if metodo == "TREMBLAY":
        return (
            "Tremblay: seleccione el informe de despacho configurado para este proveedor. "
            "RND validará y normalizará ese formato antes de mostrar la vista previa."
        )
    if metodo == "TIO_PUJIO":
        return (
            "Tío Pujio: seleccione el archivo Control de Pedidos. "
            "RND validará que corresponda a ese formato."
        )
    if metodo == "DETALLE_VENTAS":
        return (
            "Seleccione el archivo Detalle de Ventas configurado para este proveedor. "
            "RND validará su estructura antes de importarlo."
        )
    if metodo == "COLUMNAS":
        return (
            "Seleccione el archivo Excel entregado por este proveedor. "
            "RND usará el mapeo de columnas configurado para ese origen."
        )
    if metodo:
        return "El proveedor tiene configurado el método de importación: {}.".format(metodo)
    return "Primero seleccione el proveedor/origen para saber qué archivo corresponde importar."

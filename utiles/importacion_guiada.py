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
    pendientes: int = 0
    errores: int = 0

    def __post_init__(self):
        # Mantiene disponible en memoria el último estado operativo del día.
        # Esto permite que el dashboard (#4/#24) lo consulte sin duplicar
        # lógica ni tocar los importadores existentes.
        if any((self.leidos, self.importados, self.omitidos, self.pendientes, self.errores)):
            _ULTIMA_IMPORTACION_POR_FECHA[date.today()] = self

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


def ayuda_proveedor(importador):
    """Texto breve y operativo según el método configurado en el proveedor."""
    metodo = str(importador or "").strip().upper()
    if metodo == "TREMBLAY":
        return (
            "Método Tremblay: seleccione el Excel o informe de despacho. "
            "RND lo normaliza automáticamente antes de mostrar la vista previa."
        )
    if metodo == "TIO_PUJIO":
        return "Método Tío Pujio: seleccione el CONTROL DE PEDIDOS recibido del proveedor."
    if metodo == "DETALLE_VENTAS":
        return "Método Detalle de ventas: seleccione el informe por provincia/cliente/producto."
    if metodo == "COLUMNAS":
        return (
            "Método Columnas configuradas: RND usará el mapeo definido para este proveedor."
        )
    if metodo == "AUTO":
        return (
            "Método Automático: RND intentará reconocer el formato del archivo. "
            "Puede fijar un método específico desde Maestros > Proveedores."
        )
    return "Seleccione primero el proveedor/origen para saber qué archivo corresponde importar."

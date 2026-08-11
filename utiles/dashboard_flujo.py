# coding=utf-8
from dataclasses import dataclass


ACCION_IMPORTAR = "importar_pedidos"
ACCION_REVISAR = "revisar_pendientes"
ACCION_ORGANIZAR = "organizar_pedidos"
ACCION_ASIGNAR = "asignar_recursos"
ACCION_VALIDAR = "validar_hojas"
ACCION_DESPACHAR = "despachar_hojas"
ACCION_COMPLETO = "reparto_completo"


@dataclass(frozen=True)
class EstadoFlujoDashboard:
    pedidos: int = 0
    pendientes_importacion: int = 0
    errores_importacion: int = 0
    sin_ruta: int = 0
    incompletos_recursos: int = 0
    en_preparacion_completos: int = 0
    listas: int = 0
    despachadas: int = 0
    ruta_recomendada: int = 0

    @property
    def accion(self):
        if self.pedidos <= 0:
            if self.pendientes_importacion or self.errores_importacion:
                return ACCION_REVISAR
            return ACCION_IMPORTAR
        if self.pendientes_importacion or self.errores_importacion:
            return ACCION_REVISAR
        if self.sin_ruta:
            return ACCION_ORGANIZAR
        if self.incompletos_recursos:
            return ACCION_ASIGNAR
        if self.en_preparacion_completos:
            return ACCION_VALIDAR
        if self.listas:
            return ACCION_DESPACHAR
        if self.despachadas:
            return ACCION_COMPLETO
        return ACCION_ORGANIZAR

    @property
    def titulo_accion(self):
        return {
            ACCION_IMPORTAR: "Importar pedidos",
            ACCION_REVISAR: "Revisar pendientes",
            ACCION_ORGANIZAR: "Organizar pedidos",
            ACCION_ASIGNAR: "Asignar chofer y camión",
            ACCION_VALIDAR: "Validar hojas de ruta",
            ACCION_DESPACHAR: "Imprimir / despachar",
            ACCION_COMPLETO: "Reparto del día completo",
        }[self.accion]

    @property
    def detalle_accion(self):
        return {
            ACCION_IMPORTAR: "Todavía no hay pedidos cargados para el reparto de hoy.",
            ACCION_REVISAR: "La última importación dejó registros que requieren atención.",
            ACCION_ORGANIZAR: "Hay pedidos que todavía deben quedar correctamente organizados por ruta.",
            ACCION_ASIGNAR: "Hay hojas con chofer o camión pendiente.",
            ACCION_VALIDAR: "Los recursos están completos; falta validar las hojas antes del despacho.",
            ACCION_DESPACHAR: "Hay hojas listas para imprimir y marcar como despachadas.",
            ACCION_COMPLETO: "No quedan acciones operativas pendientes para hoy.",
        }[self.accion]

    def pasos(self):
        """Devuelve los cinco pasos con estado: completo, pendiente o atención."""
        importado = self.pedidos > 0
        revisar_ok = not (self.pendientes_importacion or self.errores_importacion)
        organizar_ok = importado and self.sin_ruta == 0
        asignar_ok = organizar_ok and self.incompletos_recursos == 0
        validar_ok = asignar_ok and self.en_preparacion_completos == 0
        return (
            ("1. Importar", "completo" if importado else "pendiente"),
            ("2. Revisar", "completo" if revisar_ok else "atencion"),
            ("3. Organizar", "completo" if organizar_ok else "pendiente"),
            ("4. Asignar recursos", "completo" if asignar_ok else "pendiente"),
            ("5. Validar / despachar", "completo" if validar_ok and self.listas == 0 else "pendiente"),
        )

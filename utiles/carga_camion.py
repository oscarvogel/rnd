# coding=utf-8
"""Reglas puras de validacion de carga del camion (Issue #69, Epic #58).

Sin pallets armados la hoja sigue su flujo legacy: no hay nada que
validar y el despacho no se bloquea por este motivo.
"""

from __future__ import annotations

from utiles.validacion_hoja_ruta import ItemChecklist, ResultadoValidacion


CODIGO_CARGA = "carga"
MAX_FALTANTES_MOSTRADOS = 5


def progreso_carga(pallets) -> tuple:
    """Devuelve (cargados, esperados) desde dicts con clave 'cargado'."""
    pallets = list(pallets or [])
    cargados = sum(1 for p in pallets if _es_cargado(p))
    return cargados, len(pallets)


def _es_cargado(pallet) -> bool:
    if isinstance(pallet, dict):
        return bool(pallet.get("cargado"))
    return bool(getattr(pallet, "cargado", False))


def _codigo(pallet) -> str:
    if isinstance(pallet, dict):
        return str(pallet.get("codigo") or "")
    return str(getattr(pallet, "codigo", "") or "")


def faltantes(pallets) -> list:
    """Codigos de pallets esperados aun no cargados."""
    return [_codigo(p) for p in (pallets or []) if not _es_cargado(p)]


def texto_progreso(pallets) -> str:
    cargados, esperados = progreso_carga(pallets)
    if not esperados:
        return "Sin pallets armados: la carga no requiere validación."
    return "Cargados {}/{} pallets.".format(cargados, esperados)


def mensaje_bloqueo(faltante_codigos) -> str:
    faltante_codigos = [c for c in (faltante_codigos or []) if c]
    if not faltante_codigos:
        return ""
    visibles = ", ".join(faltante_codigos[:MAX_FALTANTES_MOSTRADOS])
    resto = len(faltante_codigos) - len(faltante_codigos[:MAX_FALTANTES_MOSTRADOS])
    if resto > 0:
        visibles += " y {} más".format(resto)
    return (
        "No se puede despachar: faltan pallets por cargar ({}). "
        "Abra 'Validar carga' desde el checklist y marque cada pallet "
        "al subirlo al camión.".format(visibles)
    )


def item_carga(pallets) -> ItemChecklist:
    """Item de checklist para anexar al resultado de validacion."""
    pendientes = faltantes(pallets)
    cargados, esperados = progreso_carga(pallets)
    if not pendientes:
        return ItemChecklist(
            CODIGO_CARGA,
            "Carga del camión validada",
            True,
            "Todos los pallets esperados están cargados ({}/{}).".format(
                cargados, esperados
            ),
        )
    return ItemChecklist(
        CODIGO_CARGA,
        "Carga del camión validada",
        False,
        "Faltan por cargar: {}.".format(", ".join(pendientes)),
    )


def resultado_con_carga(resultado, pallets):
    """Anexa el control de carga al resultado (solo si hay pallets)."""
    pallets = list(pallets or [])
    if not pallets:
        return resultado
    items = tuple(resultado.items) + (item_carga(pallets),)
    return ResultadoValidacion(
        items=items,
        pedidos=resultado.pedidos,
        kg=resultado.kg,
        bultos=resultado.bultos,
    )

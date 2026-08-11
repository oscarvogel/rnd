# coding=utf-8
from collections import defaultdict
from datetime import date

from modelos.Accesos import Acceso
from modelos.EstadoHojaRuta import EstadoHojaRuta
from modelos.HojaRuta import HojaDeRuta
from modelos.ParametrosSistema import ParamSist
from utiles.dashboard_flujo import EstadoFlujoDashboard
from utiles.importacion_guiada import obtener_resultado_dia
from utiles.validacion_hoja_ruta import validar_hoja


PERMISO_HOJA_RUTA = "HojaDeRuta"


def obtener_estado_flujo(usu_id, fecha=None):
    """Construye una foto coherente del reparto del día para el dashboard."""
    fecha = fecha or date.today()
    try:
        if not Acceso.ValidaMenu(usu_id=usu_id, for_valid=PERMISO_HOJA_RUTA):
            return None
    except Exception:
        return None

    resumen_importacion = obtener_resultado_dia(fecha)
    pendientes_importacion = int(getattr(resumen_importacion, "pendientes", 0) or 0)
    errores_importacion = int(getattr(resumen_importacion, "errores", 0) or 0)

    registros = list(HojaDeRuta.select().where(HojaDeRuta.fecha == fecha))
    if not registros:
        return EstadoFlujoDashboard(
            pendientes_importacion=pendientes_importacion,
            errores_importacion=errores_importacion,
        )

    empleado_generico = int(ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 23)
    camion_generico = int(ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 1)

    sin_ruta = sum(1 for r in registros if not int(getattr(r, "ruta_id", 0) or 0))
    por_ruta = defaultdict(list)
    for registro in registros:
        ruta_id = int(getattr(registro, "ruta_id", 0) or 0)
        if ruta_id:
            por_ruta[ruta_id].append(registro)

    estados = {
        int(e.ruta_id): e.estado
        for e in EstadoHojaRuta.select().where(EstadoHojaRuta.fecha == fecha)
    }

    incompletos_recursos = 0
    en_preparacion_completos = 0
    listas = 0
    despachadas = 0

    for ruta_id, pedidos_ruta in por_ruta.items():
        estado = estados.get(ruta_id, EstadoHojaRuta.EN_PREPARACION)
        resultado = validar_hoja(
            pedidos_ruta, fecha, ruta_id, empleado_generico, camion_generico
        )
        if estado == EstadoHojaRuta.DESPACHADA:
            despachadas += 1
        elif estado == EstadoHojaRuta.LISTA:
            listas += 1
        elif resultado.valida:
            en_preparacion_completos += 1
        else:
            codigos = {item.codigo for item in resultado.pendientes}
            if "chofer" in codigos or "camion" in codigos:
                incompletos_recursos += 1

    return EstadoFlujoDashboard(
        pedidos=len(registros),
        pendientes_importacion=pendientes_importacion,
        errores_importacion=errores_importacion,
        sin_ruta=sin_ruta,
        incompletos_recursos=incompletos_recursos,
        en_preparacion_completos=en_preparacion_completos,
        listas=listas,
        despachadas=despachadas,
    )

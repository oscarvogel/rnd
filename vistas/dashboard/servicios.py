# coding=utf-8
"""Servicios de datos del dashboard operativo (issue #4).

Centraliza las consultas que alimentan las tarjetas del dashboard.
Cada servicio:

* Verifica permisos con ``Acceso.ValidaMenu`` antes de ejecutar la
  consulta y retorna ``None`` si el usuario no tiene acceso. Asi
  el bloque permanece oculto y **no se ejecuta query ni se revela
  la cantidad** (requisito explicito de #4).
* Acepta ``fecha`` opcional para que los tests no dependan de la
  fecha real y la operacion pueda fijar un dia especifico.
* Captura excepciones y las retorna como ``ResultadoConsulta``
  con ``estado="error"`` para que la tarjeta pueda mostrar el
  fallback sin romper el dashboard.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from modelos.Accesos import Acceso
from modelos.Equipos import Vencimientos, get_vencimientos_proximos
from modelos.HojaRuta import HojaDeRuta
from modelos.ParametrosSistema import ParamSist


# --- Codigos de permiso usados por el dashboard ---------------------------
# Se mappean a ``for_valid`` de los modulos existentes. Se mantienen
# como constantes para que el equipo los pueda ajustar sin tocar
# la UI.
PERMISO_HOJA_RUTA = "HojaDeRuta"
PERMISO_EQUIPOS = "Equipos"


@dataclass
class ResultadoConsulta:
    """Resultado inmutable de una consulta del dashboard."""

    estado: str  # "ok" | "vacio" | "error" | "sin_permiso"
    cantidad: int = 0
    detalle: str = ""
    fecha: Optional[date] = None

    @property
    def es_visible(self):
        """Si el indicador debe mostrarse al usuario."""
        return self.estado != "sin_permiso"

    @property
    def es_error(self):
        return self.estado == "error"

    @property
    def es_vacio(self):
        return self.estado == "vacio"

    @property
    def es_ok(self):
        return self.estado == "ok" and self.cantidad > 0


def _validar_permiso(usu_id, for_valid):
    """Retorna True si el usuario tiene permiso sobre ``for_valid``."""
    try:
        return Acceso.ValidaMenu(usu_id=usu_id, for_valid=for_valid)
    except Exception:
        # Si la consulta de permiso falla (BD caida, etc.) no
        # mostramos el indicador. La tarjeta no debe romper el
        # dashboard entero.
        return False


def _to_resultado(estado, cantidad=0, detalle="", fecha=None):
    return ResultadoConsulta(
        estado=estado,
        cantidad=cantidad,
        detalle=detalle,
        fecha=fecha,
    )


def hojas_ruta_del_dia(usu_id, fecha=None):
    """Cantidad de hojas de ruta para ``fecha`` (hoy por default).

    Retorna ``estado="sin_permiso"`` si el usuario no tiene acceso
    al modulo de hoja de ruta. Esto evita tanto la consulta como
    la revelacion del conteo.
    """
    fecha = fecha or date.today()
    if not _validar_permiso(usu_id, PERMISO_HOJA_RUTA):
        return _to_resultado("sin_permiso", fecha=fecha)
    try:
        cantidad = (
            HojaDeRuta.select()
            .where(HojaDeRuta.fecha == fecha)
            .count()
        )
    except Exception as exc:
        return _to_resultado("error", detalle=str(exc), fecha=fecha)
    if cantidad == 0:
        return _to_resultado("vacio", fecha=fecha)
    return _to_resultado("ok", cantidad=cantidad, fecha=fecha)


def hojas_ruta_pendientes(usu_id, fecha=None):
    """Registros del dia que aun conservan chofer o camion generico."""
    fecha = fecha or date.today()
    if not _validar_permiso(usu_id, PERMISO_HOJA_RUTA):
        return _to_resultado("sin_permiso", fecha=fecha)
    try:
        camion_generico = int(
            ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 1
        )
        empleado_generico = int(
            ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 23
        )
        cantidad = (
            HojaDeRuta.select()
            .where(
                HojaDeRuta.fecha == fecha,
                (
                    (HojaDeRuta.equipo_asignado == camion_generico)
                    | (HojaDeRuta.responsable == empleado_generico)
                ),
            )
            .count()
        )
    except Exception as exc:
        return _to_resultado("error", detalle=str(exc), fecha=fecha)
    if cantidad == 0:
        return _to_resultado("vacio", fecha=fecha)
    return _to_resultado("ok", cantidad=cantidad, fecha=fecha)


def vencimientos_proximos(usu_id, dias=10, fecha=None):
    """Cantidad de vencimientos de equipos/personal en los proximos dias.

    Usa ``get_vencimientos_proximos`` del modelo de Equipos. Si el
    usuario no tiene permiso sobre Equipos, retorna sin_permiso.
    """
    fecha = fecha or date.today()
    if not _validar_permiso(usu_id, PERMISO_EQUIPOS):
        return _to_resultado("sin_permiso", fecha=fecha)
    try:
        # ``get_vencimientos_proximos`` usa date.today() internamente.
        # Para mantener la fecha coherente con el resto del dashboard
        # la exponemos en el resultado aunque la query no la use.
        cantidad = sum(1 for _ in get_vencimientos_proximos())
    except Exception as exc:
        return _to_resultado("error", detalle=str(exc), fecha=fecha)
    if cantidad == 0:
        return _to_resultado("vacio", fecha=fecha)
    return _to_resultado("ok", cantidad=cantidad, fecha=fecha)


def alertas_vencidas(usu_id, fecha=None):
    """Vencimientos anteriores a hoy que requieren atencion."""
    fecha = fecha or date.today()
    if not _validar_permiso(usu_id, PERMISO_EQUIPOS):
        return _to_resultado("sin_permiso", fecha=fecha)
    try:
        cantidad = (
            Vencimientos.select()
            .where(Vencimientos.fecha_vencimiento < fecha)
            .count()
        )
    except Exception as exc:
        return _to_resultado("error", detalle=str(exc), fecha=fecha)
    if cantidad == 0:
        return _to_resultado("vacio", fecha=fecha)
    return _to_resultado("ok", cantidad=cantidad, fecha=fecha)

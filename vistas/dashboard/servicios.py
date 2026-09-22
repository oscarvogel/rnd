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
from modelos.Clientes import RutaReparto
from modelos.Equipos import Vencimientos, get_vencimientos_proximos
from modelos.EstadoHojaRuta import EstadoHojaRuta
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
    ruta_id: int = 0

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


def _to_resultado(estado, cantidad=0, detalle="", fecha=None, ruta_id=0):
    return ResultadoConsulta(
        estado=estado,
        cantidad=cantidad,
        detalle=detalle,
        fecha=fecha,
        ruta_id=int(ruta_id or 0),
    )


def hojas_ruta_del_dia(usu_id, fecha=None):
    """Resumen de hojas/rutas del día, no cantidad de renglones.

    Una hoja de ruta puede contener muchos pedidos. El dashboard debe contar
    rutas distintas y mostrar su estado operativo para evitar que el usuario
    confunda cantidad de líneas con cantidad de hojas.
    """
    fecha = fecha or date.today()
    if not _validar_permiso(usu_id, PERMISO_HOJA_RUTA):
        return _to_resultado("sin_permiso", fecha=fecha)
    try:
        registros = list(HojaDeRuta.select().where(HojaDeRuta.fecha == fecha))
        if not registros:
            return _to_resultado("vacio", fecha=fecha)

        camion_generico = int(
            ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 1
        )
        empleado_generico = int(
            ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 23
        )

        por_ruta = {}
        for registro in registros:
            ruta_id = int(getattr(registro, "ruta_id", 0) or 0)
            if ruta_id:
                por_ruta.setdefault(ruta_id, []).append(registro)

        if not por_ruta:
            return _to_resultado(
                "vacio",
                detalle="Hay pedidos del día todavía sin organizar en una ruta.",
                fecha=fecha,
            )

        nombres = {
            int(r.id): r.descripcion
            for r in RutaReparto.select().where(RutaReparto.id.in_(list(por_ruta)))
        }
        estados = {
            int(e.ruta_id): e.estado
            for e in EstadoHojaRuta.select().where(EstadoHojaRuta.fecha == fecha)
        }

        lineas = []
        for ruta_id, pedidos in sorted(
            por_ruta.items(), key=lambda item: nombres.get(item[0], str(item[0]))
        ):
            primero = pedidos[0]
            responsable_id = int(getattr(primero, "responsable_id", 0) or 0)
            equipo_id = int(getattr(primero, "equipo_asignado_id", 0) or 0)
            recursos_ok = (
                responsable_id not in (0, empleado_generico)
                and equipo_id not in (0, camion_generico)
            )
            estado = estados.get(ruta_id, EstadoHojaRuta.EN_PREPARACION)
            if not recursos_ok:
                estado_txt = "Pendiente de asignación"
            elif estado == EstadoHojaRuta.DESPACHADA:
                estado_txt = "Despachada"
            elif estado == EstadoHojaRuta.LISTA:
                estado_txt = "Lista para imprimir"
            else:
                estado_txt = "Lista para revisar"

            chofer = "Chofer pendiente"
            camion = "Camión pendiente"
            if recursos_ok:
                try:
                    chofer = primero.responsable.nombre_completo
                except Exception:
                    chofer = "Chofer #{}".format(responsable_id)
                try:
                    camion = str(primero.equipo_asignado)
                except Exception:
                    camion = "Camión #{}".format(equipo_id)

            lineas.append(
                "{} · {} · {} · {}".format(
                    nombres.get(ruta_id, "Ruta #{}".format(ruta_id)),
                    estado_txt,
                    chofer,
                    camion,
                )
            )

        detalle = "\n".join(lineas[:4])
        if len(lineas) > 4:
            detalle += "\n+ {} hoja(s) más".format(len(lineas) - 4)
        unica = next(iter(por_ruta)) if len(por_ruta) == 1 else 0
        return _to_resultado(
            "ok",
            cantidad=len(por_ruta),
            detalle=detalle,
            fecha=fecha,
            ruta_id=unica,
        )
    except Exception as exc:
        return _to_resultado("error", detalle=str(exc), fecha=fecha)


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

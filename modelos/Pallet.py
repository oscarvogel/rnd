# coding=utf-8
"""Pallets de preparacion y control de carga (Issue #66, Epic #58).

Principio de diseno: un pallet NO pertenece a un unico cliente/destino.
Puede contener multiples clientes, lugares de entrega, facturas y
productos, incluyendo cantidades parciales de una linea.

Cada ``PalletDetalle`` referencia la linea logistica real (``HojaDeRuta``)
y su cantidad asignada al pallet. Cliente, destino y producto NO se
duplican: se leen desde la linea. La edicion posterior es compatible:
un detalle puede ajustarse o quitarse mientras el pallet lo permita.
"""

from __future__ import annotations

from datetime import date, datetime

import peewee

from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import ModeloBase, db
from utiles.carga_camion import mensaje_bloqueo
from utiles.etiqueta_pallet import normalizar_codigo
from utiles.pallets import (
    ESTADO_ARMADO,
    a_decimal,
    agrupar_por_cliente_destino,
    prefijo_codigo,
    saldo_disponible,
    totales,
    validar_agregado,
)


ESTADO_CARGADO = "CARGADO"


class Pallet(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    codigo = peewee.CharField(max_length=40, unique=True)
    estado = peewee.CharField(max_length=30, default=ESTADO_ARMADO)
    observaciones = peewee.TextField(null=True)
    creado = peewee.DateField(default=date.today)
    cargado_por = peewee.CharField(max_length=100, default="")
    cargado_en = peewee.DateTimeField(null=True)
    # Contexto operativo de la carga. Se guarda en el pallet para que incluso
    # un pallet vacío pertenezca inequívocamente al reparto que lo creó.
    fecha_reparto = peewee.DateField(null=True)
    ruta_id = peewee.IntegerField(null=True)
    responsable_id = peewee.IntegerField(null=True)
    equipo_id = peewee.IntegerField(null=True)

    class Meta:
        db_table = "pallet"
        indexes = (
            (("codigo",), True),
            (("estado",), False),
            (("fecha_reparto", "ruta_id", "responsable_id", "equipo_id"), False),
        )

    def __str__(self):
        return self.codigo


class PalletDetalle(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    pallet = peewee.ForeignKeyField(
        Pallet,
        backref="detalles",
        on_update="CASCADE",
        on_delete="CASCADE",
    )
    hoja_ruta = peewee.ForeignKeyField(
        HojaDeRuta,
        backref="pallet_detalles",
        on_update="CASCADE",
        on_delete="CASCADE",
    )
    cantidad = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)
    kg = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)
    bultos = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)

    class Meta:
        db_table = "pallet_detalle"
        indexes = (
            (("pallet", "hoja_ruta"), True),
        )


def asegurar_esquema_pallets():
    """Crea solo las tablas nuevas si no existen; no altera tablas legacy."""
    db.create_tables([Pallet, PalletDetalle], safe=True)


def crear_pallet(
    codigo=None,
    observaciones=None,
    fecha=None,
    fecha_reparto=None,
    ruta_id=None,
    responsable_id=None,
    equipo_id=None,
):
    """Crea un pallet con codigo unico y, cuando se conoce, su carga operativa."""
    observaciones = (observaciones or "").strip() or None
    contexto = {
        "fecha_reparto": fecha_reparto,
        "ruta_id": ruta_id,
        "responsable_id": responsable_id,
        "equipo_id": equipo_id,
    }
    if codigo:
        return Pallet.create(
            codigo=normalizar_codigo(codigo),
            observaciones=observaciones,
            **contexto
        )
    fecha_codigo = fecha_reparto or fecha
    prefijo = prefijo_codigo(fecha_codigo)
    secuencia = Pallet.select().where(Pallet.codigo.startswith(prefijo)).count() + 1
    while True:
        candidato = "{}-{:03d}".format(prefijo, secuencia)
        try:
            return Pallet.create(
                codigo=candidato,
                observaciones=observaciones,
                **contexto
            )
        except peewee.IntegrityError:
            secuencia += 1


def pallets_para_carga(fecha_reparto, ruta_id, responsable_id, equipo_id):
    """Devuelve sólo pallets ARMADO pertenecientes al contexto operativo dado."""
    if not (fecha_reparto and ruta_id and responsable_id and equipo_id):
        return []
    return list(
        Pallet.select()
        .where(
            Pallet.estado == ESTADO_ARMADO,
            Pallet.fecha_reparto == fecha_reparto,
            Pallet.ruta_id == int(ruta_id),
            Pallet.responsable_id == int(responsable_id),
            Pallet.equipo_id == int(equipo_id),
        )
        .order_by(Pallet.id)
    )


def _sumas_asignadas(hoja_ids):
    """Suma lo ya paletizado por hoja en UNA query (GROUP BY).

    ``lineas_con_saldo`` se llama en cada refresco de ArmadoPallets con
    todas las hojas del día: hacerlo de a una (get_by_id + SUM por hoja)
    eran 2N roundtrips contra el MySQL remoto por cada artículo movido.
    """
    ids = [int(i) for i in dict.fromkeys(hoja_ids or []) if i]
    ceros = {
        "cantidad": a_decimal(0),
        "kg": a_decimal(0),
        "bultos": a_decimal(0),
    }
    resultado = {i: dict(ceros) for i in ids}
    if not ids:
        return resultado
    consulta = (
        PalletDetalle.select(
            PalletDetalle.hoja_ruta,
            peewee.fn.COALESCE(peewee.fn.SUM(PalletDetalle.cantidad), 0).alias("cantidad"),
            peewee.fn.COALESCE(peewee.fn.SUM(PalletDetalle.kg), 0).alias("kg"),
            peewee.fn.COALESCE(peewee.fn.SUM(PalletDetalle.bultos), 0).alias("bultos"),
        )
        .where(PalletDetalle.hoja_ruta.in_(ids))
        .group_by(PalletDetalle.hoja_ruta)
    )
    for fila in consulta:
        # OJO: usar el id crudo, nunca fila.hoja_ruta (dispararía un SELECT
        # por fila para traer el objeto relacionado).
        resultado[int(fila.hoja_ruta_id)] = {
            "cantidad": a_decimal(fila.cantidad),
            "kg": a_decimal(fila.kg),
            "bultos": a_decimal(fila.bultos),
        }
    return resultado


def _suma_asignada(hoja_ruta_id, excluir_pallet_id=None):
    consulta = PalletDetalle.select(
        peewee.fn.COALESCE(peewee.fn.SUM(PalletDetalle.cantidad), 0).alias("cantidad"),
        peewee.fn.COALESCE(peewee.fn.SUM(PalletDetalle.kg), 0).alias("kg"),
        peewee.fn.COALESCE(peewee.fn.SUM(PalletDetalle.bultos), 0).alias("bultos"),
    ).where(PalletDetalle.hoja_ruta == hoja_ruta_id)
    if excluir_pallet_id is not None:
        consulta = consulta.where(PalletDetalle.pallet != excluir_pallet_id)
    fila = consulta.dicts().first() or {}
    return {
        "cantidad": a_decimal(fila.get("cantidad")),
        "kg": a_decimal(fila.get("kg")),
        "bultos": a_decimal(fila.get("bultos")),
    }


def saldo_linea(hoja_ruta_id):
    """Saldo disponible de una linea descontando lo ya paletizado."""
    hoja = HojaDeRuta.get_by_id(hoja_ruta_id)
    asignado = _suma_asignada(hoja_ruta_id)
    return {
        "cantidad": saldo_disponible(hoja.cantidad, asignado["cantidad"]),
        "kg": saldo_disponible(hoja.kg, asignado["kg"]),
        "bultos": saldo_disponible(hoja.cantidad_bultos, asignado["bultos"]),
    }


def agregar_detalle(pallet, hoja_ruta, cantidad=None, kg=None, bultos=None):
    """Agrega (suma) cantidades de una linea a un pallet."""
    pallet_id = getattr(pallet, "id", pallet)
    hoja_id = getattr(hoja_ruta, "id", hoja_ruta)
    saldo = saldo_linea(hoja_id)
    if cantidad is None:
        cantidad = saldo["cantidad"]
    if kg is None:
        kg = saldo["kg"]
    if bultos is None:
        bultos = saldo["bultos"]
    ok, mensaje = validar_agregado(
        saldo["cantidad"], saldo["kg"], saldo["bultos"], cantidad, kg, bultos
    )
    if not ok:
        raise ValueError(mensaje)
    detalle, _ = PalletDetalle.get_or_create(
        pallet=pallet_id,
        hoja_ruta=hoja_id,
        defaults={"cantidad": 0, "kg": 0, "bultos": 0},
    )
    detalle.cantidad = a_decimal(detalle.cantidad) + a_decimal(cantidad)
    detalle.kg = a_decimal(detalle.kg) + a_decimal(kg)
    detalle.bultos = a_decimal(detalle.bultos) + a_decimal(bultos)
    detalle.save()
    return detalle


def fijar_detalle(pallet, hoja_ruta, cantidad, kg, bultos):
    """Fija (reemplaza) las cantidades de una linea en un pallet."""
    pallet_id = getattr(pallet, "id", pallet)
    hoja_id = getattr(hoja_ruta, "id", hoja_ruta)
    hoja = HojaDeRuta.get_by_id(hoja_id)
    otros = _suma_asignada(hoja_id, excluir_pallet_id=pallet_id)
    disponible_cantidad = saldo_disponible(hoja.cantidad, otros["cantidad"])
    disponible_kg = saldo_disponible(hoja.kg, otros["kg"])
    disponible_bultos = saldo_disponible(hoja.cantidad_bultos, otros["bultos"])
    ok, mensaje = validar_agregado(
        disponible_cantidad, disponible_kg, disponible_bultos,
        cantidad, kg, bultos,
    )
    if not ok:
        raise ValueError(mensaje)
    detalle, _ = PalletDetalle.get_or_create(
        pallet=pallet_id,
        hoja_ruta=hoja_id,
        defaults={"cantidad": 0, "kg": 0, "bultos": 0},
    )
    detalle.cantidad = a_decimal(cantidad)
    detalle.kg = a_decimal(kg)
    detalle.bultos = a_decimal(bultos)
    detalle.save()
    return detalle


def quitar_detalle(pallet, hoja_ruta):
    """Quita una linea de un pallet. Devuelve filas eliminadas (0/1)."""
    return (
        PalletDetalle.delete()
        .where(
            (PalletDetalle.pallet == getattr(pallet, "id", pallet))
            & (PalletDetalle.hoja_ruta == getattr(hoja_ruta, "id", hoja_ruta))
        )
        .execute()
    )


def composicion_pallet(pallet):
    """Lineas del pallet con datos derivados de la HojaDeRuta (sin duplicar).

    Una sola pasada: el JOIN ya trae cada hoja con su detalle, así que los
    nombres de lugar se resuelven con un único IN. (Antes el mismo JOIN se
    ejecutaba dos veces y las hojas se volvían a pedir por separado.)
    """
    from modelos.Clientes import LugarEntrega

    pallet_id = getattr(pallet, "id", pallet)
    detalles = list(
        PalletDetalle.select(PalletDetalle, HojaDeRuta)
        .join(HojaDeRuta)
        .where(PalletDetalle.pallet == pallet_id)
        .order_by(PalletDetalle.id)
    )
    lugar_ids = {
        hoja.lugar_entrega_id
        for detalle in detalles
        for hoja in (detalle.hoja_ruta,)
        if hoja.lugar_entrega_id
    }
    nombres_lugar = {}
    if lugar_ids:
        nombres_lugar = {
            lugar.id: lugar.nombre
            for lugar in LugarEntrega.select().where(
                LugarEntrega.id.in_(lugar_ids)
            )
        }
    filas = []
    for detalle in detalles:
        hoja = detalle.hoja_ruta
        filas.append({
            "detalle_id": detalle.id,
            "hoja_ruta_id": hoja.id,
            "cliente_id": getattr(hoja, "cliente_id", None),
            "cliente": getattr(hoja, "nombre_cliente", "") or "",
            "lugar_entrega_id": getattr(hoja, "lugar_entrega_id", None),
            "lugar_entrega": nombres_lugar.get(hoja.lugar_entrega_id, ""),
            "producto": hoja.producto or "",
            "comprobante": hoja.comprobante or "",
            "cantidad": a_decimal(detalle.cantidad),
            "kg": a_decimal(detalle.kg),
            "bultos": a_decimal(detalle.bultos),
        })
    return filas


def totales_pallet(pallet):
    return totales(composicion_pallet(pallet))


def totales_por_destino(pallet):
    return agrupar_por_cliente_destino(composicion_pallet(pallet))


def lineas_con_saldo(hoja_ids):
    """Saldos de varias líneas con DOS queries en total.

    Trae las hojas en un IN y lo asignado en un GROUP BY, en vez de un
    get_by_id + SUM por hoja. Mismo resultado que llamar a saldo_linea
    por cada una; las inexistentes se omiten igual que antes.
    """
    ids = [int(i) for i in dict.fromkeys(hoja_ids or []) if i]
    if not ids:
        return {}
    asignados = _sumas_asignadas(ids)
    hojas = {h.id: h for h in HojaDeRuta.select().where(HojaDeRuta.id.in_(ids))}
    resultado = {}
    for hoja_id in ids:
        hoja = hojas.get(hoja_id)
        if hoja is None:
            continue
        asignado = asignados[hoja_id]
        resultado[hoja_id] = {
            "cantidad": saldo_disponible(hoja.cantidad, asignado["cantidad"]),
            "kg": saldo_disponible(hoja.kg, asignado["kg"]),
            "bultos": saldo_disponible(hoja.cantidad_bultos, asignado["bultos"]),
        }
    return resultado


def lineas_por_pallet(pallet_ids):
    """Cantidad de líneas por pallet en UNA query (COUNT + GROUP BY).

    Para resúmenes ("Líneas en pallets: N") sin traer la composición
    completa de cada pallet.
    """
    ids = [int(i) for i in dict.fromkeys(pallet_ids or []) if i]
    resultado = {i: 0 for i in ids}
    if not ids:
        return resultado
    consulta = (
        PalletDetalle.select(
            PalletDetalle.pallet,
            peewee.fn.COUNT(PalletDetalle.id).alias("lineas"),
        )
        .where(PalletDetalle.pallet.in_(ids))
        .group_by(PalletDetalle.pallet)
    )
    for fila in consulta:
        # OJO: id crudo, nunca fila.pallet (traería el objeto con un SELECT).
        resultado[int(fila.pallet_id)] = int(fila.lineas)
    return resultado


def buscar_por_codigo(codigo):
    from utiles.etiqueta_pallet import codigo_desde_payload

    codigo = codigo_desde_payload(codigo)
    if not codigo:
        return None
    return Pallet.get_or_none(peewee.fn.UPPER(Pallet.codigo) == codigo)


def pallets_de_hoja(fecha, ruta_id):
    hoja_ids = [
        h.id for h in HojaDeRuta.select(HojaDeRuta.id).where(
            HojaDeRuta.fecha == fecha, HojaDeRuta.ruta == ruta_id
        )
    ]
    if not hoja_ids:
        return []
    pallet_ids = (
        PalletDetalle.select(PalletDetalle.pallet)
        .where(PalletDetalle.hoja_ruta.in_(hoja_ids))
        .distinct()
    )
    return list(Pallet.select().where(Pallet.id.in_(pallet_ids)).order_by(Pallet.codigo))


def marcar_cargado(pallet, usuario=""):
    pallet = Pallet.get_by_id(getattr(pallet, "id", pallet))
    pallet.estado = ESTADO_CARGADO
    pallet.cargado_por = str(usuario or "")
    pallet.cargado_en = datetime.now()
    pallet.save()
    return pallet


def desmarcar_cargado(pallet):
    pallet = Pallet.get_by_id(getattr(pallet, "id", pallet))
    pallet.estado = ESTADO_ARMADO
    pallet.cargado_por = ""
    pallet.cargado_en = None
    pallet.save()
    return pallet


def puede_despachar(fecha, ruta_id):
    hoja_ids = [
        h.id for h in HojaDeRuta.select(HojaDeRuta.id).where(
            HojaDeRuta.fecha == fecha, HojaDeRuta.ruta == ruta_id
        )
    ]
    pallets = pallets_de_hoja(fecha, ruta_id)
    if not pallets:
        return True, [], ""
    saldos = lineas_con_saldo(hoja_ids)
    faltan = sum(1 for saldo in saldos.values() if a_decimal(saldo.get("cantidad")) > 0)
    if faltan:
        return False, [], (
            "No se puede despachar: faltan {} líneas por asignar a "
            "pallets. Complete el armado en 'Armar pallets' antes de "
            "despachar.".format(faltan)
        )
    pendientes = [p.codigo for p in pallets if p.estado != ESTADO_CARGADO]
    if pendientes:
        return False, pendientes, mensaje_bloqueo(pendientes)
    return True, [], ""

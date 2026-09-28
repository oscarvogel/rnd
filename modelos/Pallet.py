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

    class Meta:
        db_table = "pallet"
        indexes = (
            (("codigo",), True),
            (("estado",), False),
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


def crear_pallet(codigo=None, observaciones=None, fecha=None):
    """Crea un pallet con codigo unico legible (PLT-AAAAMMDD-NNN)."""
    observaciones = (observaciones or "").strip() or None
    if codigo:
        return Pallet.create(
            codigo=str(codigo).strip(),
            observaciones=observaciones,
        )
    prefijo = prefijo_codigo(fecha)
    secuencia = Pallet.select().where(Pallet.codigo.startswith(prefijo)).count() + 1
    while True:
        candidato = "{}-{:03d}".format(prefijo, secuencia)
        try:
            return Pallet.create(codigo=candidato, observaciones=observaciones)
        except peewee.IntegrityError:
            secuencia += 1


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
    """Agrega (suma) cantidades de una linea a un pallet.

    Cantidades None significan 'todo el saldo disponible'. Valida que no
    se asigne mas que el saldo. Devuelve el PalletDetalle actualizado.
    """
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
    """Fija (reemplaza) las cantidades de una linea en un pallet.

    Permite edicion posterior: valida contra el total de la linea
    descontando lo asignado en OTROS pallets.
    """
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
    """Lineas del pallet con datos derivados de la HojaDeRuta (sin duplicar)."""
    from modelos.Clientes import LugarEntrega

    pallet_id = getattr(pallet, "id", pallet)
    consulta = (
        PalletDetalle.select(PalletDetalle, HojaDeRuta)
        .join(HojaDeRuta)
        .where(PalletDetalle.pallet == pallet_id)
        .order_by(PalletDetalle.id)
    )
    hojas_ids = [d.hoja_ruta_id for d in consulta.clone()]
    nombres_lugar = {}
    if hojas_ids:
        hojas = list(HojaDeRuta.select().where(HojaDeRuta.id.in_(hojas_ids)))
        lugar_ids = {
            h.lugar_entrega_id for h in hojas if h.lugar_entrega_id
        }
        if lugar_ids:
            nombres_lugar = {
                l.id: l.nombre
                for l in LugarEntrega.select().where(
                    LugarEntrega.id.in_(lugar_ids)
                )
            }
        lugares = {
            h.id: nombres_lugar.get(h.lugar_entrega_id, "")
            for h in hojas
        }
    else:
        lugares = {}
    filas = []
    for detalle in consulta:
        hoja = detalle.hoja_ruta
        filas.append({
            "detalle_id": detalle.id,
            "hoja_ruta_id": hoja.id,
            "cliente_id": getattr(hoja, "cliente_id", None),
            "cliente": getattr(hoja, "nombre_cliente", "") or "",
            "lugar_entrega_id": getattr(hoja, "lugar_entrega_id", None),
            "lugar_entrega": lugares.get(hoja.id, ""),
            "producto": hoja.producto or "",
            "comprobante": hoja.comprobante or "",
            "cantidad": a_decimal(detalle.cantidad),
            "kg": a_decimal(detalle.kg),
            "bultos": a_decimal(detalle.bultos),
        })
    return filas


def totales_pallet(pallet):
    """Totales del pallet y cantidad de lineas."""
    return totales(composicion_pallet(pallet))


def totales_por_destino(pallet):
    """Totales del pallet agrupados por cliente/destino."""
    return agrupar_por_cliente_destino(composicion_pallet(pallet))


def lineas_con_saldo(hoja_ids):
    """Saldo disponible por linea para mostrar 'falta asignar'."""
    resultado = {}
    for hoja_id in hoja_ids:
        try:
            resultado[hoja_id] = saldo_linea(hoja_id)
        except HojaDeRuta.DoesNotExist:
            continue
    return resultado


def pallets_de_hoja(fecha, ruta_id):
    """Pallets con mercaderia en las hojas de una fecha/ruta.

    Son los pallets 'esperados' en el camion para ese despacho.
    """
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
    return list(
        Pallet.select().where(Pallet.id.in_(pallet_ids)).order_by(Pallet.codigo)
    )


def marcar_cargado(pallet, usuario=""):
    """Marca un pallet como cargado registrando quien y cuando."""
    pallet = Pallet.get_by_id(getattr(pallet, "id", pallet))
    pallet.estado = ESTADO_CARGADO
    pallet.cargado_por = str(usuario or "")
    pallet.cargado_en = datetime.now()
    pallet.save()
    return pallet


def desmarcar_cargado(pallet):
    """Devuelve un pallet a ARMADO (permite corregir la validacion)."""
    pallet = Pallet.get_by_id(getattr(pallet, "id", pallet))
    pallet.estado = ESTADO_ARMADO
    pallet.cargado_por = ""
    pallet.cargado_en = None
    pallet.save()
    return pallet


def puede_despachar(fecha, ruta_id):
    """Gate de despacho por carga (Issue #69).

    Sin pallets armados no hay nada que validar: (True, [], "").
    Con pallets, todos deben estar CARGADO.
    """
    pallets = pallets_de_hoja(fecha, ruta_id)
    if not pallets:
        return True, [], ""
    pendientes = [p.codigo for p in pallets if p.estado != ESTADO_CARGADO]
    if pendientes:
        return False, pendientes, mensaje_bloqueo(pendientes)
    return True, [], ""

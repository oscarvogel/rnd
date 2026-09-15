# coding=utf-8
"""Modelo logistico aditivo para documentos/pedidos y sus lineas.

Issue #62: separa el documento original de la hoja de ruta sin romper la
estructura legacy. La relacion se hace mediante una tabla puente para permitir
que una misma linea original participe en mas de una hoja de ruta.
"""
from __future__ import annotations

from datetime import date
import hashlib

import peewee

from modelos.Clientes import Cliente
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import ModeloBase, db
from modelos.Proveedores import Proveedor


def normalizar_numero_documento(valor):
    if valor is None:
        return ""
    texto = str(valor).strip()
    if not texto or texto.lower() == "nan":
        return ""
    if texto.endswith(".0") and texto[:-2].isdigit():
        texto = texto[:-2]
    return texto.replace(".", "")


def clave_documento_importado(proveedor_id, cliente_id, numero_factura, fecha_documento):
    factura = normalizar_numero_documento(numero_factura)
    proveedor = int(proveedor_id or 0)
    cliente = int(cliente_id or 0)
    if factura:
        return "P{}|F{}".format(proveedor, factura)

    if isinstance(fecha_documento, date):
        fecha_txt = fecha_documento.strftime("%Y%m%d")
    else:
        fecha_txt = str(fecha_documento or "")
    return "P{}|C{}|D{}|SIN_FACTURA".format(proveedor, cliente, fecha_txt)


class DocumentoPedido(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    clave_origen = peewee.CharField(max_length=180, unique=True)
    proveedor = peewee.ForeignKeyField(
        Proveedor,
        backref="documentos_pedido",
        null=True,
        on_update="CASCADE",
        on_delete="RESTRICT",
    )
    cliente = peewee.ForeignKeyField(
        Cliente,
        backref="documentos_pedido",
        null=True,
        on_update="CASCADE",
        on_delete="RESTRICT",
    )
    fecha_documento = peewee.DateField(null=True)
    numero_factura = peewee.CharField(max_length=40, default="")
    numero_remito = peewee.CharField(max_length=40, default="")
    comprobante_origen = peewee.CharField(max_length=80, default="")
    origen = peewee.CharField(max_length=80, default="")
    observaciones = peewee.TextField(null=True)

    class Meta:
        db_table = "documento_pedido"
        indexes = (
            (("proveedor", "numero_factura"), False),
            (("cliente", "fecha_documento"), False),
        )


class DocumentoPedidoDetalle(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    documento = peewee.ForeignKeyField(
        DocumentoPedido,
        backref="detalles",
        on_update="CASCADE",
        on_delete="CASCADE",
    )
    linea_origen = peewee.CharField(max_length=80)
    producto = peewee.CharField(max_length=150)
    cantidad_original = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)
    kg_original = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)
    bultos_original = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)
    observaciones = peewee.TextField(null=True)

    class Meta:
        db_table = "documento_pedido_detalle"
        indexes = (
            (("documento", "linea_origen"), True),
        )


class DocumentoPedidoHojaRuta(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    detalle = peewee.ForeignKeyField(
        DocumentoPedidoDetalle,
        backref="asignaciones_hoja_ruta",
        on_update="CASCADE",
        on_delete="CASCADE",
    )
    hoja_ruta = peewee.ForeignKeyField(
        HojaDeRuta,
        backref="documentos_asociados",
        on_update="CASCADE",
        on_delete="CASCADE",
    )
    cantidad_asignada = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)
    kg_asignados = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)
    bultos_asignados = peewee.DecimalField(max_digits=16, decimal_places=2, default=0)

    class Meta:
        db_table = "documento_pedido_hoja_ruta"
        indexes = (
            (("detalle", "hoja_ruta"), True),
        )


def asegurar_esquema_documentos():
    """Crea solo las tablas nuevas si no existen; no altera tablas legacy."""
    db.create_tables(
        [DocumentoPedido, DocumentoPedidoDetalle, DocumentoPedidoHojaRuta],
        safe=True,
    )


def obtener_o_crear_documento(
    proveedor,
    cliente,
    fecha_documento,
    numero_factura="",
    numero_remito="",
    comprobante_origen="",
    origen="",
):
    factura = normalizar_numero_documento(numero_factura)
    remito = normalizar_numero_documento(numero_remito)
    comprobante = normalizar_numero_documento(comprobante_origen or factura)
    clave = clave_documento_importado(
        getattr(proveedor, "id", proveedor),
        getattr(cliente, "id", cliente),
        factura,
        fecha_documento,
    )

    documento, creado = DocumentoPedido.get_or_create(
        clave_origen=clave,
        defaults={
            "proveedor": proveedor or None,
            "cliente": cliente,
            "fecha_documento": fecha_documento,
            "numero_factura": factura,
            "numero_remito": remito,
            "comprobante_origen": comprobante,
            "origen": str(origen or ""),
        },
    )

    # La factura importada no se pisa. El remito si puede completarse despues.
    if not creado and remito and not documento.numero_remito:
        documento.numero_remito = remito
        documento.save()
    return documento, creado


def huella_linea_importada(producto, cantidad=0, kg=0, bultos=0, observaciones=""):
    """Huella estable de contenido para que ordenar la grilla no cambie la identidad."""
    valores = []
    for valor in (producto, cantidad, kg, bultos, observaciones):
        texto = "" if valor is None else str(valor).strip()
        if texto.lower() == "nan":
            texto = ""
        valores.append(texto)
    canonico = "|".join(valores)
    return hashlib.sha1(canonico.encode("utf-8")).hexdigest()[:24]


def identidad_linea_importada(
    producto,
    cantidad=0,
    kg=0,
    bultos=0,
    observaciones="",
    ocurrencia=1,
):
    return "{}:{}".format(
        huella_linea_importada(producto, cantidad, kg, bultos, observaciones),
        int(ocurrencia),
    )


def obtener_o_crear_detalle(
    documento,
    linea_origen,
    producto,
    cantidad=0,
    kg=0,
    bultos=0,
    observaciones="",
):
    return DocumentoPedidoDetalle.get_or_create(
        documento=documento,
        linea_origen=str(linea_origen),
        defaults={
            "producto": str(producto or ""),
            "cantidad_original": cantidad or 0,
            "kg_original": kg or 0,
            "bultos_original": bultos or 0,
            "observaciones": observaciones or "",
        },
    )


def vincular_hoja_ruta(detalle, hoja_ruta):
    """Vincula una salida con una linea original permitiendo futuros parciales."""
    return DocumentoPedidoHojaRuta.get_or_create(
        detalle=detalle,
        hoja_ruta=hoja_ruta,
        defaults={
            "cantidad_asignada": hoja_ruta.cantidad or 0,
            "kg_asignados": hoja_ruta.kg or 0,
            "bultos_asignados": hoja_ruta.cantidad_bultos or 0,
        },
    )


def documento_de_hoja_ruta(hoja_ruta_id):
    return (
        DocumentoPedidoHojaRuta.select(
            DocumentoPedidoHojaRuta,
            DocumentoPedidoDetalle,
            DocumentoPedido,
        )
        .join(DocumentoPedidoDetalle)
        .join(DocumentoPedido)
        .where(DocumentoPedidoHojaRuta.hoja_ruta == hoja_ruta_id)
        .first()
    )




def vinculo_existente_de_detalle(detalle, fecha=None):
    consulta = (
        DocumentoPedidoHojaRuta.select(DocumentoPedidoHojaRuta, HojaDeRuta)
        .join(HojaDeRuta)
        .where(DocumentoPedidoHojaRuta.detalle == getattr(detalle, "id", detalle))
    )
    if fecha is not None:
        consulta = consulta.where(HojaDeRuta.fecha == fecha)
    return consulta.order_by(DocumentoPedidoHojaRuta.id).first()


def buscar_hoja_legacy_sin_vincular(cliente_id, fecha, producto, comprobante):
    """Adopta una fila legacy solo si coincide tambien la factura/comprobante."""
    vinculadas = DocumentoPedidoHojaRuta.select(DocumentoPedidoHojaRuta.hoja_ruta)
    return (
        HojaDeRuta.select()
        .where(
            HojaDeRuta.cliente == cliente_id,
            HojaDeRuta.fecha == fecha,
            HojaDeRuta.producto == producto,
            HojaDeRuta.comprobante == normalizar_numero_documento(comprobante),
            HojaDeRuta.id.not_in(vinculadas),
        )
        .order_by(HojaDeRuta.id)
        .first()
    )

def referencias_por_hojas(hoja_ids):
    """Devuelve factura/remito por hoja de ruta sin ocultar el comprobante legacy."""
    ids = [int(i) for i in hoja_ids if i]
    if not ids:
        return {}
    asegurar_esquema_documentos()
    consulta = (
        DocumentoPedidoHojaRuta.select(
            DocumentoPedidoHojaRuta,
            DocumentoPedidoDetalle,
            DocumentoPedido,
        )
        .join(DocumentoPedidoDetalle)
        .join(DocumentoPedido)
        .where(DocumentoPedidoHojaRuta.hoja_ruta.in_(ids))
    )
    resultado = {}
    for vinculo in consulta:
        documento = vinculo.detalle.documento
        resultado[vinculo.hoja_ruta_id] = {
            "factura": documento.numero_factura or "",
            "remito": documento.numero_remito or "",
            "comprobante_origen": documento.comprobante_origen or "",
            "documento_id": documento.id,
        }
    return resultado


def actualizar_remito_de_hoja(hoja_ruta_id, numero_remito):
    """Permite asociar/modificar el remito sin alterar la factura importada."""
    asegurar_esquema_documentos()
    vinculo = documento_de_hoja_ruta(hoja_ruta_id)
    if not vinculo:
        return False
    documento = vinculo.detalle.documento
    documento.numero_remito = normalizar_numero_documento(numero_remito)
    documento.save()
    return True

def backfill_documentos_legacy():
    """Migra registros legacy de forma explicita y repetible.

    No se ejecuta automaticamente al iniciar la app. Devuelve la cantidad de
    hojas de ruta que quedaron vinculadas.
    """
    asegurar_esquema_documentos()
    vinculadas = 0

    for hoja in HojaDeRuta.select().order_by(HojaDeRuta.id):
        if DocumentoPedidoHojaRuta.select().where(
            DocumentoPedidoHojaRuta.hoja_ruta == hoja.id
        ).exists():
            continue

        factura = normalizar_numero_documento(hoja.comprobante)
        clave = "LEGACY|C{}|D{}|F{}".format(
            hoja.cliente_id,
            hoja.fecha.strftime("%Y%m%d"),
            factura or "SIN_FACTURA",
        )
        documento, _ = DocumentoPedido.get_or_create(
            clave_origen=clave,
            defaults={
                "proveedor": None,
                "cliente": hoja.cliente,
                "fecha_documento": hoja.fecha,
                "numero_factura": factura,
                "numero_remito": "",
                "comprobante_origen": factura,
                "origen": "legacy-hoja-de-ruta",
            },
        )
        detalle, _ = DocumentoPedidoDetalle.get_or_create(
            documento=documento,
            linea_origen=hoja.id,
            defaults={
                "producto": hoja.producto or "",
                "cantidad_original": hoja.cantidad or 0,
                "kg_original": hoja.kg or 0,
                "bultos_original": hoja.cantidad_bultos or 0,
                "observaciones": hoja.observaciones or "",
            },
        )
        _, creado = vincular_hoja_ruta(detalle, hoja)
        if creado:
            vinculadas += 1

    return vinculadas

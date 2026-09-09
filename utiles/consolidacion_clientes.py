# coding=utf-8
"""Consolidacion controlada de clientes duplicados por lugar de entrega."""

from dataclasses import dataclass, field

from modelos.Clientes import Cliente, CodigoClienteProveedor, LugarEntrega
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import db


@dataclass
class ResumenConsolidacion:
    destino_id: int
    origenes: list = field(default_factory=list)
    pedidos: int = 0
    codigos: int = 0
    lugares: int = 0
    advertencias: list = field(default_factory=list)

    def texto(self):
        lineas = [
            "Cliente destino: {}".format(self.destino_id),
            "Clientes a consolidar: {}".format(len(self.origenes)),
            "Pedidos históricos a reasignar: {}".format(self.pedidos),
            "Códigos de proveedor a revisar/mover: {}".format(self.codigos),
            "Lugares de entrega detectados: {}".format(self.lugares),
        ]
        if self.advertencias:
            lineas.append("")
            lineas.append("Advertencias:")
            lineas.extend("- {}".format(x) for x in self.advertencias)
        return "\n".join(lineas)


def _ids_validos(destino_id, origen_ids):
    destino_id = int(destino_id)
    origen_ids = sorted({int(x) for x in origen_ids if int(x) != destino_id})
    if not origen_ids:
        raise ValueError("Debe seleccionar al menos un cliente origen distinto del destino")
    if not Cliente.select().where(Cliente.id == destino_id).exists():
        raise ValueError("El cliente destino no existe")
    existentes = {x.id for x in Cliente.select().where(Cliente.id.in_(origen_ids))}
    faltantes = [x for x in origen_ids if x not in existentes]
    if faltantes:
        raise ValueError("Hay clientes origen inexistentes: {}".format(faltantes))
    return destino_id, origen_ids


def simular_consolidacion(destino_id, origen_ids):
    destino_id, origen_ids = _ids_validos(destino_id, origen_ids)
    destino = Cliente.get_by_id(destino_id)
    origenes = list(Cliente.select().where(Cliente.id.in_(origen_ids)).order_by(Cliente.razon_social))

    resumen = ResumenConsolidacion(
        destino_id=destino_id,
        origenes=[(x.id, x.razon_social) for x in origenes],
        pedidos=HojaDeRuta.select().where(HojaDeRuta.cliente.in_(origen_ids)).count(),
        codigos=CodigoClienteProveedor.select().where(CodigoClienteProveedor.cliente.in_(origen_ids)).count(),
        lugares=LugarEntrega.select().where(LugarEntrega.cliente.in_(origen_ids)).count(),
    )

    cuit_destino = (destino.cuit or "").strip()
    for origen in origenes:
        cuit_origen = (origen.cuit or "").strip()
        if cuit_destino and cuit_origen and cuit_destino != cuit_origen:
            resumen.advertencias.append(
                "CUIT distinto: {} ({}) vs destino {} ({})".format(
                    origen.razon_social, cuit_origen, destino.razon_social, cuit_destino
                )
            )
    return resumen


def _nombre_disponible(destino_id, lugar):
    base = (lugar.nombre or "Lugar de entrega").strip() or "Lugar de entrega"
    existente = LugarEntrega.get_or_none(
        (LugarEntrega.cliente == destino_id) & (LugarEntrega.nombre == base)
    )
    if not existente:
        return base, None
    misma_direccion = (existente.direccion or "").strip() == (lugar.direccion or "").strip()
    misma_localidad = existente.localidad_id == lugar.localidad_id
    if misma_direccion and misma_localidad:
        return base, existente
    sufijo = "{} - origen {}".format(base, lugar.cliente_id)
    n = 2
    candidato = sufijo
    while LugarEntrega.select().where(
        (LugarEntrega.cliente == destino_id) & (LugarEntrega.nombre == candidato)
    ).exists():
        candidato = "{} ({})".format(sufijo, n)
        n += 1
    return candidato, None


def consolidar_clientes(destino_id, origen_ids):
    """Consolida clientes dentro de una transaccion y conserva trazabilidad.

    Los clientes origen quedan inactivos, nunca se borran fisicamente.
    """
    resumen = simular_consolidacion(destino_id, origen_ids)
    destino_id, origen_ids = _ids_validos(destino_id, origen_ids)

    with db.atomic():
        mapa_lugares = {}

        # Primero trasladamos/reutilizamos destinos y construimos un mapa de IDs.
        for lugar in LugarEntrega.select().where(LugarEntrega.cliente.in_(origen_ids)).order_by(LugarEntrega.id):
            nombre, existente = _nombre_disponible(destino_id, lugar)
            if existente:
                mapa_lugares[lugar.id] = existente.id
                continue

            principal_destino = LugarEntrega.select().where(
                (LugarEntrega.cliente == destino_id) &
                (LugarEntrega.principal == True) &
                (LugarEntrega.activo == True)
            ).exists()
            nuevo = LugarEntrega.create(
                cliente=destino_id,
                nombre=nombre,
                direccion=lugar.direccion,
                localidad=lugar.localidad_id,
                ruta_reparto=lugar.ruta_reparto_id,
                principal=bool(lugar.principal and not principal_destino),
                activo=lugar.activo,
                observaciones=lugar.observaciones,
            )
            mapa_lugares[lugar.id] = nuevo.id

        # Garantizamos que cada origen tenga al menos un destino utilizable si posee datos legacy.
        for cliente in Cliente.select().where(Cliente.id.in_(origen_ids)):
            lugares_origen = list(LugarEntrega.select().where(LugarEntrega.cliente == cliente.id))
            if not lugares_origen and (cliente.direccion or cliente.localidad_id or cliente.ruta_reparto_id):
                nombre = "Principal"
                if cliente.localidad_id:
                    try:
                        nombre = cliente.localidad.descripcion
                    except Exception:
                        pass
                temporal = LugarEntrega.create(
                    cliente=destino_id,
                    nombre=_nombre_legacy_disponible(destino_id, nombre, cliente.id),
                    direccion=cliente.direccion,
                    localidad=cliente.localidad_id,
                    ruta_reparto=cliente.ruta_reparto_id,
                    principal=not LugarEntrega.select().where(
                        (LugarEntrega.cliente == destino_id) & (LugarEntrega.principal == True)
                    ).exists(),
                    activo=True,
                )
                mapa_lugares["legacy:{}".format(cliente.id)] = temporal.id

        # Pedidos: primero preservamos el destino historico y luego cambiamos cliente.
        for pedido in HojaDeRuta.select().where(HojaDeRuta.cliente.in_(origen_ids)):
            origen_id = pedido.cliente_id
            if pedido.lugar_entrega_id and pedido.lugar_entrega_id in mapa_lugares:
                pedido.lugar_entrega = mapa_lugares[pedido.lugar_entrega_id]
            elif not pedido.lugar_entrega_id:
                candidatos = list(
                    LugarEntrega.select()
                    .where(LugarEntrega.cliente == origen_id)
                    .order_by(LugarEntrega.principal.desc(), LugarEntrega.id)
                )
                if candidatos and candidatos[0].id in mapa_lugares:
                    pedido.lugar_entrega = mapa_lugares[candidatos[0].id]
                else:
                    legacy = mapa_lugares.get("legacy:{}".format(origen_id))
                    if legacy:
                        pedido.lugar_entrega = legacy
            pedido.cliente = destino_id
            pedido.save()

        # Codigos: deduplicamos solo coincidencias exactas proveedor+codigo.
        for codigo in list(CodigoClienteProveedor.select().where(CodigoClienteProveedor.cliente.in_(origen_ids))):
            duplicado = CodigoClienteProveedor.get_or_none(
                (CodigoClienteProveedor.cliente == destino_id) &
                (CodigoClienteProveedor.proveedor == codigo.proveedor_id) &
                (CodigoClienteProveedor.codigo == codigo.codigo)
            )
            if duplicado:
                codigo.delete_instance()
            else:
                codigo.cliente = destino_id
                codigo.save()

        # Los lugares origen originales quedan eliminables luego de mover los pedidos.
        LugarEntrega.delete().where(LugarEntrega.cliente.in_(origen_ids)).execute()

        # No borramos clientes: quedan inactivos para auditoria y posible recuperacion manual.
        Cliente.update(activo=False).where(Cliente.id.in_(origen_ids)).execute()

        # Si no quedo principal activo, promovemos el primero.
        if not LugarEntrega.select().where(
            (LugarEntrega.cliente == destino_id) &
            (LugarEntrega.principal == True) &
            (LugarEntrega.activo == True)
        ).exists():
            primero = LugarEntrega.get_or_none(
                (LugarEntrega.cliente == destino_id) & (LugarEntrega.activo == True)
            )
            if primero:
                primero.principal = True
                primero.save()

    return resumen


def _nombre_legacy_disponible(destino_id, nombre, origen_id):
    base = (nombre or "Principal").strip() or "Principal"
    if not LugarEntrega.select().where(
        (LugarEntrega.cliente == destino_id) & (LugarEntrega.nombre == base)
    ).exists():
        return base
    candidato = "{} - origen {}".format(base, origen_id)
    n = 2
    while LugarEntrega.select().where(
        (LugarEntrega.cliente == destino_id) & (LugarEntrega.nombre == candidato)
    ).exists():
        candidato = "{} - origen {} ({})".format(base, origen_id, n)
        n += 1
    return candidato

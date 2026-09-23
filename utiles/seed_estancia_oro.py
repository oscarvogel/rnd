# coding=utf-8
"""Seed idempotente para probar importaciones de La Estancia de Oro.

Los clientes/codigos/domicilios/localidades corresponden al PDF operativo
"Estancia de oro 09-09-26.pdf" usado para validar el importador por IA.

Las rutas CENTRO/NORTE son una decision exclusiva del DEMO para que los
pedidos queden listos para recorrer el flujo operativo; no provienen del PDF.
"""
from __future__ import annotations


PROVEEDOR_ESTANCIA_ORO = {
    "razon_social": "LA ESTANCIA DE ORO S.A.",
    "cuit": "30-71573241-2",
    "direccion": "Zona rural - Col. Belgrano (2257) - Santa Fe",
    "telefono": "(03404) 496229 / 15-606738",
    "contacto": "Administracion",
    "metodo_importacion": "COLUMNAS",
}

CLIENTES_ESTANCIA_ORO = (
    {
        "codigo": "1956",
        "razon_social": "MARTINEZ CARLA CHAVELY",
        "cuit": "27-36474601-1",
        "direccion": "VELEZ SARSFIELD 0",
        "localidad": "Garupa",
        "ruta": "CENTRO",
    },
    {
        "codigo": "1941",
        "razon_social": "CEFERINO RODRIGUEZ SUPERMERCADOS SRL",
        "cuit": "30-71081635-9",
        "direccion": "RN 14 KM1260",
        "localidad": "San Vicente",
        "ruta": "NORTE",
    },
    {
        "codigo": "1994",
        "razon_social": "COOP FRIGORIFICA LEANDRO N ALEM LTDA",
        "cuit": "30-63753015-8",
        "direccion": "A DEL VALLE 656",
        "localidad": "Aristobulo del Valle",
        "ruta": "CENTRO",
    },
    {
        "codigo": "1909",
        "razon_social": "MIMEN SRL",
        "cuit": "33-69815650-9",
        "direccion": "1 DE MAYO N°57",
        "localidad": "Puerto Iguazu",
        "ruta": "NORTE",
    },
    {
        "codigo": "2387",
        "razon_social": "ROSA RODRIGO RAFAELA",
        "cuit": "20-39527190-4",
        "direccion": "TUPAC AMARU 1304",
        "localidad": "San Vicente",
        "ruta": "NORTE",
    },
    {
        "codigo": "2373",
        "razon_social": "BRITOS ROCIO ELIANE ALUMINE",
        "cuit": "27-33147412-1",
        "direccion": "LAS HERAS 0",
        "localidad": "Puerto Libertad",
        "ruta": "NORTE",
    },
    {
        "codigo": "1945",
        "razon_social": "MARQUEZ MAXIMILIANO LEANDRO",
        "cuit": "20-39228964-0",
        "direccion": "DR DARIO S/N",
        "localidad": "Montecarlo",
        "ruta": "NORTE",
    },
    {
        "codigo": "1944",
        "razon_social": "MULLER DENIS ROBERTO",
        "cuit": "20-41302481-2",
        "direccion": "ALEM 299",
        "localidad": "San Vicente",
        "ruta": "NORTE",
    },
)

MAPEO_COLUMNAS_NORMALIZADAS = (
    ("Cliente", "codigo_cliente"),
    ("Nombre_Cliente", "detalle_cliente"),
    ("Comprobante", "comprobante"),
    ("Producto", "producto"),
    ("Cantidad", "cantidad"),
    ("KG", "kilos"),
    ("Bultos", "bultos"),
    ("Observaciones", "observaciones"),
)


def seed_estancia_oro() -> dict:
    """Crea/actualiza proveedor, clientes, codigos y lugares de entrega.

    Es seguro ejecutarlo varias veces. Devuelve un resumen para scripts/tests.
    """
    from modelos.ModeloBase import db
    from modelos.Proveedores import Proveedor, ProcesoLista
    from modelos.Clientes import (
        Cliente,
        CodigoClienteProveedor,
        Localidades,
        LugarEntrega,
        RutaReparto,
    )

    if db.is_closed():
        db.connect(reuse_if_open=True)

    proveedor, _ = Proveedor.get_or_create(
        razon_social=PROVEEDOR_ESTANCIA_ORO["razon_social"],
        defaults={
            "cuit": PROVEEDOR_ESTANCIA_ORO["cuit"],
            "direccion": PROVEEDOR_ESTANCIA_ORO["direccion"],
            "telefono": PROVEEDOR_ESTANCIA_ORO["telefono"],
            "contacto": PROVEEDOR_ESTANCIA_ORO["contacto"],
            "activo": True,
            "observaciones": (
                "Proveedor demo para validar importacion PDF/imagen con IA"
            ),
            "metodo_importacion": PROVEEDOR_ESTANCIA_ORO["metodo_importacion"],
        },
    )
    proveedor.cuit = PROVEEDOR_ESTANCIA_ORO["cuit"]
    proveedor.direccion = PROVEEDOR_ESTANCIA_ORO["direccion"]
    proveedor.telefono = PROVEEDOR_ESTANCIA_ORO["telefono"]
    proveedor.contacto = PROVEEDOR_ESTANCIA_ORO["contacto"]
    proveedor.activo = True
    proveedor.observaciones = (
        "Proveedor demo para validar importacion PDF/imagen con IA"
    )
    proveedor.metodo_importacion = PROVEEDOR_ESTANCIA_ORO["metodo_importacion"]
    proveedor.save()

    rutas = {}
    for nombre in ("CENTRO", "NORTE"):
        ruta, _ = RutaReparto.get_or_create(
            descripcion=nombre,
            defaults={"activo": True},
        )
        if not ruta.activo:
            ruta.activo = True
            ruta.save()
        rutas[nombre] = ruta

    clientes_creados = []
    codigos = []

    for dato in CLIENTES_ESTANCIA_ORO:
        localidad, _ = Localidades.get_or_create(
            descripcion=dato["localidad"],
            defaults={"provincia": "Misiones"},
        )
        if localidad.provincia != "Misiones":
            localidad.provincia = "Misiones"
            localidad.save()

        cliente = Cliente.get_or_none(
            Cliente.razon_social == dato["razon_social"]
        )
        if cliente is None and dato["cuit"]:
            cliente = Cliente.get_or_none(Cliente.cuit == dato["cuit"])
        if cliente is None:
            cliente = Cliente.create(
                razon_social=dato["razon_social"],
                cuit=dato["cuit"],
                direccion=dato["direccion"],
                telefono=None,
                contacto=None,
                activo=True,
                observaciones="Cliente seed La Estancia de Oro",
                localidad=localidad,
                ruta_reparto=rutas[dato["ruta"]],
            )
        else:
            cliente.razon_social = dato["razon_social"]
            cliente.cuit = dato["cuit"]
            cliente.direccion = dato["direccion"]
            cliente.activo = True
            cliente.observaciones = "Cliente seed La Estancia de Oro"
            cliente.localidad = localidad
            cliente.ruta_reparto = rutas[dato["ruta"]]
            cliente.save()

        lugar, _ = LugarEntrega.get_or_create(
            cliente=cliente,
            nombre=dato["localidad"],
            defaults={
                "direccion": dato["direccion"],
                "localidad": localidad,
                "ruta_reparto": rutas[dato["ruta"]],
                "principal": True,
                "activo": True,
                "observaciones": "Destino seed La Estancia de Oro",
            },
        )
        lugar.direccion = dato["direccion"]
        lugar.localidad = localidad
        lugar.ruta_reparto = rutas[dato["ruta"]]
        lugar.principal = True
        lugar.activo = True
        lugar.observaciones = "Destino seed La Estancia de Oro"
        lugar.save()

        relacion, _ = CodigoClienteProveedor.get_or_create(
            codigo=dato["codigo"],
            proveedor=proveedor,
            defaults={"cliente": cliente},
        )
        if relacion.cliente_id != cliente.id:
            relacion.cliente = cliente
            relacion.save()

        clientes_creados.append(cliente)
        codigos.append(relacion)

    for codigo, columna in MAPEO_COLUMNAS_NORMALIZADAS:
        proceso, _ = ProcesoLista.get_or_create(
            proveedor=proveedor,
            codigo=codigo,
            defaults={"columna": columna},
        )
        if proceso.columna != columna:
            proceso.columna = columna
            proceso.save()

    return {
        "proveedor_id": proveedor.id,
        "proveedor": proveedor.razon_social,
        "clientes": len(clientes_creados),
        "codigos": len(codigos),
        "localidades": len({dato["localidad"] for dato in CLIENTES_ESTANCIA_ORO}),
    }

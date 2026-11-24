# coding=utf-8
"""Seed idempotente para probar la importacion de los remitos de Noalsa.

Los datos del cliente corresponden al PDF escaneado "noalsa_separado.pdf"
(cuatro remitos, un comprobante por pagina) que se usa para validar el lector
generico de PDF/imagen con IA. El PDF no se versiona: se copia a
demo_importaciones como 07_proveedor_noalsa.pdf.

Las rutas CENTRO/NORTE son una decision exclusiva del DEMO para que los
pedidos queden listos para recorrer el flujo operativo; no provienen del PDF.
"""
from __future__ import annotations


PROVEEDOR_NOALSA = {
    "razon_social": "Noalsa",
    "cuit": "30-64806084-6",
    "direccion": "Ruta Prov. N. 2 (X5900) Villa Maria - Cordoba",
    "telefono": "(0353) 4531901",
    "contacto": "Administracion",
    "metodo_importacion": "COLUMNAS",
}

# "codigo" es el numero de cliente que Noalsa imprime en el remito
# (Sr(es): 000564). El lector por IA puede devolver ese codigo, el CUIT o el
# nombre del cliente; se registran todos como codigos del proveedor para que
# la vista previa resuelva el cliente sin intervencion manual.
CLIENTES_NOALSA = (
    {
        "codigo": "000564",
        "codigos": (
            "000564",
            "564",
            "30708054840",
            "30-70805484-0",
            "NOMBRE:NEGIAR S.R.L.",
            "NOMBRE:NEGIAR SRL",
        ),
        "codigo_cuit": "30708054840",
        "razon_social": "NEGIAR S.R.L.",
        "cuit": "30-70805484-0",
        "direccion": "CALLE 61 N. 3706",
        "localidad": "Posadas",
        "ruta": "CENTRO",
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


def seed_noalsa() -> dict:
    """Crea/actualiza proveedor, cliente, codigos y lugar de entrega.

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
        razon_social=PROVEEDOR_NOALSA["razon_social"],
        defaults={
            "cuit": PROVEEDOR_NOALSA["cuit"],
            "direccion": PROVEEDOR_NOALSA["direccion"],
            "telefono": PROVEEDOR_NOALSA["telefono"],
            "contacto": PROVEEDOR_NOALSA["contacto"],
            "activo": True,
            "observaciones": (
                "Proveedor demo para importar remitos escaneados de Noalsa"
            ),
            "metodo_importacion": PROVEEDOR_NOALSA["metodo_importacion"],
        },
    )
    proveedor.cuit = PROVEEDOR_NOALSA["cuit"]
    proveedor.direccion = PROVEEDOR_NOALSA["direccion"]
    proveedor.telefono = PROVEEDOR_NOALSA["telefono"]
    proveedor.contacto = PROVEEDOR_NOALSA["contacto"]
    proveedor.activo = True
    proveedor.observaciones = (
        "Proveedor demo para importar remitos escaneados de Noalsa"
    )
    proveedor.metodo_importacion = PROVEEDOR_NOALSA["metodo_importacion"]
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

    for dato in CLIENTES_NOALSA:
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
                observaciones="Cliente seed Noalsa",
                localidad=localidad,
                ruta_reparto=rutas[dato["ruta"]],
            )
        else:
            cliente.razon_social = dato["razon_social"]
            cliente.cuit = dato["cuit"]
            cliente.direccion = dato["direccion"]
            cliente.activo = True
            cliente.observaciones = "Cliente seed Noalsa"
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
                "observaciones": "Destino seed Noalsa",
            },
        )
        lugar.direccion = dato["direccion"]
        lugar.localidad = localidad
        lugar.ruta_reparto = rutas[dato["ruta"]]
        lugar.principal = True
        lugar.activo = True
        lugar.observaciones = "Destino seed Noalsa"
        lugar.save()

        for codigo in dato["codigos"]:
            relacion, _ = CodigoClienteProveedor.get_or_create(
                codigo=codigo,
                proveedor=proveedor,
                defaults={"cliente": cliente},
            )
            if relacion.cliente_id != cliente.id:
                relacion.cliente = cliente
                relacion.save()
            codigos.append(relacion)

        clientes_creados.append(cliente)

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
        "localidades": len({dato["localidad"] for dato in CLIENTES_NOALSA}),
    }

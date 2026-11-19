# coding=utf-8
"""Seed idempotente para probar la importacion de Tacural (PDF escaneado).

Los clientes, codigos y domicilios corresponden al PDF escaneado de Tacural
("assets/proveedor_tacural_demo.pdf") usado para validar el importador de
facturas escaneadas.

Las rutas CENTRO/NORTE son una decision exclusiva del DEMO para que los pedidos
queden listos para recorrer el flujo operativo; no provienen del PDF.
"""
from __future__ import annotations


PROVEEDOR_TACURAL = {
    "razon_social": "CHACINADOS TACURAL SRL",
    "cuit": "30-58743818-2",
    "direccion": "Chaco 6349 - Santa Fe",
    "telefono": "0342-4891307",
    "contacto": "Administracion",
    "metodo_importacion": "TACURAL",
}

# "codigo" es el numero de cliente que imprime Tacural en la factura.
# "codigo_cuit" es el CUIT: el importador lo usa para resolver el cliente.
CLIENTES_TACURAL = (
    {
        "codigo": "5808",
        "codigo_cuit": "27-20144842-0",
        "razon_social": "LOZANO MARIELA GUADALUPE",
        "cuit": "27-20144842-0",
        "direccion": "RUTA PROVINCIAL 213 8026 Dp",
        "localidad": "Posadas",
        "ruta": "CENTRO",
    },
    {
        "codigo": "5997",
        "codigo_cuit": "20-16442991-2",
        "razon_social": "BENITEZ OMAR ANIBAL",
        "cuit": "20-16442991-2",
        "direccion": "RUTA 12 KM8.5 ESQ. GUARANI",
        "localidad": "Garupa",
        "ruta": "CENTRO",
    },
    {
        "codigo": "9258",
        "codigo_cuit": "27-37116773-6",
        "razon_social": "VARGAS MARIA JOSE",
        "cuit": "27-37116773-6",
        "direccion": "PERU 701",
        "localidad": "Obera",
        "ruta": "NORTE",
    },
    {
        "codigo": "9098",
        "codigo_cuit": "33-70990435-9",
        "razon_social": "HIPERMERCADO DEL POLLO S.R.L.",
        "cuit": "33-70990435-9",
        "direccion": "AVDA LAVALLE 2720",
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


def seed_tacural() -> dict:
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
        razon_social=PROVEEDOR_TACURAL["razon_social"],
        defaults={
            "cuit": PROVEEDOR_TACURAL["cuit"],
            "direccion": PROVEEDOR_TACURAL["direccion"],
            "telefono": PROVEEDOR_TACURAL["telefono"],
            "contacto": PROVEEDOR_TACURAL["contacto"],
            "activo": True,
            "observaciones": (
                "Proveedor demo para validar importacion de facturas escaneadas"
            ),
            "metodo_importacion": PROVEEDOR_TACURAL["metodo_importacion"],
        },
    )
    proveedor.cuit = PROVEEDOR_TACURAL["cuit"]
    proveedor.direccion = PROVEEDOR_TACURAL["direccion"]
    proveedor.telefono = PROVEEDOR_TACURAL["telefono"]
    proveedor.contacto = PROVEEDOR_TACURAL["contacto"]
    proveedor.activo = True
    proveedor.observaciones = (
        "Proveedor demo para validar importacion de facturas escaneadas"
    )
    proveedor.metodo_importacion = PROVEEDOR_TACURAL["metodo_importacion"]
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

    for dato in CLIENTES_TACURAL:
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
                observaciones="Cliente seed Tacural",
                localidad=localidad,
                ruta_reparto=rutas[dato["ruta"]],
            )
        else:
            cliente.razon_social = dato["razon_social"]
            cliente.cuit = dato["cuit"]
            cliente.direccion = dato["direccion"]
            cliente.activo = True
            cliente.observaciones = "Cliente seed Tacural"
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
                "observaciones": "Destino seed Tacural",
            },
        )
        lugar.direccion = dato["direccion"]
        lugar.localidad = localidad
        lugar.ruta_reparto = rutas[dato["ruta"]]
        lugar.principal = True
        lugar.activo = True
        lugar.observaciones = "Destino seed Tacural"
        lugar.save()

        # El importador manda el CUIT del comprobante; el codigo de Tacural
        # sirve de respaldo para los comprobantes que no traen CUIT.
        for codigo in (dato["codigo_cuit"], dato["codigo"]):
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
        "localidades": len({dato["localidad"] for dato in CLIENTES_TACURAL}),
    }

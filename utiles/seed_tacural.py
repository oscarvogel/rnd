# coding=utf-8
"""Seed idempotente para probar la importacion de Tacural (PDF escaneado).

Los clientes, codigos y domicilios son de DEMO y corresponden al PDF de muestra
que genera `utiles.generador_pdf_tacural` (misma estructura que el comprobante
real, con una pagina escaneada de lado).

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
# Los datos son de DEMO: el PDF de muestra se dibuja con estos mismos
# clientes, asi que no se versiona ningun dato de clientes reales.
CLIENTES_TACURAL = (
    {
        "codigo": "5808",
        "codigo_cuit": "30700000111",
        "razon_social": "SUPERMERCADO LOS DOS S.R.L.",
        "cuit": "30-70000011-1",
        "direccion": "AV. CENTRAL 1234",
        "localidad": "Posadas",
        "ruta": "CENTRO",
    },
    {
        "codigo": "5997",
        "codigo_cuit": "30700000122",
        "razon_social": "COMERCIO EL ORIENTE",
        "cuit": "30-70000012-2",
        "direccion": "RUTA 12 KM 8.5 ESQ. GUARANI",
        "localidad": "Garupa",
        "ruta": "CENTRO",
    },
    {
        "codigo": "9258",
        "codigo_cuit": "30700000133",
        "razon_social": "ALMACEN CENTRAL",
        "cuit": "30-70000013-3",
        "direccion": "PERU 701",
        "localidad": "Obera",
        "ruta": "NORTE",
    },
    {
        "codigo": "9098",
        "codigo_cuit": "30700000144",
        "razon_social": "HIPERMERCADO DEL NORTE S.R.L.",
        "cuit": "30-70000014-4",
        "direccion": "AVDA LAVALLE 2720",
        "localidad": "Posadas",
        "ruta": "CENTRO",
    },
)


def _factura(numero, cliente, codigo_cliente, direccion, localidad, cp, telefono,
             cajas, pedido, total_kilos, items, girada=False):
    """Arma una factura de muestra a partir de los datos del cliente demo."""
    importance = {}
    for item in items:
        item = dict(item)
        item["importe"] = round(item["kg"] * item["punit"], 2)
        importance.setdefault("items", []).append(item)
    return {
        "numero": numero,
        "fecha": "18/11/2026",
        "razon_social": cliente["razon_social"],
        "codigo_cliente": codigo_cliente,
        "direccion": direccion,
        "localidad": localidad.upper(),
        "provincia": "Misiones",
        "cp": cp,
        "telefono": telefono,
        "cuit": cliente["cuit"],
        "cajas": cajas,
        "pedido": pedido,
        "total_kilos": total_kilos,
        "cae": "8646326778{:04d}".format(pedido),
        "vto_cae": "28/11/2026",
        "girada": girada,
        "items": importance["items"],
    }


# Las cuatro facturas del PDF de muestra. Reproducen los casos que hacen
# trabajar al importador: lineas con unidades y sin unidades, y una pagina
# escaneada de lado.
FACTURAS_MUESTRA = (
    _factura(
        "A00011-00420901", CLIENTES_TACURAL[0], "5808", "AV. CENTRAL 1234",
        "Posadas", "3300", "03764-400011", 2, 1, 53.60,
        (
            {"codigo": 10110, "descripcion": "JAMON COCIDO ESPE 3", "unid": 3,
             "kg": 15.60, "punit": 8413.88, "bonif": 10, "iva": 21},
            {"codigo": 10314, "descripcion": "SALAME MILAN SIN", "unid": 2,
             "kg": 4.60, "punit": 10509.92, "bonif": 10, "iva": 21},
            {"codigo": 10200, "descripcion": "MORTADELA", "unid": 1,
             "kg": 3.80, "punit": 7147.94, "bonif": 10, "iva": 21},
            {"codigo": 10421, "descripcion": "SALCHI PARRILLER", "unid": 1,
             "kg": 1.60, "punit": 8066.12, "bonif": 10, "iva": 21},
            {"codigo": 10132, "descripcion": "JAMON COCIDO PAMP", "unid": 3,
             "kg": 15.00, "punit": 4165.29, "bonif": 10, "iva": 21},
            {"codigo": 10202, "descripcion": "MORTADELA PAMPITA", "unid": 1,
             "kg": 3.00, "punit": 3123.96, "bonif": 10, "iva": 21},
            {"codigo": 10130, "descripcion": "FIAMBRE COCIDO PA", "unid": 2,
             "kg": 10.00, "punit": 2759.51, "bonif": 10, "iva": 21},
        ),
    ),
    _factura(
        "A00011-00420902", CLIENTES_TACURAL[1], "5997", "RUTA 12 KM 8.5 ESQ. GUARANI",
        "Garupa", "3304", "03764-400012", 3, 2, 75.40,
        (
            {"codigo": 10130, "descripcion": "FIAMBRE COCIDO PA 12", "unid": None,
             "kg": 12.00, "punit": 2759.51, "bonif": 10, "iva": 21},
            {"codigo": 20242, "descripcion": "PANCETA AHUMADA D", "unid": None,
             "kg": 4.60, "punit": 13636.86, "bonif": 10, "iva": 21},
            {"codigo": 10314, "descripcion": "SALAME MILAN SIN", "unid": None,
             "kg": 2.40, "punit": 10509.92, "bonif": 10, "iva": 21},
            {"codigo": 10200, "descripcion": "MORTADELA", "unid": None,
             "kg": 3.80, "punit": 7147.94, "bonif": 10, "iva": 21},
            {"codigo": 20140, "descripcion": "BONDIOLA", "unid": None,
             "kg": 1.60, "punit": 15824.38, "bonif": 10, "iva": 21},
            {"codigo": 10132, "descripcion": "JAMON COCIDO PAMP", "unid": None,
             "kg": 51.00, "punit": 4165.29, "bonif": 10, "iva": 21},
        ),
    ),
    _factura(
        "A00011-00420903", CLIENTES_TACURAL[2], "9258", "PERU 701",
        "Obera", "3360", "03764-400013", 4, 3, 120.00,
        (
            {"codigo": 10134, "descripcion": "FIAMBRE COCIDO DE 12", "unid": None,
             "kg": 60.00, "punit": 2759.51, "bonif": 10, "iva": 21},
            {"codigo": 10132, "descripcion": "JAMON COCIDO PAMP 12", "unid": None,
             "kg": 60.00, "punit": 4165.29, "bonif": 10, "iva": 21},
        ),
        girada=True,
    ),
    _factura(
        "A00011-00420904", CLIENTES_TACURAL[3], "9098", "AVDA LAVALLE 2720",
        "Posadas", "3300", "03764-400014", 10, 16, 194.80,
        (
            {"codigo": 20242, "descripcion": "PANCETA AHUMADA D 80", "unid": None,
             "kg": 145.00, "punit": 13636.86, "bonif": 10, "iva": 21},
            {"codigo": 20241, "descripcion": "PANCETA SALADA", "unid": None,
             "kg": 36.80, "punit": 13636.86, "bonif": 10, "iva": 21},
            {"codigo": 10804, "descripcion": "PANCETA AHUMADA D 40", "unid": None,
             "kg": 13.00, "punit": 13873.39, "bonif": 10, "iva": 21},
        ),
    ),
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

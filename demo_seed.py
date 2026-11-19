# coding=utf-8
"""Schema y datos idempotentes para la instalacion RND DEMO.

Incluye un escenario de consolidacion (#53): dos cuentas duplicadas de
"Cinco Hermanos" y dos de "Ceferino", con lugares de entrega y pedidos
historicos ficticios, para probar Simular + Consolidar sin riesgo.
"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import shutil

import pandas as pd


def _ruta_asset(nombre):
    """Devuelve la ruta de un archivo de assets/ o None si no esta.

    En desarrollo vive en la raiz del repo; en la build congelada queda
    dentro de _internal, al lado del modulo demo_seed.
    """
    base = Path(__file__).resolve().parent
    for carpeta in (base / "assets", base.parent / "assets"):
        candidato = carpeta / nombre
        if candidato.is_file():
            return candidato
    return None


def prepare_demo_database() -> None:
    # Importar despues de configurar sistema.demo.ini en demo_main.py.
    from modelos.ModeloBase import Auditoria, db
    from modelos.Usuarios import Usuario
    from modelos.Formula import Formula, MenuLateral
    from modelos.Accesos import Acceso
    from modelos.ParametrosSistema import ParamSist
    from modelos.Proveedores import Proveedor, ProcesoLista
    from modelos.Clientes import (
        Cliente,
        CodigoClienteProveedor,
        Localidades,
        LugarEntrega,
        RutaReparto,
    )
    from modelos.Tablas import TipoDeMovil, UnidadNegocio, Monedas
    from modelos.Empleados import ConceptoLiquidacion, Empleado
    from modelos.Equipos import ChoferEquipo, Equipos, Vencimientos
    from modelos.HojaRuta import HojaDeRuta
    from modelos.Pallet import Pallet, PalletDetalle
    from modelos.EstadoHojaRuta import EstadoHojaRuta

    if db.is_closed():
        db.connect(reuse_if_open=True)

    tables = [
        Auditoria,
        Usuario,
        Formula,
        MenuLateral,
        Acceso,
        ParamSist,
        Proveedor,
        ProcesoLista,
        RutaReparto,
        Localidades,
        Cliente,
        LugarEntrega,
        CodigoClienteProveedor,
        TipoDeMovil,
        UnidadNegocio,
        Monedas,
        ConceptoLiquidacion,
        Empleado,
        Equipos,
        ChoferEquipo,
        Vencimientos,
        HojaDeRuta,
        EstadoHojaRuta,
        Pallet,
        PalletDetalle,
    ]
    db.create_tables(tables, safe=True)

    _asegurar_lugares_entrega_multi_direccion(db)
    _asegurar_columna_metodo_importacion(db)
    _asegurar_columnas_pallet(db)

    admin, _ = Usuario.get_or_create(
        usu_id=1,
        defaults={
            "usuario": "demo",
            "nombre": "Usuario",
            "apellido": "Demo",
            "clave": "DEMO",
            "user_level": "01",
            "usuario_activo": True,
        },
    )
    if not admin.usuario_activo or admin.clave != "DEMO" or admin.user_level != "01":
        admin.usuario = "demo"
        admin.nombre = "Usuario"
        admin.apellido = "Demo"
        admin.clave = "DEMO"
        admin.user_level = "01"
        admin.usuario_activo = True
        admin.save()

    ParamSist.get_or_create(parametro="NACIONALIDAD", defaults={"valor": "ARG"})

    ruta_centro, _ = RutaReparto.get_or_create(descripcion="CENTRO", defaults={"activo": True})
    ruta_norte, _ = RutaReparto.get_or_create(descripcion="NORTE", defaults={"activo": True})

    obere, _ = Localidades.get_or_create(descripcion="Obera", defaults={"provincia": "Misiones"})
    san_vicente, _ = Localidades.get_or_create(descripcion="San Vicente", defaults={"provincia": "Misiones"})
    puerto_rico, _ = Localidades.get_or_create(descripcion="Puerto Rico", defaults={"provincia": "Misiones"})
    posadas, _ = Localidades.get_or_create(descripcion="Posadas", defaults={"provincia": "Misiones"})
    puerto_iguazu, _ = Localidades.get_or_create(descripcion="Puerto Iguazu", defaults={"provincia": "Misiones"})
    garupa, _ = Localidades.get_or_create(descripcion="Garupa", defaults={"provincia": "Misiones"})
    eldorado, _ = Localidades.get_or_create(descripcion="Eldorado", defaults={"provincia": "Misiones"})
    jardin_america, _ = Localidades.get_or_create(descripcion="Jardin America", defaults={"provincia": "Misiones"})
    candelaria, _ = Localidades.get_or_create(descripcion="Candelaria", defaults={"provincia": "Misiones"})

    clientes = []
    for data in (
        ("Cinco Hermanos", "30-70000001-1", "Av. Principal 120", puerto_rico, ruta_centro),
        ("Ceferino", "30-70000002-2", "Ruta 14 Km 980", obere, ruta_centro),
        ("Comercial San Vicente", "30-70000003-3", "Av. Libertador 450", san_vicente, ruta_norte),
        ("Mercado del Norte", "30-70000004-4", "Belgrano 88", san_vicente, ruta_norte),
    ):
        cliente, _ = Cliente.get_or_create(
            razon_social=data[0],
            defaults={
                "cuit": data[1],
                "direccion": data[2],
                "telefono": "03743-400000",
                "contacto": "Contacto demo",
                "activo": True,
                "observaciones": "Datos cargados automaticamente por RND DEMO",
                "localidad": data[3],
                "ruta_reparto": data[4],
            },
        )
        clientes.append(cliente)

    # Cuentas duplicadas para consolidacion (#53):
    # - "Cinco Hermanos San Vicente" sin CUIT: simular sin advertencias,
    #   permite el flujo completo Simular -> Consolidar.
    # - "Ceferino Obera" con CUIT distinto al destino: simular muestra la
    #   advertencia de identidad y bloquea la consolidacion automatica.
    dup_cinco, _ = Cliente.get_or_create(
        razon_social="Cinco Hermanos San Vicente",
        defaults={
            "cuit": None,
            "direccion": "Av. Libertador 450",
            "telefono": "03743-401011",
            "contacto": "Sucursal San Vicente",
            "activo": True,
            "observaciones": "Cuenta duplicada de Cinco Hermanos cargada para probar consolidacion",
            "localidad": san_vicente,
            "ruta_reparto": ruta_norte,
        },
    )
    dup_ceferino, _ = Cliente.get_or_create(
        razon_social="Ceferino Obera",
        defaults={
            "cuit": "30-77777777-7",
            "direccion": "Ruta 14 Km 980",
            "telefono": "03743-402022",
            "contacto": "Sucursal Obera",
            "activo": True,
            "observaciones": "Cuenta duplicada de Ceferino cargada para probar consolidacion",
            "localidad": obere,
            "ruta_reparto": ruta_centro,
        },
    )

    proveedores_demo = {}
    for razon_social, metodo, cuit in (
        ("Proveedor Demo - Tremblay", "TREMBLAY", "30-79999991-1"),
        ("Proveedor Demo - Tio Pujio", "TIO_PUJIO", "30-79999992-2"),
        ("Proveedor Demo - Detalle Ventas", "DETALLE_VENTAS", "30-79999993-3"),
        ("Proveedor Demo - Columnas", "COLUMNAS", "30-79999994-4"),
        ("Recreo", "DETALLE_VENTAS", "30-79999995-5"),
        ("Lario", "REPORTE_VIAJE", "30-79999996-6"),
    ):
        proveedor, _ = Proveedor.get_or_create(
            razon_social=razon_social,
            defaults={
                "cuit": cuit,
                "direccion": "Parque Industrial",
                "telefono": "03743-499999",
                "contacto": "Administracion",
                "activo": True,
                "observaciones": "Proveedor generado automaticamente por RND DEMO",
                "metodo_importacion": metodo,
            },
        )
        if proveedor.metodo_importacion != metodo or not proveedor.activo:
            proveedor.metodo_importacion = metodo
            proveedor.activo = True
            proveedor.save()
        proveedores_demo.setdefault(metodo, []).append(proveedor)

    # Compatibilidad con demos anteriores: el viejo "Proveedor Demo" queda como
    # Tremblay, pero ya no es el proveedor recomendado para las pruebas nuevas.
    proveedor_legacy = Proveedor.get_or_none(razon_social="Proveedor Demo")
    if proveedor_legacy is not None and proveedor_legacy.metodo_importacion != "TREMBLAY":
        proveedor_legacy.metodo_importacion = "TREMBLAY"
        proveedor_legacy.save()

    # Códigos externos específicos por proveedor para poder grabar los archivos
    # de ejemplo sin que el operador tenga que vincular clientes manualmente.
    codigos_demo = {
        "TREMBLAY": (("201504", clientes[0]), ("200633", clientes[1])),
        "TIO_PUJIO": (("10333", clientes[0]), ("10334", clientes[1])),
        "DETALLE_VENTAS": (
            ("NOMBRE:CINCO HERMANOS", clientes[0]),
            ("NOMBRE:CEFERINO", clientes[1]),
        ),
        "COLUMNAS": (("CLI-001", clientes[0]), ("CLI-002", clientes[1])),
    }
    for metodo, relaciones in codigos_demo.items():
        for proveedor in proveedores_demo.get(metodo, []):
            for codigo, cliente in relaciones:
                relacion, _ = CodigoClienteProveedor.get_or_create(
                    codigo=codigo,
                    proveedor=proveedor,
                    defaults={"cliente": cliente},
                )
                if relacion.cliente_id != cliente.id:
                    relacion.cliente = cliente
                    relacion.save()

    proveedor_columnas = proveedores_demo["COLUMNAS"][0]
    for codigo, columna in (
        ("Cliente", "Cliente"),
        ("Nombre_Cliente", "Nombre_Cliente"),
        ("Comprobante", "Comprobante"),
        ("Producto", "Producto"),
        ("Cantidad", "Cantidad"),
        ("KG", "KG"),
        ("Bultos", "Bultos"),
        ("Observaciones", "Observaciones"),
    ):
        proceso, _ = ProcesoLista.get_or_create(
            proveedor=proveedor_columnas,
            codigo=codigo,
            defaults={"columna": columna},
        )
        if proceso.columna != columna:
            proceso.columna = columna
            proceso.save()

    _generar_archivos_importacion_demo()

    # Caso real de prueba para el importador PDF/imagen con IA (#124).
    # Se mantiene en un modulo separado para poder ejecutarlo también a demanda.
    from utiles.seed_estancia_oro import seed_estancia_oro
    seed_estancia_oro()

    # Tacural: factura escaneada con un comprobante por pagina. El modulo
    # aparte deja el proveedor y sus clientes listos para probar la lectura.
    from utiles.seed_tacural import seed_tacural
    seed_tacural()

    def lugar(cliente, nombre, direccion, localidad, ruta, principal=False):
        obj, _ = LugarEntrega.get_or_create(
            cliente=cliente,
            nombre=nombre,
            defaults={
                "direccion": direccion,
                "localidad": localidad,
                "ruta_reparto": ruta,
                "principal": principal,
                "activo": True,
                "observaciones": "Lugar de entrega de demostracion",
            },
        )
        if (
            obj.activo is not True
            or bool(obj.principal) != principal
            or obj.direccion != direccion
            or obj.localidad_id != (localidad.id if localidad else None)
            or obj.observaciones != "Lugar de entrega de demostracion"
        ):
            obj.direccion = direccion
            obj.localidad = localidad
            obj.ruta_reparto = ruta
            obj.activo = True
            obj.observaciones = "Lugar de entrega de demostracion"
            obj.save()
        if principal and not obj.principal:
            obj.principal = True
            obj.save()
        return obj

    # Lugares de los clientes "reales" (destinos de consolidacion).
    lugar(clientes[0], "Puerto Rico", "Av. Principal 120", puerto_rico, ruta_centro, principal=True)
    lugar(clientes[0], "San Vicente", "Av. Libertador 450", san_vicente, ruta_norte)
    lugar(clientes[1], "Puerto Rico", "Av. Costanera 800", puerto_rico, ruta_norte, principal=True)
    lugar(clientes[1], "Obera", "Ruta 14 Km 980", obere, ruta_centro)
    # Lugares de las cuentas duplicadas: mismo nombre/direccion/localidad que
    # el destino para que la consolidacion los reutilice sin renombrar.
    lugar_san_vicente_dup = lugar(dup_cinco, "San Vicente", "Av. Libertador 450", san_vicente, ruta_norte, principal=True)
    lugar_obera_dup = lugar(dup_ceferino, "Obera", "Ruta 14 Km 980", obere, ruta_centro, principal=True)

    # Clientes del Reporte de viaje de Lario para que la importacion del PDF
    # muestre remitos resueltos por CUIT.
    lario_clientes = (
        ("SUPERMERCADOS NELSON S.R.L.", "30-71569257-7", "AV ZAPIOLA 5957", posadas, ruta_centro),
        ("RANKING S.R.L.", "30-71635982-0", "AV. REP. ARGENTINA 26", puerto_iguazu, ruta_norte),
        ("CANTERO MARGARITA OFELIA", "27-24631616-9", "DE LAS AMERICA Y VENEZUELA", garupa, ruta_centro),
        ("S.A. IMPORTADORA Y EXPORTADORA DE LA", "30-50673003-8", "AV TOMAS GUIDO 6070", posadas, ruta_centro),
        ("CALIFORNIA S.A.", "30-53952341-0", "CORDOBA 215", posadas, ruta_centro),
        ("AUTOSERVICIO CEFERINO RODRIGUEZ S.H.", "30-68791728-2", "RUTA NAC. 14 KM.1260", san_vicente, ruta_norte),
        ("AUTOSERVICIO MAYORISTA DIARCO S.A.", "30-60737179-9", "RUTA NAC.12", posadas, ruta_centro),
        ("MAYCAR SOCIEDAD ANONIMA (VITAL)", "30-61286533-3", "RUTA NAC.12 KM 6.5", posadas, ruta_centro),
        ("MARKWART YESSICA SILVANA", "27-33569342-1", "VILCAPUGIO Y JURAMENTO KM.10", eldorado, ruta_norte),
        ("V-ALLES SRL", "30-71512726-8", "AV. SAN MARTIN 333 KM.6", eldorado, ruta_norte),
        ("SILVA DANIELA DE LOS ANGELES", "27-29596433-8", "CHACRA 147 CASA 8 M.A", posadas, ruta_centro),
        ("R.N.D. SRL * MERCADERIA *", "30-71113274-7", "CALLE 248 NRO 2377 B", posadas, ruta_centro),
        ("RC S.R.L.", "30-71279110-8", "POLONIA 55", eldorado, ruta_norte),
        ("EL CONDOR SRL", "30-70867397-4", "AV. BELTRAME 1307", obere, ruta_centro),
        ("BOCANEGRA FACUNDO JAVIER", "20-29566747-9", "CASA 83 - B DOCENTE", obere, ruta_centro),
        ("SOL DE MAYO SRL", "30-59133999-7", "AV. LIBERTAD Y CUBA", jardin_america, ruta_norte),
        ("EL ARCO SRL", "30-70994384-3", "AV. B.ROQUE GONZALEZ ESQ. PRINGLES", candelaria, ruta_centro),
    )
    for nombre, cuit, direccion, localidad, ruta in lario_clientes:
        cliente, _ = Cliente.get_or_create(
            cuit=cuit,
            defaults={
                "razon_social": nombre,
                "direccion": direccion,
                "telefono": "03743-400000",
                "contacto": "Cliente demo Lario",
                "activo": True,
                "observaciones": "Cliente demo para importar el Reporte de viaje de Lario",
                "localidad": localidad,
                "ruta_reparto": ruta,
            },
        )
        lugar(cliente, localidad.descripcion, direccion, localidad, ruta, principal=True)

    concepto, _ = ConceptoLiquidacion.get_or_create(
        descripcion="Chofer",
        defaults={"monto": Decimal("0.00"), "activo": True},
    )
    choferes = []
    for nombre, apellido, email, doc in (
        ("Juan", "Gomez", "juan.demo@rnd.local", "30111222"),
        ("Carlos", "Benitez", "carlos.demo@rnd.local", "28999888"),
    ):
        empleado, _ = Empleado.get_or_create(
            email=email,
            defaults={
                "nombre": nombre,
                "apellido": apellido,
                "direccion": "Domicilio demo",
                "fecha_contratacion": date.today() - timedelta(days=900),
                "documento": doc,
                "telefono": "03743-455555",
                "activo": True,
                "concepto_liquidacion": concepto,
            },
        )
        choferes.append(empleado)

    camion, _ = TipoDeMovil.get_or_create(descripcion="CAMION", defaults={"activo": True})
    UnidadNegocio.get_or_create(descripcion="Distribucion", defaults={"prefijo": "RND", "activo": True})

    # get_or_create solo busca por descripcion; si ya existe una moneda con el
    # simbolo "$" pero otra descripcion, el INSERT choca con el UNIQUE simbolo.
    moneda_pesos = Monedas.get_or_none(descripcion="Pesos")
    if moneda_pesos is None:
        moneda_pesos = Monedas.get_or_none(simbolo="$")
    if moneda_pesos is None:
        moneda_pesos = Monedas.create(descripcion="Pesos", simbolo="$", activo=True)
    elif moneda_pesos.descripcion != "Pesos" or moneda_pesos.simbolo != "$" or not moneda_pesos.activo:
        moneda_pesos.descripcion = "Pesos"
        moneda_pesos.simbolo = "$"
        moneda_pesos.activo = True
        moneda_pesos.save()

    equipos = []
    for idx, patente in enumerate(("AF123AA", "AG456BB"), start=1):
        equipo, _ = Equipos.get_or_create(
            patente=patente,
            defaults={
                "descripcion": f"Camion Demo {idx}",
                "fecha_adquisicion": date.today() - timedelta(days=700 + idx * 30),
                "tipo_movil": camion,
                "observaciones": "Unidad de demostracion",
                "capacidad_tanque": Decimal("180.00"),
                "activo": True,
                "nro_chasis": f"DEMO-CHASIS-{idx}",
                "nro_motor": f"DEMO-MOTOR-{idx}",
            },
        )
        equipos.append(equipo)
        ChoferEquipo.get_or_create(
            empleado=choferes[idx - 1],
            movil=equipo,
            fecha_inicio=date.today() - timedelta(days=30),
        )
        Vencimientos.get_or_create(
            movil=equipo,
            descripcion="Seguro",
            defaults={"fecha_vencimiento": date.today() + timedelta(days=7 + idx)},
        )

    hoy = date.today()

    def pedido(cliente, lugar_entrega, ruta, comprobante, dias_atras, producto, cantidad, kg, bultos, equipo, responsable, observaciones):
        HojaDeRuta.get_or_create(
            comprobante=comprobante,
            defaults={
                "fecha": hoy - timedelta(days=dias_atras),
                "cliente": cliente,
                "nombre_cliente": cliente.razon_social,
                "lugar_entrega": lugar_entrega,
                "ruta": ruta,
                "producto": producto,
                "cantidad": Decimal(cantidad),
                "kg": Decimal(kg),
                "cantidad_bultos": Decimal(bultos),
                "observaciones": observaciones,
                "equipo_asignado": equipo,
                "responsable": responsable,
            },
        )

    for comprobante, cliente, ruta, producto, cantidad, kg, bultos, equipo, responsable in (
        ("FC-0001-00001234", clientes[0], ruta_centro, "Bebidas", "24", "320", "24", equipos[0], choferes[0]),
        ("FC-0001-00001235", clientes[1], ruta_centro, "Alimentos", "18", "210", "18", equipos[0], choferes[0]),
        ("FC-0001-00001236", clientes[2], ruta_norte, "Limpieza", "30", "275", "30", equipos[1], choferes[1]),
        ("FC-0001-00001237", clientes[3], ruta_norte, "Bebidas", "12", "155", "12", equipos[1], choferes[1]),
    ):
        pedido(cliente, None, ruta, comprobante, 0, producto, cantidad, kg, bultos, equipo, responsable, "Pedido demo")

    # Pedidos historicos de las cuentas duplicadas: los reasigna la
    # consolidacion al cliente destino si se ejecuta el flujo de #53.
    pedido(dup_cinco, lugar_san_vicente_dup, ruta_norte, "FC-2024-0000201", 200, "Bebidas", "20", "260", "20", equipos[0], choferes[0], "Pedido historico demo")
    pedido(dup_cinco, lugar_san_vicente_dup, ruta_norte, "FC-2025-0000102", 130, "Alimentos", "16", "180", "16", equipos[1], choferes[1], "Pedido historico demo")
    pedido(dup_cinco, lugar_san_vicente_dup, ruta_norte, "FC-2025-0000203", 60, "Limpieza", "28", "240", "28", equipos[0], choferes[0], "Pedido historico demo")
    pedido(dup_ceferino, lugar_obera_dup, ruta_centro, "FC-2025-0000304", 110, "Alimentos", "14", "150", "14", equipos[1], choferes[1], "Pedido historico demo")
    pedido(dup_ceferino, lugar_obera_dup, ruta_centro, "FC-2025-0000405", 45, "Bebidas", "22", "190", "22", equipos[0], choferes[0], "Pedido historico demo")
    pedido(dup_ceferino, lugar_obera_dup, ruta_centro, "FC-2026-0000106", 15, "Limpieza", "10", "120", "10", equipos[1], choferes[1], "Pedido historico demo")

    EstadoHojaRuta.get_or_create(
        fecha=hoy,
        ruta=ruta_centro,
        defaults={"estado": EstadoHojaRuta.LISTA, "actualizado_por": "demo"},
    )
    EstadoHojaRuta.get_or_create(
        fecha=hoy,
        ruta=ruta_norte,
        defaults={"estado": EstadoHojaRuta.EN_PREPARACION, "actualizado_por": "demo"},
    )

    _seed_menu(Formula, MenuLateral)


def _seed_menu(Formula, MenuLateral) -> None:
    # El seed vive en utiles.menu_operativo para que producción reciba la
    # misma estructura en el arranque (Migraciones._fase_menu_operativo).
    # El demo agrega además la sección DEMO con el reseteo de datos.
    from utiles.menu_operativo import asegurar_menu_operativo

    asegurar_menu_operativo(sis_id=1, incluir_demo=True)

def _asegurar_lugares_entrega_multi_direccion(db) -> None:
    """Elimina el índice legacy UNIQUE(cliente_id, nombre) en SQLite DEMO.

    El modelo actual permite repetir una referencia cuando la dirección es
    distinta. Demos ya creados conservan índices viejos aunque create_tables
    use el modelo nuevo, por eso hay que retirarlo explícitamente.
    """
    try:
        indices = list(db.execute_sql(
            "PRAGMA index_list('lugares_entrega')"
        ).fetchall())
    except Exception:
        return

    for indice in indices:
        if len(indice) < 3 or not indice[2]:
            continue
        nombre_indice = indice[1]
        try:
            columnas = [
                fila[2]
                for fila in db.execute_sql(
                    'PRAGMA index_info("{}")'.format(
                        str(nombre_indice).replace('"', '""')
                    )
                ).fetchall()
            ]
        except Exception:
            continue
        if columnas != ["cliente_id", "nombre"]:
            continue
        if str(nombre_indice).startswith("sqlite_autoindex"):
            # Peewee crea este índice como CREATE UNIQUE INDEX, pero dejamos
            # este guard por seguridad ante esquemas manuales.
            continue
        db.execute_sql(
            'DROP INDEX IF EXISTS "{}"'.format(
                str(nombre_indice).replace('"', '""')
            )
        )

    db.execute_sql(
        "CREATE UNIQUE INDEX IF NOT EXISTS "
        "uq_lugares_entrega_cliente_nombre_direccion "
        "ON lugares_entrega(cliente_id, nombre, direccion)"
    )


def _asegurar_columna_metodo_importacion(db) -> None:
    """Agrega la columna nueva también sobre demos SQLite ya existentes."""
    try:
        columnas = {col.name for col in db.get_columns("proveedor")}
    except Exception:
        return
    if "metodo_importacion" in columnas:
        return
    db.execute_sql(
        "ALTER TABLE proveedor ADD COLUMN metodo_importacion "
        "VARCHAR(30) NOT NULL DEFAULT 'COLUMNAS'"
    )


def _asegurar_columnas_pallet(db) -> None:
    """Agrega quién/cuándo validó la carga sobre demos SQLite ya existentes."""
    try:
        columnas = {col.name for col in db.get_columns("pallet")}
    except Exception:
        return
    if "cargado_por" not in columnas:
        db.execute_sql(
            "ALTER TABLE pallet ADD COLUMN cargado_por "
            "VARCHAR(100) NOT NULL DEFAULT ''"
        )
    if "cargado_en" not in columnas:
        db.execute_sql("ALTER TABLE pallet ADD COLUMN cargado_en DATETIME")


def _generar_archivos_importacion_demo() -> None:
    """Genera los archivos listos para probar cada método del importador."""
    destino = Path(__file__).resolve().parent / "demo_importaciones"
    destino.mkdir(exist_ok=True)

    # Tremblay: layout irregular cliente/productos, igual al importador real.
    tremblay = [
        ["", "BONDA JOSE", "", "", "", "", "", "", "", "", ""],
        ["201504", "Cinco Hermanos", "PUERTO RICO", "11/09/2026", "0001001", "3", "", "", "", "", ""],
        ["CODIGO", "DETALLE", "", "", "", "ORIGINAL", "DESP.", "DIF.", "KG", "TOTAL", "COMPROB."],
        ["1035", "CREMA DE LECHE TREMBLAY X 200 CM3 X 12 U", "", "", "", 2, 2, 0, 7.2, 45000, "000800153513"],
        ["11106", "QUESO CREMA TREMBLAY CLASICO 12x290gr", "", "", "", 1, 1, 0, 3.5, 28000, "000800153513"],
        ["200633", "Ceferino", "OBERA", "11/09/2026", "0001002", "2", "", "", "", "", ""],
        ["CODIGO", "DETALLE", "", "", "", "ORIGINAL", "DESP.", "DIF.", "KG", "TOTAL", "COMPROB."],
        ["1021", "MANTECA TREMBLAY X 100 GR X 60 U", "", "", "", 2, 2, 0, 12.0, 62000, "000800153514"],
    ]
    pd.DataFrame(tremblay).to_excel(destino / "01_tremblay_demo.xlsx", index=False, header=False)

    # Tío Pujio.
    filas = [[""] * 17 for _ in range(10)]
    filas.append(["", "Fecha", "", "Tipo", "Comprobante", "", "", "", "Hormas", "", "Kilos", "", "", "", "", "", ""])
    for codigo, nombre, comprobante, producto_codigo, producto, bultos, kilos in (
        (10333, "Cinco Hermanos", "N0001-00115811", 2, "QUESO TYBO", 8, 31.82),
        (10334, "Ceferino", "N0001-00115812", 22, "RICOTTA", 6, 21.40),
    ):
        cliente = [""] * 17
        cliente[0], cliente[2], cliente[4] = "Cliente :", codigo, nombre
        filas.append(cliente)
        pedido = [""] * 17
        pedido[1], pedido[3], pedido[5] = "11/09/2026", "PED", comprobante
        filas.append(pedido)
        item = [""] * 17
        item[1], item[2], item[7], item[10] = producto_codigo, producto, bultos, kilos
        filas.append(item)
    pd.DataFrame(filas).to_excel(destino / "02_tio_pujio_demo.xlsx", index=False, header=False)

    # Detalle de ventas.
    detalle = [
        ["Ventas Provincia Misiones desde fecha 10/09/2026 hasta fecha 11/09/2026", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        ["", "", "", "", "", "", "", "", ""],
        ["Tipo Operacion", "ciudad", "Cliente", "Codigo", "DescripcionProducto", "", "Unidades", "Kilos", "Total"],
        ["Chacinados", "PUERTO RICO", "Cinco Hermanos", 12311, "FIAMBRE COCIDO", "", 12, 52.25, 264468.60],
        ["Lacteos", "OBERA", "Ceferino", 15718, "QUESO CREMOSO", "", 10, 13.09, 146372.38],
    ]
    pd.DataFrame(detalle).to_excel(destino / "03_detalle_ventas_demo.xlsx", index=False, header=False)

    # Columnas configurables.
    columnas = pd.DataFrame([
        {
            "Cliente": "CLI-001",
            "Nombre_Cliente": "Cinco Hermanos",
            "Comprobante": "DEMO-COL-001",
            "Producto": "Bebidas",
            "Cantidad": 10,
            "KG": 120,
            "Bultos": 10,
            "Observaciones": "Importación demo por columnas",
        },
        {
            "Cliente": "CLI-002",
            "Nombre_Cliente": "Ceferino",
            "Comprobante": "DEMO-COL-002",
            "Producto": "Alimentos",
            "Cantidad": 8,
            "KG": 95,
            "Bultos": 8,
            "Observaciones": "Importación demo por columnas",
        },
    ])
    columnas.to_excel(destino / "04_columnas_demo.xlsx", index=False)

    # Tacural: el proveedor manda un PDF escaneado con un comprobante por
    # pagina. El archivo viene en assets/ y se copia para que el tester lo
    # tenga a mano, igual que las cuatro planillas.
    origen = _ruta_asset("proveedor_tacural_demo.pdf")
    if origen is not None:
        shutil.copyfile(origen, destino / "05_proveedor_tacural.pdf")

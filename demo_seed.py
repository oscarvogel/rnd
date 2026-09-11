# coding=utf-8
"""Schema y datos idempotentes para la instalacion RND DEMO.

Incluye un escenario de consolidacion (#53): dos cuentas duplicadas de
"Cinco Hermanos" y dos de "Ceferino", con lugares de entrega y pedidos
historicos ficticios, para probar Simular + Consolidar sin riesgo.
"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd


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
    ]
    db.create_tables(tables, safe=True)

    _asegurar_columna_metodo_importacion(db)

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
        proveedores_demo[metodo] = proveedor

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
        proveedor = proveedores_demo[metodo]
        for codigo, cliente in relaciones:
            relacion, _ = CodigoClienteProveedor.get_or_create(
                codigo=codigo,
                proveedor=proveedor,
                defaults={"cliente": cliente},
            )
            if relacion.cliente_id != cliente.id:
                relacion.cliente = cliente
                relacion.save()

    proveedor_columnas = proveedores_demo["COLUMNAS"]
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
    def formula(nombre, orden, archivo="", valid="", pare=0, imag=""):
        obj, _ = Formula.get_or_create(
            for_nomb=nombre,
            sis_id=1,
            defaults={
                "tfo_id": 1,
                "for_orde": orden,
                "for_pare": pare,
                "for_arch": archivo,
                "for_imag": imag,
                "gfo_id": 0,
                "for_valid": valid,
            },
        )
        # get_or_create no actualiza filas ya existentes; repara el demo para
        # que corridas anteriores queden con la misma jerarquia e iconos.
        campos = {
            "tfo_id": 1,
            "for_orde": orden,
            "for_pare": pare,
            "for_arch": archivo,
            "for_imag": imag,
            "gfo_id": 0,
            "for_valid": valid,
        }
        if any(getattr(obj, campo) != valor for campo, valor in campos.items()):
            for campo, valor in campos.items():
                setattr(obj, campo, valor)
            obj.save()
        return obj

    f_oper = formula("Operaciones", 1)
    f_maestros = formula("Maestros", 2)
    cab_oper, _ = MenuLateral.get_or_create(nombre="OPERACIONES", for_id=f_oper, for_pare=0)
    cab_mae, _ = MenuLateral.get_or_create(nombre="MAESTROS", for_id=f_maestros, for_pare=0)

    opciones = (
        (f_oper, cab_oper.id, "Importar pedidos", "ImportacionPedidos.ImportacionPedidosController", "IMPORTAR_PEDIDOS", 10, "iconfinder_icon-81-document-add_314445.png"),
        (f_oper, cab_oper.id, "Organizar pedidos", "BandejaPedidos.BandejaPedidosController", "ORGANIZAR_PEDIDOS", 20, "edit.png"),
        (f_oper, cab_oper.id, "Asignar recursos", "AsignacionRecursos.AsignacionRecursosController", "ASIGNAR_RECURSOS", 30, "empleados.png"),
        (f_oper, cab_oper.id, "Validar hoja de ruta", "ValidacionHojaRuta.ValidacionHojaRutaController", "VALIDAR_HOJA", 40, "search.png"),
        (f_maestros, cab_mae.id, "Clientes", "ABMClientes.ABMClientesController", "ABM_CLIENTES", 50, "clientes.png"),
        (f_maestros, cab_mae.id, "Equipos", "ABMEquipos.ABMEquiposController", "ABM_EQUIPOS", 60, "maquinas.png"),
    )
    for padre, menu_parent, nombre, archivo, valid, orden, imag in opciones:
        f = formula(nombre, orden, archivo, valid, pare=padre.for_id, imag=imag)
        MenuLateral.get_or_create(nombre=nombre, for_id=f, for_pare=menu_parent)

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


def _generar_archivos_importacion_demo() -> None:
    """Genera cuatro archivos listos para probar cada método del importador."""
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

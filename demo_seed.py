# coding=utf-8
"""Schema y datos idempotentes para la instalacion RND DEMO.

Incluye un escenario de consolidacion (#53): dos cuentas duplicadas de
"Cinco Hermanos" y dos de "Ceferino", con lugares de entrega y pedidos
historicos ficticios, para probar Simular + Consolidar sin riesgo.
"""

from datetime import date, timedelta
from decimal import Decimal


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

    proveedor, _ = Proveedor.get_or_create(
        razon_social="Proveedor Demo",
        defaults={
            "cuit": "30-79999999-9",
            "direccion": "Parque Industrial",
            "telefono": "03743-499999",
            "contacto": "Administracion",
            "activo": True,
            "observaciones": "Proveedor de demostracion",
        },
    )
    for idx, cliente in enumerate(clientes, start=1):
        CodigoClienteProveedor.get_or_create(
            codigo=f"CLI-{idx:03d}",
            cliente=cliente,
            proveedor=proveedor,
        )
    # El duplicado de Cinco Hermanos reutiliza el mismo codigo del proveedor:
    # la consolidacion lo deduplicara. El de Ceferino tiene codigo propio que
    # sera movido al cliente destino.
    CodigoClienteProveedor.get_or_create(
        codigo="CLI-001",
        cliente=dup_cinco,
        proveedor=proveedor,
    )
    CodigoClienteProveedor.get_or_create(
        codigo="CLI-006",
        cliente=dup_ceferino,
        proveedor=proveedor,
    )

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
    f_demo = formula("Demo", 90)
    cab_oper, _ = MenuLateral.get_or_create(nombre="OPERACIONES", for_id=f_oper, for_pare=0)
    cab_mae, _ = MenuLateral.get_or_create(nombre="MAESTROS", for_id=f_maestros, for_pare=0)
    cab_demo, _ = MenuLateral.get_or_create(nombre="DEMO", for_id=f_demo, for_pare=0)

    opciones = (
        (f_oper, cab_oper.id, "Importar pedidos", "ImportacionPedidos.ImportacionPedidosController", "IMPORTAR_PEDIDOS", 10, "iconfinder_icon-81-document-add_314445.png"),
        (f_oper, cab_oper.id, "Organizar pedidos", "BandejaPedidos.BandejaPedidosController", "ORGANIZAR_PEDIDOS", 20, "edit.png"),
        (f_oper, cab_oper.id, "Asignar recursos", "AsignacionRecursos.AsignacionRecursosController", "ASIGNAR_RECURSOS", 30, "empleados.png"),
        (f_oper, cab_oper.id, "Validar hoja de ruta", "ValidacionHojaRuta.ValidacionHojaRutaController", "VALIDAR_HOJA", 40, "search.png"),
        (f_maestros, cab_mae.id, "Clientes", "ABMClientes.ABMClientesController", "ABM_CLIENTES", 50, "clientes.png"),
        (f_maestros, cab_mae.id, "Equipos", "ABMEquipos.ABMEquiposController", "ABM_EQUIPOS", 60, "maquinas.png"),
        (f_demo, cab_demo.id, "Restablecer datos demo", "ResetDemo.ResetDemoController", "RESET_DEMO", 900, "edit.png"),
    )
    for padre, menu_parent, nombre, archivo, valid, orden, imag in opciones:
        f = formula(nombre, orden, archivo, valid, pare=padre.for_id, imag=imag)
        MenuLateral.get_or_create(nombre=nombre, for_id=f, for_pare=menu_parent)


def reset_demo_database() -> None:
    """Borra por completo la base DEMO y vuelve a cargar el seed inicial.

    Esta operación está deliberadamente bloqueada fuera de RND_DEMO_MODE y
    fuera de SQLite para que nunca pueda tocar una base productiva.
    """
    import os
    from peewee import SqliteDatabase

    if os.getenv("RND_DEMO_MODE") != "1":
        raise RuntimeError("El restablecimiento sólo está disponible en RND DEMO.")

    from modelos.ModeloBase import Auditoria, db
    if not isinstance(db, SqliteDatabase):
        raise RuntimeError("El restablecimiento DEMO sólo puede ejecutarse sobre SQLite.")

    from modelos.Usuarios import Usuario
    from modelos.Formula import Formula, MenuLateral
    from modelos.Accesos import Acceso
    from modelos.ParametrosSistema import ParamSist
    from modelos.Proveedores import Proveedor, ProcesoLista
    from modelos.Clientes import (
        Cliente, CodigoClienteProveedor, Localidades, LugarEntrega, RutaReparto,
    )
    from modelos.Tablas import TipoDeMovil, UnidadNegocio, Monedas
    from modelos.Empleados import ConceptoLiquidacion, Empleado
    from modelos.Equipos import ChoferEquipo, Equipos, Vencimientos
    from modelos.HojaRuta import HojaDeRuta
    from modelos.EstadoHojaRuta import EstadoHojaRuta

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

    if db.is_closed():
        db.connect(reuse_if_open=True)

    # SQLite no permite deshabilitar FK dentro de una transacción activa.
    db.execute_sql("PRAGMA foreign_keys = OFF")
    try:
        for model in reversed(tables):
            model.drop_table(safe=True)
    finally:
        db.execute_sql("PRAGMA foreign_keys = ON")

    prepare_demo_database()

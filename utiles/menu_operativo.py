# coding=utf-8
"""Estructura del menú operativo del shell moderno (issue #3).

La barra lateral, el menubar y los permisos se alimentan de las tablas
``formula`` / ``menu_lateral``. Ese seed sólo existía en RND DEMO
(``demo_seed._seed_menu``), así que producción mostraba la navegación
vieja (Archivos/Tablas, Archivo/Hoja Ruta) aunque corriera el código
nuevo: mismo programa, distinta DATA.

Este módulo centraliza el seed idempotente para ambos entornos. Sólo
agrega las filas que faltan y repara las que derivaron; nunca borra ni
desactiva filas existentes (ni las legacy de producción ni sus accesos).

Las opciones se buscan por ``(for_nomb, sis_id, for_valid)`` y no sólo
por nombre: si producción ya tiene una fórmula legacy homónima (ej.
"Clientes" con otro ``for_valid``) se crea la fila nueva en vez de
secuestrar la vieja.
"""

from modelos.Formula import Formula, MenuLateral
from pyqt5libs.pyqt5libs import Constantes
from pyqt5libs.pyqt5libs.utiles import LeerIni

CABECERAS = (
    ("Operaciones", 1),
    ("Maestros", 2),
)

# (cabecera, nombre, for_arch, for_valid, orden, icono)
OPCIONES_OPERATIVAS = (
    ("Operaciones", "Importar pedidos",
     "ImportacionPedidos.ImportacionPedidosController",
     "IMPORTAR_PEDIDOS", 10,
     "iconfinder_icon-81-document-add_314445.png"),
    ("Operaciones", "Organizar pedidos",
     "BandejaPedidos.BandejaPedidosController",
     "ORGANIZAR_PEDIDOS", 20, "edit.png"),
    ("Operaciones", "Asignar recursos",
     "AsignacionRecursos.AsignacionRecursosController",
     "ASIGNAR_RECURSOS", 30, "empleados.png"),
    ("Operaciones", "Armar pallets",
     "ArmadoPallets.ArmadoPalletsController",
     "ARMAR_PALLETS", 35, "edit.png"),
    ("Operaciones", "Validar hoja de ruta",
     "ValidacionHojaRuta.ValidacionHojaRutaController",
     "VALIDAR_HOJA", 40, "search.png"),
    ("Maestros", "Clientes",
     "ABMClientes.ABMClientesController",
     "ABM_CLIENTES", 50, "clientes.png"),
    ("Maestros", "Equipos",
     "ABMEquipos.ABMEquiposController",
     "ABM_EQUIPOS", 60, "maquinas.png"),
    ("Maestros", "Proveedores",
     "ABMProveedores.ABMProveedoresController",
     "ABM_PROVEEDORES", 70, "proveedores.png"),
)

# Sólo para RND DEMO: en producción no tiene sentido.
CABECERA_DEMO = ("Demo", 3)
OPCION_DEMO_RESET = (
    "Demo", "Restablecer datos demo",
    "ResetDemo.ResetDemoController",
    "RESET_DEMO", 80, "edit.png",
)


def _sis_id(sis_id=None):
    if sis_id is not None:
        return int(sis_id)
    try:
        return int(LeerIni("sistema") or Constantes.IDSISTEMA)
    except (TypeError, ValueError):
        return int(Constantes.IDSISTEMA)


def _gfo_valido(sistema):
    """Grupo de formularios válido para las filas nuevas.

    Producción tiene ``FK formula.gfo_id -> gruform(gfo_id)`` y el 0 del
    demo no existe ahí (1452). Se reutiliza el grupo de las cabeceras ya
    existentes del sistema; si no hay ninguna, el primer grupo de gruform;
    si tampoco hay tabla gruform (SQLite demo), 0 como antes.
    """
    try:
        fila = (Formula.select(Formula.gfo_id)
                .where(Formula.sis_id == sistema, Formula.for_pare == 0)
                .order_by(Formula.for_id).tuples().first())
        if fila is not None:
            return int(fila[0])
    except Exception:
        pass
    try:
        cursor = Formula._meta.database.execute_sql(
            "SELECT gfo_id FROM gruform ORDER BY gfo_id LIMIT 1")
        fila = cursor.fetchone()
        if fila is not None:
            return int(fila[0])
    except Exception:
        pass
    return 0


def asegurar_formula(nombre, orden, archivo="", valid="", pare=0, imag="",
                     sis_id=None, gfo_id=0):
    """Crea la fórmula si falta; si existe con el mismo valid, la repara."""
    sistema = _sis_id(sis_id)
    obj, _creada = Formula.get_or_create(
        for_nomb=nombre,
        sis_id=sistema,
        for_valid=valid,
        defaults={
            "tfo_id": 1,
            "for_orde": orden,
            "for_pare": pare,
            "for_arch": archivo,
            "for_imag": imag,
            "gfo_id": gfo_id,
        },
    )
    # get_or_create no actualiza filas ya existentes; repara la jerarquía,
    # el destino y los iconos para que corridas anteriores queden iguales.
    campos = {
        "tfo_id": 1,
        "for_orde": orden,
        "for_pare": pare,
        "for_arch": archivo,
        "for_imag": imag,
        "gfo_id": gfo_id,
    }
    if any(getattr(obj, campo) != valor for campo, valor in campos.items()):
        for campo, valor in campos.items():
            setattr(obj, campo, valor)
        obj.save()
    return obj


def asegurar_cabecera(nombre, orden, sis_id=None, gfo_id=0):
    """Crea la fórmula cabecera y su entrada en menu_lateral (for_pare=0)."""
    formula = asegurar_formula(nombre, orden, sis_id=sis_id, gfo_id=gfo_id)
    cabecera, _ = MenuLateral.get_or_create(
        nombre=nombre.upper(), for_id=formula, for_pare=0)
    return formula, cabecera


def asegurar_opcion(cabecera_nombre, nombre, archivo, valid, orden, imag,
                    cabeceras, sis_id=None, gfo_id=0):
    """Crea la opción bajo su cabecera (fórmula + item de menu_lateral)."""
    _formula_cabecera, cabecera = cabeceras[cabecera_nombre]
    padre_id = _formula_cabecera.for_id
    formula = asegurar_formula(nombre, orden, archivo=archivo, valid=valid,
                               pare=padre_id, imag=imag, sis_id=sis_id,
                               gfo_id=gfo_id)
    MenuLateral.get_or_create(
        nombre=nombre, for_id=formula, for_pare=cabecera.id)
    return formula


def asegurar_menu_operativo(sis_id=None, incluir_demo=False):
    """Asegura la navegación del shell moderno. Idempotente y aditivo."""
    sistema = _sis_id(sis_id)
    grupo = _gfo_valido(sistema)
    cabeceras = {}
    for nombre, orden in CABECERAS:
        cabeceras[nombre] = asegurar_cabecera(
            nombre, orden, sis_id=sistema, gfo_id=grupo)
    for cabecera_nombre, nombre, archivo, valid, orden, imag in OPCIONES_OPERATIVAS:
        asegurar_opcion(cabecera_nombre, nombre, archivo, valid, orden, imag,
                        cabeceras, sis_id=sistema, gfo_id=grupo)
    if incluir_demo:
        nombre_cab, orden_cab = CABECERA_DEMO
        cabeceras[nombre_cab] = asegurar_cabecera(
            nombre_cab, orden_cab, sis_id=sistema, gfo_id=grupo)
        (cabecera_nombre, nombre, archivo, valid, orden,
         imag) = OPCION_DEMO_RESET
        asegurar_opcion(cabecera_nombre, nombre, archivo, valid, orden, imag,
                        cabeceras, sis_id=sistema, gfo_id=grupo)

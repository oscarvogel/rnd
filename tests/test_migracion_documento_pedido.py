# coding=utf-8
"""La migracion de #89 no podia correr en una instalacion sin importar pedidos.

MigrarVersion altera ``documento_pedido.cliente_id`` en cada login, pero las tablas
documento_pedido* son aditivas (#82) y solo se creaban al importar pedidos
(Documentos.asegurar_esquema_documentos). En una instalacion que nunca importo,
MySQL respondia 1146 "Table 'rnd.documento_pedido' doesn't exist" y el arranque
terminaba en "No se pudieron aplicar las migraciones de la base de datos".

El test corre la migracion REAL contra un MySQL simulado. Lo unico que se
reemplaza es el servidor, porque la falla es del servidor (1146), no del codigo:
si el test pasara con el fix sin llegar a la migracion, no probaria nada.
"""
import re

import peewee
import pytest

import controladores.Migraciones as modulo_migraciones
import modelos.Documentos as documentos_mod
from modelos.Clientes import Cliente, Localidades, LugarEntrega, RutaReparto
from modelos.Documentos import (
    DocumentoPedido,
    DocumentoPedidoDetalle,
    DocumentoPedidoHojaRuta,
)
from modelos.Empleados import ConceptoLiquidacion
from modelos.EstadoHojaRuta import EstadoHojaRuta
from modelos.HojaRuta import HojaDeRuta
from modelos.Pallet import Pallet, PalletDetalle
from modelos.Proveedores import ProcesoLista, Proveedor


MODELOS_MIGRADOS = [
    Cliente,
    Localidades,
    LugarEntrega,
    RutaReparto,
    HojaDeRuta,
    Pallet,
    PalletDetalle,
    ProcesoLista,
    ConceptoLiquidacion,
    EstadoHojaRuta,
    Proveedor,
    DocumentoPedido,
    DocumentoPedidoDetalle,
    DocumentoPedidoHojaRuta,
]


def tabla(modelo):
    """Nombre real de la tabla.

    En peewee 4 los modelos declarados con el ``db_table`` viejo devuelven un
    objeto Metadata en vez de un string, asi que hay que normalizar.
    """
    return str(modelo._meta.table_name)


def _tipo_sql(campo):
    """Tipo SQL de la columna como texto.

    Ojo: en peewee 4 ``ddl_datatype`` devuelve un nodo SQL, no un string, y
    MySQLColumn.sql() no sabe renderizar un nodo. Hay que compilarlo.
    """
    tipo = campo.ddl_datatype(peewee.Context())
    if isinstance(tipo, str):
        return tipo
    return peewee.Context().sql(tipo).query()[0]


def _describe(modelo):
    """Filas de DESCRIBE derivadas de los metadatos reales del modelo.

    Se calculan desde el modelo en vez de hardcodearlos: es lo que MySQL
    devolveria de verdad para esa tabla.
    """
    filas = []
    for campo in modelo._meta.sorted_fields:
        filas.append((
            campo.column_name,
            _tipo_sql(campo),
            "YES" if campo.null else "NO",
            "PRI" if campo.primary_key else "",
            campo.default,
            "",
        ))
    return filas


_RE_CREATE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?`?([A-Za-z0-9_]+)`?", re.I
)
_RE_ALTER = re.compile(r"ALTER\s+TABLE\s+`?([A-Za-z0-9_]+)`?", re.I)
_RE_DESCRIBE = re.compile(r"DESCRIBE\s+`?([A-Za-z0-9_]+)`?", re.I)
_RE_SHOW_INDEX = re.compile(r"SHOW\s+INDEX\s+FROM\s+`?([A-Za-z0-9_]+)`?", re.I)
_RE_DDL = re.compile(r"\s*(?:ALTER|CREATE|DROP)\b", re.I)


class _CursorVacio:
    """Cursor que no trae filas: alcanza para las consultas de la migracion."""

    description = ()
    rowcount = 0

    def __init__(self, filas=()):
        self.filas = list(filas)

    def fetchall(self):
        return list(self.filas)

    def fetchone(self):
        return self.filas[0] if self.filas else None

    def iterator(self):
        return iter(self.filas)

    def close(self):
        pass

    def __iter__(self):
        return iter(self.filas)


class MySQLSimulado(peewee.MySQLDatabase):
    """MySQL sin socket: registra el DDL y reproduce el 1146 de tabla inexistente."""

    def __init__(self):
        super().__init__("rnd_prueba")
        self.tablas = set()
        self.ddl = []
        self._por_tabla = {tabla(m): m for m in MODELOS_MIGRADOS}

    # -- superficie que peewee / playhouse necesitan -------------------
    def get_tables(self, schema=None):
        return sorted(self.tablas)

    def get_foreign_keys(self, table, schema=None):
        return []

    def execute_sql(self, sql, params=None):
        describe = _RE_DESCRIBE.search(sql) if isinstance(sql, str) else None
        if describe:
            modelo = self._por_tabla.get(describe.group(1))
            return _CursorVacio(_describe(modelo) if modelo else ())

        indices = _RE_SHOW_INDEX.search(sql) if isinstance(sql, str) else None
        if indices:
            # Sin indices unicos legacy: la migracion agrega el actual.
            return _CursorVacio(())

        self._registrar(sql)
        return _CursorVacio()

    # -- emulacion del servidor ---------------------------------------
    def _registrar(self, sql):
        if not isinstance(sql, str) or not _RE_DDL.match(sql):
            return
        self.ddl.append(sql)

        creada = _RE_CREATE.search(sql)
        if creada:
            self.tablas.add(creada.group(1))
            return

        alterada = _RE_ALTER.search(sql)
        if alterada and alterada.group(1) not in self.tablas:
            raise peewee.ProgrammingError(
                1146, "Table 'rnd.%s' doesn't exist" % alterada.group(1)
            )


@pytest.fixture
def mysql(monkeypatch):
    """MySQL simulado con las tablas legacy de una instalacion real."""
    simulado = MySQLSimulado()
    monkeypatch.setattr(modulo_migraciones, "db", simulado)
    monkeypatch.setattr(documentos_mod, "db", simulado)

    # Lo que ya existe antes de migrar. documento_pedido* NO va a proposito:
    # esa es justamente la instalacion que rompia.
    for modelo in (Cliente, RutaReparto, Localidades, HojaDeRuta,
                   Proveedor, Pallet):
        simulado.tablas.add(tabla(modelo))

    with simulado.bind_ctx(MODELOS_MIGRADOS, bind_refs=False, bind_backrefs=False):
        yield simulado


def _tablas_de_ddl(ddl, regex):
    nombres = set()
    for sql in ddl:
        encontrado = regex.search(sql)
        if encontrado:
            nombres.add(encontrado.group(1))
    return nombres


def test_migrar_sin_documento_pedido_no_aborta_el_arranque(mysql):
    """El login no debe fallar en una instalacion que nunca importo pedidos."""
    migracion = modulo_migraciones.MigracionBaseDatos()
    migracion.esperar_migracion()

    assert migracion.error is None, "La migracion fallo: {}".format(
        repr(migracion.error)
    )


def test_migrar_crea_documento_pedido_antes_de_alterarlo(mysql):
    """Las tablas tienen que existir antes del alter que las deja nullable."""
    assert tabla(DocumentoPedido) not in mysql.tablas

    migracion = modulo_migraciones.MigracionBaseDatos()
    migracion.esperar_migracion()

    for modelo in (DocumentoPedido, DocumentoPedidoDetalle,
                   DocumentoPedidoHojaRuta):
        assert tabla(modelo) in mysql.tablas

    # El CREATE tiene que ocurrir antes que el ALTER de la misma tabla.
    crea = next(
        i for i, sql in enumerate(mysql.ddl)
        if _RE_CREATE.search(sql)
        and _RE_CREATE.search(sql).group(1) == tabla(DocumentoPedido)
    )
    altera = next(
        i for i, sql in enumerate(mysql.ddl)
        if _RE_ALTER.search(sql)
        and _RE_ALTER.search(sql).group(1) == tabla(DocumentoPedido)
    )
    assert crea < altera


def test_migrar_sigue_corrigiendo_cliente_id_de_instalaciones_viejas(mysql):
    """El alter de #89 debe seguir aplicando: salva instalaciones con NOT NULL."""
    migracion = modulo_migraciones.MigracionBaseDatos()
    migracion.esperar_migracion()

    # Sin esto el test pasaria aunque la migracion abortara en ese mismo alter,
    # que es exactamente lo que hacia antes del fix.
    assert migracion.error is None, "La migracion fallo: {}".format(
        repr(migracion.error)
    )

    alters = [
        sql for sql in mysql.ddl
        if _RE_ALTER.search(sql)
        and _RE_ALTER.search(sql).group(1) == tabla(DocumentoPedido)
    ]
    assert len(alters) == 1, alters
    assert "cliente_id" in alters[0]
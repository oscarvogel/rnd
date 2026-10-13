import logging
import sys
import time
import traceback
import threading
import peewee
from peewee import JOIN

from modelos.Clientes import CodigoClienteProveedor, LugarEntrega, Cliente
from modelos.Empleados import ConceptoLiquidacion
from modelos.EstadoHojaRuta import EstadoHojaRuta
from modelos.HojaRuta import HojaDeRuta
from modelos.Pallet import Pallet, PalletDetalle
from modelos.ModeloBase import Auditoria, db
from playhouse.migrate import (
    MySQLMigrator, CharField, migrate, DecimalField, IntegerField,
    BooleanField, FloatField, TextField, TimeField, DateTimeField,
)

from modelos.Clientes import Localidades
from modelos.Documentos import asegurar_esquema_documentos
from modelos.Proveedores import ProcesoLista, Proveedor
from pyqt5libs.pyqt5libs.utiles import LeerIni
from utiles.menu_operativo import asegurar_menu_operativo


class MigracionBaseDatos:
    migraciones = []
    colentero = IntegerField(default=0)
    colentero1 = IntegerField(default=1)
    colfloat = FloatField(default=0)

    def __init__(self):
        database = db
        self.migraciones = []
        self.migrator = MySQLMigrator(database)
        self.thread = None
        self.error = None
        self._cache_describe = {}
        self._cache_fks = {}
        self._cache_tablas = None
        self.Migrar()

    # -- Introspección: no repetir trabajo ya aplicado ---------------------
    # La migración corre en cada login contra un MySQL remoto. Cada ALTER /
    # SELECT es un roundtrip de red, y `alter_column_type` reconstruye la
    # tabla aunque ya esté correcta. Por eso antes de cada DDL se verifica
    # con DESCRIBE / information_schema si hace falta. Si la introspección
    # falla, se ejecuta igual (comportamiento anterior).
    def _tablas(self):
        if self._cache_tablas is None:
            try:
                self._cache_tablas = set(db.get_tables())
            except Exception:
                logging.exception("No se pudo listar tablas para la migración")
                return None
        return self._cache_tablas

    def _describe(self, tabla):
        if tabla not in self._cache_describe:
            try:
                cursor = db.execute_sql("DESCRIBE `%s`" % tabla.replace("`", "``"))
                columnas = {}
                for fila in cursor.fetchall():
                    try:
                        columnas[str(fila[0])] = {
                            "tipo": str(fila[1] or ""),
                            "null": str(fila[2] or "").upper(),
                        }
                    except (IndexError, TypeError):
                        continue
                self._cache_describe[tabla] = columnas
            except Exception as exc:
                code = exc.args[0] if getattr(exc, "args", None) else None
                if code == 1146:
                    logging.debug("Tabla %s aún no existe", tabla)
                    return None
                logging.exception("No se pudo describir tabla %s", tabla)
                return None
        return self._cache_describe.get(tabla)

    def _tiene_columna(self, tabla, columna):
        descripcion = self._describe(tabla)
        if descripcion is None:
            return False
        return columna in descripcion

    def _columna_es_int_nullable(self, tabla, columna):
        descripcion = self._describe(tabla)
        if not descripcion or columna not in descripcion:
            return False
        info = descripcion[columna]
        return info["null"] == "YES" and "int" in info["tipo"].lower()

    def _fks(self, tabla):
        if tabla not in self._cache_fks:
            try:
                cursor = db.execute_sql(
                    "SELECT COLUMN_NAME, REFERENCED_TABLE_NAME "
                    "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA = DATABASE() "
                    "AND TABLE_NAME = %s "
                    "AND REFERENCED_TABLE_NAME IS NOT NULL",
                    (tabla,),
                )
                pares = set()
                for fila in cursor.fetchall():
                    try:
                        pares.add((str(fila[0]), str(fila[1])))
                    except (IndexError, TypeError):
                        continue
                self._cache_fks[tabla] = pares
            except Exception:
                logging.exception("No se pudieron leer FKs de %s", tabla)
                return None
        return self._cache_fks.get(tabla)

    def _tiene_fk(self, tabla, columna, ref_tabla):
        fks = self._fks(tabla)
        if fks is None:
            return False
        return (columna, ref_tabla) in fks

    def _ejecutar_lote(self, ops):
        if not ops:
            return
        self.migraciones = list(ops)
        try:
            self.RealizaMigraciones()
        finally:
            self.migraciones = []
            self._cache_describe.clear()

    def MigrarVersion(self):
        inicio_total = time.monotonic()
        migrator = self.migrator

        def fase(nombre, func):
            inicio = time.monotonic()
            func()
            logging.debug("Migración [%s] %.2fs", nombre, time.monotonic() - inicio)

        fase("columnas_cliente", lambda: self._fase_columnas_cliente(migrator))
        fase("tablas_base", self._fase_tablas_base)
        fase("indices_lugares", self._quitar_unicidad_nombre_lugar_entrega)
        fase("lugar_entrega_hr", lambda: self._fase_lugar_entrega_hr(migrator))
        fase("columnas_pallet", lambda: self._fase_columnas_pallet(migrator))
        fase("backfill_pallets", self._backfill_contexto_pallets)
        fase("tremblay", self._fase_tremblay)
        fase("documentos", self._fase_documentos)
        fase("tipos_nullable", lambda: self._fase_tipos_nullable(migrator))
        fase("menu_operativo", self._fase_menu_operativo)
        fase("lugares_iniciales", self._crear_lugares_iniciales)

        logging.info(
            "Migración de base de datos completa en %.2fs",
            time.monotonic() - inicio_total,
        )

    def _fase_columnas_cliente(self, migrator):
        agregados = [
            ("cliente", "ruta_reparto_id",
             migrator.add_column("cliente", "ruta_reparto_id", self.colentero)),
            ("cliente", "localidad_id",
             migrator.add_column("cliente", "localidad_id", self.colentero)),
            ("hoja_de_ruta", "nombre_cliente",
             migrator.add_column(
                 "hoja_de_ruta", "nombre_cliente",
                 CharField(max_length=100, default=""))),
        ]
        pendientes = [
            op for tabla, columna, op in agregados
            if not self._tiene_columna(tabla, columna)
        ]
        for tabla, columna, ref, op in [
            ("cliente", "ruta_reparto_id", "rutas_reparto",
             migrator.add_foreign_key_constraint(
                 "cliente", "ruta_reparto_id", "rutas_reparto", "id",
                 on_delete="RESTRICT", on_update="CASCADE")),
            ("cliente", "localidad_id", "localidades",
             migrator.add_foreign_key_constraint(
                 "cliente", "localidad_id", "localidades", "id",
                 on_delete="RESTRICT", on_update="CASCADE")),
        ]:
            if not self._tiene_fk(tabla, columna, ref):
                pendientes.append(op)
            else:
                logging.debug("FK %s.%s -> %s ya existe, se omite",
                              tabla, columna, ref)
        self._ejecutar_lote(pendientes)

    def _fase_tablas_base(self):
        modelos = [
            (CodigoClienteProveedor, "CodigoClienteProveedor"),
            (Localidades, "Localidades"),
            (LugarEntrega, "LugarEntrega"),
            (HojaDeRuta, "HojaDeRuta"),
            (Pallet, "Pallet"),
            (PalletDetalle, "PalletDetalle"),
            (ProcesoLista, "ProcesoLista"),
            (ConceptoLiquidacion, "ConceptoLiquidacion"),
            (EstadoHojaRuta, "EstadoHojaRuta"),
        ]
        existentes = self._tablas()
        if existentes is None:
            for modelo, nombre in modelos:
                try:
                    modelo().create_table()
                except peewee.OperationalError:
                    logging.debug("Tabla %s ya existe, no se crea de nuevo", nombre)
            return
        faltantes = [
            modelo for modelo, _nombre in modelos
            if str(modelo._meta.table_name) not in existentes
        ]
        if not faltantes:
            logging.debug("Tablas base ya existen, se omite CREATE")
            return
        try:
            db.create_tables(faltantes, safe=True)
        except peewee.OperationalError:
            logging.debug("Tablas base ya existían al crearlas", exc_info=True)
        self._cache_tablas = None

    def _fase_lugar_entrega_hr(self, migrator):
        pendientes = []
        if not self._tiene_columna("hoja_de_ruta", "lugar_entrega_id"):
            pendientes.append(
                migrator.add_column(
                    "hoja_de_ruta", "lugar_entrega_id", IntegerField(null=True)))
        if not self._tiene_fk("hoja_de_ruta", "lugar_entrega_id", "lugares_entrega"):
            pendientes.append(
                migrator.add_foreign_key_constraint(
                    "hoja_de_ruta", "lugar_entrega_id", "lugares_entrega", "id",
                    on_delete="RESTRICT", on_update="CASCADE"))
        else:
            logging.debug("FK hoja_de_ruta.lugar_entrega_id ya existe, se omite")
        self._ejecutar_lote(pendientes)

    def _fase_columnas_pallet(self, migrator):
        agregados = [
            ("proveedor", "metodo_importacion",
             migrator.add_column(
                 "proveedor", "metodo_importacion",
                 CharField(max_length=30, default="COLUMNAS"))),
            ("pallet", "cargado_por",
             migrator.add_column(
                 "pallet", "cargado_por",
                 CharField(max_length=100, default=""))),
            ("pallet", "cargado_en",
             migrator.add_column("pallet", "cargado_en", DateTimeField(null=True))),
            ("pallet", "fecha_reparto",
             migrator.add_column(
                 "pallet", "fecha_reparto", peewee.DateField(null=True))),
            ("pallet", "ruta_id",
             migrator.add_column("pallet", "ruta_id", IntegerField(null=True))),
            ("pallet", "responsable_id",
             migrator.add_column(
                 "pallet", "responsable_id", IntegerField(null=True))),
            ("pallet", "equipo_id",
             migrator.add_column("pallet", "equipo_id", IntegerField(null=True))),
        ]
        pendientes = [
            op for tabla, columna, op in agregados
            if not self._tiene_columna(tabla, columna)
        ]
        if len(pendientes) < len(agregados):
            logging.debug("Columnas pallet/proveedor ya existen (%d/%d), se omiten",
                          len(agregados) - len(pendientes), len(agregados))
        self._ejecutar_lote(pendientes)

    def _fase_tremblay(self):
        try:
            (Proveedor.update(metodo_importacion="TREMBLAY")
             .where((Proveedor.id == 15)
                    & ((Proveedor.metodo_importacion != "TREMBLAY")
                       | (Proveedor.metodo_importacion.is_null(True))))
             .execute())
        except Exception:
            logging.exception("No se pudo inicializar método Tremblay para proveedor 15")

    def _fase_documentos(self):
        # documento_pedido y sus tablas hijas son aditivas (#82) y solo se
        # creaban al importar pedidos (ver Documentos.asegurar_esquema_documentos).
        # La migracion siguiente altera su cliente_id, asi que la tabla tiene que
        # existir antes: en una instalacion que nunca importo, MySQL devolvia
        # 1146 "Table 'rnd.documento_pedido' doesn't exist" y abortaba TODO el
        # arranque con "No se pudieron aplicar las migraciones".
        # safe=True no toca instalaciones que ya tienen las tablas, y el modelo
        # ya declara cliente nullable, de modo que el alter queda como no-op
        # para las nuevas y sigue corrigiendo a las viejas que lo tengan NOT NULL.
        existentes = self._tablas()
        esperadas = {"documento_pedido", "documento_pedido_detalle",
                     "documento_pedido_hoja_ruta"}
        if existentes is not None and esperadas.issubset(existentes):
            logging.debug("Tablas documento_pedido ya existen, se omite CREATE")
        else:
            asegurar_esquema_documentos()
            self._cache_tablas = None

    def _fase_tipos_nullable(self, migrator):
        # ALTER COLUMN TYPE reconstruye la tabla en MySQL aunque ya esté
        # correcta: en cada login reescribía hoja_de_ruta dos veces. Sólo se
        # ejecuta si la columna sigue NOT NULL (instalaciones viejas de #89).
        candidatos = [
            ("hoja_de_ruta", "cliente_id",
             migrator.alter_column_type(
                 "hoja_de_ruta", "cliente_id", IntegerField(null=True))),
            ("hoja_de_ruta", "ruta_id",
             migrator.alter_column_type(
                 "hoja_de_ruta", "ruta_id", IntegerField(null=True))),
            ("documento_pedido", "cliente_id",
             migrator.alter_column_type(
                 "documento_pedido", "cliente_id", IntegerField(null=True))),
        ]
        pendientes = [
            op for tabla, columna, op in candidatos
            if not self._columna_es_int_nullable(tabla, columna)
        ]
        if len(pendientes) < len(candidatos):
            logging.debug("Tipos nullable ya correctos (%d/%d), se omiten",
                          len(candidatos) - len(pendientes), len(candidatos))
        self._ejecutar_lote(pendientes)

    def _fase_menu_operativo(self):
        # La barra lateral y el menubar se alimentan de formula/menu_lateral.
        # Producción nunca recibió el seed del shell moderno (sólo el demo),
        # así que mostraba la navegación vieja con el código nuevo.
        # Aditivo: nunca borra ni desactiva filas existentes.
        try:
            asegurar_menu_operativo()
        except Exception:
            logging.exception("No se pudo asegurar el menú operativo")

    def _backfill_contexto_pallets(self):
        """Completa contexto de pallets legacy cuando puede deducirse sin ambigüedad.

        Los pallets vacíos anteriores quedan sin contexto porque no existe evidencia
        suficiente para asignarlos con seguridad. Un pallet con detalles de más de una
        carga también se conserva sin contexto y se registra en log para revisión.

        Sólo se evalúan pallets pendientes CON detalles: re-consultar los vacíos
        en cada login era N+1 queries para nada, una vez por pallet y por login.
        """
        try:
            con_detalle = PalletDetalle.select(PalletDetalle.pallet).distinct()
            pendientes = list(
                Pallet.select().where(
                    Pallet.fecha_reparto.is_null(True),
                    Pallet.id.in_(con_detalle),
                )
            )
            if not pendientes:
                logging.debug("Sin pallets pendientes de contexto, se omite backfill")
                return
            for pallet in pendientes:
                detalles = list(
                    PalletDetalle.select(PalletDetalle, HojaDeRuta)
                    .join(HojaDeRuta)
                    .where(PalletDetalle.pallet == pallet.id)
                )
                if not detalles:
                    continue
                contextos = {
                    (
                        detalle.hoja_ruta.fecha,
                        int(detalle.hoja_ruta.ruta_id or 0),
                        int(detalle.hoja_ruta.responsable_id or 0),
                        int(detalle.hoja_ruta.equipo_asignado_id or 0),
                    )
                    for detalle in detalles
                }
                if len(contextos) != 1:
                    logging.warning(
                        "Pallet legacy %s tiene más de un contexto de carga; no se migra",
                        pallet.codigo,
                    )
                    continue
                fecha_reparto, ruta_id, responsable_id, equipo_id = next(iter(contextos))
                if not (fecha_reparto and ruta_id and responsable_id and equipo_id):
                    continue
                # UPDATE directo: evita el SELECT + INSERT de auditoría que hace
                # ModeloBase.save(), innecesarios para un backfill de una vez.
                (Pallet.update(
                    fecha_reparto=fecha_reparto,
                    ruta_id=ruta_id,
                    responsable_id=responsable_id,
                    equipo_id=equipo_id,
                ).where(Pallet.id == pallet.id).execute())
        except Exception:
            logging.exception("No se pudo completar el contexto de pallets legacy")

    def _quitar_unicidad_nombre_lugar_entrega(self):
        """Migra índices de lugares: misma referencia puede tener otra dirección."""
        try:
            filas = list(db.execute_sql("SHOW INDEX FROM lugares_entrega").fetchall())
        except Exception:
            logging.exception("No se pudieron inspeccionar índices de lugares_entrega")
            return

        indices = {}
        for fila in filas:
            try:
                non_unique = int(fila[1])
                key_name = str(fila[2])
                seq = int(fila[3])
                column_name = str(fila[4])
            except (IndexError, TypeError, ValueError):
                continue
            if non_unique != 0 or key_name.upper() == "PRIMARY":
                continue
            indices.setdefault(key_name, []).append((seq, column_name))

        tiene_indice_actual = False
        for key_name, columnas in indices.items():
            ordenadas = [nombre for _seq, nombre in sorted(columnas, key=lambda item: item[0])]
            if ordenadas == ["cliente_id", "nombre", "direccion"]:
                tiene_indice_actual = True
                continue
            if ordenadas != ["cliente_id", "nombre"]:
                continue
            seguro = key_name.replace("`", "``")
            db.execute_sql("ALTER TABLE lugares_entrega DROP INDEX `{}`".format(seguro))
            logging.info("Eliminado índice legacy %s de lugares_entrega", key_name)

        if not tiene_indice_actual:
            db.execute_sql(
                "ALTER TABLE lugares_entrega ADD UNIQUE INDEX "
                "uq_lugares_entrega_cliente_nombre_direccion "
                "(cliente_id, nombre, direccion)"
            )
            logging.info("Creado índice por cliente+nombre+dirección en lugares_entrega")

    def _crear_lugares_iniciales(self):
        """Preserva dirección/ruta actuales creando un destino principal inicial."""
        try:
            # Un solo query con LEFT JOIN: en régimen ya no hay clientes sin
            # lugar y esto cuesta 1 roundtrip en vez de 1 EXISTS por cliente.
            sin_lugar = list(
                Cliente.select()
                .join(LugarEntrega, JOIN.LEFT_OUTER,
                      on=(LugarEntrega.cliente == Cliente.id))
                .where(LugarEntrega.id.is_null(True))
            )
            if not sin_lugar:
                logging.debug("Todos los clientes ya tienen lugar, se omite backfill")
                return
            for cliente in sin_lugar:
                if not (cliente.direccion or cliente.localidad_id or cliente.ruta_reparto_id):
                    continue
                nombre = "Principal"
                if cliente.localidad_id:
                    try:
                        nombre = cliente.localidad.descripcion
                    except Exception:
                        pass
                LugarEntrega.create(
                    cliente=cliente,
                    nombre=nombre,
                    direccion=cliente.direccion,
                    localidad=cliente.localidad_id,
                    ruta_reparto=cliente.ruta_reparto_id,
                    principal=True,
                    activo=True,
                )
        except Exception:
            logging.exception("No se pudieron crear los lugares de entrega iniciales")

    def RealizaMigraciones(self):
        IGNORAR = {1060, 1022, 1061, 1091}
        for m in self.migraciones:
            try:
                migrate(m)
            except Exception as e:
                code = None
                if hasattr(e, "args") and e.args:
                    code = e.args[0]
                if code in IGNORAR:
                    logging.debug("Migracion ya aplicada (mysql %s): %s", code, e)
                    continue
                ex = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
                self.Traceback = ''.join(ex)
                logging.error(self.Traceback)
                raise

    def _run_in_thread(self):
        try:
            self.MigrarVersion()
        except Exception as exc:
            self.error = exc
            logging.exception("Falló la migración de la base de datos")

    def Migrar(self):
        if not self.thread or not self.thread.is_alive():
            self.thread = threading.Thread(target=self._run_in_thread)
            self.thread.daemon = True
            self.thread.start()
        else:
            print("Ya hay una migración en curso")

    def esperar_migracion(self):
        if self.thread and self.thread.is_alive():
            self.thread.join()

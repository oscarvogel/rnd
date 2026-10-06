import logging
import sys
import traceback
import threading
import peewee

from modelos.Clientes import CodigoClienteProveedor, LugarEntrega, Cliente
from modelos.Empleados import ConceptoLiquidacion
from modelos.EstadoHojaRuta import EstadoHojaRuta
from modelos.HojaRuta import HojaDeRuta
from modelos.Pallet import Pallet, PalletDetalle
from modelos.ModeloBase import Auditoria, db
from playhouse.migrate import (
    MySQLMigrator, CharField, migrate, DecimalField, IntegerField,
    BooleanField, FloatField, TextField, TimeField, DateTimeField, DateField,
)

from modelos.Clientes import Localidades
from modelos.Proveedores import ProcesoLista, Proveedor
from pyqt5libs.pyqt5libs.utiles import LeerIni


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
        self.Migrar()

    def MigrarVersion(self):
        migrator = self.migrator
        observaciones = CharField(max_length=200, default='')
        orden_servicio = CharField(max_length=12, default='')
        self.migraciones.append(migrator.add_column('cliente', 'ruta_reparto_id', self.colentero))
        self.migraciones.append(migrator.add_foreign_key_constraint(
            'cliente', 'ruta_reparto_id', 'rutas_reparto', 'id',
            on_delete='RESTRICT', on_update='CASCADE'))
        self.migraciones.append(migrator.add_column('cliente', 'localidad_id', self.colentero))
        self.migraciones.append(migrator.add_foreign_key_constraint(
            'cliente', 'localidad_id', 'localidades', 'id',
            on_delete='RESTRICT', on_update='CASCADE'))
        self.migraciones.append(migrator.add_column(
            'hoja_de_ruta', 'nombre_cliente', CharField(max_length=100, default='')))
        self.RealizaMigraciones()

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
        for modelo, nombre in modelos:
            try:
                modelo().create_table()
            except peewee.OperationalError:
                logging.debug("Tabla %s ya existe, no se crea de nuevo", nombre)

        self._quitar_unicidad_nombre_lugar_entrega()

        self.migraciones = [
            migrator.add_column('hoja_de_ruta', 'lugar_entrega_id', IntegerField(null=True)),
            migrator.add_foreign_key_constraint(
                'hoja_de_ruta', 'lugar_entrega_id', 'lugares_entrega', 'id',
                on_delete='RESTRICT', on_update='CASCADE'),
        ]
        self.RealizaMigraciones()

        self.migraciones = [
            migrator.add_column(
                "proveedor", "metodo_importacion",
                CharField(max_length=30, default="COLUMNAS"),
            ),
            migrator.add_column(
                "pallet", "cargado_por", CharField(max_length=100, default=""),
            ),
            migrator.add_column("pallet", "cargado_en", DateTimeField(null=True)),
            migrator.add_column("pallet", "fecha_reparto", DateField(null=True)),
            migrator.add_column("pallet", "ruta_id", IntegerField(null=True)),
            migrator.add_column("pallet", "responsable_id", IntegerField(null=True)),
            migrator.add_column("pallet", "equipo_id", IntegerField(null=True)),
        ]
        self.RealizaMigraciones()
        self._backfill_contexto_pallets()

        try:
            Proveedor.update(metodo_importacion="TREMBLAY").where(Proveedor.id == 15).execute()
        except Exception:
            logging.exception("No se pudo inicializar método Tremblay para proveedor 15")

        self.migraciones = [
            migrator.alter_column_type('hoja_de_ruta', 'cliente_id', IntegerField(null=True)),
            migrator.alter_column_type('hoja_de_ruta', 'ruta_id', IntegerField(null=True)),
            migrator.alter_column_type('documento_pedido', 'cliente_id', IntegerField(null=True)),
        ]
        self.RealizaMigraciones()

        self._crear_lugares_iniciales()

    def _backfill_contexto_pallets(self):
        """Completa contexto de pallets legacy cuando puede deducirse sin ambigüedad.

        Los pallets vacíos anteriores quedan sin contexto porque no existe evidencia
        suficiente para asignarlos con seguridad. Un pallet con detalles de más de una
        carga también se conserva sin contexto y se registra en log para revisión.
        """
        try:
            pendientes = Pallet.select().where(Pallet.fecha_reparto.is_null(True))
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
                pallet.fecha_reparto = fecha_reparto
                pallet.ruta_id = ruta_id
                pallet.responsable_id = responsable_id
                pallet.equipo_id = equipo_id
                pallet.save()
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
            for cliente in Cliente.select():
                if LugarEntrega.select().where(LugarEntrega.cliente == cliente.id).exists():
                    continue
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

# coding=utf-8
import os
import unittest
from unittest.mock import patch

from peewee import MySQLDatabase, SqliteDatabase

from utiles.demo_reset import DemoResetError, _vaciar_esquema_sqlite, validar_reset_demo


class DemoResetSafetyTests(unittest.TestCase):
    def test_rechaza_fuera_de_demo(self):
        db = SqliteDatabase("sistema.db")
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("RND_DEMO_MODE", None)
            with self.assertRaises(DemoResetError):
                validar_reset_demo(db)

    def test_rechaza_mysql_aun_en_demo(self):
        db = MySQLDatabase("rnd")
        with patch.dict(os.environ, {"RND_DEMO_MODE": "1"}):
            with self.assertRaises(DemoResetError):
                validar_reset_demo(db)

    def test_rechaza_otro_archivo_sqlite(self):
        db = SqliteDatabase("produccion_local.db")
        with patch.dict(os.environ, {"RND_DEMO_MODE": "1"}):
            with self.assertRaises(DemoResetError):
                validar_reset_demo(db)

    def test_acepta_solo_sistema_db_en_demo(self):
        db = SqliteDatabase("sistema.db")
        with patch.dict(os.environ, {"RND_DEMO_MODE": "1"}):
            ruta = validar_reset_demo(db)
        self.assertEqual(ruta.name.lower(), "sistema.db")


    def test_vaciar_esquema_elimina_todas_las_tablas_no_sistema(self):
        db = SqliteDatabase(":memory:")
        db.connect()
        db.execute_sql("CREATE TABLE pedidos_demo (id INTEGER PRIMARY KEY, valor TEXT)")
        db.execute_sql("INSERT INTO pedidos_demo(valor) VALUES ('viejo')")
        db.execute_sql("CREATE TABLE otra_tabla (id INTEGER PRIMARY KEY)")
        _vaciar_esquema_sqlite(db)
        db.connect(reuse_if_open=True)
        tablas = {
            fila[0]
            for fila in db.execute_sql(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        self.assertEqual(tablas, set())
        db.close()

    unittest.main()

# coding=utf-8
import os
import unittest
from unittest.mock import patch

from peewee import MySQLDatabase, SqliteDatabase

from utiles.demo_reset import DemoResetError, validar_reset_demo


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


if __name__ == "__main__":
    unittest.main()

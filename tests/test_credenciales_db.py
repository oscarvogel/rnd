# coding=utf-8
"""Regression test para el RecursionError de la conexion a la DB.

El commit 35bafc8 hizo que RecycledMySQLDatabase.connect() llamara a
connect_with_credentials_dialog(), que a su vez llamaba a db.connect() y
re-entraba al mismo override -> recursion infinita -> la app crasheaba en
silencio al arrancar (solo quedaba un rnd_crash.log).

Aca se verifica que el dialog conecta por el metodo base de peewee, aplica
las credenciales nuevas al objeto db (db.init) y NO recursea.
"""
import os
import sys
import types
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# --- Fakes para no importar el arbol completo bajo pytest. ---------------
# `controladores/__init__.py` importa TODOS los controladores (Main, Login,
# etc.) y `mongoengine` tarda ~6s en importar; ambos rompen/ralentizan la
# suite. Al meter los modulos en sys.modules, el `from controladores.
# ConfiguracionDB import pedir_credenciales_db` interno resuelve contra el
# fake sin disparar el __init__ del paquete.
_fake_ctrl = types.ModuleType("controladores")
_fake_ctrl.__path__ = []
_fake_cdb = types.ModuleType("controladores.ConfiguracionDB")
_fake_cdb.pedir_credenciales_db = None
_fake_mongo = types.ModuleType("mongoengine")
_fake_mongo.Document = object
_fake_mongo.DynamicDocument = object
_fake_mongo.connect = lambda *a, **k: None
for _name, _mod in [
    ("controladores", _fake_ctrl),
    ("controladores.ConfiguracionDB", _fake_cdb),
    ("mongoengine", _fake_mongo),
]:
    sys.modules.setdefault(_name, _mod)

import peewee
from peewee import OperationalError

import PyQt5.QtWidgets as QtWidgets

import modelos.ModeloBase as modelo_base


class _FakeDB:
    def __init__(self):
        self.init_calls = []
        self.connect_calls = []
        self._connected_at = 0.0

    def init(self, **kwargs):
        self.init_calls.append(kwargs)


CREDENCIALES_VALIDAS = {
    "host": "db.example.com",
    "port": "3306",
    "user": "rnd_app",
    "password": "nueva-clave",
    "basedatos": "rnd",
    "recordar": True,
}


class CredencialesDBTests(unittest.TestCase):
    def setUp(self):
        self.fake_db = _FakeDB()
        patcher_db = mock.patch.object(modelo_base, "db", self.fake_db)
        patcher_db.start()
        self.addCleanup(patcher_db.stop)

        def fake_base_connect(self, *args, **kwargs):
            self.connect_calls.append((args, kwargs))
            if len(self.connect_calls) == 1:
                raise OperationalError(1045, "Access denied")
            return None

        patcher_conn = mock.patch.object(peewee.Database, "connect", fake_base_connect)
        patcher_conn.start()
        self.addCleanup(patcher_conn.stop)

        patcher_dialog = mock.patch.object(
            _fake_cdb,
            "pedir_credenciales_db",
            return_value=CREDENCIALES_VALIDAS,
        )
        patcher_dialog.start()
        self.addCleanup(patcher_dialog.stop)

        # Sin QApplication el dialog no se puede mostrar (abortaria el
        # proceso); para probar el flujo completo simulamos una app activa.
        patcher_app = mock.patch.object(
            QtWidgets.QApplication, "instance", return_value=mock.Mock()
        )
        patcher_app.start()
        self.addCleanup(patcher_app.stop)

    def test_no_recursion_y_aplica_credenciales_nuevas(self):
        ok = modelo_base.connect_with_credentials_dialog(max_attempts=3)
        self.assertTrue(ok)
        # 1er connect falla con 1045, 2do (con la clave nueva) funciona.
        self.assertEqual(len(self.fake_db.connect_calls), 2)
        self.assertTrue(self.fake_db.init_calls, "db.init() deberia haberse llamado")
        self.assertEqual(self.fake_db.init_calls[-1]["password"], "nueva-clave")
        self.assertEqual(self.fake_db.init_calls[-1]["host"], "db.example.com")

    def test_cancelar_dialog_devuelve_false(self):
        with mock.patch.object(_fake_cdb, "pedir_credenciales_db", return_value=None):
            ok = modelo_base.connect_with_credentials_dialog(max_attempts=3)
        self.assertFalse(ok)

    def test_sin_qapplication_no_crash_y_devuelve_false(self):
        with mock.patch.object(QtWidgets.QApplication, "instance", return_value=None):
            ok = modelo_base.connect_with_credentials_dialog(max_attempts=3)
        self.assertFalse(ok)
        self.assertEqual(len(self.fake_db.connect_calls), 0)

    def test_aplicar_credenciales_no_toca_db_sqlite(self):
        class _FakeSqlite:
            def init(self, **kwargs):
                raise AssertionError("init() no deberia llamarse para sqlite")

        fake_db = _FakeSqlite()
        with mock.patch.object(modelo_base, "SqliteDatabase", _FakeSqlite), mock.patch.object(
            modelo_base, "db", fake_db
        ):
            modelo_base.aplicar_credenciales_db(CREDENCIALES_VALIDAS)

    # --- Regresiones issue #11 / DB_PASSWORD --------------------------------
    # La password ahora se lee con prioridad: RND_DB_PASSWORD > sistema.ini >
    # QSettings > MYSQL_PASSWORD. Todos los tests aislan el sistema.ini local
    # (LeerIni -> "") para probar la cadena de env/QSettings de forma
    # deterministica; la fuente ini tiene su propio test dedicado.
    def test_mysql_password_ignora_env_generica_db_password(self):
        """DB_PASSWORD (generica, comun en maquinas reales con la clave de
        OTRO proyecto) NO debe ganar sobre la clave persistida en QSettings.
        """
        env = {
            "RND_DB_PASSWORD": "",
            "MYSQL_PASSWORD": "",
            "DB_PASSWORD": "clave-de-otro-proyecto",
        }
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            modelo_base, "_persisted_password", return_value="clave-correcta"
        ), mock.patch.object(modelo_base, "LeerIni", return_value=""):
            self.assertEqual(modelo_base._mysql_password(), "clave-correcta")

    def test_mysql_password_prioriza_env_explicita_sobre_qsettings(self):
        env = {"RND_DB_PASSWORD": "clave-env", "MYSQL_PASSWORD": "", "DB_PASSWORD": "otra"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            modelo_base, "_persisted_password", return_value="clave-qsettings"
        ), mock.patch.object(modelo_base, "LeerIni", return_value="clave-ini"):
            self.assertEqual(modelo_base._mysql_password(), "clave-env")

    def test_mysql_password_prioriza_qsettings_sobre_env_generica(self):
        """Regresion issue #11: la clave que el usuario ingresa en el dialog
        y persiste en QSettings DEBE ganar sobre la env var generica
        MYSQL_PASSWORD (que en maquinas reales suele estar seteada con la
        clave de otro proyecto). Sin esto RND pide la clave en cada arranque
        porque la generica pisa la persistida."""
        env = {"RND_DB_PASSWORD": "", "MYSQL_PASSWORD": "clave-de-otro-proyecto", "DB_PASSWORD": "otra"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            modelo_base, "_persisted_password", return_value="clave-correcta"
        ), mock.patch.object(modelo_base, "LeerIni", return_value=""):
            self.assertEqual(modelo_base._mysql_password(), "clave-correcta")

    def test_mysql_password_usa_env_generica_solo_sin_persistida(self):
        """MYSQL_PASSWORD solo como ultimo recurso, si no hay nada persistido."""
        env = {"RND_DB_PASSWORD": "", "MYSQL_PASSWORD": "clave-generica", "DB_PASSWORD": "otra"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            modelo_base, "_persisted_password", return_value=""
        ), mock.patch.object(modelo_base, "LeerIni", return_value=""):
            self.assertEqual(modelo_base._mysql_password(), "clave-generica")

    def test_mysql_password_vacia_sin_env_ni_qsettings(self):
        env = {"RND_DB_PASSWORD": "", "MYSQL_PASSWORD": "", "DB_PASSWORD": "otra"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            modelo_base, "_persisted_password", return_value=""
        ), mock.patch.object(modelo_base, "LeerIni", return_value=""):
            self.assertEqual(modelo_base._mysql_password(), "")

    def test_mysql_password_usa_ini_como_fuente_canonica(self):
        """sistema.ini -> password= es la fuente canonica (editable por el
        operador, no depende de env vars ni del registro). Debe ganar sobre
        QSettings y sobre MYSQL_PASSWORD, pero perder frente a
        RND_DB_PASSWORD."""
        env = {"RND_DB_PASSWORD": "", "MYSQL_PASSWORD": "clave-generica", "DB_PASSWORD": "otra"}
        with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(
            modelo_base, "_persisted_password", return_value="clave-qsettings"
        ), mock.patch.object(modelo_base, "LeerIni", return_value="clave-ini"):
            self.assertEqual(modelo_base._mysql_password(), "clave-ini")

    def test_persisted_password_lee_leerconf_no_leerini(self):
        """_persisted_password() debe leer de QSettings (LeerConf), no del
        sistema.ini (LeerIni), que es donde la persistencia del dialog no
        escribe."""
        with mock.patch.object(modelo_base, "LeerConf", return_value="clave-qsettings"), mock.patch.object(
            modelo_base, "LeerIni", return_value="clave-ini"
        ):
            self.assertEqual(modelo_base._persisted_password(), "clave-qsettings")


if __name__ == "__main__":
    unittest.main()

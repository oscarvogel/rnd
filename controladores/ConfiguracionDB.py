# coding=utf-8
"""Controller para pedir y persistir credenciales de la DB.

Flujo:
  1. Lee la config actual (sistema.ini + QSettings + env var).
  2. Muestra el dialog ConfiguracionDBView con los valores pre-llenados.
  3. Si el usuario acepta, persiste (QSettings + env var) y devuelve
     la config nueva. Si cancela, devuelve None.

Decisiones de diseno:
  - La clave se guarda en QSettings (registry de Windows, user scope).
    Esto la hace accesible a RND sin requerir env var en cada shell.
  - Tambien se setea como env var en el proceso actual para que la
    conexion pymysql inmediata la encuentre. No se persiste la env var
    a nivel de sistema (eso queda a criterio del operador si quiere
    usar SetEnvironmentVariable con scope 'User').
  - Si el usuario desmarca "Recordar", la config NO se persiste; solo
    queda en memoria para esta corrida.
"""
import os

from pyqt5libs.pyqt5libs.utiles import GrabaConf, LeerIni

from vistas.ConfiguracionDB import ConfiguracionDBView


def _leer_config_actual(carpeta):
    """Lee host/user/port/basedatos del ini y password de env var o QSettings."""
    host = LeerIni("host", carpeta=carpeta) or ""
    user = LeerIni("user", carpeta=carpeta) or ""
    basedatos = LeerIni("basedatos", carpeta=carpeta) or "rnd"
    port = LeerIni("port", carpeta=carpeta) or "3306"
    # Password: env var primero, despues QSettings.
    password = (
        os.getenv("RND_DB_PASSWORD")
        or os.getenv("MYSQL_PASSWORD")
        or LeerIni("password", carpeta=carpeta)
        or ""
    )
    return {
        "host": host,
        "user": user,
        "basedatos": basedatos,
        "port": port,
        "password": password,
    }


def _persistir_config(config, carpeta):
    """Persiste la config nueva en QSettings y en el env var del proceso.

    No se sobreescribe el sistema.ini (es el default). Solo se actualiza
    la persistencia (QSettings) que tiene precedencia via LeerIni.
    """
    # Persistir en QSettings
    GrabaConf(clave="host", valor=config["host"], carpeta=carpeta)
    GrabaConf(clave="user", valor=config["user"], carpeta=carpeta)
    GrabaConf(clave="basedatos", valor=config["basedatos"], carpeta=carpeta)
    GrabaConf(clave="port", valor=str(config["port"]), carpeta=carpeta)
    GrabaConf(clave="password", valor=config["password"], carpeta=carpeta)
    # Tambien setear en el env var del proceso para que la conexion
    # pymysql inmediata (que lee _mysql_password()) la encuentre.
    os.environ["RND_DB_PASSWORD"] = config["password"]


def pedir_credenciales_db(parent=None, carpeta=None, mensaje=None):
    """Muestra el dialog de credenciales y devuelve la config nueva (dict) o None.

    Args:
        parent: widget padre para que el dialog sea modal.
        carpeta: carpeta de inicio donde esta sistema.ini.
        mensaje: texto a mostrar arriba (ej. "No se pudo conectar. Verifica los datos.").

    Returns:
        dict con la nueva config ('host', 'port', 'user', 'password', 'basedatos',
        'recordar') o None si el usuario cancelo.
    """
    carpeta = carpeta or os.getcwd()
    config_actual = _leer_config_actual(carpeta)

    dialog = ConfiguracionDBView(
        config_actual=config_actual,
        mensaje=mensaje,
        parent=parent,
    )
    if dialog.exec_() != dialog.Accepted:
        return None

    config = dialog.get_config()
    if config and config.get("recordar"):
        _persistir_config(config, carpeta)
    return config

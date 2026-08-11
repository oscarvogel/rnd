# coding=utf-8
"""Controller para pedir y persistir credenciales de la DB.

Flujo:
  1. Lee la config actual (sistema.ini + QSettings + env var).
  2. Muestra el dialog ConfiguracionDBView con los valores pre-llenados.
  3. Si el usuario acepta, persiste (QSettings + env var + sistema.ini) y
     devuelve la config nueva. Si cancela, devuelve None.

Decisiones de diseno:
  - La clave se guarda en QSettings (registry de Windows, user scope)
    Y en el sistema.ini activo (clave `password` en [param]). El ini es la
    fuente canonica y la que sobrevive reinstalaciones (el instalador usa
    onlyifdoesntexist) y la que el operador puede editar a mano sin saber
    de registros ni env vars. _mysql_password() la lee con LeerIni().
  - Tambien se setea como env var en el proceso actual para que la
    conexion pymysql inmediata la encuentre. No se persiste la env var
    a nivel de sistema (eso queda a criterio del operador si quiere
    usar SetEnvironmentVariable con scope 'User').
  - Si el usuario desmarca "Recordar", la config NO se persiste; solo
    queda en memoria para esta corrida.
"""
import configparser
import os

from pyqt5libs.pyqt5libs.utiles import GrabaConf, LeerConf, LeerIni, resolver_configuracion_activa

from vistas.ConfiguracionDB import ConfiguracionDBView


def _persistir_ini(seccion, clave, valor):
    """Escribe `clave = valor` en la seccion `seccion` del ini activo.

    El ini activo es el que resuelve resolver_configuracion_activa()
    (por defecto sistema.ini en la carpeta de inicio). Conserva el resto
    del archivo intacto (comentarios, otras claves).
    """
    try:
        ruta = resolver_configuracion_activa()["ruta"]
        if not ruta or not os.path.isfile(ruta):
            return
        config = configparser.ConfigParser()
        config.read(ruta, encoding="utf-8")
        if not config.has_section(seccion):
            config.add_section(seccion)
        config.set(seccion, clave, str(valor))
        with open(ruta, "w", encoding="utf-8") as fh:
            config.write(fh)
    except Exception:
        # Si falla la escritura del ini no debemos romper el flujo del dialog.
        pass



def _leer_config_actual(carpeta):
    """Lee host/user/port/basedatos del ini y password de env var o QSettings."""
    host = LeerIni("host", carpeta=carpeta) or ""
    user = LeerIni("user", carpeta=carpeta) or ""
    basedatos = LeerIni("basedatos", carpeta=carpeta) or "rnd"
    port = LeerIni("port", carpeta=carpeta) or "3306"
    # Password: env var primero, despues QSettings (la persistencia que
    # escribe GrabaConf) y por ultimo el ini como fallback.
    password = (
        os.getenv("RND_DB_PASSWORD")
        or os.getenv("MYSQL_PASSWORD")
        or LeerConf("password")
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
    la persistencia (QSettings) que tiene precedencia via LeerConf/LeerIni.

    OJO: GrabaConf(clave, valor, sistema=None) tiene el tercer parametro
    `sistema`, NO `carpeta`. Pasar `carpeta` aca escribia la clave en
    QSettings("Servin LGSM", "<ruta>") en vez de QSettings("Servin LGSM",
    "Sistema"), y nunca la leia nadie -> la clave se perdia en cada corrida.
    """
    # Persistir en QSettings
    GrabaConf(clave="host", valor=config["host"])
    GrabaConf(clave="user", valor=config["user"])
    GrabaConf(clave="basedatos", valor=config["basedatos"])
    GrabaConf(clave="port", valor=str(config["port"]))
    GrabaConf(clave="password", valor=config["password"])
    # Persistir en el sistema.ini activo (fuente canonica: sobrevive
    # reinstalaciones y es editable a mano).
    _persistir_ini("param", "host", config["host"])
    _persistir_ini("param", "user", config["user"])
    _persistir_ini("param", "basedatos", config["basedatos"])
    _persistir_ini("param", "port", config["port"])
    _persistir_ini("param", "password", config["password"])
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

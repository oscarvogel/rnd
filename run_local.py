# coding=utf-8
"""Launcher exclusivo para desarrollo local de RND.

Produccion sigue arrancando con ``python main.py`` y usa ``sistema.ini``.
Este launcher fuerza un INI y una credencial DPAPI independientes.
"""

import configparser
import os
import shutil
import socket
import sys
from pathlib import Path


LOCAL_PROFILE = "local"
LOCAL_INI = "sistema.local.ini"
LOCAL_TEMPLATE = "sistema.local.ini.example"


def _prepare_local_config(base_dir: Path) -> bool:
    target = base_dir / LOCAL_INI
    if target.exists():
        return True

    template = base_dir / LOCAL_TEMPLATE
    if not template.exists():
        print("ERROR: falta {}.".format(template), file=sys.stderr)
        return False

    shutil.copyfile(str(template), str(target))
    print("Se creo {} desde la plantilla.".format(target))
    print("Revise host, base de datos y usuario y vuelva a ejecutar python run_local.py.")
    return False


def _read_connection(base_dir: Path):
    ini_path = base_dir / LOCAL_INI
    config = configparser.ConfigParser()
    if not config.read(str(ini_path), encoding="utf-8") or not config.has_section("param"):
        raise RuntimeError("No se pudo leer {}".format(ini_path))

    host = config.get("param", "host", fallback="").strip()
    database = config.get("param", "basedatos", fallback="").strip()
    user = config.get("param", "user", fallback="").strip()
    port = config.getint("param", "port", fallback=3306)
    return host, port, database, user


def _mysql_port_available(host: str, port: int, timeout: float = 1.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _print_connection_diagnostic(base_dir: Path) -> bool:
    try:
        host, port, database, user = _read_connection(base_dir)
    except Exception as exc:
        print("ERROR DE CONFIGURACION LOCAL: {}".format(exc), file=sys.stderr)
        return False

    print("MySQL local configurado: {}:{} / base={} / usuario={}".format(
        host, port, database, user
    ))

    if not host or not database or not user:
        print("ERROR: sistema.local.ini no tiene host, basedatos o user validos.", file=sys.stderr)
        return False

    if not _mysql_port_available(host, port):
        print("", file=sys.stderr)
        print("ERROR: no hay un servidor MySQL accesible en {}:{}.".format(host, port), file=sys.stderr)
        print("RND LOCAL necesita una instancia MySQL local o un servidor de desarrollo configurado en sistema.local.ini.", file=sys.stderr)
        print("Esto NO intenta ni hace fallback a PRODUCCION.", file=sys.stderr)
        print("", file=sys.stderr)
        print("En Windows puede verificarlo con:", file=sys.stderr)
        print("  Test-NetConnection {} -Port {}".format(host, port), file=sys.stderr)
        print("", file=sys.stderr)
        print("Si su MySQL local usa otro host/puerto, edite:", file=sys.stderr)
        print("  {}".format(base_dir / LOCAL_INI), file=sys.stderr)
        return False

    print("Pre-chequeo de red MySQL: OK")
    return True


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    if not _prepare_local_config(base_dir):
        return 2

    # Aisla la credencial local de la credencial historica de produccion.
    os.environ["RND_CREDENTIAL_PROFILE"] = LOCAL_PROFILE
    os.environ["RND_ENV"] = "local"

    print("=" * 66)
    print("RND - ENTORNO LOCAL / DESARROLLO")
    print("Configuracion: {}".format(base_dir / LOCAL_INI))
    print("La configuracion y credencial de PRODUCCION no se modifican.")
    print("=" * 66)

    if not _print_connection_diagnostic(base_dir):
        return 3

    import main as rnd_main

    return rnd_main.inicio(["-i", str(base_dir), "-a", LOCAL_INI])


if __name__ == "__main__":
    sys.exit(main())

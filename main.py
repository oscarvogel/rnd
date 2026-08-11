# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

#Punto de Inicio del sistema
import argparse
import configparser
import logging
import os
import subprocess
import sys
from pathlib import Path

from pyqt5libs.pyqt5libs.utiles import BorrarConf, GrabaConf, LeerIni, initialize_logger
from rnd_credentials import (
    AuthenticationRejected,
    ConnectionUnavailable,
    CredentialError,
    MySQLSettings,
    resolve_mysql_password,
    save_machine_password,
    save_mysql_settings,
    validate_mysql_connection,
)

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2026"
__license__ = "GPL 3.0"
__version__ = "2026.8.11.1"

WINDOWS_APP_USER_MODEL_ID = "VogelConsultoria.RND"

CREDENTIAL_CONFIGURED = 0
CREDENTIAL_CANCELLED = 2
CREDENTIAL_CONFIGURATION_FAILED = 3


def _set_windows_app_id(setter=None, platform=None):
    current_platform = sys.platform if platform is None else platform
    if current_platform != "win32":
        return False
    if setter is None:
        import ctypes

        setter = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID
    try:
        return setter(WINDOWS_APP_USER_MODEL_ID) == 0
    except Exception:
        logging.warning("No se pudo establecer la identidad de RND en Windows.")
        return False

def _build_arg_parser():
    analizador = argparse.ArgumentParser(description='Sistema.')
    analizador.add_argument("-i", "--inicio", default=os.getcwd(), help="Carpeta de Inicio de sistema.")
    analizador.add_argument("-a", "--archivo", default="sistema.ini", help="Archivo de Configuracion de sistema.")
    analizador.add_argument(
        "--startup-check",
        action="store_true",
        help="Valida configuracion y recursos sin abrir la interfaz.",
    )
    analizador.add_argument(
        "--configure-db-credential",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    analizador.add_argument(
        "--edit-db-connection",
        action="store_true",
        help="Abre la configuración de conexión MySQL de RND.",
    )
    return analizador


def _load_mysql_settings(inicio, archivo):
    ini_path = Path(inicio).resolve() / archivo
    config = configparser.ConfigParser()
    if not config.read(ini_path, encoding="utf-8") or not config.has_section("param"):
        raise ValueError("No se pudo leer la configuración MySQL de RND.")

    host = config.get("param", "host", fallback="").strip()
    database = config.get("param", "basedatos", fallback="").strip()
    user = config.get("param", "user", fallback="").strip()
    port_value = config.get("param", "port", fallback="3306").strip()
    if not host or not database or not user:
        raise ValueError("Faltan parámetros de conexión MySQL requeridos.")
    try:
        port = int(port_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("El puerto MySQL configurado no es válido.") from exc

    return MySQLSettings(host=host, port=port, database=database, user=user)


def _credential_configuration_command(
    inicio,
    archivo,
    *,
    frozen=None,
    executable=None,
    script_path=None,
):
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    executable = executable or sys.executable
    script_path = script_path or str(Path(__file__).resolve())
    arguments = [] if is_frozen else [script_path]
    arguments.extend(
        ["--configure-db-credential", "-i", str(inicio), "-a", str(archivo)]
    )
    return executable, subprocess.list2cmdline(arguments)


def _launch_elevated_credential_configurator(inicio, archivo):
    from win32com.shell import shell, shellcon
    import win32api
    import win32con
    import win32event
    import win32process

    executable, parameters = _credential_configuration_command(inicio, archivo)
    try:
        process_info = shell.ShellExecuteEx(
            fMask=shellcon.SEE_MASK_NOCLOSEPROCESS,
            lpVerb="runas",
            lpFile=executable,
            lpParameters=parameters,
            lpDirectory=str(Path(inicio).resolve()),
            nShow=win32con.SW_SHOWNORMAL,
        )
    except Exception as exc:
        if getattr(exc, "winerror", None) == 1223:
            return CREDENTIAL_CANCELLED
        return CREDENTIAL_CONFIGURATION_FAILED

    handle = process_info["hProcess"]
    try:
        win32event.WaitForSingleObject(handle, win32event.INFINITE)
        return win32process.GetExitCodeProcess(handle)
    finally:
        win32api.CloseHandle(handle)


def _ensure_mysql_credential(
    inicio,
    archivo,
    *,
    resolver=resolve_mysql_password,
    launcher=_launch_elevated_credential_configurator,
    settings_loader=_load_mysql_settings,
    validator=validate_mysql_connection,
):
    def configure_and_resolve():
        if launcher(inicio, archivo) != CREDENTIAL_CONFIGURED:
            return None
        try:
            return resolver()
        except CredentialError:
            return None

    try:
        password = resolver()
    except CredentialError:
        password = configure_and_resolve()

    if password is None:
        return False

    settings = settings_loader(inicio, archivo)
    try:
        validator(settings, password)
    except AuthenticationRejected:
        password = configure_and_resolve()
        if password is None:
            return False
        settings = settings_loader(inicio, archivo)
        try:
            validator(settings, password)
        except AuthenticationRejected:
            return False
    return True


def _save_connection_configuration(settings, password, ini_path):
    target = Path(ini_path)
    original = target.read_bytes()
    save_mysql_settings(settings, target)
    try:
        save_machine_password(password)
    except Exception:
        temporary = target.with_suffix(target.suffix + ".rollback")
        try:
            temporary.write_bytes(original)
            os.replace(str(temporary), str(target))
        finally:
            temporary.unlink(missing_ok=True)
        raise


def _run_credential_dialog(settings, ini_path, dialog_factory=None):
    if dialog_factory is None:
        from vistas.ConfigurarCredencialDB import CredentialDialog

        dialog_factory = CredentialDialog
    dialog = dialog_factory(
        settings,
        saver=lambda candidate, password: _save_connection_configuration(
            candidate, password, ini_path
        ),
    )
    if dialog.exec_():
        return CREDENTIAL_CONFIGURED
    return CREDENTIAL_CANCELLED


def _validate_startup(inicio, archivo):
    carpeta_inicio = Path(inicio).resolve()
    archivo_ini = carpeta_inicio / archivo
    required_paths = [
        archivo_ini,
        carpeta_inicio / "imagenes",
        carpeta_inicio / "temas",
        carpeta_inicio / "sistema.ini",
        carpeta_inicio / "rnd.ini",
    ]
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        return False, "faltan recursos requeridos: {}".format(", ".join(missing))

    config = configparser.ConfigParser()
    if not config.read(archivo_ini, encoding="utf-8"):
        return False, "no se pudo leer {}".format(archivo_ini)
    if not config.has_section("param"):
        return False, "{} no tiene la seccion [param]".format(archivo_ini)

    required_keys = ["host", "basedatos", "port", "icono", "logo", "iniciosistema"]
    missing_keys = [
        key for key in required_keys
        if not config.get("param", key, fallback="").strip()
    ]
    if missing_keys:
        return False, "{} no tiene parametros requeridos: {}".format(
            archivo_ini,
            ", ".join(missing_keys),
        )

    media_paths = [
        carpeta_inicio / "imagenes" / config.get("param", "icono"),
        carpeta_inicio / "imagenes" / config.get("param", "logo"),
    ]
    missing_media = [str(path) for path in media_paths if not path.exists()]
    if missing_media:
        return False, "faltan archivos de marca: {}".format(", ".join(missing_media))

    return True, "inicio={} archivo={}".format(carpeta_inicio, archivo_ini)


def inicio(argv=None):
    _set_windows_app_id()
    BorrarConf()
    argumento = _build_arg_parser().parse_args(argv)
    carpeta = argumento.inicio + "\\"
    GrabaConf(clave="iniciosistema", valor=carpeta)
    GrabaConf(clave="archivoini", valor=argumento.archivo)

    if argumento.startup_check:
        ok, message = _validate_startup(argumento.inicio, argumento.archivo)
        if ok:
            print("STARTUP_CHECK_OK {}".format(message))
            return 0
        print("STARTUP_CHECK_ERROR {}".format(message), file=sys.stderr)
        return 1

    from PyQt5.QtWidgets import QApplication, QMessageBox
    from pyqt5libs.pyqt5libs.utiles import icono_sistema

    # print("PATH del archivo {}".format(sys.argv[1]))

    # carpeta, archivo = os.path.split(os.path.abspath(__file__))
    # print(len(sys.argv))
    # if len(sys.argv) > 1:
    #     carpeta = sys.argv[1] + "\\"
    #     GrabaConf(clave="iniciosistema", valor=sys.argv[1] + "\\")
    # else:
    #     carpeta = ""
    initialize_logger(LeerIni("iniciosistema", carpeta=carpeta))
    logging.basicConfig()
    logging.debug("carpeta inicio{} archivo de inicio {}".format(argumento.inicio, argumento.archivo))
    print("carpeta inicio{} archivo de inicio {}".format(argumento.inicio, argumento.archivo))
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    sys.path.insert(0, LeerIni("iniciosistema", carpeta=carpeta))
    # if len(sys.argv) > 1:
    #     logging.debug("inicio de sistema {}".format(sys.argv[1]))
    GrabaConf(clave="DEBUG", valor=True)
    GrabaConf(clave="Reconecta", valor=True)
    GrabaConf(clave="usuario", valor=os.getenv("RND_DB_USER", LeerIni("user") or ""))
    # ModeloBase().init()
    args = []
    #args = ['', '-style', 'Cleanlooks']
    # myStyle = MyProxyStyle('Fusion')
    app = QApplication(args)
    app.setWindowIcon(icono_sistema())

    if argumento.edit_db_connection:
        result = _launch_elevated_credential_configurator(
            argumento.inicio,
            argumento.archivo,
        )
        if result == CREDENTIAL_CONFIGURATION_FAILED:
            QMessageBox.critical(
                None,
                "RND",
                "No se pudo abrir la configuración de conexión MySQL.",
            )
        return result

    if argumento.configure_db_credential:
        try:
            settings = _load_mysql_settings(argumento.inicio, argumento.archivo)
            ini_path = Path(argumento.inicio).resolve() / argumento.archivo
            return _run_credential_dialog(settings, ini_path)
        except (CredentialError, ValueError):
            QMessageBox.critical(
                None,
                "RND",
                "No se pudo configurar la credencial MySQL de RND.",
            )
            return CREDENTIAL_CONFIGURATION_FAILED

    try:
        credential_ready = _ensure_mysql_credential(
            argumento.inicio,
            argumento.archivo,
        )
    except ConnectionUnavailable:
        QMessageBox.critical(
            None,
            "RND",
            "No se pudo conectar con el servidor MySQL. Verifique la red y vuelva a intentar.",
        )
        return 1

    if not credential_ready:
        QMessageBox.information(
            None,
            "RND",
            "La credencial MySQL de RND no quedó configurada.",
        )
        return 0
    # app.setStyle(myStyle)

    # Tema QSS global (issue #5). Se aplica a nivel de aplicacion para
    # que la ventana principal, formularios, grillas y dialogos compartan
    # el mismo lenguaje visual. Si el QSS no esta disponible, la app
    # arranca con el estilo default de Qt (fallback seguro).
    from utiles.tema import aplicar_tema
    aplicar_tema(app)

    from controladores.Main import MainController

    ex = MainController()
    # ex.view.ImagenFondo()
    if ex.login():
        ex.run()
        return app.exec_()
    return 0

if __name__ == "__main__":
    import traceback

    try:
        sys.exit(inicio())
    except SystemExit:
        raise
    except BaseException as exc:
        log_path = os.path.join(os.getcwd(), "rnd_crash.log")
        with open(log_path, "w", encoding="utf-8") as log_file:
            log_file.write(
                "Excepcion no capturada: {}: {}\n\n".format(
                    type(exc).__name__, exc
                )
            )
            log_file.write(traceback.format_exc())
        print("CRASH: {}: {}".format(type(exc).__name__, exc), file=sys.stderr)
        print("Log escrito en: {}".format(log_path), file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

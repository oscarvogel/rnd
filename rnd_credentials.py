"""Almacenamiento seguro y compartido de la credencial MySQL de RND."""

import configparser
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping, Optional

import pymysql
import win32crypt


CREDENTIAL_DESCRIPTION = "RND MySQL"
CREDENTIAL_FILENAME = "mysql.credential"
CRYPTPROTECT_UI_FORBIDDEN = 0x1
CRYPTPROTECT_LOCAL_MACHINE = 0x4


class CredentialError(RuntimeError):
    """Error seguro para mostrar al usuario sin filtrar secretos."""


class CredentialMissing(CredentialError):
    def __init__(self):
        super().__init__("No hay una credencial MySQL configurada para RND.")


class CredentialCorrupt(CredentialError):
    def __init__(self):
        super().__init__("La credencial MySQL guardada no se pudo leer.")


class CredentialWriteError(CredentialError):
    def __init__(self):
        super().__init__("La credencial MySQL no se pudo guardar.")


class SettingsWriteError(CredentialError):
    def __init__(self):
        super().__init__("Los datos de conexión MySQL no se pudieron guardar.")


class AuthenticationRejected(CredentialError):
    def __init__(self):
        super().__init__("MySQL rechazó el usuario o la contraseña de RND.")


class ConnectionUnavailable(CredentialError):
    def __init__(self):
        super().__init__("No se pudo establecer la conexión con el servidor MySQL.")


@dataclass(frozen=True)
class MySQLSettings:
    host: str
    port: int
    database: str
    user: str


def _validate_settings(settings: MySQLSettings) -> None:
    if (
        not settings.host.strip()
        or not settings.database.strip()
        or not settings.user.strip()
        or not isinstance(settings.port, int)
        or not 1 <= settings.port <= 65535
    ):
        raise SettingsWriteError()


def save_mysql_settings(settings: MySQLSettings, ini_path: Path) -> None:
    """Guarda metadatos no secretos sin reemplazar las demás claves del INI."""
    _validate_settings(settings)
    target = Path(ini_path)
    temporary = target.with_suffix(target.suffix + ".tmp")
    config = configparser.ConfigParser(strict=False)

    try:
        if not config.read(target, encoding="utf-8"):
            raise OSError("missing INI")
        if not config.has_section("param"):
            raise configparser.NoSectionError("param")

        config.set("param", "host", settings.host.strip())
        config.set("param", "port", str(settings.port))
        config.set("param", "basedatos", settings.database.strip())
        config.set("param", "user", settings.user.strip())
        config.remove_option("param", "password")

        with temporary.open("w", encoding="utf-8", newline="") as output:
            config.write(output)
        os.replace(str(temporary), str(target))
    except SettingsWriteError:
        raise
    except Exception as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise SettingsWriteError() from exc


def credential_path(environ: Optional[Mapping[str, str]] = None) -> Path:
    environment = os.environ if environ is None else environ
    program_data = environment.get("ProgramData") or r"C:\ProgramData"
    return Path(program_data) / "RND" / CREDENTIAL_FILENAME


def save_machine_password(password: str, path: Optional[Path] = None) -> None:
    if not password:
        raise CredentialWriteError()

    target = Path(path) if path is not None else credential_path()
    temporary = target.with_suffix(target.suffix + ".tmp")
    flags = CRYPTPROTECT_LOCAL_MACHINE | CRYPTPROTECT_UI_FORBIDDEN

    try:
        encrypted = win32crypt.CryptProtectData(
            password.encode("utf-8"),
            CREDENTIAL_DESCRIPTION,
            None,
            None,
            None,
            flags,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(encrypted)
        os.replace(str(temporary), str(target))
    except Exception as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        raise CredentialWriteError() from exc


def load_machine_password(path: Optional[Path] = None) -> str:
    target = Path(path) if path is not None else credential_path()
    if not target.is_file():
        raise CredentialMissing()

    try:
        encrypted = target.read_bytes()
        _description, clear = win32crypt.CryptUnprotectData(
            encrypted, None, None, None, CRYPTPROTECT_UI_FORBIDDEN
        )
        password = clear.decode("utf-8")
        if not password:
            raise ValueError("empty credential")
        return password
    except Exception as exc:
        raise CredentialCorrupt() from exc


def resolve_mysql_password(
    environ: Optional[Mapping[str, str]] = None,
    path: Optional[Path] = None,
) -> str:
    environment = os.environ if environ is None else environ
    explicit = environment.get("RND_DB_PASSWORD", "")
    if explicit:
        return explicit
    return load_machine_password(path)


def _mysql_error_code(error: BaseException) -> Optional[int]:
    if not getattr(error, "args", None):
        return None
    code = error.args[0]
    return code if isinstance(code, int) else None


def validate_mysql_connection(
    settings: MySQLSettings,
    password: str,
    connect=pymysql.connect,
) -> None:
    try:
        connection = connect(
            host=settings.host,
            port=settings.port,
            database=settings.database,
            user=settings.user,
            password=password,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
        )
    except pymysql.MySQLError as exc:
        if _mysql_error_code(exc) == 1045:
            raise AuthenticationRejected() from exc
        raise ConnectionUnavailable() from exc
    except Exception as exc:
        raise ConnectionUnavailable() from exc

    try:
        connection.close()
    except Exception as exc:
        raise ConnectionUnavailable() from exc

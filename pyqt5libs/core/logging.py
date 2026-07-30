"""Helpers reutilizables para logging de aplicaciones.

Permite configurar logging a consola y archivo, además de capturar excepciones
con una API simple para aplicaciones de escritorio.
"""

import logging
from functools import wraps
from pathlib import Path
from typing import Callable, Optional

DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def configure_logging(
    *,
    name: Optional[str] = None,
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True,
    fmt: str = DEFAULT_FORMAT,
):
    """Configura y devuelve un logger.

    Si `log_file` se informa, crea el directorio destino automáticamente.
    La función evita duplicar handlers si se llama varias veces sobre el mismo logger.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(fmt)

    if console and not any(isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler) for handler in logger.handlers):
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if log_file and not any(isinstance(handler, logging.FileHandler) and getattr(handler, "baseFilename", None) == str(Path(log_file).resolve()) for handler in logger.handlers):
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None):
    """Devuelve un logger estándar."""
    return logging.getLogger(name)


def log_exception(logger, message: str, exc: BaseException):
    """Registra una excepción con traceback."""
    logger.exception("%s: %s", message, exc)


def capture_exceptions(logger=None, *, message: str = "Error no controlado", reraise: bool = True):
    """Decorador para registrar excepciones.

    Por defecto vuelve a lanzar la excepción luego de registrarla.
    """
    active_logger = logger or logging.getLogger(__name__)

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                log_exception(active_logger, message, exc)
                if reraise:
                    raise
                return None

        return wrapper

    return decorator


__all__ = [
    "DEFAULT_FORMAT",
    "configure_logging",
    "get_logger",
    "log_exception",
    "capture_exceptions",
]

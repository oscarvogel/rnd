"""Helpers para configuración INI.

Este módulo centraliza lectura y escritura de archivos INI usando
`configparser`, evitando rutas fijas y manteniendo una API simple para
aplicaciones de escritorio.
"""

from configparser import ConfigParser
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

PathLike = Union[str, Path]


class IniConfig:
    """Wrapper liviano para archivos INI."""

    def __init__(self, path: PathLike, *, encoding: str = "utf-8"):
        self.path = Path(path)
        self.encoding = encoding
        self.parser = ConfigParser()

    def exists(self) -> bool:
        return self.path.exists()

    def read(self):
        self.parser.read(self.path, encoding=self.encoding)
        return self

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding=self.encoding) as file:
            self.parser.write(file)
        return self

    def get(self, section: str, option: str, default: Optional[Any] = None) -> Any:
        if not self.parser.has_section(section) and section != self.parser.default_section:
            return default
        if not self.parser.has_option(section, option):
            return default
        return self.parser.get(section, option)

    def get_int(self, section: str, option: str, default: Optional[int] = None) -> Optional[int]:
        value = self.get(section, option, default=None)
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_float(self, section: str, option: str, default: Optional[float] = None) -> Optional[float]:
        value = self.get(section, option, default=None)
        if value is None:
            return default
        try:
            return float(str(value).replace(",", "."))
        except (TypeError, ValueError):
            return default

    def get_bool(self, section: str, option: str, default: Optional[bool] = None) -> Optional[bool]:
        value = self.get(section, option, default=None)
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "si", "sí", "on"}

    def set(self, section: str, option: str, value: Any):
        if not self.parser.has_section(section) and section != self.parser.default_section:
            self.parser.add_section(section)
        self.parser.set(section, option, "" if value is None else str(value))
        return self

    def update_section(self, section: str, values: Mapping[str, Any]):
        for option, value in values.items():
            self.set(section, option, value)
        return self

    def as_dict(self) -> Dict[str, Dict[str, str]]:
        return {section: dict(self.parser.items(section)) for section in self.parser.sections()}


def load_ini(path: PathLike, *, encoding: str = "utf-8") -> IniConfig:
    return IniConfig(path, encoding=encoding).read()


def save_ini(path: PathLike, data: Mapping[str, Mapping[str, Any]], *, encoding: str = "utf-8") -> IniConfig:
    config = IniConfig(path, encoding=encoding)
    for section, values in data.items():
        config.update_section(section, values)
    return config.save()


__all__ = ["IniConfig", "load_ini", "save_ini"]

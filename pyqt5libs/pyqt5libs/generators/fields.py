"""Estructuras comunes para generadores de pantallas.

Este módulo define una representación neutral de campos para que distintos
inspectores de modelos puedan producir metadata común y reutilizable.
"""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class FieldInfo:
    """Metadata neutral de un campo de modelo."""

    name: str
    kind: str
    label: str
    required: bool = False
    primary_key: bool = False
    default: Optional[Any] = None
    max_length: Optional[int] = None
    choices: Optional[Any] = None
    raw_field: Optional[Any] = None

    def as_dict(self):
        return {
            "name": self.name,
            "kind": self.kind,
            "label": self.label,
            "required": self.required,
            "primary_key": self.primary_key,
            "default": self.default,
            "max_length": self.max_length,
            "choices": self.choices,
        }


def normalize_label(name: str) -> str:
    """Convierte un nombre técnico en una etiqueta legible."""
    return name.replace("_", " ").strip().capitalize()


__all__ = ["FieldInfo", "normalize_label"]

"""Generación neutral de listados para ABM.

Construye una especificación serializable de columnas, clave primaria y campos
buscables a partir de `FieldInfo`.
"""

from dataclasses import dataclass
from typing import Iterable, List, Optional

from pyqt5libs.generators.fields import FieldInfo

SEARCHABLE_KINDS = {"string", "text"}
VISIBLE_KINDS = {
    "integer",
    "float",
    "decimal",
    "string",
    "text",
    "boolean",
    "date",
    "datetime",
    "time",
    "foreign_key",
}


@dataclass(frozen=True)
class ListColumnSpec:
    """Columna dentro de un listado generado."""

    name: str
    label: str
    kind: str
    visible: bool = True
    searchable: bool = False
    primary_key: bool = False

    def as_dict(self):
        return {
            "name": self.name,
            "label": self.label,
            "kind": self.kind,
            "visible": self.visible,
            "searchable": self.searchable,
            "primary_key": self.primary_key,
        }


@dataclass(frozen=True)
class ListSpec:
    """Listado generado desde metadata de campos."""

    columns: List[ListColumnSpec]
    primary_key: Optional[str] = None
    searchable_fields: Optional[List[str]] = None

    def as_dict(self):
        return {
            "primary_key": self.primary_key,
            "searchable_fields": list(self.searchable_fields or []),
            "columns": [column.as_dict() for column in self.columns],
        }

    def visible_columns(self) -> List[ListColumnSpec]:
        return [column for column in self.columns if column.visible]

    def headers(self) -> List[str]:
        return [column.label for column in self.visible_columns()]

    def field_names(self) -> List[str]:
        return [column.name for column in self.visible_columns()]


def column_from_field(field_info: FieldInfo, *, visible_primary_key: bool = True) -> ListColumnSpec:
    """Convierte `FieldInfo` en una columna de listado."""
    visible = field_info.kind in VISIBLE_KINDS
    if field_info.primary_key and not visible_primary_key:
        visible = False

    return ListColumnSpec(
        name=field_info.name,
        label=field_info.label,
        kind=field_info.kind,
        visible=visible,
        searchable=field_info.kind in SEARCHABLE_KINDS,
        primary_key=field_info.primary_key,
    )


def build_list_spec(fields: Iterable[FieldInfo], *, visible_primary_key: bool = True) -> ListSpec:
    """Construye una especificación neutral de listado."""
    columns = [column_from_field(field_info, visible_primary_key=visible_primary_key) for field_info in fields]
    primary_key = next((column.name for column in columns if column.primary_key), None)
    searchable_fields = [column.name for column in columns if column.searchable]
    return ListSpec(columns=columns, primary_key=primary_key, searchable_fields=searchable_fields)


def build_list_spec_as_dict(fields: Iterable[FieldInfo], *, visible_primary_key: bool = True):
    """Devuelve una especificación de listado serializable."""
    return build_list_spec(fields, visible_primary_key=visible_primary_key).as_dict()


__all__ = [
    "SEARCHABLE_KINDS",
    "VISIBLE_KINDS",
    "ListColumnSpec",
    "ListSpec",
    "column_from_field",
    "build_list_spec",
    "build_list_spec_as_dict",
]

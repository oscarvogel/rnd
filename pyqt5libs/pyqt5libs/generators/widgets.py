"""Mapeo de metadata de campos a especificaciones de widgets.

Esta fase no instancia widgets PyQt todavía. Define una especificación neutral
para decidir qué control corresponde a cada tipo de campo detectado.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

from pyqt5libs.generators.fields import FieldInfo


WIDGET_BY_KIND = {
    "string": "line_edit",
    "text": "text_edit",
    "integer": "spin_box",
    "float": "double_spin_box",
    "decimal": "double_spin_box",
    "boolean": "check_box",
    "date": "date_edit",
    "datetime": "datetime_edit",
    "time": "time_edit",
    "foreign_key": "combo_box",
    "unknown": "line_edit",
}


@dataclass(frozen=True)
class WidgetSpec:
    """Especificación neutral de widget para un campo."""

    field_name: str
    widget_type: str
    label: str
    required: bool = False
    read_only: bool = False
    options: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self):
        return {
            "field_name": self.field_name,
            "widget_type": self.widget_type,
            "label": self.label,
            "required": self.required,
            "read_only": self.read_only,
            "options": dict(self.options),
        }


def widget_type_for_field(field_info: FieldInfo) -> str:
    """Devuelve el tipo de widget neutral para un `FieldInfo`."""
    return WIDGET_BY_KIND.get(field_info.kind, "line_edit")


def widget_options_for_field(field_info: FieldInfo) -> Dict[str, Any]:
    """Construye opciones útiles para el widget a generar."""
    options: Dict[str, Any] = {}
    if field_info.max_length:
        options["max_length"] = field_info.max_length
    if field_info.default is not None:
        options["default"] = field_info.default
    if field_info.choices:
        options["choices"] = field_info.choices
    return options


def widget_spec_from_field(field_info: FieldInfo) -> WidgetSpec:
    """Convierte metadata de campo en una especificación de widget."""
    return WidgetSpec(
        field_name=field_info.name,
        widget_type=widget_type_for_field(field_info),
        label=field_info.label,
        required=field_info.required,
        read_only=field_info.primary_key,
        options=widget_options_for_field(field_info),
    )


def widget_specs_from_fields(fields):
    """Convierte una lista de `FieldInfo` en especificaciones de widgets."""
    return [widget_spec_from_field(field_info) for field_info in fields]


def widget_specs_as_dict(fields):
    """Devuelve especificaciones de widgets serializables."""
    return [spec.as_dict() for spec in widget_specs_from_fields(fields)]


__all__ = [
    "WIDGET_BY_KIND",
    "WidgetSpec",
    "widget_type_for_field",
    "widget_options_for_field",
    "widget_spec_from_field",
    "widget_specs_from_fields",
    "widget_specs_as_dict",
]

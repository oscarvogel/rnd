"""Generación neutral de formularios desde especificaciones de widgets.

Esta fase todavía no instancia widgets PyQt reales. Construye una estructura
serializable y testeable que luego podrá convertirse en controles visuales.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from pyqt5libs.generators.widgets import WidgetSpec


@dataclass(frozen=True)
class FormFieldSpec:
    """Campo dentro de un formulario generado."""

    name: str
    label: str
    widget_type: str
    required: bool = False
    read_only: bool = False
    row: int = 0
    column: int = 0
    options: Optional[dict] = None

    def as_dict(self):
        return {
            "name": self.name,
            "label": self.label,
            "widget_type": self.widget_type,
            "required": self.required,
            "read_only": self.read_only,
            "row": self.row,
            "column": self.column,
            "options": dict(self.options or {}),
        }


@dataclass(frozen=True)
class FormSpec:
    """Formulario generado a partir de `WidgetSpec`."""

    fields: List[FormFieldSpec]
    columns: int = 1

    def as_dict(self):
        return {
            "columns": self.columns,
            "fields": [field.as_dict() for field in self.fields],
        }

    def field_map(self) -> Dict[str, FormFieldSpec]:
        return {field.name: field for field in self.fields}


def form_field_from_widget_spec(spec: WidgetSpec, *, row: int = 0, column: int = 0) -> FormFieldSpec:
    """Convierte un `WidgetSpec` en `FormFieldSpec`."""
    return FormFieldSpec(
        name=spec.field_name,
        label=spec.label,
        widget_type=spec.widget_type,
        required=spec.required,
        read_only=spec.read_only,
        row=row,
        column=column,
        options=dict(spec.options),
    )


def build_form_spec(widget_specs: Iterable[WidgetSpec], *, columns: int = 1, include_read_only: bool = True) -> FormSpec:
    """Construye una especificación neutral de formulario.

    `columns` permite distribuir los campos en una grilla lógica.
    """
    columns = max(1, int(columns or 1))
    fields: List[FormFieldSpec] = []
    position = 0

    for spec in widget_specs:
        if spec.read_only and not include_read_only:
            continue
        row = position // columns
        column = position % columns
        fields.append(form_field_from_widget_spec(spec, row=row, column=column))
        position += 1

    return FormSpec(fields=fields, columns=columns)


def build_form_spec_as_dict(widget_specs: Iterable[WidgetSpec], *, columns: int = 1, include_read_only: bool = True):
    """Devuelve una especificación de formulario serializable."""
    return build_form_spec(widget_specs, columns=columns, include_read_only=include_read_only).as_dict()


__all__ = [
    "FormFieldSpec",
    "FormSpec",
    "form_field_from_widget_spec",
    "build_form_spec",
    "build_form_spec_as_dict",
]

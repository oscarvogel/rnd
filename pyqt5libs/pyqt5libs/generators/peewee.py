"""Introspección básica de modelos Peewee para generar ABM.

La salida de este módulo usa `FieldInfo`, una estructura neutral que luego
podrá alimentar generadores de formularios, listados y validaciones.
"""

from typing import List

from pyqt5libs.generators.fields import FieldInfo, normalize_label


FIELD_TYPE_MAP = {
    "AutoField": "integer",
    "BigAutoField": "integer",
    "IntegerField": "integer",
    "BigIntegerField": "integer",
    "SmallIntegerField": "integer",
    "FloatField": "float",
    "DoubleField": "float",
    "DecimalField": "decimal",
    "CharField": "string",
    "EmailField": "string",
    "TextField": "text",
    "BooleanField": "boolean",
    "DateField": "date",
    "DateTimeField": "datetime",
    "TimeField": "time",
    "ForeignKeyField": "foreign_key",
}


def map_peewee_field_kind(field) -> str:
    """Mapea una clase de campo Peewee a un tipo neutral."""
    return FIELD_TYPE_MAP.get(field.__class__.__name__, "unknown")


def inspect_field(field) -> FieldInfo:
    """Convierte un campo Peewee en `FieldInfo`."""
    name = getattr(field, "name", None) or getattr(field, "column_name", "")
    verbose_name = getattr(field, "verbose_name", None)
    label = verbose_name or normalize_label(name)

    return FieldInfo(
        name=name,
        kind=map_peewee_field_kind(field),
        label=label,
        required=not bool(getattr(field, "null", False)),
        primary_key=bool(getattr(field, "primary_key", False)),
        default=getattr(field, "default", None),
        max_length=getattr(field, "max_length", None),
        choices=getattr(field, "choices", None),
        raw_field=field,
    )


def inspect_model(model) -> List[FieldInfo]:
    """Devuelve metadata neutral de los campos de un modelo Peewee."""
    fields = getattr(model._meta, "sorted_fields", None)
    if fields is None:
        fields = list(getattr(model._meta, "fields", {}).values())
    return [inspect_field(field) for field in fields]


def inspect_model_as_dict(model):
    """Devuelve metadata serializable de los campos de un modelo Peewee."""
    return [field.as_dict() for field in inspect_model(model)]


__all__ = [
    "FIELD_TYPE_MAP",
    "map_peewee_field_kind",
    "inspect_field",
    "inspect_model",
    "inspect_model_as_dict",
]

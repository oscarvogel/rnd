"""Ensamblador para generar especificaciones y clases ABM.

Une introspección de campos, widgets, formulario y listado en un contrato único.
Además permite crear una clase ABM dinámica compatible con el ABM histórico.
"""

from dataclasses import dataclass
from typing import Any, Optional

from pyqt5libs.generators.forms import FormSpec, build_form_spec
from pyqt5libs.generators.lists import ListSpec, build_list_spec
from pyqt5libs.generators.peewee import inspect_model
from pyqt5libs.generators.persistence import create_record, remove_record, update_record
from pyqt5libs.generators.validation import validate_values, validation_rules_for_fields
from pyqt5libs.generators.widgets import widget_specs_from_fields


@dataclass(frozen=True)
class ABMSpec:
    """Especificación completa de un ABM automático."""

    model: Any
    title: str
    fields: list
    widgets: list
    form: FormSpec
    list: ListSpec
    view_mode: str = "tabs"
    form_columns: int = 1

    def as_dict(self):
        return {
            "title": self.title,
            "view_mode": self.view_mode,
            "form_columns": self.form_columns,
            "fields": [field.as_dict() for field in self.fields],
            "widgets": [widget.as_dict() for widget in self.widgets],
            "form": self.form.as_dict(),
            "list": self.list.as_dict(),
        }


def default_title_for_model(model) -> str:
    """Obtiene un título legible para el ABM desde el modelo."""
    meta = getattr(model, "_meta", None)
    table_name = getattr(meta, "table_name", None)
    if table_name:
        return str(table_name).replace("_", " ").title()
    return getattr(model, "__name__", "Registros")


def create_abm_spec_from_model(
    model,
    *,
    title: Optional[str] = None,
    form_columns: int = 1,
    view_mode: str = "tabs",
    include_read_only_fields: bool = True,
    visible_primary_key: bool = True,
) -> ABMSpec:
    """Crea una especificación ABM completa desde un modelo Peewee."""
    fields = inspect_model(model)
    widgets = widget_specs_from_fields(fields)
    form = build_form_spec(widgets, columns=form_columns, include_read_only=include_read_only_fields)
    list_spec = build_list_spec(fields, visible_primary_key=visible_primary_key)

    return ABMSpec(
        model=model,
        title=title or default_title_for_model(model),
        fields=fields,
        widgets=widgets,
        form=form,
        list=list_spec,
        view_mode=view_mode,
        form_columns=max(1, int(form_columns or 1)),
    )


def create_abm_spec_as_dict(model, **kwargs):
    """Devuelve una especificación ABM serializable."""
    return create_abm_spec_from_model(model, **kwargs).as_dict()


def _default_abm_base_class():
    """Importa el ABM histórico solo cuando realmente hace falta."""
    from pyqt5libs.libs.vistas.ABM import ABM

    return ABM


def _field_info_map(spec: ABMSpec):
    return {field.name: field for field in spec.fields}


def _raw_field_for_name(spec: ABMSpec, name: str):
    field = _field_info_map(spec).get(name)
    return getattr(field, "raw_field", None) if field else None


def _visible_raw_fields(spec: ABMSpec):
    names = spec.list.field_names()
    fields = []
    for name in names:
        raw_field = _raw_field_for_name(spec, name)
        if raw_field is not None:
            fields.append(raw_field)
    return fields


def _searchable_raw_fields(spec: ABMSpec):
    fields = []
    for name in spec.list.searchable_fields or []:
        raw_field = _raw_field_for_name(spec, name)
        if raw_field is not None:
            fields.append(raw_field)
    return fields


def _primary_key_raw_field(spec: ABMSpec):
    if not spec.list.primary_key:
        return None
    return _raw_field_for_name(spec, spec.list.primary_key)


def create_control_for_form_field(form_field):
    """Crea un control PyQt para un campo generado.

    Se importa de forma lazy para que la generación de clases pueda testearse
    sin instanciar PyQt.
    """
    widget_type = form_field.widget_type

    if widget_type == "text_edit":
        from PyQt5.QtWidgets import QTextEdit

        return QTextEdit()
    if widget_type == "check_box":
        from pyqt5libs.pyqt5libs.Checkbox import CheckBox

        return CheckBox()
    if widget_type == "combo_box":
        from PyQt5.QtWidgets import QComboBox

        return QComboBox()
    if widget_type in {"date_edit", "datetime_edit", "time_edit"}:
        from pyqt5libs.pyqt5libs.Fechas import FechaLine

        return FechaLine()
    if widget_type in {"spin_box", "double_spin_box"}:
        from pyqt5libs.pyqt5libs.Spinner import Spinner

        return Spinner()

    from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto

    control = EntradaTexto()
    max_length = form_field.options.get("max_length") if form_field.options else None
    if max_length and hasattr(control, "setMaxLength"):
        control.setMaxLength(int(max_length))
    return control


def create_abm_class_from_spec(spec: ABMSpec, *, base_class=None, class_name: Optional[str] = None):
    """Crea una clase ABM dinámica desde `ABMSpec`.

    La clase resultante hereda del ABM histórico o de `base_class` si se provee.
    Esto permite testear la configuración sin abrir una UI real.
    """
    base_class = base_class or _default_abm_base_class()
    generated_name = class_name or "{}ABM".format(str(spec.title).replace(" ", ""))
    primary_key = _primary_key_raw_field(spec)
    validation_rules = validation_rules_for_fields(spec.fields)

    def ArmaCarga(self):
        for form_field in spec.form.fields:
            raw_field = _raw_field_for_name(spec, form_field.name)
            control = create_control_for_form_field(form_field)
            self.ArmaEntrada(
                raw_field or form_field.name,
                texto=form_field.label,
                control=control,
                enabled=not form_field.read_only,
            )

    def ValidateValues(self, values):
        return validate_values(values, self.validation_rules)

    def CreateRecord(self, values):
        return create_record(self.generated_spec, values, self.validation_rules)

    def UpdateRecord(self, record, values):
        return update_record(self.generated_spec, record, values, self.validation_rules)

    def CanRemove(self, record):
        return record is not None

    def RemoveRecord(self, record):
        if not self.CanRemove(record):
            from pyqt5libs.generators.persistence import DeleteResult

            return DeleteResult(ok=False, record=record, message="El registro no puede borrarse")
        return remove_record(record)

    attrs = {
        "__doc__": "ABM generado automáticamente para {}.".format(spec.title),
        "generated_spec": spec,
        "validation_rules": validation_rules,
        "model": spec.model,
        "titulo": spec.title,
        "view_mode": spec.view_mode,
        "form_layout_mode": "two_columns" if spec.form_columns > 1 else "single",
        "form_columns": spec.form_columns,
        "camposAMostrar": _visible_raw_fields(spec),
        "ordenBusqueda": _searchable_raw_fields(spec),
        "campoClave": primary_key,
        "autoincremental": bool(primary_key),
        "ArmaCarga": ArmaCarga,
        "ValidateValues": ValidateValues,
        "CreateRecord": CreateRecord,
        "UpdateRecord": UpdateRecord,
        "CanRemove": CanRemove,
        "RemoveRecord": RemoveRecord,
    }

    return type(generated_name, (base_class,), attrs)


def create_abm_class_from_model(model, **kwargs):
    """Crea una clase ABM dinámica desde un modelo Peewee."""
    base_class = kwargs.pop("base_class", None)
    class_name = kwargs.pop("class_name", None)
    spec = create_abm_spec_from_model(model, **kwargs)
    return create_abm_class_from_spec(spec, base_class=base_class, class_name=class_name)


def create_abm_from_model(model, **kwargs):
    """Crea una clase ABM dinámica desde un modelo Peewee."""
    return create_abm_class_from_model(model, **kwargs)


__all__ = [
    "ABMSpec",
    "default_title_for_model",
    "create_abm_spec_from_model",
    "create_abm_spec_as_dict",
    "create_control_for_form_field",
    "create_abm_class_from_spec",
    "create_abm_class_from_model",
    "create_abm_from_model",
]

"""Validaciones automáticas para AutoABM.

Convierte metadata de campos en reglas de validación reutilizables y testeables.
"""

from dataclasses import dataclass
from typing import Any, Callable, Iterable, List

from pyqt5libs.forms import validators
from pyqt5libs.generators.fields import FieldInfo


@dataclass(frozen=True)
class ValidationRule:
    """Regla de validación aplicada a un campo."""

    field_name: str
    label: str
    validator: Callable[[Any], validators.ValidationResult]
    name: str

    def validate(self, value: Any) -> validators.ValidationResult:
        return self.validator(value)


@dataclass(frozen=True)
class FieldValidationResult:
    """Resultado de validar un campo."""

    field_name: str
    ok: bool
    message: str = ""


@dataclass(frozen=True)
class FormValidationResult:
    """Resultado de validar un formulario completo."""

    ok: bool
    errors: List[FieldValidationResult]

    def first_error(self):
        return self.errors[0] if self.errors else None


def is_email_field(field_info: FieldInfo) -> bool:
    name = field_info.name.lower()
    return name in {"email", "correo", "mail"} or "email" in name or "correo" in name


def is_cuit_field(field_info: FieldInfo) -> bool:
    return field_info.name.lower() in {"cuit", "cuil", "cuit_cuil"}


def validation_rules_for_field(field_info: FieldInfo) -> List[ValidationRule]:
    """Crea reglas automáticas para un campo."""
    rules: List[ValidationRule] = []

    if field_info.required and not field_info.primary_key:
        rules.append(
            ValidationRule(
                field_name=field_info.name,
                label=field_info.label,
                name="required",
                validator=lambda value, label=field_info.label: validators.required(value, label),
            )
        )

    if field_info.max_length:
        rules.append(
            ValidationRule(
                field_name=field_info.name,
                label=field_info.label,
                name="max_length",
                validator=lambda value, label=field_info.label, max_length=field_info.max_length: validators.max_length(value, max_length, label),
            )
        )

    if field_info.kind in {"integer"} and not field_info.primary_key:
        rules.append(
            ValidationRule(
                field_name=field_info.name,
                label=field_info.label,
                name="integer",
                validator=lambda value, label=field_info.label: validators.integer(value, label),
            )
        )

    if field_info.kind in {"float", "decimal"}:
        rules.append(
            ValidationRule(
                field_name=field_info.name,
                label=field_info.label,
                name="numeric",
                validator=lambda value, label=field_info.label: validators.numeric(value, label),
            )
        )

    if is_email_field(field_info):
        rules.append(
            ValidationRule(
                field_name=field_info.name,
                label=field_info.label,
                name="email",
                validator=lambda value, label=field_info.label: validators.email(value, label),
            )
        )

    if is_cuit_field(field_info):
        rules.append(
            ValidationRule(
                field_name=field_info.name,
                label=field_info.label,
                name="cuit",
                validator=lambda value, label=field_info.label: validators.cuit(value, label),
            )
        )

    return rules


def validation_rules_for_fields(fields: Iterable[FieldInfo]) -> List[ValidationRule]:
    rules: List[ValidationRule] = []
    for field_info in fields:
        rules.extend(validation_rules_for_field(field_info))
    return rules


def validate_field_value(field_name: str, value: Any, rules: Iterable[ValidationRule]) -> FieldValidationResult:
    for rule in rules:
        if rule.field_name != field_name:
            continue
        result = rule.validate(value)
        if not result.ok:
            return FieldValidationResult(field_name=field_name, ok=False, message=result.message)
    return FieldValidationResult(field_name=field_name, ok=True)


def validate_values(values: dict, rules: Iterable[ValidationRule]) -> FormValidationResult:
    errors: List[FieldValidationResult] = []
    grouped = {}
    for rule in rules:
        grouped.setdefault(rule.field_name, []).append(rule)

    for field_name, field_rules in grouped.items():
        result = validate_field_value(field_name, values.get(field_name), field_rules)
        if not result.ok:
            errors.append(result)

    return FormValidationResult(ok=not errors, errors=errors)


__all__ = [
    "ValidationRule",
    "FieldValidationResult",
    "FormValidationResult",
    "is_email_field",
    "is_cuit_field",
    "validation_rules_for_field",
    "validation_rules_for_fields",
    "validate_field_value",
    "validate_values",
]

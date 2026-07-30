"""Validadores reutilizables para formularios administrativos.

Las funciones de este módulo son deliberadamente simples y no dependen de
widgets PyQt. Esto permite probarlas fácilmente y reutilizarlas en pantallas
ABM, formularios de carga o validaciones previas al guardado.
"""

import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class ValidationResult:
    """Resultado estándar de una validación."""

    ok: bool
    message: str = ""

    def __bool__(self):
        return self.ok


def valid(message: str = "") -> ValidationResult:
    return ValidationResult(ok=True, message=message)


def invalid(message: str) -> ValidationResult:
    return ValidationResult(ok=False, message=message)


def is_empty(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def required(value: Any, field_name: str = "Campo") -> ValidationResult:
    if is_empty(value):
        return invalid(f"{field_name} es obligatorio")
    return valid()


def min_length(value: Any, length: int, field_name: str = "Campo") -> ValidationResult:
    if is_empty(value):
        return valid()
    if len(str(value).strip()) < length:
        return invalid(f"{field_name} debe tener al menos {length} caracteres")
    return valid()


def max_length(value: Any, length: int, field_name: str = "Campo") -> ValidationResult:
    if is_empty(value):
        return valid()
    if len(str(value).strip()) > length:
        return invalid(f"{field_name} no debe superar {length} caracteres")
    return valid()


def numeric(value: Any, field_name: str = "Campo") -> ValidationResult:
    if is_empty(value):
        return valid()
    try:
        float(str(value).replace(",", "."))
    except ValueError:
        return invalid(f"{field_name} debe ser numérico")
    return valid()


def integer(value: Any, field_name: str = "Campo") -> ValidationResult:
    if is_empty(value):
        return valid()
    try:
        int(str(value).strip())
    except ValueError:
        return invalid(f"{field_name} debe ser un número entero")
    return valid()


def email(value: Any, field_name: str = "Email") -> ValidationResult:
    if is_empty(value):
        return valid()
    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(pattern, str(value).strip()):
        return invalid(f"{field_name} no tiene un formato válido")
    return valid()


def cuit(value: Any, field_name: str = "CUIT") -> ValidationResult:
    """Valida CUIT/CUIL argentino con dígito verificador."""
    if is_empty(value):
        return valid()
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 11:
        return invalid(f"{field_name} debe tener 11 dígitos")

    factors = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    total = sum(int(digit) * factor for digit, factor in zip(digits[:10], factors))
    remainder = total % 11
    expected = 11 - remainder
    if expected == 11:
        expected = 0
    elif expected == 10:
        expected = 9

    if int(digits[-1]) != expected:
        return invalid(f"{field_name} no es válido")
    return valid()


def in_range(value: Any, minimum: Optional[float] = None, maximum: Optional[float] = None, field_name: str = "Campo") -> ValidationResult:
    if is_empty(value):
        return valid()
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        return invalid(f"{field_name} debe ser numérico")

    if minimum is not None and number < minimum:
        return invalid(f"{field_name} debe ser mayor o igual a {minimum}")
    if maximum is not None and number > maximum:
        return invalid(f"{field_name} debe ser menor o igual a {maximum}")
    return valid()


def first_error(*results: ValidationResult) -> ValidationResult:
    for result in results:
        if not result.ok:
            return result
    return valid()


__all__ = [
    "ValidationResult",
    "valid",
    "invalid",
    "is_empty",
    "required",
    "min_length",
    "max_length",
    "numeric",
    "integer",
    "email",
    "cuit",
    "in_range",
    "first_error",
]

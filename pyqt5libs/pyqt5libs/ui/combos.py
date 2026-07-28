"""Helpers reutilizables para QComboBox.

Estas funciones centralizan operaciones repetidas con combos: cargar opciones,
seleccionar por valor y leer el dato asociado al item seleccionado.
"""

from typing import Any, Iterable, Mapping, Optional


def _get_value(item: Any, key: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def normalize_combo_item(item: Any, text_key: str = "text", value_key: str = "value"):
    """Normaliza un item a `(texto, valor)`.

    Soporta:
    - string simple: texto y valor iguales.
    - tupla/lista: `(valor, texto)`.
    - dict/objeto: usando `text_key` y `value_key`.
    """
    if isinstance(item, str):
        return item, item

    if isinstance(item, (tuple, list)):
        if len(item) == 1:
            return str(item[0]), item[0]
        value, text = item[0], item[1]
        return str(text), value

    text = _get_value(item, text_key)
    value = _get_value(item, value_key)
    if text is None:
        text = value
    if value is None:
        value = text
    return str(text), value


def load_combo(combo, items: Iterable[Any], *, text_key: str = "text", value_key: str = "value", clear: bool = True, placeholder: Optional[str] = None):
    """Carga opciones en un QComboBox.

    Devuelve el mismo combo para permitir encadenamiento.
    """
    if clear:
        combo.clear()

    if placeholder is not None:
        combo.addItem(placeholder, None)

    for item in items:
        text, value = normalize_combo_item(item, text_key=text_key, value_key=value_key)
        combo.addItem(text, value)

    return combo


def selected_data(combo, default: Any = None) -> Any:
    """Devuelve el dato asociado al item seleccionado."""
    index = combo.currentIndex()
    if index < 0:
        return default
    data = combo.itemData(index)
    return default if data is None else data


def selected_text(combo, default: str = "") -> str:
    """Devuelve el texto visible del item seleccionado."""
    text = combo.currentText()
    return text if text else default


def select_by_data(combo, value: Any) -> bool:
    """Selecciona el primer item cuyo dato coincida con `value`."""
    index = combo.findData(value)
    if index < 0:
        return False
    combo.setCurrentIndex(index)
    return True


def select_by_text(combo, text: str, *, case_sensitive: bool = False) -> bool:
    """Selecciona el primer item cuyo texto visible coincida."""
    target = text if case_sensitive else text.lower()
    for index in range(combo.count()):
        current = combo.itemText(index)
        comparable = current if case_sensitive else current.lower()
        if comparable == target:
            combo.setCurrentIndex(index)
            return True
    return False


__all__ = [
    "normalize_combo_item",
    "load_combo",
    "selected_data",
    "selected_text",
    "select_by_data",
    "select_by_text",
]

"""Helpers reutilizables para tablas Qt.

El módulo se enfoca en operaciones repetidas sobre widgets tipo tabla:
configurar cabeceras, normalizar filas, cargar datos y leer la selección.
"""

from typing import Any, Iterable, Mapping, Sequence

from PyQt5.QtWidgets import QTableWidgetItem


def normalize_table_row(row: Any, columns: Sequence[str] = ()): 
    """Normaliza una fila a una lista de valores.

    Soporta:
    - dict: usa el orden de `columns`.
    - objeto: usa atributos en el orden de `columns`.
    - lista/tupla: respeta el orden recibido.
    - valor simple: devuelve una lista con un solo valor.
    """
    if isinstance(row, Mapping):
        if columns:
            return [row.get(column) for column in columns]
        return list(row.values())

    if columns and not isinstance(row, (list, tuple)):
        return [getattr(row, column, None) for column in columns]

    if isinstance(row, (list, tuple)):
        return list(row)

    return [row]


def clear_table(table):
    """Limpia todas las filas de la tabla."""
    table.setRowCount(0)
    return table


def setup_headers(table, headers: Sequence[str]):
    """Configura las cabeceras horizontales de una tabla."""
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels([str(header) for header in headers])
    return table


def append_row(table, row: Sequence[Any]):
    """Agrega una fila al final de la tabla."""
    row_index = table.rowCount()
    table.insertRow(row_index)
    for column_index, value in enumerate(row):
        item = QTableWidgetItem("" if value is None else str(value))
        table.setItem(row_index, column_index, item)
    return row_index


def load_table(table, rows: Iterable[Any], *, headers: Sequence[str] = (), columns: Sequence[str] = (), clear: bool = True):
    """Carga filas en una tabla.

    `headers` define las columnas visibles.
    `columns` define el orden de extracción para dicts u objetos.
    """
    if headers:
        setup_headers(table, headers)
    if clear:
        clear_table(table)

    for row in rows:
        append_row(table, normalize_table_row(row, columns=columns))
    return table


def current_row_index(table) -> int:
    """Devuelve el índice de la fila actual o -1 si no hay selección."""
    return table.currentRow()


def current_row_values(table):
    """Devuelve los textos de la fila seleccionada."""
    row = table.currentRow()
    if row < 0:
        return []
    values = []
    for column in range(table.columnCount()):
        item = table.item(row, column)
        values.append(item.text() if item else "")
    return values


def current_cell_text(table, column: int, default: str = "") -> str:
    """Devuelve el texto de una celda de la fila actual."""
    row = table.currentRow()
    if row < 0:
        return default
    item = table.item(row, column)
    return item.text() if item else default


__all__ = [
    "normalize_table_row",
    "clear_table",
    "setup_headers",
    "append_row",
    "load_table",
    "current_row_index",
    "current_row_values",
    "current_cell_text",
]

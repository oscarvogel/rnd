"""Importador del informe de despacho Tremblay (layout cliente + productos).

El archivo `docs/informe tremblay.xls` (renombrado al fixture
`tests/fixtures/informe_tremblay.xls`) tiene un layout irregular:
- Fila 0 vacia / fila 1 con un nombre de informe (se descarta).
- Bloques por cliente con doble cabecera repetida:
  * Cabecera cliente: codigo | nombre | lugar_entrega+remito | fecha | pedido | bultos
  * Cabecera productos: CODIGO | DETALLE | ... | ORIGINAL | DESP. | DIF. | KG | TOTAL | COMPROB.
  * N filas de producto: codigo | detalle | ... | original | despachado | dif | kg | total | comprob

Este modulo expone `procesar_informe_tremblay(archivo_entrada)` que devuelve la
ruta de un xlsx temporal con la estructura que espera
`ImportacionPedidosController`: una fila por producto con las columnas
`Cliente`, `Nombre_Cliente`, `Producto`, `Cantidad`, `KG`, `Bultos`, etc.

Decisiones de mapeo (ver issue #6):
- `Cantidad` se toma de la columna DESP. (despachado real).
- El comprobante del xls NO pisa `HojaDeRuta.comprobante` (eso lo decide
  `ProcesoLista` para el proveedor); igual lo exponemos en la columna
  `Comprobante` por si se quiere auditar o mover a `Observaciones`.
- `Observaciones` se completa con `"Comprobante Tremblay: <numero>"` para
  no perder el dato si la columna `Comprobante` se descarta en
  `ProcesoLista`.
- La fila 1 del archivo (ej "BONDA JOSE") se descarta.
"""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import List, Tuple

import pandas as pd
import xlsxwriter


_CABECERA_PRODUCTOS_COL0 = "CODIGO"
_CABECERA_PRODUCTOS_COL1 = "DETALLE"


def _to_str(value) -> str:
    """Normaliza una celda a string vacio si es NaN/None."""
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value).strip()


def _to_num(value) -> float:
    """Convierte una celda numerica. Si falla, devuelve 0.0."""
    if value is None:
        return 0.0
    if isinstance(value, float) and pd.isna(value):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    # Aceptar coma como decimal y puntos como separador de miles
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def _es_cabecera_cliente(row: List[str]) -> bool:
    """Detecta la fila cabecera de un cliente.

    Heuristica: col0 numerica (codigo de cliente), col1 NO es "DETALLE" ni
    "CODIGO", y la fila tiene al menos fecha en col[3] o pedido en col[4].
    Esto filtra la fila "BONDA JOSE" (nombre del informe) que aparece en
    fila 1 sin fecha ni pedido.
    """
    if not row or len(row) < 5:
        return False
    col0 = _to_str(row[0])
    col1 = _to_str(row[1]).upper()
    if not col0 or not col1:
        return False
    if col1 == _CABECERA_PRODUCTOS_COL1:
        return False
    if col0.upper() == _CABECERA_PRODUCTOS_COL0:
        return False
    if not col0.isdigit():
        return False
    fecha = _to_str(row[3])
    pedido = _to_str(row[4])
    if not fecha and not pedido:
        return False
    return True


def _es_cabecera_productos(row: List[str]) -> bool:
    """Detecta la fila cabecera de productos (`CODIGO | DETALLE | ...`)."""
    if not row or len(row) < 2:
        return False
    col0 = _to_str(row[0]).upper()
    col1 = _to_str(row[1]).upper()
    return col0 == _CABECERA_PRODUCTOS_COL0 and col1 == _CABECERA_PRODUCTOS_COL1


def _es_fila_producto(row: List[str]) -> bool:
    """Detecta si la fila es un producto: col0 numerica, col1 con texto y
    col6 (DESP.) presente."""
    if not row or len(row) < 7:
        return False
    col0 = _to_str(row[0])
    col1 = _to_str(row[1])
    if not col0 or not col1:
        return False
    if col0.upper() == _CABECERA_PRODUCTOS_COL0:
        return False
    if not col0.isdigit():
        return False
    # Para distinguir de la cabecera de cliente: la cabecera de cliente
    # tiene col3 (fecha) con formato dd/mm/aaaa.
    fecha = _to_str(row[3]) if len(row) > 3 else ""
    if re.match(r"\d{1,2}/\d{1,2}/\d{2,4}", fecha):
        return False
    return True


def _parsear_bloque(df: pd.DataFrame, inicio: int) -> Tuple[dict, int]:
    """Lee un bloque de cliente a partir de la fila `inicio` (cabecera
    cliente). Devuelve (dict_cliente, fila_despues_del_bloque)."""
    row = [_to_str(c) for c in df.iloc[inicio].tolist()]
    cliente = {
        "codigo": _to_str(row[0]),
        "nombre": _to_str(row[1]),
        "lugar_entrega": _to_str(row[2]) if len(row) > 2 else "",
        "fecha": _to_str(row[3]) if len(row) > 3 else "",
        "pedido": _to_str(row[4]) if len(row) > 4 else "",
        "bultos": _to_num(row[5]) if len(row) > 5 else 0.0,
    }
    cursor = inicio + 1
    # Saltar la fila de cabecera de productos (CODIGO | DETALLE | ...)
    if cursor < len(df) and _es_cabecera_productos(
        [_to_str(c) for c in df.iloc[cursor].tolist()]
    ):
        cursor += 1
    return cliente, cursor


def _procesar_fila_producto(
    cliente: dict, row: List
) -> dict:
    """Convierte una fila de producto + el cliente actual en un dict
    con las columnas que espera el controller."""
    comprobante = _to_str(row[10]) if len(row) > 10 else ""
    obs_parts = []
    if comprobante:
        obs_parts.append(f"Comprobante Tremblay: {comprobante}")
    lugar = cliente.get("lugar_entrega", "")
    if lugar:
        obs_parts.append(f"Lugar: {lugar}")
    return {
        "Cliente": cliente["codigo"],
        "Nombre_Cliente": cliente["nombre"],
        "Lugar_Entrega": cliente["lugar_entrega"],
        "Fecha": cliente["fecha"],
        "Pedido": cliente["pedido"],
        "Bultos": cliente["bultos"],
        "Producto": _to_str(row[0]),
        "Detalle": _to_str(row[1]),
        "Cantidad": _to_num(row[6]),  # DESP.
        "Original": _to_num(row[5]),  # ORIGINAL
        "Diferencia": _to_num(row[7]),  # DIF.
        "KG": _to_num(row[8]),  # KG
        "Total": _to_num(row[9]),  # TOTAL
        "Comprobante": comprobante,
        "Observaciones": " | ".join(obs_parts),
    }


def procesar_informe_tremblay(archivo_entrada: str) -> str:
    """Procesa el xls de informe de despacho Tremblay.

    Args:
        archivo_entrada: ruta del archivo .xls (o .xlsx).

    Returns:
        Ruta del xlsx temporal generado, listo para que
        `ImportacionPedidosController` lo lea como si fuera un pedido.
    """
    path = Path(archivo_entrada)
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {archivo_entrada}")

    try:
        df = pd.read_excel(archivo_entrada, sheet_name=0, header=None, dtype=str, keep_default_na=False)
    except Exception as exc:
        raise ValueError(
            f"No se pudo leer el archivo {archivo_entrada}: {exc}"
        ) from exc

    # Columnas de salida (orden fijo, para que la grilla del controller las
    # muestre consistentes entre importaciones).
    columnas = [
        "Cliente",
        "Nombre_Cliente",
        "Lugar_Entrega",
        "Fecha",
        "Pedido",
        "Bultos",
        "Producto",
        "Detalle",
        "Cantidad",
        "Original",
        "Diferencia",
        "KG",
        "Total",
        "Comprobante",
        "Observaciones",
    ]

    resultado: List[dict] = []
    cliente_actual: dict = {}
    estado = "esperando_cliente"  # o "en_productos"
    total_filas = len(df)

    # La primera fila esta vacia y la segunda ("BONDA JOSE") no es un
    # cliente real; _es_cabecera_cliente la rechaza por faltar fecha/pedido.
    cursor = 0

    while cursor < total_filas:
        row = [_to_str(c) for c in df.iloc[cursor].tolist()]

        if _es_cabecera_cliente(row):
            cliente_actual, cursor = _parsear_bloque(df, cursor)
            estado = "en_productos"
            continue

        if _es_cabecera_productos(row):
            cursor += 1
            continue

        if estado == "en_productos" and _es_fila_producto(row):
            if cliente_actual:
                resultado.append(
                    _procesar_fila_producto(cliente_actual, df.iloc[cursor].tolist())
                )
            cursor += 1
            continue

        # Fila vacia o no reconocida: avanzar
        cursor += 1

    df_salida = pd.DataFrame(resultado, columns=columnas)
    if df_salida.empty:
        raise ValueError(
            "El archivo no contiene bloques cliente/producto reconocibles. "
            "Verifica que sea un informe de despacho Tremblay valido."
        )

    # Generar xlsx temporal usando openpyxl directo para preservar
    # strings numericas (ej "000100232326" no se convierte a int 100232326).
    tmp = tempfile.NamedTemporaryFile(
        mode="wb", suffix=".xlsx", delete=False
    )
    tmp.close()
    _escribir_xlsx_con_strings(df_salida, tmp.name)
    return tmp.name


def _escribir_xlsx_con_strings(df: pd.DataFrame, ruta: str) -> None:
    """Escribe un DataFrame a xlsx preservando strings numericas como texto.

    pandas + openpyxl por defecto convierten una string como "000100232326" a
    int 100232326 al escribir. Esto rompe codigos de pedido y comprobante
    que necesitan preservar ceros a la izquierda. xlsxwriter permite
    forzar `write_string` con formato texto, lo que openpyxl+pandas no
    pueden expresar limpiamente.
    """
    wb = xlsxwriter.Workbook(ruta)
    ws = wb.add_worksheet()
    text_fmt = wb.add_format({"num_format": "@"})
    for col_idx, col_name in enumerate(df.columns):
        ws.write_string(0, col_idx, str(col_name))
    for row_idx, row in enumerate(df.itertuples(index=False), start=1):
        for col_idx, value in enumerate(row):
            if value is None or (isinstance(value, float) and pd.isna(value)):
                ws.write_blank(row_idx, col_idx, None)
            elif isinstance(value, str):
                ws.write_string(row_idx, col_idx, value, text_fmt)
            elif isinstance(value, bool):
                ws.write_boolean(row_idx, col_idx, value)
            else:
                # int / float / datetime / etc: numero directo
                ws.write_number(row_idx, col_idx, value)
    wb.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m utiles.importacion_informe_tremblay <archivo.xls>")
        sys.exit(1)
    salida = procesar_informe_tremblay(sys.argv[1])
    print(f"XLSX generado: {salida}")

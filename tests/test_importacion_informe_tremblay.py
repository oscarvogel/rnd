"""Tests unitarios del importador de informe de despacho Tremblay."""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pandas as pd
import pytest

# Asegurar que el paquete raiz este en sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

modulo = importlib.import_module("utiles.importacion_informe_tremblay")
procesar_informe_tremblay = modulo.procesar_informe_tremblay


FIXTURE_XLS = ROOT / "tests" / "fixtures" / "informe_tremblay.xls"


@pytest.fixture
def df_procesado() -> pd.DataFrame:
    """Procesa el fixture y devuelve el DataFrame resultante."""
    ruta_xlsx = procesar_informe_tremblay(str(FIXTURE_XLS))
    return pd.read_excel(ruta_xlsx)


def test_procesa_fixture_sin_error(df_procesado):
    """El fixture real debe procesarse sin tirar excepciones."""
    assert not df_procesado.empty


def test_cantidad_de_filas_es_la_esperada(df_procesado):
    """El informe de julio 2026 trae 293 lineas de producto en 41 clientes."""
    assert len(df_procesado) == 293


def test_columnas_de_salida(df_procesado):
    """Las columnas del xlsx matchean el contrato del controller."""
    columnas_esperadas = [
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
    assert list(df_procesado.columns) == columnas_esperadas


def test_bonda_jose_no_aparece_como_cliente(df_procesado):
    """La fila 'BONDA JOSE' (cabecera del informe) debe descartarse."""
    assert "BONDA JOSE" not in df_procesado["Nombre_Cliente"].values
    assert "000019" not in df_procesado["Cliente"].astype(str).values


def test_primer_cliente_es_valle(df_procesado):
    """El primer cliente del informe es VALLE DISTRIBUCIONES SRL."""
    primer_cliente = df_procesado.iloc[0]
    assert primer_cliente["Cliente"] == 201504
    assert "VALLE DISTRIBUCIONES SRL" in primer_cliente["Nombre_Cliente"]


def test_observaciones_contiene_comprobante_y_lugar(df_procesado):
    """Las observaciones deben llevar el comprobante y el lugar de entrega."""
    con_observaciones = df_procesado[df_procesado["Observaciones"] != ""]
    assert not con_observaciones.empty
    # Al menos una fila debe tener el formato esperado
    muestra = con_observaciones.iloc[0]["Observaciones"]
    assert "Comprobante Tremblay:" in muestra or "Lugar:" in muestra


def test_cantidad_toma_desp(df_procesado):
    """La columna Cantidad se mapea desde la columna DESP. del xls."""
    # Para el primer cliente (VALLE) con despacho real, los productos
    # despachados tienen Cantidad > 0
    productos_despachados = df_procesado[df_procesado["Cantidad"] > 0]
    assert len(productos_despachados) > 0


def test_kg_no_es_todo_cero(df_procesado):
    """El informe real tiene productos con kilos > 0."""
    assert (df_procesado["KG"] > 0).sum() > 100


def test_archivo_inexistente_falla():
    """Un path que no existe debe tirar FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        procesar_informe_tremblay("no_existe_este_archivo.xls")


def test_archivo_sin_bloques_reconocibles(tmp_path):
    """Un xls sin estructura de despacho debe tirar ValueError."""
    # Crear un xlsx vacio pero con un valor en fila 0 (sin estructura)
    df_vacio = pd.DataFrame([["solo", "una", "fila", "xlsx", "", "", "", "", "", "", ""]])
    ruta = tmp_path / "vacio.xlsx"
    df_vacio.to_excel(ruta, header=False, index=False)
    with pytest.raises(ValueError, match="no contiene bloques"):
        procesar_informe_tremblay(str(ruta))

"""Normalizadores de archivos de pedidos de proveedores.

Los formatos externos se convierten a un contrato de columnas comun para que
ImportacionPedidosController no necesite conocer posiciones ni IDs de proveedor.
"""
from __future__ import annotations

import os
import re
import tempfile
import unicodedata

import pandas as pd


COLUMNAS_NORMALIZADAS = [
    "codigo_cliente",
    "detalle_cliente",
    "destino",
    "comprobante",
    "cantidad",
    "producto",
    "bultos",
    "kilos",
    "observaciones",
]


def _texto(valor):
    if pd.isna(valor):
        return ""
    return str(valor).strip()


def _notificar(callback, porcentaje):
    if callback:
        callback(porcentaje)


def _guardar_temporal(filas):
    if not filas:
        raise ValueError("El archivo no contiene pedidos reconocibles")
    df = pd.DataFrame(filas, columns=COLUMNAS_NORMALIZADAS)
    temporal = tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False)
    temporal.close()
    df.to_excel(temporal.name, index=False, engine="openpyxl")
    return temporal.name


def _clave_cliente(nombre):
    """Genera una clave estable cuando el proveedor no informa codigo de cliente."""
    texto = unicodedata.normalize("NFKD", _texto(nombre))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto.upper()).strip()
    return ("NOMBRE:" + texto)[:100]


def _es_tio_pujio(df):
    limite = min(len(df), 80)
    for i in range(limite):
        fila = [_texto(v).upper() for v in df.iloc[i].tolist()]
        if "CLIENTE :" in fila:
            return True
    return False


def procesar_tio_pujio(archivo_entrada, progreso=None):
    """Convierte CONTROL DE PEDIDOS de Tio Pujio a columnas normalizadas."""
    if not os.path.exists(archivo_entrada):
        raise FileNotFoundError(archivo_entrada)

    df = pd.read_excel(archivo_entrada, sheet_name=0, header=None)
    _notificar(progreso, 10)

    codigo_cliente = ""
    nombre_cliente = ""
    comprobante = ""
    filas = []
    total = max(len(df), 1)

    for indice, row in df.iterrows():
        valores = row.tolist()
        textos = [_texto(v) for v in valores]
        primero = textos[0].upper() if textos else ""

        if primero == "CLIENTE :":
            codigo_cliente = textos[2] if len(textos) > 2 else ""
            nombre_cliente = textos[4] if len(textos) > 4 else ""
            comprobante = ""
            continue

        tipo = textos[3].upper() if len(textos) > 3 else ""
        if tipo == "PED":
            comprobante = textos[5] if len(textos) > 5 else ""
            continue

        descripcion = textos[2] if len(textos) > 2 else ""
        if not codigo_cliente or not nombre_cliente or not descripcion:
            continue
        if descripcion.upper().startswith("SUBTOTALES"):
            continue

        # Las lineas de producto tienen codigo en B, descripcion en C,
        # hormas en H y kilos en K.
        codigo_producto = textos[1] if len(textos) > 1 else ""
        hormas = valores[7] if len(valores) > 7 and not pd.isna(valores[7]) else ""
        kilos = valores[10] if len(valores) > 10 and not pd.isna(valores[10]) else ""
        if not codigo_producto or hormas == "" or kilos == "":
            continue

        filas.append({
            "codigo_cliente": codigo_cliente,
            "detalle_cliente": nombre_cliente,
            "destino": "",
            "comprobante": comprobante,
            "cantidad": hormas,
            "producto": descripcion,
            "bultos": hormas,
            "kilos": kilos,
            "observaciones": "Producto Tio Pujio: {}".format(codigo_producto),
        })
        if indice % 20 == 0:
            _notificar(progreso, 10 + int((indice + 1) / total * 80))

    _notificar(progreso, 95)
    salida = _guardar_temporal(filas)
    _notificar(progreso, 100)
    return salida


def _buscar_fila_encabezados(df):
    requeridas = {
        "tipo operacion",
        "ciudad",
        "cliente",
        "codigo",
        "descripcionproducto",
        "unidades",
        "kilos",
    }
    for indice, row in df.iterrows():
        presentes = {_texto(v).lower() for v in row.tolist() if _texto(v)}
        if requeridas.issubset(presentes):
            return indice
    return None


def procesar_detalle_ventas(archivo_entrada, progreso=None):
    """Convierte Detalle de Ventas por Provincia/Cliente/Producto."""
    if not os.path.exists(archivo_entrada):
        raise FileNotFoundError(archivo_entrada)

    bruto = pd.read_excel(archivo_entrada, sheet_name=0, header=None)
    fila_header = _buscar_fila_encabezados(bruto)
    if fila_header is None:
        raise ValueError("No se encontro el encabezado del Detalle de Ventas")

    _notificar(progreso, 20)
    df = pd.read_excel(archivo_entrada, sheet_name=0, header=fila_header)
    filas = []
    total = max(len(df), 1)

    for indice, row in df.iterrows():
        cliente = _texto(row.get("Cliente"))
        producto = _texto(row.get("DescripcionProducto"))
        if not cliente or not producto:
            continue

        ciudad = _texto(row.get("ciudad"))
        tipo = _texto(row.get("Tipo Operacion"))
        codigo_producto = _texto(row.get("Codigo"))
        unidades = row.get("Unidades", "")
        kilos = row.get("Kilos", "")
        if pd.isna(unidades):
            unidades = ""
        if pd.isna(kilos):
            kilos = ""

        observaciones = " / ".join(
            parte for parte in (
                "Ciudad: {}".format(ciudad) if ciudad else "",
                "Tipo: {}".format(tipo) if tipo else "",
                "Producto: {}".format(codigo_producto) if codigo_producto else "",
            ) if parte
        )

        filas.append({
            "codigo_cliente": _clave_cliente(cliente),
            "detalle_cliente": cliente,
            "destino": ciudad,
            "comprobante": "",
            "cantidad": unidades,
            "producto": producto,
            "bultos": unidades,
            "kilos": kilos,
            "observaciones": observaciones,
        })
        if indice % 20 == 0:
            _notificar(progreso, 20 + int((indice + 1) / total * 70))

    _notificar(progreso, 95)
    salida = _guardar_temporal(filas)
    _notificar(progreso, 100)
    return salida


def normalizar_archivo_pedidos(archivo_entrada, progreso=None):
    """Detecta formatos conocidos y devuelve un xlsx normalizado.

    Retorna ``None`` si el archivo no corresponde a uno de estos dos formatos,
    permitiendo que los importadores historicos (por ejemplo Tremblay) sigan
    funcionando sin cambios.
    """
    if not archivo_entrada or not os.path.exists(archivo_entrada):
        return None

    try:
        bruto = pd.read_excel(archivo_entrada, sheet_name=0, header=None)
    except Exception:
        return None

    _notificar(progreso, 5)
    if _es_tio_pujio(bruto):
        return procesar_tio_pujio(archivo_entrada, progreso=progreso)

    if _buscar_fila_encabezados(bruto) is not None:
        return procesar_detalle_ventas(archivo_entrada, progreso=progreso)

    return None

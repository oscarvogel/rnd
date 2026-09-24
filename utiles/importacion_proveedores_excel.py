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


METODO_COLUMNAS = "COLUMNAS"
METODO_TIO_PUJIO = "TIO_PUJIO"
METODO_DETALLE_VENTAS = "DETALLE_VENTAS"
METODO_TREMBLAY = "TREMBLAY"

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
    """Convierte CONTROL DE PEDIDOS de Tio Pujio a columnas normalizadas.

    El reporte cambia de posiciones entre versiones/exportaciones. Por eso no
    dependemos de columnas fijas: detectamos Cliente, PED, Hormas y Kilos por
    contenido, y usamos esas referencias para extraer cada línea.
    """
    if not os.path.exists(archivo_entrada):
        raise FileNotFoundError(archivo_entrada)

    df = pd.read_excel(archivo_entrada, sheet_name=0, header=None)
    _notificar(progreso, 10)

    codigo_cliente = ""
    nombre_cliente = ""
    comprobante = ""
    filas = []
    total = max(len(df), 1)
    columna_hormas = None
    columna_kilos = None

    def no_vacios(valores):
        return [
            (indice, _texto(valor))
            for indice, valor in enumerate(valores)
            if _texto(valor)
        ]

    for indice, row in df.iterrows():
        valores = row.tolist()
        celdas = no_vacios(valores)
        textos_mayus = {pos: texto.upper() for pos, texto in celdas}

        # Las cabeceras se repiten en cada página. En las exportaciones reales
        # la cifra de Hormas aparece una columna a la izquierda del rótulo.
        pos_hormas = next(
            (pos for pos, texto in textos_mayus.items() if texto == "HORMAS"),
            None,
        )
        pos_kilos = next(
            (pos for pos, texto in textos_mayus.items() if texto == "KILOS"),
            None,
        )
        if pos_hormas is not None and pos_kilos is not None:
            columna_hormas = max(0, pos_hormas - 1)
            columna_kilos = pos_kilos
            continue

        cliente_pos = next(
            (pos for pos, texto in textos_mayus.items() if texto == "CLIENTE :"),
            None,
        )
        if cliente_pos is not None:
            posteriores = [
                (pos, texto) for pos, texto in celdas if pos > cliente_pos
            ]
            codigo_cliente = posteriores[0][1] if posteriores else ""
            try:
                numero_cliente = float(codigo_cliente.replace(",", "."))
                if numero_cliente.is_integer():
                    codigo_cliente = str(int(numero_cliente))
            except (TypeError, ValueError):
                pass
            nombre_cliente = posteriores[1][1] if len(posteriores) > 1 else ""
            comprobante = ""
            continue

        ped_pos = next(
            (pos for pos, texto in textos_mayus.items() if texto == "PED"),
            None,
        )
        if ped_pos is not None:
            posteriores = [
                texto for pos, texto in celdas if pos > ped_pos
            ]
            comprobante = posteriores[0] if posteriores else ""
            continue

        if not codigo_cliente or not nombre_cliente or not comprobante:
            continue
        if columna_hormas is None or columna_kilos is None:
            continue

        # Una línea de producto tiene un código numérico antes de una
        # descripción textual y cantidades en las columnas Hormas/Kilos.
        hormas = (
            valores[columna_hormas]
            if columna_hormas < len(valores) and not pd.isna(valores[columna_hormas])
            else ""
        )
        kilos = (
            valores[columna_kilos]
            if columna_kilos < len(valores) and not pd.isna(valores[columna_kilos])
            else ""
        )
        if hormas == "" or kilos == "":
            continue

        descripcion_pos = None
        descripcion = ""
        for pos, texto in celdas:
            mayus = texto.upper()
            if mayus.startswith("SUBTOTALES") or mayus == "TOTALES :":
                descripcion = ""
                break
            if pos >= columna_hormas:
                break
            # Evitar fechas, tipos y comprobantes; la descripción es el primer
            # texto de producto que aparece antes de las cantidades.
            if mayus == "PED" or re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", texto):
                continue
            if re.match(r"^[A-Z]\d{4}-", mayus):
                continue
            try:
                float(texto.replace(",", "."))
                continue
            except ValueError:
                descripcion_pos = pos
                descripcion = texto
                break

        if not descripcion or descripcion_pos is None:
            continue

        codigo_producto = ""
        for pos, texto in reversed(celdas):
            if pos >= descripcion_pos:
                continue
            try:
                numero = float(texto.replace(",", "."))
            except ValueError:
                continue
            codigo_producto = str(int(numero)) if numero.is_integer() else texto
            break

        if not codigo_producto:
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


def _normalizar_salida_tremblay(ruta_procesada, progreso=None):
    """Convierte la salida histórica de Tremblay al contrato común."""
    df = pd.read_excel(ruta_procesada)
    requeridas = {"Cliente", "Nombre_Cliente", "Producto", "Detalle", "Cantidad", "KG", "Bultos"}
    if not requeridas.issubset(set(df.columns)):
        raise ValueError("La salida de Tremblay no contiene las columnas esperadas")

    filas = []
    total = max(len(df), 1)
    for indice, row in df.iterrows():
        codigo_producto = _texto(row.get("Producto"))
        observaciones = _texto(row.get("Observaciones"))
        if codigo_producto:
            detalle_codigo = "Código producto Tremblay: {}".format(codigo_producto)
            observaciones = " | ".join(
                parte for parte in (observaciones, detalle_codigo) if parte
            )
        filas.append({
            "codigo_cliente": row.get("Cliente", ""),
            "detalle_cliente": _texto(row.get("Nombre_Cliente")),
            "destino": _texto(row.get("Lugar_Entrega")),
            "comprobante": _texto(row.get("Comprobante")),
            "cantidad": "" if pd.isna(row.get("Cantidad")) else row.get("Cantidad"),
            "producto": _texto(row.get("Detalle")),
            "bultos": "" if pd.isna(row.get("Bultos")) else row.get("Bultos"),
            "kilos": "" if pd.isna(row.get("KG")) else row.get("KG"),
            "observaciones": observaciones,
        })
        if indice % 25 == 0:
            _notificar(progreso, 25 + int((indice + 1) / total * 65))

    _notificar(progreso, 95)
    salida = _guardar_temporal(filas)
    _notificar(progreso, 100)
    return salida


def procesar_tremblay_normalizado(archivo_entrada, progreso=None):
    """Procesa un informe .xls Tremblay y devuelve columnas normalizadas."""
    from utiles.importacion_informe_tremblay import procesar_informe_tremblay

    _notificar(progreso, 15)
    ruta_historica = procesar_informe_tremblay(archivo_entrada)
    return _normalizar_salida_tremblay(ruta_historica, progreso=progreso)


def normalizar_archivo_pedidos(archivo_entrada, progreso=None, metodo=None):
    """Normaliza usando el método explícito del proveedor.

    Si metodo es None conserva autodetección únicamente por compatibilidad.
    El flujo de UI debe pasar siempre el método configurado en el proveedor.
    """
    if not archivo_entrada or not os.path.exists(archivo_entrada):
        return None

    extension = os.path.splitext(str(archivo_entrada))[1].lower()
    if extension in {".pdf", ".png", ".jpg", ".jpeg"}:
        from utiles.importacion_pdf_ia import extraer_pedidos_pdf_ia

        filas = extraer_pedidos_pdf_ia(
            archivo_entrada,
            progreso=progreso,
        )
        return _guardar_temporal(filas)

    metodo = (metodo or "").strip().upper()
    if metodo == METODO_COLUMNAS:
        return None
    if metodo == METODO_TREMBLAY:
        return procesar_tremblay_normalizado(archivo_entrada, progreso=progreso)

    try:
        bruto = pd.read_excel(archivo_entrada, sheet_name=0, header=None)
    except Exception:
        return None

    _notificar(progreso, 5)

    if metodo == METODO_TIO_PUJIO:
        if not _es_tio_pujio(bruto):
            raise ValueError("El archivo no coincide con el formato Tío Pujio configurado para este proveedor")
        return procesar_tio_pujio(archivo_entrada, progreso=progreso)

    if metodo == METODO_DETALLE_VENTAS:
        if _buscar_fila_encabezados(bruto) is None:
            raise ValueError("El archivo no coincide con el formato Detalle de Ventas configurado para este proveedor")
        return procesar_detalle_ventas(archivo_entrada, progreso=progreso)

    if metodo:
        raise ValueError("Método de importación desconocido: {}".format(metodo))

    if _es_tio_pujio(bruto):
        return procesar_tio_pujio(archivo_entrada, progreso=progreso)
    if _buscar_fila_encabezados(bruto) is not None:
        return procesar_detalle_ventas(archivo_entrada, progreso=progreso)
    if str(archivo_entrada).lower().endswith(".xls"):
        try:
            return procesar_tremblay_normalizado(archivo_entrada, progreso=progreso)
        except (ValueError, FileNotFoundError):
            return None
    return None

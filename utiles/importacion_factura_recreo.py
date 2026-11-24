# coding=utf-8
"""Importador de facturas PDF de Recreo.

El PDF es una factura unica con una linea por articulo. Se lee el texto y se
normaliza al contrato comun del importador de pedidos.
"""
from __future__ import annotations

import io
import os
import re
import tempfile
import zipfile

import pandas as pd
import pdfplumber

from utiles.importacion_proveedores_excel import COLUMNAS_NORMALIZADAS, _notificar


RE_PRODUCTO = re.compile(
    r"^(\d{4,6})\s+(.+?)\s+(\d+)\s+(\d+)\s+([\d.,]+)\s+([\d.,]+)\s+(\d+)\s+([\d.,]+)$"
)


def _texto_pdf(archivo_entrada):
    with pdfplumber.open(archivo_entrada) as pdf:
        return "\n".join((pagina.extract_text() or "") for pagina in pdf.pages)


def _numero(texto):
    texto = str(texto or "").strip().replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto:
        texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _entero(texto):
    numero = _numero(texto)
    return int(numero) if numero is not None else None


def _formatear_numero(valor):
    if valor is None:
        return ""
    if float(valor).is_integer():
        return "{:,.0f}".format(valor).replace(",", ".")
    return "{:,.2f}".format(valor).replace(",", "X").replace(".", ",").replace("X", ".")


def _parece_factura_recreo(texto):
    mayus = texto.upper()
    return (
        "INDUSTRIAS FRIGORIFICAS" in mayus
        and "RECREO S.A.I.C." in mayus
        and "ART" in mayus
        and "DESCRIPCION" in mayus
        and "BULTOS" in mayus
    )


def _cabecera(texto):
    cliente = re.search(
        r"Cliente:\s*(\S+)\s+([^\n]+?)\s+CUIT:\s*([\d-]+)",
        texto,
        re.IGNORECASE,
    )
    if not cliente:
        raise ValueError("No se encontro el cliente en la factura de Recreo")

    factura = re.search(r"N\D{0,3}(\d{8,16})", texto)
    if not factura:
        raise ValueError("No se encontro el numero de factura de Recreo")

    fecha = re.search(r"Fecha:\s*(\d{2}/\d{2}/\d{4})", texto)
    entrega = re.search(r"Entregar en:\s*([^\n]+)", texto, re.IGNORECASE)

    codigo = cliente.group(1).strip()
    nombre = re.sub(r"\s+", " ", cliente.group(2)).strip()
    cuit = re.sub(r"\D", "", cliente.group(3))
    direccion_entrega = entrega.group(1).strip() if entrega else ""
    ciudad = ""
    if direccion_entrega:
        primera = direccion_entrega.split(",", 1)[0].strip()
        partes = primera.split()
        if partes and not partes[-1].isdigit():
            ciudad = partes[-1]
    return {
        "codigo_cliente": codigo,
        "detalle_cliente": nombre,
        "cuit": cuit,
        "comprobante": factura.group(1),
        "fecha": fecha.group(1) if fecha else "",
        "destino": ciudad or direccion_entrega,
    }


def _productos(texto):
    productos = []
    en_tabla = False
    for linea in (linea.strip() for linea in texto.splitlines()):
        if not linea:
            continue
        if not en_tabla:
            mayus = linea.upper()
            if mayus.startswith("ART") and "DESCRIPCION" in mayus and "BULTOS" in mayus:
                en_tabla = True
            continue
        if linea.upper().startswith("OBS.:"):
            break
        coincidencia = RE_PRODUCTO.match(linea)
        if coincidencia:
            productos.append(
                {
                    "codigo": coincidencia.group(1),
                    "descripcion": coincidencia.group(2).strip(),
                    "bultos": int(coincidencia.group(3)),
                    "unidades": int(coincidencia.group(4)),
                    "kilos": _numero(coincidencia.group(5)),
                }
            )
        elif productos:
            productos[-1]["descripcion"] = (
                productos[-1]["descripcion"] + " " + linea
            ).strip()
    if not productos:
        raise ValueError("La factura de Recreo no contiene articulos reconocibles")
    return productos


def _totales(texto):
    def buscar(patron):
        coincidencia = re.search(patron, texto, re.IGNORECASE)
        return coincidencia.group(1) if coincidencia else None

    return {
        "unidades": _entero(buscar(r"Unidades\s+([\d.]+)")),
        "kilos": _numero(buscar(r"Peso Neto Total\s+([\d.,]+)")),
        "bultos": _entero(buscar(r"Cant\.\s*Bultos\s+([\d.]+)")),
    }


def _agregar_advertencia(advertencias, texto):
    if advertencias is not None and texto and texto not in advertencias:
        advertencias.append(texto)


def _validar_totales(productos, totales, advertencias):
    sumas = {
        "unidades": sum(producto["unidades"] for producto in productos),
        "kilos": sum(producto["kilos"] or 0 for producto in productos),
        "bultos": sum(producto["bultos"] for producto in productos),
    }
    diferencias = []
    for clave, etiqueta in (
        ("unidades", "Unidades"),
        ("kilos", "Peso neto"),
        ("bultos", "Bultos"),
    ):
        esperado = totales.get(clave)
        if esperado is None:
            continue
        if abs(sumas[clave] - esperado) > 0.01:
            diferencias.append(
                "{}: factura {} vs lineas {}".format(
                    etiqueta,
                    _formatear_numero(esperado),
                    _formatear_numero(sumas[clave]),
                )
            )
    if diferencias:
        _agregar_advertencia(
            advertencias,
            "Los totales de la factura no coinciden con la suma de las lineas ({}).".format(
                "; ".join(diferencias)
            ),
        )


def _guardar_temporal(filas):
    df = pd.DataFrame(filas, columns=COLUMNAS_NORMALIZADAS)
    temporal = tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False)
    temporal.close()
    df.to_excel(temporal.name, index=False, engine="openpyxl")
    return temporal.name


def _extraer_factura(texto, advertencias=None):
    """Convierte el texto de una factura de Recreo en cabecera y filas.

    Se usa tanto para un PDF suelto como para cada PDF dentro de un ZIP de
    WhatsApp. Las advertencias se acumulan en la lista recibida.
    """
    if not _parece_factura_recreo(texto):
        raise ValueError(
            "El PDF no corresponde a una factura de Recreo. "
            "Verifique el proveedor seleccionado o use el metodo Columnas."
        )

    cabecera = _cabecera(texto)
    productos = _productos(texto)
    totales = _totales(texto)

    if not cabecera["cuit"]:
        _agregar_advertencia(
            advertencias,
            "La factura de Recreo no informa un CUIT valido; el cliente puede quedar pendiente.",
        )
    _validar_totales(productos, totales, advertencias)

    filas = []
    for producto in productos:
        observaciones = "Cod. {} | Factura {} | Fecha {} | Recreo".format(
            producto["codigo"],
            cabecera["comprobante"],
            cabecera["fecha"],
        ).strip()
        filas.append(
            {
                "codigo_cliente": cabecera["cuit"] or cabecera["codigo_cliente"],
                "detalle_cliente": cabecera["detalle_cliente"],
                "destino": cabecera["destino"],
                "comprobante": cabecera["comprobante"],
                "cantidad": producto["unidades"],
                "producto": producto["descripcion"][:100],
                "bultos": producto["bultos"],
                "kilos": producto["kilos"],
                "observaciones": observaciones[:100],
            }
        )
    return cabecera, filas


def procesar_factura_recreo(archivo_entrada, progreso=None, advertencias=None):
    if not archivo_entrada or not os.path.exists(archivo_entrada):
        raise FileNotFoundError(archivo_entrada)
    if os.path.splitext(archivo_entrada)[1].lower() != ".pdf":
        raise ValueError("La factura de Recreo debe ser un PDF")

    _notificar(progreso, 10)
    texto = _texto_pdf(archivo_entrada)
    _notificar(progreso, 40)
    _, filas = _extraer_factura(texto, advertencias)
    _notificar(progreso, 90)
    salida = _guardar_temporal(filas)
    _notificar(progreso, 100)
    return salida


def _entradas_pdf_zip(contenedor):
    """Devuelve los PDF utiles del ZIP, sin carpetas ni metadatos de macOS."""
    entradas = []
    for info in contenedor.infolist():
        if info.is_dir():
            continue
        nombre = info.filename.replace("\\", "/")
        if nombre.startswith("__MACOSX/"):
            continue
        if not nombre.lower().endswith(".pdf"):
            continue
        if os.path.basename(nombre).startswith("._"):
            continue
        entradas.append(info)
    return sorted(entradas, key=lambda info: info.filename.lower())


def procesar_facturas_recreo_zip(archivo_entrada, progreso=None, advertencias=None):
    """Importa todas las facturas PDF de Recreo contenidas en un ZIP.

    Es el formato en que los proveedores envian varias facturas juntas por
    WhatsApp. Cada PDF se procesa de forma independiente: una factura dañada
    no impide importar el resto, pero queda informada como advertencia.
    """
    if not archivo_entrada or not os.path.exists(archivo_entrada):
        raise FileNotFoundError(archivo_entrada)
    if os.path.splitext(archivo_entrada)[1].lower() != ".zip":
        raise ValueError("El lote de facturas de Recreo debe ser un archivo ZIP")

    try:
        contenedor = zipfile.ZipFile(archivo_entrada)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ValueError(
            "El archivo ZIP no se pudo abrir: {}".format(exc)
        ) from exc

    with contenedor:
        entradas = _entradas_pdf_zip(contenedor)
        if not entradas:
            raise ValueError("El ZIP no contiene facturas PDF de Recreo")

        total = len(entradas)
        filas_totales = []
        leidas = 0
        comprobantes = set()
        errores = []

        for indice, info in enumerate(entradas, start=1):
            _notificar(progreso, 5 + int((indice - 1) / total * 85))
            nombre = os.path.basename(info.filename.replace("\\", "/"))

            if info.flag_bits & 0x1:
                errores.append("{} (protegido con contraseña)".format(nombre))
                _agregar_advertencia(
                    advertencias,
                    "{}: se omite la factura porque el PDF esta protegido.".format(nombre),
                )
                continue

            try:
                with contenedor.open(info) as archivo_pdf:
                    contenido = archivo_pdf.read()
                texto = _texto_pdf(io.BytesIO(contenido))
                advertencias_factura = []
                cabecera, filas = _extraer_factura(texto, advertencias_factura)
            except Exception as exc:
                errores.append("{} ({})".format(nombre, exc))
                _agregar_advertencia(
                    advertencias,
                    "{}: se omite la factura ({}).".format(nombre, exc),
                )
                continue

            clave = re.sub(r"\D", "", cabecera["comprobante"])
            if clave and clave in comprobantes:
                _agregar_advertencia(
                    advertencias,
                    "{}: la factura {} ya estaba en el ZIP; se importa una sola vez.".format(
                        nombre, cabecera["comprobante"]
                    ),
                )
                continue
            if clave:
                comprobantes.add(clave)

            for texto_advertencia in advertencias_factura:
                _agregar_advertencia(
                    advertencias,
                    "{}: {}".format(nombre, texto_advertencia),
                )
            filas_totales.extend(filas)
            leidas += 1

        if not filas_totales:
            detalle = "; ".join(errores) if errores else "no se encontraron facturas legibles"
            raise ValueError(
                "No se pudo importar ninguna de las {} facturas del ZIP: {}".format(
                    total, detalle
                )
            )

        if errores:
            _agregar_advertencia(
                advertencias,
                "Se importaron {} de {} facturas del ZIP. Con problemas: {}.".format(
                    leidas, total, "; ".join(errores)
                ),
            )

        _notificar(progreso, 95)
        salida = _guardar_temporal(filas_totales)
        _notificar(progreso, 100)
        return salida

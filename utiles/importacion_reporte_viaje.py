# coding=utf-8
"""Importador del Reporte de viaje de Lario (PDF de remitos por viaje).

El PDF es una tabla de 16 columnas con una fila por remito. Se lee por
coordenadas porque el export superpone textos largos (CUIT, ciudad/C.P.) y
algunos nombres quedan truncados en la columna Socio.
"""
from __future__ import annotations

import os
import re
import tempfile
from collections import defaultdict

import pandas as pd
import pdfplumber

from utiles.importacion_proveedores_excel import COLUMNAS_NORMALIZADAS, _notificar


EXTENSIONES = {".pdf"}

COL_PUNTO = 0
COL_ZONA = 1
COL_PEDIDO = 2
COL_ALBARAN = 3
COL_TIPO = 4
COL_CUENTA = 5
COL_SOCIO = 6
COL_CUIT = 7
COL_CALLE = 8
COL_CIUDAD = 9
COL_CP = 10
COL_CAJAS = 11
COL_SUBTOTAL = 12
COL_NETO = 13
COL_BRUTO = 14
COL_CONGELADO = 15
CANTIDAD_COLUMNAS = 16

HEADER_KEYS = {
    "PUNTO",
    "DESCARGA",
    "SOCIO",
    "C.U.I.T",
    "CAJAS",
    "PESO",
    "CUENTA",
}


def _texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def _colapsar(valor):
    return re.sub(r"\s+", " ", _texto(valor)).strip()


def _solo_digitos(valor):
    """Deja solo los digitos de un texto (para celdas que son numericas)."""
    return "".join(caracter for caracter in _texto(valor) if caracter.isdigit())


def _cuit_valido(digitos):
    if len(digitos) != 11 or not digitos.isdigit():
        return False
    pesos = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
    suma = sum(int(digito) * peso for digito, peso in zip(digitos[:10], pesos))
    verificador = 11 - (suma % 11)
    if verificador == 11:
        verificador = 0
    elif verificador == 10:
        verificador = 9
    return verificador == int(digitos[10])


def _formatear_numero(valor):
    if valor is None:
        return ""
    if float(valor).is_integer():
        return "{:,.0f}".format(valor).replace(",", ".")
    return "{:,.2f}".format(valor).replace(",", "X").replace(".", ",").replace("X", ".")


def _parse_numero(texto):
    texto = _texto(texto).replace(" ", "")
    if not texto:
        return None
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return None


def _merge_bounds(valores, tolerancia=1.2):
    salida = []
    for valor in sorted(valores):
        if salida and abs(valor - salida[-1]) <= tolerancia:
            salida[-1] = (salida[-1] + valor) / 2.0
        else:
            salida.append(valor)
    return salida


def _agrupar_por_top(items, tolerancia=2.0):
    grupos = []
    for item in sorted(items, key=lambda x: (x["top"], x["x0"])):
        if grupos and abs(item["top"] - grupos[-1][0]) <= tolerancia:
            grupos[-1][1].append(item)
        else:
            grupos.append([item["top"], [item]])
    return [grupo[1] for grupo in grupos]


def _overlap(a0, a1, b0, b1):
    return max(0.0, min(a1, b1) - max(a0, b0))


def _columna_por_solapamiento(word, bounds):
    mejor_indice = None
    mejor_solape = 0.0
    for indice in range(len(bounds) - 1):
        solape = _overlap(word["x0"], word["x1"], bounds[indice], bounds[indice + 1])
        if solape > mejor_solape:
            mejor_solape = solape
            mejor_indice = indice
    if mejor_indice is not None:
        return mejor_indice
    centro = (word["x0"] + word["x1"]) / 2.0
    return min(
        range(len(bounds) - 1),
        key=lambda i: abs(centro - (bounds[i] + bounds[i + 1]) / 2.0),
    )


def _posiciones_de_celdas(page, top_cabecera):
    """Devuelve los bordes x de las celdas de la cabecera.

    Crystal Report (el export de Lario) dibuja cada celda como rectangulo.
    Otros exportadores dibujan el mismo poligono, que pdfplumber reporta como
    curva. Se usan los rectangulos y, si no hay, se cae a las curvas.
    """
    posiciones = []
    for rect in page.rects:
        if rect["top"] <= top_cabecera + 1.0 <= rect["bottom"]:
            posiciones.append(rect["x0"])
            posiciones.append(rect["x1"])
    if posiciones:
        return posiciones
    for curva in page.curves:
        if curva["top"] <= top_cabecera + 1.0 <= curva["bottom"]:
            posiciones.append(curva["x0"])
            posiciones.append(curva["x1"])
    return posiciones


def _detectar_columnas(page):
    words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
    mejor = None
    for grupo in _agrupar_por_top(words):
        textos = {word["text"].upper() for word in grupo}
        puntaje = len(textos & HEADER_KEYS)
        if puntaje and (mejor is None or puntaje > mejor[0]):
            mejor = (puntaje, min(word["top"] for word in grupo))
    if mejor is None:
        raise ValueError("No se encontro la cabecera del Reporte de viaje")

    top_cabecera = mejor[1]
    posiciones = _posiciones_de_celdas(page, top_cabecera)
    bounds = _merge_bounds(posiciones)
    if len(bounds) - 1 != CANTIDAD_COLUMNAS:
        raise ValueError(
            "El Reporte de viaje no tiene las {} columnas esperadas".format(
                CANTIDAD_COLUMNAS
            )
        )
    return bounds


def _texto_por_rango(chars, bounds, desde, hasta):
    inicio = bounds[desde]
    fin = bounds[hasta]
    seleccion = [char for char in chars if inicio - 1.0 <= char["x0"] < fin]
    seleccion.sort(key=lambda char: char["x0"])
    return _colapsar("".join(char["text"] for char in seleccion))


def _recuperar_cuit(chars, bounds):
    inicio = bounds[COL_CUIT]
    fin = bounds[COL_CUIT + 1]
    por_color = defaultdict(list)
    for char in chars:
        if inicio - 1.5 <= char["x0"] <= fin + 1.0:
            color = char.get("non_stroking_color")
            try:
                hash(color)
            except TypeError:
                color = str(color)
            por_color[color].append(char)

    candidatos = []
    for chars_color in por_color.values():
        chars_color = sorted(chars_color, key=lambda char: char["x0"])
        digitos = "".join(char["text"] for char in chars_color if char["text"].isdigit())
        for coincidencia in re.finditer(r"\d{11}", digitos):
            if _cuit_valido(coincidencia.group(0)):
                candidatos.append(coincidencia.group(0))

    unicos = list(dict.fromkeys(candidatos))
    if unicos:
        return unicos[0]
    todos = "".join(
        char["text"]
        for char in sorted(chars, key=lambda char: char["x0"])
        if inicio - 1.5 <= char["x0"] <= fin + 1.0 and char["text"].isdigit()
    )
    for coincidencia in re.finditer(r"\d{11}", todos):
        if _cuit_valido(coincidencia.group(0)):
            return coincidencia.group(0)
    return ""


def _celdas_por_palabras(words, bounds):
    celdas = defaultdict(list)
    for word in words:
        celdas[_columna_por_solapamiento(word, bounds)].append(word)
    return celdas


def _texto_celda(celdas, indice):
    return _colapsar(
        " ".join(
            word["text"] for word in sorted(celdas.get(indice, []), key=lambda w: w["x0"])
        )
    )


def _leer_pdf(archivo_entrada, progreso=None, advertencias=None):
    filas = []
    totales = {}
    bounds = None

    with pdfplumber.open(archivo_entrada) as pdf:
        total_paginas = max(len(pdf.pages), 1)
        for indice_pagina, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
            if not words:
                _notificar(progreso, 10 + int(indice_pagina / total_paginas * 80))
                continue
            if bounds is None:
                bounds = _detectar_columnas(page)

            chars = page.chars
            for grupo in _agrupar_por_top(words):
                texto_fila = _colapsar(
                    " ".join(word["text"] for word in sorted(grupo, key=lambda w: w["x0"]))
                )
                texto_mayus = texto_fila.upper()
                if "PUNTO DE DESCARGA" in texto_mayus:
                    continue

                celdas = _celdas_por_palabras(grupo, bounds)
                if texto_mayus.startswith("TOTAL"):
                    totales = {
                        "cajas": _parse_numero(_texto_celda(celdas, COL_CAJAS)),
                        "subtotal": _parse_numero(_texto_celda(celdas, COL_SUBTOTAL)),
                        "neto": _parse_numero(_texto_celda(celdas, COL_NETO)),
                    }
                    continue

                pedido = _texto_celda(celdas, COL_PEDIDO)
                albaran = _texto_celda(celdas, COL_ALBARAN)
                if not pedido and not albaran:
                    continue

                chars_fila = [
                    char
                    for char in chars
                    if abs(char["top"] - grupo[0]["top"]) <= 2.0
                ]
                cuit = _recuperar_cuit(chars_fila, bounds)
                cuenta_socio = _texto_por_rango(chars_fila, bounds, COL_CUENTA, COL_SOCIO + 1)
                if cuit:
                    cuenta_socio = cuenta_socio.replace(cuit, " ")
                coincidencia = re.match(r"^(\d+)\s*(.*)$", cuenta_socio)
                if coincidencia:
                    cuenta = coincidencia.group(1)
                    socio = _colapsar(coincidencia.group(2))
                else:
                    cuenta = ""
                    socio = cuenta_socio

                filas.append(
                    {
                        "pedido": pedido,
                        "albaran": albaran,
                        "tipo": _texto_celda(celdas, COL_TIPO),
                        "cuenta": cuenta,
                        "socio": socio,
                        "cuit": cuit,
                        "calle": _texto_celda(celdas, COL_CALLE),
                        "ciudad": _texto_por_rango(chars_fila, bounds, COL_CIUDAD, COL_CIUDAD + 1),
                        # El C.P. se solapa con el final de la ciudad: el export
                        # deja letras pegadas ("PUERTO IGUAZ" + 337000 ->
                        # "3U37000"). El C.P. es siempre numerico, asi que se
                        # queda solo con los digitos.
                        "cp": _solo_digitos(
                            _texto_por_rango(chars_fila, bounds, COL_CP, COL_CP + 1)
                        ),
                        "cajas": _parse_numero(_texto_celda(celdas, COL_CAJAS)),
                        "subtotal": _parse_numero(_texto_celda(celdas, COL_SUBTOTAL)),
                        "neto": _parse_numero(_texto_celda(celdas, COL_NETO)),
                        "bruto": _parse_numero(_texto_celda(celdas, COL_BRUTO)),
                        "congelado": _parse_numero(_texto_celda(celdas, COL_CONGELADO)),
                    }
                )
            _notificar(progreso, 10 + int(indice_pagina / total_paginas * 80))

    if not filas:
        raise ValueError("El Reporte de viaje no contiene remitos reconocibles")
    return filas, totales


def _agregar_advertencia(advertencias, texto):
    if advertencias is None:
        return
    if texto and texto not in advertencias:
        advertencias.append(texto)


def _normalizar_filas(filas_pdf):
    filas = []
    for fila in filas_pdf:
        albaran = fila["albaran"]
        es_wr_out = albaran.upper().startswith("WR/")
        cajas = fila["cajas"]
        neto = fila["neto"]
        revisar = []
        if es_wr_out:
            revisar.append("remito WR/OUT sin peso (posible anulacion)")
        elif cajas is None:
            revisar.append("sin cajas informadas")

        if cajas is None:
            cajas = 0
        if neto is None:
            neto = 0

        codigo_cliente = fila["cuit"] or fila["cuenta"]
        observaciones = []
        if revisar:
            observaciones.append("REVISAR: {}".format("; ".join(revisar)))
        if fila["cuenta"]:
            observaciones.append("Cta {}".format(fila["cuenta"]))
        if fila["pedido"]:
            observaciones.append("Ped {}".format(fila["pedido"]))
        cp = re.sub(r"\D", "", fila["cp"])
        if cp:
            observaciones.append("CP {}".format(cp[:4]))
        if fila["bruto"] is not None:
            observaciones.append("Bruto {}".format(_formatear_numero(fila["bruto"])))
        if fila["congelado"] is not None:
            observaciones.append("Cong {}".format(_formatear_numero(fila["congelado"])))

        filas.append(
            {
                "codigo_cliente": codigo_cliente,
                "detalle_cliente": fila["socio"],
                "destino": fila["ciudad"],
                "comprobante": albaran,
                "cantidad": cajas,
                "producto": fila["tipo"],
                "bultos": cajas,
                "kilos": neto,
                "observaciones": " | ".join(observaciones)[:100],
            }
        )
    return filas


def _validar_totales(filas_pdf, totales, advertencias):
    if not totales:
        return
    suma_cajas = sum(fila["cajas"] or 0 for fila in filas_pdf)
    suma_neto = sum(fila["neto"] or 0 for fila in filas_pdf)
    diferencias = []
    if totales.get("cajas") is not None and abs(suma_cajas - totales["cajas"]) > 0.5:
        diferencias.append(
            "Cajas: PDF {} vs filas {}".format(
                _formatear_numero(totales["cajas"]), _formatear_numero(suma_cajas)
            )
        )
    if totales.get("neto") is not None and abs(suma_neto - totales["neto"]) > 0.5:
        diferencias.append(
            "Peso neto: PDF {} vs filas {}".format(
                _formatear_numero(totales["neto"]), _formatear_numero(suma_neto)
            )
        )
    if diferencias:
        _agregar_advertencia(
            advertencias,
            "El TOTAL del PDF no coincide con la suma de las filas ({}). "
            "Puede faltar detalle: revisa antes de grabar.".format(
                "; ".join(diferencias)
            ),
        )


def _guardar_temporal(filas):
    if not filas:
        raise ValueError("El Reporte de viaje no contiene remitos reconocibles")
    df = pd.DataFrame(filas, columns=COLUMNAS_NORMALIZADAS)
    temporal = tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False)
    temporal.close()
    df.to_excel(temporal.name, index=False, engine="openpyxl")
    return temporal.name


def procesar_reporte_viaje(archivo_entrada, progreso=None, advertencias=None):
    if not archivo_entrada or not os.path.exists(archivo_entrada):
        raise FileNotFoundError(archivo_entrada)

    extension = os.path.splitext(archivo_entrada)[1].lower()
    if extension not in EXTENSIONES:
        raise ValueError(
            "El metodo Reporte de viaje requiere el PDF de remitos del viaje"
        )

    _notificar(progreso, 5)
    filas_pdf, totales = _leer_pdf(
        archivo_entrada,
        progreso=progreso,
        advertencias=advertencias,
    )
    _validar_totales(filas_pdf, totales, advertencias)
    revisar = sum(
        1
        for fila in filas_pdf
        if fila["albaran"].upper().startswith("WR/") or fila["cajas"] is None
    )
    if revisar:
        _agregar_advertencia(
            advertencias,
            "Hay {} remito(s) marcados REVISAR (WR/OUT o sin cajas). "
            "Quedan desmarcados en la vista previa.".format(revisar),
        )

    filas = _normalizar_filas(filas_pdf)
    salida = _guardar_temporal(filas)
    _notificar(progreso, 100)
    return salida

# coding=utf-8
"""Genera el PDF de muestra de Tacural para el DEMO.

El archivo que manda Tacural es un escaneo de papel. Para el DEMO no hace
falta el escaneo real: se dibuja una factura con la misma estructura
(encabezado del proveedor, datos del cliente, tabla de productos, total de
kilos) y se le da una apariencia de documento escaneado, incluida una pagina
girada, que es el caso que mas le cuesta al lector.

Se genera en tiempo de ejecucion por dos razones: no se versiona un PDF (la
higiene del repo prohibe los binarios pesados) y no se versionan datos de
clientes reales. Ademas, el demo queda igual en cualquier maquina.
"""
from __future__ import annotations

import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


FUENTES_MONO = (
    r"C:\Windows\Fonts\consola.ttf",
    r"C:\Windows\Fonts\cour.ttf",
    r"C:\Windows\Fonts\lucon.ttf",
)

# Lienzo a 150 dpi (A4).
ANCHO = 1240
ALTO = 1754
PAPEL = (250, 249, 244)
TINTA = (28, 28, 28)

# Columnas de la tabla de productos, en caracteres (fuente monoespaciada).
COLUMNAS = (
    ("codigo", 0, 7, "left"),
    ("descripcion", 8, 40, "left"),
    ("unid", 41, 48, "right"),
    ("kg", 49, 58, "right"),
    ("punit", 59, 72, "right"),
    ("bonif", 73, 82, "right"),
    ("iva", 83, 90, "right"),
    ("importe", 91, 108, "right"),
)


def _fuente(tamano):
    for ruta in FUENTES_MONO:
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, tamano)
            except OSError:
                continue
    return ImageFont.load_default()


def _ancho_caracter(fuente):
    try:
        return fuente.getlength("0")
    except AttributeError:
        return 8


def _numero(valor, decimales=2):
    """Formato argentino: 8.413,88"""
    if valor is None or valor == "":
        return "-"
    if isinstance(valor, str):
        return valor
    texto = "{:,.{}f}".format(float(valor), decimales)
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def _entero(valor):
    if valor is None or valor == "":
        return "-"
    if isinstance(valor, str):
        return valor
    return str(int(round(float(valor))))


def _linea_tabla(item):
    """Arma la linea de la tabla con las columnas alineadas.

    Las columnas sin dato quedan en blanco, como en el comprobante real.
    """
    def vacio_si_none(valor, formateador):
        if valor is None:
            return ""
        return formateador(valor)

    valores = {
        "codigo": vacio_si_none(item.get("codigo"), _entero),
        "descripcion": (item.get("descripcion") or "")[:30],
        "unid": vacio_si_none(item.get("unid"), _entero),
        "kg": vacio_si_none(item.get("kg"), _numero),
        "punit": vacio_si_none(item.get("punit"), _numero),
        "bonif": vacio_si_none(item.get("bonif"), lambda v: _numero(v, 2)),
        "iva": vacio_si_none(item.get("iva"), lambda v: _numero(v, 2)),
        "importe": vacio_si_none(item.get("importe"), _numero),
    }
    partes = []
    for campo, inicio, fin, alineacion in COLUMNAS:
        ancho = fin - inicio
        texto = valores[campo][:ancho]
        if alineacion == "right":
            partes.append(texto.rjust(ancho))
        else:
            partes.append(texto.ljust(ancho))
    return " ".join(partes)


def _render_factura(factura, indice):
    """Dibuja una factura con la estructura del comprobante de Tacural."""
    fuente = _fuente(19)
    fuente_titulo = _fuente(34)
    fuente_chica = _fuente(16)
    paso = _ancho_caracter(fuente)

    lienzo = Image.new("RGB", (ANCHO, ALTO), PAPEL)
    dibujo = ImageDraw.Draw(lienzo)

    def escribir(x, y, texto, tamano=fuente):
        dibujo.text((x, y), texto, font=tamano, fill=TINTA)

    # Encabezado del proveedor (izquierda) y del comprobante (derecha).
    escribir(90, 90, "TACURAL", fuente_titulo)
    escribir(90, 140, "El Sabor del Tierno Casero", fuente_chica)
    escribir(90, 170, "CHACINADOS TACURAL SRL", fuente)
    escribir(90, 200, "Chaco 6349 - Santa Fe", fuente)
    escribir(90, 230, "Tel/Fax: ( 0342 ) 4891307", fuente)
    escribir(90, 280, "IVA RESPONSABLE INSCRIPTO", fuente)

    derecha = ANCHO - 90 - 34 * paso
    escribir(derecha, 90, "FACTURA A ELECTRONICA", fuente)
    escribir(derecha, 120, "{}".format(factura["numero"]), fuente)
    escribir(derecha, 160, "FECHA {}".format(factura["fecha"]), fuente)
    escribir(derecha, 210, "ING. BRUTOS : 921-741323-6", fuente_chica)
    escribir(derecha, 240, "Cuit.: 30-58743818-2", fuente_chica)

    # Datos del cliente.
    y = 340
    escribir(90, y, "Razon Social: {}".format(factura["razon_social"]), fuente)
    escribir(90, y + 30, "Direccion: {}".format(factura["direccion"]), fuente)
    escribir(90, y + 60, "Provincia: {}".format(factura["provincia"]), fuente)
    escribir(90 + 34 * paso, y + 60, "C.P.:{}".format(factura["cp"]), fuente)
    escribir(90, y + 90, "IVA: Responsable inscripto", fuente)
    escribir(90, y + 120, "COND. DE PAGO: CTA CTE 7 DIAS FF", fuente)
    escribir(derecha, y, "Cod.Cliente: {}".format(factura["codigo_cliente"]), fuente)
    escribir(derecha, y + 30, "Localidad: {}".format(factura["localidad"]), fuente)
    escribir(derecha, y + 60, "Tel: {}".format(factura["telefono"]), fuente)
    escribir(derecha, y + 90, "CUIT: {}".format(factura["cuit"]), fuente)
    escribir(derecha, y + 120, "CAJA : Cajas: {}".format(factura["cajas"]), fuente)

    # Tabla de productos.
    y_tabla = y + 200
    escribir(90, y_tabla, _linea_tabla({
        "codigo": "Cod.Art",
        "descripcion": "Descript.",
        "unid": "Unid.",
        "kg": "Kg",
        "punit": "P.Unit",
        "bonif": "% Bonif.",
        "iva": "%Iva",
        "importe": "Importe",
    }), fuente)
    dibujo.line(
        [(90, y_tabla + 30), (ANCHO - 90, y_tabla + 30)],
        fill=TINTA,
        width=1,
    )
    y_item = y_tabla + 50
    for item in factura["items"]:
        escribir(90, y_item, _linea_tabla(item), fuente)
        y_item += 32

    escribir(90, 1240, "Numero de pedido: {}".format(factura["pedido"]), fuente)
    escribir(90, 1360, "TOTAL KILOGRAMOS   {}".format(
        _numero(factura["total_kilos"])
    ), fuente)
    escribir(90, 1400, "CAE {}  VTO CAE {}".format(
        factura["cae"], factura["vto_cae"]
    ), fuente_chica)

    # El logo y una flecha suelta, como en el escaneo.
    dibujo.ellipse([110, 60, 330, 140], outline=TINTA, width=3)
    dibujo.line([(60, 210), (110, 260)], fill=TINTA, width=2)

    return lienzo


def _efecto_escaneo(imagen, semilla):
    """Le da el aspecto de un documento fotografiado."""
    aleatorio = random.Random(semilla)
    imagen = imagen.rotate(aleatorio.uniform(-0.6, 0.6), resample=Image.BICUBIC, fillcolor=PAPEL)
    imagen = imagen.filter(ImageFilter.GaussianBlur(0.25))

    grano = Image.new("L", imagen.size, 128)
    pixeles = grano.load()
    for x in range(0, imagen.size[0], 2):
        for y in range(0, imagen.size[1], 2):
            valor = aleatorio.randint(118, 138)
            pixeles[x, y] = valor
            if x + 1 < imagen.size[0]:
                pixeles[x + 1, y] = valor
            if y + 1 < imagen.size[1]:
                pixeles[x, y + 1] = valor
    grano = grano.filter(ImageFilter.GaussianBlur(0.4))
    return Image.blend(imagen, Image.merge("RGB", (grano, grano, grano)), 0.035)


def _girar(imagen):
    """Deja la pagina de lado, como las que Tacural escanea torcidas."""
    girada = imagen.rotate(90, expand=True)
    lienzo = Image.new("RGB", (girada.size[0] + 120, girada.size[1] + 120), PAPEL)
    lienzo.paste(girada, (60, 60))
    return lienzo


def generar_pdf_muestra_tacural(destino) -> str:
    """Escribe el PDF de muestra con las facturas definidas en el seed."""
    from utiles.seed_tacural import FACTURAS_MUESTRA

    paginas = []
    for indice, factura in enumerate(FACTURAS_MUESTRA, start=1):
        imagen = _render_factura(factura, indice)
        imagen = _efecto_escaneo(imagen, 1000 + indice)
        if factura.get("girada"):
            imagen = _girar(imagen)
        paginas.append(imagen.convert("RGB"))

    destino = str(destino)
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    paginas[0].save(
        destino,
        "PDF",
        save_all=True,
        append_images=paginas[1:],
        resolution=150.0,
    )
    return destino

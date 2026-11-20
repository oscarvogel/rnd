# coding=utf-8
"""Dibuja un Reporte de viaje de muestra (el PDF de remitos por viaje de Lario).

El archivo real de Lario es un PDF exportado por el sistema: una tabla de 16
columnas, con una fila por remito, los CUIT en un color distinto y una fila
TOTAL al pie. El importador (utiles/importacion_reporte_viaje.py) detecta las
columnas por los rectangulos de la cabecera y recupera el CUIT por color, asi
que el PDF de muestra tiene que respectar esa estructura.

Se dibuja en el momento (no se versiona) por la misma razon que el PDF de
Tacural: el repo no versiona binarios ni datos de clientes. Ademas, el archivo
real lleva clientes, CUIT, direcciones y subtotales de una operacion real, que
no pueden viajar en un instalador publico.

Los clientes del archivo son los clientes ficticios del DEMO.
"""
from __future__ import annotations

import fitz

# Limites de columna del reporte real (en puntos, pagina apaisada 792x612).
# Se replican tal cual para que el importador detecte las mismas columnas.
COLUMNAS = (
    ("PUNTO DE DESCARGA", 51.5, 143.5),
    ("Zona comercial", 143.5, 183.4),
    ("Pedido de Venta", 183.4, 230.2),
    ("Albarán", 230.2, 299.6),
    ("Tipo de producto", 299.6, 339.5),
    ("Cuenta", 339.5, 375.1),
    ("Socio", 375.1, 444.4),
    ("C.U.I.T", 444.4, 473.1),
    ("Calle", 473.1, 542.5),
    ("Ciudad", 542.5, 566.7),
    ("C.P", 566.7, 590.9),
    ("Cajas", 590.9, 615.2),
    ("Subtotal", 615.2, 639.4),
    ("Peso neto", 639.4, 668.1),
    ("Peso bruto", 668.1, 696.8),
    ("Peso congelado", 696.8, 732.3),
)

ANCHO_PAGINA = 792.0
ALTO_PAGINA = 612.0
TOP_CABECERA = 50.0
ALTO_FILA = 5.6
# El export de Lario usa cuerpo de 3,96 pt: con esa letra el CUIT (11
# digitos) entra en su columna de 28,7 pt sin superponerse con la calle.
TAMANO_TEXTO = 4.0
MARGEN = 1.0

COLOR_TEXTO = (0, 0, 0)
COLOR_CUIT = (0.65, 0, 0)
COLOR_BANDA = (0.85, 0.87, 0.92)
COLOR_TOTAL = (0.75, 0.77, 0.82)


def _numero(valor, decimales=2):
    """Formatea como el export: 3778688,89 (coma decimal, sin punto de miles).

    El export de Lario no separa los miles y el importe tiene que entrar en
    su columna de 24 pt, asi que se respeta el mismo formato.
    """
    if valor is None:
        return ""
    texto = "{:.{}f}".format(valor, decimales)
    if decimales == 0:
        return texto
    return texto.replace(".", ",")


def _fila_pdf(fila):
    """Arma una fila del reporte con los 16 valores en el orden del export."""
    return (
        fila["punto"],
        fila["zona"],
        fila["pedido"],
        fila["albaran"],
        fila["tipo"],
        fila["cuenta"],
        fila["socio"],
        fila["cuit"],
        fila["calle"],
        fila["ciudad"],
        fila["cp"],
        _numero(fila["cajas"], 0),
        _numero(fila["subtotal"]),
        _numero(fila["neto"]),
        _numero(fila["bruto"]),
        _numero(fila["congelado"]),
    )


def _recorta(texto, ancho_maximo):
    """Corta el texto al ancho de la celda, como hace el export real.

    El export de Lario no pasa la linea: el nombre del socio queda truncado
    al ancho de su columna y el CUIT empieza justo despues. Si el texto se
    pasa del ancho, se superpone al CUIT y las dos cadenas se mezclan.
    """
    if not texto:
        return ""
    if fitz.get_text_length(texto, fontname="helv", fontsize=TAMANO_TEXTO) <= ancho_maximo:
        return texto
    recortado = ""
    for caracter in texto:
        if fitz.get_text_length(recortado + caracter, fontname="helv", fontsize=TAMANO_TEXTO) > ancho_maximo:
            break
        recortado += caracter
    return recortado.rstrip()


def _escribe_celda(pagina, x0, x1, texto, y, color, derecha=False, recortar=False):
    """Escribe una celda.

    El export real deja el texto desbordar hacia la columna siguiente (por eso
    el C.P. arrastraba letras de la ciudad). Solo el nombre del socio se
    recorta, para que no se mezcle con el CUIT.
    """
    if not texto:
        return
    if recortar:
        texto = _recorta(texto, (x1 - x0) - MARGEN)
    ancho_texto = fitz.get_text_length(texto, fontname="helv", fontsize=TAMANO_TEXTO)
    if derecha:
        x = x1 - MARGEN - ancho_texto
    else:
        x = x0 + MARGEN
    pagina.insert_text((x, y), texto, fontname="helv", fontsize=TAMANO_TEXTO, color=color)


def _dibuja_cabecera(pagina):
    """La banda de la cabecera: un rectangulo por celda (de ahi salen los limites)."""
    alto = 7.0
    for etiqueta, x0, x1 in COLUMNAS:
        pagina.draw_rect(
            fitz.Rect(x0, TOP_CABECERA - 1.0, x1, TOP_CABECERA + alto),
            color=None,
            fill=COLOR_BANDA,
            width=0,
        )
        pagina.insert_text(
            (x0 + MARGEN, TOP_CABECERA + 4.0),
            etiqueta,
            fontname="helv",
            fontsize=TAMANO_TEXTO,
            color=COLOR_TEXTO,
        )


def _dibuja_total(pagina, y, totales):
    """Fila TOTAL: caja gris con los cuatro totales del export."""
    inicio = COLUMNAS[9][1]
    fin = COLUMNAS[13][2]
    pagina.draw_rect(
        fitz.Rect(inicio, y - 5.0, fin, y + 1.0),
        color=None,
        fill=COLOR_TOTAL,
        width=0,
    )
    pagina.insert_text(
        (inicio + MARGEN, y - 1.0),
        "TOTAL",
        fontname="helv",
        fontsize=TAMANO_TEXTO,
        color=COLOR_TEXTO,
    )
    valores = (
        (COLUMNAS[10], _numero(totales["cp"], 0)),
        (COLUMNAS[11], _numero(totales["cajas"], 0)),
        (COLUMNAS[12], _numero(totales["subtotal"])),
        (COLUMNAS[13], _numero(totales["neto"])),
    )
    for (etiqueta, x0, x1), texto in valores:
        _escribe_celda(pagina, x0, x1, texto, y - 1.0, COLOR_TEXTO, derecha=True)


def _filas_de_muestra():
    """Arma las filas del archivo de muestra con los clientes ficticios del DEMO."""
    from utiles.seed_tacural import CLIENTES_TACURAL

    clientes = tuple(
        (
            cliente["codigo"],
            cliente["razon_social"],
            cliente["codigo_cuit"],
            cliente["direccion"],
            cliente["localidad"],
            "330000" if cliente["localidad"] == "Posadas" else "336000",
        )
        for cliente in CLIENTES_TACURAL
    )

    filas = []
    remito = 24732
    albaran = "00901"
    for indice, (cuenta, socio, cuit, calle, ciudad, cp) in enumerate(clientes):
        # Cada cliente con un remito de Carne y otro de Fiambre.
        for tipo, cajas, neto in (("Carne", 30, 599.75), ("Fiambre", 17, 371.87)):
            filas.append(
                {
                    "punto": "DEPOSITO RND (BONDA)",
                    "zona": "226 SO172960",
                    "pedido": "{} SO17{}".format(226 + indice, 2960 + indice),
                    "albaran": "{}-{}".format(albaran, str(remito).zfill(8)),
                    "tipo": tipo,
                    "cuenta": cuenta,
                    "socio": socio,
                    "cuit": cuit,
                    "calle": calle,
                    "ciudad": ciudad,
                    "cp": cp,
                    "cajas": cajas,
                    "subtotal": round(cajas * 125963.0, 2),
                    "neto": neto,
                    "bruto": round(neto * 1.05, 2),
                    "congelado": neto,
                }
            )
            remito += 1

    # Un remito anulado (WR/OUT): sin peso, queda marcado REVISAR.
    filas.append(
        {
            "punto": "DEPOSITO RND (BONDA)",
            "zona": "307 SO172931",
            "pedido": "307 SO172931",
            "albaran": "WR/OUT/35697",
            "tipo": "Carne",
            "cuenta": "985",
            "socio": "ALMACEN CENTRAL",
            "cuit": "30700000139",
            "calle": "PERU 701",
            "ciudad": "OBERA",
            "cp": "336000",
            "cajas": 0,
            "subtotal": 0.0,
            "neto": 0.0,
            "bruto": 0.0,
            "congelado": 0.0,
        }
    )
    # Un remito sin cajas informadas: tambien queda marcado REVISAR.
    filas.append(
        {
            "punto": "DEPOSITO RND (BONDA)",
            "zona": "307 SO172958",
            "pedido": "307 SO172958",
            "albaran": "00901-00024733",
            "tipo": "Carne",
            "cuenta": "5997",
            "socio": "COMERCIO EL ORIENTE",
            "cuit": "30700000121",
            "calle": "RUTA 12 KM 8.5 ESQ. GUARANI",
            "ciudad": "POSADAS",
            "cp": "330000",
            "cajas": None,
            "subtotal": 14570278.85,
            "neto": 1153.68,
            "bruto": 1220.47,
            "congelado": 1153.68,
        }
    )
    return filas


def generar_pdf_muestra_lario(destino, filas=None) -> str:
    """Escribe el Reporte de viaje de muestra y devuelve la ruta.

    Se pueden pasar filas propias (mismo formato que las de muestra) para
    probar casos puntuales del importador.
    """
    if filas is None:
        filas = _filas_de_muestra()

    documento = fitz.open()
    pagina = documento.new_page(width=ANCHO_PAGINA, height=ALTO_PAGINA)
    _dibuja_cabecera(pagina)

    y = TOP_CABECERA + 9.0
    for fila in filas:
        valores = _fila_pdf(fila)
        for indice, ((etiqueta, x0, x1), texto) in enumerate(zip(COLUMNAS, valores)):
            color = COLOR_CUIT if indice == 7 else COLOR_TEXTO
            derecha = indice >= 11
            _escribe_celda(
                pagina, x0, x1, texto, y, color,
                derecha=derecha,
                recortar=(indice == 6),
            )
        y += ALTO_FILA

    totales = {
        "cp": 0,
        "cajas": sum(fila["cajas"] or 0 for fila in filas),
        "subtotal": round(sum(fila["subtotal"] for fila in filas), 2),
        "neto": round(sum(fila["neto"] for fila in filas), 2),
    }
    _dibuja_total(pagina, y + 4.0, totales)

    destino = str(destino)
    documento.save(destino, deflate=True)
    documento.close()
    return destino

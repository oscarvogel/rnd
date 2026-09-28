# coding=utf-8
"""Identidad fisica del pallet: codigo, QR y etiqueta (Issue #68, Epic #58).

El payload QR lleva namespace propio para no confundirse con otros
codigos: ``RND-PALLET:<CODIGO>``. La etiqueta nunca asume un unico
cliente o destino: lista todos los destinos del pallet.
"""

from __future__ import annotations

import os
import tempfile

PREFIJO_QR = "RND-PALLET"


def normalizar_codigo(codigo) -> str:
    """Codigo canonico para comparar lo escaneado/ingresado."""
    return str(codigo or "").strip().upper()


def payload_qr(codigo) -> str:
    """Contenido del QR. Vacio si el codigo es vacio."""
    codigo = normalizar_codigo(codigo)
    if not codigo:
        return ""
    return "{}:{}".format(PREFIJO_QR, codigo)


def codigo_desde_payload(payload) -> str:
    """Recupera el codigo desde un QR escaneado (tolerante)."""
    texto = str(payload or "").strip()
    if not texto:
        return ""
    if ":" in texto:
        prefijo, _, resto = texto.partition(":")
        if prefijo.strip().upper() == PREFIJO_QR:
            return normalizar_codigo(resto)
    return normalizar_codigo(texto)


def generar_qr_png(codigo, destino=None, box_size=10, border=4) -> str:
    """Genera el PNG del QR y devuelve su ruta."""
    import qrcode

    payload = payload_qr(codigo)
    if not payload:
        raise ValueError("Código de pallet vacío.")
    if destino is None:
        destino = os.path.join(
            tempfile.gettempdir(),
            "etiqueta_{}.png".format(normalizar_codigo(codigo)),
        )
    imagen = qrcode.make(payload, box_size=box_size, border=border)
    imagen.save(destino)
    return destino


def lineas_resumen(destinos) -> list:
    """Lineas de destino para la etiqueta (multi-cliente seguro)."""
    lineas = []
    for destino in destinos or []:
        lineas.append(
            "{} / {}: {} cant".format(
                destino.get("cliente") or "Sin cliente",
                destino.get("lugar_entrega") or "Sin lugar",
                destino.get("cantidad", 0),
            )
        )
    return lineas


def generar_pdf_etiqueta(codigo, totales, destinos, qr_png, destino_pdf=None) -> str:
    """Etiqueta 100x150mm: codigo grande, QR y resumen minimo."""
    from fpdf import FPDF

    codigo = normalizar_codigo(codigo)
    if not codigo:
        raise ValueError("Código de pallet vacío.")
    if destino_pdf is None:
        destino_pdf = os.path.join(
            "documentacion", "Etiqueta_{}.pdf".format(codigo)
        )
    directorio = os.path.dirname(destino_pdf)
    if directorio and not os.path.exists(directorio):
        os.makedirs(directorio)

    pdf = FPDF(orientation="P", unit="mm", format=(100, 150))
    pdf.set_auto_page_break(auto=False)
    pdf.add_page()
    pdf.set_font("Arial", "B", 26)
    pdf.cell(0, 14, codigo, 0, 1, "C")
    pdf.set_font("Arial", "", 11)
    pdf.cell(
        0, 7,
        "PALLET RND - escanee para validar la carga",
        0, 1, "C",
    )
    if qr_png and os.path.exists(qr_png):
        pdf.image(qr_png, x=20, y=38, w=60, h=60)
    pdf.set_y(102)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(
        0, 7,
        "Lineas: {}   Cant: {}   KG: {}   Bultos: {}".format(
            totales.get("lineas", 0), totales.get("cantidad", 0),
            totales.get("kg", 0), totales.get("bultos", 0),
        ),
        0, 1, "C",
    )
    pdf.set_font("Arial", "", 10)
    for linea in lineas_resumen(destinos)[:8]:
        pdf.cell(0, 6, linea[:60], 0, 1, "L")
    pdf.output(destino_pdf)
    return destino_pdf

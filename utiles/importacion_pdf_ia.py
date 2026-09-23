# coding=utf-8
"""Extraccion de pedidos desde PDF o imagen usando un endpoint de vision IA.

El modulo no graba datos en RND. Solo transforma documentos escaneados a una
lista de filas normalizadas que luego pasan por la vista previa y las mismas
validaciones del importador Excel.

Configuracion por variables de entorno:
- RND_PDF_AI_URL: endpoint OpenAI-compatible de chat/completions.
- RND_PDF_AI_API_KEY: credencial del servicio.
- RND_PDF_AI_MODEL: modelo con vision habilitada.
- RND_PDF_AI_TIMEOUT: timeout por pagina en segundos (opcional, default 120).

Las credenciales nunca se persisten ni se imprimen.
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Iterable

import fitz
from dotenv import load_dotenv


load_dotenv()


_EXT_IMAGEN = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

_SYSTEM_PROMPT = """Sos un extractor de pedidos para un sistema logistico.
Debes leer UNA pagina de un PDF o imagen de proveedor y devolver exclusivamente
JSON valido. No inventes datos. Si un dato no se ve, usa string vacio o null.

La pagina puede ser una FACTURA, NOTA DE PEDIDO, REMITO u otro documento.
Extrae datos utiles para reparto, no impuestos ni totales contables.

Esquema exacto:
{
  "documento": {
    "tipo": "FACTURA|NOTA_PEDIDO|REMITO|OTRO",
    "numero": "",
    "fecha": "",
    "cliente_codigo": "",
    "cliente_nombre": "",
    "cuit": "",
    "domicilio": "",
    "localidad": "",
    "provincia": "",
    "confianza": 0.0,
    "advertencias": []
  },
  "items": [
    {
      "codigo": "",
      "descripcion": "",
      "cantidad": null,
      "bultos": null,
      "kilos": null,
      "confianza": 0.0,
      "advertencias": []
    }
  ]
}

Reglas:
- cantidad es la cantidad/unidades/hormas/cajas despachadas que figure en la linea.
- bultos debe usar Cajas/Bultos si existe; si no existe, puede repetir cantidad.
- kilos debe conservar decimales.
- numero debe ser el numero de factura/nota/remito visible.
- cliente_codigo debe usar Nro.Cliente/codigo de cliente si existe.
- no confundas precios, importes o totales monetarios con kilos/cantidad.
- una pagina sin pedido reconocible debe devolver items=[].
- confianza va de 0 a 1.
- agrega advertencias si un sello, firma, arruga o baja calidad tapa un dato.
"""

_USER_PROMPT = """Extrae esta pagina para importarla a RND.
Prioriza cliente, localidad, domicilio, documento y lineas de productos.
Devuelve solamente JSON con el esquema indicado."""


class ConfiguracionPdfIAError(ValueError):
    """Configuracion incompleta del proveedor de vision IA."""


class ExtraccionPdfIAError(ValueError):
    """La IA o el documento no pudieron convertirse a pedidos validos."""


def _texto(valor) -> str:
    if valor is None:
        return ""
    return str(valor).strip()


def _numero(valor):
    if valor is None or valor == "":
        return ""
    if isinstance(valor, (int, float)):
        return valor
    texto = str(valor).strip()
    if not texto:
        return ""
    texto = texto.replace(" ", "")
    # Soportar 1.234,56 y 1234.56 sin confundir miles/decimales.
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    try:
        numero = float(texto)
        return int(numero) if numero.is_integer() else numero
    except ValueError:
        return valor


def _clave_nombre(nombre: str) -> str:
    texto = unicodedata.normalize("NFKD", _texto(nombre))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"\s+", " ", texto.upper()).strip()
    return ("NOMBRE:" + texto)[:100] if texto else ""


def _configuracion() -> tuple[str, str, str, int]:
    # RND permite sobreescribir proveedor/modelo, pero por defecto reutiliza
    # la configuracion MiniMax-M3 que ya usamos en otros servicios Vogel.
    url = (
        _texto(os.getenv("RND_PDF_AI_URL"))
        or _texto(os.getenv("GROUP_SUMMARY_AI_CHAT_URL"))
        or "https://api.minimax.io/v1/chat/completions"
    )
    api_key = (
        _texto(os.getenv("RND_PDF_AI_API_KEY"))
        or _texto(os.getenv("MINIMAX_API_KEY"))
        or _texto(os.getenv("GROUP_SUMMARY_AI_API_KEY"))
    )
    model = (
        _texto(os.getenv("RND_PDF_AI_MODEL"))
        or _texto(os.getenv("MINIMAX_MODEL"))
        or _texto(os.getenv("GROUP_SUMMARY_AI_MODEL"))
        or "MiniMax-M3"
    )
    timeout_raw = _texto(os.getenv("RND_PDF_AI_TIMEOUT") or "120")

    if not api_key:
        raise ConfiguracionPdfIAError(
            "Para importar PDF/imagen con IA falta la API key. "
            "Configure RND_PDF_AI_API_KEY o MINIMAX_API_KEY y vuelva a intentar."
        )
    try:
        timeout = max(15, int(timeout_raw))
    except ValueError:
        timeout = 120
    return url, api_key, model, timeout


def _extraer_json(texto: str) -> dict:
    contenido = _texto(texto)
    if not contenido:
        raise ExtraccionPdfIAError("La IA devolvio una respuesta vacia")

    # MiniMax-M3 puede anteponer un bloque <think>...</think>. No forma parte
    # del resultado estructurado y debe descartarse antes de buscar el JSON.
    contenido = re.sub(
        r"<think>.*?</think>",
        "",
        contenido,
        flags=re.I | re.S,
    ).strip()

    if contenido.startswith("```"):
        contenido = re.sub(r"^```(?:json)?\s*", "", contenido, flags=re.I)
        contenido = re.sub(r"\s*```$", "", contenido)
    inicio = contenido.find("{")
    fin = contenido.rfind("}")
    if inicio < 0 or fin < inicio:
        raise ExtraccionPdfIAError("La IA no devolvio JSON reconocible")
    try:
        data = json.loads(contenido[inicio:fin + 1])
    except json.JSONDecodeError as exc:
        raise ExtraccionPdfIAError(
            "La IA devolvio JSON invalido: {}".format(exc)
        ) from exc
    if not isinstance(data, dict):
        raise ExtraccionPdfIAError("La respuesta IA no tiene formato de objeto")
    return data


def _contenido_respuesta(payload: dict) -> str:
    try:
        contenido = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ExtraccionPdfIAError(
            "El endpoint IA respondio con un formato no compatible"
        ) from exc

    if isinstance(contenido, str):
        return contenido
    if isinstance(contenido, list):
        partes = []
        for bloque in contenido:
            if isinstance(bloque, dict):
                texto = bloque.get("text")
                if texto:
                    partes.append(str(texto))
        return "\n".join(partes)
    return str(contenido or "")


def _llamar_vision(
    imagen_bytes: bytes,
    mime_type: str,
    *,
    url: str,
    api_key: str,
    model: str,
    timeout: int,
) -> dict:
    data_url = "data:{};base64,{}".format(
        mime_type,
        base64.b64encode(imagen_bytes).decode("ascii"),
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _USER_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url},
                    },
                ],
            },
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer {}".format(api_key),
            "Content-Type": "application/json",
        },
        method="POST",
    )
    raw = None
    ultimo_error = None
    for intento in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
            break
        except urllib.error.HTTPError as exc:
            ultimo_error = exc
            detalle = ""
            try:
                detalle = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detalle = ""
            detalle = detalle[:500]
            if exc.code in {429, 500, 502, 503, 504} and intento < 3:
                time.sleep(float(intento))
                continue
            raise ExtraccionPdfIAError(
                "El servicio de IA rechazo la pagina (HTTP {}). {}"
                .format(exc.code, detalle)
            ) from exc
        except urllib.error.URLError as exc:
            ultimo_error = exc
            if intento < 3:
                time.sleep(float(intento))
                continue
            raise ExtraccionPdfIAError(
                "No se pudo conectar con el servicio de IA: {}".format(exc.reason)
            ) from exc

    if raw is None:
        raise ExtraccionPdfIAError(
            "No se obtuvo respuesta del servicio de IA: {}".format(ultimo_error)
        )

    try:
        response_payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExtraccionPdfIAError(
            "El servicio de IA devolvio una respuesta no JSON"
        ) from exc
    return _extraer_json(_contenido_respuesta(response_payload))


def _imagenes_desde_archivo(path: Path) -> list[tuple[bytes, str]]:
    extension = path.suffix.lower()
    if extension in _EXT_IMAGEN:
        return [(path.read_bytes(), _EXT_IMAGEN[extension])]
    if extension != ".pdf":
        raise ValueError(
            "Formato no soportado para IA: {}. Use PDF, PNG, JPG o JPEG."
            .format(extension or "sin extension")
        )

    imagenes = []
    try:
        documento = fitz.open(str(path))
    except Exception as exc:
        raise ExtraccionPdfIAError(
            "No se pudo abrir el PDF: {}".format(exc)
        ) from exc

    try:
        if documento.page_count == 0:
            raise ExtraccionPdfIAError("El PDF no contiene paginas")
        matriz = fitz.Matrix(1.7, 1.7)
        for pagina in documento:
            pix = pagina.get_pixmap(matrix=matriz, alpha=False)
            imagenes.append((pix.tobytes("png"), "image/png"))
    finally:
        documento.close()
    return imagenes


def _advertencias(*fuentes: Iterable[str]) -> list[str]:
    salida = []
    for fuente in fuentes:
        if not fuente:
            continue
        valores = [fuente] if isinstance(fuente, str) else fuente
        for valor in valores:
            texto = _texto(valor)
            if texto and texto not in salida:
                salida.append(texto)
    return salida


def _normalizar_documento(data: dict, numero_pagina: int) -> list[dict]:
    documento = data.get("documento") or {}
    items = data.get("items") or []
    if not isinstance(documento, dict) or not isinstance(items, list):
        raise ExtraccionPdfIAError(
            "La pagina {} no respeta el esquema esperado".format(numero_pagina)
        )

    cliente_nombre = _texto(documento.get("cliente_nombre"))
    cliente_codigo = (
        _texto(documento.get("cliente_codigo"))
        or _texto(documento.get("cuit"))
        or _clave_nombre(cliente_nombre)
    )
    localidad = _texto(documento.get("localidad"))
    domicilio = _texto(documento.get("domicilio"))
    cuit = _texto(documento.get("cuit"))
    numero_documento = _texto(documento.get("numero"))
    tipo_documento = _texto(documento.get("tipo") or "OTRO").upper()
    fecha = _texto(documento.get("fecha"))
    confianza_doc = documento.get("confianza")
    advertencias_doc = documento.get("advertencias") or []

    filas = []
    for item in items:
        if not isinstance(item, dict):
            continue
        descripcion = _texto(item.get("descripcion"))
        codigo_producto = _texto(item.get("codigo"))
        cantidad = _numero(item.get("cantidad"))
        bultos = _numero(item.get("bultos"))
        kilos = _numero(item.get("kilos"))
        if bultos in ("", None):
            bultos = cantidad

        # Una linea util debe tener producto y al menos una magnitud.
        if not descripcion and not codigo_producto:
            continue
        if cantidad in ("", None) and kilos in ("", None):
            continue

        advertencias = _advertencias(
            advertencias_doc,
            item.get("advertencias") or [],
        )
        confianza_item = item.get("confianza")
        confianza = confianza_item if confianza_item is not None else confianza_doc

        observaciones = [
            "Origen IA pagina {}".format(numero_pagina),
            "{} {}".format(tipo_documento, numero_documento).strip(),
            "Fecha: {}".format(fecha) if fecha else "",
            "Domicilio: {}".format(domicilio) if domicilio else "",
            "CUIT: {}".format(cuit) if cuit else "",
            "Codigo producto: {}".format(codigo_producto) if codigo_producto else "",
        ]
        try:
            confianza_num = float(confianza)
        except (TypeError, ValueError):
            confianza_num = None
        if confianza_num is not None and confianza_num < 0.80:
            observaciones.append(
                "REVISAR IA: confianza {:.0f}%".format(confianza_num * 100)
            )
        if advertencias:
            observaciones.append(
                "REVISAR IA: {}".format("; ".join(advertencias))
            )

        faltantes_criticos = []
        if not cliente_nombre:
            faltantes_criticos.append("cliente")
        if not numero_documento:
            faltantes_criticos.append("documento")
        if not localidad:
            faltantes_criticos.append("localidad")
        if not descripcion and not codigo_producto:
            faltantes_criticos.append("producto")
        if cantidad in ("", None):
            faltantes_criticos.append("cantidad")
        if faltantes_criticos:
            observaciones.append(
                "REVISAR IA: faltan {}".format(", ".join(faltantes_criticos))
            )

        filas.append({
            "codigo_cliente": cliente_codigo,
            "detalle_cliente": cliente_nombre,
            "destino": localidad,
            "comprobante": numero_documento,
            "cantidad": cantidad,
            "producto": descripcion or codigo_producto,
            "bultos": bultos,
            "kilos": kilos,
            "observaciones": " | ".join(x for x in observaciones if x),
        })
    return filas


def extraer_pedidos_pdf_ia(
    archivo_entrada: str,
    progreso: Callable[[int], None] | None = None,
) -> list[dict]:
    """Extrae y normaliza pedidos desde PDF/imagen sin grabarlos en la base."""
    path = Path(archivo_entrada)
    if not path.exists():
        raise FileNotFoundError(archivo_entrada)

    url, api_key, model, timeout = _configuracion()
    imagenes = _imagenes_desde_archivo(path)
    total = max(len(imagenes), 1)
    filas = []

    if progreso:
        progreso(5)

    for indice, (imagen_bytes, mime_type) in enumerate(imagenes, start=1):
        if progreso:
            progreso(5 + int((indice - 1) / total * 85))
        data = _llamar_vision(
            imagen_bytes,
            mime_type,
            url=url,
            api_key=api_key,
            model=model,
            timeout=timeout,
        )
        filas.extend(_normalizar_documento(data, indice))
        if progreso:
            progreso(5 + int(indice / total * 85))

    if not filas:
        raise ExtraccionPdfIAError(
            "No se encontraron pedidos reconocibles en el PDF/imagen. "
            "Revise la calidad del archivo o el modelo IA configurado."
        )

    if progreso:
        progreso(100)
    return filas

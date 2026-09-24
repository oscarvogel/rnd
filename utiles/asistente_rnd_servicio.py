# coding=utf-8
"""Servicio de respuestas del Asistente RND usando MiniMax/OpenAI-compatible."""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from utiles.asistente_rnd_conocimiento import (
    knowledge_for_prompt,
    match_article,
)
from utiles.asistente_rnd_store import record_unresolved


def _load_env():
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
    else:
        root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=root / ".env", override=False)


_load_env()


SYSTEM_PROMPT = """Sos el Asistente RND, especializado exclusivamente en enseñar a usar RND Logística.

OBJETIVO:
- Resolver dudas de funcionamiento del sistema.
- Explicar pasos operativos usando nombres reales de pantallas y acciones.
- Ayudar a entender qué sigue en el flujo Importar -> Revisar -> Organizar -> Asignar -> Revisar -> Imprimir.

REGLAS ESTRICTAS:
- No inventes botones, pantallas, estados, permisos ni datos.
- No afirmes que ejecutaste acciones. El asistente sólo orienta.
- No respondas conocimiento general fuera de RND.
- Si la pregunta no es sobre RND, devolvé scope="out".
- Si es sobre RND pero la base suministrada no alcanza para contestar con seguridad, devolvé resolved=false.
- Usá sólo el conocimiento operativo incluido en este prompt.
- Si la pregunta dice "acá", "ahora", "después" o similar, usá PANTALLA ACTUAL como contexto.
- Preferí respuestas breves y pasos numerados.
- No sugieras repetir una importación fallida sin verificar antes posibles duplicados.

Respondé EXCLUSIVAMENTE JSON válido con esta forma:
{
  "scope": "rnd" | "out",
  "resolved": true | false,
  "answer": "texto de respuesta"
}
"""


OUT_OF_SCOPE = (
    "Mi función está limitada a ayudarte con el uso de RND Logística. "
    "No respondo consultas generales ajenas al sistema."
)

UNRESOLVED = (
    "No tengo información suficiente en la base de conocimiento de RND para "
    "responder eso con seguridad. Dejé registrada la consulta para revisión."
)


def _config():
    url = (
        (os.getenv("RND_ASSISTANT_AI_URL") or "").strip()
        or (os.getenv("RND_PDF_AI_URL") or "").strip()
        or "https://api.minimax.io/v1/chat/completions"
    )
    key = (
        (os.getenv("RND_ASSISTANT_AI_API_KEY") or "").strip()
        or (os.getenv("RND_PDF_AI_API_KEY") or "").strip()
        or (os.getenv("MINIMAX_API_KEY") or "").strip()
    )
    model = (
        (os.getenv("RND_ASSISTANT_AI_MODEL") or "").strip()
        or (os.getenv("RND_PDF_AI_MODEL") or "").strip()
        or (os.getenv("MINIMAX_MODEL") or "").strip()
        or "MiniMax-M3"
    )
    try:
        timeout = max(10, int(os.getenv("RND_ASSISTANT_AI_TIMEOUT") or "45"))
    except ValueError:
        timeout = 45
    return url, key, model, timeout


def _strip_reasoning(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.I | re.S).strip()


def _extract_json(text: str) -> dict:
    text = _strip_reasoning(text)
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("respuesta sin JSON")
    value = json.loads(text[start:end + 1])
    if not isinstance(value, dict):
        raise ValueError("respuesta JSON no es objeto")
    return value


def _content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    value = (choices[0].get("message") or {}).get("content", "")
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(
            str(item.get("text"))
            for item in value
            if isinstance(item, dict) and item.get("text")
        )
    return str(value or "")


def answer_message(question: str, context: str = "", history=None) -> dict:
    question = (question or "").strip()
    if not question:
        return {"content": "", "source": "empty", "resolved": False}

    direct = match_article(question, context=context)
    if direct is not None:
        return {
            "content": direct.get("answer", ""),
            "source": "knowledge",
            "resolved": True,
            "article_id": direct.get("id"),
        }

    url, key, model, timeout = _config()
    if not key:
        record_unresolved(question, context, source="ai_not_configured")
        return {
            "content": (
                "La consulta no coincide con un procedimiento conocido y la IA del "
                "Asistente RND no está configurada. La pregunta quedó registrada."
            ),
            "source": "fallback",
            "resolved": False,
        }

    messages = [{
        "role": "system",
        "content": (
            SYSTEM_PROMPT
            + "\n\nPANTALLA ACTUAL:\n" + (context or "No identificada")
            + "\n\nBASE DE CONOCIMIENTO RND:\n" + knowledge_for_prompt()
        ),
    }]
    for item in (history or [])[-10:]:
        role = item.get("role")
        body = (item.get("content") or "").strip()
        if role in {"user", "assistant"} and body:
            messages.append({"role": role, "content": body})
    messages.append({"role": "user", "content": question})

    payload = {
        "model": model,
        "thinking": {"type": "disabled"},
        "temperature": 0.1,
        "max_completion_tokens": 1200,
        "messages": messages,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer {}".format(key),
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = json.loads(response.read().decode("utf-8"))
        result = _extract_json(_content(raw))
    except (OSError, ValueError, KeyError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return {
            "content": (
                "No pude consultar la IA en este momento. Podés seguir usando las "
                "preguntas sugeridas y los procedimientos conocidos de RND."
            ),
            "source": "error",
            "resolved": False,
        }

    if result.get("scope") == "out":
        return {"content": OUT_OF_SCOPE, "source": "scope", "resolved": True}

    if not bool(result.get("resolved")):
        record_unresolved(question, context, source="ai_unresolved")
        return {"content": UNRESOLVED, "source": "unresolved", "resolved": False}

    answer = (result.get("answer") or "").strip()
    if not answer:
        record_unresolved(question, context, source="ai_empty")
        return {"content": UNRESOLVED, "source": "unresolved", "resolved": False}
    return {"content": answer, "source": "ai", "resolved": True}

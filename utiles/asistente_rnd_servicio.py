# coding=utf-8
"""Asistente RND IA-first sobre MiniMax/OpenAI-compatible.

Toda consulta funcional llega primero al modelo. Python no intenta reconocer
intenciones ni procedimientos mediante palabras clave, aliases o árboles de
decisión. El modelo recibe contexto de pantalla, conversación y conocimiento
RND, y devuelve una decisión estructurada.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

from utiles.asistente_rnd_conocimiento import knowledge_for_prompt
from utiles.asistente_rnd_store import record_unresolved


def _load_env():
    if getattr(sys, "frozen", False):
        root = Path(sys.executable).resolve().parent
    else:
        root = Path(__file__).resolve().parents[1]
    load_dotenv(dotenv_path=root / ".env", override=False)


_load_env()


SYSTEM_PROMPT = """Sos el Asistente RND, un agente IA especializado exclusivamente en enseñar a usar RND Logística.

PRINCIPIO IA-FIRST:
Vos interpretás la pregunta. No existe un router de keywords antes de vos.
Analizá libremente la consulta, la pantalla actual, el historial y toda la base
de conocimiento. Elegí qué información es pertinente y sintetizá la respuesta.

OBJETIVO:
- Resolver dudas de funcionamiento de RND.
- Explicar pasos operativos usando nombres reales de pantallas y acciones.
- Entender preguntas naturales como "¿qué hago ahora?", "¿por qué no me deja?",
  "¿qué sigue?", aunque no coincidan literalmente con el manual.
- Combinar más de un artículo de conocimiento cuando sea necesario.

REGLAS:
- No inventes botones, pantallas, estados, permisos ni datos.
- No afirmes que ejecutaste una acción: este asistente sólo orienta.
- No uses conocimiento general para completar huecos del procedimiento.
- Si la consulta no pertenece a RND, elegí status="out_of_scope".
- Si pertenece a RND pero el conocimiento entregado no alcanza para responder
  con seguridad, elegí status="unresolved".
- Si podés responder de forma fundada, elegí status="answered".
- La PANTALLA ACTUAL es contexto, no una restricción: una pregunta puede referirse
  a otra parte de RND.
- Preferí respuestas breves y pasos numerados cuando sean útiles.
- Ante una importación fallida, no sugieras repetirla sin verificar duplicados.
- sources debe contener los IDs de los artículos realmente usados.

Respondé EXCLUSIVAMENTE JSON válido:
{
  "status": "answered" | "unresolved" | "out_of_scope",
  "answer": "respuesta para el usuario",
  "sources": ["id_articulo"],
  "reason": "explicación breve de por qué tomaste esa decisión"
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


def _messages(question: str, context: str, history) -> list:
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
    return messages


def answer_message(question: str, context: str = "", history=None) -> dict:
    question = (question or "").strip()
    if not question:
        return {"content": "", "source": "empty", "resolved": False}

    url, key, model, timeout = _config()
    if not key:
        record_unresolved(question, context, source="ai_not_configured")
        return {
            "content": (
                "El Asistente RND necesita MiniMax para interpretar las consultas. "
                "No hay una API key configurada y la pregunta quedó registrada."
            ),
            "source": "not_configured",
            "resolved": False,
        }

    payload = {
        "model": model,
        "thinking": {"type": "disabled"},
        "temperature": 0.1,
        "max_completion_tokens": 1400,
        "messages": _messages(question, context, history),
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
        decision = _extract_json(_content(raw))
    except (OSError, ValueError, KeyError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return {
            "content": "No pude consultar MiniMax en este momento. Intentá nuevamente.",
            "source": "ai_error",
            "resolved": False,
        }

    status = str(decision.get("status") or "").strip()
    sources = decision.get("sources")
    if not isinstance(sources, list):
        sources = []

    if status == "out_of_scope":
        return {
            "content": OUT_OF_SCOPE,
            "source": "ai",
            "decision": status,
            "resolved": True,
            "sources": sources,
        }

    if status != "answered":
        record_unresolved(question, context, source="ai_unresolved")
        return {
            "content": UNRESOLVED,
            "source": "ai",
            "decision": "unresolved",
            "resolved": False,
            "sources": sources,
        }

    answer = str(decision.get("answer") or "").strip()
    if not answer:
        record_unresolved(question, context, source="ai_empty")
        return {
            "content": UNRESOLVED,
            "source": "ai",
            "decision": "unresolved",
            "resolved": False,
            "sources": sources,
        }

    return {
        "content": answer,
        "source": "ai",
        "decision": "answered",
        "resolved": True,
        "sources": sources,
    }

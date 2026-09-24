# coding=utf-8
"""Cliente textual del Asistente RND.

La IA interpreta lenguaje libre, pero recibe una única base de conocimiento
canónica y versionada con el código. No hay router de intenciones ni respuestas
por frases exactas.
"""
from __future__ import annotations

from pathlib import Path

from utiles.importacion_pdf_ia import llamar_minimax_texto


SYSTEM_PROMPT = """Sos un asistente de ayuda para usuarios de RND Logistica.

Tu unico dominio es el uso del sistema RND. Responde usando solamente la base
de conocimiento canonica que se adjunta abajo.

Reglas:
- Interpreta la pregunta libremente. No dependas de palabras exactas.
- Explica pasos concretos y breves.
- Usa los nombres de pantallas y acciones que figuran en el conocimiento.
- No inventes botones, funciones, estados, filtros ni restricciones.
- No afirmes que hiciste una accion dentro del sistema.
- No deduzcas que una funcion no existe solo porque no se menciona en una
  seccion concreta. Solo afirma que algo no esta soportado cuando la base
  canonica lo diga expresamente.
- Ante una pregunta sobre formatos o capacidades, busca primero la regla
  explicita de la base antes de inferir por experiencia general.
- Si la pregunta es sobre RND pero el conocimiento no alcanza, decilo
  claramente.
- Si la pregunta no es sobre RND, explica brevemente que solo podes ayudar con
  RND.
- Si la pregunta pide como lo hace internamente y ese mecanismo esta explicado
  en el conocimiento, podes explicarlo en lenguaje operativo sin mostrar codigo.
- Responde como texto normal. NO devuelvas JSON.
"""


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _leer_conocimiento() -> str:
    """Carga únicamente la base canónica validada contra el código actual."""
    ruta = _root() / "docs" / "asistente_rnd_conocimiento_tecnico.md"
    if not ruta.exists():
        raise RuntimeError("No se encontro la base de conocimiento canonica de RND")

    texto = ruta.read_text(encoding="utf-8").strip()
    if not texto:
        raise RuntimeError("La base de conocimiento canonica de RND esta vacia")

    return "### {}\n{}".format(ruta.name, texto)


def preguntar(pregunta: str, historial=None, contexto: str = "") -> str:
    """Pregunta a MiniMax y devuelve texto plano.

    No interpreta la intencion en Python y no exige un contrato JSON.
    """
    pregunta = str(pregunta or "").strip()
    if not pregunta:
        raise ValueError("La pregunta esta vacia")

    conocimiento = _leer_conocimiento()
    messages = [{
        "role": "system",
        "content": (
            SYSTEM_PROMPT
            + "\n\nPANTALLA / CONTEXTO ACTUAL:\n"
            + (str(contexto or "").strip() or "No identificado")
            + "\n\nCONOCIMIENTO RND DISPONIBLE:\n"
            + conocimiento
        ),
    }]

    for item in (historial or [])[-8:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": pregunta})

    return llamar_minimax_texto(
        messages,
        max_completion_tokens=1400,
        temperature=0.1,
    )

# coding=utf-8
"""Spike minimo del Asistente RND.

No tiene UI, persistencia, auditoria ni router de intenciones. Su unico objetivo
es probar de punta a punta que una pregunta de usuario puede enviarse a MiniMax
con conocimiento real de RND y volver como texto util.
"""
from __future__ import annotations

from pathlib import Path

from utiles.importacion_pdf_ia import llamar_minimax_texto


SYSTEM_PROMPT = """Sos un asistente de ayuda para usuarios de RND Logistica.

Tu unico dominio es el uso del sistema RND. Responde usando solamente el
conocimiento RND que se adjunta abajo.

Reglas:
- Interpreta la pregunta libremente. No dependas de palabras exactas.
- Explica pasos concretos y breves.
- Usa los nombres de pantallas y acciones que figuran en el conocimiento.
- No inventes botones, funciones, estados ni datos.
- No afirmes que hiciste una accion dentro del sistema.
- Si la pregunta es sobre RND pero el conocimiento no alcanza, decilo
  claramente.
- Si la pregunta no es sobre RND, explica brevemente que solo podes ayudar con
  RND.
- Responde como texto normal. NO devuelvas JSON.
"""


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _leer_conocimiento() -> str:
    """Carga documentacion versionada del repo para este spike."""
    root = _root()
    rutas = [
        root / "docs" / "manual_usuario_importacion_hoja_ruta.md",
        root / "docs" / "guia_usuario.md",
    ]
    partes = []
    for ruta in rutas:
        if not ruta.exists():
            continue
        texto = ruta.read_text(encoding="utf-8").strip()
        if texto:
            partes.append(
                "### {}\n{}".format(ruta.name, texto)
            )
    if not partes:
        raise RuntimeError("No se encontro documentacion RND para el asistente")
    return "\n\n".join(partes)


def preguntar(pregunta: str, historial=None) -> str:
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

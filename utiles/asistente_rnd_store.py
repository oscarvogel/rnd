# coding=utf-8
"""Persistencia local del Asistente RND.

Se usa LOCALAPPDATA para que el conocimiento editable y las consultas no
resueltas sobrevivan a upgrades/reinstalaciones del ejecutable. En tests puede
sobreescribirse con RND_ASSISTANT_DATA_DIR.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path


def data_dir() -> Path:
    override = (os.getenv("RND_ASSISTANT_DATA_DIR") or "").strip()
    if override:
        root = Path(override)
    else:
        root = Path(
            os.getenv("LOCALAPPDATA")
            or os.getenv("APPDATA")
            or (Path.home() / ".rnd")
        ) / "RND" / "asistente"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _knowledge_path() -> Path:
    return data_dir() / "knowledge.json"


def _unresolved_path() -> Path:
    return data_dir() / "unresolved.jsonl"


def load_knowledge_overrides() -> dict:
    path = _knowledge_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    articles = data.get("articles", {})
    return articles if isinstance(articles, dict) else {}


def save_knowledge_override(article: dict) -> None:
    article_id = str(article.get("id") or "").strip()
    if not article_id:
        raise ValueError("El articulo necesita un id")
    overrides = load_knowledge_overrides()
    overrides[article_id] = article
    payload = {"version": 1, "articles": overrides}
    path = _knowledge_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


def record_unresolved(question: str, context: str = "", source: str = "assistant") -> None:
    question = (question or "").strip()
    if not question:
        return
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "context": (context or "").strip(),
        "question": question,
        "source": source,
        "status": "pending",
    }
    with _unresolved_path().open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def list_unresolved(limit: int = 500) -> list:
    path = _unresolved_path()
    if not path.exists():
        return []
    rows = []
    try:
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows[-max(1, int(limit)):]

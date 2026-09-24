# coding=utf-8
import json

from utiles.asistente_rnd_conocimiento import match_article, suggestions_for_context
from utiles.asistente_rnd_servicio import OUT_OF_SCOPE, answer_message


def test_conocimiento_detecta_importacion_pdf():
    article = match_article("¿Cómo importo un PDF con IA?", context="ImportacionPedidos")
    assert article is not None
    assert article["id"] == "importar_pdf"


def test_conocimiento_usa_contexto_para_organizar():
    article = match_article("¿qué hago en organizar pedidos?", context="BandejaPedidos")
    assert article is not None
    assert article["id"] == "organizar_pedidos"


def test_sugerencias_dependen_de_pantalla():
    suggestions = suggestions_for_context("AsignacionRecursos")
    assert any("chofer" in item.lower() for item in suggestions)


def test_respuesta_conocida_no_necesita_api(monkeypatch):
    monkeypatch.delenv("RND_ASSISTANT_AI_API_KEY", raising=False)
    monkeypatch.delenv("RND_PDF_AI_API_KEY", raising=False)
    monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
    result = answer_message("¿Cómo genero el PDF?", context="VerHojaRuta")
    assert result["source"] == "knowledge"
    assert result["resolved"] is True
    assert "Imprimir" in result["content"]


def test_fuera_de_alcance_descarta_respuesta_general(monkeypatch):
    monkeypatch.setenv("RND_ASSISTANT_AI_API_KEY", "test-key")

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def read(self):
            body = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "scope": "out",
                            "resolved": False,
                            "answer": "respuesta general que no debe mostrarse",
                        })
                    }
                }]
            }
            return json.dumps(body).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_kw: Response())
    result = answer_message("¿Cómo se cura la gripe?", context="Dashboard")
    assert result["content"] == OUT_OF_SCOPE
    assert "gripe" not in result["content"].lower()

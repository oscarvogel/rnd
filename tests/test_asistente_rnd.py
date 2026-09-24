# coding=utf-8
import json
from pathlib import Path

from utiles.asistente_rnd_conocimiento import knowledge_for_prompt
from utiles.asistente_rnd_servicio import OUT_OF_SCOPE, UNRESOLVED, answer_message


class FakeResponse:
    def __init__(self, decision):
        self.decision = decision

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        body = {
            "choices": [{
                "message": {"content": json.dumps(self.decision, ensure_ascii=False)}
            }]
        }
        return json.dumps(body, ensure_ascii=False).encode("utf-8")


def _fake_ai(monkeypatch, decision, captured=None):
    monkeypatch.setenv("RND_ASSISTANT_AI_API_KEY", "test-key")

    def urlopen(request, **_kwargs):
        if captured is not None:
            captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(decision)

    monkeypatch.setattr("urllib.request.urlopen", urlopen)


def test_toda_consulta_funcional_va_primero_a_ia(monkeypatch):
    captured = {}
    _fake_ai(monkeypatch, {
        "status": "answered",
        "answer": "Usá Imprimir después de revisar la hoja.",
        "sources": ["imprimir_hoja"],
        "reason": "La consulta refiere a emisión de Hoja de Ruta.",
    }, captured)

    result = answer_message("¿Cómo genero el PDF?", context="VerHojaRuta")

    assert result["source"] == "ai"
    assert result["decision"] == "answered"
    system_prompt = captured["payload"]["messages"][0]["content"]
    assert "PANTALLA ACTUAL:\nVerHojaRuta" in system_prompt
    assert "Generar o imprimir la Hoja de Ruta" in system_prompt
    assert captured["payload"]["messages"][-1]["content"] == "¿Cómo genero el PDF?"


def test_ia_puede_combinar_conocimiento_sin_router_python(monkeypatch):
    _fake_ai(monkeypatch, {
        "status": "answered",
        "answer": "Primero organizá la ruta y después asigná chofer y camión.",
        "sources": ["organizar_pedidos", "asignar_recursos"],
        "reason": "La pregunta requiere dos etapas del flujo.",
    })
    result = answer_message("Ya importé, ¿qué hago ahora?", context="BandejaPedidos")
    assert result["resolved"] is True
    assert result["sources"] == ["organizar_pedidos", "asignar_recursos"]


def test_fuera_de_alcance_lo_decide_la_ia(monkeypatch):
    _fake_ai(monkeypatch, {
        "status": "out_of_scope",
        "answer": "",
        "sources": [],
        "reason": "No pertenece a RND.",
    })
    result = answer_message("¿Cómo se cura la gripe?", context="Dashboard")
    assert result["content"] == OUT_OF_SCOPE


def test_no_resuelta_por_ia_se_registra(monkeypatch, tmp_path):
    monkeypatch.setenv("RND_ASSISTANT_DATA_DIR", str(tmp_path))
    _fake_ai(monkeypatch, {
        "status": "unresolved",
        "answer": "",
        "sources": [],
        "reason": "No hay información suficiente.",
    })
    result = answer_message("¿Qué significa el código X99?", context="ImportacionPedidos")
    assert result["content"] == UNRESOLVED
    assert (tmp_path / "unresolved.jsonl").exists()


def test_base_entregada_a_ia_contiene_funciones_rnd():
    prompt = knowledge_for_prompt()
    assert "Importar pedidos desde PDF o imagen con IA" in prompt
    assert "Asignar chofer y camión" in prompt
    assert "Generar o imprimir la Hoja de Ruta" in prompt


def test_asistente_es_flotante_y_always_on_top():
    source = Path("vistas/AsistenteRnd.py").read_text(encoding="utf-8")
    assert "class AsistenteRndFlotante(QWidget)" in source
    assert "Qt.WindowStaysOnTopHint" in source
    assert "Qt.Tool" in source
    assert "BUBBLE_SIZE = 70" in source
    assert "PANEL_WIDTH = 380" in source
    assert "class AssistantBubbleButton(QPushButton)" in source
    assert "QLinearGradient" in source
    assert "#F5C518" in source


def test_shell_no_depende_de_boton_asistente():
    header = Path("vistas/shell/Encabezado.py").read_text(encoding="utf-8")
    main = Path("controladores/Main.py").read_text(encoding="utf-8")
    assert "boton_asistente" not in header
    assert "AsistenteRndFlotante" in main
    assert "_mostrar_asistente_flotante()" in main


def test_config_asistente_reutiliza_fallback_group_summary(monkeypatch):
    from utiles.asistente_rnd_servicio import _config

    for name in (
        "RND_ASSISTANT_AI_URL",
        "RND_PDF_AI_URL",
        "RND_ASSISTANT_AI_API_KEY",
        "RND_PDF_AI_API_KEY",
        "MINIMAX_API_KEY",
        "RND_ASSISTANT_AI_MODEL",
        "RND_PDF_AI_MODEL",
        "MINIMAX_MODEL",
        "RND_ASSISTANT_AI_TIMEOUT",
        "RND_PDF_AI_TIMEOUT",
    ):
        monkeypatch.delenv(name, raising=False)

    monkeypatch.setenv(
        "GROUP_SUMMARY_AI_CHAT_URL",
        "https://example.test/v1/chat/completions",
    )
    monkeypatch.setenv("GROUP_SUMMARY_AI_API_KEY", "group-key")
    monkeypatch.setenv("GROUP_SUMMARY_AI_MODEL", "MiniMax-M3")

    url, key, model, timeout = _config()

    assert url == "https://example.test/v1/chat/completions"
    assert key == "group-key"
    assert model == "MiniMax-M3"
    assert timeout == 120


def test_asistente_reintenta_error_transitorio(monkeypatch):
    import urllib.error
    from utiles.asistente_rnd_servicio import _call_minimax

    attempts = {"count": 0}

    class OkResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            body = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "status": "answered",
                            "answer": "OK",
                            "sources": [],
                            "reason": "test",
                        })
                    }
                }]
            }
            return json.dumps(body).encode("utf-8")

    def urlopen(request, **_kwargs):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise urllib.error.HTTPError(
                request.full_url, 503, "busy", hdrs=None, fp=None
            )
        return OkResponse()

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    monkeypatch.setattr("time.sleep", lambda *_args: None)

    decision = _call_minimax(
        {"messages": []},
        url="https://example.test/v1/chat/completions",
        key="test-key",
        timeout=15,
    )

    assert attempts["count"] == 2
    assert decision["status"] == "answered"

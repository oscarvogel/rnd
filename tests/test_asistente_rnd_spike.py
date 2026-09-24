# coding=utf-8
import json
import urllib.error

from utiles.asistente_rnd_spike import preguntar
from utiles.importacion_pdf_ia import llamar_minimax_texto


def test_spike_envia_manual_y_pregunta_a_minimax(monkeypatch):
    capturado = {}

    def fake_call(messages, **kwargs):
        capturado["messages"] = messages
        capturado["kwargs"] = kwargs
        return "Primero organiza los pedidos y despues asigna chofer y camion."

    monkeypatch.setattr(
        "utiles.asistente_rnd_spike.llamar_minimax_texto",
        fake_call,
    )

    respuesta = preguntar("Ya importe los pedidos, que hago ahora?")

    assert respuesta.startswith("Primero organiza")
    system = capturado["messages"][0]["content"]
    assert "Manual de usuario" in system
    assert "Importar pedidos" in system
    assert capturado["messages"][-1] == {
        "role": "user",
        "content": "Ya importe los pedidos, que hago ahora?",
    }
    assert capturado["kwargs"]["max_completion_tokens"] == 1400


def test_spike_acepta_texto_normal_sin_json(monkeypatch):
    monkeypatch.setattr(
        "utiles.asistente_rnd_spike.llamar_minimax_texto",
        lambda *_args, **_kwargs: "Anda a Ver Hoja de Ruta y selecciona fecha y ruta.",
    )

    respuesta = preguntar("Como veo la hoja?")

    assert respuesta == "Anda a Ver Hoja de Ruta y selecciona fecha y ruta."


def test_cliente_texto_reutiliza_configuracion_pdf_y_reintenta(monkeypatch):
    monkeypatch.setattr(
        "utiles.importacion_pdf_ia._configuracion",
        lambda: (
            "https://example.test/v1/chat/completions",
            "test-key",
            "MiniMax-M3",
            120,
        ),
    )
    monkeypatch.setattr("time.sleep", lambda *_args: None)

    intentos = {"cantidad": 0}

    class OkResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps({
                "choices": [{
                    "message": {
                        "content": "<think>interno</think>Respuesta de prueba"
                    }
                }]
            }).encode("utf-8")

    def fake_urlopen(request, **kwargs):
        intentos["cantidad"] += 1
        assert request.get_header("Authorization") == "Bearer test-key"
        assert kwargs["timeout"] == 120
        if intentos["cantidad"] == 1:
            raise urllib.error.HTTPError(
                request.full_url,
                503,
                "busy",
                hdrs=None,
                fp=None,
            )
        return OkResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    respuesta = llamar_minimax_texto([
        {"role": "user", "content": "hola"}
    ])

    assert intentos["cantidad"] == 2
    assert respuesta == "Respuesta de prueba"

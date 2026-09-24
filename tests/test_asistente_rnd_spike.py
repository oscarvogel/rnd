# coding=utf-8
import http.client
import json
import urllib.error
from pathlib import Path

from utiles.asistente_rnd_spike import preguntar
from utiles.importacion_pdf_ia import llamar_minimax_texto


def _capturar_system(monkeypatch, pregunta):
    capturado = {}

    def fake_call(messages, **kwargs):
        capturado["messages"] = messages
        capturado["kwargs"] = kwargs
        return "ok"

    monkeypatch.setattr(
        "utiles.asistente_rnd_spike.llamar_minimax_texto",
        fake_call,
    )
    preguntar(pregunta)
    return capturado


def test_spike_envia_base_canonica_y_pregunta_a_minimax(monkeypatch):
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
    assert "Base de conocimiento canónica del Asistente RND" in system
    assert "Importar pedidos" in system
    assert "PDF" in system
    assert "Pedidos para organizar" in system
    assert "Asignar chofer y camión" in system
    assert capturado["messages"][-1] == {
        "role": "user",
        "content": "Ya importe los pedidos, que hago ahora?",
    }
    assert capturado["kwargs"]["max_completion_tokens"] == 1400


def test_spike_carga_solo_la_base_canonica():
    source = Path("utiles/asistente_rnd_spike.py").read_text(encoding="utf-8")

    assert "asistente_rnd_conocimiento_tecnico.md" in source
    assert "manual_usuario_importacion_hoja_ruta.md" not in source
    assert "guia_usuario.md" not in source


def test_conocimiento_pdf_ia_no_vuelve_a_negar_pdf(monkeypatch):
    capturado = _capturar_system(monkeypatch, "Puedo importar un PDF?")

    system = capturado["messages"][0]["content"]
    assert "Excel: `.xlsx` y `.xls`" in system
    assert "PDF: `.pdf`" in system
    assert "Imágenes: `.png`, `.jpg` y `.jpeg`" in system
    assert "Es incorrecto responder que RND sólo acepta Excel" in system
    assert "convertirlo manualmente" in system
    assert "REVISAR IA" in system
    assert "se pueden corregir las celdas" in system


def test_conocimiento_documenta_cargar_hoja_y_productos(monkeypatch):
    capturado = _capturar_system(
        monkeypatch,
        "Que hace Cargar hoja y que puedo editar en Productos?",
    )

    system = capturado["messages"][0]["content"]
    assert "Cargar hoja** no navega a otra pantalla" in system
    assert "única columna editable" in system
    assert "**Cantidad a entregar**" in system
    assert "Producto." in system
    assert "KG." in system
    assert "Bultos." in system


def test_conocimiento_tecnico_explica_lugar_duplicados_y_hoja_vacia(monkeypatch):
    capturado = _capturar_system(monkeypatch, "Como detecta los lugares de entrega?")

    system = capturado["messages"][0]["content"]
    assert "código informado por el proveedor" in system
    assert "exactamente un lugar activo" in system
    assert "no crea otra línea operativa" in system
    assert "filtros opcionales" in system
    assert "todos los pedidos de esa fecha+ruta" in system


def test_spike_no_contiene_router_de_intenciones():
    source = Path("utiles/asistente_rnd_spike.py").read_text(encoding="utf-8")

    assert "match_article" not in source
    assert "aliases" not in source
    assert "SequenceMatcher" not in source
    assert "keyword" not in source.lower()


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


def test_cliente_texto_reintenta_remote_disconnected(monkeypatch):
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
                    "message": {"content": "Respuesta recuperada"}
                }]
            }).encode("utf-8")

    def fake_urlopen(_request, **_kwargs):
        intentos["cantidad"] += 1
        if intentos["cantidad"] == 1:
            raise http.client.RemoteDisconnected(
                "Remote end closed connection without response"
            )
        return OkResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    respuesta = llamar_minimax_texto([
        {"role": "user", "content": "hola"}
    ])

    assert intentos["cantidad"] == 2
    assert respuesta == "Respuesta recuperada"


def test_conocimiento_no_mezcla_filtros_de_asignacion_y_ver_hoja(monkeypatch):
    capturado = _capturar_system(
        monkeypatch,
        "Por que Asignar chofer y camion dice Sin pedidos?",
    )

    system = capturado["messages"][0]["content"]
    assert "**No filtra por chofer ni por camión.**" in system
    assert "Esos filtros pertenecen a" in system
    assert "No atribuir **Sin pedidos**" in system


def test_conocimiento_distingue_imprimir_de_estado_lista(monkeypatch):
    capturado = _capturar_system(monkeypatch, "Si puedo imprimir, la hoja ya esta LISTA?")

    system = " ".join(capturado["messages"][0]["content"].split())
    assert "Poder imprimir no significa automáticamente que la hoja esté en estado LISTA" in system
    assert "Impresión y validación de estado son controles distintos" in system


def test_spike_entrega_contexto_de_pantalla_a_minimax(monkeypatch):
    capturado = {}

    def fake_call(messages, **_kwargs):
        capturado["system"] = messages[0]["content"]
        return "ok"

    monkeypatch.setattr(
        "utiles.asistente_rnd_spike.llamar_minimax_texto",
        fake_call,
    )

    preguntar(
        "Que puedo hacer aca?",
        contexto="Bandeja de pedidos (BandejaPedidosView)",
    )

    assert "PANTALLA / CONTEXTO ACTUAL:" in capturado["system"]
    assert "Bandeja de pedidos (BandejaPedidosView)" in capturado["system"]


def test_manuales_humanos_quedaron_alineados_con_pdf_ia():
    manual = Path("docs/manual_usuario_importacion_hoja_ruta.md").read_text(
        encoding="utf-8"
    )
    guia = Path("docs/guia_usuario.md").read_text(encoding="utf-8")

    assert "RND acepta:" in manual
    assert "No es necesario convertir el PDF manualmente a Excel." in manual
    assert "PDF e imágenes se procesan con IA" in guia
    assert "No hace falta convertirlos manualmente a Excel." in guia

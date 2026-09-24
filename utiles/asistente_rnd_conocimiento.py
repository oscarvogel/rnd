# coding=utf-8
"""Conocimiento funcional del Asistente RND.

Los articulos base viajan versionados con RND. Un articulo puede ser
sobrescrito desde la interfaz y queda persistido fuera del ejecutable.
"""
from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from utiles.asistente_rnd_store import load_knowledge_overrides, save_knowledge_override


BASE_ARTICLES = [
    {
        "id": "flujo_general",
        "title": "Flujo diario de RND",
        "aliases": [
            "flujo general", "como uso el sistema", "por donde empiezo",
            "que hago primero", "pasos del sistema", "flujo diario",
        ],
        "contexts": ["Dashboard", "Main"],
        "answer": (
            "El flujo recomendado es:\n"
            "1. Importar los pedidos del proveedor para la fecha de reparto.\n"
            "2. Revisar la vista previa y grabar los pedidos.\n"
            "3. Abrir Organizar pedidos y verificar cliente, lugar de entrega, factura y cantidades.\n"
            "4. Organizar los pedidos en la ruta correcta.\n"
            "5. Asignar chofer y camión.\n"
            "6. Revisar la Hoja de Ruta.\n"
            "7. Imprimir el PDF final.\n\n"
            "Regla práctica: Importar → Revisar → Organizar → Asignar → Revisar → Imprimir."
        ),
    },
    {
        "id": "importar_excel",
        "title": "Importar pedidos desde Excel",
        "aliases": [
            "importar excel", "como importo pedidos", "cargar excel",
            "importacion pedidos", "importar archivo proveedor",
        ],
        "contexts": ["ImportacionPedidos"],
        "answer": (
            "1. Entrá a Importación de pedidos.\n"
            "2. Seleccioná proveedor/origen y fecha de reparto.\n"
            "3. Presioná Examinar y elegí el Excel.\n"
            "4. Si tiene varias hojas, elegí la correcta y revisá fila inicial/final.\n"
            "5. Cargá la vista previa. Todavía no se graban pedidos.\n"
            "6. Revisá cliente, comprobante, producto, cantidad, kilos, bultos y observaciones.\n"
            "7. Desmarcá las filas que no deban importarse.\n"
            "8. Cuando esté correcto, presioná Grabar pedidos."
        ),
    },
    {
        "id": "importar_pdf",
        "title": "Importar pedidos desde PDF o imagen con IA",
        "aliases": [
            "importar pdf", "cargar pdf", "pdf con ia", "importar imagen",
            "pedido escaneado", "factura pdf", "tremblay pdf",
        ],
        "contexts": ["ImportacionPedidos"],
        "answer": (
            "En Importación de pedidos podés seleccionar un PDF o una imagen. "
            "RND usa MiniMax para extraer cliente, documento y productos y los pasa por la misma vista previa del Excel.\n\n"
            "Antes de grabar revisá especialmente las filas marcadas con REVISAR IA, el cliente, el número de documento, "
            "la localidad, el producto y la cantidad. La IA sólo prepara la importación: no graba directamente."
        ),
    },
    {
        "id": "cliente_no_encontrado",
        "title": "El sistema no encuentra o no reconoce un cliente",
        "aliases": [
            "no encuentra cliente", "cliente no encontrado", "no reconoce cliente",
            "asociar cliente", "codigo proveedor cliente", "cliente pendiente",
        ],
        "contexts": ["ImportacionPedidos", "BandejaPedidos", "ABMClientes"],
        "answer": (
            "Normalmente falta relacionar el código que usa el proveedor con el cliente interno de RND.\n"
            "1. Buscá el cliente correcto cuando RND solicite la asociación.\n"
            "2. Confirmá que sea el mismo cliente y no otro con nombre parecido.\n"
            "3. Guardá la relación proveedor/código/cliente.\n"
            "4. Volvé a procesar o continuar la fila pendiente.\n\n"
            "No crees un cliente duplicado sólo para resolver un código de proveedor."
        ),
    },
    {
        "id": "lugares_entrega",
        "title": "Cliente con más de un lugar de entrega",
        "aliases": [
            "dos domicilios", "varios destinos", "lugar de entrega",
            "cliente con varios lugares", "cambiar lugar entrega",
        ],
        "contexts": ["BandejaPedidos", "ABMClientes"],
        "answer": (
            "Cliente y lugar de entrega son conceptos distintos. Un mismo cliente puede tener varios destinos. "
            "Por ejemplo, un cliente puede recibir en Puerto Rico y San Vicente. "
            "Debe existir un solo cliente y seleccionar el lugar de entrega correspondiente para cada pedido; "
            "no dupliques el cliente por cada destino."
        ),
    },
    {
        "id": "organizar_pedidos",
        "title": "Organizar pedidos en una ruta",
        "aliases": [
            "organizar pedidos", "asignar ruta", "armar ruta",
            "organizar factura", "que hago en organizar",
        ],
        "contexts": ["BandejaPedidos"],
        "answer": (
            "1. Abrí Organizar pedidos y elegí la misma fecha de la importación.\n"
            "2. Buscá los pedidos o la factura/comprobante.\n"
            "3. Revisá cliente, lugar de entrega, factura, productos y cantidades.\n"
            "4. Seleccioná los pedidos que deben viajar juntos.\n"
            "5. Elegí la ruta de reparto.\n"
            "6. Presioná Organizar selección.\n"
            "7. Después continuá con Asignar chofer y camión."
        ),
    },
    {
        "id": "modificar_pedidos",
        "title": "Qué se puede corregir antes de despachar",
        "aliases": [
            "que puedo modificar", "modificar pedido", "cambiar cantidad",
            "corregir pedido", "editar pedido", "productos boton",
        ],
        "contexts": ["BandejaPedidos", "VerHojaRuta"],
        "answer": (
            "Antes de emitir la hoja final revisá los datos operativos del pedido. "
            "Las correcciones deben hacerse en la etapa correspondiente y luego volver a cargar/revisar la hoja. "
            "Si la duda es sobre un campo concreto, indicame cuál (cantidad, cliente, lugar de entrega, producto, ruta, chofer o camión) "
            "y te indico el circuito correcto."
        ),
    },
    {
        "id": "asignar_recursos",
        "title": "Asignar chofer y camión",
        "aliases": [
            "asignar chofer", "asignar camion", "chofer y camion",
            "cargar hoja asignacion", "asignar recursos",
        ],
        "contexts": ["AsignacionRecursos"],
        "answer": (
            "1. Seleccioná la fecha y la ruta que acabás de organizar.\n"
            "2. Cargá los pedidos de esa combinación.\n"
            "3. Seleccioná el chofer/responsable.\n"
            "4. Seleccioná el camión/equipo.\n"
            "5. Verificá los pedidos que quedarán incluidos.\n"
            "6. Guardá la asignación.\n"
            "7. Continuá a la revisión de la Hoja de Ruta."
        ),
    },
    {
        "id": "revisar_hoja",
        "title": "Revisar la Hoja de Ruta",
        "aliases": [
            "revisar hoja ruta", "ver hoja ruta", "controlar hoja",
            "revision hoja", "que hago despues de asignar",
        ],
        "contexts": ["VerHojaRuta", "ValidacionHojaRuta"],
        "answer": (
            "Seleccioná fecha y ruta y cargá la hoja. Antes de imprimir verificá cliente, factura, producto, cantidad, "
            "kilos, bultos, observaciones, chofer y camión. Si encontrás un error, corregilo antes de emitir el PDF."
        ),
    },
    {
        "id": "imprimir_hoja",
        "title": "Generar o imprimir la Hoja de Ruta",
        "aliases": [
            "imprimir hoja", "generar pdf", "hoja de ruta pdf",
            "no puedo imprimir", "emitir hoja",
        ],
        "contexts": ["VerHojaRuta", "ValidacionHojaRuta"],
        "answer": (
            "Para emitir la Hoja de Ruta deben estar completos la fecha, la ruta, el chofer/responsable y el camión/equipo, "
            "y deben existir pedidos para esa combinación. Cargá y revisá la hoja y luego presioná Imprimir."
        ),
    },
    {
        "id": "hoja_vacia",
        "title": "La Hoja de Ruta aparece vacía",
        "aliases": [
            "hoja vacia", "no aparecen pedidos", "no carga hoja",
            "sin pedidos hoja ruta", "cargar hoja no muestra",
        ],
        "contexts": ["VerHojaRuta", "AsignacionRecursos", "ValidacionHojaRuta"],
        "answer": (
            "Revisá en este orden: fecha seleccionada, ruta seleccionada, que los pedidos se hayan grabado para esa fecha, "
            "que hayan sido organizados en esa ruta y que no haya filtros de chofer/camión dejando la grilla sin resultados."
        ),
    },
    {
        "id": "permisos",
        "title": "No aparece una opción o botón",
        "aliases": [
            "no aparece menu", "no aparece opcion", "no veo boton",
            "falta menu", "permisos", "no me deja entrar",
        ],
        "contexts": [],
        "answer": (
            "El menú de RND depende de los permisos del usuario. Si una opción no aparece, primero verificá que el usuario tenga "
            "el permiso correspondiente. Si el botón sí aparece pero falla al abrir, eso ya puede ser un error y conviene registrar "
            "el mensaje exacto que muestra RND."
        ),
    },
    {
        "id": "evitar_duplicados",
        "title": "Qué hacer si una importación se interrumpe",
        "aliases": [
            "importar dos veces", "pedido duplicado", "duplico importacion",
            "se corto importacion", "error al grabar pedidos",
        ],
        "contexts": ["ImportacionPedidos"],
        "answer": (
            "Si hubo un error o corte mientras se grababan pedidos, no repitas la importación automáticamente. "
            "Primero verificá qué documentos quedaron grabados para evitar duplicarlos. Después reintentá sólo lo que corresponda."
        ),
    },
]


STOPWORDS = {
    "a", "al", "como", "de", "del", "el", "en", "la", "las", "lo", "los",
    "me", "para", "por", "que", "se", "un", "una", "y", "con", "esto",
}


CONTEXT_SUGGESTIONS = {
    "ImportacionPedidos": [
        "¿Cómo importo un Excel?",
        "¿Cómo importo un PDF con IA?",
        "No encuentra el cliente, ¿qué hago?",
        "¿Qué reviso antes de grabar?",
    ],
    "BandejaPedidos": [
        "¿Qué hago en Organizar pedidos?",
        "¿Qué puedo modificar acá?",
        "¿Cómo cambio el lugar de entrega?",
        "¿Qué hago después?",
    ],
    "AsignacionRecursos": [
        "¿Cómo asigno chofer y camión?",
        "¿Qué hace Cargar Hoja?",
        "No aparecen pedidos, ¿qué reviso?",
        "¿Qué hago después?",
    ],
    "VerHojaRuta": [
        "¿Qué tengo que revisar?",
        "¿Cómo corrijo un pedido?",
        "¿Cómo genero el PDF?",
        "La hoja aparece vacía",
    ],
    "ValidacionHojaRuta": [
        "¿Qué tengo que validar?",
        "¿Cómo vuelvo a corregir la hoja?",
        "¿Cómo genero el PDF?",
        "¿Qué hago después?",
    ],
}


def normalize_text(value: str) -> str:
    text = unicodedata.normalize("NFD", (value or "").lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value: str) -> list:
    return [
        token for token in normalize_text(value).split()
        if token not in STOPWORDS and len(token) > 2
    ]


def _score(message: str, alias: str) -> float:
    norm_msg = normalize_text(message)
    norm_alias = normalize_text(alias)
    if not norm_alias:
        return 0.0
    if norm_alias in norm_msg:
        return 1.0
    expected = _tokens(norm_alias)
    actual = _tokens(norm_msg)
    if not expected:
        return 0.0
    hits = 0
    for token in expected:
        if any(
            token == candidate
            or SequenceMatcher(None, token, candidate).ratio() >= 0.80
            for candidate in actual
        ):
            hits += 1
    token_score = hits / len(expected)
    return max(token_score, SequenceMatcher(None, norm_msg, norm_alias).ratio())


def list_articles() -> list:
    overrides = load_knowledge_overrides()
    merged = []
    seen = set()
    for base in BASE_ARTICLES:
        article = dict(overrides.get(base["id"]) or base)
        if article.get("enabled", True):
            merged.append(article)
        seen.add(base["id"])
    for article_id, article in overrides.items():
        if article_id in seen or not isinstance(article, dict):
            continue
        if article.get("enabled", True):
            merged.append(article)
    return merged


def match_article(message: str, context: str = ""):
    best = None
    best_score = 0.0
    for article in list_articles():
        aliases = list(article.get("aliases") or []) + [article.get("title") or ""]
        for alias in aliases:
            score = _score(message, alias)
            if context and context in (article.get("contexts") or []):
                score += 0.06
            if score > best_score:
                best, best_score = article, score
    return best if best_score >= 0.76 else None


def knowledge_for_prompt() -> str:
    blocks = []
    for article in list_articles():
        blocks.append(
            "TEMA: {title}\nALIASES: {aliases}\nRESPUESTA/POLITICA:\n{answer}".format(
                title=article.get("title", ""),
                aliases=", ".join(article.get("aliases") or []),
                answer=article.get("answer", ""),
            )
        )
    return "\n\n---\n\n".join(blocks)


def suggestions_for_context(context: str) -> list:
    return CONTEXT_SUGGESTIONS.get(context, [
        "¿Cómo se usa RND?",
        "¿Cómo importo pedidos?",
        "¿Cómo organizo una ruta?",
        "¿Cómo genero la Hoja de Ruta?",
    ])


def save_article(article: dict) -> None:
    save_knowledge_override(article)

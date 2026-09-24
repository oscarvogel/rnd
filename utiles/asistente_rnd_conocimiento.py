# coding=utf-8
"""Base de conocimiento funcional del Asistente RND.

No hay matching por palabras clave ni reglas de intención en Python.
Todo el conocimiento se entrega a MiniMax y el modelo decide qué partes
son pertinentes para la consulta y el contexto actual.
"""
from __future__ import annotations

from utiles.asistente_rnd_store import load_knowledge_overrides, save_knowledge_override


BASE_ARTICLES = [
    {
        "id": "flujo_general",
        "title": "Flujo diario de RND",
        "context_hint": "Flujo principal / pantalla inicial",
        "content": (
            "El flujo recomendado es: Importar pedidos -> revisar vista previa -> "
            "grabar -> Organizar pedidos -> asignar chofer y camión -> revisar Hoja "
            "de Ruta -> imprimir el PDF final. Antes de avanzar entre etapas se deben "
            "revisar cliente, lugar de entrega, comprobante, productos y cantidades."
        ),
    },
    {
        "id": "importar_excel",
        "title": "Importar pedidos desde Excel",
        "context_hint": "Importación de pedidos",
        "content": (
            "Entrar a Importación de pedidos. Seleccionar proveedor/origen y fecha "
            "de reparto. Presionar Examinar y elegir el Excel. Si tiene varias hojas, "
            "elegir la correcta y revisar fila inicial/final. Cargar la vista previa: "
            "en esta etapa todavía no se graban pedidos. Revisar cliente, comprobante, "
            "producto, cantidad, kilos, bultos y observaciones; desmarcar filas que no "
            "correspondan. Cuando esté correcto, usar Grabar pedidos."
        ),
    },
    {
        "id": "importar_pdf",
        "title": "Importar pedidos desde PDF o imagen con IA",
        "context_hint": "Importación de pedidos",
        "content": (
            "En Importación de pedidos también se puede seleccionar un PDF o imagen. "
            "RND usa MiniMax para extraer cliente, documento y productos y los lleva "
            "a la misma vista previa del Excel. La IA no graba directamente. Antes de "
            "grabar hay que revisar especialmente filas con REVISAR IA, cliente, número "
            "de documento, localidad, producto y cantidad."
        ),
    },
    {
        "id": "cliente_no_encontrado",
        "title": "Cliente no reconocido durante la importación",
        "context_hint": "Importación / Clientes",
        "content": (
            "Si RND no reconoce el cliente, normalmente falta relacionar el código que "
            "usa el proveedor con el cliente interno. Buscar el cliente correcto cuando "
            "RND solicite la asociación, verificar que no sea otro de nombre parecido y "
            "guardar la relación proveedor/código/cliente. No crear un cliente duplicado "
            "sólo para resolver un código de proveedor."
        ),
    },
    {
        "id": "lugares_entrega",
        "title": "Cliente con varios lugares de entrega",
        "context_hint": "Clientes / Organizar pedidos",
        "content": (
            "Cliente y lugar de entrega son conceptos distintos. Un mismo cliente puede "
            "tener varios destinos, por ejemplo Puerto Rico y San Vicente. Debe existir "
            "un solo cliente y seleccionarse el lugar de entrega correcto para cada "
            "pedido; no se duplica el cliente por destino."
        ),
    },
    {
        "id": "organizar_pedidos",
        "title": "Organizar pedidos en una ruta",
        "context_hint": "Organizar pedidos / Bandeja de pedidos",
        "content": (
            "Abrir Organizar pedidos y elegir la misma fecha de la importación. Buscar "
            "los pedidos o la factura/comprobante. Revisar cliente, lugar de entrega, "
            "factura, productos y cantidades. Seleccionar los pedidos que viajarán juntos, "
            "elegir la ruta y usar Organizar selección. El paso siguiente es asignar "
            "chofer y camión."
        ),
    },
    {
        "id": "corregir_pedidos",
        "title": "Correcciones antes de despachar",
        "context_hint": "Organizar pedidos / Hoja de Ruta",
        "content": (
            "Antes de emitir la hoja final se deben revisar los datos operativos del "
            "pedido. Las correcciones deben realizarse en la etapa correspondiente y "
            "después volver a cargar/revisar la hoja. Los datos que suelen requerir "
            "revisión son cantidad, cliente, lugar de entrega, producto, ruta, chofer "
            "y camión."
        ),
    },
    {
        "id": "asignar_recursos",
        "title": "Asignar chofer y camión",
        "context_hint": "Asignar chofer y camión",
        "content": (
            "Seleccionar la fecha y la ruta ya organizada, cargar los pedidos, elegir "
            "chofer/responsable y camión/equipo, verificar los pedidos incluidos y guardar "
            "la asignación. El paso siguiente es revisar la Hoja de Ruta."
        ),
    },
    {
        "id": "revisar_hoja",
        "title": "Revisar la Hoja de Ruta",
        "context_hint": "Ver Hoja de Ruta / Validación",
        "content": (
            "Seleccionar fecha y ruta y cargar la hoja. Antes de imprimir verificar "
            "cliente, factura, producto, cantidad, kilos, bultos, observaciones, chofer "
            "y camión. Si hay un error debe corregirse antes de emitir el PDF."
        ),
    },
    {
        "id": "imprimir_hoja",
        "title": "Generar o imprimir la Hoja de Ruta",
        "context_hint": "Ver Hoja de Ruta / Validación",
        "content": (
            "Para emitir la Hoja de Ruta deben estar completos fecha, ruta, "
            "chofer/responsable y camión/equipo, y deben existir pedidos para esa "
            "combinación. Cargar y revisar la hoja antes de usar Imprimir."
        ),
    },
    {
        "id": "hoja_vacia",
        "title": "La Hoja de Ruta aparece vacía",
        "context_hint": "Asignación / Hoja de Ruta",
        "content": (
            "Revisar fecha seleccionada, ruta seleccionada, que los pedidos se hayan "
            "grabado para esa fecha, que hayan sido organizados en esa ruta y que no "
            "haya filtros de chofer o camión dejando la grilla sin resultados."
        ),
    },
    {
        "id": "permisos",
        "title": "No aparece una opción o botón",
        "context_hint": "Cualquier pantalla",
        "content": (
            "El menú de RND depende de los permisos del usuario. Si una opción no aparece, "
            "revisar primero el permiso correspondiente. Si el botón aparece pero falla al "
            "abrir, registrar el mensaje exacto porque puede tratarse de un error."
        ),
    },
    {
        "id": "evitar_duplicados",
        "title": "Importación interrumpida o posible duplicado",
        "context_hint": "Importación de pedidos",
        "content": (
            "Si hubo un error o corte mientras se grababan pedidos, no repetir la "
            "importación automáticamente. Primero verificar qué documentos quedaron "
            "grabados para evitar duplicarlos y luego reintentar sólo lo que corresponda."
        ),
    },
]


GENERIC_SUGGESTIONS = [
    "¿Qué puedo hacer desde esta pantalla?",
    "¿Cuál es el siguiente paso?",
    "¿Cómo importo pedidos?",
    "¿Cómo genero la Hoja de Ruta?",
]


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


def knowledge_for_prompt() -> str:
    blocks = []
    for article in list_articles():
        blocks.append(
            "ID: {id}\nTEMA: {title}\nCONTEXTO ORIENTATIVO: {context}\n"
            "CONOCIMIENTO:\n{content}".format(
                id=article.get("id", ""),
                title=article.get("title", ""),
                context=article.get("context_hint", ""),
                content=article.get("content", ""),
            )
        )
    return "\n\n---\n\n".join(blocks)


def suggestions() -> list:
    return list(GENERIC_SUGGESTIONS)


def save_article(article: dict) -> None:
    save_knowledge_override(article)

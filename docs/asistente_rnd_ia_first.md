# Asistente RND — arquitectura IA-first

Fecha: 2026-09-24  
Rama inicial: `feat/asistente-rnd-minimax`

## Objetivo

Incorporar dentro de RND un asistente especializado en explicar el funcionamiento
del sistema y resolver dudas operativas de los usuarios.

El asistente **no ejecuta operaciones de negocio**. No importa, modifica, elimina,
organiza ni despacha pedidos. Su función es orientar al usuario.

## Principio obligatorio: IA-first

Toda consulta funcional se envía primero a MiniMax.

No debe existir un router previo basado en:

- `if` por palabras o frases;
- `match/case` de intenciones;
- aliases usados para elegir respuestas;
- expresiones regulares usadas para decidir qué procedimiento contestar;
- árboles de decisión funcionales.

La aplicación entrega a MiniMax la pregunta, la pantalla activa, el historial
reciente y la base de conocimiento vigente. MiniMax decide qué conocimiento es
pertinente, si debe combinar varios procedimientos, si puede responder con
seguridad y si la pregunta está fuera del dominio RND.

Python sólo valida el contrato técnico de la respuesta y aplica el resultado
estructurado del modelo.

## Contrato de decisión

MiniMax devuelve JSON con:

- `status=answered`: hay respuesta fundada en el conocimiento RND;
- `status=unresolved`: la pregunta es sobre RND, pero falta conocimiento;
- `status=out_of_scope`: la consulta no pertenece a RND;
- `answer`: texto para el usuario;
- `sources`: IDs de los artículos usados;
- `reason`: explicación corta de la decisión para diagnóstico.

Las consultas `unresolved` se registran para revisión.

## Base de conocimiento

La base contiene **conocimiento, no reglas de enrutamiento**. Cada artículo tiene
ID estable, título, contexto orientativo y contenido/procedimiento. El contexto es
una pista semántica para MiniMax, nunca una condición de código.

Los artículos base viajan versionados con RND. Los cambios creados desde la
interfaz administrativa se guardan en la base compartida
`asistente_conocimiento`, por lo que todas las PCs conectadas a la misma base
usan el mismo conocimiento.

En DEMO, tests o ante una indisponibilidad de la DB existe un fallback local en
`%LOCALAPPDATA%\RND\asistente\knowledge.json`.

Sólo los usuarios administradores de RND pueden abrir la edición de conocimiento.

## Consultas no resueltas

Cuando MiniMax determina que una pregunta pertenece a RND pero no puede
responderla con seguridad, RND registra en
`asistente_consulta_no_resuelta`:

- fecha/hora;
- usuario;
- pantalla activa;
- pregunta;
- origen;
- estado.

Esto permite revisar desde una PC administrativa qué están preguntando los
usuarios. Sólo administradores pueden abrir la auditoría global.

En DEMO, tests o caída de DB se conserva un fallback local en
`%LOCALAPPDATA%\RND\asistente\unresolved.jsonl`.

## Contexto de pantalla

La **burbuja flotante** y la tecla **F1** capturan la ventana activa. La burbuja permanece por encima de las ventanas de RND, se expande a un panel compacto y vuelve a minimizarse sin perder la conversación. Ese dato
se envía a MiniMax para resolver preguntas naturales como “¿qué hago ahora?”,
“¿qué sigue?”, “¿por qué no me deja?” o “¿qué tengo que revisar acá?”. La
decisión sigue siendo de la IA.

## Configuración MiniMax

El asistente reutiliza la configuración ya disponible para importación PDF.

Prioridad:

1. `RND_ASSISTANT_AI_*`;
2. `RND_PDF_AI_*`;
3. `MINIMAX_*`;
4. defaults de MiniMax.

No es necesario mantener dos credenciales para RND.

## Límites

- No inventar funciones de RND.
- No responder temas generales ajenos a RND.
- No usar conocimiento general para rellenar procedimientos faltantes.
- No ejecutar acciones transaccionales.
- No repetir automáticamente una importación fallida sin verificar duplicados.

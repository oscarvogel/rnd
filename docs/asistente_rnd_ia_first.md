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

La aplicación entrega a MiniMax:

1. la pregunta del usuario;
2. la pantalla/ventana activa;
3. el historial reciente de conversación;
4. la base de conocimiento vigente.

MiniMax decide:

- qué conocimiento es pertinente;
- si debe combinar varios procedimientos;
- si puede responder con seguridad;
- si la pregunta está fuera del dominio RND.

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

La base contiene **conocimiento**, no reglas de enrutamiento.

Cada artículo tiene:

- ID estable;
- título;
- contexto orientativo;
- contenido/procedimiento.

El contexto es una pista semántica para MiniMax, nunca una condición de código.

Los artículos base viajan con RND. Los cambios hechos desde la interfaz se
guardan en:

`%LOCALAPPDATA%\RND\asistente\knowledge.json`

Eso permite ampliar procedimientos sin tocar la base de negocio y preserva los
cambios entre actualizaciones.

## Consultas no resueltas

Cuando MiniMax determina que la pregunta pertenece a RND pero no puede
responderla con seguridad, RND registra:

- fecha/hora;
- pantalla activa;
- pregunta;
- origen;
- estado.

Archivo local:

`%LOCALAPPDATA%\RND\asistente\unresolved.jsonl`

La interfaz **Consultas no resueltas** permite revisar esas dudas y convertirlas
en nuevo conocimiento o detectar una pantalla/proceso que deba mejorarse.

## Contexto de pantalla

El botón **Asistente IA** y la tecla **F1** capturan la ventana activa.

Ese dato se envía a MiniMax para resolver preguntas naturales como:

- “¿qué hago ahora?”;
- “¿qué sigue?”;
- “¿por qué no me deja?”;
- “¿qué tengo que revisar acá?”.

La decisión sigue siendo de la IA.

## Configuración MiniMax

El asistente reutiliza la configuración ya disponible para importación PDF.

Prioridad de configuración:

1. `RND_ASSISTANT_AI_*`;
2. `RND_PDF_AI_*`;
3. `MINIMAX_*`;
4. defaults de MiniMax.

De esta forma no es necesario mantener dos credenciales para RND.

## Límites

- No inventar funciones de RND.
- No responder temas generales ajenos a RND.
- No usar conocimiento general para rellenar procedimientos faltantes.
- No ejecutar acciones transaccionales.
- No repetir automáticamente una importación fallida sin verificar duplicados.

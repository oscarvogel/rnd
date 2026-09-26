# coding=utf-8
"""Bateria manual de preguntas reales para el spike del Asistente RND.

Ejecuta consultas independientes contra MiniMax usando el conocimiento actual.
No forma parte de la UI ni modifica datos de RND.

Uso:
    py scripts\\probar_asistente_rnd_casos.py
"""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.asistente_rnd_spike import preguntar


CASOS = [
    "Ya importe los pedidos, que hago ahora?",
    "Como detecta RND el lugar de entrega durante la importacion?",
    "El cliente tiene dos lugares de entrega y ninguno es principal, que pasa?",
    "Que pasa si importo dos veces la misma factura?",
    "Por que Asignar chofer y camion me dice Sin pedidos?",
    "Tengo pedidos pero Ver Hoja de Ruta aparece vacia, que reviso?",
    "Que necesita una hoja para poder quedar LISTA?",
    "Como decide la ruta si el lugar de entrega no tiene una?",
]


def main() -> int:
    errores = 0
    for numero, pregunta in enumerate(CASOS, start=1):
        print("\n" + "=" * 80)
        print("CASO {}: {}".format(numero, pregunta))
        print("-" * 80)
        try:
            respuesta = preguntar(pregunta)
        except Exception as exc:
            errores += 1
            print("ERROR: {}".format(exc))
            continue
        print(respuesta)

    print("\n" + "=" * 80)
    print("Casos ejecutados: {} | errores tecnicos: {}".format(
        len(CASOS), errores
    ))
    return 1 if errores else 0


if __name__ == "__main__":
    raise SystemExit(main())

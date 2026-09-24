# coding=utf-8
"""Prueba manual del spike del Asistente RND.

Uso:
    py scripts\\probar_asistente_rnd.py "Ya importe pedidos, que hago ahora?"

Sin argumentos abre un modo interactivo simple.
"""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.asistente_rnd_spike import preguntar


def _preguntar_seguro(texto: str) -> bool:
    try:
        respuesta = preguntar(texto)
    except Exception as exc:
        # El spike nunca debe tirar un traceback al operador.
        print("Asistente no disponible: {}".format(exc))
        return False

    print("\nAsistente RND:\n{}\n".format(respuesta))
    return True


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv:
        return 0 if _preguntar_seguro(" ".join(argv)) else 1

    print("Spike Asistente RND / MiniMax")
    print("Escribi 'salir' para terminar.\n")

    while True:
        try:
            texto = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not texto:
            continue
        if texto.lower() in {"salir", "exit", "quit"}:
            return 0

        _preguntar_seguro(texto)


if __name__ == "__main__":
    raise SystemExit(main())

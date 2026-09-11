# coding=utf-8
"""Backfill explicito para #62.

Uso:
    python scripts/migrar_documentos_logisticos.py
"""
from modelos.Documentos import backfill_documentos_legacy


if __name__ == "__main__":
    cantidad = backfill_documentos_legacy()
    print("DOCUMENTOS_BACKFILL=OK")
    print("HOJAS_VINCULADAS={}".format(cantidad))

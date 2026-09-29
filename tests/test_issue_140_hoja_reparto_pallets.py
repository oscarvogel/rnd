# coding=utf-8
"""Regresiones del PDF operativo de reparto - Issue #140."""

from pathlib import Path


def _source():
    return Path("utiles/Reportes.py").read_text(encoding="utf-8")


def test_issue_140_pdf_se_alimenta_de_pallet_detalle():
    source = _source()
    assert "PalletDetalle" in source
    assert "PalletDetalle.hoja_ruta.in_" in source
    assert "d.cantidad" in source
    assert "d.bultos" in source


def test_issue_140_distingue_descarga_parcial_y_completa():
    source = _source()
    assert "DESCARGA PARCIAL - RETIRAR SOLO LO INDICADO" in source
    assert "DESCARGA COMPLETA" in source
    assert "len(destinos_pallet[d.pallet_id]) > 1" in source


def test_issue_140_presenta_secuencia_de_entregas_no_paradas():
    source = _source()
    assert "SECUENCIA DE ENTREGAS" in source
    assert 'titulo = "ENTREGA {:02d}{}"' in source
    assert "TOTAL ENTREGA {:02d}: {} BULTOS" in source
    assert "Entregas: {}" in source
    assert "MAPA DE DESCARGA" not in source
    assert 'titulo = "PARADA {:02d}{}"' not in source


def test_issue_140_agrupa_entrega_por_cliente_y_lugar_no_por_pallet():
    source = _source()
    assert 'int(getattr(h, "cliente_id", 0) or 0)' in source
    assert 'int(getattr(h, "lugar_entrega_id", 0) or 0)' in source
    assert 'entrega["pallets"].setdefault(d.pallet_id' in source
    assert 'for numero, clave in enumerate(orden, start=1)' in source


def test_issue_140_incluye_resumen_y_continuacion():
    source = _source()
    assert "RESUMEN GENERAL DEL VIAJE" in source
    assert "CONTINUACIÓN" in source


def test_issue_140_conserva_fallback_sin_pallets():
    source = _source()
    assert "_reporte_legacy" in source
    assert "SIN PALLETS ASIGNADOS" in source

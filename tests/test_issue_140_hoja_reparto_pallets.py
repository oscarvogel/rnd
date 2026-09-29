# coding=utf-8
"""Regresiones del PDF operativo de reparto - Issue #140."""

from pathlib import Path


def test_issue_140_pdf_se_alimenta_de_pallet_detalle():
    source = Path("utiles/Reportes.py").read_text(encoding="utf-8")
    assert "PalletDetalle" in source
    assert "PalletDetalle.hoja_ruta.in_" in source
    assert "d.cantidad" in source
    assert "d.bultos" in source


def test_issue_140_distingue_descarga_parcial_y_completa():
    source = Path("utiles/Reportes.py").read_text(encoding="utf-8")
    assert "DESCARGA PARCIAL - RETIRAR SOLO LO INDICADO" in source
    assert "DESCARGA COMPLETA" in source
    assert "len(destinos_pallet[d.pallet_id]) > 1" in source


def test_issue_140_incluye_mapa_paradas_y_resumen():
    source = Path("utiles/Reportes.py").read_text(encoding="utf-8")
    assert "MAPA DE DESCARGA" in source
    assert "PARADA {:02d}" in source
    assert "RESUMEN GENERAL DEL VIAJE" in source
    assert "CONTINUACIÓN" in source


def test_issue_140_conserva_fallback_sin_pallets():
    source = Path("utiles/Reportes.py").read_text(encoding="utf-8")
    assert "_reporte_legacy" in source
    assert "SIN PALLETS ASIGNADOS" in source

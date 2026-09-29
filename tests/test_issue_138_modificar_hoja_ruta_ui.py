# coding: utf-8
"""Contrato visual del issue #138."""

from pathlib import Path


def test_issue_138_dialogo_modificar_hoja_tiene_tamano_operativo():
    source = Path("vistas/VerHojaRuta.py").read_text(encoding="utf-8")

    assert "self.resize(820, 600)" in source
    assert "self.setMinimumSize(720, 520)" in source
    assert "QFormLayout.AllNonFixedFieldsGrow" in source


def test_issue_138_acciones_principales_son_comodas():
    source = Path("vistas/VerHojaRuta.py").read_text(encoding="utf-8")

    assert 'self.btn_grabar.setMinimumSize(180, 44)' in source
    assert 'self.btn_cerrar.setMinimumSize(180, 44)' in source
    assert 'self.btn_grabar.setProperty("role", "primary")' in source

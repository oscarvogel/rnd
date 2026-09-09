"""Regresiones de alta rápida de cliente durante importación (#45)."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENTES = ROOT / "modelos" / "Clientes.py"


def test_buscador_precarga_nombre_y_muestra_boton_crear():
    source = CLIENTES.read_text(encoding="utf-8")
    assert 'ventana.lineEdit.setText(nombre_cliente)' in source
    assert 'QPushButton("Crear cliente")' in source
    assert 'ventana.horizontalLayout.insertWidget(0, btn_crear)' in source


def test_crear_cliente_selecciona_y_cierra_el_mismo_dialogo():
    source = CLIENTES.read_text(encoding="utf-8")
    assert 'ventana.ValorRetorno = str(cliente.id)' in source
    assert 'ventana.lRetval = True' in source
    assert 'ventana.accept()' in source

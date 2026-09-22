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



def test_bandeja_ofrece_alta_rapida_cliente_y_lugar_sin_salir_de_factura():
    source = (ROOT / "controladores" / "BandejaPedidos.py").read_text(
        encoding="utf-8"
    )
    assert 'QPushButton("Alta rápida cliente + lugar")' in source
    assert 'rapido.setWindowTitle("Alta rápida de cliente + lugar")' in source
    assert 'botones_rapidos.button(QDialogButtonBox.Save).setText("Crear y usar")' in source
    assert "Cliente.create(" in source
    assert "LugarEntrega.create(" in source


def test_alta_rapida_precarga_y_deja_cliente_lugar_ruta_seleccionados():
    source = (ROOT / "controladores" / "BandejaPedidos.py").read_text(
        encoding="utf-8"
    )
    assert "cbo_cliente.currentText() or factura.cliente" in source
    assert "cbo_cliente.findData(cliente.id)" in source
    assert "cbo_lugar.findData(lugar.id)" in source
    assert "cbo_ruta.findData(ruta_id)" in source
    assert 'QPushButton("Administrar clientes y lugares")' in source

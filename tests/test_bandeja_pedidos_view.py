# coding=utf-8
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from utiles.bandeja_pedidos import FacturaBandeja
from vistas.BandejaPedidos import BandejaPedidosView


_QT_APP = QApplication.instance() or QApplication([])


def _app():
    return _QT_APP


def _factura(clave, numero):
    return FacturaBandeja(
        clave=clave,
        documento_id=0,
        factura=numero,
        cliente="Cliente",
        cliente_id=1,
        lugar_entrega="Puerto Rico",
        lugar_entrega_id=1,
        ruta="CENTRO",
        ruta_id=1,
        remito="",
        productos=2,
        cantidad=2,
        kg=20,
        bultos=2,
        observaciones="",
        pendiente_cantidad=0,
        hoja_ids=(1, 2),
        responsable_ids=(23,),
        equipo_ids=(1,),
    )


def _row_for_invoice(view, numero):
    for row in range(view.tabla.rowCount()):
        item = view.tabla.item(row, view.COLUMNA_FACTURA)
        if item and item.text() == numero:
            return row
    raise AssertionError("No se encontro factura {}".format(numero))


def test_bandeja_abre_configurada_maximizada():
    _app()
    view = BandejaPedidosView()
    assert view.windowState() & Qt.WindowMaximized
    view.close()


def test_filtrar_factura_conserva_seleccion_previa():
    _app()
    view = BandejaPedidosView()
    view.cargar_facturas(
        [
            _factura("D1", "8001535540"),
            _factura("D2", "8001535500"),
        ],
        "23",
        "1",
    )

    row_otra = _row_for_invoice(view, "8001535500")
    view.tabla.item(row_otra, 0).setCheckState(Qt.Checked)

    view.txt_comprobante.setText("8001535540")
    visibles = view._filas_visibles()
    assert len(visibles) == 1
    assert view.tabla.item(visibles[0], view.COLUMNA_FACTURA).text() == "8001535540"
    assert set(view.claves_seleccionadas()) == {"D2"}

    view.txt_comprobante.clear()
    assert len(view._filas_visibles()) == 2
    view.close()


def test_seleccionar_todo_con_filtro_afecta_solo_facturas_visibles():
    _app()
    view = BandejaPedidosView()
    view.cargar_facturas(
        [
            _factura("D1", "FAC-100"),
            _factura("D2", "FAC-101"),
            _factura("D3", "FAC-200"),
        ],
        "23",
        "1",
    )

    view.txt_comprobante.setText("FAC-10")
    view.alternar_seleccion_todos()

    assert set(view.claves_seleccionadas()) == {"D1", "D2"}
    view.close()

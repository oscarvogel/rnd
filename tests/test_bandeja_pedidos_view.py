# coding=utf-8
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from utiles.bandeja_pedidos import PedidoBandeja
from vistas.BandejaPedidos import BandejaPedidosView


_APP = None

def _app():
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    return _APP


def _pedido(id_, comprobante):
    return PedidoBandeja(
        id=id_,
        cliente="Cliente {}".format(id_),
        comprobante=comprobante,
        producto="Producto",
        cantidad=1,
        kg=10,
        bultos=1,
        observaciones="",
        ruta_id=1,
        ruta="CENTRO",
        responsable_id=23,
        equipo_id=1,
    )


def test_bandeja_abre_configurada_maximizada():
    _app()
    view = BandejaPedidosView()
    assert view.windowState() & Qt.WindowMaximized
    view.close()


def test_filtrar_y_seleccionar_factura_conserva_otras_selecciones():
    _app()
    view = BandejaPedidosView()
    view.cargar_pedidos(
        [
            _pedido(1, "8001535540"),
            _pedido(2, "8001535540"),
            _pedido(3, "8001535500"),
        ],
        "23",
        "1",
    )

    # Selección previa de otra factura: debe conservarse.
    view.tabla.item(2, 0).setCheckState(Qt.Checked)

    view.txt_comprobante.setText("8001535540")
    assert view._filas_visibles() == [0, 1]

    view.seleccionar_factura_visible()
    assert set(view.ids_seleccionados()) == {1, 2, 3}

    view.txt_comprobante.clear()
    assert view._filas_visibles() == [0, 1, 2]
    view.close()


def test_seleccionar_todo_con_filtro_afecta_solo_filas_visibles():
    _app()
    view = BandejaPedidosView()
    view.cargar_pedidos(
        [
            _pedido(1, "FAC-100"),
            _pedido(2, "FAC-100"),
            _pedido(3, "FAC-200"),
        ],
        "23",
        "1",
    )

    view.txt_comprobante.setText("FAC-100")
    view.alternar_seleccion_todos()

    assert set(view.ids_seleccionados()) == {1, 2}
    view.close()

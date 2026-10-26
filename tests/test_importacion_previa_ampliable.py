# coding=utf-8
"""La vista previa debe poder agrandarse en pantallas chicas (#ver ajuste).

En un monitor de 1366x768 con escalado de Windows el alto efectivo baja a
~614 px y la grilla de vista previa quedaba en 28-46 px (menos de una fila).
"""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QSizePolicy

from utiles.importacion_guiada import ResumenImportacion


_QT_APP = QApplication.instance() or QApplication([])


def _vista(alto=700):
    from vistas.ImportacionPedidos import ImportacionPedidosView

    view = ImportacionPedidosView()
    view.resize(1366, alto)
    view.show()
    _QT_APP.processEvents()
    return view


def test_grilla_previa_tiene_alto_minimo_util():
    view = _vista()
    try:
        assert view.grid_datos.minimumHeight() >= 160
        assert view.grid_datos.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    finally:
        view.close()


def test_resultado_oculto_hasta_tener_resumen():
    view = _vista()
    try:
        assert not view.grupo_resultado.isVisible()

        view.mostrar_resultado(ResumenImportacion(leidos=2, importados=2))
        _QT_APP.processEvents()

        assert view.grupo_resultado.isVisible()
        assert view.lbl_resultado_titulo.text()
    finally:
        view.close()


def test_ampliar_vista_previa_oculta_pasos_y_agranda_grilla():
    view = _vista()
    try:
        alto_normal = view.grid_datos.height()

        assert view.alternar_vista_previa() is True
        _QT_APP.processEvents()

        assert not view.grupo_origen.isVisible()
        assert not view.grupo_archivo.isVisible()
        assert not view.bajada.isVisible()
        assert view.btn_ampliar.text() == "Reducir vista previa"
        assert view.grid_datos.height() > alto_normal * 1.5

        assert view.alternar_vista_previa() is False
        _QT_APP.processEvents()

        assert view.grupo_origen.isVisible()
        assert view.grupo_archivo.isVisible()
        assert view.bajada.isVisible()
        assert view.btn_ampliar.text() == "Ampliar vista previa"
        assert view.grid_datos.height() == alto_normal
    finally:
        view.close()


def test_ampliar_mantiene_oculto_el_resultado_hasta_reducir():
    view = _vista()
    try:
        view.mostrar_resultado(ResumenImportacion(leidos=2, importados=2))
        view.alternar_vista_previa()
        _QT_APP.processEvents()

        assert not view.grupo_resultado.isVisible()

        view.alternar_vista_previa()
        _QT_APP.processEvents()

        assert view.grupo_resultado.isVisible()
    finally:
        view.close()

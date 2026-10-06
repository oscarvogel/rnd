# coding=utf-8
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QSizePolicy


_QT_APP = QApplication.instance() or QApplication([])


def test_grilla_contenido_pallet_aprovecha_alto_disponible():
    from vistas.ArmadoPallets import ArmadoPalletsView

    view = ArmadoPalletsView()
    try:
        assert view.grilla_contenido.minimumHeight() >= 180
        assert view.grilla_contenido.maximumHeight() > 10000
        assert view.grilla_contenido.sizePolicy().verticalPolicy() == QSizePolicy.Expanding
    finally:
        view.close()

# coding=utf-8
"""Issue #68: codigo/QR e impresion operativa del pallet (Epic #58)."""

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from peewee import SqliteDatabase
from PyQt5.QtWidgets import QApplication


_QT_APP = QApplication.instance() or QApplication([])


_TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture()
def base_etiqueta():
    from modelos.Clientes import (
        Cliente, Localidades, LugarEntrega, RutaReparto,
    )
    from modelos.Empleados import ConceptoLiquidacion, Empleado
    from modelos.Equipos import Equipos
    from modelos.HojaRuta import HojaDeRuta
    from modelos.ModeloBase import Auditoria
    from modelos.ModeloBase import db as db_real
    from modelos.Pallet import Pallet, PalletDetalle
    from modelos.Tablas import TipoDeMovil

    modelos = [
        Auditoria, ConceptoLiquidacion, TipoDeMovil, RutaReparto,
        Localidades, Cliente, LugarEntrega, Empleado, Equipos,
        HojaDeRuta, Pallet, PalletDetalle,
    ]
    _TEST_DB.bind(modelos)
    _TEST_DB.connect()
    _TEST_DB.create_tables(modelos)
    try:
        yield {
            "Cliente": Cliente, "HojaDeRuta": HojaDeRuta,
            "Pallet": Pallet,
        }
    finally:
        _TEST_DB.drop_tables(modelos)
        _TEST_DB.close()
        db_real.bind(modelos)


def test_payload_qr_con_namespace():
    from utiles.etiqueta_pallet import (
        codigo_desde_payload, normalizar_codigo, payload_qr,
    )

    assert payload_qr("plt-20260928-001") == "RND-PALLET:PLT-20260928-001"
    assert payload_qr("") == ""
    assert codigo_desde_payload("RND-PALLET:PLT-20260928-001") == "PLT-20260928-001"
    assert codigo_desde_payload("plt-20260928-001") == "PLT-20260928-001"
    assert codigo_desde_payload("") == ""
    assert normalizar_codigo("  plt-1 ") == "PLT-1"


def test_qr_png_se_genera(tmp_path):
    from PIL import Image

    from utiles.etiqueta_pallet import generar_qr_png

    destino = str(tmp_path / "qr.png")
    ruta = generar_qr_png("PLT-20260928-001", destino=destino)
    assert ruta == destino
    with Image.open(destino) as imagen:
        assert imagen.size[0] > 100


def test_pdf_etiqueta_no_asume_cliente_unico(tmp_path):
    from utiles.etiqueta_pallet import generar_pdf_etiqueta, lineas_resumen

    destinos = [
        {"cliente": "Cinco Hermanos", "lugar_entrega": "Central",
         "cantidad": 24},
        {"cliente": "Ceferino", "lugar_entrega": "Sucursal",
         "cantidad": 1},
    ]
    assert len(lineas_resumen(destinos)) == 2

    qr_falso = str(tmp_path / "qr.png")
    from PIL import Image
    Image.new("RGB", (100, 100), "white").save(qr_falso)
    destino_pdf = str(tmp_path / "etiqueta.pdf")
    ruta = generar_pdf_etiqueta(
        "PLT-20260928-001",
        {"lineas": 2, "cantidad": 25, "kg": 300, "bultos": 25},
        destinos, qr_falso, destino_pdf=destino_pdf,
    )
    assert ruta == destino_pdf
    assert os.path.getsize(destino_pdf) > 1000


def _pallet_mixto(base_etiqueta):
    from modelos.Pallet import PalletDetalle, agregar_detalle, crear_pallet

    Cliente = base_etiqueta["Cliente"]
    HojaDeRuta = base_etiqueta["HojaDeRuta"]
    cliente_a = Cliente.create(razon_social="A")
    cliente_b = Cliente.create(razon_social="B")

    def linea(cliente, nombre, comprobante):
        return HojaDeRuta.create(
            fecha=date(2026, 9, 28), cliente=cliente,
            nombre_cliente=nombre, comprobante=comprobante, producto="P",
            cantidad=5, kg=50, cantidad_bultos=5, observaciones="",
            equipo_asignado=1, responsable=1,
        )

    pallet = crear_pallet()
    agregar_detalle(pallet, linea(cliente_a, "A", "FA"))
    agregar_detalle(pallet, linea(cliente_b, "B", "FB"))
    assert PalletDetalle.select().count() == 2
    return pallet


def test_buscar_por_codigo(base_etiqueta):
    from modelos.Pallet import buscar_por_codigo

    pallet = _pallet_mixto(base_etiqueta)
    assert buscar_por_codigo(pallet.codigo).id == pallet.id
    assert buscar_por_codigo(pallet.codigo.lower()).id == pallet.id
    assert buscar_por_codigo(
        "RND-PALLET:{}".format(pallet.codigo)
    ).id == pallet.id
    assert buscar_por_codigo("PLT-INEXISTENTE") is None
    assert buscar_por_codigo("") is None


def test_codigos_no_se_repiten(base_etiqueta):
    from modelos.Pallet import crear_pallet

    codigos = {crear_pallet().codigo for _ in range(3)}
    assert len(codigos) == 3


def test_dialogo_muestra_qr_y_composicion(base_etiqueta):
    from vistas.EtiquetaPallet import EtiquetaPalletDialog

    pallet = _pallet_mixto(base_etiqueta)
    dialogo = EtiquetaPalletDialog()
    assert dialogo.mostrar_pallet(pallet.id) is True
    assert dialogo.lbl_codigo.text() == pallet.codigo
    assert dialogo.lbl_qr.pixmap() is not None
    assert not dialogo.lbl_qr.pixmap().isNull()
    assert "2 líneas" in dialogo.lbl_resumen.text()
    assert "A" in dialogo.lbl_destinos.text()
    assert "B" in dialogo.lbl_destinos.text()

    assert dialogo.mostrar_pallet("PLT-INEXISTENTE") is False
    assert "No se encontró" in dialogo.lbl_error.text()
    dialogo.close()


def test_pdf_etiqueta_desde_controlador(base_etiqueta, tmp_path):
    from controladores.ArmadoPallets import ArmadoPalletsController

    pallet = _pallet_mixto(base_etiqueta)
    controller = ArmadoPalletsController.__new__(ArmadoPalletsController)
    destino_pdf = str(tmp_path / "etiqueta_ctrl.pdf")
    ruta = controller.pdf_etiqueta(pallet.id, destino_pdf=destino_pdf)
    assert ruta == destino_pdf
    assert os.path.getsize(destino_pdf) > 1000

    dialogo = controller.dialogo_etiqueta(pallet.id)
    assert dialogo is not None
    assert dialogo.pallet_actual_id() == pallet.id
    dialogo.close()
    assert controller.dialogo_etiqueta(999999) is None

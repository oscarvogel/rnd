# coding=utf-8
import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication

from controladores.RemitosTioPujio import RemitosTioPujioController
from utiles.remitos_tio_pujio import (
    ESTADO_ASIGNADO,
    ESTADO_AMBIGUO,
    ESTADO_SIN_PEDIDO,
    PedidoCruce,
    RemitoImportado,
    ResultadoCruce,
)
from vistas.RemitosTioPujio import RemitosTioPujioView


_APP = QApplication.instance() or QApplication([])


def _resultado(estado=ESTADO_ASIGNADO, motivo=""):
    remito = RemitoImportado(
        numero_remito="R0003-00073508",
        codigo_cliente="757",
        nombre_cliente="GAUZE SRL",
        fecha=date(2026, 9, 8),
        importe_total=-866895.06,
    )
    pedido = PedidoCruce(
        numero_pedido="N0001-00116681",
        codigo_cliente="757",
        importe_total=823928.22,
    )
    return ResultadoCruce(
        remito=remito,
        pedido=pedido,
        estado=estado,
        motivo=motivo,
    )


def test_vista_remitos_tiene_dos_botones_excel_y_grilla():
    view = RemitosTioPujioView()

    assert view.btn_pedidos.text() == "Seleccionar Excel"
    assert view.btn_remitos.text() == "Seleccionar Excel"
    assert view.btn_cruzar.text() == "Leer y cruzar"
    assert view.btn_grabar.text() == "Grabar remitos"
    assert view.tabla.columnCount() == 8
    assert not view.btn_grabar.isEnabled()

    view.close()


def test_vista_carga_resultados_en_la_grilla():
    view = RemitosTioPujioView()

    view.cargar_resultados([_resultado()])

    assert view.tabla.rowCount() == 1
    assert view.tabla.item(0, 1).text() == "R0003-00073508"
    assert view.tabla.item(0, 3).text() == "GAUZE SRL"
    assert view.tabla.item(0, 5).text() == "N0001-00116681"
    assert view.tabla.item(0, 6).text() == "Asignado"

    view.close()


def test_vista_muestra_estados_de_revision():
    view = RemitosTioPujioView()

    view.cargar_resultados(
        [
            _resultado(ESTADO_AMBIGUO, "total fuera de rango"),
            _resultado(ESTADO_SIN_PEDIDO, "no hay pedido para el cliente"),
        ]
    )

    assert view.tabla.item(0, 6).text() == "Revisar"
    assert view.tabla.item(1, 6).text() == "Sin pedido"

    view.close()


def test_controlador_puede_abrirse_sin_proveedor_predefinido():
    controller = RemitosTioPujioController()
    assert controller.proveedor_id == 0
    controller.view.close()


def test_controlador_solo_habilita_grabar_si_hay_asignados_nuevos():
    controller = RemitosTioPujioController(proveedor_id=16)
    assert controller._hay_para_grabar() is False

    controller.resultados = [_resultado(ESTADO_ASIGNADO)]
    assert controller._hay_para_grabar() is True

    controller.resultados = [_resultado(ESTADO_ASIGNADO, "ya estaba asociado")]
    assert controller._hay_para_grabar() is False

    controller.view.close()


def test_controlador_muestra_todo_guardado_si_no_hay_nuevos():
    controller = RemitosTioPujioController(proveedor_id=16)
    controller.resultados = [_resultado(ESTADO_ASIGNADO, "ya estaba asociado")]

    controller._actualizar_estado_mensaje()
    controller._actualizar_estado_grabar()

    assert "ya estaban asociados" in controller.view.lbl_estado.text()
    assert controller.view.btn_grabar.text() == "Todo guardado"
    assert not controller.view.btn_grabar.isEnabled()
    controller.view.close()


def test_controlador_muestra_mensaje_de_remitos_pendientes():
    controller = RemitosTioPujioController(proveedor_id=16)
    controller.resultados = [_resultado(ESTADO_ASIGNADO)]

    controller._actualizar_estado_mensaje()
    controller._actualizar_estado_grabar()

    assert "para grabar" in controller.view.lbl_estado.text()
    assert controller.view.btn_grabar.text() == "Grabar remitos"
    assert controller.view.btn_grabar.isEnabled()
    controller.view.close()


def test_resumen_avisa_cuando_no_hay_cambios():
    controller = RemitosTioPujioController(proveedor_id=16)
    controller._pedidos_archivo = 1
    controller._pedidos_sistema = 1

    texto = controller._texto_resumen(
        [_resultado(ESTADO_ASIGNADO, "ya estaba asociado")]
    )

    assert "No hay cambios pendientes" in texto
    controller.view.close()


def test_resumen_informa_pedidos_faltantes():
    controller = RemitosTioPujioController(proveedor_id=16)
    controller._pedidos_archivo = 57
    controller._pedidos_sistema = 54

    texto = controller._texto_resumen([_resultado()])

    assert "Para grabar: 1" in texto
    assert "Pedidos en el sistema: 54/57" in texto
    assert "Faltan importar 3 pedido(s)" in texto

    controller.view.close()

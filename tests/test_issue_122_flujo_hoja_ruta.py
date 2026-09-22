# coding=utf-8
"""Regresiones del flujo operativo de hoja de ruta (issue #122)."""

import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication


ROOT = Path(__file__).resolve().parents[1]


def _app():
    return QApplication.instance() or QApplication([])


def test_asignacion_muestra_revision_como_siguiente_paso_y_oculta_atajo_validacion():
    app = _app()
    assert app is not None
    from vistas.AsignacionRecursos import AsignacionRecursosView

    view = AsignacionRecursosView()
    try:
        assert view.btn_ver_hoja.text() == "Revisar hoja de ruta"
        assert view.btn_siguiente.isHidden()
        view.mostrar_exito(
            date(2026, 9, 22),
            "Centro",
            "Juan Perez",
            "Camion 10",
        )
        assert view.btn_ver_hoja.isEnabled()
        assert not view.panel_exito.isHidden()
        assert "Hoja lista para revisar" in view.lbl_exito.text()
    finally:
        view.deleteLater()


def test_revision_continua_a_validacion_con_misma_fecha_y_ruta():
    from controladores.VerHojaRuta import VerHojaRutaController

    controller = VerHojaRutaController.__new__(VerHojaRutaController)
    controller.view = MagicMock()
    controller.view.cbo_ruta_reparto.valor.return_value = 7
    controller.view.fecha_reparto.valor.return_value = date(2026, 9, 22)

    destino = MagicMock()
    with patch(
        "controladores.ValidacionHojaRuta.ValidacionHojaRutaController",
        return_value=destino,
    ) as crear:
        controller.ir_validacion()

    crear.assert_called_once_with(
        fecha_inicial=date(2026, 9, 22),
        ruta_inicial=7,
    )
    destino.run.assert_called_once_with()
    controller.view.close.assert_called_once_with()


def test_validacion_abre_hoja_para_imprimir_sin_anidar_otro_continuar():
    from controladores.ValidacionHojaRuta import ValidacionHojaRutaController

    controller = ValidacionHojaRutaController.__new__(ValidacionHojaRutaController)
    controller.view = MagicMock()
    controller.view.ruta_id.return_value = 9
    controller.fecha_actual = MagicMock(return_value=date(2026, 9, 22))

    destino = MagicMock()
    with patch(
        "controladores.VerHojaRuta.VerHojaRutaController",
        return_value=destino,
    ) as crear:
        controller.ver_hoja_ruta()

    crear.assert_called_once_with(
        fecha_inicial=date(2026, 9, 22),
        ruta_inicial=9,
        permitir_continuar=False,
    )
    destino.run.assert_called_once_with()


def test_validacion_lista_habilita_ver_imprimir_y_despachar():
    app = _app()
    assert app is not None
    from vistas.ValidacionHojaRuta import ValidacionHojaRutaView

    view = ValidacionHojaRutaView()
    resultado = SimpleNamespace(
        pedidos=3,
        kg=1250,
        bultos=42,
        items=[],
        valida=True,
    )
    try:
        view.mostrar(resultado, "LISTA")
        assert view.btn_hoja.isEnabled()
        assert view.btn_despachar.isEnabled()
        assert "Genere o revise el PDF" in view.lbl_mensaje.text()
    finally:
        view.deleteLater()


def test_dashboard_se_recarga_al_recuperar_el_foco_principal():
    source = (ROOT / "vistas/Main.py").read_text(encoding="utf-8")
    assert "QEvent.WindowActivate" in source
    assert "_recargar_dashboard_si_visible" in source
    assert "dashboard.recargar()" in source


def test_flujo_organizar_asignar_revisar_no_deja_ventanas_anteriores_abiertas():
    bandeja = (ROOT / "controladores/BandejaPedidos.py").read_text(encoding="utf-8")
    asignacion = (ROOT / "controladores/AsignacionRecursos.py").read_text(encoding="utf-8")
    revision = (ROOT / "controladores/VerHojaRuta.py").read_text(encoding="utf-8")

    assert "self.ventana_siguiente.run()\n        self.view.close()" in bandeja
    assert "self.ventana_hoja.run()\n        # El flujo continúa" in asignacion
    assert "self.ventana_validacion.run()\n        self.view.close()" in revision

# coding=utf-8
"""Regresiones del flujo operativo de hoja de ruta (issue #122)."""

import os
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import Qt
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



def test_asignacion_usa_combos_autocomplete_y_no_acepta_texto_invalido():
    app = _app()
    assert app is not None
    from vistas.AsignacionRecursos import AsignacionRecursosView

    view = AsignacionRecursosView()
    try:
        view.cargar_responsables([(7, "Juan Perez"), (8, "Maria Gomez")])
        view.cargar_equipos([(11, "Camion 11"), (12, "Camion 12")])

        assert view.cbo_responsable.isEditable()
        assert view.cbo_equipo.isEditable()
        assert view.cbo_responsable.completer().caseSensitivity() == Qt.CaseInsensitive
        assert view.cbo_responsable.completer().filterMode() == Qt.MatchContains

        view.cbo_responsable.setEditText("Juan Perez")
        assert view.responsable_id() == 7

        view.cbo_responsable.setCurrentIndex(1)
        view.cbo_responsable.setEditText("Nombre que no existe")
        assert view.responsable_id() == 0
    finally:
        view.deleteLater()


def test_ver_hoja_muestra_recursos_solo_lectura_y_deriva_a_asignacion():
    app = _app()
    assert app is not None
    from vistas.VerHojaRuta import VerHojaRutaView

    view = VerHojaRutaView()
    try:
        assert view.btn_recursos.text() == "Modificar chofer / camión"
        assert view.btn_grabar.isHidden()
        view.mostrar_recursos("Juan Perez", "Camion 11")
        assert view.lbl_chofer.text() == "Juan Perez"
        assert view.lbl_camion.text() == "Camion 11"
    finally:
        view.deleteLater()


def test_modificar_recursos_conserva_fecha_ruta_y_cierra_revision_actual():
    from controladores.VerHojaRuta import VerHojaRutaController

    controller = VerHojaRutaController.__new__(VerHojaRutaController)
    controller.view = MagicMock()
    controller.view.cbo_ruta_reparto.valor.return_value = 4
    controller.view.fecha_reparto.valor.return_value = date(2026, 9, 22)

    destino = MagicMock()
    with patch(
        "controladores.AsignacionRecursos.AsignacionRecursosController",
        return_value=destino,
    ) as crear:
        controller.modificar_recursos()

    crear.assert_called_once_with(
        fecha_inicial=date(2026, 9, 22),
        ruta_inicial=4,
    )
    destino.run.assert_called_once_with()
    controller.view.close.assert_called_once_with()


def test_hoja_lista_con_recursos_pendientes_se_marca_como_inconsistente():
    app = _app()
    assert app is not None
    from vistas.VerHojaRuta import VerHojaRutaView

    view = VerHojaRutaView()
    try:
        view.mostrar_estado_operativo(
            "LISTA",
            8,
            2920.76,
            698,
            permitir_continuar=True,
            recursos_completos=False,
        )
        assert "REQUIERE CORRECCIÓN" in view.lbl_estado_operativo.text()
        assert not view.btn_continuar.isEnabled()
        assert not view.btn_imprimir.isEnabled()
        assert view.btn_imprimir.text() == "PDF no disponible"
    finally:
        view.deleteLater()



def test_revision_no_expone_checkbox_ni_ids_internos():
    app = _app()
    assert app is not None
    from vistas.VerHojaRuta import VerHojaRutaView

    view = VerHojaRutaView()
    try:
        encabezados = [
            view.grilla_datos.horizontalHeaderItem(i).text()
            for i in range(view.grilla_datos.columnCount())
        ]
        assert "Selecciona" not in encabezados
        assert view.grilla_datos.isColumnHidden(encabezados.index("id"))
        assert view.grilla_datos.isColumnHidden(encabezados.index("codigo_cliente"))
    finally:
        view.deleteLater()


def test_cambio_de_recursos_invalida_estado_lista_y_bloquea_despachadas():
    source = (ROOT / "controladores" / "AsignacionRecursos.py").read_text(
        encoding="utf-8"
    )
    assert "estado.estado == EstadoHojaRuta.DESPACHADA" in source
    assert "No se pueden modificar sus recursos" in source
    assert "estado.estado = EstadoHojaRuta.EN_PREPARACION" in source

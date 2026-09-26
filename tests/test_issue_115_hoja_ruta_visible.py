# coding=utf-8
"""Regresiones de visibilidad para issue #115."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_asignacion_expone_accion_directa_a_hoja():
    vista = _source("vistas/AsignacionRecursos.py")
    controlador = _source("controladores/AsignacionRecursos.py")
    assert "Revisar hoja de ruta" in vista
    assert "Volver al dashboard" in vista
    assert "Asignación guardada" in vista
    assert "mostrar_exito" in controlador
    assert "VerHojaRutaController(" in controlador
    assert "ruta_inicial=self.view.ruta_id()" in controlador


def test_ver_hoja_recibe_ruta_y_destaca_impresion():
    vista = _source("vistas/VerHojaRuta.py")
    controlador = _source("controladores/VerHojaRuta.py")
    assert "Imprimir PDF" in vista
    assert "Actualizar" in vista
    assert 'setProperty("role", "primary")' in vista
    assert "ruta_inicial=0" in controlador
    assert "showMaximized()" in controlador
    assert "No hay datos para esta fecha y ruta" in controlador


def test_dashboard_abre_hoja_con_ruta_y_muestra_estado():
    dashboard = _source("vistas/dashboard/dashboard_view.py")
    servicios = _source("vistas/dashboard/servicios.py")
    main = _source("controladores/Main.py")
    assert 'NAV_HOJAS_RUTA_DIA + "|"' not in dashboard  # se compone de forma segura
    assert "self._ruta_hero" in dashboard
    assert "Lista para imprimir" in servicios
    assert "Lista para revisar" in servicios
    assert "Pendiente de asignación" in servicios
    assert "cantidad=len(por_ruta)" in servicios
    assert "ruta_inicial=ruta_id" in main


def test_ver_hoja_no_dereferencia_recursos_genericos_inexistentes():
    controlador = _source("controladores/VerHojaRuta.py")
    assert "def _fk_id" in controlador
    assert "def _cargar_recurso" in controlador
    assert ".responsable.id" not in controlador
    assert ".equipo_asignado.id" not in controlador
    assert 'getattr(registro, "{}_id".format(atributo), 0)' in controlador
    assert "modelo.get_or_none(modelo.id == recurso_id)" in controlador

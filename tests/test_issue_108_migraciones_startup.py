# coding=utf-8
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtWidgets import QApplication, QDialog

from vistas.MigracionProgress import MigracionProgressDialog


ROOT = Path(__file__).resolve().parents[1]
_APP = None


def _app():
    global _APP
    if _APP is None:
        _APP = QApplication.instance() or QApplication([])
    return _APP


def test_issue_108_login_espera_migracion_antes_del_dashboard():
    source = (ROOT / "controladores" / "Main.py").read_text(encoding="utf-8")
    login = source[source.index("    def login("):source.index("    def _ejecutar_migraciones_con_feedback(")]

    assert "self._ejecutar_migraciones_con_feedback()" in login
    assert "self._inicializar_dashboard" in login
    assert login.index("self._ejecutar_migraciones_con_feedback()") < login.index(
        "self._inicializar_dashboard"
    )


def test_issue_108_modal_es_indeterminado_y_no_cancelable():
    _app()
    dialogo = MigracionProgressDialog()

    assert dialogo.isModal()
    assert dialogo.progreso.minimum() == 0
    assert dialogo.progreso.maximum() == 0

    dialogo.reject()
    assert dialogo.result() == 0

    dialogo.finalizar()
    assert dialogo.result() == QDialog.Accepted


def test_issue_108_migracion_expone_error_al_controlador():
    source = (ROOT / "controladores" / "Migraciones.py").read_text(encoding="utf-8")

    assert "self.error = None" in source
    assert "self.error = exc" in source
    assert 'logging.exception("Falló la migración de la base de datos")' in source

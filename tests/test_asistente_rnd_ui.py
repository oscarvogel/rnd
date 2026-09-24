# coding=utf-8
from pathlib import Path


def test_panel_asistente_es_toggleable_y_no_tiene_burbuja_permanente():
    source = Path("vistas/AsistenteRndPanel.py").read_text(encoding="utf-8")

    assert "class AsistenteRndPanel(QWidget)" in source
    assert "def show_panel(self):" in source
    assert "def hide_panel(self):" in source
    assert "def toggle(self):" in source
    assert "self.btn_close.clicked.connect(self.hide_panel)" in source
    assert "Qt.Key_Escape" in source
    assert "BUBBLE_SIZE" not in source
    assert "show_bubble" not in source


def test_panel_conserva_historial_al_ocultarse():
    source = Path("vistas/AsistenteRndPanel.py").read_text(encoding="utf-8")

    assert "self.history = []" in source
    hide_block = source.split("def hide_panel(self):", 1)[1].split(
        "def toggle(self):", 1
    )[0]
    assert "self.hide()" in hide_block
    assert "self.history.clear" not in hide_block
    assert "self.history = []" not in hide_block


def test_main_expone_asistente_por_boton_y_f1_global():
    main = Path("controladores/Main.py").read_text(encoding="utf-8")
    header = Path("vistas/shell/Encabezado.py").read_text(encoding="utf-8")

    assert 'QShortcut(QKeySequence("F1"), self.view)' in main
    assert "Qt.ApplicationShortcut" in main
    assert "activated.connect(self.toggle_asistente)" in main
    assert "boton_asistente.clicked.connect(self.toggle_asistente)" in main
    assert 'QPushButton("Vogel IA")' in header
    assert 'setObjectName("encabezadoBotonAsistente")' in header
    assert 'logo_oscar_sin_fondo.png' in header
    assert 'QSize(20, 20)' in header


def test_fallo_ia_se_muestra_sin_traceback_en_panel():
    source = Path("vistas/AsistenteRndPanel.py").read_text(encoding="utf-8")

    assert "except Exception as exc:" in source
    assert "self.error.emit(str(exc))" in source
    assert "El asistente no está disponible en este momento." in source
    assert "traceback" not in source.lower()



def test_boton_asistente_usa_identidad_visual_vogel():
    theme = Path("temas/vogel2026.qss").read_text(encoding="utf-8")

    assert "QPushButton#encabezadoBotonAsistente" in theme
    assert "stop:0 #19B9E7" in theme
    assert "stop:1 #0866C8" in theme
    assert "#F5C518" in theme
    assert "border-radius: 16px" in theme



def test_panel_se_mantiene_visible_sobre_abm_sin_robar_foco():
    source = Path("vistas/AsistenteRndPanel.py").read_text(encoding="utf-8")

    assert "QTimer" in source
    assert "setInterval(300)" in source
    assert "timeout.connect(self._keep_visible_above_rnd)" in source
    assert "def _set_native_topmost(self, enabled):" in source
    assert "user32.SetWindowPos" in source
    assert "SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW" in source
    assert "self._set_native_topmost(True)" in source
    assert "self._set_native_topmost(False)" in source

    keep_block = source.split("def _keep_visible_above_rnd(self):", 1)[1].split(
        "def show_panel(self):", 1
    )[0]
    assert "activateWindow()" not in keep_block


def test_panel_se_ancla_al_borde_derecho_de_la_pantalla():
    source = Path("vistas/AsistenteRndPanel.py").read_text(encoding="utf-8")

    dock_block = source.split("def _dock_right(self):", 1)[1].split(
        "def _keep_visible_above_rnd(self):", 1
    )[0]
    assert "available.right() - self.width() - PANEL_MARGIN + 1" in dock_block
    assert "reference.right()" not in dock_block

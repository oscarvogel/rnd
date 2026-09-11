# coding=utf-8
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOGIN = ROOT / "vistas" / "Login.py"
ASSETS = ROOT / "assets" / "login"


def test_login_moderno_mantiene_contrato_y_marca():
    source = LOGIN.read_text(encoding="utf-8")

    for atributo in (
        "self.cboUsuario",
        "self.textPass",
        "self.btnIngresar",
        "self.btnCerrar",
    ):
        assert atributo in source

    assert "RND Logística - Inicio de sesión" in source
    assert "Desarrollado por" in source
    assert "vogelconsultoria.com.ar" in source


def test_login_usa_recursos_svg_y_no_dibujo_manual():
    source = LOGIN.read_text(encoding="utf-8")

    assert 'SvgImageLabel("rnd_hero.svg")' in source
    assert 'SvgImageLabel("rnd_logo.svg")' in source
    assert 'SvgImageLabel("vogel_logo.svg")' in source
    assert "paintEvent" not in source
    assert "QPainter" not in source

    for filename in ("rnd_hero.svg", "rnd_logo.svg", "vogel_logo.svg"):
        path = ASSETS / filename
        assert path.exists()
        assert "<svg" in path.read_text(encoding="utf-8")

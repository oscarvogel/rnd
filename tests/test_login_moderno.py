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
    assert "rnd_login_mockup.b64" in source


def test_login_usa_mockup_aprobado_y_controles_reales():
    source = LOGIN.read_text(encoding="utf-8")

    assert "base64.b64decode" in source
    assert "self.background" in source
    assert "self.cboUsuario = CboUsuario(Form)" in source
    assert "self.textPass = Password(Form)" in source
    assert "self.btnIngresar = QPushButton" in source
    assert "self.btnCerrar = QPushButton" in source
    assert "QPainter" not in source
    assert "paintEvent" not in source

    asset = ASSETS / "rnd_login_mockup.b64"
    assert asset.exists()
    assert len(asset.read_text(encoding="ascii").strip()) > 10000

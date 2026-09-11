# coding=utf-8
from pathlib import Path


def test_login_moderno_mantiene_contrato_y_marca():
    source = (Path(__file__).resolve().parents[1] / "vistas" / "Login.py").read_text(
        encoding="utf-8"
    )

    # Contrato que consume LoginController.
    for atributo in ("self.cboUsuario", "self.textPass", "self.btnIngresar", "self.btnCerrar"):
        assert atributo in source

    # Identidad aprobada para RND + Vogel.
    assert "Logística y Distribución" in source
    assert "Desarrollado por" in source
    assert "V O G E L" in source
    assert "vogelconsultoria.com.ar" in source


def test_login_moderno_no_depende_de_mockup_binario():
    source = (Path(__file__).resolve().parents[1] / "vistas" / "Login.py").read_text(
        encoding="utf-8"
    )
    assert "class LogisticsHero" in source
    assert "paintEvent" in source
    assert "RNDLogoWidget" in source

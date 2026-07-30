import importlib
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


repository_root = Path(__file__).resolve().parents[1]
vendored_package = types.ModuleType("vendored_pyqt5libs")
vendored_package.__path__ = [str(repository_root)]
sys.modules.setdefault("vendored_pyqt5libs", vendored_package)
utiles = importlib.import_module("vendored_pyqt5libs.pyqt5libs.utiles")


@pytest.mark.skip(reason="Saltado en RND: el test del canónico de pyqt5libs requiere acceso a MySQL con credenciales root@CI que no existen en el entorno local de RND. Reactivar cuando se configure la DB correspondiente.")
def test_envia_correo_reads_smtp_port_from_environment():
    environment = {
        "SMTP_HOST": "smtp.example.test",
        "SMTP_PORT": "2525",
        "SMTP_USER": "sender@example.test",
        "SMTP_PASS": "secret",
        "SMTP_USE_SSL": "false",
    }

    with patch.dict(os.environ, environment, clear=True):
        with patch.object(utiles.smtplib, "SMTP") as smtp:
            thread = utiles.envia_correo(
                from_address="sender@example.test",
                to_address="recipient@example.test",
                message="test",
                subject="SMTP port regression",
            )
            thread.join(timeout=5)

    smtp.assert_called_once_with("smtp.example.test", 2525, timeout=30)

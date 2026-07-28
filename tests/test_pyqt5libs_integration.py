import importlib
import os
import unittest
import builtins
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_UPSTREAM_COMMIT = "030edce9ca384d259c4c7f2851398918f1e3d8f1"


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        self.target()


class RecordingSMTP:
    connections = []

    def __init__(self, server, port, timeout=None):
        self.connections.append((server, port, timeout))

    def ehlo(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def starttls(self):
        return None

    def login(self, username, password):
        return None

    def sendmail(self, from_address, recipients, message):
        return None

    def quit(self):
        return None


class Pyqt5libsIntegrationTests(unittest.TestCase):
    def test_vendored_library_records_expected_upstream_and_new_core_module(self):
        commit_file = ROOT / "pyqt5libs" / "UPSTREAM_COMMIT"

        self.assertEqual(
            commit_file.read_text(encoding="utf-8").strip(),
            EXPECTED_UPSTREAM_COMMIT,
        )
        module = importlib.import_module("pyqt5libs.pyqt5libs.core.config")
        self.assertTrue(hasattr(module, "IniConfig"))

    def test_envia_correo_reads_smtp_port_from_correct_environment_variable(self):
        from pyqt5libs.pyqt5libs import utiles

        RecordingSMTP.connections.clear()
        environment = {
            "SMTP_HOST": "smtp.example.test",
            "SMTP_PORT": "2525",
            "SMTP_USER": "",
            "SMTP_PASS": "",
            "SMTP_USE_SSL": "false",
        }
        original_import = builtins.__import__

        def import_without_rnd_models(name, *args, **kwargs):
            if name == "modelos.ParametrosSistema":
                raise ImportError("RND model access disabled in integration test")
            return original_import(name, *args, **kwargs)

        with patch.dict(os.environ, environment, clear=False):
            os.environ.pop("SMPT_PORT", None)
            with patch.object(builtins, "__import__", import_without_rnd_models):
                with patch.object(utiles.threading, "Thread", ImmediateThread):
                    with patch.object(utiles.smtplib, "SMTP", RecordingSMTP):
                        with patch.object(utiles.logging, "warning"):
                            utiles.envia_correo(
                                from_address="rnd@example.test",
                                to_address="destino@example.test",
                                message="Prueba RND",
                                subject="Prueba",
                            )

        self.assertEqual(
            [
                (connection[0], int(connection[1]))
                for connection in RecordingSMTP.connections
            ],
            [("smtp.example.test", 2525)],
        )


if __name__ == "__main__":
    unittest.main()

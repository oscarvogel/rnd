import os
import subprocess
import tempfile
import unittest
import warnings
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv-build" / "Scripts" / "python.exe"
EXPECTED_SCREENS = {
    "login": "Inicio de sistema",
    "clientes": "Gestión de Tabla de Clientes",
    "importacion_pedidos": "Importación de Pedidos",
    "hoja_ruta": "Ver Hoja de Ruta",
}


class GuiSmokeTests(unittest.TestCase):
    def test_render_screens_creates_four_real_view_captures_without_database(self):
        from tools.render_meet_screens import render_screens

        with tempfile.TemporaryDirectory() as output_dir:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                manifest = render_screens(output_dir)

            self.assertEqual(set(manifest), set(EXPECTED_SCREENS))
            for screen_name, expected_title in EXPECTED_SCREENS.items():
                with self.subTest(screen=screen_name):
                    screen = manifest[screen_name]
                    image_path = Path(screen["path"])
                    self.assertEqual(screen["title"], expected_title)
                    self.assertGreaterEqual(screen["width"], 640)
                    self.assertGreaterEqual(screen["height"], 180)
                    self.assertGreater(screen["controls"], 3)
                    self.assertTrue(image_path.exists())
                    self.assertGreater(image_path.stat().st_size, 1_000)
                    if screen_name == "login":
                        self.assertGreaterEqual(screen["images"], 1)
                        self.assertLessEqual(screen["max_image_width"], 160)

    def test_cli_renders_screens_from_repository_root(self):
        with tempfile.TemporaryDirectory() as output_dir:
            environment = os.environ.copy()
            environment["QT_QPA_PLATFORM"] = "offscreen"
            result = subprocess.run(
                [
                    str(PYTHON),
                    "tools/render_meet_screens.py",
                    "--output",
                    output_dir,
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"login"', result.stdout)


if __name__ == "__main__":
    unittest.main()

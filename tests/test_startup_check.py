import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)


class StartupCheckTests(unittest.TestCase):
    def run_startup_check(self, *args):
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        return subprocess.run(
            [str(PYTHON), "main.py", "--startup-check", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_startup_check_succeeds_without_opening_ui(self):
        result = self.run_startup_check("-i", ".", "-a", "sistema.ini")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STARTUP_CHECK_OK", result.stdout)
        self.assertIn("sistema.ini", result.stdout)

    def test_startup_check_fails_when_config_is_missing(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            result = self.run_startup_check("-i", empty_dir, "-a", "sistema.ini")

        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn("STARTUP_CHECK_ERROR", output)
        self.assertIn("sistema.ini", output)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

import rnd_credentials
import run_local


class LocalEnvironmentTests(unittest.TestCase):
    def test_production_keeps_historical_credential_filename(self):
        path = rnd_credentials.credential_path({"ProgramData": r"C:\ProgramData"})
        self.assertEqual(path.name, "mysql.credential")

    def test_local_profile_uses_separate_credential_filename(self):
        path = rnd_credentials.credential_path(
            {
                "ProgramData": r"C:\ProgramData",
                "RND_CREDENTIAL_PROFILE": "local",
            }
        )
        self.assertEqual(path.name, "mysql.local.credential")

    def test_local_config_is_created_from_template_and_requires_rerun(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            (base / run_local.LOCAL_TEMPLATE).write_text(
                "[param]\nhost=127.0.0.1\n", encoding="utf-8"
            )

            ready = run_local._prepare_local_config(base)

            self.assertFalse(ready)
            self.assertTrue((base / run_local.LOCAL_INI).exists())

    def test_existing_local_config_is_used_without_touching_production(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            local_ini = base / run_local.LOCAL_INI
            production_ini = base / "sistema.ini"
            local_ini.write_text("local", encoding="utf-8")
            production_ini.write_text("production", encoding="utf-8")

            ready = run_local._prepare_local_config(base)

            self.assertTrue(ready)
            self.assertEqual(production_ini.read_text(encoding="utf-8"), "production")


if __name__ == "__main__":
    unittest.main()

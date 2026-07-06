import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingStaticTests(unittest.TestCase):
    def test_pyinstaller_spec_includes_runtime_resources(self):
        spec = (ROOT / "main.spec").read_text(encoding="utf-8")

        for resource in ("imagenes", "temas", "sistema.ini", "rnd.ini"):
            with self.subTest(resource=resource):
                self.assertIn(resource, spec)

        self.assertIn("hooks\\\\rthook_pymysql.py", spec)
        self.assertIn("contents_directory='.'", spec)

    def test_inno_installer_uses_fixed_rnd_directory(self):
        installer = (ROOT / "installer" / "RND.iss").read_text(encoding="utf-8")

        expected_entries = (
            "DefaultDirName=C:\\RND",
            "DisableDirPage=yes",
            "UsePreviousAppDir=no",
            "PrivilegesRequired=admin",
            'Filename: "{app}\\sistema.ini"; Section: "param"; Key: "InicioSistema"; String: "{app}\\"',
            'Filename: "{app}\\rnd.ini"; Section: "param"; Key: "InicioSistema"; String: "{app}\\"',
        )

        for entry in expected_entries:
            with self.subTest(entry=entry):
                self.assertIn(entry, installer)

    def test_runtime_ini_defaults_point_to_c_rnd(self):
        for ini_name in ("sistema.ini", "rnd.ini"):
            with self.subTest(ini=ini_name):
                content = (ROOT / ini_name).read_text(encoding="utf-8")
                self.assertIn("InicioSistema = C:\\RND\\", content)


if __name__ == "__main__":
    unittest.main()

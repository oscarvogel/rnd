import re
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

        for dependency in (
            'collect_all("pyqt5libs")',
            'collect_all("libs")',
            "win32crypt",
            "win32com.shell.shell",
            "vistas.ConfigurarCredencialDB",
        ):
            with self.subTest(dependency=dependency):
                self.assertIn(dependency, spec)

    def test_pyinstaller_bundles_controllers_loaded_from_database_menu(self):
        spec = (ROOT / "main.spec").read_text(encoding="utf-8")

        self.assertIn('collect_submodules("controladores")', spec)
        self.assertIn("controller_hiddenimports", spec)
        self.assertRegex(
            spec,
            r"(?s)hiddenimports=.*controller_hiddenimports",
        )

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

        for guard in (
            "{param:DIR|}",
            "InitializeSetup",
            "PrepareToInstall",
            "WizardDirValue",
        ):
            with self.subTest(guard=guard):
                self.assertIn(guard, installer)

    def test_installer_preserves_ini_and_offers_launch(self):
        installer = (ROOT / "installer" / "RND.iss").read_text(encoding="utf-8")
        self.assertRegex(
            installer,
            r'Source: "\.\.\\dist\\main\\sistema\.ini";.*onlyifdoesntexist',
        )
        self.assertIn("postinstall", installer)
        self.assertIn("runasoriginaluser", installer)
        self.assertIn("Configurar conexión MySQL", installer)
        self.assertIn("--edit-db-connection", installer)

    def test_release_version_and_brand_are_consistent(self):
        expected = "2026.8.11.1"
        main_source = (ROOT / "main.py").read_text(encoding="utf-8")
        installer = (ROOT / "installer" / "RND.iss").read_text(encoding="utf-8")
        version_info = (ROOT / "version.txt").read_text(encoding="utf-8")
        sistema_ini = (ROOT / "sistema.ini").read_text(encoding="utf-8")

        self.assertEqual(
            re.search(r'__version__\s*=\s*"([^"]+)"', main_source).group(1),
            expected,
        )
        self.assertIn('#define AppVersion "{}"'.format(expected), installer)
        self.assertIn(
            "filevers=({})".format(", ".join(expected.split("."))),
            version_info,
        )
        self.assertIn("logo = vogel_consultoria_oficial.png", sistema_ini)
        self.assertIn("icono = vogel_consultoria_oficial.ico", sistema_ini)
        self.assertTrue((ROOT / "imagenes" / "vogel_consultoria_oficial.png").is_file())
        self.assertTrue((ROOT / "imagenes" / "vogel_consultoria_oficial.ico").is_file())

    def test_runtime_ini_defaults_point_to_c_rnd(self):
        for ini_name in ("sistema.ini", "rnd.ini"):
            with self.subTest(ini=ini_name):
                content = (ROOT / ini_name).read_text(encoding="utf-8")
                self.assertIn("InicioSistema = C:\\RND\\", content)


if __name__ == "__main__":
    unittest.main()

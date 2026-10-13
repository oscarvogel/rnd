import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackagingStaticTests(unittest.TestCase):
    def test_pyinstaller_spec_includes_runtime_resources(self):
        spec = (ROOT / "main.spec").read_text(encoding="utf-8")

        for resource in (
            "assets",
            "imagenes",
            "temas",
            "docs/asistente_rnd_conocimiento_tecnico.md",
            "sistema.ini",
            "rnd.ini",
        ):
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
        self.assertIn('#define MyAppVersion "{}"'.format(expected), installer)
        self.assertIn("#define AppVersion MyAppVersion", installer)
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


    def test_production_build_keeps_version_templates_clean(self):
        build_script = (ROOT / "scripts" / "build_installer.ps1").read_text(encoding="utf-8")
        spec = (ROOT / "main.spec").read_text(encoding="utf-8")

        self.assertIn("installer\\.production_build_state", build_script)
        self.assertIn("build\\generated", build_script)
        self.assertIn('"/DMyAppVersion=$Version"', build_script)
        self.assertNotIn("WriteAllText($VersionFile", build_script)
        self.assertNotIn("WriteAllText($IssFile", build_script)
        self.assertIn('os.environ.get("RND_VERSION_FILE", "version.txt")', spec)
        self.assertIn("version=version_file", spec)


if __name__ == "__main__":
    unittest.main()



def test_demo_packaging_includes_assistant_knowledge_and_ai_env():
    root = ROOT
    spec = (root / "installer" / "RND_Demo.spec").read_text(encoding="utf-8")
    build = (root / "scripts" / "build_demo_installer.ps1").read_text(
        encoding="utf-8"
    )
    iss = (root / "installer" / "RND_Demo.iss").read_text(encoding="utf-8")

    assert "../docs/asistente_rnd_conocimiento_tecnico.md" in spec
    assert 'dist\\RND Demo\\.env' in build
    assert 'Source: "..\\dist\\RND Demo\\*"' in iss


def test_demo_installer_never_packages_a_credential():
    """El instalador de la demo es publico: no puede llevar claves reales.

    Este test antes afirmaba lo contrario. Exigia que el build escribiera
    MINIMAX_API_KEY en dist\\RND Demo\\.env, lo cual fijaba la filtracion como
    contrato. Anyadir la proteccion sin tocarlo dejaba la suite en rojo y
    empujaba a revertir el arreglo.
    """
    build = (ROOT / "scripts" / "build_demo_installer.ps1").read_text(encoding="utf-8")

    # La lista blanca del build no puede incluir ninguna credencial.
    blanca = re.search(r"\$allowed = @\((.*?)\)", build, re.S)
    assert blanca, "No se encontro la lista blanca de variables IA"
    assert "MINIMAX_API_KEY" not in blanca.group(1)
    assert "RND_PDF_AI_API_KEY" not in blanca.group(1)
    assert "RND_PDF_AI_URL" in blanca.group(1)

    # Tampoco puede nombrarlas como algo que se escribe en el .env de la demo.
    escritura = re.search(r"\$order = @\((.*?)\)", build, re.S)
    assert escritura, "No se encontro el orden de escritura del .env de la demo"
    assert "MINIMAX_API_KEY" not in escritura.group(1)
    assert "RND_PDF_AI_API_KEY" not in escritura.group(1)

    # Y el build se verifica a si mismo antes de generar el instalador.
    assert "ABORTADO: la configuracion IA trae" in build
    assert "Values.ContainsKey($prohibida)" in build


def test_demo_installer_requires_the_proxy_url_not_a_key():
    build = (ROOT / "scripts" / "build_demo_installer.ps1").read_text(encoding="utf-8")

    assert 'ContainsKey("RND_PDF_AI_URL")' in build
    assert "RND_PDF_AI_TOKEN" in build


def test_proxy_keeps_the_provider_credential_out_of_the_docroot():
    """El proxy es lo unico que puede ver la clave que paga la IA.

    Si el secreto quedara bajo public_html, cualquiera que lo pida por HTTP
    se llevaria la credencial. Por eso la ruta sale con ../
    """
    deploy = ROOT / "deploy" / "rnd-ia"
    proxy = (deploy / "proxy.php").read_text(encoding="utf-8")

    assert "__DIR__ . '/../rnd-ia-secreto.php'" in proxy
    assert (deploy / "rnd-ia-secreto.php.ejemplo").is_file()
    assert (deploy / ".htaccess").is_file()

    # El ejemplo se puede publicar: nunca trae una clave real.
    ejemplo = (deploy / "rnd-ia-secreto.php.ejemplo").read_text(encoding="utf-8")
    assert "PEGAR_AQUI_LA_CLAVE" in ejemplo
    assert "MINIMAX_API_KEY" not in ejemplo
    assert "sk-" not in ejemplo

    # OpenRouter: la politica de datos se fuerza en el proxy y no depende de
    # que alguien la haya activado en el panel de la cuenta.
    assert "'data_collection'] = 'deny'" in proxy
    assert "'zdr'] = true" in proxy

import configparser
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import main
import rnd_credentials


class CredentialStorageTests(unittest.TestCase):
    def test_password_is_encrypted_with_machine_scope(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "RND" / "mysql.credential"
            with mock.patch.object(
                rnd_credentials.win32crypt,
                "CryptProtectData",
                return_value=b"encrypted-test-blob",
            ) as protect:
                rnd_credentials.save_machine_password("unit-test-secret", target)

            self.assertEqual(target.read_bytes(), b"encrypted-test-blob")
            flags = protect.call_args.args[-1]
            self.assertTrue(flags & rnd_credentials.CRYPTPROTECT_LOCAL_MACHINE)
            self.assertTrue(flags & rnd_credentials.CRYPTPROTECT_UI_FORBIDDEN)

    def test_connection_metadata_is_saved_without_password(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            ini = Path(temp_dir) / "sistema.ini"
            ini.write_text(
                "[param]\nhost=old\nport=3306\nbasedatos=old\nuser=old\n"
                "password=remove-me\nlogo=keep.png\n",
                encoding="utf-8",
            )
            settings = rnd_credentials.MySQLSettings("new-host", 3307, "rnd", "rnd_user")
            rnd_credentials.save_mysql_settings(settings, ini)

            config = configparser.ConfigParser()
            config.read(ini, encoding="utf-8")
            self.assertEqual(config.get("param", "host"), "new-host")
            self.assertEqual(config.getint("param", "port"), 3307)
            self.assertEqual(config.get("param", "basedatos"), "rnd")
            self.assertEqual(config.get("param", "user"), "rnd_user")
            self.assertEqual(config.get("param", "logo"), "keep.png")
            self.assertFalse(config.has_option("param", "password"))

    def test_missing_credential_launches_configurator_once(self):
        resolver = mock.Mock(
            side_effect=[rnd_credentials.CredentialMissing(), "unit-test-password"]
        )
        launcher = mock.Mock(return_value=main.CREDENTIAL_CONFIGURED)
        validator = mock.Mock()
        settings = rnd_credentials.MySQLSettings("host", 3306, "rnd", "user")

        result = main._ensure_mysql_credential(
            r"C:\RND",
            "sistema.ini",
            resolver=resolver,
            launcher=launcher,
            settings_loader=mock.Mock(return_value=settings),
            validator=validator,
        )

        self.assertTrue(result)
        launcher.assert_called_once_with(r"C:\RND", "sistema.ini")
        validator.assert_called_once_with(settings, "unit-test-password")

    def test_windows_identity_matches_installer_shortcuts(self):
        setter = mock.Mock(return_value=0)
        self.assertTrue(main._set_windows_app_id(setter=setter, platform="win32"))
        setter.assert_called_once_with("VogelConsultoria.RND")

    def test_parser_exposes_connection_editor_mode(self):
        parsed = main._build_arg_parser().parse_args(["--edit-db-connection"])
        self.assertTrue(parsed.edit_db_connection)


if __name__ == "__main__":
    unittest.main()

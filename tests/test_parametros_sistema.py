import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.argv = [sys.argv[0]]

from modelos.ParametrosSistema import ParamSist


class MissingParameterQuery:
    def where(self, *_args, **_kwargs):
        return self

    def get(self):
        raise ParamSist.DoesNotExist()


class ExistingParameterQuery:
    def __init__(self, value):
        self.value = value

    def where(self, *_args, **_kwargs):
        return self

    def get(self):
        return SimpleNamespace(valor=self.value)


class ParamSistTests(unittest.TestCase):
    def test_obtener_parametro_returns_stored_value_when_exists(self):
        with patch.object(ParamSist, "select", return_value=ExistingParameterQuery("darkblue.css")):
            self.assertEqual(ParamSist.ObtenerParametro("TEMA", "qdark.css"), "darkblue.css")

    def test_obtener_parametro_returns_default_when_creating_missing_parameter(self):
        saved = []

        def fake_save(instance):
            saved.append((instance.parametro, instance.valor))
            return 1

        with (
            patch.object(ParamSist, "select", return_value=MissingParameterQuery()),
            patch.object(ParamSist, "save", autospec=True, side_effect=fake_save),
        ):
            value = ParamSist.ObtenerParametro("smtp_server", "localhost")

        self.assertEqual(value, "localhost")
        self.assertEqual(saved, [("smtp_server", "localhost")])


if __name__ == "__main__":
    unittest.main()

import hashlib
import json

import pytest

from utiles import actualizador


def _manifest(**overrides):
    data = {
        "schema_version": 1,
        "app_id": "rnd",
        "version": "2026.09.02.18.00.00",
        "download_url": "https://example.invalid/RND_Setup.exe",
        "sha256": "a" * 64,
        "notes": "Prueba",
    }
    data.update(overrides)
    return data


def test_version_comparison():
    assert actualizador.is_newer_version("2026.8.11.1", "2026.09.02.18.00.00")
    assert not actualizador.is_newer_version("2026.09.02.18.00.00", "2026.09.02.18.00.00")
    assert not actualizador.is_newer_version("2026.09.03", "2026.09.02.18.00.00")


def test_manifest_valid():
    assert actualizador.validate_manifest(_manifest())["app_id"] == "rnd"


@pytest.mark.parametrize(
    "data",
    [
        {},
        _manifest(app_id="otra"),
        _manifest(schema_version=2),
        _manifest(sha256="bad"),
        _manifest(version="x.y"),
    ],
)
def test_manifest_invalid(data):
    with pytest.raises((ValueError, TypeError)):
        actualizador.validate_manifest(data)


def test_sha256_file(tmp_path):
    target = tmp_path / "installer.exe"
    target.write_bytes(b"rnd")
    assert actualizador.sha256_file(target) == hashlib.sha256(b"rnd").hexdigest()


def test_fetch_network_error_is_exception(monkeypatch):
    def fail(*args, **kwargs):
        raise OSError("offline")

    monkeypatch.setattr(actualizador.urllib.request, "urlopen", fail)
    with pytest.raises(OSError):
        actualizador.fetch_manifest("https://example.invalid/latest.json")

import hashlib
import json
import logging
import os
import subprocess
import tempfile
import threading
import urllib.request

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from utiles.build_info import APP_ID, MANIFEST_URL


LOG = logging.getLogger(__name__)


def _version_tuple(value):
    try:
        return tuple(int(part) for part in str(value).strip().split("."))
    except (TypeError, ValueError):
        raise ValueError("Version invalida: {!r}".format(value))


def is_newer_version(current, published):
    return _version_tuple(published) > _version_tuple(current)


def validate_manifest(data):
    required = ("schema_version", "app_id", "version", "download_url", "sha256")
    if not isinstance(data, dict):
        raise ValueError("Manifest invalido")
    missing = [key for key in required if not data.get(key)]
    if missing:
        raise ValueError("Faltan campos del manifest: {}".format(", ".join(missing)))
    if data["app_id"] != APP_ID:
        raise ValueError("Manifest de otra aplicacion")
    if int(data["schema_version"]) != 1:
        raise ValueError("Schema de manifest no soportado")
    _version_tuple(data["version"])
    digest = str(data["sha256"]).lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError("SHA256 invalido")
    return data


def fetch_manifest(url=MANIFEST_URL, timeout=5):
    request = urllib.request.Request(url, headers={"User-Agent": "RND-Updater/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
    return validate_manifest(json.loads(payload))


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_installer(manifest, timeout=30):
    fd, path = tempfile.mkstemp(prefix="rnd-update-", suffix=".exe")
    os.close(fd)
    try:
        request = urllib.request.Request(
            manifest["download_url"], headers={"User-Agent": "RND-Updater/1"}
        )
        with urllib.request.urlopen(request, timeout=timeout) as response, open(path, "wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
        if sha256_file(path).lower() != str(manifest["sha256"]).lower():
            raise ValueError("SHA256 del instalador no coincide")
        return path
    except Exception:
        try:
            os.unlink(path)
        except OSError:
            pass
        raise


class UpdateCoordinator(QObject):
    update_found = pyqtSignal(dict)
    check_failed = pyqtSignal(str)

    def __init__(self, parent, current_version):
        super().__init__(parent)
        self.current_version = current_version
        self.update_found.connect(self._offer_update)
        self.check_failed.connect(self._log_check_error)

    def start(self):
        threading.Thread(target=self._check_worker, name="rnd-update-check", daemon=True).start()

    def _check_worker(self):
        try:
            manifest = fetch_manifest()
            if is_newer_version(self.current_version, manifest["version"]):
                self.update_found.emit(manifest)
        except Exception as exc:
            self.check_failed.emit(str(exc))

    def _log_check_error(self, message):
        LOG.warning("No se pudo comprobar actualizaciones de RND: %s", message)

    def _offer_update(self, manifest):
        notes = manifest.get("notes") or "Hay una nueva version disponible."
        text = "RND {} esta disponible.\n\n{}\n\n¿Desea actualizar ahora?".format(
            manifest["version"], notes
        )
        answer = QMessageBox.question(None, "Actualizacion de RND", text)
        if answer != QMessageBox.Yes:
            return
        threading.Thread(
            target=self._download_worker, args=(manifest,), name="rnd-update-download", daemon=True
        ).start()

    def _download_worker(self, manifest):
        try:
            installer = download_installer(manifest)
            subprocess.Popen([installer, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
            os._exit(0)
        except Exception as exc:
            LOG.exception("Fallo la actualizacion de RND: %s", exc)

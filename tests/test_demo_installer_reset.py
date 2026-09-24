from pathlib import Path


def test_demo_installer_resets_sqlite_on_every_install():
    iss = Path("installer/RND_Demo.iss").read_text(encoding="utf-8")

    assert "[InstallDelete]" in iss
    assert 'Type: files; Name: "{app}\\sistema.db"' in iss
    assert 'Type: files; Name: "{app}\\sistema.db-wal"' in iss
    assert 'Type: files; Name: "{app}\\sistema.db-shm"' in iss
    assert 'Type: files; Name: "{app}\\sistema.db-journal"' in iss


def test_demo_installer_closes_running_app_before_reset():
    iss = Path("installer/RND_Demo.iss").read_text(encoding="utf-8")

    assert "CloseApplications=yes" in iss
    assert "RestartApplications=no" in iss

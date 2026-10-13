# coding=utf-8
"""Regresión del crash del dashboard en producción (hilos Qt + señales).

El ``QThreadPool`` con autoDelete borraba el C++ del runnable al volver
de ``run()`` mientras Python todavía lo referenciaba (isla
señales→lambda→trabajo): el GC lo borraba dos veces y el heap quedaba
corrompido. En producción se veía como
``'_SenalesTrabajo' does not have a signal with the signature
resultado(...)`` seguido de ``wrapped C/C++ object ... has been
deleted``.

El executor ahora es dueño del ciclo de vida (autoDelete False,
discard al entregar, sin teardown dentro de la emisión) y los emits
toleran el apagado. Además ``Acceso.ValidaMenu`` no debe abrir
diálogos fuera del hilo gráfico (las tareas del dashboard corren en
QThreadPool y un QMessageBox ahí corrompe Qt).
"""
import gc
import os
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication
from peewee import SqliteDatabase

_APP = QApplication.instance() or QApplication([])
_TEST_DB = SqliteDatabase(":memory:")


def _bombear_hasta(condicion, timeout_s=20.0):
    """Bombea eventos hasta que condicion() sea True o se acabe el tiempo."""
    from PyQt5.QtCore import QEventLoop

    loop = QEventLoop()
    vencido = {"si": False}

    def _revisar():
        if vencido["si"]:
            return
        try:
            if condicion():
                loop.quit()
        except Exception:
            loop.quit()

    timer = QTimer()
    timer.setInterval(25)
    timer.timeout.connect(_revisar)
    timer.start()
    QTimer.singleShot(int(timeout_s * 1000), loop.quit)
    loop.exec_()
    timer.stop()
    if not condicion():
        vencido["si"] = True
    return condicion()


def test_ejecutor_entrega_todo_y_libera():
    from vistas.dashboard.ejecutor import EjecutorConsultasQt

    recibidos = []
    fallos = []
    ex = EjecutorConsultasQt()
    total = 60
    for i in range(total):
        if i % 5 == 0:
            ex.ejecutar(
                lambda i=i: (_ for _ in ()).throw(ValueError("boom {}".format(i))),
                recibidos.append,
                fallos.append,
            )
        else:
            ex.ejecutar(
                lambda i=i: {"i": i},
                recibidos.append,
                fallos.append,
            )

    entregado = _bombear_hasta(
        lambda: len(recibidos) + len(fallos) == total
    )
    assert entregado, "sólo llegaron {} de {} callbacks".format(
        len(recibidos) + len(fallos), total
    )
    assert len(fallos) == total // 5
    assert all(isinstance(exc, ValueError) for exc in fallos)
    assert sorted(r["i"] for r in recibidos) == [
        i for i in range(total) if i % 5 != 0
    ]

    assert _bombear_hasta(lambda: ex.pendientes() == 0)
    assert ex.pendientes() == 0


def test_ejecutor_tolera_muerte_del_dueno_en_vuelo():
    """Borrar el executor con trabajos en vuelo no debe crashear."""
    from vistas.dashboard.ejecutor import EjecutorConsultasQt

    recibidos = []
    ex = EjecutorConsultasQt()
    for i in range(12):
        ex.ejecutar(lambda i=i: time.sleep(0.02) or i,
                    recibidos.append, lambda exc: None)
    del ex
    gc.collect()
    # Si hay use-after-free, esto muere con access violation en vez de
    # volver: el test falla de forma inconfundible.
    assert _bombear_hasta(
        lambda: len(recibidos) == 12, timeout_s=20.0
    ), "sólo llegaron {} de 12 callbacks".format(len(recibidos))


def test_emitir_seguro_con_senales_muertas():
    import sip

    from vistas.dashboard.ejecutor import _SenalesTrabajo, _emitir_seguro

    senales = _SenalesTrabajo()
    assert _emitir_seguro(senales, "finalizado") is True
    sip.delete(senales)
    assert sip.isdeleted(senales)
    assert _emitir_seguro(senales, "resultado", {"x": 1}) is False
    assert _emitir_seguro(senales, "finalizado") is False


def _base_accesos(bd=None):
    from modelos.Accesos import Acceso
    from modelos.Formula import Formula
    from modelos.ModeloBase import db as db_real
    from modelos.Usuarios import Usuario

    bd = bd if bd is not None else _TEST_DB
    modelos = [Usuario, Formula, Acceso]
    bd.bind(modelos)
    bd.connect()
    bd.create_tables(modelos)
    return modelos, db_real, bd


def test_valida_menu_sin_dialogo_fuera_del_hilo_grafico(monkeypatch, tmp_path):
    """Un QMessageBox en un worker corrompe Qt: fuera del hilo gráfico
    el permiso faltante se niega en silencio."""
    from peewee import SqliteDatabase

    from modelos.Usuarios import Usuario

    # Archivo (no :memory:): cada hilo abre su conexión al mismo banco.
    bd = SqliteDatabase(str(tmp_path / "accesos.db"))
    modelos, db_real, bd = _base_accesos(bd)
    try:
        operario = Usuario.create(
            usuario="oper", nombre="Op", apellido="Erario",
            clave="X", user_level="02", usuario_activo=True,
        )
        monkeypatch.setattr(
            "modelos.Accesos.LeerConf",
            lambda clave=None, sistema=None: operario.usu_id,
        )
        avisos = []
        monkeypatch.setattr(
            "modelos.Accesos.Ventanas.showAlert",
            lambda *args: avisos.append(args),
        )

        from modelos.Accesos import Acceso

        # En el hilo gráfico se preserva el aviso legacy.
        assert Acceso.ValidaMenu(for_valid="INEXISTENTE", usu_id=operario.usu_id) is False
        assert len(avisos) == 1

        # En un worker no debe abrir nada (y no debe romper).
        resultado = {}

        def _en_worker():
            try:
                resultado["valor"] = Acceso.ValidaMenu(
                    for_valid="INEXISTENTE", usu_id=operario.usu_id
                )
            except Exception as exc:  # noqa: BLE001
                resultado["error"] = exc

        hilo = threading.Thread(target=_en_worker)
        hilo.start()
        hilo.join(timeout=15)
        assert not hilo.is_alive()
        assert "error" not in resultado, resultado.get("error")
        assert resultado.get("valor") is False
        assert len(avisos) == 1, "se abrió un diálogo desde el worker"
    finally:
        bd.drop_tables(modelos)
        bd.close()
        db_real.bind(modelos)

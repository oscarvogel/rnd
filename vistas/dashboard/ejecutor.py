# coding=utf-8
"""Ejecucion de consultas del dashboard fuera del hilo grafico."""

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal


class _SenalesTrabajo(QObject):
    resultado = pyqtSignal(object)
    error = pyqtSignal(object)
    finalizado = pyqtSignal()


class _TrabajoConsulta(QRunnable):
    def __init__(self, tarea):
        super().__init__()
        self.tarea = tarea
        self.senales = _SenalesTrabajo()

    def run(self):
        try:
            self.senales.resultado.emit(self.tarea())
        except Exception as exc:  # el limite de seguridad queda en la UI
            self.senales.error.emit(exc)
        finally:
            self.senales.finalizado.emit()


class EjecutorConsultasQt:
    """Despacha trabajo en ``QThreadPool`` y retorna por señales Qt."""

    def __init__(self, pool=None):
        self._pool = pool or QThreadPool.globalInstance()
        self._trabajos = set()

    def ejecutar(self, tarea, al_terminar, al_fallar):
        trabajo = _TrabajoConsulta(tarea)
        self._trabajos.add(trabajo)
        trabajo.senales.resultado.connect(al_terminar)
        trabajo.senales.error.connect(al_fallar)
        trabajo.senales.finalizado.connect(
            lambda: self._trabajos.discard(trabajo)
        )
        self._pool.start(trabajo)


class EjecutorConsultasSincrono:
    """Implementacion determinista para pruebas unitarias."""

    def ejecutar(self, tarea, al_terminar, al_fallar):
        try:
            al_terminar(tarea())
        except Exception as exc:
            al_fallar(exc)


__all__ = ["EjecutorConsultasQt", "EjecutorConsultasSincrono"]

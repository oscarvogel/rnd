# coding=utf-8
"""Ejecucion de consultas del dashboard fuera del hilo grafico."""

import logging

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal


class _SenalesTrabajo(QObject):
    resultado = pyqtSignal(object)
    error = pyqtSignal(object)
    finalizado = pyqtSignal()


def _emitir_seguro(senales, nombre, *args):
    """Emite una señal tolerando el apagado en curso.

    Devuelve False si el dueño ya no existe (cierre de la app con
    trabajos en vuelo): es una carrera esperable, no un bug, y se
    registra en debug en vez de imprimir tracebacks.
    """
    try:
        senal = getattr(senales, nombre)
    except (RuntimeError, AttributeError):
        logging.debug("Trabajo del dashboard sin señales (apagado en curso)")
        return False
    try:
        senal.emit(*args)
    except (RuntimeError, AttributeError):
        logging.debug(
            "Señal %s del dashboard descartada (apagado en curso)", nombre)
        return False
    return True


class _TrabajoConsulta(QRunnable):
    """Runnable con ciclo de vida determinista.

    Con autoDelete (default de Qt) el pool borra el C++ del runnable al
    volver de run() mientras Python todavía lo referencia: use-after-free
    que en producción aparecía como señales "deleted" o firmas
    inexistentes. Por eso el pool NO lo borra; lo retiene el ejecutor
    hasta que ``finalizado`` llega al hilo gráfico y recién ahí se
    liberan las referencias.
    """

    def __init__(self, tarea):
        super().__init__()
        self.setAutoDelete(False)
        self.tarea = tarea
        self.senales = _SenalesTrabajo()

    def run(self):
        senales = self.senales
        try:
            resultado = self.tarea()
        except Exception as exc:  # el limite de seguridad queda en la UI
            _emitir_seguro(senales, "error", exc)
        else:
            _emitir_seguro(senales, "resultado", resultado)
        finally:
            _emitir_seguro(senales, "finalizado")


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
        trabajo.senales.finalizado.connect(lambda: self._liberar(trabajo))
        self._pool.start(trabajo)

    def pendientes(self):
        """Trabajos retenidos aún no entregados (para tests/monitoreo)."""
        return len(self._trabajos)

    def _liberar(self, trabajo):
        # OJO: esto corre DENTRO de la emisión de `finalizado`. No se puede
        # desconectar la señal ni borrar nada acá: mutar la lista de
        # conexiones o el C++ del emisor en pleno unwind es use-after-free
        # (crasheaba al rato con 0xC0000005/0xC0000409). Sólo se suelta la
        # referencia del ejecutor; el ciclo señales→lambda→trabajo→señales
        # lo levanta el GC cíclico en un punto seguro. Y como el pool no
        # borra (autoDelete False), el C++ se destruye exactamente una vez
        # junto con el wrapper Python: ni doble-free de Qt ni borrado
        # prematuro.
        self._trabajos.discard(trabajo)


class EjecutorConsultasSincrono:
    """Implementacion determinista para pruebas unitarias."""

    def ejecutar(self, tarea, al_terminar, al_fallar):
        try:
            al_terminar(tarea())
        except Exception as exc:
            al_fallar(exc)


__all__ = ["EjecutorConsultasQt", "EjecutorConsultasSincrono"]

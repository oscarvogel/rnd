"""Ejecución simple de tareas en segundo plano.

Este módulo ofrece una abstracción liviana basada en `threading` para correr
procesos largos sin bloquear la interfaz. No depende de PyQt, por lo que puede
usarse desde aplicaciones de consola, servicios o pantallas PyQt.
"""

import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple, Dict


@dataclass(frozen=True)
class TaskResult:
    """Resultado de una tarea finalizada."""

    ok: bool
    value: Any = None
    error: Optional[BaseException] = None


class BackgroundTask:
    """Ejecuta una función en un hilo secundario."""

    def __init__(
        self,
        target: Callable,
        *args,
        on_success: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[BaseException], None]] = None,
        on_done: Optional[Callable[[TaskResult], None]] = None,
        daemon: bool = True,
        **kwargs,
    ):
        self.target = target
        self.args: Tuple[Any, ...] = args
        self.kwargs: Dict[str, Any] = kwargs
        self.on_success = on_success
        self.on_error = on_error
        self.on_done = on_done
        self.daemon = daemon
        self.result: Optional[TaskResult] = None
        self.thread: Optional[threading.Thread] = None

    def start(self):
        """Inicia la tarea y devuelve `self`."""
        if self.thread and self.thread.is_alive():
            raise RuntimeError("La tarea ya está en ejecución")
        self.thread = threading.Thread(target=self._run, daemon=self.daemon)
        self.thread.start()
        return self

    def join(self, timeout: Optional[float] = None):
        """Espera la finalización del hilo y devuelve el resultado disponible."""
        if self.thread:
            self.thread.join(timeout)
        return self.result

    def is_running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def _run(self):
        try:
            value = self.target(*self.args, **self.kwargs)
            self.result = TaskResult(ok=True, value=value)
            if self.on_success:
                self.on_success(value)
        except Exception as exc:
            self.result = TaskResult(ok=False, error=exc)
            if self.on_error:
                self.on_error(exc)
        finally:
            if self.on_done and self.result is not None:
                self.on_done(self.result)


def run_in_background(target: Callable, *args, **kwargs) -> BackgroundTask:
    """Crea e inicia una `BackgroundTask`."""
    return BackgroundTask(target, *args, **kwargs).start()


__all__ = ["TaskResult", "BackgroundTask", "run_in_background"]

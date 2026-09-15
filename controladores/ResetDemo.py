# coding=utf-8
"""Controlador del reset de datos de RND DEMO."""

import os
import sys
from pathlib import Path

from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QMessageBox, qApp

from utiles.demo_reset import DemoResetError, resetear_datos_demo


class ResetDemoController:
    """Acción de menú DEMO -> Restablecer datos demo."""

    def __init__(self, parent=None):
        self.parent = parent

    def _reiniciar_demo(self):
        if getattr(sys, "frozen", False):
            programa = sys.executable
            argumentos = []
            directorio = str(Path(sys.executable).resolve().parent)
        else:
            root = Path(__file__).resolve().parent.parent
            # Usar el mismo intérprete con el que se abrió RND. demo.ps1 ya
            # garantiza que sea el .venv propio de O:\rnd.
            programa = sys.executable
            argumentos = [str(root / "demo_main.py")]
            directorio = str(root)

        iniciado = QProcess.startDetached(programa, argumentos, directorio)
        if not iniciado:
            raise DemoResetError(
                "Los datos fueron regenerados, pero no se pudo reiniciar RND DEMO automáticamente."
            )
        qApp.quit()

    def run(self):
        if os.getenv("RND_DEMO_MODE") != "1":
            QMessageBox.critical(
                self.parent,
                "RND DEMO",
                "Esta opción solo está disponible en RND DEMO.",
            )
            return

        respuesta = QMessageBox.warning(
            self.parent,
            "Restablecer datos demo",
            "Se eliminarán todos los cambios realizados durante esta demostración "
            "y se volverán a cargar los datos iniciales.\n\n¿Desea continuar?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        try:
            resetear_datos_demo()
            QMessageBox.information(
                self.parent,
                "RND DEMO",
                "Los datos demo fueron restablecidos. RND DEMO se reiniciará ahora.",
            )
            self._reiniciar_demo()
        except Exception as exc:
            QMessageBox.critical(
                self.parent,
                "No se pudo restablecer RND DEMO",
                str(exc),
            )

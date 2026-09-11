# coding=utf-8
"""Acción de mantenimiento disponible únicamente en RND DEMO."""

import os
import sys
from pathlib import Path

from PyQt5.QtCore import QProcess
from PyQt5.QtWidgets import QApplication, QMessageBox


class ResetDemoController:
    """Restablece la base SQLite demo y reinicia la aplicación."""

    def _es_demo(self):
        return os.getenv("RND_DEMO_MODE") == "1"

    def _confirmar(self):
        box = QMessageBox()
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Restablecer datos demo")
        box.setText(
            "Se eliminarán todos los datos generados durante esta prueba y "
            "RND DEMO volverá al estado inicial."
        )
        box.setInformativeText(
            "Clientes, lugares de entrega, pedidos, equipos, choferes y estados "
            "volverán a generarse desde el seed demo."
        )
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
        box.setDefaultButton(QMessageBox.Cancel)
        boton_si = box.button(QMessageBox.Yes)
        if boton_si is not None:
            boton_si.setText("Restablecer")
        return box.exec_() == QMessageBox.Yes

    def _reiniciar(self):
        if getattr(sys, "frozen", False):
            programa = sys.executable
            argumentos = []
        else:
            programa = sys.executable
            raiz = Path(__file__).resolve().parents[1]
            argumentos = [str(raiz / "demo_main.py")]

        iniciado = QProcess.startDetached(programa, argumentos)
        if isinstance(iniciado, tuple):
            iniciado = bool(iniciado[0])
        return bool(iniciado)

    def run(self):
        if not self._es_demo():
            QMessageBox.critical(
                None,
                "Operación no permitida",
                "Esta opción sólo está disponible dentro de RND DEMO.",
            )
            return

        if not self._confirmar():
            return

        try:
            from demo_seed import reset_demo_database
            reset_demo_database()
        except Exception as exc:
            QMessageBox.critical(
                None,
                "No se pudo restablecer el demo",
                "Ocurrió un error al regenerar los datos:\n\n{}".format(exc),
            )
            return

        QMessageBox.information(
            None,
            "Datos demo restablecidos",
            "Los datos fueron regenerados correctamente. RND DEMO se reiniciará ahora.",
        )

        if self._reiniciar():
            QApplication.quit()
        else:
            QMessageBox.warning(
                None,
                "Reinicio manual requerido",
                "Los datos ya fueron restablecidos, pero RND DEMO no pudo reiniciarse "
                "automáticamente. Cierre y vuelva a abrir la aplicación.",
            )

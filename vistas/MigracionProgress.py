# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class MigracionProgressDialog(QDialog):
    """Modal no cancelable mientras RND prepara la base de datos."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._finalizada = False
        self.setWindowTitle("Actualizando sistema")
        self.setModal(True)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setMinimumWidth(420)

        titulo = QLabel("Actualizando sistema")
        titulo.setObjectName("tituloMigracion")

        detalle = QLabel(
            "Estamos preparando la base de datos para esta versión.\n"
            "Esto puede demorar unos segundos."
        )
        detalle.setWordWrap(True)
        detalle.setObjectName("detalleMigracion")

        self.progreso = QProgressBar()
        self.progreso.setRange(0, 0)
        self.progreso.setTextVisible(False)
        self.progreso.setMinimumHeight(14)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(titulo)
        layout.addWidget(detalle)
        layout.addWidget(self.progreso)

        self.setStyleSheet(
            """
            QDialog {
                background: #f5f7fb;
                border: 1px solid #d9e0ea;
            }
            QLabel#tituloMigracion {
                color: #0d2342;
                font-size: 20px;
                font-weight: 700;
            }
            QLabel#detalleMigracion {
                color: #40516b;
                font-size: 13px;
            }
            QProgressBar {
                border: 1px solid #c8d2e1;
                border-radius: 6px;
                background: #e8edf5;
            }
            QProgressBar::chunk {
                border-radius: 6px;
                background: #0d2342;
            }
            """
        )

    def finalizar(self):
        self._finalizada = True
        self.accept()

    def reject(self):
        if self._finalizada:
            super().reject()

    def closeEvent(self, event):
        if self._finalizada:
            super().closeEvent(event)
        else:
            event.ignore()

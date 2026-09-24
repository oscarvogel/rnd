# coding=utf-8
"""Asistente RND flotante.

La experiencia principal es una burbuja siempre visible sobre las ventanas de
RND. Se expande a un panel compacto, no modal, y vuelve a colapsarse sin perder
la conversación.
"""
from __future__ import annotations

import html
import re
import uuid

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from utiles.asistente_rnd_conocimiento import list_articles, save_article
from utiles.asistente_rnd_servicio import answer_message
from utiles.asistente_rnd_store import list_unresolved


BUBBLE_SIZE = 62
PANEL_WIDTH = 410
PANEL_HEIGHT = 610
SCREEN_MARGIN = 22


def _is_admin():
    try:
        from modelos.Usuarios import Usuario
        from pyqt5libs.pyqt5libs.utiles import LeerConf

        usu_id = int(LeerConf("idUsuario") or 0)
        return bool(usu_id and Usuario().IsAdmin(usu_id))
    except Exception:
        return False


class _AnswerThread(QThread):
    ready = pyqtSignal(dict)

    def __init__(self, question, context, history, parent=None):
        super().__init__(parent)
        self.question = question
        self.context = context
        self.history = list(history or [])

    def run(self):
        self.ready.emit(
            answer_message(
                self.question,
                context=self.context,
                history=self.history,
            )
        )


class KnowledgeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asistente IA - Base de conocimiento")
        self.resize(900, 620)
        self._articles = []

        root = QHBoxLayout(self)
        splitter = QSplitter()
        root.addWidget(splitter)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        self.list_widget = QListWidget()
        self.new_button = QPushButton("Nuevo artículo")
        left_layout.addWidget(
            QLabel("Conocimiento compartido disponible para MiniMax")
        )
        left_layout.addWidget(self.list_widget, 1)
        left_layout.addWidget(self.new_button)
        splitter.addWidget(left)

        right = QWidget()
        form = QVBoxLayout(right)
        self.title_edit = QLineEdit()
        self.context_edit = QLineEdit()
        self.content_edit = QTextEdit()
        self.save_button = QPushButton("Guardar")
        self.save_button.setProperty("role", "primary")
        form.addWidget(QLabel("Título"))
        form.addWidget(self.title_edit)
        form.addWidget(QLabel("Contexto orientativo (no es una regla)"))
        form.addWidget(self.context_edit)
        form.addWidget(QLabel("Conocimiento / procedimiento"))
        form.addWidget(self.content_edit, 1)
        form.addWidget(
            QLabel(
                "MiniMax decide cuándo y cómo usar este contenido. "
                "No se configuran palabras clave ni condiciones."
            )
        )
        form.addWidget(self.save_button)
        splitter.addWidget(right)
        splitter.setSizes([300, 600])

        self.list_widget.currentRowChanged.connect(self._load_selected)
        self.new_button.clicked.connect(self._new_article)
        self.save_button.clicked.connect(self._save)
        self._reload()

    def _reload(self, select_id=None):
        self._articles = list_articles()
        self.list_widget.clear()
        index = 0
        for i, article in enumerate(self._articles):
            self.list_widget.addItem(
                article.get("title") or article.get("id") or "(sin título)"
            )
            if select_id and article.get("id") == select_id:
                index = i
        if self._articles:
            self.list_widget.setCurrentRow(index)

    def _load_selected(self, row):
        if row < 0 or row >= len(self._articles):
            return
        article = self._articles[row]
        self.title_edit.setProperty("article_id", article.get("id"))
        self.title_edit.setText(article.get("title", ""))
        self.context_edit.setText(article.get("context_hint", ""))
        self.content_edit.setPlainText(article.get("content", ""))

    def _new_article(self):
        self.list_widget.clearSelection()
        self.title_edit.setProperty("article_id", None)
        self.title_edit.clear()
        self.context_edit.clear()
        self.content_edit.clear()
        self.title_edit.setFocus()

    def _save(self):
        title = self.title_edit.text().strip()
        content = self.content_edit.toPlainText().strip()
        if not title or not content:
            QMessageBox.warning(
                self,
                "Base de conocimiento",
                "Completá título y contenido.",
            )
            return

        article_id = self.title_edit.property("article_id")
        if not article_id:
            slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
            article_id = "custom_{}_{}".format(
                slug[:32] or "article",
                uuid.uuid4().hex[:6],
            )

        save_article(
            {
                "id": article_id,
                "title": title,
                "context_hint": self.context_edit.text().strip(),
                "content": content,
                "enabled": True,
            }
        )
        self._reload(select_id=article_id)
        QMessageBox.information(
            self,
            "Base de conocimiento",
            "Conocimiento guardado.",
        )


class UnresolvedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asistente IA - Consultas no resueltas")
        self.resize(1040, 520)

        root = QVBoxLayout(self)
        root.addWidget(
            QLabel(
                "MiniMax marcó estas consultas como no resolubles "
                "con el conocimiento actual."
            )
        )

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Usuario", "Pantalla", "Pregunta", "Origen"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)
        self._load()

    def _load(self):
        rows = list_unresolved()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            values = [
                row.get("timestamp", ""),
                row.get("user", ""),
                row.get("context", ""),
                row.get("question", ""),
                row.get("source", ""),
            ]
            for col, value in enumerate(values):
                self.table.setItem(
                    row_index,
                    col,
                    QTableWidgetItem(str(value)),
                )
        self.table.resizeColumnsToContents()


class AsistenteRndFlotante(QWidget):
    """Burbuja flotante que se expande a un panel compacto.

    Es una ventana Tool independiente y always-on-top. Por eso no queda detrás
    de ABMs o formularios maximizados del sistema.
    """

    def __init__(self, context_provider=None):
        super().__init__(None)
        self.context_provider = context_provider
        self.context = "Dashboard principal"
        self.history = []
        self.worker = None
        self.expanded = False
        self._drag_offset = None

        self.setObjectName("asistenteRndFlotante")
        self.setWindowTitle("Asistente RND")
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)

        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._application_state_changed)

        self._build_ui()
        self._set_collapsed(initial=True)

        self._keep_on_top_timer = QTimer(self)
        self._keep_on_top_timer.setInterval(1200)
        self._keep_on_top_timer.timeout.connect(self._keep_visible)
        self._keep_on_top_timer.start()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.bubble_button = QPushButton("IA")
        self.bubble_button.setObjectName("asistenteBubble")
        self.bubble_button.setToolTip("Asistente RND · clic para abrir")
        self.bubble_button.setFixedSize(BUBBLE_SIZE, BUBBLE_SIZE)
        self.bubble_button.clicked.connect(self.expand)
        self.bubble_button.setStyleSheet(
            "QPushButton#asistenteBubble {"
            "background-color:#0A84D8;color:white;border:3px solid white;"
            "border-radius:31px;font-size:15pt;font-weight:700;"
            "}"
            "QPushButton#asistenteBubble:hover {background-color:#0866C8;}"
        )
        root.addWidget(self.bubble_button, 0, Qt.AlignRight | Qt.AlignBottom)

        self.panel = QFrame()
        self.panel.setObjectName("asistentePanel")
        self.panel.setStyleSheet(
            "QFrame#asistentePanel {"
            "background-color:#F8FAFC;border:1px solid #B8DBEC;"
            "border-radius:14px;"
            "}"
        )
        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(9)

        header = QHBoxLayout()
        title = QLabel("Asistente RND")
        title.setStyleSheet(
            "font-size:13pt;font-weight:700;color:#083B6D;"
        )
        self.context_label = QLabel("")
        self.context_label.setStyleSheet("color:#64748B;font-size:8pt;")
        self.minimize_button = QPushButton("—")
        self.minimize_button.setFixedSize(30, 28)
        self.minimize_button.setToolTip("Minimizar a burbuja")
        self.minimize_button.clicked.connect(self.collapse)

        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.context_label)
        header.addWidget(self.minimize_button)
        panel_layout.addLayout(header)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        self.chat.setStyleSheet(
            "QTextBrowser {background:white;border:1px solid #D7EAF3;"
            "border-radius:10px;padding:5px;}"
        )
        panel_layout.addWidget(self.chat, 1)

        hint = QLabel(
            "Podés preguntar, por ejemplo: “¿qué hago ahora?” o "
            "“¿por qué no me deja continuar?”"
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#64748B;font-size:8pt;")
        panel_layout.addWidget(hint)

        send_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Preguntá con tus palabras…")
        self.send_button = QPushButton("Enviar")
        self.send_button.setProperty("role", "primary")
        self.send_button.setFixedWidth(72)
        send_row.addWidget(self.input, 1)
        send_row.addWidget(self.send_button)
        panel_layout.addLayout(send_row)

        footer = QHBoxLayout()
        if _is_admin():
            base_button = QPushButton("Conocimiento")
            audit_button = QPushButton("No resueltas")
            base_button.clicked.connect(self.open_knowledge)
            audit_button.clicked.connect(self.open_unresolved)
            footer.addWidget(base_button)
            footer.addWidget(audit_button)
        footer.addStretch(1)
        footer.addWidget(QLabel("F1 abre/minimiza"))
        panel_layout.addLayout(footer)

        self.send_button.clicked.connect(self.send)
        self.input.returnPressed.connect(self.send)

        root.addWidget(self.panel)
        self.panel.hide()

        self._append(
            "assistant",
            "Preguntame con tus palabras sobre el funcionamiento de RND. "
            "MiniMax interpreta la consulta usando la pantalla en la que estás "
            "trabajando y la base de conocimiento del sistema.",
        )

    def _current_context(self):
        if callable(self.context_provider):
            try:
                value = str(self.context_provider() or "").strip()
                if value:
                    self.context = value
            except Exception:
                pass
        return self.context

    def _available_geometry(self):
        app = QApplication.instance()
        active = app.activeWindow() if app else None
        screen = active.screen() if active is not None else None
        if screen is None and app is not None:
            screen = app.primaryScreen()
        return screen.availableGeometry() if screen is not None else None

    def _dock_bottom_right(self):
        geometry = self._available_geometry()
        if geometry is None:
            return
        self.move(
            geometry.right() - self.width() - SCREEN_MARGIN + 1,
            geometry.bottom() - self.height() - SCREEN_MARGIN + 1,
        )

    def _set_collapsed(self, initial=False):
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.expanded = False
        self.panel.hide()
        self.bubble_button.show()
        self.setFixedSize(BUBBLE_SIZE, BUBBLE_SIZE)
        self._dock_bottom_right()
        if not initial:
            self.show()
            self.raise_()

    def expand(self):
        self.setAttribute(Qt.WA_ShowWithoutActivating, False)
        self.context = self._current_context()
        short_context = self.context.split("|", 1)[-1].strip()
        self.context_label.setText(short_context[:34])

        self.expanded = True
        self.bubble_button.hide()
        self.panel.show()

        geometry = self._available_geometry()
        height = PANEL_HEIGHT
        if geometry is not None:
            height = min(PANEL_HEIGHT, max(430, geometry.height() - 44))
        self.setFixedSize(PANEL_WIDTH, height)
        self._dock_bottom_right()
        self.show()
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def collapse(self):
        self._set_collapsed()

    def toggle(self):
        if self.expanded:
            self.collapse()
        else:
            self.expand()

    def show_bubble(self):
        self._set_collapsed()
        self.show()
        self.raise_()

    def _keep_visible(self):
        app = QApplication.instance()
        if app is not None and app.applicationState() != Qt.ApplicationActive:
            return
        if not self.isVisible():
            self.show()
        self.raise_()

    def _application_state_changed(self, state):
        if state == Qt.ApplicationActive:
            self.show()
            self.raise_()
        else:
            self.hide()

    def ask(self, text):
        self.input.setText(text)
        self.send()

    def send(self):
        question = self.input.text().strip()
        if not question or self.worker is not None:
            return

        self.context = self._current_context()
        short_context = self.context.split("|", 1)[-1].strip()
        self.context_label.setText(short_context[:34])

        self.input.clear()
        self._append("user", question)
        self.history.append({"role": "user", "content": question})
        self.input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.send_button.setText("…")

        self.worker = _AnswerThread(
            question,
            self.context,
            self.history[:-1],
            self,
        )
        self.worker.ready.connect(self._answer_ready)
        self.worker.finished.connect(self._worker_finished)
        self.worker.start()

    def _answer_ready(self, result):
        text = (result or {}).get("content") or "No pude generar una respuesta."
        self._append("assistant", text)
        self.history.append({"role": "assistant", "content": text})

    def _worker_finished(self):
        if self.worker is not None:
            self.worker.deleteLater()
        self.worker = None
        self.input.setEnabled(True)
        self.send_button.setEnabled(True)
        self.send_button.setText("Enviar")
        self.input.setFocus()

    def _append(self, role, text):
        label = "Vos" if role == "user" else "Asistente RND"
        bg = "#EAF6FC" if role == "user" else "#FFFFFF"
        self.chat.append(
            '<div style="margin:6px 0;padding:8px;border:1px solid #D7EAF3;'
            'border-radius:8px;background:{};"><b>{}</b><br>{}</div>'.format(
                bg,
                html.escape(label),
                html.escape(text).replace("\n", "<br>"),
            )
        )
        self.chat.verticalScrollBar().setValue(
            self.chat.verticalScrollBar().maximum()
        )

    def open_knowledge(self):
        if _is_admin():
            KnowledgeDialog(self).exec_()

    def open_unresolved(self):
        if _is_admin():
            UnresolvedDialog(self).exec_()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        super().mouseReleaseEvent(event)

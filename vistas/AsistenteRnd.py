# coding=utf-8
"""Interfaz PyQt5 del Asistente RND."""
from __future__ import annotations

import html
import re
import uuid

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox,
    QPushButton, QSplitter, QTableWidget, QTableWidgetItem, QTextBrowser,
    QTextEdit, QVBoxLayout, QWidget,
)

from utiles.asistente_rnd_conocimiento import list_articles, save_article, suggestions
from utiles.asistente_rnd_servicio import answer_message
from utiles.asistente_rnd_store import list_unresolved


class _AnswerThread(QThread):
    ready = pyqtSignal(dict)

    def __init__(self, question, context, history, parent=None):
        super().__init__(parent)
        self.question = question
        self.context = context
        self.history = list(history or [])

    def run(self):
        self.ready.emit(answer_message(
            self.question,
            context=self.context,
            history=self.history,
        ))


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
        left_layout.addWidget(QLabel("Conocimiento disponible para MiniMax"))
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
        form.addWidget(QLabel(
            "MiniMax decide cuándo y cómo usar este contenido. "
            "No se configuran palabras clave ni condiciones."
        ))
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
                self, "Base de conocimiento", "Completá título y contenido."
            )
            return

        article_id = self.title_edit.property("article_id")
        if not article_id:
            slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
            article_id = "custom_{}_{}".format(
                slug[:32] or "article", uuid.uuid4().hex[:6]
            )

        article = {
            "id": article_id,
            "title": title,
            "context_hint": self.context_edit.text().strip(),
            "content": content,
            "enabled": True,
        }
        save_article(article)
        self._reload(select_id=article_id)
        QMessageBox.information(
            self, "Base de conocimiento", "Conocimiento guardado."
        )


class UnresolvedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asistente IA - Consultas no resueltas")
        self.resize(920, 500)
        root = QVBoxLayout(self)
        root.addWidget(QLabel(
            "MiniMax marcó estas consultas como no resolubles con el conocimiento actual."
        ))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Fecha", "Pantalla", "Pregunta", "Origen"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)
        self._load()

    def _load(self):
        rows = list_unresolved()
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(reversed(rows)):
            values = [
                row.get("timestamp", ""),
                row.get("context", ""),
                row.get("question", ""),
                row.get("source", ""),
            ]
            for col, value in enumerate(values):
                self.table.setItem(
                    row_index, col, QTableWidgetItem(str(value))
                )
        self.table.resizeColumnsToContents()


class AsistenteRndDialog(QDialog):
    def __init__(self, context="Dashboard principal", parent=None):
        super().__init__(parent)
        self.context = context or "Dashboard principal"
        self.history = []
        self.worker = None
        self.setWindowTitle("Asistente RND")
        self.resize(780, 660)
        self.setModal(False)

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Asistente RND · IA-first")
        title.setStyleSheet("font-size: 14pt; font-weight: 600;")
        self.context_label = QLabel("Contexto: {}".format(self.context))
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(self.context_label)
        root.addLayout(header)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(False)
        root.addWidget(self.chat, 1)

        suggestions_layout = QHBoxLayout()
        for suggestion in suggestions():
            button = QPushButton(suggestion)
            button.setProperty("role", "secondary")
            button.clicked.connect(
                lambda _checked=False, text=suggestion: self.ask(text)
            )
            suggestions_layout.addWidget(button)
        root.addLayout(suggestions_layout)

        send_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "Preguntá con tus palabras cómo hacer algo en RND..."
        )
        self.send_button = QPushButton("Enviar")
        self.send_button.setProperty("role", "primary")
        send_row.addWidget(self.input, 1)
        send_row.addWidget(self.send_button)
        root.addLayout(send_row)

        footer = QHBoxLayout()
        self.knowledge_button = QPushButton("Base de conocimiento")
        self.unresolved_button = QPushButton("Consultas no resueltas")
        footer.addWidget(self.knowledge_button)
        footer.addWidget(self.unresolved_button)
        footer.addStretch(1)
        footer.addWidget(QLabel("F1 abre el asistente"))
        root.addLayout(footer)

        self.send_button.clicked.connect(self.send)
        self.input.returnPressed.connect(self.send)
        self.knowledge_button.clicked.connect(self.open_knowledge)
        self.unresolved_button.clicked.connect(self.open_unresolved)

        self._append(
            "assistant",
            "Preguntame con tus palabras. MiniMax interpreta la consulta usando "
            "la pantalla actual, el historial y la base de conocimiento de RND. "
            "No modifico datos: te explico el procedimiento.",
        )

    def set_context(self, context):
        self.context = context or "Dashboard principal"
        self.context_label.setText("Contexto: {}".format(self.context))

    def _append(self, role, text):
        label = "Vos" if role == "user" else "Asistente RND"
        bg = "#EAF6FC" if role == "user" else "#FFFFFF"
        self.chat.append(
            '<div style="margin:8px 0;padding:10px;border:1px solid #D7EAF3;'
            'border-radius:8px;background:{};"><b>{}</b><br>{}</div>'.format(
                bg,
                html.escape(label),
                html.escape(text).replace("\n", "<br>"),
            )
        )
        self.chat.verticalScrollBar().setValue(
            self.chat.verticalScrollBar().maximum()
        )

    def ask(self, text):
        self.input.setText(text)
        self.send()

    def send(self):
        question = self.input.text().strip()
        if not question or self.worker is not None:
            return

        self.input.clear()
        self._append("user", question)
        self.history.append({"role": "user", "content": question})
        self.input.setEnabled(False)
        self.send_button.setEnabled(False)
        self.send_button.setText("Consultando MiniMax…")

        self.worker = _AnswerThread(
            question, self.context, self.history[:-1], self
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

    def open_knowledge(self):
        KnowledgeDialog(self).exec_()

    def open_unresolved(self):
        UnresolvedDialog(self).exec_()

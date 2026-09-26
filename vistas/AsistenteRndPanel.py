# coding=utf-8
"""Panel compacto del Asistente RND.

La UI mantiene el nucleo IA-first del spike: no contiene reglas de negocio ni
routers de intenciones. Solo administra conversacion, contexto de pantalla y la
llamada asincronica al servicio ya validado.
"""
from __future__ import annotations

import ctypes
import html
import re
import sys

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QShortcut,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QColor

from utiles.asistente_rnd_spike import preguntar


PANEL_WIDTH = 420
PANEL_MAX_HEIGHT = 660
PANEL_MARGIN = 18


class _AssistantThread(QThread):
    respuesta = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, pregunta, historial, contexto, parent=None):
        super().__init__(parent)
        self.pregunta = pregunta
        self.historial = list(historial or [])
        self.contexto = contexto or ""

    def run(self):
        try:
            texto = preguntar(
                self.pregunta,
                historial=self.historial,
                contexto=self.contexto,
            )
        except Exception as exc:
            self.error.emit(str(exc))
            return
        self.respuesta.emit(texto)


class AsistenteRndPanel(QWidget):
    """Panel lateral rapido: F1/boton abre, F1/X/Esc oculta."""

    def __init__(self, anchor=None, context_provider=None):
        super().__init__(None)
        self.anchor = anchor
        self.context_provider = context_provider
        self.history = []
        self._thread = None
        self._wanted_visible = False
        self._contexto_actual = ""

        self.setObjectName("asistenteRndWindow")
        self.setWindowTitle("Asistente RND")
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(PANEL_WIDTH)
        self.setMaximumWidth(PANEL_WIDTH)

        self._build_ui()
        self._apply_style()

        self._escape = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self._escape.setContext(Qt.WidgetWithChildrenShortcut)
        self._escape.activated.connect(self.hide_panel)

        app = QApplication.instance()
        if app is not None:
            app.applicationStateChanged.connect(self._on_application_state)

        # Algunos ABM legacy son ventanas nativas top-level. En Windows,
        # Qt.WindowStaysOnTopHint/raise_() no siempre alcanza para conservar
        # el panel delante de ellas. Reafirmamos HWND_TOPMOST sin activar el
        # asistente, de modo que el operador sigue trabajando en el ABM.
        self._keep_on_top_timer = QTimer(self)
        self._keep_on_top_timer.setInterval(300)
        self._keep_on_top_timer.timeout.connect(self._keep_visible_above_rnd)
        self._keep_on_top_timer.start()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(0)

        self.card = QFrame()
        self.card.setObjectName("asistenteCard")
        self.card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        outer.addWidget(self.card)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(8, 59, 109, 90))
        self.card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)

        titles = QVBoxLayout()
        titles.setSpacing(1)

        title = QLabel("Asistente RND")
        title.setObjectName("asistenteTitulo")
        titles.addWidget(title)

        subtitle = QLabel("Ayuda del sistema · MiniMax")
        subtitle.setObjectName("asistenteSubtitulo")
        titles.addWidget(subtitle)

        top.addLayout(titles, stretch=1)

        self.btn_close = QPushButton("×")
        self.btn_close.setObjectName("asistenteCerrar")
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setToolTip("Cerrar panel · F1 o Esc")
        self.btn_close.clicked.connect(self.hide_panel)
        top.addWidget(self.btn_close)

        layout.addLayout(top)

        self.lbl_context = QLabel("")
        self.lbl_context.setObjectName("asistenteContexto")
        self.lbl_context.setWordWrap(True)
        layout.addWidget(self.lbl_context)

        self.chat = QTextBrowser()
        self.chat.setObjectName("asistenteConversacion")
        self.chat.setOpenExternalLinks(False)
        self.chat.setReadOnly(True)
        layout.addWidget(self.chat, stretch=1)

        self._append_message(
            "assistant",
            "Hola. Preguntame cómo usar RND o qué revisar si algo no aparece como esperás.",
            store=False,
        )

        self.status = QLabel("Listo")
        self.status.setObjectName("asistenteEstado")
        layout.addWidget(self.status)

        compose = QHBoxLayout()
        compose.setSpacing(8)

        self.input = QLineEdit()
        self.input.setObjectName("asistenteEntrada")
        self.input.setPlaceholderText("Escribí tu consulta sobre RND…")
        self.input.returnPressed.connect(self.send_current)
        compose.addWidget(self.input, stretch=1)

        self.btn_send = QPushButton("Enviar")
        self.btn_send.setObjectName("asistenteEnviar")
        self.btn_send.setCursor(Qt.PointingHandCursor)
        self.btn_send.clicked.connect(self.send_current)
        compose.addWidget(self.btn_send)

        layout.addLayout(compose)

        hint = QLabel("F1 abre/cierra · Esc cierra")
        hint.setObjectName("asistenteAtajo")
        layout.addWidget(hint)

    def _apply_style(self):
        self.setStyleSheet(
            """
            QWidget#asistenteRndWindow {
                background: transparent;
            }
            QFrame#asistenteCard {
                background-color: #F8FBFE;
                border: 1px solid #9ED9F1;
                border-radius: 16px;
            }
            QLabel#asistenteTitulo {
                color: #083B6D;
                font-size: 14pt;
                font-weight: 700;
                background: transparent;
            }
            QLabel#asistenteSubtitulo {
                color: #64748B;
                font-size: 9pt;
                background: transparent;
            }
            QLabel#asistenteContexto {
                color: #0B5D97;
                background-color: #E9F7FD;
                border: 1px solid #B9E6F8;
                border-radius: 7px;
                padding: 7px 9px;
                font-size: 9pt;
            }
            QTextBrowser#asistenteConversacion {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #D7EAF3;
                border-radius: 10px;
                padding: 8px;
                font-size: 10pt;
            }
            QLabel#asistenteEstado,
            QLabel#asistenteAtajo {
                color: #64748B;
                background: transparent;
                font-size: 8.5pt;
            }
            QPushButton#asistenteCerrar {
                background-color: transparent;
                color: #475569;
                border: none;
                border-radius: 14px;
                min-width: 30px;
                max-width: 30px;
                min-height: 30px;
                max-height: 30px;
                font-size: 17pt;
                font-weight: 600;
                padding: 0;
            }
            QPushButton#asistenteCerrar:hover {
                background-color: #E2E8F0;
                color: #0F172A;
            }
            QLineEdit#asistenteEntrada {
                background-color: #FFFFFF;
                color: #0F172A;
                border: 1px solid #B8DBEC;
                border-radius: 9px;
                padding: 8px 10px;
                min-height: 30px;
            }
            QLineEdit#asistenteEntrada:focus {
                border: 2px solid #0A84D8;
                padding: 7px 9px;
            }
            QPushButton#asistenteEnviar {
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #19B9E7,
                    stop:1 #0866C8
                );
                color: #FFFFFF;
                border: 1px solid #0A84D8;
                border-radius: 9px;
                padding: 8px 14px;
                min-height: 30px;
                font-weight: 600;
            }
            QPushButton#asistenteEnviar:hover {
                border-color: #F5C518;
            }
            QPushButton#asistenteEnviar:disabled {
                background-color: #94A3B8;
                border-color: #94A3B8;
            }
            """
        )

    @staticmethod
    def _message_html(role, text):
        escaped = html.escape(str(text or ""))
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", escaped)
        lines = escaped.splitlines() or [""]
        formatted = []
        for line in lines:
            stripped = line.strip()
            if stripped == "---":
                formatted.append("<hr>")
                continue
            if stripped.startswith("#"):
                stripped = stripped.lstrip("#").strip()
                formatted.append("<b>{}</b>".format(stripped))
                continue
            if stripped.startswith("- "):
                stripped = "• " + stripped[2:]
            formatted.append(stripped or "&nbsp;")

        body = "<br>".join(formatted)
        if role == "user":
            return (
                "<div style='margin:8px 0 8px 44px;padding:9px 11px;"
                "background:#E9F7FD;border:1px solid #B9E6F8;"
                "border-radius:10px;color:#083B6D;'>"
                "<b>Vos</b><br>{}</div>"
            ).format(body)

        return (
            "<div style='margin:8px 32px 8px 0;padding:9px 11px;"
            "background:#F8FAFC;border:1px solid #E2E8F0;"
            "border-radius:10px;color:#0F172A;'>"
            "<b>Asistente</b><br>{}</div>"
        ).format(body)

    def _append_message(self, role, text, *, store=True):
        self.chat.append(self._message_html(role, text))
        if store:
            self.history.append({"role": role, "content": str(text or "")})
        bar = self.chat.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _read_context(self):
        if callable(self.context_provider):
            try:
                return str(self.context_provider() or "").strip()
            except Exception:
                return ""
        return ""

    def _refresh_context(self):
        self._contexto_actual = self._read_context()
        if self._contexto_actual:
            self.lbl_context.setText("Contexto: {}".format(self._contexto_actual))
            self.lbl_context.show()
        else:
            self.lbl_context.hide()

    def send_current(self):
        if self._thread is not None:
            return

        question = self.input.text().strip()
        if not question:
            return

        self._refresh_context()
        previous_history = list(self.history)
        self._append_message("user", question)
        self.input.clear()
        self._set_busy(True)

        self._thread = _AssistantThread(
            question,
            previous_history,
            self._contexto_actual,
            parent=self,
        )
        self._thread.respuesta.connect(self._on_answer)
        self._thread.error.connect(self._on_error)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _set_busy(self, busy):
        self.input.setEnabled(not busy)
        self.btn_send.setEnabled(not busy)
        self.status.setText(
            "Consultando MiniMax…" if busy else "Listo"
        )

    def _on_answer(self, text):
        self._append_message("assistant", text)
        self._set_busy(False)
        self.input.setFocus()

    def _on_error(self, detail):
        self._append_message(
            "assistant",
            "El asistente no está disponible en este momento. "
            "Podés seguir usando RND normalmente y volver a intentar.",
        )
        self.status.setText("Consulta no disponible")
        self.input.setEnabled(True)
        self.btn_send.setEnabled(True)
        self.input.setFocus()

    def _on_thread_finished(self):
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.deleteLater()

    def _available_geometry(self):
        active = QApplication.activeWindow()
        if active is self:
            active = None

        screen = None
        if active is not None and hasattr(active, "screen"):
            screen = active.screen()
        if screen is None and self.anchor is not None and hasattr(self.anchor, "screen"):
            screen = self.anchor.screen()
        if screen is None:
            screen = QApplication.primaryScreen()
        return screen.availableGeometry(), active

    def _dock_right(self):
        available, _active = self._available_geometry()
        height = min(PANEL_MAX_HEIGHT, max(420, available.height() - PANEL_MARGIN * 2))
        self.resize(PANEL_WIDTH, height)

        # Posicion estable: borde derecho de la pantalla de RND. No depende del
        # tamaño/posición del ABM activo, así abrir una ventana centrada no mueve
        # ni tapa el asistente.
        x = available.right() - self.width() - PANEL_MARGIN + 1
        y = available.top() + PANEL_MARGIN
        self.move(x, y)

    def _set_native_topmost(self, enabled):
        """Fuerza el orden Z nativo en Windows sin robar foco.

        Los ABM legacy de RND son ventanas top-level independientes. En Windows
        una Qt.Tool sin owner puede quedar detrás de ellas aunque tenga
        WindowStaysOnTopHint. SetWindowPos resuelve ese caso a nivel HWND.
        """
        if sys.platform != "win32":
            return False

        try:
            user32 = ctypes.windll.user32
            hwnd = ctypes.c_void_p(int(self.winId()))
            insert_after = ctypes.c_void_p(
                (2 ** (ctypes.sizeof(ctypes.c_void_p) * 8) - 1)
                if enabled else
                (2 ** (ctypes.sizeof(ctypes.c_void_p) * 8) - 2)
            )
            # SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW
            flags = 0x0001 | 0x0002 | 0x0010 | 0x0040
            result = user32.SetWindowPos(
                hwnd,
                insert_after,
                0,
                0,
                0,
                0,
                flags,
            )
            return bool(result)
        except Exception:
            # Fallback seguro: si la API nativa no está disponible, Qt sigue
            # usando WindowStaysOnTopHint y raise_().
            return False

    def _keep_visible_above_rnd(self):
        if not self._wanted_visible:
            return

        app = QApplication.instance()
        if app is None or app.applicationState() != Qt.ApplicationActive:
            return

        if not self.isVisible():
            self.show()

        if not self._set_native_topmost(True):
            self.raise_()

    def show_panel(self):
        self._wanted_visible = True
        self._refresh_context()
        self._dock_right()
        self.show()
        self._set_native_topmost(True)
        self.raise_()
        self.activateWindow()
        self.input.setFocus()

    def hide_panel(self):
        self._wanted_visible = False
        self._set_native_topmost(False)
        self.hide()

    def toggle(self):
        if self.isVisible() and self._wanted_visible:
            self.hide_panel()
        else:
            self.show_panel()

    def closeEvent(self, event):
        self.hide_panel()
        event.ignore()

    def _on_application_state(self, state):
        if state != Qt.ApplicationActive:
            self._set_native_topmost(False)
            if self.isVisible():
                self.hide()
            return
        if self._wanted_visible:
            self._dock_right()
            self.show()
            self._set_native_topmost(True)
            self.raise_()

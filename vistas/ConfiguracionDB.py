# coding=utf-8
"""Dialog de configuracion de la base de datos.

Se muestra cuando RND no puede conectar (auth fail, SSL, host inalcanzable,
etc) o cuando es el primer arranque y no hay credenciales persistidas.
El usuario puede corregir los valores y aceptar; el sistema los persiste
y reintenta la conexion.
"""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyqt5libs.pyqt5libs.EntradaTexto import Password
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta


class ConfiguracionDBView(QDialog):
    """Dialog modal para pedir/confirmar credenciales de la DB."""

    def __init__(self, config_actual=None, mensaje=None, parent=None):
        """
        Args:
            config_actual: dict con 'host', 'port', 'user', 'password',
                'basedatos'. Si viene None, se cargan defaults vacios.
            mensaje: texto opcional que se muestra arriba del form
                (ej. "RND no pudo conectar. Verifica los datos.").
            parent: widget padre (para que el dialog sea modal sobre la app).
        """
        super().__init__(parent)
        self._config_actual = config_actual or {}
        self._resultado = None
        self._setup_ui(mensaje)
        self._cargar_config()

    def _setup_ui(self, mensaje):
        self.setWindowTitle("Configuracion de la base de datos")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)

        # Mensaje opcional arriba
        if mensaje:
            label_mensaje = QLabel(mensaje)
            label_mensaje.setWordWrap(True)
            label_mensaje.setStyleSheet("color: #b00; font-weight: bold;")
            layout.addWidget(label_mensaje)

        # Instrucciones
        label_info = Etiqueta(
            texto=(
                "Ingresa los datos de conexion. Si no los sabes, "
                "consulta con el administrador del sistema."
            )
        )
        label_info.setWordWrap(True)
        layout.addWidget(label_info)

        # Form
        form = QFormLayout()
        self.txt_host = QLineEdit()
        self.txt_host.setPlaceholderText("ej: vps-XXXXX.dattaweb.com")
        form.addRow("Servidor:", self.txt_host)

        self.spn_port = QSpinBox()
        self.spn_port.setRange(1, 65535)
        self.spn_port.setValue(3306)
        form.addRow("Puerto:", self.spn_port)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("ej: rnd_app")
        form.addRow("Usuario:", self.txt_user)

        self.txt_password = Password()
        self.txt_password.setPlaceholderText("clave de la base de datos")
        self.txt_password.setEchoMode(QLineEdit.Password)
        form.addRow("Contrasena:", self.txt_password)

        self.txt_basedatos = QLineEdit()
        self.txt_basedatos.setPlaceholderText("ej: rnd")
        form.addRow("Base de datos:", self.txt_basedatos)

        layout.addLayout(form)

        # Checkbox "recordar"
        self.chk_recordar = QCheckBox("Recordar en este equipo")
        self.chk_recordar.setChecked(True)
        layout.addWidget(self.chk_recordar)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_aceptar)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Ok).setText("Aceptar")
        buttons.button(QDialogButtonBox.Cancel).setText("Cancelar")
        layout.addWidget(buttons)

    def _cargar_config(self):
        """Pre-llena el form con los valores actuales."""
        cfg = self._config_actual
        self.txt_host.setText(str(cfg.get("host", "")))
        puerto = cfg.get("port") or 3306
        try:
            self.spn_port.setValue(int(puerto))
        except (TypeError, ValueError):
            self.spn_port.setValue(3306)
        self.txt_user.setText(str(cfg.get("user", "")))
        # Password: si hay una persistida, mostrarla enmascarada. Si no, vacia.
        password = cfg.get("password", "")
        if password:
            self.txt_password.setText(password)
        self.txt_basedatos.setText(str(cfg.get("basedatos", "")))

    def _on_aceptar(self):
        host = self.txt_host.text().strip()
        port = self.spn_port.value()
        user = self.txt_user.text().strip()
        password = self.txt_password.text()
        basedatos = self.txt_basedatos.text().strip()

        # Validacion basica
        if not host:
            QMessageBox.warning(self, "Falta el servidor", "Ingresa el servidor.")
            return
        if not user:
            QMessageBox.warning(self, "Falta el usuario", "Ingresa el usuario.")
            return
        if not password:
            QMessageBox.warning(self, "Falta la contrasena", "Ingresa la contrasena.")
            return
        if not basedatos:
            QMessageBox.warning(self, "Falta la base de datos", "Ingresa la base de datos.")
            return

        self._resultado = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "basedatos": basedatos,
            "recordar": self.chk_recordar.isChecked(),
        }
        self.accept()

    def get_config(self):
        """Devuelve la config nueva (dict) o None si el usuario cancelo."""
        return self._resultado

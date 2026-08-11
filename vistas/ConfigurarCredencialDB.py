from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from rnd_credentials import (
    CredentialError,
    MySQLSettings,
    save_machine_password,
    validate_mysql_connection,
)


class CredentialDialog(QDialog):
    """Configura la conexión MySQL compartida por los usuarios de la PC."""

    def __init__(
        self,
        settings: MySQLSettings,
        validator=validate_mysql_connection,
        saver=save_machine_password,
        parent=None,
    ):
        super().__init__(parent)
        self.settings = settings
        self._validator = validator
        self._saver = saver
        self._validated_configuration = None

        self.setWindowTitle("Configurar conexión MySQL de RND")
        self.setModal(True)
        self.setMinimumWidth(440)

        explanation = QLabel(
            "Configure la conexión compartida de RND. El servidor, puerto, "
            "base y usuario se guardarán en sistema.ini; la contraseña se "
            "guardará cifrada para esta computadora."
        )
        explanation.setWordWrap(True)

        self.server_edit = QLineEdit(settings.host)
        self.port_edit = QLineEdit(str(settings.port))
        self.database_edit = QLineEdit(settings.database)
        self.user_edit = QLineEdit(settings.user)
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText("Contraseña MySQL")
        for edit in (
            self.server_edit,
            self.port_edit,
            self.database_edit,
            self.user_edit,
            self.password_edit,
        ):
            edit.textChanged.connect(self._configuration_changed)

        form = QFormLayout()
        form.addRow("Servidor:", self.server_edit)
        form.addRow("Puerto:", self.port_edit)
        form.addRow("Base de datos:", self.database_edit)
        form.addRow("Usuario:", self.user_edit)
        form.addRow("Contraseña:", self.password_edit)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.test_button = QPushButton("Probar conexión")
        self.test_button.clicked.connect(self.test_connection)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_button = buttons.button(QDialogButtonBox.Save)
        self.save_button.setText("Guardar y continuar")
        self.save_button.setEnabled(False)
        buttons.accepted.connect(self.save_credential)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(explanation)
        layout.addLayout(form)
        layout.addWidget(self.test_button)
        layout.addWidget(self.status_label)
        layout.addWidget(buttons)

    def _configuration_changed(self):
        self._validated_configuration = None
        self.save_button.setEnabled(False)
        self.status_label.setStyleSheet("")
        self.status_label.clear()

    def _candidate_settings(self):
        host = self.server_edit.text().strip()
        database = self.database_edit.text().strip()
        user = self.user_edit.text().strip()
        try:
            port = int(self.port_edit.text().strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("El puerto MySQL debe ser un número entre 1 y 65535.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("El puerto MySQL debe ser un número entre 1 y 65535.")
        if not host or not database or not user:
            raise ValueError("Complete servidor, base de datos y usuario.")
        return MySQLSettings(host, port, database, user)

    def test_connection(self):
        password = self.password_edit.text()
        if not password:
            self.status_label.setText("Ingrese la contraseña para probar la conexión.")
            return
        try:
            settings = self._candidate_settings()
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return

        self.test_button.setEnabled(False)
        try:
            self._validator(settings, password)
        except CredentialError as exc:
            self._validated_configuration = None
            self.save_button.setEnabled(False)
            self.status_label.setText(str(exc))
        except Exception:
            self._validated_configuration = None
            self.save_button.setEnabled(False)
            self.status_label.setText("No se pudo probar la conexión MySQL.")
        else:
            self._validated_configuration = (settings, password)
            self.save_button.setEnabled(True)
            self.status_label.setText("Conexión verificada correctamente.")
            self.status_label.setStyleSheet("color: #176b2c;")
        finally:
            self.test_button.setEnabled(True)

    def save_credential(self):
        password = self.password_edit.text()
        try:
            settings = self._candidate_settings()
        except ValueError as exc:
            self.save_button.setEnabled(False)
            self.status_label.setText(str(exc))
            return
        if not password or (settings, password) != self._validated_configuration:
            self.save_button.setEnabled(False)
            self.status_label.setText("Vuelva a probar la contraseña antes de guardarla.")
            return

        try:
            self._saver(settings, password)
        except CredentialError as exc:
            self.status_label.setStyleSheet("color: #8b1a1a;")
            self.status_label.setText(str(exc))
            return

        self.password_edit.clear()
        super().accept()

    def reject(self):
        self.password_edit.clear()
        super().reject()

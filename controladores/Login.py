# coding=utf-8
from PyQt5.QtCore import Qt


from modelos.ModeloBase import reconnect_if_needed
from modelos.Usuarios import Usuario
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import GrabaConf, inicializar_y_capturar_excepciones
from vistas.Login import LoginView


class LoginController(ControladorBase):

    lRetVal = False

    def __init__(self):
        super().__init__()
        self.view = LoginView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(lambda: self.CerrarFormulario(False))
        self.view.btnIngresar.clicked.connect(self.ValidaIngreso)
        self.view.textPass.keyPressed.connect(self.onKeyPressedTextPass)
        # self.view.btnCerrar.clicked.connect(self.view.Cerrar)

    def CerrarFormulario(self, lIngresa):
        self.lRetVal = lIngresa
        self.view._want_to_close = True
        self.view.Cerrar()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def ValidaIngreso(self, *args, **kwargs):
        if Usuario().ValidaPassword(self.view.cboUsuario.text(), self.view.textPass.text()):
            self.view._want_to_close = True
            self.lRetVal = True
            GrabaConf(valor=self.view.cboUsuario.text(), clave="idUsuario")

            #print(self.comboBox.currentData())
            self.cUsuario = self.view.cboUsuario.currentText()
            self.view.Cerrar()
        else:
            Ventanas.showAlert("Sistema", "Clave no valida para el usuario")
            self.view.textPass.setText("")
            self.view.textPass.setFocus()

    def onKeyPressedTextPass(self, key):
        if key in [Qt.Key_Return, Qt.EnterKeyReturn, Qt.Key_Enter]:
            self.view.btnIngresar.click()
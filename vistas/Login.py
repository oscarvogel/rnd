# coding=utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout

from modelos.Usuarios import CboUsuario
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.Botones import Boton, BotonCerrarFormulario
from pyqt5libs.pyqt5libs.EntradaTexto import Password
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.utiles import imagen




class LoginView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)

    def setupUi(self, Form):
        Form.resize(667, 188)
        self.setWindowTitle("Inicio de sistema")
        layoutPpal = QHBoxLayout(Form)

        layoutInicio = QVBoxLayout()
        labelImagen = Etiqueta()
        pixmap = QPixmap(imagen("logo.png")).scaled(
            150,
            150,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
        labelImagen.setPixmap(pixmap)
        layoutInicio.addWidget(labelImagen)
        layoutPpal.addLayout(layoutInicio)

        layoutIngreso = QVBoxLayout()

        layoutParam = QGridLayout()
        lblNombre = Etiqueta(texto="Usuario")
        self.cboUsuario = CboUsuario()
        layoutParam.addWidget(lblNombre, 0, 0)
        layoutParam.addWidget(self.cboUsuario, 0, 1)
        lblPass = Etiqueta(texto=u"Contraseña")
        self.textPass = Password()
        layoutParam.addWidget(lblPass, 1, 0)
        layoutParam.addWidget(self.textPass, 1, 1)
        layoutIngreso.addLayout(layoutParam)
        layoutBotones = QHBoxLayout()
        self.btnIngresar = Boton(texto="Ingresar", imagen=imagen("iconfinder_Login_in_85265.png"))
        self.btnIngresar.setDefault(True)
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnIngresar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutIngreso.addLayout(layoutBotones)
        layoutPpal.addLayout(layoutIngreso)
        self.textPass.proximoWidget = self.btnIngresar

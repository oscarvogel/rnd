# -*- coding: utf-8 -*-
try:
    import win32print
except:
    pass
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog


class Ui_FormPrinter(QDialog):

    cPrinterSelected = ''

    def __init__(self, parent=None):
        QDialog.__init__(self, parent=None)
        self.setupUi(self)

    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(613, 132)
        self.layoutWidget = QtWidgets.QWidget(Form)
        self.layoutWidget.setGeometry(QtCore.QRect(0, 0, 611, 129))
        self.layoutWidget.setObjectName("layoutWidget")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.labelTitulo = QtWidgets.QLabel(self.layoutWidget)
        self.labelTitulo.setObjectName("labelTitulo")
        self.verticalLayout.addWidget(self.labelTitulo)
        self.comboBoxImpresoras = QtWidgets.QComboBox(self.layoutWidget)
        self.comboBoxImpresoras.setObjectName("comboBoxImpresoras")
        self.verticalLayout.addWidget(self.comboBoxImpresoras)
        self.labelEstado = QtWidgets.QLabel(self.layoutWidget)
        self.labelEstado.setObjectName("labelEstado")
        self.verticalLayout.addWidget(self.labelEstado)
        self.labelTipo = QtWidgets.QLabel(self.layoutWidget)
        self.labelTipo.setObjectName("labelTipo")
        self.verticalLayout.addWidget(self.labelTipo)
        self.labelUbicacion = QtWidgets.QLabel(self.layoutWidget)
        self.labelUbicacion.setObjectName("labelUbicacion")
        self.verticalLayout.addWidget(self.labelUbicacion)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButtonAceptar = QtWidgets.QPushButton(self.layoutWidget)
        self.pushButtonAceptar.setObjectName("pushButtonAceptar")
        self.horizontalLayout.addWidget(self.pushButtonAceptar)
        self.pushButtonCerrar = QtWidgets.QPushButton(self.layoutWidget)
        self.pushButtonCerrar.setObjectName("pushButtonCerrar")
        self.horizontalLayout.addWidget(self.pushButtonCerrar)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

        printers = win32print.EnumPrinters(2)
        for p in printers:
            self.comboBoxImpresoras.addItem(p[2])

        icono = QIcon("imagenes/aceptar.bmp")
        self.pushButtonAceptar.setIcon(icono)
        self.pushButtonAceptar.setIconSize(QSize(32,32))

        icono = QIcon("imagenes/log-out.png")
        self.pushButtonCerrar.setIcon(icono)
        self.pushButtonCerrar.setIconSize(QSize(32,32))

        self.pushButtonAceptar.clicked.connect(self.Aceptar)
        self.pushButtonCerrar.clicked.connect(self.Cerrar)
        self.comboBoxImpresoras.currentTextChanged.connect(self.ActualizaDatosImpre)

    def Cerrar(self):
        self.cPrinterSelected = ''
        self.close()

    def Aceptar(self):
        self.cPrinterSelected = self.comboBoxImpresoras.currentText().strip()
        self.close()

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Seleccione la impresora"))
        self.labelTitulo.setText(_translate("Form", "Seleccione la impresora"))
        self.pushButtonAceptar.setText(_translate("Form", "Aceptar"))
        self.pushButtonCerrar.setText(_translate("Form", "Cancelar"))
        self.labelEstado.setText(_translate("Form", "Estado"))
        self.labelTipo.setText(_translate("Form", "Tipo"))
        self.labelUbicacion.setText(_translate("Form", "Ubicacion"))

    def ActualizaDatosImpre(self):
        impre = self.comboBoxImpresoras.currentText()
        d = win32print.OpenPrinter(impre)
        p = win32print.GetPrinter(d, 2)
        self.labelUbicacion.setText("Ubicacion: {}".format(p['pLocation']))
        self.labelTipo.setText("Tipo {}".format(p['pDriverName']))
        #self.labelEstado.setText()
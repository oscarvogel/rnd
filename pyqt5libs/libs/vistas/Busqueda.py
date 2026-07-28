# -*- coding: utf-8 -*-
from ast import mod
import datetime
import decimal
import logging
from functools import reduce

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QTableWidget, QHBoxLayout, QTableWidgetItem

from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.Botones import BotonAceptar, BotonCerrarFormulario
from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto
from pyqt5libs.pyqt5libs.Formulario import Formulario
from pyqt5libs.pyqt5libs.utiles import LeerIni, FormatoFecha, imagen


class UiBusqueda(Formulario):
    modelo = None  # modelo sobre la que se realiza la busqueda
    cOrden = ""  # orden de busqueda
    limite = 100  # maximo registros a mostrar
    campos = []  # campos a mostrar
    campoBusqueda = None  # campo sobre el cual realizar la busqueda
    lRetval = False  # indica si presiono en aceptar o cancelar
    ValorRetorno = ''  # valor que selecciono el usuario
    camposTabla = None  # los campos de la tabla
    campoRetorno = None  # campo del cual obtiene el dato para retornar el codigo/valor
    colRetorno = 0  # la columna de donde retorna el valor
    colBusqueda = 0  # la columno que establece la busqueda
    campoRetornoDetalle = ''  # campo que retorna el detalle
    condiciones = ''  # condiciones de filtrado
    data = ''  # datos a mostrar

    def __init__(self):
        Formulario.__init__(self)
        self.setupUi(self)
        # self.CargaDatos()

    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(829, 556)
        Dialog.setWindowTitle("Busqueda de datos en {}".format(self.modelo._meta.name if self.modelo else ""))
        self.setWindowModality(Qt.ApplicationModal)

        self.verticalLayout = QVBoxLayout(Dialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.lineEdit = EntradaTexto(Dialog, tooltip='Ingresa tu busqueda',
                                     placeholderText="Ingresa tu busqueda")
        self.lineEdit.setObjectName("lineEdit")
        self.verticalLayout.addWidget(self.lineEdit)
        self.tableView = QTableWidget(Dialog)
        self.tableView.setObjectName("tableView")
        self.tableView.setSortingEnabled(True)

        self.verticalLayout.addWidget(self.tableView)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.btnAceptar = BotonAceptar(textoBoton="&Seleccionar", imagen=imagen("cargar.png"))
        self.btnAceptar.setObjectName("btnAceptar")
        self.horizontalLayout.addWidget(self.btnAceptar)
        self.btnCancelar = BotonCerrarFormulario(imagen=imagen("close.png"))
        self.btnCancelar.setObjectName("btnCancelar")
        self.horizontalLayout.addWidget(self.btnCancelar)
        self.verticalLayout.addLayout(self.horizontalLayout)

        # self.retranslateUi(Dialog)
        self.btnCancelar.clicked.connect(self.Cerrar)
        self.lineEdit.textChanged.connect(self.CargaDatos)
        self.btnAceptar.clicked.connect(self.Aceptar)
        self.tableView.cellClicked.connect(self.cell_was_clicked)
        self.tableView.doubleClicked.connect(self.Aceptar)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Busqueda en " + self.tabla))
        self.btnAceptar.setText(_translate("Dialog", "Aceptar"))
        self.btnCancelar.setText(_translate("Dialog", "Cerrar"))

    def Aceptar(self):
        self.lRetval = True
        if self.tableView.currentItem():
            self.ValorRetorno = self.tableView.currentItem().text()
            self.ValorRetorno = self.tableView.item(self.tableView.currentRow(), self.colRetorno).text()
            self.campoRetornoDetalle = self.tableView.item(self.tableView.currentRow(), self.colBusqueda).text()
            print("Seleccionado {} columna {} fila {}".format(self.ValorRetorno,
                                                              self.tableView.currentColumn(),
                                                              self.tableView.currentRow()))
            self.close()

    def cell_was_clicked(self, row, column):
        item = self.tableView.item(row, column)

        self.ValorRetorno = item.text()
        logging.info("Row {} and Column {} was clicked value {} item {}"
                     .format(row, column, self.tableView.currentItem().text(), item))

    def CargaDatos(self):

        textoBusqueda = self.lineEdit.text()

        if not self.data:
            if not self.modelo:
                Ventanas.showAlert(LeerIni('nombre_sistema'), "No se ha establecido el modelo para la busqueda")
                return
            rows = self.modelo.select().dicts()
        else:
            rows = self.data

        if self.condiciones:
            if isinstance(self.condiciones, list):
                for c in self.condiciones:
                    rows = rows.where(c)
            else:
                rows = rows.where(self.condiciones)

        if textoBusqueda:
            rows = self.ArmaBusqueda(rows)

        rows = rows.limit(self.limite)
        self.tableView.setColumnCount(len(self.campos))
        self.tableView.setRowCount(len(rows))

        logging.info("SQL de condiciones de busqueda {}".format(self.condiciones))
        # self.tableView.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)

        for col in range(0, len(self.campos)):
            if self.campos[col] == self.campoRetorno.column_name:
                self.colRetorno = col
            if isinstance(self.campoBusqueda, list):
                if self.campos[col] == self.campoBusqueda[0]:
                    self.colBusqueda = col
            else:
                if self.campos[col] == self.campoBusqueda.column_name:
                    self.colBusqueda = col

            self.tableView.setHorizontalHeaderItem(col, QTableWidgetItem(self.campos[col].capitalize()))

        fila = 0
        for row in rows:
            for col in range(0, len(self.campos)):
                if isinstance(row[self.campos[col]], (int, decimal.Decimal,)):
                    item = QTableWidgetItem(str(row[self.campos[col]]))
                elif isinstance(row[self.campos[col]], (datetime.date)):
                    item = QTableWidgetItem(FormatoFecha(row[self.campos[col]], formato='dma'))
                else:
                    item = QTableWidgetItem(QTableWidgetItem(row[self.campos[col]]))

                item.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled)
                self.tableView.setItem(fila, col, item)

            fila += 1
        self.tableView.resizeRowsToContents()
        self.tableView.resizeColumnsToContents()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Down:
            self.tableView.setFocus()
        elif event.key() == QtCore.Qt.Key_Enter or event.key() == QtCore.Qt.Key_Return:
            self.btnAceptar.click()

    def ArmaBusqueda(self, rows):
        if isinstance(self.campoBusqueda, list):
            # getattr(self.modelo, campo).contains(self.lineEdit.text()) crea una condición de búsqueda que verifica
            # si el campo contiene la palabra buscada.
            # (getattr(self.model, campo).contains(self.lineEdit.text()) for campo in self.campoBusqueda)
            # genera una secuencia de condiciones para cada campo en la lista.
            # reduce(lambda x, y: x | y, ...) combina estas condiciones utilizando el operador OR (|).

            rows = rows.where(reduce(lambda x, y: x | y, (getattr(self.modelo, campo).contains(self.lineEdit.text())
                                                          for campo in self.campoBusqueda)))
            # for b in self.campoBusqueda:
            #     rows = rows.where(b.contains(self.lineEdit.text()))
        else:
            rows = rows.where(self.campoBusqueda.contains(self.lineEdit.text()))
        return rows


class DBrowse(VistaBase):

    def __int__(self):
        self.setupUi(self)
        self.lineEdit.setVisible(False)

    def crea_busqueda(self, data):

        ventana = UiBusqueda()
        ventana.data = data
        ventana.CargaDatos()
        ventana.setModal(True)
        ventana.show()
        if ventana.lRetval:
            return ventana.ValorRetorno
        else:
            return -1


class Buscador:
    
    modelo = None  # modelo sobre la que se realiza la busqueda
    codigo = None  # campo que contiene el codigo
    nombre = None  # campo que contiene el nombre
    campos = []  # campos a mostrar
    cOrden = None  # orden de busqueda
    condiciones = []  # condiciones de filtrado
    campos_busqueda = []  # campos sobre los cuales realizar la busqueda

    def __init__(self):
        self.valorRetorno = None
        self.lRetval = False  # indica si presiono en aceptar o cancelar
    
    def buscar(self, parent=None):
        """Realiza una busqueda y devuelve el resultado seleccionado"""
        ventana = UiBusqueda()
        ventana.modelo = self.modelo
        ventana.cOrden = self.cOrden
        ventana.campos = self.campos
        ventana.campoBusqueda = self.campos_busqueda if self.campos_busqueda else self.campoRetorno.column_name
        ventana.camposTabla = self.campos
        ventana.campoRetorno = self.codigo.column_name if isinstance(self.codigo, str) else self.codigo
        ventana.condiciones = self.condiciones
        ventana.CargaDatos()
        ventana.exec_()
        if ventana.lRetval:
            self.valorRetorno = ventana.ValorRetorno
            self.lRetval = True
            return self.valorRetorno
        return None
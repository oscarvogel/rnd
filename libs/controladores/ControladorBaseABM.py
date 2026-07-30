# coding=utf-8
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

__author__ = "Jose Oscar Vogel <oscarvogel@gmail.com>"
__copyright__ = "Copyright (C) 2018 Jose Oscar Vogel"
__license__ = "GPL 3.0"
__version__ = "0.1"

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QProgressDialog, QMessageBox

#Controlador base del cual derivan todos los abm del sistema
from modelos.ModeloBase import reconnect_if_needed
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from pyqt5libs.libs.vistas.ABM import ABM


class ControladorBaseABM(ControladorBase):

    campoclave = None #campo clave para actualizar la tabla, tiene que ser caracter

    def __init__(self):
        super().__init__()
        self.view = ABM()
        # self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnAceptar.clicked.connect(self.onClickBtnAceptar)
        self.view.tableView.doubleClicked.connect(self.onDoubleClikedTableWidget)
        self.view.btnExcel.clicked.connect(self.onClickBtnExcel)
        self.view.btnBorrar.clicked.connect(self.onClickBtnBorrar)
        self.view.btnEditar.clicked.connect(self.view.Modifica)
        self.view.btnAgregar.clicked.connect(self.view.Agrega)
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.lineEditBusqueda.textChanged.connect(self.view.Busqueda)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        if not self.model:
            Ventanas.showAlert("Sistema", "Debes establecer un modelo a actualizar")
            return
        if self.campoclave is None:
            Ventanas.showAlert("Sistema", "Debes establecer un campo clave a actualizar")
            return

        if self.onPreClickAceptar():
            if self.view.tipo == 'M':
                dato = self.model.get_by_id(self.view.controles[self.campoclave].text())
            else:
                dato = self.model()

            for control in self.view.controles:
                dato.__data__[control] = self.view.controles[control].valor()
            dato.save(force_insert=self.view.tipo == 'A')
            self.view.btnAceptarClicked()
        self.onPostClickAceptar()

    def onPostClickAceptar(self):
        pass

    def onPreClickAceptar(self):
        return True

    def onDoubleClikedTableWidget(self, index):
        if self.view.tableView.currentRow() == -1:
            return
        self.view.btnEditar.click()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def onClickBtnExcel(self, *args, **kwargs):
        limite = self.view.limite
        self.view.limite = 10000000
        self.view.ArmaTabla()
        self.view.tableView.ExportaExcel()
        self.view.limite = limite

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def onClickBtnBorrar(self, *args, **kwargs):
        if not self.view.tableView.currentRow() != -1:
            return

        if not self.view.campoClave:
            Ventanas.showAlert("Sistema", "No tenes establecido el campo clave y no podemos continuar")

        if Ventanas.showConfirmation("Sistema", "Deseas borrar el registro seleccionado?") == QMessageBox.Ok:
            id = self.view.tableView.ObtenerItem(
                fila=self.view.tableView.currentRow(),
                col=self.view.campoClave.column_name.capitalize())

            modelo = self.model.get_by_id(id)
            modelo.delete_instance()
            self.CargaDatos()
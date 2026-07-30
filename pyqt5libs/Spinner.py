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

import datetime

from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtWidgets import QDoubleSpinBox, QHBoxLayout

from .Etiquetas import Etiqueta
from .utiles import InicioMes, FinMes, FechaMysql, MesIdentificador


class Spinner(QDoubleSpinBox):

    proximoWidget = None
    # emit signal
    keyPressed = QtCore.pyqtSignal(int)  # presiona tecla manda la tecla prsionad
    
    focusOut = pyqtSignal()  # 🔔 señal personalizada
    
    focusIn = pyqtSignal()  # 🔔 señal personalizada

    def __init__(self, parent=None, *args, **kwargs):
        QDoubleSpinBox.__init__(self, parent)

        font = QFont()
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
            font.setPointSizeF(self.tamanio)
        else:
            font.setPointSizeF(10)
        self.setFont(font)
        self.setMaximum(9999999999)
        self.setMinimum(-9999999999)

        if 'decimales' in kwargs:
            self.setDecimals(kwargs['decimales'])
        else:
            self.setDecimals(4)
        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])
            
        if 'placeholderText' in kwargs:
            self.setToolTip(kwargs['placeholderText'])

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Enter or \
                        event.key() == QtCore.Qt.Key_Return or\
                        event.key() == QtCore.Qt.Key_Tab:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
            else:
                self.focusNextChild()
        else:
            QDoubleSpinBox.keyPressEvent(self, event)
        self.keyPressed.emit(event.key())

    def focusInEvent(self, *args, **kwargs):
        self.selectAll()
        self.focusIn.emit()  # 🔔 emitís la señal cuando gana el foco
        QDoubleSpinBox.focusInEvent(self, *args, **kwargs)

    def focusOutEvent(self, *args, **kwargs):
        self.setStyleSheet("background-color: Dodgerblue")
        self.focusOut.emit()  # 🔥 emitís la señal cuando pierde el foco
        QDoubleSpinBox.focusOutEvent(self, *args, **kwargs)

    def setText(self, p_str):
        if isinstance(p_str, str):
            p_str = float(p_str or 0)
        self.setValue(p_str)

    def text(self):
        return str(self.value())

    def valor(self):
        return self.value()

    def setColor(self, *args, **kwargs):
        if 'backgroundcolor' in kwargs:
            if isinstance(kwargs['backgroundcolor'], QColor):
                color = kwargs['backgroundcolor']
                self.setStyleSheet('background-color: rgb({},{},{})'.format(
                    color.red(), color.green(), color.blue()
                ))

        if 'color' in kwargs:
            if isinstance(kwargs['color'], QColor):
                color = kwargs['color']
                self.setStyleSheet('color: rgb({},{},{});{}'.format(
                    color.red(), color.green(), color.blue(), self.styleSheet()
                ))
        if 'restaura' in kwargs:
            self.setStyleSheet("")

        if 'estilo' in kwargs:
            self.setStyleSheet(kwargs['estilo'])


class Periodo(QHBoxLayout):

    cPeriodo = ''
    dInicio = None #date que indica el primer dia del mes
    dFin = None #date que indica el ultimo dia del mes
    textoEtiqueta = ''
    proximoWidget = None #proximo widget al que va cuando da enter
    periodo_descripcion = '' #describe el periodo con nombre del mes
    enabled = True
    actualiza_periodo = pyqtSignal()

    def __init__(self, parent=None, *args, **kwargs):

        QHBoxLayout.__init__(self)
        if 'texto' in kwargs:
            textoEtiqueta = kwargs['texto']
            self.labelPeriodo = Etiqueta(parent, texto=textoEtiqueta)
            self.labelPeriodo.setObjectName("labelPeriodo")
            self.addWidget(self.labelPeriodo)

        self.lineEditMes = Spinner(decimales=0)
        self.lineEditMes.setDecimals(0)
        self.lineEditMes.setObjectName("lineEditMes")
        self.addWidget(self.lineEditMes)
        self.lineEditAnio = Spinner(decimales=0)
        self.lineEditAnio.setDecimals(0)
        self.lineEditAnio.setObjectName("lineEditAnio")
        self.addWidget(self.lineEditAnio)

        self.lineEditMes.proximoWidget = self.lineEditAnio
        self.lineEditAnio.valueChanged.connect(self.ActualizaPeriodo)
        self.lineEditMes.valueChanged.connect(self.ActualizaPeriodo)
        self.lineEditAnio.setValue(datetime.date.today().year)
        self.lineEditMes.setValue(datetime.date.today().month)
        self.lineEditMes.setMinimum(1.)
        self.lineEditMes.setMaximum(12.)
        self.lineEditAnio.setMinimum(2000.)
        self.lineEditAnio.setMaximum(2050.)
        self.lineEditAnio.setValue(datetime.date.today().year)
        self.lineEditAnio.proximoWidget = self.proximoWidget

    def ActualizaPeriodo(self):
        self.cPeriodo = str(round(self.lineEditAnio.value())) + str(round(self.lineEditMes.value())).zfill(2)
        if self.lineEditMes.value() >= 1 and self.lineEditMes.value() <= 12:
            self.dInicio = InicioMes(datetime.date(int(self.lineEditAnio.value()),
                                               int(self.lineEditMes.value()), 1))
        self.dFin = FinMes(self.dInicio)
        if self.lineEditMes.value() != 0:
            self.periodo_descripcion = MesIdentificador(periodo=self.cPeriodo)
        self.actualiza_periodo.emit()

    def setText(self, p_str):
        if not p_str:
            p_str = FechaMysql()[:6]
        self.cPeriodo = p_str
        self.lineEditMes.setValue(float(p_str[4:]))
        self.lineEditAnio.setValue(float(p_str[:4]))

    def setStyleSheet(self, p_str):
        self.lineEditMes.setStyleSheet(p_str)
        self.lineEditAnio.setStyleSheet(p_str)

    def valor(self):
        return self.cPeriodo
    
    def setFocus(self):
        self.lineEditMes.setFocus()
        self.lineEditMes.selectAll()


# -*- coding: utf-8 -*-
import os
import sys
from os.path import join

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QDesktopWidget, QHBoxLayout

from .EntradaTexto import EntradaTexto
from .Etiquetas import Etiqueta
from .Fechas import FechaLine
from .utiles import icono_sistema, ubicacion_sistema

try:
    from modelos.ParametrosSistema import ParamSist
except ModuleNotFoundError:
    class ParamSist:
        @staticmethod
        def ObtenerParametro(_nombre, default=None):
            return default


class Formulario(QDialog):

    lblStatusBar = None
    centraform = True
    controles = {}

    def __init__(self, parent=None):
        QDialog.__init__(self, parent=None)
        self.setModal(False)
        self.Exception = self.Traceback = ""
        self.LanzarExcepciones = False
        self.setWindowIcon(icono_sistema())
        # self.setWindowModality(Qt.NonModal)
        self._want_to_close = False
        flags = Qt.WindowMinMaxButtonsHint | Qt.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.setMinimumSize(420, 160)
        self.EstablecerTema()
        # self.EstablecerOrden()

    def Cerrar(self):
        self._want_to_close = True
        self.close()

    def exec_(self):
        if self.centraform:
            self.Center()
        QDialog.exec_(self)

    def Center(self):
        qr = self.frameGeometry()

        # center point of screen
        cp = QDesktopWidget().availableGeometry().center()

        # move rectangle's center point to screen's center point
        qr.moveCenter(cp)

        # top left of rectangle becomes top left of window centering it
        self.move(qr.topLeft())

    def resizeEvent(self, QResizeEvent):
        QDialog.resizeEvent(self, QResizeEvent)

    def addStatusBar(self, layout=None):
        if layout:
            self.lblStatusBar = Etiqueta()
            layout.addWidget(self.lblStatusBar)

    def setTextStatusBar(self, text=''):
        if self.lblStatusBar:
            self.lblStatusBar.setText(text)

    def ArmaEntrada(self, nombre="", boxlayout=None, texto='', *args, **kwargs):
        if not nombre:
            return
        if not boxlayout:
            boxlayout = QHBoxLayout()
            lAgrega = True
        else:
            lAgrega = False

        if not texto:
            if isinstance(nombre, str):
                texto = nombre.capitalize()
            else:
                if not 'control' in kwargs:
                    if nombre.field_type in ['DATE']:
                        kwargs['control'] = FechaLine()
                texto = nombre.verbose_name if nombre.verbose_name else nombre.name.capitalize()


        if not isinstance(nombre, str): #si no es un campo texto intento convertir de un campo de pewee
            nombre = nombre.name

        labelNombre = Etiqueta(texto=texto)
        labelNombre.setObjectName("labelNombre")
        boxlayout.addWidget(labelNombre)

        if 'control' in kwargs:
            lineEditNombre = kwargs['control']
        else:
            lineEditNombre = EntradaTexto()

        if 'relleno' in kwargs:
            lineEditNombre.relleno = kwargs['relleno']

        if 'inputmask' in kwargs:
            lineEditNombre.setInputMask(kwargs['inputmask'])

        lineEditNombre.setObjectName(nombre)
        #print(type(lineEditNombre))
        boxlayout.addWidget(lineEditNombre)
        if 'enabled' in kwargs:
            lineEditNombre.setEnabled(kwargs['enabled'])

        self.controles[nombre] = lineEditNombre

        if lAgrega:
            self.verticalLayoutDatos.addLayout(boxlayout)
        return boxlayout

    def setupUi(self, Form):
        pass

    def ConectarWidgets(self):
        pass

    # def closeEvent(self, evnt):
    #     if self._want_to_close:
    #         super(Formulario, self).closeEvent(evnt)
    #     else:
    #         evnt.ignore()
    #         #self.setWindowState(QtCore.Qt.WindowMinimized)

    def keyPressEvent(self, QKeyEvent):
        QKeyEvent.ignore()

    def EstablecerTema(self):
        tema_configurado = ParamSist.ObtenerParametro("TEMA", "forestal_moderno.css")
        if not tema_configurado or tema_configurado == "TEMA":
            tema_configurado = "forestal_moderno.css"

        if not tema_configurado.lower().endswith('.css'):
            tema_configurado += '.css'
        
        candidatos = [
            join(ubicacion_sistema(), 'temas', tema_configurado),
            join('temas', tema_configurado),
            join('libs', 'temas', tema_configurado),
            join(os.path.dirname(__file__), '..', 'libs', 'temas', tema_configurado),
        ]

        if hasattr(sys, "_MEIPASS"):
            candidatos.append(join(sys._MEIPASS, 'temas', tema_configurado))

        tema = next((candidato for candidato in candidatos if os.path.isfile(candidato)), "")

        if not tema:
            candidatos_fallback = [
                join(ubicacion_sistema(), 'temas', 'forestal_moderno.css'),
                join('temas', 'forestal_moderno.css'),
                join('libs', 'temas', 'forestal_moderno.css'),
                join(os.path.dirname(__file__), '..', 'libs', 'temas', 'forestal_moderno.css'),
                join('libs', 'temas', 'ubuntu.css'),
                join(os.path.dirname(__file__), '..', 'libs', 'temas', 'ubuntu.css'),
            ]
            if hasattr(sys, "_MEIPASS"):
                candidatos_fallback.append(join(sys._MEIPASS, 'temas', 'forestal_moderno.css'))
            tema = next((candidato for candidato in candidatos_fallback if os.path.isfile(candidato)), "")

        if not tema:
            return

        with open(tema, encoding="utf-8") as style_file:
            style = style_file.read()
        self.setStyleSheet(style)

    def EstablecerOrden(self):
        pass

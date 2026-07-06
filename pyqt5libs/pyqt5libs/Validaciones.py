# coding=utf-8
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLineEdit, QHBoxLayout

from modelos.ModeloBase import reconnect_if_needed

from . import Ventanas
from .EntradaTexto import EntradaTexto
from .Etiquetas import Etiqueta, EtiquetaRoja
from .utiles import inicializar_y_capturar_excepciones
from ..libs.vistas.Busqueda import UiBusqueda


class Validaciones(EntradaTexto):

    #modelo sobre la que se consulta
    modelo = ''

    #orden para la busqueda si se presiona F2
    cOrden = ''

    #campos que se van a mostrar
    campos = ''

    #campos de la tabla, permite hacer uniones de campos
    camposTabla = None

    #el campo que va a retornar la busqueda
    campoRetorno = None

    #el campo del nombre
    campoNombre = None

    #largo se utiliza para la cantidad de ingreso y para el zfill y rellanar con ceros
    largo = 0

    #este es el widget que va a contener la descripcion del nombre
    widgetNombre = None

    #en caso de que necesitems hacer una condicion para mostrar los datos se utiliza esta propiedad
    condiciones = ''

    #indica si el valor obtenido es valido o no
    valido = False

    #cursor que guarda los valores obtenidos por el outfocus
    cursor = None

    #clase para la busqueda
    clasebusqueda = None

    #indica si muestra la excepciones cuando hay un error
    LanzarExcepciones = True

    #emite una señal cuando se realizo la validacion
    postvalida = pyqtSignal()

    solo_numeros = True

    campos_busqueda = None
    
    realiza_busqueda = False

    def __init__(self, parent=None, *args, **kwargs):
        EntradaTexto.__init__(self, parent, *args, **kwargs)
        font = QFont()
        font.setPointSizeF(10)
        self.setFont(font)
        if self.largo != 0:
            self.setMaxLength(self.largo)
        self.setMaximumWidth(50)
        self.setToolTip("Presione F2 para buscar")

    @inicializar_y_capturar_excepciones
    def keyPressEvent(self, event, *args, **kwargs):
        self.lastKey = event.key()
        if event.key() == QtCore.Qt.Key_F2:
            self.busqueda(event)
        elif event.key() == QtCore.Qt.Key_Enter or \
                        event.key() == QtCore.Qt.Key_Return or\
                        event.key() == QtCore.Qt.Key_Tab:
            
            if self.realiza_busqueda and not self.value():
                self.busqueda(event)
            if self.proximoWidget:
                self.proximoWidget.setFocus()
            self.valida()
        QLineEdit.keyPressEvent(self, event)
    
    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def busqueda(self, event, *args, **kwargs):
        if self.clasebusqueda:
            ventana = self.clasebusqueda()
        else:
            ventana = UiBusqueda()
        ventana.modelo = self.modelo
        ventana.cOrden = self.cOrden
        ventana.campos = self.campos
        ventana.campoBusqueda = self.campos_busqueda if self.campos_busqueda else self.cOrden
        ventana.camposTabla = self.camposTabla
        ventana.campoRetorno = self.campoRetorno
        ventana.condiciones = self.condiciones
        ventana.CargaDatos()
        ventana.exec_()
        if ventana.lRetval:
            self.setText(ventana.ValorRetorno)
            self.valido = True
            QLineEdit.keyPressEvent(self, event)
   
    @inicializar_y_capturar_excepciones
    def focusOutEvent(self, QFocusEvent, *args, **kwargs):
        if self.lastKey != QtCore.Qt.Key_F2:
            self.valida()
        QLineEdit.focusOutEvent(self, QFocusEvent)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def valida(self, *args, **kwargs):
        if not self.text():
            return
        if self.largo != 0:
            self.setText(str(self.text()).zfill(self.largo))
        if self.solo_numeros:
            if not self.text().isnumeric():
                Ventanas.showAlert("Sistema", "Campo permite unicamente numeros")
                self.setText('')
                return
        #data = SQL().BuscaUno(self.tabla, self.campoRetorno, self.text())
        data = self.modelo.select().where(self.campoRetorno == self.text())

        if self.condiciones:
            if isinstance(self.condiciones, list):
                for c in self.condiciones:
                    data = data.where(c)
            else:
                data = data.where(self.condiciones)
        data = data.dicts()
        if data:
            self.valido = True
            self.setStyleSheet("background-color: Dodgerblue")
            self.cursor = data
            if self.widgetNombre:
                for d in data:
                    if isinstance(self.campoNombre, list):
                        texto = " ".join(str(d[c.name]).strip() for c in self.campoNombre)
                        self.widgetNombre.setText(texto)
                    else:
                        self.widgetNombre.setText(str(d[self.campoNombre.name]).strip())
        else:
            self.valido = False
            self.setStyleSheet("background-color: yellow")
            #Ventanas.showAlert("Error", "Codigo no encontrado en el sistema")
        self.postvalida.emit()

class ValidaConNombre(QHBoxLayout):

    textoEtiqueta = 'Nombre'
    modelo = None
    campoNombre = None
    campoRetorno = None
    camposTabla = []
    largo = 0
    maxwidth = 50
    solo_numeros = True
    condiciones = None
    campos_busqueda = None

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)

        if 'texto' in kwargs:
            self.textoEtiqueta = kwargs['texto']

        self.labelNombre = Etiqueta(parent, texto=self.textoEtiqueta)
        self.labelNombre.setObjectName("labelNombre")
        self.addWidget(self.labelNombre)

        self.lineEditCodigo = Validaciones(parent)
        self.lineEditCodigo.setObjectName("lineEditNombre")
        self.lineEditCodigo.modelo = self.modelo
        self.lineEditCodigo.campoNombre = self.campoNombre
        self.lineEditCodigo.campoRetorno = self.campoRetorno
        self.lineEditCodigo.cOrden = self.campoNombre
        self.lineEditCodigo.camposTabla = self.camposTabla
        self.lineEditCodigo.campos = self.lineEditCodigo.camposTabla
        self.lineEditCodigo.largo = self.largo
        self.lineEditCodigo.condiciones = self.condiciones
        self.lineEditCodigo.solo_numeros = self.solo_numeros
        self.lineEditCodigo.setMaximumWidth(self.maxwidth)
        self.lineEditCodigo.campos_busqueda = self.campos_busqueda if self.campos_busqueda else self.campoNombre
        self.addWidget(self.lineEditCodigo)

        self.labelDescripcion = EtiquetaRoja(parent, texto="")
        self.labelDescripcion.setObjectName("labelDescripcion")
        self.addWidget(self.labelDescripcion)
        self.lineEditCodigo.widgetNombre = self.labelDescripcion
        
    def valor(self):
        """Devuelve el valor del campo de retorno"""
        return self.lineEditCodigo.valor()

class ValidaConTexto(QHBoxLayout):

    textoEtiqueta = 'Codigo'
    modelo = None #modelo sobre el que se realiza la validacion
    nombre = None #nombre de la busqueda
    codigo = None #campo de retorno de la validacion
    orden = None #orden de busqueda, si no se especifica se utiliza el nombre
    condiciones = None #condiciones de filtrado para la busqueda y la validacion,
                        #puede ser una lista de condiciones
    campos = [] #lista con los campos a mostrar si se hace la busqueda con F2
    largo = 0 #indica cuantos caracteres se deja introducir
    ancho = 50 #maximo ancho del control para el codigo
    solo_numeros = True #indica si el campo permite solo numeros
    campos_busqueda = None
    #clase para la busqueda
    clasebusqueda = None
    campoNombre = None #campo que se va a mostrar como nombre


    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent)

        if 'texto' in kwargs:
            self.textoEtiqueta = kwargs['texto']

        self.labelNombre = Etiqueta(parent, texto=self.textoEtiqueta)
        self.labelNombre.setObjectName("labelNombre")
        self.addWidget(self.labelNombre)

        self.lineEditCodigo = Validaciones(parent)
        self.lineEditCodigo.setObjectName("lineEditNombre")
        self.lineEditCodigo.modelo = self.modelo
        self.lineEditCodigo.campoNombre = self.campoNombre if self.campoNombre else self.nombre
        self.lineEditCodigo.campoRetorno = self.codigo
        if self.campos_busqueda:
            self.lineEditCodigo.campos_busqueda = self.campos_busqueda
        else:
            self.lineEditCodigo.cOrden = self.orden if self.orden else self.nombre
        self.lineEditCodigo.condiciones = self.condiciones
        self.lineEditCodigo.campos = self.campos
        self.lineEditCodigo.largo = self.largo
        self.lineEditCodigo.solo_numeros = self.solo_numeros
        self.lineEditCodigo.clasebusqueda = self.clasebusqueda
        self.lineEditCodigo.setMaximumWidth(self.ancho)
        self.addWidget(self.lineEditCodigo)

        self.textNombre = Etiqueta()
        self.lineEditCodigo.widgetNombre = self.textNombre
        self.addWidget(self.textNombre)

    def setText(self, p_str):
        self.lineEditCodigo.setText(p_str)

    def setStyleSheet(self, p_str):
        self.lineEditCodigo.setStyleSheet(p_str)

    def valor(self):
        return self.lineEditCodigo.valor()
# coding=utf-8
import datetime
import decimal

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLineEdit, QHBoxLayout, QTextEdit, QItemDelegate, QCompleter

from . import Ventanas
from .Etiquetas import Etiqueta
from .utiles import validar_cuit, FechaMysql, MesIdentificador, PeriodoAFecha


class EntradaTexto(QLineEdit):
    ventana = None

    # para cuando se presiona ENTER cual es el widget que obtiene el foco
    proximoWidget = None

    # guarda la ultima tecla presionada
    lastKey = None

    largo = 0

    # para campos numericos que debo rellenar con ceros adelante
    relleno = 0

    # emit signal
    keyPressed = QtCore.pyqtSignal(int)  # presiona tecla manda la tecla prsionad
    when = QtCore.pyqtSignal()  # cuando recibe el foco emite una señal
    lostfocus = QtCore.pyqtSignal()  # cuando pierde el foco emite una señal

    def __init__(self, parent=None, *args, **kwargs):

        QLineEdit.__init__(self, parent, *args)
        self.ventana = parent
        font = QFont()
        if 'tamanio' in kwargs:
            font.setPointSizeF(kwargs['tamanio'])
        else:
            font.setPointSizeF(10)
        self.setFont(font)

        if 'tooltip' in kwargs:
            self.setToolTip(kwargs['tooltip'])
        if 'placeholderText' in kwargs:
            self.setPlaceholderText(kwargs['placeholderText'])

        if 'alineacion' in kwargs:
            if kwargs['alineacion'].upper() == 'DERECHA':
                self.setAlignment(QtCore.Qt.AlignRight)
            elif kwargs['alineacion'].upper() == 'IZQUIERDA':
                self.setAlignment(QtCore.Qt.AlignLeft)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

        if 'inputmask' in kwargs:
            self.setInputMask(kwargs['inputmask'])

        if 'largo' in kwargs:
            self.largo = kwargs['largo']

        if 'relleno' in kwargs:
            self.relleno = kwargs['relleno']

    def keyPressEvent(self, event):
        self.lastKey = event.key()
        if event.key() == QtCore.Qt.Key_Enter or \
                event.key() == QtCore.Qt.Key_Return or \
                event.key() == QtCore.Qt.Key_Tab:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QLineEdit.keyPressEvent(self, event)
        self.keyPressed.emit(event.key())

    def focusOutEvent(self, QFocusEvent):
        if self.relleno > 0:
            self.setText(self.text().zfill(self.relleno))

        if self.text():
            self.setStyleSheet("background-color: Dodgerblue")
        else:
            self.setStyleSheet("background-color: white")
        if self.largo > 0:
            if len(self.text()) > self.largo:
                Ventanas.showAlert("Sistema", f"Se ha introducido mayor al permitido")
                self.setText(self.text()[:self.largo])
        QLineEdit.focusOutEvent(self, QFocusEvent)
        self.lostfocus.emit()

    def focusInEvent(self, QFocusEvent):
        self.when.emit()
        self.selectAll()
        QLineEdit.focusInEvent(self, QFocusEvent)

    def setLargo(self, largo=0):
        if largo > 0:
            self.largo = largo
            self.setMaxLength(self.largo)

    def value(self):

        return float(self.text() or 0)

    def valor(self):
        return self.text()

    def setText(self, a0: str) -> None:
        if isinstance(a0, (int, decimal.Decimal, float)):
            a0 = str(a0)
        elif isinstance(a0, datetime.time):
            a0 = a0.strftime("%H:%M:%S")
        elif isinstance(a0, datetime.datetime):
            a0 = a0.strftime("%d/%m/%Y")
        elif isinstance(a0, datetime.date):
            a0 = a0.strftime("%d/%m/%Y")
        super().setText(a0)


class Factura(QHBoxLayout):
    numero = ''
    titulo = ''
    tamanio = 10
    enabled = True

    def __init__(self, parent=None, *args, **kwargs):
        QHBoxLayout.__init__(self)
        if 'titulo' in kwargs:
            self.titulo = kwargs['titulo']
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        if 'enabled' in kwargs:
            self.enabled = kwargs['enabled']

        self.setupUi(parent)

    def setupUi(self, layout):

        if self.titulo:
            self.labelTitulo = Etiqueta(layout, texto=self.titulo, tamanio=self.tamanio)
            self.labelTitulo.setObjectName("labelTitulo")
            self.addWidget(self.labelTitulo)

        self.lineEditPtoVta = EntradaTexto(layout, placeholderText="Pto Vta", tamanio=self.tamanio)
        self.lineEditPtoVta.setObjectName("lineEditPtoVta")
        self.lineEditPtoVta.setEnabled(self.enabled)
        self.addWidget(self.lineEditPtoVta)

        self.lineEditNumero = EntradaTexto(layout, placeholderText="Numero", tamanio=self.tamanio)
        self.lineEditNumero.setObjectName("lineEditNumero")
        self.lineEditNumero.setEnabled(self.enabled)
        self.addWidget(self.lineEditNumero)

        self.lineEditPtoVta.proximoWidget = self.lineEditNumero
        self.lineEditNumero.largo = 8
        self.lineEditPtoVta.largo = 4
        self.lineEditPtoVta.setMaximumWidth(40)
        self.lineEditNumero.setMaximumWidth(70)

        self.lineEditPtoVta.editingFinished.connect(self.AssignNumero)
        self.lineEditNumero.editingFinished.connect(self.AssignNumero)

    def AssignNumero(self):
        self.lineEditNumero.setText(str(self.lineEditNumero.text()).zfill(8))
        self.lineEditPtoVta.setText(str(self.lineEditPtoVta.text()).zfill(4))
        self.numero = str(self.lineEditPtoVta.text()).zfill(4) + \
                      str(self.lineEditNumero.text()).zfill(8)

    def setText(self, texto):
        if texto:
            if len(texto) == 12:
                self.lineEditPtoVta.setText(texto[:4])
                self.lineEditNumero.setText(texto[4:])
            elif len(texto) == 8:
                self.lineEditPtoVta.setText('0000')
                self.lineEditNumero.setText(texto)
            else:
                self.lineEditPtoVta.setText('')
                self.lineEditNumero.setText('')
        else:
            self.lineEditPtoVta.setText('')
            self.lineEditNumero.setText('')
        self.AssignNumero()

class TextEdit(QTextEdit):
    tamanio = 10

    def __init__(self, *args, **kwargs):
        QTextEdit.__init__(self, *args)
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        if 'placeholderText' in kwargs:
            self.setPlaceholderText(kwargs['placeholderText'])
        if 'alto' in kwargs:
            self.setMaximumHeight(kwargs['alto'])
        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])

        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)

    def text(self):
        return self.toPlainText()

    def valor(self):
        return self.text()


class CUIT(EntradaTexto):
    denominacion = ""
    domicilio = ""
    consultaafip = False

    def __init__(self, *args, **kwargs):
        EntradaTexto.__init__(self, *args, **kwargs)
        self.setInputMask("99-99999999-9")

    def focusOutEvent(self, QFocusEvent):
        EntradaTexto().focusOutEvent(QFocusEvent)
        if not validar_cuit(self.text()):
            Ventanas.showAlert("Sistema", "ERROR: CUIT/CUIL no valido. Verfique!!!")
        # if self.consultaafip:
        #     padron = PadronAfip()
        #     ok = padron.ConsultarPersona(cuit=str(self.text()).replace("-", ""))
        #     if padron.errores:
        #         Ventanas.showAlert(LeerIni("nombre_sistema"), "Error al leer informacion en la AFIP")
        #     else:
        #         self.denominacion = padron.denominacion
        #         self.domicilio = padron.direccion


class EntradaFecha(EntradaTexto):

    def __init__(self, *args, **kwargs):
        EntradaTexto.__init__(self, *args, **kwargs)
        self.setInputMask("99/99/9999")

    def setFecha(self, fecha=datetime.datetime.today(), format=None):
        if format:
            if format == "Ymd":
                fecha = datetime.date(year=int(fecha[:4]),
                                      month=int(fecha[4:6]),
                                      day=int(fecha[-2:]))
        if isinstance(fecha, int):
            if fecha > 0:
                self.setDate(datetime.date.today() + datetime.timedelta(days=fecha))
            else:
                self.setDate(datetime.date.today() - datetime.timedelta(days=abs(fecha)))
        else:
            self.setDate(fecha)

    def getFechaSql(self):
        fecha = str(self.text())
        if fecha.replace("/", "").replace("0", ""):
            fecha = datetime.datetime.strptime(fecha, "%d/%m/%Y").date().strftime('%Y%m%d')
        else:
            fecha = '00000000'
        return fecha

    def setDate(self, QDate):
        fecha = QDate.strftime("%d/%m/%Y")
        self.setText(fecha)


class Password(EntradaTexto):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setInputMethodHints(QtCore.Qt.ImhHiddenText | QtCore.Qt.ImhNoAutoUppercase |
                                 QtCore.Qt.ImhNoPredictiveText | QtCore.Qt.ImhSensitiveData)
        self.setEchoMode(QtWidgets.QLineEdit.Password)


class CUITDelegate(QItemDelegate):

    def __init__(self):
        super().__init__()

    def createEditor(self, parent, option, index):
        editor = CUIT(parent)
        editor.consultaafip = True
        # editor.setInputMask("99-99999999-9")

        return editor


class AutoCompleter(EntradaTexto):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def creaCompleter(self, datos=[]):
        completer = QCompleter(datos)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.highlighted.connect(self.setHighlighted)
        self.setCompleter(completer)

    def setHighlighted(self, text):
        self.lastSelected = text

    def getSelected(self):
        return self.lastSelected


class HoraDelegate(QItemDelegate):

    def __init__(self):
        super().__init__()

    def createEditor(self, parent, option, index):
        editor = EntradaTexto(parent)
        editor.setInputMask("99:99:99")

        return editor


class IdentificadorSueldo(EntradaTexto):
    periodo = ''

    def focusInEvent(self, QFocusEvent):
        super().focusInEvent(QFocusEvent)

        if not self.periodo:
            self.periodo = FechaMysql()[:6]

        if not self.text():
            self.setText(MesIdentificador(dFecha=PeriodoAFecha(self.periodo)))

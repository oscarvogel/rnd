# coding=utf-8
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QDateEdit,QItemDelegate, QHBoxLayout

from . import Ventanas
from .EntradaTexto import EntradaTexto
from .Etiquetas import Etiqueta


class Fecha(QDateEdit):

    proximoWidget = None
    tamanio = 10

    def __init__(self, *args, **kwargs):
        QDateEdit.__init__(self, *args)
        self.setCalendarPopup(True)
        #self.cw = QNCalendarWidget(n=1, columns=1)
        #self.setCalendarWidget(self.cw)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)
        if 'fecha' in kwargs:
            self.setFecha(kwargs['fecha'])
        else:
            self.setFecha(0)

    def setFecha(self, fecha=datetime.datetime.today(), format=None):
        if format:
            if format == "Ymd":
                fecha = datetime.date(year=int(fecha[:4]),
                                      month=int(fecha[4:6]),
                                      day=int(fecha[-2:]))
        if isinstance(fecha, str):
            fecha = datetime.datetime.strptime(fecha, format)

        if isinstance(fecha, int):
            if fecha > 0:
                self.setDate(datetime.date.today() + datetime.timedelta(days=fecha))
            else:
                self.setDate(datetime.date.today() - datetime.timedelta(days=abs(fecha)))
        else:
            self.setDate(fecha)

    def keyPressEvent(self, QKeyEvent, *args, **kwargs):
        teclaEnter = [Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab]
        if QKeyEvent.key() in teclaEnter:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        QDateEdit.keyPressEvent(self, QKeyEvent, *args, **kwargs)

    def getFechaSql(self):
        fecha = str(self.text())
        fecha = datetime.datetime.strptime(fecha, "%d/%m/%Y").date().strftime('%Y%m%d')
        return fecha

    def setText(self, fecha=datetime.datetime.today()):
        if isinstance(fecha, (str)):
            fecha = datetime.datetime.today()
        self.setFecha(fecha)

    def toPyDate(self):
        return self.date().toPyDate()

    def getPeriodo(self):
        periodo = self.getFechaSql()[:6]
        return periodo

    def valor(self):
        return self.toPyDate()

class FechaDelegate(QItemDelegate):

    def __init__(self):
        super().__init__()

    def createEditor(self,parent, option, index):
        editor = Fecha(parent, fecha=datetime.datetime.today())

        return editor

class RangoFechas(QHBoxLayout):

    etiqueta_desde = "Desde fecha"
    etiqueta_hasta = "Hasta fecha"
    desde_fecha_ini = 0
    hasta_fecha_ini = 0

    def __init__(self, *args, **kwargs):
        super().__init__()
        if 'desde_fecha' in kwargs:
            self.desde_fecha_ini = kwargs['desde_fecha']
        if 'hasta_fecha' in kwargs:
            self.hasta_fecha_ini = kwargs['hasta_fecha']
        self.setupUi()

    def setupUi(self):
        lblDesdeFecha = Etiqueta(texto=self.etiqueta_desde)
        self.desde_fecha = Fecha(fecha=self.desde_fecha_ini)
        lblHastaFecha = Etiqueta(texto=self.etiqueta_hasta)
        self.hasta_fecha = Fecha(fecha=self.hasta_fecha_ini)
        self.addWidget(lblDesdeFecha)
        self.addWidget(self.desde_fecha)
        self.addWidget(lblHastaFecha)
        self.addWidget(self.hasta_fecha)
        self.desde_fecha.proximoWidget = self.hasta_fecha

class FechaLine(EntradaTexto):

    proximoWidget = None
    tamanio = 10
    nulldate = False
    fecha = None

    def __init__(self, *args, **kwargs):
        super().__init__()
        # self.setCalendarPopup(True)

        if 'enabled' in kwargs:
            self.setEnabled(kwargs['enabled'])
        if 'tamanio' in kwargs:
            self.tamanio = kwargs['tamanio']
        font = QFont()
        font.setPointSizeF(self.tamanio)
        self.setFont(font)
        if 'fecha' in kwargs:
            self.setFecha(kwargs['fecha'])
        # else:
        #     self.setFecha()

        # reg_ex_str = "^(?:(?:31(\/|-|\.)(?:0?[13578]|1[02]))\1|(?:(?:29|30)(\/|-|\.)(?:0?[13-9]|1[0-2])\2))(?:(?:1[6-9]|[2-9]\d)?\d{2})$|^(?:29(\/|-|\.)0?2\3(?:(?:(?:1[6-9]|[2-9]\d)?(?:0[48]|[2468][048]|[13579][26])|(?:(?:16|[2468][048]|[3579][26])00))))$|^(?:0?[1-9]|1\d|2[0-8])(\/|-|\.)(?:(?:0?[1-9])|(?:1[0-2]))\4(?:(?:1[6-9]|[2-9]\d)?\d{2})$"
        # reg_ex = QtCore.QRegExp(reg_ex_str)
        # input_validator = QRegExpValidator(reg_ex, self)
        # self.setValidator(input_validator)
        self.setupUi()

    def setupUi(self):
        self.setInputMask("00/00/0000")
        # self.addWidget(self.textFecha)

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
        elif not fecha or isinstance(fecha, str): #quiere decir que viene None de la tabla en mysql es 0000-00-00
            self.nulldate = True
            # self.setSpecialValueText("0000-00-00")
            self.fecha = "0000-00-00"
        else:
            self.setDate(fecha)

        if isinstance(self.fecha, str):
            self.setText(self.fecha)
        else:
            self.setText(self.fecha.strftime('%d/%m/%Y'))

    def setDate(self, date):
        self.fecha = date

    def keyPressEvent(self, QKeyEvent, *args, **kwargs):
        teclaEnter = [Qt.Key_Enter, Qt.Key_Return, Qt.Key_Tab]
        if QKeyEvent.key() in teclaEnter:
            if self.proximoWidget:
                self.proximoWidget.setFocus()
        elif QKeyEvent.key() in [Qt.Key_Delete, Qt.Key_Backspace]:
            self.clear()
        EntradaTexto.keyPressEvent(self, QKeyEvent, *args, **kwargs)

    def getFechaSql(self):
        # fecha = str(self.text())
        # fecha = datetime.datetime.strptime(fecha, "%d/%m/%Y").date().strftime('%Y%m%d')
        fecha = self.fecha.strftime("%Y%m%d")
        return fecha

    def getPeriodo(self):
        periodo = self.getFechaSql()[:6]
        return periodo

    def toPyDate(self):
        self.focusOutEvent()
        return self.fecha.date()

    def valor(self):
        return self.fecha or "00000000"

    # def text(self):
    #     return self.valor()

    def minimumDate(self):
        return datetime.date(2000, 1, 1)

    def focusOutEvent(self, QFocusEvent=None):
        if len(self.text()) == 8 or self.text().endswith('/'):
            self.setText(f'{self.text()[:6]}{datetime.datetime.now().year}')
        try:
            self.fecha = datetime.datetime.strptime(self.text(), "%d/%m/%Y")
            self.setStyleSheet("background-color: Dodgerblue")
        except:
            Ventanas.showAlert("Sistema", "Fecha no valida")
            self.setStyleSheet("background-color: Red")

class HoraEntradaSalida(QHBoxLayout):

    etiqueta_desde = "Inicio"
    etiqueta_hasta = "Fin"

    def __init__(self):
        super().__init__()
        self.setupUi()

    def setupUi(self):
        lblDesdeHora = Etiqueta(texto=self.etiqueta_desde)
        self.desde_hora = EntradaTexto(inputmask='00:00')
        lblHastaHora = Etiqueta(texto=self.etiqueta_hasta)
        self.hasta_hora = EntradaTexto(inputmask='00:00')
        self.addWidget(lblDesdeHora)
        self.addWidget(self.desde_hora)
        self.addWidget(lblHastaHora)
        self.addWidget(self.hasta_hora)

class Hora(EntradaTexto):
    
    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.setInputMask("00:00")
        self.setMaxLength(5)
    
def calcular_diferencia_horas(hora_inicio, hora_fin):
    formato = "%H:%M"
    
    # Convertir los strings a objetos datetime
    inicio = datetime.datetime.strptime(hora_inicio, formato)
    fin = datetime.datetime.strptime(hora_fin, formato)
    
    # Calcular la diferencia
    diferencia = fin - inicio
    
    # Convertir la diferencia a horas en float
    horas_float = diferencia.total_seconds() / 3600.0
    
    return horas_float
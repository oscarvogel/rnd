# coding=utf-8
import datetime
import decimal
import logging

from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QTabWidget, QWidget, QGridLayout, QHBoxLayout, QLineEdit, QCheckBox, QComboBox, \
    QApplication, QMessageBox

from modelos.ModeloBase import reconnect_if_needed
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.BarraProgreso import Avance
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.Checkbox import CheckBox
from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha, FechaLine
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.Spinner import Spinner
from pyqt5libs.pyqt5libs.Validaciones import ValidaConTexto
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones, EsVerdadero, imagen



class ABM(VistaBase):

    #diccionario que guarda los controles que se agreguen al abm
    controles = {}

    #modelo sobre el que se hace el abm
    model = None

    #indica si es un alta o una modificacion
    tipo = "A"

    #campos a mostrar en la grilla
    camposAMostrar = []

    #condicion para filtrar la tabla
    condicion = None

    #limite de registros
    limite = 100

    #orden de busqueda
    ordenBusqueda = None

    #campo
    campoClave = None

    #campo clave autoincremental
    autoincremental = True

    #campo para el foco
    campoFoco = None

    #columna para los botones del formulario de carga de datos
    colBoton = 0

    #titulo para el abm
    titulo = None

    #indica si permite agregar un nuevo registro
    permiteagregar = True

    #el id de la tabla cuando se modifica
    idtabla = 0

    #color de fondo para los renglones de la grilla
    dynamicBackColor = None

    data = ""

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.controles = {}
        self.initUi()

    @inicializar_y_capturar_excepciones
    def initUi(self, *args, **kwargs):
        self.resize(906, 584)
        nombre_tabla = self.model._meta.table_name.title() if self.model else ''
        if self.titulo:
            self.setWindowTitle("ABM de {}".format(self.titulo))
        else:
            self.setWindowTitle("ABM de {}".format(nombre_tabla))

        self.verticalLayout = QVBoxLayout(self)
        self.lblTitulo = Etiqueta(tamanio=15, texto="ABM de {}".format(nombre_tabla))
        self.verticalLayout.addWidget(self.lblTitulo)

        self.tabWidget = QTabWidget()
        self.tabLista = QWidget()
        self.gridLayout = QGridLayout(self.tabLista)

        self.avance = Avance()
        self.avance.setVisible(False)
        self.verticalLayout.addWidget(self.avance)

        self.lineEditBusqueda = EntradaTexto(self.tabLista, placeholderText="Busqueda")
        self.lineEditBusqueda.setObjectName("lineEditBusqueda")
        self.gridLayout.addWidget(self.lineEditBusqueda, 0, 0, 1, 1)

        self.tableView = Grilla(self.tabLista)
        self.tableView.setObjectName("tableView")
        self.tableView.enabled = True

        # extraigo los nombres de las columnas
        self.tableView.cabeceras = [x.verbose_name if x.verbose_name else x.column_name.capitalize()
                                    for x in self.camposAMostrar]
        self.tableView.ArmaCabeceras()
        self.gridLayout.addWidget(self.tableView, 1, 0, 1, 1)
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")

        self.BotonesAdicionales()

        self.btnAgregar = Boton(self.tabLista, texto="&Agregar",
                                imagen=imagen("new.png"), tamanio=QSize(32,32),
                                tooltip='Agrega nuevo registro', enabled=self.permiteagregar)

        self.btnAgregar.setObjectName("btnAgregar")
        self.horizontalLayout.addWidget(self.btnAgregar)

        self.btnEditar = Boton(self.tabLista, imagen=imagen('edit.png'), tamanio=QSize(32,32),
                               tooltip='Modifica registro', texto='Editar')
        self.btnEditar.setObjectName("btnEditar")
        self.horizontalLayout.addWidget(self.btnEditar)

        self.btnBorrar = Boton(self.tabLista, imagen=imagen('delete.png'), tamanio=QSize(32,32),
                               tooltip='Borrar registro', texto='Borrar')
        self.btnBorrar.setObjectName("btnBorrar")
        self.horizontalLayout.addWidget(self.btnBorrar)

        self.btnExcel = Boton(self.tabLista, imagen=imagen("79354_excel_icon.png"), tamanio=QSize(32,32),
                               tooltip='Exportar a Excel', texto='Excel')
        self.horizontalLayout.addWidget(self.btnExcel)

        self.btnCerrar = Boton(self.tabLista, imagen=imagen('close.png'), tamanio=QSize(32,32),
                               tooltip='Cerrar ABM', texto='Cerrar')
        self.btnCerrar.setObjectName("btnCerrar")
        self.horizontalLayout.addWidget(self.btnCerrar)
        self.gridLayout.addLayout(self.horizontalLayout, 2, 0, 1, 1)

        self.tabWidget.addTab(self.tabLista, "Lista")
        self.tabDetalle = QWidget()
        self.tabWidget.addTab(self.tabDetalle, "Detalle")
        self.tabDetalle.setEnabled(False)

        self.verticalLayout.addWidget(self.tabWidget)

        self.ArmaDatos()
        self.ArmaTabla()
        # self.ConectaWidgets()

    def BotonesAdicionales(self):
        pass

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def ArmaTabla(self, *args, **kwargs):
        self.tableView.setRowCount(0)
        self.avance.setVisible(True)
        if self.data:
           data =  self.data
        else:
            if not self.model: #si no esta establecido el modelo no hago nada
                return

            data = self.model.select().dicts()
            if self.condicion:
                for c in self.condicion:
                    data = data.where(c)

        if self.lineEditBusqueda.text():
            data = self.ArmaBusqueda(data)

        total = len(data)
        avance = 0
        data = data.limit(self.limite)
        for d in data:
            color = QColor(255, 255, 255)
            # QApplication.processEvents()
            avance += 1
            self.avance.actualizar(avance / total * 100)
            if self.camposAMostrar:
                item = [d[x.name] for x in self.camposAMostrar]
            else:
                item = [d[x] for x in d]
            for x in d:
                if self.dynamicBackColor:
                    if x in self.dynamicBackColor:
                        if d[x] == self.dynamicBackColor[x]['valor']:
                            color = self.dynamicBackColor[x]['color']
                        else:
                            color = QColor(255,255,255)
                else:
                    color = self.DevuelveColor(d)
            self.tableView.AgregaItem(item, backgroundColor=color)
        self.avance.setVisible(False)

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def ArmaBusqueda(self, data, *args, **kwargs):
        if self.ordenBusqueda:
            texto = self.lineEditBusqueda.text()
            if isinstance(self.ordenBusqueda, list):
                # Construimos una expresión OR combinando todos los campos
                cond = None
                for campo in self.ordenBusqueda:
                    expr = campo.contains(texto)
                    cond = expr if cond is None else cond | expr
                data = data.where(cond)
            else:
                data = data.where(self.ordenBusqueda.contains(texto))
        else:
            Ventanas.showAlert("Sistema", "Orden no establecido y no se puede realizar la busqueda")
        return data

    
    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def ArmaDatos(self, *args, **kwargs):
        self.verticalLayoutDatos = QVBoxLayout(self.tabDetalle)
        self.verticalLayoutDatos.setObjectName("verticalLayoutDatos")
        self.ArmaCarga()
        self.colBoton = 0

        self.grdBotones = QGridLayout()
        self.grdBotones.setObjectName("grdBotones")
        self.AgregaBotonesDatos()

        self.btnAceptar = Boton(self.tabDetalle, texto='Guardar', imagen=imagen('save.png'), tamanio=QSize(32,32),
                                tooltip="Guardar cambios")
        self.btnAceptar.setObjectName("btnAceptar")
        self.grdBotones.addWidget(self.btnAceptar, 0, self.colBoton, 1, 1)

        self.colBoton += 1
        self.btnCancelar = Boton(self.tabDetalle, texto='Cerrar', imagen=imagen('close.png'), tamanio=QSize(32,32),
                                 tooltip="Cerrar sin guardar")
        self.btnCancelar.setObjectName("btnCancelar")
        self.grdBotones.addWidget(self.btnCancelar, 0, self.colBoton, 1, 1)
        self.verticalLayoutDatos.addLayout(self.grdBotones)
        self.verticalLayout.addWidget(self.tabWidget)
        self.btnCancelar.clicked.connect(self.btnCancelarClicked)
        self.btnAceptar.clicked.connect(self.btnAceptarClicked)
        self.verticalLayoutDatos.addStretch(1)

    def Busqueda(self):
        self.ArmaTabla()

    def ConectaWidgets(self):
        self.lineEditBusqueda.textChanged.connect(self.Busqueda)
        self.btnCerrar.clicked.connect(self.cerrarformulario)
        self.btnBorrar.clicked.connect(self.Borrar)
        self.btnEditar.clicked.connect(self.Modifica)
        self.btnAgregar.clicked.connect(self.Agrega)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def Borrar(self, *args, **kwargs):
        if not self.tableView.currentRow() != -1:
            return

        if not self.campoClave:
            Ventanas.showAlert("Sistema", "No tenes establecido el campo clave y no podemos continuar")

        if Ventanas.showConfirmation("Sistema", "Deseas borrar el registro seleccionado?") == QMessageBox.Ok:
            id = self.tableView.ObtenerItem(fila=self.tableView.currentRow(), col=self.campoClave.column_name.capitalize())
            data = self.model.get_by_id(id)
            data.delete_instance()
            self.ArmaTabla()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def Modifica(self, *args, **kwargs):

        self.tipo = 'M'
        if not self.tableView.currentRow() != -1:
            return

        if not self.campoClave:
            Ventanas.showAlert("Sistema", "No tenes establecido el campo clave y no podemos continuar")

        id = self.tableView.ObtenerItem(fila=self.tableView.currentRow(),
                                        col=self.campoClave.verbose_name if self.campoClave.verbose_name else
                                        self.campoClave.column_name.capitalize())
        id = id.replace('.', '')
        self.idtabla = id

        if self.campoClave.field_type in ['VARCHAR']:
            data = self.model.select().where(self.campoClave == id).dicts()
        elif self.campoClave.field_type in ['AUTO', 'INTEGER']:
            data = self.model.select().where(self.campoClave == int(id)).dicts()
        else:
            data = self.model.select().where(self.campoClave == id).dicts()
        self.tabDetalle.setEnabled(True)
        self.tabWidget.setCurrentIndex(1)
        self.CargaDatos(data)
        if self.campoFoco:
            self.campoFoco.setFocus()
        self.PostClickModifica()

    def CargaDatos(self, data=None):
        if not data:
            return
        for d in data:
            print(d)
            logging.debug("{}".format(d))
            for k in d:
                if k in self.controles:
                    if k == self.campoClave.name:
                        self.controles[k].setEnabled(False)
                    if isinstance(self.controles[k], QLineEdit):
                        if isinstance(d[k], (int, decimal.Decimal, float)):
                            self.controles[k].setText(str(d[k]))
                        elif isinstance(d[k], (datetime.date)):
                            self.controles[k].setText(d[k].strftime('%d/%m/%Y'))
                        else:
                            self.controles[k].setText(d[k].strip() if d[k] else '')
                    elif isinstance(self.controles[k], (QCheckBox, CheckBox)):
                        if EsVerdadero(d[k]) or d[k]:
                            self.controles[k].setChecked(True)
                        else:
                            self.controles[k].setChecked(False)
                    elif isinstance(self.controles[k], QComboBox):
                        if isinstance(d[k], (bytes,)):
                            if EsVerdadero(self.cursor[k]):
                                self.controles[k].setCurrentIndex(self.controles[k].findData('Si'))
                            else:
                                self.controles[k].setCurrentIndex(self.controles[k].findData('No'))
                        elif isinstance(d[k], (int, decimal.Decimal, float)):
                            self.controles[k].setCurrentIndex(self.controles[k].findData(d[k]))
                        else:
                            self.controles[k].setCurrentText(d[k] if d[k] else '')
                    elif isinstance(self.controles[k], (Fecha)):
                        if self.controles[k]:
                            self.controles[k].setText(d[k])
                    elif isinstance(self.controles[k], Spinner):
                        self.controles[k].setText(d[k])
                    else:
                        if d[k] is None:
                            self.controles[k].setText('')
                        else:
                            self.controles[k].setText(d[k].strip())

                    self.controles[k].setStyleSheet("background-color: white")

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
        if 'layout' in kwargs:
            boxlayout.addLayout(lineEditNombre)
        else:
            boxlayout.addWidget(lineEditNombre)
        if 'enabled' in kwargs:
            lineEditNombre.setEnabled(kwargs['enabled'])

        if 'control' in kwargs and isinstance(kwargs['control'], ValidaConTexto):
            self.controles[nombre] = kwargs['control'].lineEditCodigo
        else:
            self.controles[nombre] = lineEditNombre

        if lAgrega:
            self.verticalLayoutDatos.addLayout(boxlayout)
        return boxlayout

    def btnCancelarClicked(self):
        self.tabWidget.setCurrentIndex(0)
        self.tabDetalle.setEnabled(False)
        self.ArmaTabla()

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        # data = self.model.get_by_id(self.controles[self.campoClave.column_name].text())
        # data.nombre = self.controles['nombre'].text()
        self.tabWidget.setCurrentIndex(0)
        self.tabDetalle.setEnabled(False)
        self.ArmaTabla()
        # self.btnCancelarClicked()

    def ArmaCarga(self):
        pass

    def Agrega(self):
        self.tipo = 'A'
        for x in self.controles:
            if self.autoincremental:
                if x in [self.campoClave.column_name,
                         self.campoClave.verbose_name,
                         self.campoClave.name]:
                    self.controles[x].setEnabled(False)
            self.controles[x].setText('')
            self.controles[x].setStyleSheet("background-color: white")
        self.tabDetalle.setEnabled(True)
        self.tabWidget.setCurrentIndex(1)
        if self.campoFoco:
            self.campoFoco.setFocus()
        self.PostClickAgrega()

    def PostClickModifica(self):
        pass

    def AgregaBotonesDatos(self):
        pass

    def PostClickAgrega(self):
        pass

    def DevuelveColor(self, item):
        return QColor(255, 255, 255)
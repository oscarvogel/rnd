# coding=utf-8
import datetime
import decimal
import logging

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QTabWidget, QWidget, QGridLayout, QHBoxLayout, QLineEdit, QCheckBox, QComboBox, \
    QApplication, QMessageBox, QSplitter, QSizePolicy, QScrollArea, QFrame, QToolButton, QMenu, QAction, QAbstractButton, \
    QAbstractItemView, QHeaderView

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

try:
    from modelos.ModeloBase import reconnect_if_needed
except ModuleNotFoundError:
    def reconnect_if_needed(func):
        return func


class ABM(VistaBase):
    """Vista base para pantallas de gestión tipo listado + ficha.

    Mantiene compatibilidad con los ABM existentes, pero incorpora mejoras de
    usabilidad: títulos más claros, búsqueda con limpiar, resumen de registros,
    estado visual de alta/modificación, conexiones protegidas, atajos de
    teclado, distribución responsive opcional y modo split listado/ficha.
    """

    controles = {}
    model = None
    tipo = "A"
    camposAMostrar = []
    condicion = None
    limite = 100
    ordenBusqueda = None
    campoClave = None
    autoincremental = True
    campoFoco = None
    colBoton = 0
    titulo = None
    permiteagregar = True
    idtabla = 0
    dynamicBackColor = None
    data = ""
    autoConectaWidgets = True
    agrupar_botones_adicionales = "auto"

    # Contenedor principal. `tabs` conserva el comportamiento histórico.
    # `split` muestra listado y ficha al mismo tiempo.
    view_mode = "tabs"
    split_sizes = (520, 420)

    # Layout de ficha. Por defecto se mantiene compatible con el armado histórico.
    # Valores soportados: single, two_columns, auto.
    form_layout_mode = "single"
    form_columns = 1
    form_auto_columns_threshold = 8
    form_field_min_width = 220
    form_field_spacing = 16
    form_panel_margins = (22, 18, 22, 18)

    def __init__(self, *args, **kwargs):
        VistaBase.__init__(self, *args, **kwargs)
        self.controles = {}
        self._widgets_conectados = False
        self._ultima_cantidad_registros = 0
        self._form_row = 0
        self._form_column = 0
        self._form_fields_count = 0
        self.initUi()

    def _nombre_pantalla(self):
        if self.titulo:
            return self.titulo
        if self.model:
            return self.model._meta.table_name.title()
        return "Registros"

    def _titulo_gestion(self):
        return "Gestión de {}".format(self._nombre_pantalla())

    def _usa_modo_split(self):
        return self.view_mode == "split"

    def _usa_layout_responsive(self):
        return self.form_layout_mode in ("auto", "two_columns")

    def _columnas_formulario(self):
        if self.form_layout_mode == "two_columns":
            return max(1, int(self.form_columns or 2))
        if self.form_layout_mode == "auto":
            if self._form_fields_count >= self.form_auto_columns_threshold:
                return max(2, int(self.form_columns or 2))
        return 1

    def _agrega_layout_campo(self, boxlayout):
        if not self._usa_layout_responsive():
            self.verticalLayoutDatos.addLayout(boxlayout)
            return

        columnas = self._columnas_formulario()
        if columnas <= 1:
            self.verticalLayoutDatos.addLayout(boxlayout)
            return

        if not hasattr(self, 'gridLayoutFormulario'):
            self.gridLayoutFormulario = QGridLayout()
            self.gridLayoutFormulario.setObjectName("gridLayoutFormulario")
            self.gridLayoutFormulario.setContentsMargins(0, 6, 0, 6)
            self.gridLayoutFormulario.setHorizontalSpacing(self.form_field_spacing)
            self.gridLayoutFormulario.setVerticalSpacing(14)
            for column in range(columnas):
                self.gridLayoutFormulario.setColumnStretch(column, 1)
            self.verticalLayoutDatos.addLayout(self.gridLayoutFormulario)

        self.gridLayoutFormulario.addLayout(boxlayout, self._form_row, self._form_column, 1, 1)
        self._form_column += 1
        if self._form_column >= columnas:
            self._form_column = 0
            self._form_row += 1

    def _configura_control_formulario(self, control):
        if not hasattr(control, 'setSizePolicy'):
            return
        control.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if hasattr(control, 'setMinimumWidth'):
            control.setMinimumWidth(int(self.form_field_min_width))

    def _configura_boton_formulario(self, boton):
        boton.setMinimumHeight(36)
        boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _configura_boton_toolbar(self, boton, ancho_minimo=104):
        boton.setMinimumHeight(36)
        boton.setMinimumWidth(ancho_minimo)
        boton.setIconSize(QSize(20, 20))
        boton.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        boton.setCursor(Qt.PointingHandCursor)
        if hasattr(boton, "setAutoDefault"):
            boton.setAutoDefault(False)
        if hasattr(boton, "setDefault"):
            boton.setDefault(False)

    def _configura_tabla_listado(self):
        self.tableView.setAlternatingRowColors(True)
        self.tableView.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tableView.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tableView.setShowGrid(False)
        self.tableView.setWordWrap(False)
        self.tableView.setCornerButtonEnabled(False)
        self.tableView.setStyleSheet(
            """
            QTableWidget#tableView {
                background: #ffffff;
                alternate-background-color: #f8fbff;
                selection-background-color: #dbeafe;
                selection-color: #111827;
                border: 1px solid #d8e0ea;
                border-radius: 8px;
                gridline-color: #eef2f7;
            }
            QTableWidget#tableView::item {
                border: none;
                padding: 6px 8px;
            }
            QTableWidget#tableView::item:selected {
                background: #dbeafe;
                color: #111827;
            }
            QHeaderView::section {
                background: #f8fafc;
                color: #374151;
                border: none;
                border-bottom: 1px solid #e5e7eb;
                padding: 8px 10px;
                font-weight: bold;
            }
            """
        )

        vertical_header = self.tableView.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setMinimumSectionSize(32)
        vertical_header.setDefaultSectionSize(34)

        horizontal_header = self.tableView.horizontalHeader()
        horizontal_header.setHighlightSections(False)
        horizontal_header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        horizontal_header.setMinimumSectionSize(90)
        horizontal_header.setSectionResizeMode(QHeaderView.Interactive)
        horizontal_header.setStretchLastSection(True)

    def _agrega_separador_toolbar(self, object_name):
        separator = QFrame(self.tabLista)
        separator.setObjectName(object_name)
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setFixedHeight(28)
        separator.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.horizontalLayout.addWidget(separator)
        return separator

    def _aplica_estilo_boton_fluent(self, boton, variante="secondary"):
        estilos = {
            "primary": (
                "background-color:#0f6cbd;color:white;border:1px solid #0f6cbd;"
                "border-radius:8px;padding:7px 14px;min-height:26px;font-weight:bold;"
            ),
            "danger": (
                "background-color:#fff7f7;color:#b91c1c;border:1px solid #fecaca;"
                "border-radius:8px;padding:7px 14px;min-height:26px;font-weight:bold;"
            ),
            "disabled_primary": (
                "background-color:#d8e4f2;color:#6b7b90;border:1px solid #d8e4f2;"
                "border-radius:8px;padding:7px 14px;min-height:26px;font-weight:bold;"
            ),
            "secondary": (
                "background-color:white;color:#111827;border:1px solid #cbd5e1;"
                "border-radius:8px;padding:7px 14px;min-height:26px;font-weight:bold;"
            ),
        }
        if hasattr(boton, "setAutoDefault"):
            boton.setAutoDefault(False)
        if hasattr(boton, "setDefault"):
            boton.setDefault(False)
        boton.setStyleSheet(estilos.get(variante, estilos["secondary"]))

    def _configura_contenedor_principal(self):
        if self._usa_modo_split():
            self.splitter = QSplitter(Qt.Horizontal)
            self.splitter.setObjectName("splitterABM")
            self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.splitter.addWidget(self.tabLista)
            self.splitter.addWidget(self.tabDetalle)
            self.splitter.setSizes(list(self.split_sizes))
            self.verticalLayout.addWidget(self.splitter)
        else:
            self.tabWidget = QTabWidget()
            self.tabWidget.addTab(self.tabLista, "Listado")
            self.tabWidget.addTab(self.tabDetalle, "Ficha")
            self.verticalLayout.addWidget(self.tabWidget)
        self.tabDetalle.setEnabled(False)

    def _mostrar_listado(self):
        if self._usa_modo_split():
            self.tabDetalle.setEnabled(False)
            if hasattr(self, 'btnAceptar'):
                self._aplica_estilo_boton_fluent(self.btnAceptar, "disabled_primary")
            self.tableView.setFocus()
        else:
            self.tabWidget.setCurrentIndex(0)
            self.tabDetalle.setEnabled(False)

    def _mostrar_ficha(self):
        self.tabDetalle.setEnabled(True)
        if hasattr(self, 'btnAceptar'):
            self._aplica_estilo_boton_fluent(self.btnAceptar, "primary")
        if self._usa_modo_split():
            self.tabDetalle.setFocus()
        else:
            self.tabWidget.setCurrentIndex(1)

    def _esta_en_listado(self):
        if self._usa_modo_split():
            return True
        return self.tabWidget.currentWidget() == self.tabLista

    def _esta_en_ficha(self):
        if self._usa_modo_split():
            return self.tabDetalle.isEnabled()
        return self.tabWidget.currentWidget() == self.tabDetalle and self.tabDetalle.isEnabled()

    def _widgets_layout(self, layout):
        widgets = []
        for index in range(layout.count()):
            item = layout.itemAt(index)
            widget = item.widget() if item else None
            if widget is not None:
                widgets.append(widget)
        return widgets

    def _botones_agrupables(self, widgets):
        botones = []
        for widget in widgets:
            if isinstance(widget, QAbstractButton) and hasattr(widget, "click"):
                botones.append(widget)
        return botones

    def _debe_agrupar_botones_adicionales(self, botones):
        modo = getattr(self, "agrupar_botones_adicionales", "auto")
        if modo == "never":
            return False
        if modo == "always":
            return len(botones) >= 1
        return len(botones) > 1

    def _accion_desde_boton_adicional(self, boton):
        accion = QAction(boton.icon(), boton.text(), self)
        accion.setToolTip(boton.toolTip())
        accion.setEnabled(boton.isEnabled())
        accion.triggered.connect(lambda checked=False, boton=boton: boton.click())
        return accion

    def _agrupa_botones_adicionales(self, botones):
        if not self._debe_agrupar_botones_adicionales(botones):
            return

        indice_insercion = 0
        for index in range(self.horizontalLayout.count()):
            item = self.horizontalLayout.itemAt(index)
            widget = item.widget() if item else None
            if widget in botones:
                indice_insercion = index
                break

        self.btnMasAcciones = QToolButton(self.tabLista)
        self.btnMasAcciones.setObjectName("btnMasAcciones")
        self.btnMasAcciones.setText("Más acciones")
        self.btnMasAcciones.setPopupMode(QToolButton.InstantPopup)
        self.btnMasAcciones.setToolTip("Acciones adicionales")
        self.btnMasAcciones.setCursor(Qt.PointingHandCursor)
        self._configura_boton_toolbar(self.btnMasAcciones)
        self._aplica_estilo_boton_fluent(self.btnMasAcciones)

        self.menuMasAcciones = QMenu(self.btnMasAcciones)
        self.menuMasAcciones.setObjectName("menuMasAcciones")
        for boton in botones:
            self.menuMasAcciones.addAction(self._accion_desde_boton_adicional(boton))
            self.horizontalLayout.removeWidget(boton)
            boton.hide()
        self.btnMasAcciones.setMenu(self.menuMasAcciones)
        self.horizontalLayout.insertWidget(indice_insercion, self.btnMasAcciones)

    def ActualizaEstado(self, texto=None):
        if not hasattr(self, 'lblEstado'):
            return
        if texto:
            self.lblEstado.setText(texto)
            return
        if self.tipo == 'M':
            self.lblEstado.setText("Editando registro {}".format(self.idtabla or "seleccionado"))
        else:
            self.lblEstado.setText("Nuevo registro")

    def ActualizaResumen(self, mostrados=0, total=0):
        if not hasattr(self, 'lblResumen'):
            return
        if total > self.limite:
            self.lblResumen.setText("Mostrando {} de {} registros".format(mostrados, total))
        else:
            self.lblResumen.setText("{} registro(s) encontrado(s)".format(mostrados))

    @inicializar_y_capturar_excepciones
    def initUi(self, *args, **kwargs):
        self.resize(906, 584)
        self.setWindowTitle(self._titulo_gestion())

        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setContentsMargins(18, 18, 18, 14)
        self.verticalLayout.setSpacing(12)

        self.lblTitulo = Etiqueta(tamanio=15, texto=self._titulo_gestion())
        self.lblTitulo.setObjectName("tituloPantalla")
        self.lblTitulo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.verticalLayout.addWidget(self.lblTitulo)

        self.avance = Avance()
        self.avance.setVisible(False)
        self.verticalLayout.addWidget(self.avance)

        self.tabLista = QWidget()
        self.tabLista.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.gridLayout = QGridLayout(self.tabLista)
        self.gridLayout.setContentsMargins(18, 18, 18, 16)
        self.gridLayout.setHorizontalSpacing(10)
        self.gridLayout.setVerticalSpacing(12)
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setRowStretch(2, 1)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("toolbarABM")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setSpacing(10)

        widgets_antes_adicionales = self._widgets_layout(self.horizontalLayout)
        self.BotonesAdicionales()
        widgets_despues_adicionales = self._widgets_layout(self.horizontalLayout)
        widgets_adicionales = [
            widget for widget in widgets_despues_adicionales
            if widget not in widgets_antes_adicionales
        ]
        self._agrupa_botones_adicionales(self._botones_agrupables(widgets_adicionales))

        self.btnAgregar = Boton(self.tabLista, texto="&Agregar",
                                imagen=imagen("new.png"), tamanio=QSize(20, 20),
                                tooltip='Agregar nuevo registro (F2)', enabled=self.permiteagregar)
        self.btnAgregar.setObjectName("btnAgregar")
        self._configura_boton_toolbar(self.btnAgregar)
        self._aplica_estilo_boton_fluent(self.btnAgregar, "primary")
        self.horizontalLayout.addWidget(self.btnAgregar)

        self.btnEditar = Boton(self.tabLista, imagen=imagen('edit.png'), tamanio=QSize(20, 20),
                               tooltip='Modificar registro seleccionado (F4 o doble clic)', texto='Editar')
        self.btnEditar.setObjectName("btnEditar")
        self._configura_boton_toolbar(self.btnEditar)
        self._aplica_estilo_boton_fluent(self.btnEditar)
        self.horizontalLayout.addWidget(self.btnEditar)

        self.btnBorrar = Boton(self.tabLista, imagen=imagen('delete.png'), tamanio=QSize(20, 20),
                               tooltip='Borrar registro seleccionado (Delete)', texto='Borrar')
        self.btnBorrar.setObjectName("btnBorrar")
        self._configura_boton_toolbar(self.btnBorrar)
        self._aplica_estilo_boton_fluent(self.btnBorrar, "danger")
        self.horizontalLayout.addWidget(self.btnBorrar)

        self._agrega_separador_toolbar("separatorToolbarABMExport")

        self.btnExcel = Boton(self.tabLista, imagen=imagen("79354_excel_icon.png"), tamanio=QSize(20, 20),
                              tooltip='Exportar listado a Excel', texto='Excel')
        self.btnExcel.setObjectName("btnExcel")
        self._configura_boton_toolbar(self.btnExcel)
        self._aplica_estilo_boton_fluent(self.btnExcel)
        self.horizontalLayout.addWidget(self.btnExcel)

        self.horizontalLayout.addStretch()
        self._agrega_separador_toolbar("separatorToolbarABMCierre")

        self.btnCerrar = Boton(self.tabLista, imagen=imagen('close.png'), tamanio=QSize(20, 20),
                               tooltip='Cerrar pantalla', texto='Cerrar')
        self.btnCerrar.setObjectName("btnCerrar")
        self._configura_boton_toolbar(self.btnCerrar)
        self._aplica_estilo_boton_fluent(self.btnCerrar)
        self.horizontalLayout.addWidget(self.btnCerrar)
        self.gridLayout.addLayout(self.horizontalLayout, 0, 0, 1, 2)

        self.lineEditBusqueda = EntradaTexto(
            self.tabLista,
            placeholderText="Buscar por nombre, código o dato visible..."
        )
        self.lineEditBusqueda.setObjectName("lineEditBusqueda")
        self.gridLayout.addWidget(self.lineEditBusqueda, 1, 0, 1, 1)

        self.btnLimpiarBusqueda = Boton(
            self.tabLista,
            texto="Limpiar",
            imagen=imagen('close.png'),
            tamanio=QSize(18, 18),
            tooltip="Limpiar búsqueda"
        )
        self.btnLimpiarBusqueda.setObjectName("btnLimpiarBusqueda")
        self._aplica_estilo_boton_fluent(self.btnLimpiarBusqueda)
        self.gridLayout.addWidget(self.btnLimpiarBusqueda, 1, 1, 1, 1)

        self.tableView = Grilla(self.tabLista)
        self.tableView.setObjectName("tableView")
        self.tableView.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tableView.enabled = True
        self.tableView.cabeceras = [
            x.verbose_name if x.verbose_name else x.column_name.capitalize()
            for x in self.camposAMostrar
        ]
        self.tableView.ArmaCabeceras()
        self._configura_tabla_listado()
        self.gridLayout.addWidget(self.tableView, 2, 0, 1, 2)

        self.lblResumen = Etiqueta(texto="Sin registros cargados")
        self.lblResumen.setObjectName("lblResumen")
        self.gridLayout.addWidget(self.lblResumen, 3, 0, 1, 2)

        self.tabDetalle = QWidget()
        self.tabDetalle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.ArmaDatos()
        self._configura_contenedor_principal()
        self.ArmaTabla()
        if self.autoConectaWidgets:
            self.ConectaWidgets()

    def BotonesAdicionales(self):
        pass

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def ArmaTabla(self, *args, **kwargs):
        self.tableView.setRowCount(0)
        self.avance.setVisible(True)
        sorting_enabled = self.tableView.isSortingEnabled()
        self.tableView.setSortingEnabled(False)
        try:
            if self.data:
                data = self.data
            else:
                if not self.model:
                    self.ActualizaResumen(0, 0)
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
                avance += 1
                if total:
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
                                color = QColor(255, 255, 255)
                    else:
                        color = self.DevuelveColor(d)
                self.tableView.AgregaItem(item, backgroundColor=color)
                self._guarda_id_fila_tabla(d)
            self._ultima_cantidad_registros = avance
            self.ActualizaResumen(avance, total)
        finally:
            self.tableView.setSortingEnabled(sorting_enabled)
            self.avance.setVisible(False)

    def _guarda_id_fila_tabla(self, data):
        if not self.campoClave:
            return
        record_id = data.get(self.campoClave.name)
        if record_id is None:
            record_id = data.get(self.campoClave.column_name)
        if record_id is None:
            return
        fila = self.tableView.rowCount() - 1
        for col in range(self.tableView.columnCount()):
            item = self.tableView.item(fila, col)
            if item is not None:
                item.setData(Qt.UserRole, record_id)

    def _id_registro_seleccionado(self):
        fila = self.tableView.currentRow()
        if fila == -1:
            return None
        item = self.tableView.item(fila, 0)
        if item is not None:
            record_id = item.data(Qt.UserRole)
            if record_id is not None:
                return record_id
        if not self.campoClave:
            return None
        posibles_columnas = [
            self.campoClave.verbose_name,
            self.campoClave.column_name.capitalize(),
            self.campoClave.column_name,
            self.campoClave.name,
        ]
        for columna in posibles_columnas:
            if columna and columna in self.tableView.cabeceras:
                return self.tableView.ObtenerItem(fila=fila, col=columna)
        return None

    def ArmaBusqueda(self, data):
        if self.ordenBusqueda:
            texto = self.lineEditBusqueda.text()
            if isinstance(self.ordenBusqueda, list):
                cond = None
                for campo in self.ordenBusqueda:
                    expr = campo.contains(texto)
                    cond = expr if cond is None else cond | expr
                data = data.where(cond)
            else:
                data = data.where(self.ordenBusqueda.contains(texto))
        else:
            Ventanas.showAlert("Sistema", "No hay campos configurados para realizar la búsqueda")
        return data

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def ArmaDatos(self, *args, **kwargs):
        self.layoutDetalle = QVBoxLayout(self.tabDetalle)
        self.layoutDetalle.setContentsMargins(0, 0, 0, 0)
        self.layoutDetalle.setSpacing(0)

        self.scrollDetalle = QScrollArea(self.tabDetalle)
        self.scrollDetalle.setObjectName("scrollDetalleABM")
        self.scrollDetalle.setWidgetResizable(True)
        self.scrollDetalle.setFrameShape(QFrame.NoFrame)
        self.layoutDetalle.addWidget(self.scrollDetalle)

        self.formPanel = QFrame()
        self.formPanel.setObjectName("formPanelABM")
        self.formPanel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.scrollDetalle.setWidget(self.formPanel)

        self.verticalLayoutDatos = QVBoxLayout(self.formPanel)
        self.verticalLayoutDatos.setObjectName("verticalLayoutDatos")
        self.verticalLayoutDatos.setContentsMargins(*self.form_panel_margins)
        self.verticalLayoutDatos.setSpacing(14)

        self.lblEstado = Etiqueta(texto="Seleccione un registro o agregue uno nuevo")
        self.lblEstado.setObjectName("lblEstado")
        self.lblEstado.setWordWrap(True)
        self.verticalLayoutDatos.addWidget(self.lblEstado)

        self.ArmaCarga()
        self.colBoton = 0

        self.grdBotones = QGridLayout()
        self.grdBotones.setObjectName("grdBotones")
        self.grdBotones.setContentsMargins(0, 10, 0, 0)
        self.grdBotones.setHorizontalSpacing(10)
        self.AgregaBotonesDatos()

        self.btnAceptar = Boton(self.tabDetalle, texto='Guardar', imagen=imagen('save.png'), tamanio=QSize(32, 32),
                                tooltip="Guardar cambios (F10)")
        self.btnAceptar.setObjectName("btnAceptar")
        self._configura_boton_formulario(self.btnAceptar)
        self._aplica_estilo_boton_fluent(self.btnAceptar, "disabled_primary")
        self.grdBotones.addWidget(self.btnAceptar, 0, self.colBoton, 1, 1)
        self.grdBotones.setColumnStretch(self.colBoton, 1)

        self.colBoton += 1
        self.btnCancelar = Boton(self.tabDetalle, texto='Cancelar', imagen=imagen('close.png'), tamanio=QSize(32, 32),
                                 tooltip="Cancelar y volver al listado (Esc)")
        self.btnCancelar.setObjectName("btnCancelar")
        self._configura_boton_formulario(self.btnCancelar)
        self._aplica_estilo_boton_fluent(self.btnCancelar)
        self.grdBotones.addWidget(self.btnCancelar, 0, self.colBoton, 1, 1)
        self.grdBotones.setColumnStretch(self.colBoton, 1)
        self.verticalLayoutDatos.addLayout(self.grdBotones)
        self.btnCancelar.clicked.connect(self.btnCancelarClicked)
        self.btnAceptar.clicked.connect(self.btnAceptarClicked)
        self.verticalLayoutDatos.addStretch(1)

    def Busqueda(self):
        self.ArmaTabla()

    def LimpiarBusqueda(self):
        self.lineEditBusqueda.clear()
        self.ArmaTabla()
        self.lineEditBusqueda.setFocus()

    def ConectaWidgets(self):
        if self._widgets_conectados:
            return
        self.lineEditBusqueda.textChanged.connect(self.Busqueda)
        self.btnLimpiarBusqueda.clicked.connect(self.LimpiarBusqueda)
        self.btnCerrar.clicked.connect(self.cerrarformulario)
        self.btnBorrar.clicked.connect(self.Borrar)
        self.btnEditar.clicked.connect(self.Modifica)
        self.btnAgregar.clicked.connect(self.Agrega)
        self._conecta_doble_click_grilla()
        self._widgets_conectados = True

    def _conecta_doble_click_grilla(self):
        try:
            self.tableView.doubleClicked.connect(self.Modifica)
        except AttributeError:
            if hasattr(self.tableView, 'cellDoubleClicked'):
                self.tableView.cellDoubleClicked.connect(lambda *_: self.Modifica())

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key_F2:
            self.Agrega()
            return
        if key == Qt.Key_F3:
            self.lineEditBusqueda.setFocus()
            self.lineEditBusqueda.selectAll()
            return
        if key == Qt.Key_F4:
            self.Modifica()
            return
        if key == Qt.Key_Delete:
            if self._esta_en_listado():
                self.Borrar()
                return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            if self._esta_en_listado():
                self.Modifica()
                return
        if key == Qt.Key_F10:
            if self._esta_en_ficha():
                self.btnAceptarClicked()
                return
        if key == Qt.Key_Escape:
            if self._esta_en_ficha():
                self.btnCancelarClicked()
            else:
                self.cerrarformulario()
            return
        super().keyPressEvent(event)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def Borrar(self, *args, **kwargs):
        if not self.tableView.currentRow() != -1:
            Ventanas.showAlert("Sistema", "Seleccione un registro para borrar")
            return

        if not self.campoClave:
            Ventanas.showAlert("Sistema", "No se pudo identificar el registro seleccionado")
            return

        if Ventanas.showConfirmation("Sistema", "¿Desea borrar el registro seleccionado?") == QMessageBox.Ok:
            id = self._id_registro_seleccionado()
            if id is None:
                Ventanas.showAlert("Sistema", "No se pudo identificar el registro seleccionado")
                return
            data = self.model.get_by_id(id)
            data.delete_instance()
            self.ArmaTabla()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def Modifica(self, *args, **kwargs):
        self.tipo = 'M'
        if not self.tableView.currentRow() != -1:
            Ventanas.showAlert("Sistema", "Seleccione un registro para editar")
            return

        if not self.campoClave:
            Ventanas.showAlert("Sistema", "No se pudo identificar el registro seleccionado")
            return

        id = self._id_registro_seleccionado()
        if id is None:
            Ventanas.showAlert("Sistema", "No se pudo identificar el registro seleccionado")
            return
        if isinstance(id, str):
            id = id.replace('.', '')
        self.idtabla = id

        if self.campoClave.field_type in ['VARCHAR']:
            data = self.model.select().where(self.campoClave == id).dicts()
        elif self.campoClave.field_type in ['AUTO', 'INTEGER']:
            data = self.model.select().where(self.campoClave == int(id)).dicts()
        else:
            data = self.model.select().where(self.campoClave == id).dicts()
        self._mostrar_ficha()
        self.ActualizaEstado()
        self.CargaDatos(data)
        if self.campoFoco:
            self.campoFoco.setFocus()
        self.PostClickModifica()

    def CargaDatos(self, data=None):
        if not data:
            return
        for d in data:
            logging.debug("%s", d)
            for k in d:
                if k in self.controles:
                    if k == self.campoClave.name:
                        self.controles[k].setEnabled(False)
                    if isinstance(self.controles[k], QLineEdit):
                        if isinstance(d[k], (int, decimal.Decimal, float)):
                            self.controles[k].setText(str(d[k]))
                        elif isinstance(d[k], datetime.date):
                            self.controles[k].setText(d[k].strftime('%d/%m/%Y'))
                        else:
                            self.controles[k].setText(d[k].strip() if d[k] else '')
                    elif isinstance(self.controles[k], (QCheckBox, CheckBox)):
                        self.controles[k].setChecked(bool(EsVerdadero(d[k]) or d[k]))
                    elif isinstance(self.controles[k], QComboBox):
                        if isinstance(d[k], bytes):
                            cursor = getattr(self, 'cursor', {})
                            if EsVerdadero(cursor.get(k)):
                                self.controles[k].setCurrentIndex(self.controles[k].findData('Si'))
                            else:
                                self.controles[k].setCurrentIndex(self.controles[k].findData('No'))
                        elif isinstance(d[k], (int, decimal.Decimal, float)):
                            self.controles[k].setCurrentIndex(self.controles[k].findData(d[k]))
                        else:
                            self.controles[k].setCurrentText(d[k] if d[k] else '')
                    elif isinstance(self.controles[k], Fecha):
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
            boxlayout = QVBoxLayout() if self._usa_layout_responsive() else QHBoxLayout()
            lAgrega = True
        else:
            lAgrega = False

        if not texto:
            if isinstance(nombre, str):
                texto = nombre.capitalize()
            else:
                if 'control' not in kwargs:
                    if nombre.field_type in ['DATE']:
                        kwargs['control'] = FechaLine()
                texto = nombre.verbose_name if nombre.verbose_name else nombre.name.capitalize()

        if not isinstance(nombre, str):
            nombre = nombre.name

        labelNombre = Etiqueta(texto=texto)
        labelNombre.setObjectName("labelNombre")
        if self._usa_layout_responsive():
            labelNombre.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
            boxlayout.setContentsMargins(0, 0, 0, 0)
            boxlayout.setSpacing(5)
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
        if self._usa_layout_responsive():
            self._configura_control_formulario(lineEditNombre)
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
            self._form_fields_count += 1
            self._agrega_layout_campo(boxlayout)
        return boxlayout

    def btnCancelarClicked(self):
        self._mostrar_listado()
        self.ActualizaEstado("Seleccione un registro o agregue uno nuevo")

    @inicializar_y_capturar_excepciones
    def btnAceptarClicked(self, *args, **kwargs):
        self._mostrar_listado()
        self.ActualizaEstado("Seleccione un registro o agregue uno nuevo")
        self.ArmaTabla()

    def ArmaCarga(self):
        pass

    def Agrega(self):
        self.tipo = 'A'
        for x in self.controles:
            if self.autoincremental and self.campoClave:
                if x in [self.campoClave.column_name,
                         self.campoClave.verbose_name,
                         self.campoClave.name]:
                    self.controles[x].setEnabled(False)
            self.controles[x].setText('')
            self.controles[x].setStyleSheet("background-color: white")
        self._mostrar_ficha()
        self.ActualizaEstado()
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

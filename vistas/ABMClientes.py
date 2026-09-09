from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit, QComboBox,
    QCheckBox, QTextEdit, QFormLayout, QListWidget, QAbstractItemView, QFrame,
)
from modelos.Clientes import Cliente, cboRutaReparto
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.libs.vistas.ABM import ABM
from pyqt5libs.pyqt5libs.EntradaTexto import TextEdit
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones


class ABMClientesView(ABM):
    model = Cliente
    camposAMostrar = [Cliente.id, Cliente.razon_social, Cliente.direccion, Cliente.telefono, Cliente.cuit, Cliente.contacto, Cliente.activo]
    ordenBusqueda = [Cliente.razon_social]
    campoClave = Cliente.id
    titulo = "Tabla de Clientes"
    autoincremental = True
    dynamicBackColor = {Cliente.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}

    def __init__(self, *args, **kwargs):
        self.on_cargar_lugares = None
        super().__init__(*args, **kwargs)
        self._ajustar_ficha_cliente()

    def _ajustar_ficha_cliente(self):
        """Mantiene las acciones visibles y compacta la ficha de clientes.

        El ABM base usa scroll para formularios largos. En clientes eso dejaba
        Guardar/Cancelar fuera de pantalla y empujaba Lugares de entrega hacia
        abajo. Dejamos el scroll solo para el contenido y fijamos las acciones
        al pie de la ficha.
        """
        self.resize(max(self.width(), 1060), max(self.height(), 720))

        observaciones = self.controles.get(Cliente.observaciones.name)
        if observaciones is not None:
            observaciones.setMinimumHeight(80)
            observaciones.setMaximumHeight(105)

        if hasattr(self, "grp_lugares"):
            self.grp_lugares.setMinimumHeight(250)

        if hasattr(self, "scrollDetalle"):
            self.scrollDetalle.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            self.scrollDetalle.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        if not all(hasattr(self, attr) for attr in (
            "verticalLayoutDatos", "grdBotones", "layoutDetalle", "tabDetalle"
        )):
            return

        # Sacar Guardar/Cancelar del contenido desplazable y dejarlos siempre
        # visibles en un pie fijo.
        self.verticalLayoutDatos.removeItem(self.grdBotones)
        self.grdBotones.setParent(None)

        self.footerFicha = QFrame(self.tabDetalle)
        self.footerFicha.setObjectName("footerFichaClientes")
        self.footerFicha.setStyleSheet(
            "QFrame#footerFichaClientes {"
            "background:#ffffff; border-top:1px solid #e5e7eb;"
            "}"
        )
        footer_layout = QVBoxLayout(self.footerFicha)
        footer_layout.setContentsMargins(22, 10, 22, 12)
        footer_layout.addLayout(self.grdBotones)
        self.layoutDetalle.addWidget(self.footerFicha)
        
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        layout_codigo = self.ArmaEntrada(Cliente.id)
        self.ArmaEntrada(Cliente.razon_social, layout_codigo)
        direccion = self.ArmaEntrada(Cliente.direccion)
        self.ArmaEntrada(Cliente.telefono, boxlayout=direccion)
        self.ArmaEntrada(Cliente.cuit, boxlayout=direccion)
        contacto = self.ArmaEntrada(Cliente.contacto)
        self.ArmaEntrada(Cliente.ruta_reparto, boxlayout=contacto, control=cboRutaReparto())
        self.ArmaEntrada(Cliente.observaciones, control=TextEdit())
        self._arma_lugares_entrega()

    def _arma_lugares_entrega(self):
        self.grp_lugares = QGroupBox("Lugares de entrega")
        layout = QVBoxLayout(self.grp_lugares)

        self.lbl_lugares_ayuda = QLabel(
            "Un cliente puede tener uno o varios destinos. La dirección y ruta operativa se toman del lugar seleccionado."
        )
        self.lbl_lugares_ayuda.setWordWrap(True)
        layout.addWidget(self.lbl_lugares_ayuda)

        self.grilla_lugares = Grilla()
        self.grilla_lugares.ArmaCabeceras([
            "Nombre / Referencia", "Dirección", "Localidad", "Ruta de Reparto",
            "Principal", "Activo", "ID",
        ])
        self.grilla_lugares.permiteagregar = False
        self.grilla_lugares.setMinimumHeight(150)
        layout.addWidget(self.grilla_lugares)

        botones = QHBoxLayout()
        self.btn_lugar_agregar = self.CreaBoton("Agregar", imagen_str="new.png")
        self.btn_lugar_editar = self.CreaBoton("Editar", imagen_str="edit.png")
        self.btn_lugar_borrar = self.CreaBoton("Borrar", imagen_str="delete.png")
        botones.addWidget(self.btn_lugar_agregar)
        botones.addWidget(self.btn_lugar_editar)
        botones.addWidget(self.btn_lugar_borrar)
        botones.addStretch(1)
        layout.addLayout(botones)

        self.verticalLayoutDatos.addWidget(self.grp_lugares)
        self.habilitar_lugares(False)

    def habilitar_lugares(self, habilitado):
        if hasattr(self, "grp_lugares"):
            self.grp_lugares.setEnabled(bool(habilitado))

    def cargar_lugares(self, filas):
        self.grilla_lugares.limpiarGrilla()
        for fila in filas:
            self.grilla_lugares.AgregaItem(list(fila))
        self.grilla_lugares.resizeColumnsToContents()

    @inicializar_y_capturar_excepciones
    def PostClickModifica(self):
        self.habilitar_lugares(bool(self.idtabla))
        if callable(self.on_cargar_lugares):
            self.on_cargar_lugares()

    @inicializar_y_capturar_excepciones
    def PostClickAgrega(self):
        self.habilitar_lugares(False)
        self.cargar_lugares([])
    
    @inicializar_y_capturar_excepciones
    def BotonesAdicionales(self):
        self.btn_codigo = self.CreaBoton(texto="Codigo", imagen_str="proveedor.png")
        self.btn_consolidar = self.CreaBoton(texto="Consolidar", imagen_str="proveedor.png")
        self.horizontalLayout.addWidget(self.btn_codigo)
        self.horizontalLayout.addWidget(self.btn_consolidar)


class LugarEntregaView(VistaBase):
    """Formulario compacto para alta/modificación de un destino del cliente."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi(self)

    def initUi(self, parent):
        self.resize(620, 460)
        self.setWindowTitle("Lugar de entrega")
        layout_ppal = QVBoxLayout(parent)
        form = QFormLayout()

        self.txt_nombre = QLineEdit()
        self.txt_direccion = QLineEdit()
        self.cbo_localidad = QComboBox()
        self.cbo_ruta = QComboBox()
        self.chk_principal = QCheckBox("Lugar principal")
        self.chk_activo = QCheckBox("Activo")
        self.chk_activo.setChecked(True)
        self.txt_observaciones = QTextEdit()
        self.txt_observaciones.setMaximumHeight(100)

        form.addRow("Nombre / Referencia *", self.txt_nombre)
        form.addRow("Dirección", self.txt_direccion)
        form.addRow("Localidad", self.cbo_localidad)
        form.addRow("Ruta de Reparto", self.cbo_ruta)
        form.addRow("", self.chk_principal)
        form.addRow("", self.chk_activo)
        form.addRow("Observaciones", self.txt_observaciones)
        layout_ppal.addLayout(form)

        botones = QHBoxLayout()
        botones.addStretch(1)
        self.btn_cancelar = self.CreaBoton("Cancelar", imagen_str="close.png")
        self.btn_guardar = self.CreaBoton("Guardar", imagen_str="save.png")
        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)
        layout_ppal.addLayout(botones)

    def cargar_combobox(self, combo, elementos, seleccionado=None):
        combo.clear()
        combo.addItem("(Sin asignar)", None)
        for ident, texto in elementos:
            combo.addItem(texto, ident)
        if seleccionado is not None:
            idx = combo.findData(seleccionado)
            if idx >= 0:
                combo.setCurrentIndex(idx)

    def valores(self):
        return {
            "nombre": self.txt_nombre.text().strip(),
            "direccion": self.txt_direccion.text().strip() or None,
            "localidad": self.cbo_localidad.currentData(),
            "ruta_reparto": self.cbo_ruta.currentData(),
            "principal": self.chk_principal.isChecked(),
            "activo": self.chk_activo.isChecked(),
            "observaciones": self.txt_observaciones.toPlainText().strip() or None,
        }

    def cargar_registro(self, lugar):
        self.txt_nombre.setText(lugar.nombre or "")
        self.txt_direccion.setText(lugar.direccion or "")
        self.cargar_combobox(
            self.cbo_localidad,
            [(x.id, str(x)) for x in lugar.localidad._meta.model.select()] if False else [],
            lugar.localidad_id,
        )


class ConsolidacionClientesView(VistaBase):
    """Asistente seguro para fusionar clientes duplicados sin borrar históricos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi(self)

    def initUi(self, parent):
        self.resize(760, 620)
        self.setWindowTitle("Consolidar clientes")
        layout = QVBoxLayout(parent)

        ayuda = QLabel(
            "Seleccione el cliente que quedará activo y uno o más clientes origen. "
            "Primero ejecute Simular. Los clientes origen no se borran: quedan inactivos."
        )
        ayuda.setWordWrap(True)
        layout.addWidget(ayuda)

        form = QFormLayout()
        self.cbo_destino = QComboBox()
        form.addRow("Cliente destino", self.cbo_destino)
        layout.addLayout(form)

        layout.addWidget(QLabel("Clientes a consolidar"))
        self.lst_origenes = QListWidget()
        self.lst_origenes.setSelectionMode(QAbstractItemView.MultiSelection)
        layout.addWidget(self.lst_origenes)

        layout.addWidget(QLabel("Vista previa / simulación"))
        self.txt_resumen = QTextEdit()
        self.txt_resumen.setReadOnly(True)
        self.txt_resumen.setMinimumHeight(180)
        layout.addWidget(self.txt_resumen)

        botones = QHBoxLayout()
        self.btn_simular = self.CreaBoton("Simular", imagen_str="edit.png")
        self.btn_consolidar = self.CreaBoton("Consolidar", imagen_str="save.png")
        self.btn_consolidar.setEnabled(False)
        self.btn_cerrar = self.CreaBoton("Cerrar", imagen_str="close.png")
        botones.addWidget(self.btn_simular)
        botones.addWidget(self.btn_consolidar)
        botones.addStretch(1)
        botones.addWidget(self.btn_cerrar)
        layout.addLayout(botones)

    def cargar_clientes(self, clientes, destino_preseleccionado=None):
        self.cbo_destino.clear()
        self.lst_origenes.clear()
        for cliente_id, razon_social in clientes:
            self.cbo_destino.addItem(razon_social, cliente_id)
            self.lst_origenes.addItem("{} - {}".format(cliente_id, razon_social))
            item = self.lst_origenes.item(self.lst_origenes.count() - 1)
            item.setData(32, cliente_id)
        if destino_preseleccionado:
            idx = self.cbo_destino.findData(destino_preseleccionado)
            if idx >= 0:
                self.cbo_destino.setCurrentIndex(idx)

    def destino_id(self):
        return self.cbo_destino.currentData()

    def origenes_ids(self):
        return [item.data(32) for item in self.lst_origenes.selectedItems()]

    def mostrar_resumen(self, texto, habilitar=False):
        self.txt_resumen.setPlainText(texto or "")
        self.btn_consolidar.setEnabled(bool(habilitar))


class CodigoClienteProveedorView(VistaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi(self)
    
    def initUi(self, parent):
        self.resize(400, 300)
        layout_ppal = QVBoxLayout(parent)
        self.setWindowTitle("Códigos de Clientes y Proveedores")
        
        self.grilla = Grilla()
        self.grilla.ArmaCabeceras(["Razón Social", "Codigo Cliente", "ID", "id_proveedor"])
        self.grilla.columnasHabilitadas = [1,]
        self.grilla.permiteagregar = False
        layout_ppal.addWidget(self.grilla)
        
        layout_botones = QHBoxLayout()
        self.btn_guardar = self.CreaBoton("Guardar", imagen_str="save.png")
        self.btn_agregar = self.CreaBoton("Agregar", imagen_str="new.png")
        self.btn_borrar = self.CreaBoton("Borrar", imagen_str="delete.png")
        self.btn_salir = self.CreaBoton("Salir", imagen_str="close.png")
        layout_botones.addWidget(self.btn_guardar)
        layout_botones.addWidget(self.btn_agregar)
        layout_botones.addWidget(self.btn_borrar)
        layout_botones.addWidget(self.btn_salir)
        layout_ppal.addLayout(layout_botones)

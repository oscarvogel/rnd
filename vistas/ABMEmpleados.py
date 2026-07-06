# -*- coding: utf-8 -*-
from PyQt5.QtGui import QColor
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout
from modelos.Empleados import Empleado, ValidaConceptos, ValidaEmpleado
from modelos.Tablas import cboMonedas, cboUnidadNegocio
from pyqt5libs.libs.vistas.ABM import ABM
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.Checkbox import CheckBox
from pyqt5libs.pyqt5libs.Spinner import Spinner
from pyqt5libs.pyqt5libs.Botones import Boton, BotonCerrarFormulario
from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto, TextEdit
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha, FechaLine, RangoFechas
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.Spinner import Periodo
from pyqt5libs.pyqt5libs.utiles import FinMes, InicioMes, LeerIni, imagen, inicializar_y_capturar_excepciones


class ABMEmpleadosView(ABM):
    model = Empleado
    if LeerIni("basedatos") == "fg":
        camposAMostrar = [Empleado.id, Empleado.nombre]
        ordenBusqueda = [Empleado.nombre]
    else:
        camposAMostrar = [Empleado.id, Empleado.nombre, Empleado.apellido, Empleado.email, Empleado.telefono, Empleado.direccion, Empleado.fecha_contratacion, Empleado.fecha_nacimiento, Empleado.activo]
        ordenBusqueda = [Empleado.nombre, Empleado.apellido]

    campoClave = Empleado.id
    titulo = "Tabla de Empleados"
    autoincremental = True
    dynamicBackColor = {Empleado.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @inicializar_y_capturar_excepciones
    def ArmaCarga(self):
        layout_codigo = self.ArmaEntrada(Empleado.id)
        self.ArmaEntrada(Empleado.apellido, layout_codigo)
        self.ArmaEntrada(Empleado.nombre, layout_codigo)
        self.ArmaEntrada(Empleado.email)
        telefono = self.ArmaEntrada(Empleado.telefono)
        self.ArmaEntrada(Empleado.direccion, boxlayout=telefono)
        self.ArmaEntrada(Empleado.documento, boxlayout=telefono)
        fechas = self.ArmaEntrada(Empleado.fecha_contratacion, control=Fecha())
        self.ArmaEntrada(Empleado.fecha_nacimiento, boxlayout=fechas, control=Fecha())
        self.ArmaEntrada(Empleado.activo, boxlayout=fechas, control=CheckBox())
        self.ArmaEntrada(Empleado.porcentaje, boxlayout=fechas)
        self.ArmaEntrada(Empleado.observaciones, control=TextEdit())
        
    def BotonesAdicionales(self):
        self.btnFicha = Boton(texto="Ficha", imagen=imagen("iconfinder_cash_5736341.png"))
        self.btn_vencimientos = Boton(texto="Vencimientos", imagen=imagen("vencimiento.png"))
        self.btnFicha.setToolTip("Ficha de personal")
        self.horizontalLayout.addWidget(self.btnFicha)
        self.horizontalLayout.addWidget(self.btn_vencimientos)

class FichaPersonalView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Ficha de personal")
        self.resize(1000, 460)
        layoutPpal = QVBoxLayout(self)

        self.layoutFechas = RangoFechas()
        self.layoutFechas.desde_fecha.setFecha(InicioMes())
        self.layoutFechas.hasta_fecha.setFecha(FinMes())
        layoutPpal.addLayout(self.layoutFechas)

        self.gridFicha = Grilla(enabled=True)
        self.gridFicha.permiteagregar = False
        cabecera = [
            "Fecha", "Detalle", "Debe", "Haber", "Periodo", "Moneda", "Cambio", "ID"
        ]
        self.gridFicha.ArmaCabeceras(cabecera)
        layoutPpal.addWidget(self.gridFicha)

        layout_totales = QHBoxLayout()
        lbl_debe = Etiqueta(texto="Debe", tamanio=15)
        self.txt_debe = EntradaTexto(enabled=False, tamanio=15)
        lbl_haber = Etiqueta(texto="Haber", tamanio=15)
        self.txt_haber = EntradaTexto(enabled=False, tamanio=15)
        lbl_diferencia = Etiqueta(texto="Diferencia", tamanio=15)
        self.txt_diferencia = EntradaTexto(enabled=False, tamanio=15)
        layout_totales.addWidget(lbl_debe)
        layout_totales.addWidget(self.txt_debe)
        layout_totales.addWidget(lbl_haber)
        layout_totales.addWidget(self.txt_haber)
        layout_totales.addWidget(lbl_diferencia)
        layout_totales.addWidget(self.txt_diferencia)
        layoutPpal.addLayout(layout_totales)

        layoutBotones = QHBoxLayout()
        self.btnCargar = Boton(texto="Cargar", imagen=imagen("iconfinder_reload_46828.png"))
        self.btnExcel = Boton(texto="Excel", imagen=imagen("79354_excel_icon.png"))
        self.btnCerrar = BotonCerrarFormulario(imagen=imagen("exit_door_logout_out_icon.png"))
        self.btnAgregar = Boton(texto="Agregar", imagen=imagen("iconfinder_icon-81-document-add_314445.png"))
        self.btnBorrar = Boton(texto="Borrar", imagen=imagen("iconfinder_icon-27-trash-can_314282.png"))
        self.btnEditar = Boton(texto="Editar", imagen=imagen("edit.png"))
        self.btnImprimir = Boton(texto="Imprimir", imagen=imagen("printing.png"))
        self.btnCuotas = Boton(texto="Cuotas", imagen=imagen("cuotas_ficha.png"))
        layoutBotones.addWidget(self.btnCargar)
        layoutBotones.addWidget(self.btnAgregar)
        layoutBotones.addWidget(self.btnEditar)
        layoutBotones.addWidget(self.btnImprimir)
        layoutBotones.addWidget(self.btnExcel)
        layoutBotones.addWidget(self.btnCuotas)
        layoutBotones.addWidget(self.btnBorrar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)

class ModificaFichaEmpleadoView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Modifica datos Ficha Empleado")
        self.resize(630, 160)
        layoutPpal = QVBoxLayout(self)

        layoutDatos = QFormLayout()
        lblFecha = Etiqueta(texto="Fecha")
        self.textFecha = Fecha(fecha=0)
        layoutDatos.addRow(lblFecha, self.textFecha)

        lblPeriodo = Etiqueta(texto="Periodo")
        self.layoutPeriodo = Periodo()
        layoutDatos.addRow(lblPeriodo, self.layoutPeriodo)

        lblDetalle = Etiqueta(texto="Detalle")
        self.textDetalle = EntradaTexto()
        layoutDatos.addRow(lblDetalle, self.textDetalle)

        lblDebe = Etiqueta(texto="Debe")
        self.spnDebe = Spinner()
        layoutDatos.addRow(lblDebe, self.spnDebe)
        
        lblHaber = Etiqueta(texto="Haber")
        self.spnHaber = Spinner()
        layoutDatos.addRow(lblHaber, self.spnHaber)

        lblMonedas = Etiqueta(texto="Moneda")
        self.cboMonedas = cboMonedas()
        layoutDatos.addRow(lblMonedas, self.cboMonedas)

        lblCambio = Etiqueta(texto="Cambio")
        self.spnCambio = Spinner()
        layoutDatos.addRow(lblCambio, self.spnCambio)

        lblConcepto = Etiqueta(texto="Concepto liquidacion")
        self.layout_concepto = ValidaConceptos()
        layoutDatos.addRow(lblConcepto, self.layout_concepto)
        
        layoutPpal.addLayout(layoutDatos)

        layoutBotones = QHBoxLayout()
        self.btnGrabar = Boton(texto="Grabar", imagen=imagen("save.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnGrabar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)

class GeneraCuotasFichaView(VistaBase):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        layoutPpal = QVBoxLayout(self)
        self.resize(510, 160)
        self.setWindowTitle("Cuotas para ficha personal")

        layoutDatos = QFormLayout()
        lblPeriodo = Etiqueta(texto="Periodo inicio")
        self.layoutPeriodo = Periodo()
        layoutDatos.addRow(lblPeriodo, self.layoutPeriodo)

        lblDescripcion = Etiqueta(texto="Descripcion")
        self.textDescripcion = EntradaTexto()
        layoutDatos.addRow(lblDescripcion, self.textDescripcion)

        lblCantCuotas = Etiqueta(texto="Cantidad cuotas")
        self.spnCantidad = Spinner(decimales=0)
        layoutDatos.addRow(lblCantCuotas, self.spnCantidad)

        lblMonedas = Etiqueta(texto="Moneda")
        self.cboMonedas = cboMonedas()
        layoutDatos.addRow(lblMonedas, self.cboMonedas)

        lblCambio = Etiqueta(texto="Cambio")
        self.spnCambio = Spinner()
        layoutDatos.addRow(lblCambio, self.spnCambio)
        
        lblMontoTotal = Etiqueta(texto="Monto total")
        self.spnMontoTotal = Spinner()
        layoutDatos.addRow(lblMontoTotal, self.spnMontoTotal)

        layoutPpal.addLayout(layoutDatos)

        layoutBotones = QHBoxLayout()
        self.btnGrabar = Boton(texto="Grabar", imagen=imagen("save.png"))
        self.btnCerrar = BotonCerrarFormulario()
        layoutBotones.addWidget(self.btnGrabar)
        layoutBotones.addWidget(self.btnCerrar)
        layoutPpal.addLayout(layoutBotones)
        

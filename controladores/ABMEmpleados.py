import peewee
from PyQt5.QtWidgets import QMessageBox
from datetime import date
from controladores.ABMEquipos import VencimientosController
from controladores.Auditoria import AuditoriaController
from controladores.PyFPDF import PyFPDFController
from modelos.Empleados import Empleado, FichaPersonal
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.libs.controladores.ControladorBaseABM import ControladorBaseABM
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import FinMes, FormatoFecha, MesIdentificador, PeriodoAFecha, inicializar_y_capturar_excepciones, periodo_siguiente
from vistas.ABMEmpleados import ABMEmpleadosView, FichaPersonalView, GeneraCuotasFichaView, ModificaFichaEmpleadoView


class ABMEmpleadosController(ControladorBaseABM):
    model = Empleado
    campoclave = Empleado.id.name
    id_formulario = 662
    
    def __init__(self):
        super().__init__()
        self.view = ABMEmpleadosView()
        self.view.btnBorrar.setText("Baja")
        self.conectarWidgets()

    def conectarWidgets(self):
        super().conectarWidgets()
        self.view.btnFicha.clicked.connect(self.onClickBtnFicha)
        self.view.btn_vencimientos.clicked.connect(self.on_click_btn_vencimientos)

    def onClickBtnBorrar(self):
        """Realiza una baja lógica del empleado seleccionado."""
        if self.view.tableView.currentRow() == -1:
            Ventanas.showAlert("Sistema", "No se ha seleccionado ningun registro")
            return
        
        if Ventanas.showConfirmation("Sistema", "Deseas dar de baja el registro seleccionado?") == QMessageBox.Ok:
            empleado = self.model.get(self.model.id == self.view.tableView.ObtenerItemNumerico(
                fila=self.view.tableView.currentRow(), col=0
            ))
            empleado.activo = False  # Cambia el estado a inactivo
            empleado.fecha_baja = date.today()  # Establece la fecha de baja
            empleado.save()
            self.CargaDatos()
            
    def onClickBtnFicha(self):
        """Abre la ventana de ficha personal del empleado seleccionado."""
        if self.view.tableView.currentRow() == -1:
            Ventanas.showAlert("Sistema", "No se ha seleccionado ningun registro")
            return
        
        empleado_id = self.view.tableView.ObtenerItemNumerico(
            fila=self.view.tableView.currentRow(), col=0
        )
        
        controlador = FichaPersonalController()
        controlador.id_empleado = empleado_id
        controlador.CargaDatos()
        controlador.exec_()
    
    @inicializar_y_capturar_excepciones
    def onClickBtnAuditoria(self, *args, **kwargs):
        """Abre la ventana de ficha personal del empleado seleccionado."""
        if self.view.tableView.currentRow() == -1:
            Ventanas.showAlert("Sistema", "No se ha seleccionado ningun registro")
            return
        
        empleado_id = self.view.tableView.ObtenerItemNumerico(
            fila=self.view.tableView.currentRow(), col=0
        )
        controlador = AuditoriaController(modelo_nombre="Empleado", registro_id=empleado_id)
        controlador.exec_()
    
    @inicializar_y_capturar_excepciones
    def on_click_btn_vencimientos(self, *args, **kwargs):
        row = self.view.tableView.filaSeleccionada()
        if row == -1:
            Ventanas.showAlert("ERROR", "Debe seleccionar un empleado para ver sus vencimientos")
            return
        id = self.view.tableView.ObtenerItemNumerico(fila=row, col=0)
        controlador = VencimientosController()
        controlador.id_tabla = id
        controlador.id_tipo = 'empleado'
        controlador.CargaDatos()
        controlador.exec_()        

class FichaPersonalController(ControladorBase):
    id_empleado = 0
    id_formulario = 104
    usuario = ""
    empleados = []
    indice = 0

    def __init__(self):
        super().__init__()
        self.view = FichaPersonalView()
        self.conectarWidgets()
    
    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnAgregar.clicked.connect(self.onClickBtnAgregar)
        self.view.btnCargar.clicked.connect(self.CargaDatos)
        self.view.btnEditar.clicked.connect(self.onClickBtnModificar)
        self.view.btnBorrar.clicked.connect(self.onClickBtnBorrar)
        self.view.btnImprimir.clicked.connect(self.onClickBtnImprimir)
        self.view.btnCuotas.clicked.connect(self.onClickBtnCuotas)
        self.view.btnExcel.clicked.connect(self.exporta_excel)

    @inicializar_y_capturar_excepciones
    def CargaDatos(self, *args, **kwargs):
        self.view.gridFicha.setRowCount(0)
        debe = peewee.fn.Sum(FichaPersonal.debe).alias('debe')
        haber = peewee.fn.Sum(FichaPersonal.haber).alias('haber')
        datos_saldo = FichaPersonal.select(debe, haber).where(
            FichaPersonal.empleado == self.id_empleado,
            FichaPersonal.fecha < self.view.layoutFechas.desde_fecha.toPyDate()
        ).group_by(
            FichaPersonal.empleado
        )

        saldo = 0
        for d in datos_saldo:
            saldo += d.debe - d.haber

        item = [
            self.view.layoutFechas.desde_fecha.toPyDate(), 'Saldo Inicial',
            0, 0, saldo
        ]

        datos = FichaPersonal.select().where(
            FichaPersonal.empleado == self.id_empleado,
            FichaPersonal.fecha.between(
                lo=self.view.layoutFechas.desde_fecha.toPyDate(),
                hi=self.view.layoutFechas.hasta_fecha.toPyDate()
            )
        ).order_by(
            FichaPersonal.debe
        )
        if self.usuario:
            datos = datos.where(
                FichaPersonal.usuario == self.usuario
            )

        suma_debe = 0
        suma_haber = 0
        for d in datos:
            suma_debe += d.debe
            suma_haber += d.haber
            # cabecera = [
            #     "Fecha", "Detalle", "Unitario", "Toneladas", "Debe", "Haber", "ID"
            # ]
            item = [
                d.fecha, d.detalle.strip(), d.debe, d.haber, d.periodo, d.moneda.simbolo, d.cambio, d.id
            ]
            self.view.gridFicha.AgregaItem(item)
        suma_diferencia = suma_debe - suma_haber
        self.view.txt_debe.setText(suma_debe)
        self.view.txt_haber.setText(suma_haber)
        self.view.txt_diferencia.setText(suma_diferencia)

    @inicializar_y_capturar_excepciones
    def onClickBtnAgregar(self, *args, **kwargs):
        controlador = ModificaFichaEmpleadoController()
        controlador.id_empleado = self.id_empleado
        controlador.id_ficha = 0
        controlador.exec_()
        self.CargaDatos()
        
    @inicializar_y_capturar_excepciones
    def onClickBtnModificar(self, *args, **kwargs):
        row = self.view.gridFicha.currentRow()
        if row == -1:
            Ventanas.showAlert("Sistema", "No se ha seleccionado ningun registro")
            return
        controlador = ModificaFichaEmpleadoController()
        controlador.id_empleado = self.id_empleado
        controlador.id_ficha = self.view.gridFicha.ObtenerItemNumerico(
            fila=row, col='ID'
        )

        controlador.CargaDatos()
        controlador.exec_()
        self.CargaDatos()    
    
    
    @inicializar_y_capturar_excepciones
    def onClickBtnBorrar(self, *args, **kwargs):
        row = self.view.gridFicha.currentRow()
        if row == -1:
            return

        if Ventanas.showConfirmation("Sistema", "Desea borrar el registro seleccionado?") == QMessageBox.Ok:
            FichaPersonal.delete().where(
                FichaPersonal.id == self.view.gridFicha.ObtenerItemNumerico(fila=row, col='ID')
            ).execute()
            self.CargaDatos()
            
    @inicializar_y_capturar_excepciones
    def onClickBtnImprimir(self, *args, **kwargs):
        if not self.view.gridFicha.rowCount():
            return
        emple = Empleado.get_by_id(self.id_empleado)
        # periodo = self.view.gridFicha.ObtenerItem(fila=0, col="Periodo")
        periodo = self.view.layoutFechas.desde_fecha.getPeriodo()
        pdf = ImprimeFichaEmpleado()
        pdf.empleado = f'{emple.nombre.strip()} {emple.apellido.strip()}'	
        pdf.periodo = MesIdentificador(periodo=periodo)
        pdf.AgregaPagina()
        pdf.Encabezado()

        datos = FichaPersonal.select().where(
            FichaPersonal.empleado == self.id_empleado,
            FichaPersonal.fecha.between(
                lo=self.view.layoutFechas.desde_fecha.toPyDate(),
                hi=self.view.layoutFechas.hasta_fecha.toPyDate()
            )
        ).order_by(FichaPersonal.debe)

        saldo = 0
        for d in datos:
            saldo += d.haber - d.debe
            item = [
                FormatoFecha(d.fecha, formato="dma"),
                f'{d.detalle[:45]}...' if len(d.detalle.strip()) > 45 else d.detalle,
                d.moneda.simbolo, d.cambio, d.debe, d.haber, saldo
            ]
            pdf.ImprimeDetalle(item, tamanio_fuente=8,)

        pdf.AgregaLineas(5)
        pdf.TrazaLinea(x1=140)
        pdf.AgregaLineas(5)
        pdf.Texto(x=145, y=pdf.get_y(), txt=f"Diferencia ${round(saldo, 2)}", negrita="B")
        pdf.AgregaLineas(15)
        pdf.Texto(x=150, y=pdf.get_y(), txt=f"__________________")
        pdf.AgregaLineas(3)
        pdf.Texto(x=150, y=pdf.get_y(), txt=f"{emple.nombre}")
        pdf.Imprime(pdf)        

    @inicializar_y_capturar_excepciones
    def onClickBtnCuotas(self, *args, **kwargs):
        controlador = GeneraCuotasFichaController()
        controlador.empleado_id = self.id_empleado
        controlador.exec_()
    
    def exporta_excel(self):
        self.view.gridFicha.ExportaExcel(titulo="Ficha empleado")        

class ModificaFichaEmpleadoController(ControladorBase):
    id_empleado = 0
    id_ficha = 0
    id_formulario = 132

    def __init__(self):
        super().__init__()
        self.view = ModificaFichaEmpleadoView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGrabar.clicked.connect(self.onClickBtnGrabar)

    @inicializar_y_capturar_excepciones
    def onClickBtnGrabar(self, *args, **kwargs):
        emple = Empleado.get_by_id(self.id_empleado)
        if emple.activo == False:
            Ventanas.showAlert("Sistema", "Empleado dado de baja. No es posible agregar datos a la ficha")
            return

        if self.id_ficha == 0:
            ficha = FichaPersonal()
            ficha.empleado_id = self.id_empleado
            nuevo = True
        else:
            ficha = FichaPersonal.get_by_id(self.id_ficha)
            nuevo = False
        ficha.fecha = self.view.textFecha.valor()
        ficha.periodo = self.view.layoutPeriodo.cPeriodo
        ficha.detalle = self.view.textDetalle.valor().upper().strip()
        ficha.debe = self.view.spnDebe.valor()
        ficha.haber = self.view.spnHaber.valor()
        ficha.moneda = self.view.cboMonedas.valor()
        ficha.cambio = self.view.spnCambio.valor()
        ficha.concepto_liquidacion = self.view.layout_concepto.lineEditCodigo.valor()
        ficha.save(force_insert=nuevo)
        self.view.Cerrar()

    @inicializar_y_capturar_excepciones
    def CargaDatos(self, *args, **kwargs):
        ficha = FichaPersonal.get_by_id(self.id_ficha)
        self.view.textFecha.setFecha(ficha.fecha)
        self.view.spnHaber.setText(ficha.haber)
        self.view.spnDebe.setText(ficha.debe)
        self.view.textDetalle.setText(ficha.detalle.strip())
        self.view.layoutPeriodo.setText(ficha.periodo)
        self.view.layoutPeriodo.cPeriodo = ficha.periodo
        self.view.layoutPeriodo.lineEditMes.setText(ficha.periodo[4:])
        self.view.layoutPeriodo.lineEditAnio.setText(ficha.periodo[:4])
        self.view.layout_concepto.lineEditCodigo.setText(ficha.concepto_liquidacion.id)
        self.view.layout_concepto.textNombre.setText(ficha.concepto_liquidacion.descripcion.strip())

        
class ImprimeFichaEmpleado(PyFPDFController):
    periodo = ""
    un = ""
    empleado = ""
    ubicacion = {
        "Fecha": 0,
        "Descripcion": 17,
        "Moneda": 95,
        "Cambio": 115,
        "Debe": 140,
        "Haber": 165,
        "Saldo": 190
    }

    def Encabezado(self):
        # self.EncabezadoEmpresa(imprimex=False)
        self.set_xy(30, 20 + self.corrimiento_cabecera)
        self.TituloInforme(f"Empleado: {self.empleado}")
        self.TituloInforme(f"Mes liquidado: {self.periodo}", tamanio=12)
        self.AgregaLineas(5)
        self.ImprimeCabecera()

class GeneraCuotasFichaController(ControladorBase):
    empleado_id = 0
    id_formulario = 104

    def __init__(self):
        super().__init__()
        self.view = GeneraCuotasFichaView()
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btnCerrar.clicked.connect(self.view.Cerrar)
        self.view.btnGrabar.clicked.connect(self.onClickBtnGrabar)

    @inicializar_y_capturar_excepciones
    def onClickBtnGrabar(self, *args, **kwargs):
        # emple = Empleado.get_by_id(self.empleado_id)
        concepto_liquidacion = ParamSist().ObtenerParametro("CODIGO_PRESTAMO", "")
        if concepto_liquidacion == "":
            Ventanas.showAlert("Sistema", "No se encuentra configurado el concepto de liquidacion para prestamos")
            return
        c_periodo = self.view.layoutPeriodo.cPeriodo
        for i in range(1, int(self.view.spnCantidad.valor()) + 1):
            ficha = FichaPersonal()
            ficha.empleado = self.empleado_id
            ficha.fecha = FinMes(PeriodoAFecha(c_periodo))
            ficha.periodo = c_periodo
            ficha.detalle = f'{self.view.textDescripcion.valor()}-Cuota {i} de {int(self.view.spnCantidad.valor())}'
            ficha.debe = round(self.view.spnMontoTotal.valor() / self.view.spnCantidad.valor(), 2)
            ficha.concepto_liquidacion = concepto_liquidacion
            ficha.moneda = self.view.cboMonedas.valor()
            ficha.cambio = self.view.spnCambio.valor()
            ficha.save()
            c_periodo = periodo_siguiente(c_periodo)
        Ventanas.showAlert("Sistema", "Cuotas generadas en la ficha del empleado")
        self.view.Cerrar()
        
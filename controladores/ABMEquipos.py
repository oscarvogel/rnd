import datetime
import re
from PyQt5.QtWidgets import QMessageBox
from modelos.Combustible import MovimientoCombustible
from modelos.Equipos import ChoferEquipo, Equipos, Vencimientos
from modelos.ModeloBase import reconnect_if_needed
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.libs.controladores.ControladorBaseABM import ControladorBaseABM
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.Excel import Excel
from pyqt5libs.pyqt5libs.utiles import FormatoFecha, inicializar_y_capturar_excepciones
from vistas.ABMEquipos import ABMEquiposView, MovimientosEquiposView, VencimientosView


class ABMEquiposController(ControladorBaseABM):
    model = Equipos
    campoclave = Equipos.id.name
    id_formulario = 662
    
    def __init__(self):
        super().__init__()
        self.view = ABMEquiposView()
        self.view.btnBorrar.setText("Baja")
        self.conectarWidgets()
        
    def conectarWidgets(self):
        super().conectarWidgets()
        self.view.btn_vencimientos.clicked.connect(self.on_click_btn_vencimientos)
        
    def onClickBtnBorrar(self):
        row = self.view.tableView.currentRow()
        if row == -1:
            Ventanas.showAlerta("Error", "No hay fila seleccionada")
            return
        
        id_equipo = self.view.tableView.ObtenerItemNumerico(fila=row, col=0)
        if Ventanas.showConfirmation("Sistema", "Deseas dar de baja el registro seleccionado?") == QMessageBox.Ok:
            try:
                equipo = Equipos.get(Equipos.id == id_equipo)
                equipo.activo = False
                equipo.fecha_baja = datetime.datetime.now()
                equipo.save()
                
                Ventanas.showAlert("Sistema", "Registro dado de baja correctamente")
            except Exception as e:
                Ventanas.showAlert("Sistema", f"Error al dar de baja el registro: {e}")
        else:
            Ventanas.showAlert("Sistema", "Eliminacion cancelada por el usuario")

       
    @inicializar_y_capturar_excepciones
    def on_click_btn_vencimientos(self, *args, **kwargs):
        row = self.view.tableView.filaSeleccionada()
        if row == -1:
            Ventanas.showAlert("ERROR", "Debe seleccionar un movil para ver sus vencimientos")
            return
        id = self.view.tableView.ObtenerItemNumerico(fila=row, col=0)
        controlador = VencimientosController()
        controlador.id_tabla = id
        controlador.id_tipo = 'movil'
        controlador.CargaDatos()
        controlador.exec_()
    
    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        ultimo_chofer = ChoferEquipo.ultimo_chofer(self.view.idtabla)
        if self.view.tipo == 'M' and ultimo_chofer:
            if self.view.chofer_asignado.valor() != str(ultimo_chofer.empleado.id):
                ultimo_chofer.fecha_fin = datetime.date.today() - datetime.timedelta(days=1)
                ultimo_chofer.save()
                ##si cambia el chofer, se crea un nuevo registro
                ChoferEquipo.create(
                    movil=self.view.idtabla,
                    empleado=self.view.chofer_asignado.valor(),
                    fecha_inicio=datetime.date.today()
                )
        else:
            ChoferEquipo.create(
                movil=self.view.idtabla,
                empleado=self.view.chofer_asignado.valor(),
                fecha_inicio=datetime.date.today()
            )
           
    
class VencimientosController(ControladorBase):
    
    id_tabla = 0
    id_tipo = ''
    
    def __init__(self):
        super().__init__()
        self.view = VencimientosView()
        self.conectarWidgets()
        
    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_grabar.clicked.connect(self.grabar)
        self.view.btn_borrar.clicked.connect(self.borrar)
        
    @inicializar_y_capturar_excepciones
    def grabar(self, *args, **kwargs):
        ids_existentes = set()
        
        # Obtener todos los vencimientos existentes de una sola vez (optimización)
        if self.id_tipo == 'movil':
            vencimientos_existentes = Vencimientos.select().where(Vencimientos.movil == self.id_tabla)
        else:
            vencimientos_existentes = Vencimientos.select().where(Vencimientos.personal == self.id_tabla)

        ids_existentes = {v.id for v in vencimientos_existentes}

        nuevos_o_actualizados = set()

        with Vencimientos._meta.database.atomic():  # Usamos una transacción
            for row in range(self.view.grid_datos.rowCount()):
                id = self.view.grid_datos.ObtenerItemNumerico(fila=row, col='id')
                fecha = self.view.grid_datos.ObtenerItemFecha(fila=row, col='Fecha')
                detalle = self.view.grid_datos.ObtenerItem(fila=row, col='Detalle')

                # Si id está presente y existe en BD: actualizamos
                if id and id in ids_existentes:
                    vencimiento = Vencimientos.get_by_id(id)
                else:
                    # Si no, creamos uno nuevo
                    vencimiento = Vencimientos()

                    # Asignar según tipo
                    if self.id_tipo == 'movil':
                        vencimiento.movil = self.id_tabla
                    else:
                        vencimiento.personal = self.id_tabla

                vencimiento.fecha_vencimiento = fecha
                vencimiento.descripcion = detalle
                vencimiento.save()

                nuevos_o_actualizados.add(vencimiento.id)
        self.view.Cerrar()
    
    @inicializar_y_capturar_excepciones
    def CargaDatos(self, *args, **kwargs):
        self.view.grid_datos.limpiarGrilla()
        vencimientos = Vencimientos.select()
        if self.id_tipo == 'movil':
            vencimientos = vencimientos.where(
                Vencimientos.movil == self.id_tabla
            )
        else:
            vencimientos = vencimientos.where(
                Vencimientos.personal == self.id_tabla
            )
        for vencimiento in vencimientos:
            self.view.grid_datos.AgregaItem([
                vencimiento.fecha_vencimiento, vencimiento.descripcion, vencimiento.id
            ])
    
    @inicializar_y_capturar_excepciones
    def borrar(self, *args, **kwargs):
        """borra un vencimiento seleccionado
        """
        row = self.view.grid_datos.filaSeleccionada()
        if row == -1:
            Ventanas.showAlert("Sistema", "Debe seleccionar un vencimiento a borrar")
            return

        id_vencimiento = self.view.grid_datos.ObtenerItemNumerico(fila=row, col='id')

        if Ventanas.showConfirmation("Sistema", "Desea borrar el vencimiento seleccionado?") == Ventanas.SI:
            vencimiento = Vencimientos.get_by_id(id_vencimiento)
            vencimiento.delete_instance()
            self.CargaDatos()
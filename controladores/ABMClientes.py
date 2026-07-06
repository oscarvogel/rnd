from modelos.Clientes import Cliente, CodigoClienteProveedor
from modelos.ModeloBase import reconnect_if_needed
from modelos.Proveedores import BuscaProveedor
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.libs.controladores.ControladorBaseABM import ControladorBaseABM
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from vistas.ABMClientes import ABMClientesView, CodigoClienteProveedorView


class ABMClientesController(ControladorBaseABM):
    model = Cliente
    campoclave = Cliente.id.name
    id_formulario = 667
    
    def __init__(self):
        super().__init__()
        self.view = ABMClientesView()
        self.conectarWidgets()
        
    def conectarWidgets(self):
        super().conectarWidgets()
        self.view.btn_codigo.clicked.connect(self.on_click_btn_codigo)
        
    def on_click_btn_codigo(self):
        row = self.view.tableView.filaSeleccionada()
        if row == -1:
            Ventanas.showAlert("ERROR", "Debe seleccionar un cliente para gestionar sus codigos")
            return
        id_cliente = self.view.tableView.ObtenerItemNumerico(fila=row, col=0)
        controlador = CodigoClienteProveedorController()
        controlador.id_cliente = id_cliente
        controlador.CargaDatos()
        controlador.exec_()
        

class CodigoClienteProveedorController(ControladorBase):
    id_formulario = 668
    id_cliente = None
    
    def __init__(self):
        super().__init__()
        self.view = CodigoClienteProveedorView()
        self.conectarWidgets()
        
    def conectarWidgets(self):
        self.view.btn_salir.clicked.connect(self.view.Cerrar)
        self.view.btn_agregar.clicked.connect(self.on_click_btn_agregar)
        self.view.btn_borrar.clicked.connect(self.on_click_btn_borrar)
        self.view.btn_guardar.clicked.connect(self.on_click_btn_grabar)

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def CargaDatos(self, *args, **kwargs):
        self.view.grilla.limpiarGrilla()
        if not self.id_cliente:
            return
        
        codigos = CodigoClienteProveedor.select().where(CodigoClienteProveedor.cliente == self.id_cliente)
        for codigo in codigos:
            self.view.grilla.AgregaItem([codigo.proveedor.razon_social, codigo.codigo, codigo.id, codigo.proveedor.id])
    
    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_agregar(self, *args, **kwargs):
        proveedor = BuscaProveedor()
        proveedor.buscar(self.view)
        if proveedor.lRetval:
            try:
                codigos = CodigoClienteProveedor.select().where(
                    (CodigoClienteProveedor.cliente == self.id_cliente) &
                    (CodigoClienteProveedor.proveedor == proveedor.valorRetorno)
                )
                if codigos.exists():
                    Ventanas.showAlert("ERROR", "El proveedor ya tiene un código asignado para este cliente")
                    return
                CodigoClienteProveedor.create(
                    cliente=self.id_cliente,
                    proveedor=proveedor.valorRetorno,
                )
            except Exception as e:
                Ventanas.showAlert("ERROR", f"No se pudo agregar el código: {str(e)}")
                return
            self.CargaDatos()
    
    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_borrar(self, *args, **kwargs):
        row = self.view.grilla.filaSeleccionada()
        if row == -1:
            Ventanas.showAlert("ERROR", "Debe seleccionar una fila para borrar")
            return
        id = self.view.grilla.ObtenerItemNumerico(fila=row, col=2)
        try:
            codigo = CodigoClienteProveedor.get(CodigoClienteProveedor.id == id)
            codigo.delete_instance()
            self.view.grilla.removeRow(row)
        except Exception as e:
            pass
    
    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_grabar(self, *args, **kwargs):
        
        for row in range(self.view.grilla.rowCount()):
            id_proveedor = self.view.grilla.ObtenerItemNumerico(fila=row, col="id_proveedor")
            codigo = self.view.grilla.ObtenerItem(fila=row, col="Codigo Cliente")
            id = self.view.grilla.ObtenerItemNumerico(fila=row, col="ID")
            
            cliente_proveedor = CodigoClienteProveedor.get_or_none(CodigoClienteProveedor.id == id)
            if cliente_proveedor:
                cliente_proveedor.codigo = codigo
                cliente_proveedor.proveedor = id_proveedor
                cliente_proveedor.save()
            else:
                CodigoClienteProveedor.create(
                    codigo=codigo,
                    cliente=self.id_cliente,
                    proveedor=id_proveedor
                )
        self.view.Cerrar()
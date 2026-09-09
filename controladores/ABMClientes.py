from PyQt5.QtWidgets import QMessageBox

from peewee import JOIN

from modelos.Clientes import (
    Cliente, CodigoClienteProveedor, LugarEntrega, Localidades, RutaReparto,
)
from modelos.ModeloBase import reconnect_if_needed
from modelos.Proveedores import BuscaProveedor
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.libs.controladores.ControladorBaseABM import ControladorBaseABM
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from utiles.consolidacion_clientes import simular_consolidacion, consolidar_clientes
from vistas.ABMClientes import (
    ABMClientesView, CodigoClienteProveedorView, LugarEntregaView,
    ConsolidacionClientesView,
)


class ABMClientesController(ControladorBaseABM):
    model = Cliente
    campoclave = Cliente.id.name
    id_formulario = 667
    
    def __init__(self):
        super().__init__()
        self.view = ABMClientesView()
        self.view.on_cargar_lugares = self.cargar_lugares_entrega
        self.conectarWidgets()
        
    def conectarWidgets(self):
        super().conectarWidgets()
        self.view.btn_codigo.clicked.connect(self.on_click_btn_codigo)
        self.view.btn_consolidar.clicked.connect(self.on_click_btn_consolidar)
        self.view.btn_lugar_agregar.clicked.connect(self.on_click_lugar_agregar)
        self.view.btn_lugar_editar.clicked.connect(self.on_click_lugar_editar)
        self.view.btn_lugar_borrar.clicked.connect(self.on_click_lugar_borrar)
        
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

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def on_click_btn_consolidar(self, *args, **kwargs):
        vista = ConsolidacionClientesView()
        clientes = list(
            Cliente.select()
            .where(Cliente.activo == True)
            .order_by(Cliente.razon_social)
        )
        if len(clientes) < 2:
            Ventanas.showAlert("Sistema", "Se necesitan al menos dos clientes activos para consolidar")
            return

        destino_preseleccionado = None
        row = self.view.tableView.filaSeleccionada()
        if row != -1:
            destino_preseleccionado = self.view.tableView.ObtenerItemNumerico(fila=row, col=0)
        vista.cargar_clientes(
            [(x.id, x.razon_social) for x in clientes],
            destino_preseleccionado=destino_preseleccionado,
        )

        estado = {"resumen": None, "firma": None}

        def firma_actual():
            destino = vista.destino_id()
            origenes = tuple(sorted(x for x in vista.origenes_ids() if x != destino))
            return destino, origenes

        def simular():
            destino, origenes = firma_actual()
            try:
                resumen = simular_consolidacion(destino, origenes)
            except Exception as exc:
                estado["resumen"] = None
                estado["firma"] = None
                vista.mostrar_resumen("No se puede simular: {}".format(exc), False)
                return
            estado["resumen"] = resumen
            estado["firma"] = (destino, origenes)
            texto = resumen.texto()
            if resumen.advertencias:
                texto += "\n\nLa consolidación requiere revisión especial por las advertencias indicadas."
            else:
                texto += "\n\nLa simulación no modificó datos. Puede continuar con Consolidar."
            vista.mostrar_resumen(texto, habilitar=not bool(resumen.advertencias))

        def ejecutar():
            destino, origenes = firma_actual()
            if not estado["resumen"] or estado["firma"] != (destino, origenes):
                Ventanas.showAlert("Sistema", "La selección cambió. Ejecute Simular nuevamente")
                vista.btn_consolidar.setEnabled(False)
                return
            if estado["resumen"].advertencias:
                Ventanas.showAlert(
                    "Sistema",
                    "Hay advertencias de identidad (por ejemplo CUIT distinto). No se consolidará automáticamente.",
                )
                return
            respuesta = QMessageBox.question(
                vista,
                "Confirmar consolidación",
                "Esta operación reasignará históricos, códigos y lugares de entrega dentro de una transacción. "
                "Los clientes origen quedarán inactivos. ¿Desea continuar?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if respuesta != QMessageBox.Yes:
                return
            try:
                resumen = consolidar_clientes(destino, origenes)
            except Exception as exc:
                Ventanas.showAlert("ERROR", "No se pudo consolidar. Se revirtieron los cambios: {}".format(exc))
                return
            vista.mostrar_resumen(
                resumen.texto() + "\n\nCONSOLIDACIÓN COMPLETADA. Los clientes origen quedaron inactivos.",
                False,
            )
            estado["resumen"] = None
            estado["firma"] = None
            try:
                self.CargaDatos()
            except Exception:
                pass

        vista.btn_simular.clicked.connect(simular)
        vista.btn_consolidar.clicked.connect(ejecutar)
        vista.btn_cerrar.clicked.connect(vista.Cerrar)
        vista.exec_()

    def _cliente_ficha(self):
        try:
            return int(self.view.idtabla or 0)
        except (TypeError, ValueError):
            return 0

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar_lugares_entrega(self, *args, **kwargs):
        cliente_id = self._cliente_ficha()
        if not cliente_id:
            self.view.cargar_lugares([])
            self.view.habilitar_lugares(False)
            return

        lugares = (
            LugarEntrega.select(LugarEntrega, Localidades, RutaReparto)
            .join(Localidades, join_type=JOIN.LEFT_OUTER, on=(LugarEntrega.localidad == Localidades.id))
            .switch(LugarEntrega)
            .join(RutaReparto, join_type=JOIN.LEFT_OUTER, on=(LugarEntrega.ruta_reparto == RutaReparto.id))
            .where(LugarEntrega.cliente == cliente_id)
            .order_by(LugarEntrega.principal.desc(), LugarEntrega.nombre)
        )
        filas = []
        for lugar in lugares:
            filas.append([
                lugar.nombre,
                lugar.direccion or "",
                lugar.localidad.descripcion if lugar.localidad_id else "",
                lugar.ruta_reparto.descripcion if lugar.ruta_reparto_id else "",
                "Sí" if lugar.principal else "",
                "Sí" if lugar.activo else "No",
                lugar.id,
            ])
        self.view.cargar_lugares(filas)
        self.view.habilitar_lugares(True)

    def _id_lugar_seleccionado(self):
        row = self.view.grilla_lugares.filaSeleccionada()
        if row == -1:
            return None
        return self.view.grilla_lugares.ObtenerItemNumerico(fila=row, col=6)

    def _abrir_lugar(self, lugar=None):
        cliente_id = self._cliente_ficha()
        if not cliente_id:
            Ventanas.showAlert(
                "Sistema",
                "Primero guarde el cliente. Luego podrá agregar sus lugares de entrega.",
            )
            return

        vista = LugarEntregaView()
        localidades = Localidades.select().order_by(Localidades.descripcion)
        rutas = RutaReparto.select().where(RutaReparto.activo == True).order_by(RutaReparto.descripcion)
        vista.cargar_combobox(
            vista.cbo_localidad,
            [(x.id, x.descripcion) for x in localidades],
            lugar.localidad_id if lugar else None,
        )
        vista.cargar_combobox(
            vista.cbo_ruta,
            [(x.id, x.descripcion) for x in rutas],
            lugar.ruta_reparto_id if lugar else None,
        )
        if lugar:
            vista.txt_nombre.setText(lugar.nombre or "")
            vista.txt_direccion.setText(lugar.direccion or "")
            vista.chk_principal.setChecked(bool(lugar.principal))
            vista.chk_activo.setChecked(bool(lugar.activo))
            vista.txt_observaciones.setPlainText(lugar.observaciones or "")

        def guardar():
            valores = vista.valores()
            if not valores["nombre"]:
                Ventanas.showAlert("Sistema", "Debe indicar un nombre o referencia para el lugar")
                return
            try:
                registro = lugar or LugarEntrega(cliente=cliente_id)
                registro.cliente = cliente_id
                for campo, valor in valores.items():
                    setattr(registro, campo, valor)
                registro.save()
            except Exception as exc:
                Ventanas.showAlert("ERROR", "No se pudo guardar el lugar de entrega: {}".format(exc))
                return
            vista.Cerrar()
            self.cargar_lugares_entrega()

        vista.btn_guardar.clicked.connect(guardar)
        vista.btn_cancelar.clicked.connect(vista.Cerrar)
        vista.exec_()

    def on_click_lugar_agregar(self):
        self._abrir_lugar()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def on_click_lugar_editar(self, *args, **kwargs):
        lugar_id = self._id_lugar_seleccionado()
        if not lugar_id:
            Ventanas.showAlert("Sistema", "Seleccione un lugar de entrega para editar")
            return
        lugar = LugarEntrega.get_or_none(
            (LugarEntrega.id == lugar_id) &
            (LugarEntrega.cliente == self._cliente_ficha())
        )
        if not lugar:
            Ventanas.showAlert("Sistema", "El lugar de entrega seleccionado ya no existe")
            self.cargar_lugares_entrega()
            return
        self._abrir_lugar(lugar)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def on_click_lugar_borrar(self, *args, **kwargs):
        lugar_id = self._id_lugar_seleccionado()
        if not lugar_id:
            Ventanas.showAlert("Sistema", "Seleccione un lugar de entrega para borrar")
            return
        lugar = LugarEntrega.get_or_none(
            (LugarEntrega.id == lugar_id) &
            (LugarEntrega.cliente == self._cliente_ficha())
        )
        if not lugar:
            self.cargar_lugares_entrega()
            return
        # En vez de eliminar físicamente, se desactiva para preservar trazabilidad histórica.
        lugar.activo = False
        lugar.principal = False
        lugar.save()
        self.cargar_lugares_entrega()
        

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

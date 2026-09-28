from modelos.Proveedores import Proveedor
from modelos.ModeloBase import reconnect_if_needed
from pyqt5libs.libs.controladores.ControladorBaseABM import ControladorBaseABM
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from vistas.ABMProveedores import ABMProveedoresView


class ABMProveedoresController(ControladorBaseABM):
    model = Proveedor
    campoclave = Proveedor.id.name
    id_formulario = 667
    
    def __init__(self):
        super().__init__()
        self.view = ABMProveedoresView()
        self.conectarWidgets()
        
    def conectarWidgets(self):
        super().conectarWidgets()

    def _copiar_controles_al_modelo(self, dato, es_alta):
        """Copia la ficha sin escribir el PK autoincremental durante un alta."""
        for nombre, control in self.view.controles.items():
            if (
                es_alta
                and self.view.autoincremental
                and nombre == self.campoclave
            ):
                continue
            dato.__data__[nombre] = control.valor()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def onClickBtnAceptar(self, *args, **kwargs):
        """Guarda proveedores respetando el AutoField también en SQLite/DEMO."""
        if not self.model:
            Ventanas.showAlert("Sistema", "Debes establecer un modelo a actualizar")
            return
        if self.campoclave is None:
            Ventanas.showAlert("Sistema", "Debes establecer un campo clave a actualizar")
            return

        if self.onPreClickAceptar():
            es_alta = self.view.tipo == 'A'
            if es_alta:
                dato = self.model()
            else:
                registro_id = self.view.idtabla or self.view.controles[self.campoclave].text()
                dato = self.model.get_by_id(registro_id)

            self._copiar_controles_al_modelo(dato, es_alta)
            dato.save(force_insert=es_alta)
            self.view.idtabla = dato.get_id()
            self.view.btnAceptarClicked()
        self.onPostClickAceptar()

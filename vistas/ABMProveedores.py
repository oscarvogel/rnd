from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QComboBox

from modelos.Proveedores import Proveedor
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.libs.vistas.ABM import ABM
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.ComboBox import Combo
from pyqt5libs.pyqt5libs.EntradaTexto import TextEdit
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.utiles import imagen, inicializar_y_capturar_excepciones
from utiles.importacion_proveedores_excel import (
    METODOS_IMPORTACION,
    normalizar_metodo_importacion,
)


class ABMProveedoresView(ABM):
    model = Proveedor
    camposAMostrar = [Proveedor.id, Proveedor.razon_social, Proveedor.direccion, Proveedor.telefono, Proveedor.cuit, Proveedor.contacto, Proveedor.metodo_importacion, Proveedor.activo]
    ordenBusqueda = [Proveedor.razon_social]
    campoClave = Proveedor.id
    titulo = "Tabla de Fabricantes y Proveedores"
    autoincremental = True
    dynamicBackColor = {Proveedor.activo.name: {'valor': False, 'color': QColor(128, 128, 128)}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    @inicializar_y_capturar_excepciones
    def ArmaCarga(self, *args, **kwargs):
        layout_codigo = self.ArmaEntrada(Proveedor.id)
        self.ArmaEntrada(Proveedor.razon_social, layout_codigo)
        direccion = self.ArmaEntrada(Proveedor.direccion)
        self.ArmaEntrada(Proveedor.telefono, boxlayout=direccion)
        cuit = self.ArmaEntrada(Proveedor.cuit, boxlayout=direccion)
        self.ArmaEntrada(Proveedor.contacto, boxlayout=cuit)
        metodo = self.ArmaEntrada(
            Proveedor.metodo_importacion,
            control=self._combo_metodo_importacion(),
        )
        self.ArmaEntrada(Proveedor.observaciones, control=TextEdit(), boxlayout=metodo)

    @staticmethod
    def _combo_metodo_importacion():
        """Sólo los métodos habilitados; el código viaja como itemData."""
        combo = Combo()
        combo.setEditable(False)
        combo.setInsertPolicy(QComboBox.NoInsert)
        for codigo, etiqueta in METODOS_IMPORTACION:
            combo.addItem("{} — {}".format(codigo, etiqueta), codigo)
        return combo

    def CargaDatos(self, data=None):
        super().CargaDatos(data)
        # El genérico selecciona por texto visible y nuestros items muestran
        # "CÓDIGO — descripción": se selecciona por código normalizado para
        # que valores históricos ("pujio") caigan en su opción canónica.
        combo = self.controles.get(Proveedor.metodo_importacion.name)
        if combo is None or not data:
            return
        for d in data:
            codigo = normalizar_metodo_importacion(d.get("metodo_importacion"))
            if codigo:
                indice = combo.findData(codigo)
                if indice >= 0:
                    combo.setCurrentIndex(indice)

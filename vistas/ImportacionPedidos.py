from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from modelos.Empleados import ValidaEmpleado
from modelos.Equipos import ValidaEquipo
from modelos.Proveedores import ValidaProveedor
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.ComboBox import Combo
from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto
from pyqt5libs.pyqt5libs.Botones import Boton
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.ProgressBar import Avance
from pyqt5libs.pyqt5libs.utiles import imagen


class ImportacionPedidosView(VistaBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Importación de Pedidos")
        self.resize(1150, 600)
        layoutPpal = QVBoxLayout(self)
        layout_archivo = QHBoxLayout()

        self.avance = Avance()
        layoutPpal.addWidget(self.avance)
        
        layout_fechas = QHBoxLayout()
        lbl_fecha = Etiqueta(texto="Fecha reparto:")
        layout_fechas.addWidget(lbl_fecha)
        self.fecha_reparto = Fecha()
        layout_fechas.addWidget(self.fecha_reparto)

        self.empresa_proveedora = ValidaProveedor(texto="Empresa Proveedora:")
        layout_fechas.addLayout(self.empresa_proveedora)
        layoutPpal.addLayout(layout_fechas)
        
        lbl_archivo = Etiqueta(texto="Archivo:")
        layout_archivo.addWidget(lbl_archivo)
        self.txt_archivo = EntradaTexto(placeholderText="Seleccionar archivo...")
        layout_archivo.addWidget(self.txt_archivo)
        self.txt_archivo.setReadOnly(True)
        self.btn_examinar = Boton(
            texto="Examinar",
            imagen=imagen("79354_excel_icon.png"),
            tooltip="Seleccionar archivo de pedidos a importar"
        )
        layout_archivo.addWidget(self.btn_examinar)
        lbl_hoja = Etiqueta(texto="Hoja:")
        layout_archivo.addWidget(lbl_hoja)
        self.cbo_hoja = Combo()
        layout_archivo.addWidget(self.cbo_hoja)
        lbl_fila_inicio = Etiqueta(texto="Fila inicio")
        self.txt_fila_inicio = EntradaTexto()
        layout_archivo.addWidget(lbl_fila_inicio)
        layout_archivo.addWidget(self.txt_fila_inicio)
        lbl_fila_fin = Etiqueta(texto="Fila fin")
        self.txt_fila_fin = EntradaTexto()
        layout_archivo.addWidget(lbl_fila_fin)
        layout_archivo.addWidget(self.txt_fila_fin)
        layoutPpal.addLayout(layout_archivo)

        
        # layout_equipo = QHBoxLayout()
        # self.equipo = ValidaEquipo(texto="Camion:")
        # layout_equipo.addLayout(self.equipo)
        # self.empleado = ValidaEmpleado(texto="Chofer:")
        # layout_equipo.addLayout(self.empleado)
        # layoutPpal.addLayout(layout_equipo)

        self.grid_datos = Grilla()
        self.grid_datos.columnasHabilitadas = [0,]
        self.grid_datos.permiteagregar = False
        layoutPpal.addWidget(self.grid_datos)

        layout_botones = QHBoxLayout()
        self.btn_importar = Boton(texto="Importar", imagen=imagen("search.png"))
        self.btn_importar.setToolTip("Importar pedidos desde el archivo seleccionado")
        self.btn_grabar = Boton(texto="Grabar", imagen=imagen("save.png"))
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"))
        layout_botones.addWidget(self.btn_importar)
        layout_botones.addWidget(self.btn_grabar)
        layout_botones.addWidget(self.btn_cerrar)
        layoutPpal.addLayout(layout_botones)
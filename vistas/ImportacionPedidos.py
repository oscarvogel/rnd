from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QGroupBox
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
        self.setWindowTitle("Preparar pedidos para reparto")
        self.resize(1180, 720)
        layoutPpal = QVBoxLayout(self)
        layoutPpal.setSpacing(12)

        titulo = QLabel("Importar pedidos")
        titulo.setObjectName("importacionTitulo")
        titulo.setProperty("role", "title")
        layoutPpal.addWidget(titulo)

        bajada = QLabel(
            "Seguí estos pasos. RND te indicará qué archivo cargar, mostrará una vista previa "
            "y al finalizar te llevará al siguiente paso del reparto."
        )
        bajada.setWordWrap(True)
        bajada.setObjectName("importacionBajada")
        layoutPpal.addWidget(bajada)

        self.avance = Avance()
        layoutPpal.addWidget(self.avance)

        # Paso 1: contexto operativo
        grupo_origen = QGroupBox("1. Elegir origen y fecha de reparto")
        grupo_origen.setObjectName("importacionPasoOrigen")
        layout_origen = QVBoxLayout(grupo_origen)
        fila_origen = QHBoxLayout()
        lbl_fecha = Etiqueta(texto="Fecha reparto:")
        fila_origen.addWidget(lbl_fecha)
        self.fecha_reparto = Fecha()
        fila_origen.addWidget(self.fecha_reparto)
        self.empresa_proveedora = ValidaProveedor(texto="Proveedor / origen:")
        fila_origen.addLayout(self.empresa_proveedora)
        fila_origen.addStretch(1)
        layout_origen.addLayout(fila_origen)
        self.lbl_ayuda_proveedor = QLabel(
            "Primero seleccione el proveedor/origen para saber qué archivo corresponde importar."
        )
        self.lbl_ayuda_proveedor.setWordWrap(True)
        self.lbl_ayuda_proveedor.setObjectName("importacionAyudaProveedor")
        layout_origen.addWidget(self.lbl_ayuda_proveedor)
        layoutPpal.addWidget(grupo_origen)

        # Paso 2: archivo. Los parámetros técnicos quedan disponibles, pero secundarios.
        grupo_archivo = QGroupBox("2. Seleccionar archivo")
        grupo_archivo.setObjectName("importacionPasoArchivo")
        layout_archivo = QVBoxLayout(grupo_archivo)
        fila_archivo = QHBoxLayout()
        self.txt_archivo = EntradaTexto(placeholderText="Seleccione el archivo recibido del proveedor...")
        self.txt_archivo.setReadOnly(True)
        fila_archivo.addWidget(self.txt_archivo, stretch=1)
        self.btn_examinar = Boton(
            texto="Seleccionar archivo",
            imagen=imagen("79354_excel_icon.png"),
            tooltip="Seleccionar archivo de pedidos a importar"
        )
        self.btn_examinar.setProperty("role", "primary")
        fila_archivo.addWidget(self.btn_examinar)
        layout_archivo.addLayout(fila_archivo)

        fila_opciones = QHBoxLayout()
        lbl_hoja = Etiqueta(texto="Hoja:")
        fila_opciones.addWidget(lbl_hoja)
        self.cbo_hoja = Combo()
        fila_opciones.addWidget(self.cbo_hoja)
        lbl_fila_inicio = Etiqueta(texto="Fila inicio (opcional)")
        self.txt_fila_inicio = EntradaTexto()
        self.txt_fila_inicio.setToolTip("Dejar vacío para comenzar desde la primera fila de la hoja")
        fila_opciones.addWidget(lbl_fila_inicio)
        fila_opciones.addWidget(self.txt_fila_inicio)
        lbl_fila_fin = Etiqueta(texto="Fila fin (opcional)")
        self.txt_fila_fin = EntradaTexto()
        self.txt_fila_fin.setToolTip("Dejar vacío para importar hasta el final de la hoja")
        fila_opciones.addWidget(lbl_fila_fin)
        fila_opciones.addWidget(self.txt_fila_fin)
        layout_archivo.addLayout(fila_opciones)

        nota_opciones = QLabel(
            "Normalmente no necesitás indicar filas: si las dejás vacías RND toma toda la hoja."
        )
        nota_opciones.setWordWrap(True)
        nota_opciones.setObjectName("importacionNotaTecnica")
        layout_archivo.addWidget(nota_opciones)
        layoutPpal.addWidget(grupo_archivo)

        # Paso 3: vista previa
        grupo_previa = QGroupBox("3. Revisar vista previa")
        grupo_previa.setObjectName("importacionPasoPrevia")
        layout_previa = QVBoxLayout(grupo_previa)
        fila_previa = QHBoxLayout()
        self.btn_importar = Boton(texto="Cargar vista previa", imagen=imagen("search.png"))
        self.btn_importar.setToolTip("Leer el archivo y mostrar los pedidos antes de grabarlos")
        fila_previa.addWidget(self.btn_importar)
        self.lbl_previa = QLabel("Todavía no se cargó ningún archivo.")
        self.lbl_previa.setWordWrap(True)
        fila_previa.addWidget(self.lbl_previa, stretch=1)
        layout_previa.addLayout(fila_previa)

        self.grid_datos = Grilla()
        self.grid_datos.columnasHabilitadas = [0,]
        self.grid_datos.permiteagregar = False
        layout_previa.addWidget(self.grid_datos)
        layoutPpal.addWidget(grupo_previa, stretch=1)

        # Paso 4: resultado y siguiente acción
        self.grupo_resultado = QGroupBox("4. Resultado")
        self.grupo_resultado.setObjectName("importacionResultado")
        layout_resultado = QVBoxLayout(self.grupo_resultado)
        self.lbl_resultado_titulo = QLabel("Listo para comenzar")
        self.lbl_resultado_titulo.setObjectName("importacionResultadoTitulo")
        layout_resultado.addWidget(self.lbl_resultado_titulo)
        self.lbl_resultado_detalle = QLabel(
            "Después de grabar los pedidos vas a ver aquí un resumen y el siguiente paso recomendado."
        )
        self.lbl_resultado_detalle.setWordWrap(True)
        layout_resultado.addWidget(self.lbl_resultado_detalle)
        layoutPpal.addWidget(self.grupo_resultado)

        layout_botones = QHBoxLayout()
        self.btn_cerrar = Boton(texto="Cerrar", imagen=imagen("close.png"))
        self.btn_grabar = Boton(texto="Grabar pedidos", imagen=imagen("save.png"))
        self.btn_grabar.setProperty("role", "primary")
        self.btn_siguiente = Boton(texto="Continuar con el reparto")
        self.btn_siguiente.setProperty("role", "primary")
        self.btn_siguiente.setEnabled(False)
        layout_botones.addWidget(self.btn_cerrar)
        layout_botones.addStretch(1)
        layout_botones.addWidget(self.btn_grabar)
        layout_botones.addWidget(self.btn_siguiente)
        layoutPpal.addLayout(layout_botones)

    def mostrar_ayuda_proveedor(self, texto):
        self.lbl_ayuda_proveedor.setText(texto)

    def mostrar_previa(self, cantidad):
        self.lbl_previa.setText(
            "Se leyeron {} registros. Revisá la grilla y desmarcá cualquier fila que no quieras grabar.".format(cantidad)
        )

    def mostrar_resultado(self, resumen):
        self.lbl_resultado_titulo.setText(resumen.titulo)
        self.lbl_resultado_detalle.setText(resumen.detalle)
        if resumen.siguiente_accion == "revisar_pendientes":
            self.btn_siguiente.setText("Revisar pendientes")
        elif resumen.siguiente_accion == "corregir_importacion":
            self.btn_siguiente.setText("Corregir importación")
        else:
            self.btn_siguiente.setText("Continuar con el reparto")
        self.btn_siguiente.setEnabled(True)

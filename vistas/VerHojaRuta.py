from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox, QLabel
from modelos.Clientes import ValidaCliente, cboRutaReparto
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.EntradaTexto import EntradaTexto
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha
from pyqt5libs.pyqt5libs.Grillas import Grilla
from pyqt5libs.pyqt5libs.ProgressBar import Avance
from pyqt5libs.pyqt5libs.Spinner import Spinner


class VerHojaRutaView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Ver Hoja de Ruta")
        self.resize(1180, 760)
        layoutPpal = QVBoxLayout(self)

        self.lbl_titulo_hoja = QLabel("Hoja de ruta")
        self.lbl_titulo_hoja.setObjectName("hojaRutaTitulo")
        self.lbl_titulo_hoja.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layoutPpal.addWidget(self.lbl_titulo_hoja)

        self.lbl_estado_operativo = QLabel("Estado: sin cargar")
        self.lbl_estado_operativo.setObjectName("hojaRutaEstadoOperativo")
        self.lbl_estado_operativo.setWordWrap(True)
        layoutPpal.addWidget(self.lbl_estado_operativo)

        self.lbl_estado_hoja = QLabel("Seleccione fecha y ruta para cargar la hoja.")
        self.lbl_estado_hoja.setObjectName("hojaRutaEstado")
        self.lbl_estado_hoja.setWordWrap(True)
        layoutPpal.addWidget(self.lbl_estado_hoja)

        self.lbl_resumen_hoja = QLabel("Pedidos: 0 · KG: 0 · Bultos: 0")
        self.lbl_resumen_hoja.setObjectName("hojaRutaResumen")
        self.lbl_resumen_hoja.setWordWrap(True)
        layoutPpal.addWidget(self.lbl_resumen_hoja)
        
        self.avance = Avance()
        layoutPpal.addWidget(self.avance)
        
        layout_fechas = QHBoxLayout()
        lbl_fecha = Etiqueta(texto="Fecha de reparto:")
        self.fecha_reparto = Fecha()
        layout_fechas.addWidget(lbl_fecha)
        layout_fechas.addWidget(self.fecha_reparto)
        lbl_ruta = Etiqueta(texto="Ruta de reparto:")
        layout_fechas.addWidget(lbl_ruta)
        self.cbo_ruta_reparto = cboRutaReparto()
        layout_fechas.addWidget(self.cbo_ruta_reparto)
        layoutPpal.addLayout(layout_fechas)
                
        recursos = QGroupBox("Recursos asignados")
        form_recursos = QFormLayout(recursos)
        self.lbl_camion = QLabel("Camión pendiente")
        self.lbl_chofer = QLabel("Chofer pendiente")
        self.lbl_camion.setObjectName("hojaRutaCamion")
        self.lbl_chofer.setObjectName("hojaRutaChofer")
        form_recursos.addRow("Camión:", self.lbl_camion)
        form_recursos.addRow("Chofer:", self.lbl_chofer)
        self.btn_recursos = self.CreaBoton(
            "Modificar chofer / camión", imagen_str="edit.png"
        )
        self.btn_recursos.setProperty("role", "secondary")
        form_recursos.addRow("", self.btn_recursos)
        layoutPpal.addWidget(recursos)
        
        self.grilla_datos = Grilla()
        cabeceras = [
            "Cliente", "Comprobante", "Factura", "Remito", "Producto",
            "Cantidad", "KG", "Bultos", "Observaciones", "id", "codigo_cliente"
        ]
        self.grilla_datos.ArmaCabeceras(cabeceras=cabeceras)
        self.grilla_datos.columnasHabilitadas = []
        self.grilla_datos.setColumnHidden(9, True)
        self.grilla_datos.setColumnHidden(10, True)
        layoutPpal.addWidget(self.grilla_datos)
        
        layout_botones = QHBoxLayout()
        self.btn_cargar = self.CreaBoton("Actualizar", imagen_str="search.png")
        self.btn_agregar = self.CreaBoton("Agregar", imagen_str="new.png")
        self.btn_modificar = self.CreaBoton("Modificar", imagen_str="edit.png")
        # Los recursos se editan únicamente desde Asignar recursos.
        # Se conserva el atributo por compatibilidad con código legacy.
        self.btn_grabar = self.CreaBoton("Grabar", imagen_str="save.png")
        self.btn_grabar.setVisible(False)
        self.btn_borrar = self.CreaBoton("Borrar", imagen_str="delete.png")
        self.btn_continuar = self.CreaBoton(
            "Hoja correcta → Continuar a validación", imagen_str="save.png"
        )
        self.btn_continuar.setProperty("role", "primary")
        self.btn_continuar.setMinimumHeight(42)
        self.btn_continuar.setCursor(Qt.PointingHandCursor)
        self.btn_continuar.setEnabled(False)
        self.btn_imprimir = self.CreaBoton("Vista previa PDF", imagen_str="printing.png")
        self.btn_imprimir.setProperty("role", "secondary")
        self.btn_imprimir.setEnabled(False)
        self.btn_imprimir.setMinimumHeight(42)
        self.btn_imprimir.setCursor(Qt.PointingHandCursor)
        self.btn_cerrar = self.CreaBoton("Cerrar", imagen_str="close.png")
        layout_botones.addWidget(self.btn_cargar)
        layout_botones.addWidget(self.btn_agregar)
        layout_botones.addWidget(self.btn_modificar)
        layout_botones.addWidget(self.btn_grabar)
        layout_botones.addWidget(self.btn_borrar)
        layout_botones.addStretch(1)
        layout_botones.addWidget(self.btn_continuar)
        layout_botones.addWidget(self.btn_imprimir)
        layout_botones.addWidget(self.btn_cerrar)
        layoutPpal.addLayout(layout_botones)

    def mostrar_recursos(self, chofer, camion):
        self.lbl_chofer.setText(chofer or "Chofer pendiente")
        self.lbl_camion.setText(camion or "Camión pendiente")

    @staticmethod
    def _set_role(boton, role):
        boton.setProperty("role", role)
        boton.style().unpolish(boton)
        boton.style().polish(boton)

    def mostrar_estado_operativo(
        self, estado, pedidos, kg, bultos, permitir_continuar=True,
        recursos_completos=True,
    ):
        if pedidos and not recursos_completos:
            texto_estado = (
                "Estado: REQUIERE CORRECCIÓN — Falta asignar chofer y/o camión"
            )
        else:
            textos = {
                "EN_PREPARACION": "Estado: EN PREPARACIÓN — Falta revisar y validar",
                "LISTA": "Estado: LISTA — Puede imprimir / despachar",
                "DESPACHADA": "Estado: DESPACHADA — Circuito operativo finalizado",
            }
            texto_estado = textos.get(
                estado, "Estado: {}".format(estado or "sin definir")
            )
        self.lbl_estado_operativo.setText(texto_estado)
        self.btn_recursos.setEnabled(bool(pedidos) and estado != "DESPACHADA")
        self.lbl_resumen_hoja.setText(
            "Pedidos: {} · KG: {} · Bultos: {}".format(pedidos, kg, bultos)
        )

        puede_continuar = (
            bool(pedidos)
            and recursos_completos
            and estado != "DESPACHADA"
            and permitir_continuar
        )
        self.btn_continuar.setEnabled(puede_continuar)
        self.btn_continuar.setVisible(permitir_continuar)
        self.btn_imprimir.setEnabled(bool(pedidos) and recursos_completos)

        if not recursos_completos:
            self.btn_continuar.setText("Asignar recursos antes de continuar")
            self.btn_imprimir.setText("PDF no disponible")
            self._set_role(self.btn_continuar, "secondary")
            self._set_role(self.btn_imprimir, "secondary")
        elif estado == "EN_PREPARACION":
            self.btn_continuar.setText("Hoja correcta → Continuar a validación")
            self.btn_imprimir.setText("Vista previa PDF")
            self._set_role(self.btn_continuar, "primary")
            self._set_role(self.btn_imprimir, "secondary")
        elif estado == "LISTA":
            self.btn_continuar.setText("Continuar a despacho")
            self.btn_imprimir.setText("Imprimir PDF")
            self._set_role(self.btn_continuar, "secondary")
            self._set_role(self.btn_imprimir, "primary")
        else:
            self.btn_imprimir.setText("Reimprimir PDF")
            self._set_role(self.btn_continuar, "secondary")
            self._set_role(self.btn_imprimir, "secondary")


class ModificaHojaDeRutaView(VistaBase):
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setupUi(self)
        
    def setupUi(self, Form):
        self.resize(600, 400)
        self.setWindowTitle("Modificar Hoja de Ruta")
        layout_ppal = QVBoxLayout(Form)
        
        layout_datos = QFormLayout()
        self.cliente = ValidaCliente()
        layout_datos.addRow(self.cliente)
        
        lbl_comprobante = Etiqueta(texto="Comprobante:")
        self.text_comprobante = EntradaTexto()
        layout_datos.addRow(lbl_comprobante, self.text_comprobante)
        
        lbl_factura = Etiqueta(texto="Factura importada:")
        self.text_factura = EntradaTexto()
        self.text_factura.setEnabled(False)
        layout_datos.addRow(lbl_factura, self.text_factura)

        lbl_remito = Etiqueta(texto="Remito:")
        self.text_remito = EntradaTexto()
        layout_datos.addRow(lbl_remito, self.text_remito)

        lbl_producto = Etiqueta(texto="Producto:")
        self.text_producto = EntradaTexto()
        layout_datos.addRow(lbl_producto, self.text_producto)
        
        lbl_cantidad = Etiqueta(texto="Cantidad:")
        self.text_cantidad = Spinner()
        layout_datos.addRow(lbl_cantidad, self.text_cantidad)
        
        lbl_kg = Etiqueta(texto="KG:")
        self.text_kg = Spinner()
        layout_datos.addRow(lbl_kg, self.text_kg)
        
        lbl_bultos = Etiqueta(texto="Bultos:")
        self.text_bultos = Spinner()
        layout_datos.addRow(lbl_bultos, self.text_bultos)
        
        lbl_observaciones = Etiqueta(texto="Observaciones:")
        self.text_observaciones = EntradaTexto()
        layout_datos.addRow(lbl_observaciones, self.text_observaciones)
        
        layout_ppal.addLayout(layout_datos)
        
        layout_botones = QHBoxLayout()
        self.btn_grabar = self.CreaBoton("Grabar", imagen_str="save.png")
        self.btn_cerrar = self.CreaBoton("Cerrar", imagen_str="close.png")
        layout_botones.addWidget(self.btn_grabar)
        layout_botones.addWidget(self.btn_cerrar)
        layout_ppal.addLayout(layout_botones)
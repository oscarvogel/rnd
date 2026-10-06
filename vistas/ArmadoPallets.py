from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup, QGroupBox, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSplitter, QTableWidget, QVBoxLayout, QWidget,
)
from modelos.Clientes import cboRutaReparto
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha
from pyqt5libs.pyqt5libs.Grillas import Grilla


class PalletSelector(QWidget):
    pallet_seleccionado = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actual_id = 0
        self.botones = {}
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(6)
        self._layout.setVerticalSpacing(6)

    def cargar(self, pallets, seleccionado=None):
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                self._grupo.removeButton(widget)
                widget.deleteLater()
        self.botones = {}
        self._actual_id = 0

        for posicion, (pallet_id, codigo) in enumerate(pallets, start=1):
            pallet_id = int(pallet_id)
            boton = QPushButton(str(posicion))
            boton.setCheckable(True)
            boton.setMinimumSize(44, 34)
            boton.setToolTip("Pallet {}\n{}".format(posicion, codigo))
            boton.setProperty("palletId", pallet_id)
            boton.setStyleSheet(
                "QPushButton { padding: 6px 10px; border: 1px solid #b8c2cc; "
                "border-radius: 8px; background: #ffffff; font-weight: 600; }"
                "QPushButton:hover { border-color: #4c84ff; }"
                "QPushButton:checked { background: #1976d2; color: white; "
                "border-color: #1976d2; }"
            )
            boton.clicked.connect(
                lambda checked=False, pid=pallet_id: self._seleccionar(pid)
            )
            self._grupo.addButton(boton)
            self.botones[pallet_id] = boton
            fila = (posicion - 1) // 10
            columna = (posicion - 1) % 10
            self._layout.addWidget(boton, fila, columna)

        if seleccionado and int(seleccionado) in self.botones:
            self._marcar(int(seleccionado), emitir=False)
        elif pallets:
            self._marcar(int(pallets[0][0]), emitir=False)

    def _marcar(self, pallet_id, emitir=True):
        boton = self.botones.get(int(pallet_id))
        if boton is None:
            self._actual_id = 0
            return
        boton.setChecked(True)
        self._actual_id = int(pallet_id)
        if emitir:
            self.pallet_seleccionado.emit(self._actual_id)

    def _seleccionar(self, pallet_id):
        self._marcar(pallet_id, emitir=True)

    def pallet_actual_id(self):
        return int(self._actual_id or 0)

    def cantidad(self):
        return len(self.botones)


class ArmadoPalletsView(VistaBase):

    COL_ID_PENDIENTE = "ID"
    COL_ID_CONTENIDO = "ID"

    CABECERAS_PENDIENTES = [
        "Cliente", "Comprobante", "Factura", "Producto",
        "Total", "Asignado", "Saldo", "Saldo KG", "Saldo bultos", "ID",
    ]
    CABECERAS_CONTENIDO = [
        "Producto", "Cliente", "Comprobante", "Cantidad",
        "KG", "Bultos", "ID",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi()

    def initUi(self):
        self.setWindowTitle("Armado de pallets")
        self.resize(1320, 800)
        layout_ppal = QVBoxLayout(self)

        self.lbl_titulo = QLabel("Armado de pallets")
        self.lbl_titulo.setObjectName("armadoPalletsTitulo")
        layout_ppal.addWidget(self.lbl_titulo)

        self.lbl_estado = QLabel("Seleccione fecha y ruta para cargar la mercadería.")
        self.lbl_estado.setObjectName("armadoPalletsEstado")
        self.lbl_estado.setWordWrap(True)
        layout_ppal.addWidget(self.lbl_estado)

        self.lbl_resumen = QLabel("Pallets: 0 · Líneas paletizadas: 0/0")
        self.lbl_resumen.setObjectName("armadoPalletsResumen")
        self.lbl_resumen.setWordWrap(True)
        layout_ppal.addWidget(self.lbl_resumen)

        layout_filtros = QHBoxLayout()
        layout_filtros.addWidget(Etiqueta(texto="Fecha de reparto:"))
        self.fecha_reparto = Fecha()
        layout_filtros.addWidget(self.fecha_reparto)
        layout_filtros.addWidget(Etiqueta(texto="Ruta de reparto:"))
        self.cbo_ruta_reparto = cboRutaReparto()
        layout_filtros.addWidget(self.cbo_ruta_reparto)
        self.btn_cargar = self.CreaBoton("Cargar mercadería", imagen_str="search.png")
        layout_filtros.addWidget(self.btn_cargar)
        layout_filtros.addStretch(1)
        layout_ppal.addLayout(layout_filtros)

        divisor = QSplitter(Qt.Horizontal)

        grp_pendientes = QGroupBox("Mercadería pendiente de preparar")
        layout_pend = QVBoxLayout(grp_pendientes)
        self.lbl_ayuda_pendientes = QLabel(
            "Seleccione una o más líneas y agréguelas al pallet. "
            "El saldo descuenta lo ya asignado a otros pallets."
        )
        self.lbl_ayuda_pendientes.setWordWrap(True)
        layout_pend.addWidget(self.lbl_ayuda_pendientes)
        self.grilla_pendientes = Grilla()
        self.grilla_pendientes.ArmaCabeceras(list(self.CABECERAS_PENDIENTES))
        self.grilla_pendientes.setSelectionMode(QTableWidget.ExtendedSelection)
        self.grilla_pendientes.setColumnHidden(
            self.CABECERAS_PENDIENTES.index("ID"), True
        )
        layout_pend.addWidget(self.grilla_pendientes)
        divisor.addWidget(grp_pendientes)

        grp_pallet = QGroupBox("Pallet actual")
        layout_pallet = QVBoxLayout(grp_pallet)
        fila_pallet = QHBoxLayout()
        fila_pallet.addWidget(QLabel("Pallets de esta carga:"))
        self.selector_pallets = PalletSelector()
        fila_pallet.addWidget(self.selector_pallets, 1)
        self.btn_nuevo_pallet = self.CreaBoton("Nuevo", imagen_str="new.png")
        fila_pallet.addWidget(self.btn_nuevo_pallet)
        layout_pallet.addLayout(fila_pallet)
        self.lbl_contexto = QLabel("")
        self.lbl_contexto.setWordWrap(True)
        layout_pallet.addWidget(self.lbl_contexto)
        self.grilla_contenido = Grilla()
        self.grilla_contenido.ArmaCabeceras(list(self.CABECERAS_CONTENIDO))
        self.grilla_contenido.setColumnHidden(
            self.CABECERAS_CONTENIDO.index("ID"), True
        )
        layout_pallet.addWidget(self.grilla_contenido)
        self.lbl_totales = QLabel("Pallet: 0 líneas · 0 cant · 0 KG · 0 bultos")
        self.lbl_totales.setObjectName("armadoPalletsTotales")
        self.lbl_totales.setWordWrap(True)
        layout_pallet.addWidget(self.lbl_totales)
        self.lbl_destinos = QLabel("")
        self.lbl_destinos.setObjectName("armadoPalletsDestinos")
        self.lbl_destinos.setWordWrap(True)
        layout_pallet.addWidget(self.lbl_destinos)
        divisor.addWidget(grp_pallet)

        divisor.setStretchFactor(0, 3)
        divisor.setStretchFactor(1, 2)
        layout_ppal.addWidget(divisor, 1)

        layout_botones = QHBoxLayout()
        self.btn_agregar = self.CreaBoton(
            "Agregar selección al pallet", imagen_str="save.png"
        )
        self.btn_agregar.setProperty("role", "primary")
        self.btn_parcial = self.CreaBoton(
            "Agregar parcial…", imagen_str="edit.png"
        )
        self.btn_quitar = self.CreaBoton(
            "Quitar del pallet", imagen_str="delete.png"
        )
        self.btn_etiqueta = self.CreaBoton(
            "Etiqueta / QR", imagen_str="printing.png"
        )
        self.btn_confirmar = self.CreaBoton(
            "Confirmar preparación", imagen_str="save.png"
        )
        self.btn_cerrar = self.CreaBoton("Cerrar", imagen_str="close.png")
        layout_botones.addWidget(self.btn_agregar)
        layout_botones.addWidget(self.btn_parcial)
        layout_botones.addWidget(self.btn_quitar)
        layout_botones.addWidget(self.btn_etiqueta)
        layout_botones.addStretch(1)
        layout_botones.addWidget(self.btn_confirmar)
        layout_botones.addWidget(self.btn_cerrar)
        layout_ppal.addLayout(layout_botones)

    def cargar_pendientes(self, filas):
        self.grilla_pendientes.limpiarGrilla()
        for fila in filas:
            self.grilla_pendientes.AgregaItem([
                str(fila.get("cliente") or ""), str(fila.get("comprobante") or ""),
                str(fila.get("factura") or ""), str(fila.get("producto") or ""),
                str(fila.get("total") or ""), str(fila.get("asignado") or ""),
                str(fila.get("saldo") or ""), str(fila.get("saldo_kg") or ""),
                str(fila.get("saldo_bultos") or ""), str(fila.get("hoja_ruta_id") or ""),
            ])
        self.grilla_pendientes.resizeColumnsToContents()

    def cargar_pallets(self, pallets, seleccionado=None):
        self.selector_pallets.cargar(pallets, seleccionado=seleccionado)

    def cantidad_pallets(self):
        return self.selector_pallets.cantidad()

    def mostrar_contexto(self, texto):
        self.lbl_contexto.setText(texto or "")

    def cargar_contenido(self, filas):
        self.grilla_contenido.limpiarGrilla()
        for fila in filas:
            self.grilla_contenido.AgregaItem([
                str(fila.get("producto") or ""), str(fila.get("cliente") or ""),
                str(fila.get("comprobante") or ""), str(fila.get("cantidad") or ""),
                str(fila.get("kg") or ""), str(fila.get("bultos") or ""),
                str(fila.get("hoja_ruta_id") or ""),
            ])
        self.grilla_contenido.resizeColumnsToContents()

    def mostrar_estado(self, texto):
        self.lbl_estado.setText(texto or "")

    def mostrar_resumen(self, texto):
        self.lbl_resumen.setText(texto or "")

    def mostrar_totales(self, totales, destinos):
        self.lbl_totales.setText(
            "Pallet: {} líneas · {} cant · {} KG · {} bultos".format(
                totales.get("lineas", 0), totales.get("cantidad", 0),
                totales.get("kg", 0), totales.get("bultos", 0),
            )
        )
        if destinos:
            self.lbl_destinos.setText(" · ".join(
                "{} / {}: {} cant".format(
                    d.get("cliente") or "Sin cliente",
                    d.get("lugar_entrega") or "Sin lugar",
                    d.get("cantidad", 0),
                ) for d in destinos
            ))
        else:
            self.lbl_destinos.setText("Pallet vacío: agregue líneas desde la mercadería pendiente.")

    def ids_pendientes_seleccionados(self):
        filas = sorted({indice.row() for indice in self.grilla_pendientes.selectedIndexes()})
        ids = []
        for fila in filas:
            try:
                ids.append(int(float(str(self.grilla_pendientes.ObtenerItem(fila, self.COL_ID_PENDIENTE)))))
            except (TypeError, ValueError):
                continue
        return ids

    def id_pendiente_en_fila(self, fila):
        try:
            return int(float(str(self.grilla_pendientes.ObtenerItem(fila, self.COL_ID_PENDIENTE))))
        except (TypeError, ValueError):
            return None

    def id_contenido_en_fila(self, fila):
        try:
            return int(float(str(self.grilla_contenido.ObtenerItem(fila, self.COL_ID_CONTENIDO))))
        except (TypeError, ValueError):
            return None

    def id_contenido_seleccionado(self):
        fila = self.grilla_contenido.filaSeleccionada()
        if fila == -1:
            return None
        try:
            return int(float(str(self.grilla_contenido.ObtenerItem(fila, self.COL_ID_CONTENIDO))))
        except (TypeError, ValueError):
            return None

    def pallet_actual_id(self):
        return self.selector_pallets.pallet_actual_id()

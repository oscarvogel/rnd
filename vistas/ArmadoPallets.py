from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QButtonGroup, QFrame, QGroupBox, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSplitter, QTableWidget, QVBoxLayout, QWidget,
)
from modelos.Clientes import cboRutaReparto
from pyqt5libs.libs.vistas.VistaBase import VistaBase
from pyqt5libs.pyqt5libs.Etiquetas import Etiqueta
from pyqt5libs.pyqt5libs.Fechas import Fecha
from pyqt5libs.pyqt5libs.Grillas import Grilla
from utiles.pallets import a_decimal, estado_limite_kg, formato_kg


class PalletSelector(QWidget):
    pallet_seleccionado = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._actual_id = 0
        self.botones = {}
        self.columnas_por_fila = 5
        self._grupo = QButtonGroup(self)
        self._grupo.setExclusive(True)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setHorizontalSpacing(6)
        self._layout.setVerticalSpacing(6)
        for columna in range(self.columnas_por_fila):
            self._layout.setColumnStretch(columna, 1)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

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
            boton.setMinimumSize(72, 40)
            boton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            boton.setToolTip("Pallet {}\n{}".format(posicion, codigo))
            boton.setProperty("palletId", pallet_id)
            boton.setStyleSheet(
                "QPushButton { padding: 7px 12px; border: 1px solid #b8c2cc; "
                "border-radius: 8px; background: #ffffff; font-weight: 700; }"
                "QPushButton:hover { border-color: #4c84ff; background: #f4f8ff; }"
                "QPushButton:checked { background: #173f68; color: white; "
                "border-color: #173f68; }"
            )
            boton.clicked.connect(
                lambda checked=False, pid=pallet_id: self._seleccionar(pid)
            )
            self._grupo.addButton(boton)
            self.botones[pallet_id] = boton
            fila = (posicion - 1) // self.columnas_por_fila
            columna = (posicion - 1) % self.columnas_por_fila
            self._layout.addWidget(boton, fila, columna)

        if seleccionado and int(seleccionado) in self.botones:
            self._marcar(int(seleccionado), emitir=False)
        elif pallets:
            self._marcar(int(pallets[0][0]), emitir=False)

        filas = max(1, (len(pallets) + self.columnas_por_fila - 1) // self.columnas_por_fila)
        self.setMinimumHeight(filas * 46)

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

    def posicion_actual(self):
        actual = self.pallet_actual_id()
        for posicion, pallet_id in enumerate(self.botones.keys(), start=1):
            if pallet_id == actual:
                return posicion
        return 0


class KpiPesoPallet(QFrame):
    """Bloque destacado con el peso total del pallet actual.

    El KG era un dato mas del resumen de abajo. Para el operador es el
    número que decide si el pallet se puede cerrar, asi que va con
    título propio y en cuerpo grande, arriba de la grilla de contenido.
    """

    TITULO = "KG ACTUALES"

    ESTILO_CARD = (
        "QFrame#armadoPalletsKpiPeso {"
        "  background: #f4f8ff; border: 1px solid #b8c2cc; border-radius: 8px; }"
    )
    COLOR_NAVY = "#173f68"
    COLOR_EXCESO = "#b91c1c"
    COLOR_DISPONIBLE = "#15803d"

    ESTILO_VALOR = (
        "color: {}; font-size: 40px; font-weight: 800; background: transparent;"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("armadoPalletsKpiPeso")
        self.setStyleSheet(self.ESTILO_CARD)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 12)
        layout.setSpacing(2)

        self.lbl_titulo = QLabel(self.TITULO)
        self.lbl_titulo.setObjectName("armadoPalletsKpiPesoTitulo")
        self.lbl_titulo.setStyleSheet(
            "color: #5a6b7c; font-size: 12px; font-weight: 700; background: transparent;"
        )
        layout.addWidget(self.lbl_titulo)

        fila_valor = QHBoxLayout()
        fila_valor.setSpacing(8)
        fila_valor.setContentsMargins(0, 0, 0, 0)
        self.lbl_valor = QLabel("0")
        self.lbl_valor.setObjectName("armadoPalletsKpiPesoValor")
        self.lbl_valor.setStyleSheet(self.ESTILO_VALOR.format(self.COLOR_NAVY))
        fila_valor.addWidget(self.lbl_valor)
        self.lbl_unidad = QLabel("KG")
        self.lbl_unidad.setObjectName("armadoPalletsKpiPesoUnidad")
        self.lbl_unidad.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.lbl_unidad.setStyleSheet(
            "color: #5a6b7c; font-size: 16px; font-weight: 700; padding-bottom: 6px;"
            " background: transparent;"
        )
        fila_valor.addWidget(self.lbl_unidad)
        fila_valor.addStretch(1)
        layout.addLayout(fila_valor)

        self.lbl_limite = QLabel("")
        self.lbl_limite.setObjectName("armadoPalletsKpiPesoLimite")
        self.lbl_limite.setWordWrap(True)
        self.lbl_limite.setStyleSheet(
            "color: #5a6b7c; font-size: 12px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(self.lbl_limite)

    def mostrar(self, kg, limite_kg=None):
        self.lbl_valor.setText(formato_kg(kg))
        estado = estado_limite_kg(kg, limite_kg)
        if estado is None:
            self.lbl_limite.setText("")
            self.lbl_valor.setStyleSheet(self.ESTILO_VALOR.format(self.COLOR_NAVY))
            return
        texto, excede = estado
        self.lbl_limite.setText(texto)
        self.lbl_valor.setStyleSheet(self.ESTILO_VALOR.format(
            self.COLOR_EXCESO if excede else self.COLOR_DISPONIBLE
        ))

    def texto_peso_actual(self):
        return "{} KG".format(self.lbl_valor.text())

    def texto_limite(self):
        return self.lbl_limite.text()


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
        self._kg_por_pallet = {}
        self._kg_actual = a_decimal(0)
        self._limite_kg_actual = None
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

        self.lbl_contexto = QLabel("")
        self.lbl_contexto.setWordWrap(True)
        layout_pallet.addWidget(self.lbl_contexto)

        self.btn_nuevo_pallet = self.CreaBoton("+ Nuevo pallet", imagen_str="new.png")
        self.btn_nuevo_pallet.setMinimumHeight(40)
        layout_pallet.addWidget(self.btn_nuevo_pallet)

        self.lbl_pallets = QLabel("Pallets:")
        self.lbl_pallets.setStyleSheet("font-weight: 600;")
        layout_pallet.addWidget(self.lbl_pallets)

        self.selector_pallets = PalletSelector()
        self.selector_pallets.pallet_seleccionado.connect(self._actualizar_pallet_actual)
        layout_pallet.addWidget(self.selector_pallets)

        self.lbl_pallet_actual = QLabel("PALLET ACTUAL: -")
        self.lbl_pallet_actual.setStyleSheet("font-size: 15px; font-weight: 800; padding: 4px 0;")
        layout_pallet.addWidget(self.lbl_pallet_actual)

        self.kpi_peso = KpiPesoPallet()
        layout_pallet.addWidget(self.kpi_peso)

        self.grilla_contenido = Grilla()
        self.grilla_contenido.ArmaCabeceras(list(self.CABECERAS_CONTENIDO))
        self.grilla_contenido.setColumnHidden(
            self.CABECERAS_CONTENIDO.index("ID"), True
        )
        self.grilla_contenido.setMinimumHeight(180)
        self.grilla_contenido.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout_pallet.addWidget(self.grilla_contenido, 1)

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
        pallets = list(pallets)
        ids_cargados = {int(pallet_id) for pallet_id, _codigo in pallets}
        self._kg_por_pallet = {
            pallet_id: kg for pallet_id, kg in self._kg_por_pallet.items()
            if pallet_id in ids_cargados
        }
        self.selector_pallets.cargar(pallets, seleccionado=seleccionado)
        self._actualizar_pallet_actual(self.selector_pallets.pallet_actual_id())

    def _actualizar_pallet_actual(self, pallet_id):
        posicion = self.selector_pallets.posicion_actual()
        texto = "PALLET ACTUAL: {}".format(posicion) if pallet_id and posicion else "PALLET ACTUAL: -"
        self.lbl_pallet_actual.setText(texto)
        self._pintar_kpi(pallet_id)

    def _pintar_kpi(self, pallet_id):
        kg = self._kg_por_pallet.get(int(pallet_id), 0) if pallet_id else 0
        self._kg_actual = a_decimal(kg)
        self.kpi_peso.mostrar(self._kg_actual, self._limite_kg_actual)

    def kg_pallet_actual(self):
        return self._kg_actual

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

    def mostrar_totales(self, totales, destinos, limite_kg=None):
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
        pallet_id = self.pallet_actual_id()
        self._limite_kg_actual = limite_kg if pallet_id else None
        if pallet_id:
            self._kg_por_pallet[pallet_id] = a_decimal(totales.get("kg"))
        self._pintar_kpi(pallet_id)

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

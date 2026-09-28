from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QVBoxLayout,
)
from pyqt5libs.libs.vistas.VistaBase import VistaBase


class ValidarCargaDialog(VistaBase):
    """Checklist de pallets esperados para validar la carga del camión."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initUi(self)

    def initUi(self, parent):
        self.resize(560, 480)
        self.setWindowTitle("Validar carga del camión")
        layout = QVBoxLayout(parent)

        ayuda = QLabel(
            "Tilde cada pallet a medida que se carga al camión. "
            "Al guardar, los tildados quedan CARGADO y los destildados "
            "vuelven a ARMADO."
        )
        ayuda.setWordWrap(True)
        layout.addWidget(ayuda)

        self.lbl_progreso = QLabel("Cargados 0/0 pallets.")
        self.lbl_progreso.setObjectName("validarCargaProgreso")
        layout.addWidget(self.lbl_progreso)

        self.lst_pallets = QListWidget()
        self.lst_pallets.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lst_pallets.itemChanged.connect(lambda _item: self.actualizar_progreso())
        layout.addWidget(self.lst_pallets)

        fila_buscar = QHBoxLayout()
        fila_buscar.addWidget(QLabel("Código:"))
        self.txt_codigo = QLineEdit()
        self.txt_codigo.setPlaceholderText("Ingrese o escanee el código del pallet")
        self.txt_codigo.returnPressed.connect(self._buscar_desde_texto)
        fila_buscar.addWidget(self.txt_codigo, 1)
        self.btn_buscar = self.CreaBoton("Buscar", imagen_str="search.png")
        self.btn_buscar.clicked.connect(self._buscar_desde_texto)
        fila_buscar.addWidget(self.btn_buscar)
        layout.addLayout(fila_buscar)

        botones = QHBoxLayout()
        botones.addStretch(1)
        self.btn_cancelar = self.CreaBoton("Cancelar", imagen_str="close.png")
        self.btn_guardar = self.CreaBoton("Guardar", imagen_str="save.png")
        botones.addWidget(self.btn_cancelar)
        botones.addWidget(self.btn_guardar)
        layout.addLayout(botones)

    def cargar_pallets(self, pallets):
        """pallets: lista de dicts {id, codigo, cargado, lineas}."""
        self.lst_pallets.blockSignals(True)
        try:
            self.lst_pallets.clear()
            for pallet in pallets:
                texto = "{} — {} líneas".format(
                    pallet.get("codigo"), pallet.get("lineas", 0)
                )
                self.lst_pallets.addItem(texto)
                item = self.lst_pallets.item(self.lst_pallets.count() - 1)
                item.setData(32, int(pallet.get("id")))
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(
                    Qt.Checked if pallet.get("cargado") else Qt.Unchecked
                )
        finally:
            self.lst_pallets.blockSignals(False)
        self.actualizar_progreso()

    def actualizar_progreso(self):
        total = self.lst_pallets.count()
        cargados = sum(
            1 for i in range(total)
            if self.lst_pallets.item(i).checkState() == Qt.Checked
        )
        self.lbl_progreso.setText(
            "Cargados {}/{} pallets.".format(cargados, total)
        )

    def seleccion(self):
        """Devuelve {pallet_id: cargado_bool} según lo tildado."""
        resultado = {}
        for i in range(self.lst_pallets.count()):
            item = self.lst_pallets.item(i)
            resultado[int(item.data(32))] = (
                item.checkState() == Qt.Checked
            )
        return resultado

    def marcar_codigo(self, codigo):
        """Tilda el pallet por código (ingreso manual o escáner)."""
        buscado = str(codigo or "").strip().upper()
        if not buscado:
            return False
        for i in range(self.lst_pallets.count()):
            item = self.lst_pallets.item(i)
            if str(item.text() or "").upper().startswith(buscado):
                item.setCheckState(Qt.Checked)
                self.lst_pallets.setCurrentRow(i)
                self.actualizar_progreso()
                return True
        return False

    def _buscar_desde_texto(self):
        if not self.marcar_codigo(self.txt_codigo.text()):
            self.txt_codigo.selectAll()
        else:
            self.txt_codigo.clear()

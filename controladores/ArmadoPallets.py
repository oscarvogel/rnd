from datetime import date
from decimal import Decimal, InvalidOperation

from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout

from modelos.Documentos import referencias_por_hojas
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import reconnect_if_needed
from modelos.Pallet import (
    ESTADO_ARMADO,
    Pallet,
    agregar_detalle,
    composicion_pallet,
    crear_pallet,
    lineas_con_saldo,
    quitar_detalle,
    totales_pallet,
    totales_por_destino,
)
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from utiles.pallets import a_decimal
from vistas.ArmadoPallets import ArmadoPalletsView


class ArmadoPalletsController(ControladorBase):
    """Pantalla guiada para armar y editar pallets (Issue #67, Epic #58)."""

    def __init__(self, fecha_inicial=None, ruta_inicial=0):
        super().__init__()
        self.view = ArmadoPalletsView()
        self.ruta_inicial = int(ruta_inicial or 0)
        self.hojas_actuales = []
        if fecha_inicial is not None:
            self.view.fecha_reparto.setFecha(fecha_inicial)
        self._seleccionar_ruta_inicial()
        self.conectarWidgets()
        self.view.showMaximized()
        if self.ruta_inicial:
            self.cargar_mercaderia()

    def _seleccionar_ruta_inicial(self):
        if not self.ruta_inicial:
            return
        combo = self.view.cbo_ruta_reparto
        if hasattr(combo, "setValor"):
            try:
                combo.setValor(self.ruta_inicial)
                return
            except Exception:
                pass
        try:
            for idx in range(combo.count()):
                if int(combo.itemData(idx) or 0) == self.ruta_inicial:
                    combo.setCurrentIndex(idx)
                    return
        except Exception:
            pass

    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.btn_cargar.clicked.connect(self.on_click_btn_cargar)
        self.view.btn_nuevo_pallet.clicked.connect(self.on_click_nuevo_pallet)
        self.view.cbo_pallet.currentIndexChanged.connect(self.on_cambio_pallet)
        self.view.btn_agregar.clicked.connect(self.on_click_btn_agregar)
        self.view.btn_parcial.clicked.connect(self.on_click_btn_parcial)
        self.view.btn_quitar.clicked.connect(self.on_click_btn_quitar)
        self.view.btn_confirmar.clicked.connect(self.on_click_btn_confirmar)

    def _ruta_seleccionada(self):
        try:
            return int(self.view.cbo_ruta_reparto.valor() or 0)
        except (TypeError, ValueError):
            return 0

    # --- Carga (métodos planos testeables; los slots delegan) ---

    def cargar_mercaderia(self):
        ruta_id = self._ruta_seleccionada()
        if not ruta_id:
            showAlert("Sistema", "Seleccione una ruta antes de cargar la mercadería.")
            return False
        fecha = self.view.fecha_reparto.valor()
        self.hojas_actuales = list(
            HojaDeRuta.select()
            .where(HojaDeRuta.fecha == fecha, HojaDeRuta.ruta == ruta_id)
            .order_by(HojaDeRuta.nombre_cliente, HojaDeRuta.producto)
        )
        if not self.hojas_actuales:
            self.view.cargar_pendientes([])
        else:
            referencias = referencias_por_hojas([h.id for h in self.hojas_actuales])
            saldos = lineas_con_saldo([h.id for h in self.hojas_actuales])
            self.view.cargar_pendientes(
                self.filas_pendientes(
                    self.hojas_actuales, referencias, saldos
                )
            )
        self.refrescar_pallets()
        self.actualizar_guias()
        return True

    @staticmethod
    def filas_pendientes(hojas, referencias, saldos):
        filas = []
        for hoja in hojas:
            referencia = referencias.get(hoja.id, {})
            saldo = saldos.get(hoja.id, {})
            total = a_decimal(hoja.cantidad)
            saldo_cantidad = a_decimal(saldo.get("cantidad"))
            filas.append({
                "hoja_ruta_id": hoja.id,
                "cliente": hoja.nombre_cliente or "",
                "comprobante": hoja.comprobante or "",
                "factura": referencia.get("factura") or hoja.comprobante or "",
                "producto": hoja.producto or "",
                "total": total,
                "asignado": total - saldo_cantidad,
                "saldo": saldo_cantidad,
                "saldo_kg": a_decimal(saldo.get("kg")),
                "saldo_bultos": a_decimal(saldo.get("bultos")),
            })
        return filas

    def refrescar_pallets(self, seleccionado=None):
        pallets = [
            (p.id, p.codigo)
            for p in Pallet.select()
            .where(Pallet.estado == ESTADO_ARMADO)
            .order_by(Pallet.id.desc())
        ]
        if seleccionado is None:
            seleccionado = self.view.pallet_actual_id()
        self.view.cargar_pallets(pallets, seleccionado=seleccionado)
        self.refrescar_contenido()

    def refrescar_contenido(self):
        pallet_id = self.view.pallet_actual_id()
        if not pallet_id:
            self.view.cargar_contenido([])
            self.view.mostrar_totales(
                {"lineas": 0, "cantidad": 0, "kg": 0, "bultos": 0}, []
            )
            return
        filas = composicion_pallet(pallet_id)
        self.view.cargar_contenido(filas)
        self.view.mostrar_totales(totales_pallet(pallet_id),
                                  totales_por_destino(pallet_id))

    def actualizar_guias(self):
        pendientes = self.view.grilla_pendientes.rowCount()
        if not self.hojas_actuales:
            self.view.mostrar_estado(
                "Sin mercadería para la fecha y ruta seleccionadas."
            )
        else:
            saldos = lineas_con_saldo([h.id for h in self.hojas_actuales])
            sin_saldo = sum(
                1 for hoja_id in saldos
                if a_decimal(saldos[hoja_id].get("cantidad")) <= 0
            )
            faltan = pendientes - sin_saldo
            if faltan > 0:
                self.view.mostrar_estado(
                    "Faltan {} líneas por paletizar. Siguiente paso: "
                    "seleccione líneas y agréguelas al pallet.".format(faltan)
                )
            else:
                self.view.mostrar_estado(
                    "Toda la mercadería ya está paletizada. Siguiente paso: "
                    "confirme la preparación o valide la carga."
                )
        total_lineas = sum(
            len(composicion_pallet(p.id))
            for p in Pallet.select().where(Pallet.estado == ESTADO_ARMADO)
        )
        self.view.mostrar_resumen(
            "Fecha: {} · Pallets armados: {} · Líneas en pallets: {}".format(
                self.view.fecha_reparto.valor(),
                self.view.cbo_pallet.count() - 1,
                total_lineas,
            )
        )

    def _pallet_activo(self, crear_si_falta=True):
        pallet_id = self.view.pallet_actual_id()
        pallet = Pallet.get_or_none(
            (Pallet.id == pallet_id) & (Pallet.estado == ESTADO_ARMADO)
        )
        if pallet is None and crear_si_falta:
            pallet = crear_pallet()
            self.refrescar_pallets(seleccionado=pallet.id)
        return pallet

    # --- Slots (delegan en los métodos planos) ---

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_cargar(self, *args, **kwargs):
        self.cargar_mercaderia()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_cambio_pallet(self, *args, **kwargs):
        self.refrescar_contenido()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_nuevo_pallet(self, *args, **kwargs):
        pallet = crear_pallet()
        self.refrescar_pallets(seleccionado=pallet.id)
        showAlert(
            "Sistema",
            "Pallet {} creado. Seleccione líneas pendientes y agréguelas.".format(
                pallet.codigo
            ),
        )
        self.actualizar_guias()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_agregar(self, *args, **kwargs):
        agregados, errores = self.agregar_lineas(
            self.view.ids_pendientes_seleccionados()
        )
        self.refrescar_contenido()
        self.cargar_mercaderia_sin_alertas()
        if errores:
            showAlert(
                "Sistema",
                "No se pudieron agregar {} líneas:\n\n{}".format(
                    len(errores), "\n".join(errores[:5])
                ),
            )
        elif agregados:
            self.actualizar_guias()
        else:
            showAlert("Sistema", "Seleccione al menos una línea con saldo disponible.")

    def agregar_lineas(self, hoja_ids):
        if not hoja_ids:
            return 0, []
        pallet = self._pallet_activo()
        if pallet is None:
            return 0, ["No hay un pallet activo."]
        agregados = 0
        errores = []
        for hoja_id in hoja_ids:
            try:
                agregar_detalle(pallet, hoja_id)
                agregados += 1
            except ValueError as exc:
                errores.append("Línea {}: {}".format(hoja_id, exc))
            except Exception as exc:
                errores.append("Línea {}: {}".format(hoja_id, exc))
        return agregados, errores

    def cargar_mercaderia_sin_alertas(self):
        """Recarga pendientes conservando el pallet (sin alertar por ruta)."""
        if not self._ruta_seleccionada() or not self.hojas_actuales:
            return
        fecha_ids = [h.id for h in self.hojas_actuales]
        self.hojas_actuales = list(
            HojaDeRuta.select()
            .where(HojaDeRuta.id.in_(fecha_ids))
            .order_by(HojaDeRuta.nombre_cliente, HojaDeRuta.producto)
        )
        referencias = referencias_por_hojas(fecha_ids)
        saldos = lineas_con_saldo(fecha_ids)
        self.view.cargar_pendientes(
            self.filas_pendientes(self.hojas_actuales, referencias, saldos)
        )
        self.actualizar_guias()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_parcial(self, *args, **kwargs):
        ids = self.view.ids_pendientes_seleccionados()
        if len(ids) != 1:
            showAlert(
                "Sistema",
                "Seleccione exactamente una línea para agregar una cantidad parcial.",
            )
            return
        from modelos.Pallet import saldo_linea

        saldo = saldo_linea(ids[0])
        dialogo = QDialog(self.view)
        dialogo.setWindowTitle("Agregar cantidad parcial")
        layout = QVBoxLayout(dialogo)
        form = QFormLayout()
        txt_cantidad = QLineEdit(str(saldo["cantidad"]))
        txt_kg = QLineEdit(str(saldo["kg"]))
        txt_bultos = QLineEdit(str(saldo["bultos"]))
        form.addRow("Cantidad (saldo: {}):".format(saldo["cantidad"]), txt_cantidad)
        form.addRow("KG (saldo: {}):".format(saldo["kg"]), txt_kg)
        form.addRow("Bultos (saldo: {}):".format(saldo["bultos"]), txt_bultos)
        layout.addLayout(form)
        botones = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        botones.accepted.connect(dialogo.accept)
        botones.rejected.connect(dialogo.reject)
        layout.addWidget(botones)
        if dialogo.exec_() != QDialog.Accepted:
            return
        try:
            cantidad = self._parse_decimal(txt_cantidad.text())
            kg = self._parse_decimal(txt_kg.text())
            bultos = self._parse_decimal(txt_bultos.text())
        except (InvalidOperation, ValueError):
            showAlert("Sistema", "Ingrese cantidades numéricas válidas.")
            return
        pallet = self._pallet_activo()
        if pallet is None:
            showAlert("Sistema", "No hay un pallet activo.")
            return
        try:
            agregar_detalle(pallet, ids[0], cantidad=cantidad, kg=kg, bultos=bultos)
        except ValueError as exc:
            showAlert("Sistema", str(exc))
            return
        self.refrescar_contenido()
        self.cargar_mercaderia_sin_alertas()

    @staticmethod
    def _parse_decimal(texto):
        return Decimal(str(texto or "0").strip().replace(",", "."))

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_quitar(self, *args, **kwargs):
        hoja_id = self.view.id_contenido_seleccionado()
        if not hoja_id:
            showAlert("Sistema", "Seleccione una línea del pallet para quitarla.")
            return
        pallet_id = self.view.pallet_actual_id()
        if not pallet_id:
            showAlert("Sistema", "No hay un pallet activo.")
            return
        quitar_detalle(pallet_id, hoja_id)
        self.refrescar_contenido()
        self.cargar_mercaderia_sin_alertas()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_confirmar(self, *args, **kwargs):
        pallet_id = self.view.pallet_actual_id()
        if not pallet_id:
            showAlert("Sistema", "Seleccione o cree un pallet para confirmar.")
            return
        pallet = Pallet.get_by_id(pallet_id)
        total = totales_pallet(pallet_id)
        destinos = totales_por_destino(pallet_id)
        if not total["lineas"]:
            showAlert("Sistema", "El pallet está vacío: agregue líneas antes de confirmar.")
            return
        detalle = "\n".join(
            "- {} / {}: {} cant".format(
                d.get("cliente") or "Sin cliente",
                d.get("lugar_entrega") or "Sin lugar",
                d.get("cantidad", 0),
            )
            for d in destinos
        )
        showAlert(
            "Sistema",
            "Pallet {} preparado: {} líneas, {} cant, {} KG, {} bultos.\n\n"
            "{}\n\nSiguiente paso: valide la carga del camión.".format(
                pallet.codigo, total["lineas"], total["cantidad"],
                total["kg"], total["bultos"], detalle,
            ),
        )
        self.actualizar_guias()

    def run(self):
        try:
            self.view.showMaximized()
        except Exception:
            pass

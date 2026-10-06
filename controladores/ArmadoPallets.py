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
    pallets_para_carga,
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
        self.contexto_carga = None
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
        self.view.selector_pallets.pallet_seleccionado.connect(self.on_cambio_pallet)
        self.view.btn_agregar.clicked.connect(self.on_click_btn_agregar)
        self.view.btn_parcial.clicked.connect(self.on_click_btn_parcial)
        self.view.btn_quitar.clicked.connect(self.on_click_btn_quitar)
        self.view.btn_etiqueta.clicked.connect(self.on_click_btn_etiqueta)
        self.view.btn_confirmar.clicked.connect(self.on_click_btn_confirmar)
        self.view.grilla_pendientes.cellDoubleClicked.connect(self.on_doble_click_pendiente)
        self.view.grilla_contenido.cellDoubleClicked.connect(self.on_doble_click_contenido)

    def _ruta_seleccionada(self):
        try:
            return int(self.view.cbo_ruta_reparto.valor() or 0)
        except (TypeError, ValueError):
            return 0

    def _resolver_contexto_carga(self):
        """Deriva fecha+ruta+chofer+equipo de las hojas visibles.

        Una fecha/ruta debe representar una única carga operativa en esta pantalla.
        Si hay más de una combinación chofer/equipo, se considera ambigua.
        """
        if not self.hojas_actuales:
            return None
        contextos = {
            (
                int(getattr(h, "responsable_id", 0) or 0),
                int(getattr(h, "equipo_asignado_id", 0) or 0),
            )
            for h in self.hojas_actuales
        }
        contextos.discard((0, 0))
        if len(contextos) != 1:
            return None
        responsable_id, equipo_id = next(iter(contextos))
        return {
            "fecha_reparto": self.view.fecha_reparto.valor(),
            "ruta_id": self._ruta_seleccionada(),
            "responsable_id": responsable_id,
            "equipo_id": equipo_id,
        }

    def _mostrar_contexto_carga(self):
        if not self.contexto_carga or not self.hojas_actuales:
            self.view.mostrar_contexto("")
            return
        hoja = self.hojas_actuales[0]
        try:
            chofer = str(hoja.responsable)
        except Exception:
            chofer = "#{}".format(self.contexto_carga["responsable_id"])
        try:
            equipo = str(hoja.equipo_asignado)
        except Exception:
            equipo = "#{}".format(self.contexto_carga["equipo_id"])
        self.view.mostrar_contexto(
            "Carga activa · Chofer: {} · Equipo: {}".format(chofer, equipo)
        )

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
        self.contexto_carga = self._resolver_contexto_carga()
        if not self.hojas_actuales:
            self.view.cargar_pendientes([])
            self._mostrar_contexto_carga()
        else:
            if self.contexto_carga is None:
                self.view.cargar_pendientes([])
                self.view.cargar_pallets([])
                self.view.mostrar_contexto("Carga ambigua: hay más de un chofer/equipo para la fecha y ruta.")
                showAlert(
                    "Sistema",
                    "La fecha y ruta seleccionadas contienen más de una combinación de "
                    "chofer/equipo. Corrija la asignación antes de armar pallets.",
                )
                return False
            referencias = referencias_por_hojas([h.id for h in self.hojas_actuales])
            saldos = lineas_con_saldo([h.id for h in self.hojas_actuales])
            self.view.cargar_pendientes(
                self.filas_pendientes(self.hojas_actuales, referencias, saldos)
            )
            self._mostrar_contexto_carga()
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

    def _pallets_contexto(self):
        if not self.contexto_carga:
            return []
        return pallets_para_carga(**self.contexto_carga)

    def refrescar_pallets(self, seleccionado=None):
        pallets_modelo = self._pallets_contexto()
        pallets = [(p.id, p.codigo) for p in pallets_modelo]
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
        self.view.mostrar_totales(totales_pallet(pallet_id), totales_por_destino(pallet_id))

    def actualizar_guias(self):
        pendientes = self.view.grilla_pendientes.rowCount()
        if not self.hojas_actuales:
            self.view.mostrar_estado("Sin mercadería para la fecha y ruta seleccionadas.")
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
        pallets = self._pallets_contexto()
        total_lineas = sum(len(composicion_pallet(p.id)) for p in pallets)
        self.view.mostrar_resumen(
            "Fecha: {} · Pallets armados: {} · Líneas en pallets: {}".format(
                self.view.fecha_reparto.valor(), self.view.cantidad_pallets(), total_lineas
            )
        )

    def _crear_pallet_en_contexto(self):
        if not self.contexto_carga:
            return None
        return crear_pallet(**self.contexto_carga)

    def _pallet_activo(self, crear_si_falta=True):
        pallet_id = self.view.pallet_actual_id()
        pallet = Pallet.get_or_none(
            (Pallet.id == pallet_id) & (Pallet.estado == ESTADO_ARMADO)
        )
        if pallet is None and crear_si_falta:
            pallet = self._crear_pallet_en_contexto()
            if pallet is not None:
                self.refrescar_pallets(seleccionado=pallet.id)
        return pallet

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
        pallet = self._crear_pallet_en_contexto()
        if pallet is None:
            showAlert("Sistema", "Cargue primero una fecha/ruta con chofer y equipo asignados.")
            return
        self.refrescar_pallets(seleccionado=pallet.id)
        showAlert(
            "Sistema",
            "Pallet {} creado para esta carga. Seleccione líneas pendientes y agréguelas.".format(
                pallet.codigo
            ),
        )
        self.actualizar_guias()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_agregar(self, *args, **kwargs):
        agregados, errores = self.agregar_lineas(self.view.ids_pendientes_seleccionados())
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

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_doble_click_pendiente(self, fila, columna):
        hoja_id = self.view.id_pendiente_en_fila(fila)
        if not hoja_id:
            return
        agregados, errores = self.agregar_lineas([hoja_id])
        if errores:
            showAlert("Sistema", errores[0])
            return
        if agregados:
            self.refrescar_contenido()
            self.cargar_mercaderia_sin_alertas()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_doble_click_contenido(self, fila, columna):
        hoja_id = self.view.id_contenido_en_fila(fila)
        pallet_id = self.view.pallet_actual_id()
        if not hoja_id or not pallet_id:
            return
        quitar_detalle(pallet_id, hoja_id)
        self.refrescar_contenido()
        self.cargar_mercaderia_sin_alertas()

    def agregar_lineas(self, hoja_ids):
        if not hoja_ids:
            return 0, []
        pallet = self._pallet_activo()
        if pallet is None:
            return 0, ["No hay un pallet activo para esta carga."]
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
        self.view.cargar_pendientes(self.filas_pendientes(self.hojas_actuales, referencias, saldos))
        self.actualizar_guias()

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_parcial(self, *args, **kwargs):
        ids = self.view.ids_pendientes_seleccionados()
        if len(ids) != 1:
            showAlert("Sistema", "Seleccione exactamente una línea para agregar una cantidad parcial.")
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

    def dialogo_etiqueta(self, pallet_id):
        from vistas.EtiquetaPallet import EtiquetaPalletDialog
        dialogo = EtiquetaPalletDialog()
        if not dialogo.mostrar_pallet(pallet_id):
            return None
        return dialogo

    def pdf_etiqueta(self, pallet_id, destino_pdf=None):
        import os
        from utiles.etiqueta_pallet import generar_pdf_etiqueta, generar_qr_png

        pallet = Pallet.get_by_id(pallet_id)
        total = totales_pallet(pallet_id)
        destinos = totales_por_destino(pallet_id)
        qr_png = generar_qr_png(pallet.codigo)
        ruta = generar_pdf_etiqueta(
            pallet.codigo, total, destinos, qr_png, destino_pdf=destino_pdf
        )
        try:
            os.startfile(ruta)
        except Exception:
            pass
        return ruta

    @inicializar_y_capturar_excepciones
    @reconnect_if_needed
    def on_click_btn_etiqueta(self, *args, **kwargs):
        pallet_id = self.view.pallet_actual_id()
        if not pallet_id:
            showAlert("Sistema", "Seleccione o cree un pallet para ver su etiqueta.")
            return
        dialogo = self.dialogo_etiqueta(pallet_id)
        if dialogo is None:
            showAlert("Sistema", "El pallet seleccionado ya no existe.")
            return
        dialogo.btn_pdf.clicked.connect(lambda: self.pdf_etiqueta(dialogo.pallet_actual_id()))
        dialogo.btn_cerrar.clicked.connect(dialogo.Cerrar)
        dialogo.exec_()

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
            ) for d in destinos
        )
        showAlert(
            "Sistema",
            "Pallet {} preparado: {} líneas, {} cant, {} KG, {} bultos.\n\n"
            "{}\n\nSiguiente paso: valide la carga del camión.".format(
                pallet.codigo, total["lineas"], total["cantidad"], total["kg"],
                total["bultos"], detalle,
            ),
        )
        self.actualizar_guias()

    def run(self):
        try:
            self.view.showMaximized()
        except Exception:
            pass

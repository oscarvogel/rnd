# coding=utf-8
from datetime import date
from decimal import Decimal

from modelos.Documentos import DocumentoPedidoDetalle, DocumentoPedidoHojaRuta
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import db, reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from vistas.PendientesEntrega import PendientesEntregaView


class PendientesEntregaController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = PendientesEntregaView()
        self.view.btn_actualizar.clicked.connect(self.cargar)
        self.view.btn_agregar_reparto.clicked.connect(self.agregar_al_reparto)

    def run(self):
        self.cargar()
        self.view.showMaximized()
        self.view.raise_()
        self.view.activateWindow()

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar(self, *args, **kwargs):
        filas = []
        detalles = list(
            DocumentoPedidoDetalle.select()
            .order_by(DocumentoPedidoDetalle.documento, DocumentoPedidoDetalle.id)
        )
        for detalle in detalles:
            asignaciones = list(
                DocumentoPedidoHojaRuta.select().where(
                    DocumentoPedidoHojaRuta.detalle == detalle.id
                )
            )
            entregado = sum(
                (Decimal(str(a.cantidad_asignada or 0)) for a in asignaciones),
                Decimal("0"),
            )
            original = Decimal(str(detalle.cantidad_original or 0))
            pendiente = original - entregado
            if pendiente <= 0:
                continue

            documento = detalle.documento
            cliente = documento.cliente
            lugar = ""
            if asignaciones:
                hoja = asignaciones[-1].hoja_ruta
                if hoja.lugar_entrega_id:
                    try:
                        lugar = hoja.lugar_entrega.nombre or ""
                    except Exception:
                        lugar = ""

            filas.append({
                "detalle_id": detalle.id,
                "factura": documento.numero_factura or documento.comprobante_origen or "",
                "cliente": cliente.razon_social if cliente is not None else "",
                "lugar": lugar,
                "producto": detalle.producto or "",
                "cantidad_original": original,
                "entregado": entregado,
                "pendiente": pendiente,
            })

        self.view.cargar(filas)


    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def agregar_al_reparto(self, *args, **kwargs):
        detalle_ids = self.view.detalles_seleccionados()
        if not detalle_ids:
            showAlert("Sistema", "Seleccione al menos un pendiente de entrega")
            return

        camion_generico = int(
            ParamSist.ObtenerParametro("CAMION_GENERICO", "1") or 1
        )
        empleado_generico = int(
            ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23") or 23
        )

        creados = 0
        sin_saldo = 0
        hoy = date.today()

        with db.atomic():
            for detalle in (
                DocumentoPedidoDetalle.select()
                .where(DocumentoPedidoDetalle.id.in_(detalle_ids))
            ):
                asignaciones = list(
                    DocumentoPedidoHojaRuta.select()
                    .where(DocumentoPedidoHojaRuta.detalle == detalle.id)
                    .order_by(DocumentoPedidoHojaRuta.id)
                )
                entregado = sum(
                    (Decimal(str(a.cantidad_asignada or 0)) for a in asignaciones),
                    Decimal("0"),
                )
                original = Decimal(str(detalle.cantidad_original or 0))
                pendiente = original - entregado
                if pendiente <= 0:
                    sin_saldo += 1
                    continue

                ultima_hoja = asignaciones[-1].hoja_ruta if asignaciones else None
                documento = detalle.documento
                cliente = documento.cliente

                if original > 0:
                    proporcion = pendiente / original
                else:
                    proporcion = Decimal("0")
                kg_pendientes = (Decimal(str(detalle.kg_original or 0)) * proporcion)
                bultos_pendientes = (
                    Decimal(str(detalle.bultos_original or 0)) * proporcion
                )

                hoja = HojaDeRuta.create(
                    fecha=hoy,
                    cliente=cliente,
                    nombre_cliente=(
                        cliente.razon_social
                        if cliente is not None
                        else (
                            ultima_hoja.nombre_cliente
                            if ultima_hoja is not None
                            else ""
                        )
                    ),
                    lugar_entrega=(
                        ultima_hoja.lugar_entrega_id
                        if ultima_hoja is not None
                        else None
                    ),
                    ruta=(
                        ultima_hoja.ruta_id
                        if ultima_hoja is not None
                        else None
                    ),
                    comprobante=(
                        documento.numero_factura
                        or documento.comprobante_origen
                        or ""
                    ),
                    producto=detalle.producto or "",
                    cantidad=pendiente,
                    kg=kg_pendientes,
                    cantidad_bultos=bultos_pendientes,
                    observaciones="Saldo pendiente de entrega",
                    equipo_asignado=camion_generico,
                    responsable=empleado_generico,
                )
                DocumentoPedidoHojaRuta.create(
                    detalle=detalle,
                    hoja_ruta=hoja,
                    cantidad_asignada=pendiente,
                    kg_asignados=kg_pendientes,
                    bultos_asignados=bultos_pendientes,
                )
                creados += 1

        if creados:
            showAlert(
                "Sistema",
                "{} pendiente(s) agregado(s) al reparto de hoy. "
                "Ahora aparecen en Organizar pedidos y deben pasar por "
                "Asignar recursos.".format(creados),
            )
        elif sin_saldo:
            showAlert("Sistema", "Los pendientes seleccionados ya no tienen saldo")

        self.cargar()

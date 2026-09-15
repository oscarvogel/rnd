# coding=utf-8
from decimal import Decimal

from modelos.Documentos import DocumentoPedidoDetalle, DocumentoPedidoHojaRuta
from modelos.ModeloBase import reconnect_if_needed
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from vistas.PendientesEntrega import PendientesEntregaView


class PendientesEntregaController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = PendientesEntregaView()
        self.view.btn_actualizar.clicked.connect(self.cargar)

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
                "factura": documento.numero_factura or documento.comprobante_origen or "",
                "cliente": cliente.razon_social if cliente is not None else "",
                "lugar": lugar,
                "producto": detalle.producto or "",
                "cantidad_original": original,
                "entregado": entregado,
                "pendiente": pendiente,
            })

        self.view.cargar(filas)

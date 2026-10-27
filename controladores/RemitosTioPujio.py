# coding=utf-8
"""Pantalla de cruce entre el Control de Pedidos y el Informe de Remitos."""

from dataclasses import replace

from PyQt5.QtWidgets import QMessageBox

from modelos.Documentos import (
    DocumentoPedido,
    asegurar_esquema_documentos,
    normalizar_numero_documento,
)
from modelos.Proveedores import Proveedor
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import openFileNameDialog
from utiles.remitos_tio_pujio import (
    ESTADO_ASIGNADO,
    ESTADO_AMBIGUO,
    ESTADO_SIN_PEDIDO,
    ESTADO_YA_TENIA_REMITO,
    cruzar_remitos,
    procesar_control_pedidos_para_cruce,
    procesar_informe_remitos,
    resumen_cruce,
)
from vistas.RemitosTioPujio import RemitosTioPujioView


ARCHIVOS_EXCEL = "Excel (*.xls;*.xlsx)"


class RemitosTioPujioController(ControladorBase):
    def __init__(self, proveedor_id=0, archivo_pedidos="", archivo_remitos=""):
        super().__init__()
        self.proveedor_id = int(proveedor_id or 0)
        self.view = RemitosTioPujioView()
        self.resultados = []
        self._pedidos_archivo = 0
        self._pedidos_sistema = 0
        self._proveedor_nombre = ""
        if archivo_pedidos:
            self.view.set_archivo_pedidos(archivo_pedidos)
        if archivo_remitos:
            self.view.set_archivo_remitos(archivo_remitos)
        self.conectarWidgets()

    def conectarWidgets(self):
        self.view.btn_pedidos.clicked.connect(self.seleccionar_pedidos)
        self.view.btn_remitos.clicked.connect(self.seleccionar_remitos)
        self.view.btn_cruzar.clicked.connect(self.cruzar)
        self.view.btn_grabar.clicked.connect(self.grabar)
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)

    def seleccionar_pedidos(self, *args, **kwargs):
        archivo = openFileNameDialog(
            title="Seleccionar Control de Pedidos",
            files=ARCHIVOS_EXCEL,
        )
        if archivo:
            self.view.set_archivo_pedidos(archivo)

    def seleccionar_remitos(self, *args, **kwargs):
        archivo = openFileNameDialog(
            title="Seleccionar Informe de Remitos",
            files=ARCHIVOS_EXCEL,
        )
        if archivo:
            self.view.set_archivo_remitos(archivo)

    def cruzar(self, *args, **kwargs):
        archivo_pedidos = self.view.archivo_pedidos()
        archivo_remitos = self.view.archivo_remitos()
        if not archivo_pedidos:
            showAlert("Sistema", "Seleccione el Control de Pedidos")
            return
        if not archivo_remitos:
            showAlert("Sistema", "Seleccione el Informe de Remitos")
            return

        try:
            pedidos = procesar_control_pedidos_para_cruce(archivo_pedidos)
            remitos = procesar_informe_remitos(archivo_remitos)
        except (ValueError, FileNotFoundError) as exc:
            showAlert("Sistema", str(exc))
            return
        except Exception as exc:
            showAlert(
                "Sistema",
                "No se pudieron leer los archivos: {}".format(exc),
            )
            return

        try:
            documentos = self._documentos_por_pedido(pedidos)
        except Exception as exc:
            showAlert(
                "Sistema",
                "No se pudieron leer los pedidos del sistema: {}".format(exc),
            )
            return

        pedidos_para_cruce = [
            replace(
                pedido,
                remito_actual=documentos[pedido.numero_pedido].numero_remito or "",
            )
            for pedido in pedidos
            if pedido.numero_pedido in documentos
        ]
        self._pedidos_archivo = len(pedidos)
        self._pedidos_sistema = len(pedidos_para_cruce)

        if not pedidos_para_cruce:
            self.resultados = []
            self.view.limpiar_resultados()
            self.view.set_resumen(
                "No se encontraron pedidos importados para este Control de "
                "Pedidos. Primero importe y grabe los pedidos."
            )
            self.view.set_estado(
                "No se encontraron pedidos importados para este Control de "
                "Pedidos. Primero importá y grabá los pedidos, y después "
                "volvé a cruzar los remitos.",
                "error",
            )
            self.view.set_grabar_habilitado(
                False,
                "Grabar remitos",
                "Primero importá y grabá los pedidos",
            )
            showAlert(
                "Sistema",
                "No hay pedidos importados para cruzar. "
                "Primero importe y grabe los pedidos.",
            )
            return

        self.resultados = cruzar_remitos(pedidos_para_cruce, remitos)
        self.view.cargar_resultados(self.resultados)
        self.view.set_resumen(self._texto_resumen(self.resultados))
        self._actualizar_estado_mensaje()
        self._actualizar_estado_grabar()

    def _documentos_por_pedido(self, pedidos):
        asegurar_esquema_documentos()
        numeros = {
            pedido.numero_pedido for pedido in pedidos if pedido.numero_pedido
        }
        if not numeros:
            return {}

        consulta = DocumentoPedido.select().where(
            DocumentoPedido.numero_factura.in_(list(numeros))
        )
        if self.proveedor_id:
            consulta = consulta.where(
                DocumentoPedido.proveedor == self.proveedor_id
            )
        documentos = list(consulta)
        if not documentos:
            return {}

        if not self.proveedor_id:
            # El Control de Pedidos no trae el proveedor. Se elige el que
            # tiene mas PED coincidentes en el sistema.
            conteo = {}
            for documento in documentos:
                proveedor_id = int(documento.proveedor_id or 0)
                if proveedor_id:
                    conteo[proveedor_id] = conteo.get(proveedor_id, 0) + 1
            if not conteo:
                return {}
            self.proveedor_id = max(conteo, key=conteo.get)

        self._proveedor_nombre = self._nombre_proveedor(self.proveedor_id)
        return {
            documento.numero_factura: documento
            for documento in documentos
            if int(documento.proveedor_id or 0) == self.proveedor_id
        }

    @staticmethod
    def _nombre_proveedor(proveedor_id):
        try:
            return Proveedor.get_by_id(proveedor_id).razon_social or ""
        except Exception:
            return ""

    def _texto_resumen(self, resultados):
        resumen = resumen_cruce(resultados)
        ya_estaban = sum(
            1
            for resultado in resultados
            if resultado.estado == ESTADO_ASIGNADO
            and resultado.motivo == "ya estaba asociado"
        )
        nuevos = resumen[ESTADO_ASIGNADO] - ya_estaban
        faltan = self._pedidos_archivo - self._pedidos_sistema
        texto = (
            "Remitos: {total} · Para grabar: {nuevos} · Ya estaban: {ya} · "
            "Revisar: {ambiguo} · Sin pedido: {sin} · "
            "Ya tenían otro remito: {otro} · "
            "Pedidos en el sistema: {sistema}/{archivo}"
        ).format(
            total=resumen["total"],
            nuevos=nuevos,
            ya=ya_estaban,
            ambiguo=resumen[ESTADO_AMBIGUO],
            sin=resumen[ESTADO_SIN_PEDIDO],
            otro=resumen[ESTADO_YA_TENIA_REMITO],
            sistema=self._pedidos_sistema,
            archivo=self._pedidos_archivo,
        )
        if faltan > 0:
            texto += " · Faltan importar {} pedido(s)".format(faltan)
        if nuevos == 0 and ya_estaban > 0:
            texto += " · No hay cambios pendientes"
        if self._proveedor_nombre:
            texto = "Proveedor: {} · {}".format(self._proveedor_nombre, texto)
        return texto

    def _hay_para_grabar(self):
        return any(
            resultado.estado == ESTADO_ASIGNADO
            and resultado.pedido is not None
            and resultado.motivo != "ya estaba asociado"
            for resultado in self.resultados
        )

    def _actualizar_estado_mensaje(self):
        if not self.resultados:
            self.view.set_estado(
                "Seleccioná los dos archivos y presioná «Leer y cruzar».",
                "info",
            )
            return

        resumen = resumen_cruce(self.resultados)
        nuevos = sum(
            1
            for resultado in self.resultados
            if resultado.estado == ESTADO_ASIGNADO
            and resultado.motivo != "ya estaba asociado"
        )
        ya_estaban = sum(
            1
            for resultado in self.resultados
            if resultado.estado == ESTADO_ASIGNADO
            and resultado.motivo == "ya estaba asociado"
        )
        problemas = (
            resumen[ESTADO_AMBIGUO]
            + resumen[ESTADO_SIN_PEDIDO]
            + resumen[ESTADO_YA_TENIA_REMITO]
        )

        if nuevos:
            texto = "Hay {} remito(s) para grabar.".format(nuevos)
            if problemas:
                texto += " Revisá también {} caso(s) marcados para revisión.".format(
                    problemas
                )
            else:
                texto += " Revisá la grilla y presioná «Grabar remitos»."
            self.view.set_estado(texto, "pendiente")
            return

        if ya_estaban and not problemas:
            self.view.set_estado(
                "Los {} remitos ya estaban asociados a los pedidos. "
                "No hay cambios pendientes para grabar.".format(ya_estaban),
                "ok",
            )
            return

        if problemas:
            self.view.set_estado(
                "No hay remitos nuevos para grabar. Revisá los {} caso(s) "
                "marcados para revisión.".format(problemas),
                "error",
            )
            return

        self.view.set_estado("No hay remitos para grabar.", "info")

    def _actualizar_estado_grabar(self):
        if self._hay_para_grabar():
            self.view.set_grabar_habilitado(
                True,
                "Grabar remitos",
                "Asociar los remitos asignados a los pedidos",
            )
            return
        if self.resultados and all(
            resultado.estado == ESTADO_ASIGNADO
            and resultado.motivo == "ya estaba asociado"
            for resultado in self.resultados
        ):
            self.view.set_grabar_habilitado(
                False,
                "Todo guardado",
                "Los remitos ya estaban asociados a los pedidos",
            )
            return
        self.view.set_grabar_habilitado(
            False,
            "Grabar remitos",
            "No hay remitos nuevos para grabar",
        )

    def grabar(self, *args, **kwargs):
        pendientes = [
            resultado
            for resultado in self.resultados
            if resultado.estado == ESTADO_ASIGNADO
            and resultado.pedido is not None
            and resultado.motivo != "ya estaba asociado"
        ]
        if not pendientes:
            showAlert("Sistema", "No hay remitos nuevos para grabar")
            return

        respuesta = QMessageBox.question(
            self.view,
            "Confirmar",
            "¿Grabar {} remito(s) en los pedidos?".format(len(pendientes)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if respuesta != QMessageBox.Yes:
            return

        actualizados = 0
        errores = 0
        for resultado in pendientes:
            try:
                actualizados += DocumentoPedido.update(
                    numero_remito=normalizar_numero_documento(
                        resultado.remito.numero_remito
                    )
                ).where(
                    (DocumentoPedido.proveedor == self.proveedor_id)
                    & (
                        DocumentoPedido.numero_factura
                        == resultado.pedido.numero_pedido
                    )
                ).execute()
            except Exception as exc:
                errores += 1
                print(
                    "[RemitosTioPujio] Error al grabar {}: {}".format(
                        resultado.remito.numero_remito, exc
                    )
                )

        showAlert(
            "Sistema",
            "Remitos grabados: {}. Errores: {}.".format(actualizados, errores),
        )
        if actualizados:
            self.cruzar()

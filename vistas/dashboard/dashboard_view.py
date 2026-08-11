# coding=utf-8
"""Vista principal del dashboard operativo."""

from datetime import date

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

from utiles.dashboard_flujo import ACCION_COMPLETO
from vistas.dashboard import servicios
from vistas.dashboard.ejecutor import EjecutorConsultasQt
from vistas.dashboard.flujo_servicio import obtener_estado_flujo
from vistas.dashboard.tarjeta import TarjetaDashboard, TarjetaHero


NAV_IMPORTAR_PEDIDOS = "importar_pedidos"
NAV_ORGANIZAR_PEDIDOS = "organizar_pedidos"
NAV_HOJAS_RUTA_DIA = "hojas_ruta_dia"
NAV_PENDIENTES = "hojas_ruta_pendientes"
NAV_VENCIMIENTOS = "vencimientos"
NAV_ALERTAS = "alertas_vencidas"


class DashboardView(QWidget):
    navegar = pyqtSignal(str)

    def __init__(self, usu_id, parent=None, ejecutor=None):
        super().__init__(parent)
        self.setObjectName("dashboardRoot")
        self._usu_id = int(usu_id or 0)
        self._ejecutor = ejecutor or EjecutorConsultasQt()
        self._accion_flujo = NAV_IMPORTAR_PEDIDOS
        self._ruta_recomendada = 0
        self._build_ui()

    def _build_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        raiz.setSpacing(16)

        cabecera = QWidget()
        cabecera.setObjectName("dashboardCabecera")
        layout_cabecera = QHBoxLayout(cabecera)
        textos = QVBoxLayout()
        titulo = QLabel("Resumen operativo")
        titulo.setObjectName("dashboardTitulo")
        textos.addWidget(titulo)
        subtitulo = QLabel("Estado del día {}".format(date.today().strftime("%d/%m/%Y")))
        subtitulo.setObjectName("dashboardSubtitulo")
        textos.addWidget(subtitulo)
        layout_cabecera.addLayout(textos)
        layout_cabecera.addStretch(1)
        self.boton_recargar = QPushButton("Actualizar")
        self.boton_recargar.setProperty("role", "secondary")
        self.boton_recargar.clicked.connect(self.recargar)
        layout_cabecera.addWidget(self.boton_recargar)
        raiz.addWidget(cabecera)

        siguiente = QWidget()
        siguiente.setObjectName("dashboardSiguientePaso")
        layout_siguiente = QVBoxLayout(siguiente)
        self.lbl_siguiente_epigrafe = QLabel("SIGUIENTE PASO")
        self.lbl_siguiente_epigrafe.setObjectName("dashboardSiguienteEpigrafe")
        layout_siguiente.addWidget(self.lbl_siguiente_epigrafe)
        self.lbl_siguiente_titulo = QLabel("Calculando estado del reparto…")
        self.lbl_siguiente_titulo.setObjectName("dashboardAccionTitulo")
        layout_siguiente.addWidget(self.lbl_siguiente_titulo)
        self.lbl_siguiente_detalle = QLabel("")
        self.lbl_siguiente_detalle.setWordWrap(True)
        self.lbl_siguiente_detalle.setObjectName("dashboardAccionDetalle")
        layout_siguiente.addWidget(self.lbl_siguiente_detalle)

        progreso = QHBoxLayout()
        self.labels_pasos = []
        for texto in ("1. Importar", "2. Revisar", "3. Organizar", "4. Asignar recursos", "5. Validar / despachar"):
            label = QLabel(texto)
            label.setObjectName("dashboardPaso")
            progreso.addWidget(label)
            self.labels_pasos.append(label)
        layout_siguiente.addLayout(progreso)

        fila_accion = QHBoxLayout()
        self.lbl_indicadores_flujo = QLabel("")
        self.lbl_indicadores_flujo.setWordWrap(True)
        fila_accion.addWidget(self.lbl_indicadores_flujo, stretch=1)
        self.btn_siguiente = QPushButton("Abrir")
        self.btn_siguiente.setProperty("role", "primary")
        self.btn_siguiente.setCursor(Qt.PointingHandCursor)
        self.btn_siguiente.clicked.connect(self._emitir_siguiente)
        fila_accion.addWidget(self.btn_siguiente)
        layout_siguiente.addLayout(fila_accion)
        raiz.addWidget(siguiente)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        raiz.addWidget(scroll)
        contenido = QWidget()
        contenido.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid = QGridLayout(contenido)
        grid.setSpacing(16)

        self.hero = TarjetaHero("Hojas de ruta del día")
        self.hero.clicked.connect(lambda: self.navegar.emit(NAV_HOJAS_RUTA_DIA))
        self.hero.conectar_reintentar(self._cargar_hero)
        grid.addWidget(self.hero, 0, 0, 1, 2)

        self.tarjeta_pendientes = TarjetaDashboard("Pendientes de asignación")
        self.tarjeta_pendientes.clicked.connect(lambda: self.navegar.emit(NAV_PENDIENTES))
        self.tarjeta_pendientes.conectar_reintentar(self._cargar_pendientes)
        grid.addWidget(self.tarjeta_pendientes, 1, 0)

        self.tarjeta_vencimientos = TarjetaDashboard("Vencimientos próximos")
        self.tarjeta_vencimientos.clicked.connect(lambda: self.navegar.emit(NAV_VENCIMIENTOS))
        self.tarjeta_vencimientos.conectar_reintentar(self._cargar_vencimientos)
        grid.addWidget(self.tarjeta_vencimientos, 1, 1)

        self.tarjeta_alertas = TarjetaDashboard("Alertas vencidas")
        self.tarjeta_alertas.clicked.connect(lambda: self.navegar.emit(NAV_ALERTAS))
        self.tarjeta_alertas.conectar_reintentar(self._cargar_alertas)
        grid.addWidget(self.tarjeta_alertas, 1, 2)
        scroll.setWidget(contenido)

    def cargar(self):
        self._cargar_flujo()
        self._cargar_hero()
        self._cargar_pendientes()
        self._cargar_vencimientos()
        self._cargar_alertas()

    def recargar(self):
        self.cargar()

    def _cargar_flujo(self):
        self.lbl_siguiente_titulo.setText("Calculando estado del reparto…")
        self.btn_siguiente.setEnabled(False)
        self._ejecutor.ejecutar(
            lambda: obtener_estado_flujo(self._usu_id),
            self._aplicar_flujo,
            self._error_flujo,
        )

    def _aplicar_flujo(self, estado):
        if estado is None:
            self.lbl_siguiente_titulo.setText("Flujo operativo no disponible")
            self.lbl_siguiente_detalle.setText("No hay permiso para consultar esta operación.")
            self.btn_siguiente.setEnabled(False)
            return
        self._accion_flujo = estado.accion
        self._ruta_recomendada = estado.ruta_recomendada
        self.lbl_siguiente_titulo.setText(estado.titulo_accion)
        self.lbl_siguiente_detalle.setText(estado.detalle_accion)
        self.btn_siguiente.setText(estado.titulo_accion)
        self.btn_siguiente.setEnabled(estado.accion != ACCION_COMPLETO)
        for label, (texto, estado_paso) in zip(self.labels_pasos, estado.pasos()):
            simbolo = "✓" if estado_paso == "completo" else ("!" if estado_paso == "atencion" else "○")
            label.setText("{} {}".format(simbolo, texto))
            label.setProperty("estado", estado_paso)
            label.style().unpolish(label)
            label.style().polish(label)
        self.lbl_indicadores_flujo.setText(
            "Pedidos: {0} · Sin ruta: {1} · Hojas sin recursos: {2} · "
            "Por validar: {3} · Listas: {4} · Despachadas: {5}".format(
                estado.pedidos, estado.sin_ruta, estado.incompletos_recursos,
                estado.en_preparacion_completos, estado.listas, estado.despachadas,
            )
        )

    def _error_flujo(self, exc):
        self.lbl_siguiente_titulo.setText("No se pudo calcular el siguiente paso")
        self.lbl_siguiente_detalle.setText(str(exc))
        self.btn_siguiente.setEnabled(False)

    def _emitir_siguiente(self):
        clave = self._accion_flujo
        if self._ruta_recomendada:
            clave = "{}|{}".format(clave, self._ruta_recomendada)
        self.navegar.emit(clave)

    def _cargar_hero(self):
        self.hero.mostrar_cargando()
        self._ejecutor.ejecutar(
            lambda: servicios.hojas_ruta_del_dia(self._usu_id),
            lambda resultado: self._aplicar_resultado(self.hero, resultado, True),
            lambda exc: self.hero.mostrar_error(str(exc)),
        )

    def _cargar_vencimientos(self):
        self.tarjeta_vencimientos.mostrar_cargando()
        self._ejecutor.ejecutar(
            lambda: servicios.vencimientos_proximos(self._usu_id),
            lambda resultado: self._aplicar_resultado(self.tarjeta_vencimientos, resultado, False),
            lambda exc: self.tarjeta_vencimientos.mostrar_error(str(exc)),
        )

    def _cargar_pendientes(self):
        self.tarjeta_pendientes.mostrar_cargando()
        self._ejecutor.ejecutar(
            lambda: servicios.hojas_ruta_pendientes(self._usu_id),
            lambda resultado: self._aplicar_resultado(self.tarjeta_pendientes, resultado, False),
            lambda exc: self.tarjeta_pendientes.mostrar_error(str(exc)),
        )

    def _cargar_alertas(self):
        self.tarjeta_alertas.mostrar_cargando()
        self._ejecutor.ejecutar(
            lambda: servicios.alertas_vencidas(self._usu_id),
            lambda resultado: self._aplicar_resultado(self.tarjeta_alertas, resultado, False),
            lambda exc: self.tarjeta_alertas.mostrar_error(str(exc)),
        )

    def _aplicar_resultado(self, tarjeta, resultado, alto_impacto):
        if not resultado.es_visible:
            tarjeta.setVisible(False)
            return
        tarjeta.setVisible(True)
        if resultado.es_error:
            tarjeta.mostrar_error(resultado.detalle)
        elif resultado.es_vacio:
            tarjeta.mostrar_vacio()
        else:
            detalle = ""
            if alto_impacto and resultado.fecha:
                detalle = "Fecha: {}".format(resultado.fecha.isoformat())
            tarjeta.mostrar_ok(resultado.cantidad, detalle=detalle)

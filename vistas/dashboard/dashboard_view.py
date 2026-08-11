# coding=utf-8
"""Vista principal del dashboard operativo."""

from datetime import date

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from vistas.dashboard import servicios
from vistas.dashboard.ejecutor import EjecutorConsultasQt
from vistas.dashboard.tarjeta import TarjetaDashboard, TarjetaHero


NAV_IMPORTAR_PEDIDOS = "importar_pedidos"
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
        self._build_ui()

    def _build_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        raiz.setSpacing(16)

        cabecera = QWidget()
        cabecera.setObjectName("dashboardCabecera")
        layout_cabecera = QHBoxLayout(cabecera)
        layout_cabecera.setContentsMargins(0, 0, 0, 0)
        layout_cabecera.setSpacing(12)

        textos = QVBoxLayout()
        textos.setContentsMargins(0, 0, 0, 0)
        textos.setSpacing(2)
        titulo = QLabel("Resumen operativo")
        titulo.setObjectName("dashboardTitulo")
        textos.addWidget(titulo)
        subtitulo = QLabel(
            "Estado del dia {}".format(date.today().strftime("%d/%m/%Y"))
        )
        subtitulo.setObjectName("dashboardSubtitulo")
        textos.addWidget(subtitulo)
        layout_cabecera.addLayout(textos)
        layout_cabecera.addStretch(1)

        self.boton_recargar = QPushButton("Actualizar")
        self.boton_recargar.setObjectName("dashboardBotonRecargar")
        self.boton_recargar.setProperty("role", "secondary")
        self.boton_recargar.setCursor(Qt.PointingHandCursor)
        self.boton_recargar.clicked.connect(self.recargar)
        layout_cabecera.addWidget(self.boton_recargar)
        raiz.addWidget(cabecera)

        # Acción operativa inicial del nuevo circuito guiado (#20).
        acceso_importar = QWidget()
        acceso_importar.setObjectName("dashboardAccionImportar")
        fila_importar = QHBoxLayout(acceso_importar)
        fila_importar.setContentsMargins(16, 12, 16, 12)
        textos_importar = QVBoxLayout()
        titulo_importar = QLabel("Preparar reparto")
        titulo_importar.setObjectName("dashboardAccionTitulo")
        textos_importar.addWidget(titulo_importar)
        detalle_importar = QLabel(
            "Comenzá importando los pedidos del proveedor. RND te va a guiar hasta dejarlos listos para organizar."
        )
        detalle_importar.setWordWrap(True)
        detalle_importar.setObjectName("dashboardAccionDetalle")
        textos_importar.addWidget(detalle_importar)
        fila_importar.addLayout(textos_importar, stretch=1)
        self.boton_importar = QPushButton("Importar pedidos")
        self.boton_importar.setObjectName("dashboardBotonImportar")
        self.boton_importar.setProperty("role", "primary")
        self.boton_importar.setCursor(Qt.PointingHandCursor)
        self.boton_importar.clicked.connect(
            lambda: self.navegar.emit(NAV_IMPORTAR_PEDIDOS)
        )
        fila_importar.addWidget(self.boton_importar)
        raiz.addWidget(acceso_importar)

        scroll = QScrollArea()
        scroll.setObjectName("dashboardScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        raiz.addWidget(scroll)

        contenido = QWidget()
        contenido.setObjectName("dashboardContenido")
        contenido.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid = QGridLayout(contenido)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(16)

        self.hero = TarjetaHero("Hojas de ruta del dia")
        self.hero.clicked.connect(lambda: self.navegar.emit(NAV_HOJAS_RUTA_DIA))
        self.hero.conectar_reintentar(self._cargar_hero)
        grid.addWidget(self.hero, 0, 0, 1, 2)

        self.tarjeta_pendientes = TarjetaDashboard("Pendientes de asignacion")
        self.tarjeta_pendientes.clicked.connect(
            lambda: self.navegar.emit(NAV_PENDIENTES)
        )
        self.tarjeta_pendientes.conectar_reintentar(self._cargar_pendientes)
        grid.addWidget(self.tarjeta_pendientes, 1, 0)

        self.tarjeta_vencimientos = TarjetaDashboard("Vencimientos proximos")
        self.tarjeta_vencimientos.clicked.connect(
            lambda: self.navegar.emit(NAV_VENCIMIENTOS)
        )
        self.tarjeta_vencimientos.conectar_reintentar(self._cargar_vencimientos)
        grid.addWidget(self.tarjeta_vencimientos, 1, 1)

        self.tarjeta_alertas = TarjetaDashboard("Alertas vencidas")
        self.tarjeta_alertas.clicked.connect(
            lambda: self.navegar.emit(NAV_ALERTAS)
        )
        self.tarjeta_alertas.conectar_reintentar(self._cargar_alertas)
        grid.addWidget(self.tarjeta_alertas, 1, 2)

        grid.setRowStretch(0, 2)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        scroll.setWidget(contenido)

    def cargar(self):
        self._cargar_hero()
        self._cargar_pendientes()
        self._cargar_vencimientos()
        self._cargar_alertas()

    def recargar(self):
        self.cargar()

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
            lambda resultado: self._aplicar_resultado(
                self.tarjeta_vencimientos, resultado, False
            ),
            lambda exc: self.tarjeta_vencimientos.mostrar_error(str(exc)),
        )

    def _cargar_pendientes(self):
        self.tarjeta_pendientes.mostrar_cargando()
        self._ejecutor.ejecutar(
            lambda: servicios.hojas_ruta_pendientes(self._usu_id),
            lambda resultado: self._aplicar_resultado(
                self.tarjeta_pendientes, resultado, False
            ),
            lambda exc: self.tarjeta_pendientes.mostrar_error(str(exc)),
        )

    def _cargar_alertas(self):
        self.tarjeta_alertas.mostrar_cargando()
        self._ejecutor.ejecutar(
            lambda: servicios.alertas_vencidas(self._usu_id),
            lambda resultado: self._aplicar_resultado(
                self.tarjeta_alertas, resultado, False
            ),
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

# coding=utf-8
"""Vista principal del dashboard operativo (issue #4).

Compone:

* Hero card: "Hojas de ruta del dia" (jerarquia maxima).
* Tarjetas secundarias: vencimientos proximos y otros indicadores
  que tengan datos confiables.

Reglas que se cumplen aca:

* Permisos: cada tarjeta consulta su servicio. Si el servicio
  retorna ``sin_permiso``, la tarjeta se oculta y NO se emite
  navegacion. Asi una tarjeta oculta nunca ejecuta la query ni
  revela su cantidad (requisito de #4).
* Estados: cada tarjeta expone ``mostrar_cargando``,
  ``mostrar_ok``, ``mostrar_vacio`` y ``mostrar_error`` para que
  un fallo parcial no impida mostrar el resto.
* Falla tolerante: la carga se hace en orden y un fallo de un
  servicio no impide abrir el dashboard. ``cargar`` retorna
  incluso si todas las consultas fallan.
* Recarga manual: el dashboard expone ``recargar()`` para
  reintento desde la UI o al volver al inicio.
* Foco/teclado: las tarjetas son focusables y se activan con
  ``Enter`` o ``Space`` (requisito de #4).
"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QGridLayout,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from vistas.dashboard import servicios
from vistas.dashboard.tarjeta import TarjetaDashboard, TarjetaHero


# Claves de navegacion que las tarjetas pueden emitir.
NAV_HOJAS_RUTA_DIA = "hojas_ruta_dia"
NAV_VENCIMIENTOS = "vencimientos"


class DashboardView(QWidget):
    """Contenedor del dashboard operativo."""

    # Senal emitida al hacer click en una tarjeta accionable.
    # El argumento es una clave que identifica el destino de
    # navegacion (ver constantes ``NAV_*`` arriba).
    navegar = pyqtSignal(str)

    def __init__(self, usu_id, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardRoot")
        self._usu_id = int(usu_id or 0)
        self._build_ui()

    # ------------------------------------------------------------------
    # Construccion de UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(24, 24, 24, 24)
        raiz.setSpacing(16)

        # Scroll para que el dashboard siga siendo usable en
        # pantallas chicas / escalado alto de Windows.
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

        # Hero: ocupa el ancho completo en la primera fila.
        self.hero = TarjetaHero("Hojas de ruta del dia")
        self.hero.clicked.connect(
            lambda: self.navegar.emit(NAV_HOJAS_RUTA_DIA)
        )
        self.hero.conectar_reintentar(self._cargar_hero)
        grid.addWidget(self.hero, 0, 0, 1, 2)

        # Tarjetas secundarias en grilla 2 columnas.
        self.tarjeta_vencimientos = TarjetaDashboard("Vencimientos proximos")
        self.tarjeta_vencimientos.clicked.connect(
            lambda: self.navegar.emit(NAV_VENCIMIENTOS)
        )
        self.tarjeta_vencimientos.conectar_reintentar(
            self._cargar_vencimientos
        )
        grid.addWidget(self.tarjeta_vencimientos, 1, 0)

        # Placeholder futuro: el segundo slot queda libre para
        # otro indicador confiable (alertas, equipos activos, etc).
        # Usamos un ``QWidget`` transparente para mantener la grilla.
        self._slot_aux = QWidget()
        self._slot_aux.setObjectName("dashboardSlotAux")
        self._slot_aux.setVisible(False)
        grid.addWidget(self._slot_aux, 1, 1)

        grid.setRowStretch(0, 2)
        grid.setRowStretch(1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        scroll.setWidget(contenido)

    # ------------------------------------------------------------------
    # Carga de datos
    # ------------------------------------------------------------------
    def cargar(self):
        """Lanza la carga de todas las tarjetas. No bloquea la UI."""
        self._cargar_hero()
        self._cargar_vencimientos()

    def recargar(self):
        """Atajo publico para reintentar la carga completa."""
        self.cargar()

    def _cargar_hero(self):
        self.hero.mostrar_cargando()
        resultado = servicios.hojas_ruta_del_dia(self._usu_id)
        self._aplicar_resultado(self.hero, resultado, alto_impacto=True)

    def _cargar_vencimientos(self):
        self.tarjeta_vencimientos.mostrar_cargando()
        resultado = servicios.vencimientos_proximos(self._usu_id)
        self._aplicar_resultado(
            self.tarjeta_vencimientos, resultado, alto_impacto=False
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
                detalle = "Fecha: {}".format(
                    resultado.fecha.isoformat()
                )
            tarjeta.mostrar_ok(resultado.cantidad, detalle=detalle)

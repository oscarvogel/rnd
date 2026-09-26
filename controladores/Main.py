# coding=utf-8
import os

from controladores.Login import LoginController
from controladores.Migraciones import MigracionBaseDatos
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import QApplication, QShortcut
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs import Constantes
from pyqt5libs.pyqt5libs.Menu import GeneraMenu
from pyqt5libs.pyqt5libs.utiles import LeerConf, LeerIni, getFileProperties, inicializar_y_capturar_excepciones
from utiles.actualizador import UpdateCoordinator
from utiles.build_info import BUILD_VERSION
from utiles.dashboard_flujo import (
    ACCION_ASIGNAR, ACCION_DESPACHAR, ACCION_IMPORTAR,
    ACCION_ORGANIZAR, ACCION_REVISAR, ACCION_VALIDAR,
)
from vistas.Main import MainView
from vistas.MigracionProgress import MigracionProgressDialog
from vistas.dashboard.dashboard_view import (
    NAV_ALERTAS, NAV_HOJAS_RUTA_DIA, NAV_IMPORTAR_PEDIDOS,
    NAV_ORGANIZAR_PEDIDOS, NAV_PENDIENTES, NAV_VENCIMIENTOS, DashboardView,
)


class MainController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = MainView()
        self._update_coordinator = None
        self._assistant_panel = None
        self._assistant_last_context = "Dashboard principal"
        self._assistant_shortcut = QShortcut(QKeySequence("F1"), self.view)
        self._assistant_shortcut.setContext(Qt.ApplicationShortcut)
        self._assistant_shortcut.setEnabled(False)
        self._assistant_shortcut.activated.connect(self.toggle_asistente)
        self.view.ArmaToolBarContable()
        self.view.ArmaToolBarVentas()
        self.view.ArmaToolBarCompras()
        self.view.ArmaToolBarSalir()
        self.conectarWidgets()

    @inicializar_y_capturar_excepciones
    def login(self, *args, **kwargs):
        logincontroller = LoginController()
        logincontroller.exec_()
        lRetVal = logincontroller.lRetVal
        if lRetVal:
            demo_mode = os.getenv("RND_DEMO_MODE") == "1"
            ejecutor = None
            if demo_mode:
                versionexe = "DEMO"
                servidor = "LOCAL"
                basedatos = "SQLite Demo"
                # Las consultas del dashboard corren en QThreadPool por defecto.
                # En el demo SQLite eso corrompe el heap (peewee + hilos Qt +
                # hilos de fondo de pymongo), asi que las corremos sincrono.
                from vistas.dashboard.ejecutor import EjecutorConsultasSincrono
                ejecutor = EjecutorConsultasSincrono()
            else:
                self._ejecutar_migraciones_con_feedback()
                propiedades = getFileProperties("main.exe")
                versionexe = propiedades["StringFileInfo"]["FileVersion"] if propiedades["StringFileInfo"] else ""
                servidor = LeerIni("ServerDB") or ""
                basedatos = LeerIni("BaseDatos") or ""
            usuario = LeerConf("usuario") or ""
            version_mostrada = versionexe or ("DEMO" if demo_mode else BUILD_VERSION)
            self.view.actualizar_encabezado(usuario=usuario, servidor=servidor, base=basedatos, estado="Conectado", version=version_mostrada)
            self.view.setWindowTitle("Usuario {} Servidor {} Base de datos {} Version sistema {}".format(usuario, servidor, basedatos, version_mostrada))
            usu_id = int(LeerConf("idUsuario") or 0)
            self.view.cargar_menu_lateral(usu_id)
            self._inicializar_dashboard(usu_id, ejecutor=ejecutor)
            self.ArmaMenu()
            self.view.encabezado.boton_asistente.setEnabled(True)
            self._assistant_shortcut.setEnabled(True)
            if not demo_mode:
                self._programar_actualizaciones()
        return lRetVal

    def _ejecutar_migraciones_con_feedback(self):
        migracion = MigracionBaseDatos()
        dialogo = MigracionProgressDialog(self.view)
        temporizador = QTimer(dialogo)
        temporizador.setInterval(100)

        def comprobar_fin():
            hilo = getattr(migracion, "thread", None)
            if hilo is None or not hilo.is_alive():
                temporizador.stop()
                dialogo.finalizar()

        temporizador.timeout.connect(comprobar_fin)
        temporizador.start()
        QTimer.singleShot(0, comprobar_fin)
        dialogo.exec_()
        migracion.esperar_migracion()

        error = getattr(migracion, "error", None)
        if error is not None:
            raise RuntimeError("No se pudieron aplicar las migraciones de la base de datos") from error

    def _programar_actualizaciones(self):
        try:
            self._update_coordinator = UpdateCoordinator(self.view, BUILD_VERSION)
            QTimer.singleShot(1500, self._update_coordinator.start)
        except Exception:
            # El updater nunca debe impedir el uso normal del sistema.
            self._update_coordinator = None

    def _inicializar_dashboard(self, usu_id, ejecutor=None):
        if self.view.dashboard is None:
            dashboard = DashboardView(usu_id=usu_id, ejecutor=ejecutor)
            dashboard.navegar.connect(self._navegar_desde_dashboard)
            self.view.registrar_dashboard(dashboard)
        else:
            self.view.dashboard._usu_id = int(usu_id or 0)
            self.view.dashboard.recargar()
        self.view.dashboard.cargar()

    def _navegar_desde_dashboard(self, clave):
        from datetime import date

        partes = str(clave).split("|", 1)
        accion = partes[0]
        ruta_id = int(partes[1]) if len(partes) > 1 and partes[1].isdigit() else 0

        if accion in (NAV_IMPORTAR_PEDIDOS, ACCION_IMPORTAR, ACCION_REVISAR):
            from controladores.ImportacionPedidos import ImportacionPedidosController
            self.view.ventana_menu_lateral = ImportacionPedidosController()
        elif accion in (NAV_ORGANIZAR_PEDIDOS, NAV_PENDIENTES, ACCION_ORGANIZAR):
            from controladores.BandejaPedidos import BandejaPedidosController
            self.view.ventana_menu_lateral = BandejaPedidosController(fecha_inicial=date.today())
        elif accion == ACCION_ASIGNAR:
            from controladores.AsignacionRecursos import AsignacionRecursosController
            self.view.ventana_menu_lateral = AsignacionRecursosController(fecha_inicial=date.today(), ruta_inicial=ruta_id)
        elif accion in (ACCION_VALIDAR, ACCION_DESPACHAR):
            from controladores.ValidacionHojaRuta import ValidacionHojaRutaController
            self.view.ventana_menu_lateral = ValidacionHojaRutaController(fecha_inicial=date.today(), ruta_inicial=ruta_id)
        elif accion == NAV_HOJAS_RUTA_DIA:
            from controladores.VerHojaRuta import VerHojaRutaController
            self.view.ventana_menu_lateral = VerHojaRutaController(
                fecha_inicial=date.today(), ruta_inicial=ruta_id
            )
        elif accion in (NAV_VENCIMIENTOS, NAV_ALERTAS):
            from controladores.ABMEquipos import ABMEquiposController
            self.view.ventana_menu_lateral = ABMEquiposController()
        else:
            return
        self.view.ventana_menu_lateral.run()

    def ArmaMenu(self):
        menu = GeneraMenu()
        menu.nIdSistema = LeerIni("sistema") or Constantes.IDSISTEMA
        menu.nIdUsuario = LeerConf("idUsuario")
        menu.ventana = self.view
        menu.Carga()

    def SalirSistema(self):
        self.view.SalirSistema()

    def conectarWidgets(self):
        self.view.encabezado.boton_asistente.clicked.connect(self.toggle_asistente)
        try:
            self.view.barra_lateral.arbol.itemClicked.connect(self.view.onClickItemMenu)
        except AttributeError:
            for btn in self.view.botones:
                btn.clicked.connect(lambda _, b=btn: self.view.onClickBtnMenuIzquierda(b))

    def _ensure_assistant_panel(self):
        if self._assistant_panel is None:
            from vistas.AsistenteRndPanel import AsistenteRndPanel

            self._assistant_panel = AsistenteRndPanel(
                anchor=self.view,
                context_provider=self._contexto_asistente,
            )
        return self._assistant_panel

    def _contexto_asistente(self):
        """Describe la pantalla activa sin usarla para rutear la consulta."""
        active = QApplication.activeWindow()

        if active is self._assistant_panel:
            return self._assistant_last_context

        if active is not None and active is not self.view:
            titulo = str(active.windowTitle() or "").strip()
            clase = active.__class__.__name__
            contexto = titulo or clase
            if titulo and clase not in titulo:
                contexto = "{} ({})".format(titulo, clase)
            self._assistant_last_context = contexto
            return contexto

        controller = getattr(self.view, "ventana_menu_lateral", None)
        window = getattr(controller, "view", None)
        if window is not None:
            titulo = str(window.windowTitle() or "").strip()
            clase = window.__class__.__name__
            contexto = titulo or clase
            if titulo and clase not in titulo:
                contexto = "{} ({})".format(titulo, clase)
            self._assistant_last_context = contexto
            return contexto

        return self._assistant_last_context

    def toggle_asistente(self):
        panel = self._ensure_assistant_panel()
        panel.toggle()

    @inicializar_y_capturar_excepciones
    def toolbtnpressed(self, a, *args, **kwargs) -> None:
        pass

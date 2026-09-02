# coding=utf-8
from controladores.Login import LoginController
from controladores.Migraciones import MigracionBaseDatos
from PyQt5.QtCore import QTimer
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
from vistas.dashboard.dashboard_view import (
    NAV_ALERTAS, NAV_HOJAS_RUTA_DIA, NAV_IMPORTAR_PEDIDOS,
    NAV_ORGANIZAR_PEDIDOS, NAV_PENDIENTES, NAV_VENCIMIENTOS, DashboardView,
)


class MainController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = MainView()
        self._update_coordinator = None
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
            MigracionBaseDatos()
            propiedades = getFileProperties("main.exe")
            versionexe = propiedades["StringFileInfo"]["FileVersion"] if propiedades["StringFileInfo"] else ""
            usuario = LeerConf("usuario") or ""
            servidor = LeerIni("ServerDB") or ""
            basedatos = LeerIni("BaseDatos") or ""
            self.view.actualizar_encabezado(usuario=usuario, servidor=servidor, base=basedatos, estado="Conectado", version=versionexe or BUILD_VERSION)
            self.view.setWindowTitle("Usuario {} Servidor {} Base de datos {} Version sistema {}".format(usuario, servidor, basedatos, versionexe or BUILD_VERSION))
            usu_id = int(LeerConf("idUsuario") or 0)
            self.view.cargar_menu_lateral(usu_id)
            self._inicializar_dashboard(usu_id)
            self.ArmaMenu()
            self._programar_actualizaciones()
        return lRetVal

    def _programar_actualizaciones(self):
        try:
            self._update_coordinator = UpdateCoordinator(self.view, BUILD_VERSION)
            QTimer.singleShot(1500, self._update_coordinator.start)
        except Exception:
            # La actualización nunca debe impedir el uso normal del sistema.
            self._update_coordinator = None

    def _inicializar_dashboard(self, usu_id):
        if self.view.dashboard is None:
            dashboard = DashboardView(usu_id=usu_id)
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
            self.view.ventana_menu_lateral = VerHojaRutaController(fecha_inicial=date.today())
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
        try:
            self.view.barra_lateral.arbol.itemClicked.connect(self.view.onClickItemMenu)
        except AttributeError:
            for btn in self.view.botones:
                btn.clicked.connect(lambda _, b=btn: self.view.onClickBtnMenuIzquierda(b))

    @inicializar_y_capturar_excepciones
    def toolbtnpressed(self, a, *args, **kwargs) -> None:
        pass

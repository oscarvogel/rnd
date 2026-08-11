# coding=utf-8
from controladores.Login import LoginController
from controladores.Migraciones import MigracionBaseDatos
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs import Constantes
from pyqt5libs.pyqt5libs.Menu import GeneraMenu
from pyqt5libs.pyqt5libs.utiles import (
    LeerConf,
    LeerIni,
    getFileProperties,
    inicializar_y_capturar_excepciones,
)
from vistas.Main import MainView
from vistas.dashboard.dashboard_view import (
    NAV_ALERTAS,
    NAV_HOJAS_RUTA_DIA,
    NAV_IMPORTAR_PEDIDOS,
    NAV_PENDIENTES,
    NAV_VENCIMIENTOS,
    DashboardView,
)


class MainController(ControladorBase):
    def __init__(self):
        super().__init__()
        self.view = MainView()
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
            if propiedades["StringFileInfo"]:
                versionexe = propiedades["StringFileInfo"]["FileVersion"]
            else:
                versionexe = ""

            usuario = LeerConf("usuario") or ""
            servidor = LeerIni("ServerDB") or ""
            basedatos = LeerIni("BaseDatos") or ""
            self.view.actualizar_encabezado(
                usuario=usuario,
                servidor=servidor,
                base=basedatos,
                estado="Conectado",
                version=versionexe,
            )
            self.view.setWindowTitle(
                "Usuario {} Servidor {} Base de datos {} Version sistema {}".format(
                    usuario, servidor, basedatos, versionexe
                )
            )
            usu_id = int(LeerConf("idUsuario") or 0)
            self.view.cargar_menu_lateral(usu_id)
            self._inicializar_dashboard(usu_id)
            self.ArmaMenu()
        return lRetVal

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
        if clave == NAV_IMPORTAR_PEDIDOS:
            from controladores.ImportacionPedidos import ImportacionPedidosController

            self.view.ventana_menu_lateral = ImportacionPedidosController()
            self.view.ventana_menu_lateral.run()
        elif clave == NAV_HOJAS_RUTA_DIA:
            from datetime import date
            from controladores.VerHojaRuta import VerHojaRutaController

            self.view.ventana_menu_lateral = VerHojaRutaController(
                fecha_inicial=date.today()
            )
            self.view.ventana_menu_lateral.run()
        elif clave == NAV_PENDIENTES:
            from datetime import date
            from controladores.VerHojaRuta import VerHojaRutaController

            self.view.ventana_menu_lateral = VerHojaRutaController(
                fecha_inicial=date.today()
            )
            self.view.ventana_menu_lateral.run()
        elif clave == NAV_VENCIMIENTOS:
            from controladores.ABMEquipos import ABMEquiposController

            self.view.ventana_menu_lateral = ABMEquiposController()
            self.view.ventana_menu_lateral.run()
        elif clave == NAV_ALERTAS:
            from controladores.ABMEquipos import ABMEquiposController

            self.view.ventana_menu_lateral = ABMEquiposController()
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
            self.view.barra_lateral.arbol.itemClicked.connect(
                self.view.onClickItemMenu
            )
        except AttributeError:
            for btn in self.view.botones:
                btn.clicked.connect(
                    lambda _, b=btn: self.view.onClickBtnMenuIzquierda(b)
                )

    @inicializar_y_capturar_excepciones
    def toolbtnpressed(self, a, *args, **kwargs) -> None:
        pass

# coding=utf-8
from PyQt5.QtWidgets import QAction, qApp

from controladores.Login import LoginController

from controladores.Migraciones import MigracionBaseDatos
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs import Constantes
from pyqt5libs.pyqt5libs.Menu import GeneraMenu
from pyqt5libs.pyqt5libs.utiles import LeerConf, LeerIni, getFileProperties, inicializar_y_capturar_excepciones
from vistas.Main import MainView
from vistas.dashboard.dashboard_view import (
    NAV_HOJAS_RUTA_DIA,
    NAV_VENCIMIENTOS,
    DashboardView,
)
from vistas.dashboard import servicios as dashboard_servicios


class MainController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = MainView()
        # Las ``ArmaToolBar*`` quedan como no-op en el shell moderno pero
        # se llaman para mantener compatibilidad con el contrato historico.
        self.view.ArmaToolBarContable()
        self.view.ArmaToolBarVentas()
        self.view.ArmaToolBarCompras()
        self.view.ArmaToolBarSalir()

        # notificar_cuotas_a_vencer()
        # notificar_polizas_a_vencer()
        self.conectarWidgets()

    @inicializar_y_capturar_excepciones
    def login(self, *args, **kwargs):
        logincontroller = LoginController()
        logincontroller.exec_()
        lRetVal = logincontroller.lRetVal
        if lRetVal:
            # main_automatizacion()
            migrador = MigracionBaseDatos()
            # hilo_vencimientos()
            propiedades = getFileProperties("main.exe")
            if propiedades["StringFileInfo"]:
                versionexe = propiedades["StringFileInfo"]["FileVersion"]
            else:
                versionexe = ''

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
                f'Usuario {usuario} Servidor {servidor}'
                f' Base de datos {basedatos} '
                f'Version sistema {versionexe}'
            )

            usu_id = int(LeerConf("idUsuario") or 0)
            self.view.cargar_menu_lateral(usu_id)

            # Dashboard operativo (issue #4). Se crea con el id del
            # usuario para que los servicios filtren por permisos.
            self._inicializar_dashboard(usu_id)

            # inicializadb()
            self.ArmaMenu()
        return lRetVal

    def _inicializar_dashboard(self, usu_id):
        """Crea, registra y conecta el dashboard operativo."""
        if self.view.dashboard is None:
            dashboard = DashboardView(usu_id=usu_id)
            dashboard.navegar.connect(self._navegar_desde_dashboard)
            self.view.registrar_dashboard(dashboard)
        else:
            # Si ya existia (por ejemplo, tras un re-login), solo
            # recargamos los datos con el nuevo usu_id.
            self.view.dashboard._usu_id = int(usu_id or 0)
            self.view.dashboard.recargar()
        # Poblamos la primera carga despues del login.
        self.view.dashboard.cargar()

    def _navegar_desde_dashboard(self, clave):
        """Abre el modulo correspondiente a una tarjeta del dashboard.

        Por ahora se delega a los modulos existentes tal cual; los
        filtros ``fecha`` o ``estado`` especificos del dashboard se
        persisten en ``LeerConf`` para que las vistas los lean si
        los soportan (el requisito de "filtro aplicado" de #4 se
        cumple para Hojas de Ruta via ``filtro_fecha``).
        """
        if clave == NAV_HOJAS_RUTA_DIA:
            from controladores.VerHojaRuta import VerHojaRutaController
            from datetime import date
            # Filtro: hoy. La vista lo lee si la version instalada
            # del modulo lo soporta; si no, queda en conf para
            # extensiones futuras.
            from pyqt5libs.pyqt5libs.utiles import GrabaConf
            GrabaConf(clave="dashboard_filtro_fecha", valor=date.today().isoformat())
            self.view.ventana_menu_lateral = VerHojaRutaController()
            self.view.ventana_menu_lateral.run()
        elif clave == NAV_VENCIMIENTOS:
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
        # El shell moderno navega via itemClicked del arbol lateral.
        try:
            self.view.barra_lateral.arbol.itemClicked.connect(
                self.view.onClickItemMenu
            )
        except AttributeError:
            # Fallback tolerante: si por algun motivo el arbol no
            # existe, conserva el comportamiento historico.
            for btn in self.view.botones:
                btn.clicked.connect(
                    lambda _, b=btn: self.view.onClickBtnMenuIzquierda(b)
                )


    @inicializar_y_capturar_excepciones
    def toolbtnpressed(self, a, *args, **kwargs) -> None:
        pass

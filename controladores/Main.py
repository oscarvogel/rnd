# coding=utf-8
from PyQt5.QtWidgets import QAction, qApp

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
                f"Usuario {usuario} Servidor {servidor}"
                f" Base de datos {basedatos} "
                f"Version sistema {versionexe}"
            )

            usu_id = int(LeerConf("idUsuario") or 0)
            self.view.cargar_menu_lateral(usu_id)

            # inicializadb()
            self.ArmaMenu()
        return lRetVal

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
            self.view.barra_lateral.arbol.itemClicked.connect(self.view.onClickItemMenu)
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

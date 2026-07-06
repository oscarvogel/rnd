# coding=utf-8
from PyQt5.QtWidgets import QAction, qApp

from controladores.Login import LoginController

from controladores.Migraciones import MigracionBaseDatos
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs import Constantes
from pyqt5libs.pyqt5libs.Menu import GeneraMenu
from pyqt5libs.pyqt5libs.utiles import LeerConf, LeerIni, getFileProperties, inicializar_y_capturar_excepciones
from vistas.Main import MainView


class MainController(ControladorBase):

    def __init__(self):
        super().__init__()
        self.view = MainView()
        # self.view.ArmaToolbarVentas()
        # self.view.ArmaToolbarCompra()
        self.view.ArmaToolBarContable()
        self.view.ArmaToolBarVentas()
        self.view.ArmaToolBarCompras()
        # self.view.ArmaToolBarSueldos()
        self.view.ArmaToolBarSalir()
        
        # #informa cuotas de polizas a vencer
        # notificar_cuotas_a_vencer()
        # #informa polizas a vencer
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
            # self.view.setWindowTitle("Usuario " + LeerConf("usuario") + " Servidor " + LeerIni("ServerDB") +
            #                         " Base de datos " + LeerIni("BaseDatos"))
            if propiedades["StringFileInfo"]:
                versionexe = propiedades["StringFileInfo"]["FileVersion"]
            else:
                versionexe = ''
            self.view.setWindowTitle(f'Usuario {LeerConf("usuario")} Servidor {LeerIni("ServerDB")}'
                                     f' Base de datos {LeerIni("BaseDatos")} '
                                     f'Version sistema {versionexe}')
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
        qApp.exit()

    def conectarWidgets(self):
        for btn in self.view.botones:
            btn.clicked.connect(lambda _, b=btn: self.view.onClickBtnMenuIzquierda(b))    


    @inicializar_y_capturar_excepciones
    def toolbtnpressed(self, a, *args, **kwargs) -> None:
        pass

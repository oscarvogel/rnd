# coding=utf-8

import importlib
import re

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, qApp
from peewee import DoesNotExist


from modelos.Accesos import Acceso
from modelos.Formula import MenuLateral
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import BorrarConf, LeerConf

from vistas.shell.AreaCentral import AreaCentralView
from vistas.shell.BarraLateral import BarraLateralView
from vistas.shell.Encabezado import EncabezadoView


class MainView(QMainWindow):
    LanzarExcepciones = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ``botones`` se conserva por compatibilidad con codigo existente
        # (controlador, scripts) que itera sobre esta lista. Con el shell
        # moderno los elementos son ``QTreeWidgetItem`` y se navega via
        # ``itemClicked`` (ver ``controladores.Main.conectarWidgets``).
        self.botones = []
        self.ventana_menu_lateral = None
        self.dashboard = None
        self.initUi()
        self.showMaximized()

    def initUi(self):
        """Punto de entrada del armado de la UI principal."""
        self.ArmaShellModerno(self)

    def ArmaShellModerno(self, main_window):
        """Compone el shell: encabezado + barra lateral + area central.

        El layout es totalmente escalable: no usa geometrias absolutas
        (a diferencia del ``QToolBox`` original) y se adapta al
        escalado de Windows via ``ancho_por_dpi``.
        """
        central = QtWidgets.QWidget(main_window)
        central.setObjectName("shellCentralRoot")
        raiz = QtWidgets.QVBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        self.encabezado = EncabezadoView()
        self.encabezado.boton_salir.clicked.connect(self.SalirSistema)
        raiz.addWidget(self.encabezado)

        cuerpo = QtWidgets.QWidget()
        cuerpo.setObjectName("shellCuerpo")
        layout_cuerpo = QtWidgets.QHBoxLayout(cuerpo)
        layout_cuerpo.setContentsMargins(0, 0, 0, 0)
        layout_cuerpo.setSpacing(0)

        self.barra_lateral = BarraLateralView()
        layout_cuerpo.addWidget(self.barra_lateral)

        self.area_central = AreaCentralView()
        layout_cuerpo.addWidget(self.area_central, stretch=1)

        raiz.addWidget(cuerpo, stretch=1)
        main_window.setCentralWidget(central)

        dpi = main_window.logicalDpiX() or 96
        self.barra_lateral.ancho_por_dpi(dpi)

    def cargar_menu_lateral(self, usu_id):
        """Carga las opciones de la barra lateral segun permisos.

        Devuelve la cantidad de items visibles para que el
        controlador o los tests puedan verificarla.
        """
        visibles = self.barra_lateral.cargar(usu_id)
        self.botones = []
        for i in range(self.barra_lateral.arbol.topLevelItemCount()):
            padre = self.barra_lateral.arbol.topLevelItem(i)
            for j in range(padre.childCount()):
                self.botones.append(padre.child(j))
        return visibles

    def registrar_dashboard(self, dashboard):
        """Conecta el dashboard operativo (#4) al area central.

        El dashboard se agrega como pagina ``dashboard`` y se
        selecciona por defecto, reemplazando al placeholder.
        """
        self.dashboard = dashboard
        self.area_central.registrar_pagina("dashboard", dashboard)
        self.area_central.mostrar("dashboard")

    def actualizar_encabezado(self, usuario, servidor, base,
                              estado="Conectado", version=""):
        self.encabezado.actualizar(
            usuario=usuario,
            servidor=servidor,
            base=base,
            estado=estado,
            version=version,
        )

    def onClickItemMenu(self, item, _columna=0):
        """Maneja clicks sobre items del arbol de navegacion lateral."""
        if item is None:
            return
        menu_id = item.data(0, Qt.UserRole)
        if menu_id is None:
            return
        try:
            dato_menu = MenuLateral.get_by_id(menu_id)
        except DoesNotExist:
            return
        if Acceso.ValidaMenu(
            usu_id=int(LeerConf("idUsuario") or 0),
            for_valid=dato_menu.for_id.for_valid,
        ):
            self.ventana_menu_lateral = self._crear_controlador_menu(
                dato_menu.for_id.for_arch
            )
            self.ventana_menu_lateral.run()

    @staticmethod
    def _crear_controlador_menu(archivo):
        """Instancia un destino historico ``Modulo.Controlador()``.

        Los nombres viven en ``Formula.for_arch``. La ventana anterior
        dependia de imports globales y ``eval``; al retirar aquellos imports
        el nuevo shell dejo de poder abrir los modulos. La resolucion tardia
        conserva el formato de datos existente sin importar todos los ABM al
        iniciar ni ejecutar expresiones arbitrarias.
        """
        expresion = (archivo or "").strip()
        coincidencia = re.fullmatch(
            r"([A-Za-z_]\w*)\.([A-Za-z_]\w*)\(\)",
            expresion,
        )
        if coincidencia is None:
            raise ValueError(
                "Destino de menu no valido: {!r}".format(expresion)
            )
        modulo_nombre, controlador_nombre = coincidencia.groups()
        modulo = importlib.import_module(
            "controladores.{}".format(modulo_nombre)
        )
        controlador = getattr(modulo, controlador_nombre)
        return controlador()

    # ------------------------------------------------------------------
    # API heredada (deprecada, mantenida por compatibilidad transitoria)
    # ------------------------------------------------------------------

    def ArmaToolBarContable(self):
        pass

    def ArmaToolBarCompras(self):
        pass

    def ArmaToolBarVentas(self):
        pass

    def ArmaToolBarSueldos(self):
        pass

    def ArmaToolBarSalir(self):
        pass

    def initMenu(self):
        pass

    def SeleccionaMenu(self, idMenu, Archivo):
        if Archivo:
            self.ventana = self._crear_controlador_menu(Archivo)
            self.ventana.run()
        else:
            Ventanas.showAlert("Error", u"Opcion de menu no establecida")

    def SalirSistema(self):
        BorrarConf()
        qApp.exit()

    def onClickBtnMenuIzquierda(self, boton, *args, **kwargs):
        """Compatibilidad: adapta botones ``Boton`` o ``QTreeWidgetItem``."""
        if hasattr(boton, "data") and callable(getattr(boton, "data", None)):
            self.onClickItemMenu(boton, 0)
            return
        if boton.text().replace('&', '').upper() == 'CERRAR':
            qApp.exit()
            return
        try:
            dato_menu = MenuLateral.get_by_id(boton.id)
            if Acceso.ValidaMenu(usu_id=LeerConf('idUsuario'),
                                 for_valid=dato_menu.for_id.for_valid):
                self.ventana_menu_lateral = self._crear_controlador_menu(
                    dato_menu.for_id.for_arch
                )
                self.ventana_menu_lateral.run()
        except DoesNotExist:
            pass

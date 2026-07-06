# coding=utf-8

from os.path import join

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QIcon, QPixmap, QPalette, QBrush
from PyQt5.QtWidgets import QMainWindow, qApp, QAction, QVBoxLayout
from peewee import DoesNotExist


from modelos.Accesos import Acceso
from modelos.Formula import Formula, MenuLateral
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.ToolBox import ToolBox
from pyqt5libs.pyqt5libs.Botones import Boton, BotonCerrarFormulario
from pyqt5libs.pyqt5libs.utiles import BorrarConf, LeerConf, imagen, inicializar_y_capturar_excepciones, ubicacion_sistema

from controladores import ABMClientes, ABMEmpleados, ABMEquipos, ABMProveedores
from controladores import ABMTablas, ImportacionPedidos, VerHojaRuta


class MainView(QMainWindow):
    LanzarExcepciones = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.ImagenFondo()
        self.initUi()
        self.showMaximized()

    def initUi(self):
        self.ArmaToolBoxLateral(self)

    def initMenu(self):
        pass

    def SeleccionaMenu(self, idMenu, Archivo):
        print("ID Menu {}".format(idMenu))
        if Archivo:
            self.ventana = eval(Archivo)
            # ventana.exec_()
            self.ventana.run()
        else:
            Ventanas.showAlert("Error", u"Opcion de menu no establecida")

    def SalirSistema(self):
        BorrarConf()
        qApp.exit()

    def ArmaToolBarSalir(self):
        pass

    def ImagenFondo(self):
        #self.setStyleSheet("background-image: url(:imagenes/FOTO1.jpg); ")
        pixmap = QPixmap(join(ubicacion_sistema(), "imagenes", "perfiles.jpg"))
        # pixmap.scaledToWidth(self.width())
        # pixmap.scaledToHeight(self.height())
        print("alto {} ancho {}".format(self.height(), self.width()))
        # oImage = QImage(join(LeerConf("InicioSistema"), "imagenes", "FOTO1.jpg"))
        # oImage.scaledToHeight(self.height())
        # oImage.scaledToWidth(self.width())
        palette = QPalette()
        palette.setBrush(10, QBrush(pixmap))
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    def ArmaToolBarContable(self):
        pass

    def ArmaToolBarCompras(self):
        pass

    def ArmaToolBarVentas(self):
        pass
    
    def ArmaToolBarSueldos(self):
        pass

    def ArmaToolBoxLateral(self, MainWindow):
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.toolBox = ToolBox(self.centralwidget)
        self.toolBox.setGeometry(QtCore.QRect(0, 0, 250, 500))
        self.toolBox.setObjectName("toolBox")
        self.paginas = []
        self.botones = []
        self.layoutBotones = []
        datos_pagina = MenuLateral.Cabeceras()

        for pag in datos_pagina:
            self.paginas.append(QtWidgets.QWidget())
            indice = len(self.paginas) - 1
            self.toolBox.addItem(self.paginas[indice], pag.nombre.strip())

            items_pagina = MenuLateral.select().join(Formula).where(
                MenuLateral.for_pare == pag.id,
            ).order_by(Formula.for_orde)
            layoutBoton = QVBoxLayout(self.paginas[indice])
            self.layoutBotones.append(layoutBoton)
            indice_boton = len(self.layoutBotones) - 1
            alto = 0
            for item in items_pagina:
                alto += 1
                boton = Boton(texto=item.nombre.strip(), imagen=imagen(
                    item.for_id.for_imag
                ), tooltip=item.for_id.for_nomb)
                boton.id = item.id
                self.layoutBotones[indice_boton].addWidget(boton)
                self.botones.append(boton)

            ancho_pagina = QtCore.QRect(0, 0, 150, alto * 35)
            self.paginas[indice].setGeometry(ancho_pagina)
            self.layoutBotones[indice_boton].addStretch(1)

        self.paginas.append(QtWidgets.QWidget())
        indice = len(self.paginas) - 1
        self.toolBox.addItem(self.paginas[indice], 'Salir')
        layoutBoton = QVBoxLayout(self.paginas[indice])
        self.layoutBotones.append(layoutBoton)
        indice_boton = len(self.layoutBotones) - 1
        boton = BotonCerrarFormulario()
        boton.clicked.connect(lambda: qApp.exit())
        self.layoutBotones[indice_boton].addWidget(boton)
        self.layoutBotones[indice_boton].addStretch(1)

        self.botones.append(boton)

        MainWindow.setCentralWidget(self.centralwidget)

    @inicializar_y_capturar_excepciones
    def onClickBtnMenuIzquierda(self, boton, *args, **kwargs):
        if boton.text().replace('&', '').upper() == 'CERRAR':
            qApp.exit()
            return
        try:
            dato_menu = MenuLateral.get_by_id(boton.id)
            if Acceso.ValidaMenu(usu_id=LeerConf('idUsuario'), for_valid=dato_menu.for_id.for_valid):
                self.ventana_menu_lateral = eval(dato_menu.for_id.for_arch)
                self.ventana_menu_lateral.run()
        except DoesNotExist:
            pass
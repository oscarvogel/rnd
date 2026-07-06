# -*- coding: utf-8 -*-
import functools

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction

from modelos.Accesos import Acceso
from modelos.Formula import Formula
from modelos.Usuarios import Usuario
from .utiles import LeerConf, imagen



class GeneraMenu(object):

    nIdSistema = 0
    nIdUsuario = 0
    ventana = None

    def __init__(self):
        pass

    def Carga(self):

        self.datos_menu = Formula().select()
        if LeerConf("DEBUG"):
            print("Id Usuario {}".format(LeerConf("idUsuario")))

        if Usuario().IsAdmin(LeerConf('idUsuario')):
            self.datos_menu = self.datos_menu.where(Formula.sis_id == self.nIdSistema)
        else:
            self.datos_menu = self.datos_menu.join(Acceso)
            self.datos_menu = self.datos_menu.where(Acceso.usu_id == self.nIdUsuario,
                                                    Formula.sis_id == self.nIdSistema)

        self.datos_menu = self.datos_menu.where(Formula.for_pare==0).order_by(Formula.for_orde)

        for d in self.datos_menu:
            menubar = self.ventana.menuBar()
            fileMenu = menubar.addMenu(d.for_nomb.strip())
            self.CargaHijos(d, fileMenu)

    def CargaHijos(self, d, fileMenu):
        hijos = Formula.select()\
            .where(Formula.for_pare == d.for_id) \
            .order_by(Formula.for_orde)
        for h in hijos:
            if h.tfo_id == 5: #separador de menu
                fileMenu.addSeparator()
            else:
                data = Acceso().select().where(Acceso.usu_id == LeerConf('idUsuario'),
                                                Acceso.for_id == h.for_id)
                if Acceso().AccesoUsuario(usu_id=LeerConf('idUsuario'), for_id=h.for_id): #si tiene autorizacion entra
                    subhijo = Formula.select()\
                        .where(Formula.for_pare==h.for_id)
                    if subhijo:
                        fileSub = fileMenu.addMenu(h.for_nomb.strip())
                        self.CargaHijos(h, fileSub)
                    else:
                        if h.for_imag:
                            menuAct = QAction(QIcon(imagen(h.for_imag)), h.for_nomb.strip(), self.ventana)
                        else:
                            menuAct = QAction(h.for_nomb.strip(), self.ventana)
                        menuAct.setStatusTip(h.for_nomb)
                        if h.tfo_id == 2:
                            #pass
                            menuAct.triggered.connect(eval('self.ventana.'+h.for_arch.strip()))
                        else:
                            #pass
                            menuAct.triggered.connect(functools.partial(self.ventana.SeleccionaMenu,
                                                                        h.for_id, h.for_arch))
                        fileMenu.addAction(menuAct)


# coding=utf-8
"""Barra lateral permanente del shell moderno de RND.

Reemplaza al ``QToolBox`` de la version anterior. Construye un arbol
con las cabeceras de ``MenuLateral`` como secciones y los items de
``MenuLateral`` (con su ``Formula`` asociada) como entradas
accionables. La validacion de permisos se realiza al construir el
arbol para que la barra lateral solo muestre opciones a las que el
usuario tiene acceso (requisito de #3).
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFrame,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from modelos.Accesos import Acceso
from modelos.Formula import Formula, MenuLateral
from pyqt5libs.pyqt5libs.utiles import imagen


class BarraLateralView(QFrame):
    """Barra lateral con navegacion jerarquica por permisos."""

    def __init__(self, parent=None, ancho_minimo=240, ancho_maximo=360):
        super().__init__(parent)
        self.setObjectName("barraLateralShell")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._ancho_minimo = ancho_minimo
        self._ancho_maximo = ancho_maximo
        self.setMinimumWidth(self._ancho_minimo)
        self.setMaximumWidth(self._ancho_maximo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.arbol = QTreeWidget()
        self.arbol.setObjectName("menuLateralArbol")
        self.arbol.setHeaderHidden(True)
        self.arbol.setIndentation(16)
        self.arbol.setUniformRowHeights(True)
        self.arbol.setExpandsOnDoubleClick(False)
        self.arbol.setFocusPolicy(Qt.StrongFocus)
        layout.addWidget(self.arbol)

        self._items_por_menu_id = {}

    def ancho_por_dpi(self, dpi):
        """Adapta el ancho de la barra al escalado de Windows.

        Mantiene un minimo confortable de 240 px y no excede los
        360 px para no comerse la zona central en pantallas chicas.
        """
        if dpi <= 96:
            ancho = 260
        elif dpi <= 120:
            ancho = 300
        else:
            ancho = 340
        ancho = max(self._ancho_minimo, min(self._ancho_maximo, ancho))
        self.setMinimumWidth(self._ancho_minimo)
        self.setMaximumWidth(self._ancho_maximo)
        self.setFixedWidth(ancho)

    def cargar(self, usu_id):
        """Construye el arbol de navegacion filtrado por permisos.

        Devuelve la cantidad de items visibles (para smoke tests).
        """
        self.arbol.clear()
        self._items_por_menu_id = {}

        cabeceras = MenuLateral.Cabeceras()
        for cabecera in cabeceras:
            item_padre = QTreeWidgetItem(self.arbol)
            item_padre.setText(0, cabecera.nombre.strip())
            item_padre.setFlags(
                item_padre.flags() & ~Qt.ItemIsSelectable
                & ~Qt.ItemIsEnabled
            )
            fuente = item_padre.font(0)
            fuente.setBold(True)
            item_padre.setFont(0, fuente)
            item_padre.setFirstColumnSpanned(True)

            hijos = MenuLateral.select().join(Formula).where(
                MenuLateral.for_pare == cabecera.id,
            ).order_by(Formula.for_orde)

            visibles = 0
            for item in hijos:
                if not Acceso().AccesoUsuario(
                    usu_id=usu_id,
                    for_id=item.for_id.for_id,
                ):
                    continue
                hijo = QTreeWidgetItem(item_padre)
                texto = item.nombre.strip()
                hijo.setText(0, texto)
                icono_path = imagen(item.for_id.for_imag)
                if icono_path:
                    hijo.setIcon(0, QIcon(icono_path))
                hijo.setData(0, Qt.UserRole, item.id)
                if item.for_id.for_nomb:
                    hijo.setToolTip(0, item.for_id.for_nomb)
                self._items_por_menu_id[item.id] = hijo
                visibles += 1

            if visibles == 0:
                item_padre.setHidden(True)
            else:
                item_padre.setExpanded(True)

        return len(self._items_por_menu_id)

    def item_por_menu_id(self, menu_id):
        return self._items_por_menu_id.get(menu_id)

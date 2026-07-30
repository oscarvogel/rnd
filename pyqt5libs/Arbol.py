# coding=utf-8
from collections import deque

from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QTreeView, QHeaderView


class ArbolView(QTreeView):

    model = None #modelo del arbol
    nombre = 'short_name' #nombre para el indice de datos
    valor = 'valor' #nombre si tiene un valor
    id = 'dbID' #nombre para el indice del ID
    parent_id = 'parentID' #nombre para el campo del parent
    level = 'level' #nombre para el campo del nivel del arbol
    checked = 'checked' #campo para guardar el estado si tiene checkbox
    coldato = 0 #columna de datos
    colindice = 1 #columna con los indices
    checkeado = [] #filas que estan chequeadas
    nocheckeado = [] #finas que no estan chequeadas

    def __init__(self):
        super().__init__()
        self.model = QStandardItemModel()
        self.checkeado = []
        self.nocheckeado = []

    def ArmaCabecera(self, cabecera=''):
        self.model.setHorizontalHeaderLabels(cabecera)
        self.setModel(self.model)
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)

    def ImportaDatos(self, datos='', root=None, concheck=False):
        self.model.setRowCount(0)
        if root is None:
            root = self.model.invisibleRootItem()
        seen = {}
        values = deque(datos)
        while values:
            value = values.popleft()
            if value[self.level] == 0:
                parent = root
            else:
                pid = value[self.parent_id]
                if pid not in seen:
                    values.append(value)
                    continue
                parent = seen[pid]
            dbid = value[self.id]
            itemnombre = QtGui.QStandardItem(value[self.nombre])
            try:
                itemValor = QtGui.QStandardItem(value[self.valor])
            except:
                itemValor = ''
            itemid = QtGui.QStandardItem(str(dbid))
            itemnombre.setEditable(False)
            if concheck:
                if value[self.checked]:
                    itemnombre.setCheckState(Qt.Checked)
                else:
                    itemnombre.setCheckState(Qt.Unchecked)
                itemnombre.setFlags(itemnombre.flags() | Qt.ItemIsUserCheckable)

            itemid.setEditable(False)
            if itemValor:
                parent.appendRow([
                    itemnombre, itemValor, itemid,
                ])
            else:
                parent.appendRow([
                    itemnombre, itemid,
                ])
            seen[dbid] = parent.child(parent.rowCount() - 1)

    def ObtenerItemSeleccionado(self, col=0):
        try:
            resultado = self.model.itemData(
                self.selectedIndexes()[col]
            )[0]
        except:
            resultado = ''
        return resultado

    def recorrer(self, model=None, parent=QModelIndex()):
        for row in range(model.rowCount(parent)):
            # dato = self.view.tree.ObtenerItem(0)
            # print(dato)
            index = model.index(row, self.coldato, parent)
            indexid = index
            nombre = model.data(index)
            index = model.index(row, self.colindice, parent)
            id = model.data(index)
            print(nombre, id)
            if model.data(indexid, Qt.CheckStateRole) == Qt.Checked:
                self.checkeado.append(id)
            else:
                self.nocheckeado.append(id)
            if model.hasChildren(indexid):
                self.recorrer(model, indexid)

        return self.checkeado, self.nocheckeado
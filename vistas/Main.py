# coding=utf-8

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, qApp
from peewee import DoesNotExist


from modelos.Accesos import Acceso
from modelos.Formula import MenuLateral
from modelos.ModeloBase import reconnect_if_needed
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
        """Registra y muestra el dashboard operativo en el area central."""
        self.dashboard = dashboard
        self.area_central.registrar_pagina("dashboard", dashboard)
        self.area_central.mostrar("dashboard")

    def actualizar_encabezado(
        self, usuario, servidor, base, estado="Conectado", version=""
    ):
        self.encabezado.actualizar(
            usuario=usuario,
            servidor=servidor,
            base=base,
            estado=estado,
            version=version,
        )

    # Prefijos de paquete probados en orden al resolver el modulo del
    # menu lateral. El primero que exista gana. Empezamos por
    # ``controladores`` porque el menu dinamico quiere instanciar un
    # controlador (con ``run()`` y widgets conectados), no una vista.
    PREFIJOS_MODULO_MENU = (
        "controladores",
        "vistas",
        "",
    )

    def _normalizar_target_menu(self, target):
        """Convierte un ``for_arch`` de la DB a ``(modulo, clase)``."""
        if not target:
            return None, None
        raw = str(target).strip()
        for pref in ("self.ventana.", "self.", "ventana."):
            if raw.startswith(pref):
                raw = raw[len(pref) :]
        raw = raw.rstrip()
        if raw.endswith(")"):
            paren = raw.rfind("(")
            if paren != -1:
                raw = raw[:paren].rstrip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ("'", '"'):
            raw = raw[1:-1]
        raw = raw.strip()
        if not raw:
            return None, None
        if "." in raw:
            mod_path, class_name = raw.rsplit(".", 1)
        else:
            mod_path, class_name = raw, None
        return mod_path.strip(), (class_name.strip() if class_name else None)

    def _importar_menu_modulo(self, mod_path):
        """Importa ``mod_path`` probando los prefijos de paquete."""
        import importlib

        if not mod_path:
            raise ModuleNotFoundError("for_arch vacio o no resoluble")
        prefijos = list(self.PREFIJOS_MODULO_MENU)
        ya_con_prefijo = any(
            mod_path == p or mod_path.startswith(p + ".") for p in prefijos if p
        )
        if ya_con_prefijo:
            prefijos = [""] + [p for p in prefijos if p]
        ultimo_exc = None
        for p in prefijos:
            full = (p + "." + mod_path) if p else mod_path
            try:
                return importlib.import_module(full)
            except ModuleNotFoundError as exc:
                ultimo_exc = exc
                if exc.name and exc.name != full.split(".")[0]:
                    raise
                continue
        raise ultimo_exc or ModuleNotFoundError(mod_path)

    def _resolver_clase_menu(self, target):
        """Devuelve la clase instanciable a partir de un ``for_arch``."""
        mod_path, class_name = self._normalizar_target_menu(target)
        modulo = self._importar_menu_modulo(mod_path)
        if class_name:
            return getattr(modulo, class_name)
        from PyQt5.QtWidgets import QWidget

        for nombre_pref in ("ControladorBase", "ControladorBaseABM"):
            cand = getattr(modulo, nombre_pref, None)
            if isinstance(cand, type) and issubclass(cand, QWidget):
                return cand
        candidatos = [
            v
            for v in vars(modulo).values()
            if isinstance(v, type)
            and issubclass(v, QWidget)
            and not v.__name__.startswith("_")
        ]
        if not candidatos:
            raise AttributeError(f"Modulo {mod_path} no tiene subclases de QWidget")
        return candidatos[0]

    def _mostrar_error_menu(self, target, exc):
        """Dialogo de error estandar cuando un item de menu no abre."""
        import traceback
        from PyQt5.QtWidgets import QMessageBox

        tb = traceback.format_exc()
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Critical)
        box.setWindowTitle("Error al abrir la opcion")
        box.setText(
            "No se pudo abrir la opcion del menu.\n\n"
            "Path guardado en la DB: '" + str(target) + "'\n\n"
            "Error: " + str(exc)
        )
        box.setDetailedText(tb)
        box.setStyleSheet(
            "QMessageBox { background-color: #ffffff; color: #000000; }"
            " QMessageBox QLabel { color: #000000; background-color: #ffffff; }"
            " QPushButton { background-color: #e0e0e0; color: #000000;"
            "                padding: 4px 12px; min-width: 60px; }"
        )
        box.exec_()

    @reconnect_if_needed
    def _leer_opcion_menu(self, menu_id):
        """Lee opcion y permiso con preflight de DB antes del callback Qt."""
        dato_menu = MenuLateral.get_by_id(menu_id)
        permitido = Acceso.ValidaMenu(
            usu_id=int(LeerConf("idUsuario") or 0),
            for_valid=dato_menu.for_id.for_valid,
        )
        return dato_menu, permitido

    def onClickItemMenu(self, item, _columna=0):
        """Maneja clicks sobre items del arbol de navegacion lateral.

        Toda la lectura DB queda dentro de un try del propio slot. De esta
        forma una conexion muerta tras inactividad no escapa al event loop de
        Qt ni puede cerrar el proceso silenciosamente.
        """
        if item is None:
            return
        menu_id = item.data(0, Qt.UserRole)
        if menu_id is None:
            return

        target = "opcion de menu id {}".format(menu_id)
        try:
            dato_menu, permitido = self._leer_opcion_menu(menu_id)
            if not permitido:
                return
            target = dato_menu.for_id.for_arch
            clase = self._resolver_clase_menu(target)
            self.ventana_menu_lateral = clase()
            self.ventana_menu_lateral.run()
        except DoesNotExist:
            return
        except Exception as exc:
            self._mostrar_error_menu(target, exc)

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
        if not Archivo:
            Ventanas.showAlert("Error", "Opcion de menu no establecida")
            return
        try:
            clase = self._resolver_clase_menu(Archivo)
            self.ventana = clase()
            self.ventana.run()
        except Exception as exc:
            self._mostrar_error_menu(Archivo, exc)

    def SalirSistema(self):
        BorrarConf()
        qApp.exit()

    def onClickBtnMenuIzquierda(self, boton, *args, **kwargs):
        """Compatibilidad: adapta botones ``Boton`` o ``QTreeWidgetItem``."""
        if hasattr(boton, "data") and callable(getattr(boton, "data", None)):
            self.onClickItemMenu(boton, 0)
            return
        if boton.text().replace("&", "").upper() == "CERRAR":
            qApp.exit()
            return

        target = "opcion de menu id {}".format(getattr(boton, "id", "?"))
        try:
            dato_menu, permitido = self._leer_opcion_menu(boton.id)
            if permitido:
                target = dato_menu.for_id.for_arch
                self.ventana_menu_lateral = self._resolver_clase_menu(target)()
                self.ventana_menu_lateral.run()
        except DoesNotExist:
            pass
        except Exception as exc:
            self._mostrar_error_menu(target, exc)

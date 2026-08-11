# coding=utf-8
"""Demo local del shell moderno y dashboard operativo de RND.

Este script arma la ventana principal de RND con:

* Encabezado Vogel (#3).
* Barra lateral con algunos modulos representativos.
* Dashboard operativo (#4) con datos simulados.
* Tema QSS vogel2026 aplicado (#5).

NO necesita MySQL: parchea ``ParamSist`` y los servicios del
dashboard para devolver datos de muestra. Tampoco genera el
ejecutable: corre el proceso Python directo.

Uso::

    .venv-build\\Scripts\\python.exe demo_dashboard.py

Para salir, cerrar la ventana.
"""

import logging
import os
import sys
from datetime import date, timedelta
from unittest.mock import MagicMock

# Forzar plataforma nativa (no offscreen) para que se vea la UI.
os.environ.setdefault("QT_QPA_PLATFORM", "")

# Hay que agregar el directorio del proyecto al path para que los
# imports absolutos (``vistas.X``) funcionen como cuando se corre
# ``main.py``.
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
os.chdir(ROOT)


def _parchear_bd():
    """Evita que el import de modelos abra MySQL.

    ``modelos.Proveedores.Proveedor`` ejecuta
    ``ParamSist.ObtenerParametro`` en el class body y eso intenta
    conectar. Lo parcheamos antes de cualquier import del paquete.
    Tambien parchemos el menu y el dashboard para mostrar datos
    de muestra.
    """
    from modelos import ParametrosSistema
    ParametrosSistema.ParamSist.ObtenerParametro = MagicMock(
        return_value="ARG"
    )

    # Apuntar ``ubicacion_sistema`` al directorio del proyecto
    # para que ``utiles.tema`` encuentre ``temas/vogel2026.qss`` y
    # ``imagen()`` resuelva los iconos de la barra lateral.
    from pyqt5libs.pyqt5libs import utiles as pyqt_utiles
    pyqt_utiles.ubicacion_sistema = lambda: ROOT
    pyqt_utiles.LeerIni = MagicMock(return_value="")
    pyqt_utiles.GrabaConf = MagicMock()
    pyqt_utiles.BorrarConf = MagicMock()

    # Accesos.Acceso.AccesoUsuario: admin (todo permitido)
    from modelos.Accesos import Acceso
    Acceso.AccesoUsuario = MagicMock(return_value=True)
    Acceso.ValidaMenu = MagicMock(return_value=True)

    # MenuLateral.Cabeceras() devuelve un par de cabeceras con items
    from modelos.Formula import Formula, MenuLateral

    def _mk_cabecera(id_, nombre):
        c = MagicMock()
        c.id = id_
        c.nombre = nombre
        return c

    def _mk_item(id_, nombre, for_imag="", for_nomb="", for_arch="",
                 for_valid="VAL"):
        item = MagicMock()
        item.id = id_
        item.nombre = nombre
        formula = MagicMock()
        formula.for_id = id_
        formula.for_imag = for_imag
        formula.for_nomb = for_nomb
        formula.for_arch = for_arch
        formula.for_valid = for_valid
        item.for_id = formula
        return item

    MenuLateral.Cabeceras = staticmethod(
        lambda: [
            _mk_cabecera(1, "Operaciones"),
            _mk_cabecera(2, "Administracion"),
        ]
    )

    items_por_padre = {
        1: [
            _mk_item(1, "Hojas de ruta", for_imag="ruta_reparto.png",
                     for_nomb="Hojas de ruta", for_arch="Main",
                     for_valid="HojaDeRuta"),
            _mk_item(2, "Equipos", for_imag="maquinas.png",
                     for_nomb="Equipos", for_arch="ABMEquipos",
                     for_valid="Equipos"),
        ],
        2: [
            _mk_item(3, "Clientes", for_imag="clientes.png",
                     for_nomb="Clientes", for_arch="ABMClientes",
                     for_valid="ABMClientes"),
            _mk_item(4, "Empleados", for_imag="empleados.png",
                     for_nomb="Empleados", for_arch="ABMEmpleados",
                     for_valid="ABMEmpleados"),
        ],
    }
    original_select = MenuLateral.select

    def _select_patched(*args, **kwargs):
        q = MagicMock()
        items = items_por_padre.get(kwargs.get("for_pare"), [])

        def _where(condicion):
            # Comparamos el lado derecho del condition para el padre
            padre_id = None
            try:
                padre_id = condicion.right.value
            except AttributeError:
                padre_id = None
            hijos = items_por_padre.get(padre_id, [])
            m = MagicMock()
            m.order_by.return_value = hijos
            return m

        q.join.return_value.where.side_effect = _where
        return q

    MenuLateral.select = _select_patched

    # Servicios del dashboard: devolver datos de muestra
    from vistas.dashboard import servicios
    servicios.hojas_ruta_del_dia = MagicMock(
        return_value=servicios.ResultadoConsulta(
            estado="ok", cantidad=8, fecha=date.today()
        )
    )
    servicios.vencimientos_proximos = MagicMock(
        return_value=servicios.ResultadoConsulta(
            estado="ok", cantidad=3, fecha=date.today()
        )
    )

    # LoginController: auto-aprobado
    from controladores.Login import LoginController
    LoginController.exec_ = MagicMock()
    LoginController.lRetVal = True

    # Evitar el reconnect_if_needed del controlador principal
    from controladores.Main import MainController
    original_login = MainController.login

    def _login_mock(self, *args, **kwargs):
        # Simula que el login ya paso: setea confs y arma menu
        from pyqt5libs.pyqt5libs.utiles import GrabaConf
        GrabaConf(valor="demo", clave="usuario")
        GrabaConf(valor="1", clave="idUsuario")
        # Llama al login original saltando el LoginController
        # ya que la logica post-login esta inline en el metodo.
        # Replicamos la parte no-DB del login:
        self.view.actualizar_encabezado(
            usuario="oscar (demo)",
            servidor="srv-demo",
            base="rnd",
            estado="Demo (datos simulados)",
            version="2026.8.3",
        )
        self.view.setWindowTitle(
            "RND Demo - Dashboard operativo (issue #4)"
        )
        self._inicializar_dashboard(usu_id=1)
        # Cargar la barra lateral con los items de muestra
        self.view.cargar_menu_lateral(1)
        # Menues tradicionales (puede fallar por la BD, esta OK)
        try:
            self.ArmaMenu()
        except Exception:
            pass
        return True

    MainController.login = _login_mock


def main():
    logging.basicConfig(level=logging.INFO)
    _parchear_bd()

    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)

    # Aplicar el tema Vogel 2026 (issue #5)
    from utiles.tema import aplicar_tema
    aplicar_tema(app)

    # Construir el controlador principal con la vista
    from controladores.Main import MainController
    controller = MainController()

    # Mostrar la ventana maximizada
    controller.view.showMaximized()

    # Log de navegacion desde el dashboard
    if controller.view.dashboard is not None:
        def _log_navegacion(clave):
            logging.info("[demo] click en tarjeta: %s", clave)
        controller.view.dashboard.navegar.connect(_log_navegacion)

    # Hook para que el menu lateral tambien logee clicks
    try:
        original = controller.view.onClickItemMenu
        def _on_click_log(item, _col=0):
            try:
                mid = item.data(0, item.data.__class__.UserRole) \
                    if hasattr(item, "data") else None
            except Exception:
                mid = None
            logging.info("[demo] click en menu lateral: id=%s texto=%s",
                         mid, item.text(0) if hasattr(item, "text") else "?")
        controller.view.barra_lateral.arbol.itemClicked.connect(_on_click_log)
    except Exception as exc:
        logging.warning("[demo] no pude conectar log de menu: %s", exc)

    # Bypass del login real: saltamos el login() y dejamos la UI lista
    # (la vista ya esta construida; el shell+dashboard se arman al
    # invocar login. Lo invocamos via el mock).
    try:
        controller.login()
    except Exception as exc:
        logging.warning("[demo] login mock fallo (no rompe la UI): %s", exc)

    # Mensaje de bienvenida por consola
    print()
    print("=" * 60)
    print("RND DEMO - Shell moderno + Dashboard + QSS Vogel 2026")
    print("=" * 60)
    print("Cierra la ventana para salir.")
    print("Los clicks en el dashboard o el menu se loguean por consola.")
    print()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())

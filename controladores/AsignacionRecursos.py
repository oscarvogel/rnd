# coding=utf-8
from datetime import date

from PyQt5.QtCore import QDate

from modelos.Clientes import RutaReparto
from modelos.Empleados import Empleado
from modelos.Equipos import Equipos
from modelos.HojaRuta import HojaDeRuta
from modelos.ModeloBase import reconnect_if_needed
from modelos.ParametrosSistema import ParamSist
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs.Ventanas import showAlert
from pyqt5libs.pyqt5libs.utiles import inicializar_y_capturar_excepciones
from utiles.asignacion_recursos import construir_resumen, validar_asignacion
from vistas.AsignacionRecursos import AsignacionRecursosView


class AsignacionRecursosController(ControladorBase):
    def __init__(self, fecha_inicial=None, ruta_inicial=0):
        super().__init__()
        self.view = AsignacionRecursosView()
        self.empleado_generico = int(ParamSist.ObtenerParametro("EMPLEADO_GENERICO", "23"))
        self.camion_generico = int(ParamSist.ObtenerParametro("CAMION_GENERICO", "1"))
        self.ruta_inicial = int(ruta_inicial or 0)
        inicial = fecha_inicial or date.today()
        self.view.fecha.setDate(QDate(inicial.year, inicial.month, inicial.day))
        self.resumen_actual = construir_resumen([])
        self.conectarWidgets()
        self.cargar_opciones()
        if self.ruta_inicial:
            self.cargar_hoja()

    def conectarWidgets(self):
        self.view.btn_cargar.clicked.connect(self.cargar_hoja)
        self.view.cbo_ruta.currentIndexChanged.connect(self.cargar_hoja)
        self.view.btn_guardar.clicked.connect(self.guardar_asignacion)
        self.view.btn_siguiente.clicked.connect(self.ir_validacion)
        self.view.btn_cerrar.clicked.connect(self.view.close)

    def fecha_actual(self):
        qdate = self.view.fecha.date()
        return date(qdate.year(), qdate.month(), qdate.day())

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar_opciones(self, *args, **kwargs):
        rutas = RutaReparto.select().where(RutaReparto.activo == True).order_by(RutaReparto.descripcion)
        responsables = Empleado.select().where(Empleado.activo == True).order_by(Empleado.nombre)
        equipos = Equipos.select().where(Equipos.activo == True).order_by(Equipos.descripcion)
        self.view.cargar_rutas([(r.id, r.descripcion) for r in rutas], self.ruta_inicial)
        self.view.cargar_responsables([
            (e.id, e.nombre_completo) for e in responsables if int(e.id) != self.empleado_generico
        ])
        self.view.cargar_equipos([
            (e.id, str(e)) for e in equipos if int(e.id) != self.camion_generico
        ])

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def cargar_hoja(self, *args, **kwargs):
        ruta_id = self.view.ruta_id()
        if not ruta_id:
            self.resumen_actual = construir_resumen([])
            self.view.set_resumen(self.resumen_actual, "Seleccione una ruta")
            self.view.lbl_estado.setText("Seleccione una hoja de ruta para continuar.")
            self.view.btn_siguiente.setEnabled(False)
            return

        registros = list(
            HojaDeRuta.select().where(
                (HojaDeRuta.fecha == self.fecha_actual()) &
                (HojaDeRuta.ruta == ruta_id)
            )
        )
        self.resumen_actual = construir_resumen(registros)
        if self.resumen_actual.vacia:
            texto_actual = "Sin pedidos"
        elif self.resumen_actual.asignacion_mixta:
            texto_actual = "Asignación inconsistente entre pedidos. Guardar normalizará toda la hoja."
        else:
            responsable = self._nombre_responsable(self.resumen_actual.responsable_id)
            equipo = self._nombre_equipo(self.resumen_actual.equipo_id)
            texto_actual = "{} · {}".format(responsable, equipo)
            self.view.seleccionar_recursos(
                self.resumen_actual.responsable_id,
                self.resumen_actual.equipo_id,
            )
        self.view.set_resumen(self.resumen_actual, texto_actual)
        completa = self.resumen_actual.recursos_completos(
            self.empleado_generico, self.camion_generico
        )
        self.view.btn_siguiente.setEnabled(completa)
        self.view.lbl_estado.setText(
            "Recursos completos. Puede continuar a validar la hoja."
            if completa else
            "Falta asignar un chofer y un camión válidos."
        )

    def _nombre_responsable(self, empleado_id):
        if not empleado_id or int(empleado_id) == self.empleado_generico:
            return "Chofer pendiente"
        try:
            return Empleado.get_by_id(empleado_id).nombre_completo
        except Exception:
            return "Chofer #{}".format(empleado_id)

    def _nombre_equipo(self, equipo_id):
        if not equipo_id or int(equipo_id) == self.camion_generico:
            return "Camión pendiente"
        try:
            return str(Equipos.get_by_id(equipo_id))
        except Exception:
            return "Camión #{}".format(equipo_id)

    @reconnect_if_needed
    @inicializar_y_capturar_excepciones
    def guardar_asignacion(self, *args, **kwargs):
        ruta_id = self.view.ruta_id()
        responsable_id = self.view.responsable_id()
        equipo_id = self.view.equipo_id()
        valido, mensaje = validar_asignacion(
            self.resumen_actual,
            responsable_id,
            equipo_id,
            self.empleado_generico,
            self.camion_generico,
        )
        if not valido:
            showAlert("Sistema", mensaje)
            return

        (
            HojaDeRuta.update(
                responsable=responsable_id,
                equipo_asignado=equipo_id,
            )
            .where(
                (HojaDeRuta.fecha == self.fecha_actual()) &
                (HojaDeRuta.ruta == ruta_id)
            )
            .execute()
        )

        inconsistentes = (
            HojaDeRuta.select()
            .where(
                (HojaDeRuta.fecha == self.fecha_actual()) &
                (HojaDeRuta.ruta == ruta_id) &
                (
                    (HojaDeRuta.responsable != responsable_id) |
                    (HojaDeRuta.equipo_asignado != equipo_id)
                )
            )
            .count()
        )
        if inconsistentes:
            showAlert("Sistema", "No se pudieron actualizar todos los pedidos de la hoja")
            self.cargar_hoja()
            return

        showAlert("Sistema", "Chofer y camión asignados correctamente a toda la hoja de ruta")
        self.cargar_hoja()

    def ir_validacion(self):
        # #23 reemplazará este destino por la validación operativa dedicada.
        from controladores.VerHojaRuta import VerHojaRutaController
        self.ventana_siguiente = VerHojaRutaController(fecha_inicial=self.fecha_actual())
        self.ventana_siguiente.run()

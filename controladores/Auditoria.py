import json
from modelos.ModeloBase import Auditoria, obtener_historial
from pyqt5libs.libs.controladores.ControladorBase import ControladorBase
from pyqt5libs.pyqt5libs import Ventanas
from pyqt5libs.pyqt5libs.utiles import FormatoFecha, inicializar_y_capturar_excepciones
from vistas.Auditoria import AuditoriaView


def format_registro(data):
    if not data:
        return "(Sin datos)"
    lines = []
    for key, value in data.items():
        # Si el valor es None o vacío, lo mostramos como vacío
        value = str(value) if value is not None else ""
        lines.append(f"{key.capitalize()}: {value.strip()}")
    return "\n".join(lines)

def acortar(texto, max_chars=50):
    return texto[:max_chars] + "..." if len(texto) > max_chars else texto

def historial_dict_a_lista_acortado(item):
    return [
        FormatoFecha(item['fecha']),
        item['accion'],
        acortar(item['antes']),
        acortar(item['despues']),
        item['id']
    ]

class AuditoriaController(ControladorBase):
    
    def __init__(self, modelo_nombre, registro_id):
        super().__init__()
        self.view = AuditoriaView()
        self.view.label_titulo.setText(f"Historial - {modelo_nombre} [{registro_id}]")
        self.modelo_nombre = modelo_nombre
        self.registro_id = registro_id
        self.conectarWidgets()
        self.CargaDatos()
        
    def conectarWidgets(self):
        self.view.btn_cerrar.clicked.connect(self.view.Cerrar)
        self.view.gridDatos.cellClicked.connect(self.mostrar_detalle)
        
    def CargaDatos(self):
        datos = obtener_historial(self.modelo_nombre, self.registro_id)
        self.view.gridDatos.limpiarGrilla()

        for fila, item in enumerate(datos):
            self.view.gridDatos.AgregaItem(historial_dict_a_lista_acortado(item))

    @inicializar_y_capturar_excepciones
    def mostrar_detalle(self, *args, **kwargs):
        """Abre la ventana de ficha personal del empleado seleccionado."""
        if self.view.gridDatos.currentRow() == -1:
            Ventanas.showAlert("Sistema", "No se ha seleccionado ningun registro")
            return
        
        auditoria_id = self.view.gridDatos.ObtenerItemNumerico(
            fila=self.view.gridDatos.currentRow(), col='id'
        )
        auditoria = Auditoria.get_by_id(auditoria_id)
        self.view.datos_antes.setPlainText(format_registro(json.loads(auditoria.datos_antiguos)))
        self.view.datos_despues.setPlainText(format_registro(json.loads(auditoria.datos_nuevos)))
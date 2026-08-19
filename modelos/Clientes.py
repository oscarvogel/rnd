import peewee
from PyQt5.QtWidgets import QMessageBox, QPushButton

from modelos.ModeloBase import ModeloBase
from modelos.ParametrosSistema import ParamSist
from modelos.Proveedores import Proveedor
from pyqt5libs.libs.vistas.Busqueda import Buscador, UiBusqueda
from pyqt5libs.pyqt5libs.ComboBox import ComboSQL
from pyqt5libs.pyqt5libs.Validaciones import ValidaConTexto


class RutaReparto(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Descripción')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')

    class Meta:
        db_table = 'rutas_reparto'
    
    def __str__(self):
        return self.descripcion
        
class Localidades(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    descripcion = peewee.CharField(max_length=100, null=False, unique=True)
    provincia = peewee.CharField(max_length=100, null=False)

    class Meta:
        db_table = 'localidades'
    
    def __str__(self):
        return self.descripcion
    
class Cliente(ModeloBase):
    
    id = peewee.AutoField(primary_key=True)
    razon_social = peewee.CharField(max_length=100, null=False, unique=True, verbose_name='Razón Social')
    direccion = peewee.CharField(max_length=100, null=True, verbose_name='Dirección')
    telefono = peewee.CharField(max_length=20, null=True, verbose_name='Teléfono')
    cuit = peewee.CharField(
        max_length=20,
        null=True,
        unique=True,
        # Antes: ParamSist.ObtenerParametro(...) == 'ARG' else 'RUC' - requeria DB al importar.
        # El sistema RND opera casi siempre con nacionalidad ARG; se hardcodea 'CUIT'
        # y se evita la query al import-time. Si la nacionalidad cambia a RUC, mover
        # esta decision a runtime (ej. al inicializar la app o al construir el form).
        verbose_name='CUIT'
    )
    contacto = peewee.CharField(max_length=100, null=True, verbose_name='Contacto')
    activo = peewee.BooleanField(default=True, verbose_name='Activo')
    observaciones = peewee.TextField(null=True, verbose_name='Observaciones')
    ruta_reparto = peewee.ForeignKeyField(
        model=RutaReparto,
        backref='clientes',
        null=True,
        verbose_name='Ruta de Reparto', default=1
    )
    localidad = peewee.ForeignKeyField(
        model=Localidades,
        backref='clientes',
        null=True,
        verbose_name='Localidad'
    )

    class Meta:
        db_table = 'cliente'
    
    def __str__(self):
        return self.razon_social

class CodigoClienteProveedor(ModeloBase):
    id = peewee.AutoField(primary_key=True)
    codigo = peewee.CharField(max_length=100, null=False, verbose_name='Código')
    cliente = peewee.ForeignKeyField(
        model=Cliente,
        backref='codigos',
        null=False,
        verbose_name='Cliente'
    )
    proveedor = peewee.ForeignKeyField(
        model=Proveedor,
        backref='codigos',
        null=True,
        verbose_name='Proveedor'
    )


    class Meta:
        db_table = 'codigos_clientes_proveedores'
    
    def __str__(self):
        return self.codigo


class ValidaCliente(ValidaConTexto):
    modelo = Cliente
    nombre = Cliente.razon_social
    codigo = Cliente.id
    campos = [Cliente.id.name, Cliente.razon_social.name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Clientes"
    condiciones = [Cliente.activo == True]
    campos_busqueda = [Cliente.razon_social.column_name]

class cboRutaReparto(ComboSQL):
    modelo = RutaReparto
    cOrden = RutaReparto.descripcion
    campovalor = RutaReparto.id.name
    campo1 = RutaReparto.descripcion.name
    condicion = RutaReparto.activo == True


class BuscadorCliente(Buscador):
    modelo = Cliente
    nombre = Cliente.razon_social
    codigo = Cliente.id
    campos = [Cliente.id.name, Cliente.razon_social.name]
    campos_busqueda = [Cliente.razon_social.column_name]
    ancho = 50
    solo_numeros = True
    textoEtiqueta = "Buscar Clientes"
    valorRetorno = None
    lRetval = False  # indica si presiono en aceptar o cancelar

    def _nombre_cliente_actual(self):
        nombre = str(getattr(self, "valor_busqueda", "") or "").strip()
        if not nombre or nombre.lower() == "nan":
            return ""
        return nombre

    def _obtener_o_crear_cliente(self, nombre_cliente, parent=None):
        """Reutiliza un cliente homónimo o lo crea, devolviendo la instancia."""
        try:
            cliente = Cliente.get_or_none(
                peewee.fn.LOWER(Cliente.razon_social) == nombre_cliente.lower()
            )
            if cliente is None:
                with Cliente._meta.database.atomic():
                    cliente = Cliente.create(razon_social=nombre_cliente)
        except peewee.IntegrityError:
            cliente = Cliente.get_or_none(
                peewee.fn.LOWER(Cliente.razon_social) == nombre_cliente.lower()
            )
        except Exception as exc:
            QMessageBox.critical(
                parent,
                "Alta de cliente",
                "No se pudo crear el cliente: {}".format(exc),
            )
            return None

        if cliente is None:
            QMessageBox.warning(
                parent,
                "Alta de cliente",
                "No se pudo recuperar el cliente después del alta.",
            )
        return cliente

    def buscar(self, parent=None):
        """Busca/asocia un cliente y permite crearlo desde el mismo diálogo."""
        nombre_cliente = self._nombre_cliente_actual()

        ventana = UiBusqueda()
        ventana.modelo = self.modelo
        ventana.cOrden = self.cOrden
        ventana.campos = self.campos
        ventana.campoBusqueda = self.campos_busqueda if self.campos_busqueda else self.campoRetorno.column_name
        ventana.camposTabla = self.campos
        ventana.campoRetorno = self.codigo.column_name if isinstance(self.codigo, str) else self.codigo
        ventana.condiciones = self.condiciones

        if nombre_cliente:
            ventana.setWindowTitle("Buscar cliente — {}".format(nombre_cliente))

            btn_crear = QPushButton("Crear cliente")
            btn_crear.setToolTip(
                'Crear "{}" y continuar con la importación'.format(nombre_cliente)
            )
            ventana.horizontalLayout.insertWidget(0, btn_crear)

            def crear_y_seleccionar():
                cliente = self._obtener_o_crear_cliente(nombre_cliente, parent=ventana)
                if cliente is None:
                    return
                ventana.ValorRetorno = str(cliente.id)
                ventana.lRetval = True
                ventana.accept()

            btn_crear.clicked.connect(crear_y_seleccionar)

            # Deja visible exactamente a quién estamos intentando asociar y filtra
            # automáticamente la grilla desde que se abre el diálogo.
            ventana.lineEdit.setText(nombre_cliente)
        else:
            ventana.CargaDatos()

        ventana.exec_()
        if ventana.lRetval:
            self.valorRetorno = ventana.ValorRetorno
            self.lRetval = True
            return self.valorRetorno

        self.valorRetorno = None
        self.lRetval = False
        return None

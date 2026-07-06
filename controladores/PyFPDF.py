import decimal
import os
import sys
from datetime import date, datetime
from functools import wraps

__version__ = "1.0"

from fpdf import Template, FPDF

from modelos.ParametrosSistema import ParamSist
from pyqt5libs.pyqt5libs import Constantes, Ventanas
from pyqt5libs.pyqt5libs.utiles import LeerIni, imagen, FormatoFecha, getFileName, AbrirArchivo, \
    inicializar_y_capturar_excepciones

DEBUG = LeerIni("debug") == 'S'


class PyFPDFController(FPDF):
    # nombre del archivo pdf a generar
    base_archivo = None

    # ubicacion de las cabeceras
    ubicacion = {}

    anchos_formato = []

    col_suma = {}

    decimales = 2

    imprimeceros = False

    LanzarExcepciones = True

    corrimiento_cabecera = 0

    def __init__(self):
        super().__init__()
        if not os.path.exists('pdf'):
            os.makedirs('pdf')
        self.set_author(ParamSist.ObtenerParametro("EMPRESA"))
        self.set_creator(ParamSist.ObtenerParametro("EMPRESA"))
        self.setFuente(familia='Courier')

    def check_page(fn):
        "Decorator to protect drawing methods"

        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            if not self.page and not kwargs.get('split_only'):
                self.error("No page open, you need to call add_page() first")
            else:
                return fn(self, *args, **kwargs)

        return wrapper

    def EncabezadoEmpresa(self, imprimex=True):
        # logo
        logo = ParamSist.ObtenerParametro("LOGO_ENCABEZADO")
        if logo:
            self.image(imagen(logo), 0, 0 + self.corrimiento_cabecera, 33)
        else:
            self.image(Constantes.LOGO, 0, 0 + self.corrimiento_cabecera, 33)
        # titulo
        # fuente
        self.set_font('Courier', '', 15)
        self.set_xy(30, 0 + self.corrimiento_cabecera)
        self.set_font_size(10.)
        self.cell(0, 4, ParamSist.ObtenerParametro('EMPRESA'), border=0)
        self.set_x(100)
        if imprimex:
            self.set_font_size(20.)
            self.cell(0, 4, "(X)", border=0)
        self.set_font_size(8.)
        self.set_x(120)
        encabezado = u"Tel: {} CUIT: {}".format(ParamSist.ObtenerParametro("TELEFONO_EMPRESA"),
                                                ParamSist.ObtenerParametro('CUIT_EMPRESA'))
        self.set_x(self.getAnchoPagina() - self.get_string_width(encabezado) - 20)
        self.cell(0, 4, encabezado, border=0, ln=5)
        self.cell(35, 4, u"{}".format(ParamSist.ObtenerParametro('DOMICILIO_EMPRESA')), border=0, ln=5)
        self.set_x(120)
        fecha = 'Fecha impresion: {}'.format(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
        self.set_x(self.getAnchoPagina() - self.get_string_width(fecha) - 20)
        self.setFuente(tamanio=8)
        self.Celda(0, alto=4, txt=fecha, ln=5, fuente=True)

        if imprimex:
            self.set_font_size(6.)
            self.cell(0, 4, u"Documento no valido como factura", border=0)
        self.set_font_size(10.)
        self.set_x(160)
        encabezado = u"{}".format(ParamSist.ObtenerParametro('TIPO_RESP_EMPRESA'))
        self.set_x(self.getAnchoPagina() - self.get_string_width(encabezado) - 20)
        self.cell(0, 4, encabezado, border=0, ln=1)
        self.set_x(30)
        self.cell(35, 4, u'Ingreso Brutos: {}'.format(ParamSist.ObtenerParametro("IIBB_EMPRESA")), ln=1)
        self.set_y(self.get_y() + 10)
        self.line(x1=0, x2=self.w, y1=self.get_y(), y2=self.get_y())
        self.set_y(self.get_y() + 5)

    def PiePagina(self):
        self.ln(4)
        self.line(0, self.get_y(), 230, self.get_y())
        self.set_x(5)
        self.cell(210, 4, u"{}".format(ParamSist.ObtenerParametro('DOMICILIO_EMPRESA')), border=0, ln=1, align='C')
        self.set_x(5)
        self.cell(210, 4, u"{}".format(ParamSist.ObtenerParametro('LOCALIDAD_EMPRESA')), border=0, ln=1, align='C')
        self.set_x(5)
        self.cell(210, 4, u"Tel: {} Email: {} Web: {}".format(ParamSist.ObtenerParametro("TELEFONO_EMPRESA"),
                                                              ParamSist.ObtenerParametro('EMAIL_EMPRESA'),
                                                              ParamSist.ObtenerParametro('WEB_EMPRESA')), border=0,
                  ln=1, align='C')

    def TituloInforme(self, titulo='', familia='arial', tamanio=14, estilo='B', y=0, alineacion='C'):
        if y != 0:
            self.set_y(y)
        self.setFuente(familia=familia, tamanio=tamanio, estilo=estilo)
        self.Celda(
            ancho=self.getAnchoPagina(), alto=0,
            txt=titulo, alineacion=alineacion, fuente=True
        )
        self.setFuente()
        self.set_y(self.get_y() + 5)

    def getAnchoPagina(self):
        return self.w

    def setFuente(self, familia='courier', estilo='', tamanio=10):
        self.set_font(family=familia, style=estilo, size=tamanio)

    @check_page
    def Celda(self, ancho=0, alto=0, txt='', borde=0, ln=0, alineacion='',
              relleno=0, link='', x=0, y=0, *args, **kwargs):
        if not 'fuente' in kwargs:
            self.setFuente()
        if 'tamanio' in kwargs:
            self.set_font_size(kwargs['tamanio'])
        # self.CheckPageBreak(ln)

        if isinstance(txt, (int, float, decimal.Decimal)):
            if 'decimales' in kwargs:
                cant_dec = kwargs['decimales']
            else:
                cant_dec = 2
            txt = f'{txt:,.{cant_dec}f}'

        if alineacion == 'D':
            alineacion = 'R'
        elif alineacion == 'I':
            alineacion = 'L'

        if x != 0:
            self.set_x(x)
        if y != 0:
            self.set_y(y)
        if 'multi' in kwargs:
            self.multi_cell(w=ancho, h=alto, txt=txt, border=borde, align=alineacion, fill=relleno)
            if ln > 0:
                self.AgregaLineas(ln)
        else:
            self.cell(w=ancho, h=alto, txt=txt, border=borde, ln=ln, align=alineacion, fill=relleno, link=link)

    def CheckPageBreak(self, h=0):
        if self.get_y() + h > self.page_break_trigger:
            self.add_page(self.cur_orientation)

    def AgregaLineas(self, ln):
        # self.CheckPageBreak(ln)
        self.ln(ln)

    def ImprimeCabecera(self, ubicaciones=None, tamanio=8):
        if not ubicaciones:
            ubicaciones = self.ubicacion
        self.line(x1=0, x2=self.getAnchoPagina(), y1=self.get_y(), y2=self.get_y())
        self.ln(4)

        i = 0
        for k, v in ubicaciones.items():
            ancho = 0
            self.Texto(x=v, y=self.get_y(), txt='{:>{}}'.format(k, ancho), tamanio=tamanio)
            i += 1

        self.ln(4)
        self.line(x1=0, x2=self.getAnchoPagina(), y1=self.get_y(), y2=self.get_y())

    @check_page
    def Texto(self, x=0, y=0, txt='', alineacion='D', ancho=0, ln=0, *args, **kwargs):
        # negrita = self.font_style
        if 'tamanio' in kwargs:
            self.set_font_size(kwargs['tamanio'])

        if 'negrita' in kwargs:
            self.set_font(self.font_family, kwargs['negrita'], self.font_size_pt)
        # self.CheckPageBreak(ln)

        imprime = True
        if isinstance(txt, (decimal.Decimal, int, float)):
            imprime = False
            if self.imprimeceros:
                self.text(x, y, txt='{:12,.{}f}'.format(txt, self.decimales))
            else:
                if txt != 0:
                    self.text(x, y, txt='{:12,.{}f}'.format(txt, self.decimales))
        elif isinstance(txt, (date)):
            txt = FormatoFecha(txt, formato='dma')

        if imprime:
            if alineacion == 'D':
                self.text(x, y, txt='{:>{}}'.format(txt, ancho))
            elif alineacion == 'I':
                self.text(x, y, txt='{:<{}}'.format(txt, ancho))
            else:
                self.text(x, y, txt='{:^{}}'.format(txt, ancho))
            # self.set_font(self.font_family, negrita, self.font_size_pt)
        if ln > 0:
            self.ln(ln)
        # self.ln(ln)

    def AgregaPagina(self, orientacion='V'):
        if orientacion == 'V':  # si es vertical pongo como Portrait cualquier otro caracter va Landscape
            orientacion = 'P'
        else:
            orientacion = 'L'

        self.add_page(orientation=orientacion)

    def ImprimeDetalle(self, item, tamanio_fuente=8, ubicacion=None, negrita='',
                       checkbreak=4, multi_linea = []):
        # self.set_font_size(tamanio_fuente)
        self.set_font(self.font_family, negrita, tamanio_fuente)
        self.CheckPageBreak(checkbreak)

        if not ubicacion:
            ubicacion = self.ubicacion
        self.ln(4)
        i = 0
        for k, v in ubicacion.items():
            if i in self.col_suma:
                self.col_suma[i] += item[i]

            derecha = False

            if isinstance(item[i], (decimal.Decimal, float, int)):
                derecha = True

            if i in multi_linea:
                self.Celda(ancho=80, alto=0, txt=item[i], tamanio_fuente=tamanio_fuente,
                           x=v, y=self.get_y(), fuente=True)
            else:
                self.Texto(x=v, y=self.get_y(), txt=item[i], alineacion='D' if derecha else 'I')
            i += 1

    @inicializar_y_capturar_excepciones
    def Imprime(self, pdf=None, *args, **kwargs):
        if not self.base_archivo:
            self.base_archivo = "archivo"
        cArchivo = getFileName(self.base_archivo, False)
        cArchivoPDF = cArchivo + '.pdf'
        if pdf:
            pdf.output(cArchivoPDF)
            AbrirArchivo(cArchivoPDF)
        else:
            Ventanas.showAlert("Sistema", "No esta especificado el objeto pdf")

    def TrazaLinea(self, x1=None, y1=None, x2=None, y2=None, grosor=0):
        self.set_line_width(width=grosor)
        if not x1:
            x1 = self.get_x()
        if not y1:
            y1 = self.get_y()
        if not x2:
            x2 = self.getAnchoPagina()
        if not y2:
            y2 = self.get_y()
        self.line(x1, y1, x2, y2)

    def color_relleno(self, rojo=0, verde=-1, azul=-1):
        """
        :param rojo: si no se se proporciona el verde y azul, indca el nivel de gris escala(0,255)
        :param verde: escala(0,255)
        :param azul: escala(0,255)
        :return:
        """
        self.set_fill_color(r=rojo, g=verde, b=azul)

    def cuadro(self, x: float, y: float, w: float, h: float, style=''):
        """
        :param x: Abscissa of upper-left corner.
        :param y: Ordinate of upper-left corner.
        :param w: Width.
        :param h: Height.
        :param style: Style of rendering. Possible values are:
                    D or empty string: draw. This is the default value.
                    F: fill
                    DF or FD: draw and fill
        :return:
        """
        self.rect(x, y, w, h, style)


class PyFPDFPlantilla(FPDF):

    def __init__(self):
        super().__init__()
        self.Exception = self.Traceback = ""
        self.InstallDir = LeerIni('iniciosistema')
        if sys.platform == "win32":
            self.Locale = "Spanish_Argentina.1252"
        elif sys.platform == "linux2":
            self.Locale = "es_AR.utf8"
        else:
            # plataforma no soportada aun (jython?), emular
            self.Locale = None
        self.FmtCantidad = self.FmtPrecio = "0.2"
        self.CUIT = ''
        self.elements = []
        self.datos = []
        self.pdf = {}
        self.comprobante = {}
        # sys.stdout = self.log
        # sys.stderr = self.log
        self.LanzarExcepciones = True

    @inicializar_y_capturar_excepciones
    def CrearPlantilla(self, papel="A4", orientacion="portrait"):
        "Iniciar la creación del archivo PDF"

        # sanity check:
        for field in self.elements:
            # si la imagen no existe, eliminar nombre para que no falle fpdf
            if field['type'] == 'I' and not os.path.exists(field["text"]):
                # ajustar rutas relativas a las imágenes predeterminadas:
                if os.path.exists(os.path.join(self.InstallDir, field["text"])):
                    field['text'] = os.path.join(self.InstallDir, field["text"])
                else:
                    field['text'] = ""

        # genero el renderizador con propiedades del PDF
        t = Template(elements=self.elements,
                     format=papel, orientation=orientacion,
                     title="%s " % self.title,
                     author="CUIT %s" % self.CUIT,
                     subject="CAE %s" % self.subject,
                     keywords=LeerIni('nombre_sistema'),
                     creator='Servin LGSM %s (http://www.servinlgsm.com.ar)' % __version__, )
        self.template = t
        return True

    @inicializar_y_capturar_excepciones
    def CargarFormato(self, archivo="factura.csv"):
        "Cargo el formato de campos a generar desde una planilla CSV"

        # si no encuentro archivo, lo busco en el directorio predeterminado:
        if not os.path.exists(archivo):
            archivo = os.path.join(self.InstallDir, "plantillas", os.path.basename(archivo))

        if DEBUG:
            print("abriendo archivo ", archivo)

        for lno, linea in enumerate(open(archivo.encode('latin1')).readlines()):
            if DEBUG:
                print("procesando linea ", lno, linea)
            args = []
            for i, v in enumerate(linea.split(";")):
                if not v.startswith("'"):
                    v = v.replace(",", ".")
                else:
                    v = v  # .decode('latin1')
                if v.strip() == '':
                    v = None
                else:
                    v = eval(v.strip())
                args.append(v)
            self.AgregarCampo(*args)
        return True

    @inicializar_y_capturar_excepciones
    def AgregarCampo(self, nombre, tipo, x1, y1, x2, y2,
                     font="Arial", size=12,
                     bold=False, italic=False, underline=False,
                     foreground=0x000000, background=0xFFFFFF,
                     align="L", text="", priority=0, **kwargs):
        "Agrego un campo a la plantilla"
        # convierto colores de string (en hexadecimal)
        if isinstance(foreground, str):
            foreground = int(foreground, 16)
        if isinstance(background, str):
            background = int(background, 16)
        ##if isinstance(text, str): text = text.encode("latin1")
        field = {
            'name': nombre,
            'type': tipo,
            'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
            'font': font, 'size': size,
            'bold': bold, 'italic': italic, 'underline': underline,
            'foreground': foreground, 'background': background,
            'align': align, 'text': text, 'priority': priority}
        field.update(kwargs)
        self.elements.append(field)
        return True

    @inicializar_y_capturar_excepciones
    def GenerarPDF(self, archivo="", *args, **kwargs):
        "Generar archivo de salida en formato PDF"
        if not archivo:
            dest = "S"  # devolver buffer (string)
        else:
            dest = "F"  # guardar en archivo
        return self.template.render(archivo, dest)

    def AgregarDato(self, campo, valor, pagina='T'):
        "Agrego un dato a la factura (internamente)"
        self.datos.append({'campo': campo, 'valor': valor, 'pagina': pagina})
        return True

    @inicializar_y_capturar_excepciones
    def ProcesarPlantilla(self, num_copias=1, lineas_max=36, qty_pos='izq'):
        "Generar el PDF según la factura creada y plantilla cargada"
        f = self.template
        hojas = 1
        copias = {1: 'Original', 2: 'Duplicado', 3: 'Triplicado'}
        comprobante = self.comprobante

        for copia in range(1, num_copias + 1):
            # completo campos y hojas
            for hoja in range(1, hojas + 1):
                f.add_page()
                f.set('copia', copias.get(copia, "Adicional %s" % copia))
                f.set('hoja', str(hoja))
                f.set('hojas', str(hojas))
                f.set('Pagina', 'Pagina %s de %s' % (hoja, hojas))

                # establezco datos según configuración:
                for d in self.datos:
                    if d['pagina'] == 'P' and hoja != 1:
                        continue
                    if d['pagina'] == 'U' and hojas != hoja:
                        # no es la última hoja
                        continue
                    f.set(d['campo'], d['valor'])
                    for k, v in list(comprobante.items()):
                        f.set(k, v)

    @inicializar_y_capturar_excepciones
    def MostrarPDF(self, archivo, imprimir=False):
        if sys.platform.startswith(("linux", 'java')):
            os.system("evince ""%s""" % archivo)
        else:
            operation = imprimir and "print" or ""
            os.startfile(archivo, operation)
        return True

    @inicializar_y_capturar_excepciones
    def Cabecera(self, *args, **kwargs):
        logo = ParamSist.ObtenerParametro("LOGO_ENCABEZADO")
        if not logo:
            logo = Constantes.LOGO
        else:
            logo = imagen(logo)
        self.AgregarDato("logo", logo)
        self.AgregarDato("EMPRESA", "Razon social: {}".format(LeerIni(clave='empresa', key='FACTURA')))
        self.AgregarDato("MEMBRETE1", "Domicilio Comercial: {}".format(LeerIni(clave='membrete1', key='FACTURA')))
        self.AgregarDato("MEMBRETE2", LeerIni(clave='membrete2', key='FACTURA'))
        self.AgregarDato("CUIT", LeerIni(clave='cuit', key='FACTURA'))
        self.AgregarDato("IIBB", LeerIni(clave='iibb', key='FACTURA'))
        self.AgregarDato("IVA", "Condicion frente al IVA: {}".format(LeerIni(clave='iva', key='FACTURA')))
        self.AgregarDato("INICIO", "Fecha inicio actividades: {}".format(LeerIni(clave='inicio', key='FACTURA')))

    @inicializar_y_capturar_excepciones
    def PiePagina(self, *args, **kwargs):
        ok = self.AgregarDato("DOMICILIO_PIEPAGINA",
                              "Domicilio Comercial: {}".format(LeerIni(clave='membrete1', key='FACTURA')))
        ok = self.AgregarDato("DOMICILIO_PIEPAGINA_1",
                              "Domicilio Comercial: {}".format(LeerIni(clave='membrete2', key='FACTURA')))
        self.AgregarDato("DOMICILIO_PIEPAGINA_2",
                         u"Tel: {} Email: {} Web: {}".format(ParamSist.ObtenerParametro("TELEFONO_EMPRESA"),
                                                             ParamSist.ObtenerParametro('EMAIL_EMPRESA'),
                                                             ParamSist.ObtenerParametro('WEB_EMPRESA')))

    @inicializar_y_capturar_excepciones
    def EstableceCampo(self, campo='', valor='', *args, **kwargs):
        f = self.template
        f.set(campo, valor)

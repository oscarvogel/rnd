# coding=utf-8

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Utilidades varias necesarias en el sistema
import argparse
import calendar
import datetime
import decimal
from io import BytesIO
import locale
import logging
import os
import random
import smtplib
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import platform
from configparser import ConfigParser
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
from logging.handlers import RotatingFileHandler
from smtplib import SMTP
from dotenv import load_dotenv
from ..libs.vistas.select_printer import Ui_FormPrinter
import json
import re
from urllib.request import Request, urlopen

# Cargar variables de entorno desde el archivo .env
load_dotenv()

try:
    import win32print
except:
    pass
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QFileDialog, QInputDialog, QLineEdit
from os.path import join
from sys import argv

from PyQt5 import QtGui
from dateutil.relativedelta import relativedelta

try:
    import win32api
except:
    pass
from cryptography.fernet import Fernet

from . import Constantes, Ventanas
import threading

__author__ = "Jose Oscar Vogel <oscar@ferreteriaavenida.com.ar>"
__copyright__ = "Copyright (C) 2019 Steffen Hnos SRL"
__license__ = "GPL 3.0"
__version__ = "0.1"


# abro el archivo con el programa por defecto en windows
# tendria que ver como hacerlo en Linux
def AbrirArchivo(cArchivo=None):
    if not cArchivo:
        return

    # Convertimos la ruta a absoluta para evitar problemas
    ruta_absoluta = os.path.abspath(cArchivo)

    if not os.path.exists(ruta_absoluta):
        print(f"Error: El archivo no existe en la ruta: {ruta_absoluta}")
        return

    try:
        if platform.system() == 'Darwin':  # macOS
            subprocess.call(['open', ruta_absoluta])
        elif platform.system() == 'Windows':  # Windows
            os.startfile(ruta_absoluta)
        else:  # Linux
            subprocess.call(['xdg-open', ruta_absoluta])
    except Exception as e:
        print(f"No se pudo abrir el archivo: {e}")


# leo el archivo de configuracion del sistema
# recibe la clave y el key a leer en caso de que tenga mas de una seccion el archivo
def _normalizar_perfil(perfil):
    if not perfil:
        return ''
    valor = str(perfil).strip().upper()
    alias = {
        'DESARROLLO': 'FGPY',
        'DEVELOPMENT': 'FGPY',
        'DEV': 'FGPY',
        'MANTENIMIENTO': 'FGLOCAL',
        'MANT': 'FGLOCAL',
        'LOCAL': 'FGLOCAL',
        'PRODUCCION': 'FGPRODUCCION',
        'PRODUCCIÓN': 'FGPRODUCCION',
        'PROD': 'FGPRODUCCION',
    }
    return alias.get(valor, valor)


def _archivo_por_perfil(perfil):
    perfil_normalizado = _normalizar_perfil(perfil)
    if not perfil_normalizado:
        return ''

    if perfil_normalizado.endswith('.ini'):
        return perfil_normalizado

    archivos = {
        'FGPY': 'sistema.ini',
        'FGLOCAL': 'conil.ini',
        'FGPRODUCCION': 'ini\\sistema-fg-py.ini',
    }
    return archivos.get(perfil_normalizado, '')


def resolver_configuracion_activa():
    analizador = argparse.ArgumentParser(description='Sistema.', add_help=False)
    analizador.add_argument("-i", "--inicio", default=None)
    analizador.add_argument("-a", "--archivo", default=None)
    analizador.add_argument("-p", "--perfil", default=None)
    argumento, _ = analizador.parse_known_args()

    carpeta = argumento.inicio or os.getcwd()
    archivo = argumento.archivo
    perfil = argumento.perfil
    origen = 'cli-archivo'

    if not archivo:
        perfil = perfil or os.environ.get('FGPY_CONFIG')
        if perfil:
            origen = 'perfil'
            archivo = _archivo_por_perfil(perfil)

    if not archivo:
        archivo = 'sistema.ini'
        origen = 'fallback'

    perfil = _normalizar_perfil(perfil)

    ruta_absoluta = archivo
    if not os.path.isabs(ruta_absoluta):
        ruta_absoluta = join(carpeta, ruta_absoluta)

    if not os.path.exists(ruta_absoluta) and archivo != 'sistema.ini':
        archivo = 'sistema.ini'
        ruta_absoluta = join(carpeta, archivo)
        origen = 'fallback'

    return {
        'carpeta': carpeta,
        'archivo': archivo,
        'ruta': ruta_absoluta,
        'perfil': perfil,
        'origen': origen,
    }


def LeerIni(clave=None, key=None, carpeta=''):
    retorno = ''
    Config = ConfigParser()
    configuracion = resolver_configuracion_activa()
    archivoini = configuracion['archivo']
    carpeta = configuracion['carpeta']
    ruta_archivo = configuracion['ruta']
    # Config.read("fasa.ini")
    if carpeta:
        Config.read(ruta_archivo)
        # logging.debug("Archivo utilizado {}".format(join(carpeta, archivoini)))
    else:
        Config.read(archivoini)
        # logging.debug("Archivo utilizado {}".format(archivoini))

    try:
        if not key:
            key = 'param'
        retorno = Config.get(key, clave)
    except:
        # Ventanas.showAlert("Sistema", "No existe la seccion {}".format(clave))
        pass
    # print("archivo {} clave {} key {} carpeta {} valor {}".format(archivoini, clave, key, carpeta, retorno))
    return retorno


def GrabarIni(clave=None, key=None, valor=''):
    if not clave or not key:
        return
    Config = ConfigParser()
    Config.read('sistema.ini')
    cfgfile = open("sistema.ini", 'w')
    if not Config.has_section(key):
        Config.add_section(key)
    Config.set(key, clave, valor)
    Config.write(cfgfile)
    cfgfile.close()


def ubicacion_sistema():
    cUbicacion = LeerIni("iniciosistema") or os.path.dirname(argv[0])

    return cUbicacion


def imagen(archivo):
    if not archivo:
        return ""
    # Build a safe path to the imagenes folder inside the application root
    archivoImg = os.path.join(ubicacion_sistema(), 'imagenes', archivo)
    if os.path.exists(archivoImg):
        return archivoImg
    # fallback: try the filename as provided (in case it's already an absolute path)
    if os.path.exists(archivo):
        return archivo
    return ""


def icono_sistema():
    cIcono = QtGui.QIcon(imagen(LeerIni("logo")))
    if not cIcono:
        cIcono = QtGui.QIcon(imagen(LeerIni("icono")))
    return cIcono


def validar_cuit(cuit):
    # validaciones minimas
    if len(cuit) != 13 or cuit[2] != "-" or cuit[11] != "-":
        return False

    base = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]

    cuit = cuit.replace("-", "")  # remuevo las barras

    # calculo el digito verificador:
    aux = 0
    for i in range(10):
        aux += int(cuit[i]) * base[i]

    aux = 11 - (aux - (int(aux / 11) * 11))

    if aux == 11:
        aux = 0
    if aux == 10:
        aux = 9

    return aux == int(cuit[10])


def FechaMysql(fecha=None):
    if isinstance(fecha, str):
        retorno = fecha
    else:
        if not fecha:
            fecha = datetime.datetime.today()
        retorno = fecha.strftime('%Y%m%d')

    return retorno


def HoraMysql(hora=None):
    if not hora:
        hora = datetime.datetime.now()

    retorno = hora.strftime('%H:%M:%S')

    return retorno


def GrabaConf(clave=None, valor=None, sistema=None):
    if not sistema:
        sistema = Constantes.SISTEMA
    settings = QSettings(Constantes.EMPRESA, sistema)
    if clave:
        if isinstance(clave, (int, float, decimal.Decimal)):
            clave = str(clave)
        settings.setValue(clave, valor)


def LeerConf(clave=None, sistema=None):
    if not sistema:
        sistema = Constantes.SISTEMA
    settings = QSettings(Constantes.EMPRESA, sistema)
    if clave:
        cValorRetorno = settings.value(clave)
    else:
        cValorRetorno = None

    return cValorRetorno


def BorrarConf(clave=None, sistema=None):
    if not sistema:
        sistema = Constantes.SISTEMA

    settings = QSettings(Constantes.EMPRESA, sistema)
    if clave:
        settings.remove(clave)
    else:
        settings.clear()


# necesario porque en mysql tengo definido el campo boolean como bit
def EsVerdadero(valor):
    return valor == b'\01'


def inicializar_y_capturar_excepciones(func):
    "Decorador para inicializar y capturar errores"

    @wraps(func)
    def capturar_errores_wrapper(self, *args, **kwargs):
        try:
            # inicializo (limpio variables)
            self.Traceback = self.Excepcion = ""
            self.HuboError = False
            return func(self, *args, **kwargs)
        except Exception as e:
            ex = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
            self.HuboError = True
            self.Traceback = ''.join(ex)
            self.Excepcion = traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1])[0]
            logging.debug(self.Traceback)
            file = open("errors.log", "a")
            file.write(self.Traceback)
            file.close()
            # Cuando estamos en modo CLI puede que no exista un QApplication activo
            # En ese caso evitamos invocar los dialogs de Qt y mostramos por consola
            try:
                from PyQt5.QtWidgets import QApplication
                gui_available = hasattr(self, 'view') and self.view is not None and QApplication.instance() is not None
            except Exception:
                gui_available = False

            if gui_available:
                Ventanas.showAlert("Error", "Se ha producido un error \n{}".format(self.Excepcion))
            else:
                # Mostrar mensaje por consola en modo headless/CLI
                print("ERROR: Se ha producido un error:\n{}".format(self.Excepcion))

            # Siempre volcamos el traceback en consola y logs
            print(self.Traceback)
            logging.debug(self.Traceback)
            if LeerIni('debug') == 'N':
                # Envio un correo al administrador del sistema
                # si no se ha configurado el correo, no se envia nada
                try:
                    remitente = 'info@vogelconsultoria.com.ar'
                    destinatario = 'info@vogelconsultoria.com.ar'
                    mensaje = "{} {} Enviado desde mi Software de Gestion desarrollado por http://www.servinlgsm.com.ar".format(
                        self.Traceback, self.Excepcion
                    )
                    motivo = f"Se envia informe de errores de {LeerIni(clave='nombre_sistema')} . Usuario {LeerConf('usuario')}"
                    envia_correo(from_address=remitente, to_address=destinatario,
                                message=mensaje, subject=motivo)
                except:
                    pass
            if self.LanzarExcepciones:
                raise
        finally:
            pass

    return capturar_errores_wrapper


def getFileName(filename='pdf', base=False):
    tf = tempfile.NamedTemporaryFile(prefix=filename, mode='w+b')
    if base:
        return os.path.basename(tf.name)
    return tf.name


def FormatoFecha(fecha: object = datetime.datetime.today(), formato: object = 'largo') -> object:
    # Establecer la configuración que tenga el entorno del usuario
    locale.setlocale(locale.LC_ALL, '')
    retorno = ''
    if isinstance(fecha, (str)):
        retorno = fecha
    else:
        if formato == 'largo':
            retorno = datetime.datetime.strftime(fecha, '%d %b %Y')
        elif formato == 'corto':
            retorno = datetime.datetime.strftime(fecha, '%d-%b')
        elif formato == 'dma':
            retorno = datetime.datetime.strftime(fecha, '%d/%m/%Y')

    return retorno


def DeCodifica(dato):
    return "{}".format(bytearray(dato, 'latin-1', errors='ignore').decode('utf-8', 'ignore'))


def saveFileDialog(form=None, files=None, title="Guardar", filename="excel/archivo.xlsx"):
    ult_carpeta = LeerConf("ult_carpeta", "sistema")
    if ult_carpeta:
        filename = os.path.join(ult_carpeta, filename)
    if not files:
        files = "Todos los archivos (*);;Archivos de texto (*.txt)"
    options = QFileDialog.Options()
    fileName, _ = QFileDialog.getSaveFileName(form, title, filename,
                                              files, options=options)
    GrabaConf(clave="ult_carpeta",
              valor=os.path.dirname(os.path.abspath(fileName)),
              sistema="sistema")
    return fileName


def openFileNameDialog(form=None, files=None, title='Abrir', filename=''):
    ult_carpeta = LeerConf("ult_carpeta", "sistema")
    if ult_carpeta:
        filename = os.path.join(ult_carpeta, filename)
    options = QFileDialog.Options()
    # options |= QFileDialog.DontUseNativeDialog
    fileName, _ = QFileDialog.getOpenFileName(form, title, filename,
                                              files, options=options)
    ult_carpeta = GrabaConf(clave="ult_carpeta",
                            valor=os.path.dirname(os.path.abspath(fileName)),
                            sistema="sistema")
    if fileName:
        return fileName
    else:
        return ''


def InicioMes(dFecha=None):
    if not dFecha:
        dFecha = datetime.date.today()

    return dFecha.replace(day=1)


def FinMes(hFecha=None):
    if not hFecha:
        hFecha = datetime.date.today()

    return hFecha.replace(day=calendar.monthrange(hFecha.year, hFecha.month)[1])


def initialize_logger(output_dir):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # create console handler and set level to info
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create error file handler and set level to error
    handler = logging.FileHandler(os.path.join(output_dir, "error.log"), "w", encoding=None, delay="true")
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # create debug file handler and set level to debug
    # handler = logging.FileHandler(os.path.join(output_dir, "all.log"), "a")
    # handler.setLevel(logging.DEBUG)
    if LeerIni('debug') == 'S':
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        handler = RotatingFileHandler(os.path.join(output_dir, "all.log"), maxBytes=2000)
        logger.addHandler(handler)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt='%m/%d/%Y %I:%M:%S %p')
        handler.setFormatter(formatter)
        logger.addHandler(handler)


def obtener_dolar_oficial_compra_ambito(timeout=15):
    """Obtiene la cotizacion del Dolar Oficial (COMPRA) desde Ambito.

    Intenta primero consumir el JSON público y como fallback parsea el HTML.
    Devuelve un float o lanza ValueError si no se puede obtener un valor valido.
    """
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; ProcesoTarifa/1.0)'}

    api_url = 'https://mercados.ambito.com/dolar/oficial/variacion'
    try:
        req = Request(api_url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode('utf-8', errors='ignore')
        data = json.loads(payload)
        compra = str(data.get('compra', '')).strip()
        if compra:
            valor = float(compra.replace('.', '').replace(',', '.'))
            if valor > 0:
                return valor
    except Exception:
        pass

    # Fallback por si el sitio vuelve a renderizar el valor en el HTML.
    url = 'https://www.ambito.com/contenidos/dolar.html'
    req = Request(url, headers=headers)
    with urlopen(req, timeout=timeout) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    m = re.search(r'D[oó]lar\s+Oficial.*?(\d{1,4},\d{1,2})\s*(?:<[^>]+>\s*)*COMPRA', html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        raise ValueError('No se pudo extraer Dolar Oficial COMPRA desde Ambito (API y HTML)')

    valor_txt = m.group(1).replace('.', '').replace(',', '.')
    valor = float(valor_txt)
    if valor <= 0:
        raise ValueError(f'Valor de dolar invalido obtenido desde Ambito: {valor}')
    return valor



def getText(vista, titulo='', etiqueta='', valor=''):
    text, okPressed = QInputDialog.getText(vista, titulo, etiqueta, QLineEdit.Normal, valor)
    if okPressed and text != '':
        return text
    else:
        return ''


def GuardarArchivo(caption="Guardar archivo", directory="", filter="", filename=""):
    cArchivo = QFileDialog.getSaveFileName(caption=caption,
                                           directory=join(directory, filename),
                                           filter=filter)
    return cArchivo[0] if cArchivo else ''


def Normaliza(valor):
    valor = DeCodifica(valor)
    return valor.replace('Ñ', 'N').replace('ñ', 'n').replace('º', '')


def HayInternet():
    retorno = True
    try:
        socket.gethostbyname('google.com')
        c = socket.create_connection(('google.com', 80), 1)
        c.close()
    except socket.gaierror:
        print("DNS error")
        retorno = False
    except socket.error:
        print("Connection error")
        retorno = False

    return retorno


def envia_correo(from_address='', to_address='', message='', subject='',
                password_email='', to_cc='', archivo_adjunto=None, nombre_archivo=None, es_html=False) -> object:
    def send_email():
        try:
            # Intentar importar ParamSist aquí para evitar dependencias circulares
            try:
                from modelos.ParametrosSistema import ParamSist

                # Obtener configuración de ParamSist
                smtp_server = ParamSist.ObtenerParametro('SMTP_SERVER')
                smtp_port = ParamSist.ObtenerParametro('SMTP_PORT', '587')
                smtp_username = ParamSist.ObtenerParametro('EMAIL_ADDRESS')

                # Prioridad: 1. Argumento password_email, 2. ParamSist EMAIL_PASSWORD, 3. ParamSist PASSWORD_EMAIL
                smtp_password = password_email
                if not smtp_password:
                    smtp_password = ParamSist.ObtenerParametro('EMAIL_PASSWORD')
                if not smtp_password:
                    smtp_password = ParamSist.ObtenerParametro('PASSWORD_EMAIL')

            except ImportError:
                # Si no se puede importar (ej. uso fuera del proyecto), usar variables de entorno o valores por defecto
                logging.warning("No se pudo importar ParamSist, usando variables de entorno")
                smtp_server = os.getenv('SMTP_HOST')
                smtp_port = os.getenv('SMTP_PORT', '587')
                smtp_username = os.getenv('SMTP_USER')
                smtp_password = password_email or os.getenv('SMTP_PASS')

            # Fallback a variables de entorno si ParamSist devolvió vacío (y se pudo importar)
            if not smtp_server:
                smtp_server = os.getenv('SMTP_HOST')
            if not smtp_port:
                smtp_port = os.getenv('SMTP_PORT', '587')
            if not smtp_username:
                smtp_username = os.getenv('SMTP_USER')
            if not smtp_password:
                smtp_password = os.getenv('SMTP_PASS')

            smtp_use_ssl = os.getenv('SMTP_USE_SSL', 'false').lower() == 'true'

            # Sanitizar credenciales: eliminar espacios en blanco al inicio/fin
            if smtp_server:
                smtp_server = smtp_server.strip()
            if smtp_username:
                smtp_username = smtp_username.strip()
            if smtp_password:
                smtp_password = smtp_password.strip()

            # Validar que tengamos al menos el servidor
            if not smtp_server:
                logging.error("SMTP_SERVER no está configurado. No se puede enviar el correo.")
                return

            # Convertir puerto a entero
            try:
                smtp_port = int(smtp_port)
            except (ValueError, TypeError):
                logging.warning(f"Puerto SMTP inválido '{smtp_port}', usando 587 por defecto")
                smtp_port = 587

            logging.debug(f"Intentando conectar a SMTP: {smtp_server}:{smtp_port} (SSL={smtp_use_ssl})")

            # Construir mensaje MIME
            mime_message = MIMEMultipart()
            mime_message["From"] = from_address
            if isinstance(to_address, list):
                mime_message["To"] = ', '.join(to_address)
            else:
                mime_message["To"] = to_address
            mime_message["Subject"] = subject
            if es_html:
                mime_message.attach(MIMEText(message, 'html'))
            else:
                mime_message.attach(MIMEText(message))
            if to_cc:
                mime_message["Cc"] = to_cc

            # Procesamiento del archivo adjunto (puede ser ruta en disco o BytesIO)
            if archivo_adjunto:
                # Determinar el nombre del archivo
                if nombre_archivo:
                    filename = nombre_archivo
                elif isinstance(archivo_adjunto, str):
                    filename = os.path.basename(archivo_adjunto)
                else:
                    filename = "archivo_adjunto"

                # Manejar diferentes tipos de archivos adjuntos
                if isinstance(archivo_adjunto, str):
                    # Es una ruta de archivo en disco
                    with open(archivo_adjunto, 'rb') as archivo:
                        adjunto = MIMEApplication(archivo.read(), Name=filename)
                elif isinstance(archivo_adjunto, BytesIO):
                    # Es un archivo en memoria
                    archivo_adjunto.seek(0)  # Asegurarnos de leer desde el principio
                    adjunto = MIMEApplication(archivo_adjunto.read(), Name=filename)
                else:
                    # Es un objeto similar a un archivo
                    archivo_adjunto.seek(0)  # Asegurarnos de leer desde el principio
                    adjunto = MIMEApplication(archivo_adjunto.read(), Name=filename)

                adjunto['Content-Disposition'] = f'attachment; filename="{filename}"'
                mime_message.attach(adjunto)

            # Preparar lista de destinatarios para sendmail
            destinatarios = []
            if isinstance(to_address, list):
                destinatarios.extend(to_address)
            elif to_address:
                destinatarios.append(to_address)
            if to_cc:
                if isinstance(to_cc, list):
                    destinatarios.extend(to_cc)
                else:
                    destinatarios.append(to_cc)

            if not destinatarios:
                logging.error("No hay destinatarios para enviar el correo")
                return

            # Conectar al servidor SMTP con timeout
            servidor = None
            try:
                if smtp_use_ssl or smtp_port == 465:
                    # Usar SMTP_SSL para puerto 465 o si está explícitamente configurado
                    logging.debug("Usando SMTP_SSL")
                    servidor = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30)
                    # EHLO después de conectar con SSL
                    logging.debug("Enviando EHLO")
                    servidor.ehlo()
                else:
                    # Usar SMTP normal con STARTTLS para puerto 587 u otros
                    logging.debug("Usando SMTP con STARTTLS")
                    servidor = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
                    servidor.ehlo()
                    if smtp_port == 587:
                        servidor.starttls()
                        servidor.ehlo()

                # Autenticación si hay credenciales
                if smtp_username and smtp_password:
                    logging.debug(f"Autenticando con usuario: {smtp_username}")
                    servidor.login(smtp_username, smtp_password)
                else:
                    logging.warning("No se proporcionaron credenciales SMTP, intentando envío sin autenticación")

                # Enviar correo
                logging.debug(f"Enviando correo a: {destinatarios}")
                servidor.sendmail(from_address, destinatarios, mime_message.as_string())
                logging.info(f"Correo enviado exitosamente a {destinatarios}")

            except smtplib.SMTPAuthenticationError as e:
                logging.error(f"Error de autenticación SMTP: {e}")
            except smtplib.SMTPException as e:
                logging.error(f"Error SMTP: {e}")
            except socket.timeout:
                logging.error(f"Timeout al conectar con {smtp_server}:{smtp_port}")
            except Exception as e:
                logging.error(f"Error inesperado al enviar correo: {e}")
                logging.exception("Detalles del error:")
            finally:
                if servidor:
                    try:
                        servidor.quit()
                    except Exception:
                        pass

        except Exception as e:
            logging.error(f"Error en send_email: {e}")
            logging.exception("Detalles del error:")

    thread = threading.Thread(target=send_email, daemon=True)
    thread.start()
    return thread

def uniqueid():
    seed = random.getrandbits(32)
    while True:
        yield seed
        seed += 1


# ==============================================================================
def getFileProperties(fname):
    # ==============================================================================
    """
    Read all properties of the given file return them as a dictionary.
    """
    propNames = ('Comments', 'InternalName', 'ProductName',
                 'CompanyName', 'LegalCopyright', 'ProductVersion',
                 'FileDescription', 'LegalTrademarks', 'PrivateBuild',
                 'FileVersion', 'OriginalFilename', 'SpecialBuild')

    props = {'FixedFileInfo': None, 'StringFileInfo': None, 'FileVersion': None}

    try:
        # backslash as parm returns dictionary of numeric info corresponding to VS_FIXEDFILEINFO struc
        fixedInfo = win32api.GetFileVersionInfo(fname, '\\')
        props['FixedFileInfo'] = fixedInfo
        props['FileVersion'] = "%d.%d.%d.%d" % (fixedInfo['FileVersionMS'] / 65536,
                                                fixedInfo['FileVersionMS'] % 65536, fixedInfo['FileVersionLS'] / 65536,
                                                fixedInfo['FileVersionLS'] % 65536)

        # \VarFileInfo\Translation returns list of available (language, codepage)
        # pairs that can be used to retreive string info. We are using only the first pair.
        lang, codepage = win32api.GetFileVersionInfo(fname, '\\VarFileInfo\\Translation')[0]

        # any other must be of the form \StringfileInfo\%04X%04X\parm_name, middle
        # two are language/codepage pair returned from above

        strInfo = {}
        for propName in propNames:
            strInfoPath = u'\\StringFileInfo\\%04X%04X\\%s' % (lang, codepage, propName)
            ## print str_info
            strInfo[propName] = win32api.GetFileVersionInfo(fname, strInfoPath)

        props['StringFileInfo'] = strInfo
    except:
        pass

    return props


def gomonth(fecha=datetime.datetime.today(), month=1):
    fecharetorno = fecha + relativedelta(months=month)
    return fecharetorno


def goday(fecha=datetime.datetime.today(), format=None, days=0):
    fecharetorno = None
    if format:
        if format == "Ymd":
            fecha = datetime.date(year=int(fecha[:4]),
                                  month=int(fecha[4:6]),
                                  day=int(fecha[-2:]))
    if isinstance(fecha, int):
        if fecha > 0:
            fecharetorno = datetime.date.today() + datetime.timedelta(days=fecha)
        else:
            fecharetorno = datetime.date.today() - datetime.timedelta(days=abs(fecha))
    elif days != 0:
        if days > 0:
            fecharetorno = fecha + datetime.timedelta(days=days)
        else:
            fecharetorno = fecha - datetime.timedelta(days=days)
    else:
        fecharetorno = fecha
    return fecharetorno


def periodo_anterior(periodo=''):
    fecha = datetime.datetime(int(periodo[:4]), int(periodo[4:]), 1, 0, 0, 0)
    retorno = FechaMysql(gomonth(fecha, -1))[:6]

    return retorno


def periodo_siguiente(periodo=''):
    fecha = datetime.datetime(int(periodo[:4]), int(periodo[4:]), 1, 0, 0, 0)
    retorno = FechaMysql(gomonth(fecha, 1))[:6]

    return retorno


def MesIdentificador(dFecha=datetime.datetime.now().date(), formato='largo', periodo=None):
    if periodo:
        dFecha = PeriodoAFecha(periodo)
    MESES = [
        'Enero',
        'Febrero',
        'Marzo',
        'Abril',
        'Mayo',
        'Junio',
        'Julio',
        'Agosto',
        'Septiembre',
        'Octubre',
        'Noviembre',
        'Diciembre',
    ]
    retorno = ''
    if formato == 'largo':
        retorno = '{}/{}'.format(MESES[dFecha.month - 1], dFecha.year)
    elif formato == 'corto':
        retorno = '{}/{}'.format(MESES[dFecha.month - 1][:3], dFecha.year)
    return retorno


def PeriodoAFecha(periodo: str = ''):
    fecha = datetime.date(int(periodo[:4]), int(periodo[4:]), 1)

    return fecha


class WinPrinters(object):
    cDefault = ''

    def __init__(self):
        self.cDefault = win32print.GetDefaultPrinterW()

    def SetPrinter(self, cPrinter=''):
        try:
            win32print.SetDefaultPrinterW(cPrinter)
        except Exception as e:
            # printer = QPrinter()
            #
            # dialog = QPrintDialog(printer)
            # dialog.exec_()
            _ventana = Ui_FormPrinter()
            _ventana.exec_()
            if _ventana.cPrinterSelected != '':
                win32print.SetDefaultPrinterW(_ventana.cPrinterSelected)
            else:
                Ventanas.showAlert("Sistema", "No se encontro la impresora {} en la maquina y se imprimira en {}"
                                   .format(cPrinter, win32print.GetDefaultPrinterW()))
                win32print.SetDefaultPrinterW(win32print.GetDefaultPrinterW())

    def GetDefaultPrinter(self):
        return win32print.GetDefaultPrinterW()

    def SendPDF(self, cPDFName, imprime=False):
        if os.path.isfile(cPDFName):
            try:
                if LeerConf('usuario') == 'OSCAR':
                    if not imprime:
                        win32api.ShellExecute(0, "open", cPDFName, None, ".", 0)
                    else:
                        os.startfile(cPDFName, "print")
                else:
                    # win32api.ShellExecute(
                    #    0,
                    #    "print",
                    #    cPDFName,
                    #    '/d:"%s"' % win32print.GetDefaultPrinter(),
                    #    ".",
                    #    0
                    # )
                    os.startfile(cPDFName, "print")
                # win32api.ShellExecute(0, "print", cPDFName, None, ".", 0)
                time.sleep(5)
                # os.system("taskill /im AcroRd32.exe /f")
            except Exception as e:
                win32api.ShellExecute(0, "open", cPDFName, None, ".", 0)
                Ventanas.showAlert("Sistema", "Para poder imprimir es necesario "
                                              "instalar un visualizador de PDF por defecto")
        else:
            Ventanas.showAlert("Sistema", "No existe el archivo para la impresion")


"""
Para los archivo de texto que se generan deben tener ceros a la izquierda sin coma ni punto decimal
"""


def NumeroTXT(valor=0, largo=12, decimales=2):
    # return str(abs(round(valor, decimales))).replace(',','').replace('.','').zfill(largo)
    return str((round(valor * 10 ** decimales))).replace(',', '').replace('.', '').zfill(largo)


def DiaSemana(fecha=datetime.datetime.now().date()):
    locale.setlocale(locale.LC_ALL, "es")
    retorno = fecha.strftime('%A')

    return retorno


def DiasVacaciones(fecha_ingreso, anio=0):
    anios_emple = Anios(fecha_ingreso, datetime.date(anio, 12, 31)) + 1
    if anios_emple <= 5:
        ndias = 14
    elif anios_emple <= 10:
        ndias = 21
    elif anios_emple <= 20:
        ndias = 28
    else:
        ndias = 35
    return ndias


def Anios(inicio, fin):
    return relativedelta(fin, inicio).years


def dias_habiles(fecha_inicial, fecha_final):
    dias_habiles = 0

    while fecha_inicial <= fecha_final:
        dia_semana = fecha_inicial.weekday()
        if dia_semana < 5:
            dias_habiles += 1
        fecha_inicial += datetime.timedelta(days=1)

    return dias_habiles

def obtener_fechas_semana(fecha):
    # Calcula el lunes de la semana
    inicio_semana = fecha - datetime.timedelta(days=fecha.weekday())
    # Calcula el domingo de la semana
    fin_semana = inicio_semana + datetime.timedelta(days=6)
    return inicio_semana, fin_semana

def encriptar(password, key=None):
    if not key:
        # Genera una nueva clave si no se proporciona
        key = Fernet.generate_key()
    cipher_suite = Fernet(key)
    cipher_text = cipher_suite.encrypt(password)
    return cipher_text, key

def desencriptar(encrypted_data, key):
    cipher_suite = Fernet(key)
    if not isinstance(encrypted_data, bytes):
        encrypted_data = encrypted_data.encode()
    plain_text = cipher_suite.decrypt(encrypted_data)
    return plain_text.decode('utf-8')

import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date, timedelta
from jinja2 import Template
from modelos.ParametrosSistema import ParamSist
from datetime import date
from datetime import datetime
import threading


# Configuración del servidor SMTP (ejemplo con Gmail)
# Se lee BAJO DEMANDA, no al importar el modulo: leerla en el import
# implicaba consultar la base de datos (ParamSist.ObtenerParametro) en
# tiempo de import y eso crasheaba la app / el build de PyInstaller cuando
# la DB todavia no estaba disponible.
def _config_smtp():
    def _parametro(nombre, default):
        try:
            return ParamSist.ObtenerParametro(nombre, default) or default
        except Exception:
            return default

    return {
        'server': os.getenv('SMTP_HOST') or _parametro('smtp_server', ''),
        'port': os.getenv('SMTP_PORT') or _parametro('smtp_port', '465'),
        'address': os.getenv('SMTP_USER') or _parametro('email_address', ''),
        'password': os.getenv('SMTP_PASS') or _parametro('email_password', ''),
    }


def main_automatizacion():
    """
    Punto de entrada principal para ejecutar las notificaciones de cuotas y pólizas.
    """
    ultimo_informe = ParamSist.ObtenerParametro('ultimo_informe_polizas', '')
    hoy = date.today()
    if ultimo_informe:
        try:
            fecha_ultimo = datetime.strptime(ultimo_informe, "%d/%m/%Y").date()
        except Exception:
            fecha_ultimo = None
        if fecha_ultimo and fecha_ultimo >= hoy:
            print("El informe ya fue enviado hoy o en una fecha posterior.")
        else:
            # Hilo para pólizas a vencer
            ParamSist.GuardarParametro('ultimo_informe_polizas', hoy.strftime("%d/%m/%Y"))
    


def enviar_correo_asunto_html(destinatario, asunto, html_content):
    """
    Envía un correo con contenido HTML.
    """
    cfg = _config_smtp()
    msg = MIMEMultipart()
    msg['From'] = cfg['address']
    msg['To'] = destinatario
    msg['Subject'] = asunto

    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP_SSL(cfg['server'], int(cfg['port'])) as server:
            server.login(cfg['address'], cfg['password'])
            server.sendmail(cfg['address'], destinatario, msg.as_string())
        print("Correo enviado exitosamente.")
    except Exception as e:
        print(f"Error al enviar correo: {e}")

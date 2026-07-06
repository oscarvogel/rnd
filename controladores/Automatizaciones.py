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
SMTP_SERVER = os.getenv('SMTP_HOST') or ParamSist.ObtenerParametro('smtp_server', '')
SMTP_PORT = os.getenv('SMTP_PORT') or ParamSist.ObtenerParametro('smtp_port', '465')
# Credenciales de la cuenta de correo
EMAIL_ADDRESS = os.getenv('SMTP_USER') or ParamSist.ObtenerParametro('email_address', '')
EMAIL_PASSWORD = os.getenv('SMTP_PASS') or ParamSist.ObtenerParametro('email_password', '')


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
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = destinatario
    msg['Subject'] = asunto

    msg.attach(MIMEText(html_content, 'html'))

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, int(SMTP_PORT)) as server:
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, destinatario, msg.as_string())
        print("Correo enviado exitosamente.")
    except Exception as e:
        print(f"Error al enviar correo: {e}")

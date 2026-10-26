# coding=utf-8
"""Prueba del cliente de RND contra el proxy real.

Se ejecuta desde probar_cliente.sh, que levanta proxy.php y un upstream falso.
No necesita credenciales reales ni red.

Las variables de IA se limpian al arrancar porque la maquina de desarrollo
puede tener MINIMAX_API_KEY exportada. Sin ese paso la prueba no midiria el
escenario de la demo, que es justamente el que no tiene credenciales.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))

fallas = []

# La URL y el token llegan por argumento y no por variable de entorno: al
# invocar un binario de Windows desde WSL el env no siempre cruza bien.
URL_PROXY = None
TOKEN_PROXY = None
for indice, argumento in enumerate(sys.argv):
    if argumento == "--url" and indice + 1 < len(sys.argv):
        URL_PROXY = sys.argv[indice + 1]
    if argumento == "--token" and indice + 1 < len(sys.argv):
        TOKEN_PROXY = sys.argv[indice + 1]

if not URL_PROXY or not TOKEN_PROXY:
    print("FALLO falta --url y/o --token")
    sys.exit(1)


def ok(mensaje):
    print("ok    {}".format(mensaje))


def mal(mensaje):
    print("FALLO {}".format(mensaje))
    fallas.append(mensaje)


# Registrar que existia una credencial real, sin imprimirla nunca. Si la maquina
# no tiene ninguna, esto avisa: la demo nunca deberia construirse con una.
#
# Importante: la limpieza va DESPUES del import, no antes. Al importarse,
# importacion_pdf_ia llama a _cargar_entorno_ia(), que hace load_dotenv() sobre
# el .env de la raiz y vuelve a poner MINIMAX_API_KEY en el entorno. Limpiar
# antes no sirve de nada: el modulo la vuelve a cargar un instante despues.
from utiles.importacion_pdf_ia import (  # noqa: E402
    ConfiguracionPdfIAError,
    ExtraccionPdfIAError,
    _configuracion,
    llamar_minimax_texto,
)

tenia_credencial_real = False
for variable in ("MINIMAX_API_KEY", "RND_PDF_AI_API_KEY", "GROUP_SUMMARY_AI_API_KEY"):
    if os.environ.pop(variable, None):
        tenia_credencial_real = True

if tenia_credencial_real:
    print("aviso: habia una credencial IA en el entorno (viene del .env de "
          "desarrollo). Se limpio para medir el escenario de la demo, que no "
          "tiene ninguna. No se imprime su valor.")
else:
    print("aviso: no habia credenciales IA en el entorno.")

os.environ["RND_PDF_AI_URL"] = URL_PROXY
os.environ["RND_PDF_AI_TOKEN"] = TOKEN_PROXY

URL_PROXY = os.environ["RND_PDF_AI_URL"]
TOKEN_PROXY = os.environ["RND_PDF_AI_TOKEN"]

url, api_key, model, timeout = _configuracion()
print("")
print("configuracion: url={} api_key={} model={} timeout={}".format(
    url, api_key, model, timeout))

if url == URL_PROXY:
    ok("el cliente apunta al proxy")
else:
    mal("el cliente no apunta al proxy: {}".format(url))

if api_key == TOKEN_PROXY:
    ok("el cliente usa el token del proxy, no una API key real")
else:
    mal("el cliente no esta usando el token del proxy")

# Camino feliz: el cliente entra por el proxy y vuelve con texto plano.
# No se compara contra una respuesta fija porque contra el upstream falso
# devuelve "pong" y contra un proveedor real devuelve lo que quiera. Lo que
# importa es que vuelva algo usable y sin credenciales.
respuesta = ""
try:
    respuesta = llamar_minimax_texto([{"role": "user", "content": "Responde: pong"}])
    if respuesta.strip():
        ok("el cliente recibio una respuesta a traves del proxy")
    else:
        mal("respuesta vacia")
    if respuesta.strip() == "pong":
        print("      (respuesta del upstream falso)")
    else:
        print("      respuesta real: {!r}".format(respuesta.strip()[:80]))
    if "<think>" in respuesta:
        mal("llego un bloque de razonamiento sin limpiar")
    else:
        ok("no llego razonamiento sucio en la respuesta")
except Exception as exc:
    mal("la llamada fallo: {}".format(exc))

if "CLAVE-DEL-SERVIDOR" in respuesta:
    mal("la clave del servidor aparecio en la respuesta del cliente")

# Token incorrecto. Solo aplica si el servidor exige token: cuando token_demo
# esta vacio el proxy acepta a cualquiera, y eso es una decision de
# configuracion, no un fallo. Se informa igual porque conviene saberlo.
os.environ["RND_PDF_AI_TOKEN"] = "token-que-no-va"
try:
    llamar_minimax_texto([{"role": "user", "content": "Responde: pong"}])
    print("aviso: el proxy NO exige token (token_demo vacio). Cualquiera que "
          "conozca la URL puede consumir cuota, solo lo limita el tope diario.")
except ExtraccionPdfIAError as exc:
    if "401" in str(exc):
        ok("el proxy corto con 401 y el cliente lo reporto")
    else:
        mal("error inesperado del proxy: {}".format(exc))
except Exception as exc:
    mal("tipo de error inesperado: {}".format(type(exc).__name__))

# Sin credencial y con proxy configurado: el mensaje es para el usuario final
# y no le pide configurar una API key que no puede configurar.
for variable in ("RND_PDF_AI_URL", "RND_PDF_AI_TOKEN"):
    os.environ.pop(variable, None)
os.environ["RND_PDF_AI_URL"] = "https://vogelconsultoria.com.ar/rnd-ia/proxy.php"
try:
    _configuracion()
    mal("no dio error sin credencial")
except ConfiguracionPdfIAError as exc:
    mensaje = str(exc)
    if "no esta disponible" in mensaje and "MINIMAX_API_KEY" not in mensaje:
        ok("el mensaje sin credencial es para el usuario")
    else:
        mal("mensaje sin credencial inesperado: {!r}".format(mensaje[:100]))

print("")
if fallas:
    print("RESULTADO: fallaron {} comprobaciones.".format(len(fallas)))
    sys.exit(1)
print("RESULTADO: todas las comprobaciones pasaron.")
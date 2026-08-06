"""Diagnostico de conexion a la DB.

Muestra que config esta usando el sistema al momento de fallar, e intenta
la conexion manual para distinguir entre problema de credenciales locales
y problema del server.

Uso:
    python scripts/diagnose_db.py [-i CARPETA_INICIO]
"""
import os
import sys
from pathlib import Path

# Asegurar que el repo este en sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Cargar la config que usa el sistema (mismo codigo que main.py)
from pyqt5libs.pyqt5libs.utiles import LeerIni, GrabaConf

# Detectar la carpeta de inicio (mismo criterio que main.py)
inicio_arg = None
for i, arg in enumerate(sys.argv):
    if arg in ("-i", "--inicio") and i + 1 < len(sys.argv):
        inicio_arg = sys.argv[i + 1]
        break
carpeta = (inicio_arg or os.getcwd()) + "\\"

# Grabar config como hace main.py (rellena LeerIni con la persistencia)
GrabaConf(clave="iniciosistema", valor=carpeta)
GrabaConf(clave="archivoini", valor="sistema.ini")

# Leer config
host = LeerIni("host", carpeta=carpeta) or ""
user = LeerIni("user", carpeta=carpeta) or ""
basedatos = LeerIni("basedatos", carpeta=carpeta) or ""
port = int(LeerIni("port", carpeta=carpeta) or "3306")
password_env = (
    os.getenv("RND_DB_PASSWORD")
    or os.getenv("MYSQL_PASSWORD")
    or os.getenv("DB_PASSWORD")
    or ""
)
# Password persistido (lo que GrabaConf escribio antes)
password_persisted = LeerIni("password", carpeta=carpeta) or ""

print("=" * 70)
print("DIAGNOSTICO DE CONEXION A DB")
print("=" * 70)
print()
print(f"Carpeta de inicio:  {carpeta}")
print(f"sistema.ini:        {carpeta}sistema.ini")
print()
print("--- Config leida del sistema.ini ---")
print(f"  host        = {host!r}")
print(f"  user        = {user!r}")
print(f"  basedatos   = {basedatos!r}")
print(f"  port        = {port}")
print()
print("--- Password ---")
print(f"  RND_DB_PASSWORD / MYSQL_PASSWORD env var: {'SETEADA' if password_env else 'NO SETEADA'} "
      f"(length={len(password_env)})")
print(f"  Password persistido (QSettings): "
      f"{'SETEADA' if password_persisted else 'NO SETEADA'} "
      f"(length={len(password_persisted)})")
if password_env and password_persisted and password_env != password_persisted:
    print("  >>> MISMATCH: el env var y la persistencia son DISTINTAS <<<")
    print("      El sistema usa el env var (si esta seteado), no la persistencia.")
print()
print("--- Test de conexion ---")
print(f"  Intentando conectar a mysql://{user}@{host}:{port}/{basedatos} ...")

import pymysql
try:
    conn = pymysql.connect(
        host=host,
        user=user,
        password=password_env,
        database=basedatos,
        port=port,
        connect_timeout=10,
    )
    print("  [OK] Conexion exitosa")
    with conn.cursor() as cur:
        cur.execute("SELECT VERSION()")
        version = cur.fetchone()
        print(f"  MySQL version: {version[0]}")
    conn.close()
except pymysql.err.OperationalError as e:
    code, msg = e.args if len(e.args) >= 2 else (0, str(e))
    print(f"  [FAIL] codigo {code}: {msg}")
    print()
    if code == 1045:
        print("  Diagnostico: 1045 = Access denied.")
        print("  El server rechazo la auth. Posibles causas:")
        print("    1. La clave del user cambio del lado del server")
        print("    2. El user no existe / no tiene permisos desde este IP")
        print("    3. El server tiene whitelist por IP y tu IP no esta")
        print()
        print("  Para verificar la clave, conectar manual con mysql-cli:")
        print(f'    mysql -h {host} -P {port} -u {user} -p {basedatos}')
    elif code == 1044:
        print("  Diagnostico: 1044 = Access denied (el user no tiene acceso a esta DB)")
    elif code == 1130:
        print("  Diagnostico: 1130 = Host no autorizado (whitelist)")
    else:
        print(f"  Ver https://dev.mysql.com/doc/mysql-errors/{code}.html")
except Exception as e:
    print(f"  [FAIL] {type(e).__name__}: {e}")
print()
print("=" * 70)

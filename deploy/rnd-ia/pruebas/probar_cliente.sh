#!/bin/bash
# Prueba del cliente Python de RND hablando contra el proxy REAL.
#
# Cierra el circuito completo: _configuracion() -> urllib -> proxy.php ->
# upstream falso. Y comprueba que los errores del proxy llegan al cliente con
# un mensaje utilizable, que es lo que ve el operador en el panel.
set -u

ORIGEN="/mnt/c/Programacion/RND/deploy/rnd-ia"
LAB="/tmp/rnd-proxy-prueba"
PUERTO_PROXY=8898
PUERTO_UPSTREAM=8899
CLAVE="CLAVE-DEL-SERVIDOR-NO-DEBE-SALIR"
PY="/mnt/c/Programacion/RND/.venv/Scripts/python.exe"

matar() {
    pkill -f "php -S 127.0.0.1:$PUERTO_PROXY"   2>/dev/null
    pkill -f "php -S 127.0.0.1:$PUERTO_UPSTREAM" 2>/dev/null
    sleep 0.5
}

matar
rm -rf "$LAB"
mkdir -p "$LAB/public_html/rnd-ia/estado" "$LAB/upstream"
cp "$ORIGEN/proxy.php" "$LAB/public_html/rnd-ia/proxy.php"
cp "$ORIGEN/pruebas/upstream_falso.php" "$LAB/upstream/upstream_falso.php"

cat > "$LAB/rnd-ia-secreto.php" <<EOF
<?php
return array(
    'clave' => '$CLAVE',
    'url' => 'http://127.0.0.1:$PUERTO_UPSTREAM/upstream_falso.php',
    'modelo' => 'MiniMax-M3',
    'token_demo' => 'token-de-prueba',
    'limite_diario' => 100000,
);
EOF

( cd "$LAB/upstream" && exec php -S "127.0.0.1:$PUERTO_UPSTREAM" >"$LAB/upstream.log" 2>&1 ) &
sleep 1.2
( cd "$LAB/public_html/rnd-ia" && exec php -S "127.0.0.1:$PUERTO_PROXY" >"$LAB/proxy.log" 2>&1 ) &
sleep 1.5

echo "=== Cliente Python contra el proxy real ==="

# El cliente corre con el Python de Windows, que no entiende rutas /mnt/c ni
# recibe bien el entorno de WSL: la URL y el token van por argumento.
PYTHON_BIN="/mnt/c/Programacion/RND/.venv/Scripts/python.exe"
SCRIPT_WIN=$(wslpath -w "$ORIGEN/pruebas/cliente_contra_proxy.py")
RAIZ_WIN=$(wslpath -w /mnt/c/Programacion/RND)

PYTHONIOENCODING=utf-8 PYTHONPATH="$RAIZ_WIN" \
"$PYTHON_BIN" "$SCRIPT_WIN" \
    --url "http://127.0.0.1:$PUERTO_PROXY/proxy.php" \
    --token "token-de-prueba"
SALIDA=$?

matar
exit $SALIDA
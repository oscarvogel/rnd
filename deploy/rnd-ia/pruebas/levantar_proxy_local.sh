#!/bin/bash
# Levanta el proxy de IA localmente, contra la URL que le indiques.
#
#   bash levantar_proxy_local.sh            -> upstream falso, sin credenciales
#   bash levantar_proxy_local.sh real       -> contra OpenRouter, con la clave
#                                               que ya tenes en el .env del repo
#
# Sirve para probar RND con demo.ps1 sin subir nada al hosting.
# Al terminar queda corriendo: se corta con Ctrl-C o con detener_proxy_local.sh
set -u

ORIGEN="/mnt/c/Programacion/RND/deploy/rnd-ia"
LAB="/tmp/rnd-proxy-local"
PUERTO_PROXY=8898
PUERTO_UPSTREAM=8899
MODO="${1:-falso}"

pkill -f "php -S 127.0.0.1:$PUERTO_PROXY" 2>/dev/null
pkill -f "php -S 127.0.0.1:$PUERTO_UPSTREAM" 2>/dev/null
sleep 0.5

rm -rf "$LAB"
mkdir -p "$LAB/public_html/rnd-ia/estado" "$LAB/upstream"
cp "$ORIGEN/proxy.php" "$LAB/public_html/rnd-ia/proxy.php"
cp "$ORIGEN/.htaccess" "$LAB/public_html/rnd-ia/.htaccess"
cp "$ORIGEN/pruebas/upstream_falso.php" "$LAB/upstream/upstream_falso.php"

if [ "$MODO" = "real" ]; then
    URL_DESTINO="https://openrouter.ai/api/v1/chat/completions"
    MODELO="minimax/minimax-m2"
else
    URL_DESTINO="http://127.0.0.1:$PUERTO_UPSTREAM/upstream_falso.php"
    MODELO="MiniMax-M3"
fi

# La clave se lee del .env del repo y no se imprime por pantalla.
if [ "$MODO" = "real" ]; then
    if [ ! -f /mnt/c/Programacion/RND/.env ]; then
        echo "No hay .env en el repo, asi que no hay clave para usar."
        exit 1
    fi
    CLAVE=$(grep -E '^MINIMAX_API_KEY=' /mnt/c/Programacion/RND/.env | head -1 | cut -d= -f2-)
    if [ -z "$CLAVE" ]; then
        echo "El .env no tiene MINIMAX_API_KEY."
        exit 1
    fi
    echo "Se va a usar la clave del .env del repo. No se imprime."
else
    CLAVE="CLAVE-DE-PRUEBA"
fi

# El token va en el archivo que el proxy lee para autenticar al cliente local.
# Se elige uno distinto al de la demo real, asi se puede probar sin conflictos.
TOKEN_LOCAL="token-local-$(date +%s)"

cat > "$LAB/rnd-ia-secreto.php" <<EOF
<?php
return array(
    'clave' => '$CLAVE',
    'url' => '$URL_DESTINO',
    'modelo' => '$MODELO',
    'token_demo' => '$TOKEN_LOCAL',
    'limite_diario' => 100000,
);
EOF

if [ "$MODO" = "real" ]; then
    ( cd "$LAB/upstream" && exec php -S "127.0.0.1:$PUERTO_UPSTREAM" >"$LAB/upstream.log" 2>&1 ) &
    sleep 1
fi
( cd "$LAB/public_html/rnd-ia" && exec php -S "127.0.0.1:$PUERTO_PROXY" >"$LAB/proxy.log" 2>&1 ) &
sleep 1.5

echo ""
echo "Proxy local escuchando en http://127.0.0.1:$PUERTO_PROXY/proxy.php"
if [ "$MODO" = "real" ]; then
    echo "Modo: REAL contra $URL_DESTINO"
else
    echo "Modo: PRUEBA contra un upstream falso. Las respuestas seran falsas."
    echo "      Para probar la IA real: bash levantar_proxy_local.sh real"
fi
echo ""
echo "Para que RND lo use, comentá MINIMAX_API_KEY en el .env del repo y agrega:"
echo ""
echo "  RND_PDF_AI_URL=http://127.0.0.1:$PUERTO_PROXY/proxy.php"
echo "  RND_PDF_AI_TOKEN=$TOKEN_LOCAL"
echo ""
echo "Despues: .\\demo.ps1"
echo ""
echo "Comprobacion rapida:"
echo "  curl -X POST http://127.0.0.1:$PUERTO_PROXY/proxy.php -H 'Content-Type: application/json' -H 'Authorization: Bearer $TOKEN_LOCAL' -d '{\"messages\":[{\"role\":\"user\",\"content\":\"hola\"}]}'"
echo ""
echo "Para detener: bash detener_proxy_local.sh"
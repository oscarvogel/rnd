#!/bin/bash
# Prueba de punta a punta del proxy de IA.
#
# Levanta el proxy REAL contra un upstream FALSO y comprueba cada barrera:
# metodo, token, sustitucion de credencial, limite de cuerpo, limite de
# imagenes, rate limit, fuga de la clave y politica de datos de OpenRouter.
#
# No usa ninguna API key real y no gasta nada. No se sube al hosting.
set -u

ORIGEN="/mnt/c/Programacion/RND/deploy/rnd-ia"
LAB="/tmp/rnd-proxy-prueba"
PUERTO_PROXY=8898
PUERTO_UPSTREAM=8899
CLAVE="CLAVE-DEL-SERVIDOR-NO-DEBE-SALIR"

fallas=0
ok()  { echo -e "\033[32mok\033[0m    $1"; }
mal() { echo -e "\033[31mFALLO\033[0m $1"; fallas=$((fallas+1)); }

comprobar() { # comprobar <etiqueta> <esperado> <real>
    if [ "$2" = "$3" ]; then ok "$1 ($3)"; else mal "$1: se esperaba $2 y se obtuvo '${3:-vacio}'"; fi
}

matar() {
    pkill -f "php -S 127.0.0.1:$PUERTO_PROXY"   2>/dev/null
    pkill -f "php -S 127.0.0.1:$PUERTO_UPSTREAM" 2>/dev/null
    sleep 0.5
}

limpiar_estado() { rm -rf "$LAB/public_html/rnd-ia/estado"; mkdir -p "$LAB/public_html/rnd-ia/estado"; }

montar() {
    matar
    rm -rf "$LAB"
    mkdir -p "$LAB/public_html/rnd-ia/estado" "$LAB/upstream/openrouter.ai"
    cp "$ORIGEN/proxy.php"     "$LAB/public_html/rnd-ia/proxy.php"
    cp "$ORIGEN/.htaccess"     "$LAB/public_html/rnd-ia/.htaccess"
    cp "$ORIGEN/pruebas/upstream_falso.php" "$LAB/upstream/upstream_falso.php"
    cp "$ORIGEN/pruebas/upstream_falso.php" "$LAB/upstream/openrouter.ai/upstream.php"
}

arrancar_upstream() {
    ( cd "$LAB/upstream" && exec php -S "127.0.0.1:$PUERTO_UPSTREAM" >"$LAB/upstream.log" 2>&1 ) &
    sleep 1.2
}

arrancar_proxy() {
    ( cd "$LAB/public_html/rnd-ia" && exec php -S "127.0.0.1:$PUERTO_PROXY" >"$LAB/proxy.log" 2>&1 ) &
    sleep 1.2
}

escribir_secreto() { # escribir_secreto <url> <limite_diario>
    cat > "$LAB/rnd-ia-secreto.php" <<EOF
<?php
return array(
    'clave' => '$CLAVE',
    'url' => '$1',
    'modelo' => 'MiniMax-M3',
    'token_demo' => 'token-de-prueba',
    'limite_diario' => $2,
);
EOF
}

URL="http://127.0.0.1:$PUERTO_PROXY/proxy.php"
AUTH=(-H 'Content-Type: application/json' -H 'Authorization: Bearer token-de-prueba')
PEDIDO='{"messages":[{"role":"user","content":"ping"}]}'

# El cuerpo va SIEMPRE por archivo. Pasarlo como argumento rompe curl con
# "Argument list too long" a partir de unos cientos de KB, y eso hace fallar
# la prueba del limite de cuerpo por un motivo que no tiene que ver con el proxy.
cuerpo() { # cuerpo <archivo> <contenido json>
    printf '%s' "$2" > "$1"
}

codigo() { curl -s -o /dev/null -w "%{http_code}" "$@"; }

echo "=== Montaje ==="
montar
escribir_secreto "http://127.0.0.1:$PUERTO_UPSTREAM/upstream_falso.php" 100000
arrancar_upstream
arrancar_proxy
echo "proxy en $PUERTO_PROXY, upstream en $PUERTO_UPSTREAM"

echo
echo "=== 1. Barrera de metodo y de token ==="
comprobar "GET sin token -> 405" 405 "$(codigo "$URL")"
comprobar "POST sin token -> 401" 401 \
    "$(codigo -X POST "$URL" -H 'Content-Type: application/json' -d "$PEDIDO")"
comprobar "POST con token incorrecto -> 401" 401 \
    "$(codigo -X POST "$URL" -H 'Content-Type: application/json' -H 'Authorization: Bearer otro' -d "$PEDIDO")"

echo
echo "=== 2. Camino feliz y sustitucion de credencial ==="
limpiar_estado
R=$(curl -s -X POST "$URL" "${AUTH[@]}" -d "$PEDIDO")
echo "respuesta: $R"
if echo "$R" | grep -q '"content":"pong"'; then ok "devuelve la respuesta del upstream"; else mal "no devolvio la respuesta del upstream"; fi
if echo "$R" | grep -qF "Bearer $CLAVE"; then
    ok "el proxy sustituyo el token del cliente por la clave del servidor"
else
    mal "el upstream no recibio la clave del servidor"
fi
if echo "$R" | grep -q 'token-de-prueba'; then mal "el token del cliente llego al upstream"; else ok "el token del cliente no llego al upstream"; fi
if echo "$R" | grep -q '"model":"MiniMax-M3"'; then ok "el modelo sale del secreto"; else mal "el modelo no se aplico"; fi

echo
echo "=== 3. Vision (una imagen) ==="
limpiar_estado
cuerpo /tmp/rnd-vision.json '{"messages":[{"role":"user","content":[{"type":"text","text":"lee"},{"type":"image_url","image_url":{"url":"data:image/png;base64,iVBORw0KGgo="}}]}]}'
V=$(curl -s -X POST "$URL" "${AUTH[@]}" --data-binary @/tmp/rnd-vision.json)
if echo "$V" | grep -q '"imagen":true'; then ok "una imagen pasa y llega al upstream"; else mal "la imagen no llego"; fi

echo
echo "=== 4. Limite de imagenes (21 > 20) ==="
limpiar_estado
python3 -c "
import json
c=[{'type':'text','text':'x'}]+[{'type':'image_url','image_url':{'url':'data:image/png;base64,iVBORw0KGgo='}} for _ in range(21)]
open('/tmp/rnd-imgs.json','w').write(json.dumps({'messages':[{'role':'user','content':c}]}))
"
comprobar "21 imagenes -> 413" 413 "$(codigo -X POST "$URL" "${AUTH[@]}" --data-binary @/tmp/rnd-imgs.json)"

echo
echo "=== 5. Limite de cuerpo (13 MB > 12 MB) ==="
limpiar_estado
python3 -c "
import json
open('/tmp/rnd-grande.json','w').write(json.dumps({'messages':[{'role':'user','content':'x'*(13*1024*1024)}]}))
"
TAM=$(stat -c %s /tmp/rnd-grande.json)
echo "cuerpo de $TAM bytes"
comprobar "13 MB -> 413" 413 "$(codigo -X POST "$URL" "${AUTH[@]}" --data-binary @/tmp/rnd-grande.json)"

echo
echo "=== 6. JSON invalido ==="
limpiar_estado
comprobar "cuerpo no JSON -> 400" 400 "$(codigo -X POST "$URL" "${AUTH[@]}" -d 'esto no es json')"

echo
echo "=== 7. Rate limit por IP (31 en el mismo minuto) ==="
limpiar_estado
cuerpo /tmp/rnd-chico.json "$PEDIDO"
UNDIMO=""
TREINTAUNO=""
for i in $(seq 1 30); do
    UNDIMO=$(codigo -X POST "$URL" "${AUTH[@]}" --data-binary @/tmp/rnd-chico.json)
done
comprobar "request 30 -> 200" 200 "$UNDIMO"
TREINTAUNO=$(codigo -X POST "$URL" "${AUTH[@]}" --data-binary @/tmp/rnd-chico.json)
comprobar "request 31 -> 429" 429 "$TREINTAUNO"

echo
echo "=== 8. La clave del servidor no aparece en ningun error ==="
limpiar_estado
TODOS="$(
    curl -s -X POST "$URL" "${AUTH[@]}" -d 'no json'
    curl -s -X POST "$URL" "${AUTH[@]}" --data-binary @/tmp/rnd-imgs.json
    curl -s "$URL"
)"
pkill -f "php -S 127.0.0.1:$PUERTO_UPSTREAM" 2>/dev/null
sleep 0.5
TODOS="$TODOS $(curl -s -X POST "$URL" "${AUTH[@]}" -d "$PEDIDO")"
if echo "$TODOS" | grep -qF "$CLAVE"; then
    mal "la clave del servidor aparece en una respuesta de error"
else
    ok "ningun mensaje de error menciona la clave del servidor"
fi
if grep -qF "$CLAVE" "$LAB/proxy.log"; then
    mal "la clave del servidor quedo en el log"
else
    ok "el log no registra la clave"
fi

echo
echo "=== 9. Politica de datos con OpenRouter ==="
arrancar_upstream
escribir_secreto "http://127.0.0.1:$PUERTO_UPSTREAM/openrouter.ai/upstream.php" 100000
limpiar_estado
pkill -f "php -S 127.0.0.1:$PUERTO_PROXY" 2>/dev/null
sleep 0.5
arrancar_proxy
OR=$(curl -s -X POST "$URL" "${AUTH[@]}" -d "$PEDIDO")
echo "respuesta: $OR"
if echo "$OR" | grep -q '"data_collection":"deny"'; then ok "fuerza data_collection deny"; else mal "no fuerza data_collection deny"; fi
if echo "$OR" | grep -q '"zdr":true'; then ok "fuerza zdr true"; else mal "no fuerza zdr true"; fi
if echo "$OR" | grep -qF "Bearer $CLAVE"; then ok "sigue sustituyendo por la clave del servidor"; else mal "no llego la clave del servidor"; fi

echo
echo "=== 10. Orden de chequeos: el metodo se evalua antes que la configuracion ==="
# Durante el despliegue real un 503 de "falta la clave" tapaba el 405 y hacia
# imposible saber si se estaba llamando mal o si el servidor estaba roto.
mv "$LAB/rnd-ia-secreto.php" "$LAB/secreto.bak"
# PHP cachea los archivos. Sin reiniciar, el proxy sigue viendo la version
# anterior del secreto y estas pruebas miden el archivo viejo, no el estado
# actual. En el hosting esto tiene el mismo efecto sobre una rotacion de clave.
pkill -f "php -S 127.0.0.1:$PUERTO_PROXY" 2>/dev/null
sleep 0.4
arrancar_proxy
SIN=$(codigo "$URL")
POST_SIN=$(curl -s -X POST "$URL" -H 'Content-Type: application/json' -d "$PEDIDO")
comprobar "GET sin configuracion -> 405 (no 503)" 405 "$SIN"
if echo "$POST_SIN" | grep -q 'falta el archivo'; then
    ok "el 503 dice que archivo falta, sin decir donde esta"
else
    mal "el 503 no identifica el problema: $POST_SIN"
fi
if echo "$POST_SIN" | grep -q '/home/'; then
    mal "el 503 filtra una ruta del servidor"
else
    ok "el 503 no filtra rutas del servidor"
fi
mv "$LAB/secreto.bak" "$LAB/rnd-ia-secreto.php"

echo
echo "=== 11. Un secreto mal formado NO puede filtrar la clave ==="
# include() emite el texto que no sea PHP. Si alguien guarda la clave sola,
# el proxy terminaba sirviendo la credencial en su propia respuesta HTTP.
mv "$LAB/rnd-ia-secreto.php" "$LAB/secreto.bak"
printf 'CLAVE-TEXTUAL-NO-DEBE-SALIR\n' > "$LAB/rnd-ia-secreto.php"
pkill -f "php -S 127.0.0.1:$PUERTO_PROXY" 2>/dev/null
sleep 0.4
arrancar_proxy
LIMPIA=$(curl -s -X POST "$URL" -H 'Content-Type: application/json' -d "$PEDIDO")
if echo "$LIMPIA" | grep -qF 'CLAVE-TEXTUAL-NO-DEBE-SALIR'; then
    mal "la clave mal formada se imprimio en la respuesta del proxy"
else
    ok "una clave mal formada no se imprime en la respuesta"
fi
if echo "$LIMPIA" | grep -q 'no devuelve un array'; then
    ok "el 503 explica que el archivo esta mal formado"
else
    mal "el 503 no explica el problema: $LIMPIA"
fi
rm -f "$LAB/rnd-ia-secreto.php"
mv "$LAB/secreto.bak" "$LAB/rnd-ia-secreto.php"

echo
echo "=== 12. Rotar la clave: cambia el archivo y hay que reiniciar ==="
# Reproduce la rotacion real. Si el servidor sigue usando la clave anterior,
# se sigue gastando con la vieja creyendo que se rotó.
pkill -f "php -S 127.0.0.1:$PUERTO_UPSTREAM" 2>/dev/null
pkill -f "php -S 127.0.0.1:$PUERTO_PROXY" 2>/dev/null
sleep 0.5
arrancar_upstream
arrancar_proxy
limpiar_estado
escribir_secreto "http://127.0.0.1:$PUERTO_UPSTREAM/upstream_falso.php" 100000
sed -i "s/'token_demo'   => 'token-de-prueba'/'token_demo'   => 'token-nuevo-tras-rotar'/" "$LAB/rnd-ia-secreto.php"
SIN_CACHE=$(curl -s -X POST "$URL" -H 'Content-Type: application/json' -H 'Authorization: Bearer token-de-prueba' -d "$PEDIDO")
if echo "$SIN_CACHE" | grep -q 'no esta habilitada'; then
    mal "tras editar el secreto, el servidor sigue con la clave anterior (cache de PHP)"
else
    ok "el cambio se reflejo sin reiniciar en este servidor"
fi
echo "  (en un hosting con validate_timestamps=0 esto NUNCA se refleja;"
echo "   hay que purgar la cache, por ejemplo con _diag.php)"

rm -f /tmp/rnd-vision.json /tmp/rnd-imgs.json /tmp/rnd-grande.json /tmp/rnd-chico.json
matar

echo
if [ "$fallas" -eq 0 ]; then
    echo -e "\033[32mRESULTADO: todas las comprobaciones pasaron.\033[0m"
else
    echo -e "\033[31mRESULTADO: fallaron $fallas comprobaciones.\033[0m"
    exit 1
fi
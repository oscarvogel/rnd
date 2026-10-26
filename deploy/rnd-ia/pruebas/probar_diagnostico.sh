#!/bin/bash
# Comprueba que _diag.php sirve para diagnosticar de verdad, en los tres
# casos que puede encontrar durante el despliegue.
set -u

ORIGEN="/mnt/c/Programacion/RND/deploy/rnd-ia"
LAB="/tmp/rnd-diag"
PUERTO=8897

pkill -f "php -S 127.0.0.1:$PUERTO" 2>/dev/null
sleep 0.4
rm -rf "$LAB"; mkdir -p "$LAB/public_html/rnd-ia"
cp "$ORIGEN/_diag.php" "$LAB/public_html/rnd-ia/_diag.php"

arrancar() {
    ( cd "$LAB/public_html/rnd-ia" && exec php -S "127.0.0.1:$PUERTO" >"$LAB/srv.log" 2>&1 ) &
    sleep 1.2
}
ver() { curl -s "http://127.0.0.1:$PUERTO/_diag.php"; }

echo "############ CASO A: el archivo NO existe ############"
rm -f "$LAB/rnd-ia-secreto.php"
arrancar
ver | sed -n '5,20p'
pkill -f "php -S 127.0.0.1:$PUERTO" 2>/dev/null; sleep 0.4

echo
echo "############ CASO B: existe pero solo tiene la clave pegada ############"
printf 'sk-clave-pegada-sin-el-php-de-alrededor\n' > "$LAB/rnd-ia-secreto.php"
arrancar
ver | sed -n '5,26p'
pkill -f "php -S 127.0.0.1:$PUERTO" 2>/dev/null; sleep 0.4

echo
echo "############ CASO C: el archivo esta bien ############"
cat > "$LAB/rnd-ia-secreto.php" <<'EOF'
<?php
return array(
    'clave' => 'sk-ejemplo-de-prueba-1234567890',
    'url' => 'https://openrouter.ai/api/v1/chat/completions',
    'modelo' => 'minimax/minimax-m2',
    'token_demo' => 'demo',
    'limite_diario' => 2000,
);
EOF
arrancar
ver | sed -n '5,30p'
pkill -f "php -S 127.0.0.1:$PUERTO" 2>/dev/null
rm -rf "$LAB"
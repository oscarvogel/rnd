<?php
/**
 * Secreto de PRUEBA. Nunca usar en el hosting real.
 *
 * Apunta a un upstream falso que corre en localhost, para poder verificar
 * el proxy de punta a punta sin una API key real y sin gastar.
 */

return array(
    'clave'        => 'CLAVE-DEL-SERVIDOR-NO-DEBE-SALIR',
    'url'          => 'http://127.0.0.1:8899/upstream_falso.php',
    'modelo'       => 'MiniMax-M3',
    'token_demo'   => 'token-de-prueba',
    'limite_diario' => 100000,
);
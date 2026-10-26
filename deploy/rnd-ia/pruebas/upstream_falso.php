<?php
/**
 * Upstream falso para probar el proxy sin gastar y sin usar una clave real.
 *
 * Responde con el formato de chat/completions que espera RND, y ademas
 * devuelve en "echo_auth" el encabezado Authorization que recibio. Sirve
 * para demostrar que el proxy reemplaza el token del cliente por la clave
 * del servidor, y que esa clave no vuelve al cliente.
 *
 * No es parte del despliegue: nunca se sube al hosting.
 */

$cuerpo = file_get_contents('php://input');
$autorizado = isset($_SERVER['HTTP_AUTHORIZATION'])
    ? $_SERVER['HTTP_AUTHORIZATION']
    : '';

$pedido = json_decode($cuerpo, true);

header('Content-Type: application/json; charset=utf-8');

if (isset($pedido['messages'][0]['content']) && is_array($pedido['messages'][0]['content'])) {
    $tieneImagen = false;
    foreach ($pedido['messages'][0]['content'] as $parte) {
        if (is_array($parte) && isset($parte['type']) && $parte['type'] === 'image_url') {
            $tieneImagen = true;
        }
    }
    if ($tieneImagen) {
        echo json_encode(array(
            'echo_auth' => $autorizado,
            'model'     => isset($pedido['model']) ? $pedido['model'] : '',
            'provider'  => isset($pedido['provider']) ? $pedido['provider'] : null,
            'imagen'    => true,
            'choices'   => array(array(
                'message' => array('content' => '{"documento":{"tipo":"FACTURA"},"items":[]}'),
            )),
        ));
        exit;
    }
}

echo json_encode(array(
    'echo_auth' => $autorizado,
    'model'     => isset($pedido['model']) ? $pedido['model'] : '',
    'provider'  => isset($pedido['provider']) ? $pedido['provider'] : null,
    'choices'   => array(array(
        'message' => array('content' => 'pong'),
    )),
));
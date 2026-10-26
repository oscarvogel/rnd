<?php
/**
 * Proxy de IA para RND DEMO - Vogel Consultoria.
 *
 * Razon de existir: el instalador de RND DEMO es publico. Si la clave de
 * MiniMax viaja dentro del .env que se instala, cualquiera que descargue el
 * instalador se lleva la credencial. Este proxy deja la clave solo en el
 * servidor y el cliente habla contra esta URL sin ningun secreto real.
 *
 * Contrato: endpoint OpenAI-compatible POST /v1/chat/completions.
 * El cliente de RND (utiles/importacion_pdf_ia.py) ya speaks ese formato,
 * asi que el proxy es transparente: si someday se cae, se puede apuntar
 * RND_PDF_AI_URL directo a MiniMax con una clave local y sigue funcionando.
 *
 * Requisitos: PHP 7.4+ con cURL. Sin base de datos. Sin dependencias.
 *
 * SEGURIDAD - lo que este archivo NO hace a proposito:
 *  - No valida ni exige identidad del usuario. Es un endpoint publico por
 *    diseno; lo frena el rate limit, no un secreto.
 *  - No registra contenido de prompts ni respuestas. Solo metadatos.
 *  - No acepta CORS. Un navegador de otro sitio no puede llamarlo.
 */

declare(strict_types=1);

// ---------------------------------------------------------------------------
// Configuracion. Todos los valores salen del archivo secreto del servidor.
// ---------------------------------------------------------------------------

const RUTA_ESTADO       = __DIR__ . '/estado';

const LIMITE_POR_MINUTO = 30;    // por IP. Una importacion de 20 paginas entra.
const LIMITE_DIARIO      = 2000; // tope global. El freno real de dinero.
const MAX_CUERPO_BYTES  = 12582912; // 12 MB. Las imagenes base64 crecen rapido.
const MAX_IMAGENES       = 20;    // por request. Una pagina = una imagen.
const NOMBRE_MODELO      = 'MiniMax-M3';

// ---------------------------------------------------------------------------

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

/**
 * Busca el archivo de credenciales FUERA del docroot.
 *
 * La carpeta donde vive el proxy es publica_html/rnd-ia/, o sea que la raiz
 * del home del usuario esta DOS niveles arriba, no uno. La version anterior
 * usaba un solo ../ y terminaba en publica_html/, que todavia sigue bajo el
 * docroot: por ahi no encontraba nada y el despliegue fallaba con un 503.
 *
 * En las pruebas locales el docroot es public/ y el secreto esta a un nivel,
 * asi que se prueban las dos profundidades y se usa la primera que exista.
 * El orden importa: primero la de produccion.
 */
function rnd_ruta_secreto(): string
{
    $candidatas = array(
        __DIR__ . '/../../rnd-ia-secreto.php',
        __DIR__ . '/../rnd-ia-secreto.php',
    );

    foreach ($candidatas as $ruta) {
        if (is_file($ruta)) {
            return $ruta;
        }
    }

    // No existe en ninguna: se devuelve la de produccion para el mensaje.
    return $candidatas[0];
}

/**
 * Devuelve la configuracion y, en 'problema', que falta si no se pudo leer.
 *
 * El campo 'problema' existe porque un 503 generico deja al operador sin
 * forma de saber que paso: si el archivo no esta, si no se puede leer, o si
 * le falta la clave. Con el detalle se arregla en un paso; sin el, hay que
 * adivinar. Solo dice que falta y como se llama el archivo, nunca su
 * contenido ni donde esta.
 */
function rnd_config(): array
{
    $config = [
        'clave'        => '',
        'url'          => 'https://api.minimax.io/v1/chat/completions',
        'modelo'       => NOMBRE_MODELO,
        'token_demo'   => '',
        'limite_diario' => LIMITE_DIARIO,
        'problema'     => '',
    ];

    // El secreto va FUERA del docroot. No existe un fallback dentro de
    // public_html a proposito: si se puede guardar la clave junto al codigo,
    // alguien la va a servir por HTTP.
    $secreto = rnd_ruta_secreto();

    if (!is_file($secreto)) {
        $config['problema'] = 'falta el archivo ' . basename($secreto);

        // La causa mas silenciosa de "falta el archivo" cuando el archivo SI
        // esta pero no se puede leer: un .htaccess padre con open_basedir.
        // Apache no puede bloquear un include de disco, pero PHP si, y el
        // sintoma es identico a que el archivo no exista.
        $restringido = ini_get('open_basedir');
        if (is_string($restringido) && trim($restringido) !== '') {
            $config['problema'] .= '. Este PHP tiene open_basedir configurado: '
                . 'tiene que incluir el directorio donde esta el archivo de credenciales';
        }
    } else {
        // include() emite a la salida TODO lo que encuentra en el archivo que
        // no sea codigo PHP. Con el archivo bien formado eso es nada, pero si
        // alguien guarda la clave sola, sin el <?php return array(...), el
        // texto crudo se imprimiria en la respuesta HTTP del proxy: la
        // credencial terminaria sirvida por el propio proxy que deberia
        // protegerla. Se captura la salida y se descarta siempre.
        ob_start();
        $incluido = include $secreto;
        ob_end_clean();

        if (!is_array($incluido)) {
            $config['problema'] = 'el archivo existe pero no devuelve un array PHP valido. '
                . 'Tiene que empezar con <?php y devolver return array(...), '
                . 'no la clave sola';
        } elseif (!isset($incluido['clave']) || trim((string) $incluido['clave']) === '') {
            $config['problema'] = 'al archivo le falta la entrada clave o esta vacia';
        } else {
            foreach ($incluido as $clave => $valor) {
                if (array_key_exists($clave, $config) && is_string($valor)) {
                    $config[$clave] = $valor;
                }
            }
        }
    }

    if ($config['problema'] === '' && empty($config['clave'])) {
        $config['problema'] = 'la clave quedo vacia';
    }

    $config['limite_diario'] = max(1, (int) $config['limite_diario']);
    return $config;
}

/** Responde con JSON y termina. Nunca incluye la clave en el cuerpo. */
function rnd_responder(int $codigo, array $cuerpo): void
{
    http_response_code($codigo);
    echo json_encode($cuerpo, JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Identidad de la IP sin confiar en cabeceras manipulables.
 * X-Forwarded-For lo pone cualquiera, asi que no se usa.
 */
function rnd_ip(): string
{
    $ip = isset($_SERVER['REMOTE_ADDR']) ? (string) $_SERVER['REMOTE_ADDR'] : '';
    return $ip === '' ? 'desconocida' : $ip;
}

/**
 * Rate limit por IP con ventana fija y tope global diario.
 * Estado en archivos con flock: no requiere base ni permisos raros.
 */
function rnd_limitar(string $ip, int $limiteDiario): void
{
    if (!is_dir(RUTA_ESTADO) && !@mkdir(RUTA_ESTADO, 0700, true) && !is_dir(RUTA_ESTADO)) {
        // Sin estado no se puede limitar. Se corta antes que servir sin freno.
        rnd_responder(503, array(
            'error' => array(
                'message' => 'El servicio de IA esta temporalmente saturado. Reintente en unos segundos.',
            ),
        ));
    }

    $minuto = (int) floor(time() / 60);
    $dia    = (int) floor(time() / 86400);
    $sello  = substr(hash('sha256', $ip . '|rnd-ia'), 0, 32);

    $ipArchivo     = RUTA_ESTADO . '/ip-' . $sello . '-' . $minuto . '.txt';
    $globalArchivo = RUTA_ESTADO . '/global-' . $dia . '.txt';

    $manejador = @fopen($ipArchivo, 'c+');
    if ($manejador === false) {
        rnd_responder(503, array('error' => array('message' => 'Servicio de IA saturado.')));
    }
    flock($manejador, LOCK_EX);
    $contador = (int) stream_get_contents($manejador);
    $contador++;
    ftruncate($manejador, 0);
    rewind($manejador);
    fwrite($manejador, (string) $contador);
    fflush($manejador);
    flock($manejador, LOCK_UN);
    fclose($manejador);

    if ($contador > LIMITE_POR_MINUTO) {
        rnd_responder(429, array(
            'error' => array(
                'message' => 'Demasiadas consultas seguidas. Espere un momento e intentelo de nuevo.',
            ),
        ));
    }

    // Tope global: frena el abuso agregado desde muchas IPs, que es lo que
    // un atacante分布式eo haria para saltarse el limite por IP.
    $global = @fopen($globalArchivo, 'c+');
    if ($global !== false) {
        flock($global, LOCK_EX);
        $total = (int) stream_get_contents($global);
        $total++;
        ftruncate($global, 0);
        rewind($global);
        fwrite($global, (string) $total);
        fflush($global);
        flock($global, LOCK_UN);
        fclose($global);

        if ($total > $limiteDiario) {
            rnd_responder(429, array(
                'error' => array(
                    'message' => 'La demostracion alcanzo su limite de uso por hoy. Contacte a Vogel Consultoria.',
                ),
            ));
        }
    }
}

/** Cuenta las imagenes de un payload de chat/completions. */
function rnd_contar_imagenes(array $payload): int
{
    $mensajes = isset($payload['messages']) && is_array($payload['messages'])
        ? $payload['messages']
        : array();
    $total = 0;
    foreach ($mensajes as $mensaje) {
        if (!is_array($mensaje) || !isset($mensaje['content']) || !is_array($mensaje['content'])) {
            continue;
        }
        foreach ($mensaje['content'] as $parte) {
            if (is_array($parte) && isset($parte['type']) && $parte['type'] === 'image_url') {
                $total++;
            }
        }
    }
    return $total;
}

// ---------------------------------------------------------------------------
// Peticion
// ---------------------------------------------------------------------------

// El metodo se comprueba PRIMERO. Al reves, un 503 de configuracion tapaba
// el 405 y hacia imposible distinguir "estoy llamando mal" de "el servidor
// esta roto" durante el despliegue.
if (($_SERVER['REQUEST_METHOD'] ?? 'GET') !== 'POST') {
    rnd_responder(405, array('error' => array('message' => 'Solo se admite POST.')));
}

$config = rnd_config();

if (!empty($config['problema'])) {
    rnd_responder(503, array(
        'error' => array(
            'message' => 'El servicio de IA no esta configurado en el servidor. '
                . $config['problema'] . '. Debe quedar un nivel arriba de la '
                . 'carpeta publica, junto a public_html y no dentro de ella, '
                . 'y el usuario del servidor debe poder leerlo.',
        ),
    ));
}

$largo = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);
if ($largo > MAX_CUERPO_BYTES) {
    rnd_responder(413, array('error' => array('message' => 'El documento enviado es demasiado grande.')));
}

$cuerpo = file_get_contents('php://input');
if ($cuerpo === false || $cuerpo === '') {
    rnd_responder(400, array('error' => array('message' => 'Peticion vacia.')));
}
if (strlen($cuerpo) > MAX_CUERPO_BYTES) {
    rnd_responder(413, array('error' => array('message' => 'El documento enviado es demasiado grande.')));
}

$payload = json_decode($cuerpo, true);
if (!is_array($payload)) {
    rnd_responder(400, array('error' => array('message' => 'Peticion con formato invalido.')));
}

if (rnd_contar_imagenes($payload) > MAX_IMAGENES) {
    rnd_responder(413, array('error' => array('message' => 'Demasiadas paginas en una sola consulta.')));
}

// El token de la demo es un interruptor, no un secreto: viaja dentro del
// ejecutable, asi que cualquiera que lo descargue puede leerlo. Sirve para
// poder apagar la demostracion cambiando un valor aca, en el servidor.
$autorizado = '';
if (isset($_SERVER['HTTP_AUTHORIZATION'])) {
    $autorizado = trim((string) $_SERVER['HTTP_AUTHORIZATION']);
}
$presentado = '';
if (stripos($autorizado, 'Bearer ') === 0) {
    $presentado = trim(substr($autorizado, 7));
}

if ($config['token_demo'] !== '') {
    if ($presentado === '' || !hash_equals($config['token_demo'], $presentado)) {
        rnd_responder(401, array(
            'error' => array('message' => 'La demostracion no esta habilitada en este momento.'),
        ));
    }
}

rnd_limitar(rnd_ip(), $config['limite_diario']);

// A partir de aca se llama al proveedor real. El token del cliente se
// descarta y se reemplaza por la credencial que nunca sale del servidor.
$payload['model'] = $config['modelo'];

// El destino sale del secreto, asi que MiniMax y OpenRouter conviven sin
// tocar codigo. Cuando es OpenRouter se fuerzan dos cosas:
//
//  - cabeceras de atribucion que la API pide para identificar la app;
//  - data_collection deny + zdr true, para que solo ruta a providers que NO
//    retienen ni entrenan con lo enviado. Importa porque lo que viaja son
//    facturas escaneadas con CUIT y domicilio: datos de terceros, no de la
//    demo. Con esto la politica se aplica siempre y no depende de que alguien
//    la haya activado en el panel de OpenRouter.
$cabeceras = [
    'Authorization: Bearer ' . $config['clave'],
    'Content-Type: application/json',
];

if (strpos($config['url'], 'openrouter.ai') !== false) {
    $cabeceras[] = 'HTTP-Referer: https://vogelconsultoria.com.ar';
    $cabeceras[] = 'X-Title: RND Logistica DEMO';

    $proveedor = isset($payload['provider']) && is_array($payload['provider'])
        ? $payload['provider']
        : array();
    $proveedor['data_collection'] = 'deny';
    $proveedor['zdr'] = true;
    $payload['provider'] = $proveedor;
}

$curl = curl_init($config['url']);
curl_setopt_array($curl, array(
    CURLOPT_POST           => true,
    CURLOPT_POSTFIELDS     => json_encode($payload),
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT        => 180,
    CURLOPT_CONNECTTIMEOUT => 15,
    CURLOPT_HTTPHEADER     => $cabeceras,
));

$respuesta = curl_exec($curl);
$codigo    = (int) curl_getinfo($curl, CURLINFO_HTTP_CODE);
$fallo     = curl_error($curl);
curl_close($curl);

// Log minimo: cuenta y status. Nunca el prompt ni la respuesta.
@file_put_contents(
    RUTA_ESTADO . '/accesos.log',
    date('c') . ' code=' . $codigo . ' ip=' . hash('sha256', rnd_ip()) . "\n",
    FILE_APPEND | LOCK_EX
);

// Limpieza de archivos de estado viejos: sin esto la carpeta crece sin fin.
if (random_int(1, 50) === 1) {
    foreach (glob(RUTA_ESTADO . '/*.txt') ?: array() as $viejo) {
        if (is_file($viejo) && filemtime($viejo) < time() - 7200) {
            @unlink($viejo);
        }
    }
}

if ($respuesta === false || $respuesta === '') {
    rnd_responder(502, array(
        'error' => array(
            'message' => 'No se pudo contactar al servicio de IA. Intente nuevamente en unos segundos.',
        ),
    ));
}

// Se devuelve la respuesta del proveedor tal cual, para que el cliente la
// procese sin cambios. Si el proveedor reporta un error, el mensaje viaja.
http_response_code($codigo === 0 ? 502 : $codigo);
echo $respuesta;
# Proxy de IA para RND DEMO

## Por que existe

El instalador de RND DEMO es publico y se descarga desde un link que se
comparte con clientes. Como el build escribia un `.env` con
`MINIMAX_API_KEY` dentro de `dist\RND Demo\`, la clave quedaba instalada en
texto plano en `%LOCALAPPDATA%\Programs\RND DEMO\.env`. No hacia falta
descompilar nada: se instalaba y se abria el archivo.

Este proxy deja la credencial **unicamente en el servidor**. El ejecutable
habla contra esta URL y no lleva ningun secreto real.

```
antes:   RND Demo.exe  --( MINIMAX_API_KEY en su .env )-->  api.minimax.io
ahora:   RND Demo.exe  --( token interruptor, sin valor)--->  /rnd-ia/  --( clave real )-->  proveedor
```

## Requisitos

- Hosting con PHP 7.4+ y extension cURL. En vogelconsultoria.com.ar (Ferozo,
  Apache) ya esta.
- Sin base de datos. Sin dependencias. Sin composer.

## Instalacion en Ferozo

Estructura final en el hosting:

```
/home/TUUSUARIO/
├── rnd-ia-secreto.php          <- CREADO POR VOS, con la clave. NO se sirve por web.
└── public_html/
    └── rnd-ia/
        ├── proxy.php           <- subido desde el repo
        ├── .htaccess           <- subido desde el repo
        └── estado/             <- se crea sola, permiso de escritura
```

El archivo de credenciales tiene que ser un archivo PHP completo:

```php
<?php
return array(
    'clave'        => '...',
    'url'          => '...',
    'modelo'       => '...',
    'token_demo'   => '...',
    'limite_diario' => 2000,
);
```

Guardar solo el valor de la clave, sin el `<?php` y el `return array(...)`,
no funciona: el `include` no devuelve nada utilizable y el proxy responde 503.

Pasos desde cPanel (**File Manager**):

1. Crear la carpeta `rnd-ia` dentro de `public_html`.
2. Subir `proxy.php` y `.htaccess` ahi.
3. Crear `rnd-ia-secreto.php` **un nivel arriba**, al lado de `public_html`.
   Si no se ve esa carpeta en File Manager, crearla desde la pestana
   **Archivos** apuntando al home, o por FTP con un cliente.
4. Editarlo y completar `clave`, `url` y `modelo`. Plantilla en
   `rnd-ia-secreto.php.ejemplo`.
5. Verificar permisos: `proxy.php` y el secreto en `644`, `estado/` en `755`.

Desde FTP la ruta es la misma: un nivel arriba de `public_html`.

## Comprobar que quedo bien

```bash
# Debe responder 401 si configuraste token_demo, o funcionar si lo dejaste vacio.
curl -X POST https://vogelconsultoria.com.ar/rnd-ia/proxy.php \
  -H "Content-Type: application/json" \
  -d '{"model":"MiniMax-M3","messages":[{"role":"user","content":"ping"}]}'
```

Respuesta esperada del proveedor, o un error en texto plano si falta algo.

Prueba de que **no** se sirve el secreto (tiene que dar 403):

```
https://vogelconsultoria.com.ar/rnd-ia/estado/accesos.log
https://vogelconsultoria.com.ar/rnd-ia/rnd-ia-secreto.php
```

## Rotar la clave

Editar `rnd-ia-secreto.php`, cambiar `clave`, guardar.

**Verificar que el cambio se aplico.** PHP cachea los archivos, y si el
hosting tiene `opcache.validate_timestamps` desactivado, editar el archivo no
cambia nada: el proxy sigue gastando con la clave vieja creyendo que se roto.
Para purgar la cache, visitar `_diag.php` (hace `opcache_reset()` al
ejecutarse) o usar la opcion de PHP del panel de control.

La forma de comprobar que la rotacion surtio efecto es cambiar tambien
`token_demo` y probar un POST con el token nuevo:

```bash
curl -X POST https://vogelconsultoria.com.ar/rnd-ia/proxy.php \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN_NUEVO" \
  -d '{"messages":[{"role":"user","content":"hola"}]}'
```

Si responde `401 La demostracion no esta habilitada`, el archivo se esta
leyendo de verdad y el token nuevo ya es el que vale. Si responde con una
respuesta del proveedor, la rotacion esta aplicada. Si responde `503` con un
problema de configuracion, el archivo se rompio al editarlo.

## Apagar la demo

Poner un valor cualquiera en `token_demo`. El ejecutable deja de poder
consultar y el panel muestra "El asistente no esta disponible en este
momento". Para volver, volver el valor anterior.

## Limites

- 30 consultas por minuto y por IP.
- `limite_diario` consultas por dia entre todas las maquinas.
- 12 MB por consulta y 20 imagenes por consulta.

Para subir o bajar, editar las constantes al principio de `proxy.php`.
El freno real de dinero es el **limite de gasto de la key del proveedor**,
no estos numeros.

## Datos de terceros

Lo que viaja por aca son facturas escaneadas de clientes finales de Vogel:
CUIT, domicilio, localidad. Son datos personales de terceros, no de la demo.

Con OpenRouter, el proxy fuerza `provider.data_collection: "deny"` y
`provider.zdr: true` para que solo se usen providers que no retienen ni
entrenan con lo enviado. Esa politica se aplica siempre, sin depender de
que alguien la haya activado en el panel de OpenRouter.

## Que protege y que no

**Protege:** ninguna credencial real sale del servidor. El ejecutable y su
`.env` no contienen nada que valga dinero.

**No protege:** el endpoint es publico. Cualquiera que conozca la URL puede
llamar al proxy y consumir cuota. Eso lo frenan los limites de arriba y el
tope de gasto de la key, no un secreto. Por eso `token_demo` es un
interruptor y no una barrera.

## Probarlo localmente, sin subir nada

Requiere PHP (en WSL alcanza) y no usa ninguna API key real ni sale a internet.

```bash
# Levanta el proxy real contra un upstream falso y comprueba 20 cosas:
# metodo, token, sustitucion de credencial, limites, rate limit y
# que la clave no aparezca en ningun error ni en el log.
wsl bash /mnt/c/Programacion/RND/deploy/rnd-ia/pruebas/probar_proxy.sh

# Cierra el circuito completo: el cliente Python de RND hablando contra
# el proxy real.
wsl bash /mnt/c/Programacion/RND/deploy/rnd-ia/pruebas/probar_cliente.sh
```

El ultimo script importa `utiles/importacion_pdf_ia`, que al cargarse lee el
`.env` de desarrollo. Si ahi sigue `MINIMAX_API_KEY`, el script la limpia
despues del import y te avisa, justamente para medir el escenario real de la
demo, que no tiene ninguna credencial.

## Si responde 503 "no esta configurado en el servidor"

**Paso 0: usar el diagnostico.** Subir `_diag.php` a `public_html/rnd-ia/` y
visitar `https://vogelconsultoria.com.ar/rnd-ia/_diag.php`. En una sola
visita dice si el archivo existe, si se puede leer, con que permisos, si el
PHP tiene `open_basedir` restringido y si el archivo devuelve un array PHP
valido. **Borrarlo apenas termines**: es una herramienta temporal, no parte
del despliegue.

El mensaje nunca imprime el valor de la credencial, solo cuantos caracteres
tiene. Y si el archivo esta mal formado, captura el texto que el `include`
soltaria en vez de mostrarlo, justamente para que la pagina no termine
sirviendo la clave que vino a revisar.

Si no querés usar el diagnostico, el mensaje del 503 dice que problema hay:

1. **El archivo se subio sin renombrar.** Tiene que quedar como
   `rnd-ia-secreto.php`, no como `rnd-ia-secreto.php.ejemplo`. Ojo con esto:
   si se sube la plantilla tal cual, el archivo no existe.

2. **Quedo dentro de `public_html`.** Tiene que estar un nivel arriba, junto a
   `public_html`. Si esta adentro, el proxy no lo encuentra y ademas queda
   expuesto por HTTP: comprobarlo con
   `https://vogelconsultoria.com.ar/rnd-ia/rnd-ia-secreto.php`, que tiene que
   responder 404.

3. **Guardo la clave sola, sin el PHP.** El archivo tiene que empezar con
   `<?php` y hacer `return array(...)`. Si solo contiene el valor de la
   clave, el `include` no devuelve nada utilizable.

4. **No se puede leer.** El usuario de PHP no tiene permiso sobre el archivo.
   En cPanel: click derecho -> **Cambiar permisos** -> `644`.

5. **`open_basedir` restringido.** Si un `.htaccess` de un directorio padre
   define `php_admin_value open_basedir` apuntando solo a `public_html`, el
   archivo de un nivel arriba queda fuera y PHP no puede incluirlo. Es la
   unica forma en que un `.htaccess` rompe el include; Apache por si solo no.

Comprobaciones que el mensaje NO hace falta hacer primero:

```
GET  https://vogelconsultoria.com.ar/rnd-ia/proxy.php   -> 405  (metodo)
POST https://vogelconsultoria.com.ar/rnd-ia/proxy.php   -> 503  (configuracion)
GET  https://vogelconsultoria.com.ar/rnd-ia/            -> 403  (sin listado)
GET  https://vogelconsultoria.com.ar/rnd-ia/estado/accesos.log -> 403
GET  https://vogelconsultoria.com.ar/rnd-ia-secreto.php -> 404  (no existe)
```

Si el GET devuelve 405 y el POST 503, el proxy esta bien instalado y lo que
falta es el archivo de credenciales.

## Si el proxy se cae

El cliente sigue funcionando. Solo pierde la IA: el panel del asistente ya
muestra un mensaje amable y RND sigue operando con normalidad. Para volver a
MiniMax directo sin tocar codigo, cargar el `.env` del cliente con
`MINIMAX_API_KEY` y borrar `RND_PDF_AI_URL`.
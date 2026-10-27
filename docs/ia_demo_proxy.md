# IA de la DEMO: de clave embebida a proxy en el servidor

## Que pasaba

El instalador de RND DEMO se publica en una release publica de GitHub y se
descarga desde un link que se comparte con clientes. El build escribia un
`.env` con `MINIMAX_API_KEY` en `dist\RND Demo\`, y `installer\RND_Demo.iss`
empaqueta todo el arbol de esa carpeta con `recursesubdirs`.

Resultado: la clave quedaba instalada, en texto plano, en
`%LOCALAPPDATA%\Programs\RND DEMO\.env` de cada maquina. No hacia falta
descompilar el ejecutable: se instalaba y se abria el archivo.

Ademas, `tests/test_packaging_static.py` exigia que el build escribiera
`MINIMAX_API_KEY` en ese `.env`. El test fijaba la filtracion como contrato,
asi que agregar la proteccion sin tocarlo dejaba la suite en rojo y empujaba
a revertir el arreglo.

## Que se cambio

**`scripts/build_demo_installer.ps1`**
- La lista blanca ya no incluye `MINIMAX_API_KEY` ni `RND_PDF_AI_API_KEY`.
  Solo viajan `RND_PDF_AI_URL`, `RND_PDF_AI_TOKEN`, modelo y timeout.
- El build ahora exige la URL del proxy en vez de una API key.
- Barrera final: si la configuracion trae una credencial, el build aborta
  antes de generar el instalador.

**`utiles/importacion_pdf_ia.py`**
- `RND_PDF_AI_TOKEN` sirve como credencial cuando la URL apunta al proxy.
  Sigue having fallback a la API key real, que tiene prioridad.
- El mensaje de error cuando falta la credencial ahora depende del contexto:
  con proxy configurado dice que la IA no esta disponible y que RND sigue
  funcionando; sin proxy sigue diciendo que configure la API key, que es el
  caso de un equipo de desarrollo.

**`tests/test_packaging_static.py`**
- Se invirtio el contrato: ahora se verifica que el build NO pueda empaquetar
  una credencial, y que el proxy mantenga la clave fuera del docroot.

**`deploy/rnd-ia/`** (nuevo)
- `proxy.php`: proxy OpenAI-compatible. La clave real vive solo en el
  servidor. Rate limit por IP y global, corte por tamano de cuerpo y por
  cantidad de imagenes, log sin contenido.
- `_diag.php`: diagnostico temporal para el despliegue. No se queda en el
  servidor.
- `rnd-ia-secreto.php.ejemplo`: plantilla de configuracion, sin clave.
- `.htaccess`: bloquea el acceso a los archivos de estado.
- `README.md`: pasos de despliegue en Ferozo.
- `pruebas/`: arnes que levanta el proxy real contra un upstream falso.

El panel del asistente ya tenia un mensaje amable cuando la IA falla
(`vistas/AsistenteRndPanel.py`), asi que si el proxy no esta desplegado la
demo sigue operando, solo pierde esa funcion.

## Estado del instalador publicado

Version `2026.10.27.02`, publicada sobre la release fija `rnd-demo` con el
mismo link de siempre. Esta build incluye el cruce de remitos de Tio Pujio
con pedidos (#150): boton en Pedidos para organizar, autodeteccion del
proveedor, mensajes de estado e iconos en los botones.

| | |
|---|---|
| SHA256 | `f21df931fd6500ef4a1f85107fb34904a4d58e5994ca469b8d306ece980481ca` |
| Tamano | 76.126.272 bytes |
| Subido | 2026-10-27 14:37 UTC |
| Link | https://github.com/oscarvogel/vogel-releases/releases/download/rnd-demo/setup_rnd_demo.exe |

Verificado contra el asset publicado: el SHA256 local coincide con el digest
de GitHub, el bundle de PyInstaller incluye los modulos del cruce y la suite
completa paso con 391 tests. La grabacion de remitos se probo en una base
DEMO SQLite aislada, sin tocar produccion.

El build conserva la misma politica de configuracion IA: el `.env` que se
empaqueta contiene unicamente:

```
RND_PDF_AI_URL=https://vogelconsultoria.com.ar/rnd-ia/proxy.php
RND_PDF_AI_TOKEN=rnd-demo-2026
RND_PDF_AI_MODEL=MiniMax-M3
RND_PDF_AI_TIMEOUT=120
```

Sin `MINIMAX_API_KEY`, sin `RND_PDF_AI_API_KEY`, sin `MYSQL_PASSWORD`, sin
`RND_DB_PASSWORD`, sin prefijos de clave.

El token viaja en el ejecutable a proposito: no es un secreto, es el
interruptor para apagar la demostracion. El servidor todavia tiene
`token_demo` vacio, asi que funciona con o sin el. Cuando quieras activarlo:
poner `rnd-demo-2026` en `token_demo` del servidor, y el mismo ejecutador
sigue funcionando sin reconstruirlo.

## Estado del despliegue en vogelconsultoria.com.ar

**En produccion y funcionando.** Cliente Python -> proxy -> MiniMax real,
respuesta correcta y sin credenciales en el camino de vuelta.

Configuracion activa en el servidor:

| Dato | Valor |
|---|---|
| Ruta del secreto | `/home/a0110632/rnd-ia-secreto.php`, permisos 644 |
| open_basedir | incluye el home completo, no bloquea nada |
| opcache | **no esta cargado**, asi que rotar la clave se aplica al instante |
| URL del proveedor | `https://api.minimax.io/v1/chat/completions` (MiniMax directo) |
| `token_demo` | vacio, el proxy no exige token |
| `limite_diario` | 200 |

Lo que quedo bien:

- `rnd-ia/rnd-ia-secreto.php` responde **404**: no es accesible por web.
- `rnd-ia/estado/accesos.log` responde **403**. El `.htaccess` funciona.
- `rnd-ia/` responde **403**: no hay listado de directorio.
- El proxy responde 200 y devuelve la respuesta de MiniMax.

### Dos cosas para decidir sobre la configuracion

**`token_demo` vacio deja el proxy abierto.** Cualquiera que conozca la URL
puede consumir cuota. Hoy el unico freno es `limite_diario: 200` entre todas las
maquinas, mas 30 por minuto y por IP. Poner un token es una linea y compra algo
que el limite diario no da: poder **apagar la demostracion en diez segundos**
cambiando un valor en el servidor, sin republicar el instalador. El token viaja
dentro del ejecutable, asi que no es un secreto, es un interruptor.

**Apunta a MiniMax directo, no a OpenRouter.** Funciona, pero MiniMax no tiene
tope de gasto por API key. OpenRouter si lo tiene, y ademas el proxy gana
resistencia: si MiniMax se cae en plena demo, OpenRouter enruta a otro modelo.
Cambiarlo es editar dos lineas del archivo de credenciales.

## Errores encontrados durante la verificacion

Ninguno de estos aparecia leyendo el codigo. Salieron al ejecutar el flujo
real y al desplegar.

### La barrera del build era codigo muerto

La primera version buscaba el nombre prohibido **en el texto ya escrito**:

```powershell
$escrito = $lines -join "`n"
if ($escrito -match "MINIMAX_API_KEY") { throw "ABORTADO" }
```

No podia dispararse nunca: las credenciales ya se filtraban antes, en
`Get-DemoAiConfig`, asi que la clave nunca llegaba a `$lines`. Apuntada a la
causa (`$Values.ContainsKey($prohibida)`) funciona.

### El include podia servir la clave en un archivo mal formado

`include` no solo ejecuta PHP: **emite a la salida todo lo que encuentra que
no sea codigo PHP**. Si el archivo de credenciales se guardaba con la clave
sola, el `include` la imprimia y el proxy terminaba sirviendo la credencial en
su propia respuesta HTTP. El proxy que existe para proteger la clave hacia
exactamente lo contrario.

Se arreglo capturando la salida con `ob_start()` / `ob_end_clean()` y
descartandola siempre, sin importar si el archivo esta bien.

### El chequeo de configuracion tapaba el 405

Estaba **antes** del chequeo de metodo. Como el archivo de credenciales no
existia, todos los metodos devolvian 503 y un GET mal hecho se disfrazaba de
servidor roto. Con el orden invertido, un GET devuelve 405 aunque falte la
configuracion.

### La ruta del secreto estaba mal: dos niveles, no uno

Este fue el error que rompio el despliegue, y era del codigo, no del hosting.

El proxy vive en `public_html/rnd-ia/`, o sea que `__DIR__ . '/..'` es
`public_html/`, que **sigue bajo el docroot**. El archivo se buscaba ahi
mientras estaba en `/home/a0110632/`, dos niveles arriba, que es donde lo habia
puesto correctamente siguiendo la instruccion del README.

Por que las pruebas locales no lo detectaron: el fixture usaba `public/` como
docroot, con el secreto a un solo nivel. Produccion tiene dos niveles de
profundidad y la prueba tenia uno, asi que la ruta de un nivel funcionaba en
local y fallaba en el servidor. Los fixtures ahora reproducen la estructura
real: `public_html/rnd-ia/` con el secreto en la raiz del home.

### PHP cachea los archivos

Encontrado al reproducir el caso anterior. Con el servidor ya arrancado, se
cambio `rnd-ia-secreto.php` de un array valido a texto plano y el proxy **siguio
respondiendo con la configuracion anterior**: no se veia el cambio.

Consecuencia practica: rotar la clave editando el archivo puede no surtir
efecto. Si el hosting tuviera `opcache.validate_timestamps` desactivado, el
cambio no se reflejaria nunca y se seguiria gastando con la credencial vieja.
En el hosting real no hay opcache, asi que no aplica, pero por eso `_diag.php`
muestra la configuracion de cache y ejecuta `opcache_reset()` al correr.

## Verificacion hecha

- Suite completa: **319 tests** en verde.
- **Sintaxis PHP validada** con `php -l` (PHP 8.5.4 en WSL) sobre `proxy.php`,
  `_diag.php` y `rnd-ia-secreto.php.ejemplo`.
- **Proxy de punta a punta**, con `deploy/rnd-ia/pruebas/probar_proxy.sh`:
  levanta el `proxy.php` real contra un upstream falso y comprueba 27 cosas,
  con el layout real de hosting. Incluye los cuatro fallos de arriba como
  pruebas permanentes.
- **Cliente Python contra el proxy real**, con
  `deploy/rnd-ia/pruebas/probar_cliente.sh` y tambien contra el proxy
  desplegado en produccion: cierra el circuito `_configuracion()` -> urllib ->
  proxy -> proveedor, y verifica que un 401 le llega al operador con el
  mensaje correcto y que el error sin credencial es el de usuario final.
- **Diagnostico probado en los tres casos** que puede encontrar, con
  `probar_diagnostico.sh`.
- Flujo real del build: con un archivo de secretos que trae
  `MINIMAX_API_KEY`, `RND_PDF_AI_API_KEY` y `MYSQL_PASSWORD` falsas, el
  `.env` generado sale con URL, token, modelo y timeout. Ninguna credencial.
  La barrera aborta cuando se le pasa una credencial.

Ninguna de estas pruebas usa una API key real, salvo la de produccion, que es
una llamada minima de verificacion.

## Hallazgo sobre el .env de desarrollo

`C:\Programacion\RND\.env` contiene `MINIMAX_API_KEY` (ademas de
`RND_DB_USER`, `RND_DB_PASSWORD` y `MYSQL_PASSWORD`). Esta correctamente
ignorado por git, pero contiene la misma clave que estaba expuesta en el
instalador.

Importa por dos motivos:

1. Hay que sacar esa linea al rotar la clave. Si se olvida, el proximo build
   vuelve a leerla de ahi.
2. Mientras siga definida tiene prioridad sobre `RND_PDF_AI_TOKEN`, asi que
   para probar el proxy en desarrollo hay que comentarla. En la demo instalada
   no hay conflicto: el `.env` que viaja ya no lleva credenciales.

Los scripts de `deploy/rnd-ia/pruebas/` limpian el entorno y nunca muestran el
valor de una clave.

## Pendientes

1. **Rotar la clave de MiniMax** en el panel del proveedor y sacar
   `MINIMAX_API_KEY` del `.env` de la raiz. Es lo primero. La clave actual
   esta expuesta: estuvo en una release publica desde el 29/09. Sacarla del
   instalador nuevo no la salva, porque cualquiera que haya descargado el
   instalador viejo ya la tiene.
2. **Borrar `_diag.php`** del servidor si todavia esta ahi.
3. **Avisar a quien tenga la demo instalada** que la actual sigue con la clave
   vieja y que la nueva ya no es valida. Instalar la nueva no alcanza si el
   cliente no la baja.
4. Opcional: activar `token_demo` en el servidor, y crear la API key de
   OpenRouter con tope de gasto para dejar de depender de MiniMax directo.

## Decisiones que quedaron documentadas

La credencial que paga la IA vive en el servidor, no en la base de datos de
RND. Guardarla en la base de una instalacion seria volver a distribuirla, que
es el problema original. La credencial propia de cada cliente, si alguna vez se
soporta, si va a su base local cifrada con DPAPI, siguiendo el patron de
`rnd_credentials.py`.

El token que viaja en el ejecutable es un interruptor, no un secreto: esta
ahi a proposito para poder apagar la demostracion cambiando un valor en el
servidor, sin republicar el instalador.

El proxy es publico por diseno. Eso no significa sin proteccion: no lleva
credenciales, lo frena el rate limit y el tope diario, y se puede apagar.
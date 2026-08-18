# Desarrollo local de RND

Esta modalidad permite trabajar contra un MySQL local sin modificar la configuración ni la credencial usada en producción.

## Producción

La forma actual no cambia:

```bat
python main.py
```

Continúa usando `sistema.ini` y la credencial segura histórica `mysql.credential`.

## Desarrollo local

Desde la carpeta del proyecto:

```bat
python run_local.py
```

La primera vez, si no existe `sistema.local.ini`, el launcher crea una copia de `sistema.local.ini.example` y termina para que pueda revisarse la configuración.

Configuración típica:

```ini
[param]
host = 127.0.0.1
basedatos = rnd
port = 3306
user = root
```

No agregue contraseñas al INI. Al volver a ejecutar `python run_local.py`, RND usa el mecanismo seguro DPAPI existente, pero con una credencial separada llamada `mysql.local.credential`.

## Actualizar una copia ya existente

Si el repositorio ya está clonado:

```bat
cd /d O:\rnd
git checkout main
git pull origin main
```

Mientras el cambio esté en la rama del issue #31 para pruebas:

```bat
cd /d O:\rnd
git fetch origin
git checkout issue-31-entorno-local
git pull origin issue-31-entorno-local
```

Después:

```bat
python run_local.py
```

## Garantía de aislamiento

- `sistema.ini` sigue reservado para producción.
- `sistema.local.ini` está excluido de Git.
- Producción usa `mysql.credential`.
- Local usa `mysql.local.credential`.
- `python main.py` no cambia de comportamiento.

# Diseño: eliminar el fallback de CSS legado en formularios RND

## Problema

Las ventanas de RND que heredan de `pyqt5libs.Formulario` pueden terminar con
un fondo oscuro y texto ilegible. `main.py` intenta aplicar el QSS global
`temas/vogel2026.qss`, pero `Formulario.EstabelecerTema()` todavía consulta el
parámetro legado `TEMA` y aplica archivos como `darkblue.css` cuando considera
que debe usar un fallback. Ese fallback no es neutro y puede volver a activar
la combinación de fondo oscuro con texto oscuro.

## Decisión

`Formulario` no aplicará automáticamente el parámetro `TEMA` ni ningún CSS
legado. El tema global de `QApplication`, cuando exista, será la única fuente
de estilos de la aplicación. Si el QSS global no está disponible, el formulario
conservará el estilo nativo de Qt y seguirá siendo funcional; no se activará un
tema oscuro por defecto.

La corrección vive en la clase base para cubrir todos los formularios derivados,
incluidos Gestión de Tabla de Clientes e Importación de Pedidos, sin modificar
su lógica de negocio.

## Validación

- Prueba de regresión: `EstabelecerTema()` no aplica CSS legado con o sin QSS
  global.
- Pruebas existentes del tema global y del arranque siguen pasando.
- Se ejecuta una validación focalizada sobre las dos vistas reportadas y la
  clase base, usando Qt offscreen cuando el entorno no permite abrir ventanas.
- Se preservan los cambios locales preexistentes del checkout.

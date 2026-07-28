# pyqt5libs

Biblioteca de utilidades y componentes reutilizables para aplicaciones de escritorio desarrolladas con PyQt5.

## Estado del proyecto

El proyecto está en etapa de ordenamiento y modernización. Ya puede instalarse localmente como paquete Python para desarrollo, pero todavía no debe considerarse una API pública estable completa.

La estructura histórica del repositorio se mantiene por compatibilidad. La estructura objetivo está documentada en `docs/estructura-paquete.md`.

## Objetivo

Centralizar utilidades repetidas de aplicaciones PyQt5 administrativas:

- vistas base;
- pantallas de gestión;
- grillas y tablas;
- formularios y validaciones;
- combos;
- diálogos y mensajes;
- estilos QSS;
- configuración;
- exportación de datos.

## Instalación para desarrollo

Desde la raíz del repositorio:

```bash
pip install -e .
```

Verificación rápida:

```bash
python -c "import pyqt5libs; print(pyqt5libs.__version__)"
```

## Instalación desde PyPI

Cuando el paquete esté publicado, podrá instalarse con:

```bash
pip install pyqt5libs
```

## Uso básico actual

Por ahora la API pública mínima expone la versión del paquete:

```python
import pyqt5libs

print(pyqt5libs.__version__)
```

Los módulos históricos existentes serán ordenados progresivamente en módulos públicos documentados.

## Requisitos

- Python 3.8 o superior
- PyQt5 5.15 o superior

## Roadmap inicial

- Ordenar estructura pública del paquete.
- Agregar tests y CI.
- Mejorar la vista de gestión existente.
- Agregar helpers de diálogos, validaciones, combos y tablas.
- Documentar ejemplos reales por módulo.

## Contribuir

Las contribuciones son bienvenidas mediante issues o pull requests.

## Licencia

Este proyecto está bajo la licencia LGPL v3.

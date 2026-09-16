"""controladores: paquete con los controladores de RND.

No importar controladores de forma ansiosa desde aqui. Varias pantallas tienen
dependencias opcionales/pesadas (por ejemplo PyMuPDF/fitz) que no deben impedir
el arranque general ni el modo DEMO antes de abrir esa funcionalidad.
"""

__all__ = [
    "ABMClientes",
    "ABMEmpleados",
    "ABMEquipos",
    "ABMProveedores",
    "ABMTablas",
    "Auditoria",
    "Automatizaciones",
    "ConfiguracionDB",
    "ImportacionPedidos",
    "Login",
    "Main",
    "Migraciones",
    "PyFPDF",
    "VerHojaRuta",
]

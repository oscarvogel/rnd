"""Estilo visual Fluent/Windows 11 para pantallas AutoABM.

El objetivo es modernizar la interfaz sin cambiar la lógica del ABM histórico.
"""


def fluent_abm_stylesheet():
    return """
    ABM {
        background: #f3f6fb;
        font-family: "Segoe UI", "Arial", sans-serif;
        font-size: 10.5pt;
        color: #1f1f1f;
    }

    #tituloPantalla {
        font-size: 20pt;
        font-weight: bold;
        color: #111827;
        padding: 2px 2px 6px 2px;
    }

    #subtituloPantalla {
        color: #5f6368;
        font-size: 11pt;
        margin-bottom: 8px;
    }

    #toolbarABM, #horizontalLayout {
        background: transparent;
        border: none;
    }

    #tabLista, #tabDetalle, #formPanelABM {
        background: #ffffff;
        border: 1px solid #d8e0ea;
        border-radius: 12px;
    }

    #tabLista {
        padding: 0px;
    }

    #scrollDetalleABM {
        background: transparent;
        border: none;
    }

    #lblEstado {
        font-size: 14pt;
        font-weight: bold;
        color: #111827;
        padding-bottom: 10px;
        border-bottom: 1px solid #edf0f5;
        margin-bottom: 8px;
    }

    #lblResumen {
        color: #4b5563;
        padding: 2px 4px 0px 4px;
    }

    #labelNombre {
        color: #374151;
        font-size: 10pt;
        font-weight: bold;
        padding-bottom: 2px;
    }

    #lineEditBusqueda, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
        background: #ffffff;
        border: 1px solid #c8d2df;
        border-radius: 8px;
        padding: 8px 10px;
        min-height: 20px;
        selection-background-color: #2563eb;
    }

    #lineEditBusqueda:focus, QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
        border: 1px solid #2563eb;
        background: #ffffff;
    }

    QCheckBox {
        spacing: 8px;
        color: #1f2937;
    }

    QCheckBox::indicator {
        width: 16px;
        height: 16px;
        border: 1px solid #9ca3af;
        border-radius: 4px;
        background: #ffffff;
    }

    QCheckBox::indicator:checked {
        background: #0f6cbd;
        border: 1px solid #0f6cbd;
    }

    QTableWidget, QTableView {
        background: #ffffff;
        border: none;
        gridline-color: #eef2f7;
        selection-background-color: #dbeafe;
        selection-color: #111827;
        alternate-background-color: #f8fbff;
    }

    QTableWidget::item, QTableView::item {
        border: none;
        padding: 8px 10px;
    }

    QTableWidget::item:selected, QTableView::item:selected {
        background: #dbeafe;
        color: #111827;
        border-radius: 6px;
    }

    QHeaderView::section {
        background: #f8fafc;
        color: #374151;
        border: none;
        border-bottom: 1px solid #e5e7eb;
        padding: 10px 12px;
        font-weight: bold;
    }

    QTableCornerButton::section {
        background: #f8fafc;
        border: none;
        border-bottom: 1px solid #e5e7eb;
    }

    QPushButton, Boton {
        background: #f8fafc;
        color: #111827;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 7px 14px;
        min-height: 26px;
        font-weight: bold;
    }

    QPushButton:hover, Boton:hover {
        background: #eef4fb;
        border-color: #b8c4d4;
    }

    QPushButton:pressed, Boton:pressed {
        background: #e2eaf4;
        border-color: #9fb0c6;
    }

    QPushButton:focus, Boton:focus {
        border: 1px solid #2563eb;
    }

    QPushButton:default, Boton:default {
        border: 1px solid #cbd5e1;
    }

    QPushButton:disabled, Boton:disabled {
        color: #8f98a8;
        background: #eef1f5;
        border-color: #e5e7eb;
    }

    QPushButton#btnAgregar, Boton#btnAgregar,
    QPushButton#btnAceptar, Boton#btnAceptar {
        background: #0f6cbd;
        color: #ffffff;
        border: 1px solid #0f6cbd;
        font-weight: bold;
    }

    QPushButton#btnAgregar:hover, Boton#btnAgregar:hover,
    QPushButton#btnAceptar:hover, Boton#btnAceptar:hover {
        background: #115ea3;
        border-color: #115ea3;
    }

    QPushButton#btnAceptar:disabled, Boton#btnAceptar:disabled {
        background: #d8e4f2;
        color: #6b7b90;
        border-color: #d8e4f2;
    }

    QPushButton#btnBorrar, Boton#btnBorrar {
        color: #b91c1c;
        border-color: #fecaca;
        background: #fff7f7;
    }

    QPushButton#btnBorrar:hover, Boton#btnBorrar:hover {
        background: #fee2e2;
        border-color: #fca5a5;
    }

    QPushButton#btnCancelar, Boton#btnCancelar {
        background: #ffffff;
        color: #111827;
    }

    QPushButton#btnCerrar, Boton#btnCerrar,
    QPushButton#btnExcel, Boton#btnExcel,
    QPushButton#btnEditar, Boton#btnEditar,
    QPushButton#btnLimpiarBusqueda, Boton#btnLimpiarBusqueda {
        background: #ffffff;
    }

    QSplitter::handle {
        background: transparent;
        width: 12px;
    }
    """

__all__ = ["fluent_abm_stylesheet"]

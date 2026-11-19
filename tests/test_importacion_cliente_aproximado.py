# coding=utf-8
"""Resolucion de clientes por nombre normalizado durante la importacion."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import controladores.ImportacionPedidos as importacion


class ClienteFalso:
    def __init__(self, id, razon_social):
        self.id = id
        self.razon_social = razon_social


def _controlador(indice):
    controller = importacion.ImportacionPedidosController.__new__(
        importacion.ImportacionPedidosController
    )
    controller._indice_clientes_nombres = indice
    return controller


def test_normaliza_el_nombre_sin_puntos_ni_espacios():
    assert importacion.normalizar_nombre_cliente("PROVOLONE S. A. S.") == "PROVOLONESAS"
    assert importacion.normalizar_nombre_cliente("PROVOLONE S.A.S.") == "PROVOLONESAS"
    assert importacion.normalizar_nombre_cliente("  lozano  ") == "LOZANO"


def test_resuelve_por_nombre_normalizado():
    cliente = ClienteFalso(7, "PROVOLONE S.A.S.")
    controller = _controlador({"PROVOLONESAS": [cliente]})

    resultado = controller._resolver_cliente_por_nombre_aproximado("PROVOLONE S. A. S.")

    assert resultado is cliente


def test_resuelve_por_prefijo_cuando_el_proveedor_trunca_el_nombre():
    cliente = ClienteFalso(9, "VARGAS MARIA JOSE ITATI")
    controller = _controlador({"VARGASMARIAJOSEITATI": [cliente]})

    resultado = controller._resolver_cliente_por_nombre_aproximado("VARGAS MARIA JOSE")

    assert resultado is cliente


def test_no_resuelve_si_hay_varios_clientes_con_el_mismo_nombre():
    controller = _controlador({
        "PROVOLONESAS": [ClienteFalso(1, "PROVOLONE S.A.S."), ClienteFalso(2, "PROVOLONE S A S")],
    })

    assert controller._resolver_cliente_por_nombre_aproximado("PROVOLONE S.A.S.") is None


def test_no_resuelve_con_nombres_demasiado_cortos():
    controller = _controlador({"PEPE": [ClienteFalso(1, "PEPE")]})

    assert controller._resolver_cliente_por_nombre_aproximado("PEPE") is None
    assert controller._resolver_cliente_por_nombre_aproximado("") is None


def test_no_resuelve_si_no_hay_ningun_cliente_parecido():
    controller = _controlador({"OTROCLIENTE": [ClienteFalso(1, "OTRO CLIENTE")]})

    assert controller._resolver_cliente_por_nombre_aproximado("PROVOLONE S.A.S.") is None

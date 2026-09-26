from controladores.ABMClientes import ABMClientesController


class _Control:
    def __init__(self, value):
        self._value = value

    def valor(self):
        return self._value


class _Dato:
    def __init__(self):
        self.__data__ = {}


class _Vista:
    autoincremental = True
    controles = {
        "id": _Control(""),
        "razon_social": _Control("Cliente nuevo"),
        "telefono": _Control("03743-000000"),
    }


def test_issue_127_alta_cliente_no_envia_id_vacio_a_sqlite():
    controller = ABMClientesController.__new__(ABMClientesController)
    controller.view = _Vista()
    controller.campoclave = "id"

    dato = _Dato()
    controller._copiar_controles_al_modelo(dato, es_alta=True)

    assert "id" not in dato.__data__
    assert dato.__data__["razon_social"] == "Cliente nuevo"
    assert dato.__data__["telefono"] == "03743-000000"


def test_issue_127_edicion_conserva_comportamiento_del_id():
    controller = ABMClientesController.__new__(ABMClientesController)
    controller.view = _Vista()
    controller.campoclave = "id"

    dato = _Dato()
    controller.view.controles = {
        "id": _Control("15"),
        "razon_social": _Control("Cliente editado"),
    }
    controller._copiar_controles_al_modelo(dato, es_alta=False)

    assert dato.__data__["id"] == "15"
    assert dato.__data__["razon_social"] == "Cliente editado"

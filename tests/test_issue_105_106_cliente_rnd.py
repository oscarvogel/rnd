import math

import pandas as pd

from controladores.ImportacionPedidos import valor_para_vista_previa


def test_issue_105_valores_excel_se_convierten_a_texto_seguro():
    assert valor_para_vista_previa(28.0) == "28"
    assert valor_para_vista_previa(31.82) == "31.82"
    assert valor_para_vista_previa(70.85000000000001) == "70.85"
    assert valor_para_vista_previa(10509.759999999998) == "10509.76"
    assert valor_para_vista_previa(7) == "7"
    assert valor_para_vista_previa("QUESO TYBO") == "QUESO TYBO"
    assert valor_para_vista_previa(float("nan")) == ""
    assert valor_para_vista_previa(pd.NA) == ""


def test_issue_105_no_entrega_float_crudo_a_la_grilla():
    valores = [28.0, 31.82, float("nan"), "texto"]
    convertidos = [valor_para_vista_previa(x) for x in valores]
    assert convertidos == ["28", "31.82", "", "texto"]
    assert all(isinstance(x, str) for x in convertidos)


def test_issue_106_abm_clientes_se_integra_con_dialogo_modal_y_refresca():
    source = open("controladores/BandejaPedidos.py", encoding="utf-8").read()

    assert "gestor.view.setParent(dialogo, Qt.Window)" in source
    assert "gestor.view.setAttribute(Qt.WA_DeleteOnClose, True)" in source
    assert "gestor.view.destroyed.connect(al_cerrar_abm)" in source
    assert "recargar_clientes()" in source
    assert "gestor_actual.view.isVisible()" in source

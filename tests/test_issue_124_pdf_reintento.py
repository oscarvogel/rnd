# coding=utf-8
from unittest.mock import MagicMock, patch


def test_issue_124_pdf_no_se_entrega_directamente_a_pandas_si_fallo_preprocesamiento():
    from controladores.ImportacionPedidos import ImportacionPedidosController

    controller = ImportacionPedidosController.__new__(ImportacionPedidosController)
    controller.view = MagicMock()
    controller.view.txt_archivo.text.return_value = r"C:\tmp\estancia.pdf"
    controller.archivo_trabajo = None
    controller.archivo_origen = None
    controller._actualizar_ayuda_proveedor = MagicMock()
    controller._preparar_archivo = MagicMock(return_value=False)

    with patch("controladores.ImportacionPedidos.pd.read_excel") as read_excel:
        ImportacionPedidosController.importar_pedidos.__wrapped__(controller)

    controller._preparar_archivo.assert_called_once_with(
        r"C:\tmp\estancia.pdf"
    )
    read_excel.assert_not_called()

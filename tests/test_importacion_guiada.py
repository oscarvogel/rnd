# coding=utf-8
import unittest
from datetime import date

from utiles.importacion_guiada import (
    ACCION_CONTINUAR,
    ACCION_CORREGIR,
    ACCION_REVISAR,
    ResumenImportacion,
    ayuda_proveedor,
    limpiar_resultados_dia,
    obtener_resultado_dia,
    registrar_resultado_dia,
)


class ResumenImportacionTests(unittest.TestCase):
    def tearDown(self):
        limpiar_resultados_dia()

    def test_importacion_exitosa_continua_reparto(self):
        resumen = ResumenImportacion(leidos=12, importados=12)
        self.assertTrue(resumen.exitosa)
        self.assertEqual(resumen.siguiente_accion, ACCION_CONTINUAR)
        self.assertIn("Pedidos importados: 12", resumen.detalle)

    def test_importacion_parcial_envia_a_revision(self):
        resumen = ResumenImportacion(
            leidos=12, importados=9, omitidos=1, pendientes=2
        )
        self.assertTrue(resumen.parcial)
        self.assertEqual(resumen.siguiente_accion, ACCION_REVISAR)
        self.assertIn("Pendientes: 2", resumen.detalle)

    def test_importacion_fallida_pide_corregir(self):
        resumen = ResumenImportacion(leidos=5, errores=1)
        self.assertTrue(resumen.fallida)
        self.assertEqual(resumen.siguiente_accion, ACCION_CORREGIR)

    def test_resultado_del_dia_queda_disponible_para_dashboard(self):
        fecha = date(2026, 8, 11)
        resumen = ResumenImportacion(leidos=4, importados=4)
        registrar_resultado_dia(resumen, fecha)
        self.assertIs(obtener_resultado_dia(fecha), resumen)

    def test_tremblay_tiene_ayuda_especifica(self):
        self.assertIn("Tremblay", ayuda_proveedor("15"))


if __name__ == "__main__":
    unittest.main()

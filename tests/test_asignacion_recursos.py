# coding=utf-8
import unittest
from types import SimpleNamespace

from utiles.asignacion_recursos import construir_resumen, validar_asignacion


class AsignacionRecursosTests(unittest.TestCase):
    def registro(self, responsable=23, equipo=1, kg=100, bultos=2):
        return SimpleNamespace(
            responsable_id=responsable,
            equipo_asignado_id=equipo,
            kg=kg,
            cantidad_bultos=bultos,
        )

    def test_asignacion_inicial_requiere_recursos_reales(self):
        resumen = construir_resumen([self.registro(), self.registro(kg=50, bultos=1)])
        self.assertEqual(resumen.pedidos, 2)
        self.assertEqual(str(resumen.kg), "150")
        self.assertFalse(resumen.recursos_completos(23, 1))
        valido, _ = validar_asignacion(resumen, 10, 5, 23, 1)
        self.assertTrue(valido)

    def test_falta_chofer_o_camion_es_invalida(self):
        resumen = construir_resumen([self.registro()])
        self.assertFalse(validar_asignacion(resumen, 0, 5, 23, 1)[0])
        self.assertFalse(validar_asignacion(resumen, 10, 0, 23, 1)[0])
        self.assertFalse(validar_asignacion(resumen, 23, 5, 23, 1)[0])
        self.assertFalse(validar_asignacion(resumen, 10, 1, 23, 1)[0])

    def test_reasignacion_uniforme_se_detecta_completa(self):
        resumen = construir_resumen([
            self.registro(responsable=10, equipo=5),
            self.registro(responsable=10, equipo=5),
        ])
        self.assertFalse(resumen.asignacion_mixta)
        self.assertEqual(resumen.responsable_id, 10)
        self.assertEqual(resumen.equipo_id, 5)
        self.assertTrue(resumen.recursos_completos(23, 1))

    def test_estado_mixto_exige_normalizacion(self):
        resumen = construir_resumen([
            self.registro(responsable=10, equipo=5),
            self.registro(responsable=11, equipo=5),
        ])
        self.assertTrue(resumen.asignacion_mixta)
        self.assertFalse(resumen.recursos_completos(23, 1))

    def test_ruta_vacia_no_permite_guardar(self):
        resumen = construir_resumen([])
        valido, mensaje = validar_asignacion(resumen, 10, 5, 23, 1)
        self.assertFalse(valido)
        self.assertIn("no tiene pedidos", mensaje)


if __name__ == "__main__":
    unittest.main()

# coding=utf-8
"""Importacion de las facturas escaneadas de Tacural."""
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utiles.importacion_factura_tacural import (  # noqa: E402
    _errores_de_orientacion,
    _errores_de_pagina,
    _filas_de_pagina,
    _limpiar_unidades_duplicadas,
    _notas_de_pagina,
    _parsear_transcripcion,
    _reajustar_pesos,
    _tipo_documento,
    procesar_factura_tacural,
)
from utiles.importacion_proveedores_excel import (  # noqa: E402
    COLUMNAS_NORMALIZADAS,
    normalizar_archivo_pedidos,
    normalizar_metodo_importacion,
)


TRANSCRIPCION_FACTURA = """TIPO_DOCUMENTO: FACTURA
NUMERO: A00011-00420809
FECHA: 18/11/2026
RAZON_SOCIAL: LOZANO MARIELA GUADALUPE
CODIGO_CLIENTE: 5808
DIRECCION: RUTA PROVINCIAL 213 8026 Dp
LOCALIDAD: POSADAS
PROVINCIA: Misiones
CP: 3300
TELEFONO: 3764721983
CUIT: 27-20144842-0
CAJA: 2
ZONA: 58
NUMERO_PEDIDO: 1
TOTAL_KILOGRAMOS: 53.60
ITEM: 10110~JAMON COCIDO ESPE 3~3~15.60~8.413,88~10.00~21.00~131.256,59
ITEM: 10314~SALAME MILAN SIN~2~4.60~10.509,92~10.00~21.00~48.345,64
ITEM: 10200~MORTADELA~1~3.80~7.147,94~10.00~21.00~27.162,15
ITEM: 10421~SALCHI PARRILLER~1~1.60~8.066,12~10.00~21.00~12.905,79
ITEM: 10132~JAMON COCIDO PAMP~3~15.00~4.165,29~10.00~21.00~62.479,35
ITEM: 10202~MORTADELA PAMPITA~1~3.00~3.123,96~10.00~21.00~9.371,89
ITEM: 10130~FIAMBRE COCIDO PA~2~10.00~2.759,51~10.00~21.00~27.595,08"""

TRANSCRIPCION_PRESUPUESTO = """TIPO_DOCUMENTO: PRESUPUESTO
NUMERO: B00099-00023463
FECHA: 11/11/2026
RAZON_SOCIAL: SILVA DANIELA
CODIGO_CLIENTE: 9164
DIRECCION: CHACRA 147 CASA 8
LOCALIDAD: POSADAS
PROVINCIA: Misiones
CP: 3300
TELEFONO: 03764-393765
CUIT: -
CAJA: -
ZONA: 58
NUMERO_PEDIDO: -
TOTAL_KILOGRAMOS: 123.90
ITEM: 10108~JAMON COCIDO C/C~18~92.70~10.082,70~10.00~-~934.666,52
ITEM: 10804~PANCETA AHUMADA~4~1.20~16.786,80~10.00~-~20.144,17
ITEM: 10130~FIAMBRE COCIDO P~6~30.00~2.700,01~10.00~-~81.000,04"""


def _crear_pdf(path, apaisada=False):
    import fitz

    documento = fitz.open()
    if apaisada:
        pagina = documento.new_page(width=842, height=595)
    else:
        pagina = documento.new_page(width=595, height=842)
    pagina.insert_text((50, 60), "TACURAL - pagina de prueba", fontsize=12)
    documento.save(str(path))
    documento.close()
    return path


def test_parsea_la_transcripcion_de_una_factura():
    encabezado, items, problemas = _parsear_transcripcion(TRANSCRIPCION_FACTURA)

    assert problemas == []
    assert encabezado["NUMERO"] == "A00011-00420809"
    assert encabezado["RAZON_SOCIAL"] == "LOZANO MARIELA GUADALUPE"
    assert encabezado["LOCALIDAD"] == "POSADAS"
    assert len(items) == 7
    assert items[0]["codigo"] == "10110"
    assert items[0]["unid"] == 3
    assert items[0]["kg"] == pytest.approx(15.60)
    assert items[0]["punit"] == pytest.approx(8413.88)
    assert items[0]["importe"] == pytest.approx(131256.59)


def test_los_kilos_de_las_lineas_cuadran_con_el_total_impreso():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)

    assert _errores_de_orientacion(encabezado, items) == []


def test_avisa_cuando_los_kilos_no_cuadran_con_el_total_impreso():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)
    encabezado["TOTAL_KILOGRAMOS"] = "99.99"

    errores = _errores_de_orientacion(encabezado, items)

    assert any("no coincide con el total impreso" in error for error in errores)


def test_una_factura_con_localidad_igual_a_provincia_no_se_marca_para_revisar():
    # Hay facturas de Tacural que imprimen "Localidad: MISIONES" con
    # "Provincia: Misiones": es un dato del proveedor, no una mala lectura.
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)
    encabezado["LOCALIDAD"] = "MISIONES"

    assert _errores_de_orientacion(encabezado, items) == []
    assert any("misma localidad" in nota for nota in _notas_de_pagina(encabezado))


def test_avisa_cuando_el_numero_no_es_de_tacural():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)
    encabezado["NUMERO"] = "FACTURA 123"

    errores = _errores_de_orientacion(encabezado, items)

    assert any("no tiene el formato de Tacural" in error for error in errores)


def test_avisa_cuando_la_razon_social_es_el_encabezado_del_proveedor():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)
    encabezado["RAZON_SOCIAL"] = "TACURAL CHACINADOS TACURAL SRL"

    errores = _errores_de_orientacion(encabezado, items)

    assert any("encabezado del proveedor" in error for error in errores)


def test_el_tipo_de_comprobante_sale_del_numero_y_no_de_la_ia():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)

    assert _tipo_documento(encabezado) == "FACTURA"

    # La IA se equivoca y dice presupuesto: manda el numero.
    encabezado["TIPO_DOCUMENTO"] = "PRESUPUESTO"
    encabezado["NUMERO"] = "B00099-00023463"
    assert _tipo_documento(encabezado) == "PRESUPUESTO"


def test_lee_un_renglon_con_los_campos_etiquetados():
    linea = (
        "ITEM: codigo=10110 | descripcion=JAMON COCIDO ESPE 3 | unid=3 | kg=15.60 "
        "| punit=8.413,88 | bonif=10.00 | iva=21.00 | importe=131.256,59"
    )

    encabezado, items, problemas = _parsear_transcripcion(linea)

    assert problemas == []
    assert items[0]["codigo"] == "10110"
    assert items[0]["descripcion"] == "JAMON COCIDO ESPE 3"
    assert items[0]["unid"] == 3
    assert items[0]["kg"] == pytest.approx(15.60)
    assert items[0]["importe"] == pytest.approx(131256.59)


def test_un_renglon_sin_la_columna_unid_no_mezcla_el_peso():
    linea = (
        "ITEM: codigo=10134 | descripcion=FIAMBRE COCIDO DE 12 | unid=- | kg=60.00 "
        "| punit=2.759,51 | bonif=10.00 | iva=21.00 | importe=165.570,48"
    )

    _, items, _ = _parsear_transcripcion(linea)

    assert items[0]["unid"] is None
    assert items[0]["kg"] == pytest.approx(60.00)


def test_avisa_cuando_el_importe_no_cierra_con_kilos_por_precio():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)
    items[0]["importe"] = 999999.99

    errores = _errores_de_pagina(encabezado, items)

    assert any("no cierra" in error for error in errores)


def test_reajusta_el_peso_cuando_la_ia_lo_carga_en_la_columna_unidades():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)
    # El modelo de la IA se equivoco de columna: cargo el peso en Unid.
    for item in items:
        item["unid"], item["kg"] = item["kg"], item["unid"]

    assert _reajustar_pesos(items, 53.60) is True
    assert items[0]["unid"] == 3
    assert items[0]["kg"] == pytest.approx(15.60)


def test_limpia_las_unidades_duplicadas_del_peso():
    items = [
        {"unid": 60.00, "kg": 60.00},
        {"unid": 4.60, "kg": 4.60},
    ]

    assert _limpiar_unidades_duplicadas(items) is True
    assert items[0]["unid"] is None
    assert items[0]["kg"] == pytest.approx(60.00)


def test_no_limpia_unidades_iguales_al_peso_cuando_son_pesos_enteros():
    # Un peso entero puede ser una unidad real: no se toca.
    items = [{"unid": 2, "kg": 2}, {"unid": 3, "kg": 3}]

    assert _limpiar_unidades_duplicadas(items) is False
    assert items[0]["unid"] == 2


def test_avisa_si_el_cuit_leido_es_el_del_proveedor():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)
    encabezado["CUIT"] = "30-58743818-2"

    errores = _errores_de_orientacion(encabezado, items)

    assert any("CUIT leido es el del proveedor" in error for error in errores)


def test_arma_las_filas_con_el_contrato_de_rnd():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)

    filas = _filas_de_pagina(encabezado, items, 1, False)

    assert len(filas) == 7
    assert list(filas[0].keys()) == COLUMNAS_NORMALIZADAS
    assert filas[0]["codigo_cliente"] == "27201448420"
    assert filas[0]["detalle_cliente"] == "LOZANO MARIELA GUADALUPE"
    assert filas[0]["destino"] == "POSADAS"
    assert filas[0]["comprobante"] == "A00011-00420809"
    assert filas[0]["cantidad"] == 3
    assert filas[0]["producto"] == "JAMON COCIDO ESPE 3"
    assert filas[0]["bultos"] == 2
    assert filas[0]["kilos"] == pytest.approx(15.60)
    assert "Cod.Art 10110" in filas[0]["observaciones"]
    assert "REVISAR" not in filas[0]["observaciones"]


def test_marca_para_revisar_las_filas_de_una_pagina_que_no_cierra():
    encabezado, items, _ = _parsear_transcripcion(TRANSCRIPCION_FACTURA)

    filas = _filas_de_pagina(encabezado, items, 1, True)

    assert all("REVISAR" in fila["observaciones"] for fila in filas)


def test_el_presupuesto_no_entra_a_la_importacion(tmp_path, monkeypatch):
    archivo = _crear_pdf(tmp_path / "tacural.pdf")
    monkeypatch.setattr(
        "utiles.importacion_factura_tacural._transcribir",
        lambda imagen, refuerzo=False: TRANSCRIPCION_PRESUPUESTO,
    )
    advertencias = []

    with pytest.raises(ValueError):
        procesar_factura_tacural(str(archivo), advertencias=advertencias)

    assert any("presupuesto" in texto for texto in advertencias)


def test_importa_la_factura_y_devuelve_el_contrato_normalizado(tmp_path, monkeypatch):
    archivo = _crear_pdf(tmp_path / "tacural.pdf")
    monkeypatch.setattr(
        "utiles.importacion_factura_tacural._transcribir",
        lambda imagen, refuerzo=False: TRANSCRIPCION_FACTURA,
    )

    salida = procesar_factura_tacural(str(archivo))

    df = pd.read_excel(salida, dtype=str)
    assert list(df.columns) == COLUMNAS_NORMALIZADAS
    assert len(df) == 7
    assert df.iloc[0]["comprobante"] == "A00011-00420809"
    assert df.iloc[0]["codigo_cliente"] == "27201448420"


def test_el_dispatcher_manda_el_pdf_de_tacural_al_lector_propio(tmp_path, monkeypatch):
    archivo = _crear_pdf(tmp_path / "tacural.pdf")
    monkeypatch.setattr(
        "utiles.importacion_factura_tacural._transcribir",
        lambda imagen, refuerzo=False: TRANSCRIPCION_FACTURA,
    )

    salida = normalizar_archivo_pedidos(str(archivo), metodo="TACURAL")

    assert salida is not None
    assert len(pd.read_excel(salida, dtype=str)) == 7
    assert normalizar_metodo_importacion("tacural") == "TACURAL"


def test_una_pagina_rotada_se_lee_con_la_orientacion_correcta(tmp_path, monkeypatch):
    archivo = _crear_pdf(tmp_path / "tacural_rotada.pdf", apaisada=True)

    def _transcribir(imagen, refuerzo=False):
        # La imagen llega vertical cuando la pagina esta en la orientacion
        # correcta (ancho < alto). En la orientacion equivocada el ancho y el
        # alto vienen invertidos.
        from PIL import Image
        import io

        with Image.open(io.BytesIO(imagen)) as abierta:
            ancho, alto = abierta.size
        if ancho < alto:
            return TRANSCRIPCION_FACTURA
        # Lectura con la pagina de lado: el modelo se confunde y devuelve el
        # encabezado del proveedor como si fuera el cliente.
        return TRANSCRIPCION_FACTURA.replace(
            "RAZON_SOCIAL: LOZANO MARIELA GUADALUPE",
            "RAZON_SOCIAL: TACURAL CHACINADOS TACURAL SRL",
        ).replace("CODIGO_CLIENTE: 5808", "CODIGO_CLIENTE: 001")

    monkeypatch.setattr(
        "utiles.importacion_factura_tacural._transcribir", _transcribir
    )

    salida = procesar_factura_tacural(str(archivo))

    df = pd.read_excel(salida, dtype=str)
    assert df.iloc[0]["detalle_cliente"] == "LOZANO MARIELA GUADALUPE"
    assert df.iloc[0]["codigo_cliente"] == "27201448420"
    assert "REVISAR" not in df.iloc[0]["observaciones"]

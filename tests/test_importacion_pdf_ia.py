# coding=utf-8
from __future__ import annotations

import os
import tempfile
from unittest.mock import patch

import pandas as pd
import pytest

from utiles.importacion_pdf_ia import (
    ConfiguracionPdfIAError,
    _configuracion,
    _extraer_json,
    _normalizar_documento,
)
from utiles.importacion_proveedores_excel import normalizar_archivo_pedidos


def test_extraer_json_acepta_bloque_markdown_y_think():
    data = _extraer_json(
        """<think>analisis interno del modelo</think>
```json
{"documento": {"tipo": "FACTURA"}, "items": []}
```"""
    )
    assert data["documento"]["tipo"] == "FACTURA"


def test_normaliza_factura_estancia_de_oro_al_contrato_rnd():
    data = {
        "documento": {
            "tipo": "FACTURA",
            "numero": "00002-00007165",
            "fecha": "09/09/2026",
            "cliente_codigo": "1956",
            "cliente_nombre": "MARTINEZ CARLA CHAVELY",
            "cuit": "27-36474601-1",
            "domicilio": "VELEZ SARSFIELD 0",
            "localidad": "GARUPA",
            "provincia": "MISIONES",
            "confianza": 0.96,
            "advertencias": [],
        },
        "items": [
            {
                "codigo": "311",
                "descripcion": "Queso Cremoso ESTANCIA DE ORO Horma X Kg",
                "cantidad": 40,
                "bultos": None,
                "kilos": 180.700,
                "confianza": 0.94,
                "advertencias": [],
            }
        ],
    }

    filas = _normalizar_documento(data, 1)

    assert len(filas) == 1
    fila = filas[0]
    assert fila["codigo_cliente"] == "1956"
    assert fila["detalle_cliente"] == "MARTINEZ CARLA CHAVELY"
    assert fila["destino"] == "GARUPA"
    assert fila["comprobante"] == "00002-00007165"
    assert fila["cantidad"] == 40
    assert fila["bultos"] == 40
    assert fila["kilos"] == pytest.approx(180.7)
    assert "Codigo producto: 311" in fila["observaciones"]


def test_baja_confianza_queda_marcada_para_revision():
    data = {
        "documento": {
            "tipo": "NOTA_PEDIDO",
            "numero": "21920",
            "cliente_codigo": "2387",
            "cliente_nombre": "ROSA RODRIGO RAFAELA",
            "localidad": "SAN VICENTE",
            "confianza": 0.70,
            "advertencias": ["sello sobre la tabla"],
        },
        "items": [
            {
                "codigo": "321",
                "descripcion": "Queso Tybo",
                "cantidad": 20,
                "kilos": 82.8,
                "confianza": 0.72,
                "advertencias": [],
            }
        ],
    }

    fila = _normalizar_documento(data, 5)[0]
    assert "REVISAR IA" in fila["observaciones"]
    assert "sello sobre la tabla" in fila["observaciones"]


def test_configuracion_por_defecto_reutiliza_minimax_y_solo_exige_api_key():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ConfiguracionPdfIAError) as exc:
            _configuracion()
    assert "RND_PDF_AI_API_KEY" in str(exc.value)
    assert "MINIMAX_API_KEY" in str(exc.value)


def test_configuracion_reutiliza_minimax_api_key():
    with patch.dict(
        os.environ,
        {"MINIMAX_API_KEY": "secreto-test"},
        clear=True,
    ):
        url, api_key, model, timeout = _configuracion()
    assert url == "https://api.minimax.io/v1/chat/completions"
    assert api_key == "secreto-test"
    assert model == "MiniMax-M3"
    assert timeout == 120


def test_advertencia_string_no_se_parte_en_caracteres_y_faltantes_desmarcables():
    data = {
        "documento": {
            "tipo": "FACTURA",
            "numero": "",
            "cliente_codigo": "",
            "cliente_nombre": "CLIENTE PRUEBA",
            "localidad": "",
            "confianza": 0.92,
            "advertencias": "sello sobre el numero",
        },
        "items": [
            {
                "codigo": "311",
                "descripcion": "Queso Cremoso",
                "cantidad": None,
                "kilos": 12.5,
                "confianza": 0.92,
                "advertencias": [],
            }
        ],
    }

    fila = _normalizar_documento(data, 1)[0]
    assert "sello sobre el numero" in fila["observaciones"]
    assert "REVISAR IA: faltan documento, localidad, cantidad" in fila["observaciones"]


def test_normalizador_general_enruta_pdf_a_ia():
    fila = {
        "codigo_cliente": "1941",
        "detalle_cliente": "CEFERINO RODRIGUEZ SUPERMERCADOS SRL",
        "destino": "SAN VICENTE",
        "comprobante": "00002-00007166",
        "cantidad": 120,
        "producto": "Queso Cremoso",
        "bultos": 120,
        "kilos": 434.3,
        "observaciones": "Origen IA pagina 2",
    }

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        ruta_pdf = tmp.name

    try:
        with patch(
            "utiles.importacion_pdf_ia.extraer_pedidos_pdf_ia",
            return_value=[fila],
        ) as extractor:
            salida = normalizar_archivo_pedidos(
                ruta_pdf,
                metodo="COLUMNAS",
            )
        extractor.assert_called_once()
        df = pd.read_excel(salida)
        assert len(df) == 1
        assert df.iloc[0]["detalle_cliente"] == fila["detalle_cliente"]
        assert df.iloc[0]["destino"] == "SAN VICENTE"
        assert df.iloc[0]["producto"] == "Queso Cremoso"
    finally:
        try:
            os.unlink(ruta_pdf)
        except OSError:
            pass
        if "salida" in locals():
            try:
                os.unlink(salida)
            except OSError:
                pass

# coding=utf-8
from types import SimpleNamespace

import pytest
from peewee import SqliteDatabase


_TEST_DB = SqliteDatabase(":memory:")


@pytest.fixture()
def base_lista_facturas(monkeypatch):
    from modelos.Clientes import Cliente, Localidades, LugarEntrega, RutaReparto
    from modelos.Documentos import (
        DocumentoPedido,
        DocumentoPedidoDetalle,
        DocumentoPedidoHojaRuta,
    )
    from modelos.ModeloBase import db as db_real
    from modelos.Pallet import Pallet, PalletDetalle
    from modelos.Proveedores import Proveedor
    import modelos.Documentos as documentos

    modelos = [
        RutaReparto,
        Localidades,
        Cliente,
        LugarEntrega,
        Proveedor,
        DocumentoPedido,
        DocumentoPedidoDetalle,
        DocumentoPedidoHojaRuta,
        Pallet,
        PalletDetalle,
    ]
    _TEST_DB.bind(modelos)
    _TEST_DB.connect()
    _TEST_DB.create_tables(modelos)
    monkeypatch.setattr(documentos, "asegurar_esquema_documentos", lambda: None)
    try:
        ruta = RutaReparto.create(descripcion="Misiones")
        cliente = Cliente.create(razon_social="Dumo S.A.", ruta_reparto=ruta)
        central = LugarEntrega.create(
            cliente=cliente,
            nombre="Central",
            direccion="Av. Misiones 123",
            ruta_reparto=ruta,
        )
        sucursal = LugarEntrega.create(
            cliente=cliente,
            nombre="Sucursal",
            direccion="Calle Sur 456",
            ruta_reparto=ruta,
        )
        proveedor_a = Proveedor.create(razon_social="Tío Pujio")
        proveedor_b = Proveedor.create(razon_social="Tremblay")
        yield {
            "DocumentoPedido": DocumentoPedido,
            "DocumentoPedidoDetalle": DocumentoPedidoDetalle,
            "DocumentoPedidoHojaRuta": DocumentoPedidoHojaRuta,
            "cliente": cliente,
            "central": central,
            "proveedor_a": proveedor_a,
            "proveedor_b": proveedor_b,
            "sucursal": sucursal,
        }
    finally:
        _TEST_DB.drop_tables(modelos)
        _TEST_DB.close()
        db_real.bind(modelos)


def _hoja(id, cliente_id, lugar_id, comprobante):
    return SimpleNamespace(
        id=id,
        cliente_id=cliente_id,
        lugar_entrega_id=lugar_id,
        nombre_cliente="Dumo S.A.",
        comprobante=comprobante,
    )


def _asociar_documento(base, hoja_id, proveedor, factura, linea):
    documento, _ = base["DocumentoPedido"].get_or_create(
        clave_origen="{}-{}".format(proveedor.id, factura),
        defaults={
            "proveedor": proveedor,
            "cliente": base["cliente"],
            "numero_factura": factura,
        },
    )
    detalle = base["DocumentoPedidoDetalle"].create(
        documento=documento,
        linea_origen=str(linea),
        producto="Queso",
    )
    base["DocumentoPedidoHojaRuta"].create(
        detalle=detalle,
        hoja_ruta=hoja_id,
    )


def test_lista_facturas_agrupa_por_destino_y_proveedor_y_evitas_repetir_factura(
    base_lista_facturas,
):
    from utiles.Reportes import construir_lista_facturas

    base = base_lista_facturas
    hoja = _hoja(101, base["cliente"].id, base["central"].id, "LEG-101")
    _asociar_documento(base, hoja.id, base["proveedor_a"], "0006-129", 1)
    _asociar_documento(base, hoja.id, base["proveedor_a"], "0006-130", 2)
    _asociar_documento(base, hoja.id, base["proveedor_b"], "03-617353", 3)
    # Varias líneas de la misma factura deben conservar un solo número.
    _asociar_documento(base, hoja.id, base["proveedor_a"], "0006-129", 4)

    resultado = construir_lista_facturas([hoja])

    assert resultado == [{
        "cliente": "Dumo S.A.",
        "lugar": "Central",
        "direccion": "Av. Misiones 123",
        "proveedores": [
            {"proveedor": "Tremblay", "facturas": ["03-617353"]},
            {"proveedor": "Tío Pujio", "facturas": ["0006-129", "0006-130"]},
        ],
    }]


def test_lista_facturas_incluye_comprobante_legacy_sin_proveedor(
    base_lista_facturas,
):
    from utiles.Reportes import construir_lista_facturas

    base = base_lista_facturas
    hoja = _hoja(102, base["cliente"].id, base["sucursal"].id, "LEG-102")

    resultado = construir_lista_facturas([hoja])

    assert resultado == [{
        "cliente": "Dumo S.A.",
        "lugar": "Sucursal",
        "direccion": "Calle Sur 456",
        "proveedores": [{
            "proveedor": "Proveedor sin identificar",
            "facturas": ["LEG-102"],
        }],
    }]


def test_pdf_lista_facturas_imprime_datos_de_ruta_y_facturas(monkeypatch):
    import utiles.Reportes as reportes

    pdf = reportes.GeneradorPDFHojaRuta(orientation="L")
    output_original = pdf.output
    capturado = {}

    def capturar_output(path):
        capturado["path"] = path
        capturado["pdf"] = output_original(dest="S")

    monkeypatch.setattr(pdf, "output", capturar_output)
    monkeypatch.setattr(reportes.os, "startfile", lambda path: None, raising=False)
    monkeypatch.setattr(reportes.messagebox, "showinfo", lambda *args: None)

    pdf.generar_lista_facturas(
        entregas=[{
            "numero": 1,
            "cliente": "Dumo S.A.",
            "destino": "Central - Av. Misiones 123",
            "proveedores": [{
                "proveedor": "Tremblay",
                "facturas": ["0006-00124129"],
            }],
            "pallets": ["PLT-20261013-001"],
        }],
        fecha_reporte="12/10/2026",
        nombre_ruta="Misiones",
        responsable="Chofer Demo",
        equipo="Camión Demo",
    )

    assert pdf.w > pdf.h, "la lista debe salir apaisada"
    contenido = pdf.pages[1]
    assert capturado["path"].endswith("ListaFacturas_12-10-2026_Misiones.pdf")
    assert "LISTA DE FACTURAS PARA REPARTO" in contenido
    assert "Chofer Demo" in contenido
    assert "Tremblay" in contenido
    assert "0006-00124129" in contenido
    assert "PLT-20261013-001" in contenido
    assert "Pallet" in contenido


def test_compacta_fusiona_destinos_en_una_fila_por_cliente(
    base_lista_facturas,
):
    from utiles.Reportes import construir_lista_facturas_compacta

    base = base_lista_facturas
    hoja_central = _hoja(101, base["cliente"].id, base["central"].id, "LEG-101")
    hoja_sucursal = _hoja(102, base["cliente"].id, base["sucursal"].id, "LEG-102")
    _asociar_documento(base, hoja_central.id, base["proveedor_a"], "0006-129", 1)
    _asociar_documento(base, hoja_sucursal.id, base["proveedor_a"], "0006-130", 2)

    resultado = construir_lista_facturas_compacta([hoja_central, hoja_sucursal])

    assert len(resultado) == 1
    fila = resultado[0]
    assert fila["numero"] == 1
    assert fila["cliente"] == "Dumo S.A."
    assert "Central - Av. Misiones 123" in fila["destino"]
    assert "Sucursal - Calle Sur 456" in fila["destino"]
    assert fila["proveedores"] == [{
        "proveedor": "Tío Pujio",
        "facturas": ["0006-129", "0006-130"],
    }]
    assert fila["pallets"] == []


def test_compacta_indica_pallet_por_hoja(base_lista_facturas):
    from modelos.Pallet import Pallet, PalletDetalle
    from utiles.Reportes import construir_lista_facturas_compacta

    base = base_lista_facturas
    hoja_central = _hoja(101, base["cliente"].id, base["central"].id, "LEG-101")
    hoja_sucursal = _hoja(102, base["cliente"].id, base["sucursal"].id, "LEG-102")
    _asociar_documento(base, hoja_central.id, base["proveedor_a"], "0006-129", 1)
    _asociar_documento(base, hoja_sucursal.id, base["proveedor_a"], "0006-130", 2)

    pallet = Pallet.create(codigo="PLT-20261013-001", observaciones="t")
    PalletDetalle.create(pallet=pallet.id, hoja_ruta=hoja_central.id,
                         cantidad=1, kg=1, bultos=1)

    resultado = construir_lista_facturas_compacta([hoja_central, hoja_sucursal])

    assert len(resultado) == 1
    assert resultado[0]["pallets"] == ["PLT-20261013-001"]


def test_compacta_numera_en_orden_de_hoja(base_lista_facturas):
    from modelos.Clientes import Cliente
    from utiles.Reportes import construir_lista_facturas_compacta

    base = base_lista_facturas
    otro = Cliente.create(razon_social="Otro S.A.")
    hoja_b = _hoja(202, otro.id, base["central"].id, "LEG-202")
    hoja_a = _hoja(101, base["cliente"].id, base["central"].id, "LEG-101")
    _asociar_documento(base, hoja_b.id, base["proveedor_a"], "F-B", 1)
    _asociar_documento(base, hoja_a.id, base["proveedor_a"], "F-A", 1)

    # El orden lo da el id de hoja (igual que el builder histórico),
    # no el orden de la lista de entrada.
    resultado = construir_lista_facturas_compacta([hoja_b, hoja_a])

    assert [f["numero"] for f in resultado] == [1, 2]
    assert resultado[0]["proveedores"] == [
        {"proveedor": "Tío Pujio", "facturas": ["F-A"]}
    ]
    assert resultado[1]["proveedores"] == [
        {"proveedor": "Tío Pujio", "facturas": ["F-B"]}
    ]


def _pdf_compacto(entregas, monkeypatch):
    import utiles.Reportes as reportes

    pdf = reportes.GeneradorPDFHojaRuta(orientation="L")
    output_original = pdf.output
    capturado = {}

    def capturar_output(path):
        capturado["path"] = path
        capturado["pdf"] = output_original(dest="S")

    monkeypatch.setattr(pdf, "output", capturar_output)
    monkeypatch.setattr(reportes.os, "startfile", lambda path: None, raising=False)
    monkeypatch.setattr(reportes.messagebox, "showinfo", lambda *args: None)

    pdf.generar_lista_facturas(
        entregas=entregas,
        fecha_reporte="13/10/2026",
        nombre_ruta="Posadas",
        responsable="Chofer Demo",
        equipo="Camión Demo",
    )
    return pdf, capturado


def test_pdf_compacto_multi_proveedor_y_sin_pallet(monkeypatch):
    pdf, _capturado = _pdf_compacto(
        [{
            "numero": 1,
            "cliente": "Dumo S.A.",
            "destino": "Central",
            "proveedores": [
                {"proveedor": "Tremblay", "facturas": ["F-T"]},
                {"proveedor": "Tío Pujio", "facturas": ["F-P1", "F-P2"]},
            ],
            "pallets": [],
        }],
        monkeypatch,
    )

    contenido = pdf.pages[1]
    assert "Tremblay" in contenido
    assert "F-T" in contenido
    assert "F-P1" in contenido
    # Sin pallet asignado se indica explícitamente.
    assert "Sin pallet" in contenido


def test_pdf_compacto_pagina_y_repite_cabecera(monkeypatch):
    entregas = [
        {
            "numero": i,
            "cliente": "Cliente {}".format(i),
            "destino": "Destino {}".format(i),
            "proveedores": [{
                "proveedor": "Tío Pujio",
                "facturas": ["N0001-{:08d}".format(i)],
            }],
            "pallets": ["PLT-{:03d}".format(i)],
        }
        for i in range(1, 31)
    ]
    pdf, _capturado = _pdf_compacto(entregas, monkeypatch)

    assert len(pdf.pages) >= 2, "30 filas deben ocupar más de una página"
    for numero_pagina in sorted(pdf.pages):
        assert "Pallet" in pdf.pages[numero_pagina]
    assert "Cliente 30" in pdf.pages[sorted(pdf.pages)[-1]]

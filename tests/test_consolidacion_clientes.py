from utiles.consolidacion_clientes import ResumenConsolidacion


def test_resumen_consolidacion_es_legible():
    resumen = ResumenConsolidacion(
        destino_id=10,
        origenes=[(20, "Cliente Puerto Rico"), (30, "Cliente San Vicente")],
        pedidos=15,
        codigos=2,
        lugares=2,
    )
    texto = resumen.texto()
    assert "Cliente destino: 10" in texto
    assert "Clientes a consolidar: 2" in texto
    assert "Pedidos históricos a reasignar: 15" in texto
    assert "Códigos de proveedor a revisar/mover: 2" in texto
    assert "Lugares de entrega detectados: 2" in texto


def test_resumen_informa_advertencias_de_identidad():
    resumen = ResumenConsolidacion(
        destino_id=1,
        origenes=[(2, "Otro")],
        advertencias=["CUIT distinto"],
    )
    texto = resumen.texto()
    assert "Advertencias:" in texto
    assert "CUIT distinto" in texto

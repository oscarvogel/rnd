from types import SimpleNamespace

from utiles.lugares_entrega import clave_duplicado, resolver_lugar_entrega


def lugar(nombre, localidad="", direccion="", activo=True):
    return SimpleNamespace(
        nombre=nombre,
        direccion=direccion,
        localidad=SimpleNamespace(descripcion=localidad) if localidad else None,
        activo=activo,
    )


def test_unico_lugar_se_autoselecciona_sin_observaciones():
    unico = lugar("Puerto Rico", "Puerto Rico")
    assert resolver_lugar_entrega("", [unico]) is unico


def test_resuelve_por_localidad_en_observaciones():
    puerto_rico = lugar("Sucursal Puerto Rico", "Puerto Rico")
    san_vicente = lugar("Sucursal San Vicente", "San Vicente")
    assert resolver_lugar_entrega(
        "Entregar mercadería en SAN VICENTE",
        [puerto_rico, san_vicente],
    ) is san_vicente


def test_resuelve_ignorando_tildes_y_mayusculas():
    obere = lugar("Oberá", "Oberá")
    apostoles = lugar("Apóstoles", "Apóstoles")
    assert resolver_lugar_entrega("ENTREGA EN OBERA", [obere, apostoles]) is obere


def test_ambiguedad_no_asigna_lugar():
    uno = lugar("Depósito Norte", "Posadas")
    dos = lugar("Sucursal Posadas", "Posadas")
    assert resolver_lugar_entrega("Entregar en Posadas", [uno, dos]) is None


def test_sin_match_queda_pendiente():
    uno = lugar("Puerto Rico", "Puerto Rico")
    dos = lugar("San Vicente", "San Vicente")
    assert resolver_lugar_entrega("Entregar en obra", [uno, dos]) is None


def test_clave_duplicado_prioriza_comprobante():
    clave_a = clave_duplicado(10, "2026-09-09", "Tablas 2x4", "A-001")
    clave_b = clave_duplicado(10, "2026-09-09", "Tablas 2x4", "A-002")
    assert clave_a != clave_b


def test_clave_duplicado_sin_comprobante_mantiene_compatibilidad():
    clave = clave_duplicado(10, "2026-09-09", "Tablas 2x4", "")
    assert clave == ("10", "2026-09-09", "tablas 2x4")

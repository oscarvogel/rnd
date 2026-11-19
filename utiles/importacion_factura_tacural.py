# coding=utf-8
"""Importador de facturas de Tacural (CHACINADOS TACURAL SRL).

El proveedor manda un PDF escaneado, sin capa de texto, con un comprobante por
pagina (facturas electronicas A00011-... y presupuestos B00099-...). Por eso el
flujo no puede ser el de los proveedores que envian Excel:

1. PyMuPDF renderiza cada pagina a PNG.
2. La IA de vision (misma credencial, endpoint y reintentos que la importacion
   PDF de RND) transcribe la pagina a lineas con formato fijo.
3. Este modulo parsea esas lineas de forma determinista y valida cada pagina
   contra los totales impresos: TOTAL KILOGRAMOS y Kg x P.Unit = Importe.

Lo que la IA aporta es la lectura; lo que decide es el codigo. Tres reglas
propias hacen que el resultado no dependa de que la IA "entienda" el documento:

- El tipo de comprobante sale del numero (A00011-... es factura, B00099-... es
  presupuesto), no de lo que la IA diga.
- El peso de cada linea se contrasta contra el TOTAL KILOGRAMOS impreso.
- Una pagina que no cierra queda marcada REVISAR y la vista previa la muestra
  desmarcada para que el operador la valide.

El modulo no graba nada en la base: devuelve un XLSX con las columnas
normalizadas que ya consume la vista previa del importador de pedidos.
"""
from __future__ import annotations

import io
import os
import re
import tempfile
from typing import Callable

import pandas as pd

from utiles.importacion_proveedores_excel import COLUMNAS_NORMALIZADAS, _notificar


NOMBRE_PROVEEDOR = "Tacural"

# El proveedor rotula los datos del cliente con estas etiquetas. La IA las
# devuelve en mayusculas con el mismo nombre de campo.
CAMPOS_ENCABEZADO = (
    "TIPO_DOCUMENTO",
    "NUMERO",
    "FECHA",
    "RAZON_SOCIAL",
    "CODIGO_CLIENTE",
    "DIRECCION",
    "LOCALIDAD",
    "PROVINCIA",
    "CP",
    "TELEFONO",
    "CUIT",
    "CAJA",
    "ZONA",
    "NUMERO_PEDIDO",
    "TOTAL_KILOGRAMOS",
)

# Etiquetas de cada campo de un renglon de productos.
CAMPOS_ITEM = ("codigo", "descripcion", "unid", "kg", "punit", "bonif", "iva", "importe")

# Palabras del encabezado del PROVEEDOR. Si aparecen como razon social, la
# pagina fue leida con la orientacion equivocada o el modelo confundio el
# emisor con el destinatario.
_MARCAS_PROVEEDOR = ("TACURAL", "CHACINADOS", "FACTURA A", "EL SABOR")

# Los comprobantes de Tacural siguen un formato fijo: A00011-######### (factura)
# y B00099-######### (presupuesto). Si el numero leido no lo respeta, la pagina
# no fue leida bien.
_RE_COMPROBANTE = re.compile(r"^[A-Z]\d{4,5}-\d{4,}$")

# Tolerancias de validacion contra los totales impresos.
_TOLERANCIA_KILOS = 0.05
_TOLERANCIA_IMPORTE_RELATIVA = 0.005
_TOLERANCIA_IMPORTE_MINIMA = 1.0

_PROMPT_TACURAL = """Transcribe esta pagina de TACURAL (CHACINADOS TACURAL SRL). Es una factura o un presupuesto.
NO uses markdown ni tablas. Escribe una sola linea por dato, con el formato EXACTO de la izquierda.

TIPO_DOCUMENTO: <FACTURA o PRESUPUESTO>
NUMERO: <numero del comprobante, por ejemplo A00011-00420809>
FECHA: <dd/mm/aaaa>
RAZON_SOCIAL: <razon social del CLIENTE, tal como esta impresa>
CODIGO_CLIENTE: <numero de cliente de TACURAL, por ejemplo 5808>
DIRECCION: <direccion del cliente>
LOCALIDAD: <localidad del cliente>
PROVINCIA: <provincia del cliente>
CP: <codigo postal>
TELEFONO: <telefono del cliente>
CUIT: <cuit del cliente con guiones, por ejemplo 27-20144842-0>
CAJA: <cantidad de cajas que figura en CAJA : Cajas: N>
ZONA: <zona, por ejemplo 58>
NUMERO_PEDIDO: <numero de pedido>
TOTAL_KILOGRAMOS: <total de kilos impreso en la pagina, por ejemplo 53.60>
ITEM: codigo=<codigo de Cod.Art> | descripcion=<texto de Descript.> | unid=<Unid.> | kg=<Kg> | punit=<P.Unit> | bonif=<% Bonif.> | iva=<%Iva> | importe=<Importe>

Reglas de la tabla de productos:
- Una linea ITEM por renglon de la tabla, en el orden en que aparecen.
- Los campos van siempre con su nombre (codigo=, descripcion=, unid=, kg=, punit=, bonif=, iva=, importe=) separados por " | ".
- descripcion es SOLO el texto de Descript., sin el codigo y sin el numero de unidades.
- La columna Unid. a veces esta VACIA: entre el texto del articulo y el precio unitario puede haber UN numero (esa es la columna Kg y entonces unid=-) o DOS numeros (el primero es Unid y el segundo es Kg).
- Los importes y precios usan coma decimal: 8.413,88.
- No inventes: si un dato no se lee o no existe, escribe "-".
- El encabezado del PROVEEDOR (TACURAL / CHACINADOS TACURAL SRL) NO es el cliente: no lo reportes como RAZON_SOCIAL.
- Si la pagina esta rotada, transcribila en su orientacion legible.
- No agregues explicaciones ni comentarios."""


def _texto(valor):
    if valor is None:
        return ""
    return str(valor).strip()


def _numero(valor):
    """Convierte un numero impreso en formato argentino a float.

    "8.413,88" -> 8413.88 ; "15.60" -> 15.6 ; "1.234" -> 1234 (miles).
    """
    texto = _texto(valor).replace(" ", "")
    if not texto or texto == "-":
        return None
    negativo = texto.startswith("-")
    if negativo:
        texto = texto[1:]
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        texto = texto.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")
    try:
        numero = float(texto)
    except ValueError:
        return None
    return -numero if negativo else numero


def _cuit(valor):
    """Devuelve los 11 digitos de un CUIT o "" si no tiene ese formato."""
    digitos = re.sub(r"\D", "", _texto(valor))
    return digitos if len(digitos) == 11 else ""


def _formatear_numero(valor):
    if valor is None:
        return ""
    if float(valor).is_integer():
        return "{:,.0f}".format(valor).replace(",", ".")
    return "{:,.2f}".format(valor).replace(",", "X").replace(".", ",").replace("X", ".")


def _tipo_documento(encabezado):
    """El tipo sale del numero del comprobante, no de lo que diga la IA.

    Tacural numera las facturas A00011-... y los presupuestos B00099-... .
    Ese prefijo es mas confiable que la etiqueta que devuelve el modelo.
    """
    numero = _texto(encabezado.get("NUMERO")).upper()
    if numero.startswith("B"):
        return "PRESUPUESTO"
    if numero.startswith("A"):
        return "FACTURA"
    return _texto(encabezado.get("TIPO_DOCUMENTO")).upper() or "FACTURA"


def _parsear_item(linea):
    """Lee un renglon de productos, con etiquetas o por posicion.

    Con etiquetas ("kg=15.60") cada campo es independiente: si falta uno se
    sabe cual es. Sin etiquetas se cae a la posicion, que es el formato que
    devuelve el modelo cuando no sigue la instruccion.
    """
    cuerpo = linea.split(":", 1)[1].strip() if ":" in linea else linea

    etiquetado = dict(re.findall(r"(\w+)\s*=\s*([^|]*)", cuerpo))
    if etiquetado:
        item = {}
        for campo in CAMPOS_ITEM:
            valor = etiquetado.get(campo, "")
            valor = valor.strip()
            item[campo] = "" if valor in ("", "-") else valor
        item["codigo"] = item["codigo"]
        item["descripcion"] = item["descripcion"]
        item["unid"] = _numero(item["unid"])
        item["kg"] = _numero(item["kg"])
        item["punit"] = _numero(item["punit"])
        item["bonif"] = _numero(item["bonif"])
        item["iva"] = _numero(item["iva"])
        item["importe"] = _numero(item["importe"])
        return item

    partes = [p.strip() for p in re.split(r"[~|]", cuerpo)]
    if len(partes) != 8:
        return None
    codigo, descripcion, unid, kg, punit, bonif, iva, importe = partes
    return {
        "codigo": "" if codigo == "-" else codigo,
        "descripcion": "" if descripcion == "-" else descripcion,
        "unid": _numero(unid),
        "kg": _numero(kg),
        "punit": _numero(punit),
        "bonif": _numero(bonif),
        "iva": _numero(iva),
        "importe": _numero(importe),
    }


def _parsear_transcripcion(texto):
    """Convierte la transcripcion de la IA en (encabezado, items, problemas)."""
    encabezado = {}
    items = []
    problemas = []

    for linea in (_texto(linea) for linea in str(texto or "").splitlines()):
        if not linea:
            continue
        if linea.upper().startswith("ITEM:"):
            item = _parsear_item(linea)
            if item is None:
                problemas.append("un renglon de productos tiene campos de mas")
                continue
            items.append(item)
            continue

        if ":" not in linea:
            continue
        clave, _, valor = linea.partition(":")
        clave = clave.strip().upper().replace(" ", "_")
        if clave in CAMPOS_ENCABEZADO:
            encabezado[clave] = "" if valor.strip() == "-" else valor.strip()

    return encabezado, items, problemas


def _suma_kilos(items):
    total = 0.0
    hay = False
    for item in items:
        if item["kg"] is not None:
            total += item["kg"]
            hay = True
    return total if hay else None


def _suma_unidades(items):
    total = 0.0
    hay = False
    for item in items:
        if item["unid"] is not None:
            total += item["unid"]
            hay = True
    return total if hay else None


def _reajustar_pesos(items, total_kilos):
    """Corrige el caso en que la IA cargo el peso en la columna Unid.

    En varias facturas la columna Unid. viene vacia y el peso real esta en Kg.
    Si el total de Kg no cierra con el total impreso pero el de Unid si, se
    intercambian las dos columnas en vez de descartar la pagina.
    """
    if total_kilos is None or not items:
        return False
    suma_kg = _suma_kilos(items)
    if suma_kg is not None and abs(suma_kg - total_kilos) <= _TOLERANCIA_KILOS:
        return False
    suma_unid = _suma_unidades(items)
    if suma_unid is None or abs(suma_unid - total_kilos) > _TOLERANCIA_KILOS:
        return False
    for item in items:
        item["unid"], item["kg"] = item["kg"], item["unid"]
    return True


def _errores_de_orientacion(encabezado, items):
    """Fallos que indican que la pagina NO fue leida bien.

    Si aparece alguno, RND prueba la pagina con otra orientacion antes de
    dar por buena la lectura.
    """
    errores = []
    numero = _texto(encabezado.get("NUMERO")).upper()
    if not _RE_COMPROBANTE.match(numero):
        errores.append("el numero de comprobante ({}) no tiene el formato de Tacural".format(
            numero or "(vacio)"
        ))
    if not items:
        errores.append("la pagina no tiene renglones de productos")
        return errores

    total_kilos = _numero(encabezado.get("TOTAL_KILOGRAMOS"))
    suma_kg = _suma_kilos(items)
    if total_kilos is None:
        errores.append("no se pudo leer el TOTAL KILOGRAMOS impreso")
    elif suma_kg is None:
        errores.append("las lineas no tienen kilos")
    elif abs(suma_kg - total_kilos) > _TOLERANCIA_KILOS:
        errores.append(
            "la suma de kilos de las lineas ({}) no coincide con el total impreso ({})".format(
                _formatear_numero(suma_kg), _formatear_numero(total_kilos)
            )
        )

    tipo = _tipo_documento(encabezado)
    if tipo != "PRESUPUESTO" and not _cuit(encabezado.get("CUIT")):
        errores.append("no se pudo leer un CUIT valido del cliente")

    razon = _texto(encabezado.get("RAZON_SOCIAL")).upper()
    if not razon:
        errores.append("no se pudo leer la razon social del cliente")
    elif any(marca in razon for marca in _MARCAS_PROVEEDOR):
        errores.append("la razon social leida es el encabezado del proveedor")

    return errores


def _notas_de_pagina(encabezado):
    """Observaciones sobre el documento que no invalidan la lectura.

    Hay facturas de Tacural que traen "Localidad: MISIONES" con
    "Provincia: Misiones": es un dato del proveedor, no un error de lectura.
    """
    notas = []
    localidad = _texto(encabezado.get("LOCALIDAD")).upper()
    provincia = _texto(encabezado.get("PROVINCIA")).upper()
    if localidad and provincia and localidad == provincia:
        notas.append(
            "el comprobante imprime la misma localidad y provincia ({})".format(localidad)
        )
    if not _texto(encabezado.get("CAJA")):
        notas.append("el comprobante no informa la cantidad de cajas")
    return notas


def _errores_de_pagina(encabezado, items):
    """Fallos de contenido que no invalidan la lectura pero hay que revisar."""
    problemas = []
    for item in items:
        if item["kg"] is None or item["punit"] is None or item["importe"] is None:
            continue
        esperado = item["kg"] * item["punit"]
        diferencia = abs(esperado - item["importe"])
        tolerancia = max(
            _TOLERANCIA_IMPORTE_MINIMA,
            item["importe"] * _TOLERANCIA_IMPORTE_RELATIVA,
        )
        if diferencia > tolerancia:
            problemas.append(
                "el renglon {} no cierra: {} kg x {} es distinto del importe {}".format(
                    item["codigo"] or "(sin codigo)",
                    _formatear_numero(item["kg"]),
                    _formatear_numero(item["punit"]),
                    _formatear_numero(item["importe"]),
                )
            )
    return problemas


def _puntuar_pagina(encabezado, items):
    """Puntua la lectura de una pagina para elegir la mejor orientacion."""
    puntaje = 0
    tipo = _tipo_documento(encabezado)

    if items:
        puntaje += 2
    con_codigo = sum(1 for item in items if re.fullmatch(r"\d{4,6}", item["codigo"] or ""))
    con_kilos = sum(1 for item in items if item["kg"] is not None)
    if items:
        puntaje += int(2 * con_codigo / len(items))
        puntaje += int(2 * con_kilos / len(items))

    if _cuit(encabezado.get("CUIT")):
        puntaje += 2
    elif tipo != "PRESUPUESTO":
        puntaje -= 2

    razon = _texto(encabezado.get("RAZON_SOCIAL")).upper()
    if razon:
        puntaje += 2
        if any(marca in razon for marca in _MARCAS_PROVEEDOR):
            puntaje -= 4
    else:
        puntaje -= 1

    codigo_cliente = _texto(encabezado.get("CODIGO_CLIENTE"))
    puntaje += 1 if codigo_cliente.isdigit() else -1

    localidad = _texto(encabezado.get("LOCALIDAD")).upper()
    provincia = _texto(encabezado.get("PROVINCIA")).upper()
    if localidad:
        puntaje += 1
    if localidad and provincia:
        puntaje += 1 if localidad != provincia else -2

    numero = _texto(encabezado.get("NUMERO")).upper()
    if _RE_COMPROBANTE.match(numero):
        puntaje += 3
    else:
        puntaje -= 3

    total_kilos = _numero(encabezado.get("TOTAL_KILOGRAMOS"))
    suma_kg = _suma_kilos(items)
    if total_kilos is not None and suma_kg is not None:
        if abs(suma_kg - total_kilos) <= _TOLERANCIA_KILOS:
            puntaje += 3
        else:
            puntaje -= 2

    return puntaje


def _render_paginas(ruta_pdf):
    """Devuelve [(indice, png_bytes, apaisada)] con cada pagina renderizada."""
    import fitz
    from PIL import Image

    paginas = []
    try:
        documento = fitz.open(str(ruta_pdf))
    except Exception as exc:
        raise ValueError("No se pudo abrir el PDF de Tacural: {}".format(exc))

    try:
        if documento.page_count == 0:
            raise ValueError("El PDF de Tacural no contiene paginas")
        matriz = fitz.Matrix(1.7, 1.7)
        for indice, pagina in enumerate(documento, start=1):
            pix = pagina.get_pixmap(matrix=matriz, alpha=False)
            imagen = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            apaisada = pagina.rect.width > pagina.rect.height
            buffer = io.BytesIO()
            imagen.save(buffer, format="PNG")
            paginas.append((indice, buffer.getvalue(), apaisada))
    finally:
        documento.close()
    return paginas


def _rotar(imagen_bytes, grados):
    """Rota la imagen en memoria (PIL rotate es antihorario)."""
    from PIL import Image

    imagen = Image.open(io.BytesIO(imagen_bytes))
    imagen = imagen.rotate(grados, expand=True)
    buffer = io.BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def _transcribir(imagen_bytes, refuerzo=False):
    from utiles.importacion_pdf_ia import llamar_vision_texto

    prompt = _PROMPT_TACURAL
    if refuerzo:
        # Segundo intento: se recuerda el orden exacto de las columnas, que es
        # lo que la IA corre cuando el documento esta sucio o rotado.
        prompt += (
            "\n\nRecordatorio: la tabla tiene las columnas Cod.Art, Descript., Unid., Kg, "
            "P.Unit, % Bonif., %Iva, Importe, en ese orden. El peso es el numero que "
            "esta bajo Kg y el precio unitario el que esta bajo P.Unit; el importe es "
            "el peso multiplicado por el precio unitario."
        )
    return llamar_vision_texto(imagen_bytes, "image/png", prompt)


def _leer_pagina(indice, imagen_bytes, apaisada, advertencias, intentos=2):
    """Transcribe una pagina y devuelve (encabezado, items, problemas, revisar, notas).

    Las paginas escaneadas de lado se leen con la rotacion correcta: se prueba
    una orientacion y, si la lectura no cierra con los datos impresos, se
    prueba la siguiente.

    La lectura por IA no es determinista: una misma pagina puede leerse con
    una columna corrida en una corrida y bien en la siguiente. Por eso, si
    ninguna orientacion cierra, se reintenta la pagina con la orientacion
    que mejor puntuacion dio: la segunda lectura suele venir limpia.
    """
    from utiles.importacion_pdf_ia import ExtraccionPdfIAError

    if apaisada:
        rotaciones = [90, -90, 180]
    else:
        rotaciones = [None, 180]

    mejor = None
    for intento in range(max(1, intentos)):
        orden = rotaciones
        if intento > 0 and mejor is not None and mejor["rotacion"] is not None:
            # Reintento: primero la orientacion que mejor funciono.
            orden = [mejor["rotacion"]] + [
                rotacion for rotacion in rotaciones if rotacion != mejor["rotacion"]
            ]
        for rotacion in orden:
            imagen = imagen_bytes if rotacion is None else _rotar(imagen_bytes, rotacion)
            try:
                transcripcion = _transcribir(imagen, refuerzo=intento > 0)
            except ExtraccionPdfIAError as exc:
                advertencias.append("Pagina {}: no se pudo leer ({}).".format(indice, exc))
                return {}, [], ["la pagina no se pudo procesar"], True, []

            encabezado, items, problemas = _parsear_transcripcion(transcripcion)
            _reajustar_pesos(items, _numero(encabezado.get("TOTAL_KILOGRAMOS")))
            errores = _errores_de_orientacion(encabezado, items)
            candidato = {
                "encabezado": encabezado,
                "items": items,
                "problemas": problemas,
                "errores": errores,
                "puntaje": _puntuar_pagina(encabezado, items),
                "rotacion": rotacion,
            }
            if mejor is None or candidato["puntaje"] > mejor["puntaje"]:
                mejor = candidato
            if not errores:
                # La lectura es coherente: no hace falta probar otra orientacion.
                break
        if mejor is not None and not mejor["errores"]:
            break

    problemas = list(mejor["problemas"]) + _errores_de_pagina(
        mejor["encabezado"], mejor["items"]
    )
    if mejor["errores"]:
        problemas.extend(mejor["errores"])
    notas = _notas_de_pagina(mejor["encabezado"])
    return (
        mejor["encabezado"],
        mejor["items"],
        problemas,
        bool(problemas),
        notas,
    )


def _filas_de_pagina(encabezado, items, indice, revisar):
    """Arma las filas normalizadas de RND para una pagina de Tacural."""
    tipo = _tipo_documento(encabezado)
    numero = _texto(encabezado.get("NUMERO"))
    cuit = _cuit(encabezado.get("CUIT"))
    codigo_cliente = _texto(encabezado.get("CODIGO_CLIENTE"))
    razon_social = _texto(encabezado.get("RAZON_SOCIAL"))
    localidad = _texto(encabezado.get("LOCALIDAD"))
    caja = _numero(encabezado.get("CAJA"))
    zona = _texto(encabezado.get("ZONA"))
    pedido = _texto(encabezado.get("NUMERO_PEDIDO"))

    # RND resuelve el cliente por CUIT; si el comprobante no lo trae, usa el
    # codigo de cliente del proveedor (CodigoClienteProveedor).
    cliente = cuit or codigo_cliente

    filas = []
    for item in items:
        descripcion = (item["descripcion"] or item["codigo"] or "").strip()
        observaciones = [
            "Cod.Art {}".format(item["codigo"]) if item["codigo"] else "",
            "{} {}".format(tipo, numero).strip(),
            "Pedido {}".format(pedido) if pedido else "",
            "Zona {}".format(zona) if zona else "",
            "Pagina {}".format(indice),
        ]
        if caja is not None:
            observaciones.append("Cajas {}".format(_formatear_numero(caja)))
        if item["bonif"] is not None:
            observaciones.append("Bonif {}".format(_formatear_numero(item["bonif"])))
        if item["iva"] is not None:
            observaciones.append("IVA {}".format(_formatear_numero(item["iva"])))
        if item["importe"] is not None:
            observaciones.append("Importe {}".format(_formatear_numero(item["importe"])))
        if codigo_cliente:
            observaciones.append("Cli {}".format(codigo_cliente))
        if revisar:
            observaciones.append("REVISAR: la pagina no cerraba con los totales")

        filas.append({
            "codigo_cliente": cliente,
            "detalle_cliente": razon_social,
            "destino": localidad,
            "comprobante": numero,
            "cantidad": "" if item["unid"] is None else item["unid"],
            "producto": descripcion[:150],
            "bultos": "" if caja is None else caja,
            "kilos": "" if item["kg"] is None else item["kg"],
            "observaciones": " | ".join(x for x in observaciones if x)[:400],
        })
    return filas


def _guardar_temporal(filas):
    df = pd.DataFrame(filas, columns=COLUMNAS_NORMALIZADAS)
    temporal = tempfile.NamedTemporaryFile(mode="wb", suffix=".xlsx", delete=False)
    temporal.close()
    df.to_excel(temporal.name, index=False, engine="openpyxl")
    return temporal.name


def procesar_factura_tacural(
    archivo_entrada,
    progreso: Callable[[int], None] | None = None,
    advertencias: list | None = None,
):
    """Convierte el PDF de Tacural al contrato de columnas de RND.

    Devuelve la ruta del XLSX normalizado. No graba nada en la base.
    """
    if not archivo_entrada or not os.path.exists(archivo_entrada):
        raise FileNotFoundError(archivo_entrada)
    if os.path.splitext(str(archivo_entrada))[1].lower() != ".pdf":
        raise ValueError("Las facturas de Tacural se importan desde el PDF escaneado")

    if advertencias is None:
        advertencias = []

    paginas = _render_paginas(archivo_entrada)
    total = max(len(paginas), 1)

    filas = []
    documentos = {}
    presupuestos = 0
    _notificar(progreso, 5)

    for posicion, (indice, imagen_bytes, apaisada) in enumerate(paginas):
        _notificar(progreso, 5 + int(posicion / total * 85))
        encabezado, items, problemas, revisar, notas = _leer_pagina(
            indice, imagen_bytes, apaisada, advertencias
        )

        tipo = _tipo_documento(encabezado)
        if tipo == "PRESUPUESTO":
            presupuestos += 1
            advertencias.append(
                "Pagina {}: es un presupuesto ({}), no se importo.".format(indice, encabezado.get("NUMERO") or "")
            )
            continue

        if not items:
            advertencias.append(
                "Pagina {}: no tiene productos reconocibles.".format(indice)
            )
            continue

        for problema in problemas:
            advertencias.append("Pagina {}: {}.".format(indice, problema))
        for nota in notas:
            advertencias.append("Pagina {}: {}.".format(indice, nota))

        filas.extend(_filas_de_pagina(encabezado, items, indice, revisar))
        numero = _texto(encabezado.get("NUMERO"))
        if numero:
            documentos[numero] = documentos.get(numero, 0) + len(items)

    _notificar(progreso, 92)

    if not filas:
        raise ValueError(
            "No se encontraron facturas de Tacural reconocibles en el PDF. "
            "Verifique que el archivo sea el escaneo de Tacural."
        )

    salida = _guardar_temporal(filas)
    _notificar(progreso, 100)

    advertencias.append(
        "Tacural: {} comprobantes, {} lineas importadas.".format(
            len(documentos), len(filas)
        )
    )
    if presupuestos:
        advertencias.append(
            "Tacural: {} presupuestos quedaron afuera de la importacion.".format(presupuestos)
        )
    return salida

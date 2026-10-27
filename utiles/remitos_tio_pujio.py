# coding=utf-8
"""Importacion y cruce de remitos de Tio Pujio.

El proveedor entrega dos reportes distintos:

- **Control de Pedidos**: PED ``N0001-...``, cliente, productos, kilos y totales.
- **Informe de Remitos**: remito ``R0003-...``, cliente, fecha, vencimiento y total.

Este modulo no toca la base de datos. Expone:

- :func:`procesar_informe_remitos` para leer el Informe de Remitos.
- :func:`procesar_control_pedidos_para_cruce` para extraer del Control de
  Pedidos solo lo necesario para el cruce: codigo de cliente, PED y total.
- :func:`cruzar_remitos` para emparejar remitos con pedidos.

El cruce se apoya en el codigo de cliente y, cuando un cliente tiene varios
comprobantes, en el orden por importe. Los importes no son identicos porque el
remito aplica otro coeficiente de IVA/percepcion; por eso se usan para ordenar
y validar, no para exigir igualdad.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
import os
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd


ESTADO_ASIGNADO = "asignado"
ESTADO_AMBIGUO = "ambiguo"
ESTADO_SIN_PEDIDO = "sin_pedido"
ESTADO_YA_TENIA_REMITO = "ya_tenia_remito"

# Coeficientes observados remito/pedido (IVA y percepciones). El remito nunca
# coincide exactamente con el total del pedido, pero el coeficiente es estable.
COEFICIENTES_REMITO_PEDIDO = (1.0, 1.02479, 1.02736, 1.05215)
TOLERANCIA_COEFICIENTE = 0.001

_COLUMNAS_REMITO = ("FECHA", "COMPROBANTE", "CLIENTE", "TOTAL")


@dataclass(frozen=True)
class RemitoImportado:
    """Una fila del Informe de Remitos."""

    numero_remito: str
    codigo_cliente: str
    nombre_cliente: str = ""
    fecha: Optional[date] = None
    vencimiento: Optional[date] = None
    importe_total: Optional[float] = None


@dataclass(frozen=True)
class PedidoCruce:
    """Datos minimos de un PED para cruzarlo con un remito."""

    numero_pedido: str
    codigo_cliente: str
    importe_total: Optional[float]
    fecha: Optional[date] = None
    nombre_cliente: str = ""
    remito_actual: str = ""


@dataclass(frozen=True)
class ResultadoCruce:
    """Resultado del cruce para un remito."""

    remito: RemitoImportado
    pedido: Optional[PedidoCruce] = None
    estado: str = ESTADO_SIN_PEDIDO
    motivo: str = ""
    candidatos: Tuple[PedidoCruce, ...] = ()


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, float) and pd.isna(valor):
        return ""
    return str(valor).strip()


def _numero(valor) -> Optional[float]:
    if valor is None:
        return None
    if isinstance(valor, float) and pd.isna(valor):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto:
        return None
    texto = texto.replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except (TypeError, ValueError):
        return None


def _fecha(valor) -> Optional[date]:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, float) and pd.isna(valor):
        return None
    texto = str(valor).strip()
    for formato in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _codigo_cliente(valor) -> str:
    texto = _texto(valor)
    if re.fullmatch(r"\d+\.0", texto):
        return texto[:-2]
    return texto


def _normalizar_codigo(valor) -> str:
    """Normaliza el codigo para comparar entre reportes.

    Los codigos numericos se comparan sin ceros a la izquierda. Los codigos
    alfanumericos se comparan en mayusculas.
    """

    texto = _codigo_cliente(valor).upper()
    if texto.isdigit():
        return str(int(texto))
    return texto


def _normalizar_remito(valor) -> str:
    """Compara ``R0003-00075264`` y ``0003-00075264`` como el mismo numero."""

    texto = re.sub(r"[^A-Z0-9]", "", _texto(valor).upper())
    if texto.startswith("R") and texto[1:].isdigit():
        texto = texto[1:]
    return texto


def _valor(valores: Sequence, indice: Optional[int]):
    if indice is None or indice < 0 or indice >= len(valores):
        return None
    return valores[indice]


def _importe_abs(valor) -> Optional[float]:
    numero = _numero(valor)
    return abs(numero) if numero is not None else None


def _es_numero_remito(texto: str) -> bool:
    limpio = re.sub(r"\s+", "", _texto(texto).upper())
    return bool(re.match(r"^[A-Z]+\d*-\d+$", limpio))


def es_informe_remitos(df: pd.DataFrame) -> bool:
    """Detecta el Informe de Remitos por su titulo."""

    for indice in range(min(len(df), 40)):
        fila = [_texto(valor).upper() for valor in df.iloc[indice].tolist()]
        if any("INFORME DE REMITOS" in texto for texto in fila):
            return True
    return False


def _ubicar_encabezado_remitos(
    df: pd.DataFrame,
) -> Tuple[Optional[int], Dict[str, int]]:
    for indice in range(min(len(df), 80)):
        fila = [_texto(valor).upper() for valor in df.iloc[indice].tolist()]
        columnas: Dict[str, int] = {}
        for posicion, texto in enumerate(fila):
            if texto in _COLUMNAS_REMITO or texto == "VENCE":
                columnas.setdefault(texto, posicion)
        if all(clave in columnas for clave in _COLUMNAS_REMITO):
            return indice, columnas
    return None, {}


def procesar_informe_remitos(archivo_entrada: str) -> List[RemitoImportado]:
    """Lee el Informe de Remitos y devuelve una fila por remito.

    Ignora cabeceras repetidas, pies de pagina y filas de totales.
    """

    archivo = os.fspath(archivo_entrada)
    if not os.path.exists(archivo):
        raise FileNotFoundError(archivo)

    df = pd.read_excel(archivo, sheet_name=0, header=None)
    if not es_informe_remitos(df):
        raise ValueError("El archivo no es un Informe de Remitos de Tio Pujio")

    fila_encabezado, columnas = _ubicar_encabezado_remitos(df)
    if fila_encabezado is None:
        raise ValueError("No se encontro el encabezado del Informe de Remitos")

    resultados: List[RemitoImportado] = []
    for indice in range(fila_encabezado + 1, len(df)):
        valores = df.iloc[indice].tolist()
        numero = _texto(_valor(valores, columnas["COMPROBANTE"]))
        if not _es_numero_remito(numero):
            continue

        codigo = _codigo_cliente(_valor(valores, columnas["CLIENTE"]))
        nombre = _texto(_valor(valores, columnas["CLIENTE"] + 1))
        if not nombre or re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", nombre):
            nombre = ""

        resultados.append(
            RemitoImportado(
                numero_remito=numero,
                codigo_cliente=codigo,
                nombre_cliente=nombre,
                fecha=_fecha(_valor(valores, columnas.get("FECHA"))),
                vencimiento=_fecha(_valor(valores, columnas.get("VENCE"))),
                importe_total=_numero(_valor(valores, columnas["TOTAL"])),
            )
        )

    if not resultados:
        raise ValueError("El archivo no contiene remitos reconocibles")
    return resultados


def es_control_pedidos(df: pd.DataFrame) -> bool:
    """Detecta el Control de Pedidos de Tio Pujio."""

    tiene_cliente = False
    tiene_ped = False
    for indice in range(min(len(df), 40)):
        fila = [_texto(valor).upper() for valor in df.iloc[indice].tolist()]
        if any("CONTROL DE PEDIDOS" in texto for texto in fila):
            return True
        if "CLIENTE :" in fila:
            tiene_cliente = True
        if "PED" in fila:
            tiene_ped = True
    return tiene_cliente and tiene_ped


def _ubicar_tot_final(df: pd.DataFrame) -> Optional[int]:
    for indice in range(min(len(df), 60)):
        fila = [_texto(valor).upper() for valor in df.iloc[indice].tolist()]
        if "TOT.FINAL" in fila:
            return fila.index("TOT.FINAL")
    return None


def procesar_control_pedidos_para_cruce(archivo_entrada: str) -> List[PedidoCruce]:
    """Extrae del Control de Pedidos: cliente, PED, fecha y total.

    El total se calcula sumando la columna ``Tot.Final`` de las lineas de
    producto del PED. Si no hay lineas, se usa el subtotal o el total que el
    reporte deja en la fila del PED.
    """

    archivo = os.fspath(archivo_entrada)
    if not os.path.exists(archivo):
        raise FileNotFoundError(archivo)

    df = pd.read_excel(archivo, sheet_name=0, header=None)
    if not es_control_pedidos(df):
        raise ValueError("El archivo no es un Control de Pedidos de Tio Pujio")

    col_tot_final = _ubicar_tot_final(df)
    col_kilos: Optional[int] = None
    for indice in range(min(len(df), 60)):
        fila = [_texto(valor).upper() for valor in df.iloc[indice].tolist()]
        if "KILOS" in fila:
            col_kilos = fila.index("KILOS")
            break

    pedidos: List[PedidoCruce] = []
    cliente_actual: Dict[str, str] = {"codigo": "", "nombre": ""}
    actual: Optional[Dict] = None

    def finalizar() -> None:
        nonlocal actual
        if not actual or not actual.get("numero_pedido"):
            actual = None
            return
        total = (
            actual.get("importe_total")
            or actual.get("subtotal")
            or actual.get("total_header")
        )
        pedidos.append(
            PedidoCruce(
                numero_pedido=actual["numero_pedido"],
                codigo_cliente=actual.get("codigo_cliente", ""),
                nombre_cliente=actual.get("nombre_cliente", ""),
                fecha=actual.get("fecha"),
                importe_total=total,
            )
        )
        actual = None

    for indice in range(len(df)):
        valores = df.iloc[indice].tolist()
        celdas = [
            (posicion, _texto(valor))
            for posicion, valor in enumerate(valores)
            if _texto(valor)
        ]
        textos = [texto.upper() for _, texto in celdas]

        if "TOT.FINAL" in textos:
            col_tot_final = next(
                posicion
                for posicion, texto in celdas
                if texto.upper() == "TOT.FINAL"
            )
            if "KILOS" in textos:
                col_kilos = next(
                    posicion
                    for posicion, texto in celdas
                    if texto.upper() == "KILOS"
                )
            continue

        cliente_pos = next(
            (posicion for posicion, texto in celdas if texto.upper() == "CLIENTE :"),
            None,
        )
        if cliente_pos is not None:
            finalizar()
            posteriores = [
                (posicion, texto)
                for posicion, texto in celdas
                if posicion > cliente_pos
            ]
            cliente_actual = {
                "codigo": (
                    _codigo_cliente(posteriores[0][1]) if posteriores else ""
                ),
                "nombre": posteriores[1][1] if len(posteriores) > 1 else "",
            }
            continue

        ped_pos = next(
            (posicion for posicion, texto in celdas if texto.upper() == "PED"),
            None,
        )
        if ped_pos is not None:
            finalizar()
            posteriores = [
                (posicion, texto)
                for posicion, texto in celdas
                if posicion > ped_pos
            ]
            numero = next(
                (
                    texto
                    for _, texto in posteriores
                    if re.match(
                        r"^[A-Z]{1,3}\d{0,4}-\d+$",
                        re.sub(r"\s+", "", texto.upper()),
                    )
                ),
                "",
            )
            fecha = next(
                (_fecha(texto) for _, texto in celdas if _fecha(texto)),
                None,
            )
            total_header = (
                _numero(valores[col_kilos])
                if col_kilos is not None and col_kilos < len(valores)
                else None
            )
            actual = {
                "codigo_cliente": cliente_actual.get("codigo", ""),
                "nombre_cliente": cliente_actual.get("nombre", ""),
                "numero_pedido": numero,
                "fecha": fecha,
                "importe_total": 0.0,
                "subtotal": None,
                "total_header": total_header,
            }
            continue

        if actual is None:
            continue

        if any(
            texto.upper().startswith("SUBTOTALES")
            or texto.upper().startswith("TOTALES")
            for _, texto in celdas
        ):
            if col_tot_final is not None and col_tot_final < len(valores):
                subtotal = _numero(valores[col_tot_final])
                if subtotal is not None:
                    actual["subtotal"] = subtotal
            continue

        if col_tot_final is not None and col_tot_final < len(valores):
            monto = _numero(valores[col_tot_final])
            if monto is not None:
                actual["importe_total"] += monto

    finalizar()

    if not pedidos:
        raise ValueError("El archivo no contiene pedidos reconocibles")
    return pedidos


def _ratio_valido(ratio: float, tolerancia: float) -> bool:
    return any(
        abs(ratio - coeficiente) <= tolerancia
        for coeficiente in COEFICIENTES_REMITO_PEDIDO
    )


def _evaluar_par(
    pedido: PedidoCruce,
    remito: RemitoImportado,
    tolerancia: float,
) -> ResultadoCruce:
    if pedido.remito_actual:
        if _normalizar_remito(pedido.remito_actual) == _normalizar_remito(
            remito.numero_remito
        ):
            return ResultadoCruce(
                remito=remito,
                pedido=pedido,
                estado=ESTADO_ASIGNADO,
                motivo="ya estaba asociado",
            )
        return ResultadoCruce(
            remito=remito,
            pedido=pedido,
            estado=ESTADO_YA_TENIA_REMITO,
            motivo="el pedido ya tiene remito {}".format(pedido.remito_actual),
        )

    total_pedido = _importe_abs(pedido.importe_total)
    total_remito = _importe_abs(remito.importe_total)

    if total_pedido and total_remito:
        ratio = total_remito / total_pedido
        if not _ratio_valido(ratio, tolerancia):
            return ResultadoCruce(
                remito=remito,
                pedido=pedido,
                estado=ESTADO_AMBIGUO,
                motivo="total fuera de rango (ratio {:.5f})".format(ratio),
                candidatos=(pedido,),
            )
        return ResultadoCruce(
            remito=remito,
            pedido=pedido,
            estado=ESTADO_ASIGNADO,
        )

    return ResultadoCruce(
        remito=remito,
        pedido=pedido,
        estado=ESTADO_ASIGNADO,
        motivo="sin importe para validar",
    )


def cruzar_remitos(
    pedidos: Iterable[PedidoCruce],
    remitos: Iterable[RemitoImportado],
    tolerancia: float = TOLERANCIA_COEFICIENTE,
) -> List[ResultadoCruce]:
    """Cruza remitos con pedidos por codigo de cliente.

    Reglas:

    - 1 pedido y 1 remito para el cliente: se asigna directo.
    - N pedidos y N remitos: se ordenan ambos por importe y se emparejan.
    - Cantidades distintas: queda ambiguo para revision manual.
    - Sin pedido para el cliente: queda sin pedido.
    - Un pedido con otro remito ya cargado no se pisa.
    """

    pedidos_por_codigo: Dict[str, List[PedidoCruce]] = defaultdict(list)
    for pedido in pedidos:
        codigo = _normalizar_codigo(pedido.codigo_cliente)
        if codigo:
            pedidos_por_codigo[codigo].append(pedido)

    remitos_por_codigo: Dict[str, List[Tuple[int, RemitoImportado]]] = defaultdict(
        list
    )
    remitos_lista = list(remitos)
    for indice, remito in enumerate(remitos_lista):
        codigo = _normalizar_codigo(remito.codigo_cliente)
        remitos_por_codigo[codigo].append((indice, remito))

    resultados: List[Optional[ResultadoCruce]] = [None] * len(remitos_lista)

    for codigo, remitos_grupo in remitos_por_codigo.items():
        pedidos_grupo = pedidos_por_codigo.get(codigo, [])

        if not codigo:
            for indice, remito in remitos_grupo:
                resultados[indice] = ResultadoCruce(
                    remito=remito,
                    estado=ESTADO_SIN_PEDIDO,
                    motivo="sin codigo de cliente",
                )
            continue

        if not pedidos_grupo:
            for indice, remito in remitos_grupo:
                resultados[indice] = ResultadoCruce(
                    remito=remito,
                    estado=ESTADO_SIN_PEDIDO,
                    motivo="no hay pedido para el cliente",
                )
            continue

        if len(pedidos_grupo) == 1 and len(remitos_grupo) == 1:
            indice, remito = remitos_grupo[0]
            resultados[indice] = _evaluar_par(
                pedidos_grupo[0], remito, tolerancia
            )
            continue

        if len(pedidos_grupo) == len(remitos_grupo):
            importes_pedidos = [_importe_abs(p.importe_total) for p in pedidos_grupo]
            importes_remitos = [
                _importe_abs(r.importe_total) for _, r in remitos_grupo
            ]
            if any(valor is None for valor in importes_pedidos) or any(
                valor is None for valor in importes_remitos
            ):
                for indice, remito in remitos_grupo:
                    resultados[indice] = ResultadoCruce(
                        remito=remito,
                        estado=ESTADO_AMBIGUO,
                        motivo="faltan importes para ordenar",
                        candidatos=tuple(pedidos_grupo),
                    )
                continue

            if len(set(importes_pedidos)) != len(importes_pedidos) or len(
                set(importes_remitos)
            ) != len(importes_remitos):
                for indice, remito in remitos_grupo:
                    resultados[indice] = ResultadoCruce(
                        remito=remito,
                        estado=ESTADO_AMBIGUO,
                        motivo="importes repetidos; no se puede ordenar",
                        candidatos=tuple(pedidos_grupo),
                    )
                continue

            pedidos_ordenados = sorted(
                pedidos_grupo, key=lambda p: _importe_abs(p.importe_total)
            )
            remitos_ordenados = sorted(
                remitos_grupo, key=lambda item: _importe_abs(item[1].importe_total)
            )
            for pedido, (indice, remito) in zip(
                pedidos_ordenados, remitos_ordenados
            ):
                resultados[indice] = _evaluar_par(pedido, remito, tolerancia)
            continue

        motivo = "{} pedido(s) y {} remito(s) para el cliente".format(
            len(pedidos_grupo), len(remitos_grupo)
        )
        for indice, remito in remitos_grupo:
            resultados[indice] = ResultadoCruce(
                remito=remito,
                estado=ESTADO_AMBIGUO,
                motivo=motivo,
                candidatos=tuple(pedidos_grupo),
            )

    return [resultado for resultado in resultados if resultado is not None]


def resumen_cruce(resultados: Iterable[ResultadoCruce]) -> Dict[str, int]:
    resumen: Dict[str, int] = {
        ESTADO_ASIGNADO: 0,
        ESTADO_AMBIGUO: 0,
        ESTADO_SIN_PEDIDO: 0,
        ESTADO_YA_TENIA_REMITO: 0,
        "total": 0,
    }
    for resultado in resultados:
        resumen[resultado.estado] = resumen.get(resultado.estado, 0) + 1
        resumen["total"] += 1
    return resumen


def main(argv: Optional[Sequence[str]] = None) -> int:
    import sys

    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 2:
        print(
            "Uso: python -m utiles.remitos_tio_pujio "
            "<control_pedidos.xls> <informe_remitos.xls>"
        )
        return 2

    pedidos = procesar_control_pedidos_para_cruce(args[0])
    remitos = procesar_informe_remitos(args[1])
    resultados = cruzar_remitos(pedidos, remitos)

    print("Pedidos: {} | Remitos: {}".format(len(pedidos), len(remitos)))
    print("Resumen: {}".format(resumen_cruce(resultados)))
    for resultado in resultados:
        pedido = resultado.pedido.numero_pedido if resultado.pedido else "-"
        print(
            "{} | cliente {} | {} | PED {} | {}".format(
                resultado.remito.numero_remito,
                resultado.remito.codigo_cliente,
                resultado.estado,
                pedido,
                resultado.motivo,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# coding=utf-8
import os
from collections import defaultdict
from decimal import Decimal

from fpdf import FPDF
from tkinter import messagebox

from modelos.ParametrosSistema import ParamSist


def _decimal(valor):
    try:
        return Decimal(str(valor or 0))
    except Exception:
        return Decimal("0")


def _numero(valor):
    valor = _decimal(valor)
    return str(int(valor)) if valor == valor.to_integral() else ("{:.2f}".format(valor)).rstrip("0").rstrip(".")


def _texto_pdf(valor):
    # FPDF clásico trabaja con fuentes core latin-1. Evita que un dato importado
    # rompa toda la hoja por un carácter fuera de esa codificación.
    return str(valor or "").encode("latin-1", "replace").decode("latin-1")


def construir_descargas_pallets(hojas):
    """Construye la vista operativa parada -> pallets -> líneas.

    La fuente es PalletDetalle: no se infieren cantidades desde HojaDeRuta.
    Devuelve [] cuando la hoja todavía no fue paletizada para permitir fallback.
    """
    from modelos.Clientes import LugarEntrega
    from modelos.Pallet import Pallet, PalletDetalle

    hojas = list(hojas)
    if not hojas:
        return []

    por_id = {h.id: h for h in hojas}
    detalles = list(
        PalletDetalle.select(PalletDetalle, Pallet)
        .join(Pallet)
        .where(PalletDetalle.hoja_ruta.in_(list(por_id)))
        .order_by(Pallet.codigo, PalletDetalle.id)
    )
    if not detalles:
        return []

    lugar_ids = {
        int(getattr(h, "lugar_entrega_id", 0) or 0)
        for h in hojas if getattr(h, "lugar_entrega_id", None)
    }
    lugares = {}
    if lugar_ids:
        lugares = {
            l.id: l
            for l in LugarEntrega.select().where(LugarEntrega.id.in_(lugar_ids))
        }

    destinos_pallet = defaultdict(set)
    for d in detalles:
        h = por_id.get(d.hoja_ruta_id)
        if h is not None:
            destinos_pallet[d.pallet_id].add(
                (int(getattr(h, "cliente_id", 0) or 0),
                 int(getattr(h, "lugar_entrega_id", 0) or 0))
            )

    paradas = {}
    orden = []
    for d in detalles:
        h = por_id.get(d.hoja_ruta_id)
        if h is None:
            continue
        clave = (
            int(getattr(h, "cliente_id", 0) or 0),
            int(getattr(h, "lugar_entrega_id", 0) or 0),
        )
        if clave not in paradas:
            lugar = lugares.get(clave[1])
            paradas[clave] = {
                "cliente": getattr(h, "nombre_cliente", "") or (
                    getattr(getattr(h, "cliente", None), "razon_social", "") or "Cliente"
                ),
                "lugar": getattr(lugar, "nombre", "") or "",
                "direccion": getattr(lugar, "direccion", "") or "",
                "pallets": {},
                "bultos": Decimal("0"),
                "kg": Decimal("0"),
            }
            orden.append(clave)

        parada = paradas[clave]
        pallet = parada["pallets"].setdefault(d.pallet_id, {
            "codigo": d.pallet.codigo,
            "parcial": len(destinos_pallet[d.pallet_id]) > 1,
            "lineas": [],
            "bultos": Decimal("0"),
            "kg": Decimal("0"),
        })
        linea = {
            "producto": getattr(h, "producto", "") or "Sin producto",
            "cantidad": _decimal(d.cantidad),
            "kg": _decimal(d.kg),
            "bultos": _decimal(d.bultos),
        }
        pallet["lineas"].append(linea)
        pallet["bultos"] += linea["bultos"]
        pallet["kg"] += linea["kg"]
        parada["bultos"] += linea["bultos"]
        parada["kg"] += linea["kg"]

    resultado = []
    for numero, clave in enumerate(orden, start=1):
        parada = paradas[clave]
        parada["numero"] = numero
        parada["pallets"] = list(parada["pallets"].values())
        resultado.append(parada)
    return resultado


class GeneradorPDFHojaRuta(FPDF):
    def __init__(self, orientation="P", unit="mm", format="A4"):
        super().__init__(orientation, unit, format)
        self.empresa_nombre = ParamSist.ObtenerParametro("NOMBRE_EMPRESA", "Mi Empresa")
        self.empresa_info = ParamSist.ObtenerParametro("INFORMACION_EMPRESA", "Dirección, Teléfono, Email")
        self.set_auto_page_break(auto=True, margin=15)
        self.fecha_reporte = ""
        self.responsable = ""
        self.equipo = ""
        self.nombre_ruta = ""

    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 7, _texto_pdf(self.empresa_nombre), 0, 1, "C")
        self.set_font("Arial", "", 8)
        self.cell(0, 5, _texto_pdf(self.empresa_info), 0, 1, "C")
        self.set_font("Arial", "B", 9)
        self.cell(95, 5, _texto_pdf("Fecha: {}".format(self.fecha_reporte)), 0, 0, "L")
        self.cell(95, 5, _texto_pdf("Ruta: {}".format(self.nombre_ruta)), 0, 1, "R")
        self.cell(95, 5, _texto_pdf("Chofer: {}".format(self.responsable)), 0, 0, "L")
        self.cell(95, 5, _texto_pdf("Camión: {}".format(self.equipo)), 0, 1, "R")
        self.ln(3)

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "I", 8)
        self.cell(0, 8, _texto_pdf("Página {}/{{nb}}".format(self.page_no())), 0, 0, "C")

    def _titulo(self, texto):
        self.set_font("Arial", "B", 15)
        self.cell(0, 9, _texto_pdf(texto), 0, 1, "C")
        self.ln(2)

    def _mapa_recorrido(self, paradas):
        self._titulo("MAPA DE DESCARGA")
        self.set_font("Arial", "B", 8)
        anchos = (15, 68, 72, 25)
        for ancho, titulo in zip(anchos, ("Parada", "Cliente / destino", "Pallets", "Bultos")):
            self.cell(ancho, 7, _texto_pdf(titulo), 1, 0, "C")
        self.ln()
        self.set_font("Arial", "", 8)
        for p in paradas:
            destino = p["cliente"]
            if p["lugar"]:
                destino += " - " + p["lugar"]
            pallets = ", ".join(
                "{}{}".format(x["codigo"], " (P)" if x["parcial"] else "")
                for x in p["pallets"]
            )
            altura = 7
            if len(destino) > 38 or len(pallets) > 42:
                altura = 10
            y = self.get_y()
            x = self.get_x()
            self.cell(anchos[0], altura, str(p["numero"]).zfill(2), 1, 0, "C")
            self.cell(anchos[1], altura, _texto_pdf(destino[:48]), 1, 0, "L")
            self.cell(anchos[2], altura, _texto_pdf(pallets[:55]), 1, 0, "L")
            self.cell(anchos[3], altura, _numero(p["bultos"]), 1, 1, "R")
        self.ln(3)
        self.set_font("Arial", "I", 8)
        self.multi_cell(0, 5, _texto_pdf("(P) = pallet con descarga parcial: contiene mercadería de más de un destino."))

    def _encabezado_parada(self, p, continuacion=False):
        titulo = "PARADA {:02d}{}".format(p["numero"], " - CONTINUACIÓN" if continuacion else "")
        self.set_font("Arial", "B", 14)
        self.cell(0, 8, _texto_pdf(titulo), 1, 1, "L")
        self.set_font("Arial", "B", 12)
        self.multi_cell(0, 7, _texto_pdf(p["cliente"]), 1, "L")
        self.set_font("Arial", "", 10)
        destino = p["lugar"]
        if p["direccion"]:
            destino = "{} - {}".format(destino, p["direccion"]) if destino else p["direccion"]
        if destino:
            self.multi_cell(0, 6, _texto_pdf("Lugar de entrega: " + destino), 1, "L")
        self.set_font("Arial", "B", 10)
        self.cell(0, 7, _texto_pdf("DESCARGAR EN ESTA PARADA: {} pallet(s) · {} bultos".format(
            len(p["pallets"]), _numero(p["bultos"]))), 1, 1, "C")
        self.ln(3)

    def _pallet(self, pallet, parada):
        lineas = pallet["lineas"]
        alto_estimado = 19 + 6 * len(lineas)
        if self.get_y() + alto_estimado > self.h - 18:
            self.add_page()
            self._encabezado_parada(parada, continuacion=True)

        estado = "DESCARGA PARCIAL - RETIRAR SOLO LO INDICADO" if pallet["parcial"] else "DESCARGA COMPLETA"
        self.set_font("Arial", "B", 11)
        self.cell(0, 8, _texto_pdf("{}  |  {}".format(pallet["codigo"], estado)), 1, 1, "L")
        self.set_font("Arial", "B", 8)
        self.cell(100, 6, "Producto", 1, 0, "C")
        self.cell(25, 6, "Cantidad", 1, 0, "C")
        self.cell(25, 6, "Kg", 1, 0, "C")
        self.cell(30, 6, "Bultos", 1, 1, "C")
        self.set_font("Arial", "", 9)
        for linea in lineas:
            self.cell(100, 6, _texto_pdf(linea["producto"][:55]), 1)
            self.cell(25, 6, _numero(linea["cantidad"]), 1, 0, "R")
            self.cell(25, 6, _numero(linea["kg"]), 1, 0, "R")
            self.cell(30, 6, _numero(linea["bultos"]), 1, 1, "R")
        self.set_font("Arial", "B", 9)
        self.cell(150, 6, "TOTAL A RETIRAR DE ESTE PALLET", 1, 0, "R")
        self.cell(30, 6, _numero(pallet["bultos"]), 1, 1, "R")
        self.ln(3)

    def _reporte_operativo(self, paradas):
        self.add_page()
        self._mapa_recorrido(paradas)

        for p in paradas:
            self.add_page()
            self._encabezado_parada(p)
            for pallet in p["pallets"]:
                self._pallet(pallet, p)
            self.set_font("Arial", "B", 11)
            self.cell(0, 8, _texto_pdf("TOTAL PARADA {:02d}: {} BULTOS".format(
                p["numero"], _numero(p["bultos"]))), "T", 1, "R")

        # Resumen al final; sólo abre página si realmente no entra.
        if self.get_y() > self.h - 55:
            self.add_page()
        self.ln(5)
        self.set_font("Arial", "B", 12)
        self.cell(0, 8, "RESUMEN GENERAL DEL VIAJE", "T", 1, "C")
        total_bultos = sum((p["bultos"] for p in paradas), Decimal("0"))
        total_kg = sum((p["kg"] for p in paradas), Decimal("0"))
        pallets = {x["codigo"] for p in paradas for x in p["pallets"]}
        self.set_font("Arial", "B", 10)
        self.cell(0, 6, _texto_pdf("Paradas: {}   ·   Pallets: {}   ·   Bultos: {}   ·   Peso: {} kg".format(
            len(paradas), len(pallets), _numero(total_bultos), _numero(total_kg))), 0, 1, "C")

    def _reporte_legacy(self, hojas):
        """Fallback para hojas antiguas que aún no tienen PalletDetalle."""
        self.add_page()
        self._titulo("HOJA DE REPARTO - SIN PALLETS ASIGNADOS")
        self.set_font("Arial", "", 9)
        self.multi_cell(0, 6, _texto_pdf(
            "Esta hoja no tiene composición de pallets registrada. Se muestra el detalle por cliente para compatibilidad."
        ))
        grupos = defaultdict(list)
        for h in hojas:
            grupos[getattr(h, "nombre_cliente", "") or "Cliente"].append(h)
        for cliente, pedidos in grupos.items():
            if self.get_y() > self.h - 45:
                self.add_page()
            self.set_font("Arial", "B", 11)
            self.cell(0, 7, _texto_pdf(cliente), 1, 1, "L")
            self.set_font("Arial", "", 9)
            for h in pedidos:
                self.cell(125, 6, _texto_pdf(getattr(h, "producto", "")[:65]), 1)
                self.cell(25, 6, _numero(getattr(h, "cantidad", 0)), 1, 0, "R")
                self.cell(30, 6, _numero(getattr(h, "cantidad_bultos", 0)), 1, 1, "R")
            self.ln(3)

    def generar_reporte(self, hoja_ruta_query, fecha_reporte, nombre_ruta, responsable, equipo):
        self.fecha_reporte = str(fecha_reporte)
        self.nombre_ruta = str(nombre_ruta)
        self.responsable = str(responsable)
        self.equipo = str(equipo)

        hojas = list(hoja_ruta_query)
        if not hojas:
            messagebox.showinfo("Sin datos", "No hay datos para generar el reporte.")
            return

        paradas = construir_descargas_pallets(hojas)
        self.alias_nb_pages()
        if paradas:
            self._reporte_operativo(paradas)
        else:
            self._reporte_legacy(hojas)

        try:
            output_dir = "documentacion"
            os.makedirs(output_dir, exist_ok=True)
            str_fecha = str(fecha_reporte).replace("/", "-")
            str_ruta = str(nombre_ruta)
            nombre_archivo = "HojaRuta_{}_{}.pdf".format(str_fecha, str_ruta)
            ruta_salida = os.path.join(output_dir, nombre_archivo)
            self.output(ruta_salida)
            messagebox.showinfo("Éxito", "PDF generado en: {}".format(ruta_salida))
            os.startfile(ruta_salida)
        except Exception as e:
            messagebox.showerror("Error", "No se pudo guardar el PDF: {}".format(e))

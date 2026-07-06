import os
from collections import defaultdict
from fpdf import FPDF
from tkinter import messagebox

from modelos.ParametrosSistema import ParamSist

class GeneradorPDFHojaRuta(FPDF):
    def __init__(self, orientation='P', unit='mm', format='A4'):
        super().__init__(orientation, unit, format)
        self.empresa_nombre = ParamSist.ObtenerParametro("NOMBRE_EMPRESA", "Mi Empresa")
        self.empresa_info = ParamSist.ObtenerParametro("INFORMACION_EMPRESA", "Dirección, Teléfono, Email")
        self.set_auto_page_break(auto=True, margin=15)
        # Valores por defecto para el encabezado
        self.fecha_reporte = ""
        self.responsable = ""
        self.equipo = ""

    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, self.empresa_nombre, 0, 1, 'C')
        self.set_font('Arial', '', 10)
        self.cell(0, 8, self.empresa_info, 0, 1, 'C')
        
        # Nueva información en el encabezado
        self.set_font('Arial', 'B', 10)
        self.cell(0, 6, f"Fecha de Reparto: {self.fecha_reporte}", 0, 1, 'L')
        self.cell(0, 6, f"Responsable: {self.responsable}", 0, 1, 'L')
        self.cell(0, 6, f"Equipo: {self.equipo}", 0, 1, 'L')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', 0, 0, 'C')

    def generar_reporte(self, hoja_ruta_query, fecha_reporte, nombre_ruta, responsable, equipo):
        # Guardar datos para que el encabezado los use
        self.fecha_reporte = str(fecha_reporte)
        self.responsable = str(responsable)
        self.equipo = str(equipo)

        if not hoja_ruta_query.exists():
            messagebox.showinfo("Sin datos", "No hay datos para generar el reporte.")
            return

        pedidos_por_cliente = defaultdict(list)
        for pedido in hoja_ruta_query:
            nombre_cliente = pedido.cliente.razon_social if hasattr(pedido, 'cliente') and hasattr(pedido.cliente, 'razon_social') else "Cliente General"
            observaciones = getattr(pedido, 'observaciones', "")
            nombre_cliente += f" ({observaciones})" if observaciones else ""
            pedidos_por_cliente[nombre_cliente].append(pedido)

        self.alias_nb_pages()
        self.add_page()

        # --- INICIALIZAR TOTALES GENERALES ---
        gran_total_cantidad = 0
        gran_total_kg = 0
        gran_total_bultos = 0

        for cliente, pedidos in sorted(pedidos_por_cliente.items()):
            self.set_font('Arial', 'B', 12)
            self.cell(0, 10, f'Cliente: {cliente}', 0, 1, 'L')
            
            self.set_font('Arial', 'B', 10)
            self.cell(95, 7, 'Producto', 1, 0, 'C')
            self.cell(25, 7, 'Cantidad', 1, 0, 'C')
            self.cell(30, 7, 'Peso (Kg)', 1, 0, 'C')
            self.cell(25, 7, 'Bultos', 1, 1, 'C')

            # Inicializar totales por cliente
            total_cantidad_cliente = 0
            total_kg_cliente = 0
            total_bultos_cliente = 0

            self.set_font('Arial', '', 10)
            for pedido in pedidos:
                try:
                    cantidad = float(pedido.cantidad if hasattr(pedido, 'cantidad') and pedido.cantidad is not None else 0)
                except (ValueError, TypeError):
                    cantidad = 0
                try:
                    peso = float(pedido.kg if hasattr(pedido, 'kg') and pedido.kg is not None else 0)
                except (ValueError, TypeError):
                    peso = 0
                try:
                    bultos = int(pedido.cantidad_bultos if hasattr(pedido, 'cantidad_bultos') and pedido.cantidad_bultos is not None else 0)
                except (ValueError, TypeError):
                    bultos = 0

                producto = str(pedido.producto if hasattr(pedido, 'producto') else "N/A")

                self.cell(95, 6, producto, 1)
                self.cell(25, 6, str(cantidad), 1, 0, 'R')
                self.cell(30, 6, f'{peso:.2f}', 1, 0, 'R')
                self.cell(25, 6, str(bultos), 1, 1, 'R')

                # Acumular totales de cliente
                total_cantidad_cliente += cantidad
                total_kg_cliente += peso
                total_bultos_cliente += bultos

            self.set_font('Arial', 'B', 10)
            self.cell(120, 8, 'TOTALES POR CLIENTE:', 1, 0, 'R')
            self.cell(30, 8, f'{total_kg_cliente:.2f} Kg', 1, 0, 'R')
            self.cell(25, 8, f'{total_bultos_cliente}', 1, 1, 'R')
            self.ln(10)

            # --- ACUMULAR TOTALES GENERALES ---
            gran_total_cantidad += total_cantidad_cliente
            gran_total_kg += total_kg_cliente
            gran_total_bultos += total_bultos_cliente

        # --- SECCIÓN DE TOTALES GENERALES ---
        self.ln(5)
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'TOTALES GENERALES DE LA RUTA', 'T', 1, 'C')
        self.ln(5)

        self.set_font('Arial', 'B', 11)
        self.cell(95, 8, 'Cantidad Total de Productos:', 0, 0, 'R')
        self.cell(25, 8, str(int(gran_total_cantidad)), 0, 1, 'L')
        self.cell(95, 8, 'Cantidad Total de Bultos:', 0, 0, 'R')
        self.cell(25, 8, str(gran_total_bultos), 0, 1, 'L')
        self.cell(95, 8, 'Peso Total (Kg):', 0, 0, 'R')
        self.cell(25, 8, f'{gran_total_kg:.2f}', 0, 1, 'L')

        try:
            output_dir = "documentacion"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            str_fecha = str(fecha_reporte).replace('/', '-')
            str_ruta = str(nombre_ruta)
            nombre_archivo = f"HojaRuta_{str_fecha}_{str_ruta}.pdf"
            ruta_salida = os.path.join(output_dir, nombre_archivo)
            
            self.output(ruta_salida)
            messagebox.showinfo("Éxito", f"PDF generado en: {ruta_salida}")
            os.startfile(ruta_salida)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el PDF: {e}")
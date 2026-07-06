import pdfplumber
import pandas as pd
import re
import tempfile
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

def procesar_pagina(page):
    """Procesa una sola página del PDF para extraer datos."""
    data = []
    current_cliente = None
    product_pattern = re.compile(r'^\d{1,4}\s+[A-Z]')
    
    text = page.extract_text()
    if not text:
        return data

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or "DESPACHO DE MERCADERIA POR ZONA" in line or \
           "Todas..." in line or "Pedido Detalle" in line or "Nro." in line:
            continue

        if line.endswith("MISIONES"):
            parts = line.replace("MISIONES", "").strip().split()
            if len(parts) < 2:
                continue
            try:
                palets = int(parts[-1])
                client_name = ' '.join(parts[:-1]).strip()
                current_cliente = client_name
                continue
            except ValueError:
                pass

        if product_pattern.match(line):
            words = line.split()
            if len(words) < 8:
                continue
            try:
                promedio = words[-1]
                kilos = words[-2]
                fecha = words[-3]
                nro_elab = words[-4]
                palet = words[-5]
                bultos = words[-6]
                pedido = words[0]
                detalle_str = ' '.join(words[1:-6])

                def clean_number(s):
                    if '.' in s:
                        parts_dot = s.split('.')
                        if len(parts_dot) > 2:
                            return ''.join(parts_dot[:-1]) + '.' + parts_dot[-1]
                        else:
                            return s.replace('.', '')
                    return s

                kilos_clean = float(clean_number(kilos)) / 1000
                promedio_clean = float(clean_number(promedio)) / 1000

                data.append({
                    'Cliente': current_cliente,
                    'Pedido': pedido,
                    'Producto': detalle_str,
                    'Bultos': bultos,
                    'Palet': palet,
                    'Kilos': round(kilos_clean, 3),
                    'Promedio': round(promedio_clean, 3),
                    'Fecha Elaboración': fecha
                })
            except Exception as e:
                print(f"⚠️ Error procesando línea producto: {line} → {e}")
                continue
    return data

def procesar_pdf_despacho(archivo_pdf: str) -> str:
    """
    Procesa un PDF de despacho de mercadería y genera un archivo Excel limpio en una carpeta temporal,
    con un nombre aleatorio para evitar colisiones.
    """
    all_data = []

    try:
        with pdfplumber.open(archivo_pdf) as pdf:
            with ThreadPoolExecutor() as executor:
                future_to_page = {executor.submit(procesar_pagina, page): page for page in pdf.pages}
                for future in as_completed(future_to_page):
                    all_data.extend(future.result())
    except Exception as e:
        raise RuntimeError(f"Error al leer el archivo PDF: {e}")

    df = pd.DataFrame(all_data)
    if df.empty:
        print("No se extrajeron datos del PDF.")
        return None

    df['Bultos'] = pd.to_numeric(df['Bultos'], errors='coerce')
    df['Palet'] = pd.to_numeric(df['Palet'], errors='coerce')
    df['Kilos'] = pd.to_numeric(df['Kilos'], errors='coerce')
    df['Promedio'] = pd.to_numeric(df['Promedio'], errors='coerce')

    columns = ['Cliente', 'Pedido', 'Producto', 'Bultos', 'Palet', 'Kilos', 'Promedio', 'Fecha Elaboración']
    df = df[columns]

    nombre_aleatorio = f"despacho_{uuid.uuid4().hex[:8]}.xlsx"
    ruta_temp = tempfile.gettempdir()
    ruta_excel = os.path.join(ruta_temp, nombre_aleatorio)

    df.to_excel(ruta_excel, index=False)

    print(f"✅ Archivo Excel generado: {ruta_excel}")
    return ruta_excel


if __name__ == "__main__":
    archivo_pdf = "o:/rnd/documentacion/MISIONES 13-8-25.PDF"  # Reemplazar con la ruta real del PDF
    ruta_excel = procesar_pdf_despacho(archivo_pdf)
    print(f"Archivo Excel creado en: {ruta_excel}")
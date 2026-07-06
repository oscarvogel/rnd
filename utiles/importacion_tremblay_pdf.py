import fitz  # PyMuPDF
import pandas as pd
import re
import tempfile
import os
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed


def procesar_pagina(page):
    """Procesa una sola página del PDF para extraer datos usando PyMuPDF."""
    data = []
    current_cliente = None
    product_pattern = re.compile(r'^\d{1,4}\s+[A-Z]')

    # Extrae el texto de la página como texto plano, preservando el orden
    text = page.get_text("text", sort=True)  # 'sort=True' ayuda a mantener el orden visual
    if not text:
        return data

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or "DESPACHO DE MERCADERIA POR ZONA" in line or \
           "Todas..." in line or "Pedido Detalle" in line or "Nro." in line:
            continue

        # Detectar cliente: línea que termina con "MISIONES"
        if line.endswith("MISIONES"):
            base_line = line.replace("MISIONES", "").strip()
            parts = base_line.split()
            if len(parts) < 2:
                continue
            try:
                # El último elemento debería ser el número de palets
                palets = int(parts[-1])
                client_name = ' '.join(parts[:-1]).strip()
                current_cliente = client_name
            except ValueError:
                pass  # No es un cliente válido, continuar
            continue

        # Detectar línea de producto: empieza con número seguido de texto
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
                    """Limpia números con puntos como separadores de miles."""
                    if '.' in s:
                        parts = s.split('.')
                        if len(parts) > 2:
                            # Más de un punto: asumimos que el último es decimal
                            integer_part = ''.join(parts[:-1])
                            decimal_part = parts[-1]
                            return f"{integer_part}.{decimal_part}"
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
    Procesa un PDF de despacho de mercadería usando PyMuPDF y genera un archivo Excel limpio
    en una carpeta temporal con nombre aleatorio.
    """
    all_data = []

    try:
        doc = fitz.open(archivo_pdf)
        with ThreadPoolExecutor() as executor:
            futures = [executor.submit(procesar_pagina, page) for page in doc]
            for future in as_completed(futures):
                all_data.extend(future.result())
        doc.close()
    except Exception as e:
        raise RuntimeError(f"Error al leer el archivo PDF con PyMuPDF: {e}")

    df = pd.DataFrame(all_data)
    if df.empty:
        print("No se extrajeron datos del PDF.")
        return None

    # Convertir columnas numéricas
    df['Bultos'] = pd.to_numeric(df['Bultos'], errors='coerce')
    df['Palet'] = pd.to_numeric(df['Palet'], errors='coerce')
    df['Kilos'] = pd.to_numeric(df['Kilos'], errors='coerce')
    df['Promedio'] = pd.to_numeric(df['Promedio'], errors='coerce')

    # Reordenar columnas
    columns = ['Cliente', 'Pedido', 'Producto', 'Bultos', 'Palet', 'Kilos', 'Promedio', 'Fecha Elaboración']
    df = df[columns]

    # Generar nombre aleatorio para el archivo Excel
    nombre_aleatorio = f"despacho_{uuid.uuid4().hex[:8]}.xlsx"
    ruta_temp = tempfile.gettempdir()
    ruta_excel = os.path.join(ruta_temp, nombre_aleatorio)

    # Guardar en Excel
    df.to_excel(ruta_excel, index=False)

    print(f"✅ Archivo Excel generado: {ruta_excel}")
    return ruta_excel


if __name__ == "__main__":
    archivo_pdf = r"o:/rnd/documentacion/MISIONES 13-8-25.PDF"  # Cambia si es necesario
    ruta_excel = procesar_pdf_despacho(archivo_pdf)
    if ruta_excel:
        print(f"Archivo Excel creado en: {ruta_excel}")
    else:
        print("No se generó el archivo Excel.")
import pandas as pd
import tempfile
import os

def procesar_archivo_tremblay(archivo_entrada):
    """
    Procesa un archivo .xls de Tremblay, extrayendo pedido, cliente, destino,
    cantidad, producto, bultos, palet nro. y kilos.
    
    Args:
        archivo_entrada (str): Ruta del archivo de entrada (.xls)
    
    Returns:
        str: Ruta del archivo CSV temporal generado.
    """
    # Leer el archivo Excel sin encabezados (formato irregular)
    try:
        df = pd.read_excel(archivo_entrada, sheet_name=0, header=None)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo {archivo_entrada}: {e}")

    # Inicializar variables
    pedido_actual = None
    cliente_actual = None
    destino_actual = None
    resultado = []

    # Recorrer cada fila
    for index, row in df.iterrows():
        # Convertir fila a lista, reemplazando NaN por cadena vacía
        row_clean = [cell if pd.notna(cell) else '' for cell in row]

        # Saltar filas completamente vacías
        if all(cell == '' for cell in row_clean):
            continue

        # Detectar encabezado de tabla: contiene "Pedido", "Detalle", etc.
        if "Pedido" in str(row_clean[0]) and "Detalle" in str(row_clean[1]):
            continue  # Saltar fila de encabezado

        # Detectar nueva cabecera de pedido: columna A tiene número o texto (no vacío ni '|')
        if row_clean[0] not in ['', '|'] and not str(row_clean[0]).strip().startswith('||'):
            # Intentar extraer pedido (columna A)
            val_pedido = row_clean[0]
            if val_pedido != '':
                try:
                    pedido_actual = int(val_pedido)
                except (ValueError, TypeError):
                    pedido_actual = str(val_pedido).strip()

            # Cliente (columna B)
            cliente_actual = str(row_clean[1]).strip()

            # Destino: puede estar en C (índice 2) o E (índice 4)
            destino_actual = str(row_clean[4]).strip() if row_clean[4] else str(row_clean[2]).strip()

        # Detectar línea de producto: columna F (índice 5) tiene cantidad, columna G (6) tiene producto
        cantidad = row_clean[5]
        producto = row_clean[6]

        if pd.notna(cantidad) and pd.notna(producto) and str(cantidad).strip() != '' and str(producto).strip() != '':
            resultado.append({
                'pedido': pedido_actual,
                'detalle (cliente)': cliente_actual,
                'destino': destino_actual,
                'cantidad': cantidad,
                'detalle del producto': producto,
                'bultos': row_clean[7] if pd.notna(row_clean[7]) else '',
                'palet nro.': row_clean[8] if pd.notna(row_clean[8]) else '',
                'kilos': row_clean[10] if pd.notna(row_clean[10]) else ''  # Columna K
            })

    # Crear DataFrame final
    df_final = pd.DataFrame(resultado)

    # Eliminar filas completamente vacías
    df_final.dropna(how='all', inplace=True)

    # Crear archivo temporal
    archivo_temporal = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8', newline='')
    df_final.to_csv(archivo_temporal.name, index=False)
    archivo_temporal.close()

    return archivo_temporal.name  # Devuelve la ruta del archivo temporal

def procesar_archivo_tremblay_excel(archivo_entrada):
    """
    Procesa un archivo .xls de Tremblay y genera un archivo Excel limpio con la estructura deseada.

    Args:
        archivo_entrada (str): Ruta del archivo de entrada (.xls)

    Returns:
        str: Ruta del archivo Excel temporal generado.
    """
    # Leer el archivo Excel sin encabezados
    try:
        df = pd.read_excel(archivo_entrada, sheet_name=0, header=None)
    except Exception as e:
        raise ValueError(f"No se pudo leer el archivo: {e}")

    # Inicializar variables
    pedido_actual = None
    cliente_actual = None
    destino_actual = None
    resultado = []

    # Recorrer cada fila
    for index, row in df.iterrows():
        row_clean = [cell if pd.notna(cell) else '' for cell in row]

        # Saltar filas completamente vacías
        if all(cell == '' for cell in row_clean):
            continue

        # Detectar encabezado de tabla (saltar)
        if "Pedido" in str(row_clean[0]) and "Detalle" in str(row_clean[1]):
            continue

        # Detectar nueva cabecera de pedido: columna A tiene pedido
        if row_clean[0] not in ['', '|'] and not str(row_clean[0]).startswith('||'):
            try:
                pedido_actual = int(row_clean[0])
            except (ValueError, TypeError):
                pedido_actual = str(row_clean[0]).strip()

            cliente_actual = str(row_clean[1]).strip()
            # Destino: puede estar en columna C (índice 2) o E (índice 4)
            destino_actual = str(row_clean[4]).strip() if row_clean[4] else ''
            destino_actual += ' ' + str(row_clean[2]).strip() if row_clean[2] else ''

        # Detectar línea de producto: columna F (índice 5) = cantidad, G (6) = producto
        cantidad = row_clean[5]
        producto = row_clean[6]

        if pd.notna(cantidad) and pd.notna(producto) and str(cantidad).strip() != '' and str(producto).strip() != '':
            resultado.append({
                'codigo_cliente': pedido_actual,
                'detalle_cliente': cliente_actual,
                'destino': destino_actual,
                'cantidad': cantidad,
                'producto': producto,
                'bultos': row_clean[8] if pd.notna(row_clean[8]) else '',
                'palet': row_clean[9] if pd.notna(row_clean[9]) else '',
                'kilos': row_clean[11] if pd.notna(row_clean[11]) else '',  # Columna K
                'elaboracion': row_clean[10] if pd.notna(row_clean[10]) else '',
                'observaciones': destino_actual
            })

    # Crear DataFrame final
    df_final = pd.DataFrame(resultado)

    # Limpiar filas completamente vacías
    df_final.dropna(how='all', inplace=True)

    # Crear archivo temporal con extensión .xlsx
    archivo_temporal = tempfile.NamedTemporaryFile(mode='wb', suffix='.xlsx', delete=False)
    archivo_temporal.close()  # Cerrar para que openpyxl pueda escribir

    # Guardar en Excel
    df_final.to_excel(archivo_temporal.name, index=False, engine='openpyxl')

    return archivo_temporal.name  # Devuelve la ruta del archivo temporal

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python -m utiles.importacion_tremblay_excel <archivo.xls>")
        sys.exit(1)
    archivo_temporal = procesar_archivo_tremblay_excel(sys.argv[1])
    print(f"Archivo procesado: {archivo_temporal}")
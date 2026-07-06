import pandas as pd

# Ruta del archivo
file_path = 'informe_pedido.xls'

# Lista para almacenar los datos
data = []

# Variables de contexto
current_cliente = None
current_fecha = None
current_pedido = None
current_lugar = None
desp_index = None  # Índice de DESP.
kg_index = None    # Índice de KG

# Leer el archivo como texto
with open(file_path, 'r', encoding='latin1') as f:
    lines = f.readlines()

for line_num, line in enumerate(lines):
    line = line.strip()
    if not line or not line.startswith('|'):
        continue

    # Dividir manteniendo los vacíos
    raw_cols = [col.strip() for col in line.split('|')]
    # Ejemplo: ['', '100', 'CREMOSO...', '', '', '', '', '100', '100', '0', '396,48', ...]

    # === Línea de encabezado de cliente
    if len(raw_cols) > 1 and raw_cols[1] == 'CODIGO' and 'CLIENTE' in raw_cols[2]:
        continue

    # === Línea de datos de cliente: | 200549|STELTER...|F|05/08/2025|000201660778|
    if len(raw_cols) > 5 and raw_cols[1].isdigit() and 'CLIENTE' not in raw_cols[2]:
        try:
            current_cliente = raw_cols[2]
            current_lugar = raw_cols[3] if len(raw_cols) > 3 else ""
            current_fecha = raw_cols[4] if len(raw_cols) > 4 else ""
            current_pedido = raw_cols[5] if len(raw_cols) > 5 else ""
        except:
            pass

    # === Encabezado de productos: buscar por contenido
    if len(raw_cols) > 8 and raw_cols[1] == 'CODIGO' and 'DETALLE' in raw_cols[2]:
        try:
            desp_index = raw_cols.index('DESP.')
            kg_index = raw_cols.index('KG')
        except ValueError as e:
            print(f"Línea {line_num}: No se encontró DESP. o KG en encabezado -> {e}")
        continue

    # === Línea de producto: tiene código en raw_cols[1] y es numérico
    if len(raw_cols) > 8 and len(raw_cols) > max(desp_index or 0, kg_index or 0):
        if raw_cols[1].isdigit():  # Es un producto
            try:
                producto_codigo = raw_cols[1]
                producto_descripcion = raw_cols[2]

                unidades_str = raw_cols[desp_index] if desp_index < len(raw_cols) else "0"
                kg_str = raw_cols[kg_index] if kg_index < len(raw_cols) else "0"

                unidades = float(unidades_str.replace(',', '.')) if unidades_str else 0.0
                kg = float(kg_str.replace(',', '.')) if kg_str else 0.0

                # Solo agregar si hay contexto
                if current_cliente and current_pedido:
                    data.append({
                        'TipoComprobante': 'FV',
                        'Fecha': current_fecha,
                        'Cliente': current_cliente,
                        'Comprobante': current_pedido,
                        'Producto_Codigo': producto_codigo,
                        'Producto_Descripcion': producto_descripcion,
                        'Undades': unidades,
                        'Kg': kg,
                        'ciudad': current_lugar,
                        'Cantidad_Bultos': unidades
                    })
            except Exception as e:
                print(f"Error procesando producto (línea {line_num}): {e}")
                continue

# Crear DataFrame
if data:
    df_final = pd.DataFrame(data)
    # Convertir Fecha
    if 'Fecha' in df_final.columns:
        df_final['Fecha'] = pd.to_datetime(df_final['Fecha'], format='%d/%m/%Y', errors='coerce')
        df_final['Fecha'] = df_final['Fecha'].dt.strftime('%Y-%m-%d')
    # Guardar
    df_final.to_excel('pedido_transformado.xlsx', index=False)
    print(f"✅ Listo: {len(data)} productos exportados a 'pedido_transformado.xlsx'")
else:
    print("❌ ERROR: No se encontraron productos. Imprimiendo primeras líneas del archivo para diagnóstico:")
    with open(file_path, 'r', encoding='latin1') as f:
        for i, l in enumerate(f):
            if i < 10:
                print(f"{i}: {repr(l.strip())}")
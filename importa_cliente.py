import csv
from peewee import fn

from modelos.Clientes import Cliente, Localidades, RutaReparto

# Asumiendo que ya tienes la conexión a la base de datos configurada
# y que los modelos están correctamente definidos como en tu mensaje

def importar_clientes_desde_csv(ruta_csv):
    with open(ruta_csv, 'r', encoding='latin1', newline='') as file:
        # Usar el delimitador correcto: en tu CSV es ';'
        reader = csv.DictReader(file, delimiter=';')

        for row in reader:
            try:
                razon_social = row['Ciente'].strip()
                telefono = row['TELÉFONO'].strip() or None
                direccion = row['Direccion'].strip() or None
                localidad_nombre = row['Localidad'].strip()
                provincia = row['PROVINCIA'].strip()
                ruta_descripcion = row['RUTA_CLASIFICADA'].strip()

                # === GESTIÓN DE LOCALIDAD ===
                localidad, created_loc = Localidades.get_or_create(
                    descripcion=localidad_nombre,
                    defaults={'provincia': provincia}
                )
                # Si ya existe, aseguramos que tenga la provincia correcta
                if not created_loc and localidad.provincia != provincia:
                    localidad.provincia = provincia
                    localidad.save()

                # === GESTIÓN DE RUTA DE REPARTO ===
                ruta_reparto, created_ruta = RutaReparto.get_or_create(
                    descripcion=ruta_descripcion,
                    defaults={'activo': True}
                )

                # === CREAR CLIENTE ===
                cliente, created_cliente = Cliente.get_or_create(
                    razon_social=razon_social,
                    defaults={
                        'telefono': telefono,
                        'direccion': direccion,
                        'contacto': None,
                        'cuit': None,
                        'observaciones': None,
                        'ruta_reparto': ruta_reparto,
                        'activo': True
                    }
                )

                # Si el cliente ya existe, puedes actualizar sus datos si es necesario
                if not created_cliente:
                    cliente.telefono = telefono or cliente.telefono
                    cliente.direccion = direccion or cliente.direccion
                    cliente.ruta_reparto = ruta_reparto
                    cliente.save()

                print(f"✅ {'Creado' if created_cliente else 'Actualizado'} cliente: {razon_social}")

            except Exception as e:
                print(f"❌ Error al procesar fila {row}: {e}")
                continue

# Llamada a la función
importar_clientes_desde_csv('documentacion/LISTA_CLIENTES_CLASIFICADA RUTEO.csv')
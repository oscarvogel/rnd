import os, sys, datetime
from pathlib import Path
base = Path(__file__).resolve().parent
# La raiz del repositorio tiene sistema.demo.ini, sistema.db y demo_seed:
# el INI se resuelve contra el cwd (resolver_configuracion_activa usa os.getcwd).
repo = base.parent.parent
out = base / 'capturas'
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(repo))
os.chdir(repo)
os.environ['RND_DEMO_MODE'] = '1'
os.environ['RND_CREDENTIAL_PROFILE'] = 'demo'
os.environ['QT_QPA_FONTDIR'] = os.path.join(os.environ.get('WINDIR', r'C:\\Windows'), 'Fonts')
sys.argv = [sys.argv[0], '-a', 'sistema.demo.ini']
from pyqt5libs.pyqt5libs.utiles import BorrarConf, GrabaConf
BorrarConf(); GrabaConf(clave='iniciosistema', valor=str(repo) + os.sep); GrabaConf(clave='archivoini', valor='sistema.demo.ini'); GrabaConf(clave='DEBUG', valor=True); GrabaConf(clave='Reconecta', valor=True); GrabaConf(clave='usuario', valor='demo')
from demo_seed import prepare_demo_database
prepare_demo_database()
from modelos.ModeloBase import db
from utiles.demo_pallet_schema import asegurar_contexto_pallet_demo
asegurar_contexto_pallet_demo(db)
from PyQt5.QtWidgets import QApplication, QComboBox, QTableWidgetItem
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont
from utiles.tema import aplicar_tema
app = QApplication([]); aplicar_tema(app)

def save(widget, name, width=None, height=None):
    widget.show(); app.processEvents()
    if width and height: widget.resize(width, height); app.processEvents()
    pix = widget.grab()
    path = out / name
    if not pix.save(str(path), 'PNG'): raise RuntimeError('No se pudo guardar ' + str(path))
    print(str(path), pix.width(), pix.height())
    widget.close()

# Captura 1 — pantalla real de importación con vista previa representativa.
from vistas.ImportacionPedidos import ImportacionPedidosView
imp = ImportacionPedidosView(); imp.fecha_reparto.setDate(QDate(2026, 10, 14))
imp.empresa_proveedora.setText('4'); imp.empresa_proveedora.textNombre.setText('Proveedor Demo - Columnas')
imp.txt_archivo.setText('04_columnas_demo.xlsx')
imp.lbl_previa.setText('Se leyeron 2 registros. Revisá la grilla y desmarcá cualquier fila que no quieras grabar.')
imp.grid_datos.ArmaCabeceras(['Importa', 'Cliente', 'Comprobante', 'Producto', 'Cantidad', 'KG', 'Bultos', 'Observaciones'])
imp.grid_datos.AgregaItem([True, 'Cinco Hermanos', 'DEMO-COL-001', 'Bebidas', '10', '120', '10', 'Importación demo'])
imp.grid_datos.AgregaItem([True, 'Ceferino', 'DEMO-COL-002', 'Alimentos', '8', '95', '8', 'Importación demo'])
imp.lbl_resultado_titulo.setText('Vista previa lista para revisar')
imp.lbl_resultado_detalle.setText('Verificá los datos antes de presionar Grabar pedidos.')
save(imp, '01_importar_vista_previa.png', 1180, 850)

# Captura 2 — bandeja de pedidos para organizar, con facturas del ejemplo.
from vistas.BandejaPedidos import BandejaPedidosView
class Factura:
    def __init__(self, clave, factura, cliente, lugar, ruta, producto, cantidad, kg, bultos, remito='', observaciones=''):
        self.clave=clave; self.factura=factura; self.cliente=cliente; self.lugar_entrega=lugar; self.ruta=ruta; self.productos=producto; self.cantidad=cantidad; self.kg=kg; self.bultos=bultos; self.remito=remito; self.observaciones=observaciones
    def estado(self, *args): return 'Pendiente'
b = BandejaPedidosView(); b.fecha.setDate(QDate(2026,10,14)); b.cargar_rutas([(1,'CENTRO'),(2,'NORTE')]); b.cbo_ruta.setCurrentIndex(1)
b.cargar_facturas([Factura('DEMO-COL-001','DEMO-COL-001','Cinco Hermanos','Puerto Rico','CENTRO','Bebidas',10,120,10),Factura('DEMO-COL-002','DEMO-COL-002','Ceferino','Obera','CENTRO','Alimentos',8,95,8)], None, None)
save(b, '02_pedidos_para_organizar.png', 1500, 780)

# Captura 3 — asignación de recursos.
from vistas.AsignacionRecursos import AsignacionRecursosView
ar = AsignacionRecursosView(); ar.fecha.setDate(QDate(2026,10,14)); ar.cargar_rutas([(1,'CENTRO'),(2,'NORTE')], seleccion=1)
ar.cargar_responsables([(1,'Juan Gómez'),(2,'Carlos Benítez')]); ar.cargar_equipos([(1,'Camión Demo 1 · AF123AA'),(2,'Camión Demo 2 · AG456BB')]); ar.seleccionar_recursos(1,1)
class Resumen: pedidos=2; kg='215'; bultos='18'; vacia=False
ar.set_resumen(Resumen(), 'Juan Gómez · Camión Demo 1 · AF123AA'); ar.lbl_estado.setText('Asignación lista para guardar.'); ar.btn_ver_hoja.setEnabled(True)
save(ar, '03_asignar_chofer_camion.png', 900, 620)

# Captura 4 — armado de pallets: mercaderia pendiente y pallet actual.
from vistas.ArmadoPallets import ArmadoPalletsView
ap = ArmadoPalletsView(); ap.fecha_reparto.setDate(QDate(2026, 10, 14))
try:
    ap.cbo_ruta_reparto.setCurrentText('CENTRO')
except Exception: pass
ap.mostrar_contexto('Fecha 14/10/2026 · Ruta CENTRO · Juan Gómez · Camión Demo 1 · AF123AA')
ap.cargar_pendientes([
    {'cliente': 'Cinco Hermanos', 'comprobante': 'DEMO-COL-001', 'factura': 'DEMO-COL-001',
     'producto': 'Bebidas', 'total': '10', 'asignado': '0', 'saldo': '10', 'saldo_kg': '120',
     'saldo_bultos': '10', 'hoja_ruta_id': '1'},
    {'cliente': 'Ceferino', 'comprobante': 'DEMO-COL-002', 'factura': 'DEMO-COL-002',
     'producto': 'Alimentos', 'total': '8', 'asignado': '0', 'saldo': '8', 'saldo_kg': '95',
     'saldo_bultos': '8', 'hoja_ruta_id': '2'},
    {'cliente': 'Comercial San Vicente', 'comprobante': 'DEMO-COL-003', 'factura': 'DEMO-COL-003',
     'producto': 'Limpieza', 'total': '30', 'asignado': '12', 'saldo': '18', 'saldo_kg': '165',
     'saldo_bultos': '18', 'hoja_ruta_id': '3'},
])
ap.cargar_pallets([(1, 'PAL-0001'), (2, 'PAL-0002')], seleccionado=1)
ap.cargar_contenido([
    {'producto': 'Bebidas', 'cliente': 'Cinco Hermanos', 'comprobante': 'DEMO-COL-001',
     'cantidad': '10', 'kg': '120', 'bultos': '10', 'hoja_ruta_id': '1'},
    {'producto': 'Alimentos', 'cliente': 'Ceferino', 'comprobante': 'DEMO-COL-002',
     'cantidad': '8', 'kg': '95', 'bultos': '8', 'hoja_ruta_id': '2'},
])
ap.mostrar_totales(
    {'lineas': 2, 'cantidad': '18', 'kg': '215', 'bultos': '18'},
    [{'cliente': 'Cinco Hermanos', 'lugar_entrega': 'Puerto Rico', 'cantidad': '10'},
     {'cliente': 'Ceferino', 'lugar_entrega': 'Obera', 'cantidad': '8'}],
)
ap.mostrar_estado('2 pallets armados. Falta confirmar la preparación y validar la carga.')
ap.mostrar_resumen('Pallets: 2 · Líneas paletizadas: 2/3')
save(ap, '04_armado_pallets.png', 1240, 760)

# Captura 5 — validar carga del camion: cada pallet se tilda al subirlo.
from vistas.ValidarCarga import ValidarCargaDialog
vc = ValidarCargaDialog()
vc.cargar_pallets([
    {'id': 1, 'codigo': 'PAL-0001', 'cargado': True, 'lineas': 2},
    {'id': 2, 'codigo': 'PAL-0002', 'cargado': False, 'lineas': 1},
])
save(vc, '05_validar_carga.png', 640, 620)

# Captura 6 — hoja cargada y lista para imprimir.
from vistas.VerHojaRuta import VerHojaRutaView
vh = VerHojaRutaView(); vh.fecha_reparto.setDate(QDate(2026,10,14)); vh.lbl_titulo_hoja.setText('Hoja de ruta · 14/10/2026 · CENTRO'); vh.mostrar_recursos('Juan Gómez','Camión Demo 1 · AF123AA'); vh.mostrar_estado_operativo('LISTA',2,'215','18',True,True)
vh.lbl_estado_hoja.setText('Hoja cargada correctamente. Revise el detalle y genere la impresión.')
# Rellenar el control de ruta utilizado en esta pantalla.
try:
    vh.cbo_ruta_reparto.setCurrentText('CENTRO')
except Exception: pass
try:
    g=vh.grilla_datos; g.setColumnCount(11); g.setHorizontalHeaderLabels(['Cliente','Comprobante','Factura','Remito','Producto','Cantidad','KG','Bultos','Observaciones','ID','Código']);
    for values in [
      ['Cinco Hermanos','DEMO-COL-001','DEMO-COL-001','','Bebidas','10','120','10','Pedido importado',1,'CLI-001'],
      ['Ceferino','DEMO-COL-002','DEMO-COL-002','','Alimentos','8','95','8','Pedido importado',2,'CLI-002']]:
        row=g.rowCount(); g.insertRow(row)
        for col,value in enumerate(values): g.setItem(row,col,QTableWidgetItem(str(value)))
    g.resizeColumnsToContents()
except Exception as exc: print('grilla:', exc)
save(vh, '06_ver_hoja_ruta.png', 1500, 820)

# El reporte de impresión se genera con el mismo generador del sistema y datos ficticios del demo.
import builtins
from unittest.mock import patch
from modelos.HojaRuta import HojaDeRuta
from utiles.Reportes import GeneradorPDFHojaRuta
# El seed del demo congela la fecha de sus pedidos en el dia en que se creo la
# base (get_or_create por comprobante), asi que se usa la fecha mas reciente
# que tenga filas y no la de hoy.
fecha_datos = None
try:
    from peewee import fn
    fila = HojaDeRuta.select(fn.MAX(HojaDeRuta.fecha)).scalar()
    fecha_datos = fila
except Exception as exc:
    print('fecha max:', exc)
query = HojaDeRuta.select().where(HojaDeRuta.fecha == (fecha_datos or datetime.date.today())).limit(10)
if query.exists():
    fecha_reporte = (fecha_datos or datetime.date.today())
    pdf = GeneradorPDFHojaRuta()
    pdf.empresa_nombre = 'Empresa de muestra'
    pdf.empresa_info = 'Datos de ejemplo'
    with patch('os.startfile', lambda *a, **k: None, create=True), patch('utiles.Reportes.messagebox.showinfo', lambda *a, **k: None, create=True), patch('utiles.Reportes.messagebox.showerror', lambda *a, **k: None, create=True):
        pdf.generar_reporte(query, fecha_reporte.strftime('%d/%m/%Y'), 'CENTRO', 'Juan Gómez', 'Camión Demo 1 · AF123AA')
    pdf_path = repo / 'documentacion' / ('HojaRuta_{}_CENTRO.pdf'.format(fecha_reporte.strftime('%d-%m-%Y')))
    if pdf_path.exists():
        import fitz
        doc=fitz.open(str(pdf_path)); page=doc[0]; pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5), alpha=False); pix.save(str(out/'07_hoja_de_ruta_impresa.png'))
        print(str(out/'07_hoja_de_ruta_impresa.png'), pix.width, pix.height)
    else:
        print('No se genero el PDF de ejemplo:', pdf_path)
        doc.close()
else: print('No hay datos demo para reporte PDF')

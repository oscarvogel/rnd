from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, KeepTogether

root = Path(r'C:\Programacion\RND')
manual = root / 'docs' / 'manual_hoja_ruta'
shots = manual / 'capturas'
out = root / 'docs' / 'manual_usuario_hoja_ruta.pdf'
pdfmetrics.registerFont(TTFont('Arial', r'C:\Windows\Fonts\arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Bold', r'C:\Windows\Fonts\arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Italic', r'C:\Windows\Fonts\ariali.ttf'))
navy = colors.HexColor('#0B3975'); blue = colors.HexColor('#0A84D8'); gray = colors.HexColor('#475569'); text = colors.HexColor('#1F2937'); pale = colors.HexColor('#EAF6FC')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleRND', fontName='Arial-Bold', fontSize=27, leading=32, textColor=navy, spaceAfter=5))
styles.add(ParagraphStyle(name='SubTitleRND', fontName='Arial-Bold', fontSize=16, leading=20, textColor=blue, spaceAfter=7))
styles.add(ParagraphStyle(name='MetaRND', fontName='Arial', fontSize=9, leading=13, textColor=gray, spaceAfter=14))
styles.add(ParagraphStyle(name='H1RND', fontName='Arial-Bold', fontSize=17, leading=21, textColor=navy, spaceBefore=3, spaceAfter=10, keepWithNext=True))
styles.add(ParagraphStyle(name='BodyRND', fontName='Arial', fontSize=9.7, leading=14, textColor=text, spaceAfter=7))
styles.add(ParagraphStyle(name='SmallRND', fontName='Arial', fontSize=8, leading=11, textColor=gray, spaceAfter=5))
styles.add(ParagraphStyle(name='FlowRND', fontName='Arial-Bold', fontSize=10.2, leading=16, textColor=navy, alignment=TA_CENTER, backColor=pale, borderColor=colors.HexColor('#C9E8F8'), borderWidth=.6, borderPadding=10, spaceBefore=4, spaceAfter=12))
styles.add(ParagraphStyle(name='BulletRND', parent=styles['BodyRND'], leftIndent=13, firstLineIndent=-8, bulletIndent=0, spaceAfter=5))

W,H=A4
left=18*mm; right=18*mm; top=17*mm; bottom=18*mm
usable_w=W-left-right; usable_h=H-top-bottom

def page_chrome(canvas, doc):
    canvas.saveState()
    if doc.page > 1:
        canvas.setStrokeColor(colors.HexColor('#D9E7F0')); canvas.setLineWidth(.55)
        canvas.line(left, H-11*mm, W-right, H-11*mm)
        canvas.setFont('Arial-Bold', 8); canvas.setFillColor(navy); canvas.drawString(left, H-8.5*mm, 'RND  |  CIRCUITO DE REPARTO')
    canvas.setStrokeColor(colors.HexColor('#D9E7F0')); canvas.setLineWidth(.5)
    canvas.line(left, 12*mm, W-right, 12*mm)
    canvas.setFont('Arial', 8); canvas.setFillColor(gray)
    canvas.drawCentredString(W/2, 7.8*mm, f'Manual de usuario  |  {doc.page}')
    canvas.restoreState()

doc=SimpleDocTemplate(str(out), pagesize=A4, leftMargin=left, rightMargin=right, topMargin=top, bottomMargin=bottom, title='Manual de usuario - Importar pedidos e imprimir la hoja de ruta', author='Vogel Consultoria')
story=[]

def P(t, style='BodyRND', target=None):
    (story if target is None else target).append(Paragraph(t, styles[style]))
def B(t, target=None):
    (story if target is None else target).append(Paragraph(t, styles['BulletRND'], bulletText='•'))
def pic(name, max_h=None, width=usable_w, target=None):
    im=Image(str(shots/name)); scale=min(width/im.imageWidth, (max_h or usable_h)/im.imageHeight); im.drawWidth=im.imageWidth*scale; im.drawHeight=im.imageHeight*scale; im.hAlign='CENTER'; (story if target is None else target).append(im)
def cap(t, target=None):
    (story if target is None else target).append(Spacer(1,3)); P(t,'SmallRND', target)
# Overview
P('Manual de usuario','TitleRND')
P('Importar pedidos e imprimir la hoja de ruta','SubTitleRND')
P('RND  |  Circuito de reparto  |  20 de octubre de 2026','MetaRND')
P('Este manual explica el recorrido operativo desde la pantalla principal de RND hasta la impresión de la hoja de ruta: importar el archivo del proveedor, revisar y grabar los pedidos, organizarlos por ruta, asignar chofer y camión, preparar la carga en pallets y generar el PDF.')
P('<i>Las capturas muestran pantallas actuales de RND. Los clientes, comprobantes y cantidades visibles son datos de demostración.</i>')
P('Recorrido rápido','H1RND')
P('Importar pedidos  &gt;  Revisar vista previa  &gt;  Grabar pedidos<br/>Organizar pedidos  &gt;  Asignar chofer y camión  &gt;  Armar pallets  &gt;  Validar carga<br/>Marcar LISTA  &gt;  Confirmar salida a reparto  &gt;  Revisar e imprimir','FlowRND')
P('Antes de empezar','H1RND')
for t in ['Tenga el archivo recibido del proveedor y confirme la fecha de reparto.','Verifique que el proveedor, los clientes, los lugares de entrega, las rutas, los choferes y los camiones estén cargados en RND.','Si una opción no aparece en la pantalla principal, puede depender del perfil de acceso.']: B(t)

story.append(PageBreak())
P('1. Importar y revisar el archivo','H1RND')
P('Desde la pantalla principal, abra <b>Importar pedidos</b>. Seleccione el <b>Proveedor / origen</b> y la <b>Fecha reparto</b> antes de elegir el archivo. Use <b>Seleccionar archivo</b> para buscarlo en el equipo.')
P('RND admite planillas Excel (.xlsx y .xls), archivos PDF e imágenes (.png, .jpg y .jpeg). En Excel, seleccione la hoja si corresponde; las filas de inicio y fin son opcionales. Los PDF e imágenes se procesan con IA. No hace falta convertirlos manualmente a Excel.')
P('Presione <b>Cargar vista previa</b> y controle cliente, comprobante, producto, cantidad, KG, bultos y observaciones. La vista previa todavía no graba pedidos. En Excel, use la casilla <b>Importa</b> para incluir o excluir filas. En PDF o imagen, corrija los datos extraídos y revise las filas marcadas <b>REVISAR IA</b>.')
P('Cuando la vista previa esté correcta, presione <b>Grabar pedidos</b>. Lea el resumen de importación y continúe con el botón que RND indique. Si hay pendientes, resuélvalos antes de seguir.')
pic('01_importar_vista_previa.png', max_h=125*mm)
cap('Figura 1. Importación con vista previa. Los datos visibles son de demostración.')

story.append(PageBreak())
P('2. Organizar los pedidos en una ruta','H1RND')
P('Abra <b>Pedidos para organizar</b> desde el paso siguiente o desde el menú operativo. Seleccione la fecha y presione <b>Actualizar</b>. Cada fila representa una factura o documento completo; revise el estado, el cliente, el lugar de entrega y la ruta.')
P('Use <b>Editar</b> para corregir cliente, lugar, ruta, remito u observación general. Use <b>Productos</b> para revisar las líneas y, si hace falta, cambiar únicamente la <b>Cantidad a entregar</b>. No puede ser negativa ni superar la cantidad original.')
P('Marque las facturas que viajarán juntas, seleccione la <b>Ruta destino</b> y presione <b>Organizar seleccionados</b>. Espere la confirmación. Después de organizar correctamente, RND habilita <b>Asignar chofer y camión</b>.')
pic('02_pedidos_para_organizar.png', max_h=94*mm)
cap('Figura 2. Bandeja de pedidos agrupada por factura. Los datos visibles son de demostración.')

story.append(PageBreak())
P('3. Asignar chofer y camión','H1RND')
P('En <b>Asignar chofer y camión</b>, seleccione la fecha y la ruta y presione <b>Cargar datos de hoja</b>. Compruebe la cantidad de pedidos, el peso y los bultos antes de asignar recursos.')
P('Seleccione un <b>Chofer / responsable</b> y un <b>Camión / equipo</b> reales. Presione <b>Guardar asignación</b>. RND guarda los recursos para todos los pedidos de esa fecha y ruta. Luego puede presionar <b>Revisar hoja de ruta</b>.')
pic('03_asignar_chofer_camion.png', max_h=117*mm)
cap('Figura 3. Asignación de recursos para una fecha y ruta. Los datos visibles son de demostración.')

story.append(PageBreak())
P('4. Armar pallets y validar la carga','H1RND')
P('El circuito admite dos formas de preparar la mercadería. Si no arman pallets, el circuito se completa igual: el requisito de carga del checklist queda como informativo y no bloquea. Si arman pallets, este paso es el que libera el checklist.')
P('Abra <b>Armado de pallets</b> y seleccione la <b>Fecha de reparto</b> y la <b>Ruta de reparto</b>. Presione <b>Cargar mercadería</b>: a la izquierda aparece la <b>Mercadería pendiente de preparar</b>, con el saldo de cada línea ya descontado de lo asignado a otros pallets.')
P('Seleccione una o más líneas y presione <b>Agregar selección al pallet</b>. Use <b>Agregar parcial…</b> para cargar una cantidad menor al saldo y <b>Quitar del pallet</b> para sacar líneas. Con <b>+ Nuevo pallet</b> abre otro pallet; los pallets se muestran numerados, un clic cambia el pallet activo y el KPI muestra su peso. <b>Etiqueta / QR</b> imprime la etiqueta del pallet seleccionado.')
P('Cuando el pallet esté completo, presione <b>Confirmar preparación</b>. Ojo con este punto: <b>Confirmar preparación no cambia el estado</b>. El pallet sigue <b>ARMADO</b> y lo que se ve es el resumen. Para despachar falta el paso siguiente.')
pic('04_armado_pallets.png', max_h=108*mm)
cap('Figura 4. Armado de pallets: mercadería pendiente de preparar y contenido del pallet actual. Los datos visibles son de demostración.')
carga = []
P('Vuelva a <b>Validar hoja de ruta</b> y presione <b>Validar carga</b>, o haga doble clic sobre el renglón pendiente del checklist: RND abre la pantalla donde se resuelve. Tilde cada pallet a medida que lo sube al camión; también puede escribir o escanear el código en el campo <b>Código</b> y presionar Enter, o usar <b>Marcar todos</b> cuando el camión ya está completo.', target=carga)
P('Presione <b>Guardar</b>: los pallets tildados quedan <b>CARGADO</b> y los destildados vuelven a <b>ARMADO</b>. Recién al guardar queda registrado quién cargó cada pallet y cuándo. <b>Cancelar</b> no guarda nada y los pallets conservan su estado.', target=carga)
pic('05_validar_carga.png', max_h=78*mm, width=92*mm, target=carga)
cap('Figura 5. Validación de la carga: cada pallet se marca a medida que sube al camión. Los datos visibles son de demostración.', target=carga)
# El bloque de la carga viaja junto: si la figura no entra, se va el texto con ella.
story.append(KeepTogether(carga))

story.append(PageBreak())
P('5. Revisar la hoja e imprimir','H1RND')
P('En <b>Ver Hoja de Ruta</b>, seleccione la fecha y la ruta y presione <b>Actualizar</b>. Revise el cliente, el comprobante, el producto, las cantidades, los KG, los bultos y los recursos asignados.')
P('Si los recursos están completos y hay pedidos, use <b>Vista previa PDF</b> para revisar la hoja durante la preparación. Cuando la hoja esté en estado <b>LISTA</b>, el botón se muestra como <b>Imprimir PDF</b>. Para marcarla LISTA, entre en <b>Validar hoja de ruta</b> y resuelva los requisitos pendientes del checklist. La impresión y el estado LISTA son controles independientes.')
P('Mientras quede un requisito pendiente, <b>Marcar LISTA</b> y <b>Confirmar salida a reparto</b> permanecen deshabilitados. Para corregir un requisito puntual, haga doble clic sobre la fila: RND abre la pantalla donde se resuelve.')
pic('06_ver_hoja_ruta.png', max_h=101*mm)
cap('Figura 6. Hoja en estado LISTA con la acción Imprimir PDF habilitada. Los datos visibles son de demostración.')
P('Con la hoja en LISTA, presione <b>Confirmar salida a reparto</b>: el camión salió a reparto y la hoja queda en estado <b>DESPACHADA</b>. Esta acción no marca los pedidos como entregados, y una hoja despachada no retrocede automáticamente.')
P('Al presionar <b>Imprimir PDF</b>, RND genera y abre el documento de la fecha y ruta seleccionadas. Desde el visor, revise el contenido y elija la impresora o la opción para guardar una copia.')

story.append(PageBreak())
P('6. El PDF de reparto','H1RND')
P('RND genera un documento por fecha y ruta. Revise el chofer, el camión y los pedidos antes de imprimir o guardar la copia.')
pic('07_hoja_de_ruta_impresa.png', max_h=170*mm, width=120*mm)
cap('Figura 7. Ejemplo del PDF de reparto generado por RND. Los datos visibles son de demostración.')
P('La impresión requiere pedidos para la fecha y ruta elegidas, además de un chofer y un camión válidos. Si falta algún dato, vuelva a la pantalla de asignación o a la bandeja para corregirlo.')
P('<b>Lista para Sergio</b> genera otro PDF, organizado por cliente y destino, con los números de factura agrupados por proveedor. El chofer debe llevar también las facturas originales.')

story.append(PageBreak())
P('7. Si algo no aparece o no permite continuar','H1RND')
for t in [
    '<b>La vista previa no muestra datos:</b> confirme proveedor, archivo y hoja de Excel. Para PDF o imagen, revise la calidad del documento y el mensaje de procesamiento.',
    '<b>La lectura del archivo tiene errores:</b> corrija la vista previa antes de grabar. No grabe filas que no haya podido verificar.',
    '<b>No hay pedidos para asignar:</b> revise la fecha y la ruta; confirme que organizó las facturas en esa ruta.',
    '<b>La hoja no muestra pedidos:</b> vuelva a presionar Actualizar y confirme fecha y ruta.',
    '<b>No se habilita la impresión:</b> confirme que haya pedidos y que la hoja tenga chofer y camión asignados.',
    '<b>No se habilita Marcar LISTA:</b> abra el checklist de Validar hoja de ruta y resuelva los requisitos pendientes.',
    '<b>El checklist pide la carga y no deja marcar LISTA:</b> presione Validar carga desde el checklist y marque cada pallet como CARGADO. Si quedan líneas sin asignar, el doble clic lo lleva a Armado de pallets.',
    '<b>Un pallet no aparece en Armado de pallets:</b> si ya está CARGADO no se muestra ahí. No se perdió: sigue visible en Validar carga y en el checklist.',
    '<b>Confirmar preparación y el pallet sigue pendiente:</b> es lo esperado. Confirmar preparación no cambia el estado; el pallet pasa a CARGADO en Validar carga.',
    '<b>La importación se interrumpió:</b> revise el resumen y los pedidos ya existentes antes de volver a cargar el archivo.'
]: B(t)

doc.build(story, onFirstPage=page_chrome, onLaterPages=page_chrome)
print(out)

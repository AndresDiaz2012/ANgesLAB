# -*- coding: utf-8 -*-
"""
================================================================================
BAREMO EN EXCEL PARA LA ADMINISTRACION DE LA CLINICA
================================================================================
El mismo baremo que se imprime en PDF, pero en un libro de Excel que la
administracion puede abrir, editar y devolver.

Por que un Excel y no solo el PDF: el baremo se negocia. La administracion
mira una cifra, la discute, la cambia y la manda de vuelta. Un PDF obliga a
que ese ida y vuelta ocurra por fuera -en un correo, en un papel anotado- y
lo que se acuerda deja de estar en ningun sitio. En una hoja de calculo la
conversacion queda dentro del propio documento.

EL LIBRO TIENE TRES HOJAS

    Base de trabajo   las pruebas con precio acordado. Una fila por prueba.
    Excluidos         las que todavia no tienen precio. No se borran: estan
                      ahi para que se les ponga uno y pasen a la otra hoja.
    Notas             como funciona el archivo, escrito para quien lo abra
                      sin haber hablado antes con nadie.

LAS COLUMNAS Y POR QUE

    Precio COP        lo que la CLINICA le cobra al paciente. Es el valor
                      maestro: se teclea a mano.
    Precio USD        =ROUNDUP(Precio COP / tasa). Formula viva, no un
                      numero copiado: al cambiar la tasa en D5 se recalculan
                      las 161 filas solas.
    Precio Convenio   =ROUNDUP(Precio COP * 0.8). Lo que recibe el
                      laboratorio; la clinica se queda el 20%.

Las formulas van VIVAS a proposito. Un Excel con numeros pegados es un PDF
con celdas: quien lo reciba tiene que rehacer las cuentas a mano y ahi es
donde se cuelan los errores. Con las formulas dentro, cambiar un precio
recalcula su dolar y su convenio en el acto, y la regla del 20% queda a la
vista en vez de ser un acuerdo que alguien recuerda.

El precio AMBULATORIO no sale en este libro. Es lo que el laboratorio le
cobra al paciente de calle, no forma parte del convenio y no tiene por que
viajar en un documento que se entrega en la clinica.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import math
from datetime import datetime

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.baremo_excel')
except Exception:  # pragma: no cover
    import logging
    _log = logging.getLogger('angeslab.baremo_excel')

try:
    from modulos.tarifas import COL_CLINICA, COL_CONVENIO
except Exception:  # pragma: no cover
    COL_CLINICA = 'PrecioClinica'
    COL_CONVENIO = 'PrecioConvenio'


# La clinica se queda esta parte de lo que le cobra al paciente. Vive aqui
# y en la formula de la hoja, que es la que manda para quien la edite.
COMISION_CLINICA = 0.20

# Importe en dolares por debajo del cual un precio no es un precio sino un
# relleno. El catalogo venia con pruebas a 50 centavos de dolar puestas para
# rellenar la casilla, y colarlas en un baremo que se firma seria peor que
# dejarlas fuera.
UMBRAL_PLACEHOLDER = 0.06

MOTIVO_SIN_PRECIO = 'Sin precio cargado'
MOTIVO_PLACEHOLDER = 'Placeholder sospechoso'


def _f(valor):
    try:
        return float(valor if valor is not None else 0)
    except (TypeError, ValueError):
        return 0.0


def clasificar(fila):
    """
    Si la prueba entra en la base de trabajo o en los excluidos.

    Devuelve (entra, motivo). El motivo solo tiene sentido si no entra.
    """
    clinica = _f(fila.get(COL_CLINICA))
    convenio = _f(fila.get(COL_CONVENIO))
    if clinica <= 0 and convenio <= 0:
        return False, MOTIVO_SIN_PRECIO
    if 0 < clinica <= UMBRAL_PLACEHOLDER:
        return False, MOTIVO_PLACEHOLDER
    return True, ''


def generar_baremo_excel(ruta, filas, config_lab=None, tasa_cop=3100.0,
                         tasa_bs=None, usuario=''):
    """
    Escribe el libro en ruta y la devuelve, o None si no se pudo.

    Args:
        filas: lo que devuelven listar_perfiles() + listar_baremo().
        tasa_cop: pesos por dolar. Va en la celda D5 y de ella cuelgan las
            formulas de la columna en dolares.
        tasa_bs: bolivares por dolar, la del BCV. Va en la celda D6 y de
            ella cuelga la columna en bolivares. Sin ella, esa columna
            no se escribe: inventar una conversion seria peor que no
            darla.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.utils import get_column_letter
    except ImportError:
        _log.error("openpyxl no disponible: no se puede generar el baremo Excel")
        return None

    cfg = config_lab or {}
    tasa = float(tasa_cop or 3100.0)
    bcv = float(tasa_bs) if tasa_bs else None

    incluidas, excluidas = [], []
    for f in filas:
        entra, motivo = clasificar(f)
        (incluidas if entra else excluidas).append((f, motivo))

    AZUL, CIAN, GRIS = '0F172A', '0891B2', '64748B'
    borde = Border(bottom=Side(style='thin', color='CBD5E1'))

    wb = Workbook()

    # ══════════════════════════════════ hoja 1: base de trabajo
    ws = wb.active
    ws.title = "Base de trabajo (%d)" % len(incluidas)

    ws['B2'] = "%s - Baremo de convenio (USD / COP)" % (
        cfg.get('NombreLaboratorio') or 'Laboratorio')
    ws['B2'].font = Font(size=14, bold=True, color=AZUL)
    ws['B3'] = ("%d pruebas/perfiles con precio acordado. El precio en pesos "
                "(columna F) es el que se edita a mano; el de dolares "
                "(columna G) y el de convenio (columna H) se recalculan solos."
                % len(incluidas))
    ws['B3'].font = Font(size=9, color=GRIS)
    if cfg.get('RIF'):
        ws['B4'] = "RIF: %s" % cfg['RIF']
        ws['B4'].font = Font(size=9, color=GRIS)

    ws['B5'] = "Tasa USD -> COP (hoy)"
    ws['B5'].font = Font(size=10, bold=True)
    ws['D5'] = tasa
    ws['D5'].font = Font(size=11, bold=True, color=CIAN)
    ws['D5'].number_format = '#,##0.00'
    ws['E5'] = "COP por 1 USD. Editelo cuando cambie la tasa."
    ws['E5'].font = Font(size=8, color=GRIS)

    if bcv:
        ws['B6'] = "Tasa BCV (Bs por USD)"
        ws['B6'].font = Font(size=10, bold=True)
        ws['D6'] = bcv
        ws['D6'].font = Font(size=11, bold=True, color=CIAN)
        ws['D6'].number_format = '#,##0.00'
        ws['E6'] = "Bs por 1 USD. De ella cuelga la columna en bolivares."
        ws['E6'].font = Font(size=8, color=GRIS)

    CABECERAS = ["Codigo", "Prueba", "Area", "Tipo",
                 "Precio COP", "Precio USD", "Precio Convenio (COP)",
                 "Precio Bs", "Nota"]
    FILA_CAB = 8
    for i, texto in enumerate(CABECERAS):
        c = ws.cell(row=FILA_CAB, column=2 + i, value=texto)
        c.font = Font(bold=True, color='FFFFFF', size=9)
        c.fill = PatternFill('solid', fgColor=CIAN)
        c.alignment = Alignment(horizontal='center', vertical='center',
                                wrap_text=True)

    r = FILA_CAB + 1
    for f, _motivo in incluidas:
        cop = round(_f(f.get(COL_CLINICA)) * tasa)
        ws.cell(row=r, column=2, value=f.get('CodigoPrueba') or '')
        ws.cell(row=r, column=3, value=f.get('NombrePrueba') or '')
        ws.cell(row=r, column=4, value=f.get('NombreArea') or '')
        ws.cell(row=r, column=5,
                value='Perfil' if f.get('es_perfil') else 'Prueba')
        ws.cell(row=r, column=6, value=cop).number_format = '#,##0'
        # Formulas vivas: al cambiar D5 o el precio en pesos, estas dos se
        # recalculan solas en el Excel de quien lo reciba.
        ws.cell(row=r, column=7,
                value='=ROUNDUP(F%d/$D$5,0)' % r).number_format = '#,##0'
        # El convenio va como FORMULA mientras siga la regla del 20%, que
        # es lo que hace util el archivo: se edita el precio y el convenio
        # se recalcula. Pero un paquete negociado -el perfil 20 se pacto en
        # 150.000, no en el 80% de 190.000- no obedece a ninguna formula, y
        # ponerle una haria que el documento dijera un importe que el
        # software no cobra. Esos van con su cifra y una nota.
        convenio_cop = round(_f(f.get(COL_CONVENIO)) * tasa)
        segun_regla = math.ceil(cop * (1 - COMISION_CLINICA))
        celda = ws.cell(row=r, column=8)
        if cop > 0 and abs(convenio_cop - segun_regla) > 1:
            celda.value = convenio_cop
            ws.cell(row=r, column=10, value='Precio acordado, no es el %d%%'
                    % int(COMISION_CLINICA * 100)).font = Font(
                        size=8, italic=True, color='B45309')
        else:
            celda.value = '=ROUNDUP(F%d*%s,0)' % (r, 1 - COMISION_CLINICA)
        celda.number_format = '#,##0'

        # Bolivares: cuelga de la tasa del BCV igual que el dolar de la
        # suya, asi que al cambiar D6 se recalculan las 300 filas solas.
        if bcv:
            ws.cell(row=r, column=9,
                    value='=ROUNDUP(F%d/$D$5*$D$6,0)' % r
                    ).number_format = '#,##0'

        for col in range(2, 11):
            ws.cell(row=r, column=col).border = borde
        if f.get('es_perfil'):
            for col in range(2, 10):
                ws.cell(row=r, column=col).font = Font(bold=True,
                                                       color='7C3AED')
        r += 1

    for col, an in zip(range(2, 11), (12, 46, 18, 9, 14, 12, 20, 14, 26)):
        ws.column_dimensions[get_column_letter(col)].width = an
    ws.freeze_panes = ws.cell(row=FILA_CAB + 1, column=1)
    ws.auto_filter.ref = "B%d:J%d" % (FILA_CAB, r - 1)
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = '%d:%d' % (FILA_CAB, FILA_CAB)

    # ══════════════════════════════════════ hoja 2: excluidos
    we = wb.create_sheet("Excluidos")
    we['B2'] = "Pruebas excluidas de la base de trabajo"
    we['B2'].font = Font(size=13, bold=True, color=AZUL)
    we['B3'] = ("No se borraron: quedan aqui por si luego se les corrige el "
                "precio y se incorporan.")
    we['B3'].font = Font(size=9, color=GRIS)

    CAB_EX = ["Codigo", "Prueba", "Area", "Tipo", "Precio USD actual", "Motivo"]
    for i, texto in enumerate(CAB_EX):
        c = we.cell(row=5, column=2 + i, value=texto)
        c.font = Font(bold=True, color='FFFFFF', size=9)
        c.fill = PatternFill('solid', fgColor='B45309')
        c.alignment = Alignment(horizontal='center', wrap_text=True)

    r = 6
    for f, motivo in excluidas:
        we.cell(row=r, column=2, value=f.get('CodigoPrueba') or '')
        we.cell(row=r, column=3, value=f.get('NombrePrueba') or '')
        we.cell(row=r, column=4, value=f.get('NombreArea') or '')
        we.cell(row=r, column=5,
                value='Perfil' if f.get('es_perfil') else 'Prueba')
        we.cell(row=r, column=6,
                value=round(_f(f.get(COL_CLINICA)), 2)).number_format = '0.00'
        etiqueta = motivo
        if motivo == MOTIVO_PLACEHOLDER:
            etiqueta = "%s $%.2f" % (motivo, _f(f.get(COL_CLINICA)))
        we.cell(row=r, column=7, value=etiqueta)
        r += 1
    for col, an in zip(range(2, 8), (12, 46, 18, 9, 18, 28)):
        we.column_dimensions[get_column_letter(col)].width = an
    we.freeze_panes = we.cell(row=6, column=1)

    # ═════════════════════════════════════════ hoja 3: notas
    wn = wb.create_sheet("Notas")
    wn['B2'] = "Como funciona este archivo"
    wn['B2'].font = Font(size=13, bold=True, color=AZUL)
    NOTAS = [
        ("MONEDAS",
         "El precio en PESOS (columna F) es el valor maestro: se edita a mano "
         "fila por fila y de el cuelga todo lo demas. El dolar (columna G) "
         "sale de dividir entre la tasa de D5, y el bolivar (columna I) de "
         "multiplicar ese dolar por la tasa del BCV de D6. Las tres cifras "
         "se redondean hacia arriba."),
        ("TASA VARIABLE",
         "La celda D5 de la hoja \"Base de trabajo\" es la tasa del dia. "
         "Cambiela cuando el dolar se mueva y la columna \"Precio USD\" de "
         "todas las filas se recalcula sola. Lo que NO cambia solo es la "
         "columna de pesos: esa la fija usted."),
        ("PRECIO CONVENIO",
         "Columna H: %d%% de descuento sobre el \"Precio COP\" de esa fila, "
         "redondeado hacia arriba. Formula: =ROUNDUP(PrecioCOP*%s,0). Si "
         "cambia el precio en pesos de una prueba, su precio de convenio se "
         "recalcula solo."
         % (int(COMISION_CLINICA * 100), 1 - COMISION_CLINICA)),
        ("QUE SIGNIFICA CADA PRECIO",
         "\"Precio COP\" es lo que la clinica le cobra al paciente. \"Precio "
         "Convenio\" es lo que la clinica le paga al laboratorio. La "
         "diferencia, el %d%%, se la queda la clinica."
         % int(COMISION_CLINICA * 100)),
        ("HOJA EXCLUIDOS",
         "Pruebas que todavia no tienen precio acordado. No estan borradas: "
         "en cuanto se les ponga uno pasan a la base de trabajo."),
    ]
    r = 4
    for titulo, texto in NOTAS:
        wn.cell(row=r, column=2, value=titulo).font = Font(bold=True, size=10,
                                                           color=CIAN)
        c = wn.cell(row=r + 1, column=2, value=texto)
        c.font = Font(size=9)
        c.alignment = Alignment(wrap_text=True, vertical='top')
        wn.row_dimensions[r + 1].height = 46
        r += 3
    wn.column_dimensions['B'].width = 118

    pie = "Generado el %s" % datetime.now().strftime('%d/%m/%Y %H:%M')
    if usuario:
        pie += " por %s" % usuario
    wn.cell(row=r, column=2, value=pie).font = Font(size=8, italic=True,
                                                    color=GRIS)

    try:
        wb.save(ruta)
    except Exception as e:
        _log.error("No se pudo guardar el baremo Excel: %s", e)
        return None

    _log.info("Baremo Excel generado: %s (%d incluidas, %d excluidas)",
              ruta, len(incluidas), len(excluidas))
    return ruta

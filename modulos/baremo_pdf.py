# -*- coding: utf-8 -*-
"""
================================================================================
BAREMO INFORMATIVO DE PRECIOS
================================================================================
La lista de precios del laboratorio en papel, con las tres cifras de cada
prueba y lo que se queda la clinica por cobrarlas.

Es un documento INFORMATIVO: sirve para acordar el convenio con la clinica,
para que recepcion sepa que se cobra en cada caso y para revisar que ninguna
prueba se quedo sin precio de convenio. No factura nada por si mismo.

Por columna:

    Ambulatorio   lo que paga el paciente que viene por su cuenta
    Clinica       lo que la clinica le cobra al paciente que viene de
                  hospitalizacion, emergencia o cirugia
    Convenio      lo que la clinica le paga al laboratorio por esa prueba
    Comision      lo que se queda la clinica (clinica - convenio)

Ver modulos/tarifas.py para el detalle de cuando se aplica cada una.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.baremo')
except Exception:  # pragma: no cover
    import logging
    _log = logging.getLogger('angeslab.baremo')

try:
    from modulos.tarifas import COL_CLINICA, COL_CONVENIO
except Exception:  # pragma: no cover
    COL_CLINICA = 'PrecioClinica'
    COL_CONVENIO = 'PrecioConvenio'


def _f(valor):
    try:
        return float(valor if valor is not None else 0)
    except (TypeError, ValueError):
        return 0.0


def _importe(valor):
    """Un guion en vez de 0,00 cuando el precio no esta cargado."""
    v = _f(valor)
    return '{:,.2f}'.format(v) if v > 0 else '—'


def generar_baremo_pdf(ruta, filas, config_lab=None, usuario='',
                       moneda='COP', solo_sin_convenio=False):
    """
    Escribe el baremo en ruta y la devuelve, o None si no se pudo.

    Args:
        filas: lo que devuelve GestorTarifas.listar_baremo().
        solo_sin_convenio: para sacar la lista de lo que falta por acordar.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (HRFlowable, Paragraph,
                                        SimpleDocTemplate, Spacer, Table,
                                        TableStyle)
    except ImportError:
        _log.error("reportlab no disponible: no se puede generar el baremo")
        return None

    cfg = config_lab or {}
    estilos = getSampleStyleSheet()

    st_titulo = ParagraphStyle('bt', parent=estilos['Title'], fontSize=15,
                               spaceAfter=2, textColor=colors.HexColor('#0f172a'))
    st_sub = ParagraphStyle('bs', parent=estilos['Normal'], fontSize=9,
                            alignment=1, textColor=colors.HexColor('#475569'))
    st_area = ParagraphStyle('ba', parent=estilos['Heading2'], fontSize=10,
                             spaceBefore=9, spaceAfter=3,
                             textColor=colors.HexColor('#0891b2'))
    st_celda = ParagraphStyle('bc', parent=estilos['Normal'], fontSize=7.5)
    st_nota = ParagraphStyle('bn', parent=estilos['Normal'], fontSize=8,
                             textColor=colors.HexColor('#64748b'))

    if solo_sin_convenio:
        filas = [f for f in filas if f.get('_sin_convenio')]

    doc = SimpleDocTemplate(ruta, pagesize=letter,
                            leftMargin=0.45 * inch, rightMargin=0.45 * inch,
                            topMargin=0.5 * inch, bottomMargin=0.6 * inch,
                            title="Baremo de precios")
    hist = []

    hist.append(Paragraph(str(cfg.get('NombreLaboratorio') or 'Laboratorio'),
                          st_titulo))
    titulo = ("PRUEBAS SIN PRECIO DE CONVENIO" if solo_sin_convenio
              else "BAREMO INFORMATIVO DE PRECIOS")
    hist.append(Paragraph(titulo, st_sub))
    pie = "Importes en " + str(moneda) + " - Generado el " \
          + datetime.now().strftime('%d/%m/%Y %H:%M')
    if usuario:
        pie += " por " + str(usuario)
    hist.append(Paragraph(pie, st_sub))
    hist.append(Spacer(1, 5))

    hist.append(Paragraph(
        "Ambulatorio: lo paga el paciente que viene por su cuenta. &nbsp; "
        "Clinica: lo que la clinica le cobra al paciente de hospitalizacion, "
        "emergencia o cirugia. &nbsp; Convenio: lo que la clinica le paga al "
        "laboratorio. &nbsp; Comision: la diferencia, que se queda la clinica.",
        st_nota))
    hist.append(Spacer(1, 4))
    hist.append(HRFlowable(width="100%", thickness=1,
                           color=colors.HexColor('#cbd5e1')))

    # Agrupar por area, que es como se lee un baremo
    por_area = {}
    for f in filas:
        area = f.get('NombreArea') or 'Sin área'
        por_area.setdefault(area, []).append(f)

    cab = ['Código', 'Prueba', 'Ambulatorio', 'Clínica', 'Convenio',
           'Comisión', '%']
    anchos = [0.72 * inch, 2.5 * inch, 0.95 * inch, 0.85 * inch,
              0.9 * inch, 0.85 * inch, 0.5 * inch]

    comandos = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1),
         [colors.white, colors.HexColor('#f8fafc')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]

    total_pruebas = 0
    sin_convenio = 0
    for area in sorted(por_area):
        pruebas = por_area[area]
        hist.append(Paragraph(str(area).upper() + " (" + str(len(pruebas)) + ")",
                              st_area))
        datos = [cab]
        for f in pruebas:
            total_pruebas += 1
            falta = f.get('_sin_convenio')
            if falta:
                sin_convenio += 1
            pct = f.get('_pct_comision') or 0
            datos.append([
                str(f.get('CodigoPrueba') or ''),
                Paragraph(str(f.get('NombrePrueba') or ''), st_celda),
                _importe(f.get('Precio')),
                _importe(f.get(COL_CLINICA)),
                _importe(f.get(COL_CONVENIO)),
                _importe(f.get('_comision')),
                ('{:.0f}%'.format(pct)) if pct else '—',
            ])
        tabla = Table(datos, colWidths=anchos, repeatRows=1)
        estilo = TableStyle(comandos)
        # Marcar en ambar lo que aun no tiene convenio acordado
        for i, f in enumerate(pruebas, start=1):
            if f.get('_sin_convenio'):
                estilo.add('BACKGROUND', (4, i), (4, i), colors.HexColor('#fef3c7'))
        tabla.setStyle(estilo)
        hist.append(tabla)

    if not filas:
        hist.append(Spacer(1, 20))
        mensaje = ("Todas las pruebas tienen precio de convenio cargado."
                   if solo_sin_convenio else "No hay pruebas que listar.")
        hist.append(Paragraph(mensaje, estilos['Normal']))

    hist.append(Spacer(1, 10))
    hist.append(HRFlowable(width="100%", thickness=1,
                           color=colors.HexColor('#cbd5e1')))
    hist.append(Spacer(1, 5))

    resumen = str(total_pruebas) + " prueba(s) en el baremo."
    if sin_convenio and not solo_sin_convenio:
        resumen += ("  " + str(sin_convenio) + " sin precio de convenio "
                    "(marcadas en ámbar): esas se le cobran a la clínica al "
                    "precio ambulatorio hasta que se acuerde el convenio.")
    hist.append(Paragraph(resumen, st_nota))

    hist.append(Spacer(1, 8))
    hist.append(Paragraph(
        "Documento informativo. Los importes de la columna Clínica los cobra "
        "la clínica al paciente; el laboratorio percibe la columna Convenio.",
        st_nota))

    try:
        doc.build(hist)
        _log.info("Baremo generado: %s (%d pruebas)", ruta, total_pruebas)
        return ruta
    except Exception as e:
        _log.error("No se pudo escribir el baremo: %s", e)
        return None

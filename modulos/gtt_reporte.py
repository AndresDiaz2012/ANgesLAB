# -*- coding: utf-8 -*-
"""
gtt_reporte.py - Generador de reporte PDF para la Prueba de Tolerancia a la Glucosa
======================================================================================
Genera un informe PDF en hoja completa (letter) con:
  - Encabezado del laboratorio y datos del paciente (mismo formato que resultados)
  - Tabla de resultados por tiempo (Basal, 30min, 1h, 2h, 3h, 4h)
  - Grafica de la curva de glucemia generada con matplotlib (embebida en reportlab)
  - Zona de interpretacion y observaciones
  - Firma del bioanalista

La grafica se imprime SOLO si el operador activa la opcion correspondiente.
Cuando se imprime con grafica, la prueba ocupa una hoja completa propia.

Uso:
    from modulos.gtt_reporte import generar_pdf_gtt, mostrar_opciones_impresion_gtt
======================================================================================
"""

import os
import io
import tempfile
from datetime import datetime

# Reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, Image as RLImage,
                                    BaseDocTemplate, PageTemplate, Frame,
                                    KeepTogether)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# Matplotlib para la grafica
try:
    import matplotlib
    matplotlib.use('Agg')   # backend sin GUI, compatible con tkinter
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.gridspec import GridSpec
    MATPLOTLIB_OK = True
except ImportError:
    MATPLOTLIB_OK = False

# PIL para convertir imagen matplotlib -> reportlab
try:
    from PIL import Image as PILImage
    PIL_OK = True
except ImportError:
    PIL_OK = False


# ===========================================================================
# CONSTANTES
# ===========================================================================

TIEMPOS_DISPLAY = [
    ('GTT001', 'Basal (0 min)',   0,   '70 - 100 mg/dL'),
    ('GTT002', '30 minutos',      30,  '< 200 mg/dL'),
    ('GTT003', '1 hora',          60,  '< 180 mg/dL'),
    ('GTT004', '2 horas',         120, '< 140 mg/dL'),
    ('GTT005', '3 horas',         180, '< 120 mg/dL'),
    ('GTT006', '4 horas',         240, '< 110 mg/dL'),
]

# Limites alto para alertas
LIMITES_ALTO = {
    'GTT001': 100.0,
    'GTT002': 200.0,
    'GTT003': 180.0,
    'GTT004': 140.0,
    'GTT005': 120.0,
    'GTT006': 110.0,
}
LIMITES_BAJO = {'GTT001': 70.0}

# Colores unificados con el reporte general de resultados
COLOR_HEADER = colors.HexColor('#1565c0')
COLOR_HEADER_DARK = colors.HexColor('#0d47a1')
COLOR_FILA_ALT = colors.HexColor('#fafafa')
COLOR_ACCENT = colors.HexColor('#1565c0')
COLOR_ROJO = colors.HexColor('#c62828')
COLOR_NARANJA = colors.HexColor('#e65100')
COLOR_AZUL_BAJO = colors.HexColor('#1565c0')
COLOR_VERDE = colors.HexColor('#2e7d32')

# Alias legacy (por compatibilidad)
COLOR_AZUL_OSCURO = COLOR_HEADER_DARK
COLOR_AZUL_MEDIO = COLOR_HEADER
COLOR_HEADER_BG = colors.HexColor('#e3f2fd')
COLOR_GRIS_CLARO = COLOR_FILA_ALT


# ===========================================================================
# FUNCIONES PUBLICAS
# ===========================================================================

def mostrar_opciones_impresion_gtt(parent):
    """
    Muestra un dialogo simple para que el operador elija si incluir la grafica.
    Returns:
        'con_grafica' | 'sin_grafica' | None (cancelado)
    """
    import tkinter as tk
    from tkinter import ttk

    result = [None]

    win = tk.Toplevel(parent)
    win.title("Opciones de Impresión - Curva GTT")
    win.resizable(False, False)
    win.configure(bg='white')
    win.geometry("380x220")
    win.grab_set()

    tk.Label(win, text="📊 Opciones de Impresión",
             font=('Segoe UI', 13, 'bold'), bg='white',
             fg='#1565c0').pack(pady=(18, 6))

    tk.Label(win, text="¿Desea incluir la gráfica de la curva de glucemia\nen el reporte impreso?",
             font=('Segoe UI', 10), bg='white', justify='center').pack(pady=6)

    tk.Label(win,
             text="Con gráfica: la prueba ocupa una hoja completa (recomendado)",
             font=('Segoe UI', 8), bg='white', fg='#555').pack()

    btn_frame = tk.Frame(win, bg='white')
    btn_frame.pack(pady=18)

    def _elegir(opcion):
        result[0] = opcion
        win.destroy()

    tk.Button(btn_frame, text="📈 Con Gráfica (hoja completa)",
              font=('Segoe UI', 10, 'bold'), bg='#1565c0', fg='white',
              relief='flat', padx=18, pady=8, cursor='hand2',
              command=lambda: _elegir('con_grafica')).pack(side='left', padx=6)

    tk.Button(btn_frame, text="📄 Solo Tabla",
              font=('Segoe UI', 10), bg='#e2e8f0', fg='#333',
              relief='flat', padx=18, pady=8, cursor='hand2',
              command=lambda: _elegir('sin_grafica')).pack(side='left', padx=6)

    tk.Button(btn_frame, text="Cancelar",
              font=('Segoe UI', 9), bg='#fafafa', fg='#666',
              relief='flat', padx=10, pady=6, cursor='hand2',
              command=lambda: _elegir(None)).pack(side='left', padx=6)

    parent.wait_window(win)
    return result[0]


def generar_pdf_gtt(db, detalle_id, filename, config_lab=None,
                    ruta_logo=None, bioanalista=None,
                    incluir_grafica=True):
    """
    Genera el PDF del resultado GTT con el MISMO formato visual
    del reporte general de resultados de ANgesLAB.
    """
    if not REPORTLAB_OK:
        raise ImportError("reportlab no esta instalado. Ejecute: pip install reportlab")

    # --- Obtener datos del detalle y solicitud ---
    det = db.query_one(f"""
        SELECT d.DetalleID, d.SolicitudID, d.PruebaID, d.Estado,
               p.CodigoPrueba, p.NombrePrueba
        FROM DetalleSolicitudes d
        LEFT JOIN Pruebas p ON d.PruebaID = p.PruebaID
        WHERE d.DetalleID = {detalle_id}
    """)
    if not det:
        return False

    sol = db.query_one(f"""
        SELECT s.*,
               pac.Nombres, pac.Apellidos, pac.NumeroDocumento,
               pac.FechaNacimiento, pac.Sexo, pac.Telefono1,
               med.Nombres & ' ' & med.Apellidos AS Medico
        FROM (Solicitudes s
        LEFT JOIN Pacientes pac ON s.PacienteID = pac.PacienteID)
        LEFT JOIN Medicos med ON s.MedicoID = med.MedicoID
        WHERE s.SolicitudID = {det['SolicitudID']}
    """)
    if not sol:
        return False

    # --- Obtener valores GTT ---
    codigos_gtt = ['GTT000', 'GTT001', 'GTT002', 'GTT003',
                   'GTT004', 'GTT005', 'GTT006', 'GTT007', 'GTT008']
    valores = {}
    for codigo in codigos_gtt:
        param = db.query_one(
            f"SELECT ParametroID FROM Parametros WHERE CodigoParametro = '{codigo}'"
        )
        if not param:
            continue
        rp = db.query_one(
            f"SELECT Valor, ValorReferencia, FueraDeRango, TipoAlerta "
            f"FROM ResultadosParametros "
            f"WHERE DetalleID = {detalle_id} AND ParametroID = {param['ParametroID']}"
        )
        if rp:
            valores[codigo] = rp

    # --- Info del paciente ---
    nombre_pac = f"{sol.get('Nombres') or ''} {sol.get('Apellidos') or ''}".strip().upper() or 'N/A'
    cedula = sol.get('NumeroDocumento') or 'N/A'
    sexo = 'Masculino' if sol.get('Sexo') == 'M' else 'Femenino' if sol.get('Sexo') == 'F' else 'N/A'
    medico = sol.get('Medico') or 'Particular'
    fecha_sol = sol['FechaSolicitud'].strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'
    num_orden = sol.get('NumeroSolicitud') or 'N/A'
    tel_pac = sol.get('Telefono1') or ''

    edad_texto = 'N/A'
    if sol.get('FechaNacimiento'):
        try:
            fn = sol['FechaNacimiento']
            hoy = datetime.now()
            edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            edad_texto = f"{edad} Años"
        except Exception:
            pass

    # --- Info del laboratorio ---
    nombre_lab = (config_lab or {}).get('NombreLaboratorio', 'LABORATORIO CLÍNICO')
    direccion_lab = (config_lab or {}).get('Direccion', '')
    email_lab = (config_lab or {}).get('Email', '')
    telefono_lab = (config_lab or {}).get('Telefono1', '')
    telefono2_lab = (config_lab or {}).get('Telefono2', '')

    # Color configurable
    color_header_hex = (config_lab or {}).get('ColorEncabezadoTabla', '#1565c0') or '#1565c0'
    _pdf_header = colors.HexColor(color_header_hex)
    _pdf_header_dark = colors.HexColor('#0d47a1')
    _pdf_accent = _pdf_header

    dosis_str = ''
    dosis_rp = valores.get('GTT000')
    if dosis_rp:
        dosis_str = str(dosis_rp.get('Valor') or '').strip()

    # =========================================================================
    # CONSTRUCCION DEL PDF — MISMO FORMATO QUE generar_pdf_resultados
    # =========================================================================
    page_size = letter
    page_w, page_h = page_size

    left_m = 0.5 * inch
    right_m = 0.5 * inch
    top_m = 0.4 * inch
    bot_m = 1.2 * inch if bioanalista else 0.6 * inch
    header_h = 2.0 * inch
    content_w = page_w - left_m - right_m

    # Fuentes unificadas con el reporte principal
    _fln = 11       # nombre lab
    _fld = 7.5      # detalle lab
    _lh = 10        # line height info
    _flbl = 7.5     # label paciente
    _fval = 7.5     # valor paciente
    _fo_label = 10   # label orden
    _fo_valor = 12   # numero orden
    _fn_pac = 11     # nombre paciente

    # Colores de etiquetas
    _lbl_color = colors.HexColor('#607d8b')
    _val_color = colors.HexColor('#212121')

    # --- Header: mismo estilo que el reporte general ---
    def draw_header(canvas, doc):
        canvas.saveState()
        y_top = page_h - top_m
        right_edge = page_w - right_m

        # ── LOGO ──
        logo_w = 2.2 * inch
        logo_h = 2.2 * inch
        logo_x = left_m
        logo_y = y_top - logo_h + 57
        if ruta_logo and os.path.exists(ruta_logo) and (config_lab or {}).get('MostrarLogo'):
            try:
                canvas.drawImage(ruta_logo, logo_x, logo_y,
                                 width=logo_w, height=logo_h,
                                 preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        # ── INFO LAB (derecha) ──
        info_y = y_top - 0.05 * inch
        canvas.setFont('Helvetica-Bold', _fln)
        canvas.setFillColor(colors.HexColor('#1a237e'))
        canvas.drawRightString(right_edge, info_y, nombre_lab.upper())

        canvas.setFont('Helvetica', _fld)
        canvas.setFillColor(colors.HexColor('#455a64'))
        info_y -= _lh + 2
        if direccion_lab:
            canvas.drawRightString(right_edge, info_y, direccion_lab[:80])
            info_y -= _lh
        if telefono_lab:
            canvas.drawRightString(right_edge, info_y, f"Telf.: {telefono_lab}")
            info_y -= _lh
        if telefono2_lab:
            canvas.drawRightString(right_edge, info_y, f"WhatsApp: {telefono2_lab}")
            info_y -= _lh
        if email_lab:
            canvas.setFillColor(colors.HexColor('#1565c0'))
            canvas.drawRightString(right_edge, info_y, email_lab)
            info_y -= _lh

        # ── LÍNEA SEPARADORA ──
        _info_h = 0.85 * inch
        _sep1_y = y_top - _info_h - 0.08 * inch
        canvas.setStrokeColor(colors.HexColor('#e0e0e0'))
        canvas.setLineWidth(0.5)
        canvas.line(left_m, _sep1_y, right_edge, _sep1_y)

        # ── NÚMERO DE ORDEN ──
        _orden_y = _sep1_y - 0.17 * inch
        canvas.setFillColor(colors.HexColor('#37474f'))
        canvas.setFont('Helvetica-Bold', _fo_label)
        canvas.drawString(left_m, _orden_y, "ORDEN NO.")
        _orden_label_w = canvas.stringWidth("ORDEN NO.  ", 'Helvetica-Bold', _fo_label)
        canvas.setFillColor(colors.HexColor('#1a237e'))
        canvas.setFont('Helvetica-Bold', _fo_valor)
        canvas.drawString(left_m + _orden_label_w, _orden_y, str(num_orden))

        # ── NOMBRE PACIENTE ──
        _nombre_y = _orden_y - 0.20 * inch
        canvas.setFillColor(colors.black)
        canvas.setFont('Helvetica-Bold', _fn_pac)
        canvas.drawString(left_m, _nombre_y, nombre_pac[:50])

        # ── BARRA DE COLOR ──
        _bar_y = _nombre_y - 0.10 * inch
        canvas.setStrokeColor(_pdf_accent)
        canvas.setLineWidth(3.0)
        canvas.line(left_m, _bar_y, right_edge, _bar_y)

        # ── DATOS DEL PACIENTE (2 columnas) ──
        _row_sp = 0.14 * inch
        _col2_x = left_m + content_w * 0.52

        def _draw_field(x, y, label, value):
            canvas.setFillColor(_lbl_color)
            canvas.setFont('Helvetica', _flbl)
            canvas.drawString(x, y, label)
            lbl_w = canvas.stringWidth(label + " ", 'Helvetica', _flbl)
            canvas.setFillColor(_val_color)
            canvas.setFont('Helvetica-Bold', _fval)
            canvas.drawString(x + lbl_w, y, value)

        _dy = _bar_y - 0.16 * inch
        _draw_field(left_m, _dy, "Cédula:", cedula)
        _draw_field(_col2_x, _dy, "Fecha de ingreso:", fecha_sol)
        _dy -= _row_sp
        _draw_field(left_m, _dy, "Sexo:", sexo)
        _draw_field(_col2_x, _dy, "Médico:", medico[:35])
        _dy -= _row_sp
        _draw_field(left_m, _dy, "Edad:", edad_texto)
        if tel_pac:
            _draw_field(_col2_x, _dy, "Teléfono:", tel_pac[:14])
        _dy -= _row_sp + 0.06 * inch

        # ── TÍTULO CENTRADO ──
        canvas.setFillColor(colors.HexColor('#37474f'))
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(page_w / 2, _dy, "Informe de resultados")
        _dy -= 0.10 * inch
        canvas.setStrokeColor(colors.HexColor('#bdbdbd'))
        canvas.setLineWidth(0.5)
        canvas.line(left_m, _dy, right_edge, _dy)

        canvas.restoreState()

    # --- Footer: firma bioanalista + pie de página ---
    def draw_footer(canvas, doc):
        canvas.saveState()
        right_edge = page_w - right_m

        if bioanalista:
            bx_bio = page_w / 2
            y_pos = 0.38 * inch + 0.85 * inch

            # Firma imagen
            ruta_firma = bioanalista.get('RutaFirma', '')
            if ruta_firma:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                ruta_abs = os.path.join(base_dir, '..', ruta_firma)
                if os.path.exists(ruta_abs):
                    try:
                        fw = 2.2 * inch
                        fh = 0.8 * inch
                        canvas.drawImage(ruta_abs, bx_bio - fw / 2, y_pos,
                                         width=fw, height=fh,
                                         preserveAspectRatio=True, mask='auto')
                        y_pos -= 0.05 * inch
                    except Exception:
                        pass

            # Línea de firma
            canvas.setStrokeColor(colors.grey)
            canvas.setLineWidth(0.5)
            lw = 1.5 * inch
            canvas.line(bx_bio - lw / 2, y_pos, bx_bio + lw / 2, y_pos)
            y_pos -= 0.12 * inch

            canvas.setFont('Helvetica-Bold', 7)
            canvas.drawCentredString(bx_bio, y_pos, bioanalista.get('NombreCompleto', ''))
            y_pos -= 0.11 * inch
            canvas.setFont('Helvetica', 6.5)
            canvas.drawCentredString(bx_bio, y_pos, f"C.I.: {bioanalista.get('Cedula', '')}")
            y_pos -= 0.1 * inch
            canvas.drawCentredString(bx_bio, y_pos, f"Reg.: {bioanalista.get('NumeroRegistro', '')}")
            y_pos -= 0.09 * inch
            canvas.setFont('Helvetica-Oblique', 6)
            canvas.drawCentredString(bx_bio, y_pos, "Bioanalista - Área Química")

        # ── PIE DE PÁGINA (misma línea que el reporte general) ──
        _pie_y = 0.22 * inch
        canvas.setStrokeColor(colors.HexColor('#e0e0e0'))
        canvas.setLineWidth(0.3)
        canvas.line(left_m, _pie_y + 0.08 * inch, right_edge, _pie_y + 0.08 * inch)

        canvas.setFont('Helvetica', 5.5)
        canvas.setFillColor(colors.HexColor('#9e9e9e'))
        _pie_texto = (f"Orden No: {num_orden}  -  {nombre_pac}"
                      f"  |  Valores de referencia reportados según edad y sexo del paciente")
        canvas.drawString(left_m, _pie_y, _pie_texto)
        canvas.drawRightString(right_edge, _pie_y, f"Página {doc.page}")

        canvas.restoreState()

    def header_footer(canvas, doc):
        draw_header(canvas, doc)
        draw_footer(canvas, doc)

    doc = BaseDocTemplate(filename, pagesize=page_size)
    content_frame = Frame(
        left_m, bot_m,
        content_w,
        page_h - top_m - header_h - bot_m,
        id='content'
    )
    page_tmpl = PageTemplate(id='gtt', frames=[content_frame], onPage=header_footer)
    doc.addPageTemplates([page_tmpl])

    styles = getSampleStyleSheet()
    elements = []

    # ---- Título de la prueba (mismo formato que titulo_prueba_style del reporte general) ----
    titulo_style = ParagraphStyle(
        'TituloGTT', parent=styles['Normal'],
        fontSize=11, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=8, spaceBefore=12,
        leading=13,
        textColor=_pdf_header_dark,
        borderWidth=0,
        borderColor=_pdf_accent,
        borderPadding=(2, 4, 2, 4),
    )
    elements.append(Paragraph("CURVA DE GLUCEMIA - TOLERANCIA A LA GLUCOSA", titulo_style))
    elements.append(Spacer(1, 0.08 * inch))

    # ---- Dosis de carga ----
    if dosis_str:
        dosis_style = ParagraphStyle(
            'Dosis', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica',
            alignment=TA_CENTER, spaceAfter=6,
            textColor=_pdf_accent,
        )
        elements.append(Paragraph(
            f"<b>Dosis de Carga Glucosada:</b> {dosis_str} g",
            dosis_style
        ))

    # ---- Tabla de resultados (idéntico al formato de _flush_area_pdf del reporte general) ----
    col_w = [2.5 * inch, 1.2 * inch, 0.8 * inch, 2.0 * inch]

    # Header de columnas (tabla separada, mismo estilo que el reporte general)
    header_data = [['Descripción del Examen', 'Resultado', 'Unidad', 'Valores Referenciales']]
    header_table = Table(header_data, colWidths=col_w)
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BACKGROUND', (0, 0), (-1, 0), _pdf_header),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
    ]))

    param_data = []
    for codigo, etiqueta, minutos, referencia in TIEMPOS_DISPLAY:
        rp = valores.get(codigo)
        if not rp:
            continue
        valor_str = str(rp.get('Valor') or '').strip()
        if not valor_str:
            continue
        param_data.append(['   ' + etiqueta, valor_str, 'mg/dL', referencia])

    if param_data:
        param_table = Table(param_data, colWidths=col_w)
        table_style = [
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
            ('LEFTPADDING', (0, 0), (0, -1), 8),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdbdbd')),
            ('LINEBELOW', (0, -1), (-1, -1), 0.8, colors.HexColor('#37474f')),
            ('LINEBELOW', (0, 0), (-1, -2), 0.25, colors.HexColor('#e0e0e0')),
        ]
        # Filas alternas
        for i in range(len(param_data)):
            if i % 2 == 1:
                table_style.append(('BACKGROUND', (0, i), (-1, i), COLOR_FILA_ALT))
        param_table.setStyle(TableStyle(table_style))

        elements.append(header_table)
        elements.append(param_table)
        elements.append(Spacer(1, 0.1 * inch))

    # ---- Interpretacion y observaciones ----
    interp_rp = valores.get('GTT007')
    obs_rp = valores.get('GTT008')
    interp_val = str((interp_rp or {}).get('Valor') or '').strip()
    obs_val = str((obs_rp or {}).get('Valor') or '').strip()

    if interp_val or obs_val:
        interp_style = ParagraphStyle(
            'InterpGTT', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica',
            spaceAfter=3,
        )
        if interp_val:
            elements.append(Paragraph(
                f"<b>Interpretación:</b> {interp_val}", interp_style))
        if obs_val:
            elements.append(Paragraph(
                f"<b>Observaciones:</b> {obs_val}", interp_style))
        elements.append(Spacer(1, 0.08 * inch))

    # ---- Grafica de la curva ----
    if incluir_grafica:
        img_grafica = _generar_imagen_grafica(valores, dosis_str)
        if img_grafica:
            grafica_w = content_w - 0.3 * inch
            grafica_h = 3.3 * inch
            elements.append(Paragraph(
                "Gráfica de la Curva de Glucemia",
                ParagraphStyle('GraficaTitulo', parent=styles['Normal'],
                               fontSize=9, fontName='Helvetica-Bold',
                               textColor=_pdf_accent, spaceAfter=3,
                               spaceBefore=6, alignment=TA_CENTER)
            ))
            elements.append(RLImage(img_grafica, width=grafica_w, height=grafica_h))
            elements.append(Spacer(1, 0.06 * inch))

            nota_style = ParagraphStyle(
                'NotaGTT', parent=styles['Normal'],
                fontSize=7, fontName='Helvetica-Oblique',
                textColor=colors.HexColor('#9e9e9e'), alignment=TA_CENTER,
            )
            elements.append(Paragraph(
                "Referencia ADA: Basal &lt;100 mg/dL (normal), 100-125 (IFG); "
                "2h &lt;140 mg/dL (normal), 140-199 (IGT), ≥200 (Diabetes).",
                nota_style
            ))

    # ---- Construir PDF ----
    doc.build(elements)
    return True


# ===========================================================================
# GENERACION DE LA IMAGEN DE LA GRAFICA (matplotlib -> bytes -> PIL -> RL)
# ===========================================================================

def _generar_imagen_grafica(valores, dosis_str='75'):
    """
    Genera la grafica de la curva usando matplotlib y la retorna como
    un objeto BytesIO compatible con reportlab Image.
    Returns None si matplotlib o PIL no estan disponibles, o no hay datos.
    """
    if not MATPLOTLIB_OK:
        return None

    # Recolectar puntos con valor
    tiempos_min = {
        'GTT001': 0, 'GTT002': 30, 'GTT003': 60,
        'GTT004': 120, 'GTT005': 180, 'GTT006': 240
    }
    etiquetas_x = {
        0: 'Basal', 30: '30 min', 60: '1 h',
        120: '2 h', 180: '3 h', 240: '4 h'
    }

    puntos = []
    for codigo, etq, minutos, _ in [
        ('GTT001', 'Basal',    0,   None),
        ('GTT002', '30 min',   30,  None),
        ('GTT003', '1 hora',   60,  None),
        ('GTT004', '2 horas',  120, None),
        ('GTT005', '3 horas',  180, None),
        ('GTT006', '4 horas',  240, None),
    ]:
        rp = valores.get(codigo)
        if not rp:
            continue
        val_str = str(rp.get('Valor') or '').strip().replace(',', '.')
        try:
            val = float(val_str)
            puntos.append((minutos, val, codigo))
        except (ValueError, TypeError):
            continue

    if len(puntos) < 1:
        return None

    # ---- Crear figura ----
    fig, ax = plt.subplots(figsize=(9, 4.5), dpi=120)
    fig.patch.set_facecolor('white')
    ax.set_facecolor('#fafafa')

    xs = [m for m, v, _ in puntos]
    ys = [v for m, v, _ in puntos]

    # Lineas de referencia
    ref_lines = [
        (100, '#4caf50', '--', '100 mg/dL (Normal basal)'),
        (140, '#ff9800', '--', '140 mg/dL (Límite 2h normal)'),
        (180, '#f44336', ':', '180 mg/dL (Límite 1h)'),
        (200, '#b71c1c', ':', '200 mg/dL (Umbral DM)'),
    ]
    for ref_y, col, ls, lbl in ref_lines:
        ax.axhline(y=ref_y, color=col, linestyle=ls, linewidth=1.2,
                   alpha=0.75, label=lbl)

    # Zona normal
    ax.axhspan(70, 100, alpha=0.07, color='green')

    # Curva
    if len(xs) >= 2:
        ax.plot(xs, ys, 'o-', color='#1565c0', linewidth=2.5,
                markersize=7, markerfacecolor='#1565c0',
                markeredgecolor='white', markeredgewidth=1.5,
                label='Glucemia del paciente', zorder=5)
    else:
        ax.plot(xs, ys, 'o', color='#1565c0', markersize=9,
                markerfacecolor='#1565c0',
                markeredgecolor='white', markeredgewidth=1.5,
                label='Glucemia del paciente', zorder=5)

    # Etiquetas de valor sobre cada punto
    for m, v, codigo in puntos:
        fuera_rango = bool((valores.get(codigo) or {}).get('FueraDeRango'))
        tipo_alerta = str((valores.get(codigo) or {}).get('TipoAlerta') or '')
        if fuera_rango and 'Critico' in tipo_alerta:
            color_txt = '#c62828'
        elif fuera_rango:
            color_txt = '#e65100'
        else:
            color_txt = '#1a237e'
        ax.annotate(f'{v:.1f}',
                    xy=(m, v),
                    xytext=(0, 12),
                    textcoords='offset points',
                    ha='center', fontsize=9, fontweight='bold',
                    color=color_txt,
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              edgecolor=color_txt, alpha=0.8))

    # Eje X
    todos_x = sorted(set(list(tiempos_min.values())))
    ax.set_xticks(todos_x)
    ax.set_xticklabels([etiquetas_x.get(t, str(t)) for t in todos_x], fontsize=9)

    # Limites Y dinamicos
    all_vals = ys + [100, 140, 180, 200]
    y_min = max(0, min(ys) - 30) if ys else 0
    y_max = max(all_vals) + 30
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(-15, max(todos_x) + 15)

    ax.set_xlabel('Tiempo (minutos)', fontsize=10)
    ax.set_ylabel('Glucosa (mg/dL)', fontsize=10)
    titulo_graf = 'Curva de Glucemia - Tolerancia a la Glucosa'
    if dosis_str:
        titulo_graf += f' (Carga: {dosis_str} g)'
    ax.set_title(titulo_graf, fontsize=11, fontweight='bold',
                 color='#1a237e', pad=8)

    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.grid(axis='x', alpha=0.15)

    ax.legend(loc='upper right', fontsize=7.5, framealpha=0.9,
              ncol=2, handlelength=1.5)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    fig.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return buf


# ===========================================================================
# VERIFICACION DE DISPONIBILIDAD
# ===========================================================================

def verificar_dependencias():
    """Retorna dict con estado de dependencias necesarias para GTT."""
    return {
        'reportlab': REPORTLAB_OK,
        'matplotlib': MATPLOTLIB_OK,
        'PIL': PIL_OK,
    }

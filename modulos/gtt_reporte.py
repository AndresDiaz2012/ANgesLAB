# -*- coding: utf-8 -*-
"""
gtt_reporte.py - Generador de reporte PDF para la Prueba de Tolerancia a la Glucosa
======================================================================================
Genera un informe PDF en hoja completa (letter) con:
  - Encabezado del laboratorio y datos del paciente
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

COLOR_AZUL_OSCURO = colors.HexColor('#1a237e')
COLOR_AZUL_MEDIO  = colors.HexColor('#1565c0')
COLOR_HEADER_BG   = colors.HexColor('#e3f2fd')
COLOR_ROJO        = colors.HexColor('#c62828')
COLOR_NARANJA     = colors.HexColor('#e65100')
COLOR_AZUL_BAJO   = colors.HexColor('#1565c0')
COLOR_VERDE       = colors.HexColor('#2e7d32')
COLOR_GRIS_CLARO  = colors.HexColor('#f5f5f5')


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
    Genera el PDF del resultado GTT.

    Args:
        db: objeto Database
        detalle_id: ID del detalle de la solicitud
        filename: ruta del archivo PDF de salida
        config_lab: dict de configuracion del laboratorio (o None)
        ruta_logo: ruta al logo (o None)
        bioanalista: dict del bioanalista responsable (o None)
        incluir_grafica: bool - si True, incluye la grafica y usa pagina completa

    Returns:
        True si exito, False si error
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
            edad_texto = f"{edad} años"
        except Exception:
            pass

    # --- Info del laboratorio ---
    nombre_lab = (config_lab or {}).get('NombreLaboratorio', 'LABORATORIO CLÍNICO')
    direccion_lab = (config_lab or {}).get('Direccion', '')
    email_lab = (config_lab or {}).get('Email', '')
    telefono_lab = (config_lab or {}).get('Telefono1', '')
    telefono2_lab = (config_lab or {}).get('Telefono2', '')

    dosis_str = ''
    dosis_rp = valores.get('GTT000')
    if dosis_rp:
        dosis_str = str(dosis_rp.get('Valor') or '').strip()

    # =========================================================================
    # CONSTRUCCION DEL PDF
    # =========================================================================
    page_size = letter
    page_w, page_h = page_size

    left_m  = 0.5 * inch
    right_m = 0.5 * inch
    top_m   = 0.4 * inch
    bot_m   = 1.2 * inch if bioanalista else 0.6 * inch
    header_h = 1.9 * inch

    # --- Funciones de dibujo de cabecera y pie ---
    def draw_header(canvas, doc):
        canvas.saveState()
        y_top = page_h - top_m

        # Logo
        logo_w = 1.1 * inch
        logo_h = 0.9 * inch
        logo_x = left_m
        logo_y = y_top - logo_h - 0.1*inch
        if ruta_logo and os.path.exists(ruta_logo) and (config_lab or {}).get('MostrarLogo'):
            try:
                canvas.drawImage(ruta_logo, logo_x, logo_y,
                                 width=logo_w, height=logo_h,
                                 preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        # Nombre lab
        info_x = left_m + logo_w + 0.25*inch
        info_y = y_top - 0.15*inch
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawString(info_x, info_y, nombre_lab.upper())
        canvas.setFont('Helvetica', 8)
        lh = 11
        iy = info_y - lh
        if direccion_lab:
            canvas.drawString(info_x, iy, direccion_lab[:75])
            iy -= lh
        if email_lab:
            canvas.drawString(info_x, iy, f"Correo: {email_lab}")
            iy -= lh
        tel_txt = ''
        if telefono_lab:
            tel_txt = f"Tel: {telefono_lab}"
        if telefono2_lab:
            tel_txt += f"  WhatsApp: {telefono2_lab}"
        if tel_txt:
            canvas.drawString(info_x, iy, tel_txt)
            iy -= lh
        canvas.setFont('Helvetica-Oblique', 7)
        canvas.drawString(info_x, iy, "Impreso por ANgesLAB - Sistema de Gestión de Laboratorio")

        # Cuadro paciente
        bx = left_m
        bw = page_w - left_m - right_m
        bh = 0.68 * inch
        by = y_top - logo_h - 0.32*inch
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1)
        canvas.rect(bx, by - bh, bw, bh)

        c1x = bx + 0.1*inch
        c2x = bx + 2.4*inch
        c3x = bx + 5.0*inch
        r1y = by - 0.18*inch
        r2y = r1y - 0.21*inch
        r3y = r2y - 0.21*inch

        canvas.setFont('Helvetica-Bold', 8)
        for (cx, txt) in [(c1x, 'NOMBRE:'), (c1x, None)]:
            break
        for (cx, ry, label) in [
            (c1x, r1y, 'NOMBRE:'), (c1x, r2y, 'CÉDULA:'), (c1x, r3y, 'EDAD:'),
            (c2x, r1y, 'GÉNERO:'), (c2x, r2y, 'MÉDICO:'),
            (c3x, r1y, 'FECHA:'),  (c3x, r2y, 'N° ORDEN:'), (c3x, r3y, 'TELÉFONO:'),
        ]:
            canvas.drawString(cx, ry, label)

        off = 0.55*inch
        canvas.setFont('Helvetica', 8)
        for (cx, ry, val) in [
            (c1x, r1y, nombre_pac[:35]), (c1x, r2y, cedula), (c1x, r3y, edad_texto),
            (c2x, r1y, sexo), (c2x, r2y, medico[:24]),
            (c3x, r1y, fecha_sol), (c3x, r2y, str(num_orden)[:18]),
            (c3x, r3y, tel_pac[:14]),
        ]:
            canvas.drawString(cx + off, ry, val)

        canvas.restoreState()

    def draw_footer(canvas, doc):
        if not bioanalista:
            return
        canvas.saveState()
        fy = bot_m - 0.1*inch
        bx_bio = page_w / 2  # centrado

        y_pos = fy + 0.85*inch

        # Firma imagen si existe
        ruta_firma = bioanalista.get('RutaFirma', '')
        if ruta_firma:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ruta_abs = os.path.join(base_dir, '..', ruta_firma)
            if os.path.exists(ruta_abs):
                try:
                    fw = 1.1*inch
                    fh = 0.38*inch
                    canvas.drawImage(ruta_abs, bx_bio - fw/2, y_pos,
                                     width=fw, height=fh,
                                     preserveAspectRatio=True, mask='auto')
                    y_pos -= 0.03*inch
                except Exception:
                    pass

        # Linea
        canvas.setStrokeColor(colors.grey)
        canvas.setLineWidth(0.5)
        lw = 1.5*inch
        canvas.line(bx_bio - lw/2, y_pos, bx_bio + lw/2, y_pos)
        y_pos -= 0.11*inch

        canvas.setFont('Helvetica-Bold', 7.5)
        canvas.drawCentredString(bx_bio, y_pos, bioanalista.get('NombreCompleto', ''))
        y_pos -= 0.1*inch
        canvas.setFont('Helvetica', 7)
        canvas.drawCentredString(bx_bio, y_pos, f"C.I.: {bioanalista.get('Cedula', '')}")
        y_pos -= 0.1*inch
        canvas.drawCentredString(bx_bio, y_pos, f"Reg.: {bioanalista.get('NumeroRegistro', '')}")
        y_pos -= 0.09*inch
        canvas.setFont('Helvetica-Oblique', 6.5)
        canvas.drawCentredString(bx_bio, y_pos, "Bioanalista - Área Química")
        canvas.restoreState()

    def header_footer(canvas, doc):
        draw_header(canvas, doc)
        draw_footer(canvas, doc)

    doc = BaseDocTemplate(filename, pagesize=page_size)
    content_frame = Frame(
        left_m, bot_m,
        page_w - left_m - right_m,
        page_h - top_m - header_h - bot_m,
        id='content'
    )
    page_tmpl = PageTemplate(id='gtt', frames=[content_frame], onPage=header_footer)
    doc.addPageTemplates([page_tmpl])

    styles = getSampleStyleSheet()
    elements = []

    # ---- Estilo titulo prueba ----
    titulo_style = ParagraphStyle(
        'TituloGTT', parent=styles['Heading1'],
        fontSize=12, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=6, spaceBefore=4,
        textColor=colors.white, backColor=COLOR_AZUL_OSCURO,
        borderPadding=(7, 7, 7, 7),
    )
    elements.append(Paragraph("CURVA DE GLUCEMIA - PRUEBA DE TOLERANCIA A LA GLUCOSA", titulo_style))
    elements.append(Spacer(1, 0.12*inch))

    # ---- Dosis de carga ----
    dosis_style = ParagraphStyle(
        'Dosis', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold',
        alignment=TA_CENTER, spaceAfter=8,
        textColor=COLOR_AZUL_MEDIO,
    )
    if dosis_str:
        elements.append(Paragraph(
            f"Dosis de Carga Glucosada: <b>{dosis_str} g</b>",
            dosis_style
        ))

    # ---- Tabla de resultados ----
    col_w = [(2.3*inch), (1.3*inch), (1.3*inch), (2.4*inch)]
    tabla_header = [['Tiempo', 'Resultado', 'Unidad', 'Valor de Referencia']]

    tabla_data = list(tabla_header)
    estilos_filas = []

    for row_idx, (codigo, etiqueta, minutos, referencia) in enumerate(TIEMPOS_DISPLAY, start=1):
        rp = valores.get(codigo)
        valor_str = ''
        fuera = False
        tipo_alerta = ''
        if rp:
            valor_str = str(rp.get('Valor') or '').strip()
            fuera = bool(rp.get('FueraDeRango'))
            tipo_alerta = str(rp.get('TipoAlerta') or '')

        if not valor_str:
            continue  # Omitir tiempos no capturados

        unidad_str = 'mg/dL'
        fila = [etiqueta, valor_str, unidad_str, referencia]
        tabla_data.append(fila)

        # Colorear segun alerta
        if fuera and 'Critico' in tipo_alerta:
            estilos_filas.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), COLOR_ROJO))
            estilos_filas.append(('FONTNAME', (1, row_idx), (1, row_idx), 'Helvetica-Bold'))
            estilos_filas.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#fff3e0')))
        elif fuera and 'Alto' in tipo_alerta:
            estilos_filas.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), COLOR_NARANJA))
            estilos_filas.append(('FONTNAME', (1, row_idx), (1, row_idx), 'Helvetica-Bold'))
            estilos_filas.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor('#fff8f0')))
        elif fuera and 'Bajo' in tipo_alerta:
            estilos_filas.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), COLOR_AZUL_BAJO))
            estilos_filas.append(('FONTNAME', (1, row_idx), (1, row_idx), 'Helvetica-Bold'))
        else:
            estilos_filas.append(('TEXTCOLOR', (1, row_idx), (1, row_idx), COLOR_VERDE))

    tabla_style_base = [
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_AZUL_MEDIO),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_GRIS_CLARO]),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
    ] + estilos_filas

    if len(tabla_data) > 1:
        tabla_rl = Table(tabla_data, colWidths=col_w)
        tabla_rl.setStyle(TableStyle(tabla_style_base))
        elements.append(tabla_rl)
        elements.append(Spacer(1, 0.15*inch))

    # ---- Interpretacion y observaciones ----
    interp_rp = valores.get('GTT007')
    obs_rp = valores.get('GTT008')
    interp_val = str((interp_rp or {}).get('Valor') or '').strip()
    obs_val = str((obs_rp or {}).get('Valor') or '').strip()

    if interp_val or obs_val:
        interp_style = ParagraphStyle(
            'InterpGTT', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica',
            spaceAfter=4, spaceBefore=4,
        )
        label_style = ParagraphStyle(
            'LabelGTT', parent=styles['Normal'],
            fontSize=9, fontName='Helvetica-Bold',
            textColor=COLOR_AZUL_OSCURO,
        )
        if interp_val:
            elements.append(Paragraph("Interpretación:", label_style))
            elements.append(Paragraph(interp_val, interp_style))
        if obs_val:
            elements.append(Paragraph("Observaciones:", label_style))
            elements.append(Paragraph(obs_val, interp_style))
        elements.append(Spacer(1, 0.1*inch))

    # ---- Grafica de la curva ----
    if incluir_grafica:
        img_grafica = _generar_imagen_grafica(valores, dosis_str)
        if img_grafica:
            # Calcular ancho disponible
            disp_w = page_w - left_m - right_m
            grafica_h = 3.5 * inch
            grafica_w = disp_w - 0.2*inch
            elements.append(Paragraph("Gráfica de la Curva de Glucemia", ParagraphStyle(
                'GraficaTitulo', parent=styles['Normal'],
                fontSize=9, fontName='Helvetica-Bold',
                textColor=COLOR_AZUL_MEDIO, spaceAfter=4, spaceBefore=6,
                alignment=TA_CENTER,
            )))
            elements.append(RLImage(img_grafica, width=grafica_w, height=grafica_h))
            elements.append(Spacer(1, 0.08*inch))

            # Leyenda interpretativa
            nota_style = ParagraphStyle(
                'NotaGTT', parent=styles['Normal'],
                fontSize=7.5, fontName='Helvetica-Oblique',
                textColor=colors.grey, alignment=TA_CENTER,
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

    puntos = []  # (minutos, valor, codigo)
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
    max_x = max(xs) if xs else 240
    ref_lines = [
        (100, '#4caf50', '--', '100 mg/dL (Normal basal)'),
        (140, '#ff9800', '--', '140 mg/dL (Límite 2h normal)'),
        (180, '#f44336', ':', '180 mg/dL (Límite 1h)'),
        (200, '#b71c1c', ':', '200 mg/dL (Umbral DM)'),
    ]
    for ref_y, col, ls, lbl in ref_lines:
        ax.axhline(y=ref_y, color=col, linestyle=ls, linewidth=1.2,
                   alpha=0.75, label=lbl)

    # Zona normal (0-100 base)
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

    # Eje X con etiquetas personalizadas
    todos_x = sorted(set(list(tiempos_min.values())))
    ax.set_xticks(todos_x)
    ax.set_xticklabels([etiquetas_x.get(t, str(t)) for t in todos_x],
                       fontsize=9)

    # Limites Y dinamicos
    all_vals = ys + [100, 140, 180, 200]
    y_min = max(0, min(ys) - 30) if ys else 0
    y_max = max(all_vals) + 30
    ax.set_ylim(y_min, y_max)
    ax.set_xlim(-15, max(todos_x) + 15)

    # Etiquetas
    ax.set_xlabel('Tiempo (minutos)', fontsize=10)
    ax.set_ylabel('Glucosa (mg/dL)', fontsize=10)
    titulo_graf = 'Curva de Glucemia - Tolerancia a la Glucosa'
    if dosis_str:
        titulo_graf += f' (Carga: {dosis_str} g)'
    ax.set_title(titulo_graf, fontsize=11, fontweight='bold',
                 color='#1a237e', pad=8)

    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.grid(axis='x', alpha=0.15)

    # Leyenda
    ax.legend(loc='upper right', fontsize=7.5, framealpha=0.9,
              ncol=2, handlelength=1.5)

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    fig.tight_layout(pad=0.5)

    # Exportar a BytesIO
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

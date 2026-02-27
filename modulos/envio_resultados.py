# -*- coding: utf-8 -*-
"""
MODULO DE ENVIO DE RESULTADOS - ANgesLAB
Genera PDF de resultados y permite enviarlos por WhatsApp o Email
"""

import os
import tempfile
import webbrowser
import smtplib
import urllib.parse
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm, mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False


class GeneradorPDF:
    """Generador de reportes PDF con diseño limpio y compacto."""

    # --- Paleta de colores ---
    COLOR_PRIMARIO = '#2c3e50'       # Azul oscuro (titulos prueba)
    COLOR_ACENTO = '#3498db'         # Azul claro (linea separadora, acentos)
    COLOR_HEADER_BG = '#f0f3f5'      # Gris muy claro (fondo encabezados tabla)
    COLOR_FILA_ALT = '#f8fafb'       # Gris imperceptible (filas alternas)
    COLOR_LINEA = '#d5dce3'          # Gris suave (lineas horizontales)
    COLOR_TEXTO = '#2c3e50'          # Texto principal
    COLOR_TEXTO_CLARO = '#7f8c8d'    # Texto secundario / pie

    # --- Dimensiones ---
    MARGEN = 1.0 * cm               # Margenes de pagina
    ANCHO_UTIL = 19.56 * cm - 2 * MARGEN  # letter width (21.59cm) - margenes

    def __init__(self, db):
        self.db = db
        self._cargar_config()

    def _cargar_config(self):
        try:
            config = self.db.query_one("SELECT * FROM ConfiguracionLaboratorio")
            if not config:
                config = self.db.query_one("SELECT * FROM ConfiguracionSistema")
            self.lab_nombre = (config.get('NombreLaboratorio') or 'LABORATORIO CLINICO') if config else 'LABORATORIO CLINICO'
            self.lab_direccion = (config.get('Direccion') or '') if config else ''
            self.lab_rif = (config.get('RIF') or '') if config else ''
            self.lab_telefono = (config.get('Telefono1') or config.get('Telefono') or '') if config else ''
            self.lab_whatsapp = (config.get('WhatsApp') or '') if config else ''
        except:
            self.lab_nombre = 'LABORATORIO CLINICO'
            self.lab_direccion = ''
            self.lab_rif = ''
            self.lab_telefono = ''
            self.lab_whatsapp = ''

    # ------------------------------------------------------------------
    # Encabezado del laboratorio (compacto, sin bordes pesados)
    # ------------------------------------------------------------------
    def _generar_encabezado_pdf(self):
        elems = []
        aw = self.ANCHO_UTIL

        # Nombre del laboratorio
        elems.append(Paragraph(
            f"<b>{self.lab_nombre}</b>",
            ParagraphStyle('Titulo', fontSize=13, leading=15,
                           alignment=TA_CENTER, spaceAfter=1,
                           textColor=colors.HexColor(self.COLOR_PRIMARIO))))

        # RIF + Direccion en una sola linea si caben
        info_parts = []
        if self.lab_rif:
            info_parts.append(f"RIF: {self.lab_rif}")
        if self.lab_direccion:
            info_parts.append(self.lab_direccion)
        if info_parts:
            elems.append(Paragraph(
                " &bull; ".join(info_parts),
                ParagraphStyle('Info', fontSize=7.5, leading=9,
                               alignment=TA_CENTER, spaceAfter=1,
                               textColor=colors.HexColor(self.COLOR_TEXTO_CLARO))))

        # Contacto
        contacto_parts = []
        if self.lab_telefono:
            contacto_parts.append(f"Tel: {self.lab_telefono}")
        if self.lab_whatsapp:
            contacto_parts.append(f"WhatsApp: {self.lab_whatsapp}")
        if contacto_parts:
            elems.append(Paragraph(
                " | ".join(contacto_parts),
                ParagraphStyle('Contacto', fontSize=7.5, leading=9,
                               alignment=TA_CENTER, spaceAfter=2,
                               textColor=colors.HexColor(self.COLOR_TEXTO_CLARO))))

        # Linea separadora fina
        elems.append(Spacer(1, 2*mm))
        elems.append(HRFlowable(
            width="100%", thickness=0.8, color=colors.HexColor(self.COLOR_ACENTO),
            spaceAfter=3*mm, spaceBefore=0))

        return elems

    # ------------------------------------------------------------------
    # Obtener datos de la solicitud
    # ------------------------------------------------------------------
    def _obtener_datos_solicitud(self, solicitud_id):
        solicitud = self.db.query_one(f"""
            SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, s.EstadoSolicitud,
                   p.Nombres, p.Apellidos, p.NumeroDocumento, p.Sexo, p.Edad,
                   m.Nombres as MedicoNombres, m.Apellidos as MedicoApellidos
            FROM (Solicitudes s
            LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID)
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)
        if not solicitud:
            raise Exception(f"Solicitud {solicitud_id} no encontrada")
        return solicitud

    # ------------------------------------------------------------------
    # Construir elementos del reporte (metodo compartido)
    # ------------------------------------------------------------------
    def _construir_elementos(self, solicitud_id, solicitud):
        elementos = []
        aw = self.ANCHO_UTIL

        # Estilos reutilizables
        s_label = ParagraphStyle('lbl', fontSize=7.5, leading=9,
                                  fontName='Helvetica-Bold',
                                  textColor=colors.HexColor(self.COLOR_TEXTO_CLARO))
        s_value = ParagraphStyle('val', fontSize=8.5, leading=10,
                                  fontName='Helvetica',
                                  textColor=colors.HexColor(self.COLOR_TEXTO))

        nombre_pac = 'Sin paciente asignado'
        if solicitud.get('Nombres') and solicitud.get('Apellidos'):
            nombre_pac = f"{solicitud['Nombres']} {solicitud['Apellidos']}"

        nombre_med = 'Particular'
        if solicitud.get('MedicoNombres') and solicitud.get('MedicoApellidos'):
            nombre_med = f"{solicitud['MedicoNombres']} {solicitud['MedicoApellidos']}"

        numero_sol = str(solicitud.get('NumeroSolicitud', f'SOL-{solicitud_id}')).replace('/', '-').replace('\\', '-')
        fecha_sol = solicitud.get('FechaSolicitud')
        fecha_str = fecha_sol.strftime('%d/%m/%Y') if fecha_sol else 'N/A'

        # ============================================================
        # Encabezado del laboratorio
        # ============================================================
        elementos += self._generar_encabezado_pdf()

        # Titulo del reporte
        elementos.append(Paragraph(
            "<b>REPORTE DE RESULTADOS</b>",
            ParagraphStyle('TitRep', fontSize=10, leading=12,
                           alignment=TA_CENTER, spaceAfter=8,
                           textColor=colors.HexColor(self.COLOR_PRIMARIO))))

        # ============================================================
        # Datos del paciente (estilo limpio sin bordes)
        # ============================================================
        col_lbl = 2.0 * cm
        col_val1 = (aw / 2) - col_lbl
        col_val2 = (aw / 2) - col_lbl

        datos_pac = [
            [Paragraph('Solicitud:', s_label), Paragraph(f'<b>{numero_sol}</b>', s_value),
             Paragraph('Fecha:', s_label), Paragraph(fecha_str, s_value)],
            [Paragraph('Paciente:', s_label), Paragraph(f'<b>{nombre_pac}</b>', s_value),
             Paragraph('Documento:', s_label), Paragraph(str(solicitud.get('NumeroDocumento') or 'N/A'), s_value)],
            [Paragraph('Sexo:', s_label), Paragraph(solicitud.get('Sexo') or 'N/A', s_value),
             Paragraph('Edad:', s_label), Paragraph(str(solicitud.get('Edad') or 'N/A'), s_value)],
            [Paragraph('Medico:', s_label), Paragraph(nombre_med, s_value),
             Paragraph('', s_label), Paragraph('', s_value)],
        ]

        t_pac = Table(datos_pac, colWidths=[col_lbl, col_val1, col_lbl, col_val2])
        t_pac.setStyle(TableStyle([
            # Sin bordes exteriores ni grid
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Linea sutil debajo de cada fila
            ('LINEBELOW', (0, 0), (-1, -2), 0.3, colors.HexColor('#e8ecef')),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, colors.HexColor(self.COLOR_LINEA)),
        ]))
        elementos.append(t_pac)
        elementos.append(Spacer(1, 5 * mm))

        # ============================================================
        # Pruebas y resultados
        # ============================================================
        try:
            pruebas = self.db.query(f"""
                SELECT d.DetalleID, pr.NombrePrueba, a.NombreArea
                FROM (DetalleSolicitudes d
                LEFT JOIN Pruebas pr ON d.PruebaID = pr.PruebaID)
                LEFT JOIN Areas a ON pr.AreaID = a.AreaID
                WHERE d.SolicitudID = {solicitud_id}
            """)

            if pruebas:
                for idx_prueba, prueba in enumerate(pruebas):
                    # --- Titulo de la prueba (barra compacta) ---
                    elementos.append(Table(
                        [[Paragraph(
                            f"<b>{prueba.get('NombrePrueba', 'Prueba')}</b>",
                            ParagraphStyle('PT', fontSize=8.5, leading=10,
                                           textColor=colors.white))]],
                        colWidths=[aw],
                        style=[
                            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(self.COLOR_PRIMARIO)),
                            ('TOPPADDING', (0, 0), (-1, -1), 4),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                            ('LEFTPADDING', (0, 0), (-1, -1), 8),
                        ]))

                    # --- Resultados de esta prueba ---
                    try:
                        resultados = self.db.query(f"""
                            SELECT r.ValorNumerico, r.ValorTexto, r.ValorReferencia,
                                   param.NombreParametro, u.Simbolo
                            FROM (ResultadosParametros r
                            LEFT JOIN Parametros param ON r.ParametroID = param.ParametroID)
                            LEFT JOIN Unidades u ON r.UnidadID = u.UnidadID
                            WHERE r.DetalleID = {prueba['DetalleID']}
                        """)

                        if resultados:
                            # Columnas: Parametro | Resultado | Unidad | Referencia
                            c1 = aw * 0.36   # Parametro
                            c2 = aw * 0.18   # Resultado
                            c3 = aw * 0.14   # Unidad
                            c4 = aw * 0.32   # Referencia
                            col_widths = [c1, c2, c3, c4]

                            # Header de la tabla de resultados
                            s_th = ParagraphStyle('th', fontSize=7.5, leading=9,
                                                   fontName='Helvetica-Bold',
                                                   textColor=colors.HexColor(self.COLOR_TEXTO))
                            header_row = [
                                Paragraph('PARAMETRO', s_th),
                                Paragraph('RESULTADO', s_th),
                                Paragraph('UNIDAD', s_th),
                                Paragraph('REFERENCIA', s_th),
                            ]
                            datos_res = [header_row]

                            s_td = ParagraphStyle('td', fontSize=8, leading=9.5,
                                                   fontName='Helvetica',
                                                   textColor=colors.HexColor(self.COLOR_TEXTO))
                            s_td_bold = ParagraphStyle('tdb', fontSize=8, leading=9.5,
                                                        fontName='Helvetica-Bold',
                                                        textColor=colors.HexColor(self.COLOR_TEXTO))

                            for r in resultados:
                                valor = r.get('ValorNumerico') or r.get('ValorTexto') or '---'
                                datos_res.append([
                                    Paragraph(str(r.get('NombreParametro') or ''), s_td),
                                    Paragraph(str(valor), s_td_bold),
                                    Paragraph(str(r.get('Simbolo') or ''), s_td),
                                    Paragraph(str(r.get('ValorReferencia') or ''), s_td),
                                ])

                            tabla_res = Table(datos_res, colWidths=col_widths)

                            # Estilo limpio: solo lineas horizontales, sin grid vertical
                            estilo_res = [
                                # Fondo del encabezado
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(self.COLOR_HEADER_BG)),
                                # Linea debajo del header
                                ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.HexColor(self.COLOR_ACENTO)),
                                # Padding compacto
                                ('TOPPADDING', (0, 0), (-1, -1), 2.5),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
                                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                # Alineacion: resultado centrado
                                ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                                ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                            ]

                            # Lineas horizontales sutiles entre filas de datos
                            for i in range(1, len(datos_res) - 1):
                                estilo_res.append(
                                    ('LINEBELOW', (0, i), (-1, i), 0.25, colors.HexColor('#e4e8eb')))

                            # Filas alternas con fondo sutil
                            for i in range(2, len(datos_res), 2):
                                estilo_res.append(
                                    ('BACKGROUND', (0, i), (-1, i), colors.HexColor(self.COLOR_FILA_ALT)))

                            # Linea de cierre al final de la tabla
                            estilo_res.append(
                                ('LINEBELOW', (0, -1), (-1, -1), 0.4, colors.HexColor(self.COLOR_LINEA)))

                            tabla_res.setStyle(TableStyle(estilo_res))
                            elementos.append(tabla_res)
                    except:
                        pass

                    # Espaciado entre secciones de prueba
                    elementos.append(Spacer(1, 4 * mm))
            else:
                elementos.append(Paragraph(
                    "No hay pruebas registradas para esta solicitud.",
                    ParagraphStyle('NoPruebas', fontSize=8)))
        except:
            elementos.append(Paragraph(
                "No se pudieron cargar las pruebas.",
                ParagraphStyle('Error', fontSize=8)))

        # ============================================================
        # Firma (compacta) - Bioanalistas por area
        # ============================================================
        elementos.append(Spacer(1, 8 * mm))

        # Intentar obtener bioanalistas de las areas de las pruebas
        bioanalistas_firma = []
        try:
            # Obtener areas unicas de las pruebas de esta solicitud
            areas_pruebas = self.db.query(f"""
                SELECT DISTINCT pr.AreaID
                FROM DetalleSolicitudes d
                LEFT JOIN Pruebas pr ON d.PruebaID = pr.PruebaID
                WHERE d.SolicitudID = {solicitud_id} AND pr.AreaID IS NOT NULL
            """)
            if areas_pruebas:
                areas_ids = [str(a['AreaID']) for a in areas_pruebas if a.get('AreaID')]
                if areas_ids:
                    areas_str = ','.join(areas_ids)
                    bioanalistas_firma = self.db.query(
                        f"SELECT b.NombreCompleto, b.Cedula, b.NumeroRegistro, "
                        f"b.RutaFirma, a.NombreArea "
                        f"FROM Bioanalistas b LEFT JOIN Areas a ON b.AreaID = a.AreaID "
                        f"WHERE b.AreaID IN ({areas_str}) AND b.Activo = True "
                        f"ORDER BY b.NombreCompleto"
                    )
        except Exception:
            bioanalistas_firma = []

        if bioanalistas_firma:
            # Mostrar firmas de bioanalistas reales
            firma_rows = []
            for bio in bioanalistas_firma[:3]:
                nombre = bio.get('NombreCompleto', '')
                cedula = bio.get('Cedula', '')
                registro = bio.get('NumeroRegistro', '')
                area = bio.get('NombreArea', '')

                # Imagen de firma si existe
                ruta_firma = bio.get('RutaFirma', '')
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ruta_abs_firma = os.path.join(base_dir, ruta_firma) if ruta_firma else ''

                firma_img_elem = ''
                if ruta_abs_firma and os.path.exists(ruta_abs_firma):
                    try:
                        from reportlab.platypus import Image as RLImage
                        firma_img_elem = RLImage(ruta_abs_firma, width=2.5*cm, height=0.9*cm)
                        firma_img_elem.hAlign = 'CENTER'
                    except Exception:
                        firma_img_elem = ''

                # Construir bloque de firma
                sig_style = ParagraphStyle('sig', fontSize=7, alignment=TA_CENTER)
                sig_name = ParagraphStyle('sigN', fontSize=7.5, leading=9,
                                          fontName='Helvetica-Bold', alignment=TA_CENTER,
                                          textColor=colors.HexColor(self.COLOR_TEXTO))
                sig_detail = ParagraphStyle('sigD', fontSize=6.5, leading=8,
                                            alignment=TA_CENTER,
                                            textColor=colors.HexColor(self.COLOR_TEXTO_CLARO))

                bloque_data = []
                if firma_img_elem:
                    bloque_data.append([firma_img_elem])
                bloque_data.append([Paragraph('_' * 40, sig_style)])
                bloque_data.append([Paragraph(f'<b>{nombre}</b>', sig_name)])
                bloque_data.append([Paragraph(f'C.I.: {cedula}', sig_detail)])
                bloque_data.append([Paragraph(f'Reg.: {registro}', sig_detail)])
                if area:
                    bloque_data.append([Paragraph(f'Bioanalista - {area}', sig_detail)])

                bloque = Table(bloque_data, colWidths=[5.0 * cm],
                               style=[
                                   ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                   ('TOPPADDING', (0, 0), (-1, -1), 1),
                                   ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                               ])
                firma_rows.append(bloque)

            # Organizar firmas lado a lado
            if len(firma_rows) == 1:
                elementos.append(Table([[firma_rows[0]]], colWidths=[self.ANCHO_UTIL],
                                       style=[('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
            else:
                col_w = self.ANCHO_UTIL / len(firma_rows)
                elementos.append(Table([firma_rows], colWidths=[col_w] * len(firma_rows),
                                       style=[('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                              ('VALIGN', (0, 0), (-1, -1), 'BOTTOM')]))
        else:
            # Fallback: firma genérica
            elementos.append(Table(
                [[Paragraph('_' * 45, ParagraphStyle('sig', fontSize=7, alignment=TA_CENTER))],
                 [Paragraph('Bioanalista Responsable',
                            ParagraphStyle('sigT', fontSize=7.5, leading=9,
                                           alignment=TA_CENTER,
                                           textColor=colors.HexColor(self.COLOR_TEXTO_CLARO)))]],
                colWidths=[5.5 * cm],
                style=[
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('TOPPADDING', (0, 0), (-1, -1), 1),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
                ]))

        # ============================================================
        # Pie de pagina
        # ============================================================
        elementos.append(Spacer(1, 3 * mm))
        elementos.append(HRFlowable(
            width="60%", thickness=0.3, color=colors.HexColor('#d5dce3'),
            spaceAfter=2*mm, spaceBefore=0))
        elementos.append(Paragraph(
            f"Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
            ParagraphStyle('Pie', fontSize=6.5, leading=8,
                           alignment=TA_CENTER,
                           textColor=colors.HexColor(self.COLOR_TEXTO_CLARO))))

        return elementos, numero_sol

    # ------------------------------------------------------------------
    # Generar PDF de resultados (ruta automatica o destino)
    # ------------------------------------------------------------------
    def generar_pdf_resultados(self, solicitud_id, ruta_destino=None):
        if not REPORTLAB_DISPONIBLE:
            raise Exception("reportlab no instalado")

        solicitud = self._obtener_datos_solicitud(solicitud_id)
        elementos, numero_sol = self._construir_elementos(solicitud_id, solicitud)

        nombre_archivo = f"Resultados_{numero_sol}.pdf"
        if ruta_destino:
            ruta_pdf = os.path.join(ruta_destino, nombre_archivo)
        else:
            ruta_pdf = os.path.join(tempfile.gettempdir(), nombre_archivo)

        doc = SimpleDocTemplate(ruta_pdf, pagesize=letter,
                               rightMargin=self.MARGEN, leftMargin=self.MARGEN,
                               topMargin=self.MARGEN, bottomMargin=self.MARGEN)
        doc.build(elementos)
        return ruta_pdf

    # ------------------------------------------------------------------
    # Generar PDF en ruta especifica
    # ------------------------------------------------------------------
    def generar_pdf_en_ruta(self, solicitud_id, ruta_archivo):
        """Genera el PDF directamente en la ruta de archivo especificada."""
        if not REPORTLAB_DISPONIBLE:
            raise Exception("reportlab no instalado")

        solicitud = self._obtener_datos_solicitud(solicitud_id)
        elementos, _ = self._construir_elementos(solicitud_id, solicitud)

        doc = SimpleDocTemplate(ruta_archivo, pagesize=letter,
                               rightMargin=self.MARGEN, leftMargin=self.MARGEN,
                               topMargin=self.MARGEN, bottomMargin=self.MARGEN)
        doc.build(elementos)
        return ruta_archivo


class EnviadorResultados:
    def __init__(self, db):
        self.db = db
        self.generador_pdf = GeneradorPDF(db)
        self._cargar_config()

    def _cargar_config(self):
        try:
            config = self.db.query_one("SELECT * FROM ConfiguracionSistema")
            self.lab_nombre = config.get('NombreLaboratorio', 'Laboratorio') if config else 'Laboratorio'
        except:
            self.lab_nombre = 'Laboratorio'

    def obtener_datos_paciente(self, solicitud_id):
        return self.db.query_one(f"""
            SELECT p.Nombres & ' ' & p.Apellidos as NombrePaciente,
                   p.Telefono1, p.Email, s.NumeroSolicitud
            FROM Solicitudes s
            LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
            WHERE s.SolicitudID = {solicitud_id}
        """)

    def enviar_whatsapp(self, solicitud_id, mensaje_personalizado=None):
        datos = self.obtener_datos_paciente(solicitud_id)

        if not datos:
            return {'exito': False, 'mensaje': 'Solicitud no encontrada', 'telefono': None}

        telefono = datos.get('Telefono1', '')
        if not telefono:
            return {'exito': False, 'mensaje': 'El paciente no tiene teléfono registrado', 'telefono': None}

        # Limpiar teléfono
        telefono_limpio = ''.join(filter(str.isdigit, str(telefono)))

        nombre = datos.get('NombrePaciente', 'Paciente') or 'Paciente'
        numero_sol = datos.get('NumeroSolicitud', '')

        mensaje = f"Estimado(a) {nombre},\n\n"
        mensaje += f"Sus resultados de laboratorio (Solicitud: {numero_sol}) están disponibles.\n\n"
        if mensaje_personalizado:
            mensaje += f"{mensaje_personalizado}\n\n"
        mensaje += f"Atentamente,\n{self.lab_nombre}"

        url = f"https://wa.me/{telefono_limpio}?text={urllib.parse.quote(mensaje)}"

        try:
            webbrowser.open(url)
            return {'exito': True, 'mensaje': f'WhatsApp abierto para {nombre}', 'telefono': telefono}
        except Exception as e:
            return {'exito': False, 'mensaje': str(e), 'telefono': telefono}

    def generar_y_guardar_pdf(self, solicitud_id, ruta_destino):
        try:
            if not os.path.exists(ruta_destino):
                os.makedirs(ruta_destino)
            ruta_pdf = self.generador_pdf.generar_pdf_resultados(solicitud_id, ruta_destino)
            return {'exito': True, 'mensaje': 'PDF generado', 'ruta': ruta_pdf}
        except Exception as e:
            return {'exito': False, 'mensaje': str(e), 'ruta': None}

    def guardar_pdf_en_archivo(self, solicitud_id, ruta_archivo):
        """Guarda el PDF en una ruta de archivo específica (path completo con nombre)"""
        try:
            # Crear directorio si no existe
            directorio = os.path.dirname(ruta_archivo)
            if directorio and not os.path.exists(directorio):
                os.makedirs(directorio)

            # Generar PDF directamente en la ruta especificada
            ruta_pdf = self.generador_pdf.generar_pdf_en_ruta(solicitud_id, ruta_archivo)
            return {'exito': True, 'mensaje': 'PDF guardado correctamente', 'ruta': ruta_pdf}
        except Exception as e:
            return {'exito': False, 'mensaje': str(e), 'ruta': None}

    def abrir_pdf(self, solicitud_id):
        try:
            ruta_pdf = self.generador_pdf.generar_pdf_resultados(solicitud_id)
            if os.name == 'nt':
                os.startfile(ruta_pdf)
            else:
                webbrowser.open('file://' + ruta_pdf)
            return {'exito': True, 'mensaje': 'PDF abierto', 'ruta': ruta_pdf}
        except Exception as e:
            return {'exito': False, 'mensaje': str(e), 'ruta': None}

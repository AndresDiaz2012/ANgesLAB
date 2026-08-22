# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE ETIQUETAS DE MUESTRAS - ANgesLAB
================================================================================
Generación de etiquetas para tubos/muestras de laboratorio.
Inspirado en SICOEXC (etiqueta.rpt, etiquetahe.rpt, etiquetaaz.rpt, etc.).

Funcionalidades:
- Generación de etiquetas PDF para impresión
- Código de barras por solicitud (Code128)
- Código QR de consulta para el paciente (portal de resultados)
- Etiquetas por área con color identificativo
- Impresión en hoja carta (cortables) o formato etiqueta

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import logging
from datetime import datetime

_log = logging.getLogger("angeslab.etiquetas")

# Verificar disponibilidad de ReportLab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, black, white
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.graphics.barcode import code128
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.graphics import renderPDF
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False
    _log.warning("ReportLab no disponible - etiquetas deshabilitadas")

import os
import tempfile

# Portal de resultados QR (opcional - la etiqueta funciona sin él)
try:
    from modulos.portal_resultados import crear_gestor_portal, qr_imagereader
    PORTAL_DISPONIBLE = True
except ImportError:
    try:
        from portal_resultados import crear_gestor_portal, qr_imagereader
        PORTAL_DISPONIBLE = True
    except ImportError:
        PORTAL_DISPONIBLE = False


# Colores por área (matching ANgesLAB areas)
COLORES_AREA = {
    1:  {'nombre': 'Hematología',    'abrev': 'HEM', 'color': '#e53935', 'color_texto': '#ffffff'},  # Rojo
    2:  {'nombre': 'Química',        'abrev': 'QUI', 'color': '#1e88e5', 'color_texto': '#ffffff'},  # Azul
    5:  {'nombre': 'Coagulación',    'abrev': 'COA', 'color': '#8e24aa', 'color_texto': '#ffffff'},  # Púrpura
    6:  {'nombre': 'Uroanálisis',    'abrev': 'URO', 'color': '#f9a825', 'color_texto': '#000000'},  # Amarillo
    7:  {'nombre': 'Parasitología',  'abrev': 'PAR', 'color': '#6d4c41', 'color_texto': '#ffffff'},  # Marrón
    8:  {'nombre': 'Hormonas',       'abrev': 'HOR', 'color': '#00acc1', 'color_texto': '#ffffff'},  # Cyan
    9:  {'nombre': 'Serología',      'abrev': 'SER', 'color': '#e91e63', 'color_texto': '#ffffff'},  # Rosa
    10: {'nombre': 'Microbiología',  'abrev': 'MIC', 'color': '#43a047', 'color_texto': '#ffffff'},  # Verde
    11: {'nombre': 'Pruebas Especiales', 'abrev': 'ESP', 'color': '#5e35b1', 'color_texto': '#ffffff'},  # Violeta
    12: {'nombre': 'Infecciosas',    'abrev': 'INF', 'color': '#ef6c00', 'color_texto': '#ffffff'},  # Naranja
    13: {'nombre': 'Inmunológicas',  'abrev': 'INM', 'color': '#00897b', 'color_texto': '#ffffff'},  # Verde azulado
    14: {'nombre': 'Renal',          'abrev': 'REN', 'color': '#3949ab', 'color_texto': '#ffffff'},  # Indigo
    29: {'nombre': 'General',        'abrev': 'GEN', 'color': '#546e7a', 'color_texto': '#ffffff'},  # Gris
}

# Área por defecto para IDs no mapeados
AREA_DEFAULT = {'nombre': 'Otro', 'abrev': '???', 'color': '#9e9e9e', 'color_texto': '#000000'}


# Formatos de impresión disponibles
FORMATO_TICKET = 'ticket'   # rollo de 80 mm, una etiqueta por página
FORMATO_HOJA = 'hoja'       # hoja carta con 30 etiquetas cortables


class GeneradorEtiquetas:
    """Genera etiquetas PDF para muestras de laboratorio."""

    # ── Formato ticket (impresora de rollo, igual que el recibo) ──────────
    TICKET_ANCHO = 226          # 80 mm en puntos
    TICKET_MARGEN = 8
    # 2.4 cm deja ~0.8 mm por módulo: legible incluso impreso a 203 dpi
    TICKET_QR = 2.4 * cm        # lado del QR en el ticket
    TICKET_BARRAS_ALTO = 5 * mm

    # ── Formato hoja carta (3 columnas x 10 filas = 30 etiquetas) ─────────
    COLS = 3
    FILAS = 10
    ETIQUETA_ANCHO = 6.5 * cm
    ETIQUETA_ALTO = 2.5 * cm
    MARGEN_H = 0.8 * cm
    MARGEN_V = 0.5 * cm
    QR_LADO = 1.5 * cm          # lado del QR impreso en la etiqueta
    QR_MARGEN = 0.15 * cm       # separación del QR al borde derecho

    def __init__(self, db, portal=None, formato=FORMATO_TICKET):
        self.db = db
        self.formato = formato
        self._config_lab = None
        # Gestor del portal de resultados: genera el enlace que abre el QR.
        # Si el módulo no está disponible la etiqueta se imprime sin QR.
        self.portal = portal
        if self.portal is None and PORTAL_DISPONIBLE:
            try:
                self.portal = crear_gestor_portal(db)
            except Exception as e:
                _log.warning("Portal QR no disponible para etiquetas: %s", e)
                self.portal = None

    # ------------------------------------------------------------------
    # Datos comunes
    # ------------------------------------------------------------------
    def _nombre_laboratorio(self):
        """Nombre del laboratorio para el encabezado del ticket."""
        if self._config_lab is None:
            try:
                cfg = self.db.query_one(
                    "SELECT TOP 1 NombreLaboratorio FROM [ConfiguracionLaboratorio]")
                self._config_lab = (cfg or {}).get('NombreLaboratorio') or ''
            except Exception:
                self._config_lab = ''
        return self._config_lab

    @staticmethod
    def _datos_paciente(solicitud):
        """Extrae los campos del paciente que se imprimen en la etiqueta."""
        fecha = solicitud.get('FechaSolicitud', datetime.now())
        fecha_str = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') \
            else str(fecha)

        edad_str = ''
        fn = solicitud.get('FechaNacimiento')
        if fn and hasattr(fn, 'year'):
            hoy = datetime.now()
            edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            edad_str = f"{edad} años"

        return {
            'nombre': f"{solicitud.get('Nombres', '')} "
                      f"{solicitud.get('Apellidos', '')}".strip(),
            'cedula': solicitud.get('NumeroDocumento', '') or '',
            'num_solicitud': solicitud.get('NumeroSolicitud', '') or '',
            'fecha': fecha_str,
            'sexo': solicitud.get('Sexo', '') or '',
            'edad': edad_str,
        }

    def _qr_solicitud(self, solicitud):
        """
        Genera el QR de consulta del paciente para una solicitud.

        Devuelve un ImageReader listo para el canvas, o None si el portal
        o las librerías de QR no están disponibles.
        """
        if not (self.portal and PORTAL_DISPONIBLE):
            return None
        try:
            fecha = solicitud.get('FechaSolicitud')
            fecha_str = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') \
                else str(fecha or '')[:10]
            nombre = (f"{solicitud.get('Nombres', '')} "
                      f"{solicitud.get('Apellidos', '')}").strip()
            contenido = self.portal.contenido_qr(
                solicitud.get('SolicitudID'),
                numero_solicitud=solicitud.get('NumeroSolicitud', ''),
                fecha=fecha_str,
                paciente=nombre,
                cedula=solicitud.get('NumeroDocumento', ''),
            )
            return qr_imagereader(contenido, size_px=180)
        except Exception as e:
            _log.warning("QR de etiqueta no generado: %s", e)
            return None

    def generar_etiquetas_solicitud(self, solicitud_id: int,
                                     ruta_salida: str = None) -> str:
        """
        Genera PDF con etiquetas para todas las pruebas de una solicitud.

        Args:
            solicitud_id: ID de la solicitud
            ruta_salida: Ruta del PDF (None = temporal)

        Returns:
            Ruta del archivo PDF generado
        """
        if not REPORTLAB_DISPONIBLE:
            raise RuntimeError("ReportLab no está instalado")

        # Obtener datos de la solicitud
        sol = self.db.query_one(
            f"SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, "
            f"p.Nombres, p.Apellidos, p.NumeroDocumento, p.FechaNacimiento, p.Sexo "
            f"FROM [Solicitudes] AS s "
            f"INNER JOIN [Pacientes] AS p ON s.PacienteID = p.PacienteID "
            f"WHERE s.SolicitudID={int(solicitud_id)}"
        )
        if not sol:
            raise ValueError(f"Solicitud no encontrada: {solicitud_id}")

        # Obtener pruebas con sus áreas
        pruebas = self.db.query(
            f"SELECT ds.DetalleID, pr.NombrePrueba, pr.CodigoPrueba, "
            f"pr.AreaID, a.NombreArea "
            # Access exige paréntesis cuando hay más de un JOIN
            f"FROM ([DetalleSolicitudes] AS ds "
            f"INNER JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID) "
            f"LEFT JOIN [Areas] AS a ON pr.AreaID = a.AreaID "
            f"WHERE ds.SolicitudID={int(solicitud_id)} "
            f"ORDER BY pr.AreaID, pr.NombrePrueba"
        ) or []

        if not pruebas:
            raise ValueError("No hay pruebas en esta solicitud")

        # Agrupar por área (una etiqueta por área, no por prueba)
        areas = {}
        for p in pruebas:
            aid = p.get('AreaID', 0)
            if aid not in areas:
                areas[aid] = {
                    'area_id': aid,
                    'nombre_area': p.get('NombreArea', 'Otro'),
                    'pruebas': [],
                }
            areas[aid]['pruebas'].append(p.get('CodigoPrueba') or p.get('NombrePrueba', ''))

        # Generar PDF
        if not ruta_salida:
            num_sol = sol.get('NumeroSolicitud', f'SOL-{solicitud_id}')
            ruta_salida = os.path.join(
                tempfile.gettempdir(),
                f"Etiquetas_{num_sol}.pdf"
            )

        return self._generar_pdf(sol, list(areas.values()), ruta_salida)

    # ------------------------------------------------------------------
    # Formato ticket (rollo de 80 mm, mismo estilo que el recibo de caja)
    # ------------------------------------------------------------------
    def _filas_ticket(self, datos, pruebas):
        """Pares etiqueta/valor que se imprimen en el ticket."""
        edad_sexo = '  |  '.join(x for x in (datos['edad'], datos['sexo']) if x)
        filas = [
            ("PACIENTE:", datos['nombre']),
            ("C.I.:", datos['cedula']),
        ]
        if edad_sexo:
            filas.append(("EDAD / SEXO:", edad_sexo))
        filas.append(("N° MUESTRA:", datos['num_solicitud']))
        filas.append(("FECHA:", datos['fecha']))
        if pruebas:
            filas.append(("PRUEBAS:", pruebas))
        return filas

    def _alto_ticket(self, n_filas, con_qr, con_lab):
        """Alto exacto que ocupa un ticket con n_filas de datos."""
        alto = 2 * self.TICKET_MARGEN
        if con_lab:
            alto += 11 + 7              # nombre del laboratorio + separador
        alto += 16 + 5                  # banda de área + espacio
        alto += n_filas * 9.5           # filas de datos
        alto += 3 + 1 + 5               # separador inferior
        if con_qr:
            alto += 9                   # rótulo "CONSULTE SUS RESULTADOS"
            alto += self.TICKET_QR + 3
        alto += self.TICKET_BARRAS_ALTO + 8   # código de barras + nº de orden
        return alto

    def _dibujar_ticket(self, c, datos, area_abrev, area_nombre,
                        color_fondo, color_texto, pruebas, qr_img=None):
        """
        Dibuja una etiqueta con el formato del recibo: 80 mm de ancho,
        encabezado centrado, bloque de datos y QR al pie.

        El canvas debe tener ya el tamaño de página devuelto por
        _alto_ticket(); se dibuja de arriba hacia abajo.
        """
        w = self.TICKET_ANCHO
        m = self.TICKET_MARGEN
        ancho_util = w - 2 * m
        nombre_lab = self._nombre_laboratorio()
        filas = self._filas_ticket(datos, pruebas)
        alto = self._alto_ticket(len(filas), qr_img is not None, bool(nombre_lab))
        y = alto - m   # cursor: borde superior del contenido

        def separador(yy):
            c.setStrokeColor(black)
            c.setLineWidth(0.5)
            c.line(m, yy, w - m, yy)

        # ── Encabezado: nombre del laboratorio ────────────────────────────
        if nombre_lab:
            c.setFillColor(black)
            c.setFont('Helvetica-Bold', 9)
            y -= 9
            c.drawCentredString(w / 2, y, self._truncar(
                c, nombre_lab.upper(), 'Helvetica-Bold', 9, ancho_util))
            y -= 2
            separador(y - 2)
            y -= 7

        # ── Banda de color del área ───────────────────────────────────────
        y -= 16
        c.setFillColor(HexColor(color_fondo))
        c.rect(m, y, ancho_util, 16, fill=1, stroke=0)
        c.setFillColor(HexColor(color_texto))
        c.setFont('Helvetica-Bold', 11)
        c.drawString(m + 4, y + 4.5, area_abrev)
        c.setFont('Helvetica', 7.5)
        c.drawRightString(w - m - 4, y + 5, self._truncar(
            c, area_nombre, 'Helvetica', 7.5, ancho_util - 42))
        y -= 5

        # ── Bloque de datos (etiqueta / valor, como el recibo) ────────────
        col_etiq = ancho_util * 0.34
        x_valor = m + col_etiq
        ancho_valor = ancho_util - col_etiq
        c.setFillColor(black)
        for etiqueta, valor in filas:
            y -= 9.5
            c.setFont('Helvetica-Bold', 7)
            c.drawString(m, y, etiqueta)
            c.setFont('Helvetica', 7)
            c.drawString(x_valor, y, self._truncar(
                c, valor, 'Helvetica', 7, ancho_valor))

        y -= 3
        separador(y)
        y -= 5

        # ── QR de consulta de resultados ──────────────────────────────────
        if qr_img is not None:
            c.setFont('Helvetica-Bold', 6.5)
            y -= 7
            c.drawCentredString(w / 2, y, 'CONSULTE SUS RESULTADOS')
            y -= 2
            lado = self.TICKET_QR
            y -= lado
            try:
                c.drawImage(qr_img, (w - lado) / 2, y, width=lado, height=lado,
                            preserveAspectRatio=True, mask='auto')
            except Exception:
                pass
            y -= 3

        # ── Código de barras del número de orden ──────────────────────────
        num = str(datos['num_solicitud'] or '')
        barcode_val = num.replace('-', '')
        y -= self.TICKET_BARRAS_ALTO
        dibujado = False
        if barcode_val:
            try:
                bc = code128.Code128(barcode_val, barWidth=0.6 * mm,
                                     barHeight=self.TICKET_BARRAS_ALTO)
                if bc.width > ancho_util:
                    bc = code128.Code128(barcode_val,
                                         barWidth=0.6 * mm * ancho_util / bc.width,
                                         barHeight=self.TICKET_BARRAS_ALTO)
                bc.drawOn(c, (w - bc.width) / 2, y)
                dibujado = True
            except Exception:
                pass
        if not dibujado:
            c.setFont('Helvetica-Bold', 7)
            c.drawCentredString(w / 2, y + 1, num)
        y -= 8
        c.setFillColor(black)
        c.setFont('Helvetica', 6)
        c.drawCentredString(w / 2, y, num)

    def _generar_pdf_ticket(self, tickets: list, ruta: str) -> str:
        """
        Genera el PDF en formato rollo: una etiqueta por página.

        tickets: lista de dicts con 'datos', 'area_id', 'pruebas' y 'qr'.
        """
        from reportlab.pdfgen import canvas as cv_module

        c = cv_module.Canvas(ruta, pagesize=(self.TICKET_ANCHO, 200))
        emitidas = 0

        for t in tickets:
            color_info = COLORES_AREA.get(t['area_id'], AREA_DEFAULT)
            n_filas = len(self._filas_ticket(t['datos'], t['pruebas']))
            alto = self._alto_ticket(n_filas, t['qr'] is not None,
                                     bool(self._nombre_laboratorio()))
            c.setPageSize((self.TICKET_ANCHO, alto))
            self._dibujar_ticket(
                c, t['datos'],
                area_abrev=color_info['abrev'],
                area_nombre=color_info['nombre'],
                color_fondo=color_info['color'],
                color_texto=color_info['color_texto'],
                pruebas=t['pruebas'],
                qr_img=t['qr'],
            )
            c.showPage()
            emitidas += 1

        c.save()
        _log.info("Etiquetas ticket: %s (%d etiquetas)", ruta, emitidas)
        return ruta

    def _generar_pdf(self, solicitud: dict, areas_pruebas: list,
                      ruta: str) -> str:
        """Genera el PDF con las etiquetas."""
        from reportlab.pdfgen import canvas as cv_module

        # QR de consulta del paciente (el mismo para toda la orden)
        qr_solicitud = self._qr_solicitud(solicitud)

        if self.formato == FORMATO_TICKET:
            datos = self._datos_paciente(solicitud)
            tickets = [{
                'datos': datos,
                'area_id': a['area_id'],
                'pruebas': ', '.join(a['pruebas'][:4]),
                'qr': qr_solicitud,
            } for a in areas_pruebas]
            return self._generar_pdf_ticket(tickets, ruta)

        c = cv_module.Canvas(ruta, pagesize=letter)
        page_w, page_h = letter

        nombre = f"{solicitud.get('Nombres', '')} {solicitud.get('Apellidos', '')}".strip()
        cedula = solicitud.get('NumeroDocumento', '')
        num_sol = solicitud.get('NumeroSolicitud', '')
        fecha = solicitud.get('FechaSolicitud', datetime.now())
        if isinstance(fecha, datetime):
            fecha_str = fecha.strftime('%d/%m/%Y')
        else:
            fecha_str = str(fecha)

        sexo = solicitud.get('Sexo', '')
        fn = solicitud.get('FechaNacimiento')
        edad_str = ''
        if fn and isinstance(fn, datetime):
            hoy = datetime.now()
            edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            edad_str = f"{edad} años"

        qr_img = qr_solicitud

        idx = 0  # índice de etiqueta en la página

        for area_info in areas_pruebas:
            area_id = area_info['area_id']
            color_info = COLORES_AREA.get(area_id, AREA_DEFAULT)

            # Calcular posición en la grilla
            col = idx % self.COLS
            fila = (idx // self.COLS) % self.FILAS

            if idx > 0 and idx % (self.COLS * self.FILAS) == 0:
                c.showPage()  # nueva página

            x = self.MARGEN_H + col * (self.ETIQUETA_ANCHO + 0.3 * cm)
            y = page_h - self.MARGEN_V - (fila + 1) * (self.ETIQUETA_ALTO + 0.2 * cm)

            self._dibujar_etiqueta(
                c, x, y,
                nombre=nombre,
                cedula=cedula,
                num_solicitud=num_sol,
                fecha=fecha_str,
                sexo=sexo,
                edad=edad_str,
                area_abrev=color_info['abrev'],
                area_nombre=color_info['nombre'],
                color_fondo=color_info['color'],
                color_texto=color_info['color_texto'],
                pruebas=', '.join(area_info['pruebas'][:4]),  # Max 4 códigos
                qr_img=qr_img,
            )
            idx += 1

        c.save()
        _log.info("Etiquetas generadas: %s (%d etiquetas)", ruta, idx)
        return ruta

    @staticmethod
    def _truncar(c, texto, fuente, tamano, ancho_max):
        """Recorta un texto para que quepa en ancho_max puntos."""
        texto = str(texto or '')
        if c.stringWidth(texto, fuente, tamano) <= ancho_max:
            return texto
        while texto and c.stringWidth(texto + '...', fuente, tamano) > ancho_max:
            texto = texto[:-1]
        return texto + '...' if texto else ''

    def _dibujar_etiqueta(self, c, x, y, nombre, cedula, num_solicitud,
                           fecha, sexo, edad, area_abrev, area_nombre,
                           color_fondo, color_texto, pruebas, qr_img=None):
        """Dibuja una etiqueta individual en el canvas."""
        w = self.ETIQUETA_ANCHO
        h = self.ETIQUETA_ALTO

        # Borde de la etiqueta
        c.setStrokeColor(HexColor('#cccccc'))
        c.setLineWidth(0.5)
        c.rect(x, y, w, h)

        # Barra de color del área (franja izquierda)
        barra_w = 1.2 * cm
        c.setFillColor(HexColor(color_fondo))
        c.rect(x, y, barra_w, h, fill=1, stroke=0)

        # Abreviatura del área en la barra
        c.setFillColor(HexColor(color_texto))
        c.setFont('Helvetica-Bold', 14)
        c.drawCentredString(x + barra_w / 2, y + h - 1.0 * cm, area_abrev)
        c.setFont('Helvetica', 6)
        c.drawCentredString(x + barra_w / 2, y + h - 1.3 * cm, area_nombre)

        # ── QR de consulta del paciente (columna derecha) ─────────────────
        zona_qr = 0.0
        if qr_img is not None:
            lado = self.QR_LADO
            qr_x = x + w - lado - self.QR_MARGEN
            qr_y = y + (h - lado) / 2 + 1.2 * mm
            try:
                c.drawImage(qr_img, qr_x, qr_y, width=lado, height=lado,
                            preserveAspectRatio=True, mask='auto')
                c.setFillColor(HexColor('#555555'))
                c.setFont('Helvetica-Bold', 4.5)
                c.drawCentredString(qr_x + lado / 2, y + 1.6 * mm,
                                    'MIS RESULTADOS')
                zona_qr = lado + self.QR_MARGEN + 1 * mm
            except Exception:
                zona_qr = 0.0

        # Contenido texto (entre la barra de área y el QR)
        tx = x + barra_w + 2 * mm
        ancho_texto = (x + w) - tx - zona_qr - 1 * mm
        c.setFillColor(black)

        # Nombre del paciente
        c.setFont('Helvetica-Bold', 7)
        c.drawString(tx, y + h - 4 * mm,
                     self._truncar(c, nombre, 'Helvetica-Bold', 7, ancho_texto))

        # Cédula + Sexo + Edad
        c.setFont('Helvetica', 6)
        info_paciente = f"CI: {cedula}"
        if sexo:
            info_paciente += f"  |  {sexo}"
        if edad:
            info_paciente += f"  |  {edad}"
        c.drawString(tx, y + h - 8 * mm,
                     self._truncar(c, info_paciente, 'Helvetica', 6, ancho_texto))

        # Solicitud + Fecha
        c.setFont('Helvetica', 6)
        c.drawString(tx, y + h - 12 * mm,
                     self._truncar(c, f"{num_solicitud}  |  {fecha}",
                                   'Helvetica', 6, ancho_texto))

        # Pruebas
        c.setFont('Helvetica', 5.5)
        c.drawString(tx, y + h - 16 * mm,
                     self._truncar(c, pruebas, 'Helvetica', 5.5, ancho_texto))

        # Código de barras (número de solicitud), ajustado al ancho libre
        try:
            barcode_val = str(num_solicitud or '').replace('-', '')
            if barcode_val and ancho_texto > 5 * mm:
                bc = code128.Code128(barcode_val, barWidth=0.6 * mm,
                                     barHeight=5.5 * mm)
                if bc.width > ancho_texto:
                    factor = ancho_texto / bc.width
                    bc = code128.Code128(barcode_val,
                                         barWidth=0.6 * mm * factor,
                                         barHeight=5.5 * mm)
                bc.drawOn(c, tx, y + 1 * mm)
        except Exception:
            pass  # Si falla el barcode, seguir sin él

    def _solicitud_para_etiqueta(self, sol_id):
        """Datos de la solicitud y sus áreas, para una etiqueta."""
        sol = self.db.query_one(
            f"SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, "
            f"p.Nombres, p.Apellidos, p.NumeroDocumento, p.FechaNacimiento, p.Sexo "
            f"FROM [Solicitudes] AS s "
            f"INNER JOIN [Pacientes] AS p ON s.PacienteID = p.PacienteID "
            f"WHERE s.SolicitudID={int(sol_id)}"
        )
        if not sol:
            return None, {}

        pruebas = self.db.query(
            f"SELECT pr.AreaID, pr.CodigoPrueba, pr.NombrePrueba "
            f"FROM [DetalleSolicitudes] AS ds "
            f"INNER JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID "
            f"WHERE ds.SolicitudID={int(sol_id)} "
            f"ORDER BY pr.AreaID"
        ) or []

        areas = {}
        for p in pruebas:
            aid = p.get('AreaID', 0)
            areas.setdefault(aid, []).append(
                p.get('CodigoPrueba') or p.get('NombrePrueba', ''))
        return sol, areas

    def _generar_batch_ticket(self, solicitud_ids: list, ruta_salida: str) -> str:
        """Batch en formato rollo: una etiqueta por página."""
        tickets = []
        for sol_id in solicitud_ids:
            sol, areas = self._solicitud_para_etiqueta(sol_id)
            if not sol:
                continue
            datos = self._datos_paciente(sol)
            qr_img = self._qr_solicitud(sol)
            for area_id, codigos in areas.items():
                tickets.append({
                    'datos': datos,
                    'area_id': area_id,
                    'pruebas': ', '.join(codigos[:4]),
                    'qr': qr_img,
                })
        return self._generar_pdf_ticket(tickets, ruta_salida)

    def generar_etiquetas_batch(self, solicitud_ids: list,
                                 ruta_salida: str = None) -> str:
        """
        Genera etiquetas para múltiples solicitudes en un solo PDF.

        Args:
            solicitud_ids: Lista de SolicitudIDs
            ruta_salida: Ruta del PDF

        Returns:
            Ruta del PDF generado
        """
        if not REPORTLAB_DISPONIBLE:
            raise RuntimeError("ReportLab no está instalado")

        if not ruta_salida:
            ruta_salida = os.path.join(
                tempfile.gettempdir(),
                f"Etiquetas_Batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            )

        if self.formato == FORMATO_TICKET:
            return self._generar_batch_ticket(solicitud_ids, ruta_salida)

        from reportlab.pdfgen import canvas as cv_module
        c = cv_module.Canvas(ruta_salida, pagesize=letter)
        page_w, page_h = letter

        idx_global = 0

        for sol_id in solicitud_ids:
            sol = self.db.query_one(
                f"SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, "
                f"p.Nombres, p.Apellidos, p.NumeroDocumento, p.FechaNacimiento, p.Sexo "
                f"FROM [Solicitudes] AS s "
                f"INNER JOIN [Pacientes] AS p ON s.PacienteID = p.PacienteID "
                f"WHERE s.SolicitudID={int(sol_id)}"
            )
            if not sol:
                continue

            qr_img = self._qr_solicitud(sol)
            nombre = f"{sol.get('Nombres', '')} {sol.get('Apellidos', '')}".strip()
            cedula = sol.get('NumeroDocumento', '')
            num_sol = sol.get('NumeroSolicitud', '')
            fecha = sol.get('FechaSolicitud', datetime.now())
            fecha_str = fecha.strftime('%d/%m/%Y') if isinstance(fecha, datetime) else str(fecha)
            sexo = sol.get('Sexo', '')
            fn = sol.get('FechaNacimiento')
            edad_str = ''
            if fn and isinstance(fn, datetime):
                hoy = datetime.now()
                edad_str = f"{hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))} años"

            # Obtener áreas de la solicitud
            pruebas = self.db.query(
                f"SELECT pr.AreaID, pr.CodigoPrueba, pr.NombrePrueba "
                f"FROM [DetalleSolicitudes] AS ds "
                f"INNER JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID "
                f"WHERE ds.SolicitudID={int(sol_id)} "
                f"ORDER BY pr.AreaID"
            ) or []

            areas = {}
            for p in pruebas:
                aid = p.get('AreaID', 0)
                if aid not in areas:
                    areas[aid] = []
                areas[aid].append(p.get('CodigoPrueba') or p.get('NombrePrueba', ''))

            for area_id, codigos in areas.items():
                col = idx_global % self.COLS
                fila = (idx_global // self.COLS) % self.FILAS

                if idx_global > 0 and idx_global % (self.COLS * self.FILAS) == 0:
                    c.showPage()

                x = self.MARGEN_H + col * (self.ETIQUETA_ANCHO + 0.3 * cm)
                y = page_h - self.MARGEN_V - (fila + 1) * (self.ETIQUETA_ALTO + 0.2 * cm)

                color_info = COLORES_AREA.get(area_id, AREA_DEFAULT)
                self._dibujar_etiqueta(
                    c, x, y,
                    nombre=nombre, cedula=cedula, num_solicitud=num_sol,
                    fecha=fecha_str, sexo=sexo, edad=edad_str,
                    area_abrev=color_info['abrev'],
                    area_nombre=color_info['nombre'],
                    color_fondo=color_info['color'],
                    color_texto=color_info['color_texto'],
                    pruebas=', '.join(codigos[:4]),
                    qr_img=qr_img,
                )
                idx_global += 1

        c.save()
        _log.info("Etiquetas batch: %s (%d etiquetas)", ruta_salida, idx_global)
        return ruta_salida


# ============================================================================
# FACTORY
# ============================================================================

def crear_generador_etiquetas(db, portal=None, formato=FORMATO_TICKET):
    """
    Crea una instancia del generador de etiquetas.

    formato: FORMATO_TICKET (rollo de 80 mm, por defecto) o
             FORMATO_HOJA (hoja carta con 30 etiquetas cortables).
    """
    return GeneradorEtiquetas(db, portal=portal, formato=formato)

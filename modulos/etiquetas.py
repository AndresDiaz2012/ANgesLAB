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


# Colores por área (matching ANgesLAB areas)
COLORES_AREA = {
    1:  {'nombre': 'Hematología',    'abrev': 'HEM', 'color': '#e53935', 'color_texto': '#ffffff'},  # Rojo
    2:  {'nombre': 'Química',        'abrev': 'QUI', 'color': '#1e88e5', 'color_texto': '#ffffff'},  # Azul
    5:  {'nombre': 'Coagulación',    'abrev': 'COA', 'color': '#8e24aa', 'color_texto': '#ffffff'},  # Púrpura
    6:  {'nombre': 'Uroanálisis',    'abrev': 'URO', 'color': '#f9a825', 'color_texto': '#000000'},  # Amarillo
    7:  {'nombre': 'Parasitología',  'abrev': 'PAR', 'color': '#6d4c41', 'color_texto': '#ffffff'},  # Marrón
    8:  {'nombre': 'Tiroides',       'abrev': 'TIR', 'color': '#00acc1', 'color_texto': '#ffffff'},  # Cyan
    9:  {'nombre': 'Serología',      'abrev': 'SER', 'color': '#e91e63', 'color_texto': '#ffffff'},  # Rosa
    10: {'nombre': 'Microbiología',  'abrev': 'MIC', 'color': '#43a047', 'color_texto': '#ffffff'},  # Verde
    29: {'nombre': 'General',        'abrev': 'GEN', 'color': '#546e7a', 'color_texto': '#ffffff'},  # Gris
}

# Área por defecto para IDs no mapeados
AREA_DEFAULT = {'nombre': 'Otro', 'abrev': '???', 'color': '#9e9e9e', 'color_texto': '#000000'}


class GeneradorEtiquetas:
    """Genera etiquetas PDF para muestras de laboratorio."""

    # Layout de etiquetas en hoja carta (3 columnas x 10 filas = 30 etiquetas)
    COLS = 3
    FILAS = 10
    ETIQUETA_ANCHO = 6.5 * cm
    ETIQUETA_ALTO = 2.5 * cm
    MARGEN_H = 0.8 * cm
    MARGEN_V = 0.5 * cm

    def __init__(self, db):
        self.db = db

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
            f"FROM [DetalleSolicitudes] AS ds "
            f"INNER JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID "
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

    def _generar_pdf(self, solicitud: dict, areas_pruebas: list,
                      ruta: str) -> str:
        """Genera el PDF con las etiquetas."""
        from reportlab.pdfgen import canvas as cv_module

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
            )
            idx += 1

        c.save()
        _log.info("Etiquetas generadas: %s (%d etiquetas)", ruta, idx)
        return ruta

    def _dibujar_etiqueta(self, c, x, y, nombre, cedula, num_solicitud,
                           fecha, sexo, edad, area_abrev, area_nombre,
                           color_fondo, color_texto, pruebas):
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

        # Contenido texto (derecha de la barra)
        tx = x + barra_w + 2 * mm
        c.setFillColor(black)

        # Nombre del paciente (truncar si es largo)
        c.setFont('Helvetica-Bold', 7)
        nombre_corto = nombre[:30] + ('...' if len(nombre) > 30 else '')
        c.drawString(tx, y + h - 4 * mm, nombre_corto)

        # Cédula + Sexo + Edad
        c.setFont('Helvetica', 6)
        info_paciente = f"CI: {cedula}"
        if sexo:
            info_paciente += f"  |  {sexo}"
        if edad:
            info_paciente += f"  |  {edad}"
        c.drawString(tx, y + h - 8 * mm, info_paciente)

        # Solicitud + Fecha
        c.setFont('Helvetica', 6)
        c.drawString(tx, y + h - 12 * mm, f"{num_solicitud}  |  {fecha}")

        # Pruebas
        c.setFont('Helvetica', 5.5)
        pruebas_corto = pruebas[:45] + ('...' if len(pruebas) > 45 else '')
        c.drawString(tx, y + h - 16 * mm, pruebas_corto)

        # Código de barras (número de solicitud)
        try:
            barcode_val = num_solicitud.replace('-', '')
            if barcode_val:
                bc = code128.Code128(barcode_val, barWidth=0.6 * mm, barHeight=6 * mm)
                bc.drawOn(c, tx, y + 1 * mm)
        except Exception:
            pass  # Si falla el barcode, seguir sin él

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
                )
                idx_global += 1

        c.save()
        _log.info("Etiquetas batch: %s (%d etiquetas)", ruta_salida, idx_global)
        return ruta_salida


# ============================================================================
# FACTORY
# ============================================================================

def crear_generador_etiquetas(db):
    """Crea una instancia del generador de etiquetas."""
    return GeneradorEtiquetas(db)

# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE HOJAS DE TRABAJO - ANgesLAB
================================================================================
Generación de hojas de trabajo por área para captura de resultados.
Inspirado en SICOEXC (hojatrabajohem.rpt, hojatrabajoqu.rpt, etc.).

Funcionalidades:
- Genera PDF con lista de pacientes pendientes por área
- Incluye parámetros de cada prueba con espacios para anotar resultados
- Filtra por fecha y estado de solicitud
- Una hoja por área del laboratorio

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import logging
from datetime import datetime, date, timedelta

_log = logging.getLogger("angeslab.hojas_trabajo")

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.units import mm, cm
    from reportlab.lib.colors import HexColor, black, white, lightgrey
    from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                     Paragraph, Spacer, PageBreak)
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False
    _log.warning("ReportLab no disponible - hojas de trabajo deshabilitadas")

import os
import tempfile

# Mapeo de áreas (consistente con el sistema)
AREAS_LAB = {
    1:  {'nombre': 'Hematología',    'abrev': 'HEM'},
    2:  {'nombre': 'Química Clínica', 'abrev': 'QUI'},
    5:  {'nombre': 'Coagulación',    'abrev': 'COA'},
    6:  {'nombre': 'Uroanálisis',    'abrev': 'URO'},
    7:  {'nombre': 'Parasitología',  'abrev': 'PAR'},
    8:  {'nombre': 'Tiroides/Hormonas', 'abrev': 'TIR'},
    9:  {'nombre': 'Serología',      'abrev': 'SER'},
    10: {'nombre': 'Microbiología',  'abrev': 'MIC'},
    29: {'nombre': 'General',        'abrev': 'GEN'},
}


class GeneradorHojasTrabajo:
    """Genera hojas de trabajo PDF por área para captura de resultados."""

    def __init__(self, db):
        self.db = db

    def generar_hoja_area(self, area_id: int, fecha: date = None,
                           ruta_salida: str = None,
                           incluir_completadas: bool = False) -> str:
        """
        Genera hoja de trabajo para un área específica.

        Args:
            area_id: ID del área
            fecha: Fecha de las solicitudes (default: hoy)
            ruta_salida: Ruta del PDF
            incluir_completadas: Si True, incluye pruebas ya completadas

        Returns:
            Ruta del PDF generado
        """
        if not REPORTLAB_DISPONIBLE:
            raise RuntimeError("ReportLab no está instalado")

        fecha = fecha or date.today()
        area_info = AREAS_LAB.get(area_id, {'nombre': f'Área {area_id}', 'abrev': '???'})

        # Obtener solicitudes pendientes del día para esta área
        estados_filtro = "('Registrada', 'En Proceso', 'Recibida')"
        if incluir_completadas:
            estados_filtro = "('Registrada', 'En Proceso', 'Recibida', 'Completada')"

        fecha_str = fecha.strftime('%m/%d/%Y')
        fecha_sig = (fecha + timedelta(days=1)).strftime('%m/%d/%Y')

        sql = (
            f"SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, "
            f"s.EstadoSolicitud, "
            f"p.Nombres, p.Apellidos, p.NumeroDocumento, p.Sexo, p.FechaNacimiento, "
            f"ds.DetalleID, ds.Estado AS EstadoPrueba, "
            f"pr.PruebaID, pr.NombrePrueba, pr.CodigoPrueba "
            f"FROM [Solicitudes] AS s "
            f"INNER JOIN [Pacientes] AS p ON s.PacienteID = p.PacienteID "
            f"INNER JOIN [DetalleSolicitudes] AS ds ON s.SolicitudID = ds.SolicitudID "
            f"INNER JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID "
            f"WHERE pr.AreaID = {int(area_id)} "
            f"AND s.FechaSolicitud >= #{fecha_str}# "
            f"AND s.FechaSolicitud < #{fecha_sig}# "
            f"AND s.EstadoSolicitud IN {estados_filtro} "
            f"ORDER BY s.NumeroSolicitud, pr.NombrePrueba"
        )
        filas = self.db.query(sql) or []

        if not filas:
            _log.info("No hay solicitudes pendientes para área %s en %s",
                       area_info['nombre'], fecha)

        # Agrupar por solicitud
        solicitudes = {}
        for f in filas:
            sid = f.get('SolicitudID')
            if sid not in solicitudes:
                solicitudes[sid] = {
                    'numero': f.get('NumeroSolicitud', ''),
                    'paciente': f"{f.get('Nombres', '')} {f.get('Apellidos', '')}".strip(),
                    'cedula': f.get('NumeroDocumento', ''),
                    'sexo': f.get('Sexo', ''),
                    'edad': self._calcular_edad(f.get('FechaNacimiento')),
                    'estado': f.get('EstadoSolicitud', ''),
                    'pruebas': [],
                }
            solicitudes[sid]['pruebas'].append({
                'nombre': f.get('NombrePrueba', ''),
                'codigo': f.get('CodigoPrueba', ''),
                'estado': f.get('EstadoPrueba', ''),
                'detalle_id': f.get('DetalleID'),
            })

        # Obtener parámetros para cada prueba
        for sid, sol_data in solicitudes.items():
            for prueba in sol_data['pruebas']:
                det_id = prueba.get('detalle_id')
                if det_id:
                    params = self.db.query(
                        f"SELECT rp.ParametroID, par.NombreParametro, "
                        f"u.NombreUnidad AS Unidad, "
                        f"rp.Valor AS Resultado, rp.ValorReferencia "
                        f"FROM [ResultadosParametros] AS rp "
                        f"INNER JOIN [Parametros] AS par ON rp.ParametroID = par.ParametroID "
                        f"LEFT JOIN [Unidades] AS u ON par.UnidadID = u.UnidadID "
                        f"WHERE rp.DetalleID={int(det_id)} "
                        f"ORDER BY par.NombreParametro"
                    ) or []
                    prueba['parametros'] = params

        # Generar PDF
        if not ruta_salida:
            ruta_salida = os.path.join(
                tempfile.gettempdir(),
                f"HojaTrabajo_{area_info['abrev']}_{fecha.strftime('%Y%m%d')}.pdf"
            )

        return self._generar_pdf(area_info, fecha, solicitudes, ruta_salida)

    def generar_todas_areas(self, fecha: date = None,
                             ruta_directorio: str = None) -> list:
        """
        Genera hojas de trabajo para todas las áreas.

        Returns:
            Lista de rutas de PDFs generados
        """
        fecha = fecha or date.today()
        ruta_dir = ruta_directorio or tempfile.gettempdir()
        rutas = []

        for area_id in AREAS_LAB:
            try:
                ruta = self.generar_hoja_area(
                    area_id, fecha,
                    ruta_salida=os.path.join(
                        ruta_dir,
                        f"HojaTrabajo_{AREAS_LAB[area_id]['abrev']}_{fecha.strftime('%Y%m%d')}.pdf"
                    )
                )
                rutas.append(ruta)
            except Exception as e:
                _log.warning("Error generando hoja para área %s: %s", area_id, e)

        return rutas

    def _generar_pdf(self, area_info: dict, fecha: date,
                      solicitudes: dict, ruta: str) -> str:
        """Genera el PDF de hoja de trabajo."""
        from reportlab.pdfgen import canvas as cv_module

        c = cv_module.Canvas(ruta, pagesize=landscape(letter))
        page_w, page_h = landscape(letter)

        # ── Encabezado ──
        self._dibujar_encabezado(c, page_w, page_h, area_info, fecha, len(solicitudes))

        y_pos = page_h - 3.5 * cm
        linea_h = 0.55 * cm
        margen_izq = 1.0 * cm
        margen_inf = 2.0 * cm

        if not solicitudes:
            c.setFont('Helvetica-Oblique', 12)
            c.drawString(margen_izq, y_pos, "No hay solicitudes pendientes para esta área en la fecha seleccionada.")
            c.save()
            return ruta

        # ── Tabla de solicitudes ──
        for sid, sol in solicitudes.items():
            # Verificar espacio en página
            pruebas_count = sum(len(p.get('parametros', [])) for p in sol['pruebas'])
            espacio_requerido = (2 + pruebas_count) * linea_h + 1.5 * cm

            if y_pos - espacio_requerido < margen_inf:
                c.showPage()
                self._dibujar_encabezado(c, page_w, page_h, area_info, fecha, len(solicitudes))
                y_pos = page_h - 3.5 * cm

            # Barra de paciente
            c.setFillColor(HexColor('#e3f2fd'))
            c.rect(margen_izq, y_pos - 0.1 * cm, page_w - 2 * margen_izq, 0.7 * cm,
                   fill=1, stroke=0)
            c.setFillColor(black)
            c.setFont('Helvetica-Bold', 8)
            paciente_info = (
                f"{sol['numero']}  |  {sol['paciente']}  |  CI: {sol['cedula']}"
                f"  |  {sol['sexo']}  |  {sol['edad']}"
            )
            c.drawString(margen_izq + 3 * mm, y_pos + 1 * mm, paciente_info)
            y_pos -= 0.9 * cm

            # Parámetros de cada prueba
            for prueba in sol['pruebas']:
                c.setFont('Helvetica-Bold', 7)
                c.setFillColor(HexColor('#1565c0'))
                codigo = prueba.get('codigo', '')
                nombre_pr = prueba.get('nombre', '')
                c.drawString(margen_izq + 2 * mm, y_pos + 1 * mm,
                             f"▸ {codigo} - {nombre_pr}")
                c.setFillColor(black)
                y_pos -= linea_h

                parametros = prueba.get('parametros', [])
                if parametros:
                    # Encabezado de parámetros
                    c.setFont('Helvetica', 6)
                    c.setFillColor(HexColor('#666666'))
                    c.drawString(margen_izq + 1 * cm, y_pos + 1 * mm, "Parámetro")
                    c.drawString(margen_izq + 9 * cm, y_pos + 1 * mm, "Unidad")
                    c.drawString(margen_izq + 12 * cm, y_pos + 1 * mm, "Val. Referencia")
                    c.drawString(margen_izq + 18 * cm, y_pos + 1 * mm, "Resultado")
                    c.setStrokeColor(HexColor('#cccccc'))
                    c.line(margen_izq + 0.5 * cm, y_pos, page_w - margen_izq, y_pos)
                    c.setFillColor(black)
                    y_pos -= linea_h

                    for param in parametros:
                        if y_pos < margen_inf:
                            c.showPage()
                            self._dibujar_encabezado(c, page_w, page_h, area_info, fecha, len(solicitudes))
                            y_pos = page_h - 3.5 * cm

                        c.setFont('Helvetica', 7)
                        nombre_p = (param.get('NombreParametro') or '')[:35]
                        unidad = param.get('Unidad', '')
                        val_ref = (param.get('ValorReferencia') or '')[:25]
                        resultado = param.get('Resultado') or ''

                        c.drawString(margen_izq + 1 * cm, y_pos + 1 * mm, nombre_p)
                        c.drawString(margen_izq + 9 * cm, y_pos + 1 * mm, unidad)
                        c.drawString(margen_izq + 12 * cm, y_pos + 1 * mm, val_ref)

                        # Si tiene resultado, mostrarlo; si no, línea punteada
                        if resultado:
                            c.setFont('Helvetica-Bold', 7)
                            c.drawString(margen_izq + 18 * cm, y_pos + 1 * mm, resultado)
                        else:
                            c.setStrokeColor(HexColor('#999999'))
                            c.setDash(2, 2)
                            c.line(margen_izq + 18 * cm, y_pos + 1 * mm,
                                   page_w - margen_izq - 1 * cm, y_pos + 1 * mm)
                            c.setDash()

                        y_pos -= linea_h

            # Separador entre solicitudes
            y_pos -= 0.3 * cm

        # ── Pie de página ──
        c.setFont('Helvetica-Oblique', 6)
        c.setFillColor(HexColor('#999999'))
        c.drawString(margen_izq, 1.0 * cm,
                     f"Hoja de trabajo generada: {datetime.now().strftime('%d/%m/%Y %H:%M')}  |  ANgesLAB")
        c.drawRightString(page_w - margen_izq, 1.0 * cm,
                          f"Área: {area_info['nombre']}  |  Fecha: {fecha.strftime('%d/%m/%Y')}")

        c.save()
        _log.info("Hoja de trabajo generada: %s (%d solicitudes)", ruta, len(solicitudes))
        return ruta

    def _dibujar_encabezado(self, c, page_w, page_h, area_info, fecha, total):
        """Dibuja el encabezado de la hoja de trabajo."""
        # Obtener nombre del laboratorio
        lab_nombre = 'Laboratorio Clínico'
        try:
            config = self.db.query_one(
                "SELECT TOP 1 NombreLaboratorio FROM [ConfiguracionLaboratorio]"
            )
            if config and config.get('NombreLaboratorio'):
                lab_nombre = config['NombreLaboratorio']
        except Exception:
            pass

        # Barra superior
        c.setFillColor(HexColor('#0f172a'))
        c.rect(0, page_h - 2.5 * cm, page_w, 2.5 * cm, fill=1, stroke=0)

        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 14)
        c.drawString(1.0 * cm, page_h - 1.2 * cm, f"HOJA DE TRABAJO - {area_info['nombre'].upper()}")

        c.setFont('Helvetica', 10)
        c.drawString(1.0 * cm, page_h - 1.9 * cm, lab_nombre)

        c.drawRightString(page_w - 1.0 * cm, page_h - 1.2 * cm,
                          f"Fecha: {fecha.strftime('%d/%m/%Y')}")
        c.drawRightString(page_w - 1.0 * cm, page_h - 1.9 * cm,
                          f"Total solicitudes: {total}")

        # Línea separadora
        c.setStrokeColor(HexColor('#0891b2'))
        c.setLineWidth(2)
        c.line(0, page_h - 2.5 * cm, page_w, page_h - 2.5 * cm)

    def _calcular_edad(self, fecha_nacimiento) -> str:
        """Calcula la edad a partir de la fecha de nacimiento."""
        if not fecha_nacimiento:
            return ''
        try:
            if isinstance(fecha_nacimiento, str):
                return ''
            hoy = datetime.now()
            fn = fecha_nacimiento
            if isinstance(fn, date) and not isinstance(fn, datetime):
                fn = datetime.combine(fn, datetime.min.time())
            edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
            if edad < 1:
                meses = (hoy.year - fn.year) * 12 + hoy.month - fn.month
                return f"{meses}m"
            return f"{edad}a"
        except Exception:
            return ''


# ============================================================================
# FACTORY
# ============================================================================

def crear_generador_hojas(db):
    """Crea una instancia del generador de hojas de trabajo."""
    return GeneradorHojasTrabajo(db)

# -*- coding: utf-8 -*-
"""
================================================================================
CORTE DE ADEUDADO POR AREA DE LA CLINICA
================================================================================
Lo que la clinica adeuda al laboratorio, agrupado por el area de donde viene
el paciente: hospitalizacion, emergencia y cirugia.

Es el documento que el laboratorio le presenta a la administracion de la
clinica para cobrar. Dentro de cada area se separa lo asegurado de lo
particular, porque no se reclaman igual: lo asegurado lo desembolsa la
clinica por convenio, y lo particular lo debe un paciente que se atendio en
la clinica y quedo a deber.

El paciente ambulatorio queda fuera a proposito: llego por su pie y no forma
parte de lo que se le reporta a la clinica. Si tiene saldo, se menciona al
pie como nota para que nadie piense que el corte se dejo algo.

Se cuenta lo que sigue debiendose (SaldoPendiente), no lo facturado: una
cuenta ya cobrada no se reclama dos veces.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.corte')
except Exception:  # pragma: no cover
    import logging
    _log = logging.getLogger('angeslab.corte')

try:
    from modulos.procedencia import (
        AREAS_CLINICA, AREA_CIRUGIA, AREA_EMERGENCIA, AREA_HOSPITALIZACION,
        area_servicio, detectar_procedencia, es_credito)
except Exception:  # pragma: no cover
    AREA_HOSPITALIZACION = 'Hospitalizacion'
    AREA_EMERGENCIA = 'Emergencia'
    AREA_CIRUGIA = 'Cirugia'
    AREAS_CLINICA = (AREA_HOSPITALIZACION, AREA_EMERGENCIA, AREA_CIRUGIA)

    def area_servicio(_tipo):
        return AREA_HOSPITALIZACION

    def es_credito(_tipo):
        return False

    def detectar_procedencia(_texto):
        return ''


ETIQUETAS_AREA = {
    AREA_HOSPITALIZACION: 'HOSPITALIZACION',
    AREA_EMERGENCIA: 'EMERGENCIA',
    AREA_CIRUGIA: 'CIRUGIA',
}


def _f(valor):
    """Lee un importe sin que un dato ilegible tumbe el corte entero."""
    try:
        return float(valor if valor is not None else 0)
    except (TypeError, ValueError):
        return 0.0


def _fecha_access(momento):
    return momento.strftime('#%m/%d/%Y %H:%M:%S#')


def _fecha_corta(valor):
    if not valor:
        return ''
    try:
        return valor.strftime('%d/%m/%Y')
    except AttributeError:
        return str(valor)[:10]


class CorteAdeudado:
    """Arma el corte de lo adeudado por area y lo deja listo para imprimir."""

    def __init__(self, db):
        self.db = db
        self._columnas = {}

    def _tiene_columna(self, tabla, columna):
        clave = tabla + '.' + columna
        if clave not in self._columnas:
            try:
                self.db.query_one("SELECT TOP 1 " + columna + " FROM " + tabla)
                self._columnas[clave] = True
            except Exception:
                self._columnas[clave] = False
        return self._columnas[clave]

    def obtener_datos(self, desde=None, hasta=None, incluir_liberadas=False):
        """
        Reune lo adeudado, repartido por area y por quien debe pagarlo.

        Args:
            desde/hasta: acotan por fecha de ingreso del paciente. Sin ellas
                se toma todo lo pendiente, que es el corte habitual.
            incluir_liberadas: normalmente no; un corte es de lo que se debe.

        Devuelve un dict con cada area, sus pacientes y los totales.
        """
        tiene_proc = self._tiene_columna('CuentasPorCobrar', 'TipoProcedencia')
        tiene_sol = self._tiene_columna('CuentasPorCobrar', 'SolicitudID')

        campos = ["CuentaCobrarID", "PacienteID", "NombrePaciente",
                  "FechaEmision", "MontoOriginal", "MontoCobrado",
                  "SaldoPendiente", "Estado", "Observaciones"]
        # Nombrar una columna que no existe tumba la consulta entera y el
        # corte saldria en blanco, que es peor que salir incompleto.
        if tiene_proc:
            campos.append("TipoProcedencia")
        if tiene_sol:
            campos.append("SolicitudID")

        sql = "SELECT " + ", ".join(campos) + " FROM [CuentasPorCobrar] WHERE 1=1"
        if not incluir_liberadas:
            sql += " AND IIF(SaldoPendiente IS NULL, 0, SaldoPendiente) > 0.001"
        if desde:
            sql += " AND FechaEmision >= " + _fecha_access(desde)
        if hasta:
            sql += " AND FechaEmision <= " + _fecha_access(hasta)
        sql += " ORDER BY FechaEmision, NombrePaciente"

        try:
            filas = self.db.query(sql) or []
        except Exception as e:
            _log.error("No se pudo leer la cartera para el corte: %s", e)
            filas = []

        areas = {}
        for area in AREAS_CLINICA:
            areas[area] = {'asegurado': [], 'particular': []}
        fuera = 0.0

        for fila in filas:
            proc = fila.get('TipoProcedencia') if tiene_proc else None
            if not proc:
                # Cuentas creadas antes de que existiera la columna: la
                # procedencia quedo escrita dentro de las observaciones,
                # mezclada con el resto del texto.
                proc = detectar_procedencia(fila.get('Observaciones'))
            area = area_servicio(proc)
            if area not in areas:
                fuera += _f(fila.get('SaldoPendiente'))
                continue
            grupo = 'asegurado' if es_credito(proc) else 'particular'
            areas[area][grupo].append(fila)

        resumen = {}
        total_general = 0.0
        for area in AREAS_CLINICA:
            t_aseg = round(sum(_f(c.get('SaldoPendiente'))
                               for c in areas[area]['asegurado']), 2)
            t_part = round(sum(_f(c.get('SaldoPendiente'))
                               for c in areas[area]['particular']), 2)
            resumen[area] = {
                'asegurado': areas[area]['asegurado'],
                'particular': areas[area]['particular'],
                'total_asegurado': t_aseg,
                'total_particular': t_part,
                'total': round(t_aseg + t_part, 2),
                'n_pacientes': (len(areas[area]['asegurado'])
                                + len(areas[area]['particular'])),
            }
            total_general += resumen[area]['total']

        return {
            'areas': resumen,
            'total_general': round(total_general, 2),
            'total_asegurado': round(sum(resumen[a]['total_asegurado']
                                         for a in AREAS_CLINICA), 2),
            'total_particular': round(sum(resumen[a]['total_particular']
                                          for a in AREAS_CLINICA), 2),
            'n_pacientes': sum(resumen[a]['n_pacientes'] for a in AREAS_CLINICA),
            'fuera_del_corte': round(fuera, 2),
            'desde': desde,
            'hasta': hasta,
            'generado': datetime.now(),
        }

    # ------------------------------------------------------------------ PDF

    def generar_pdf(self, ruta, datos=None, config_lab=None, usuario=''):
        """
        Escribe el corte en ruta y la devuelve, o None si no se pudo.

        Sin reportlab no hay documento: quien llama debe avisarlo en vez de
        dejar al usuario esperando un papel que no va a salir.
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
            _log.error("reportlab no disponible: no se puede generar el corte")
            return None

        if datos is None:
            datos = self.obtener_datos()
        cfg = config_lab or {}
        estilos = getSampleStyleSheet()

        st_titulo = ParagraphStyle('ct_t', parent=estilos['Title'], fontSize=15,
                                   spaceAfter=2,
                                   textColor=colors.HexColor('#0f172a'))
        st_sub = ParagraphStyle('ct_s', parent=estilos['Normal'], fontSize=9,
                                alignment=1,
                                textColor=colors.HexColor('#475569'))
        st_area = ParagraphStyle('ct_a', parent=estilos['Heading2'], fontSize=11,
                                 spaceBefore=10, spaceAfter=4,
                                 textColor=colors.HexColor('#0891b2'))
        st_grupo = ParagraphStyle('ct_g', parent=estilos['Normal'], fontSize=9,
                                  spaceBefore=4, spaceAfter=2,
                                  textColor=colors.HexColor('#334155'))
        st_celda = ParagraphStyle('ct_c', parent=estilos['Normal'], fontSize=8)
        st_nota = ParagraphStyle('ct_n', parent=estilos['Normal'], fontSize=8,
                                 textColor=colors.HexColor('#64748b'))

        doc = SimpleDocTemplate(ruta, pagesize=letter,
                                leftMargin=0.5 * inch, rightMargin=0.5 * inch,
                                topMargin=0.5 * inch, bottomMargin=0.6 * inch,
                                title="Corte de adeudado")
        hist = []

        hist.append(Paragraph(str(cfg.get('NombreLaboratorio') or 'Laboratorio'),
                              st_titulo))
        hist.append(Paragraph("CORTE DE ADEUDADO POR AREA", st_sub))

        periodo = "Todo lo pendiente"
        if datos.get('desde') or datos.get('hasta'):
            d = _fecha_corta(datos.get('desde')) or '-'
            h = _fecha_corta(datos.get('hasta')) or '-'
            periodo = "Ingresos del " + d + " al " + h
        pie = periodo + " - Generado el " + datos['generado'].strftime('%d/%m/%Y %H:%M')
        if usuario:
            pie += " por " + str(usuario)
        hist.append(Paragraph(pie, st_sub))
        hist.append(Spacer(1, 6))
        hist.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor('#cbd5e1')))

        anchos = [1.5 * inch, 2.5 * inch, 0.95 * inch, 0.95 * inch, 0.95 * inch]
        cabecera = ['Ingreso', 'Paciente', 'Monto', 'Abonado', 'Debe']

        comandos_base = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e2e8f0')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#0f172a')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2),
             [colors.white, colors.HexColor('#f8fafc')]),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f1f5f9')),
        ]

        def bloque(titulo, cuentas, total):
            if not cuentas:
                return
            hist.append(Paragraph(
                titulo + " - " + str(len(cuentas)) + " paciente(s)", st_grupo))
            filas = [cabecera]
            for c in cuentas:
                filas.append([
                    _fecha_corta(c.get('FechaEmision')),
                    Paragraph(str(c.get('NombrePaciente') or ''), st_celda),
                    '{:,.2f}'.format(_f(c.get('MontoOriginal'))),
                    '{:,.2f}'.format(_f(c.get('MontoCobrado'))),
                    '{:,.2f}'.format(_f(c.get('SaldoPendiente'))),
                ])
            filas.append(['', 'Subtotal', '', '', '{:,.2f}'.format(total)])
            tabla = Table(filas, colWidths=anchos, repeatRows=1)
            tabla.setStyle(TableStyle(comandos_base))
            hist.append(tabla)
            hist.append(Spacer(1, 4))

        hay_algo = False
        for area in AREAS_CLINICA:
            d = datos['areas'][area]
            if d['n_pacientes'] == 0:
                continue
            hay_algo = True
            hist.append(Paragraph(
                ETIQUETAS_AREA.get(area, area)
                + " - adeudado " + '{:,.2f}'.format(d['total']), st_area))
            bloque("Asegurado (lo desembolsa la clinica)",
                   d['asegurado'], d['total_asegurado'])
            bloque("Particular (lo debe el paciente)",
                   d['particular'], d['total_particular'])

        if not hay_algo:
            hist.append(Spacer(1, 20))
            hist.append(Paragraph(
                "No hay saldos pendientes en hospitalizacion, emergencia "
                "ni cirugia.", estilos['Normal']))

        hist.append(Spacer(1, 10))
        hist.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor('#cbd5e1')))
        hist.append(Spacer(1, 6))

        resumen = [['Area', 'Pacientes', 'Asegurado', 'Particular', 'Total']]
        for area in AREAS_CLINICA:
            d = datos['areas'][area]
            resumen.append([
                ETIQUETAS_AREA.get(area, area),
                str(d['n_pacientes']),
                '{:,.2f}'.format(d['total_asegurado']),
                '{:,.2f}'.format(d['total_particular']),
                '{:,.2f}'.format(d['total']),
            ])
        resumen.append([
            'TOTAL', str(datos['n_pacientes']),
            '{:,.2f}'.format(datos['total_asegurado']),
            '{:,.2f}'.format(datos['total_particular']),
            '{:,.2f}'.format(datos['total_general']),
        ])

        tabla_res = Table(resumen, colWidths=[1.7 * inch, 0.9 * inch, 1.2 * inch,
                                              1.2 * inch, 1.2 * inch])
        tabla_res.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0891b2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e2e8f0')),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#94a3b8')),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        hist.append(tabla_res)

        if datos.get('fuera_del_corte', 0) > 0.01:
            hist.append(Spacer(1, 8))
            hist.append(Paragraph(
                "Nota: quedan " + '{:,.2f}'.format(datos['fuera_del_corte'])
                + " de pacientes ambulatorios, que no forman parte de este corte.",
                st_nota))

        hist.append(Spacer(1, 26))
        firmas = Table([['_' * 34, '', '_' * 34],
                        ['Por el laboratorio', '', 'Por la clinica']],
                       colWidths=[2.6 * inch, 1.0 * inch, 2.6 * inch])
        firmas.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#475569')),
        ]))
        hist.append(firmas)

        try:
            doc.build(hist)
            _log.info("Corte de adeudado generado: %s (total %.2f)",
                      ruta, datos['total_general'])
            return ruta
        except Exception as e:
            _log.error("No se pudo escribir el corte: %s", e)
            return None


def crear_corte(db):
    """Fabrica, al estilo del resto de modulos."""
    return CorteAdeudado(db)

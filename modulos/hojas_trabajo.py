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
    8:  {'nombre': 'Hormonas',       'abrev': 'HOR'},
    9:  {'nombre': 'Serología',      'abrev': 'SER'},
    10: {'nombre': 'Microbiología',  'abrev': 'MIC'},
    11: {'nombre': 'Pruebas Especiales', 'abrev': 'ESP'},
    12: {'nombre': 'Infecciosas',    'abrev': 'INF'},
    13: {'nombre': 'Inmunológicas',  'abrev': 'INM'},
    14: {'nombre': 'Renal',          'abrev': 'REN'},
    29: {'nombre': 'General',        'abrev': 'GEN'},
}


# ── Estados de solicitud que representan trabajo por hacer ──────────────────
# El sistema crea las solicitudes como 'Pendiente' y las pasa a 'En Proceso' y
# luego a 'Completada'. La version anterior filtraba por ('Registrada',
# 'En Proceso', 'Recibida'), nombres que este sistema no usa: la consulta no
# devolvia nunca una fila y la hoja de trabajo salia siempre vacia.
# Se aceptan tambien los nombres antiguos por si una base vieja los trae.
ESTADOS_PENDIENTES = ('Pendiente', 'Registrada', 'Recibida', 'En Proceso')
ESTADOS_COMPLETADOS = ('Completada', 'Validada')


def _lista_sql(valores):
    """Convierte una tupla de estados en una lista SQL entre parentesis."""
    return "(" + ", ".join(f"'{v}'" for v in valores) + ")"


class GeneradorHojasTrabajo:
    """Genera hojas de trabajo PDF por área para captura de resultados."""

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def _filtro_estados(self, incluir_completadas=False):
        estados = ESTADOS_PENDIENTES
        if incluir_completadas:
            estados = estados + ESTADOS_COMPLETADOS
        return _lista_sql(estados)

    def areas_con_trabajo(self, fecha: date = None,
                          incluir_completadas: bool = False) -> list:
        """
        Áreas que tienen pruebas pendientes en la fecha, con su cantidad.

        Permite mostrar en pantalla qué hojas tiene sentido generar en vez de
        sacar una hoja en blanco por cada área del laboratorio.

        Returns lista de dicts: {'area_id', 'nombre', 'abrev', 'pruebas',
        'solicitudes'}
        """
        fecha = fecha or date.today()
        fecha_str = fecha.strftime('%m/%d/%Y')
        fecha_sig = (fecha + timedelta(days=1)).strftime('%m/%d/%Y')

        # Access no admite COUNT(DISTINCT ...): se agrupa primero por área y
        # solicitud en una subconsulta y luego se suma
        sql = (
            f"SELECT t.AreaID, t.NombreArea, "
            f"SUM(t.Pruebas) AS Pruebas, COUNT(*) AS Solicitudes "
            f"FROM (SELECT pr.AreaID AS AreaID, a.NombreArea AS NombreArea, "
            f"      s.SolicitudID AS SolicitudID, COUNT(*) AS Pruebas "
            f"      FROM ((([Solicitudes] AS s "
            f"      INNER JOIN [DetalleSolicitudes] AS ds "
            f"          ON s.SolicitudID = ds.SolicitudID) "
            f"      INNER JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID) "
            f"      LEFT JOIN [Areas] AS a ON pr.AreaID = a.AreaID) "
            f"      WHERE s.FechaSolicitud >= #{fecha_str}# "
            f"      AND s.FechaSolicitud < #{fecha_sig}# "
            f"      AND s.EstadoSolicitud IN "
            f"          {self._filtro_estados(incluir_completadas)} "
            f"      GROUP BY pr.AreaID, a.NombreArea, s.SolicitudID) AS t "
            f"GROUP BY t.AreaID, t.NombreArea "
            f"ORDER BY t.NombreArea"
        )
        try:
            filas = self.db.query(sql) or []
        except Exception as e:
            _log.error("No se pudo consultar el trabajo por área: %s", e)
            return []

        salida = []
        for f in filas:
            area_id = f.get('AreaID')
            if area_id is None:
                continue
            info = AREAS_LAB.get(area_id, {})
            salida.append({
                'area_id': area_id,
                'nombre': f.get('NombreArea') or info.get('nombre',
                                                          f'Área {area_id}'),
                'abrev': info.get('abrev', f'A{area_id}'),
                'pruebas': int(f.get('Pruebas') or 0),
                'solicitudes': int(f.get('Solicitudes') or 0),
            })
        return salida

    def _parametros_de_prueba(self, prueba_id, detalle_id):
        """
        Parámetros que hay que anotar para esa prueba.

        Se leen de ParametrosPrueba (la definición de la prueba), no de
        ResultadosParametros: esa tabla solo tiene filas DESPUES de capturar un
        resultado, así que consultarla dejaba la hoja de trabajo sin una sola
        línea donde escribir, que es justo para lo que sirve la hoja.

        El valor ya capturado, si existe, se trae con un LEFT JOIN para poder
        reimprimir una hoja parcialmente llena.
        """
        # Se consulta en dos pasos a propósito: Access rechaza un LEFT JOIN
        # cuyo ON mezcla una comparación entre campos con una constante
        # («La expresión JOIN no se admite»), que es justo lo que hace falta
        # para traer el valor de un DetalleID concreto.
        sql = (
            f"SELECT pp.ParametroID, par.NombreParametro, par.Observaciones, "
            f"u.NombreUnidad AS Unidad, pp.Secuencia "
            f"FROM (([ParametrosPrueba] AS pp "
            f"INNER JOIN [Parametros] AS par ON pp.ParametroID = par.ParametroID) "
            f"LEFT JOIN [Unidades] AS u ON par.UnidadID = u.UnidadID) "
            f"WHERE pp.PruebaID = {int(prueba_id)} "
            f"ORDER BY pp.Secuencia"
        )
        try:
            filas = self.db.query(sql) or []
        except Exception as e:
            _log.warning("No se pudieron leer los parámetros de la prueba %s: %s",
                         prueba_id, e)
            return []

        # Valores ya capturados, para poder reimprimir una hoja a medio llenar
        capturados = {}
        try:
            for r in self.db.query(
                    f"SELECT ParametroID, Valor, ValorReferencia "
                    f"FROM [ResultadosParametros] "
                    f"WHERE DetalleID = {int(detalle_id)}") or []:
                capturados[r.get('ParametroID')] = r
        except Exception as e:
            _log.debug("Sin resultados previos para el detalle %s: %s",
                       detalle_id, e)

        for f in filas:
            previo = capturados.get(f.get('ParametroID')) or {}
            f['Resultado'] = previo.get('Valor') or ''
            # El valor de referencia vive en Parametros.Observaciones hasta que
            # se captura el resultado y se copia a ResultadosParametros
            f['ValorReferencia'] = (previo.get('ValorReferencia')
                                    or f.get('Observaciones') or '')
        return filas

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
        area_info = dict(AREAS_LAB.get(
            area_id, {'nombre': f'Área {area_id}', 'abrev': f'A{area_id}'}))
        # El nombre real del área manda sobre el mapeo fijo del módulo
        try:
            fila_area = self.db.query_one(
                f"SELECT NombreArea FROM [Areas] WHERE AreaID = {int(area_id)}")
            if fila_area and fila_area.get('NombreArea'):
                area_info['nombre'] = fila_area['NombreArea']
        except Exception:
            pass

        fecha_str = fecha.strftime('%m/%d/%Y')
        fecha_sig = (fecha + timedelta(days=1)).strftime('%m/%d/%Y')

        sql = (
            f"SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, "
            f"s.EstadoSolicitud, "
            f"p.Nombres, p.Apellidos, p.NumeroDocumento, p.Sexo, p.FechaNacimiento, "
            f"ds.DetalleID, ds.Estado AS EstadoPrueba, "
            f"pr.PruebaID, pr.NombrePrueba, pr.CodigoPrueba "
            f"FROM (([Solicitudes] AS s "
            f"INNER JOIN [Pacientes] AS p ON s.PacienteID = p.PacienteID) "
            f"INNER JOIN [DetalleSolicitudes] AS ds ON s.SolicitudID = ds.SolicitudID) "
            f"INNER JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID "
            f"WHERE pr.AreaID = {int(area_id)} "
            f"AND s.FechaSolicitud >= #{fecha_str}# "
            f"AND s.FechaSolicitud < #{fecha_sig}# "
            f"AND s.EstadoSolicitud IN {self._filtro_estados(incluir_completadas)} "
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
                'prueba_id': f.get('PruebaID'),
            })

        # Parámetros a anotar de cada prueba
        for sid, sol_data in solicitudes.items():
            for prueba in sol_data['pruebas']:
                det_id = prueba.get('detalle_id')
                pr_id = prueba.get('prueba_id')
                if det_id and pr_id:
                    prueba['parametros'] = self._parametros_de_prueba(pr_id,
                                                                     det_id)

        # Generar PDF
        if not ruta_salida:
            ruta_salida = os.path.join(
                tempfile.gettempdir(),
                f"HojaTrabajo_{area_info['abrev']}_{fecha.strftime('%Y%m%d')}.pdf"
            )

        return self._generar_pdf(area_info, fecha, solicitudes, ruta_salida)

    def generar_todas_areas(self, fecha: date = None,
                             ruta_directorio: str = None,
                             incluir_completadas: bool = False,
                             solo_con_trabajo: bool = True) -> list:
        """
        Genera hojas de trabajo para las áreas que tienen trabajo ese día.

        Antes recorría las trece áreas del mapeo y devolvía una hoja por cada
        una, aunque estuviera vacía: se imprimían once o doce hojas en blanco.

        Args:
            solo_con_trabajo: si es False genera todas las áreas conocidas.

        Returns:
            Lista de rutas de PDFs generados
        """
        fecha = fecha or date.today()
        ruta_dir = ruta_directorio or tempfile.gettempdir()
        rutas = []

        if solo_con_trabajo:
            areas = [a['area_id']
                     for a in self.areas_con_trabajo(fecha, incluir_completadas)]
        else:
            areas = list(AREAS_LAB)

        for area_id in areas:
            try:
                abrev = AREAS_LAB.get(area_id, {}).get('abrev', f'A{area_id}')
                ruta = self.generar_hoja_area(
                    area_id, fecha,
                    ruta_salida=os.path.join(
                        ruta_dir,
                        f"HojaTrabajo_{abrev}_{fecha.strftime('%Y%m%d')}.pdf"
                    ),
                    incluir_completadas=incluir_completadas
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
            # Un campo vacio se omite en vez de imprimir la palabra «None»
            partes = [sol['numero'], sol['paciente']]
            if sol.get('cedula'):
                partes.append(f"CI: {sol['cedula']}")
            if sol.get('sexo'):
                partes.append(str(sol['sexo']))
            if sol.get('edad'):
                partes.append(str(sol['edad']))
            paciente_info = "  |  ".join(str(x or '') for x in partes)
            c.drawString(margen_izq + 3 * mm, y_pos + 1 * mm, paciente_info)
            y_pos -= 0.9 * cm

            # Parámetros de cada prueba
            for prueba in sol['pruebas']:
                c.setFont('Helvetica-Bold', 7)
                c.setFillColor(HexColor('#1565c0'))
                codigo = prueba.get('codigo') or ''
                nombre_pr = prueba.get('nombre') or ''
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
                        nombre_p = str(param.get('NombreParametro') or '')[:35]
                        unidad = param.get('Unidad') or ''
                        val_ref = str(param.get('ValorReferencia') or '')[:25]
                        resultado = str(param.get('Resultado') or '')

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

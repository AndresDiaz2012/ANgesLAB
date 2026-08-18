# -*- coding: utf-8 -*-
"""
Historial Clinico - ANgesLAB
================================================================================
Modulo para consulta del historial clinico de pacientes.

Funcionalidades:
- Historial completo de solicitudes y resultados por paciente
- Comparacion de resultados entre la ultima y penultima solicitud
- Evaluacion de tendencias (mejorando/empeorando/estable)
- Resumen estadistico del paciente con areas y alertas
- Evolucion completa multi-punto de una prueba
- Timeline filtrable por fecha y area clinica
- Deteccion de parametros historicamente fuera de rango

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import re
import logging
from datetime import datetime, date, timedelta


class GestorHistorialClinico:
    """Gestor centralizado para consulta de historial clinico de pacientes."""

    def __init__(self, db, usuario=None):
        self.db = db
        self.usuario = usuario or {}
        self._cache_unidades = {}

    def _obtener_unidad(self, unidad_id):
        """Obtiene el simbolo de una unidad con cache para evitar N+1 queries."""
        if not unidad_id:
            return ''
        if unidad_id in self._cache_unidades:
            return self._cache_unidades[unidad_id]
        try:
            unidad = self.db.query_one(
                f"SELECT Simbolo FROM Unidades WHERE UnidadID = {unidad_id}"
            )
            texto = (unidad.get('Simbolo') or '') if unidad else ''
        except Exception:
            texto = ''
        # Convertir notación ^N a superíndices Unicode
        _super = {'0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
                  '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'}
        import re
        def _repl(m):
            return ''.join(_super.get(c, c) for c in m.group(1))
        texto = re.sub(r'\^(\d+)', _repl, texto)
        texto = texto.replace('mm3', 'mm³').replace('uL', 'µL')
        self._cache_unidades[unidad_id] = texto
        return texto

    # ================================================================
    # RESUMEN DEL PACIENTE
    # ================================================================

    def obtener_resumen_paciente(self, paciente_id):
        """
        Obtiene estadisticas resumen del paciente.

        Returns:
            Dict con {exito, datos: {total_solicitudes, primera_visita,
                      ultima_visita, pruebas_frecuentes,
                      total_parametros_capturados, areas_clinicas,
                      alertas_recientes}}
        """
        if not paciente_id:
            return {'exito': False, 'mensaje': 'Paciente no especificado', 'datos': None}

        try:
            # Totales y fechas
            stats = self.db.query_one(
                f"SELECT COUNT(*) AS Total, "
                f"MIN(FechaSolicitud) AS PrimeraFecha, "
                f"MAX(FechaSolicitud) AS UltimaFecha "
                f"FROM Solicitudes "
                f"WHERE PacienteID = {paciente_id} AND EstadoSolicitud <> 'Anulada'"
            )

            # Pruebas frecuentes (Access: JOINs multiples necesitan parentesis)
            frecuentes = self.db.query(
                f"SELECT TOP 5 p.PruebaID, p.CodigoPrueba, p.NombrePrueba, COUNT(*) AS Veces "
                f"FROM (DetalleSolicitudes d "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID) "
                f"INNER JOIN Pruebas p ON d.PruebaID = p.PruebaID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"GROUP BY p.PruebaID, p.CodigoPrueba, p.NombrePrueba "
                f"ORDER BY COUNT(*) DESC"
            )

            # Total de parametros capturados
            total_params = self.db.query_one(
                f"SELECT COUNT(*) AS Total FROM "
                f"(ResultadosParametros rp "
                f"INNER JOIN DetalleSolicitudes d ON rp.DetalleID = d.DetalleID) "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"AND rp.Valor IS NOT NULL AND rp.Valor <> ''"
            )

            # Areas clinicas con conteo (Access no soporta COUNT DISTINCT)
            areas = self.db.query(
                f"SELECT a.NombreArea, COUNT(*) AS Veces "
                f"FROM ((DetalleSolicitudes d "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID) "
                f"INNER JOIN Pruebas p ON d.PruebaID = p.PruebaID) "
                f"INNER JOIN Areas a ON p.AreaID = a.AreaID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"GROUP BY a.NombreArea "
                f"ORDER BY COUNT(*) DESC"
            )

            # Alertas: parametros fuera de rango en la ultima solicitud
            alertas = self._obtener_alertas_ultima_solicitud(paciente_id)

            return {
                'exito': True,
                'datos': {
                    'total_solicitudes': (stats or {}).get('Total', 0) or 0,
                    'primera_visita': (stats or {}).get('PrimeraFecha'),
                    'ultima_visita': (stats or {}).get('UltimaFecha'),
                    'pruebas_frecuentes': frecuentes or [],
                    'total_parametros_capturados': (total_params or {}).get('Total', 0) or 0,
                    'areas_clinicas': areas or [],
                    'alertas_recientes': alertas,
                }
            }
        except Exception as e:
            return {'exito': False, 'mensaje': f'Error obteniendo resumen: {e}', 'datos': None}

    def _obtener_alertas_ultima_solicitud(self, paciente_id):
        """Obtiene parametros numericos fuera de rango de la ultima solicitud."""
        try:
            ultima = self.db.query_one(
                f"SELECT TOP 1 SolicitudID FROM Solicitudes "
                f"WHERE PacienteID = {paciente_id} AND EstadoSolicitud <> 'Anulada' "
                f"ORDER BY FechaSolicitud DESC"
            )
            if not ultima:
                return []

            sol_id = ultima['SolicitudID']

            # Prioridad 1: usar FueraDeRango/TipoAlerta ya calculados al capturar
            resultados = self.db.query(
                f"SELECT par.NombreParametro, rp.ValorReferencia AS ValorRef, "
                f"rp.Valor, rp.FueraDeRango, rp.TipoAlerta, par.UnidadID "
                f"FROM (ResultadosParametros rp "
                f"INNER JOIN DetalleSolicitudes d ON rp.DetalleID = d.DetalleID) "
                f"INNER JOIN Parametros par ON rp.ParametroID = par.ParametroID "
                f"WHERE d.SolicitudID = {sol_id} "
                f"AND rp.Valor IS NOT NULL AND rp.Valor <> ''"
            )

            alertas = []
            for r in (resultados or []):
                valor_str = str(r.get('Valor', '')).replace(',', '.').strip()
                valor_ref = r.get('ValorRef') or ''
                unidad = self._obtener_unidad(r.get('UnidadID'))

                # Usar FueraDeRango si ya fue calculado
                fuera_rango = r.get('FueraDeRango')
                tipo_alerta = r.get('TipoAlerta') or ''

                if fuera_rango:
                    # Mapear TipoAlerta a 'alto'/'bajo' (acepta mayusculas o minusculas)
                    tipo_lower = tipo_alerta.lower()
                    if 'alto' in tipo_lower:
                        tipo = 'alto'
                    elif 'bajo' in tipo_lower:
                        tipo = 'bajo'
                    else:
                        tipo = 'alto'
                    alertas.append({
                        'parametro': r.get('NombreParametro', ''),
                        'valor': valor_str,
                        'unidad': unidad,
                        'referencia': valor_ref,
                        'tipo': tipo,
                        'critico': 'critico' in tipo_lower,
                    })
                    continue

                # Fallback: calcular con valor de referencia textual
                if not valor_ref:
                    continue
                try:
                    valor_num = float(valor_str)
                except (ValueError, TypeError):
                    continue

                fuera = self._verificar_fuera_de_rango(valor_num, valor_ref)
                if fuera:
                    alertas.append({
                        'parametro': r.get('NombreParametro', ''),
                        'valor': valor_str,
                        'unidad': unidad,
                        'referencia': valor_ref,
                        'tipo': fuera,
                        'critico': False,
                    })

            return alertas
        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning("Error obteniendo alertas: %s", e)
            return []

    def _verificar_fuera_de_rango(self, valor, valor_ref):
        """
        Verifica si un valor esta fuera del rango de referencia.
        Returns: 'alto', 'bajo' o None
        Maneja separador de miles espanol: "4.000"=4000, "150.000"=150000
        """
        if not valor_ref:
            return None
        ref_str = str(valor_ref).strip()

        def _p(s):
            """Parsea numero manejando separador de miles espanol.
            '4.000'->4000, '150.000'->150000, '4.5'->4.5, '0.800'->0.8"""
            s = str(s).strip().replace(',', '.')
            if '.' in s:
                partes = s.split('.')
                if (len(partes) == 2 and partes[0] not in ('', '0', '-0')
                        and len(partes[1]) == 3 and partes[1].isdigit()):
                    s = partes[0] + partes[1]  # "4.000"→"4000", "4.500"→"4500"
            return float(s)

        # Formato "min - max" (con o sin unidades al final)
        match = re.search(r'([\d.,]+)\s*[-\u2013]\s*([\d.,]+)', ref_str)
        if match:
            try:
                ref_min = _p(match.group(1))
                ref_max = _p(match.group(2))
                if valor < ref_min:
                    return 'bajo'
                elif valor > ref_max:
                    return 'alto'
                return None
            except (ValueError, TypeError):
                pass

        # Formato "< valor" o "<= valor"
        match = re.search(r'<\s*=?\s*([\d.,]+)', ref_str)
        if match:
            try:
                limite = _p(match.group(1))
                if valor > limite:
                    return 'alto'
                return None
            except (ValueError, TypeError):
                pass

        # Formato "> valor" o ">= valor"
        match = re.search(r'>\s*=?\s*([\d.,]+)', ref_str)
        if match:
            try:
                limite = _p(match.group(1))
                if valor < limite:
                    return 'bajo'
                return None
            except (ValueError, TypeError):
                pass

        return None

    # ================================================================
    # EVALUACION DE RANGO: UNICA FUENTE DE VERDAD
    # ================================================================
    def evaluar_alerta(self, valor, valor_ref, fuera_guardado=None,
                       tipo_guardado=''):
        """
        Decide si un resultado esta fuera de rango, y de que lado.

        Es el unico sitio donde se toma esa decision. Antes cada vista la
        resolvia por su cuenta: el Resumen calculaba la alerta a partir del
        texto de referencia, mientras que Comparativa, Evolucion y el detalle
        de una solicitud se limitaban a leer la columna FueraDeRango. Como las
        columnas BIT que Access agrega con ALTER TABLE nacen en False y no en
        NULL, todo resultado capturado antes de que existiera esa columna se
        mostraba como normal en esas tres vistas. El mismo paciente aparecia
        con el colesterol "alto" en una pestana y "dentro de rango" en la de al
        lado; en un informe clinico eso no es un detalle cosmetico.

        Args:
            valor: valor capturado (texto o numero)
            valor_ref: texto del valor de referencia
            fuera_guardado: columna FueraDeRango, si existe
            tipo_guardado: columna TipoAlerta, si existe

        Returns:
            (fuera_de_rango: bool, tipo: 'alto' | 'bajo' | '')
        """
        # La bandera guardada manda: la calculo el modulo de captura, que
        # conoce reglas por sexo y edad que aqui no estan disponibles
        if fuera_guardado:
            tipo_lower = str(tipo_guardado or '').lower()
            if 'bajo' in tipo_lower:
                return True, 'bajo'
            return True, 'alto'

        if valor in (None, '') or not valor_ref:
            return False, ''
        try:
            valor_num = float(str(valor).replace(',', '.').strip())
        except (ValueError, TypeError):
            return False, ''      # resultados cualitativos: no aplica

        tipo = self._verificar_fuera_de_rango(valor_num, valor_ref)
        return (True, tipo) if tipo else (False, '')

    def _resultados_por_detalle(self, detalle_ids):
        """
        Trae de una sola vez los resultados de varios detalles.

        Devuelve {(DetalleID, ParametroID): fila}. Evita el patron N+1 que
        hacia una consulta por parametro y por medicion: la pestana de
        Evolucion de una hematologia completa con diez visitas llegaba a
        doscientas consultas para pintar una tabla, y sobre una base Access
        compartida por red eso se siente.
        """
        indice = {}
        ids = [int(d) for d in (detalle_ids or []) if d]
        if not ids:
            return indice
        try:
            filas = self.db.query(
                f"SELECT DetalleID, ParametroID, Valor, ValorReferencia, "
                f"Estado, FechaCaptura, FueraDeRango, TipoAlerta "
                f"FROM ResultadosParametros "
                f"WHERE DetalleID IN ({', '.join(str(i) for i in ids)})"
            ) or []
        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning(
                "Error leyendo resultados en bloque: %s", e)
            return indice
        for f in filas:
            indice[(f.get('DetalleID'), f.get('ParametroID'))] = f
        return indice

    # ================================================================
    # CONTEXTO PARA EL REGISTRO DE UNA NUEVA SOLICITUD
    # ================================================================
    def contexto_para_ingreso(self, paciente_id, dias_ventana=90):
        """
        Lo que el laboratorio ya sabe del paciente, para mostrarlo al
        registrarlo.

        Hasta ahora el historial solo se consultaba en su propia pantalla: al
        recibir de nuevo a un paciente conocido, el mostrador no veia nada de
        lo anterior. Se repetian pruebas hechas dias antes y se perdia de vista
        que la ultima visita habia salido alterada.

        Args:
            paciente_id: paciente que se esta registrando
            dias_ventana: cuantos dias atras se considera «reciente» una
                prueba, para avisar de repeticiones

        Returns dict:
            es_conocido        - tiene visitas anteriores
            total_visitas      - solicitudes no anuladas
            ultima_visita      - fecha de la ultima
            dias_desde_ultima  - int o None
            alertas_ultima     - parametros fuera de rango en la ultima visita
            ultima_orden       - pruebas de la ultima solicitud (repetir orden)
            recientes          - {PruebaID: dias} de lo hecho dentro de la ventana
        """
        vacio = {
            'es_conocido': False, 'total_visitas': 0, 'ultima_visita': None,
            'dias_desde_ultima': None, 'alertas_ultima': [],
            'ultima_orden': [], 'recientes': {},
        }
        if not paciente_id:
            return vacio

        try:
            stats = self.db.query_one(
                f"SELECT COUNT(*) AS Total, MAX(FechaSolicitud) AS Ultima "
                f"FROM Solicitudes "
                f"WHERE PacienteID = {paciente_id} "
                f"AND EstadoSolicitud <> 'Anulada'"
            ) or {}
            total = int(stats.get('Total') or 0)
            if not total:
                return vacio

            ultima_fecha = stats.get('Ultima')
            dias = None
            if ultima_fecha is not None:
                try:
                    f = (ultima_fecha.date()
                         if hasattr(ultima_fecha, 'date') else ultima_fecha)
                    dias = (date.today() - f).days
                except Exception:
                    dias = None

            # Ultima solicitud completa, para poder repetir la orden
            ultima_sol = self.db.query_one(
                f"SELECT TOP 1 SolicitudID FROM Solicitudes "
                f"WHERE PacienteID = {paciente_id} "
                f"AND EstadoSolicitud <> 'Anulada' "
                f"ORDER BY FechaSolicitud DESC, SolicitudID DESC"
            ) or {}
            ultima_orden = []
            if ultima_sol.get('SolicitudID'):
                ultima_orden = self.db.query(
                    f"SELECT d.PruebaID, p.CodigoPrueba, p.NombrePrueba, "
                    f"p.Precio "
                    f"FROM DetalleSolicitudes d "
                    f"INNER JOIN Pruebas p ON d.PruebaID = p.PruebaID "
                    f"WHERE d.SolicitudID = {ultima_sol['SolicitudID']} "
                    f"ORDER BY p.NombrePrueba"
                ) or []

            # Pruebas hechas dentro de la ventana, con cuantos dias tienen
            recientes = {}
            try:
                desde = (date.today() - timedelta(days=int(dias_ventana)))
                filas = self.db.query(
                    f"SELECT d.PruebaID, MAX(s.FechaSolicitud) AS Ultima "
                    f"FROM DetalleSolicitudes d "
                    f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID "
                    f"WHERE s.PacienteID = {paciente_id} "
                    f"AND s.EstadoSolicitud <> 'Anulada' "
                    f"AND s.FechaSolicitud >= #{desde.strftime('%m/%d/%Y')}# "
                    f"GROUP BY d.PruebaID"
                ) or []
                for f in filas:
                    fecha = f.get('Ultima')
                    if fecha is None:
                        continue
                    try:
                        fd = fecha.date() if hasattr(fecha, 'date') else fecha
                        recientes[f.get('PruebaID')] = (date.today() - fd).days
                    except Exception:
                        continue
            except Exception as e:
                logging.getLogger("angeslab.historial_clinico").debug(
                    "No se pudieron leer las pruebas recientes: %s", e)

            return {
                'es_conocido': True,
                'total_visitas': total,
                'ultima_visita': ultima_fecha,
                'dias_desde_ultima': dias,
                'alertas_ultima': self._obtener_alertas_ultima_solicitud(paciente_id),
                'ultima_orden': ultima_orden,
                'recientes': recientes,
            }
        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning(
                "Error obteniendo contexto de ingreso: %s", e)
            return vacio

    # ================================================================
    # HISTORIAL CRONOLOGICO CON FILTROS
    # ================================================================

    def obtener_historial_paciente(self, paciente_id, fecha_desde=None,
                                   fecha_hasta=None, area_id=None):
        """
        Obtiene el historial de solicitudes del paciente con filtros opcionales.

        Args:
            paciente_id: ID del paciente
            fecha_desde: datetime o None - filtrar desde esta fecha
            fecha_hasta: datetime o None - filtrar hasta esta fecha
            area_id: int o None - filtrar por area clinica

        Returns:
            Dict con {exito, solicitudes: [{SolicitudID, NumeroSolicitud,
                      FechaSolicitud, EstadoSolicitud, pruebas: [...]}]}
        """
        if not paciente_id:
            return {'exito': False, 'mensaje': 'Paciente no especificado', 'solicitudes': []}

        try:
            where = (f"s.PacienteID = {paciente_id} "
                     f"AND s.EstadoSolicitud <> 'Anulada'")

            if fecha_desde:
                where += f" AND s.FechaSolicitud >= #{fecha_desde.strftime('%m/%d/%Y')}#"
            if fecha_hasta:
                where += (f" AND s.FechaSolicitud <= "
                          f"#{fecha_hasta.strftime('%m/%d/%Y')} 23:59:59#")

            if area_id:
                where += (f" AND s.SolicitudID IN ("
                          f"SELECT d2.SolicitudID FROM DetalleSolicitudes d2 "
                          f"WHERE d2.PruebaID IN ("
                          f"SELECT PruebaID FROM Pruebas WHERE AreaID = {area_id}))")

            solicitudes = self.db.query(
                f"SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, "
                f"s.EstadoSolicitud, s.MontoTotal, "
                f"s.DiagnosticoPresuntivo, s.Observaciones "
                f"FROM Solicitudes s "
                f"WHERE {where} "
                f"ORDER BY s.FechaSolicitud DESC, s.SolicitudID DESC"
            )

            # Las pruebas de todas las solicitudes se traen de una vez: una
            # consulta por solicitud convertia el historial de un paciente
            # cronico en cuarenta viajes a la base de datos
            ids = [str(int(s['SolicitudID'])) for s in (solicitudes or [])]
            por_solicitud = {}
            if ids:
                prueba_where = f"d.SolicitudID IN ({', '.join(ids)})"
                if area_id:
                    prueba_where += f" AND p.AreaID = {area_id}"
                for pr in (self.db.query(
                        f"SELECT d.SolicitudID, d.DetalleID, d.PruebaID, d.Estado, "
                        f"p.CodigoPrueba, p.NombrePrueba "
                        f"FROM DetalleSolicitudes d "
                        f"LEFT JOIN Pruebas p ON d.PruebaID = p.PruebaID "
                        f"WHERE {prueba_where} "
                        f"ORDER BY p.NombrePrueba") or []):
                    por_solicitud.setdefault(pr.get('SolicitudID'), []).append(pr)

            for sol in (solicitudes or []):
                sol['pruebas'] = por_solicitud.get(sol['SolicitudID'], [])

            return {'exito': True, 'solicitudes': solicitudes or []}
        except Exception as e:
            return {'exito': False, 'mensaje': f'Error obteniendo historial: {e}', 'solicitudes': []}

    def obtener_areas_paciente(self, paciente_id):
        """Obtiene las areas clinicas distintas que tiene el paciente."""
        if not paciente_id:
            return []
        try:
            return self.db.query(
                f"SELECT DISTINCT a.AreaID, a.NombreArea "
                f"FROM ((DetalleSolicitudes d "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID) "
                f"INNER JOIN Pruebas p ON d.PruebaID = p.PruebaID) "
                f"INNER JOIN Areas a ON p.AreaID = a.AreaID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"ORDER BY a.NombreArea"
            ) or []
        except Exception:
            return []

    # ================================================================
    # RESULTADOS DE UN DETALLE
    # ================================================================

    def obtener_resultados_detalle(self, detalle_id):
        """
        Obtiene los resultados parametrizados de un detalle de solicitud.

        Returns:
            Lista de dicts con {NombreParametro, Valor, Unidad, ValorRef, Seccion,
                                FueraDeRango, TipoAlerta, ...}
        """
        try:
            # Obtener PruebaID del detalle
            detalle_info = self.db.query_one(
                f"SELECT PruebaID FROM DetalleSolicitudes WHERE DetalleID = {detalle_id}"
            )
            if not detalle_info:
                return []
            prueba_id = detalle_info['PruebaID']

            # Parametros de la prueba
            params = self.db.query(
                f"SELECT pp.ParametroID, par.NombreParametro, par.UnidadID, "
                f"par.Seccion, par.Observaciones AS ValorRefDefault, pp.Secuencia "
                f"FROM ParametrosPrueba pp "
                f"INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID "
                f"WHERE pp.PruebaID = {prueba_id} "
                f"ORDER BY pp.Secuencia"
            ) or []

            # Todos los valores del detalle en una sola consulta
            capturados = self._resultados_por_detalle([detalle_id])

            resultados = []
            for par in params:
                param_id = par['ParametroID']
                rp = capturados.get((detalle_id, param_id)) or {}
                valor_ref = rp.get('ValorReferencia') or par.get('ValorRefDefault') or ''
                fuera, tipo = self.evaluar_alerta(
                    rp.get('Valor'), valor_ref,
                    rp.get('FueraDeRango'), rp.get('TipoAlerta'))
                row = {
                    'NombreParametro': par.get('NombreParametro', ''),
                    'UnidadID': par.get('UnidadID'),
                    'Unidad': self._obtener_unidad(par.get('UnidadID')),
                    'ValorRef': valor_ref,
                    'Seccion': par.get('Seccion', ''),
                    'Secuencia': par.get('Secuencia', 0),
                    'Valor': rp.get('Valor', ''),
                    'Estado': rp.get('Estado', ''),
                    'FechaCaptura': rp.get('FechaCaptura'),
                    'FueraDeRango': fuera,
                    'TipoAlerta': tipo or (rp.get('TipoAlerta') or ''),
                }
                resultados.append(row)

            return resultados
        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning("Error obteniendo resultados detalle: %s", e)
            return []

    # ================================================================
    # COMPARATIVA (2 ULTIMAS INSTANCIAS DE UNA PRUEBA)
    # ================================================================

    def obtener_comparativa(self, paciente_id, prueba_id):
        """
        Compara los resultados de las dos ultimas instancias de una prueba.

        Returns:
            Dict con {exito, prueba_nombre, fecha_anterior, fecha_reciente,
                      parametros: [{nombre, unidad, valor_ref, valor_anterior,
                                   valor_reciente, tendencia, seccion}]}
        """
        if not paciente_id or not prueba_id:
            return {'exito': False, 'mensaje': 'Datos incompletos', 'parametros': []}

        try:
            detalles = self.db.query(
                f"SELECT TOP 2 d.DetalleID, s.SolicitudID, s.FechaSolicitud, "
                f"s.NumeroSolicitud "
                f"FROM DetalleSolicitudes d "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND d.PruebaID = {prueba_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"AND d.Estado IN ('Capturado', 'Validado') "
                f"ORDER BY s.FechaSolicitud DESC, s.SolicitudID DESC"
            )

            if not detalles or len(detalles) == 0:
                return {'exito': False, 'mensaje': 'No hay resultados para esta prueba',
                        'parametros': []}

            prueba_info = self.db.query_one(
                f"SELECT NombrePrueba FROM Pruebas WHERE PruebaID = {prueba_id}"
            )
            prueba_nombre = (prueba_info or {}).get('NombrePrueba', '')

            detalle_reciente = detalles[0]
            detalle_anterior = detalles[1] if len(detalles) > 1 else None

            parametros_def = self.db.query(
                f"SELECT pp.ParametroID, par.NombreParametro, par.UnidadID, "
                f"par.Seccion, par.Observaciones AS ValorRefDefault, pp.Secuencia "
                f"FROM ParametrosPrueba pp "
                f"INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID "
                f"WHERE pp.PruebaID = {prueba_id} "
                f"ORDER BY pp.Secuencia"
            )

            # Ambas mediciones en una sola consulta, en vez de dos por parametro
            ids_detalle = [detalle_reciente['DetalleID']]
            if detalle_anterior:
                ids_detalle.append(detalle_anterior['DetalleID'])
            capturados = self._resultados_por_detalle(ids_detalle)

            resultado_comparativo = []

            for param in (parametros_def or []):
                param_id = param['ParametroID']

                val_rec = capturados.get((detalle_reciente['DetalleID'], param_id)) or {}
                val_ant = {}
                if detalle_anterior:
                    val_ant = capturados.get(
                        (detalle_anterior['DetalleID'], param_id)) or {}

                valor_reciente = val_rec.get('Valor', '')
                valor_anterior = val_ant.get('Valor', '')
                valor_ref = (val_rec.get('ValorReferencia')
                             or val_ant.get('ValorReferencia')
                             or param.get('ValorRefDefault') or '')

                tendencia = self._evaluar_tendencia_parametro(
                    valor_anterior, valor_reciente, valor_ref
                )

                # Se evalua con la misma regla que el resumen y las alertas
                fuera_rango_rec, tipo_alerta_rec = self.evaluar_alerta(
                    valor_reciente, valor_ref,
                    val_rec.get('FueraDeRango'), val_rec.get('TipoAlerta'))
                fuera_rango_ant, tipo_alerta_ant = self.evaluar_alerta(
                    valor_anterior, valor_ref,
                    val_ant.get('FueraDeRango'), val_ant.get('TipoAlerta'))

                resultado_comparativo.append({
                    'nombre': param['NombreParametro'] or '',
                    'unidad': self._obtener_unidad(param.get('UnidadID')),
                    'valor_ref': valor_ref,
                    'valor_anterior': valor_anterior,
                    'valor_reciente': valor_reciente,
                    'tendencia': tendencia,
                    'seccion': param.get('Seccion') or '',
                    'fuera_rango_reciente': fuera_rango_rec,
                    'tipo_alerta_reciente': tipo_alerta_rec,
                    'fuera_rango_anterior': fuera_rango_ant,
                    'tipo_alerta_anterior': tipo_alerta_ant,
                })

            return {
                'exito': True,
                'prueba_nombre': prueba_nombre,
                'fecha_reciente': detalle_reciente.get('FechaSolicitud'),
                'numero_reciente': detalle_reciente.get('NumeroSolicitud', ''),
                'fecha_anterior': detalle_anterior.get('FechaSolicitud') if detalle_anterior else None,
                'numero_anterior': detalle_anterior.get('NumeroSolicitud', '') if detalle_anterior else '',
                'parametros': resultado_comparativo,
            }
        except Exception as e:
            return {'exito': False, 'mensaje': f'Error en comparativa: {e}', 'parametros': []}

    # ================================================================
    # PRUEBAS CON RESULTADOS
    # ================================================================

    def obtener_pruebas_con_resultados(self, paciente_id):
        """
        Obtiene lista de pruebas distintas realizadas al paciente con resultados.

        Returns:
            Lista de dicts con {PruebaID, CodigoPrueba, NombrePrueba, Veces, UltimaFecha}
        """
        if not paciente_id:
            return []

        try:
            return self.db.query(
                f"SELECT p.PruebaID, p.CodigoPrueba, p.NombrePrueba, "
                f"COUNT(*) AS Veces, MAX(s.FechaSolicitud) AS UltimaFecha "
                f"FROM (DetalleSolicitudes d "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID) "
                f"INNER JOIN Pruebas p ON d.PruebaID = p.PruebaID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"AND d.Estado IN ('Capturado', 'Validado') "
                f"GROUP BY p.PruebaID, p.CodigoPrueba, p.NombrePrueba "
                f"ORDER BY MAX(s.FechaSolicitud) DESC"
            ) or []
        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning("Error obteniendo pruebas con resultados: %s", e)
            return []

    # ================================================================
    # EVOLUCION DE UN PARAMETRO
    # ================================================================

    def obtener_evolucion_parametro(self, paciente_id, parametro_id):
        """
        Obtiene todos los valores historicos de un parametro especifico.

        Returns:
            Dict con {exito, nombre_parametro, unidad, valor_ref,
                      valores: [{fecha, valor, numero_solicitud}]}
        """
        if not paciente_id or not parametro_id:
            return {'exito': False, 'mensaje': 'Datos incompletos', 'valores': []}

        try:
            param_info = self.db.query_one(
                f"SELECT NombreParametro, UnidadID "
                f"FROM Parametros WHERE ParametroID = {parametro_id}"
            )
            if not param_info:
                return {'exito': False, 'mensaje': 'Parametro no encontrado', 'valores': []}

            valores = self.db.query(
                f"SELECT rp.Valor, rp.ValorReferencia, rp.FueraDeRango, rp.TipoAlerta, "
                f"rp.FechaCaptura, "
                f"s.FechaSolicitud, s.NumeroSolicitud "
                f"FROM (ResultadosParametros rp "
                f"INNER JOIN DetalleSolicitudes d ON rp.DetalleID = d.DetalleID) "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND rp.ParametroID = {parametro_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"AND rp.Valor IS NOT NULL AND rp.Valor <> '' "
                f"ORDER BY s.FechaSolicitud ASC"
            )

            # Tomar ValorReferencia del registro mas reciente que lo tenga
            valor_ref = ''
            for v in reversed(valores or []):
                if v.get('ValorReferencia'):
                    valor_ref = v['ValorReferencia']
                    break

            return {
                'exito': True,
                'nombre_parametro': param_info.get('NombreParametro', ''),
                'unidad': self._obtener_unidad(param_info.get('UnidadID')),
                'valor_ref': valor_ref,
                'valores': valores or [],
            }
        except Exception as e:
            return {'exito': False, 'mensaje': f'Error obteniendo evolucion: {e}', 'valores': []}

    # ================================================================
    # EVOLUCION COMPLETA DE UNA PRUEBA (TODOS LOS PARAMETROS)
    # ================================================================

    def obtener_evolucion_completa_prueba(self, paciente_id, prueba_id):
        """
        Obtiene el historial completo de TODOS los parametros de una prueba
        a traves de todas las solicitudes del paciente.

        Returns:
            Dict con {exito, prueba_nombre, mediciones: [
                {fecha, numero_solicitud, detalle_id}
            ], parametros: [{
                nombre, unidad, valor_ref, seccion, parametro_id,
                valores: [{fecha, valor, tendencia}],
                resumen: {minimo, maximo, promedio, tendencia_general}
            }]}
        """
        if not paciente_id or not prueba_id:
            return {'exito': False, 'mensaje': 'Datos incompletos'}

        try:
            prueba_info = self.db.query_one(
                f"SELECT NombrePrueba FROM Pruebas WHERE PruebaID = {prueba_id}"
            )
            prueba_nombre = (prueba_info or {}).get('NombrePrueba', '')

            # Todas las instancias de esta prueba para el paciente (cronologico)
            detalles = self.db.query(
                f"SELECT d.DetalleID, s.SolicitudID, s.FechaSolicitud, "
                f"s.NumeroSolicitud "
                f"FROM DetalleSolicitudes d "
                f"INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND d.PruebaID = {prueba_id} "
                f"AND s.EstadoSolicitud <> 'Anulada' "
                f"AND d.Estado IN ('Capturado', 'Validado') "
                f"ORDER BY s.FechaSolicitud ASC"
            )

            if not detalles:
                return {'exito': False, 'mensaje': 'No hay resultados para esta prueba'}

            # Lista de mediciones (eje temporal)
            mediciones = []
            for det in detalles:
                mediciones.append({
                    'fecha': det.get('FechaSolicitud'),
                    'numero_solicitud': det.get('NumeroSolicitud', ''),
                    'detalle_id': det['DetalleID'],
                })

            # Parametros de la prueba
            parametros_def = self.db.query(
                f"SELECT pp.ParametroID, par.NombreParametro, par.UnidadID, "
                f"par.Seccion, par.Observaciones AS ValorRefDefault, pp.Secuencia "
                f"FROM ParametrosPrueba pp "
                f"INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID "
                f"WHERE pp.PruebaID = {prueba_id} "
                f"ORDER BY pp.Secuencia"
            )

            # Todas las mediciones de todos los parametros en una sola consulta
            capturados = self._resultados_por_detalle(
                [d['DetalleID'] for d in detalles])

            parametros_resultado = []

            for param in (parametros_def or []):
                param_id = param['ParametroID']
                unidad = self._obtener_unidad(param.get('UnidadID'))

                # El rango de referencia se resuelve antes de recorrer las
                # mediciones: si se toma del primer registro que lo traiga, un
                # parametro nunca capturado se queda sin rango y la tendencia
                # no se puede calificar de favorable o desfavorable
                valor_ref = param.get('ValorRefDefault') or ''
                for det in detalles:
                    ref_row = (capturados.get((det['DetalleID'], param_id))
                               or {}).get('ValorReferencia')
                    if ref_row:
                        valor_ref = ref_row
                        break

                valores = []
                valores_numericos = []
                valor_anterior_str = None

                for det in detalles:
                    val_row = capturados.get((det['DetalleID'], param_id)) or {}
                    valor_str = val_row.get('Valor', '')

                    fuera_rango, tipo_alerta = self.evaluar_alerta(
                        valor_str, valor_ref,
                        val_row.get('FueraDeRango'), val_row.get('TipoAlerta'))

                    # Calcular tendencia respecto al valor anterior
                    tendencia = self._evaluar_tendencia_parametro(
                        valor_anterior_str, valor_str, valor_ref
                    ) if valor_anterior_str is not None else {
                        'direccion': 'sin_datos', 'favorable': None,
                        'icono': '—', 'color': '#9e9e9e'
                    }

                    valores.append({
                        'fecha': det.get('FechaSolicitud'),
                        'numero_solicitud': det.get('NumeroSolicitud', ''),
                        'valor': valor_str,
                        'tendencia': tendencia,
                        'fuera_rango': fuera_rango,
                        'tipo_alerta': tipo_alerta,
                    })

                    # Acumular numerico para resumen
                    if valor_str:
                        try:
                            valores_numericos.append(
                                float(str(valor_str).replace(',', '.'))
                            )
                        except (ValueError, TypeError):
                            pass

                    if valor_str:
                        valor_anterior_str = valor_str

                # Calcular resumen estadistico
                resumen = self._calcular_resumen_evolucion(
                    valores_numericos, valor_ref
                )

                parametros_resultado.append({
                    'nombre': param['NombreParametro'] or '',
                    'parametro_id': param_id,
                    'unidad': unidad,
                    'valor_ref': valor_ref,
                    'seccion': param.get('Seccion') or '',
                    'valores': valores,
                    'resumen': resumen,
                    # Permite que la interfaz oculte los parametros que este
                    # paciente nunca se hizo, en vez de listar filas vacias
                    'tiene_datos': bool(valores_numericos) or any(
                        v['valor'] for v in valores),
                })

            return {
                'exito': True,
                'prueba_nombre': prueba_nombre,
                'mediciones': mediciones,
                'parametros': parametros_resultado,
            }
        except Exception as e:
            return {'exito': False, 'mensaje': f'Error en evolucion completa: {e}'}

    def _calcular_resumen_evolucion(self, valores_numericos, valor_ref):
        """Calcula estadisticas de resumen para una lista de valores numericos."""
        if not valores_numericos:
            return {
                'minimo': None, 'maximo': None, 'promedio': None,
                'total_mediciones': 0, 'tendencia_general': 'sin_datos'
            }

        minimo = min(valores_numericos)
        maximo = max(valores_numericos)
        promedio = sum(valores_numericos) / len(valores_numericos)

        # Determinar tendencia general
        tendencia_general = 'estable'
        if len(valores_numericos) >= 2:
            primero = valores_numericos[0]
            ultimo = valores_numericos[-1]
            rango = maximo - minimo

            if rango > 0:
                cambio_pct = abs(ultimo - primero) / rango
                if cambio_pct < 0.15:
                    tendencia_general = 'estable'
                elif ultimo > primero:
                    favorable = self._es_favorable(primero, ultimo, valor_ref)
                    if favorable is True:
                        tendencia_general = 'mejorando'
                    elif favorable is False:
                        tendencia_general = 'empeorando'
                    else:
                        tendencia_general = 'subiendo'
                else:
                    favorable = self._es_favorable(primero, ultimo, valor_ref)
                    if favorable is True:
                        tendencia_general = 'mejorando'
                    elif favorable is False:
                        tendencia_general = 'empeorando'
                    else:
                        tendencia_general = 'bajando'

                # Detectar fluctuacion
                if len(valores_numericos) >= 3:
                    cambios_direccion = 0
                    for i in range(2, len(valores_numericos)):
                        d1 = valores_numericos[i-1] - valores_numericos[i-2]
                        d2 = valores_numericos[i] - valores_numericos[i-1]
                        if (d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0):
                            cambios_direccion += 1
                    if cambios_direccion >= len(valores_numericos) // 2:
                        tendencia_general = 'fluctuante'

        return {
            'minimo': minimo,
            'maximo': maximo,
            'promedio': round(promedio, 2),
            'total_mediciones': len(valores_numericos),
            'tendencia_general': tendencia_general,
        }

    # ================================================================
    # ALERTAS HISTORICAS
    # ================================================================

    def obtener_alertas_historicas(self, paciente_id, max_solicitudes=5):
        """
        Obtiene parametros que han estado fuera de rango en las ultimas
        N solicitudes del paciente.

        Returns:
            Lista de dicts con {parametro, valor, unidad, referencia,
                               tipo, fecha, numero_solicitud}
        """
        if not paciente_id:
            return []

        try:
            solicitudes = self.db.query(
                f"SELECT TOP {max_solicitudes} SolicitudID, FechaSolicitud, "
                f"NumeroSolicitud "
                f"FROM Solicitudes "
                f"WHERE PacienteID = {paciente_id} AND EstadoSolicitud <> 'Anulada' "
                f"ORDER BY FechaSolicitud DESC"
            )

            alertas = []
            for sol in (solicitudes or []):
                # Access exige parentesis con varios JOIN: sin ellos la
                # consulta lanzaba excepcion, el except devolvia [] y la vista
                # de alertas historicas quedaba vacia para todo paciente
                resultados = self.db.query(
                    f"SELECT par.NombreParametro, rp.ValorReferencia AS ValorRef, "
                    f"par.Observaciones AS ValorRefDefault, "
                    f"rp.Valor, rp.FueraDeRango, rp.TipoAlerta, u.Simbolo AS Unidad "
                    f"FROM ((ResultadosParametros rp "
                    f"INNER JOIN DetalleSolicitudes d ON rp.DetalleID = d.DetalleID) "
                    f"INNER JOIN Parametros par ON rp.ParametroID = par.ParametroID) "
                    f"LEFT JOIN Unidades u ON par.UnidadID = u.UnidadID "
                    f"WHERE d.SolicitudID = {sol['SolicitudID']} "
                    f"AND rp.Valor IS NOT NULL AND rp.Valor <> ''"
                )

                for r in (resultados or []):
                    valor_str = str(r.get('Valor', '')).replace(',', '.').strip()
                    valor_ref = (r.get('ValorRef')
                                 or r.get('ValorRefDefault') or '')
                    fuera, tipo = self.evaluar_alerta(
                        valor_str, valor_ref,
                        r.get('FueraDeRango'), r.get('TipoAlerta'))
                    if not fuera:
                        continue
                    alertas.append({
                        'parametro': r.get('NombreParametro', ''),
                        'valor': valor_str,
                        'unidad': r.get('Unidad') or '',
                        'referencia': valor_ref,
                        'tipo': tipo,
                        'critico': 'critico' in str(r.get('TipoAlerta') or '').lower(),
                        'fecha': sol.get('FechaSolicitud'),
                        'numero_solicitud': sol.get('NumeroSolicitud', ''),
                    })

            return alertas
        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning(
                "Error obteniendo alertas historicas: %s", e)
            return []

    # ================================================================
    # EVALUACION DE TENDENCIAS
    # ================================================================

    def _evaluar_tendencia_parametro(self, valor_anterior, valor_reciente, valor_ref):
        """
        Evalua la tendencia de un parametro entre dos mediciones.

        Returns:
            Dict con {direccion, favorable, icono, color}
        """
        if not valor_anterior or not valor_reciente:
            return {'direccion': 'sin_datos', 'favorable': None,
                    'icono': '\u2014', 'color': '#9e9e9e'}

        try:
            v_ant = float(str(valor_anterior).replace(',', '.'))
            v_rec = float(str(valor_reciente).replace(',', '.'))
        except (ValueError, TypeError):
            if str(valor_anterior).strip() == str(valor_reciente).strip():
                return {'direccion': 'estable', 'favorable': None,
                        'icono': '\u2192', 'color': '#9e9e9e'}
            else:
                return {'direccion': 'cambio', 'favorable': None,
                        'icono': '~', 'color': '#f59e0b'}

        tolerancia = 0.01
        if abs(v_rec - v_ant) <= tolerancia:
            return {'direccion': 'estable', 'favorable': None,
                    'icono': '\u2192', 'color': '#9e9e9e'}

        subio = v_rec > v_ant
        favorable = self._es_favorable(v_ant, v_rec, valor_ref)

        if subio:
            if favorable is True:
                return {'direccion': 'subio', 'favorable': True,
                        'icono': '\u2191', 'color': '#2e7d32'}
            elif favorable is False:
                return {'direccion': 'subio', 'favorable': False,
                        'icono': '\u2191', 'color': '#c62828'}
            else:
                return {'direccion': 'subio', 'favorable': None,
                        'icono': '\u2191', 'color': '#f59e0b'}
        else:
            if favorable is True:
                return {'direccion': 'bajo', 'favorable': True,
                        'icono': '\u2193', 'color': '#2e7d32'}
            elif favorable is False:
                return {'direccion': 'bajo', 'favorable': False,
                        'icono': '\u2193', 'color': '#c62828'}
            else:
                return {'direccion': 'bajo', 'favorable': None,
                        'icono': '\u2193', 'color': '#f59e0b'}

    def _es_favorable(self, v_ant, v_rec, valor_ref):
        """
        Determina si el cambio es favorable segun el rango de referencia.
        Formatos soportados: "3.5 - 5.5", "< 200", "> 40", "<= 100",
                             ">= 60", "70 - 110 mg/dL"

        Returns: True (mejorando), False (empeorando), None (no determinable)
        """
        if not valor_ref:
            return None

        ref_str = str(valor_ref).strip()

        # Formato "min - max" (con o sin unidades)
        match = re.search(r'([\d.,]+)\s*[-\u2013]\s*([\d.,]+)', ref_str)
        if match:
            try:
                ref_min = float(match.group(1).replace(',', '.'))
                ref_max = float(match.group(2).replace(',', '.'))
                centro = (ref_min + ref_max) / 2

                dist_ant = abs(v_ant - centro)
                dist_rec = abs(v_rec - centro)

                if dist_rec < dist_ant:
                    return True
                elif dist_rec > dist_ant:
                    return False
                else:
                    return None
            except (ValueError, TypeError):
                pass

        # Formato "< valor" o "<= valor" - valores mas bajos son mejores
        match = re.search(r'^[<≤]\s*=?\s*([\d.,]+)', ref_str)
        if match:
            try:
                limite = float(match.group(1).replace(',', '.'))
                # Acercarse al limite desde arriba es favorable
                dist_ant = max(0, v_ant - limite)
                dist_rec = max(0, v_rec - limite)
                if dist_rec < dist_ant:
                    return True
                elif dist_rec > dist_ant:
                    return False
                return None
            except (ValueError, TypeError):
                pass

        # Formato "> valor" o ">= valor" - valores mas altos son mejores
        match = re.search(r'^[>≥]\s*=?\s*([\d.,]+)', ref_str)
        if match:
            try:
                limite = float(match.group(1).replace(',', '.'))
                # Acercarse al limite desde abajo es favorable
                dist_ant = max(0, limite - v_ant)
                dist_rec = max(0, limite - v_rec)
                if dist_rec < dist_ant:
                    return True
                elif dist_rec > dist_ant:
                    return False
                return None
            except (ValueError, TypeError):
                pass

        return None

    # ================================================================
    # PREPARACION DE DATOS PARA INTERPRETACION IA
    # ================================================================

    def preparar_datos_para_ia(self, paciente_id, prueba_id, solicitud_id=None):
        """
        Prepara un paquete de datos estructurado para el motor de IA clinica.
        Combina: info del paciente, resultados actuales, historial previo y tendencias.

        Args:
            paciente_id: int
            prueba_id: int
            solicitud_id: int (opcional) - si None usa la mas reciente

        Returns:
            dict con:
                'paciente_info': dict datos demograficos del paciente
                'prueba_info': dict info de la prueba (nombre, area_id, codigo)
                'area_id': int
                'resultados_actuales': list[dict] parametros del ultimo resultado
                'parametros_alterados': list[dict] solo los fuera de rango
                'historial_evolucion': dict resultado de obtener_evolucion_completa_prueba
                'tiene_historial_previo': bool
                'n_mediciones_previas': int
        """
        resultado = {
            'paciente_info': {},
            'prueba_info': {},
            'area_id': None,
            'resultados_actuales': [],
            'parametros_alterados': [],
            'historial_evolucion': {},
            'tiene_historial_previo': False,
            'n_mediciones_previas': 0,
        }

        try:
            # Informacion del paciente
            pac = self.db.query_one(
                f"SELECT PacienteID, Nombres, Apellidos, FechaNacimiento, Sexo, "
                f"NumeroDocumento FROM Pacientes WHERE PacienteID = {paciente_id}"
            )
            if pac:
                resultado['paciente_info'] = dict(pac)

            # Informacion de la prueba y area
            prueba = self.db.query_one(
                f"SELECT p.PruebaID, p.NombrePrueba, p.CodigoPrueba, p.AreaID, "
                f"a.NombreArea FROM Pruebas p "
                f"LEFT JOIN Areas a ON p.AreaID = a.AreaID "
                f"WHERE p.PruebaID = {prueba_id}"
            )
            if prueba:
                resultado['prueba_info'] = dict(prueba)
                resultado['area_id'] = prueba.get('AreaID')

            # Determinar el DetalleID mas reciente para esta prueba/paciente
            filtro_sol = f"AND ds.SolicitudID = {solicitud_id}" if solicitud_id else ""
            detalle_rec = self.db.query_one(f"""
                SELECT TOP 1 ds.DetalleID, ds.SolicitudID, s.FechaSolicitud,
                       s.NumeroSolicitud
                FROM (Solicitudes s INNER JOIN DetalleSolicitudes ds
                      ON s.SolicitudID = ds.SolicitudID)
                WHERE s.PacienteID = {paciente_id}
                  AND ds.PruebaID = {prueba_id}
                  AND s.EstadoSolicitud NOT IN ('Anulada', 'Pendiente')
                  {filtro_sol}
                ORDER BY s.FechaSolicitud DESC
            """)

            if not detalle_rec:
                return resultado

            detalle_id = detalle_rec.get('DetalleID')
            sol_id = detalle_rec.get('SolicitudID')

            # Datos clinicos de la solicitud (diagnostico y observaciones del medico)
            if sol_id:
                try:
                    sol_info = self.db.query_one(
                        f"SELECT DiagnosticoPresuntivo, Observaciones, "
                        f"FechaSolicitud, NumeroSolicitud "
                        f"FROM Solicitudes WHERE SolicitudID = {sol_id}"
                    )
                    if sol_info:
                        resultado['paciente_info']['DiagnosticoPresuntivo'] = (
                            sol_info.get('DiagnosticoPresuntivo') or '')
                        resultado['paciente_info']['ObservacionesSolicitud'] = (
                            sol_info.get('Observaciones') or '')
                        resultado['paciente_info']['FechaSolicitud'] = (
                            sol_info.get('FechaSolicitud'))
                        resultado['paciente_info']['NumeroSolicitud'] = (
                            sol_info.get('NumeroSolicitud') or '')
                except Exception as e:
                    logging.getLogger("angeslab.historial_clinico").warning("[preparar_datos_para_ia] Error datos solicitud: %s", e)

            # Resultados del detalle actual
            try:
                filas = self.db.query(f"""
                    SELECT rp.ResultadoParamID, rp.ParametroID, rp.Valor,
                           rp.ValorReferencia, rp.FueraDeRango, rp.TipoAlerta,
                           pr.NombreParametro, pr.TipoResultado,
                           pr.UnidadID
                    FROM (ResultadosParametros rp
                    INNER JOIN Parametros pr ON rp.ParametroID = pr.ParametroID)
                    WHERE rp.DetalleID = {detalle_id}
                    ORDER BY pr.NombreParametro
                """)

                params_actuales = []
                params_alterados = []
                for r in filas:
                    unidad = self._obtener_unidad(r.get('UnidadID'))
                    fuera = r.get('FueraDeRango') or ''
                    alerta = r.get('TipoAlerta') or ''
                    param = {
                        'nombre': r.get('NombreParametro') or '',
                        'valor': str(r.get('Valor') or ''),
                        'valor_referencia': str(r.get('ValorReferencia') or ''),
                        'fuera_rango': str(fuera),
                        'tipo_alerta': str(alerta),
                        'unidad': unidad,
                        'parametro_id': r.get('ParametroID'),
                        'tipo_resultado': r.get('TipoResultado') or '',
                    }
                    params_actuales.append(param)
                    if fuera and str(fuera).lower() not in ('', 'none', 'false', '0'):
                        params_alterados.append(param)

                resultado['resultados_actuales'] = params_actuales
                resultado['parametros_alterados'] = params_alterados
            except Exception as e:
                logging.getLogger("angeslab.historial_clinico").warning("[preparar_datos_para_ia] Error resultados actuales: %s", e)

            # Historial de evolucion (reutiliza metodo existente)
            try:
                evolucion = self.obtener_evolucion_completa_prueba(paciente_id, prueba_id)
                resultado['historial_evolucion'] = evolucion
                n_med = len(evolucion.get('mediciones', []))
                resultado['n_mediciones_previas'] = max(0, n_med - 1)
                resultado['tiene_historial_previo'] = n_med > 1
            except Exception as e:
                logging.getLogger("angeslab.historial_clinico").warning("[preparar_datos_para_ia] Error historial: %s", e)

        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning("[preparar_datos_para_ia] Error general: %s", e)

        return resultado


    # ================================================================
    # TENDENCIAS GLOBALES DEL PACIENTE
    # ================================================================

    def obtener_tendencias_globales(self, paciente_id):
        """
        Calcula indicadores de tendencia global comparando las 2 ultimas solicitudes.

        Returns dict con:
            'exito': bool
            'total_params_ultima': int  - total de parametros con valor en ultima solicitud
            'alterados_ultima': int     - parametros fuera de rango en ultima solicitud
            'alterados_penultima': int  - parametros fuera de rango en solicitud anterior
            'mejorando': int  - params que estaban fuera y ahora estan normales
            'empeorando': int - params que estaban normales y ahora estan fuera
            'tendencia_global': str  - 'mejorando'|'empeorando'|'optimo'|'estable'|'sin_datos'
            'icono_tendencia': str
            'color_tendencia': str (hex)
        """
        resultado = {
            'exito': False,
            'total_params_ultima': 0,
            'alterados_ultima': 0,
            'alterados_penultima': 0,
            'mejorando': 0,
            'empeorando': 0,
            'tendencia_global': 'sin_datos',
            'icono_tendencia': '\u2014',
            'color_tendencia': '#9e9e9e',
        }
        try:
            # Obtener las 2 ultimas solicitudes del paciente
            soles = self.db.query(
                f"SELECT TOP 2 s.SolicitudID FROM Solicitudes s "
                f"WHERE s.PacienteID = {paciente_id} "
                f"AND s.EstadoSolicitud NOT IN ('Anulada', 'Pendiente') "
                f"ORDER BY s.FechaSolicitud DESC, s.SolicitudID DESC"
            )
            if not soles or len(soles) < 1:
                return resultado

            sol_ids = [s['SolicitudID'] for s in soles]
            sol_ultima = sol_ids[0]
            sol_penultima = sol_ids[1] if len(sol_ids) > 1 else None

            def _consultar(sol_id):
                """Parametros con valor de una solicitud, con su referencia."""
                return self.db.query(
                    f"SELECT rp.ParametroID, rp.Valor, rp.FueraDeRango, "
                    f"rp.TipoAlerta, rp.ValorReferencia, "
                    f"par.Observaciones AS ValorRefDefault "
                    f"FROM ((DetalleSolicitudes ds "
                    f"INNER JOIN ResultadosParametros rp "
                    f"    ON ds.DetalleID = rp.DetalleID) "
                    f"INNER JOIN Parametros par "
                    f"    ON rp.ParametroID = par.ParametroID) "
                    f"WHERE ds.SolicitudID = {sol_id} "
                    f"AND rp.Valor IS NOT NULL AND rp.Valor <> ''"
                ) or []

            def _es_fuera(r):
                # Se evalua con la misma regla que el resto del historial: leer
                # solo la columna FueraDeRango hacia que este banner anunciara
                # «Optimo» a un paciente con la hemoglobina y la glicemia
                # alteradas, porque esa columna esta en False en todo resultado
                # anterior a que la columna existiera
                fuera, _ = self.evaluar_alerta(
                    r.get('Valor'),
                    r.get('ValorReferencia') or r.get('ValorRefDefault') or '',
                    r.get('FueraDeRango'), r.get('TipoAlerta'))
                return fuera

            # Parametros de la ultima solicitud
            filas_ult = _consultar(sol_ultima)
            if not filas_ult:
                return resultado

            total_ult = len(filas_ult)
            set_alt_ult = {r['ParametroID'] for r in filas_ult if _es_fuera(r)}
            alt_ult = len(set_alt_ult)

            resultado['total_params_ultima'] = total_ult
            resultado['alterados_ultima'] = alt_ult
            resultado['exito'] = True

            if not sol_penultima:
                # Sin visita anterior: solo reportar estado actual
                if alt_ult == 0:
                    resultado.update({
                        'tendencia_global': 'optimo',
                        'icono_tendencia': '\u2713 \u00d3ptimo',
                        'color_tendencia': '#1b5e20',
                    })
                else:
                    resultado.update({
                        'tendencia_global': 'sin_datos',
                        'icono_tendencia': '\u2014 Sin historial previo',
                        'color_tendencia': '#9e9e9e',
                    })
                return resultado

            # Parametros de la penultima solicitud
            filas_pen = _consultar(sol_penultima)
            set_alt_pen = {r['ParametroID'] for r in (filas_pen or []) if _es_fuera(r)}
            alt_pen = len(set_alt_pen)

            resultado['alterados_penultima'] = alt_pen

            # Calcular cambios: mejorando = estaban fuera y ahora normales
            mejorando = len(set_alt_pen - set_alt_ult)
            empeorando = len(set_alt_ult - set_alt_pen)
            resultado['mejorando'] = mejorando
            resultado['empeorando'] = empeorando

            # Determinar tendencia global
            if alt_ult == 0 and alt_pen == 0:
                resultado.update({
                    'tendencia_global': 'optimo',
                    'icono_tendencia': '\u2713 \u00d3ptimo',
                    'color_tendencia': '#1b5e20',
                })
            elif mejorando > empeorando:
                resultado.update({
                    'tendencia_global': 'mejorando',
                    'icono_tendencia': '\u2191 Mejorando',
                    'color_tendencia': '#2e7d32',
                })
            elif empeorando > mejorando:
                resultado.update({
                    'tendencia_global': 'empeorando',
                    'icono_tendencia': '\u2193 Empeorando',
                    'color_tendencia': '#c62828',
                })
            else:
                resultado.update({
                    'tendencia_global': 'estable',
                    'icono_tendencia': '\u2192 Estable',
                    'color_tendencia': '#546e7a',
                })

        except Exception as e:
            logging.getLogger("angeslab.historial_clinico").warning("[obtener_tendencias_globales] Error: %s", e)

        return resultado


def crear_gestor_historial(db, usuario=None):
    """Crea una instancia del gestor de historial clinico."""
    return GestorHistorialClinico(db, usuario)

"""
================================================================================
MODULO DE REPORTES DE RESULTADOS - ANgesLAB
================================================================================
Genera reportes de resultados de laboratorio en diversos formatos:
- Reporte individual por solicitud
- Reporte por paciente
- Consolidados por area
- Alertas de valores criticos

Estructura de resultados por area:
- Hematologia: Serie roja, blanca, plaquetas
- Quimica: Perfiles lipidico, renal, hepatico
- Uroanalisis: Fisico, quimico, sedimento
- Coprologia: Macroscopico, microscopico, parasitologia

Autor: Sistema ANgesLAB
================================================================================
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
import os

# Importar configuración administrativa
try:
    from modulos.config_administrativa import ConfiguradorAdministrativo
    CONFIG_ADMIN_DISPONIBLE = True
except ImportError:
    CONFIG_ADMIN_DISPONIBLE = False

# ============================================================================
# CONFIGURACION DE REPORTES
# ============================================================================

class ConfigReportes:
    """Configuracion para generacion de reportes"""

    # Formato de fecha para reportes
    FORMATO_FECHA = "%d/%m/%Y"
    FORMATO_HORA = "%H:%M"
    FORMATO_FECHA_HORA = "%d/%m/%Y %H:%M"

    # Configuracion de secciones por area
    SECCIONES_POR_AREA = {
        1: {  # Hematologia
            "nombre": "HEMATOLOGIA",
            "secciones": ["Serie Roja", "Serie Blanca", "Plaquetas", "Otros"]
        },
        2: {  # Quimica Clinica
            "nombre": "QUIMICA CLINICA",
            "secciones": ["Glucosa", "Lipidos", "Renal", "Hepatico", "Proteinas", "Electrolitos", "Pancreatico", "Cardiaco"]
        },
        5: {  # Coagulacion
            "nombre": "COAGULACION",
            "secciones": ["Coagulacion"]
        },
        6: {  # Uroanalisis
            "nombre": "UROANALISIS",
            "secciones": ["Examen Fisico", "Examen Quimico", "Sedimento"]
        },
        7: {  # Coprologia
            "nombre": "COPROLOGIA",
            "secciones": ["Examen Macroscopico", "Examen Quimico", "Examen Microscopico", "Parasitologia"]
        },
        8: {  # Hormonas
            "nombre": "HORMONAS",
            "secciones": ["Tiroides", "Fertilidad", "Marcadores", "Metabolicas"]
        },
        9: {  # Serologia
            "nombre": "SEROLOGIA",
            "secciones": [
                "Antigenos Febriles", "Salmonella Typhi", "Salmonella Paratyphi",
                "Brucella", "Proteus OX-19",
                "Infecciosas", "Inflamatorios", "Autoinmunes"
            ]
        },
        10: {  # Microbiologia
            "nombre": "MICROBIOLOGIA / BACTERIOLOGIA",
            "secciones": ["Datos de Muestra", "Resultado del Cultivo", "Identificacion del Germen",
                          "Recuento de Colonias", "Coloracion de Gram", "Antibiograma", "Observaciones"]
        }
    }

    # Alertas de valores criticos
    VALORES_CRITICOS = {
        "HEMA_HB": {"bajo": 7.0, "alto": 20.0, "unidad": "g/dL"},
        "HEMA_PLT": {"bajo": 50000, "alto": 1000000, "unidad": "/mm3"},
        "HEMA_GB": {"bajo": 2000, "alto": 30000, "unidad": "/mm3"},
        "QUIM_GLI": {"bajo": 50, "alto": 400, "unidad": "mg/dL"},
        "QUIM_POTASIO": {"bajo": 2.5, "alto": 6.5, "unidad": "mEq/L"},
        "QUIM_SODIO": {"bajo": 120, "alto": 160, "unidad": "mEq/L"},
        "QUIM_CREAT": {"bajo": None, "alto": 10.0, "unidad": "mg/dL"},
    }


# ============================================================================
# CLASE PRINCIPAL DE REPORTES
# ============================================================================

class ReportesResultados:
    """
    Genera reportes de resultados de laboratorio
    """

    def __init__(self, db):
        self.db = db
        self.config = ConfigReportes()

        # Inicializar configuración administrativa
        if CONFIG_ADMIN_DISPONIBLE:
            try:
                self.config_admin = ConfiguradorAdministrativo(db)
            except:
                self.config_admin = None
        else:
            self.config_admin = None

    # -------------------------------------------------------------------------
    # OBTENCION DE DATOS
    # -------------------------------------------------------------------------

    def obtener_solicitud_completa(self, solicitud_id):
        """
        Obtiene todos los datos de una solicitud con sus resultados

        Retorna: dict con toda la informacion estructurada
        """
        # Datos de la solicitud
        solicitud = self.db.query_one(f"""
            SELECT
                s.*,
                p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                p.NumeroDocumento as CedulaPaciente,
                p.FechaNacimiento,
                p.Sexo,
                p.Edad,
                m.Nombres + ' ' + m.Apellidos as NombreMedico,
                m.NumeroMPPS
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not solicitud:
            return None

        # Pruebas solicitadas con sus resultados (tabla: DetalleSolicitudes)
        pruebas = self.db.query(f"""
            SELECT
                ds.DetalleID, ds.SolicitudID, ds.PruebaID, ds.Estado,
                pr.CodigoPrueba,
                pr.NombrePrueba,
                pr.AreaID,
                a.NombreArea
            FROM DetalleSolicitudes ds
            INNER JOIN Pruebas pr ON ds.PruebaID = pr.PruebaID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            WHERE ds.SolicitudID = {solicitud_id}
            ORDER BY a.NombreArea, pr.NombrePrueba
        """)

        # Para cada prueba, obtener sus resultados (tabla: ResultadosParametros)
        for prueba in pruebas:
            resultados = self.db.query(f"""
                SELECT
                    rp.ResultadoParamID, rp.DetalleID, rp.ParametroID, rp.Valor,
                    rp.Estado, rp.FechaCaptura,
                    param.CodigoParametro,
                    param.NombreParametro,
                    param.Seccion,
                    param.Observaciones as ValorReferencia,
                    u.Simbolo as UnidadSimbolo
                FROM ResultadosParametros rp
                INNER JOIN Parametros param ON rp.ParametroID = param.ParametroID
                LEFT JOIN Unidades u ON param.UnidadID = u.UnidadID
                WHERE rp.DetalleID = {prueba['DetalleID']}
                ORDER BY param.Seccion, rp.ResultadoParamID
            """)
            prueba['resultados'] = resultados

        solicitud['pruebas'] = pruebas

        return solicitud

    def obtener_resultados_por_area(self, solicitud_id):
        """
        Obtiene resultados organizados por area y seccion

        Retorna: dict estructurado por areas
        """
        solicitud = self.obtener_solicitud_completa(solicitud_id)
        if not solicitud:
            return None

        # Organizar por area
        por_area = {}
        for prueba in solicitud['pruebas']:
            area_id = prueba['AreaID']
            area_nombre = prueba['NombreArea']

            if area_id not in por_area:
                por_area[area_id] = {
                    'nombre': area_nombre,
                    'pruebas': [],
                    'secciones': {}
                }

            por_area[area_id]['pruebas'].append(prueba)

            # Organizar resultados por seccion
            for resultado in prueba.get('resultados', []):
                seccion = resultado.get('Seccion') or 'General'
                if seccion not in por_area[area_id]['secciones']:
                    por_area[area_id]['secciones'][seccion] = []
                por_area[area_id]['secciones'][seccion].append(resultado)

        solicitud['por_area'] = por_area
        return solicitud

    # -------------------------------------------------------------------------
    # EVALUACION DE RESULTADOS
    # -------------------------------------------------------------------------

    def evaluar_resultado(self, codigo_parametro, valor, sexo='M', edad=None):
        """
        Evalua un resultado y determina si esta fuera de rango

        Retorna: dict con {estado, alerta, mensaje}
        """
        # Verificar si es un valor critico
        if codigo_parametro in self.config.VALORES_CRITICOS:
            critico = self.config.VALORES_CRITICOS[codigo_parametro]
            try:
                valor_num = float(valor)
                if critico['bajo'] and valor_num < critico['bajo']:
                    return {
                        'estado': 'CRITICO_BAJO',
                        'alerta': True,
                        'mensaje': f"VALOR CRITICO BAJO: {valor} {critico['unidad']}"
                    }
                if critico['alto'] and valor_num > critico['alto']:
                    return {
                        'estado': 'CRITICO_ALTO',
                        'alerta': True,
                        'mensaje': f"VALOR CRITICO ALTO: {valor} {critico['unidad']}"
                    }
            except (ValueError, TypeError):
                pass

        # Evaluar contra valores de referencia de la BD
        ref = self.db.query_one(f"""
            SELECT * FROM ValoresReferencia
            WHERE ParametroID IN (
                SELECT ParametroID FROM Parametros WHERE CodigoParametro = '{codigo_parametro}'
            )
            AND (SexoAplica = 'A' OR SexoAplica = '{sexo}')
            ORDER BY SexoAplica DESC
        """)

        if ref:
            try:
                valor_num = float(valor)
                if ref.get('ValorMinimo') and valor_num < ref['ValorMinimo']:
                    return {
                        'estado': 'BAJO',
                        'alerta': False,
                        'mensaje': 'Valor por debajo del rango normal'
                    }
                if ref.get('ValorMaximo') and valor_num > ref['ValorMaximo']:
                    return {
                        'estado': 'ALTO',
                        'alerta': False,
                        'mensaje': 'Valor por encima del rango normal'
                    }
            except (ValueError, TypeError):
                pass

        return {
            'estado': 'NORMAL',
            'alerta': False,
            'mensaje': ''
        }

    def obtener_alertas_criticas(self, solicitud_id):
        """
        Obtiene todas las alertas criticas de una solicitud

        Retorna: lista de alertas
        """
        solicitud = self.obtener_solicitud_completa(solicitud_id)
        if not solicitud:
            return []

        alertas = []
        for prueba in solicitud['pruebas']:
            for resultado in prueba.get('resultados', []):
                valor = resultado.get('Valor')
                if valor is not None and valor != '':
                    try:
                        valor_num = float(str(valor).replace(',', '.').strip())
                    except (ValueError, TypeError):
                        continue  # No es numerico, saltar
                    evaluacion = self.evaluar_resultado(
                        resultado.get('CodigoParametro', ''),
                        valor_num,
                        solicitud.get('Sexo', 'M'),
                        solicitud.get('Edad')
                    )
                    if evaluacion['alerta']:
                        alertas.append({
                            'prueba': prueba['NombrePrueba'],
                            'parametro': resultado['NombreParametro'],
                            'valor': valor_num,
                            'unidad': resultado.get('UnidadSimbolo', ''),
                            'estado': evaluacion['estado'],
                            'mensaje': evaluacion['mensaje']
                        })

        return alertas

    # -------------------------------------------------------------------------
    # GENERACION DE REPORTES TEXTO
    # -------------------------------------------------------------------------

    def generar_reporte_texto(self, solicitud_id):
        """
        Genera reporte de resultados en formato texto

        Retorna: string con el reporte formateado
        """
        datos = self.obtener_resultados_por_area(solicitud_id)
        if not datos:
            return "Solicitud no encontrada"

        lineas = []
        ancho = 80

        # Encabezado
        lineas.append("=" * ancho)

        # Obtener configuración administrativa
        config_lab = None
        if self.config_admin:
            config_lab = self.config_admin.obtener_configuracion()

        # Usar texto personalizado de encabezado o por defecto
        if config_lab and config_lab.get('TextoEncabezado'):
            lineas.append(config_lab['TextoEncabezado'].center(ancho))
        else:
            lineas.append("REPORTE DE RESULTADOS DE LABORATORIO".center(ancho))

        lineas.append("=" * ancho)

        # Datos del laboratorio desde configuración administrativa
        if config_lab:
            if config_lab.get('NombreLaboratorio'):
                lineas.append(config_lab['NombreLaboratorio'].center(ancho))
            if config_lab.get('RazonSocial'):
                lineas.append(config_lab['RazonSocial'].center(ancho))
            if config_lab.get('RIF'):
                lineas.append(f"RIF: {config_lab['RIF']}".center(ancho))
            if config_lab.get('Direccion'):
                lineas.append(config_lab['Direccion'].center(ancho))
            if config_lab.get('Telefono1'):
                telefono_texto = f"Teléfono: {config_lab['Telefono1']}"
                if config_lab.get('WhatsApp'):
                    telefono_texto += f" | WhatsApp: {config_lab['WhatsApp']}"
                elif config_lab.get('Telefono2'):
                    telefono_texto += f" / {config_lab['Telefono2']}"
                lineas.append(telefono_texto.center(ancho))
            if config_lab.get('Email'):
                lineas.append(f"Email: {config_lab['Email']}".center(ancho))
        else:
            lineas.append("LABORATORIO CLINICO".center(ancho))

        lineas.append("-" * ancho)

        # Datos de la solicitud
        lineas.append(f"Solicitud No: {datos['NumeroSolicitud']}")
        lineas.append(f"Fecha: {datos['FechaSolicitud'].strftime('%d/%m/%Y') if datos['FechaSolicitud'] else 'N/A'}")
        lineas.append(f"Paciente: {datos['NombrePaciente']}")
        lineas.append(f"Cedula: {datos['CedulaPaciente']}")
        if datos.get('Edad'):
            lineas.append(f"Edad: {datos['Edad']} anos - Sexo: {'Masculino' if datos['Sexo'] == 'M' else 'Femenino'}")
        if datos.get('NombreMedico'):
            lineas.append(f"Medico: {datos['NombreMedico']}")

        lineas.append("=" * ancho)

        # Resultados por area
        for area_id, area_data in datos.get('por_area', {}).items():
            lineas.append("")
            lineas.append(f">>> {area_data['nombre']} <<<".center(ancho))
            lineas.append("-" * ancho)

            # Por cada seccion
            for seccion, resultados in area_data.get('secciones', {}).items():
                if seccion != 'General':
                    lineas.append(f"\n  {seccion}:")
                    lineas.append("  " + "-" * 40)

                for r in resultados:
                    nombre = r['NombreParametro']
                    valor = r.get('Valor') or '---'
                    unidad = r.get('UnidadSimbolo') or ''
                    referencia = r.get('ValorReferencia') or ''

                    # Indicador de fuera de rango (evaluar en vivo)
                    indicador = ""
                    try:
                        valor_num = float(str(valor).replace(',', '.').strip())
                        eval_r = self.evaluar_resultado(
                            r.get('CodigoParametro', ''), valor_num,
                            datos.get('Sexo', 'M'), datos.get('Edad')
                        )
                        if eval_r.get('estado') in ('CRITICO_BAJO', 'CRITICO_ALTO'):
                            indicador = " ***"
                        elif eval_r.get('estado') == 'ALTO':
                            indicador = " (H)"
                        elif eval_r.get('estado') == 'BAJO':
                            indicador = " (L)"
                    except (ValueError, TypeError):
                        pass

                    linea = f"  {nombre:<25} {valor:>10} {unidad:<8} {referencia:<20}{indicador}"
                    lineas.append(linea)

        # Pie de reporte
        lineas.append("")
        lineas.append("=" * ancho)
        lineas.append("Fecha de impresion: " + datetime.now().strftime('%d/%m/%Y %H:%M'))

        # Alertas criticas
        alertas = self.obtener_alertas_criticas(solicitud_id)
        if alertas:
            lineas.append("")
            lineas.append("*** ALERTAS DE VALORES CRITICOS ***")
            for a in alertas:
                lineas.append(f"  ! {a['parametro']}: {a['valor']} {a['unidad']} - {a['mensaje']}")

        # Notas de resultados personalizadas
        if config_lab and config_lab.get('NotasResultados'):
            lineas.append("")
            lineas.append(config_lab['NotasResultados'])

        # Firma del director
        if config_lab and config_lab.get('MostrarFirma'):
            lineas.append("")
            lineas.append("=" * ancho)
            lineas.append("")
            lineas.append("_" * 40)
            if config_lab.get('NombreDirector'):
                lineas.append(config_lab['NombreDirector'].center(ancho))
            if config_lab.get('TituloDirector'):
                lineas.append(config_lab['TituloDirector'].center(ancho))
            if config_lab.get('TextoAutorizacion'):
                lineas.append("")
                lineas.append(config_lab['TextoAutorizacion'].center(ancho))

        # Texto de pie de página personalizado
        if config_lab and config_lab.get('TextoPiePagina'):
            lineas.append("")
            lineas.append(config_lab['TextoPiePagina'].center(ancho))
        else:
            lineas.append("")
            lineas.append("*** Este reporte no tiene validez sin firma del bioanalista ***")

        # Horario de atención
        if config_lab and config_lab.get('HorarioAtencion'):
            lineas.append("")
            lineas.append(f"Horario de Atención: {config_lab['HorarioAtencion']}".center(ancho))

        lineas.append("=" * ancho)

        return "\n".join(lineas)

    # -------------------------------------------------------------------------
    # REPORTES ESPECIFICOS POR AREA
    # -------------------------------------------------------------------------

    def generar_reporte_hematologia(self, solicitud_id):
        """Genera reporte especifico de hematologia"""
        datos = self.obtener_resultados_por_area(solicitud_id)
        if not datos or 1 not in datos.get('por_area', {}):
            return "No hay resultados de hematologia"

        hema = datos['por_area'][1]
        lineas = []

        lineas.append("HEMATOLOGIA COMPLETA")
        lineas.append("=" * 60)

        # Serie Roja
        if 'Serie Roja' in hema.get('secciones', {}):
            lineas.append("\nSERIE ROJA:")
            lineas.append("-" * 40)
            for r in hema['secciones']['Serie Roja']:
                nombre = r['NombreParametro']
                valor = r.get('Valor') or '---'
                ref = r.get('ValorReferencia') or ''
                lineas.append(f"  {nombre:<20} {valor:>10}  {ref}")

        # Serie Blanca
        if 'Serie Blanca' in hema.get('secciones', {}):
            lineas.append("\nSERIE BLANCA:")
            lineas.append("-" * 40)
            for r in hema['secciones']['Serie Blanca']:
                nombre = r['NombreParametro']
                valor = r.get('Valor') or '---'
                ref = r.get('ValorReferencia') or ''
                lineas.append(f"  {nombre:<20} {valor:>10}  {ref}")

        # Plaquetas
        if 'Plaquetas' in hema.get('secciones', {}):
            lineas.append("\nPLAQUETAS:")
            lineas.append("-" * 40)
            for r in hema['secciones']['Plaquetas']:
                nombre = r['NombreParametro']
                valor = r.get('Valor') or '---'
                ref = r.get('ValorReferencia') or ''
                lineas.append(f"  {nombre:<20} {valor:>10}  {ref}")

        return "\n".join(lineas)

    def generar_reporte_quimica(self, solicitud_id):
        """Genera reporte especifico de quimica clinica"""
        datos = self.obtener_resultados_por_area(solicitud_id)
        if not datos or 2 not in datos.get('por_area', {}):
            return "No hay resultados de quimica clinica"

        quim = datos['por_area'][2]
        lineas = []

        lineas.append("QUIMICA CLINICA")
        lineas.append("=" * 60)

        for seccion_nombre in ['Glucosa', 'Lipidos', 'Renal', 'Hepatico', 'Proteinas', 'Electrolitos']:
            if seccion_nombre in quim.get('secciones', {}):
                lineas.append(f"\n{seccion_nombre.upper()}:")
                lineas.append("-" * 40)
                for r in quim['secciones'][seccion_nombre]:
                    nombre = r['NombreParametro']
                    valor = r.get('Valor') or '---'
                    unidad = r.get('UnidadSimbolo') or ''
                    ref = r.get('ValorReferencia') or ''

                    indicador = ""
                    try:
                        valor_num = float(str(valor).replace(',', '.').strip())
                        eval_r = self.evaluar_resultado(r.get('CodigoParametro', ''), valor_num)
                        if eval_r.get('estado') != 'NORMAL':
                            indicador = " *"
                    except (ValueError, TypeError):
                        pass

                    lineas.append(f"  {nombre:<25} {valor:>8} {unidad:<8} {ref}{indicador}")

        return "\n".join(lineas)

    def generar_reporte_uroanalisis(self, solicitud_id):
        """Genera reporte especifico de uroanalisis"""
        datos = self.obtener_resultados_por_area(solicitud_id)
        if not datos or 6 not in datos.get('por_area', {}):
            return "No hay resultados de uroanalisis"

        uro = datos['por_area'][6]
        lineas = []

        lineas.append("EXAMEN GENERAL DE ORINA")
        lineas.append("=" * 60)

        for seccion_nombre in ['Examen Fisico', 'Examen Quimico', 'Sedimento']:
            if seccion_nombre in uro.get('secciones', {}):
                lineas.append(f"\n{seccion_nombre.upper()}:")
                lineas.append("-" * 40)
                for r in uro['secciones'][seccion_nombre]:
                    nombre = r['NombreParametro']
                    valor = r.get('Valor') or '---'
                    ref = r.get('ValorReferencia') or ''
                    lineas.append(f"  {nombre:<25} {valor:<15} {ref}")

        return "\n".join(lineas)

    def generar_reporte_coprologia(self, solicitud_id):
        """Genera reporte especifico de coprologia"""
        datos = self.obtener_resultados_por_area(solicitud_id)
        if not datos or 7 not in datos.get('por_area', {}):
            return "No hay resultados de coprologia"

        copro = datos['por_area'][7]
        lineas = []

        lineas.append("EXAMEN DE HECES (COPROANALISIS)")
        lineas.append("=" * 60)

        for seccion_nombre in ['Examen Macroscopico', 'Examen Quimico', 'Examen Microscopico', 'Parasitologia']:
            if seccion_nombre in copro.get('secciones', {}):
                lineas.append(f"\n{seccion_nombre.upper()}:")
                lineas.append("-" * 40)
                for r in copro['secciones'][seccion_nombre]:
                    nombre = r['NombreParametro']
                    valor = r.get('Valor') or '---'
                    ref = r.get('ValorReferencia') or ''
                    lineas.append(f"  {nombre:<25} {valor:<15} {ref}")

        return "\n".join(lineas)

    def generar_reporte_serologia(self, solicitud_id):
        """Genera reporte especifico de serologia / antigenos febriles"""
        datos = self.obtener_resultados_por_area(solicitud_id)
        if not datos or 9 not in datos.get('por_area', {}):
            return "No hay resultados de serologia"

        sero = datos['por_area'][9]
        lineas = []

        lineas.append("SEROLOGIA - ANTIGENOS FEBRILES")
        lineas.append("=" * 60)

        # Secciones de antigenos febriles primero
        secciones_febriles = [
            'Antigenos Febriles', 'Salmonella Typhi', 'Salmonella Paratyphi',
            'Brucella', 'Proteus OX-19'
        ]
        # Luego el resto de secciones serologicas
        secciones_otras = ['Infecciosas', 'Inflamatorios', 'Autoinmunes']

        for seccion_nombre in secciones_febriles + secciones_otras:
            if seccion_nombre in sero.get('secciones', {}):
                lineas.append(f"\n{seccion_nombre.upper()}:")
                lineas.append("-" * 40)
                for r in sero['secciones'][seccion_nombre]:
                    nombre = r['NombreParametro']
                    valor = r.get('Valor') or '---'
                    unidad = r.get('UnidadSimbolo') or ''
                    ref = r.get('ValorReferencia') or ''

                    indicador = ""
                    try:
                        # Para titulaciones, evaluar si es positivo
                        valor_str = str(valor).strip().upper()
                        if valor_str.startswith('1:') or valor_str.startswith('1/'):
                            # Es una titulacion (1:80, 1:160, etc.)
                            partes = valor_str.replace('/', ':').split(':')
                            if len(partes) == 2:
                                titulo = int(partes[1])
                                if titulo >= 160:
                                    indicador = " ** POSITIVO **"
                                elif titulo >= 80:
                                    indicador = " * SOSPECHOSO *"
                        elif valor_str in ['POSITIVO', 'REACTIVO']:
                            indicador = " ** POSITIVO **"
                    except (ValueError, TypeError):
                        pass

                    linea = f"  {nombre:<30} {valor:>12} {unidad:<8} {ref:<20}{indicador}"
                    lineas.append(linea)

        # Tambien capturar secciones no listadas explicitamente
        for seccion_nombre, resultados in sero.get('secciones', {}).items():
            if seccion_nombre not in secciones_febriles + secciones_otras and seccion_nombre != 'General':
                lineas.append(f"\n{seccion_nombre.upper()}:")
                lineas.append("-" * 40)
                for r in resultados:
                    nombre = r['NombreParametro']
                    valor = r.get('Valor') or '---'
                    ref = r.get('ValorReferencia') or ''
                    lineas.append(f"  {nombre:<30} {valor:>12}  {ref}")

        lineas.append("")
        lineas.append("NOTA: Para antigenos febriles, titulaciones >= 1:160 se")
        lineas.append("consideran significativas. Titulaciones de 1:80 son sospechosas")
        lineas.append("y deben correlacionarse con cuadro clinico. Se recomienda")
        lineas.append("segunda muestra a los 7-14 dias para demostrar seroconversion.")

        return "\n".join(lineas)

    # -------------------------------------------------------------------------
    # REPORTES CONSOLIDADOS
    # -------------------------------------------------------------------------

    def generar_reporte_diario(self, fecha):
        """
        Genera reporte consolidado de solicitudes del dia

        Retorna: dict con estadisticas del dia
        """
        fecha_str = fecha.strftime('%m/%d/%Y')

        # Total de solicitudes
        total = self.db.query_one(f"""
            SELECT COUNT(*) as Total FROM Solicitudes
            WHERE DATEVALUE(FechaSolicitud) = #{fecha_str}#
        """)

        # Por estado
        por_estado = self.db.query(f"""
            SELECT EstadoSolicitud, COUNT(*) as Cantidad
            FROM Solicitudes
            WHERE DATEVALUE(FechaSolicitud) = #{fecha_str}#
            GROUP BY EstadoSolicitud
        """)

        # Por area
        por_area = self.db.query(f"""
            SELECT a.NombreArea, COUNT(DISTINCT ds.SolicitudID) as Solicitudes, COUNT(ds.DetalleID) as Pruebas
            FROM DetalleSolicitudes ds
            INNER JOIN Pruebas p ON ds.PruebaID = p.PruebaID
            INNER JOIN Areas a ON p.AreaID = a.AreaID
            INNER JOIN Solicitudes s ON ds.SolicitudID = s.SolicitudID
            WHERE DATEVALUE(s.FechaSolicitud) = #{fecha_str}#
            GROUP BY a.NombreArea
        """)

        # Ingresos del dia
        ingresos = self.db.query_one(f"""
            SELECT
                SUM(MontoTotal) as Total,
                SUM(CASE WHEN EstadoPago='Pagada' THEN MontoCobrado ELSE 0 END) as Cobrado
            FROM Facturas
            WHERE DATEVALUE(FechaEmision) = #{fecha_str}# AND Anulada = False
        """)

        return {
            'fecha': fecha,
            'total_solicitudes': total['Total'] if total else 0,
            'por_estado': {e['EstadoSolicitud']: e['Cantidad'] for e in por_estado},
            'por_area': por_area,
            'ingresos_total': ingresos['Total'] if ingresos and ingresos['Total'] else 0,
            'ingresos_cobrado': ingresos['Cobrado'] if ingresos and ingresos['Cobrado'] else 0
        }

    def generar_reporte_paciente(self, paciente_id, fecha_desde=None, fecha_hasta=None):
        """
        Genera historial de resultados de un paciente

        Retorna: lista de solicitudes con sus resultados
        """
        where = f"s.PacienteID = {paciente_id}"
        if fecha_desde:
            where += f" AND s.FechaSolicitud >= #{fecha_desde.strftime('%m/%d/%Y')}#"
        if fecha_hasta:
            where += f" AND s.FechaSolicitud <= #{fecha_hasta.strftime('%m/%d/%Y')}#"

        solicitudes = self.db.query(f"""
            SELECT s.*, p.Nombres + ' ' + p.Apellidos as NombrePaciente
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            WHERE {where}
            ORDER BY s.FechaSolicitud DESC
        """)

        for sol in solicitudes:
            sol['pruebas'] = self.db.query(f"""
                SELECT ds.DetalleID, ds.SolicitudID, ds.PruebaID, ds.Estado,
                       pr.NombrePrueba, a.NombreArea
                FROM DetalleSolicitudes ds
                INNER JOIN Pruebas pr ON ds.PruebaID = pr.PruebaID
                INNER JOIN Areas a ON pr.AreaID = a.AreaID
                WHERE ds.SolicitudID = {sol['SolicitudID']}
            """)

        return solicitudes


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("Modulo de Reportes de Resultados - ANgesLAB")
    print("=" * 50)
    print("\nEste modulo requiere una conexion a la base de datos.")
    print("Funciones disponibles:")
    print("  - generar_reporte_texto(solicitud_id)")
    print("  - generar_reporte_hematologia(solicitud_id)")
    print("  - generar_reporte_quimica(solicitud_id)")
    print("  - generar_reporte_uroanalisis(solicitud_id)")
    print("  - generar_reporte_coprologia(solicitud_id)")
    print("  - generar_reporte_serologia(solicitud_id)")
    print("  - generar_reporte_diario(fecha)")
    print("  - generar_reporte_paciente(paciente_id)")

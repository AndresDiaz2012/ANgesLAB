"""
================================================================================
MODULO DE PLANTILLAS DE REPORTES - ANgesLAB
================================================================================
Contiene las 73 plantillas de reportes del sistema organizadas por categoria:
- Reportes de Recepcion (12)
- Reportes de Resultados por Area (31)
- Reportes de Microbiologia/Bacteriologia (4)
- Reportes de Facturacion (11)
- Reportes Gerenciales (8)
- Reportes de Inventario (4)
- Reportes de Auditoria (3)

Autor: Sistema ANgesLAB
================================================================================
"""

from datetime import datetime, date
from decimal import Decimal
import os

# ============================================================================
# CONFIGURACION DE PLANTILLAS
# ============================================================================

class ConfigPlantillas:
    """Configuracion global de plantillas"""

    # Rutas de plantillas
    TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')

    # Estilos CSS comunes
    CSS_COMUN = """
    <style>
        @page { margin: 1cm; }
        body { font-family: Arial, sans-serif; font-size: 11pt; }
        .header { text-align: center; margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 14pt; }
        .header h2 { margin: 5px 0; font-size: 12pt; font-weight: normal; }
        .info-box { border: 1px solid #333; padding: 10px; margin: 10px 0; }
        .info-row { display: flex; margin: 3px 0; }
        .info-label { font-weight: bold; width: 120px; }
        .info-value { flex: 1; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { border: 1px solid #333; padding: 5px; text-align: left; }
        th { background-color: #f0f0f0; }
        .section-title { background-color: #333; color: white; padding: 5px 10px; margin: 15px 0 5px 0; }
        .footer { margin-top: 30px; text-align: center; font-size: 9pt; }
        .firma { margin-top: 50px; text-align: center; }
        .firma-linea { border-top: 1px solid #333; width: 200px; margin: 0 auto; }
        .alerta { color: red; font-weight: bold; }
        .valor-alto { color: red; }
        .valor-bajo { color: blue; }
        .codigo-barras { font-family: 'Libre Barcode 39', monospace; font-size: 36pt; }
        .text-center { text-align: center; }
        .text-right { text-align: right; }
        .bold { font-weight: bold; }
        .small { font-size: 9pt; }
    </style>
    """


# ============================================================================
# CLASE PRINCIPAL DE PLANTILLAS
# ============================================================================

class PlantillasReportes:
    """
    Genera reportes usando plantillas HTML
    """

    def __init__(self, db):
        self.db = db
        self.config = ConfigPlantillas()
        self._cargar_config_laboratorio()

    def _cargar_config_laboratorio(self):
        """Carga la configuracion del laboratorio"""
        try:
            # Intentar ConfiguracionLaboratorio primero (tabla principal)
            config = self.db.query_one("SELECT * FROM ConfiguracionLaboratorio")
            if not config:
                config = self.db.query_one("SELECT * FROM ConfiguracionSistema")
            self.lab_nombre = (config.get('NombreLaboratorio') or 'LABORATORIO CLINICO') if config else 'LABORATORIO CLINICO'
            self.lab_rif = (config.get('RIF') or '') if config else ''
            self.lab_direccion = (config.get('Direccion') or '') if config else ''
            self.lab_telefono = (config.get('Telefono1') or config.get('Telefono') or '') if config else ''
            self.lab_whatsapp = (config.get('WhatsApp') or '') if config else ''
            self.lab_email = (config.get('Email') or '') if config else ''
        except:
            self.lab_nombre = 'LABORATORIO CLINICO'
            self.lab_rif = ''
            self.lab_direccion = ''
            self.lab_telefono = ''
            self.lab_whatsapp = ''
            self.lab_email = ''

    # -------------------------------------------------------------------------
    # ENCABEZADO COMUN
    # -------------------------------------------------------------------------

    def _generar_encabezado(self, titulo_reporte):
        """Genera el encabezado HTML comun para todos los reportes"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{titulo_reporte}</title>
            {self.config.CSS_COMUN}
        </head>
        <body>
            <div class="header">
                <h1>{self.lab_nombre}</h1>
                <h2>RIF: {self.lab_rif}</h2>
                <p class="small">{self.lab_direccion}</p>
                <p class="small">Tel: {self.lab_telefono}{f' | WhatsApp: {self.lab_whatsapp}' if self.lab_whatsapp else ''}{f' | Email: {self.lab_email}' if self.lab_email else ''}</p>
                <hr>
                <h2>{titulo_reporte}</h2>
            </div>
        """

    def _generar_pie(self, incluir_firma=True):
        """Genera el pie de pagina"""
        html = '<div class="footer">'

        if incluir_firma:
            html += """
            <div class="firma">
                <div class="firma-linea"></div>
                <p>Bioanalista Responsable</p>
            </div>
            """

        html += f"""
            <p>Impreso: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p class="small">Este documento no tiene validez sin firma del profesional responsable</p>
        </div>
        </body>
        </html>
        """
        return html

    # =========================================================================
    # REPORTES DE RECEPCION (R01 - R12)
    # =========================================================================

    def R01_comprobante_solicitud(self, solicitud_id):
        """
        R01 - Comprobante de Solicitud
        Entrega al paciente al momento del registro
        """
        # Obtener datos de la solicitud
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento as CedulaPaciente,
                   p.Telefono as TelefonoPaciente,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body><h1>Solicitud no encontrada</h1></body></html>"

        # Obtener pruebas
        pruebas = self.db.query(f"""
            SELECT ps.*, pr.NombrePrueba, pr.PrecioBase
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            WHERE ps.SolicitudID = {solicitud_id}
            ORDER BY pr.NombrePrueba
        """)

        # Calcular totales
        total = sum(p.get('PrecioBase', 0) or 0 for p in pruebas)

        # Obtener pagos
        pagos = self.db.query(f"""
            SELECT SUM(Monto) as TotalPagado FROM Pagos
            WHERE FacturaID IN (SELECT FacturaID FROM Facturas WHERE SolicitudID = {solicitud_id})
        """)
        pagado = pagos[0].get('TotalPagado', 0) if pagos and pagos[0].get('TotalPagado') else 0
        pendiente = total - pagado

        html = self._generar_encabezado("COMPROBANTE DE SOLICITUD")

        html += f"""
        <div class="info-box">
            <div style="display: flex; justify-content: space-between;">
                <div>
                    <p class="bold">Solicitud No: {sol.get('NumeroSolicitud', 'N/A')}</p>
                    <p>Fecha: {sol.get('FechaSolicitud').strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'}</p>
                </div>
                <div class="text-right">
                    <p class="codigo-barras">*{sol.get('NumeroSolicitud', '')}*</p>
                </div>
            </div>
        </div>

        <div class="info-box">
            <h3>Datos del Paciente</h3>
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('CedulaPaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Telefono:</span>
                <span class="info-value">{sol.get('TelefonoPaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Medico:</span>
                <span class="info-value">{sol.get('NombreMedico', 'Particular')}</span>
            </div>
        </div>

        <h3>Pruebas Solicitadas</h3>
        <table>
            <thead>
                <tr>
                    <th>No.</th>
                    <th>Prueba</th>
                    <th class="text-right">Precio</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, prueba in enumerate(pruebas, 1):
            precio = prueba.get('PrecioBase', 0) or 0
            html += f"""
                <tr>
                    <td>{i}</td>
                    <td>{prueba.get('NombrePrueba', 'N/A')}</td>
                    <td class="text-right">{precio:,.2f}</td>
                </tr>
            """

        html += f"""
            </tbody>
            <tfoot>
                <tr>
                    <td colspan="2" class="text-right bold">TOTAL:</td>
                    <td class="text-right bold">{total:,.2f}</td>
                </tr>
                <tr>
                    <td colspan="2" class="text-right">Abonado:</td>
                    <td class="text-right">{pagado:,.2f}</td>
                </tr>
                <tr>
                    <td colspan="2" class="text-right bold">Pendiente:</td>
                    <td class="text-right bold">{pendiente:,.2f}</td>
                </tr>
            </tfoot>
        </table>

        <div class="info-box">
            <h3>Fecha Estimada de Entrega</h3>
            <p class="bold text-center" style="font-size: 14pt;">
                {sol.get('FechaEntrega').strftime('%d/%m/%Y') if sol.get('FechaEntrega') else 'Consultar en recepcion'}
            </p>
        </div>

        <div class="small" style="margin-top: 20px;">
            <p><strong>INSTRUCCIONES:</strong></p>
            <ul>
                <li>Presente este comprobante para retirar sus resultados</li>
                <li>Los resultados solo se entregan al paciente o persona autorizada</li>
                <li>Horario de entrega: Lunes a Viernes 8:00am - 5:00pm</li>
            </ul>
        </div>
        """

        html += self._generar_pie(incluir_firma=False)
        return html

    def R02_boleta_principal(self, solicitud_id):
        """
        R02 - Boleta Principal de Solicitud
        Etiqueta para muestras y seguimiento
        """
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento as CedulaPaciente
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        # Obtener areas involucradas
        areas = self.db.query(f"""
            SELECT DISTINCT a.CodigoArea, a.NombreArea
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            WHERE ps.SolicitudID = {solicitud_id}
        """)

        areas_texto = ", ".join([a.get('CodigoArea', '') for a in areas])

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; font-size: 10pt; width: 10cm; }}
                .codigo {{ font-family: 'Libre Barcode 39', monospace; font-size: 28pt; text-align: center; }}
                .numero {{ font-size: 14pt; font-weight: bold; text-align: center; }}
                .paciente {{ font-size: 12pt; margin: 5px 0; }}
                .areas {{ background: #333; color: white; padding: 3px; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="numero">{sol.get('NumeroSolicitud', 'N/A')}</div>
            <div class="codigo">*{sol.get('NumeroSolicitud', '')}*</div>
            <div class="paciente">{sol.get('NombrePaciente', 'N/A')[:30]}</div>
            <div>CI: {sol.get('CedulaPaciente', 'N/A')}</div>
            <div>{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            <div class="areas">{areas_texto}</div>
        </body>
        </html>
        """
        return html

    def R03_lista_pacientes_dia(self, fecha=None):
        """
        R03 - Lista de Pacientes del Dia
        """
        if fecha is None:
            fecha = date.today()
        fecha_str = fecha.strftime('%m/%d/%Y')

        pacientes = self.db.query(f"""
            SELECT s.NumeroSolicitud, s.FechaSolicitud,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento,
                   COUNT(ps.PruebaSolicitadaID) as CantidadPruebas,
                   s.EstadoSolicitud
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN PruebasSolicitadas ps ON s.SolicitudID = ps.SolicitudID
            WHERE DATEVALUE(s.FechaSolicitud) = #{fecha_str}#
            GROUP BY s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud,
                     p.Nombres, p.Apellidos, p.NumeroDocumento, s.EstadoSolicitud
            ORDER BY s.FechaSolicitud
        """)

        html = self._generar_encabezado(f"LISTA DE PACIENTES - {fecha.strftime('%d/%m/%Y')}")

        html += f"""
        <p>Total de pacientes: <strong>{len(pacientes)}</strong></p>

        <table>
            <thead>
                <tr>
                    <th>No.</th>
                    <th>Solicitud</th>
                    <th>Paciente</th>
                    <th>Cedula</th>
                    <th>Pruebas</th>
                    <th>Estado</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, pac in enumerate(pacientes, 1):
            html += f"""
            <tr>
                <td>{i}</td>
                <td>{pac.get('NumeroSolicitud', 'N/A')}</td>
                <td>{pac.get('NombrePaciente', 'N/A')}</td>
                <td>{pac.get('NumeroDocumento', 'N/A')}</td>
                <td class="text-center">{pac.get('CantidadPruebas', 0)}</td>
                <td>{pac.get('EstadoSolicitud', 'N/A')}</td>
            </tr>
            """

        html += """
            </tbody>
        </table>
        """

        html += self._generar_pie(incluir_firma=False)
        return html

    def R11_etiquetas_muestras(self, solicitud_id):
        """
        R11 - Etiquetas de Muestras
        Genera etiquetas para tubos/contenedores
        """
        sol = self.db.query_one(f"""
            SELECT s.*, p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return ""

        # Obtener tipos de muestra requeridos
        muestras = self.db.query(f"""
            SELECT DISTINCT tm.Codigo, tm.Nombre, tm.Color
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            LEFT JOIN TiposMuestra tm ON pr.TipoMuestraID = tm.TipoMuestraID
            WHERE ps.SolicitudID = {solicitud_id}
        """)

        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                .etiqueta {
                    width: 5cm; height: 2.5cm;
                    border: 1px solid #333;
                    margin: 5px; padding: 5px;
                    display: inline-block;
                    font-family: Arial; font-size: 9pt;
                }
                .codigo { font-family: monospace; font-size: 8pt; }
                .nombre { font-weight: bold; font-size: 10pt; }
            </style>
        </head>
        <body>
        """

        for muestra in muestras:
            html += f"""
            <div class="etiqueta">
                <div class="codigo">{sol.get('NumeroSolicitud', '')}</div>
                <div class="nombre">{sol.get('NombrePaciente', '')[:25]}</div>
                <div>CI: {sol.get('NumeroDocumento', '')}</div>
                <div>{datetime.now().strftime('%d/%m/%Y')}</div>
                <div style="background:{muestra.get('Color', '#fff')}; padding:2px;">
                    {muestra.get('Nombre', 'MUESTRA')}
                </div>
            </div>
            """

        html += "</body></html>"
        return html

    # =========================================================================
    # REPORTES DE RESULTADOS POR AREA (R13 - R43)
    # =========================================================================

    def R13_hematologia_completa(self, solicitud_id):
        """
        R13 - Hematologia Completa
        Incluye: Serie Roja, Serie Blanca, Plaquetas
        """
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Sexo, p.Edad, p.FechaNacimiento,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        # Obtener resultados de hematologia (Area 1)
        resultados = self.db.query(f"""
            SELECT r.*, param.NombreParametro, param.Seccion, param.CodigoParametro,
                   u.Simbolo as Unidad
            FROM Resultados r
            INNER JOIN Parametros param ON r.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON r.UnidadID = u.UnidadID
            INNER JOIN PruebasSolicitadas ps ON r.PruebaSolicitadaID = ps.PruebaSolicitadaID
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            WHERE ps.SolicitudID = {solicitud_id} AND pr.AreaID = 1
            ORDER BY param.Seccion, r.ResultadoID
        """)

        # Organizar por seccion
        secciones = {}
        for r in resultados:
            seccion = r.get('Seccion', 'General')
            if seccion not in secciones:
                secciones[seccion] = []
            secciones[seccion].append(r)

        html = self._generar_encabezado("HEMATOLOGIA COMPLETA")

        # Datos del paciente
        html += f"""
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('NumeroDocumento', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Edad/Sexo:</span>
                <span class="info-value">{sol.get('Edad', 'N/A')} anos / {'Masculino' if sol.get('Sexo') == 'M' else 'Femenino'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Solicitud:</span>
                <span class="info-value">{sol.get('NumeroSolicitud', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Fecha:</span>
                <span class="info-value">{sol.get('FechaSolicitud').strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Medico:</span>
                <span class="info-value">{sol.get('NombreMedico', 'Particular')}</span>
            </div>
        </div>
        """

        # Serie Roja
        if 'Serie Roja' in secciones:
            html += """
            <div class="section-title">SERIE ROJA</div>
            <table>
                <thead>
                    <tr>
                        <th>Parametro</th>
                        <th class="text-center">Resultado</th>
                        <th class="text-center">Unidad</th>
                        <th>Valores de Referencia</th>
                    </tr>
                </thead>
                <tbody>
            """
            for r in secciones['Serie Roja']:
                valor = r.get('ValorNumerico') or r.get('ValorTexto') or '---'
                clase = ''
                if r.get('FueraDeRango'):
                    clase = 'valor-alto' if r.get('TipoAlerta') == 'Alto' else 'valor-bajo'
                html += f"""
                <tr>
                    <td>{r.get('NombreParametro', 'N/A')}</td>
                    <td class="text-center {clase}">{valor}</td>
                    <td class="text-center">{r.get('Unidad', '')}</td>
                    <td>{r.get('ValorReferencia', '')}</td>
                </tr>
                """
            html += "</tbody></table>"

        # Serie Blanca
        if 'Serie Blanca' in secciones:
            html += """
            <div class="section-title">SERIE BLANCA (Formula Leucocitaria)</div>
            <table>
                <thead>
                    <tr>
                        <th>Parametro</th>
                        <th class="text-center">Resultado</th>
                        <th class="text-center">Unidad</th>
                        <th>Valores de Referencia</th>
                    </tr>
                </thead>
                <tbody>
            """
            for r in secciones['Serie Blanca']:
                valor = r.get('ValorNumerico') or r.get('ValorTexto') or '---'
                clase = ''
                if r.get('FueraDeRango'):
                    clase = 'valor-alto' if r.get('TipoAlerta') == 'Alto' else 'valor-bajo'
                html += f"""
                <tr>
                    <td>{r.get('NombreParametro', 'N/A')}</td>
                    <td class="text-center {clase}">{valor}</td>
                    <td class="text-center">{r.get('Unidad', '')}</td>
                    <td>{r.get('ValorReferencia', '')}</td>
                </tr>
                """
            html += "</tbody></table>"

        # Plaquetas
        if 'Plaquetas' in secciones:
            html += """
            <div class="section-title">PLAQUETAS</div>
            <table>
                <thead>
                    <tr>
                        <th>Parametro</th>
                        <th class="text-center">Resultado</th>
                        <th class="text-center">Unidad</th>
                        <th>Valores de Referencia</th>
                    </tr>
                </thead>
                <tbody>
            """
            for r in secciones['Plaquetas']:
                valor = r.get('ValorNumerico') or r.get('ValorTexto') or '---'
                clase = ''
                if r.get('FueraDeRango'):
                    clase = 'valor-alto' if r.get('TipoAlerta') == 'Alto' else 'valor-bajo'
                html += f"""
                <tr>
                    <td>{r.get('NombreParametro', 'N/A')}</td>
                    <td class="text-center {clase}">{valor}</td>
                    <td class="text-center">{r.get('Unidad', '')}</td>
                    <td>{r.get('ValorReferencia', '')}</td>
                </tr>
                """
            html += "</tbody></table>"

        # Observaciones
        html += """
        <div style="margin-top: 20px;">
            <strong>Observaciones:</strong>
            <div style="border: 1px solid #ccc; min-height: 50px; padding: 5px;">
            </div>
        </div>
        """

        html += self._generar_pie(incluir_firma=True)
        return html

    def R18_perfil_lipidico(self, solicitud_id):
        """
        R18 - Perfil Lipidico Completo
        Incluye: Colesterol Total, Trigliceridos, HDL, LDL, VLDL
        """
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Sexo, p.Edad,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        # Obtener resultados de lipidos (seccion Lipidos en Area 2)
        resultados = self.db.query(f"""
            SELECT r.*, param.NombreParametro, param.CodigoParametro,
                   u.Simbolo as Unidad
            FROM Resultados r
            INNER JOIN Parametros param ON r.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON r.UnidadID = u.UnidadID
            INNER JOIN PruebasSolicitadas ps ON r.PruebaSolicitadaID = ps.PruebaSolicitadaID
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            WHERE ps.SolicitudID = {solicitud_id}
            AND pr.AreaID = 2
            AND param.Seccion = 'Lipidos'
            ORDER BY r.ResultadoID
        """)

        html = self._generar_encabezado("PERFIL LIPIDICO")

        # Datos del paciente
        html += f"""
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('NumeroDocumento', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Edad/Sexo:</span>
                <span class="info-value">{sol.get('Edad', 'N/A')} anos / {'Masculino' if sol.get('Sexo') == 'M' else 'Femenino'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Solicitud:</span>
                <span class="info-value">{sol.get('NumeroSolicitud', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Fecha:</span>
                <span class="info-value">{sol.get('FechaSolicitud').strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'}</span>
            </div>
        </div>

        <div class="section-title">PERFIL LIPIDICO</div>
        <table>
            <thead>
                <tr>
                    <th>Parametro</th>
                    <th class="text-center">Resultado</th>
                    <th class="text-center">Unidad</th>
                    <th>Valores Deseables</th>
                    <th>Riesgo</th>
                </tr>
            </thead>
            <tbody>
        """

        # Valores de referencia para lipidos
        ref_lipidos = {
            'COLESTEROL': {'deseable': '<200', 'limite': '200-239', 'alto': '>=240'},
            'TRIGLICERIDOS': {'deseable': '<150', 'limite': '150-199', 'alto': '>=200'},
            'HDL': {'deseable': '>60', 'limite': '40-60', 'bajo': '<40'},
            'LDL': {'deseable': '<100', 'limite': '100-159', 'alto': '>=160'},
            'VLDL': {'deseable': '<30', 'limite': '30-40', 'alto': '>40'}
        }

        for r in resultados:
            valor = r.get('ValorNumerico') or r.get('ValorTexto') or '---'
            nombre = r.get('NombreParametro', 'N/A')
            codigo = r.get('CodigoParametro', '')

            # Determinar riesgo
            riesgo = 'Normal'
            clase = ''
            if codigo in ref_lipidos and r.get('ValorNumerico'):
                val = float(r.get('ValorNumerico', 0))
                if codigo == 'COLESTEROL':
                    if val >= 240:
                        riesgo = 'ALTO'
                        clase = 'valor-alto'
                    elif val >= 200:
                        riesgo = 'Limite'
                elif codigo == 'TRIGLICERIDOS':
                    if val >= 200:
                        riesgo = 'ALTO'
                        clase = 'valor-alto'
                    elif val >= 150:
                        riesgo = 'Limite'
                elif codigo == 'HDL':
                    if val < 40:
                        riesgo = 'BAJO'
                        clase = 'valor-bajo'
                elif codigo == 'LDL':
                    if val >= 160:
                        riesgo = 'ALTO'
                        clase = 'valor-alto'
                    elif val >= 100:
                        riesgo = 'Limite'

            ref = ref_lipidos.get(codigo, {})
            deseable = ref.get('deseable', r.get('ValorReferencia', ''))

            html += f"""
            <tr>
                <td>{nombre}</td>
                <td class="text-center bold {clase}">{valor}</td>
                <td class="text-center">{r.get('Unidad', 'mg/dL')}</td>
                <td>{deseable}</td>
                <td class="{clase}">{riesgo}</td>
            </tr>
            """

        html += """
            </tbody>
        </table>

        <div style="margin-top: 20px; font-size: 10pt;">
            <strong>Interpretacion de Riesgo Cardiovascular:</strong>
            <ul>
                <li>Colesterol Total: Deseable &lt;200, Limite 200-239, Alto &ge;240 mg/dL</li>
                <li>Trigliceridos: Deseable &lt;150, Limite 150-199, Alto &ge;200 mg/dL</li>
                <li>HDL (Colesterol Bueno): Deseable &gt;60, Bajo &lt;40 mg/dL</li>
                <li>LDL (Colesterol Malo): Optimo &lt;100, Elevado &ge;160 mg/dL</li>
            </ul>
        </div>
        """

        html += self._generar_pie(incluir_firma=True)
        return html

    def R19_perfil_renal(self, solicitud_id):
        """
        R19 - Perfil Renal
        Incluye: Urea, Creatinina, Acido Urico, BUN
        """
        return self._generar_reporte_seccion(solicitud_id, "PERFIL RENAL", 2, "Renal")

    def R20_perfil_hepatico(self, solicitud_id):
        """
        R20 - Perfil Hepatico
        Incluye: TGO, TGP, FA, GGT, Bilirrubinas
        """
        return self._generar_reporte_seccion(solicitud_id, "PERFIL HEPATICO", 2, "Hepatico")

    def R26_examen_orina(self, solicitud_id):
        """
        R26 - Examen General de Orina
        """
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Sexo, p.Edad,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        # Obtener resultados de uroanalisis (Area 6)
        resultados = self.db.query(f"""
            SELECT r.*, param.NombreParametro, param.Seccion,
                   u.Simbolo as Unidad
            FROM Resultados r
            INNER JOIN Parametros param ON r.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON r.UnidadID = u.UnidadID
            INNER JOIN PruebasSolicitadas ps ON r.PruebaSolicitadaID = ps.PruebaSolicitadaID
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            WHERE ps.SolicitudID = {solicitud_id} AND pr.AreaID = 6
            ORDER BY param.Seccion, r.ResultadoID
        """)

        # Organizar por seccion
        secciones = {}
        for r in resultados:
            seccion = r.get('Seccion', 'General')
            if seccion not in secciones:
                secciones[seccion] = []
            secciones[seccion].append(r)

        html = self._generar_encabezado("EXAMEN GENERAL DE ORINA")

        # Datos del paciente
        html += f"""
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('NumeroDocumento', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Solicitud:</span>
                <span class="info-value">{sol.get('NumeroSolicitud', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Fecha:</span>
                <span class="info-value">{sol.get('FechaSolicitud').strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'}</span>
            </div>
        </div>
        """

        for seccion_nombre in ['Examen Fisico', 'Examen Quimico', 'Sedimento']:
            if seccion_nombre in secciones:
                html += f"""
                <div class="section-title">{seccion_nombre.upper()}</div>
                <table>
                    <thead>
                        <tr>
                            <th>Parametro</th>
                            <th class="text-center">Resultado</th>
                            <th>Valores de Referencia</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for r in secciones[seccion_nombre]:
                    valor = r.get('ValorTexto') or r.get('ValorNumerico') or '---'
                    html += f"""
                    <tr>
                        <td>{r.get('NombreParametro', 'N/A')}</td>
                        <td class="text-center">{valor}</td>
                        <td>{r.get('ValorReferencia', '')}</td>
                    </tr>
                    """
                html += "</tbody></table>"

        html += self._generar_pie(incluir_firma=True)
        return html

    def R29_coproanalisis(self, solicitud_id):
        """
        R29 - Coproanalisis Completo (Examen de Heces)
        """
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Sexo, p.Edad,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        # Obtener resultados de coprologia (Area 7)
        resultados = self.db.query(f"""
            SELECT r.*, param.NombreParametro, param.Seccion,
                   u.Simbolo as Unidad
            FROM Resultados r
            INNER JOIN Parametros param ON r.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON r.UnidadID = u.UnidadID
            INNER JOIN PruebasSolicitadas ps ON r.PruebaSolicitadaID = ps.PruebaSolicitadaID
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            WHERE ps.SolicitudID = {solicitud_id} AND pr.AreaID = 7
            ORDER BY param.Seccion, r.ResultadoID
        """)

        # Organizar por seccion
        secciones = {}
        for r in resultados:
            seccion = r.get('Seccion', 'General')
            if seccion not in secciones:
                secciones[seccion] = []
            secciones[seccion].append(r)

        html = self._generar_encabezado("EXAMEN DE HECES (COPROANALISIS)")

        # Datos del paciente
        html += f"""
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('NumeroDocumento', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Solicitud:</span>
                <span class="info-value">{sol.get('NumeroSolicitud', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Fecha:</span>
                <span class="info-value">{sol.get('FechaSolicitud').strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'}</span>
            </div>
        </div>
        """

        for seccion_nombre in ['Examen Macroscopico', 'Examen Quimico', 'Examen Microscopico', 'Parasitologia']:
            if seccion_nombre in secciones:
                html += f"""
                <div class="section-title">{seccion_nombre.upper()}</div>
                <table>
                    <thead>
                        <tr>
                            <th>Parametro</th>
                            <th class="text-center">Resultado</th>
                            <th>Valores de Referencia</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for r in secciones[seccion_nombre]:
                    valor = r.get('ValorTexto') or r.get('ValorNumerico') or '---'
                    html += f"""
                    <tr>
                        <td>{r.get('NombreParametro', 'N/A')}</td>
                        <td class="text-center">{valor}</td>
                        <td>{r.get('ValorReferencia', '')}</td>
                    </tr>
                    """
                html += "</tbody></table>"

        html += self._generar_pie(incluir_firma=True)
        return html

    # =========================================================================
    # REPORTES DE SEROLOGIA / ANTIGENOS FEBRILES (R31 - R35)
    # =========================================================================

    def R31_antigenos_febriles(self, solicitud_id):
        """
        R31 - Antigenos Febriles (Reacciones Febriles)
        Incluye: Aglutinaciones para Salmonella Typhi (O y H),
                 Salmonella Paratyphi A/B, Brucella abortus/melitensis,
                 Proteus OX-19 (Weil-Felix)
        Metodo: Aglutinacion en placa / tubo
        """
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Sexo, p.Edad, p.FechaNacimiento,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        # Obtener resultados de serologia (Area 9)
        resultados = self.db.query(f"""
            SELECT rp.*, param.NombreParametro, param.Seccion, param.CodigoParametro,
                   param.Observaciones as ValorReferencia,
                   u.Simbolo as Unidad,
                   pr.NombrePrueba
            FROM ResultadosParametros rp
            INNER JOIN Parametros param ON rp.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON param.UnidadID = u.UnidadID
            INNER JOIN DetalleSolicitudes ds ON rp.DetalleID = ds.DetalleID
            INNER JOIN Pruebas pr ON ds.PruebaID = pr.PruebaID
            WHERE ds.SolicitudID = {solicitud_id} AND pr.AreaID = 9
            ORDER BY param.Seccion, rp.ResultadoParamID
        """)

        # Organizar por seccion
        secciones = {}
        for r in resultados:
            seccion = r.get('Seccion') or 'General'
            if seccion not in secciones:
                secciones[seccion] = []
            secciones[seccion].append(r)

        # CSS especifico para antigenos febriles
        css_febriles = """
        <style>
            .febriles-titulo {
                background-color: #1b5e20; color: white; padding: 8px 12px;
                font-size: 13pt; font-weight: bold; margin: 20px 0 5px 0;
                border-radius: 3px;
            }
            .febriles-seccion {
                background-color: #2e7d32; color: white; padding: 5px 10px;
                font-size: 11pt; margin: 10px 0 5px 0;
            }
            .febriles-table { width: 100%; border-collapse: collapse; margin: 8px 0; }
            .febriles-table th {
                background-color: #1b5e20; color: white; padding: 6px 10px;
                text-align: left; font-size: 10pt;
            }
            .febriles-table td {
                padding: 5px 10px; border: 1px solid #ccc; font-size: 10pt;
            }
            .febriles-table tr:nth-child(even) { background-color: #f1f8e9; }
            .positivo { color: #c62828; font-weight: bold; }
            .sospechoso { color: #e65100; font-weight: bold; }
            .negativo { color: #2e7d32; }
            .metodo-box {
                background-color: #e8f5e9; border: 1px solid #a5d6a7;
                padding: 8px 12px; margin: 10px 0; border-radius: 4px;
                font-size: 10pt;
            }
            .interpretacion-box {
                background-color: #fff3e0; border: 1px solid #ffcc80;
                padding: 10px 14px; margin: 15px 0; border-radius: 4px;
                font-size: 10pt;
            }
            .interpretacion-box h4 { margin: 0 0 8px 0; color: #e65100; }
            .interpretacion-box ul { margin: 5px 0; padding-left: 20px; }
            .interpretacion-box li { margin: 3px 0; }
        </style>
        """

        html = self._generar_encabezado("ANTIGENOS FEBRILES (REACCIONES FEBRILES)")
        html += css_febriles

        # Datos del paciente
        html += f"""
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('NumeroDocumento', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Edad:</span>
                <span class="info-value">{sol.get('Edad', 'N/A')}</span>
                <span class="info-label" style="margin-left:20px;">Sexo:</span>
                <span class="info-value">{'Masculino' if sol.get('Sexo') == 'M' else 'Femenino'}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Medico:</span>
                <span class="info-value">{sol.get('NombreMedico', 'Particular')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Solicitud:</span>
                <span class="info-value">{sol.get('NumeroSolicitud', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Fecha:</span>
                <span class="info-value">{sol.get('FechaSolicitud').strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'}</span>
            </div>
        </div>

        <div class="metodo-box">
            <strong>Metodo:</strong> Aglutinacion en placa y/o tubo (diluciones seriadas)
        </div>
        """

        # Orden preferente de secciones para antigenos febriles
        orden_secciones = [
            'Antigenos Febriles',
            'Salmonella Typhi', 'Tificas O', 'Tificas H',
            'Salmonella Paratyphi', 'Paratificas A', 'Paratificas B',
            'Brucella', 'Brucella abortus', 'Brucella melitensis',
            'Proteus OX-19', 'Proteus', 'Weil-Felix',
            'Infecciosas', 'Inflamatorios', 'Autoinmunes',
            'General'
        ]

        secciones_ordenadas = []
        for s in orden_secciones:
            if s in secciones:
                secciones_ordenadas.append(s)
        for s in secciones:
            if s not in secciones_ordenadas:
                secciones_ordenadas.append(s)

        for seccion_nombre in secciones_ordenadas:
            params = secciones[seccion_nombre]
            html += f'<div class="febriles-seccion">{seccion_nombre.upper()}</div>'

            html += """
            <table class="febriles-table">
                <thead>
                    <tr>
                        <th style="width:35%;">Determinacion</th>
                        <th style="width:20%; text-align:center;">Resultado</th>
                        <th style="width:20%; text-align:center;">Unidad</th>
                        <th style="width:25%;">Valor de Referencia</th>
                    </tr>
                </thead>
                <tbody>
            """

            for r in params:
                valor = r.get('Valor') or '---'
                nombre_param = r.get('NombreParametro', 'N/A')
                unidad = r.get('Unidad') or ''
                referencia = r.get('ValorReferencia') or ''

                # Determinar clase CSS segun titulacion
                clase = 'negativo'
                valor_str = str(valor).strip().upper()
                try:
                    if valor_str.startswith('1:') or valor_str.startswith('1/'):
                        partes = valor_str.replace('/', ':').split(':')
                        if len(partes) == 2:
                            titulo = int(partes[1])
                            if titulo >= 160:
                                clase = 'positivo'
                            elif titulo >= 80:
                                clase = 'sospechoso'
                    elif valor_str in ['POSITIVO', 'REACTIVO', 'POS', '+']:
                        clase = 'positivo'
                    elif valor_str in ['NEGATIVO', 'NO REACTIVO', 'NEG', '-']:
                        clase = 'negativo'
                except (ValueError, TypeError):
                    pass

                html += f"""
                <tr>
                    <td>{nombre_param}</td>
                    <td class="text-center {clase}">{valor}</td>
                    <td class="text-center">{unidad}</td>
                    <td>{referencia}</td>
                </tr>
                """

            html += "</tbody></table>"

        # Interpretacion clinica
        html += """
        <div class="interpretacion-box">
            <h4>INTERPRETACION DE RESULTADOS</h4>
            <ul>
                <li><strong>Reacciones de Widal (Salmonella):</strong>
                    Titulaciones &ge; 1:160 son sugestivas de infeccion activa.
                    Titulaciones de 1:80 son sospechosas y requieren segunda muestra.</li>
                <li><strong>Brucella:</strong>
                    Titulaciones &ge; 1:160 son sugestivas de brucelosis.
                    En zonas endemicas, titulaciones &ge; 1:320 son mas significativas.</li>
                <li><strong>Proteus OX-19 (Weil-Felix):</strong>
                    Titulaciones &ge; 1:160 sugieren infeccion por Rickettsia.</li>
                <li><strong>Importante:</strong> Se recomienda obtener una segunda muestra
                    a los 7-14 dias para demostrar seroconversion (aumento de 4 veces
                    el titulo inicial). Correlacionar siempre con el cuadro clinico.</li>
            </ul>
        </div>
        """

        html += self._generar_pie(incluir_firma=True)
        return html

    def R32_serologia_general(self, solicitud_id):
        """
        R32 - Serologia General
        Wrapper para resultados generales de serologia (area 9)
        """
        return self.R31_antigenos_febriles(solicitud_id)

    # =========================================================================
    # REPORTES DE MICROBIOLOGIA / BACTERIOLOGIA (R40 - R43)
    # =========================================================================

    def R40_microbiologia_cultivo(self, solicitud_id):
        """
        R40 - Reporte de Microbiologia / Bacteriologia
        Incluye: Urocultivo, Hemocultivo, Coprocultivo, Cultivo de Secrecion,
                 Identificacion de germen, Recuento de colonias, Antibiograma (S/I/R)
        """
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Sexo, p.Edad,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        # Obtener resultados de microbiologia (Area 10)
        resultados = self.db.query(f"""
            SELECT rp.*, param.NombreParametro, param.Seccion, param.TipoResultado,
                   param.Observaciones as ValorReferencia,
                   u.Simbolo as Unidad,
                   pr.NombrePrueba
            FROM ResultadosParametros rp
            INNER JOIN Parametros param ON rp.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON param.UnidadID = u.UnidadID
            INNER JOIN DetalleSolicitudes ds ON rp.DetalleID = ds.DetalleID
            INNER JOIN Pruebas pr ON ds.PruebaID = pr.PruebaID
            WHERE ds.SolicitudID = {solicitud_id} AND pr.AreaID = 10
            ORDER BY pr.NombrePrueba, param.Seccion, rp.ResultadoParamID
        """)

        # Organizar por prueba y seccion
        pruebas_dict = {}
        for r in resultados:
            prueba_nombre = r.get('NombrePrueba', 'Sin Nombre')
            if prueba_nombre not in pruebas_dict:
                pruebas_dict[prueba_nombre] = {}
            seccion = r.get('Seccion') or 'General'
            if seccion not in pruebas_dict[prueba_nombre]:
                pruebas_dict[prueba_nombre][seccion] = []
            pruebas_dict[prueba_nombre][seccion].append(r)

        # CSS especifico para microbiologia
        css_micro = """
        <style>
            .micro-titulo-prueba {
                background-color: #1a237e; color: white; padding: 8px 12px;
                font-size: 13pt; font-weight: bold; margin: 20px 0 5px 0;
                border-radius: 3px;
            }
            .micro-seccion {
                background-color: #455a64; color: white; padding: 5px 10px;
                font-size: 11pt; margin: 10px 0 5px 0;
            }
            .antibiograma-table { width: 100%; border-collapse: collapse; margin: 8px 0; }
            .antibiograma-table th {
                background-color: #263238; color: white; padding: 6px 10px;
                text-align: left; font-size: 10pt;
            }
            .antibiograma-table td {
                padding: 5px 10px; border: 1px solid #ccc; font-size: 10pt;
            }
            .antibiograma-table tr:nth-child(even) { background-color: #f5f5f5; }
            .sensible { color: #2e7d32; font-weight: bold; }
            .intermedio { color: #f57f17; font-weight: bold; }
            .resistente { color: #c62828; font-weight: bold; }
            .resultado-cultivo {
                padding: 8px 12px; margin: 5px 0;
                border-left: 4px solid #1a237e; background-color: #f5f5f5;
            }
            .germen-identificado {
                font-size: 12pt; font-weight: bold; color: #b71c1c;
                padding: 5px 0;
            }
            .dato-muestra {
                display: inline-block; margin-right: 20px;
                padding: 3px 8px; background-color: #e8eaf6; border-radius: 3px;
            }
        </style>
        """

        html = self._generar_encabezado("MICROBIOLOGIA / BACTERIOLOGIA")
        html += css_micro

        # Datos del paciente
        html += f"""
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('NumeroDocumento', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Edad:</span>
                <span class="info-value">{sol.get('Edad', 'N/A')}</span>
                <span class="info-label" style="margin-left:20px;">Sexo:</span>
                <span class="info-value">{sol.get('Sexo', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Medico:</span>
                <span class="info-value">{sol.get('NombreMedico', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Solicitud:</span>
                <span class="info-value">{sol.get('NumeroSolicitud', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Fecha:</span>
                <span class="info-value">{sol.get('FechaSolicitud').strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'}</span>
            </div>
        </div>
        """

        # Renderizar cada prueba de microbiologia
        for prueba_nombre, secciones in pruebas_dict.items():
            html += f'<div class="micro-titulo-prueba">{prueba_nombre.upper()}</div>'

            # Orden preferente de secciones (incluye todas las variantes)
            orden_secciones = [
                'Tipo de Muestra', 'Datos de Muestra', 'Muestra',
                'Coloracion de Gram', 'Gram', 'Tincion de Gram',
                'Coloracion Acido-Resistente', 'Ziehl-Neelsen',
                'Examen Directo',
                'Cultivo', 'Resultado del Cultivo', 'Resultado',
                'Identificacion', 'Identificacion del Germen', 'Germen Aislado',
                'Recuento', 'Recuento de Colonias',
                'Antibiograma', 'Sensibilidad Antibiotica',
                'Observaciones', 'General'
            ]

            secciones_ordenadas = []
            for s in orden_secciones:
                if s in secciones:
                    secciones_ordenadas.append(s)
            # Agregar secciones restantes que no esten en el orden preferente
            for s in secciones:
                if s not in secciones_ordenadas:
                    secciones_ordenadas.append(s)

            for seccion_nombre in secciones_ordenadas:
                params = secciones[seccion_nombre]
                seccion_upper = seccion_nombre.upper()

                # Detectar si es seccion de antibiograma
                es_antibiograma = any(x in seccion_upper for x in [
                    'ANTIBIOGRAMA', 'SENSIBILIDAD', 'ANTIBIOTICO', 'SUSCEPTIBILIDAD'
                ])

                html += f'<div class="micro-seccion">{seccion_upper}</div>'

                if es_antibiograma:
                    # Renderizar como tabla de antibiograma con columnas S/I/R
                    html += """
                    <table class="antibiograma-table">
                        <thead>
                            <tr>
                                <th style="width:50%;">Antibiotico</th>
                                <th style="width:25%; text-align:center;">Resultado</th>
                                <th style="width:25%; text-align:center;">Interpretacion</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    for r in params:
                        valor = r.get('Valor') or '---'
                        valor_upper = valor.upper().strip()

                        # Determinar clase CSS segun sensibilidad
                        if valor_upper in ['S', 'SENSIBLE']:
                            clase = 'sensible'
                            interpretacion = 'Sensible'
                        elif valor_upper in ['I', 'INTERMEDIO', 'SDD']:
                            clase = 'intermedio'
                            interpretacion = 'Intermedio'
                        elif valor_upper in ['R', 'RESISTENTE']:
                            clase = 'resistente'
                            interpretacion = 'Resistente'
                        else:
                            clase = ''
                            interpretacion = valor

                        html += f"""
                        <tr>
                            <td>{r.get('NombreParametro', 'N/A')}</td>
                            <td class="text-center {clase}">{valor}</td>
                            <td class="text-center {clase}">{interpretacion}</td>
                        </tr>
                        """
                    html += "</tbody></table>"
                else:
                    # Renderizar como lista de resultados normales
                    html += '<table><thead><tr>'
                    html += '<th style="width:40%;">Parametro</th>'
                    html += '<th style="width:30%; text-align:center;">Resultado</th>'
                    html += '<th style="width:30%;">Valor de Referencia</th>'
                    html += '</tr></thead><tbody>'

                    for r in params:
                        valor = r.get('Valor') or '---'
                        nombre_param = r.get('NombreParametro', 'N/A')
                        referencia = r.get('ValorReferencia') or ''

                        # Resaltar germen identificado
                        nombre_upper = nombre_param.upper()
                        es_germen = any(x in nombre_upper for x in [
                            'GERMEN', 'MICROORGANISMO', 'AGENTE', 'BACTERIA',
                            'ORGANISMO AISLADO', 'IDENTIFICACION'
                        ])

                        if es_germen and valor != '---':
                            html += f"""
                            <tr>
                                <td><strong>{nombre_param}</strong></td>
                                <td class="text-center germen-identificado">{valor}</td>
                                <td>{referencia}</td>
                            </tr>
                            """
                        else:
                            html += f"""
                            <tr>
                                <td>{nombre_param}</td>
                                <td class="text-center">{valor}</td>
                                <td>{referencia}</td>
                            </tr>
                            """
                    html += "</tbody></table>"

        html += self._generar_pie(incluir_firma=True)
        return html

    def R41_urocultivo(self, solicitud_id):
        """
        R41 - Urocultivo
        Wrapper que usa R40 filtrado para urocultivo
        """
        return self.R40_microbiologia_cultivo(solicitud_id)

    def R42_hemocultivo(self, solicitud_id):
        """
        R42 - Hemocultivo
        Wrapper que usa R40 filtrado para hemocultivo
        """
        return self.R40_microbiologia_cultivo(solicitud_id)

    def R43_coprocultivo(self, solicitud_id):
        """
        R43 - Coprocultivo
        Wrapper que usa R40 filtrado para coprocultivo
        """
        return self.R40_microbiologia_cultivo(solicitud_id)

    def R44B_cultivo_secrecion(self, solicitud_id):
        """R44B - Cultivo de Secrecion (general, faringea, vaginal, otica, uretral, nasal)"""
        return self.R40_microbiologia_cultivo(solicitud_id)

    def R45B_cultivo_herida(self, solicitud_id):
        """R45B - Cultivo de Secrecion de Herida"""
        return self.R40_microbiologia_cultivo(solicitud_id)

    def R46B_baciloscopia(self, solicitud_id):
        """R46B - Baciloscopia (BK/BAAR) - Coloracion Ziehl-Neelsen"""
        return self.R40_microbiologia_cultivo(solicitud_id)

    def R47B_cultivo_micologico(self, solicitud_id):
        """R47B - Cultivo Micologico (Hongos)"""
        return self.R40_microbiologia_cultivo(solicitud_id)

    def R48B_cultivo_conjuntival(self, solicitud_id):
        """R48B - Cultivo de Secrecion Conjuntival/Ocular"""
        return self.R40_microbiologia_cultivo(solicitud_id)

    def _generar_reporte_seccion(self, solicitud_id, titulo, area_id, seccion):
        """Genera reporte generico para una seccion de area"""
        sol = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Sexo, p.Edad,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not sol:
            return "<html><body>Solicitud no encontrada</body></html>"

        resultados = self.db.query(f"""
            SELECT r.*, param.NombreParametro, u.Simbolo as Unidad
            FROM Resultados r
            INNER JOIN Parametros param ON r.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON r.UnidadID = u.UnidadID
            INNER JOIN PruebasSolicitadas ps ON r.PruebaSolicitadaID = ps.PruebaSolicitadaID
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            WHERE ps.SolicitudID = {solicitud_id}
            AND pr.AreaID = {area_id}
            AND param.Seccion = '{seccion}'
            ORDER BY r.ResultadoID
        """)

        html = self._generar_encabezado(titulo)

        html += f"""
        <div class="info-box">
            <div class="info-row">
                <span class="info-label">Paciente:</span>
                <span class="info-value">{sol.get('NombrePaciente', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Cedula:</span>
                <span class="info-value">{sol.get('NumeroDocumento', 'N/A')}</span>
            </div>
            <div class="info-row">
                <span class="info-label">Solicitud:</span>
                <span class="info-value">{sol.get('NumeroSolicitud', 'N/A')}</span>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>Parametro</th>
                    <th class="text-center">Resultado</th>
                    <th class="text-center">Unidad</th>
                    <th>Valores de Referencia</th>
                </tr>
            </thead>
            <tbody>
        """

        for r in resultados:
            valor = r.get('ValorNumerico') or r.get('ValorTexto') or '---'
            clase = ''
            if r.get('FueraDeRango'):
                clase = 'valor-alto' if r.get('TipoAlerta') == 'Alto' else 'valor-bajo'
            html += f"""
            <tr>
                <td>{r.get('NombreParametro', 'N/A')}</td>
                <td class="text-center {clase}">{valor}</td>
                <td class="text-center">{r.get('Unidad', '')}</td>
                <td>{r.get('ValorReferencia', '')}</td>
            </tr>
            """

        html += "</tbody></table>"
        html += self._generar_pie(incluir_firma=True)
        return html

    # =========================================================================
    # REPORTES DE FACTURACION (R44 - R54)
    # =========================================================================

    def R44_factura_fiscal(self, factura_id):
        """
        R44 - Factura Fiscal
        Conforme a normativas fiscales venezolanas
        """
        factura = self.db.query_one(f"""
            SELECT f.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Direccion as DireccionPaciente,
                   p.Telefono as TelefonoPaciente
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE f.FacturaID = {factura_id}
        """)

        if not factura:
            return "<html><body>Factura no encontrada</body></html>"

        detalles = self.db.query(f"""
            SELECT df.*, pr.NombrePrueba
            FROM DetalleFacturas df
            LEFT JOIN Pruebas pr ON df.PruebaID = pr.PruebaID
            WHERE df.FacturaID = {factura_id}
        """)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; font-size: 10pt; }}
                .factura {{ border: 2px solid #333; padding: 15px; }}
                .header {{ display: flex; justify-content: space-between; border-bottom: 2px solid #333; padding-bottom: 10px; }}
                .numero-factura {{ font-size: 16pt; font-weight: bold; color: #333; }}
                .control {{ font-size: 12pt; color: #666; }}
                table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                th, td {{ border: 1px solid #333; padding: 5px; }}
                th {{ background: #f0f0f0; }}
                .totales {{ width: 300px; float: right; }}
                .totales td {{ text-align: right; }}
                .legal {{ font-size: 8pt; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <div class="factura">
                <div class="header">
                    <div>
                        <h2>{self.lab_nombre}</h2>
                        <p>RIF: {self.lab_rif}</p>
                        <p>{self.lab_direccion}</p>
                        <p>Tel: {self.lab_telefono}</p>
                    </div>
                    <div style="text-align: right;">
                        <div class="numero-factura">FACTURA</div>
                        <div class="numero-factura">No. {factura.get('NumeroFactura', 'N/A')}</div>
                        <div class="control">Control: {factura.get('NumeroControl', 'N/A')}</div>
                        <div>Fecha: {factura.get('FechaEmision').strftime('%d/%m/%Y') if factura.get('FechaEmision') else 'N/A'}</div>
                    </div>
                </div>

                <div style="margin: 15px 0; border: 1px solid #ccc; padding: 10px;">
                    <p><strong>Cliente:</strong> {factura.get('NombrePaciente', 'N/A')}</p>
                    <p><strong>Cedula/RIF:</strong> {factura.get('NumeroDocumento', 'N/A')}</p>
                    <p><strong>Direccion:</strong> {factura.get('DireccionPaciente', 'N/A')}</p>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Cantidad</th>
                            <th>Descripcion</th>
                            <th>Precio Unit.</th>
                            <th>Total</th>
                        </tr>
                    </thead>
                    <tbody>
        """

        for d in detalles:
            cantidad = d.get('Cantidad', 1)
            precio = d.get('PrecioUnitario', 0) or 0
            total = cantidad * precio
            html += f"""
                <tr>
                    <td style="text-align:center;">{cantidad}</td>
                    <td>{d.get('Descripcion', '') or d.get('NombrePrueba', 'Servicio')}</td>
                    <td style="text-align:right;">{precio:,.2f}</td>
                    <td style="text-align:right;">{total:,.2f}</td>
                </tr>
            """

        subtotal = factura.get('SubTotal', 0) or 0
        iva = factura.get('MontoIVA', 0) or 0
        total = factura.get('MontoTotal', 0) or 0

        html += f"""
                    </tbody>
                </table>

                <table class="totales">
                    <tr>
                        <td><strong>Sub-Total:</strong></td>
                        <td>{subtotal:,.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>IVA (16%):</strong></td>
                        <td>{iva:,.2f}</td>
                    </tr>
                    <tr>
                        <td><strong>TOTAL:</strong></td>
                        <td style="font-size:14pt;"><strong>{total:,.2f}</strong></td>
                    </tr>
                </table>

                <div style="clear:both;"></div>

                <div class="legal">
                    <p>Contribuyente Ordinario - Retencion de IVA 75%</p>
                    <p>Esta factura solo es valida si contiene el sello y firma del emisor</p>
                </div>

                <div style="margin-top: 30px; display: flex; justify-content: space-between;">
                    <div style="text-align:center;">
                        <div style="border-top: 1px solid #333; width: 150px;"></div>
                        <p>Emitido por</p>
                    </div>
                    <div style="text-align:center;">
                        <div style="border-top: 1px solid #333; width: 150px;"></div>
                        <p>Recibido por</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def R45_recibo_caja(self, pago_id):
        """
        R45 - Recibo de Caja
        """
        pago = self.db.query_one(f"""
            SELECT pg.*, f.NumeroFactura,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento
            FROM Pagos pg
            INNER JOIN Facturas f ON pg.FacturaID = f.FacturaID
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE pg.PagoID = {pago_id}
        """)

        if not pago:
            return "<html><body>Pago no encontrado</body></html>"

        # Convertir monto a letras (simplificado)
        def numero_a_letras(n):
            unidades = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
            decenas = ['', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
            if n < 10:
                return unidades[int(n)]
            elif n < 100:
                return decenas[int(n//10)] + (' y ' + unidades[int(n%10)] if n%10 != 0 else '')
            else:
                return str(n)

        monto = pago.get('Monto', 0) or 0
        monto_letras = numero_a_letras(int(monto))

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; font-size: 11pt; width: 15cm; }}
                .recibo {{ border: 2px solid #333; padding: 15px; }}
                .header {{ text-align: center; border-bottom: 1px solid #333; padding-bottom: 10px; }}
                .numero {{ font-size: 18pt; font-weight: bold; }}
                .monto-box {{ border: 2px solid #333; padding: 10px; font-size: 18pt; text-align: center; margin: 15px 0; }}
            </style>
        </head>
        <body>
            <div class="recibo">
                <div class="header">
                    <h2>{self.lab_nombre}</h2>
                    <p>RIF: {self.lab_rif}</p>
                    <div class="numero">RECIBO DE CAJA</div>
                    <div class="numero">No. {pago.get('NumeroRecibo', pago_id)}</div>
                </div>

                <p>Fecha: {pago.get('FechaPago').strftime('%d/%m/%Y') if pago.get('FechaPago') else datetime.now().strftime('%d/%m/%Y')}</p>

                <p><strong>Recibimos de:</strong> {pago.get('NombrePaciente', 'N/A')}</p>
                <p><strong>Cedula:</strong> {pago.get('NumeroDocumento', 'N/A')}</p>

                <div class="monto-box">
                    <strong>{monto:,.2f}</strong>
                </div>

                <p><strong>La cantidad de:</strong> {monto_letras.upper()} BOLIVARES</p>

                <p><strong>Por concepto de:</strong> Pago de servicios de laboratorio</p>
                <p><strong>Factura No:</strong> {pago.get('NumeroFactura', 'N/A')}</p>
                <p><strong>Forma de pago:</strong> {pago.get('FormaPago', 'Efectivo')}</p>

                <div style="margin-top: 40px; text-align: center;">
                    <div style="border-top: 1px solid #333; width: 200px; margin: 0 auto;"></div>
                    <p>Cajero</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    def R48_libro_ventas(self, mes, anio):
        """
        R48 - Libro de Ventas
        Para declaracion fiscal mensual
        """
        fecha_inicio = f"{anio}-{mes:02d}-01"
        fecha_fin = f"{anio}-{mes:02d}-31"

        facturas = self.db.query(f"""
            SELECT f.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE f.FechaEmision >= #{fecha_inicio}#
            AND f.FechaEmision <= #{fecha_fin}#
            AND f.Anulada = False
            ORDER BY f.FechaEmision, f.NumeroFactura
        """)

        html = self._generar_encabezado(f"LIBRO DE VENTAS - {mes:02d}/{anio}")

        html += f"""
        <p>Periodo: {mes:02d}/{anio}</p>
        <p>RIF: {self.lab_rif}</p>

        <table style="font-size: 9pt;">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>No. Factura</th>
                    <th>Control</th>
                    <th>RIF/CI Cliente</th>
                    <th>Cliente</th>
                    <th>Base Imp.</th>
                    <th>IVA</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
        """

        total_base = 0
        total_iva = 0
        total_general = 0

        for f in facturas:
            base = f.get('SubTotal', 0) or 0
            iva = f.get('MontoIVA', 0) or 0
            total = f.get('MontoTotal', 0) or 0

            total_base += base
            total_iva += iva
            total_general += total

            html += f"""
            <tr>
                <td>{f.get('FechaEmision').strftime('%d/%m/%Y') if f.get('FechaEmision') else ''}</td>
                <td>{f.get('NumeroFactura', '')}</td>
                <td>{f.get('NumeroControl', '')}</td>
                <td>{f.get('NumeroDocumento', '')}</td>
                <td>{f.get('NombrePaciente', '')[:25]}</td>
                <td class="text-right">{base:,.2f}</td>
                <td class="text-right">{iva:,.2f}</td>
                <td class="text-right">{total:,.2f}</td>
            </tr>
            """

        html += f"""
            </tbody>
            <tfoot>
                <tr style="font-weight: bold; background: #f0f0f0;">
                    <td colspan="5">TOTALES</td>
                    <td class="text-right">{total_base:,.2f}</td>
                    <td class="text-right">{total_iva:,.2f}</td>
                    <td class="text-right">{total_general:,.2f}</td>
                </tr>
            </tfoot>
        </table>

        <div style="margin-top: 30px;">
            <p>Total de facturas: {len(facturas)}</p>
        </div>
        """

        html += self._generar_pie(incluir_firma=False)
        return html

    # =========================================================================
    # REPORTES GERENCIALES (R55 - R62)
    # =========================================================================

    def R55_dashboard_ejecutivo(self, fecha_desde, fecha_hasta):
        """
        R55 - Dashboard Ejecutivo
        Resumen de indicadores principales
        """
        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        # Solicitudes
        solicitudes = self.db.query_one(f"""
            SELECT
                COUNT(*) as Total,
                SUM(IIF(EstadoSolicitud='Entregada', 1, 0)) as Entregadas,
                SUM(IIF(EstadoSolicitud='EnProceso', 1, 0)) as EnProceso,
                SUM(IIF(EstadoSolicitud='Registrada', 1, 0)) as Pendientes
            FROM Solicitudes
            WHERE FechaSolicitud >= #{f_desde}# AND FechaSolicitud <= #{f_hasta}#
        """)

        # Ingresos
        ingresos = self.db.query_one(f"""
            SELECT
                SUM(MontoTotal) as TotalFacturado,
                SUM(MontoCobrado) as TotalCobrado,
                SUM(MontoPendiente) as TotalPendiente
            FROM Facturas
            WHERE FechaEmision >= #{f_desde}# AND FechaEmision <= #{f_hasta}#
            AND Anulada = False
        """)

        # Pruebas por area
        por_area = self.db.query(f"""
            SELECT a.NombreArea, COUNT(ps.PruebaSolicitadaID) as Cantidad
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            INNER JOIN Solicitudes s ON ps.SolicitudID = s.SolicitudID
            WHERE s.FechaSolicitud >= #{f_desde}# AND s.FechaSolicitud <= #{f_hasta}#
            GROUP BY a.AreaID, a.NombreArea
            ORDER BY COUNT(ps.PruebaSolicitadaID) DESC
        """)

        html = self._generar_encabezado("DASHBOARD EJECUTIVO")

        sol_total = solicitudes.get('Total', 0) if solicitudes else 0
        sol_entregadas = solicitudes.get('Entregadas', 0) if solicitudes else 0
        sol_proceso = solicitudes.get('EnProceso', 0) if solicitudes else 0
        sol_pendientes = solicitudes.get('Pendientes', 0) if solicitudes else 0

        ing_facturado = ingresos.get('TotalFacturado', 0) if ingresos and ingresos.get('TotalFacturado') else 0
        ing_cobrado = ingresos.get('TotalCobrado', 0) if ingresos and ingresos.get('TotalCobrado') else 0
        ing_pendiente = ingresos.get('TotalPendiente', 0) if ingresos and ingresos.get('TotalPendiente') else 0

        html += f"""
        <p>Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}</p>

        <div style="display: flex; gap: 20px; margin: 20px 0;">
            <div class="info-box" style="flex: 1; text-align: center;">
                <h3>SOLICITUDES</h3>
                <p style="font-size: 24pt; font-weight: bold;">{sol_total}</p>
                <p>Entregadas: {sol_entregadas}</p>
                <p>En Proceso: {sol_proceso}</p>
                <p>Pendientes: {sol_pendientes}</p>
            </div>

            <div class="info-box" style="flex: 1; text-align: center;">
                <h3>INGRESOS</h3>
                <p style="font-size: 24pt; font-weight: bold;">{ing_facturado:,.2f}</p>
                <p>Cobrado: {ing_cobrado:,.2f}</p>
                <p>Pendiente: {ing_pendiente:,.2f}</p>
            </div>
        </div>

        <h3>Pruebas por Area</h3>
        <table>
            <thead>
                <tr>
                    <th>Area</th>
                    <th class="text-right">Cantidad</th>
                    <th>Porcentaje</th>
                </tr>
            </thead>
            <tbody>
        """

        total_pruebas = sum(a.get('Cantidad', 0) for a in por_area)
        for area in por_area:
            cant = area.get('Cantidad', 0)
            pct = (cant / total_pruebas * 100) if total_pruebas > 0 else 0
            html += f"""
            <tr>
                <td>{area.get('NombreArea', 'N/A')}</td>
                <td class="text-right">{cant}</td>
                <td>
                    <div style="background: #ddd; height: 20px; width: 100%;">
                        <div style="background: #4CAF50; height: 20px; width: {pct}%;"></div>
                    </div>
                    {pct:.1f}%
                </td>
            </tr>
            """

        html += "</tbody></table>"
        html += self._generar_pie(incluir_firma=False)
        return html

    def R58_pruebas_mas_solicitadas(self, fecha_desde, fecha_hasta, top=20):
        """
        R58 - Pruebas mas Solicitadas
        """
        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        pruebas = self.db.query(f"""
            SELECT TOP {top} pr.CodigoPrueba, pr.NombrePrueba, a.NombreArea,
                   COUNT(ps.PruebaSolicitadaID) as Cantidad,
                   SUM(pr.PrecioBase) as Ingresos
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            INNER JOIN Solicitudes s ON ps.SolicitudID = s.SolicitudID
            WHERE s.FechaSolicitud >= #{f_desde}# AND s.FechaSolicitud <= #{f_hasta}#
            GROUP BY pr.PruebaID, pr.CodigoPrueba, pr.NombrePrueba, a.NombreArea
            ORDER BY COUNT(ps.PruebaSolicitadaID) DESC
        """)

        html = self._generar_encabezado("PRUEBAS MAS SOLICITADAS")

        html += f"""
        <p>Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}</p>
        <p>Top {top} pruebas</p>

        <table>
            <thead>
                <tr>
                    <th>No.</th>
                    <th>Codigo</th>
                    <th>Prueba</th>
                    <th>Area</th>
                    <th class="text-right">Cantidad</th>
                    <th class="text-right">Ingresos</th>
                </tr>
            </thead>
            <tbody>
        """

        for i, p in enumerate(pruebas, 1):
            html += f"""
            <tr>
                <td>{i}</td>
                <td>{p.get('CodigoPrueba', '')}</td>
                <td>{p.get('NombrePrueba', 'N/A')}</td>
                <td>{p.get('NombreArea', 'N/A')}</td>
                <td class="text-right">{p.get('Cantidad', 0)}</td>
                <td class="text-right">{p.get('Ingresos', 0) or 0:,.2f}</td>
            </tr>
            """

        html += "</tbody></table>"
        html += self._generar_pie(incluir_firma=False)
        return html


# ============================================================================
# DICCIONARIO DE REPORTES DISPONIBLES
# ============================================================================

CATALOGO_REPORTES = {
    # Recepcion
    'R01': {'nombre': 'Comprobante de Solicitud', 'metodo': 'R01_comprobante_solicitud', 'categoria': 'Recepcion'},
    'R02': {'nombre': 'Boleta Principal', 'metodo': 'R02_boleta_principal', 'categoria': 'Recepcion'},
    'R03': {'nombre': 'Lista de Pacientes del Dia', 'metodo': 'R03_lista_pacientes_dia', 'categoria': 'Recepcion'},
    'R11': {'nombre': 'Etiquetas de Muestras', 'metodo': 'R11_etiquetas_muestras', 'categoria': 'Recepcion'},

    # Resultados
    'R13': {'nombre': 'Hematologia Completa', 'metodo': 'R13_hematologia_completa', 'categoria': 'Resultados'},
    'R18': {'nombre': 'Perfil Lipidico', 'metodo': 'R18_perfil_lipidico', 'categoria': 'Resultados'},
    'R19': {'nombre': 'Perfil Renal', 'metodo': 'R19_perfil_renal', 'categoria': 'Resultados'},
    'R20': {'nombre': 'Perfil Hepatico', 'metodo': 'R20_perfil_hepatico', 'categoria': 'Resultados'},
    'R26': {'nombre': 'Examen de Orina', 'metodo': 'R26_examen_orina', 'categoria': 'Resultados'},
    'R29': {'nombre': 'Coproanalisis', 'metodo': 'R29_coproanalisis', 'categoria': 'Resultados'},

    # Serologia / Antigenos Febriles
    'R31': {'nombre': 'Antigenos Febriles', 'metodo': 'R31_antigenos_febriles', 'categoria': 'Resultados'},
    'R32': {'nombre': 'Serologia General', 'metodo': 'R32_serologia_general', 'categoria': 'Resultados'},

    # Microbiologia / Bacteriologia
    'R40': {'nombre': 'Microbiologia - Cultivo General', 'metodo': 'R40_microbiologia_cultivo', 'categoria': 'Resultados'},
    'R41': {'nombre': 'Urocultivo', 'metodo': 'R41_urocultivo', 'categoria': 'Resultados'},
    'R42': {'nombre': 'Hemocultivo', 'metodo': 'R42_hemocultivo', 'categoria': 'Resultados'},
    'R43': {'nombre': 'Coprocultivo', 'metodo': 'R43_coprocultivo', 'categoria': 'Resultados'},
    'R44B': {'nombre': 'Cultivo de Secrecion', 'metodo': 'R44B_cultivo_secrecion', 'categoria': 'Resultados'},
    'R45B': {'nombre': 'Cultivo de Secrecion de Herida', 'metodo': 'R45B_cultivo_herida', 'categoria': 'Resultados'},
    'R46B': {'nombre': 'Baciloscopia (BK/BAAR)', 'metodo': 'R46B_baciloscopia', 'categoria': 'Resultados'},
    'R47B': {'nombre': 'Cultivo Micologico', 'metodo': 'R47B_cultivo_micologico', 'categoria': 'Resultados'},
    'R48B': {'nombre': 'Cultivo de Secrecion Conjuntival', 'metodo': 'R48B_cultivo_conjuntival', 'categoria': 'Resultados'},

    # Facturacion
    'R44': {'nombre': 'Factura Fiscal', 'metodo': 'R44_factura_fiscal', 'categoria': 'Facturacion'},
    'R45': {'nombre': 'Recibo de Caja', 'metodo': 'R45_recibo_caja', 'categoria': 'Facturacion'},
    'R48': {'nombre': 'Libro de Ventas', 'metodo': 'R48_libro_ventas', 'categoria': 'Facturacion'},

    # Gerenciales
    'R55': {'nombre': 'Dashboard Ejecutivo', 'metodo': 'R55_dashboard_ejecutivo', 'categoria': 'Gerencial'},
    'R58': {'nombre': 'Pruebas mas Solicitadas', 'metodo': 'R58_pruebas_mas_solicitadas', 'categoria': 'Gerencial'},
}


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("Modulo de Plantillas de Reportes - ANgesLAB")
    print("=" * 50)
    print("\nReportes disponibles:")
    for codigo, info in CATALOGO_REPORTES.items():
        print(f"  {codigo}: {info['nombre']} ({info['categoria']})")

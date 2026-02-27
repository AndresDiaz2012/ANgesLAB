"""
================================================================================
MODULO DE REPORTES - ESPECIFICACIONES TECNICAS ANgesLAB
================================================================================
Implementacion de los 24 reportes segun especificaciones tecnicas:

CATEGORIA: FACTURACION Y VENTAS (RPT-001 a RPT-006)
- RPT-001: Factura Completa
- RPT-002: Diario de Facturacion
- RPT-003: Recibo de Caja
- RPT-004: Relacion de Facturas
- RPT-005: Resumen de Facturacion
- RPT-006: Libro de Ventas

CATEGORIA: SOLICITUDES Y GESTION (RPT-007 a RPT-010)
- RPT-007: Comprobante Solicitud
- RPT-008: Relacion de Solicitudes
- RPT-009: Pruebas por Efectuar
- RPT-010: Auditoria Solicitudes

CATEGORIA: RESULTADOS Y BOLETAS (RPT-011 a RPT-014)
- RPT-011: Boleta Principal
- RPT-012: Boletas por Entregar
- RPT-013: HDT por Solicitud Master
- RPT-014: Pruebas Efectuadas y Resultados

CATEGORIA: INVENTARIO (RPT-015 a RPT-018)
- RPT-015: Inventario Valorado
- RPT-016: Lista de Existencias
- RPT-017: Movimientos de Existencia
- RPT-018: Control de Minimos

CATEGORIA: CAJA Y FINANZAS (RPT-019 a RPT-021)
- RPT-019: Diario de Caja
- RPT-020: Saldos de Caja
- RPT-021: Estado de Cuentas V3

CATEGORIA: CATALOGOS (RPT-022 a RPT-024)
- RPT-022: Lista de Precios
- RPT-023: Lista de Pruebas
- RPT-024: Lista de Pacientes

Autor: Sistema ANgesLAB
================================================================================
"""

from datetime import datetime, date
from decimal import Decimal
import os

# ============================================================================
# CONFIGURACION DE ESTILOS CSS
# ============================================================================

CSS_REPORTES = """
<style>
    @page {
        margin: 1cm;
        size: letter;
    }
    @media print {
        .no-print { display: none; }
        .page-break { page-break-before: always; }
    }
    * { box-sizing: border-box; }
    body {
        font-family: Arial, Helvetica, sans-serif;
        font-size: 10pt;
        line-height: 1.4;
        margin: 0;
        padding: 15px;
    }
    .reporte-container {
        max-width: 800px;
        margin: 0 auto;
        border: 1px solid #333;
        padding: 0;
    }
    .encabezado {
        background: linear-gradient(to bottom, #f8f8f8, #e8e8e8);
        border-bottom: 2px solid #333;
        padding: 15px;
        text-align: center;
    }
    .encabezado h1 {
        margin: 0 0 5px 0;
        font-size: 16pt;
        color: #333;
    }
    .encabezado .subtitulo {
        font-size: 9pt;
        color: #666;
    }
    .datos-fiscales {
        font-size: 9pt;
        margin-top: 5px;
    }
    .numero-documento {
        font-size: 14pt;
        font-weight: bold;
        color: #000;
        margin: 10px 0;
    }
    .seccion {
        border-bottom: 1px solid #ccc;
        padding: 10px 15px;
    }
    .seccion-titulo {
        background: #333;
        color: white;
        padding: 5px 15px;
        font-weight: bold;
        font-size: 10pt;
        margin: 0;
    }
    .fila-datos {
        display: flex;
        margin: 3px 0;
    }
    .etiqueta {
        font-weight: bold;
        width: 130px;
        color: #333;
    }
    .valor {
        flex: 1;
    }
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 9pt;
    }
    th {
        background: #f0f0f0;
        border: 1px solid #333;
        padding: 6px 8px;
        text-align: left;
        font-weight: bold;
    }
    td {
        border: 1px solid #ccc;
        padding: 5px 8px;
    }
    .text-right { text-align: right; }
    .text-center { text-align: center; }
    .text-bold { font-weight: bold; }
    .totales-box {
        background: #f8f8f8;
        padding: 10px 15px;
        border-top: 2px solid #333;
    }
    .total-fila {
        display: flex;
        justify-content: space-between;
        padding: 3px 0;
    }
    .total-final {
        font-size: 14pt;
        font-weight: bold;
        border-top: 2px solid #333;
        margin-top: 5px;
        padding-top: 5px;
    }
    .pie-reporte {
        padding: 15px;
        font-size: 8pt;
        color: #666;
        border-top: 1px solid #ccc;
    }
    .firma-box {
        margin-top: 30px;
        text-align: center;
    }
    .firma-linea {
        border-top: 1px solid #333;
        width: 200px;
        margin: 0 auto;
        padding-top: 5px;
    }
    .alerta { color: #d00; font-weight: bold; }
    .exito { color: #080; }
    .advertencia { color: #f80; }
    .monto-grande {
        font-size: 18pt;
        font-weight: bold;
    }
    .codigo-barras {
        font-family: 'Libre Barcode 39', 'Code 39', monospace;
        font-size: 32pt;
    }
    .grid-2col {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 10px;
    }
    .resaltado {
        background: #ffffcc;
        padding: 2px 5px;
    }
</style>
"""


# ============================================================================
# CLASE PRINCIPAL DE REPORTES ESPECIFICACIONES
# ============================================================================

class ReportesEspecificaciones:
    """
    Genera los 24 reportes segun especificaciones tecnicas
    """

    def __init__(self, db):
        self.db = db
        self._cargar_config_laboratorio()

    def _cargar_config_laboratorio(self):
        """Carga configuracion del laboratorio"""
        try:
            config = self.db.query_one("SELECT * FROM ConfiguracionSistema")
            self.lab_nombre = config.get('NombreLaboratorio', 'LABORATORIO CLINICO') if config else 'LABORATORIO CLINICO'
            self.lab_rif = config.get('RIF', 'J-00000000-0') if config else 'J-00000000-0'
            self.lab_direccion = config.get('Direccion', '') if config else ''
            self.lab_telefono = config.get('Telefono', '') if config else ''
            self.lab_email = config.get('Email', '') if config else ''
        except:
            self.lab_nombre = 'LABORATORIO CLINICO'
            self.lab_rif = 'J-00000000-0'
            self.lab_direccion = ''
            self.lab_telefono = ''
            self.lab_email = ''

    def _generar_encabezado_html(self, titulo_reporte, subtitulo=''):
        """Genera encabezado HTML estandar"""
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{titulo_reporte}</title>
            {CSS_REPORTES}
        </head>
        <body>
            <div class="reporte-container">
                <div class="encabezado">
                    <h1>{self.lab_nombre}</h1>
                    <div class="datos-fiscales">
                        RIF: {self.lab_rif}<br>
                        {self.lab_direccion}<br>
                        Tel: {self.lab_telefono} | {self.lab_email}
                    </div>
                    <div class="numero-documento">{titulo_reporte}</div>
                    {f'<div class="subtitulo">{subtitulo}</div>' if subtitulo else ''}
                </div>
        """

    def _generar_pie_html(self, incluir_firma=False, texto_firma=''):
        """Genera pie de pagina HTML"""
        html = '<div class="pie-reporte">'

        if incluir_firma:
            html += f"""
            <div class="firma-box">
                <div class="firma-linea">{texto_firma or 'Firma Autorizada'}</div>
            </div>
            """

        html += f"""
            <div style="margin-top: 20px; text-align: center;">
                Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </div>
        </div>
        </div>
        </body>
        </html>
        """
        return html

    # =========================================================================
    # CATEGORIA: FACTURACION Y VENTAS (RPT-001 a RPT-006)
    # =========================================================================

    def RPT_001_factura_completa(self, numero_factura=None, fecha_factura=None, codigo_cliente=None):
        """
        RPT-001: Factura - Completa
        Prioridad: CRITICA | Frecuencia: ALTA - Multiple por hora
        Tablas: FACTURAS, RENGLONES_FACTURA, SOLICITUDES, CLIENTES, COBROS
        """
        # Construir WHERE
        where_clauses = ["f.Anulada = False"]
        if numero_factura:
            where_clauses.append(f"f.NumeroFactura = '{numero_factura}'")
        if fecha_factura:
            where_clauses.append(f"DATEVALUE(f.FechaEmision) = #{fecha_factura.strftime('%m/%d/%Y')}#")
        if codigo_cliente:
            where_clauses.append(f"p.PacienteID = {codigo_cliente}")

        where_sql = " AND ".join(where_clauses)

        # Obtener factura
        factura = self.db.query_one(f"""
            SELECT f.*,
                   p.Nombres + ' ' + p.Apellidos as NombreCliente,
                   p.NumeroDocumento as RucCedula,
                   p.Direccion as DireccionCliente,
                   p.Telefono as TelefonoCliente
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE {where_sql}
            ORDER BY f.FechaEmision DESC
        """)

        if not factura:
            return "<html><body><h1>Factura no encontrada</h1></body></html>"

        # Obtener detalles
        detalles = self.db.query(f"""
            SELECT df.*, pr.CodigoPrueba, pr.NombrePrueba
            FROM DetalleFacturas df
            LEFT JOIN Pruebas pr ON df.PruebaID = pr.PruebaID
            WHERE df.FacturaID = {factura['FacturaID']}
            ORDER BY df.DetalleID
        """)

        # Obtener cobros
        cobros = self.db.query(f"""
            SELECT * FROM Pagos WHERE FacturaID = {factura['FacturaID']}
        """)

        # Calcular totales
        subtotal = factura.get('SubTotal', 0) or 0
        descuento = factura.get('Descuento', 0) or 0
        base_imponible = subtotal - descuento
        iva = factura.get('MontoIVA', 0) or 0
        total = factura.get('MontoTotal', 0) or 0

        html = self._generar_encabezado_html(
            f"FACTURA No. {factura.get('NumeroFactura', 'N/A')}",
            f"Control: {factura.get('NumeroControl', 'N/A')}"
        )

        # Datos del cliente
        html += f"""
        <div class="seccion">
            <div class="seccion-titulo">DATOS DEL CLIENTE</div>
            <div style="padding: 10px;">
                <div class="grid-2col">
                    <div>
                        <div class="fila-datos">
                            <span class="etiqueta">Cliente:</span>
                            <span class="valor">{factura.get('NombreCliente', 'N/A')}</span>
                        </div>
                        <div class="fila-datos">
                            <span class="etiqueta">RIF/Cedula:</span>
                            <span class="valor">{factura.get('RucCedula', 'N/A')}</span>
                        </div>
                    </div>
                    <div>
                        <div class="fila-datos">
                            <span class="etiqueta">Direccion:</span>
                            <span class="valor">{factura.get('DireccionCliente', 'N/A')}</span>
                        </div>
                        <div class="fila-datos">
                            <span class="etiqueta">Fecha:</span>
                            <span class="valor">{factura.get('FechaEmision').strftime('%d/%m/%Y') if factura.get('FechaEmision') else 'N/A'}</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        """

        # Detalle de servicios
        html += """
        <div class="seccion">
            <div class="seccion-titulo">DETALLE DE SERVICIOS</div>
            <table>
                <thead>
                    <tr>
                        <th style="width:60px;">Cod.</th>
                        <th>Descripcion</th>
                        <th style="width:50px;" class="text-center">Qty</th>
                        <th style="width:80px;" class="text-right">Precio</th>
                        <th style="width:90px;" class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        for det in detalles:
            codigo = det.get('CodigoPrueba', 'SRV')
            descripcion = det.get('Descripcion') or det.get('NombrePrueba', 'Servicio')
            cantidad = det.get('Cantidad', 1)
            precio = det.get('PrecioUnitario', 0) or 0
            total_linea = cantidad * precio

            html += f"""
                <tr>
                    <td>{codigo}</td>
                    <td>{descripcion}</td>
                    <td class="text-center">{cantidad}</td>
                    <td class="text-right">{precio:,.2f}</td>
                    <td class="text-right">{total_linea:,.2f}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        # Totales
        html += f"""
        <div class="totales-box">
            <div class="total-fila">
                <span>Subtotal:</span>
                <span>$ {subtotal:,.2f}</span>
            </div>
            <div class="total-fila">
                <span>Descuento ({(descuento/subtotal*100) if subtotal > 0 else 0:.0f}%):</span>
                <span>$ {descuento:,.2f}</span>
            </div>
            <div class="total-fila">
                <span>Base Imponible:</span>
                <span>$ {base_imponible:,.2f}</span>
            </div>
            <div class="total-fila">
                <span>IVA (16%):</span>
                <span>$ {iva:,.2f}</span>
            </div>
            <div class="total-fila total-final">
                <span>TOTAL:</span>
                <span class="monto-grande">$ {total:,.2f}</span>
            </div>
        </div>
        """

        # Pie con forma de pago
        forma_pago = factura.get('FormaPago', 'Contado')
        observaciones = factura.get('Observaciones', '')

        html += f"""
        <div class="seccion">
            <div class="fila-datos">
                <span class="etiqueta">Forma de Pago:</span>
                <span class="valor">{forma_pago}</span>
            </div>
            {f'<div class="fila-datos"><span class="etiqueta">Observaciones:</span><span class="valor">{observaciones}</span></div>' if observaciones else ''}
            <div style="margin-top: 10px; font-size: 8pt; color: #666;">
                <p>* Esta factura constituye titulo ejecutivo conforme a la ley</p>
                <p>* Contribuyente Ordinario</p>
            </div>
        </div>
        """

        html += self._generar_pie_html(incluir_firma=True, texto_firma='Emitido por')
        return html

    def RPT_002_diario_facturacion(self, fecha_desde=None, fecha_hasta=None):
        """
        RPT-002: Diario de Facturacion
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        if not fecha_desde:
            fecha_desde = date.today()
        if not fecha_hasta:
            fecha_hasta = fecha_desde

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        facturas = self.db.query(f"""
            SELECT f.*, p.Nombres + ' ' + p.Apellidos as NombreCliente,
                   p.NumeroDocumento
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE f.FechaEmision >= #{f_desde}# AND f.FechaEmision <= #{f_hasta}#
            ORDER BY f.FechaEmision, f.NumeroFactura
        """)

        html = self._generar_encabezado_html(
            "DIARIO DE FACTURACION",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        html += """
        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>No. Factura</th>
                        <th>Control</th>
                        <th>Cliente</th>
                        <th>RIF/CI</th>
                        <th class="text-right">Subtotal</th>
                        <th class="text-right">IVA</th>
                        <th class="text-right">Total</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
        """

        total_subtotal = 0
        total_iva = 0
        total_general = 0
        total_anuladas = 0

        for f in facturas:
            anulada = f.get('Anulada', False)
            subtotal = f.get('SubTotal', 0) or 0
            iva = f.get('MontoIVA', 0) or 0
            total = f.get('MontoTotal', 0) or 0

            if not anulada:
                total_subtotal += subtotal
                total_iva += iva
                total_general += total
            else:
                total_anuladas += 1

            clase_anulada = 'style="text-decoration: line-through; color: #999;"' if anulada else ''

            html += f"""
                <tr {clase_anulada}>
                    <td>{f.get('FechaEmision').strftime('%d/%m/%Y') if f.get('FechaEmision') else ''}</td>
                    <td>{f.get('NumeroFactura', '')}</td>
                    <td>{f.get('NumeroControl', '')}</td>
                    <td>{f.get('NombreCliente', '')[:25]}</td>
                    <td>{f.get('NumeroDocumento', '')}</td>
                    <td class="text-right">{subtotal:,.2f}</td>
                    <td class="text-right">{iva:,.2f}</td>
                    <td class="text-right">{total:,.2f}</td>
                    <td>{'ANULADA' if anulada else 'OK'}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background: #f0f0f0;">
                        <td colspan="5">TOTALES ({len(facturas)} facturas, {total_anuladas} anuladas)</td>
                        <td class="text-right">{total_subtotal:,.2f}</td>
                        <td class="text-right">{total_iva:,.2f}</td>
                        <td class="text-right">{total_general:,.2f}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_003_recibo_caja(self, numero_recibo=None, pago_id=None):
        """
        RPT-003: Recibo de Caja
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        where = f"pg.PagoID = {pago_id}" if pago_id else f"pg.NumeroRecibo = '{numero_recibo}'"

        pago = self.db.query_one(f"""
            SELECT pg.*, f.NumeroFactura, f.MontoTotal as TotalFactura,
                   p.Nombres + ' ' + p.Apellidos as NombreCliente,
                   p.NumeroDocumento
            FROM Pagos pg
            INNER JOIN Facturas f ON pg.FacturaID = f.FacturaID
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE {where}
        """)

        if not pago:
            return "<html><body><h1>Recibo no encontrado</h1></body></html>"

        monto = pago.get('Monto', 0) or 0

        # Convertir a letras
        monto_letras = self._numero_a_letras(monto)

        html = self._generar_encabezado_html(
            f"RECIBO DE CAJA No. {pago.get('NumeroRecibo', pago_id)}",
            f"Fecha: {pago.get('FechaPago').strftime('%d/%m/%Y') if pago.get('FechaPago') else datetime.now().strftime('%d/%m/%Y')}"
        )

        html += f"""
        <div class="seccion">
            <div class="fila-datos">
                <span class="etiqueta">Recibimos de:</span>
                <span class="valor text-bold">{pago.get('NombreCliente', 'N/A')}</span>
            </div>
            <div class="fila-datos">
                <span class="etiqueta">Cedula/RIF:</span>
                <span class="valor">{pago.get('NumeroDocumento', 'N/A')}</span>
            </div>
        </div>

        <div class="seccion" style="text-align: center; padding: 20px;">
            <div style="border: 3px solid #333; padding: 15px; display: inline-block; min-width: 200px;">
                <div class="monto-grande">$ {monto:,.2f}</div>
            </div>
        </div>

        <div class="seccion">
            <div class="fila-datos">
                <span class="etiqueta">La cantidad de:</span>
                <span class="valor text-bold">{monto_letras.upper()}</span>
            </div>
            <div class="fila-datos">
                <span class="etiqueta">Por concepto de:</span>
                <span class="valor">Pago de servicios de laboratorio clinico</span>
            </div>
            <div class="fila-datos">
                <span class="etiqueta">Factura No.:</span>
                <span class="valor">{pago.get('NumeroFactura', 'N/A')}</span>
            </div>
            <div class="fila-datos">
                <span class="etiqueta">Forma de Pago:</span>
                <span class="valor">{pago.get('FormaPago', 'Efectivo')}</span>
            </div>
            {f'<div class="fila-datos"><span class="etiqueta">Referencia:</span><span class="valor">{pago.get("Referencia", "")}</span></div>' if pago.get('Referencia') else ''}
        </div>
        """

        html += self._generar_pie_html(incluir_firma=True, texto_firma='Cajero')
        return html

    def RPT_004_relacion_facturas(self, fecha_desde=None, fecha_hasta=None, estado=None):
        """
        RPT-004: Relacion de Facturas
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        if not fecha_desde:
            fecha_desde = date.today().replace(day=1)
        if not fecha_hasta:
            fecha_hasta = date.today()

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        where_estado = ""
        if estado:
            where_estado = f" AND f.EstadoPago = '{estado}'"

        facturas = self.db.query(f"""
            SELECT f.*, p.Nombres + ' ' + p.Apellidos as NombreCliente,
                   p.NumeroDocumento,
                   (SELECT SUM(Monto) FROM Pagos WHERE FacturaID = f.FacturaID) as TotalPagado
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE f.FechaEmision >= #{f_desde}# AND f.FechaEmision <= #{f_hasta}#
            {where_estado}
            ORDER BY f.NumeroFactura
        """)

        html = self._generar_encabezado_html(
            "RELACION DE FACTURAS",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        html += """
        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>No. Factura</th>
                        <th>Fecha</th>
                        <th>Cliente</th>
                        <th class="text-right">Total</th>
                        <th class="text-right">Pagado</th>
                        <th class="text-right">Pendiente</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
        """

        total_facturado = 0
        total_pagado = 0
        total_pendiente = 0

        for f in facturas:
            total_fact = f.get('MontoTotal', 0) or 0
            pagado = f.get('TotalPagado', 0) or 0
            pendiente = total_fact - pagado

            total_facturado += total_fact
            total_pagado += pagado
            total_pendiente += pendiente

            estado_pago = 'PAGADA' if pendiente <= 0 else ('PARCIAL' if pagado > 0 else 'PENDIENTE')
            clase_estado = 'exito' if estado_pago == 'PAGADA' else ('advertencia' if estado_pago == 'PARCIAL' else 'alerta')

            if f.get('Anulada'):
                estado_pago = 'ANULADA'
                clase_estado = ''

            html += f"""
                <tr>
                    <td>{f.get('NumeroFactura', '')}</td>
                    <td>{f.get('FechaEmision').strftime('%d/%m/%Y') if f.get('FechaEmision') else ''}</td>
                    <td>{f.get('NombreCliente', '')[:30]}</td>
                    <td class="text-right">{total_fact:,.2f}</td>
                    <td class="text-right">{pagado:,.2f}</td>
                    <td class="text-right">{pendiente:,.2f}</td>
                    <td class="{clase_estado}">{estado_pago}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background: #f0f0f0;">
                        <td colspan="3">TOTALES ({len(facturas)} facturas)</td>
                        <td class="text-right">{total_facturado:,.2f}</td>
                        <td class="text-right">{total_pagado:,.2f}</td>
                        <td class="text-right">{total_pendiente:,.2f}</td>
                        <td></td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_005_resumen_facturacion(self, fecha_desde=None, fecha_hasta=None):
        """
        RPT-005: Resumen de Facturacion
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        if not fecha_desde:
            fecha_desde = date.today().replace(day=1)
        if not fecha_hasta:
            fecha_hasta = date.today()

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        # Resumen general
        resumen = self.db.query_one(f"""
            SELECT COUNT(*) as TotalFacturas,
                   SUM(IIF(Anulada = False, SubTotal, 0)) as TotalSubtotal,
                   SUM(IIF(Anulada = False, MontoIVA, 0)) as TotalIVA,
                   SUM(IIF(Anulada = False, MontoTotal, 0)) as TotalGeneral,
                   SUM(IIF(Anulada = True, 1, 0)) as FacturasAnuladas
            FROM Facturas
            WHERE FechaEmision >= #{f_desde}# AND FechaEmision <= #{f_hasta}#
        """)

        # Por forma de pago
        por_forma_pago = self.db.query(f"""
            SELECT FormaPago, COUNT(*) as Cantidad, SUM(MontoTotal) as Total
            FROM Facturas
            WHERE FechaEmision >= #{f_desde}# AND FechaEmision <= #{f_hasta}#
            AND Anulada = False
            GROUP BY FormaPago
        """)

        # Por dia
        por_dia = self.db.query(f"""
            SELECT DATEVALUE(FechaEmision) as Fecha, COUNT(*) as Cantidad,
                   SUM(MontoTotal) as Total
            FROM Facturas
            WHERE FechaEmision >= #{f_desde}# AND FechaEmision <= #{f_hasta}#
            AND Anulada = False
            GROUP BY DATEVALUE(FechaEmision)
            ORDER BY DATEVALUE(FechaEmision)
        """)

        html = self._generar_encabezado_html(
            "RESUMEN DE FACTURACION",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        # Resumen general
        html += f"""
        <div class="seccion">
            <div class="seccion-titulo">RESUMEN GENERAL</div>
            <div class="grid-2col" style="padding: 15px;">
                <div>
                    <div class="fila-datos">
                        <span class="etiqueta">Total Facturas:</span>
                        <span class="valor text-bold">{resumen.get('TotalFacturas', 0) if resumen else 0}</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">Anuladas:</span>
                        <span class="valor">{resumen.get('FacturasAnuladas', 0) if resumen else 0}</span>
                    </div>
                </div>
                <div>
                    <div class="fila-datos">
                        <span class="etiqueta">Subtotal:</span>
                        <span class="valor">$ {resumen.get('TotalSubtotal', 0) or 0 if resumen else 0:,.2f}</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">IVA:</span>
                        <span class="valor">$ {resumen.get('TotalIVA', 0) or 0 if resumen else 0:,.2f}</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">TOTAL:</span>
                        <span class="valor text-bold monto-grande">$ {resumen.get('TotalGeneral', 0) or 0 if resumen else 0:,.2f}</span>
                    </div>
                </div>
            </div>
        </div>
        """

        # Por forma de pago
        html += """
        <div class="seccion">
            <div class="seccion-titulo">POR FORMA DE PAGO</div>
            <table>
                <thead>
                    <tr>
                        <th>Forma de Pago</th>
                        <th class="text-center">Cantidad</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        for fp in por_forma_pago:
            html += f"""
                <tr>
                    <td>{fp.get('FormaPago', 'Sin especificar')}</td>
                    <td class="text-center">{fp.get('Cantidad', 0)}</td>
                    <td class="text-right">$ {fp.get('Total', 0) or 0:,.2f}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        # Por dia
        html += """
        <div class="seccion">
            <div class="seccion-titulo">DETALLE POR DIA</div>
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th class="text-center">Facturas</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        for dia in por_dia:
            fecha = dia.get('Fecha')
            fecha_str = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else str(fecha)
            html += f"""
                <tr>
                    <td>{fecha_str}</td>
                    <td class="text-center">{dia.get('Cantidad', 0)}</td>
                    <td class="text-right">$ {dia.get('Total', 0) or 0:,.2f}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_006_libro_ventas(self, mes, anio):
        """
        RPT-006: Libro de Ventas
        Prioridad: ALTA (Legal) | Frecuencia: BAJA - Mensual
        """
        fecha_inicio = f"{anio}-{mes:02d}-01"
        fecha_fin = f"{anio}-{mes:02d}-31"

        facturas = self.db.query(f"""
            SELECT f.*,
                   p.Nombres + ' ' + p.Apellidos as NombreCliente,
                   p.NumeroDocumento
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE f.FechaEmision >= #{fecha_inicio}#
            AND f.FechaEmision <= #{fecha_fin}#
            ORDER BY f.FechaEmision, f.NumeroFactura
        """)

        html = self._generar_encabezado_html(
            "LIBRO DE VENTAS",
            f"Periodo Fiscal: {mes:02d}/{anio}"
        )

        html += f"""
        <div class="seccion">
            <div class="fila-datos">
                <span class="etiqueta">RIF:</span>
                <span class="valor">{self.lab_rif}</span>
            </div>
            <div class="fila-datos">
                <span class="etiqueta">Razon Social:</span>
                <span class="valor">{self.lab_nombre}</span>
            </div>
        </div>
        """

        html += """
        <div class="seccion">
            <table style="font-size: 8pt;">
                <thead>
                    <tr>
                        <th>Oper.</th>
                        <th>Fecha</th>
                        <th>Factura</th>
                        <th>Control</th>
                        <th>RIF/CI</th>
                        <th>Nombre/Razon Social</th>
                        <th class="text-right">Base Imp.</th>
                        <th class="text-right">IVA</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        total_base = 0
        total_iva = 0
        total_general = 0
        num_operacion = 0

        for f in facturas:
            num_operacion += 1
            anulada = f.get('Anulada', False)

            base = (f.get('SubTotal', 0) or 0) if not anulada else 0
            iva = (f.get('MontoIVA', 0) or 0) if not anulada else 0
            total = (f.get('MontoTotal', 0) or 0) if not anulada else 0

            total_base += base
            total_iva += iva
            total_general += total

            estilo = 'style="text-decoration: line-through;"' if anulada else ''

            html += f"""
                <tr {estilo}>
                    <td class="text-center">{num_operacion}</td>
                    <td>{f.get('FechaEmision').strftime('%d/%m') if f.get('FechaEmision') else ''}</td>
                    <td>{f.get('NumeroFactura', '')}</td>
                    <td>{f.get('NumeroControl', '')}</td>
                    <td>{f.get('NumeroDocumento', '')}</td>
                    <td>{f.get('NombreCliente', '')[:20]}{'...' if len(f.get('NombreCliente', '')) > 20 else ''}</td>
                    <td class="text-right">{base:,.2f}</td>
                    <td class="text-right">{iva:,.2f}</td>
                    <td class="text-right">{total:,.2f}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background: #f0f0f0;">
                        <td colspan="6">TOTALES DEL PERIODO</td>
                        <td class="text-right">{total_base:,.2f}</td>
                        <td class="text-right">{total_iva:,.2f}</td>
                        <td class="text-right">{total_general:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>

        <div class="seccion">
            <div class="seccion-titulo">RESUMEN FISCAL</div>
            <table style="width: 50%;">
                <tr>
                    <td>Total Operaciones:</td>
                    <td class="text-right text-bold">{num_operacion}</td>
                </tr>
                <tr>
                    <td>Base Imponible:</td>
                    <td class="text-right">$ {total_base:,.2f}</td>
                </tr>
                <tr>
                    <td>Total IVA (16%):</td>
                    <td class="text-right">$ {total_iva:,.2f}</td>
                </tr>
                <tr style="font-weight: bold; background: #f0f0f0;">
                    <td>TOTAL VENTAS:</td>
                    <td class="text-right">$ {total_general:,.2f}</td>
                </tr>
            </table>
        </div>
        """

        html += self._generar_pie_html(incluir_firma=True, texto_firma='Contador / Responsable')
        return html

    # =========================================================================
    # CATEGORIA: SOLICITUDES Y GESTION (RPT-007 a RPT-010)
    # =========================================================================

    def RPT_007_comprobante_solicitud(self, numero_solicitud=None, solicitud_id=None):
        """
        RPT-007: Comprobante Solicitud
        Prioridad: CRITICA | Frecuencia: ALTA - Varias por hora
        """
        where = f"s.SolicitudID = {solicitud_id}" if solicitud_id else f"s.NumeroSolicitud = '{numero_solicitud}'"

        solicitud = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Telefono, p.Edad, p.Sexo,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE {where}
        """)

        if not solicitud:
            return "<html><body><h1>Solicitud no encontrada</h1></body></html>"

        # Obtener pruebas
        pruebas = self.db.query(f"""
            SELECT ps.*, pr.NombrePrueba, pr.PrecioBase, pr.CodigoPrueba,
                   tm.Nombre as TipoMuestra, tm.Color as ColorTubo
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            LEFT JOIN TiposMuestra tm ON pr.TipoMuestraID = tm.TipoMuestraID
            WHERE ps.SolicitudID = {solicitud['SolicitudID']}
            ORDER BY pr.NombrePrueba
        """)

        total = sum(p.get('PrecioBase', 0) or 0 for p in pruebas)

        # Obtener muestras unicas
        muestras = {}
        for p in pruebas:
            muestra = p.get('TipoMuestra', 'Muestra')
            if muestra and muestra not in muestras:
                muestras[muestra] = p.get('ColorTubo', '')

        html = self._generar_encabezado_html(
            "COMPROBANTE DE SOLICITUD",
            f"No. {solicitud.get('NumeroSolicitud', 'N/A')}"
        )

        # Codigo de barras
        html += f"""
        <div style="text-align: center; padding: 10px;">
            <div class="codigo-barras">*{solicitud.get('NumeroSolicitud', '')}*</div>
        </div>
        """

        # Datos paciente
        html += f"""
        <div class="seccion">
            <div class="seccion-titulo">PACIENTE</div>
            <div style="padding: 10px;">
                <div class="fila-datos">
                    <span class="etiqueta">Nombre:</span>
                    <span class="valor text-bold">{solicitud.get('NombrePaciente', 'N/A')}</span>
                </div>
                <div class="grid-2col">
                    <div class="fila-datos">
                        <span class="etiqueta">Edad:</span>
                        <span class="valor">{solicitud.get('Edad', 'N/A')} anos</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">Sexo:</span>
                        <span class="valor">{'Masculino' if solicitud.get('Sexo') == 'M' else 'Femenino'}</span>
                    </div>
                </div>
                <div class="fila-datos">
                    <span class="etiqueta">Telefono:</span>
                    <span class="valor">{solicitud.get('Telefono', 'N/A')}</span>
                </div>
                <div class="fila-datos">
                    <span class="etiqueta">Medico:</span>
                    <span class="valor">{solicitud.get('NombreMedico', 'Particular')}</span>
                </div>
            </div>
        </div>
        """

        # Pruebas solicitadas
        html += """
        <div class="seccion">
            <div class="seccion-titulo">PRUEBAS SOLICITADAS</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 30px;"></th>
                        <th>Prueba</th>
                        <th class="text-right" style="width: 100px;">Precio</th>
                    </tr>
                </thead>
                <tbody>
        """

        for p in pruebas:
            html += f"""
                <tr>
                    <td class="text-center">&#9745;</td>
                    <td>{p.get('NombrePrueba', 'N/A')}</td>
                    <td class="text-right">$ {p.get('PrecioBase', 0) or 0:,.2f}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold;">
                        <td colspan="2">Total:</td>
                        <td class="text-right">$ {total:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        # Muestras requeridas
        if muestras:
            html += """
            <div class="seccion">
                <div class="seccion-titulo">MUESTRAS REQUERIDAS</div>
                <ul style="padding: 10px 10px 10px 30px;">
            """
            for muestra, color in muestras.items():
                html += f"""<li>{muestra} {f'(tubo {color})' if color else ''}</li>"""
            html += "</ul></div>"

        # Fecha de entrega
        fecha_entrega = solicitud.get('FechaEntrega')
        html += f"""
        <div class="seccion" style="text-align: center; padding: 15px;">
            <div class="seccion-titulo">ENTREGA ESTIMADA</div>
            <div style="padding: 15px;">
                <span style="font-size: 16pt; font-weight: bold;">
                    {fecha_entrega.strftime('%d/%m/%Y') if fecha_entrega else 'Consultar en recepcion'}
                </span>
                {f' - 5:00 PM' if fecha_entrega else ''}
            </div>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_008_relacion_solicitudes(self, fecha_desde=None, fecha_hasta=None, estado=None):
        """
        RPT-008: Relacion de Solicitudes
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        if not fecha_desde:
            fecha_desde = date.today()
        if not fecha_hasta:
            fecha_hasta = fecha_desde

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        where_estado = f" AND s.EstadoSolicitud = '{estado}'" if estado else ""

        solicitudes = self.db.query(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento,
                   (SELECT COUNT(*) FROM PruebasSolicitadas WHERE SolicitudID = s.SolicitudID) as TotalPruebas,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE s.FechaSolicitud >= #{f_desde}# AND s.FechaSolicitud <= #{f_hasta}#
            {where_estado}
            ORDER BY s.FechaSolicitud DESC, s.NumeroSolicitud
        """)

        html = self._generar_encabezado_html(
            "RELACION DE SOLICITUDES",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        html += """
        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>No. Solicitud</th>
                        <th>Fecha</th>
                        <th>Paciente</th>
                        <th>Cedula</th>
                        <th class="text-center">Pruebas</th>
                        <th>Estado</th>
                        <th>Medico</th>
                    </tr>
                </thead>
                <tbody>
        """

        for s in solicitudes:
            estado_class = ''
            estado_val = s.get('EstadoSolicitud', 'Pendiente')
            if estado_val == 'Entregada':
                estado_class = 'exito'
            elif estado_val in ['EnProceso', 'EnAnalisis']:
                estado_class = 'advertencia'

            html += f"""
                <tr>
                    <td>{s.get('NumeroSolicitud', '')}</td>
                    <td>{s.get('FechaSolicitud').strftime('%d/%m/%Y') if s.get('FechaSolicitud') else ''}</td>
                    <td>{s.get('NombrePaciente', '')[:25]}</td>
                    <td>{s.get('NumeroDocumento', '')}</td>
                    <td class="text-center">{s.get('TotalPruebas', 0)}</td>
                    <td class="{estado_class}">{estado_val}</td>
                    <td>{(s.get('NombreMedico', '') or 'Particular')[:20]}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="background: #f0f0f0;">
                        <td colspan="7" class="text-bold">Total: {len(solicitudes)} solicitudes</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_009_pruebas_por_efectuar(self, fecha_desde=None, fecha_hasta=None):
        """
        RPT-009: Pruebas por Efectuar
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        if not fecha_desde:
            fecha_desde = date.today()
        if not fecha_hasta:
            fecha_hasta = fecha_desde

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        pruebas = self.db.query(f"""
            SELECT ps.*, pr.NombrePrueba, pr.CodigoPrueba,
                   s.NumeroSolicitud, s.Prioridad,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   a.NombreArea
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            INNER JOIN Solicitudes s ON ps.SolicitudID = s.SolicitudID
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            WHERE s.FechaSolicitud >= #{f_desde}# AND s.FechaSolicitud <= #{f_hasta}#
            AND ps.Estado IN ('Pendiente', 'Recibida', 'EnProceso')
            ORDER BY s.Prioridad DESC, a.NombreArea, s.NumeroSolicitud
        """)

        html = self._generar_encabezado_html(
            "PRUEBAS POR EFECTUAR",
            f"Fecha: {fecha_desde.strftime('%d/%m/%Y')}"
        )

        html += f"""
        <div class="seccion">
            <p>Total de pruebas pendientes: <strong>{len(pruebas)}</strong></p>
        </div>
        """

        # Agrupar por area
        por_area = {}
        for p in pruebas:
            area = p.get('NombreArea', 'Sin Area')
            if area not in por_area:
                por_area[area] = []
            por_area[area].append(p)

        for area, lista in por_area.items():
            html += f"""
            <div class="seccion">
                <div class="seccion-titulo">{area} ({len(lista)} pruebas)</div>
                <table>
                    <thead>
                        <tr>
                            <th>Solicitud</th>
                            <th>Paciente</th>
                            <th>Prueba</th>
                            <th>Estado</th>
                            <th>Prioridad</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for p in lista:
                prioridad_class = 'alerta' if p.get('Prioridad') == 'Urgente' else ''
                html += f"""
                    <tr>
                        <td>{p.get('NumeroSolicitud', '')}</td>
                        <td>{p.get('NombrePaciente', '')[:20]}</td>
                        <td>{p.get('NombrePrueba', '')}</td>
                        <td>{p.get('Estado', '')}</td>
                        <td class="{prioridad_class}">{p.get('Prioridad', 'Normal')}</td>
                    </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            """

        html += self._generar_pie_html()
        return html

    def RPT_010_auditoria_solicitudes(self, fecha_desde=None, fecha_hasta=None, usuario_id=None):
        """
        RPT-010: Auditoria Solicitudes
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        if not fecha_desde:
            fecha_desde = date.today()
        if not fecha_hasta:
            fecha_hasta = fecha_desde

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        where_usuario = f" AND h.UsuarioID = {usuario_id}" if usuario_id else ""

        try:
            historial = self.db.query(f"""
                SELECT h.*, s.NumeroSolicitud,
                       u.NombreUsuario,
                       p.Nombres + ' ' + p.Apellidos as NombrePaciente
                FROM HistorialSolicitudes h
                INNER JOIN Solicitudes s ON h.SolicitudID = s.SolicitudID
                LEFT JOIN Usuarios u ON h.UsuarioID = u.UsuarioID
                INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE h.FechaAccion >= #{f_desde}# AND h.FechaAccion <= #{f_hasta}#
                {where_usuario}
                ORDER BY h.FechaAccion DESC
            """)
        except:
            historial = []

        html = self._generar_encabezado_html(
            "AUDITORIA DE SOLICITUDES",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        if not historial:
            html += """
            <div class="seccion" style="text-align: center; padding: 30px;">
                <p>No se encontraron registros de auditoria para el periodo seleccionado.</p>
            </div>
            """
        else:
            html += """
            <div class="seccion">
                <table>
                    <thead>
                        <tr>
                            <th>Fecha/Hora</th>
                            <th>Solicitud</th>
                            <th>Paciente</th>
                            <th>Accion</th>
                            <th>Usuario</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for h in historial:
                html += f"""
                    <tr>
                        <td>{h.get('FechaAccion').strftime('%d/%m/%Y %H:%M') if h.get('FechaAccion') else ''}</td>
                        <td>{h.get('NumeroSolicitud', '')}</td>
                        <td>{h.get('NombrePaciente', '')[:20]}</td>
                        <td>{h.get('Accion', '')[:40]}</td>
                        <td>{h.get('NombreUsuario', 'Sistema')}</td>
                    </tr>
                """

            html += f"""
                    </tbody>
                    <tfoot>
                        <tr style="background: #f0f0f0;">
                            <td colspan="5">Total registros: {len(historial)}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            """

        html += self._generar_pie_html()
        return html

    # =========================================================================
    # CATEGORIA: RESULTADOS Y BOLETAS (RPT-011 a RPT-014)
    # =========================================================================

    def RPT_011_boleta_principal(self, numero_solicitud=None, solicitud_id=None):
        """
        RPT-011: Boleta - Principal
        Prioridad: CRITICA | Frecuencia: ALTA - Multiple por hora
        """
        where = f"s.SolicitudID = {solicitud_id}" if solicitud_id else f"s.NumeroSolicitud = '{numero_solicitud}'"

        solicitud = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Edad, p.Sexo, p.FechaNacimiento,
                   m.Nombres + ' ' + m.Apellidos as NombreMedico
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
            WHERE {where}
        """)

        if not solicitud:
            return "<html><body><h1>Solicitud no encontrada</h1></body></html>"

        # Obtener resultados agrupados por area
        resultados = self.db.query(f"""
            SELECT r.*, param.NombreParametro, param.Seccion,
                   u.Simbolo as Unidad,
                   pr.NombrePrueba, a.NombreArea, a.AreaID
            FROM Resultados r
            INNER JOIN Parametros param ON r.ParametroID = param.ParametroID
            LEFT JOIN Unidades u ON r.UnidadID = u.UnidadID
            INNER JOIN PruebasSolicitadas ps ON r.PruebaSolicitadaID = ps.PruebaSolicitadaID
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            WHERE ps.SolicitudID = {solicitud['SolicitudID']}
            ORDER BY a.Secuencia, pr.NombrePrueba, r.ResultadoID
        """)

        html = self._generar_encabezado_html(
            "RESULTADOS DE LABORATORIO",
            f"Solicitud No. {solicitud.get('NumeroSolicitud', 'N/A')}"
        )

        # Datos del paciente
        html += f"""
        <div class="seccion">
            <div class="seccion-titulo">DATOS DEL PACIENTE</div>
            <div class="grid-2col" style="padding: 10px;">
                <div>
                    <div class="fila-datos">
                        <span class="etiqueta">Nombre:</span>
                        <span class="valor text-bold">{solicitud.get('NombrePaciente', 'N/A')}</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">Edad:</span>
                        <span class="valor">{solicitud.get('Edad', 'N/A')} anos</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">Sexo:</span>
                        <span class="valor">{'Masculino' if solicitud.get('Sexo') == 'M' else 'Femenino'}</span>
                    </div>
                </div>
                <div>
                    <div class="fila-datos">
                        <span class="etiqueta">Medico:</span>
                        <span class="valor">{solicitud.get('NombreMedico', 'Particular')}</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">Fecha:</span>
                        <span class="valor">{solicitud.get('FechaSolicitud').strftime('%d/%m/%Y') if solicitud.get('FechaSolicitud') else 'N/A'}</span>
                    </div>
                </div>
            </div>
        </div>
        """

        # Agrupar resultados por area
        por_area = {}
        for r in resultados:
            area = r.get('NombreArea', 'General')
            if area not in por_area:
                por_area[area] = []
            por_area[area].append(r)

        # Generar tablas por area
        for area, lista_resultados in por_area.items():
            html += f"""
            <div class="seccion">
                <div class="seccion-titulo">{area.upper()}</div>
                <table>
                    <thead>
                        <tr>
                            <th>Prueba</th>
                            <th class="text-center">Resultado</th>
                            <th class="text-center">Unidad</th>
                            <th>Valor de Referencia</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for r in lista_resultados:
                valor = r.get('ValorNumerico') or r.get('ValorTexto') or '---'
                clase = ''
                if r.get('FueraDeRango'):
                    clase = 'alerta' if r.get('TipoAlerta') in ['Alto', 'CriticoAlto'] else 'advertencia'

                html += f"""
                    <tr>
                        <td>{r.get('NombreParametro', 'N/A')}</td>
                        <td class="text-center text-bold {clase}">{valor}</td>
                        <td class="text-center">{r.get('Unidad', '')}</td>
                        <td>{r.get('ValorReferencia', '')}</td>
                    </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            """

        html += self._generar_pie_html(incluir_firma=True, texto_firma='Bioanalista')
        return html

    def RPT_012_boletas_por_entregar(self, fecha=None):
        """
        RPT-012: Boletas por Entregar
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        if not fecha:
            fecha = date.today()

        f_str = fecha.strftime('%m/%d/%Y')

        solicitudes = self.db.query(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Telefono,
                   (SELECT COUNT(*) FROM PruebasSolicitadas WHERE SolicitudID = s.SolicitudID) as TotalPruebas,
                   (SELECT COUNT(*) FROM PruebasSolicitadas WHERE SolicitudID = s.SolicitudID AND Estado = 'Completada') as PruebasListas
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            WHERE s.EstadoSolicitud IN ('Completada', 'Validada')
            AND DATEVALUE(s.FechaEntrega) <= #{f_str}#
            ORDER BY s.FechaEntrega, s.NumeroSolicitud
        """)

        html = self._generar_encabezado_html(
            "BOLETAS POR ENTREGAR",
            f"Fecha: {fecha.strftime('%d/%m/%Y')}"
        )

        html += f"""
        <div class="seccion">
            <p>Total de boletas listas para entrega: <strong>{len(solicitudes)}</strong></p>
        </div>

        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>No. Solicitud</th>
                        <th>Paciente</th>
                        <th>Telefono</th>
                        <th class="text-center">Pruebas</th>
                        <th>F. Entrega</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
        """

        for s in solicitudes:
            total_pruebas = s.get('TotalPruebas', 0)
            pruebas_listas = s.get('PruebasListas', 0)
            porcentaje = (pruebas_listas / total_pruebas * 100) if total_pruebas > 0 else 0

            html += f"""
                <tr>
                    <td>{s.get('NumeroSolicitud', '')}</td>
                    <td>{s.get('NombrePaciente', '')[:25]}</td>
                    <td>{s.get('Telefono', '')}</td>
                    <td class="text-center">{pruebas_listas}/{total_pruebas}</td>
                    <td>{s.get('FechaEntrega').strftime('%d/%m/%Y') if s.get('FechaEntrega') else ''}</td>
                    <td class="{'exito' if porcentaje == 100 else 'advertencia'}">{porcentaje:.0f}% Listo</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_013_hdt_solicitud_master(self, solicitud_id):
        """
        RPT-013: HDT por Solicitud - Master (Hoja de Trabajo)
        Prioridad: CRITICA | Frecuencia: ALTA
        """
        solicitud = self.db.query_one(f"""
            SELECT s.*,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento, p.Edad, p.Sexo
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            WHERE s.SolicitudID = {solicitud_id}
        """)

        if not solicitud:
            return "<html><body><h1>Solicitud no encontrada</h1></body></html>"

        # Obtener pruebas con parametros
        pruebas = self.db.query(f"""
            SELECT ps.*, pr.NombrePrueba, pr.CodigoPrueba,
                   a.NombreArea
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            WHERE ps.SolicitudID = {solicitud_id}
            ORDER BY a.Secuencia, pr.NombrePrueba
        """)

        html = self._generar_encabezado_html(
            "HOJA DE TRABAJO",
            f"Solicitud: {solicitud.get('NumeroSolicitud', 'N/A')}"
        )

        html += f"""
        <div class="seccion">
            <div class="grid-2col">
                <div>
                    <div class="fila-datos">
                        <span class="etiqueta">Paciente:</span>
                        <span class="valor text-bold">{solicitud.get('NombrePaciente', 'N/A')}</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">Cedula:</span>
                        <span class="valor">{solicitud.get('NumeroDocumento', 'N/A')}</span>
                    </div>
                </div>
                <div>
                    <div class="fila-datos">
                        <span class="etiqueta">Edad/Sexo:</span>
                        <span class="valor">{solicitud.get('Edad', 'N/A')} / {'M' if solicitud.get('Sexo') == 'M' else 'F'}</span>
                    </div>
                    <div class="fila-datos">
                        <span class="etiqueta">Fecha:</span>
                        <span class="valor">{solicitud.get('FechaSolicitud').strftime('%d/%m/%Y') if solicitud.get('FechaSolicitud') else 'N/A'}</span>
                    </div>
                </div>
            </div>
        </div>
        """

        # Agrupar por area
        por_area = {}
        for p in pruebas:
            area = p.get('NombreArea', 'General')
            if area not in por_area:
                por_area[area] = []
            por_area[area].append(p)

        for area, lista in por_area.items():
            html += f"""
            <div class="seccion">
                <div class="seccion-titulo">{area}</div>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 30px;">&#9744;</th>
                            <th>Codigo</th>
                            <th>Prueba</th>
                            <th>Estado</th>
                            <th style="width: 150px;">Resultado</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for p in lista:
                html += f"""
                    <tr>
                        <td class="text-center">&#9744;</td>
                        <td>{p.get('CodigoPrueba', '')}</td>
                        <td>{p.get('NombrePrueba', '')}</td>
                        <td>{p.get('Estado', 'Pendiente')}</td>
                        <td style="border-bottom: 1px solid #999;"></td>
                    </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            """

        html += """
        <div class="seccion">
            <p><strong>Observaciones:</strong></p>
            <div style="border: 1px solid #ccc; min-height: 60px; padding: 5px;"></div>
        </div>
        """

        html += self._generar_pie_html(incluir_firma=True, texto_firma='Analista')
        return html

    def RPT_014_pruebas_efectuadas_resultados(self, fecha_desde=None, fecha_hasta=None):
        """
        RPT-014: Pruebas Efectuadas y Resultados
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        if not fecha_desde:
            fecha_desde = date.today()
        if not fecha_hasta:
            fecha_hasta = fecha_desde

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        pruebas = self.db.query(f"""
            SELECT ps.*, pr.NombrePrueba, pr.CodigoPrueba,
                   s.NumeroSolicitud,
                   p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   a.NombreArea
            FROM PruebasSolicitadas ps
            INNER JOIN Pruebas pr ON ps.PruebaID = pr.PruebaID
            INNER JOIN Solicitudes s ON ps.SolicitudID = s.SolicitudID
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            INNER JOIN Areas a ON pr.AreaID = a.AreaID
            WHERE ps.Estado IN ('Completada', 'Validada')
            AND ps.FechaRealizacion >= #{f_desde}# AND ps.FechaRealizacion <= #{f_hasta}#
            ORDER BY a.NombreArea, ps.FechaRealizacion
        """)

        html = self._generar_encabezado_html(
            "PRUEBAS EFECTUADAS Y RESULTADOS",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        html += f"""
        <div class="seccion">
            <p>Total de pruebas realizadas: <strong>{len(pruebas)}</strong></p>
        </div>

        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Solicitud</th>
                        <th>Paciente</th>
                        <th>Area</th>
                        <th>Prueba</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
        """

        for p in pruebas:
            html += f"""
                <tr>
                    <td>{p.get('FechaRealizacion').strftime('%d/%m/%Y') if p.get('FechaRealizacion') else ''}</td>
                    <td>{p.get('NumeroSolicitud', '')}</td>
                    <td>{p.get('NombrePaciente', '')[:20]}</td>
                    <td>{p.get('NombreArea', '')}</td>
                    <td>{p.get('NombrePrueba', '')}</td>
                    <td class="exito">{p.get('Estado', '')}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    # =========================================================================
    # CATEGORIA: INVENTARIO (RPT-015 a RPT-018)
    # =========================================================================

    def RPT_015_inventario_valorado(self, categoria=None):
        """
        RPT-015: Inventario Valorado
        Prioridad: MEDIA | Frecuencia: BAJA - Semanal/Mensual
        """
        where_cat = f" AND p.Categoria = '{categoria}'" if categoria else ""

        try:
            productos = self.db.query(f"""
                SELECT p.*, p.Stock * p.PrecioUnitario as ValorTotal
                FROM Productos p
                WHERE p.Activo = True {where_cat}
                ORDER BY p.Categoria, p.Nombre
            """)
        except:
            productos = []

        html = self._generar_encabezado_html(
            "INVENTARIO VALORADO",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"
        )

        if not productos:
            html += """
            <div class="seccion" style="text-align: center; padding: 30px;">
                <p>No se encontraron productos en el inventario.</p>
            </div>
            """
        else:
            html += """
            <div class="seccion">
                <table>
                    <thead>
                        <tr>
                            <th>Codigo</th>
                            <th>Producto</th>
                            <th>Categoria</th>
                            <th class="text-center">Stock</th>
                            <th class="text-right">P. Unit.</th>
                            <th class="text-right">Valor Total</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            total_valor = 0
            for p in productos:
                valor = p.get('ValorTotal', 0) or 0
                total_valor += valor

                stock = p.get('Stock', 0) or 0
                minimo = p.get('StockMinimo', 0) or 0
                clase_stock = 'alerta' if stock <= minimo else ''

                html += f"""
                    <tr>
                        <td>{p.get('Codigo', '')}</td>
                        <td>{p.get('Nombre', '')}</td>
                        <td>{p.get('Categoria', '')}</td>
                        <td class="text-center {clase_stock}">{stock}</td>
                        <td class="text-right">{p.get('PrecioUnitario', 0) or 0:,.2f}</td>
                        <td class="text-right">{valor:,.2f}</td>
                    </tr>
                """

            html += f"""
                    </tbody>
                    <tfoot>
                        <tr style="font-weight: bold; background: #f0f0f0;">
                            <td colspan="5">VALOR TOTAL DEL INVENTARIO</td>
                            <td class="text-right">$ {total_valor:,.2f}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            """

        html += self._generar_pie_html()
        return html

    def RPT_016_lista_existencias(self, fecha=None):
        """
        RPT-016: Lista de Existencias
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        try:
            productos = self.db.query("""
                SELECT p.*
                FROM Productos p
                WHERE p.Activo = True
                ORDER BY p.Nombre
            """)
        except:
            productos = []

        html = self._generar_encabezado_html(
            "LISTA DE EXISTENCIAS",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"
        )

        html += f"""
        <div class="seccion">
            <p>Total de productos: <strong>{len(productos)}</strong></p>
            <table>
                <thead>
                    <tr>
                        <th>Codigo</th>
                        <th>Descripcion</th>
                        <th class="text-center">Existencia</th>
                        <th class="text-center">Minimo</th>
                        <th>Ubicacion</th>
                    </tr>
                </thead>
                <tbody>
        """

        for p in productos:
            stock = p.get('Stock', 0) or 0
            minimo = p.get('StockMinimo', 0) or 0
            clase = 'alerta' if stock <= minimo else ''

            html += f"""
                <tr>
                    <td>{p.get('Codigo', '')}</td>
                    <td>{p.get('Nombre', '')}</td>
                    <td class="text-center {clase}">{stock}</td>
                    <td class="text-center">{minimo}</td>
                    <td>{p.get('Ubicacion', '')}</td>
                </tr>
            """

        html += """
                </tbody>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_017_movimientos_existencia(self, fecha_desde=None, fecha_hasta=None, producto_id=None):
        """
        RPT-017: Movimientos de Existencia
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        if not fecha_desde:
            fecha_desde = date.today().replace(day=1)
        if not fecha_hasta:
            fecha_hasta = date.today()

        html = self._generar_encabezado_html(
            "MOVIMIENTOS DE EXISTENCIA",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        html += """
        <div class="seccion" style="text-align: center; padding: 30px;">
            <p>Modulo de inventario - Movimientos pendiente de configurar.</p>
            <p>Implemente la tabla MovimientosInventario para habilitar este reporte.</p>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_018_control_minimos(self):
        """
        RPT-018: Control de Minimos
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        try:
            productos = self.db.query("""
                SELECT p.*
                FROM Productos p
                WHERE p.Activo = True AND p.Stock <= p.StockMinimo
                ORDER BY (p.Stock - p.StockMinimo), p.Nombre
            """)
        except:
            productos = []

        html = self._generar_encabezado_html(
            "CONTROL DE MINIMOS - ALERTA DE STOCK",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"
        )

        if not productos:
            html += """
            <div class="seccion exito" style="text-align: center; padding: 30px;">
                <p style="font-size: 14pt;">&#10003; Todos los productos estan por encima del stock minimo.</p>
            </div>
            """
        else:
            html += f"""
            <div class="seccion alerta" style="padding: 10px;">
                <p><strong>&#9888; ATENCION:</strong> {len(productos)} producto(s) requieren reposicion.</p>
            </div>

            <div class="seccion">
                <table>
                    <thead>
                        <tr>
                            <th>Codigo</th>
                            <th>Producto</th>
                            <th class="text-center">Stock Actual</th>
                            <th class="text-center">Stock Minimo</th>
                            <th class="text-center">Diferencia</th>
                            <th>Proveedor</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for p in productos:
                stock = p.get('Stock', 0) or 0
                minimo = p.get('StockMinimo', 0) or 0
                diferencia = stock - minimo

                html += f"""
                    <tr>
                        <td>{p.get('Codigo', '')}</td>
                        <td>{p.get('Nombre', '')}</td>
                        <td class="text-center alerta">{stock}</td>
                        <td class="text-center">{minimo}</td>
                        <td class="text-center alerta">{diferencia}</td>
                        <td>{p.get('Proveedor', '')}</td>
                    </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            """

        html += self._generar_pie_html()
        return html

    # =========================================================================
    # CATEGORIA: CAJA Y FINANZAS (RPT-019 a RPT-021)
    # =========================================================================

    def RPT_019_diario_caja(self, fecha_desde=None, fecha_hasta=None, usuario=None):
        """
        RPT-019: Diario de Caja
        Prioridad: ALTA | Frecuencia: MEDIA - 1-2 por dia
        """
        if not fecha_desde:
            fecha_desde = date.today()
        if not fecha_hasta:
            fecha_hasta = fecha_desde

        f_desde = fecha_desde.strftime('%m/%d/%Y')
        f_hasta = fecha_hasta.strftime('%m/%d/%Y')

        where_usuario = f" AND pg.UsuarioID = {usuario}" if usuario else ""

        pagos = self.db.query(f"""
            SELECT pg.*, f.NumeroFactura,
                   p.Nombres + ' ' + p.Apellidos as NombreCliente
            FROM Pagos pg
            INNER JOIN Facturas f ON pg.FacturaID = f.FacturaID
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE pg.FechaPago >= #{f_desde}# AND pg.FechaPago <= #{f_hasta}#
            {where_usuario}
            ORDER BY pg.FechaPago, pg.PagoID
        """)

        # Agrupar por forma de pago
        por_forma = {}
        total_general = 0

        for pg in pagos:
            forma = pg.get('FormaPago', 'Efectivo')
            monto = pg.get('Monto', 0) or 0

            if forma not in por_forma:
                por_forma[forma] = 0
            por_forma[forma] += monto
            total_general += monto

        html = self._generar_encabezado_html(
            "DIARIO DE CAJA",
            f"Periodo: {fecha_desde.strftime('%d/%m/%Y')} al {fecha_hasta.strftime('%d/%m/%Y')}"
        )

        html += """
        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Recibo</th>
                        <th>Factura</th>
                        <th>Cliente</th>
                        <th>Forma Pago</th>
                        <th class="text-right">Monto</th>
                    </tr>
                </thead>
                <tbody>
        """

        for pg in pagos:
            html += f"""
                <tr>
                    <td>{pg.get('FechaPago').strftime('%d/%m/%Y') if pg.get('FechaPago') else ''}</td>
                    <td>{pg.get('NumeroRecibo', pg.get('PagoID', ''))}</td>
                    <td>{pg.get('NumeroFactura', '')}</td>
                    <td>{pg.get('NombreCliente', '')[:20]}</td>
                    <td>{pg.get('FormaPago', 'Efectivo')}</td>
                    <td class="text-right">{pg.get('Monto', 0) or 0:,.2f}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background: #f0f0f0;">
                        <td colspan="5">TOTAL</td>
                        <td class="text-right">{total_general:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        # Resumen por forma de pago
        html += """
        <div class="seccion">
            <div class="seccion-titulo">RESUMEN POR FORMA DE PAGO</div>
            <table style="width: 50%;">
                <thead>
                    <tr>
                        <th>Forma de Pago</th>
                        <th class="text-right">Total</th>
                    </tr>
                </thead>
                <tbody>
        """

        for forma, total in por_forma.items():
            html += f"""
                <tr>
                    <td>{forma}</td>
                    <td class="text-right">{total:,.2f}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="font-weight: bold; background: #f0f0f0;">
                        <td>TOTAL GENERAL</td>
                        <td class="text-right">{total_general:,.2f}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        html += self._generar_pie_html(incluir_firma=True, texto_firma='Cajero')
        return html

    def RPT_020_saldos_caja(self, fecha=None):
        """
        RPT-020: Saldos de Caja
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        if not fecha:
            fecha = date.today()

        f_str = fecha.strftime('%m/%d/%Y')

        # Obtener saldos
        try:
            saldo_inicial = self.db.query_one(f"""
                SELECT SaldoInicial FROM CierreCaja
                WHERE DATEVALUE(Fecha) = #{f_str}#
            """)
        except:
            saldo_inicial = None

        ingresos = self.db.query_one(f"""
            SELECT SUM(Monto) as TotalIngresos FROM Pagos
            WHERE DATEVALUE(FechaPago) = #{f_str}#
        """)

        html = self._generar_encabezado_html(
            "SALDOS DE CAJA",
            f"Fecha: {fecha.strftime('%d/%m/%Y')}"
        )

        saldo_ini = saldo_inicial.get('SaldoInicial', 0) if saldo_inicial else 0
        total_ingresos = ingresos.get('TotalIngresos', 0) if ingresos and ingresos.get('TotalIngresos') else 0
        saldo_final = saldo_ini + total_ingresos

        html += f"""
        <div class="seccion">
            <table style="width: 60%; margin: 0 auto;">
                <tr>
                    <td style="padding: 10px;">Saldo Inicial:</td>
                    <td class="text-right" style="padding: 10px;">$ {saldo_ini:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Total Ingresos:</td>
                    <td class="text-right exito" style="padding: 10px;">+ $ {total_ingresos:,.2f}</td>
                </tr>
                <tr style="font-weight: bold; font-size: 14pt; background: #f0f0f0;">
                    <td style="padding: 15px;">SALDO FINAL:</td>
                    <td class="text-right" style="padding: 15px;">$ {saldo_final:,.2f}</td>
                </tr>
            </table>
        </div>
        """

        html += self._generar_pie_html(incluir_firma=True, texto_firma='Cajero / Supervisor')
        return html

    def RPT_021_estado_cuentas(self, cliente_id=None):
        """
        RPT-021: Estado de Cuentas V3
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        where_cliente = f" WHERE f.PacienteID = {cliente_id}" if cliente_id else ""

        cuentas = self.db.query(f"""
            SELECT f.*, p.Nombres + ' ' + p.Apellidos as NombreCliente,
                   p.NumeroDocumento,
                   (SELECT SUM(Monto) FROM Pagos WHERE FacturaID = f.FacturaID) as TotalPagado
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            {where_cliente}
            AND f.Anulada = False
            ORDER BY p.Apellidos, p.Nombres, f.FechaEmision
        """)

        html = self._generar_encabezado_html(
            "ESTADO DE CUENTAS",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y')}"
        )

        # Agrupar por cliente
        por_cliente = {}
        for c in cuentas:
            cliente = c.get('NombreCliente', 'Sin Nombre')
            if cliente not in por_cliente:
                por_cliente[cliente] = {
                    'documento': c.get('NumeroDocumento', ''),
                    'facturas': []
                }
            por_cliente[cliente]['facturas'].append(c)

        total_facturado = 0
        total_pagado = 0
        total_pendiente = 0

        for cliente, datos in por_cliente.items():
            html += f"""
            <div class="seccion">
                <div class="seccion-titulo">{cliente} - {datos['documento']}</div>
                <table>
                    <thead>
                        <tr>
                            <th>Factura</th>
                            <th>Fecha</th>
                            <th class="text-right">Total</th>
                            <th class="text-right">Pagado</th>
                            <th class="text-right">Pendiente</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            subtotal_fact = 0
            subtotal_pag = 0
            subtotal_pend = 0

            for f in datos['facturas']:
                total_f = f.get('MontoTotal', 0) or 0
                pagado_f = f.get('TotalPagado', 0) or 0
                pendiente_f = total_f - pagado_f

                subtotal_fact += total_f
                subtotal_pag += pagado_f
                subtotal_pend += pendiente_f

                clase_pend = 'alerta' if pendiente_f > 0 else 'exito'

                html += f"""
                    <tr>
                        <td>{f.get('NumeroFactura', '')}</td>
                        <td>{f.get('FechaEmision').strftime('%d/%m/%Y') if f.get('FechaEmision') else ''}</td>
                        <td class="text-right">{total_f:,.2f}</td>
                        <td class="text-right">{pagado_f:,.2f}</td>
                        <td class="text-right {clase_pend}">{pendiente_f:,.2f}</td>
                    </tr>
                """

            total_facturado += subtotal_fact
            total_pagado += subtotal_pag
            total_pendiente += subtotal_pend

            html += f"""
                    </tbody>
                    <tfoot>
                        <tr style="font-weight: bold; background: #f8f8f8;">
                            <td colspan="2">Subtotal {cliente[:15]}...</td>
                            <td class="text-right">{subtotal_fact:,.2f}</td>
                            <td class="text-right">{subtotal_pag:,.2f}</td>
                            <td class="text-right">{subtotal_pend:,.2f}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>
            """

        # Totales generales
        html += f"""
        <div class="totales-box">
            <div class="total-fila">
                <span>Total Facturado:</span>
                <span>$ {total_facturado:,.2f}</span>
            </div>
            <div class="total-fila">
                <span>Total Pagado:</span>
                <span>$ {total_pagado:,.2f}</span>
            </div>
            <div class="total-fila total-final alerta">
                <span>TOTAL PENDIENTE:</span>
                <span>$ {total_pendiente:,.2f}</span>
            </div>
        </div>
        """

        html += self._generar_pie_html()
        return html

    # =========================================================================
    # CATEGORIA: CATALOGOS (RPT-022 a RPT-024)
    # =========================================================================

    def RPT_022_lista_precios(self, codigo_lista=None):
        """
        RPT-022: Lista de Precios
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        pruebas = self.db.query("""
            SELECT p.*, a.NombreArea
            FROM Pruebas p
            INNER JOIN Areas a ON p.AreaID = a.AreaID
            WHERE p.Activo = True
            ORDER BY a.Secuencia, p.NombrePrueba
        """)

        html = self._generar_encabezado_html(
            "LISTA DE PRECIOS",
            f"Vigente desde: {datetime.now().strftime('%d/%m/%Y')}"
        )

        # Agrupar por area
        por_area = {}
        for p in pruebas:
            area = p.get('NombreArea', 'General')
            if area not in por_area:
                por_area[area] = []
            por_area[area].append(p)

        for area, lista in por_area.items():
            html += f"""
            <div class="seccion">
                <div class="seccion-titulo">{area}</div>
                <table>
                    <thead>
                        <tr>
                            <th>Codigo</th>
                            <th>Descripcion</th>
                            <th class="text-right">Precio</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            for p in lista:
                html += f"""
                    <tr>
                        <td>{p.get('CodigoPrueba', '')}</td>
                        <td>{p.get('NombrePrueba', '')}</td>
                        <td class="text-right">$ {p.get('PrecioBase', 0) or 0:,.2f}</td>
                    </tr>
                """

            html += """
                    </tbody>
                </table>
            </div>
            """

        html += """
        <div class="seccion" style="font-size: 8pt; color: #666;">
            <p>* Precios sujetos a cambios sin previo aviso</p>
            <p>* IVA no incluido</p>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_023_lista_pruebas(self, codigo_area=None, estado=None):
        """
        RPT-023: Lista de Pruebas
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        where_area = f" AND a.CodigoArea = '{codigo_area}'" if codigo_area else ""
        where_estado = " AND p.Activo = True" if estado != 'todos' else ""

        pruebas = self.db.query(f"""
            SELECT p.*, a.NombreArea, a.CodigoArea,
                   (SELECT COUNT(*) FROM ParametrosPrueba WHERE PruebaID = p.PruebaID) as NumParametros
            FROM Pruebas p
            INNER JOIN Areas a ON p.AreaID = a.AreaID
            WHERE 1=1 {where_area} {where_estado}
            ORDER BY a.Secuencia, p.NombrePrueba
        """)

        html = self._generar_encabezado_html(
            "LISTA DE PRUEBAS",
            f"Total: {len(pruebas)} pruebas"
        )

        html += """
        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>Codigo</th>
                        <th>Nombre de la Prueba</th>
                        <th>Area</th>
                        <th class="text-center">Params.</th>
                        <th class="text-center">Estado</th>
                    </tr>
                </thead>
                <tbody>
        """

        for p in pruebas:
            estado_text = 'Activa' if p.get('Activo', True) else 'Inactiva'
            estado_class = 'exito' if p.get('Activo', True) else ''

            html += f"""
                <tr>
                    <td>{p.get('CodigoPrueba', '')}</td>
                    <td>{p.get('NombrePrueba', '')}</td>
                    <td>{p.get('NombreArea', '')}</td>
                    <td class="text-center">{p.get('NumParametros', 0)}</td>
                    <td class="text-center {estado_class}">{estado_text}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="background: #f0f0f0;">
                        <td colspan="5">Total de registros: {len(pruebas)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    def RPT_024_lista_pacientes(self, filtro_nombre=None, filtro_codigo=None):
        """
        RPT-024: Lista de Pacientes
        Prioridad: MEDIA | Frecuencia: MEDIA
        """
        where_clauses = ["Activo = True"]

        if filtro_nombre:
            where_clauses.append(f"(Nombres LIKE '%{filtro_nombre}%' OR Apellidos LIKE '%{filtro_nombre}%')")
        if filtro_codigo:
            where_clauses.append(f"NumeroDocumento LIKE '%{filtro_codigo}%'")

        where_sql = " AND ".join(where_clauses)

        pacientes = self.db.query(f"""
            SELECT p.*,
                   (SELECT COUNT(*) FROM Solicitudes WHERE PacienteID = p.PacienteID) as TotalSolicitudes,
                   (SELECT MAX(FechaSolicitud) FROM Solicitudes WHERE PacienteID = p.PacienteID) as UltimaVisita
            FROM Pacientes p
            WHERE {where_sql}
            ORDER BY p.Apellidos, p.Nombres
        """)

        html = self._generar_encabezado_html(
            "LISTA DE PACIENTES",
            f"Total: {len(pacientes)} pacientes"
        )

        html += """
        <div class="seccion">
            <table>
                <thead>
                    <tr>
                        <th>Cedula</th>
                        <th>Nombre Completo</th>
                        <th class="text-center">Edad</th>
                        <th>Telefono</th>
                        <th class="text-center">Visitas</th>
                        <th>Ultima Visita</th>
                    </tr>
                </thead>
                <tbody>
        """

        for p in pacientes:
            nombre_completo = f"{p.get('Apellidos', '')} {p.get('Nombres', '')}"
            ultima = p.get('UltimaVisita')
            ultima_str = ultima.strftime('%d/%m/%Y') if ultima else 'Nunca'

            html += f"""
                <tr>
                    <td>{p.get('NumeroDocumento', '')}</td>
                    <td>{nombre_completo}</td>
                    <td class="text-center">{p.get('Edad', '')}</td>
                    <td>{p.get('Telefono', '')}</td>
                    <td class="text-center">{p.get('TotalSolicitudes', 0)}</td>
                    <td>{ultima_str}</td>
                </tr>
            """

        html += f"""
                </tbody>
                <tfoot>
                    <tr style="background: #f0f0f0;">
                        <td colspan="6">Total de registros: {len(pacientes)}</td>
                    </tr>
                </tfoot>
            </table>
        </div>
        """

        html += self._generar_pie_html()
        return html

    # =========================================================================
    # UTILIDADES
    # =========================================================================

    def _numero_a_letras(self, numero):
        """Convierte un numero a texto en espanol"""
        unidades = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
        decenas = ['', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
        especiales = {11: 'once', 12: 'doce', 13: 'trece', 14: 'catorce', 15: 'quince',
                      16: 'dieciseis', 17: 'diecisiete', 18: 'dieciocho', 19: 'diecinueve'}

        try:
            n = int(numero)
            if n == 0:
                return 'cero'
            if n < 10:
                return unidades[n]
            if n < 20:
                return especiales.get(n, decenas[1] + ('y ' + unidades[n % 10] if n % 10 else ''))
            if n < 100:
                return decenas[n // 10] + (' y ' + unidades[n % 10] if n % 10 else '')
            if n < 1000:
                return ('cien' if n == 100 else 'ciento ' if n < 200 else unidades[n // 100] + 'cientos ') + self._numero_a_letras(n % 100)
            if n < 1000000:
                miles = n // 1000
                resto = n % 1000
                if miles == 1:
                    return 'mil ' + self._numero_a_letras(resto)
                return self._numero_a_letras(miles) + ' mil ' + self._numero_a_letras(resto)
            return str(numero)
        except:
            return str(numero)


# ============================================================================
# CATALOGO DE REPORTES
# ============================================================================

CATALOGO_REPORTES_ESPECIFICACIONES = {
    # Facturacion y Ventas
    'RPT-001': {'nombre': 'Factura - Completa', 'metodo': 'RPT_001_factura_completa', 'categoria': 'Facturacion', 'prioridad': 'CRITICA'},
    'RPT-002': {'nombre': 'Diario de Facturacion', 'metodo': 'RPT_002_diario_facturacion', 'categoria': 'Facturacion', 'prioridad': 'CRITICA'},
    'RPT-003': {'nombre': 'Recibo de Caja', 'metodo': 'RPT_003_recibo_caja', 'categoria': 'Facturacion', 'prioridad': 'CRITICA'},
    'RPT-004': {'nombre': 'Relacion de Facturas', 'metodo': 'RPT_004_relacion_facturas', 'categoria': 'Facturacion', 'prioridad': 'CRITICA'},
    'RPT-005': {'nombre': 'Resumen de Facturacion', 'metodo': 'RPT_005_resumen_facturacion', 'categoria': 'Facturacion', 'prioridad': 'CRITICA'},
    'RPT-006': {'nombre': 'Libro de Ventas', 'metodo': 'RPT_006_libro_ventas', 'categoria': 'Facturacion', 'prioridad': 'ALTA'},

    # Solicitudes y Gestion
    'RPT-007': {'nombre': 'Comprobante Solicitud', 'metodo': 'RPT_007_comprobante_solicitud', 'categoria': 'Solicitudes', 'prioridad': 'CRITICA'},
    'RPT-008': {'nombre': 'Relacion de Solicitudes', 'metodo': 'RPT_008_relacion_solicitudes', 'categoria': 'Solicitudes', 'prioridad': 'CRITICA'},
    'RPT-009': {'nombre': 'Pruebas por Efectuar', 'metodo': 'RPT_009_pruebas_por_efectuar', 'categoria': 'Solicitudes', 'prioridad': 'MEDIA'},
    'RPT-010': {'nombre': 'Auditoria Solicitudes', 'metodo': 'RPT_010_auditoria_solicitudes', 'categoria': 'Solicitudes', 'prioridad': 'CRITICA'},

    # Resultados y Boletas
    'RPT-011': {'nombre': 'Boleta - Principal', 'metodo': 'RPT_011_boleta_principal', 'categoria': 'Resultados', 'prioridad': 'CRITICA'},
    'RPT-012': {'nombre': 'Boletas por Entregar', 'metodo': 'RPT_012_boletas_por_entregar', 'categoria': 'Resultados', 'prioridad': 'CRITICA'},
    'RPT-013': {'nombre': 'HDT por Solicitud - Master', 'metodo': 'RPT_013_hdt_solicitud_master', 'categoria': 'Resultados', 'prioridad': 'CRITICA'},
    'RPT-014': {'nombre': 'Pruebas Efectuadas y Resultados', 'metodo': 'RPT_014_pruebas_efectuadas_resultados', 'categoria': 'Resultados', 'prioridad': 'MEDIA'},

    # Inventario
    'RPT-015': {'nombre': 'Inventario Valorado', 'metodo': 'RPT_015_inventario_valorado', 'categoria': 'Inventario', 'prioridad': 'MEDIA'},
    'RPT-016': {'nombre': 'Lista de Existencias', 'metodo': 'RPT_016_lista_existencias', 'categoria': 'Inventario', 'prioridad': 'MEDIA'},
    'RPT-017': {'nombre': 'Movimientos de Existencia', 'metodo': 'RPT_017_movimientos_existencia', 'categoria': 'Inventario', 'prioridad': 'MEDIA'},
    'RPT-018': {'nombre': 'Control de Minimos', 'metodo': 'RPT_018_control_minimos', 'categoria': 'Inventario', 'prioridad': 'MEDIA'},

    # Caja y Finanzas
    'RPT-019': {'nombre': 'Diario de Caja', 'metodo': 'RPT_019_diario_caja', 'categoria': 'Caja', 'prioridad': 'ALTA'},
    'RPT-020': {'nombre': 'Saldos de Caja', 'metodo': 'RPT_020_saldos_caja', 'categoria': 'Caja', 'prioridad': 'MEDIA'},
    'RPT-021': {'nombre': 'Estado de Cuentas V3', 'metodo': 'RPT_021_estado_cuentas', 'categoria': 'Caja', 'prioridad': 'MEDIA'},

    # Catalogos
    'RPT-022': {'nombre': 'Lista de Precios', 'metodo': 'RPT_022_lista_precios', 'categoria': 'Catalogos', 'prioridad': 'MEDIA'},
    'RPT-023': {'nombre': 'Lista de Pruebas', 'metodo': 'RPT_023_lista_pruebas', 'categoria': 'Catalogos', 'prioridad': 'MEDIA'},
    'RPT-024': {'nombre': 'Lista de Pacientes', 'metodo': 'RPT_024_lista_pacientes', 'categoria': 'Catalogos', 'prioridad': 'MEDIA'},
}


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("MODULO DE REPORTES - ESPECIFICACIONES TECNICAS ANgesLAB")
    print("=" * 70)
    print(f"\nTotal de reportes implementados: {len(CATALOGO_REPORTES_ESPECIFICACIONES)}")
    print("\nReportes por categoria:")

    categorias = {}
    for codigo, info in CATALOGO_REPORTES_ESPECIFICACIONES.items():
        cat = info['categoria']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append((codigo, info['nombre'], info['prioridad']))

    for cat, reportes in categorias.items():
        print(f"\n{cat}:")
        for codigo, nombre, prioridad in reportes:
            print(f"  {codigo}: {nombre} [{prioridad}]")

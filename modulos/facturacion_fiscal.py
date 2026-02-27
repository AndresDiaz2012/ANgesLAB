"""
================================================================================
MODULO DE FACTURACION FISCAL - ANgesLAB
================================================================================
Modulo de facturacion adaptado a normativas fiscales venezolanas:
- Control de numeracion de facturas
- Manejo de IVA segun normativa vigente
- Soporte para exoneraciones
- Generacion de reportes fiscales
- Libro de ventas

Normativas aplicadas:
- Providencia SNAT/2011/0071 (Facturacion)
- Ley de IVA vigente
- Codigo de Comercio

Autor: Sistema ANgesLAB
================================================================================
"""

from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import os

# ============================================================================
# CONFIGURACION FISCAL
# ============================================================================

class ConfiguracionFiscal:
    """Configuracion fiscal del sistema"""

    # Tasas de IVA vigentes (actualizar segun normativa)
    TASA_IVA_GENERAL = Decimal('16.00')      # 16% General
    TASA_IVA_REDUCIDA = Decimal('8.00')       # 8% Reducida
    TASA_IVA_SUNTUARIA = Decimal('31.00')     # 31% Productos suntuarios
    TASA_IVA_EXENTO = Decimal('0.00')         # 0% Exento

    # Servicios de laboratorio (segun normativa pueden estar exentos o con tasa reducida)
    TASA_IVA_LABORATORIO = Decimal('16.00')   # Servicios de laboratorio

    # Formatos de numeracion
    FORMATO_FACTURA = "FAC-{YYYY}-{NNNNNN}"           # FAC-2024-000001
    FORMATO_NOTA_CREDITO = "NC-{YYYY}-{NNNNNN}"       # NC-2024-000001
    FORMATO_NOTA_DEBITO = "ND-{YYYY}-{NNNNNN}"        # ND-2024-000001

    # Datos del contribuyente (deben configurarse desde el sistema)
    @staticmethod
    def cargar_datos_contribuyente(db):
        """Carga los datos del contribuyente desde la configuracion"""
        # Intentar ConfiguracionLaboratorio primero (tabla principal)
        config = None
        try:
            config = db.query_one("SELECT * FROM ConfiguracionLaboratorio")
        except:
            pass
        if not config:
            config = db.query_one("SELECT * FROM ConfiguracionSistema")
        return {
            'nombre': config.get('NombreLaboratorio', 'LABORATORIO') if config else 'LABORATORIO',
            'rif': (config.get('RIF') or '') if config else '',
            'direccion': (config.get('Direccion') or '') if config else '',
            'telefono': (config.get('Telefono1') or config.get('Telefono') or '') if config else '',
            'whatsapp': (config.get('WhatsApp') or '') if config else '',
            'email': (config.get('Email') or '') if config else '',
            'tasa_iva': Decimal(str(config.get('TasaIVALaboratorio') or config.get('IVAPorDefecto') or 16)) if config else Decimal('16')
        }


# ============================================================================
# CLASE PRINCIPAL DE FACTURACION
# ============================================================================

class FacturacionFiscal:
    """
    Maneja la facturacion conforme a normativas fiscales
    """

    def __init__(self, db):
        self.db = db
        self.config = ConfiguracionFiscal.cargar_datos_contribuyente(db)

    # -------------------------------------------------------------------------
    # GENERACION DE NUMEROS DE DOCUMENTO
    # -------------------------------------------------------------------------

    def generar_numero_factura(self):
        """Genera el siguiente numero de factura secuencial"""
        anio = datetime.now().year

        # Obtener ultima factura del anio
        result = self.db.query_one(f"""
            SELECT MAX(NumeroFactura) as Ultimo
            FROM Facturas
            WHERE NumeroFactura LIKE 'FAC-{anio}-%'
        """)

        if result and result['Ultimo']:
            # Extraer numero y incrementar
            try:
                ultimo = result['Ultimo']
                numero = int(ultimo.split('-')[-1]) + 1
            except:
                numero = 1
        else:
            numero = 1

        return f"FAC-{anio}-{numero:06d}"

    def generar_numero_control(self):
        """
        Genera numero de control fiscal
        Segun normativa: 00-NNNNNNNN
        """
        anio = datetime.now().year

        result = self.db.query_one(f"""
            SELECT MAX(NumeroControl) as Ultimo
            FROM Facturas
            WHERE NumeroControl IS NOT NULL
            AND YEAR(FechaEmision) = {anio}
        """)

        if result and result['Ultimo']:
            try:
                numero = int(result['Ultimo'].replace('-', '')) + 1
            except:
                numero = 1
        else:
            numero = 1

        return f"00-{numero:08d}"

    # -------------------------------------------------------------------------
    # CALCULOS FISCALES
    # -------------------------------------------------------------------------

    def calcular_iva(self, base_imponible, tasa_iva=None):
        """
        Calcula el IVA sobre la base imponible
        Retorna: (monto_iva, total_con_iva)
        """
        if tasa_iva is None:
            tasa_iva = self.config['tasa_iva']

        base = Decimal(str(base_imponible))
        tasa = Decimal(str(tasa_iva))

        monto_iva = (base * tasa / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        total = base + monto_iva

        return float(monto_iva), float(total)

    def calcular_totales_factura(self, detalles, descuento_porcentaje=0, es_exonerada=False):
        """
        Calcula todos los totales de una factura

        Parametros:
        - detalles: lista de dict con {precio, cantidad, descuento}
        - descuento_porcentaje: descuento global sobre el subtotal
        - es_exonerada: si la factura esta exonerada de IVA

        Retorna: dict con todos los montos calculados
        """
        # Calcular subtotal
        subtotal = Decimal('0.00')
        for item in detalles:
            precio = Decimal(str(item.get('precio', 0)))
            cantidad = Decimal(str(item.get('cantidad', 1)))
            desc_item = Decimal(str(item.get('descuento', 0)))

            monto_item = (precio * cantidad) - desc_item
            subtotal += monto_item

        # Aplicar descuento global
        descuento = Decimal(str(descuento_porcentaje))
        monto_descuento = (subtotal * descuento / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        base_imponible = subtotal - monto_descuento

        # Calcular IVA
        if es_exonerada:
            monto_iva = Decimal('0.00')
            monto_exento = base_imponible
            base_imponible_iva = Decimal('0.00')
        else:
            tasa = self.config['tasa_iva']
            monto_iva = (base_imponible * tasa / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
            monto_exento = Decimal('0.00')
            base_imponible_iva = base_imponible

        # Total
        total = base_imponible + monto_iva

        return {
            'subtotal': float(subtotal),
            'monto_descuento': float(monto_descuento),
            'porcentaje_descuento': float(descuento),
            'base_imponible': float(base_imponible_iva),
            'monto_exento': float(monto_exento),
            'tasa_iva': float(self.config['tasa_iva']),
            'monto_iva': float(monto_iva),
            'total': float(total)
        }

    # -------------------------------------------------------------------------
    # CREACION DE FACTURAS
    # -------------------------------------------------------------------------

    def crear_factura(self, datos_factura, detalles, usuario_id):
        """
        Crea una factura completa con todos sus detalles

        Parametros:
        - datos_factura: dict con datos de la factura
        - detalles: lista de pruebas/items a facturar
        - usuario_id: ID del usuario que crea la factura

        Retorna: ID de la factura creada
        """
        # Generar numeros
        numero_factura = self.generar_numero_factura()
        numero_control = self.generar_numero_control()

        # Calcular totales
        descuento = datos_factura.get('descuento_porcentaje', 0)
        es_exonerada = datos_factura.get('es_exonerada', False)
        totales = self.calcular_totales_factura(detalles, descuento, es_exonerada)

        # Insertar factura
        factura_data = {
            'NumeroFactura': numero_factura,
            'NumeroControl': numero_control,
            'FechaEmision': datetime.now(),
            'PacienteID': datos_factura['paciente_id'],
            'ResponsablePagoID': datos_factura.get('responsable_id'),
            'SolicitudID': datos_factura.get('solicitud_id'),
            'TipoFactura': datos_factura.get('tipo', 'Contado'),
            'CondicionPago': datos_factura.get('condicion_pago', 'Contado'),

            # Totales
            'SubTotal': totales['subtotal'],
            'MontoDescuento': totales['monto_descuento'],
            'PorcentajeDescuento': totales['porcentaje_descuento'],
            'BaseImponible': totales['base_imponible'],
            'TasaIVA': totales['tasa_iva'],
            'MontoIVA': totales['monto_iva'],
            'MontoExento': totales['monto_exento'],
            'MontoTotal': totales['total'],

            # Estado
            'EstadoPago': 'Pendiente',
            'MontoCobrado': 0,
            'SaldoPendiente': totales['total'],

            # Exoneracion
            'EstaExonerada': es_exonerada,
            'NumeroExoneracion': datos_factura.get('numero_exoneracion'),
            'FechaExoneracion': datos_factura.get('fecha_exoneracion'),

            # Observaciones
            'Observaciones': datos_factura.get('observaciones', ''),

            # Auditoria
            'UsuarioEmite': usuario_id,
            'FechaRegistro': datetime.now()
        }

        self.db.insert('Facturas', factura_data)

        # Obtener ID de la factura recien creada
        factura_id = self.db.query_one(
            f"SELECT MAX(FacturaID) as ID FROM Facturas WHERE NumeroFactura='{numero_factura}'"
        )['ID']

        # Insertar detalles
        for item in detalles:
            precio = Decimal(str(item.get('precio', 0)))
            cantidad = Decimal(str(item.get('cantidad', 1)))
            desc = Decimal(str(item.get('descuento', 0)))

            subtotal_item = (precio * cantidad) - desc

            if es_exonerada:
                iva_item = 0
            else:
                iva_item = float((subtotal_item * self.config['tasa_iva'] / 100).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP
                ))

            detalle_data = {
                'FacturaID': factura_id,
                'PruebaID': item['prueba_id'],
                'Descripcion': item.get('descripcion', ''),
                'Cantidad': int(cantidad),
                'PrecioUnitario': float(precio),
                'Descuento': float(desc),
                'SubTotal': float(subtotal_item),
                'MontoIVA': iva_item,
                'Total': float(subtotal_item) + iva_item,
                'Exonerada': es_exonerada
            }

            self.db.insert('DetalleFacturas', detalle_data)

        # Log de auditoria
        self._registrar_auditoria(usuario_id, 'INSERT', 'Facturas', factura_id,
                                  f"Factura {numero_factura} creada")

        return factura_id, numero_factura

    # -------------------------------------------------------------------------
    # ANULACION DE FACTURAS
    # -------------------------------------------------------------------------

    def anular_factura(self, factura_id, motivo, usuario_id):
        """
        Anula una factura (segun normativa, las facturas no se eliminan)

        Parametros:
        - factura_id: ID de la factura a anular
        - motivo: motivo de la anulacion
        - usuario_id: usuario que anula
        """
        # Verificar que la factura existe y no esta anulada
        factura = self.db.query_one(f"SELECT * FROM Facturas WHERE FacturaID={factura_id}")

        if not factura:
            raise ValueError("Factura no encontrada")

        if factura.get('Anulada'):
            raise ValueError("La factura ya esta anulada")

        # Verificar que no tenga cobros (si los tiene, hay que anularlos primero)
        cobros = self.db.query(f"SELECT * FROM Cobros WHERE FacturaID={factura_id} AND Anulado=False")
        if cobros:
            raise ValueError("La factura tiene cobros activos. Anulelos primero.")

        # Anular factura
        self.db.update('Facturas', {
            'Anulada': True,
            'MotivoAnulacion': motivo,
            'FechaAnulacion': datetime.now(),
            'EstadoPago': 'Anulada'
        }, f"FacturaID={factura_id}")

        # Log de auditoria
        self._registrar_auditoria(usuario_id, 'ANULAR', 'Facturas', factura_id,
                                  f"Factura {factura['NumeroFactura']} anulada: {motivo}")

    # -------------------------------------------------------------------------
    # COBROS
    # -------------------------------------------------------------------------

    def registrar_cobro(self, datos_cobro, usuario_id):
        """
        Registra un cobro/pago de factura

        Parametros:
        - datos_cobro: dict con datos del cobro
        - usuario_id: usuario que registra
        """
        factura_id = datos_cobro['factura_id']

        # Obtener factura
        factura = self.db.query_one(f"SELECT * FROM Facturas WHERE FacturaID={factura_id}")
        if not factura:
            raise ValueError("Factura no encontrada")

        if factura.get('Anulada'):
            raise ValueError("No se puede cobrar una factura anulada")

        monto_cobro = Decimal(str(datos_cobro['monto']))
        saldo_actual = Decimal(str(factura.get('SaldoPendiente', 0)))

        if monto_cobro > saldo_actual:
            raise ValueError(f"El monto excede el saldo pendiente ({saldo_actual})")

        # Generar numero de cobro
        anio = datetime.now().year
        result = self.db.query_one(f"SELECT COUNT(*)+1 as Num FROM Cobros WHERE YEAR(FechaCobro)={anio}")
        numero_cobro = f"COB-{anio}-{result['Num']:06d}"

        # Insertar cobro
        cobro_data = {
            'NumeroCobro': numero_cobro,
            'FechaCobro': datetime.now(),
            'FacturaID': factura_id,
            'MontoCobrado': float(monto_cobro),
            'FormaPagoID': datos_cobro['forma_pago_id'],
            'BancoID': datos_cobro.get('banco_id'),
            'CuentaBancariaID': datos_cobro.get('cuenta_id'),
            'NumeroReferencia': datos_cobro.get('referencia', ''),
            'NumeroCheque': datos_cobro.get('numero_cheque', ''),
            'Observaciones': datos_cobro.get('observaciones', ''),
            'UsuarioRegistro': usuario_id,
            'FechaRegistro': datetime.now()
        }

        self.db.insert('Cobros', cobro_data)

        # Actualizar factura
        nuevo_cobrado = Decimal(str(factura.get('MontoCobrado', 0))) + monto_cobro
        nuevo_saldo = saldo_actual - monto_cobro

        # Determinar nuevo estado
        if nuevo_saldo <= 0:
            nuevo_estado = 'Pagada'
        elif nuevo_cobrado > 0:
            nuevo_estado = 'Parcial'
        else:
            nuevo_estado = 'Pendiente'

        self.db.update('Facturas', {
            'MontoCobrado': float(nuevo_cobrado),
            'SaldoPendiente': float(nuevo_saldo),
            'EstadoPago': nuevo_estado
        }, f"FacturaID={factura_id}")

        # Log de auditoria
        self._registrar_auditoria(usuario_id, 'INSERT', 'Cobros', None,
                                  f"Cobro {numero_cobro} de {monto_cobro} a factura {factura['NumeroFactura']}")

        return numero_cobro

    # -------------------------------------------------------------------------
    # REPORTES FISCALES
    # -------------------------------------------------------------------------

    def generar_libro_ventas(self, fecha_desde, fecha_hasta):
        """
        Genera el libro de ventas para el periodo indicado
        Segun formato SENIAT

        Retorna: lista de registros del libro de ventas
        """
        facturas = self.db.query(f"""
            SELECT
                f.NumeroFactura,
                f.NumeroControl,
                f.FechaEmision,
                p.NumeroDocumento as RIFCliente,
                p.Nombres + ' ' + p.Apellidos as NombreCliente,
                f.TipoFactura,
                f.BaseImponible,
                f.TasaIVA,
                f.MontoIVA,
                f.MontoExento,
                f.MontoTotal,
                f.Anulada
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE f.FechaEmision BETWEEN #{fecha_desde.strftime('%m/%d/%Y')}#
                AND #{fecha_hasta.strftime('%m/%d/%Y')}#
            ORDER BY f.FechaEmision, f.NumeroFactura
        """)

        libro = []
        for f in facturas:
            registro = {
                'fecha': f['FechaEmision'],
                'numero_factura': f['NumeroFactura'],
                'numero_control': f['NumeroControl'],
                'rif_cliente': f['RIFCliente'] or 'SIN RIF',
                'nombre_cliente': f['NombreCliente'],
                'tipo_operacion': 'VENTA' if not f['Anulada'] else 'ANULADA',
                'base_imponible': f['BaseImponible'] or 0,
                'alicuota': f['TasaIVA'] or 0,
                'impuesto': f['MontoIVA'] or 0,
                'exento': f['MontoExento'] or 0,
                'total': f['MontoTotal'] if not f['Anulada'] else 0
            }
            libro.append(registro)

        return libro

    def resumen_fiscal_periodo(self, fecha_desde, fecha_hasta):
        """
        Genera resumen fiscal del periodo

        Retorna: dict con totales del periodo
        """
        result = self.db.query_one(f"""
            SELECT
                COUNT(*) as TotalFacturas,
                SUM(CASE WHEN Anulada=False THEN 1 ELSE 0 END) as FacturasActivas,
                SUM(CASE WHEN Anulada=True THEN 1 ELSE 0 END) as FacturasAnuladas,
                SUM(CASE WHEN Anulada=False THEN BaseImponible ELSE 0 END) as TotalBaseImponible,
                SUM(CASE WHEN Anulada=False THEN MontoIVA ELSE 0 END) as TotalIVA,
                SUM(CASE WHEN Anulada=False THEN MontoExento ELSE 0 END) as TotalExento,
                SUM(CASE WHEN Anulada=False THEN MontoTotal ELSE 0 END) as TotalVentas,
                SUM(CASE WHEN Anulada=False THEN MontoCobrado ELSE 0 END) as TotalCobrado
            FROM Facturas
            WHERE FechaEmision BETWEEN #{fecha_desde.strftime('%m/%d/%Y')}#
                AND #{fecha_hasta.strftime('%m/%d/%Y')}#
        """)

        return {
            'periodo_desde': fecha_desde,
            'periodo_hasta': fecha_hasta,
            'total_facturas': result['TotalFacturas'] or 0,
            'facturas_activas': result['FacturasActivas'] or 0,
            'facturas_anuladas': result['FacturasAnuladas'] or 0,
            'base_imponible': result['TotalBaseImponible'] or 0,
            'total_iva': result['TotalIVA'] or 0,
            'total_exento': result['TotalExento'] or 0,
            'total_ventas': result['TotalVentas'] or 0,
            'total_cobrado': result['TotalCobrado'] or 0,
            'por_cobrar': (result['TotalVentas'] or 0) - (result['TotalCobrado'] or 0)
        }

    # -------------------------------------------------------------------------
    # AUDITORIA
    # -------------------------------------------------------------------------

    def _registrar_auditoria(self, usuario_id, accion, tabla, registro_id, detalle):
        """Registra una entrada en el log de auditoria"""
        try:
            self.db.insert('LogAuditoria', {
                'FechaHora': datetime.now(),
                'UsuarioID': usuario_id,
                'Accion': accion,
                'Tabla': tabla,
                'RegistroID': registro_id,
                'ValorNuevo': detalle
            })
        except:
            pass  # No fallar si no se puede registrar auditoria


# ============================================================================
# FUNCIONES DE VALIDACION FISCAL
# ============================================================================

def validar_rif(rif):
    """
    Valida formato de RIF venezolano
    Formatos validos: V-12345678-9, J-12345678-9, G-12345678-9, etc.
    """
    import re
    patron = r'^[VJGEP]-\d{8}-\d$'
    return bool(re.match(patron, rif.upper()))

def validar_cedula(cedula):
    """
    Valida formato de cedula venezolana
    Formatos validos: V-12345678, E-12345678
    """
    import re
    patron = r'^[VE]-?\d{6,8}$'
    return bool(re.match(patron, cedula.upper().replace('.', '')))

def formatear_monto(monto, simbolo='Bs.'):
    """Formatea un monto con separadores de miles"""
    return f"{simbolo} {monto:,.2f}"

def monto_en_letras(monto):
    """Convierte un monto a letras (para facturas)"""
    # Implementacion basica
    unidades = ['', 'un', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve']
    decenas = ['', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa']
    especiales = ['diez', 'once', 'doce', 'trece', 'catorce', 'quince']

    parte_entera = int(monto)
    centavos = int(round((monto - parte_entera) * 100))

    # Conversion basica (hasta 999)
    def convertir_centenas(n):
        if n == 0:
            return 'cero'
        if n < 10:
            return unidades[n]
        if n < 16:
            return especiales[n - 10]
        if n < 20:
            return f'dieci{unidades[n - 10]}'
        if n < 100:
            d, u = divmod(n, 10)
            if u == 0:
                return decenas[d]
            if d == 2:
                return f'veinti{unidades[u]}'
            return f'{decenas[d]} y {unidades[u]}'
        c, resto = divmod(n, 100)
        if c == 1:
            if resto == 0:
                return 'cien'
            return f'ciento {convertir_centenas(resto)}'
        centenas_txt = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos',
                       'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos']
        if resto == 0:
            return centenas_txt[c]
        return f'{centenas_txt[c]} {convertir_centenas(resto)}'

    resultado = convertir_centenas(parte_entera)
    if centavos > 0:
        resultado += f' con {centavos:02d}/100'

    return resultado.upper() + ' BOLIVARES'


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("Modulo de Facturacion Fiscal - ANgesLAB")
    print("=" * 50)

    # Ejemplo de calculos
    config = ConfiguracionFiscal()
    print(f"Tasa IVA General: {config.TASA_IVA_GENERAL}%")
    print(f"Tasa IVA Laboratorio: {config.TASA_IVA_LABORATORIO}%")

    # Ejemplo de monto en letras
    print(f"\n123.45 = {monto_en_letras(123.45)}")
    print(f"1000.00 = {monto_en_letras(1000.00)}")

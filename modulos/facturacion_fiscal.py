"""
================================================================================
MODULO DE FACTURACION FISCAL - ANgesLAB
================================================================================
Modulo de facturacion adaptado a normativas fiscales venezolanas:
- Control de numeracion de facturas, notas de credito y debito
- Manejo de IVA segun normativa vigente
- IGTF (Impuesto a Grandes Transacciones Financieras) al 3%
- Soporte para exoneraciones
- Soporte multi-moneda (USD, VES, COP) con tasas BCV
- Retenciones de IVA
- Generacion de reportes fiscales
- Libro de ventas formato SENIAT

Normativas aplicadas:
- Providencia SNAT/2011/0071 (Facturacion)
- Providencia SNAT/2024/000102 (Facturacion digital)
- Providencia SNAT/2022/000013 (IGTF en facturas)
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

    # IGTF (Impuesto a Grandes Transacciones Financieras)
    # Aplica a pagos en divisas, criptomonedas y transferencias internacionales
    TASA_IGTF = Decimal('3.00')  # 3%

    # Formas de pago que activan IGTF automaticamente (nombres de FormasPago)
    FORMAS_PAGO_IGTF = {'Divisa', 'Zelle'}

    # Tipos de documento fiscal
    TIPO_FACTURA = 'Factura'
    TIPO_NOTA_CREDITO = 'NC'
    TIPO_NOTA_DEBITO = 'ND'

    # Tasas de retencion de IVA
    RETENCION_IVA_ORDINARIO = Decimal('75.00')    # 75% contribuyente ordinario
    RETENCION_IVA_ESPECIAL = Decimal('100.00')     # 100% contribuyente especial

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
        except Exception:
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
            'tasa_iva': Decimal(str(config.get('TasaIVALaboratorio') or config.get('IVAPorDefecto') or 16)) if config else Decimal('16'),
            # Campos IGTF / Fiscal
            'igtf_activo': bool(config.get('IGTFActivo', True)) if config else True,
            'tasa_igtf': Decimal(str(config.get('TasaIGTF') or 3)) if config else Decimal('3'),
            'tipo_contribuyente': (config.get('TipoContribuyente') or 'Ordinario') if config else 'Ordinario',
        }


# ============================================================================
# CLASE PRINCIPAL DE FACTURACION
# ============================================================================

class FacturacionFiscal:
    """
    Maneja la facturacion conforme a normativas fiscales venezolanas.
    Soporta IGTF, multi-moneda, notas de credito/debito y retenciones.
    """

    def __init__(self, db):
        self.db = db
        self.config = ConfiguracionFiscal.cargar_datos_contribuyente(db)

    # -------------------------------------------------------------------------
    # GENERACION DE NUMEROS DE DOCUMENTO
    # -------------------------------------------------------------------------

    def _generar_numero_secuencial(self, prefijo):
        """Genera el siguiente numero secuencial para un prefijo dado."""
        anio = datetime.now().year

        result = self.db.query_one(f"""
            SELECT MAX(NumeroFactura) as Ultimo
            FROM Facturas
            WHERE NumeroFactura LIKE '{prefijo}-{anio}-%'
        """)

        if result and result['Ultimo']:
            try:
                ultimo = result['Ultimo']
                numero = int(ultimo.split('-')[-1]) + 1
            except Exception:
                numero = 1
        else:
            numero = 1

        return f"{prefijo}-{anio}-{numero:06d}"

    def generar_numero_factura(self):
        """Genera el siguiente numero de factura secuencial"""
        return self._generar_numero_secuencial('FAC')

    def generar_numero_nota_credito(self):
        """Genera el siguiente numero de nota de credito: NC-YYYY-NNNNNN"""
        return self._generar_numero_secuencial('NC')

    def generar_numero_nota_debito(self):
        """Genera el siguiente numero de nota de debito: ND-YYYY-NNNNNN"""
        return self._generar_numero_secuencial('ND')

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
            except Exception:
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

    def calcular_igtf(self, monto_total, forma_pago_nombre=None, aplica_igtf=False):
        """
        Calcula el IGTF (3%) sobre pagos en divisas/cripto.

        Segun Providencia SNAT/2022/000013, el IGTF se aplica a
        pagos realizados en moneda extranjera, criptomonedas o
        transferencias internacionales.

        Args:
            monto_total: monto total de la factura (base + IVA)
            forma_pago_nombre: nombre de la forma de pago (de FormasPago)
            aplica_igtf: forzar aplicacion de IGTF

        Returns:
            (monto_igtf, total_con_igtf) como floats
        """
        if not self.config.get('igtf_activo', True):
            return 0.0, float(monto_total)

        # Auto-detectar si la forma de pago activa IGTF
        if forma_pago_nombre and forma_pago_nombre in ConfiguracionFiscal.FORMAS_PAGO_IGTF:
            aplica_igtf = True

        if not aplica_igtf:
            return 0.0, float(monto_total)

        base = Decimal(str(monto_total))
        tasa = self.config.get('tasa_igtf', ConfiguracionFiscal.TASA_IGTF)

        monto_igtf = (base * tasa / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        return float(monto_igtf), float(base + monto_igtf)

    def calcular_retencion_iva(self, monto_iva, es_contribuyente_especial=None):
        """
        Calcula la retencion de IVA.

        Segun normativa:
        - Contribuyente ordinario: 75% del IVA
        - Contribuyente especial: 100% del IVA

        Args:
            monto_iva: monto del IVA a retener
            es_contribuyente_especial: si None, usa config del sistema

        Returns:
            float: monto de la retencion
        """
        if es_contribuyente_especial is None:
            es_contribuyente_especial = (
                self.config.get('tipo_contribuyente', 'Ordinario') == 'Especial'
            )

        tasa = (ConfiguracionFiscal.RETENCION_IVA_ESPECIAL
                if es_contribuyente_especial
                else ConfiguracionFiscal.RETENCION_IVA_ORDINARIO)

        retencion = (Decimal(str(monto_iva)) * tasa / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        return float(retencion)

    def calcular_totales_factura(self, detalles, descuento_porcentaje=0,
                                 es_exonerada=False, forma_pago_nombre=None):
        """
        Calcula todos los totales de una factura incluyendo IGTF.

        Parametros:
        - detalles: lista de dict con {precio, cantidad, descuento}
        - descuento_porcentaje: descuento global sobre el subtotal
        - es_exonerada: si la factura esta exonerada de IVA
        - forma_pago_nombre: nombre de forma de pago (para auto-detectar IGTF)

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

        # Total (sin IGTF)
        total = base_imponible + monto_iva

        # Calcular IGTF
        monto_igtf, total_con_igtf = self.calcular_igtf(
            float(total), forma_pago_nombre
        )

        return {
            'subtotal': float(subtotal),
            'monto_descuento': float(monto_descuento),
            'porcentaje_descuento': float(descuento),
            'base_imponible': float(base_imponible_iva),
            'monto_exento': float(monto_exento),
            'tasa_iva': float(self.config['tasa_iva']),
            'monto_iva': float(monto_iva),
            'total': float(total),
            # Campos IGTF
            'monto_igtf': monto_igtf,
            'tasa_igtf': float(self.config.get('tasa_igtf', 3)),
            'total_con_igtf': total_con_igtf,
            'aplica_igtf': monto_igtf > 0,
        }

    # -------------------------------------------------------------------------
    # CREACION DE FACTURAS
    # -------------------------------------------------------------------------

    def crear_factura(self, datos_factura, detalles, usuario_id, gestor_tasas=None):
        """
        Crea una factura completa con todos sus detalles.
        Soporta multi-moneda, IGTF y tipos de documento (FAC/NC/ND).

        Parametros:
        - datos_factura: dict con datos de la factura
            - paciente_id (requerido)
            - moneda_factura: 'USD', 'VES', 'COP' (default: 'USD')
            - tipo_documento: 'Factura', 'NC', 'ND' (default: 'Factura')
            - factura_afectada_id: int (para NC/ND)
            - forma_pago_nombre: str (para auto-detectar IGTF)
            - descuento_porcentaje, es_exonerada, etc.
        - detalles: lista de pruebas/items a facturar
        - usuario_id: ID del usuario que crea la factura
        - gestor_tasas: instancia de GestorTasasCambio (opcional, para conversiones)

        Retorna: (factura_id, numero_factura)
        """
        tipo_doc = datos_factura.get('tipo_documento', 'Factura')
        moneda = datos_factura.get('moneda_factura', 'USD')

        # Generar numeros segun tipo de documento
        if tipo_doc == ConfiguracionFiscal.TIPO_NOTA_CREDITO:
            numero_factura = self.generar_numero_nota_credito()
        elif tipo_doc == ConfiguracionFiscal.TIPO_NOTA_DEBITO:
            numero_factura = self.generar_numero_nota_debito()
        else:
            numero_factura = self.generar_numero_factura()

        numero_control = self.generar_numero_control()

        # Calcular totales con IGTF
        descuento = datos_factura.get('descuento_porcentaje', 0)
        es_exonerada = datos_factura.get('es_exonerada', False)
        forma_pago = datos_factura.get('forma_pago_nombre')
        totales = self.calcular_totales_factura(
            detalles, descuento, es_exonerada, forma_pago
        )

        # Obtener tasa de cambio para montos duales
        tasa_cambio = 1.0
        if gestor_tasas:
            try:
                tasa_cambio = gestor_tasas.get_tasa_actual('USD')
            except Exception:
                tasa_cambio = 1.0

        # Calcular montos duales (USD y Bs)
        total_factura = totales['total_con_igtf'] if totales['aplica_igtf'] else totales['total']
        total_dec = Decimal(str(total_factura))
        tasa_dec = Decimal(str(tasa_cambio))

        if moneda == 'USD':
            monto_total_usd = float(total_dec)
            monto_total_bs = float((total_dec * tasa_dec).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP))
        elif moneda in ('VES', 'Bs', 'Bs.'):
            monto_total_bs = float(total_dec)
            if tasa_dec > 0:
                monto_total_usd = float((total_dec / tasa_dec).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP))
            else:
                monto_total_usd = float(total_dec)
        elif moneda == 'COP':
            # COP: usar tasa COP/USD si disponible
            tasa_cop = 1.0
            if gestor_tasas:
                try:
                    tasa_cop = gestor_tasas.get_tasa_actual('COP_USD')
                except Exception:
                    pass
            tasa_cop_dec = Decimal(str(tasa_cop))
            if tasa_cop_dec > 0:
                monto_total_usd = float((total_dec / tasa_cop_dec).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP))
            else:
                monto_total_usd = float(total_dec)
            monto_total_bs = float((Decimal(str(monto_total_usd)) * tasa_dec).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP))
        else:
            monto_total_usd = float(total_dec)
            monto_total_bs = float((total_dec * tasa_dec).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP))

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

            # IGTF
            'MontoIGTF': totales['monto_igtf'],
            'TasaIGTF': totales['tasa_igtf'],
            'AplicaIGTF': totales['aplica_igtf'],

            # Multi-moneda
            'MonedaFactura': moneda,
            'TasaCambioDia': tasa_cambio,
            'MontoTotalBs': monto_total_bs,
            'MontoTotalUSD': monto_total_usd,

            # Tipo de documento (Factura / NC / ND)
            'TipoDocumento': tipo_doc,
            'FacturaAfectadaID': datos_factura.get('factura_afectada_id'),

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
        tipo_label = {'Factura': 'Factura', 'NC': 'Nota de Credito', 'ND': 'Nota de Debito'}
        self._registrar_auditoria(usuario_id, 'INSERT', 'Facturas', factura_id,
                                  f"{tipo_label.get(tipo_doc, tipo_doc)} {numero_factura} creada")

        return factura_id, numero_factura

    # -------------------------------------------------------------------------
    # NOTAS DE CREDITO Y DEBITO
    # -------------------------------------------------------------------------

    def crear_nota_credito(self, factura_original_id, detalles_nc, motivo,
                           usuario_id, gestor_tasas=None):
        """
        Crea una Nota de Credito referenciando una factura original.

        Args:
            factura_original_id: ID de la factura que se acredita
            detalles_nc: items a acreditar (parcial o total)
            motivo: razon de la nota de credito
            usuario_id: usuario que crea
            gestor_tasas: GestorTasasCambio (opcional)

        Returns:
            (nc_id, nc_numero)
        """
        factura_original = self.db.query_one(
            f"SELECT * FROM Facturas WHERE FacturaID={factura_original_id}"
        )
        if not factura_original:
            raise ValueError("Factura original no encontrada")

        datos_nc = {
            'paciente_id': factura_original['PacienteID'],
            'responsable_id': factura_original.get('ResponsablePagoID'),
            'solicitud_id': factura_original.get('SolicitudID'),
            'tipo_documento': ConfiguracionFiscal.TIPO_NOTA_CREDITO,
            'factura_afectada_id': factura_original_id,
            'observaciones': f"NC por: {motivo}. Ref: {factura_original.get('NumeroFactura', '')}",
            'moneda_factura': factura_original.get('MonedaFactura', 'USD'),
            'tipo': factura_original.get('TipoFactura', 'Contado'),
            'es_exonerada': bool(factura_original.get('EstaExonerada', False)),
        }

        return self.crear_factura(datos_nc, detalles_nc, usuario_id, gestor_tasas)

    def crear_nota_debito(self, factura_original_id, detalles_nd, motivo,
                          usuario_id, gestor_tasas=None):
        """
        Crea una Nota de Debito referenciando una factura original.

        Args:
            factura_original_id: ID de la factura afectada
            detalles_nd: items del cargo adicional
            motivo: razon de la nota de debito
            usuario_id: usuario que crea
            gestor_tasas: GestorTasasCambio (opcional)

        Returns:
            (nd_id, nd_numero)
        """
        factura_original = self.db.query_one(
            f"SELECT * FROM Facturas WHERE FacturaID={factura_original_id}"
        )
        if not factura_original:
            raise ValueError("Factura original no encontrada")

        datos_nd = {
            'paciente_id': factura_original['PacienteID'],
            'responsable_id': factura_original.get('ResponsablePagoID'),
            'solicitud_id': factura_original.get('SolicitudID'),
            'tipo_documento': ConfiguracionFiscal.TIPO_NOTA_DEBITO,
            'factura_afectada_id': factura_original_id,
            'observaciones': f"ND por: {motivo}. Ref: {factura_original.get('NumeroFactura', '')}",
            'moneda_factura': factura_original.get('MonedaFactura', 'USD'),
            'tipo': factura_original.get('TipoFactura', 'Contado'),
            'es_exonerada': bool(factura_original.get('EstaExonerada', False)),
        }

        return self.crear_factura(datos_nd, detalles_nd, usuario_id, gestor_tasas)

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
        Registra un cobro/pago de factura con soporte IGTF y multi-moneda.

        Parametros:
        - datos_cobro: dict con datos del cobro
            - factura_id (requerido)
            - monto (requerido)
            - forma_pago_id (requerido)
            - moneda_pago: 'USD', 'VES', 'COP' (default: 'USD')
            - banco_id, cuenta_id, referencia, numero_cheque, observaciones
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

        # Determinar si aplica IGTF segun forma de pago
        forma_pago_nombre = None
        aplica_igtf = False
        monto_igtf = Decimal('0')

        try:
            fp = self.db.query_one(
                f"SELECT Nombre FROM FormasPago WHERE FormaPagoID={datos_cobro['forma_pago_id']}"
            )
            if fp:
                forma_pago_nombre = fp['Nombre']
                if forma_pago_nombre in ConfiguracionFiscal.FORMAS_PAGO_IGTF:
                    aplica_igtf = True
        except Exception:
            pass

        if aplica_igtf and self.config.get('igtf_activo', True):
            tasa_igtf = self.config.get('tasa_igtf', ConfiguracionFiscal.TASA_IGTF)
            monto_igtf = (monto_cobro * tasa_igtf / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )

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
            'FechaRegistro': datetime.now(),
            # Campos IGTF
            'MontoIGTF': float(monto_igtf),
            'AplicaIGTF': aplica_igtf,
            'MonedaPago': datos_cobro.get('moneda_pago', 'USD'),
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
        igtf_info = f" (IGTF: {monto_igtf})" if aplica_igtf else ""
        self._registrar_auditoria(usuario_id, 'INSERT', 'Cobros', None,
                                  f"Cobro {numero_cobro} de {monto_cobro}{igtf_info} a factura {factura['NumeroFactura']}")

        return numero_cobro

    # -------------------------------------------------------------------------
    # REPORTES FISCALES
    # -------------------------------------------------------------------------

    def generar_libro_ventas(self, fecha_desde, fecha_hasta):
        """
        Genera el libro de ventas para el periodo indicado.
        Formato SENIAT con columnas de IGTF y multi-moneda.

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
                f.TipoDocumento,
                f.BaseImponible,
                f.TasaIVA,
                f.MontoIVA,
                f.MontoExento,
                f.MontoTotal,
                f.MontoIGTF,
                f.TasaIGTF,
                f.AplicaIGTF,
                f.MonedaFactura,
                f.TasaCambioDia,
                f.MontoTotalBs,
                f.MontoTotalUSD,
                f.FacturaAfectadaID,
                f.Anulada
            FROM Facturas f
            INNER JOIN Pacientes p ON f.PacienteID = p.PacienteID
            WHERE f.FechaEmision BETWEEN #{fecha_desde.strftime('%m/%d/%Y')}#
                AND #{fecha_hasta.strftime('%m/%d/%Y')}#
            ORDER BY f.FechaEmision, f.NumeroFactura
        """)

        libro = []
        for f in facturas:
            tipo_doc = f.get('TipoDocumento', 'Factura')

            # Tipo de operacion segun documento
            if f.get('Anulada'):
                tipo_op = 'ANULADA'
            elif tipo_doc == 'NC':
                tipo_op = 'NOTA DE CREDITO'
            elif tipo_doc == 'ND':
                tipo_op = 'NOTA DE DEBITO'
            else:
                tipo_op = 'VENTA'

            registro = {
                'fecha': f['FechaEmision'],
                'numero_factura': f['NumeroFactura'],
                'numero_control': f['NumeroControl'],
                'rif_cliente': f['RIFCliente'] or 'SIN RIF',
                'nombre_cliente': f['NombreCliente'],
                'tipo_operacion': tipo_op,
                'tipo_documento': tipo_doc,
                'base_imponible': f['BaseImponible'] or 0,
                'alicuota': f['TasaIVA'] or 0,
                'impuesto': f['MontoIVA'] or 0,
                'exento': f['MontoExento'] or 0,
                'total': f['MontoTotal'] if not f['Anulada'] else 0,
                # Campos IGTF
                'igtf': f.get('MontoIGTF') or 0,
                'tasa_igtf': f.get('TasaIGTF') or 0,
                'aplica_igtf': bool(f.get('AplicaIGTF')),
                # Multi-moneda
                'moneda': f.get('MonedaFactura', 'USD'),
                'tasa_cambio': f.get('TasaCambioDia') or 0,
                'total_bs': f.get('MontoTotalBs') or 0,
                'total_usd': f.get('MontoTotalUSD') or 0,
                # Referencia NC/ND
                'factura_afectada': f.get('FacturaAfectadaID'),
            }
            libro.append(registro)

        return libro

    def resumen_fiscal_periodo(self, fecha_desde, fecha_hasta):
        """
        Genera resumen fiscal del periodo con IGTF.

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
                SUM(CASE WHEN Anulada=False THEN MontoCobrado ELSE 0 END) as TotalCobrado,
                SUM(CASE WHEN Anulada=False THEN MontoIGTF ELSE 0 END) as TotalIGTF
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
            'por_cobrar': (result['TotalVentas'] or 0) - (result['TotalCobrado'] or 0),
            'total_igtf': result.get('TotalIGTF') or 0,
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
        except Exception:
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
    print(f"Tasa IGTF: {config.TASA_IGTF}%")

    # Ejemplo de monto en letras
    print(f"\n123.45 = {monto_en_letras(123.45)}")
    print(f"1000.00 = {monto_en_letras(1000.00)}")

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


try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.facturacion_fiscal')
except Exception:  # pragma: no cover - respaldo si falta el modulo
    import logging as _logging
    _log = _logging.getLogger('angeslab.facturacion_fiscal')
    _log.addHandler(_logging.NullHandler())


# ============================================================================
# CONFIGURACION FISCAL
# ============================================================================

def _tasa_configurada(config):
    """
    La tasa de IVA del laboratorio, respetando el cero.

    Un cero NO es "sin configurar": es un laboratorio cuyos servicios estan
    exentos, que es el caso normal de un laboratorio clinico. El codigo
    anterior encadenaba con 'or' y, como en Python el cero es falso, un cero
    configurado terminaba facturando al 16%.

    Sin ninguna de las dos claves se cae al 16%, que es la alicuota general
    y lo que habia antes.
    """
    if not config:
        return Decimal('16')
    for clave in ('TasaIVALaboratorio', 'IVAPorDefecto'):
        if clave not in config:
            continue
        valor = config.get(clave)
        if valor is None:
            continue
        try:
            return Decimal(str(valor))
        except Exception:
            continue
    return Decimal('16')


def _es_especial(tipo):
    """True si el tipo de contribuyente configurado es 'Especial'."""
    return 'especial' in str(tipo or '').strip().lower()


def igtf_corresponde(config):
    """
    Si este laboratorio tiene que cobrar IGTF. Solo con las DOS condiciones.

    La Providencia SNAT/2022/000013 (G.O. 42.339) designa agentes de
    percepcion del IGTF a los sujetos pasivos ESPECIALES, y a nadie mas. Un
    contribuyente ordinario que suma el 3% a un pago en divisas le cobra al
    paciente un impuesto que no tiene derecho a percibir.

    Antes bastaba con IGTFActivo, y ademas valia verdadero cuando faltaba,
    de modo que un laboratorio ordinario sin configurar cobraba IGTF en cada
    pago en Divisa o Zelle. Ahora:

      - ordinario (o sin tipo configurado): nunca, aunque IGTFActivo diga
        que si; el interruptor no puede crear una obligacion que la ley no da.
      - especial: solo si IGTFActivo esta encendido expresamente.
    """
    if not config:
        return False
    if not _es_especial(config.get('TipoContribuyente')):
        return False
    return bool(config.get('IGTFActivo') or False)


class ConfiguracionFiscal:
    """Configuracion fiscal del sistema"""

    # Tasas de IVA vigentes (actualizar segun normativa)
    TASA_IVA_GENERAL = Decimal('16.00')      # 16% General
    TASA_IVA_REDUCIDA = Decimal('8.00')       # 8% Reducida
    TASA_IVA_SUNTUARIA = Decimal('31.00')     # 31% Productos suntuarios
    TASA_IVA_EXENTO = Decimal('0.00')         # 0% Exento

    # Servicios de laboratorio clinico.
    #
    # Estan EXENTOS. La Sala Constitucional del TSJ, en sentencia 1505 del
    # 5/6/2003, declaro exentos del IVA los servicios medico-asistenciales,
    # odontologicos, de cirugia y hospitalizacion prestados por entes
    # privados, y la jurisprudencia contencioso-tributaria posterior lo ha
    # aplicado a los laboratorios clinicos para las actividades propias del
    # laboratorio.
    #
    # Ojo: la exencion cubre el SERVICIO, no todo lo que venda el negocio.
    # Un bien mueble -reactivos, materiales- sigue gravado, y ahi aplica la
    # alicuota general.
    #
    # Esta constante se deja en cero para que, si alguien la usa como valor
    # inicial, no empiece cobrando un impuesto que el servicio no causa. La
    # tasa real de cada instalacion sale de ConfiguracionLaboratorio.
    TASA_IVA_LABORATORIO = Decimal('0.00')    # Exento (TSJ 1505/2003)

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

    # Tasas de retencion de ISLR (Decreto 1.808)
    # Clave: codigo de actividad → (porcentaje retencion, sustraendo UT)
    RETENCIONES_ISLR = {
        'servicios_salud':      {'tasa': Decimal('1.00'),  'sustraendo_ut': 0,  'descripcion': 'Servicios de salud'},
        'servicios_profesional': {'tasa': Decimal('3.00'),  'sustraendo_ut': 0,  'descripcion': 'Honorarios profesionales PJD'},
        'servicios_general':    {'tasa': Decimal('2.00'),  'sustraendo_ut': 0,  'descripcion': 'Servicios en general'},
        'compras_bienes':       {'tasa': Decimal('1.00'),  'sustraendo_ut': 0,  'descripcion': 'Compra de bienes muebles'},
        'alquiler_inmueble':    {'tasa': Decimal('3.00'),  'sustraendo_ut': 0,  'descripcion': 'Alquiler de bienes inmuebles'},
        'comisiones':           {'tasa': Decimal('3.00'),  'sustraendo_ut': 0,  'descripcion': 'Comisiones mercantiles'},
        'fletes':               {'tasa': Decimal('1.00'),  'sustraendo_ut': 0,  'descripcion': 'Fletes y transporte'},
        'publicidad':           {'tasa': Decimal('5.00'),  'sustraendo_ut': 0,  'descripcion': 'Publicidad y propaganda'},
    }

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
        except Exception as _exc:
            _log.warning("cargar_datos_contribuyente: %s", _exc)
        if not config:
            config = db.query_one("SELECT * FROM ConfiguracionSistema")
        return {
            'nombre': config.get('NombreLaboratorio', 'LABORATORIO') if config else 'LABORATORIO',
            'rif': (config.get('RIF') or '') if config else '',
            'direccion': (config.get('Direccion') or '') if config else '',
            'telefono': (config.get('Telefono1') or config.get('Telefono') or '') if config else '',
            'whatsapp': (config.get('WhatsApp') or '') if config else '',
            'email': (config.get('Email') or '') if config else '',
            'tasa_iva': _tasa_configurada(config),
            # Campos IGTF / Fiscal
            'igtf_activo': igtf_corresponde(config),
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
        El siguiente numero de control, sacado del rango que asigno la
        imprenta digital (Providencia SNAT/2026/00093, art. 9).

        Antes se deducia del mayor numero que hubiera en la tabla de
        facturas. Con la norma derogada bastaba; con esta no, porque el
        rango lo fija un tercero: si la imprenta asigno del 1 al 1.000 y el
        programa sigue contando hasta el 1.001, ese documento esta fuera del
        rango autorizado y nadie se entera.

        Devuelve None cuando no queda rango. Quien llama tiene que avisar y
        NO emitir: poner un numero que nadie autorizo es peor que no
        facturar hasta que lleguen los nuevos.

        Mientras no haya ningun rango cargado se conserva el comportamiento
        anterior, para que una instalacion que todavia no ha pedido rangos
        -o que factura con maquina fiscal- siga funcionando igual.
        """
        try:
            from modulos import rangos_control
        except Exception:
            rangos_control = None

        if rangos_control is not None:
            try:
                if rangos_control.listar_rangos(self.db, solo_activos=True):
                    datos = rangos_control.tomar_numero(self.db)
                    # Con rangos cargados pero agotados se devuelve None a
                    # proposito: hay que pedir mas, no seguir contando
                    return datos['numero'] if datos else None
            except Exception as e:
                _log.warning("No se pudo tomar el numero del rango: %s", e)

        # Sin rangos: como antes
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
        if not self.config.get('igtf_activo', False):
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

    def _tasa_item(self, item):
        """La tasa de IVA de una linea: la suya si la trae, si no la del laboratorio."""
        tasa = item.get('tasa_iva') if item else None
        if tasa is None or tasa == '':
            return Decimal(str(self.config['tasa_iva']))
        try:
            return Decimal(str(tasa))
        except Exception:
            return Decimal(str(self.config['tasa_iva']))

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
        # Subtotal, agrupado por la tasa de IVA de cada linea.
        #
        # Cada linea puede traer su 'tasa_iva' (maestros_fiscales: la prueba
        # exenta, el frasco que se vende gravado al 16%). La que no la trae
        # usa la del laboratorio, que es lo que se hacia con todas antes: una
        # factura sin tasas por linea sale identica a como salia.
        grupos = {}
        subtotal = Decimal('0.00')
        for item in detalles:
            precio = Decimal(str(item.get('precio', 0)))
            cantidad = Decimal(str(item.get('cantidad', 1)))
            desc_item = Decimal(str(item.get('descuento', 0)))

            monto_item = (precio * cantidad) - desc_item
            subtotal += monto_item
            tasa_item = Decimal('0') if es_exonerada else self._tasa_item(item)
            grupos[tasa_item] = grupos.get(tasa_item, Decimal('0.00')) + monto_item

        # Aplicar descuento global
        descuento = Decimal(str(descuento_porcentaje))
        monto_descuento = (subtotal * descuento / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

        base_imponible = subtotal - monto_descuento

        # Calcular IVA
        #
        # Con la tasa en cero el importe va a EXENTO, no a "base imponible
        # gravada al 0%". No es lo mismo: una operacion exenta esta fuera
        # del impuesto y la factura la marca con (E), mientras que una base
        # gravada al 0% declara una operacion que si causa impuesto. Los
        # servicios de un laboratorio clinico privado estan exentos, asi que
        # es el caso corriente y no una rareza.
        #
        # El descuento global se reparte entre los grupos en proporcion a su
        # importe; el ultimo grupo absorbe el centimo de redondeo para que
        # exento + bases sumen exactamente la base de la factura.
        monto_exento = Decimal('0.00')
        base_imponible_iva = Decimal('0.00')
        monto_iva = Decimal('0.00')
        desglose = []
        restante = base_imponible
        tasas = sorted(grupos)
        for i, tasa in enumerate(tasas):
            bruto = grupos[tasa]
            if i == len(tasas) - 1:
                base_grupo = restante
            elif subtotal:
                base_grupo = (base_imponible * bruto / subtotal).quantize(
                    Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                base_grupo = Decimal('0.00')
            restante -= base_grupo
            if not tasa:
                monto_exento += base_grupo
                desglose.append({'tasa': 0.0, 'base': float(base_grupo), 'iva': 0.0})
                continue
            iva_grupo = (base_grupo * tasa / Decimal('100')).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP)
            base_imponible_iva += base_grupo
            monto_iva += iva_grupo
            desglose.append({'tasa': float(tasa), 'base': float(base_grupo),
                             'iva': float(iva_grupo)})

        # La tasa que se guarda en la cabecera: la unica gravada si hay una
        # sola; si no hay ninguna, la configurada (como antes).
        gravadas = [t for t in tasas if t]
        tasa_cabecera = gravadas[0] if len(gravadas) == 1 else self.config['tasa_iva']

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
            'tasa_iva': float(tasa_cabecera),
            'monto_iva': float(monto_iva),
            'desglose_iva': desglose,
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

        # Un mes declarado no recibe documentos nuevos (periodos.py)
        try:
            from modulos import periodos
            periodos.verificar_abierto(self.db, datetime.now(), 'una factura')
        except ImportError:
            pass

        # Generar numeros segun tipo de documento
        if tipo_doc == ConfiguracionFiscal.TIPO_NOTA_CREDITO:
            numero_factura = self.generar_numero_nota_credito()
        elif tipo_doc == ConfiguracionFiscal.TIPO_NOTA_DEBITO:
            numero_factura = self.generar_numero_nota_debito()
        else:
            numero_factura = self.generar_numero_factura()

        # Con imprenta digital (HKA) el numero de control lo asigna ella al
        # emitir (emision.py): aqui no se toma ninguno, y menos del rango de
        # contingencia, que es para cuando HKA no responde.
        try:
            from modulos import emision as _emision
            _emision.asegurar_esquema(self.db)
            digital = _emision.usa_emisor_digital(self.db)
        except Exception as _exc:
            _log.warning("crear_factura: emisor: %s", _exc)
            _emision, digital = None, False
        numero_control = None if digital else self.generar_numero_control()

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
                except Exception as _exc:
                    _log.warning("crear_factura: %s", _exc)
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
            # Quien recibe la factura (maestros_fiscales.Clientes); sin
            # cliente, el receptor es el paciente como siempre
            'ClienteID': datos_factura.get('cliente_id'),
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

        if _emision is None:
            # Sin las columnas nuevas no se puede guardar el cliente
            factura_data.pop('ClienteID', None)
        else:
            # Con HKA nace pendiente de emitir; sin el, el numero de control
            # ya esta puesto y la factura queda emitida como siempre
            factura_data['EstadoEmision'] = _emision.PENDIENTE if digital else _emision.EMITIDA
            factura_data['Emisor'] = _emision.TIPO_HKA if digital else _emision.TIPO_LOCAL

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
                iva_item = float((subtotal_item * self._tasa_item(item) / 100).quantize(
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
        except Exception as _exc:
            _log.warning("registrar_cobro: %s", _exc)

        if aplica_igtf and self.config.get('igtf_activo', False):
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
        Libro de ventas del periodo. Lo arma reportes.libro_ventas.

        La version anterior salia en la moneda de cada factura (casi siempre
        dolares, cuando el libro va en bolivares) y, por un INNER JOIN con
        Pacientes, dejaba fuera las facturas a nombre de un cliente. Se
        mantienen las claves de antes para quien las lea.
        """
        from modulos.reportes import libro_ventas
        libro = libro_ventas(self.db, fecha_desde, fecha_hasta)
        return [{
            'fecha': r['fecha'], 'numero_factura': r['numero_factura'],
            'numero_control': r['numero_control'], 'rif_cliente': r['rif'] or 'SIN RIF',
            'nombre_cliente': r['razon_social'], 'tipo_operacion': r['tipo'],
            'base_imponible': float(r['base_imponible']), 'alicuota': float(r['alicuota']),
            'impuesto': float(r['iva']), 'exento': float(r['exento']),
            'total': float(r['total']), 'iva_retenido': float(r['iva_retenido']),
            'moneda': r['moneda_original'], 'tasa_cambio': float(r['tasa']),
            'factura_afectada': r['factura_afectada'],
        } for r in libro['registros']]

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
                AND #{fecha_hasta.strftime('%m/%d/%Y')} 23:59:59#
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
    # RETENCION ISLR (Decreto 1.808)
    # -------------------------------------------------------------------------

    def calcular_retencion_islr(self, monto_bruto, tipo_actividad='servicios_general',
                                  es_persona_natural=False):
        """
        Calcula la retención de ISLR según tipo de actividad.

        Args:
            monto_bruto: Monto total del pago
            tipo_actividad: Código de actividad (ver RETENCIONES_ISLR)
            es_persona_natural: True si el beneficiario es persona natural

        Returns:
            dict con tasa, monto_retencion, monto_neto, descripcion
        """
        info = ConfiguracionFiscal.RETENCIONES_ISLR.get(
            tipo_actividad,
            ConfiguracionFiscal.RETENCIONES_ISLR['servicios_general']
        )
        tasa = info['tasa']
        monto = Decimal(str(monto_bruto))
        retencion = (monto * tasa / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )
        return {
            'tipo_actividad': tipo_actividad,
            'descripcion': info['descripcion'],
            'tasa_retencion': float(tasa),
            'monto_bruto': float(monto),
            'monto_retencion': float(retencion),
            'monto_neto': float(monto - retencion),
            'es_persona_natural': es_persona_natural,
        }

    def registrar_retencion_islr(self, datos, usuario_id=None):
        """
        Registra un comprobante de retención ISLR.

        Args:
            datos: dict con ProveedorID, NumeroDocumento, FechaDocumento,
                   MontoDocumento, TipoActividad, MontoRetencion, TasaRetencion,
                   NumeroComprobante, Periodo (AAAAMM)
        """
        fecha = datos.get('FechaDocumento', datetime.now())
        if isinstance(fecha, datetime):
            fecha_str = f"#{fecha.strftime('%m/%d/%Y %H:%M:%S')}#"
        else:
            fecha_str = f"#{fecha.strftime('%m/%d/%Y')}#"

        sql = (
            "INSERT INTO [RetencionesISLR] "
            "([ProveedorID], [NumeroDocumento], [FechaDocumento], "
            "[MontoDocumento], [TipoActividad], [TasaRetencion], [MontoRetencion], "
            "[NumeroComprobante], [Periodo], [FechaRegistro]) "
            f"VALUES ("
            f"{int(datos.get('ProveedorID', 0))}, "
            f"'{str(datos.get('NumeroDocumento', '')).replace(chr(39), chr(39)*2)}', "
            f"{fecha_str}, "
            f"{float(datos.get('MontoDocumento', 0))}, "
            f"'{datos.get('TipoActividad', 'servicios_general')}', "
            f"{float(datos.get('TasaRetencion', 0))}, "
            f"{float(datos.get('MontoRetencion', 0))}, "
            f"'{str(datos.get('NumeroComprobante', '')).replace(chr(39), chr(39)*2)}', "
            f"'{datos.get('Periodo', datetime.now().strftime('%Y%m'))}', "
            f"#{datetime.now().strftime('%m/%d/%Y %H:%M:%S')}#"
            f")"
        )
        self.db.execute(sql)

        if usuario_id:
            self._registrar_auditoria(
                usuario_id, 'Registrar Retencion ISLR',
                'RetencionesISLR', 0,
                f"Comprobante: {datos.get('NumeroComprobante', '')}"
            )

    def listar_retenciones_islr(self, periodo=None, proveedor_id=None):
        """Lista retenciones ISLR con filtros opcionales."""
        where = []
        if periodo:
            where.append(f"r.Periodo='{periodo}'")
        if proveedor_id:
            where.append(f"r.ProveedorID={int(proveedor_id)}")

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        sql = (
            f"SELECT r.*, p.RazonSocial, p.RIF "
            f"FROM [RetencionesISLR] AS r "
            f"LEFT JOIN [Proveedores] AS p ON r.ProveedorID = p.ProveedorID "
            f"{where_sql} "
            f"ORDER BY r.FechaDocumento DESC"
        )
        return self.db.query(sql) or []

    # -------------------------------------------------------------------------
    # LIBRO DE COMPRAS (formato SENIAT)
    # -------------------------------------------------------------------------

    def generar_libro_compras(self, fecha_desde, fecha_hasta):
        """
        Libro de compras en formato SENIAT.

        Lo arma compras.libro_compras desde las facturas de proveedor
        registradas. La version anterior leia CuentasPorPagar, donde no hay
        IVA, y suponia que todo monto traia IVA al 16%: una compra exenta
        salia con credito fiscal. Se mantienen las claves de antes para quien
        las lea.
        """
        from modulos.compras import libro_compras
        libro = libro_compras(self.db, fecha_desde, fecha_hasta)
        registros = []
        for r in libro['registros']:
            registros.append(dict(r, numero_doc=r['numero_factura'],
                                  monto_total=r['total'], iva_soportado=r['iva'],
                                  tasa_iva=r['alicuota'], monto_exento=r['exento'],
                                  tipo_contribuyente=''))
        t = libro['totales']
        return {
            'periodo_desde': libro['periodo_desde'],
            'periodo_hasta': libro['periodo_hasta'],
            'registros': registros,
            'totales': dict(t, total_exento=t['total_exento'],
                            total_retenciones_iva=t['retencion_iva'],
                            total_retenciones_islr=0.0,
                            num_registros=len(registros)),
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
        except Exception as _exc:
            _log.warning("_registrar_auditoria: %s", _exc)


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

def monto_en_letras(monto, moneda='VES'):
    """
    El importe escrito con letras, para el renglon "Son:" de la factura.

    Hasta cientos de millones, que es mas de lo que cabe en una factura de
    laboratorio. Antes solo sabia contar hasta 999 y por encima lanzaba
    IndexError, que factura_pdf recogia en silencio: la linea no ha salido
    nunca en una factura de verdad.

    Args:
        monto: cantidad a expresar en palabras
        moneda: 'VES'/'Bs' (bolivares), 'USD' (dolares) o 'COP' (pesos)
    """
    UNIDADES = ['', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete',
                'ocho', 'nueve']
    ESPECIALES = ['diez', 'once', 'doce', 'trece', 'catorce', 'quince']
    DECENAS = ['', 'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta',
               'sesenta', 'setenta', 'ochenta', 'noventa']
    CENTENAS = ['', 'ciento', 'doscientos', 'trescientos', 'cuatrocientos',
                'quinientos', 'seiscientos', 'setecientos', 'ochocientos',
                'novecientos']

    def hasta_999(n, apocope=False):
        """
        El numero en letras. Con apocope, 'un' en vez de 'uno': se usa
        delante de 'mil' y de 'millon', donde se dice "veintiun mil".
        """
        if n == 0:
            return ''
        if n < 10:
            u = UNIDADES[n]
            return 'un' if (apocope and n == 1) else u
        if n < 16:
            return ESPECIALES[n - 10]
        if n < 20:
            return 'dieci' + hasta_999(n - 10, apocope)
        if n < 30:
            resto = n - 20
            if resto == 0:
                return 'veinte'
            return 'veinti' + hasta_999(resto, apocope)
        if n < 100:
            d, u = divmod(n, 10)
            if u == 0:
                return DECENAS[d]
            return '%s y %s' % (DECENAS[d], hasta_999(u, apocope))
        if n == 100:
            return 'cien'
        c, resto = divmod(n, 100)
        if resto == 0:
            return CENTENAS[c]
        return '%s %s' % (CENTENAS[c], hasta_999(resto, apocope))

    def en_letras(n):
        if n == 0:
            return 'cero'
        partes = []

        millones, resto = divmod(n, 1000000)
        if millones:
            if millones == 1:
                partes.append('un millon')
            else:
                partes.append('%s millones' % hasta_999(millones, apocope=True))

        miles, unidades = divmod(resto, 1000)
        if miles:
            # "mil" y no "un mil"; a partir de dos, "dos mil"
            if miles == 1:
                partes.append('mil')
            else:
                partes.append('%s mil' % hasta_999(miles, apocope=True))

        if unidades:
            partes.append(hasta_999(unidades))

        return ' '.join(partes)

    try:
        monto = float(monto or 0)
    except (TypeError, ValueError):
        monto = 0.0
    negativo = monto < 0
    monto = abs(monto)

    parte_entera = int(monto)
    centavos = int(round((monto - parte_entera) * 100))
    # El redondeo puede empujar los centavos a 100
    if centavos >= 100:
        parte_entera += 1
        centavos -= 100

    resultado = en_letras(parte_entera)
    if centavos > 0:
        resultado += ' con %02d/100' % centavos
    if negativo:
        resultado = 'menos ' + resultado

    nombres_moneda = {
        'VES': 'BOLIVARES', 'BS': 'BOLIVARES', 'BS.': 'BOLIVARES',
        'USD': 'DOLARES', 'COP': 'PESOS COLOMBIANOS', 'EUR': 'EUROS',
    }
    unidad = nombres_moneda.get(str(moneda or 'VES').upper(), 'BOLIVARES')
    return '%s %s' % (resultado.upper(), unidad)


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

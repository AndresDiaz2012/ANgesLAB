# -*- coding: utf-8 -*-
"""
================================================================================
EMISION DE DOCUMENTOS FISCALES - FASE 4 DEL ERP ADMINISTRATIVO
================================================================================
Desde el 19/04/2027 (Providencia SNAT/2026/00093) una factura existe
fiscalmente cuando un medio autorizado le asigna su numero de control. El
laboratorio contrato la imprenta digital The Factory HKA.

ANgesLAB arma el documento UNA vez (documento_fiscal) y lo entrega a un
EMISOR intercambiable:

    EmisorHKA           la imprenta digital, por su API REST
    EmisorContingencia  talonario impreso de imprenta autorizada, para cuando
                        HKA no responde (falla electrica, sin internet); el
                        numero sale de los rangos cargados en rangos_control
    EmisorLocal         lo de siempre: el numero de control lo pone el
                        programa. Sirve hasta que HKA este configurado.

CICLO DE VIDA (Facturas.EstadoEmision)

    Pendiente --emitir--> Emitida
        |                    `--anular--> Anulada
        |--HKA lo rechaza--> Rechazada (se corrige y se reenvia)
        `--sin conexion----> Pendiente (se reintenta, o pasa a Contingencia)

NUNCA DOS VECES

Cada factura viaja con un identificador fijo, ANGESLAB-<FacturaID>, en
transaccionId, y con su mismo numero de documento. Un reintento manda
exactamente el mismo documento. Una factura Emitida no se vuelve a mandar.

LO QUE FALTA CONFIRMAR CON HKA

La estructura del JSON sale de su wiki publico (manual de integracion
REST). Los CODIGOS de sus catalogos (tipo de documento, impuesto, tipo de
identificacion, forma de pago) no estan publicados: los de CATALOGO_HKA son
los habituales de HKA y estan marcados para confirmar cuando lleguen sus
catalogos. Tampoco esta documentado un metodo para consultar el estado de un
envio cuya respuesta se perdio.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.emision')
except Exception:  # pragma: no cover
    import logging as _logging
    _log = _logging.getLogger('angeslab.emision')

from modulos.compras import (_d, _q, _insert, _update, _ultimo_id, _fecha,
                             _tabla_existe, _tiene_columna)

TIPO_HKA = 'HKA'
TIPO_LOCAL = 'Local'
TIPO_CONTINGENCIA = 'Contingencia'

PENDIENTE, EMITIDA, RECHAZADA, ANULADA = 'Pendiente', 'Emitida', 'Rechazada', 'Anulada'

URL_DEMO_HKA = 'https://demoemisionv2.thefactoryhka.com.ve'

# ── Catalogos de HKA: POR CONFIRMAR con los que envie HKA ─────────────────
CATALOGO_HKA = {
    'tipo_documento': {'Factura': '01', 'NC': '02', 'ND': '03'},
    'codigo_impuesto': {Decimal('16'): 'G', Decimal('8'): 'R', Decimal('31'): 'A',
                        Decimal('0'): 'E'},
    'servicio': '2',   # indicadorBienoServicio: 1 bien, 2 servicio
    'bien': '1',
    'moneda': 'VES',
}


class ErrorEmision(Exception):
    """Base. El mensaje es para el usuario."""


class ErrorDatos(ErrorEmision):
    """Al documento le falta un requisito: no se manda."""


class ErrorRechazo(ErrorEmision):
    """El emisor recibio el documento y lo rechazo. Hay que corregir."""

    def __init__(self, mensaje, validaciones=None, respuesta=None):
        super().__init__(mensaje)
        self.validaciones = validaciones or []
        self.respuesta = respuesta


class ErrorConexion(ErrorEmision):
    """No hubo respuesta (red, caida, tiempo). Se puede reintentar."""


# ══════════════════════════════════════════════════════════════════════════
#  Esquema
# ══════════════════════════════════════════════════════════════════════════
COLUMNAS_FACTURAS = {
    'ClienteID': 'INTEGER', 'EstadoEmision': 'TEXT(15)', 'Emisor': 'TEXT(15)',
    'TransaccionID': 'TEXT(40)', 'SerieControl': 'TEXT(10)',
    'FechaAsignacionControl': 'DATETIME', 'MensajeEmisor': 'TEXT(255)',
    'RespuestaEmisor': 'MEMO', 'IntentosEmision': 'INTEGER',
}

DDL_EMISORES = (
    "CREATE TABLE [EmisoresFiscales] ([EmisorID] COUNTER PRIMARY KEY, [Tipo] TEXT(15), "
    "[Ambiente] TEXT(15), [URLBase] TEXT(200), [Usuario] TEXT(100), [ClaveCifrada] MEMO, "
    "[Serie] TEXT(10), [Sucursal] TEXT(10), [Activo] BIT, [FechaActualizacion] DATETIME)")


def asegurar_esquema(db):
    hechos = []
    if not _tabla_existe(db, 'EmisoresFiscales'):
        db.execute(DDL_EMISORES)
        hechos.append('tabla EmisoresFiscales')
    if _tabla_existe(db, 'Facturas'):
        for col, tipo in COLUMNAS_FACTURAS.items():
            if not _tiene_columna(db, 'Facturas', col):
                try:
                    db.execute("ALTER TABLE [Facturas] ADD COLUMN [%s] %s" % (col, tipo))
                    hechos.append('Facturas.%s' % col)
                except Exception as e:
                    _log.error("No se pudo anadir Facturas.%s: %s", col, e)
    return hechos


# ══════════════════════════════════════════════════════════════════════════
#  Configuracion del emisor
# ══════════════════════════════════════════════════════════════════════════
def _cifrar(texto):
    try:
        from modulos.seguridad_db import ProtectorCredenciales
        return ProtectorCredenciales.cifrar(texto)
    except Exception:  # pragma: no cover
        return texto


def _descifrar(texto):
    try:
        from modulos.seguridad_db import ProtectorCredenciales
        return ProtectorCredenciales.descifrar(texto)
    except Exception:  # pragma: no cover
        return texto


def guardar_emisor_hka(db, usuario, clave, ambiente='Prueba', url_base=None,
                       serie='', sucursal=''):
    """
    Deja HKA como emisor activo. La clave se guarda cifrada (DPAPI en
    Windows), nunca en claro. Prueba = ambiente demo de HKA.
    """
    asegurar_esquema(db)
    if not str(usuario or '').strip() or not str(clave or '').strip():
        raise ErrorDatos('Faltan el usuario y la clave que entrega HKA.')
    if ambiente not in ('Prueba', 'Produccion'):
        raise ErrorDatos('El ambiente es Prueba o Produccion.')
    url = (url_base or '').strip().rstrip('/') or (URL_DEMO_HKA if ambiente == 'Prueba' else '')
    if not url.startswith('https://'):
        raise ErrorDatos('Falta la direccion (https://...) del ambiente de %s de HKA.' % ambiente)
    db.execute("UPDATE [EmisoresFiscales] SET Activo=False")
    _insert(db, 'EmisoresFiscales', {
        'Tipo': TIPO_HKA, 'Ambiente': ambiente, 'URLBase': url,
        'Usuario': str(usuario).strip()[:100], 'ClaveCifrada': _cifrar(str(clave)),
        'Serie': str(serie or '')[:10], 'Sucursal': str(sucursal or '')[:10],
        'Activo': True, 'FechaActualizacion': datetime.now()})


def emisor_activo(db):
    """La fila del emisor activo, o None si se emite como siempre (local)."""
    if not _tabla_existe(db, 'EmisoresFiscales'):
        return None
    return db.query_one("SELECT TOP 1 * FROM [EmisoresFiscales] WHERE Activo=True "
                        "ORDER BY EmisorID DESC")


def usa_emisor_digital(db):
    fila = emisor_activo(db)
    return bool(fila and fila.get('Tipo') == TIPO_HKA)


# ══════════════════════════════════════════════════════════════════════════
#  El documento, independiente del emisor
# ══════════════════════════════════════════════════════════════════════════
def _receptor(db, fac):
    """Quien recibe la factura: el cliente si lo tiene, si no el paciente."""
    if fac.get('ClienteID') and _tabla_existe(db, 'Clientes'):
        c = db.query_one("SELECT * FROM [Clientes] WHERE ClienteID=%d" % int(fac['ClienteID']))
        if c:
            doc = str(c.get('Documento') or '')
            return {'tipo_id': doc[:1].upper(), 'numero_id': doc,
                    'razon_social': c.get('RazonSocial') or '',
                    'direccion': c.get('DomicilioFiscal') or '',
                    'telefono': c.get('Telefono') or '', 'correo': c.get('Email') or '',
                    'juridico': c.get('TipoCliente') != 'Natural'}
    p = db.query_one("SELECT * FROM [Pacientes] WHERE PacienteID=%d" % int(fac.get('PacienteID') or 0)) or {}
    tipo = str(p.get('TipoDocumento') or 'V').strip()[:1].upper() or 'V'
    numero = str(p.get('NumeroDocumento') or '').strip()
    if numero and not numero[:1].isalpha():
        numero = '%s-%s' % (tipo, numero)
    return {'tipo_id': tipo, 'numero_id': numero,
            'razon_social': ('%s %s' % (p.get('Nombres') or '', p.get('Apellidos') or '')).strip(),
            'direccion': p.get('DireccionCompleta') or '', 'telefono': p.get('Telefono1') or '',
            'correo': p.get('Email') or '', 'juridico': False}


def documento_fiscal(db, factura_id):
    """
    La factura en una forma neutra, valida para cualquier emisor.

    Los importes van en bolivares, que es la moneda legal del documento; si
    la factura se hizo en divisas se convierten a su tasa, y la divisa viaja
    aparte como referencia (art. 8 de la 00093).
    """
    fac = db.query_one("SELECT * FROM [Facturas] WHERE FacturaID=%d" % int(factura_id))
    if not fac:
        raise ErrorDatos('La factura %s no existe.' % factura_id)
    detalles = db.query("SELECT * FROM [DetalleFacturas] WHERE FacturaID=%d ORDER BY DetalleFacturaID"
                        % int(factura_id)) or []
    moneda = str(fac.get('MonedaFactura') or 'USD').upper()
    tasa = _d(fac.get('TasaCambioDia'), '0')
    en_bs = moneda in ('VES', 'BS', 'BS.')
    if not en_bs and tasa <= 0:
        raise ErrorDatos('La factura %s esta en %s y no tiene tasa de cambio.'
                         % (fac.get('NumeroFactura'), moneda))
    a_bs = (lambda m: _q(m)) if en_bs else (lambda m: _q(_d(m) * tasa))

    receptor = _receptor(db, fac)
    faltan = []
    if not receptor['razon_social']:
        faltan.append('nombre o razon social del receptor')
    if not receptor['numero_id']:
        faltan.append('cedula o RIF del receptor')
    if receptor['juridico'] and not receptor['direccion']:
        faltan.append('domicilio fiscal del receptor')
    if not detalles:
        faltan.append('al menos una linea')
    if faltan:
        raise ErrorDatos('A la factura %s le falta: %s.' % (fac.get('NumeroFactura'), ', '.join(faltan)))

    lineas = []
    exento = Decimal('0')
    grupos = {}
    for i, d in enumerate(detalles, 1):
        importe = a_bs(d.get('SubTotal'))
        iva = a_bs(d.get('MontoIVA'))
        tasa_iva = _d(d.get('TasaIVA'), '0')
        if tasa_iva <= 0 and iva > 0 and importe > 0:
            tasa_iva = (iva * 100 / importe).quantize(Decimal('1'))
        if d.get('Exonerada') or iva <= 0:
            tasa_iva, iva = Decimal('0'), Decimal('0')
        cantidad = _d(d.get('Cantidad'), '1') or Decimal('1')
        lineas.append({'n': i, 'codigo': str(d.get('PruebaID') or ''),
                       'descripcion': str(d.get('Descripcion') or '')[:200],
                       'cantidad': cantidad, 'precio': _q(importe / cantidad),
                       'importe': importe, 'tasa_iva': tasa_iva, 'iva': iva,
                       'total': importe + iva, 'servicio': bool(d.get('PruebaID'))})
        if tasa_iva == 0:
            exento += importe
        else:
            g = grupos.setdefault(tasa_iva, [Decimal('0'), Decimal('0')])
            g[0] += importe
            g[1] += iva
    gravado = sum((g[0] for g in grupos.values()), Decimal('0'))
    total_iva = sum((g[1] for g in grupos.values()), Decimal('0'))

    afectada = None
    if fac.get('FacturaAfectadaID'):
        a = db.query_one("SELECT * FROM [Facturas] WHERE FacturaID=%d" % int(fac['FacturaAfectadaID']))
        if a:
            afectada = {'numero': a.get('NumeroFactura'), 'serie': a.get('SerieControl') or '',
                        'fecha': _fecha(a.get('FechaEmision')),
                        'monto': a_bs(a.get('MontoTotal'))}
    if fac.get('TipoDocumento') in ('NC', 'ND') and not afectada:
        raise ErrorDatos('Una nota de credito o debito necesita la factura afectada.')

    emision = fac.get('FechaEmision')
    if isinstance(emision, str):
        try:
            emision = datetime.fromisoformat(emision)
        except ValueError:
            emision = datetime.combine(_fecha(emision), datetime.min.time())
    return {
        'factura_id': int(fac['FacturaID']), 'tipo': fac.get('TipoDocumento') or 'Factura',
        'numero': str(fac.get('NumeroFactura') or ''), 'fecha': emision or datetime.now(),
        'transaccion_id': fac.get('TransaccionID') or 'ANGESLAB-%d' % int(fac['FacturaID']),
        'receptor': receptor, 'lineas': lineas, 'exento': exento, 'gravado': gravado,
        'iva': total_iva, 'total': exento + gravado + total_iva,
        'desglose': {k: (v[0], v[1]) for k, v in grupos.items()},
        'moneda_original': moneda, 'tasa': tasa,
        'total_divisa': _q(fac.get('MontoTotal')) if not en_bs else None,
        'condicion': fac.get('CondicionPago') or 'Contado', 'afectada': afectada,
        'motivo': fac.get('Observaciones') or '',
    }


# ══════════════════════════════════════════════════════════════════════════
#  HKA
# ══════════════════════════════════════════════════════════════════════════
def _f2(valor):
    return '%.2f' % _q(valor)


def numero_hka(numero):
    """HKA pide el numero de documento solo con digitos: FAC-2027-000012 -> 2027000012."""
    digitos = ''.join(c for c in str(numero) if c.isdigit())
    if not digitos:
        raise ErrorDatos('El numero de documento %s no tiene digitos.' % numero)
    return digitos


def json_hka(doc, serie='', sucursal=''):
    """El documentoElectronico de HKA (estructura de su wiki, manual REST)."""
    from modulos.facturacion_fiscal import monto_en_letras
    cat = CATALOGO_HKA
    f = doc['fecha']
    ident = {
        'tipoDocumento': cat['tipo_documento'][doc['tipo']],
        'numeroDocumento': numero_hka(doc['numero']),
        'tipoProveedor': '', 'tipoTransaccion': '',
        'fechaEmision': f.strftime('%d/%m/%Y'),
        'fechaVencimiento': '', 'horaEmision': f.strftime('%I:%M:%S %p').lower(),
        'anulado': False, 'tipoDePago': doc['condicion'], 'serie': serie or '',
        'sucursal': sucursal or '', 'tipoDeVenta': 'Interna', 'moneda': cat['moneda'],
        'transaccionId': doc['transaccion_id'],
    }
    if doc['afectada']:
        a = doc['afectada']
        ident.update({'serieFacturaAfectada': a['serie'],
                      'numeroFacturaAfectada': numero_hka(a['numero']),
                      'fechaFacturaAfectada': a['fecha'].strftime('%d/%m/%Y') if a['fecha'] else '',
                      'montoFacturaAfectada': _f2(a['monto']),
                      'comentarioFacturaAfectada': doc['motivo'][:200]})
    r = doc['receptor']
    impuestos = [{'codigoTotalImp': cat['codigo_impuesto'].get(t, 'G'), 'alicuotaImp': _f2(t),
                  'baseImponibleImp': _f2(b), 'valorTotalImp': _f2(i)}
                 for t, (b, i) in sorted(doc['desglose'].items())]
    if doc['exento'] > 0:
        impuestos.append({'codigoTotalImp': cat['codigo_impuesto'][Decimal('0')],
                          'alicuotaImp': '0.00', 'baseImponibleImp': _f2(doc['exento']),
                          'valorTotalImp': '0.00'})
    totales = {
        'nroItems': str(len(doc['lineas'])), 'montoGravadoTotal': _f2(doc['gravado']),
        'montoExentoTotal': _f2(doc['exento']), 'subtotal': _f2(doc['exento'] + doc['gravado']),
        'totalAPagar': _f2(doc['total']), 'totalIVA': _f2(doc['iva']),
        'montoTotalConIVA': _f2(doc['total']), 'montoEnLetras': monto_en_letras(float(doc['total']), 'VES'),
        'totalDescuento': '0.00', 'impuestosSubtotal': impuestos,
    }
    cuerpo = {
        'encabezado': {
            'identificacionDocumento': ident,
            'comprador': {'tipoIdentificacion': r['tipo_id'],
                          'numeroIdentificacion': r['numero_id'].replace('-', '')[1:]
                          if r['numero_id'][:1].isalpha() else r['numero_id'],
                          'razonSocial': r['razon_social'][:200], 'direccion': r['direccion'][:250],
                          'pais': 'VE', 'telefono': [r['telefono']] if r['telefono'] else [],
                          'correo': [r['correo']] if r['correo'] else []},
            'totales': totales,
        },
        'detallesItems': [{
            'numeroLinea': str(l['n']), 'codigoPLU': l['codigo'],
            'indicadorBienoServicio': cat['servicio'] if l['servicio'] else cat['bien'],
            'descripcion': l['descripcion'], 'cantidad': str(l['cantidad'].normalize()),
            'precioUnitario': _f2(l['precio']), 'precioItem': _f2(l['importe']),
            'codigoImpuesto': cat['codigo_impuesto'].get(l['tasa_iva'], 'G'),
            'tasaIVA': _f2(l['tasa_iva']), 'valorIVA': _f2(l['iva']),
            'valorTotalItem': _f2(l['total'])} for l in doc['lineas']],
    }
    if doc['total_divisa'] is not None:
        cuerpo['encabezado']['totalesOtraMoneda'] = {
            'moneda': doc['moneda_original'], 'tipoCambio': '%.4f' % doc['tasa'],
            'totalAPagar': _f2(doc['total_divisa']),
            'montoTotalConIVA': _f2(doc['total_divisa'])}
    return {'documentoElectronico': cuerpo}


class EmisorHKA:
    """
    Cliente de la API REST de The Factory HKA.

    http: objeto con .post(url, json=, headers=, timeout=) que devuelve algo
    con .status_code y .json() (requests.Session). Se inyecta para poder
    probarlo sin red.
    """

    TIMEOUT = 30
    MARGEN_TOKEN = timedelta(minutes=10)

    def __init__(self, url_base, usuario, clave, serie='', sucursal='', http=None, ahora=None):
        self.url = url_base.rstrip('/')
        self.usuario, self.clave = usuario, clave
        self.serie, self.sucursal = serie, sucursal
        # La sesion HTTP se crea al primer envio: para listar pendientes o
        # anular localmente no hace falta red ni la libreria
        self.http = http
        # HKA da la expiracion del token en UTC
        self.ahora = ahora or (lambda: datetime.now(timezone.utc).replace(tzinfo=None))
        self._token = None
        self._vence = None

    @classmethod
    def desde_configuracion(cls, fila, http=None):
        return cls(fila['URLBase'], fila['Usuario'], _descifrar(fila['ClaveCifrada']),
                   fila.get('Serie') or '', fila.get('Sucursal') or '', http=http)

    def _llamar(self, ruta, cuerpo, con_token=True):
        headers = {'Content-Type': 'application/json'}
        if con_token:
            headers['Authorization'] = 'Bearer %s' % self._obtener_token()
        if self.http is None:
            import requests
            self.http = requests.Session()
        try:
            r = self.http.post(self.url + ruta, json=cuerpo, headers=headers, timeout=self.TIMEOUT)
        except Exception as e:
            raise ErrorConexion('HKA no responde (%s). Puede reintentar o pasar a contingencia.'
                                % type(e).__name__)
        if r.status_code >= 500:
            raise ErrorConexion('HKA respondio con error de servidor (%s).' % r.status_code)
        try:
            datos = r.json()
        except Exception:
            raise ErrorConexion('HKA devolvio una respuesta que no se entiende (%s).' % r.status_code)
        return r.status_code, datos

    def _obtener_token(self, forzar=False):
        if not forzar and self._token and self._vence and self.ahora() < self._vence - self.MARGEN_TOKEN:
            return self._token
        estado, datos = self._llamar('/api/Autenticacion',
                                     {'usuario': self.usuario, 'clave': self.clave}, con_token=False)
        if estado != 200 or str(datos.get('codigo')) != '200' or not datos.get('token'):
            raise ErrorRechazo('HKA no acepto el usuario y la clave: %s'
                               % (datos.get('mensaje') or estado), respuesta=datos)
        self._token = datos['token']
        try:
            self._vence = datetime.strptime(str(datos.get('expiracion'))[:19], '%Y-%m-%dT%H:%M:%S')
        except Exception:
            self._vence = self.ahora() + timedelta(hours=12)
        return self._token

    def _con_token(self, ruta, cuerpo):
        estado, datos = self._llamar(ruta, cuerpo)
        if estado == 401:
            # El token vencio antes de lo previsto: uno nuevo y una sola vez mas
            self._obtener_token(forzar=True)
            estado, datos = self._llamar(ruta, cuerpo)
        return estado, datos

    def emitir(self, doc):
        estado, datos = self._con_token('/api/Emision', json_hka(doc, self.serie, self.sucursal))
        if estado != 200 or str(datos.get('codigo')) != '200':
            validaciones = datos.get('validaciones') or []
            raise ErrorRechazo('HKA rechazo el documento: %s%s' % (
                datos.get('mensaje') or estado,
                (' - ' + '; '.join(str(v) for v in validaciones)) if validaciones else ''),
                validaciones, datos)
        res = datos.get('resultado') or {}
        if not res.get('numeroControl'):
            raise ErrorRechazo('HKA no devolvio numero de control.', respuesta=datos)
        fecha = None
        try:
            fecha = datetime.strptime('%s %s' % (res.get('fechaAsignacion') or '',
                                                 res.get('horaAsignacion') or ''), '%d/%m/%Y %I:%M:%S %p')
        except Exception:
            fecha = datetime.now()
        return {'numero_control': res['numeroControl'], 'serie': res.get('serie') or self.serie,
                'fecha': fecha, 'respuesta': datos}

    def anular(self, doc, motivo):
        ahora = datetime.now()
        estado, datos = self._con_token('/api/Anular', {
            'serie': self.serie, 'tipoDocumento': CATALOGO_HKA['tipo_documento'][doc['tipo']],
            'numeroDocumento': numero_hka(doc['numero']), 'motivoAnulacion': motivo[:200],
            'fechaAnulacion': ahora.strftime('%d/%m/%Y'),
            'horaAnulacion': ahora.strftime('%I:%M:%S %p').lower()})
        if estado != 200 or str(datos.get('codigo')) != '200':
            raise ErrorRechazo('HKA no anulo el documento: %s' % (datos.get('mensaje') or estado),
                               datos.get('validaciones'), datos)
        return datos

    def descargar(self, doc, tipo_archivo='PDF'):
        estado, datos = self._con_token('/api/Descarga', {
            'serie': self.serie, 'tipoDocumento': CATALOGO_HKA['tipo_documento'][doc['tipo']],
            'numeroDocumento': numero_hka(doc['numero']), 'tipoArchivo': tipo_archivo})
        if estado != 200:
            raise ErrorRechazo('HKA no entrego el archivo: %s' % (datos.get('mensaje') or estado),
                               respuesta=datos)
        return datos


class EmisorContingencia:
    """Talonario impreso: el numero sale de los rangos cargados en rangos_control."""

    def __init__(self, db):
        self.db = db

    def emitir(self, doc):
        from modulos import rangos_control
        datos = rangos_control.tomar_numero(self.db)
        if not datos:
            raise ErrorRechazo('No queda rango de numeros de control del talonario de '
                               'contingencia. Cargue el rango de la imprenta.')
        return {'numero_control': datos['numero'], 'serie': '', 'fecha': datetime.now(),
                'respuesta': {'contingencia': True}}

    def anular(self, doc, motivo):
        return {'contingencia': True}


class EmisorLocal:
    """Sin imprenta digital: el numero de control ya lo puso crear_factura."""

    def __init__(self, db):
        self.db = db

    def emitir(self, doc):
        fac = self.db.query_one("SELECT NumeroControl FROM [Facturas] WHERE FacturaID=%d"
                                % doc['factura_id'])
        numero = (fac or {}).get('NumeroControl')
        if not numero:
            raise ErrorRechazo('La factura no tiene numero de control.')
        return {'numero_control': numero, 'serie': '', 'fecha': datetime.now(), 'respuesta': {}}

    def anular(self, doc, motivo):
        return {}


# ══════════════════════════════════════════════════════════════════════════
#  El ciclo de vida
# ══════════════════════════════════════════════════════════════════════════
class GestorEmision:

    def __init__(self, db, emisor=None, http=None):
        self.db = db
        asegurar_esquema(db)
        if emisor is None:
            fila = emisor_activo(db)
            emisor = (EmisorHKA.desde_configuracion(fila, http) if fila and fila.get('Tipo') == TIPO_HKA
                      else EmisorLocal(db))
        self.emisor = emisor

    def _tipo_emisor(self, emisor):
        return {EmisorHKA: TIPO_HKA, EmisorContingencia: TIPO_CONTINGENCIA}.get(type(emisor), TIPO_LOCAL)

    def _factura(self, factura_id):
        fac = self.db.query_one("SELECT * FROM [Facturas] WHERE FacturaID=%d" % int(factura_id))
        if not fac:
            raise ErrorDatos('La factura %s no existe.' % factura_id)
        return fac

    def emitir(self, factura_id, contingencia=False):
        """
        Emite una factura. Devuelve el numero de control. Una ya emitida
        devuelve el suyo sin volver a mandarla.
        """
        fac = self._factura(factura_id)
        if fac.get('Anulada'):
            raise ErrorDatos('La factura %s esta anulada.' % fac.get('NumeroFactura'))
        if fac.get('EstadoEmision') == EMITIDA:
            return fac.get('NumeroControl')
        doc = documento_fiscal(self.db, factura_id)
        emisor = EmisorContingencia(self.db) if contingencia else self.emisor
        intentos = int(fac.get('IntentosEmision') or 0) + 1
        base = {'TransaccionID': doc['transaccion_id'], 'IntentosEmision': intentos,
                'Emisor': self._tipo_emisor(emisor)}
        try:
            r = emisor.emitir(doc)
        except ErrorConexion as e:
            _update(self.db, 'Facturas', dict(base, EstadoEmision=PENDIENTE,
                                              MensajeEmisor=str(e)[:255]),
                    'FacturaID=%d' % int(factura_id))
            raise
        except ErrorRechazo as e:
            _update(self.db, 'Facturas', dict(base, EstadoEmision=RECHAZADA,
                                              MensajeEmisor=str(e)[:255],
                                              RespuestaEmisor=str(e.respuesta or '')[:4000]),
                    'FacturaID=%d' % int(factura_id))
            raise
        _update(self.db, 'Facturas', dict(
            base, EstadoEmision=EMITIDA, NumeroControl=str(r['numero_control'])[:20],
            SerieControl=str(r.get('serie') or '')[:10], FechaAsignacionControl=r.get('fecha'),
            MensajeEmisor='Contingencia' if contingencia else 'Emitida',
            RespuestaEmisor=str(r.get('respuesta') or '')[:4000]),
            'FacturaID=%d' % int(factura_id))
        _log.info("Factura %s emitida por %s: control %s", doc['numero'],
                  base['Emisor'], r['numero_control'])
        return r['numero_control']

    def anular(self, factura_id, motivo, usuario_id=0):
        if not str(motivo or '').strip():
            raise ErrorDatos('Indique el motivo de la anulacion.')
        fac = self._factura(factura_id)
        if fac.get('Anulada'):
            raise ErrorDatos('La factura ya esta anulada.')
        if fac.get('EstadoEmision') == EMITIDA and fac.get('Emisor') == TIPO_HKA:
            self.emisor.anular(documento_fiscal(self.db, factura_id), motivo)
        _update(self.db, 'Facturas', {'Anulada': True, 'MotivoAnulacion': str(motivo)[:255],
                                      'FechaAnulacion': datetime.now(), 'EstadoEmision': ANULADA},
                'FacturaID=%d' % int(factura_id))

    def pendientes(self):
        """Lo que hay que mirar: sin emitir, rechazadas o sin respuesta."""
        return self.db.query(
            "SELECT * FROM [Facturas] WHERE (Anulada IS NULL OR Anulada=False) AND "
            "(EstadoEmision IS NULL OR EstadoEmision IN ('%s', '%s')) ORDER BY FacturaID"
            % (PENDIENTE, RECHAZADA)) or []

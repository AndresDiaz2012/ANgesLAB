# -*- coding: utf-8 -*-
"""
================================================================================
COMPRAS E INVENTARIO - FASE 2 DEL ERP ADMINISTRATIVO
================================================================================
Una compra se carga UNA vez -al recibir la mercancia con la factura del
proveedor- y de ahi salen solos los tres registros que antes se llevaban por
separado, o no se llevaban:

    factura del proveedor  ->  Compras / DetalleCompras   (libro de compras)
                           ->  entrada al inventario, por lote, a costo
                               promedio ponderado
                           ->  cuenta por pagar, con vencimiento segun los
                               dias de credito del proveedor

Si los tres salen del mismo dato, no pueden discrepar. El criterio de la
fase 2 en la especificacion es justo ese: una compra aparece en inventario,
libro de compras y cuentas por pagar con los mismos montos.

TABLAS

Compras, DetalleCompras y Pagos ya venian en la base del instalador, vacias
y sin codigo que las usara. Se aprovechan tal cual y se les anaden las
columnas que faltan (numero de control, exento, base, orden de origen...).
Son nuevas OrdenesCompra, DetalleOrdenCompra, LotesProducto y
RecetaServicio. Todo se crea solo y sin tocar lo que existe.

MONEDA

El inventario se valora en dolares, como los precios del laboratorio. Una
factura en bolivares se convierte a la tasa que trae la propia compra: el
costo de un reactivo es lo que costo el dia que entro, no lo que costaria
hoy. La factura se guarda en su moneda original, que es la que va al libro.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.compras')
except Exception:  # pragma: no cover
    import logging as _logging
    _log = _logging.getLogger('angeslab.compras')


CENT = Decimal('0.01')
MONEDAS = ('USD', 'VES')

ESTADO_BORRADOR = 'Borrador'
ESTADO_APROBADA = 'Aprobada'
ESTADO_PARCIAL = 'Recibida parcial'
ESTADO_RECIBIDA = 'Recibida'
ESTADO_ANULADA = 'Anulada'

SIN_LOTE = 'SIN LOTE'


class ErrorCompra(ValueError):
    """Un dato que impide registrar la operacion. El mensaje es para el usuario."""


# ══════════════════════════════════════════════════════════════════════════
#  Utilidades de SQL (dialecto Access)
# ══════════════════════════════════════════════════════════════════════════
def _d(valor, por_defecto='0'):
    try:
        return Decimal(str(valor if valor not in (None, '') else por_defecto))
    except Exception:
        return Decimal(por_defecto)


def _q(valor):
    return _d(valor).quantize(CENT, rounding=ROUND_HALF_UP)


def _sql(valor):
    if valor is None:
        return 'NULL'
    if isinstance(valor, bool):
        return 'True' if valor else 'False'
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, (int, float)):
        return repr(valor)
    if isinstance(valor, datetime):
        return valor.strftime('#%m/%d/%Y %H:%M:%S#')
    if isinstance(valor, date):
        return valor.strftime('#%m/%d/%Y#')
    return "'%s'" % str(valor).replace("'", "''")


def _insert(db, tabla, campos):
    db.execute("INSERT INTO [%s] (%s) VALUES (%s)" % (
        tabla, ', '.join('[%s]' % c for c in campos),
        ', '.join(_sql(v) for v in campos.values())))


def _update(db, tabla, campos, where):
    db.execute("UPDATE [%s] SET %s WHERE %s" % (
        tabla, ', '.join('[%s]=%s' % (c, _sql(v)) for c, v in campos.items()), where))


def _ultimo_id(db, tabla, col_id, where=''):
    fila = db.query_one("SELECT TOP 1 [%s] FROM [%s] %s ORDER BY [%s] DESC"
                        % (col_id, tabla, ('WHERE ' + where) if where else '', col_id))
    return int((fila or {}).get(col_id) or 0)


def _tiene_columna(db, tabla, columna):
    try:
        db.query("SELECT TOP 1 [%s] FROM [%s]" % (columna, tabla))
        return True
    except Exception:
        return False


def _tabla_existe(db, tabla):
    try:
        db.query("SELECT TOP 1 * FROM [%s]" % tabla)
        return True
    except Exception:
        return False


def _fecha(valor):
    """date desde date, datetime o 'dd/mm/aaaa' / 'aaaa-mm-dd'. None si vacio."""
    if valor in (None, ''):
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    texto = str(valor).strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%d-%m-%Y'):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    raise ErrorCompra('Fecha no valida: %s (use dd/mm/aaaa)' % texto)


# ══════════════════════════════════════════════════════════════════════════
#  Esquema
# ══════════════════════════════════════════════════════════════════════════
DDL = {
    'OrdenesCompra': (
        "CREATE TABLE [OrdenesCompra] ([OrdenCompraID] COUNTER PRIMARY KEY, "
        "[NumeroOrden] TEXT(20), [ProveedorID] INTEGER, [FechaOrden] DATETIME, "
        "[Moneda] TEXT(5), [Estado] TEXT(20), [MontoTotal] DOUBLE, "
        "[Observaciones] TEXT(255), [UsuarioCrea] TEXT(50), [UsuarioAprueba] TEXT(50), "
        "[FechaAprobacion] DATETIME, [MotivoAnulacion] TEXT(255))"),
    'DetalleOrdenCompra': (
        "CREATE TABLE [DetalleOrdenCompra] ([DetalleOrdenID] COUNTER PRIMARY KEY, "
        "[OrdenCompraID] INTEGER, [ProductoID] INTEGER, [Cantidad] DOUBLE, "
        "[CantidadRecibida] DOUBLE, [PrecioUnitario] DOUBLE, [PorcentajeIVA] DOUBLE)"),
    'LotesProducto': (
        "CREATE TABLE [LotesProducto] ([LoteProductoID] COUNTER PRIMARY KEY, "
        "[ProductoID] INTEGER, [Lote] TEXT(50), [FechaVencimiento] DATETIME, "
        "[CantidadInicial] DOUBLE, [CantidadActual] DOUBLE, [CostoUnitario] DOUBLE, "
        "[CompraID] INTEGER, [FechaRegistro] DATETIME)"),
    'RecetaServicio': (
        "CREATE TABLE [RecetaServicio] ([RecetaID] COUNTER PRIMARY KEY, "
        "[PruebaID] INTEGER, [ProductoID] INTEGER, [Cantidad] DOUBLE, "
        "[FechaDesde] DATETIME)"),
    # Las tres siguientes vienen en la base del instalador; se crean igual
    # que alli solo en las instalaciones donde no existen.
    'Compras': (
        "CREATE TABLE [Compras] ([CompraID] COUNTER PRIMARY KEY, [NumeroCompra] TEXT(20), "
        "[FechaCompra] DATETIME, [ProveedorID] INTEGER, [NumeroFacturaProveedor] TEXT(50), "
        "[FechaFacturaProveedor] DATETIME, [SubTotal] DOUBLE, [MontoDescuento] DOUBLE, "
        "[MontoIVA] DOUBLE, [MontoTotal] DOUBLE, [TasaIVA] DOUBLE, [EstadoPago] TEXT(20), "
        "[MontoPagado] DOUBLE, [SaldoPendiente] DOUBLE, [FechaRecepcion] DATETIME, "
        "[RecibidoPor] TEXT(100), [Observaciones] TEXT(255), [Anulada] BIT, "
        "[MotivoAnulacion] TEXT(255), [UsuarioRegistro] TEXT(50), [FechaRegistro] DATETIME)"),
    'DetalleCompras': (
        "CREATE TABLE [DetalleCompras] ([DetalleCompraID] COUNTER PRIMARY KEY, "
        "[CompraID] INTEGER, [ProductoID] INTEGER, [Cantidad] DOUBLE, "
        "[PrecioUnitario] DOUBLE, [Descuento] DOUBLE, [PorcentajeIVA] DOUBLE, "
        "[MontoIVA] DOUBLE, [SubTotal] DOUBLE, [Total] DOUBLE, [Lote] TEXT(50), "
        "[FechaVencimiento] DATETIME)"),
    'Pagos': (
        "CREATE TABLE [Pagos] ([PagoID] COUNTER PRIMARY KEY, [NumeroPago] TEXT(20), "
        "[FechaPago] DATETIME, [CompraID] INTEGER, [MontoPagado] DOUBLE, "
        "[FormaPagoID] INTEGER, [BancoID] INTEGER, [CuentaBancariaID] INTEGER, "
        "[NumeroCheque] TEXT(50), [Beneficiario] TEXT(200), [NumeroReferencia] TEXT(50), "
        "[Observaciones] TEXT(255), [UsuarioRegistro] TEXT(50), [FechaRegistro] DATETIME, "
        "[Anulado] BIT, [MotivoAnulacion] TEXT(255))"),
}

COLUMNAS_NUEVAS = {
    'Compras': {
        'NumeroControl': 'TEXT(20)', 'OrdenCompraID': 'INTEGER',
        'MontoExento': 'DOUBLE', 'BaseImponible': 'DOUBLE',
        'Moneda': 'TEXT(5)', 'TasaCambio': 'DOUBLE',
        'RetencionIVA': 'DOUBLE', 'RetencionISLR': 'DOUBLE',
        'CuentaPagarID': 'INTEGER',
    },
    'DetalleCompras': {'DetalleOrdenID': 'INTEGER', 'CostoUSD': 'DOUBLE'},
    'CuentasPorPagar': {'ProveedorID': 'INTEGER', 'CompraID': 'INTEGER'},
    'Pagos': {'CuentaPagarID': 'INTEGER', 'TasaCambio': 'DOUBLE'},
    'MovimientosInventario': {'DocumentoReferencia': 'TEXT(50)',
                              'FechaVencimiento': 'DATETIME'},
}


def asegurar_esquema(db):
    """Crea lo que falte, sin borrar ni cambiar nada. Devuelve lo hecho."""
    hechos = []
    for tabla, ddl in DDL.items():
        if _tabla_existe(db, tabla):
            continue
        try:
            db.execute(ddl)
            hechos.append('tabla %s' % tabla)
        except Exception as e:
            _log.error("No se pudo crear %s: %s", tabla, e)
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        if not _tabla_existe(db, tabla):
            continue
        for col, tipo in columnas.items():
            if _tiene_columna(db, tabla, col):
                continue
            try:
                db.execute("ALTER TABLE [%s] ADD COLUMN [%s] %s" % (tabla, col, tipo))
                hechos.append('%s.%s' % (tabla, col))
            except Exception as e:
                _log.error("No se pudo anadir %s.%s: %s", tabla, col, e)
    if hechos:
        _log.info("Compras: %s", ', '.join(hechos))
    return hechos


# ══════════════════════════════════════════════════════════════════════════
#  Inventario: existencias, lotes y costo promedio
# ══════════════════════════════════════════════════════════════════════════
def costo_promedio(existencia, promedio, cantidad, costo):
    """
    Costo promedio ponderado tras una entrada.

    Una existencia negativa (se consumio mas de lo que se cargo) no pondera:
    esas unidades no tienen costo, y dejarlas restar daria un promedio
    absurdo, hasta negativo.
    """
    existencia = max(_d(existencia), Decimal('0'))
    cantidad, costo, promedio = _d(cantidad), _d(costo), _d(promedio)
    if existencia + cantidad <= 0:
        return costo
    if existencia == 0 or promedio <= 0:
        return costo
    return ((existencia * promedio + cantidad * costo) / (existencia + cantidad)).quantize(
        Decimal('0.0001'), rounding=ROUND_HALF_UP)


def _producto(db, producto_id):
    fila = db.query_one("SELECT * FROM [Productos] WHERE ProductoID=%d" % int(producto_id))
    if not fila:
        raise ErrorCompra('El producto %s no existe.' % producto_id)
    return fila


def _movimiento(db, producto_id, tipo, cantidad, existencia_ant, existencia_nueva,
                costo, motivo, referencia, lote=None, vence=None, usuario=None):
    campos = {
        'ProductoID': int(producto_id), 'TipoMovimiento': tipo,
        'Cantidad': float(cantidad), 'ExistenciaAnterior': float(existencia_ant),
        'ExistenciaNueva': float(existencia_nueva), 'FechaMovimiento': datetime.now(),
        'Motivo': (motivo or '')[:255], 'DocumentoReferencia': referencia[:50],
    }
    if costo is not None:
        campos['CostoUnitario'] = float(costo)
        campos['CostoTotal'] = float(_q(_d(costo) * _d(cantidad)))
    if lote:
        campos['Lote'] = lote[:50]
    if vence:
        campos['FechaVencimiento'] = vence
    if usuario:
        campos['UsuarioRegistra'] = str(usuario)[:50]
    _insert(db, 'MovimientosInventario', campos)


def entrada_inventario(db, producto_id, cantidad, costo_usd, lote, vence,
                       referencia, motivo, compra_id=None, usuario=None):
    """Entra mercancia: existencia, costo promedio, ultimo precio y lote."""
    prod = _producto(db, producto_id)
    ant = _d(prod.get('ExistenciaActual'))
    nueva = ant + _d(cantidad)
    promedio = costo_promedio(ant, prod.get('PrecioPromedioCompra'), cantidad, costo_usd)
    _update(db, 'Productos', {
        'ExistenciaActual': float(nueva), 'UltimoPrecioCompra': float(_d(costo_usd)),
        'PrecioPromedioCompra': float(promedio)}, 'ProductoID=%d' % int(producto_id))
    _insert(db, 'LotesProducto', {
        'ProductoID': int(producto_id), 'Lote': (lote or SIN_LOTE)[:50],
        'FechaVencimiento': vence, 'CantidadInicial': float(cantidad),
        'CantidadActual': float(cantidad), 'CostoUnitario': float(_d(costo_usd)),
        'CompraID': compra_id, 'FechaRegistro': datetime.now()})
    _movimiento(db, producto_id, 'Entrada', cantidad, ant, nueva, costo_usd,
                motivo, referencia, lote, vence, usuario)


def salida_inventario(db, producto_id, cantidad, referencia, motivo, usuario=None):
    """
    Saca mercancia por FEFO: primero el lote que vence antes; los lotes sin
    fecha, al final. Si los lotes no alcanzan (consumos anteriores a cargar
    lotes) el resto sale sin lote y la existencia puede quedar negativa: se
    registra igual, porque el reactivo se gasto, y la toma fisica lo cuadra.
    Devuelve [(lote, cantidad)] de lo que salio.
    """
    prod = _producto(db, producto_id)
    restante = _d(cantidad)
    existencia = _d(prod.get('ExistenciaActual'))
    lotes = db.query(
        "SELECT * FROM [LotesProducto] WHERE ProductoID=%d AND CantidadActual > 0"
        % int(producto_id)) or []
    lotes.sort(key=lambda l: (_fecha(l.get('FechaVencimiento')) or date.max,
                              int(l['LoteProductoID'])))
    salidas = []
    for lote in lotes:
        if restante <= 0:
            break
        disponible = _d(lote.get('CantidadActual'))
        toma = min(disponible, restante)
        _update(db, 'LotesProducto', {'CantidadActual': float(disponible - toma)},
                'LoteProductoID=%d' % int(lote['LoteProductoID']))
        _movimiento(db, producto_id, 'Salida', toma, existencia, existencia - toma,
                    lote.get('CostoUnitario'), motivo, referencia, lote.get('Lote'),
                    _fecha(lote.get('FechaVencimiento')), usuario)
        existencia -= toma
        restante -= toma
        salidas.append((lote.get('Lote'), toma))
    if restante > 0:
        _movimiento(db, producto_id, 'Salida', restante, existencia, existencia - restante,
                    prod.get('PrecioPromedioCompra'), motivo, referencia, None, None, usuario)
        existencia -= restante
        salidas.append((None, restante))
        if existencia < 0:
            _log.warning("Existencia negativa del producto %s: %s", producto_id, existencia)
    _update(db, 'Productos', {'ExistenciaActual': float(existencia)},
            'ProductoID=%d' % int(producto_id))
    return salidas


# ══════════════════════════════════════════════════════════════════════════
#  Ordenes de compra
# ══════════════════════════════════════════════════════════════════════════
class GestorCompras:

    def __init__(self, db, usuario=None):
        self.db = db
        self.usuario = str(usuario or '')
        asegurar_esquema(db)

    # ── utilidades ─────────────────────────────────────────────────────
    def _proveedor(self, proveedor_id):
        from modulos.modulo_administrativo import GestorProveedores
        prov = GestorProveedores(self.db).obtener_proveedor(int(proveedor_id or 0))
        if not prov:
            raise ErrorCompra('El proveedor no existe.')
        if prov.get('Activo') in (False, 0):
            raise ErrorCompra('El proveedor %s esta inactivo.' % prov.get('RazonSocial'))
        return prov

    def _numero(self, tabla, col, prefijo):
        anio = datetime.now().year
        fila = self.db.query_one("SELECT COUNT(*) AS N FROM [%s] WHERE [%s] LIKE '%s-%d-%%'"
                                 % (tabla, col, prefijo, anio))
        return '%s-%d-%06d' % (prefijo, anio, int((fila or {}).get('N') or 0) + 1)

    @staticmethod
    def _lineas_validas(lineas, pide_lote=False):
        if not lineas:
            raise ErrorCompra('Agregue al menos un producto.')
        salida = []
        for i, l in enumerate(lineas, 1):
            try:
                cantidad = _d(l.get('cantidad'))
                precio = _d(l.get('precio'))
                iva = _d(l.get('iva'), '0')
            except Exception:
                raise ErrorCompra('Linea %d: cantidad, precio o IVA no son numeros.' % i)
            if not l.get('producto_id'):
                raise ErrorCompra('Linea %d: falta el producto.' % i)
            if cantidad <= 0:
                raise ErrorCompra('Linea %d: la cantidad tiene que ser mayor que cero.' % i)
            if precio < 0:
                raise ErrorCompra('Linea %d: el precio no puede ser negativo.' % i)
            if iva not in (Decimal('0'), Decimal('8'), Decimal('16'), Decimal('31')):
                raise ErrorCompra('Linea %d: alicuota de IVA no valida (%s%%).' % (i, iva))
            linea = dict(l, cantidad=cantidad, precio=precio, iva=iva)
            if pide_lote:
                linea['vence'] = _fecha(l.get('vence'))
                linea['lote'] = str(l.get('lote') or '').strip()
            salida.append(linea)
        return salida

    # ── ordenes ────────────────────────────────────────────────────────
    def crear_orden(self, proveedor_id, lineas, moneda='USD', observaciones=''):
        self._proveedor(proveedor_id)
        if moneda not in MONEDAS:
            raise ErrorCompra('Moneda no valida: %s' % moneda)
        lineas = self._lineas_validas(lineas)
        for l in lineas:
            _producto(self.db, l['producto_id'])
        total = sum((_q(l['cantidad'] * l['precio'] * (1 + l['iva'] / 100))
                     for l in lineas), Decimal('0'))
        numero = self._numero('OrdenesCompra', 'NumeroOrden', 'OC')
        _insert(self.db, 'OrdenesCompra', {
            'NumeroOrden': numero, 'ProveedorID': int(proveedor_id),
            'FechaOrden': datetime.now(), 'Moneda': moneda, 'Estado': ESTADO_BORRADOR,
            'MontoTotal': float(total), 'Observaciones': (observaciones or '')[:255],
            'UsuarioCrea': self.usuario[:50]})
        orden_id = _ultimo_id(self.db, 'OrdenesCompra', 'OrdenCompraID',
                              "NumeroOrden='%s'" % numero)
        for l in lineas:
            _insert(self.db, 'DetalleOrdenCompra', {
                'OrdenCompraID': orden_id, 'ProductoID': int(l['producto_id']),
                'Cantidad': float(l['cantidad']), 'CantidadRecibida': 0.0,
                'PrecioUnitario': float(l['precio']), 'PorcentajeIVA': float(l['iva'])})
        return orden_id

    def obtener_orden(self, orden_id):
        orden = self.db.query_one("SELECT * FROM [OrdenesCompra] WHERE OrdenCompraID=%d"
                                  % int(orden_id))
        if not orden:
            raise ErrorCompra('La orden %s no existe.' % orden_id)
        orden['lineas'] = self.db.query(
            "SELECT d.*, p.NombreProducto FROM [DetalleOrdenCompra] AS d "
            "LEFT JOIN [Productos] AS p ON d.ProductoID = p.ProductoID "
            "WHERE d.OrdenCompraID=%d ORDER BY d.DetalleOrdenID" % int(orden_id)) or []
        return orden

    def aprobar_orden(self, orden_id):
        """
        Quien aprueba no puede ser quien la creo (especificacion, seccion 11):
        nadie cierra solo una operacion que compromete dinero.
        """
        orden = self.obtener_orden(orden_id)
        if orden.get('Estado') != ESTADO_BORRADOR:
            raise ErrorCompra('Solo se aprueba una orden en borrador (esta: %s).'
                              % orden.get('Estado'))
        if self.usuario and self.usuario == str(orden.get('UsuarioCrea') or ''):
            raise ErrorCompra('La orden la tiene que aprobar otro usuario, no quien la creo.')
        _update(self.db, 'OrdenesCompra', {
            'Estado': ESTADO_APROBADA, 'UsuarioAprueba': self.usuario[:50],
            'FechaAprobacion': datetime.now()}, 'OrdenCompraID=%d' % int(orden_id))

    def anular_orden(self, orden_id, motivo):
        orden = self.obtener_orden(orden_id)
        if not str(motivo or '').strip():
            raise ErrorCompra('Indique el motivo de la anulacion.')
        if any(_d(l.get('CantidadRecibida')) > 0 for l in orden['lineas']):
            raise ErrorCompra('La orden ya tiene mercancia recibida: no se puede anular.')
        _update(self.db, 'OrdenesCompra', {'Estado': ESTADO_ANULADA,
                                           'MotivoAnulacion': str(motivo)[:255]},
                'OrdenCompraID=%d' % int(orden_id))

    def listar_ordenes(self, estado=None):
        sql = ("SELECT o.*, p.RazonSocial FROM [OrdenesCompra] AS o "
               "LEFT JOIN [Proveedores] AS p ON o.ProveedorID = p.ProveedorID")
        if estado:
            sql += " WHERE o.Estado='%s'" % str(estado).replace("'", "''")
        return self.db.query(sql + " ORDER BY o.OrdenCompraID DESC") or []

    def ordenes_pendientes(self, proveedor_id=None):
        """Aprobadas o recibidas en parte: las que pueden recibir mercancia."""
        filas = [o for o in self.listar_ordenes()
                 if o.get('Estado') in (ESTADO_APROBADA, ESTADO_PARCIAL)]
        if proveedor_id:
            filas = [o for o in filas if int(o.get('ProveedorID') or 0) == int(proveedor_id)]
        return filas

    # ── recepcion con factura ──────────────────────────────────────────
    @staticmethod
    def totales(lineas):
        """Subtotal, exento, base e IVA por alicuota, total. En la moneda de la factura."""
        exento = base = iva = Decimal('0')
        desglose = {}
        for l in lineas:
            importe = _q(l['cantidad'] * l['precio'])
            if l['iva'] == 0:
                exento += importe
                continue
            impuesto = _q(importe * l['iva'] / 100)
            base += importe
            iva += impuesto
            g = desglose.setdefault(l['iva'], [Decimal('0'), Decimal('0')])
            g[0] += importe
            g[1] += impuesto
        return {'subtotal': exento + base, 'exento': exento, 'base': base, 'iva': iva,
                'total': exento + base + iva,
                'desglose': {float(k): (float(v[0]), float(v[1])) for k, v in desglose.items()}}

    def comparar_con_orden(self, orden_id, lineas):
        """Avisos (no errores) donde la factura no coincide con lo pedido."""
        orden = self.obtener_orden(orden_id)
        por_detalle = {int(d['DetalleOrdenID']): d for d in orden['lineas']}
        avisos = []
        for l in lineas:
            det = por_detalle.get(int(l.get('detalle_orden_id') or 0))
            nombre = (det or {}).get('NombreProducto') or 'producto %s' % l['producto_id']
            if not det:
                avisos.append('%s no estaba en la orden %s.' % (nombre, orden['NumeroOrden']))
                continue
            pendiente = _d(det.get('Cantidad')) - _d(det.get('CantidadRecibida'))
            if l['cantidad'] > pendiente:
                avisos.append('%s: llegan %s y quedaban %s por recibir.'
                              % (nombre, l['cantidad'].normalize(), pendiente.normalize()))
            if _q(l['precio']) != _q(det.get('PrecioUnitario')):
                avisos.append('%s: precio facturado %s, pactado %s.'
                              % (nombre, _q(l['precio']), _q(det.get('PrecioUnitario'))))
        return avisos

    def registrar_compra(self, factura, lineas, confirmar_avisos=False):
        """
        Registra la factura del proveedor con la mercancia recibida.

        factura: proveedor_id, numero, numero_control, fecha (dd/mm/aaaa),
                 moneda ('USD'/'VES'), tasa (Bs por USD, obligatoria en VES),
                 orden_id (opcional), observaciones.
        lineas:  producto_id, cantidad, precio (en la moneda de la factura),
                 iva (0/8/16/31), lote, vence, detalle_orden_id (opcional).

        Si la factura no cuadra con la orden devuelve los avisos SIN guardar;
        con confirmar_avisos=True se guarda igual. Devuelve
        {'compra_id', 'cuenta_pagar_id', 'numero', 'avisos', 'totales'}.
        """
        prov = self._proveedor(factura.get('proveedor_id'))
        numero = str(factura.get('numero') or '').strip()
        control = str(factura.get('numero_control') or '').strip()
        if not numero:
            raise ErrorCompra('Falta el numero de la factura del proveedor.')
        if not control:
            raise ErrorCompra('Falta el numero de control de la factura: sin el, '
                              'el IVA de la compra no es credito fiscal.')
        fecha = _fecha(factura.get('fecha')) or date.today()
        if fecha > date.today():
            raise ErrorCompra('La fecha de la factura no puede ser futura.')
        moneda = factura.get('moneda') or 'USD'
        if moneda not in MONEDAS:
            raise ErrorCompra('Moneda no valida: %s' % moneda)
        # La tasa BCV del dia de la factura hace falta siempre: en bolivares
        # para valorar el inventario en dolares, y en dolares porque el libro
        # de compras se lleva en bolivares.
        tasa = _d(factura.get('tasa'), '0')
        if tasa <= 0:
            raise ErrorCompra('Indique la tasa BCV (Bs por USD) del dia de la factura.')
        repetida = self.db.query_one(
            "SELECT CompraID FROM [Compras] WHERE ProveedorID=%d AND NumeroFacturaProveedor='%s' "
            "AND (Anulada IS NULL OR Anulada=False)"
            % (int(prov['ProveedorID']), numero.replace("'", "''")))
        if repetida:
            raise ErrorCompra('La factura %s de %s ya esta registrada.'
                              % (numero, prov.get('RazonSocial')))

        lineas = self._lineas_validas(lineas, pide_lote=True)
        for l in lineas:
            _producto(self.db, l['producto_id'])
        orden_id = int(factura.get('orden_id') or 0) or None
        avisos = []
        if orden_id:
            orden = self.obtener_orden(orden_id)
            if orden.get('Estado') not in (ESTADO_APROBADA, ESTADO_PARCIAL):
                raise ErrorCompra('La orden %s esta %s: no puede recibir mercancia.'
                                  % (orden['NumeroOrden'], orden.get('Estado', '').lower()))
            if int(orden.get('ProveedorID') or 0) != int(prov['ProveedorID']):
                raise ErrorCompra('La orden %s es de otro proveedor.' % orden['NumeroOrden'])
            avisos = self.comparar_con_orden(orden_id, lineas)
            if avisos and not confirmar_avisos:
                return {'compra_id': None, 'cuenta_pagar_id': None, 'numero': None,
                        'avisos': avisos, 'totales': self.totales(lineas)}

        t = self.totales(lineas)
        a_usd = (lambda m: _q(m / tasa)) if moneda == 'VES' else (lambda m: _q(m))
        ahora = datetime.now()
        numero_compra = self._numero('Compras', 'NumeroCompra', 'COM')
        _insert(self.db, 'Compras', {
            'NumeroCompra': numero_compra, 'FechaCompra': ahora,
            'ProveedorID': int(prov['ProveedorID']), 'NumeroFacturaProveedor': numero[:50],
            'NumeroControl': control[:20], 'FechaFacturaProveedor': fecha,
            'SubTotal': float(t['subtotal']), 'MontoDescuento': 0.0,
            'MontoExento': float(t['exento']), 'BaseImponible': float(t['base']),
            'MontoIVA': float(t['iva']), 'MontoTotal': float(t['total']),
            'TasaIVA': max(t['desglose'] or [0.0]),
            'Moneda': moneda, 'TasaCambio': float(tasa),
            'RetencionIVA': 0.0, 'RetencionISLR': 0.0,
            'EstadoPago': 'Pendiente', 'MontoPagado': 0.0,
            'SaldoPendiente': float(t['total']), 'FechaRecepcion': ahora,
            'RecibidoPor': self.usuario[:100], 'OrdenCompraID': orden_id,
            'Observaciones': str(factura.get('observaciones') or '')[:255],
            'Anulada': False, 'UsuarioRegistro': self.usuario[:50], 'FechaRegistro': ahora})
        compra_id = _ultimo_id(self.db, 'Compras', 'CompraID',
                               "NumeroCompra='%s'" % numero_compra)

        referencia = 'COMPRA %s' % numero_compra
        for l in lineas:
            importe = _q(l['cantidad'] * l['precio'])
            impuesto = _q(importe * l['iva'] / 100)
            # El IVA de la compra es credito fiscal (o gasto, segun el
            # contador), no costo del reactivo: el inventario se valora sin el.
            costo_usd = (l['precio'] / tasa) if moneda == 'VES' else l['precio']
            costo_usd = costo_usd.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
            _insert(self.db, 'DetalleCompras', {
                'CompraID': compra_id, 'ProductoID': int(l['producto_id']),
                'Cantidad': float(l['cantidad']), 'PrecioUnitario': float(l['precio']),
                'Descuento': 0.0, 'PorcentajeIVA': float(l['iva']),
                'MontoIVA': float(impuesto), 'SubTotal': float(importe),
                'Total': float(importe + impuesto), 'Lote': l['lote'][:50] or None,
                'FechaVencimiento': l['vence'],
                'DetalleOrdenID': int(l.get('detalle_orden_id') or 0) or None,
                'CostoUSD': float(costo_usd)})
            entrada_inventario(self.db, l['producto_id'], l['cantidad'], costo_usd,
                               l['lote'], l['vence'], referencia,
                               'Factura %s de %s' % (numero, prov.get('RazonSocial')),
                               compra_id, self.usuario)
            if l.get('detalle_orden_id'):
                det = self.db.query_one("SELECT * FROM [DetalleOrdenCompra] "
                                        "WHERE DetalleOrdenID=%d" % int(l['detalle_orden_id']))
                if det:
                    _update(self.db, 'DetalleOrdenCompra', {
                        'CantidadRecibida': float(_d(det.get('CantidadRecibida')) + l['cantidad'])},
                        'DetalleOrdenID=%d' % int(l['detalle_orden_id']))
        if orden_id:
            self._actualizar_estado_orden(orden_id)

        # La cuenta por pagar, en dolares como las demas
        dias = int(prov.get('DiasCredito') or 0)
        total_usd = a_usd(t['total'])
        _insert(self.db, 'CuentasPorPagar', {
            'ProveedorNombre': str(prov.get('RazonSocial') or '')[:200],
            'ProveedorRIF': str(prov.get('RIF') or '')[:20],
            'NumeroDocumento': numero[:50], 'FechaEmision': fecha,
            'FechaVencimiento': fecha + timedelta(days=dias),
            'MontoOriginal': float(total_usd), 'MontoPagado': 0.0,
            'SaldoPendiente': float(total_usd), 'Estado': 'Pendiente',
            'Observaciones': 'Compra %s%s' % (
                numero_compra, (' (Bs %s a %s Bs/USD)' % (t['total'], tasa))
                if moneda == 'VES' else ''),
            'ProveedorID': int(prov['ProveedorID']), 'CompraID': compra_id})
        cxp_id = _ultimo_id(self.db, 'CuentasPorPagar', 'CuentaPagarID',
                            'CompraID=%d' % compra_id)
        _update(self.db, 'Compras', {'CuentaPagarID': cxp_id}, 'CompraID=%d' % compra_id)
        _log.info("Compra %s registrada: factura %s, %s %s", numero_compra, numero,
                  t['total'], moneda)
        return {'compra_id': compra_id, 'cuenta_pagar_id': cxp_id, 'numero': numero_compra,
                'avisos': avisos, 'totales': t}

    def _actualizar_estado_orden(self, orden_id):
        orden = self.obtener_orden(orden_id)
        completas = all(_d(l.get('CantidadRecibida')) >= _d(l.get('Cantidad'))
                        for l in orden['lineas'])
        alguna = any(_d(l.get('CantidadRecibida')) > 0 for l in orden['lineas'])
        estado = ESTADO_RECIBIDA if completas else (ESTADO_PARCIAL if alguna else orden['Estado'])
        _update(self.db, 'OrdenesCompra', {'Estado': estado},
                'OrdenCompraID=%d' % int(orden_id))

    def obtener_compra(self, compra_id):
        compra = self.db.query_one("SELECT * FROM [Compras] WHERE CompraID=%d" % int(compra_id))
        if not compra:
            raise ErrorCompra('La compra %s no existe.' % compra_id)
        compra['lineas'] = self.db.query(
            "SELECT d.*, p.NombreProducto FROM [DetalleCompras] AS d "
            "LEFT JOIN [Productos] AS p ON d.ProductoID = p.ProductoID "
            "WHERE d.CompraID=%d ORDER BY d.DetalleCompraID" % int(compra_id)) or []
        return compra

    def listar_compras(self, desde=None, hasta=None, incluir_anuladas=False):
        where = []
        if not incluir_anuladas:
            where.append('(c.Anulada IS NULL OR c.Anulada=False)')
        if desde:
            where.append('c.FechaFacturaProveedor >= %s' % _sql(_fecha(desde)))
        if hasta:
            where.append('c.FechaFacturaProveedor < %s' % _sql(_fecha(hasta) + timedelta(days=1)))
        sql = ("SELECT c.*, p.RazonSocial FROM [Compras] AS c "
               "LEFT JOIN [Proveedores] AS p ON c.ProveedorID = p.ProveedorID")
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        return self.db.query(sql + ' ORDER BY c.CompraID DESC') or []

    def anular_compra(self, compra_id, motivo):
        """
        Deshace una compra mal cargada: saca del inventario lo que entro y
        anula la cuenta por pagar. No si ya se le pago algo al proveedor ni
        si la mercancia ya se consumio: eso se corrige con una nota de credito
        del proveedor, no borrando la compra.
        """
        if not str(motivo or '').strip():
            raise ErrorCompra('Indique el motivo de la anulacion.')
        compra = self.obtener_compra(compra_id)
        if compra.get('Anulada'):
            raise ErrorCompra('La compra ya esta anulada.')
        if _d(compra.get('MontoPagado')) > 0:
            raise ErrorCompra('Ya hay pagos a esta compra: no se puede anular.')
        cxp_id = compra.get('CuentaPagarID')
        if cxp_id:
            cxp = self.db.query_one("SELECT * FROM [CuentasPorPagar] WHERE CuentaPagarID=%d"
                                    % int(cxp_id))
            if cxp and _d(cxp.get('MontoPagado')) > 0:
                raise ErrorCompra('Ya hay pagos a esta compra: no se puede anular.')
        lotes = self.db.query("SELECT * FROM [LotesProducto] WHERE CompraID=%d"
                              % int(compra_id)) or []
        for lote in lotes:
            if _d(lote.get('CantidadActual')) < _d(lote.get('CantidadInicial')):
                raise ErrorCompra('Parte de la mercancia de esta compra ya se consumio: '
                                  'pida al proveedor una nota de credito.')
        referencia = 'ANULA %s' % compra.get('NumeroCompra')
        for lote in lotes:
            prod = _producto(self.db, lote['ProductoID'])
            ant = _d(prod.get('ExistenciaActual'))
            cant = _d(lote.get('CantidadInicial'))
            _update(self.db, 'LotesProducto', {'CantidadActual': 0.0},
                    'LoteProductoID=%d' % int(lote['LoteProductoID']))
            _update(self.db, 'Productos', {'ExistenciaActual': float(ant - cant)},
                    'ProductoID=%d' % int(lote['ProductoID']))
            _movimiento(self.db, lote['ProductoID'], 'Salida', cant, ant, ant - cant,
                        lote.get('CostoUnitario'), 'Anulacion: %s' % motivo, referencia,
                        lote.get('Lote'), _fecha(lote.get('FechaVencimiento')), self.usuario)
        _update(self.db, 'Compras', {'Anulada': True, 'MotivoAnulacion': str(motivo)[:255],
                                     'EstadoPago': 'Anulada', 'SaldoPendiente': 0.0},
                'CompraID=%d' % int(compra_id))
        if cxp_id:
            _update(self.db, 'CuentasPorPagar', {'Estado': 'Anulada', 'SaldoPendiente': 0.0},
                    'CuentaPagarID=%d' % int(cxp_id))
        for det in compra['lineas']:
            if det.get('DetalleOrdenID'):
                d = self.db.query_one("SELECT * FROM [DetalleOrdenCompra] WHERE DetalleOrdenID=%d"
                                      % int(det['DetalleOrdenID']))
                if d:
                    _update(self.db, 'DetalleOrdenCompra', {
                        'CantidadRecibida': float(max(Decimal('0'), _d(d.get('CantidadRecibida'))
                                                      - _d(det.get('Cantidad'))))},
                        'DetalleOrdenID=%d' % int(det['DetalleOrdenID']))
        if compra.get('OrdenCompraID'):
            orden = self.obtener_orden(compra['OrdenCompraID'])
            if not any(_d(l.get('CantidadRecibida')) > 0 for l in orden['lineas']):
                _update(self.db, 'OrdenesCompra', {'Estado': ESTADO_APROBADA},
                        'OrdenCompraID=%d' % int(compra['OrdenCompraID']))
            else:
                self._actualizar_estado_orden(compra['OrdenCompraID'])

    # ── reposicion ─────────────────────────────────────────────────────
    def productos_bajo_minimo(self):
        """Productos activos en o bajo su minimo: la requisicion que se propone sola."""
        filas = self.db.query("SELECT * FROM [Productos] WHERE Activo=True") or []
        salida = []
        for p in filas:
            minimo = _d(p.get('ExistenciaMinima'))
            if minimo > 0 and _d(p.get('ExistenciaActual')) <= minimo:
                maximo = _d(p.get('ExistenciaMaxima'))
                objetivo = maximo if maximo > minimo else minimo * 2
                p['CantidadSugerida'] = float(max(objetivo - _d(p.get('ExistenciaActual')),
                                                  Decimal('0')))
                salida.append(p)
        return salida


# ══════════════════════════════════════════════════════════════════════════
#  Consumo por receta
# ══════════════════════════════════════════════════════════════════════════
ESTADOS_PROCESADOS = ('Capturado', 'Validado')


class GestorRecetas:
    """
    Que gasta cada prueba, y descontarlo del inventario al procesarla.

    La receta tiene fecha de inicio. Al definirla no se descuenta lo que se
    hizo antes: esos reactivos ya se contaron (o no) en su momento, y cobrar
    ahora meses de pruebas viejas dejaria el inventario en negativo de golpe.
    """

    def __init__(self, db, usuario=None):
        self.db = db
        self.usuario = str(usuario or '')
        asegurar_esquema(db)

    def definir_receta(self, prueba_id, componentes):
        """componentes: [(producto_id, cantidad por prueba)]. Reemplaza la anterior."""
        limpio = []
        for producto_id, cantidad in componentes:
            cantidad = _d(cantidad)
            if cantidad <= 0:
                raise ErrorCompra('La cantidad por prueba tiene que ser mayor que cero.')
            _producto(self.db, producto_id)
            limpio.append((int(producto_id), cantidad))
        anterior = self.receta(prueba_id)
        desde = min((r['FechaDesde'] for r in anterior if r.get('FechaDesde')),
                    default=None) or datetime.now()
        self.db.execute("DELETE FROM [RecetaServicio] WHERE PruebaID=%d" % int(prueba_id))
        for producto_id, cantidad in limpio:
            _insert(self.db, 'RecetaServicio', {
                'PruebaID': int(prueba_id), 'ProductoID': producto_id,
                'Cantidad': float(cantidad),
                'FechaDesde': desde if isinstance(desde, datetime) else datetime.now()})

    def receta(self, prueba_id):
        return self.db.query(
            "SELECT r.*, p.NombreProducto, p.UnidadMedida FROM [RecetaServicio] AS r "
            "LEFT JOIN [Productos] AS p ON r.ProductoID = p.ProductoID "
            "WHERE r.PruebaID=%d" % int(prueba_id)) or []

    def _ya_consumido(self, detalle_id):
        return bool(self.db.query_one(
            "SELECT TOP 1 MovimientoID FROM [MovimientosInventario] "
            "WHERE DocumentoReferencia='DET-%d'" % int(detalle_id)))

    def consumir_pendientes(self):
        """
        Descuenta los reactivos de toda prueba procesada desde que su receta
        existe y que aun no se haya descontado. Se puede llamar las veces que
        haga falta: cada prueba se descuenta una sola vez (la referencia
        DET-<id> en el movimiento lo impide). Devuelve cuantas descontó.
        """
        recetas = {}
        for r in self.db.query("SELECT * FROM [RecetaServicio]") or []:
            recetas.setdefault(int(r['PruebaID']), []).append(r)
        if not recetas:
            return 0
        estados = ', '.join("'%s'" % e for e in ESTADOS_PROCESADOS)
        ids = ', '.join(str(i) for i in recetas)
        detalles = self.db.query(
            "SELECT d.DetalleID, d.PruebaID, d.Cantidad, s.FechaSolicitud, s.NumeroSolicitud "
            "FROM [DetalleSolicitudes] AS d INNER JOIN [Solicitudes] AS s "
            "ON d.SolicitudID = s.SolicitudID "
            "WHERE d.Estado IN (%s) AND d.PruebaID IN (%s)" % (estados, ids)) or []
        hechos = 0
        for det in detalles:
            receta = recetas[int(det['PruebaID'])]
            desde = min(r['FechaDesde'] for r in receta if r.get('FechaDesde'))
            fecha_sol = det.get('FechaSolicitud')
            if isinstance(desde, str):
                desde = datetime.fromisoformat(desde)
            if isinstance(fecha_sol, str):
                fecha_sol = datetime.fromisoformat(fecha_sol)
            if fecha_sol is None or fecha_sol < desde:
                continue
            if self._ya_consumido(det['DetalleID']):
                continue
            veces = _d(det.get('Cantidad'), '1') or Decimal('1')
            for r in receta:
                salida_inventario(self.db, r['ProductoID'], _d(r['Cantidad']) * veces,
                                  'DET-%d' % int(det['DetalleID']),
                                  'Consumo solicitud %s' % (det.get('NumeroSolicitud') or ''),
                                  self.usuario)
            hechos += 1
        if hechos:
            _log.info("Consumo por receta: %d pruebas descontadas", hechos)
        return hechos


# ══════════════════════════════════════════════════════════════════════════
#  Cuentas por pagar: pagos con historial y antiguedad de saldos
# ══════════════════════════════════════════════════════════════════════════
TRAMOS = (('Por vencer', None, 0), ('1-30', 1, 30), ('31-60', 31, 60),
          ('61-90', 61, 90), ('Mas de 90', 91, None))


def registrar_pago_cxp(db, cuenta_id, monto, forma_pago_id=None, referencia='',
                       usuario='', fecha=None):
    """
    Abona a una cuenta por pagar y deja el pago en la tabla Pagos, que es el
    historial: antes solo cambiaba el saldo y no quedaba rastro de cuando ni
    como se pago. Si la cuenta viene de una compra, la compra se actualiza
    igual. Devuelve (ok, mensaje).
    """
    asegurar_esquema(db)
    cuenta = db.query_one("SELECT * FROM [CuentasPorPagar] WHERE CuentaPagarID=%d"
                          % int(cuenta_id))
    if not cuenta:
        return False, 'Cuenta no encontrada.'
    if cuenta.get('Estado') in ('Pagada', 'Anulada'):
        return False, 'La cuenta esta %s.' % str(cuenta.get('Estado')).lower()
    monto = _q(monto)
    saldo = _q(cuenta.get('SaldoPendiente'))
    if monto <= 0:
        return False, 'El monto tiene que ser mayor que cero.'
    if monto > saldo:
        return False, 'El monto (%s) excede el saldo (%s).' % (monto, saldo)
    pagado = _q(cuenta.get('MontoPagado')) + monto
    nuevo = saldo - monto
    estado = 'Pagada' if nuevo <= 0 else 'Parcial'
    _update(db, 'CuentasPorPagar', {'MontoPagado': float(pagado),
                                    'SaldoPendiente': float(nuevo), 'Estado': estado},
            'CuentaPagarID=%d' % int(cuenta_id))
    anio = datetime.now().year
    n = db.query_one("SELECT COUNT(*) AS N FROM [Pagos] WHERE NumeroPago LIKE 'PAG-%d-%%'" % anio)
    _insert(db, 'Pagos', {
        'NumeroPago': 'PAG-%d-%06d' % (anio, int((n or {}).get('N') or 0) + 1),
        'FechaPago': fecha or datetime.now(), 'CompraID': cuenta.get('CompraID'),
        'CuentaPagarID': int(cuenta_id), 'MontoPagado': float(monto),
        'FormaPagoID': int(forma_pago_id) if forma_pago_id else None,
        'Beneficiario': str(cuenta.get('ProveedorNombre') or '')[:200],
        'NumeroReferencia': str(referencia or '')[:50],
        'UsuarioRegistro': str(usuario or '')[:50], 'FechaRegistro': datetime.now(),
        'Anulado': False})
    if cuenta.get('CompraID'):
        _update(db, 'Compras', {'MontoPagado': float(pagado), 'EstadoPago': estado},
                'CompraID=%d' % int(cuenta['CompraID']))
    return True, 'Pago registrado. Saldo pendiente: %s' % nuevo


def historial_pagos(db, cuenta_id):
    asegurar_esquema(db)
    return db.query("SELECT * FROM [Pagos] WHERE CuentaPagarID=%d AND "
                    "(Anulado IS NULL OR Anulado=False) ORDER BY PagoID" % int(cuenta_id)) or []


def antiguedad_saldos(db, hoy=None):
    """
    Saldos abiertos por proveedor y tramo de dias vencidos.
    {proveedor: {tramo: monto, 'Total': monto}}, y la fila 'TOTAL'.
    """
    hoy = hoy or date.today()
    cuentas = db.query("SELECT * FROM [CuentasPorPagar] WHERE Estado IN "
                       "('Pendiente', 'Parcial')") or []
    tabla = {}
    vacio = lambda: dict({t[0]: Decimal('0') for t in TRAMOS}, Total=Decimal('0'))
    total = vacio()
    for c in cuentas:
        saldo = _q(c.get('SaldoPendiente'))
        if saldo <= 0:
            continue
        vence = _fecha(c.get('FechaVencimiento')) or hoy
        dias = (hoy - vence).days
        tramo = next(t[0] for t in TRAMOS
                     if (t[1] is None and dias <= t[2]) or
                     (t[1] is not None and dias >= t[1] and (t[2] is None or dias <= t[2])))
        fila = tabla.setdefault(str(c.get('ProveedorNombre') or 'Sin proveedor'), vacio())
        for destino in (fila, total):
            destino[tramo] += saldo
            destino['Total'] += saldo
    tabla['TOTAL'] = total
    return tabla


def vencimientos(db, dias=7, hoy=None):
    """Cuentas abiertas que vencen en los proximos 'dias' (y las ya vencidas)."""
    hoy = hoy or date.today()
    limite = hoy + timedelta(days=dias)
    filas = db.query("SELECT * FROM [CuentasPorPagar] WHERE Estado IN "
                     "('Pendiente', 'Parcial')") or []
    salida = [c for c in filas if (_fecha(c.get('FechaVencimiento')) or hoy) <= limite]
    return sorted(salida, key=lambda c: _fecha(c.get('FechaVencimiento')) or hoy)


# ══════════════════════════════════════════════════════════════════════════
#  Libro de compras
# ══════════════════════════════════════════════════════════════════════════
def libro_compras(db, desde, hasta):
    """
    El libro de compras del periodo, desde las facturas registradas.

    Sustituye al calculo anterior, que leia CuentasPorPagar (donde no hay
    IVA) y suponia que todo monto traia IVA al 16%: una compra exenta salia
    con un credito fiscal que no existe. Aqui cada linea trae su base, su
    exento y su IVA tal como vinieron en la factura del proveedor.
    """
    asegurar_esquema(db)
    from modulos.maestros_fiscales import columnas_proveedor
    col_rif = columnas_proveedor(db).get('RIF') or 'RIF'
    desde, hasta = _fecha(desde), _fecha(hasta)
    compras = db.query(
        "SELECT c.*, p.RazonSocial, p.[%s] AS ProveedorRIF FROM [Compras] AS c "
        "LEFT JOIN [Proveedores] AS p ON c.ProveedorID = p.ProveedorID "
        "WHERE (c.Anulada IS NULL OR c.Anulada=False) "
        "AND c.FechaFacturaProveedor >= %s AND c.FechaFacturaProveedor < %s "
        "ORDER BY c.FechaFacturaProveedor, c.CompraID"
        % (col_rif, _sql(desde), _sql(hasta + timedelta(days=1)))) or []
    registros = []
    tot = {k: Decimal('0') for k in ('total_compras', 'total_exento', 'base_imponible',
                                     'iva_soportado', 'retencion_iva')}
    for i, c in enumerate(compras, 1):
        # El libro va en bolivares: una factura en divisas se convierte a la
        # tasa que se registro con ella
        tasa = _d(c.get('TasaCambio'))
        en_divisa = c.get('Moneda') not in ('VES', None, '') and tasa > 0
        a_bs = (lambda m, t=tasa: _q(_d(m) * t)) if en_divisa else (lambda m: _q(m))
        fila = {
            'n': i, 'fecha': _fecha(c.get('FechaFacturaProveedor')),
            'rif': c.get('ProveedorRIF') or '', 'razon_social': c.get('RazonSocial') or '',
            'numero_factura': c.get('NumeroFacturaProveedor') or '',
            'numero_control': c.get('NumeroControl') or '',
            'moneda_original': c.get('Moneda') or 'USD',
            'total': float(a_bs(c.get('MontoTotal'))),
            'exento': float(a_bs(c.get('MontoExento'))),
            'base_imponible': float(a_bs(c.get('BaseImponible'))),
            'iva': float(a_bs(c.get('MontoIVA'))),
            'alicuota': float(_d(c.get('TasaIVA'))),
            'retencion_iva': float(a_bs(c.get('RetencionIVA'))),
        }
        registros.append(fila)
        tot['total_compras'] += _d(fila['total'])
        tot['total_exento'] += _d(fila['exento'])
        tot['base_imponible'] += _d(fila['base_imponible'])
        tot['iva_soportado'] += _d(fila['iva'])
        tot['retencion_iva'] += _d(fila['retencion_iva'])
    return {'periodo_desde': desde, 'periodo_hasta': hasta, 'registros': registros,
            'totales': {k: float(v) for k, v in tot.items()}}

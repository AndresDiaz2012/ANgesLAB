# -*- coding: utf-8 -*-
"""
================================================================================
REPORTES FISCALES Y DE GESTION - FASE 5 DEL ERP ADMINISTRATIVO
================================================================================
FISCALES (en bolivares, desde los documentos):

  libro_ventas     una linea por documento con numero de control. Sustituye
                   al de facturacion_fiscal, que salia en la moneda de la
                   factura (dolares, casi siempre) y solo listaba facturas
                   cuyo receptor era un paciente.
  resumen_iva      debitos (ventas), creditos (compras), retenciones de IVA
                   que le hicieron al laboratorio y lo que queda a pagar o
                   de excedente: los numeros que se pasan a la declaracion.

DE GESTION (en la moneda del laboratorio, desde las solicitudes):

  Los ingresos del laboratorio hoy estan en Solicitudes -los recibos-, no
  en Facturas; por eso estos reportes leen solicitudes. Las anuladas no
  cuentan.

  ventas_por_area, ventas_por_procedencia, costo_por_prueba (lo que gasta la
  receta a costo promedio frente al precio) y estado_resultados (ingresos
  menos consumo de insumos menos gastos).

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import timedelta
from decimal import Decimal

from modulos.compras import _d, _q, _sql, _fecha, _tabla_existe, _tiene_columna


def _rango(desde, hasta):
    desde, hasta = _fecha(desde), _fecha(hasta)
    if not desde or not hasta or hasta < desde:
        raise ValueError('Indique un rango de fechas valido.')
    return desde, hasta, _sql(desde), _sql(hasta + timedelta(days=1))


def rango_de_periodo(per):
    from datetime import date
    anio, mes = int(per[:4]), int(per[4:])
    inicio = date(anio, mes, 1)
    fin = (date(anio + (mes == 12), mes % 12 + 1, 1) - timedelta(days=1))
    return inicio, fin


# ══════════════════════════════════════════════════════════════════════════
#  Libro de ventas
# ══════════════════════════════════════════════════════════════════════════
def _receptores(db, facturas):
    """{FacturaID: (documento, nombre)} con el cliente si lo hay, si no el paciente."""
    salida = {}
    clientes = {}
    if _tabla_existe(db, 'Clientes'):
        ids = {int(f['ClienteID']) for f in facturas if f.get('ClienteID')}
        if ids:
            for c in db.query("SELECT * FROM [Clientes] WHERE ClienteID IN (%s)"
                              % ', '.join(map(str, ids))) or []:
                clientes[int(c['ClienteID'])] = (c.get('Documento') or '', c.get('RazonSocial') or '')
    pac_ids = {int(f['PacienteID']) for f in facturas if f.get('PacienteID')}
    pacientes = {}
    if pac_ids:
        for p in db.query("SELECT PacienteID, TipoDocumento, NumeroDocumento, Nombres, Apellidos "
                          "FROM [Pacientes] WHERE PacienteID IN (%s)" % ', '.join(map(str, pac_ids))) or []:
            num = str(p.get('NumeroDocumento') or '')
            if num and not num[:1].isalpha():
                num = '%s-%s' % ((p.get('TipoDocumento') or 'V')[:1], num)
            pacientes[int(p['PacienteID'])] = (num, ('%s %s' % (p.get('Nombres') or '',
                                                                p.get('Apellidos') or '')).strip())
    for f in facturas:
        cli = clientes.get(int(f.get('ClienteID') or 0))
        salida[int(f['FacturaID'])] = cli or pacientes.get(int(f.get('PacienteID') or 0), ('', ''))
    return salida


def _retenciones_iva_por_factura(db, ids):
    if not ids or not _tabla_existe(db, 'RetencionesRecibidas'):
        return {}
    filas = db.query("SELECT FacturaID, SUM(MontoRetenido) AS T FROM [RetencionesRecibidas] "
                     "WHERE Tipo='IVA' AND (Anulada IS NULL OR Anulada=False) AND FacturaID IN (%s) "
                     "GROUP BY FacturaID" % ', '.join(map(str, ids))) or []
    return {int(f['FacturaID']): _q(f.get('T')) for f in filas}


def libro_ventas(db, desde, hasta):
    """
    El libro de ventas del periodo, en bolivares.

    Entran los documentos con numero de control (emitidos) y los anulados,
    que figuran con importes en cero. Una nota de credito resta. Una
    factura que HKA aun no emitio no esta en el libro: todavia no existe
    fiscalmente.
    """
    desde, hasta, d_sql, h_sql = _rango(desde, hasta)
    facturas = db.query(
        "SELECT * FROM [Facturas] WHERE FechaEmision >= %s AND FechaEmision < %s "
        "ORDER BY FechaEmision, FacturaID" % (d_sql, h_sql)) or []
    facturas = [f for f in facturas if f.get('NumeroControl') or f.get('Anulada')]
    receptores = _receptores(db, facturas)
    retenido = _retenciones_iva_por_factura(db, [int(f['FacturaID']) for f in facturas])
    afectadas = {}
    ids_af = {int(f['FacturaAfectadaID']) for f in facturas if f.get('FacturaAfectadaID')}
    if ids_af:
        for a in db.query("SELECT FacturaID, NumeroFactura FROM [Facturas] WHERE FacturaID IN (%s)"
                          % ', '.join(map(str, ids_af))) or []:
            afectadas[int(a['FacturaID'])] = a.get('NumeroFactura')

    registros = []
    tot = {k: Decimal('0') for k in ('total', 'exento', 'base', 'iva', 'retenido')}
    for i, f in enumerate(facturas, 1):
        moneda = str(f.get('MonedaFactura') or 'USD').upper()
        tasa = _d(f.get('TasaCambioDia'))
        en_bs = moneda in ('VES', 'BS', 'BS.') or tasa <= 0
        a_bs = (lambda m: _q(m)) if en_bs else (lambda m, t=tasa: _q(_d(m) * t))
        signo = Decimal('-1') if f.get('TipoDocumento') == 'NC' else Decimal('1')
        anulada = bool(f.get('Anulada'))
        k = Decimal('0') if anulada else signo
        doc, nombre = receptores.get(int(f['FacturaID']), ('', ''))
        fila = {
            'n': i, 'fecha': _fecha(f.get('FechaEmision')), 'rif': doc, 'razon_social': nombre,
            'tipo': 'ANULADA' if anulada else {'NC': 'NOTA DE CREDITO', 'ND': 'NOTA DE DEBITO'}
            .get(f.get('TipoDocumento'), 'FACTURA'),
            'numero_factura': f.get('NumeroFactura') or '', 'numero_control': f.get('NumeroControl') or '',
            'factura_afectada': afectadas.get(int(f.get('FacturaAfectadaID') or 0), ''),
            'total': a_bs(f.get('MontoTotal')) * k, 'exento': a_bs(f.get('MontoExento')) * k,
            'base_imponible': a_bs(f.get('BaseImponible')) * k, 'alicuota': _d(f.get('TasaIVA')),
            'iva': a_bs(f.get('MontoIVA')) * k,
            'iva_retenido': Decimal('0') if anulada else retenido.get(int(f['FacturaID']), Decimal('0')),
            'contingencia': f.get('Emisor') == 'Contingencia',
            'moneda_original': moneda, 'tasa': tasa,
        }
        registros.append(fila)
        tot['total'] += fila['total']
        tot['exento'] += fila['exento']
        tot['base'] += fila['base_imponible']
        tot['iva'] += fila['iva']
        tot['retenido'] += fila['iva_retenido']
    return {'desde': desde, 'hasta': hasta, 'registros': registros, 'totales': tot}


# ══════════════════════════════════════════════════════════════════════════
#  Resumen para la declaracion de IVA
# ══════════════════════════════════════════════════════════════════════════
def resumen_iva(db, per, excedente_anterior=0, retenciones_por_descontar=0):
    """
    Lo que va a la declaracion mensual de IVA, en bolivares.

    cuota      = debitos fiscales - creditos fiscales - excedente del mes anterior
    a pagar    = cuota (si es positiva) - retenciones de IVA que le hicieron
                 al laboratorio (las del mes + las que quedaron por descontar)

    Lo que no alcanza a descontarse pasa al mes siguiente: excedente de
    credito si la cuota es negativa, retenciones por descontar si superan
    la cuota. Es un resumen de trabajo para el contador, no la planilla.
    """
    from modulos.compras import libro_compras
    from modulos.retenciones import GestorRetenciones
    desde, hasta = rango_de_periodo(per)
    ventas = libro_ventas(db, desde, hasta)
    compras = libro_compras(db, desde, hasta)
    debitos = ventas['totales']['iva']
    creditos = _q(compras['totales']['iva_soportado'])
    ret_mes = _q(GestorRetenciones(db).resumen_periodo(per)['iva_retenido'])
    exc_ant = _q(excedente_anterior)
    ret_ant = _q(retenciones_por_descontar)
    cuota = debitos - creditos - exc_ant
    excedente_siguiente = -cuota if cuota < 0 else Decimal('0')
    cuota = max(cuota, Decimal('0'))
    retenciones = ret_mes + ret_ant
    a_pagar = max(cuota - retenciones, Decimal('0'))
    ret_siguiente = max(retenciones - cuota, Decimal('0'))
    return {
        'periodo': per,
        'ventas_exentas': ventas['totales']['exento'], 'ventas_base': ventas['totales']['base'],
        'debitos_fiscales': debitos,
        'compras_exentas': _q(compras['totales']['total_exento']),
        'compras_base': _q(compras['totales']['base_imponible']), 'creditos_fiscales': creditos,
        'excedente_anterior': exc_ant, 'cuota_tributaria': cuota,
        'retenciones_mes': ret_mes, 'retenciones_anteriores': ret_ant,
        'iva_a_pagar': a_pagar, 'excedente_siguiente': excedente_siguiente,
        'retenciones_por_descontar_siguiente': ret_siguiente,
    }


# ══════════════════════════════════════════════════════════════════════════
#  Gestion
# ══════════════════════════════════════════════════════════════════════════
def _solicitudes_validas(where_extra=''):
    return ("(s.EstadoSolicitud IS NULL OR s.EstadoSolicitud <> 'Anulada')" + where_extra)


def ventas_por_area(db, desde, hasta):
    """Pruebas vendidas e importe por area, de mayor a menor."""
    _, _, d_sql, h_sql = _rango(desde, hasta)
    filas = db.query(
        "SELECT a.NombreArea, COUNT(d.DetalleID) AS Pruebas, "
        "SUM(d.PrecioUnitario * IIF(d.Cantidad IS NULL, 1, d.Cantidad)) AS Importe "
        "FROM (([DetalleSolicitudes] AS d INNER JOIN [Solicitudes] AS s ON d.SolicitudID = s.SolicitudID) "
        "LEFT JOIN [Pruebas] AS p ON d.PruebaID = p.PruebaID) "
        "LEFT JOIN [Areas] AS a ON p.AreaID = a.AreaID "
        "WHERE s.FechaSolicitud >= %s AND s.FechaSolicitud < %s AND %s "
        "GROUP BY a.NombreArea" % (d_sql, h_sql, _solicitudes_validas())) or []
    salida = [{'area': f.get('NombreArea') or 'Sin area', 'pruebas': int(f.get('Pruebas') or 0),
               'importe': _q(f.get('Importe'))} for f in filas]
    return sorted(salida, key=lambda r: r['importe'], reverse=True)


def ventas_por_procedencia(db, desde, hasta):
    """Solicitudes e importe por procedencia (particular, ambulatorio, seguro...)."""
    _, _, d_sql, h_sql = _rango(desde, hasta)
    filas = db.query(
        "SELECT s.TipoServicio, COUNT(s.SolicitudID) AS N, SUM(s.MontoTotal) AS Importe "
        "FROM [Solicitudes] AS s WHERE s.FechaSolicitud >= %s AND s.FechaSolicitud < %s AND %s "
        "GROUP BY s.TipoServicio" % (d_sql, h_sql, _solicitudes_validas())) or []
    salida = [{'procedencia': f.get('TipoServicio') or 'Sin procedencia',
               'solicitudes': int(f.get('N') or 0), 'importe': _q(f.get('Importe'))} for f in filas]
    return sorted(salida, key=lambda r: r['importe'], reverse=True)


def costo_por_prueba(db):
    """
    Para cada prueba con receta: lo que gasta a costo promedio, su precio y
    el margen. Una prueba que cuesta mas de lo que se cobra salta a la vista.
    """
    if not _tabla_existe(db, 'RecetaServicio'):
        return []
    filas = db.query(
        "SELECT r.PruebaID, p.NombrePrueba, p.Precio, r.Cantidad, pr.PrecioPromedioCompra, "
        "pr.UltimoPrecioCompra FROM ([RecetaServicio] AS r LEFT JOIN [Pruebas] AS p "
        "ON r.PruebaID = p.PruebaID) LEFT JOIN [Productos] AS pr ON r.ProductoID = pr.ProductoID") or []
    por_prueba = {}
    for f in filas:
        unit = _d(f.get('PrecioPromedioCompra')) or _d(f.get('UltimoPrecioCompra'))
        p = por_prueba.setdefault(int(f['PruebaID']), {
            'prueba': f.get('NombrePrueba') or str(f['PruebaID']), 'precio': _q(f.get('Precio')),
            'costo': Decimal('0')})
        p['costo'] += _d(f.get('Cantidad')) * unit
    salida = []
    for p in por_prueba.values():
        p['costo'] = _q(p['costo'])
        p['margen'] = p['precio'] - p['costo']
        p['margen_pct'] = (p['margen'] * 100 / p['precio']).quantize(Decimal('0.1')) \
            if p['precio'] > 0 else None
        salida.append(p)
    return sorted(salida, key=lambda r: (r['margen_pct'] is None, r['margen_pct'] or 0))


def estado_resultados(db, desde, hasta):
    """
    Ingresos del periodo (solicitudes no anuladas, neto de descuentos) menos
    el consumo de insumos que se descontaron por receta, menos los gastos.
    Sencillo a proposito: muestra si el mes dejo o no dejo, no reemplaza la
    contabilidad del contador.
    """
    _, _, d_sql, h_sql = _rango(desde, hasta)
    col = 'MontoNeto' if _tiene_columna(db, 'Solicitudes', 'MontoNeto') else 'MontoTotal'
    ing = db.query_one("SELECT SUM(IIF(s.%s IS NULL, s.MontoTotal, s.%s)) AS T FROM [Solicitudes] AS s "
                       "WHERE s.FechaSolicitud >= %s AND s.FechaSolicitud < %s AND %s"
                       % (col, col, d_sql, h_sql, _solicitudes_validas())) or {}
    consumo = Decimal('0')
    if _tabla_existe(db, 'MovimientosInventario'):
        c = db.query_one("SELECT SUM(CostoTotal) AS T FROM [MovimientosInventario] "
                         "WHERE TipoMovimiento='Salida' AND FechaMovimiento >= %s "
                         "AND FechaMovimiento < %s" % (d_sql, h_sql)) or {}
        consumo = _q(c.get('T'))
    gastos = []
    if _tabla_existe(db, 'Gastos'):
        gastos = db.query(
            "SELECT c.Nombre, SUM(g.Monto) AS T FROM [Gastos] AS g LEFT JOIN [CategoriaGastos] AS c "
            "ON g.CategoriaGastoID = c.CategoriaID WHERE g.Fecha >= %s AND g.Fecha < %s "
            "AND (g.Anulado IS NULL OR g.Anulado=False) GROUP BY c.Nombre" % (d_sql, h_sql)) or []
    por_categoria = sorted([{'categoria': g.get('Nombre') or 'Sin categoria', 'monto': _q(g.get('T'))}
                            for g in gastos], key=lambda g: g['monto'], reverse=True)
    total_gastos = sum((g['monto'] for g in por_categoria), Decimal('0'))
    ingresos = _q(ing.get('T'))
    return {'ingresos': ingresos, 'consumo_insumos': consumo,
            'margen_bruto': ingresos - consumo, 'gastos': por_categoria,
            'total_gastos': total_gastos, 'resultado': ingresos - consumo - total_gastos}

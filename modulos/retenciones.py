# -*- coding: utf-8 -*-
"""
================================================================================
RETENCIONES RECIBIDAS - FASE 3 DEL ERP ADMINISTRATIVO
================================================================================
El laboratorio NO es agente de retencion: no retiene IVA ni ISLR a nadie y
paga a sus proveedores el total de la factura. Lo que si le pasa es lo
contrario: una aseguradora o una empresa que es agente le paga reteniendole
una parte y le entrega un comprobante.

Ese comprobante es dinero. La parte retenida no llega al banco, pero la
cuenta del cliente queda saldada por ella, y el laboratorio la descuenta
despues:

    retencion de IVA   ->  se resta del IVA a pagar en la declaracion
    retencion de ISLR  ->  anticipo del ISLR del ejercicio

Si no se registra, pasan dos cosas malas: la cuenta del cliente queda
debiendo lo que ya pago (y alguien se lo cobra dos veces), y el laboratorio
paga de mas en la declaracion porque nadie junto los comprobantes.

COMO SE APLICA

Como un abono mas a la cuenta por cobrar (desembolsos_clinica), de modo que
queda en el historial de esa cuenta y libera al paciente si la deja en cero,
pero SIN pasar por caja: no entro efectivo.

MONEDAS

El comprobante viene en bolivares. La cuenta por cobrar esta en la moneda
del laboratorio (dolares). Se convierte a la tasa de la factura si la hay,
o a la que se indique: la del dia en que se facturo, que es cuando nacio el
impuesto retenido.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.retenciones')
except Exception:  # pragma: no cover
    import logging as _logging
    _log = _logging.getLogger('angeslab.retenciones')

from modulos.compras import (_d, _q, _insert, _update, _ultimo_id, _fecha, _tabla_existe,
                             _tiene_columna)
from modulos.maestros_fiscales import normalizar_rif, rif_valido

TIPOS = ('IVA', 'ISLR')
# Porcentajes que la norma deja usar al agente sobre el IVA de la factura
PORCENTAJES_IVA = (Decimal('75'), Decimal('100'))

DDL = (
    "CREATE TABLE [RetencionesRecibidas] ([RetencionID] COUNTER PRIMARY KEY, "
    "[Tipo] TEXT(5), [NumeroComprobante] TEXT(30), [FechaComprobante] DATETIME, "
    "[Periodo] TEXT(6), [AgenteRIF] TEXT(20), [AgenteNombre] TEXT(200), "
    "[ClienteID] INTEGER, [FacturaID] INTEGER, [CuentaCobrarID] INTEGER, "
    "[NumeroFactura] TEXT(30), [BaseRetencion] DOUBLE, [ImpuestoFactura] DOUBLE, "
    "[Porcentaje] DOUBLE, [MontoRetenido] DOUBLE, [TasaCambio] DOUBLE, "
    "[MontoAplicado] DOUBLE, [Anulada] BIT, [MotivoAnulacion] TEXT(255), "
    "[Usuario] TEXT(50), [FechaRegistro] DATETIME)")


class ErrorRetencion(ValueError):
    """Un dato que impide registrar la retencion. El mensaje es para el usuario."""


def asegurar_esquema(db):
    if _tabla_existe(db, 'RetencionesRecibidas'):
        return False
    db.execute(DDL)
    _log.info("Tabla RetencionesRecibidas creada")
    return True


def periodo_de(fecha):
    return '%04d%02d' % (fecha.year, fecha.month)


class GestorRetenciones:

    def __init__(self, db, usuario='', usuario_id=0):
        self.db = db
        self.usuario = str(usuario or '')
        self.usuario_id = int(usuario_id or 0)
        asegurar_esquema(db)

    def _periodo_abierto(self, fecha, que):
        from modulos import periodos
        try:
            periodos.verificar_abierto(self.db, fecha, que)
        except periodos.PeriodoCerrado as e:
            raise ErrorRetencion(str(e))

    # ── lectura de lo que se retiene ───────────────────────────────────
    def _factura(self, factura_id):
        fila = self.db.query_one("SELECT * FROM [Facturas] WHERE FacturaID=%d" % int(factura_id))
        if not fila:
            raise ErrorRetencion('La factura %s no existe.' % factura_id)
        if fila.get('Anulada'):
            raise ErrorRetencion('La factura %s esta anulada.' % fila.get('NumeroFactura'))
        return fila

    def _cuenta(self, cuenta_id):
        fila = self.db.query_one("SELECT * FROM [CuentasPorCobrar] WHERE CuentaCobrarID=%d"
                                 % int(cuenta_id))
        if not fila:
            raise ErrorRetencion('La cuenta por cobrar %s no existe.' % cuenta_id)
        return fila

    def _cuenta_de_factura(self, factura_id):
        return self.db.query_one("SELECT TOP 1 * FROM [CuentasPorCobrar] WHERE FacturaID=%d "
                                 "ORDER BY CuentaCobrarID DESC" % int(factura_id))

    @staticmethod
    def _en_bs(monto, moneda, tasa):
        """Un importe de la factura, en bolivares."""
        if str(moneda or 'USD').upper() in ('VES', 'BS', 'BS.'):
            return _q(monto)
        return _q(_d(monto) * tasa)

    def ya_registrada(self, tipo, agente_rif, numero):
        return self.db.query_one(
            "SELECT * FROM [RetencionesRecibidas] WHERE Tipo='%s' AND AgenteRIF='%s' "
            "AND NumeroComprobante='%s' AND (Anulada IS NULL OR Anulada=False)"
            % (tipo, str(agente_rif).replace("'", "''"), str(numero).replace("'", "''")))

    def retenido_de_factura(self, factura_id, tipo):
        fila = self.db.query_one(
            "SELECT SUM(MontoRetenido) AS T FROM [RetencionesRecibidas] WHERE FacturaID=%d "
            "AND Tipo='%s' AND (Anulada IS NULL OR Anulada=False)" % (int(factura_id), tipo))
        return _q((fila or {}).get('T') or 0)

    # ── registrar ──────────────────────────────────────────────────────
    def registrar(self, datos):
        """
        datos: tipo ('IVA'/'ISLR'), numero_comprobante, fecha (dd/mm/aaaa),
               agente_rif, agente_nombre, factura_id y/o cuenta_cobrar_id,
               monto_retenido (Bs) o porcentaje (IVA: 75/100), tasa (Bs/USD,
               obligatoria si no hay factura con su tasa), cliente_id.

        Devuelve el RetencionID. Valida todo antes de escribir nada.
        """
        tipo = str(datos.get('tipo') or '').upper()
        if tipo not in TIPOS:
            raise ErrorRetencion('El tipo de retencion es IVA o ISLR.')
        numero = str(datos.get('numero_comprobante') or '').strip()
        if not numero:
            raise ErrorRetencion('Falta el numero del comprobante.')
        fecha = _fecha(datos.get('fecha')) or date.today()
        if fecha > date.today():
            raise ErrorRetencion('La fecha del comprobante no puede ser futura.')
        self._periodo_abierto(fecha, 'una retencion')
        rif = normalizar_rif(datos.get('agente_rif'))
        if not rif or not rif_valido(rif):
            raise ErrorRetencion('El RIF del agente de retencion no es valido: %s'
                                 % (datos.get('agente_rif') or '(vacio)'))
        if self.ya_registrada(tipo, rif, numero):
            raise ErrorRetencion('El comprobante %s de %s ya esta registrado.' % (numero, rif))

        factura = self._factura(datos['factura_id']) if datos.get('factura_id') else None
        cuenta = None
        if datos.get('cuenta_cobrar_id'):
            cuenta = self._cuenta(datos['cuenta_cobrar_id'])
        elif factura:
            cuenta = self._cuenta_de_factura(factura['FacturaID'])
        if not factura and not cuenta:
            raise ErrorRetencion('Indique la factura o la cuenta por cobrar retenida.')
        if tipo == 'IVA' and not factura:
            raise ErrorRetencion('Una retencion de IVA se registra contra la factura que '
                                 'llevo el IVA.')

        tasa = _d(datos.get('tasa'), '0')
        if tasa <= 0 and factura:
            tasa = _d(factura.get('TasaCambioDia'), '0')
        moneda = (factura or {}).get('MonedaFactura') or 'USD'
        if tasa <= 0 and str(moneda).upper() not in ('VES', 'BS', 'BS.'):
            raise ErrorRetencion('Indique la tasa (Bs por USD) del dia de la factura.')

        porcentaje = _d(datos.get('porcentaje'), '0')
        monto = _d(datos.get('monto_retenido'), '0')
        impuesto = Decimal('0')
        if tipo == 'IVA':
            impuesto = self._en_bs(factura.get('MontoIVA'), moneda, tasa)
            if impuesto <= 0:
                raise ErrorRetencion('La factura %s no llevo IVA: no se le puede retener IVA. '
                                     'Los servicios del laboratorio estan exentos.'
                                     % factura.get('NumeroFactura'))
            if monto <= 0:
                if porcentaje not in PORCENTAJES_IVA:
                    raise ErrorRetencion('Indique el monto retenido o el porcentaje (75 o 100).')
                monto = _q(impuesto * porcentaje / 100)
            ya = self.retenido_de_factura(factura['FacturaID'], 'IVA')
            if monto + ya > impuesto:
                raise ErrorRetencion('Lo retenido de IVA (%s Bs) supera el IVA de la factura '
                                     '(%s Bs).' % (monto + ya, impuesto))
            base = impuesto
        else:
            if factura:
                base = self._en_bs(_d(factura.get('MontoTotal')) - _d(factura.get('MontoIVA')),
                                   moneda, tasa)
            else:
                base = _q(_d(cuenta.get('MontoOriginal')) * tasa)
            if monto <= 0:
                if porcentaje <= 0:
                    raise ErrorRetencion('Indique el monto retenido o el porcentaje de ISLR.')
                monto = _q(base * porcentaje / 100)
            if monto > base:
                raise ErrorRetencion('La retencion de ISLR (%s Bs) no puede superar la base '
                                     '(%s Bs).' % (monto, base))
        monto = _q(monto)
        if monto <= 0:
            raise ErrorRetencion('El monto retenido tiene que ser mayor que cero.')
        if porcentaje <= 0 and base > 0:
            porcentaje = (monto * 100 / base).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # Lo que se rebaja de la cuenta, en su moneda
        aplicado = Decimal('0')
        if cuenta:
            if str(moneda).upper() in ('VES', 'BS', 'BS.') and tasa <= 0:
                aplicado = monto
            else:
                aplicado = _q(monto / tasa) if tasa > 0 else monto
            saldo = _q(cuenta.get('SaldoPendiente'))
            if aplicado > saldo:
                raise ErrorRetencion('La retencion (%s) supera lo que debe la cuenta (%s). '
                                     'Revise si ya se cobro.' % (aplicado, saldo))

        _insert(self.db, 'RetencionesRecibidas', {
            'Tipo': tipo, 'NumeroComprobante': numero[:30], 'FechaComprobante': fecha,
            'Periodo': periodo_de(fecha), 'AgenteRIF': rif,
            'AgenteNombre': str(datos.get('agente_nombre') or '')[:200],
            'ClienteID': int(datos['cliente_id']) if datos.get('cliente_id') else None,
            'FacturaID': int(factura['FacturaID']) if factura else None,
            'CuentaCobrarID': int(cuenta['CuentaCobrarID']) if cuenta else None,
            'NumeroFactura': str((factura or {}).get('NumeroFactura') or '')[:30],
            'BaseRetencion': float(base), 'ImpuestoFactura': float(impuesto),
            'Porcentaje': float(porcentaje), 'MontoRetenido': float(monto),
            'TasaCambio': float(tasa) if tasa > 0 else None,
            'MontoAplicado': float(aplicado), 'Anulada': False,
            'Usuario': self.usuario[:50], 'FechaRegistro': datetime.now()})
        ret_id = _ultimo_id(self.db, 'RetencionesRecibidas', 'RetencionID')

        if cuenta and aplicado > 0:
            from modulos.desembolsos_clinica import GestorDesembolsos
            gd = GestorDesembolsos(self.db)
            gd.asegurar_esquema()
            ok, msg, _ = gd.registrar_abono(
                cuenta['CuentaCobrarID'], float(aplicado), self.usuario_id,
                referencia='Comp. %s %s' % (tipo, numero), origen='Retencion %s' % tipo,
                observaciones='Comprobante %s de %s' % (numero, rif),
                registrar_en_caja=False)
            if not ok:
                # No deberia pasar (se valido el saldo), pero si pasa no puede
                # quedar una retencion registrada que no rebajo la cuenta
                self.db.execute("DELETE FROM [RetencionesRecibidas] WHERE RetencionID=%d" % ret_id)
                raise ErrorRetencion('No se pudo aplicar a la cuenta: %s' % msg)
        if factura and aplicado > 0:
            cobrado = _q(factura.get('MontoCobrado')) + aplicado
            saldo_f = max(_q(factura.get('SaldoPendiente')) - aplicado, Decimal('0'))
            _update(self.db, 'Facturas', {
                'MontoCobrado': float(cobrado), 'SaldoPendiente': float(saldo_f),
                'EstadoPago': 'Pagada' if saldo_f <= 0 else 'Parcial'},
                'FacturaID=%d' % int(factura['FacturaID']))
        _log.info("Retencion %s %s de %s registrada: %s Bs", tipo, numero, rif, monto)
        return ret_id

    # ── anular ─────────────────────────────────────────────────────────
    def anular(self, retencion_id, motivo):
        """
        Anula un comprobante mal cargado y devuelve a la cuenta lo que se le
        rebajo. Si en el medio se cobro el resto de la cuenta, la cuenta
        vuelve a quedar con saldo: es correcto, lo retenido no era real.
        """
        if not str(motivo or '').strip():
            raise ErrorRetencion('Indique el motivo de la anulacion.')
        r = self.db.query_one("SELECT * FROM [RetencionesRecibidas] WHERE RetencionID=%d"
                              % int(retencion_id))
        if not r:
            raise ErrorRetencion('La retencion no existe.')
        if r.get('Anulada'):
            raise ErrorRetencion('La retencion ya esta anulada.')
        self._periodo_abierto(_fecha(r.get('FechaComprobante')), 'la anulacion de una retencion')
        aplicado = _q(r.get('MontoAplicado'))
        if r.get('CuentaCobrarID') and aplicado > 0:
            cuenta = self._cuenta(r['CuentaCobrarID'])
            cobrado = max(_q(cuenta.get('MontoCobrado')) - aplicado, Decimal('0'))
            saldo = _q(cuenta.get('SaldoPendiente')) + aplicado
            campos = {'MontoCobrado': float(cobrado), 'SaldoPendiente': float(saldo),
                      'Estado': 'Pendiente' if cobrado <= 0 else 'Parcial'}
            if _tiene_columna(self.db, 'CuentasPorCobrar', 'FechaLiberacion'):
                # Vuelve a deber: ya no esta liberada
                campos['FechaLiberacion'] = None
            _update(self.db, 'CuentasPorCobrar', campos,
                    'CuentaCobrarID=%d' % int(r['CuentaCobrarID']))
            if _tabla_existe(self.db, 'AbonosCuentaCobrar'):
                _insert(self.db, 'AbonosCuentaCobrar', {
                    'CuentaCobrarID': int(r['CuentaCobrarID']),
                    'PacienteID': cuenta.get('PacienteID'),
                    'NombrePaciente': cuenta.get('NombrePaciente'),
                    'FechaAbono': datetime.now(), 'Monto': -float(aplicado),
                    'SaldoAnterior': float(_q(cuenta.get('SaldoPendiente'))),
                    'SaldoPosterior': float(saldo),
                    'Referencia': 'Anula comp. %s %s' % (r['Tipo'], r['NumeroComprobante']),
                    'Origen': 'Anulacion retencion', 'UsuarioID': self.usuario_id,
                    'Observaciones': str(motivo)[:255]})
        if r.get('FacturaID') and aplicado > 0:
            f = self.db.query_one("SELECT * FROM [Facturas] WHERE FacturaID=%d" % int(r['FacturaID']))
            if f:
                cobrado = max(_q(f.get('MontoCobrado')) - aplicado, Decimal('0'))
                _update(self.db, 'Facturas', {
                    'MontoCobrado': float(cobrado),
                    'SaldoPendiente': float(_q(f.get('SaldoPendiente')) + aplicado),
                    'EstadoPago': 'Pendiente' if cobrado <= 0 else 'Parcial'},
                    'FacturaID=%d' % int(r['FacturaID']))
        _update(self.db, 'RetencionesRecibidas', {'Anulada': True,
                                                  'MotivoAnulacion': str(motivo)[:255]},
                'RetencionID=%d' % int(retencion_id))

    # ── reportes ───────────────────────────────────────────────────────
    def listar(self, periodo=None, tipo=None, incluir_anuladas=False):
        where = []
        if periodo:
            where.append("Periodo='%s'" % str(periodo).replace("'", ''))
        if tipo:
            where.append("Tipo='%s'" % str(tipo).replace("'", ''))
        if not incluir_anuladas:
            where.append('(Anulada IS NULL OR Anulada=False)')
        sql = 'SELECT * FROM [RetencionesRecibidas]'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        return self.db.query(sql + ' ORDER BY FechaComprobante, RetencionID') or []

    def resumen_periodo(self, periodo):
        """
        Lo que va a la declaracion del mes: IVA retenido (se resta del IVA a
        pagar) e ISLR retenido (anticipo del ejercicio), en bolivares.
        """
        filas = self.listar(periodo)
        total = {t: Decimal('0') for t in TIPOS}
        for f in filas:
            total[f['Tipo']] += _q(f.get('MontoRetenido'))
        return {'periodo': periodo, 'iva_retenido': float(total['IVA']),
                'islr_retenido': float(total['ISLR']), 'comprobantes': len(filas),
                'detalle': filas}

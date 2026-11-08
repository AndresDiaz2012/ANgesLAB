# -*- coding: utf-8 -*-
"""
Pruebas de las retenciones recibidas (fase 3).

El laboratorio no es agente de retencion: solo recibe comprobantes de sus
clientes agentes. Lo que se protege:
  - que la retencion rebaje la cuenta del cliente (si no, se le cobra dos
    veces lo que ya pago) y no pase por caja (no entro efectivo);
  - que no se registre dos veces el mismo comprobante, ni se retenga mas
    IVA del que tuvo la factura, ni IVA a una factura exenta;
  - que el total del mes sea el que va a la declaracion.

Las tablas Facturas y CuentasPorCobrar tienen las columnas de la base de la
clinica.
"""

import os
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import retenciones as rt
from tests.sqlite_access import DBAccessEnSqlite

AGENTE = 'G-20000110-0'
HOY = date.today()
PERIODO = '%04d%02d' % (HOY.year, HOY.month)


def base():
    db = DBAccessEnSqlite()
    db.execute("CREATE TABLE Facturas (FacturaID INTEGER PRIMARY KEY, NumeroFactura TEXT, "
               "NumeroControl TEXT, FechaEmision TEXT, PacienteID INTEGER, MontoIVA REAL, "
               "MontoTotal REAL, MontoCobrado REAL, SaldoPendiente REAL, EstadoPago TEXT, "
               "MonedaFactura TEXT, TasaCambioDia REAL, Anulada INTEGER)")
    db.execute("CREATE TABLE CuentasPorCobrar (CuentaCobrarID INTEGER PRIMARY KEY, "
               "PacienteID INTEGER, NombrePaciente TEXT, FacturaID INTEGER, SolicitudID INTEGER, "
               "FechaEmision TEXT, FechaVencimiento TEXT, MontoOriginal REAL, MontoCobrado REAL, "
               "SaldoPendiente REAL, Estado TEXT, DiasVencida INTEGER, TipoProcedencia TEXT, "
               "Observaciones TEXT)")
    # Factura 1: servicios exentos, 100 USD, tasa 40
    db.execute("INSERT INTO Facturas VALUES (1, 'FAC-1', '00-1', '2026-11-01', 5, 0, 100, 0, 100, "
               "'Pendiente', 'USD', 40, 0)")
    db.execute("INSERT INTO CuentasPorCobrar VALUES (1, 5, 'PEREZ JUAN', 1, NULL, '2026-11-01', "
               "NULL, 100, 0, 100, 'Pendiente', 0, 'Seguro', '')")
    # Factura 2: un producto gravado, 10 + 1.6 IVA USD, tasa 40
    db.execute("INSERT INTO Facturas VALUES (2, 'FAC-2', '00-2', '2026-11-01', 6, 1.6, 11.6, 0, 11.6, "
               "'Pendiente', 'USD', 40, 0)")
    db.execute("INSERT INTO CuentasPorCobrar VALUES (2, 6, 'GOMEZ ANA', 2, NULL, '2026-11-01', "
               "NULL, 11.6, 0, 11.6, 'Pendiente', 0, 'Empresa', '')")
    return db


class Base(unittest.TestCase):

    def setUp(self):
        self.db = base()
        self.g = rt.GestorRetenciones(self.db, usuario='admin', usuario_id=1)

    def islr(self, **extra):
        d = {'tipo': 'ISLR', 'numero_comprobante': 'R-001', 'fecha': HOY.strftime('%d/%m/%Y'),
             'agente_rif': AGENTE, 'agente_nombre': 'Seguros X', 'factura_id': 1,
             'porcentaje': 2}
        d.update(extra)
        return d

    def cuenta(self, cid=1):
        return self.db.query_one("SELECT * FROM CuentasPorCobrar WHERE CuentaCobrarID=%d" % cid)


class TestIslr(Base):

    def test_rebaja_la_cuenta_en_dolares(self):
        self.g.registrar(self.islr())
        # 2% de 100 USD = 2 USD = 80 Bs
        r = self.g.listar()[0]
        self.assertEqual((r['MontoRetenido'], r['MontoAplicado']), (80.0, 2.0))
        c = self.cuenta()
        self.assertEqual((c['SaldoPendiente'], c['MontoCobrado'], c['Estado']), (98.0, 2.0, 'Parcial'))

    def test_queda_en_el_historial_y_no_en_caja(self):
        self.g.registrar(self.islr())
        abono = self.db.query_one("SELECT * FROM AbonosCuentaCobrar")
        self.assertEqual(abono['Origen'], 'Retencion ISLR')
        self.assertIn('R-001', abono['Referencia'])
        with self.assertRaises(Exception):
            self.db.query("SELECT * FROM MovimientosCaja")  # nunca se toco

    def test_actualiza_la_factura(self):
        self.g.registrar(self.islr())
        f = self.db.query_one("SELECT * FROM Facturas WHERE FacturaID=1")
        self.assertEqual((f['SaldoPendiente'], f['EstadoPago']), (98.0, 'Parcial'))

    def test_monto_explicito(self):
        self.g.registrar(self.islr(porcentaje=None, monto_retenido=120))
        self.assertEqual(self.g.listar()[0]['Porcentaje'], 3.0)

    def test_no_supera_la_base(self):
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.islr(porcentaje=None, monto_retenido=5000))

    def test_contra_cuenta_sin_factura_pide_tasa(self):
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.islr(factura_id=None, cuenta_cobrar_id=1))
        self.g.registrar(self.islr(factura_id=None, cuenta_cobrar_id=1, tasa=40))
        self.assertEqual(self.cuenta()['SaldoPendiente'], 98.0)


class TestIva(Base):

    def iva(self, **extra):
        d = self.islr(tipo='IVA', numero_comprobante='20261100000001', factura_id=2,
                      porcentaje=75)
        d.update(extra)
        return d

    def test_setenta_y_cinco_por_ciento_del_iva(self):
        self.g.registrar(self.iva())
        r = self.g.listar()[0]
        # IVA 1.6 USD = 64 Bs; 75% = 48 Bs = 1.20 USD
        self.assertEqual((r['ImpuestoFactura'], r['MontoRetenido'], r['MontoAplicado']),
                         (64.0, 48.0, 1.2))
        self.assertEqual(self.cuenta(2)['SaldoPendiente'], 10.4)

    def test_factura_exenta_no_admite_retencion_de_iva(self):
        with self.assertRaises(rt.ErrorRetencion) as ctx:
            self.g.registrar(self.iva(factura_id=1))
        self.assertIn('exento', str(ctx.exception))

    def test_porcentaje_no_permitido(self):
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.iva(porcentaje=50))

    def test_no_se_retiene_mas_iva_del_que_hubo(self):
        self.g.registrar(self.iva())
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.iva(numero_comprobante='20261100000002', porcentaje=None,
                                      monto_retenido=20))

    def test_iva_sin_factura_no(self):
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.iva(factura_id=None, cuenta_cobrar_id=2))


class TestValidaciones(Base):

    def test_comprobante_repetido(self):
        self.g.registrar(self.islr())
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.islr())

    def test_rif_del_agente_invalido(self):
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.islr(agente_rif='J-12345678-0'))

    def test_fecha_futura(self):
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.islr(fecha=(HOY + timedelta(days=2)).strftime('%d/%m/%Y')))

    def test_no_mas_de_lo_que_se_debe(self):
        self.db.execute("UPDATE CuentasPorCobrar SET SaldoPendiente=1 WHERE CuentaCobrarID=1")
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.islr())
        self.assertEqual(self.g.listar(), [])

    def test_factura_anulada(self):
        self.db.execute("UPDATE Facturas SET Anulada=1 WHERE FacturaID=1")
        with self.assertRaises(rt.ErrorRetencion):
            self.g.registrar(self.islr())


class TestAnular(Base):

    def test_devuelve_el_saldo_y_libera_el_comprobante(self):
        rid = self.g.registrar(self.islr())
        self.g.anular(rid, 'Comprobante de otra factura')
        c = self.cuenta()
        self.assertEqual((c['SaldoPendiente'], c['MontoCobrado'], c['Estado']), (100.0, 0.0, 'Pendiente'))
        self.assertEqual(self.g.listar(), [])
        # el mismo numero se puede volver a cargar bien
        self.g.registrar(self.islr())

    def test_queda_rastro_en_el_historial(self):
        rid = self.g.registrar(self.islr())
        self.g.anular(rid, 'error')
        montos = [a['Monto'] for a in self.db.query("SELECT * FROM AbonosCuentaCobrar ORDER BY AbonoID")]
        self.assertEqual(montos, [2.0, -2.0])

    def test_sin_motivo_no(self):
        rid = self.g.registrar(self.islr())
        with self.assertRaises(rt.ErrorRetencion):
            self.g.anular(rid, '')


class TestResumenDelMes(Base):

    def test_totales_para_la_declaracion(self):
        self.g.registrar(self.islr())
        self.g.registrar(self.islr(tipo='IVA', numero_comprobante='C-9', factura_id=2, porcentaje=100))
        r = self.g.resumen_periodo(PERIODO)
        self.assertEqual((r['iva_retenido'], r['islr_retenido'], r['comprobantes']), (64.0, 80.0, 2))

    def test_otro_mes_vacio(self):
        self.g.registrar(self.islr())
        self.assertEqual(self.g.resumen_periodo('202001')['comprobantes'], 0)


if __name__ == '__main__':
    unittest.main()

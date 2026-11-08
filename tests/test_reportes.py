# -*- coding: utf-8 -*-
"""
Pruebas de la fase 5: libro de ventas, resumen de IVA, cierre de periodo y
reportes de gestion.
"""

import os
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import reportes as rp, periodos, compras as cp
from modulos.retenciones import GestorRetenciones, ErrorRetencion
from modulos.maestros_fiscales import GestorClientes
from tests.test_emision import base as base_facturas
from tests.test_compras import base_del_instalador

HOY = date.today()
MES = '%04d%02d' % (HOY.year, HOY.month)
MES_PASADO = (HOY.replace(day=1) - timedelta(days=1))


def factura(db, fecha, total, iva=0.0, control='00-1', tipo='Factura', anulada=0, cliente=None,
            afectada=None, tasa=40):
    db.execute("INSERT INTO Facturas (NumeroFactura, NumeroControl, FechaEmision, PacienteID, "
               "BaseImponible, TasaIVA, MontoIVA, MontoExento, MontoTotal, MonedaFactura, TasaCambioDia, "
               "TipoDocumento, Anulada, ClienteID, FacturaAfectadaID) VALUES ('FAC-%s', %s, '%s 09:00:00', 5, "
               "%s, %s, %s, %s, %s, 'USD', %s, '%s', %d, %s, %s)"
               % (control, "'%s'" % control if control else 'NULL', fecha, 10 if iva else 0,
                  16 if iva else 0, iva, total - (10 + iva if iva else 0), total, tasa, tipo, anulada,
                  cliente or 'NULL', afectada or 'NULL'))
    return db.query_one("SELECT MAX(FacturaID) AS I FROM Facturas")['I']


class TestLibroVentas(unittest.TestCase):

    def setUp(self):
        self.db = base_facturas()
        self.f1 = factura(self.db, HOY, 100, control='00-1')
        self.f2 = factura(self.db, HOY, 111.6, iva=1.6, control='00-2')

    def libro(self):
        return rp.libro_ventas(self.db, HOY, HOY)

    def test_en_bolivares(self):
        r = self.libro()['registros']
        self.assertEqual([x['total'] for x in r], [Decimal('4000.00'), Decimal('4464.00')])
        self.assertEqual(r[1]['iva'], Decimal('64.00'))
        self.assertEqual(self.libro()['totales']['iva'], Decimal('64.00'))

    def test_receptor_cliente_o_paciente(self):
        cid = GestorClientes(self.db).crear({'TipoCliente': 'Aseguradora', 'Documento': 'G-20000303-0',
                                             'RazonSocial': 'Seguros X', 'DomicilioFiscal': 'X'})
        factura(self.db, HOY, 50, control='00-3', cliente=cid)
        r = self.libro()['registros']
        self.assertEqual((r[0]['rif'], r[0]['razon_social']), ('V-12345678', 'JUAN PEREZ'))
        self.assertEqual((r[2]['rif'], r[2]['razon_social']), ('G-20000303-0', 'Seguros X'))

    def test_sin_numero_de_control_no_esta(self):
        factura(self.db, HOY, 70, control=None)
        self.assertEqual(len(self.libro()['registros']), 2)

    def test_anulada_figura_en_cero(self):
        factura(self.db, HOY, 70, control='00-4', anulada=1)
        r = self.libro()['registros'][-1]
        self.assertEqual((r['tipo'], r['total']), ('ANULADA', Decimal('0')))

    def test_nota_de_credito_resta(self):
        factura(self.db, HOY, 10, control='00-5', tipo='NC', afectada=self.f1)
        r = self.libro()['registros'][-1]
        self.assertEqual((r['tipo'], r['total'], r['factura_afectada']),
                         ('NOTA DE CREDITO', Decimal('-400.00'), 'FAC-00-1'))

    def test_retencion_de_iva_recibida(self):
        self.db.execute("CREATE TABLE CuentasPorCobrar (CuentaCobrarID INTEGER PRIMARY KEY, "
                        "FacturaID INTEGER, SaldoPendiente REAL, MontoCobrado REAL, MontoOriginal REAL, "
                        "Estado TEXT, PacienteID INTEGER, NombrePaciente TEXT)")
        GestorRetenciones(self.db).registrar({
            'tipo': 'IVA', 'numero_comprobante': 'C1', 'agente_rif': 'G-20000110-0',
            'factura_id': self.f2, 'porcentaje': 75})
        self.assertEqual(self.libro()['registros'][1]['iva_retenido'], Decimal('48.00'))

    def test_compatibilidad_de_facturacion_fiscal(self):
        from modulos.facturacion_fiscal import FacturacionFiscal
        filas = FacturacionFiscal(self.db).generar_libro_ventas(HOY, HOY)
        self.assertEqual(filas[1]['impuesto'], 64.0)


class TestResumenIva(unittest.TestCase):

    def test_debitos_creditos_retenciones(self):
        db = base_del_instalador()
        # ventas: Facturas de la base de emision en la misma base
        for ddl in base_facturas().query("SELECT sql FROM sqlite_master WHERE type='table' "
                                         "AND name IN ('Facturas','Pacientes')"):
            db.execute(ddl['sql'])
        db.execute("INSERT INTO Pacientes VALUES (5, 'JUAN', 'PEREZ', 'V', '1', '', '', '')")
        factura(db, HOY, 111.6, iva=1.6, control='00-9')            # debito 64 Bs
        from modulos.modulo_administrativo import GestorProveedores
        pid = GestorProveedores(db).crear_proveedor({'RazonSocial': 'P', 'RIF': 'G-20000303-0'})
        cp.GestorCompras(db).registrar_compra(
            {'proveedor_id': pid, 'numero': '1', 'numero_control': '1', 'tasa': 40},
            [{'producto_id': 1, 'cantidad': 1, 'precio': 5, 'iva': 16}])   # credito 0.8 USD = 32 Bs
        r = rp.resumen_iva(db, MES, excedente_anterior=10)
        self.assertEqual((r['debitos_fiscales'], r['creditos_fiscales'], r['cuota_tributaria'],
                          r['iva_a_pagar']), (Decimal('64.00'), Decimal('32.00'), Decimal('22.00'),
                                              Decimal('22.00')))

    def test_excedente_y_retenciones_pasan_al_mes_siguiente(self):
        db = base_facturas()
        r = rp.resumen_iva(db, MES, excedente_anterior=5, retenciones_por_descontar=3)
        self.assertEqual((r['iva_a_pagar'], r['excedente_siguiente'],
                          r['retenciones_por_descontar_siguiente']),
                         (Decimal('0'), Decimal('5.00'), Decimal('3.00')))


class TestCierreDePeriodo(unittest.TestCase):

    def setUp(self):
        self.db = base_del_instalador()
        from modulos.modulo_administrativo import GestorProveedores
        self.pid = GestorProveedores(self.db).crear_proveedor({'RazonSocial': 'P', 'RIF': 'G-20000303-0'})
        self.per = periodos.periodo(MES_PASADO)

    def compra(self, fecha, numero='1'):
        return cp.GestorCompras(self.db).registrar_compra(
            {'proveedor_id': self.pid, 'numero': numero, 'numero_control': numero, 'tasa': 40,
             'fecha': fecha.strftime('%d/%m/%Y')},
            [{'producto_id': 1, 'cantidad': 1, 'precio': 5}])

    def test_mes_cerrado_no_recibe_compras(self):
        periodos.cerrar(self.db, self.per, 'admin')
        with self.assertRaises(cp.ErrorCompra) as ctx:
            self.compra(MES_PASADO)
        self.assertIn('cerrado', str(ctx.exception))
        self.compra(HOY)  # el mes en curso sigue abierto

    def test_ni_anulaciones_de_ese_mes(self):
        r = self.compra(MES_PASADO)
        periodos.cerrar(self.db, self.per)
        with self.assertRaises(cp.ErrorCompra):
            cp.GestorCompras(self.db).anular_compra(r['compra_id'], 'x')

    def test_reabrir_exige_motivo_y_lo_guarda(self):
        periodos.cerrar(self.db, self.per)
        with self.assertRaises(ValueError):
            periodos.reabrir(self.db, self.per, '')
        periodos.reabrir(self.db, self.per, 'Declaracion sustitutiva', 'admin')
        self.assertFalse(periodos.esta_cerrado(self.db, MES_PASADO))
        self.assertEqual(periodos.listar(self.db)[0]['MotivoReapertura'], 'Declaracion sustitutiva')
        self.compra(MES_PASADO)

    def test_no_se_cierra_el_mes_en_curso(self):
        with self.assertRaises(ValueError):
            periodos.cerrar(self.db, MES)

    def test_periodo_mal_escrito(self):
        with self.assertRaises(ValueError):
            periodos.cerrar(self.db, '2026-10')

    def test_retencion_en_mes_cerrado(self):
        db = base_facturas()
        periodos.cerrar(db, self.per)
        with self.assertRaises(ErrorRetencion):
            GestorRetenciones(db).registrar({'tipo': 'ISLR', 'numero_comprobante': 'X',
                                             'fecha': MES_PASADO.strftime('%d/%m/%Y'),
                                             'agente_rif': 'G-20000110-0', 'cuenta_cobrar_id': 1,
                                             'monto_retenido': 1, 'tasa': 40})


def base_gestion():
    db = base_del_instalador()
    db.execute("CREATE TABLE Areas (AreaID INTEGER PRIMARY KEY, NombreArea TEXT)")
    db.execute("INSERT INTO Areas VALUES (1, 'Hematologia'), (2, 'Quimica')")
    db.execute("CREATE TABLE Pruebas (PruebaID INTEGER PRIMARY KEY, NombrePrueba TEXT, AreaID INTEGER, Precio REAL)")
    db.execute("INSERT INTO Pruebas VALUES (7, 'Glicemia', 2, 5), (8, 'Hematologia completa', 1, 8)")
    db.execute("DROP TABLE Solicitudes")
    db.execute("CREATE TABLE Solicitudes (SolicitudID INTEGER PRIMARY KEY, FechaSolicitud TEXT, "
               "NumeroSolicitud TEXT, MontoTotal REAL, MontoNeto REAL, TipoServicio TEXT, EstadoSolicitud TEXT)")
    db.execute("DROP TABLE DetalleSolicitudes")
    db.execute("CREATE TABLE DetalleSolicitudes (DetalleID INTEGER PRIMARY KEY, SolicitudID INTEGER, "
               "PruebaID INTEGER, PrecioUnitario REAL, Cantidad INTEGER, Estado TEXT)")
    hoy = HOY.strftime('%Y-%m-%d 08:00:00')
    db.execute("INSERT INTO Solicitudes VALUES (1, '%s', 'S1', 13, 13, 'Particular', NULL)" % hoy)
    db.execute("INSERT INTO Solicitudes VALUES (2, '%s', 'S2', 5, 4, NULL, 'Completada')" % hoy)
    db.execute("INSERT INTO Solicitudes VALUES (3, '%s', 'S3', 99, 99, NULL, 'Anulada')" % hoy)
    db.execute("INSERT INTO DetalleSolicitudes VALUES (10, 1, 7, 5, 1, 'Validado'), "
               "(11, 1, 8, 8, 1, 'Validado'), (20, 2, 7, 5, 1, 'Validado'), (30, 3, 8, 99, 1, 'Pendiente')")
    db.execute("CREATE TABLE CategoriaGastos (CategoriaID INTEGER PRIMARY KEY, Nombre TEXT)")
    db.execute("INSERT INTO CategoriaGastos VALUES (1, 'Alquiler')")
    db.execute("CREATE TABLE Gastos (GastoID INTEGER PRIMARY KEY, Fecha TEXT, CategoriaGastoID INTEGER, "
               "Monto REAL, Anulado INTEGER)")
    db.execute("INSERT INTO Gastos VALUES (1, '%s', 1, 6, 0), (2, '%s', 1, 50, 1)" % (hoy, hoy))
    return db


class TestGestion(unittest.TestCase):

    def setUp(self):
        self.db = base_gestion()

    def test_ventas_por_area_sin_anuladas(self):
        r = rp.ventas_por_area(self.db, HOY, HOY)
        self.assertEqual([(x['area'], x['pruebas'], x['importe']) for x in r],
                         [('Quimica', 2, Decimal('10.00')), ('Hematologia', 1, Decimal('8.00'))])

    def test_ventas_por_procedencia(self):
        r = rp.ventas_por_procedencia(self.db, HOY, HOY)
        self.assertEqual({x['procedencia']: x['importe'] for x in r},
                         {'Particular': Decimal('13.00'), 'Sin procedencia': Decimal('5.00')})

    def test_costo_por_prueba(self):
        g = cp.GestorCompras(self.db)
        from modulos.modulo_administrativo import GestorProveedores
        pid = GestorProveedores(self.db).crear_proveedor({'RazonSocial': 'P', 'RIF': 'G-20000303-0'})
        g.registrar_compra({'proveedor_id': pid, 'numero': '1', 'numero_control': '1', 'tasa': 40},
                           [{'producto_id': 1, 'cantidad': 10, 'precio': 6}])
        cp.GestorRecetas(self.db).definir_receta(7, [(1, 1)])
        r = rp.costo_por_prueba(self.db)[0]
        self.assertEqual((r['prueba'], r['costo'], r['margen'], r['margen_pct']),
                         ('Glicemia', Decimal('6.00'), Decimal('-1.00'), Decimal('-20.0')))

    def test_estado_de_resultados(self):
        r = rp.estado_resultados(self.db, HOY, HOY)
        self.assertEqual((r['ingresos'], r['total_gastos'], r['resultado']),
                         (Decimal('17.00'), Decimal('6.00'), Decimal('11.00')))


if __name__ == '__main__':
    unittest.main()

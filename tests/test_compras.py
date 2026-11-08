# -*- coding: utf-8 -*-
"""
Pruebas de la fase 2: compras, inventario, consumo por receta y cuentas por
pagar.

El criterio de la fase en la especificacion es el que se prueba aqui ante
todo: una compra registrada aparece en inventario, libro de compras y
cuentas por pagar con los mismos montos.

La base imita la del instalador (Proveedores con NumeroDocumento, Telefono1,
PersonaContacto; Compras, DetalleCompras y Pagos ya creadas y vacias), que
es la que corre en la clinica.
"""

import os
import sys
import unittest
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import compras as cp
from modulos.modulo_administrativo import GestorProveedores
from tests.sqlite_access import DBAccessEnSqlite

RIF_SENIAT = 'G-20000303-0'
RIF_BCV = 'G-20000110-0'
HOY = date.today()


def base_del_instalador():
    db = DBAccessEnSqlite()
    db.execute("CREATE TABLE Proveedores (ProveedorID INTEGER PRIMARY KEY AUTOINCREMENT, "
               "CodigoProveedor TEXT, RazonSocial TEXT, NombreComercial TEXT, TipoDocumento TEXT, "
               "NumeroDocumento TEXT, Direccion TEXT, Ciudad TEXT, Estado TEXT, Telefono1 TEXT, "
               "Telefono2 TEXT, Email TEXT, PersonaContacto TEXT, CondicionesPago TEXT, "
               "DiasCredito INTEGER, LimiteCredito REAL, Observaciones TEXT, Activo INTEGER, "
               "FechaRegistro TEXT)")
    db.execute("CREATE TABLE Productos (ProductoID INTEGER PRIMARY KEY AUTOINCREMENT, "
               "CodigoProducto TEXT, NombreProducto TEXT, TipoProducto TEXT, UnidadMedida TEXT, "
               "ExistenciaActual REAL, ExistenciaMinima REAL, ExistenciaMaxima REAL, "
               "UltimoPrecioCompra REAL, PrecioPromedioCompra REAL, Lote TEXT, "
               "FechaVencimiento TEXT, Activo INTEGER, FechaCreacion TEXT)")
    db.execute("CREATE TABLE MovimientosInventario (MovimientoID INTEGER PRIMARY KEY AUTOINCREMENT, "
               "ProductoID INTEGER, TipoMovimiento TEXT, Cantidad REAL, CostoUnitario REAL, "
               "CostoTotal REAL, ExistenciaAnterior REAL, ExistenciaNueva REAL, Motivo TEXT, "
               "DocumentoReferencia TEXT, Lote TEXT, FechaVencimiento TEXT, FechaMovimiento TEXT, "
               "UsuarioRegistra TEXT)")
    db.execute("CREATE TABLE CuentasPorPagar (CuentaPagarID INTEGER PRIMARY KEY AUTOINCREMENT, "
               "ProveedorNombre TEXT, ProveedorRIF TEXT, NumeroDocumento TEXT, FechaEmision TEXT, "
               "FechaVencimiento TEXT, MontoOriginal REAL, MontoPagado REAL, SaldoPendiente REAL, "
               "CategoriaGastoID INTEGER, Estado TEXT, Observaciones TEXT)")
    db.execute("CREATE TABLE Solicitudes (SolicitudID INTEGER PRIMARY KEY, FechaSolicitud TEXT, "
               "NumeroSolicitud TEXT)")
    db.execute("CREATE TABLE DetalleSolicitudes (DetalleID INTEGER PRIMARY KEY, SolicitudID INTEGER, "
               "PruebaID INTEGER, Cantidad INTEGER, Estado TEXT)")
    for tabla in ('Compras', 'DetalleCompras', 'Pagos'):
        db.execute(cp.DDL[tabla])
    for nombre, minimo in (('Reactivo glucosa', 2), ('Tubo tapa roja', 100)):
        db.execute("INSERT INTO Productos (NombreProducto, TipoProducto, UnidadMedida, "
                   "ExistenciaActual, ExistenciaMinima, ExistenciaMaxima, UltimoPrecioCompra, "
                   "PrecioPromedioCompra, Activo) VALUES ('%s', 'Reactivo', 'Und', 0, %d, 0, 0, 0, 1)"
                   % (nombre, minimo))
    return db


class Base(unittest.TestCase):

    def setUp(self):
        self.db = base_del_instalador()
        gp = GestorProveedores(self.db)
        self.prov = gp.crear_proveedor({'RazonSocial': 'Reactivos C.A.', 'RIF': RIF_SENIAT,
                                        'DiasCredito': 15})
        self.otro = gp.crear_proveedor({'RazonSocial': 'Otro C.A.', 'RIF': RIF_BCV})
        self.g = cp.GestorCompras(self.db, usuario='compras')

    def factura(self, **extra):
        f = {'proveedor_id': self.prov, 'numero': 'F-100', 'numero_control': '00-00001234',
             'fecha': HOY.strftime('%d/%m/%Y'), 'moneda': 'USD', 'tasa': 40}
        f.update(extra)
        return f

    def producto(self, pid):
        return self.db.query_one("SELECT * FROM Productos WHERE ProductoID=%d" % pid)


class TestProveedoresEnLaBaseDelInstalador(Base):
    """El esquema del instalador no tiene columna RIF: la fase 1 fallaba aqui."""

    def test_el_rif_se_guarda_en_numero_documento(self):
        fila = self.db.query_one("SELECT * FROM Proveedores WHERE ProveedorID=%d" % self.prov)
        self.assertEqual(fila['NumeroDocumento'], RIF_SENIAT)
        self.assertEqual(fila['TipoDocumento'], 'RIF')

    def test_hacia_afuera_se_llama_rif(self):
        p = GestorProveedores(self.db).obtener_proveedor(self.prov)
        self.assertEqual(p['RIF'], RIF_SENIAT)
        self.assertEqual(p['DiasCredito'], 15)

    def test_busca_por_rif_en_la_columna_real(self):
        self.assertEqual(len(GestorProveedores(self.db).listar_proveedores(busqueda='20000303')), 1)

    def test_rif_repetido_se_rechaza(self):
        with self.assertRaises(ValueError):
            GestorProveedores(self.db).crear_proveedor({'RazonSocial': 'X', 'RIF': RIF_SENIAT})


class TestCostoPromedio(unittest.TestCase):

    def test_pondera_por_cantidad(self):
        self.assertEqual(cp.costo_promedio(10, 2, 30, 4), Decimal('3.5000'))

    def test_sin_existencia_es_el_costo_nuevo(self):
        self.assertEqual(cp.costo_promedio(0, 99, 5, 4), Decimal('4'))

    def test_existencia_negativa_no_pondera(self):
        self.assertEqual(cp.costo_promedio(-3, 2, 5, 4), Decimal('4'))


class TestOrdenes(Base):

    def test_crear_y_aprobar_por_otro_usuario(self):
        oid = self.g.crear_orden(self.prov, [{'producto_id': 1, 'cantidad': 10, 'precio': 5}])
        orden = self.g.obtener_orden(oid)
        self.assertEqual(orden['Estado'], cp.ESTADO_BORRADOR)
        self.assertTrue(orden['NumeroOrden'].startswith('OC-'))
        cp.GestorCompras(self.db, usuario='admin').aprobar_orden(oid)
        self.assertEqual(self.g.obtener_orden(oid)['Estado'], cp.ESTADO_APROBADA)

    def test_quien_crea_no_aprueba(self):
        oid = self.g.crear_orden(self.prov, [{'producto_id': 1, 'cantidad': 1, 'precio': 5}])
        with self.assertRaises(cp.ErrorCompra):
            self.g.aprobar_orden(oid)

    def test_lineas_invalidas(self):
        for mala in ({'producto_id': 1, 'cantidad': 0, 'precio': 5},
                     {'producto_id': 1, 'cantidad': 1, 'precio': -1},
                     {'producto_id': 1, 'cantidad': 1, 'precio': 1, 'iva': 12},
                     {'producto_id': 999, 'cantidad': 1, 'precio': 1}):
            with self.assertRaises(cp.ErrorCompra):
                self.g.crear_orden(self.prov, [mala])

    def test_anular_sin_recepcion(self):
        oid = self.g.crear_orden(self.prov, [{'producto_id': 1, 'cantidad': 1, 'precio': 5}])
        self.g.anular_orden(oid, 'Pedido duplicado')
        self.assertEqual(self.g.obtener_orden(oid)['Estado'], cp.ESTADO_ANULADA)


class TestCompraCuadraEnLosTresSitios(Base):
    """El criterio de la fase 2."""

    def setUp(self):
        super().setUp()
        self.r = self.g.registrar_compra(self.factura(), [
            {'producto_id': 1, 'cantidad': 4, 'precio': 25, 'iva': 16,
             'lote': 'L1', 'vence': (HOY + timedelta(days=200)).strftime('%d/%m/%Y')},
            {'producto_id': 2, 'cantidad': 100, 'precio': 0.5, 'iva': 0},
        ])

    def test_factura(self):
        c = self.g.obtener_compra(self.r['compra_id'])
        self.assertEqual((c['BaseImponible'], c['MontoIVA'], c['MontoExento'], c['MontoTotal']),
                         (100.0, 16.0, 50.0, 166.0))
        self.assertTrue(c['NumeroCompra'].startswith('COM-'))
        self.assertEqual(len(c['lineas']), 2)

    def test_inventario(self):
        self.assertEqual(self.producto(1)['ExistenciaActual'], 4)
        self.assertEqual(self.producto(1)['PrecioPromedioCompra'], 25)
        self.assertEqual(self.producto(2)['ExistenciaActual'], 100)
        lote = self.db.query_one("SELECT * FROM LotesProducto WHERE ProductoID=1")
        self.assertEqual((lote['Lote'], lote['CantidadActual']), ('L1', 4))

    def test_el_iva_no_entra_al_costo(self):
        self.assertEqual(self.producto(1)['UltimoPrecioCompra'], 25)

    def test_cuenta_por_pagar_por_el_total_con_vencimiento_del_proveedor(self):
        cxp = self.db.query_one("SELECT * FROM CuentasPorPagar WHERE CuentaPagarID=%d"
                                % self.r['cuenta_pagar_id'])
        self.assertEqual(cxp['MontoOriginal'], 166.0)
        self.assertEqual(cxp['ProveedorRIF'], RIF_SENIAT)
        self.assertEqual(cxp['FechaVencimiento'][:10], str(HOY + timedelta(days=15)))

    def test_libro_de_compras_en_bolivares(self):
        libro = cp.libro_compras(self.db, HOY, HOY)
        fila = libro['registros'][0]
        self.assertEqual((fila['base_imponible'], fila['iva'], fila['exento'], fila['total']),
                         (4000.0, 640.0, 2000.0, 6640.0))
        self.assertEqual((fila['rif'], fila['numero_control']), (RIF_SENIAT, '00-00001234'))
        self.assertEqual(libro['totales']['iva_soportado'], 640.0)

    def test_misma_factura_dos_veces_no(self):
        with self.assertRaises(cp.ErrorCompra):
            self.g.registrar_compra(self.factura(), [{'producto_id': 1, 'cantidad': 1, 'precio': 1}])


class TestFacturaEnBolivares(Base):

    def test_inventario_en_dolares_y_libro_en_bolivares(self):
        r = self.g.registrar_compra(self.factura(moneda='VES', tasa=40), [
            {'producto_id': 1, 'cantidad': 2, 'precio': 1000, 'iva': 16}])
        self.assertEqual(self.producto(1)['UltimoPrecioCompra'], 25)
        cxp = self.db.query_one("SELECT * FROM CuentasPorPagar WHERE CuentaPagarID=%d"
                                % r['cuenta_pagar_id'])
        self.assertEqual(cxp['MontoOriginal'], 58.0)  # 2320 Bs / 40
        self.assertEqual(cp.libro_compras(self.db, HOY, HOY)['registros'][0]['total'], 2320.0)


class TestValidacionesDeLaFactura(Base):

    def test_sin_numero_de_control(self):
        with self.assertRaises(cp.ErrorCompra) as ctx:
            self.g.registrar_compra(self.factura(numero_control=''),
                                    [{'producto_id': 1, 'cantidad': 1, 'precio': 1}])
        self.assertIn('control', str(ctx.exception))

    def test_sin_tasa(self):
        with self.assertRaises(cp.ErrorCompra):
            self.g.registrar_compra(self.factura(tasa=0),
                                    [{'producto_id': 1, 'cantidad': 1, 'precio': 1}])

    def test_fecha_futura(self):
        manana = (HOY + timedelta(days=1)).strftime('%d/%m/%Y')
        with self.assertRaises(cp.ErrorCompra):
            self.g.registrar_compra(self.factura(fecha=manana),
                                    [{'producto_id': 1, 'cantidad': 1, 'precio': 1}])

    def test_nada_se_guarda_si_falla_la_validacion(self):
        with self.assertRaises(cp.ErrorCompra):
            self.g.registrar_compra(self.factura(), [{'producto_id': 1, 'cantidad': 1, 'precio': 1},
                                                     {'producto_id': 1, 'cantidad': -1, 'precio': 1}])
        self.assertEqual(self.db.query("SELECT * FROM Compras"), [])
        self.assertEqual(self.producto(1)['ExistenciaActual'], 0)


class TestRecepcionContraOrden(Base):

    def setUp(self):
        super().setUp()
        self.oid = self.g.crear_orden(self.prov, [
            {'producto_id': 1, 'cantidad': 10, 'precio': 25, 'iva': 16},
            {'producto_id': 2, 'cantidad': 200, 'precio': 0.5}])
        cp.GestorCompras(self.db, usuario='admin').aprobar_orden(self.oid)
        self.det = {int(d['ProductoID']): int(d['DetalleOrdenID'])
                    for d in self.g.obtener_orden(self.oid)['lineas']}

    def linea(self, pid, cant, precio, iva=0):
        return {'producto_id': pid, 'cantidad': cant, 'precio': precio, 'iva': iva,
                'detalle_orden_id': self.det[pid]}

    def test_recepcion_parcial_y_luego_completa(self):
        self.g.registrar_compra(self.factura(orden_id=self.oid),
                                [self.linea(1, 4, 25, 16)])
        self.assertEqual(self.g.obtener_orden(self.oid)['Estado'], cp.ESTADO_PARCIAL)
        self.g.registrar_compra(self.factura(orden_id=self.oid, numero='F-101'),
                                [self.linea(1, 6, 25, 16), self.linea(2, 200, 0.5)])
        self.assertEqual(self.g.obtener_orden(self.oid)['Estado'], cp.ESTADO_RECIBIDA)

    def test_precio_distinto_avisa_y_no_guarda(self):
        r = self.g.registrar_compra(self.factura(orden_id=self.oid), [self.linea(1, 4, 27, 16)])
        self.assertIsNone(r['compra_id'])
        self.assertTrue(any('precio' in a for a in r['avisos']))
        self.assertEqual(self.db.query("SELECT * FROM Compras"), [])

    def test_confirmando_los_avisos_se_guarda(self):
        r = self.g.registrar_compra(self.factura(orden_id=self.oid),
                                    [self.linea(1, 12, 25, 16)], confirmar_avisos=True)
        self.assertIsNotNone(r['compra_id'])
        self.assertTrue(any('quedaban' in a for a in r['avisos']))

    def test_orden_de_otro_proveedor(self):
        with self.assertRaises(cp.ErrorCompra):
            self.g.registrar_compra(self.factura(proveedor_id=self.otro, orden_id=self.oid),
                                    [self.linea(1, 1, 25, 16)])

    def test_orden_sin_aprobar_no_recibe(self):
        oid = self.g.crear_orden(self.prov, [{'producto_id': 1, 'cantidad': 1, 'precio': 1}])
        with self.assertRaises(cp.ErrorCompra):
            self.g.registrar_compra(self.factura(orden_id=oid),
                                    [{'producto_id': 1, 'cantidad': 1, 'precio': 1}])

    def test_no_se_anula_una_orden_con_mercancia(self):
        self.g.registrar_compra(self.factura(orden_id=self.oid), [self.linea(1, 4, 25, 16)])
        with self.assertRaises(cp.ErrorCompra):
            self.g.anular_orden(self.oid, 'ya no')


class TestAnularCompra(Base):

    def setUp(self):
        super().setUp()
        self.r = self.g.registrar_compra(self.factura(), [
            {'producto_id': 1, 'cantidad': 4, 'precio': 25, 'iva': 16, 'lote': 'L1'}])

    def test_deshace_inventario_y_cuenta(self):
        self.g.anular_compra(self.r['compra_id'], 'Cargada al proveedor equivocado')
        self.assertEqual(self.producto(1)['ExistenciaActual'], 0)
        cxp = self.db.query_one("SELECT * FROM CuentasPorPagar")
        self.assertEqual(cxp['Estado'], 'Anulada')
        self.assertEqual(cp.libro_compras(self.db, HOY, HOY)['registros'], [])

    def test_con_pagos_no_se_anula(self):
        cp.registrar_pago_cxp(self.db, self.r['cuenta_pagar_id'], 10)
        with self.assertRaises(cp.ErrorCompra):
            self.g.anular_compra(self.r['compra_id'], 'x')

    def test_con_mercancia_consumida_no_se_anula(self):
        cp.salida_inventario(self.db, 1, 1, 'MANUAL', 'consumo')
        with self.assertRaises(cp.ErrorCompra):
            self.g.anular_compra(self.r['compra_id'], 'x')

    def test_la_misma_factura_se_puede_volver_a_cargar_bien(self):
        self.g.anular_compra(self.r['compra_id'], 'mal cargada')
        r = self.g.registrar_compra(self.factura(), [
            {'producto_id': 1, 'cantidad': 4, 'precio': 25, 'iva': 16}])
        self.assertIsNotNone(r['compra_id'])


class TestSalidaFefo(Base):

    def test_sale_primero_el_que_vence_antes(self):
        f = lambda d: (HOY + timedelta(days=d)).strftime('%d/%m/%Y')
        self.g.registrar_compra(self.factura(), [
            {'producto_id': 1, 'cantidad': 5, 'precio': 10, 'lote': 'TARDE', 'vence': f(300)},
            {'producto_id': 1, 'cantidad': 5, 'precio': 10, 'lote': 'PRONTO', 'vence': f(30)}])
        salidas = cp.salida_inventario(self.db, 1, 7, 'X', 'prueba')
        self.assertEqual([(l, float(c)) for l, c in salidas], [('PRONTO', 5.0), ('TARDE', 2.0)])
        self.assertEqual(self.producto(1)['ExistenciaActual'], 3)

    def test_sin_lotes_suficientes_sale_igual_y_queda_negativo(self):
        cp.salida_inventario(self.db, 1, 2, 'X', 'prueba')
        self.assertEqual(self.producto(1)['ExistenciaActual'], -2)


class TestConsumoPorReceta(Base):

    def setUp(self):
        super().setUp()
        self.g.registrar_compra(self.factura(), [
            {'producto_id': 1, 'cantidad': 10, 'precio': 25, 'lote': 'L1'}])
        self.rec = cp.GestorRecetas(self.db, usuario='lab')

    def solicitud(self, sid, fecha, estado='Capturado', prueba=7):
        self.db.execute("INSERT INTO Solicitudes VALUES (%d, '%s', 'S-%d')"
                        % (sid, fecha.strftime('%Y-%m-%d %H:%M:%S'), sid))
        self.db.execute("INSERT INTO DetalleSolicitudes VALUES (%d, %d, %d, 1, '%s')"
                        % (sid * 10, sid, prueba, estado))

    def test_descuenta_una_sola_vez(self):
        self.rec.definir_receta(7, [(1, 0.5)])
        self.solicitud(1, datetime.now() + timedelta(seconds=1))
        self.assertEqual(self.rec.consumir_pendientes(), 1)
        self.assertEqual(self.rec.consumir_pendientes(), 0)
        self.assertEqual(self.producto(1)['ExistenciaActual'], 9.5)

    def test_no_descuenta_lo_anterior_a_la_receta(self):
        self.solicitud(1, datetime.now() - timedelta(days=30))
        self.rec.definir_receta(7, [(1, 1)])
        self.assertEqual(self.rec.consumir_pendientes(), 0)

    def test_solo_pruebas_procesadas(self):
        self.rec.definir_receta(7, [(1, 1)])
        self.solicitud(1, datetime.now() + timedelta(seconds=1), estado='Pendiente')
        self.assertEqual(self.rec.consumir_pendientes(), 0)

    def test_redefinir_conserva_la_fecha_de_inicio(self):
        self.rec.definir_receta(7, [(1, 1)])
        desde = self.rec.receta(7)[0]['FechaDesde']
        self.rec.definir_receta(7, [(1, 2), (2, 1)])
        self.assertEqual({r['FechaDesde'] for r in self.rec.receta(7)}, {desde})

    def test_cantidad_cero_no(self):
        with self.assertRaises(cp.ErrorCompra):
            self.rec.definir_receta(7, [(1, 0)])


class TestCuentasPorPagar(Base):

    def setUp(self):
        super().setUp()
        self.r = self.g.registrar_compra(self.factura(), [
            {'producto_id': 1, 'cantidad': 4, 'precio': 25}])
        self.cid = self.r['cuenta_pagar_id']

    def test_abonos_con_historial_y_compra_al_dia(self):
        ok, _ = cp.registrar_pago_cxp(self.db, self.cid, 40, referencia='T-1', usuario='admin')
        self.assertTrue(ok)
        cp.registrar_pago_cxp(self.db, self.cid, 60, referencia='T-2')
        pagos = cp.historial_pagos(self.db, self.cid)
        self.assertEqual([p['MontoPagado'] for p in pagos], [40.0, 60.0])
        self.assertEqual(self.db.query_one("SELECT Estado FROM CuentasPorPagar")['Estado'], 'Pagada')
        compra = self.g.obtener_compra(self.r['compra_id'])
        self.assertEqual((compra['MontoPagado'], compra['EstadoPago']), (100.0, 'Pagada'))

    def test_no_se_paga_de_mas(self):
        ok, msg = cp.registrar_pago_cxp(self.db, self.cid, 101)
        self.assertFalse(ok)
        self.assertEqual(cp.historial_pagos(self.db, self.cid), [])

    def test_cuenta_pagada_no_recibe_mas(self):
        cp.registrar_pago_cxp(self.db, self.cid, 100)
        ok, _ = cp.registrar_pago_cxp(self.db, self.cid, 1)
        self.assertFalse(ok)

    def test_antiguedad_de_saldos(self):
        self.db.execute("UPDATE CuentasPorPagar SET FechaVencimiento='%s'"
                        % (HOY - timedelta(days=45)))
        tabla = cp.antiguedad_saldos(self.db)
        self.assertEqual(tabla['Reactivos C.A.']['31-60'], Decimal('100.00'))
        self.assertEqual(tabla['TOTAL']['Total'], Decimal('100.00'))

    def test_vencimientos_de_la_semana(self):
        self.assertEqual(cp.vencimientos(self.db, dias=7), [])
        self.assertEqual(len(cp.vencimientos(self.db, dias=15)), 1)


class TestReposicion(Base):

    def test_propone_lo_que_esta_bajo_minimo(self):
        nombres = [p['NombreProducto'] for p in self.g.productos_bajo_minimo()]
        self.assertEqual(nombres, ['Reactivo glucosa', 'Tubo tapa roja'])
        self.g.registrar_compra(self.factura(), [{'producto_id': 2, 'cantidad': 500, 'precio': 1}])
        self.assertEqual([p['ProductoID'] for p in self.g.productos_bajo_minimo()], [1])


class TestEsquema(unittest.TestCase):

    def test_idempotente(self):
        db = base_del_instalador()
        self.assertTrue(cp.asegurar_esquema(db))
        self.assertEqual(cp.asegurar_esquema(db), [])


if __name__ == '__main__':
    unittest.main()

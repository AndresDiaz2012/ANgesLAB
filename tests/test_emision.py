# -*- coding: utf-8 -*-
"""
Pruebas de la emision de documentos fiscales (fase 4, sin la conexion real
con HKA).

HKA se simula con un servidor falso que responde como dice su wiki: asi se
prueba lo que depende de ANgesLAB -que documento se arma, que se hace con
cada respuesta, que nunca se emita dos veces- sin credenciales. Cuando HKA
entregue el ambiente de pruebas, lo que difiera se corrige contra el.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import emision as em
from modulos.maestros_fiscales import GestorClientes, asegurar_esquema as esquema_maestros
from tests.sqlite_access import DBAccessEnSqlite


def base():
    db = DBAccessEnSqlite()
    db.execute("CREATE TABLE Facturas (FacturaID INTEGER PRIMARY KEY AUTOINCREMENT, NumeroFactura TEXT, "
               "NumeroControl TEXT, FechaEmision TEXT, PacienteID INTEGER, ResponsablePagoID INTEGER, "
               "SolicitudID INTEGER, TipoFactura TEXT, CondicionPago TEXT, SubTotal REAL, "
               "MontoDescuento REAL, PorcentajeDescuento REAL, BaseImponible REAL, TasaIVA REAL, "
               "MontoIVA REAL, MontoExento REAL, MontoTotal REAL, MontoIGTF REAL, TasaIGTF REAL, "
               "AplicaIGTF INTEGER, MonedaFactura TEXT, TasaCambioDia REAL, MontoTotalBs REAL, "
               "MontoTotalUSD REAL, TipoDocumento TEXT, FacturaAfectadaID INTEGER, EstadoPago TEXT, "
               "MontoCobrado REAL, SaldoPendiente REAL, EstaExonerada INTEGER, NumeroExoneracion TEXT, "
               "FechaExoneracion TEXT, Observaciones TEXT, UsuarioEmite INTEGER, FechaRegistro TEXT, "
               "Anulada INTEGER, MotivoAnulacion TEXT, FechaAnulacion TEXT)")
    db.execute("CREATE TABLE DetalleFacturas (DetalleFacturaID INTEGER PRIMARY KEY AUTOINCREMENT, "
               "FacturaID INTEGER, PruebaID INTEGER, Descripcion TEXT, Cantidad INTEGER, "
               "PrecioUnitario REAL, Descuento REAL, SubTotal REAL, MontoIVA REAL, Total REAL, "
               "Exonerada INTEGER)")
    db.execute("CREATE TABLE Pacientes (PacienteID INTEGER PRIMARY KEY, Nombres TEXT, Apellidos TEXT, "
               "TipoDocumento TEXT, NumeroDocumento TEXT, DireccionCompleta TEXT, Telefono1 TEXT, Email TEXT)")
    db.execute("INSERT INTO Pacientes VALUES (5, 'JUAN', 'PEREZ', 'V', '12345678', 'Caracas', '0414', 'j@x.com')")
    db.execute("CREATE TABLE Proveedores (ProveedorID INTEGER PRIMARY KEY, RazonSocial TEXT)")
    db.execute("CREATE TABLE Pruebas (PruebaID INTEGER PRIMARY KEY, NombrePrueba TEXT)")
    db.execute("CREATE TABLE ConfiguracionLaboratorio (ID INTEGER PRIMARY KEY, NombreLaboratorio TEXT, "
               "RIF TEXT, IVAPorDefecto REAL, TipoContribuyente TEXT, IGTFActivo INTEGER)")
    db.execute("INSERT INTO ConfiguracionLaboratorio VALUES (1, 'LAB', 'J-00000000-0', 16, 'Ordinario', 0)")
    em.asegurar_esquema(db)
    esquema_maestros(db)
    return db


def factura(db, iva=0.0, moneda='USD', tasa=40, cliente=None, tipo='Factura', afectada=None):
    db.execute("INSERT INTO Facturas (NumeroFactura, FechaEmision, PacienteID, CondicionPago, "
               "MontoIVA, MontoTotal, MonedaFactura, TasaCambioDia, TipoDocumento, FacturaAfectadaID, "
               "ClienteID, Anulada) VALUES ('FAC-2027-%06d', '2027-04-20 10:15:30', 5, 'Contado', %s, %s, "
               "'%s', %s, '%s', %s, %s, 0)"
               % (len(db.query("SELECT * FROM Facturas")) + 1, iva, 100 + iva, moneda, tasa, tipo,
                  afectada or 'NULL', cliente or 'NULL'))
    fid = db.query_one("SELECT MAX(FacturaID) AS I FROM Facturas")['I']
    db.execute("INSERT INTO DetalleFacturas (FacturaID, PruebaID, Descripcion, Cantidad, SubTotal, "
               "MontoIVA, Total, Exonerada) VALUES (%d, 7, 'Hematologia', 1, 100, 0, 100, 0)" % fid)
    if iva:
        db.execute("INSERT INTO DetalleFacturas (FacturaID, PruebaID, Descripcion, Cantidad, SubTotal, "
                   "MontoIVA, Total, Exonerada) VALUES (%d, NULL, 'Frasco', 1, 10, %s, %s, 0)"
                   % (fid, iva, 10 + iva))
    return fid


class Respuesta:
    def __init__(self, estado, datos):
        self.status_code, self._datos = estado, datos

    def json(self):
        return self._datos


class HKAFalso:
    """Responde como el wiki de HKA. Cuenta las llamadas para ver que se manda."""

    def __init__(self):
        self.llamadas = []
        self.rechazar = None
        self.caido = False
        self.token_vencido_una_vez = False
        self.control = 0

    def post(self, url, json=None, headers=None, timeout=None):
        ruta = url.split('.ve', 1)[-1]
        self.llamadas.append((ruta, json, headers))
        if self.caido:
            raise ConnectionError('sin red')
        if ruta == '/api/Autenticacion':
            if json != {'usuario': 'lab', 'clave': 'secreta'}:
                return Respuesta(200, {'codigo': '403', 'mensaje': 'Usuario o clave invalidos'})
            return Respuesta(200, {'codigo': 200, 'mensaje': 'Token generado exitosamente',
                                   'token': 'T' * 300,
                                   'expiracion': (datetime.now(timezone.utc) + timedelta(hours=12)).strftime('%Y-%m-%dT%H:%M:%SZ')})
        if self.token_vencido_una_vez:
            self.token_vencido_una_vez = False
            return Respuesta(401, {'codigo': '401', 'mensaje': 'token vencido'})
        if ruta == '/api/Emision':
            if self.rechazar:
                return Respuesta(200, {'codigo': '203', 'mensaje': 'Documento con errores',
                                       'validaciones': [self.rechazar]})
            self.control += 1
            ident = json['documentoElectronico']['encabezado']['identificacionDocumento']
            return Respuesta(200, {'codigo': '200', 'mensaje': 'Documento procesado correctamente',
                                   'resultado': {'imprentaDigital': 'HKA', 'autorizado': True,
                                                 'serie': 'A', 'tipoDocumento': ident['tipoDocumento'],
                                                 'numeroDocumento': ident['numeroDocumento'],
                                                 'numeroControl': '00-%08d' % self.control,
                                                 'fechaAsignacion': '20/04/2027',
                                                 'horaAsignacion': '10:16:01 am'}})
        if ruta == '/api/Anular':
            return Respuesta(200, {'codigo': '200', 'mensaje': 'Documento anulado'})
        return Respuesta(404, {'codigo': '404'})

    def rutas(self):
        return [r for r, _, _ in self.llamadas]


def emisor(http):
    return em.EmisorHKA(em.URL_DEMO_HKA, 'lab', 'secreta', serie='A', http=http)


class TestDocumento(unittest.TestCase):

    def setUp(self):
        self.db = base()

    def test_receptor_es_el_paciente_si_no_hay_cliente(self):
        doc = em.documento_fiscal(self.db, factura(self.db))
        self.assertEqual((doc['receptor']['numero_id'], doc['receptor']['razon_social']),
                         ('V-12345678', 'JUAN PEREZ'))

    def test_receptor_es_el_cliente_si_lo_hay(self):
        cid = GestorClientes(self.db).crear({'TipoCliente': 'Aseguradora', 'Documento': 'G-20000303-0',
                                             'RazonSocial': 'Seguros X', 'DomicilioFiscal': 'Valencia'})
        doc = em.documento_fiscal(self.db, factura(self.db, cliente=cid))
        self.assertEqual((doc['receptor']['numero_id'], doc['receptor']['direccion']),
                         ('G-20000303-0', 'Valencia'))

    def test_importes_en_bolivares_y_divisa_de_referencia(self):
        doc = em.documento_fiscal(self.db, factura(self.db, iva=1.6))
        self.assertEqual((doc['exento'], doc['gravado'], doc['iva'], doc['total']),
                         (Decimal('4000.00'), Decimal('400.00'), Decimal('64.00'), Decimal('4464.00')))
        self.assertEqual(doc['total_divisa'], Decimal('101.60'))

    def test_sin_tasa_no_se_arma(self):
        with self.assertRaises(em.ErrorDatos):
            em.documento_fiscal(self.db, factura(self.db, tasa=0))

    def test_nota_de_credito_sin_afectada(self):
        with self.assertRaises(em.ErrorDatos):
            em.documento_fiscal(self.db, factura(self.db, tipo='NC'))

    def test_receptor_juridico_sin_domicilio(self):
        self.db.execute("INSERT INTO Clientes (TipoCliente, Documento, RazonSocial, Activo) "
                        "VALUES ('Juridica', 'G-20000303-0', 'X', 1)")
        with self.assertRaises(em.ErrorDatos) as ctx:
            em.documento_fiscal(self.db, factura(self.db, cliente=1))
        self.assertIn('domicilio', str(ctx.exception))


class TestJsonHKA(unittest.TestCase):

    def test_estructura_del_wiki(self):
        db = base()
        j = em.json_hka(em.documento_fiscal(db, factura(db, iva=1.6)), serie='A')['documentoElectronico']
        ident = j['encabezado']['identificacionDocumento']
        self.assertEqual((ident['tipoDocumento'], ident['numeroDocumento'], ident['transaccionId']),
                         ('01', '2027000001', 'ANGESLAB-1'))
        self.assertEqual((ident['fechaEmision'], ident['horaEmision']), ('20/04/2027', '10:15:30 am'))
        comp = j['encabezado']['comprador']
        self.assertEqual((comp['tipoIdentificacion'], comp['numeroIdentificacion']), ('V', '12345678'))
        tot = j['encabezado']['totales']
        self.assertEqual((tot['montoExentoTotal'], tot['montoGravadoTotal'], tot['totalIVA'],
                          tot['totalAPagar']), ('4000.00', '400.00', '64.00', '4464.00'))
        self.assertEqual([i['codigoImpuesto'] for i in j['detallesItems']], ['E', 'G'])
        self.assertEqual([i['indicadorBienoServicio'] for i in j['detallesItems']], ['2', '1'])
        self.assertEqual(j['encabezado']['totalesOtraMoneda']['moneda'], 'USD')


class TestEmisionConHKA(unittest.TestCase):

    def setUp(self):
        self.db = base()
        self.hka = HKAFalso()
        self.g = em.GestorEmision(self.db, emisor(self.hka))
        self.fid = factura(self.db)

    def fila(self):
        return self.db.query_one("SELECT * FROM Facturas WHERE FacturaID=%d" % self.fid)

    def test_emite_y_guarda_el_numero_de_hka(self):
        self.assertEqual(self.g.emitir(self.fid), '00-00000001')
        f = self.fila()
        self.assertEqual((f['EstadoEmision'], f['Emisor'], f['SerieControl'], f['TransaccionID']),
                         ('Emitida', 'HKA', 'A', 'ANGESLAB-%d' % self.fid))

    def test_una_emitida_no_se_vuelve_a_mandar(self):
        self.g.emitir(self.fid)
        self.g.emitir(self.fid)
        self.assertEqual(self.hka.rutas().count('/api/Emision'), 1)

    def test_el_token_se_reutiliza(self):
        self.g.emitir(self.fid)
        self.g.emitir(factura(self.db))
        self.assertEqual(self.hka.rutas().count('/api/Autenticacion'), 1)

    def test_token_vencido_se_renueva_una_vez(self):
        self.g.emisor._obtener_token()
        self.hka.token_vencido_una_vez = True
        self.assertEqual(self.g.emitir(self.fid), '00-00000001')
        self.assertEqual(self.hka.rutas().count('/api/Autenticacion'), 2)

    def test_rechazo_queda_registrado_y_se_puede_reenviar(self):
        self.hka.rechazar = 'RIF del comprador invalido'
        with self.assertRaises(em.ErrorRechazo):
            self.g.emitir(self.fid)
        self.assertEqual(self.fila()['EstadoEmision'], 'Rechazada')
        self.assertIn('RIF del comprador', self.fila()['MensajeEmisor'])
        self.hka.rechazar = None
        self.g.emitir(self.fid)
        f = self.fila()
        self.assertEqual((f['EstadoEmision'], f['IntentosEmision']), ('Emitida', 2))

    def test_sin_conexion_queda_pendiente_con_el_mismo_identificador(self):
        self.hka.caido = True
        with self.assertRaises(em.ErrorConexion):
            self.g.emitir(self.fid)
        self.assertEqual(self.fila()['EstadoEmision'], 'Pendiente')
        self.hka.caido = False
        self.g.emitir(self.fid)
        enviados = [j['documentoElectronico']['encabezado']['identificacionDocumento']['transaccionId']
                    for r, j, _ in self.hka.llamadas if r == '/api/Emision' and j]
        self.assertEqual(set(enviados), {'ANGESLAB-%d' % self.fid})

    def test_clave_equivocada(self):
        g = em.GestorEmision(self.db, em.EmisorHKA(em.URL_DEMO_HKA, 'lab', 'mala', http=self.hka))
        with self.assertRaises(em.ErrorRechazo) as ctx:
            g.emitir(self.fid)
        self.assertIn('usuario y la clave', str(ctx.exception))

    def test_anular_una_emitida_avisa_a_hka(self):
        self.g.emitir(self.fid)
        self.g.anular(self.fid, 'Error en el monto')
        self.assertIn('/api/Anular', self.hka.rutas())
        self.assertEqual(self.fila()['EstadoEmision'], 'Anulada')
        with self.assertRaises(em.ErrorDatos):
            self.g.emitir(self.fid)

    def test_pendientes(self):
        self.hka.caido = True
        with self.assertRaises(em.ErrorConexion):
            self.g.emitir(self.fid)
        self.assertEqual([f['FacturaID'] for f in self.g.pendientes()], [self.fid])


class TestContingencia(unittest.TestCase):

    def setUp(self):
        self.db = base()
        self.hka = HKAFalso()
        self.hka.caido = True
        self.g = em.GestorEmision(self.db, emisor(self.hka))
        self.fid = factura(self.db)

    def test_sin_rango_de_talonario_no_emite(self):
        with self.assertRaises(em.ErrorRechazo):
            self.g.emitir(self.fid, contingencia=True)

    def test_con_talonario_toma_su_numero(self):
        from modulos import rangos_control
        rangos_control.registrar_rango(self.db, 1, 50)
        self.assertEqual(self.g.emitir(self.fid, contingencia=True), '00-00000001')
        f = self.db.query_one("SELECT * FROM Facturas WHERE FacturaID=%d" % self.fid)
        self.assertEqual((f['EstadoEmision'], f['Emisor']), ('Emitida', 'Contingencia'))


class TestConfiguracion(unittest.TestCase):

    def test_la_clave_no_se_guarda_en_claro(self):
        db = base()
        em.guardar_emisor_hka(db, 'lab', 'secreta')
        fila = em.emisor_activo(db)
        self.assertNotEqual(fila['ClaveCifrada'], 'secreta')
        self.assertEqual(fila['URLBase'], em.URL_DEMO_HKA)
        self.assertEqual(em.EmisorHKA.desde_configuracion(fila, http=HKAFalso()).clave, 'secreta')

    def test_produccion_exige_su_url(self):
        with self.assertRaises(em.ErrorDatos):
            em.guardar_emisor_hka(base(), 'lab', 'x', ambiente='Produccion')

    def test_sin_emisor_es_local(self):
        db = base()
        self.assertFalse(em.usa_emisor_digital(db))
        self.assertIsInstance(em.GestorEmision(db).emisor, em.EmisorLocal)


class TestCrearFacturaConHKA(unittest.TestCase):
    """crear_factura no toma numero de control si emite HKA, y guarda el cliente."""

    def _crear(self, db, cliente_id=None):
        from modulos.facturacion_fiscal import FacturacionFiscal
        ff = FacturacionFiscal(db)
        return ff.crear_factura({'paciente_id': 5, 'cliente_id': cliente_id, 'moneda_factura': 'USD'},
                                [{'prueba_id': 7, 'descripcion': 'Hematologia', 'precio': 100,
                                  'cantidad': 1, 'tasa_iva': 0}], 1)

    def test_con_hka_nace_pendiente_y_sin_control(self):
        db = base()
        em.guardar_emisor_hka(db, 'lab', 'secreta')
        fid, _ = self._crear(db)
        f = db.query_one("SELECT * FROM Facturas WHERE FacturaID=%d" % fid)
        self.assertEqual((f['NumeroControl'], f['EstadoEmision'], f['Emisor']), (None, 'Pendiente', 'HKA'))

    def test_sin_hka_queda_emitida_local(self):
        db = base()
        fid, _ = self._crear(db)
        f = db.query_one("SELECT * FROM Facturas WHERE FacturaID=%d" % fid)
        self.assertTrue(f['NumeroControl'])
        self.assertEqual(f['EstadoEmision'], 'Emitida')

    def test_guarda_el_cliente(self):
        db = base()
        cid = GestorClientes(db).crear({'TipoCliente': 'Natural', 'Documento': 'V-1000000',
                                        'RazonSocial': 'Padre'})
        fid, _ = self._crear(db, cid)
        self.assertEqual(db.query_one("SELECT ClienteID FROM Facturas WHERE FacturaID=%d" % fid)['ClienteID'], cid)


if __name__ == '__main__':
    unittest.main()

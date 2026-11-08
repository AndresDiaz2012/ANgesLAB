# -*- coding: utf-8 -*-
"""
Pruebas de los maestros fiscales (fase 1 del ERP administrativo).

Lo que se protege:
  - que no se guarde un RIF con el digito verificador equivocado: tiene
    formato correcto y es de otra persona, y la factura no le sirve a nadie;
  - que el cliente que recibe la factura este completo antes de facturarle;
  - que cada prueba pueda llevar su propio regimen de IVA sin cambiar lo que
    factura una instalacion que no marca ninguna.

La base es SQLite con una traduccion minima del dialecto de Access, para
que el SQL que escribe el modulo se ejecute de verdad y no contra un doble
que lo acepta todo.
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import maestros_fiscales as mf
from modulos.facturacion_fiscal import FacturacionFiscal
from modulos.modulo_administrativo import GestorProveedores
from tests.sqlite_access import DBAccessEnSqlite


def base_con_tablas_viejas():
    """Lo que ya existe en una instalacion: Proveedores y Pruebas sin lo nuevo."""
    db = DBAccessEnSqlite()
    db.execute("CREATE TABLE Proveedores (ProveedorID INTEGER PRIMARY KEY AUTOINCREMENT, "
               "RazonSocial TEXT, RIF TEXT, Direccion TEXT, Telefono TEXT, Email TEXT, "
               "Contacto TEXT, TipoContribuyente TEXT, Observaciones TEXT, Activo INTEGER, "
               "FechaCreacion TEXT)")
    db.execute("CREATE TABLE Pruebas (PruebaID INTEGER PRIMARY KEY, NombrePrueba TEXT)")
    db.execute("INSERT INTO Pruebas VALUES (1, 'Hematologia completa')")
    db.execute("INSERT INTO Pruebas VALUES (2, 'Frasco recolector')")
    return db


# RIF reales de entes publicos, faciles de comprobar en el portal del SENIAT
RIF_SENIAT = 'G-20000303-0'
RIF_BCV = 'G-20000110-0'


class TestRif(unittest.TestCase):

    def test_rif_publicos_conocidos_son_validos(self):
        self.assertTrue(mf.rif_valido(RIF_SENIAT))
        self.assertTrue(mf.rif_valido(RIF_BCV))

    def test_un_digito_cambiado_lo_invalida(self):
        self.assertFalse(mf.rif_valido('G-20000303-1'))
        self.assertFalse(mf.rif_valido('G-20000304-0'))

    def test_se_entiende_como_lo_escribe_la_gente(self):
        self.assertEqual(mf.normalizar_rif('g200003030'), RIF_SENIAT)
        self.assertEqual(mf.normalizar_rif(' G 20.000.303 0 '), RIF_SENIAT)

    def test_rellena_con_ceros_hasta_ocho_digitos(self):
        rif = mf.normalizar_rif('J-1234567-0')
        self.assertEqual(rif, 'J-01234567-0')

    def test_sin_digito_verificador_no_es_rif(self):
        self.assertIsNone(mf.normalizar_rif('J-1234'))
        self.assertFalse(mf.rif_valido('J-12345678'))

    def test_letra_desconocida(self):
        self.assertIsNone(mf.normalizar_rif('X-12345678-9'))

    def test_el_digito_calculado_cierra_el_ciclo(self):
        for letra in 'VEJPG':
            d = mf.digito_verificador(letra, '12345678')
            self.assertTrue(mf.rif_valido('%s-12345678-%d' % (letra, d)))

    def test_cedula(self):
        self.assertEqual(mf.normalizar_cedula('12.345.678'), 'V-12345678')
        self.assertEqual(mf.normalizar_cedula('e-8123456'), 'E-8123456')
        self.assertIsNone(mf.normalizar_cedula('abc'))


class TestEsquema(unittest.TestCase):

    def test_crea_tablas_y_columnas_que_faltan(self):
        db = base_con_tablas_viejas()
        hechos = mf.asegurar_esquema(db)
        self.assertIn('tabla Clientes', hechos)
        self.assertIn('Proveedores.TipoPersona', hechos)
        self.assertIn('Pruebas.RegimenIVA', hechos)

    def test_llamarlo_dos_veces_no_hace_nada_la_segunda(self):
        db = base_con_tablas_viejas()
        mf.asegurar_esquema(db)
        self.assertEqual(mf.asegurar_esquema(db), [])

    def test_no_toca_los_datos_existentes(self):
        db = base_con_tablas_viejas()
        mf.asegurar_esquema(db)
        self.assertEqual(len(db.query("SELECT * FROM Pruebas")), 2)


class TestClientes(unittest.TestCase):

    def setUp(self):
        self.db = base_con_tablas_viejas()
        mf.asegurar_esquema(self.db)
        self.g = mf.GestorClientes(self.db)

    def _juridico(self, **extra):
        d = {'TipoCliente': 'Aseguradora', 'Documento': RIF_SENIAT,
             'RazonSocial': 'Seguros Ejemplo C.A.', 'DomicilioFiscal': 'Caracas',
             'CondicionPago': 'Credito', 'DiasCredito': 30, 'LimiteCredito': 5000}
        d.update(extra)
        return d

    def test_alta_de_un_cliente_juridico(self):
        cid = self.g.crear(self._juridico())
        c = self.g.obtener(cid)
        self.assertEqual(c['Documento'], RIF_SENIAT)
        self.assertEqual(c['TipoContribuyente'], 'Ordinario')
        self.assertEqual(c['DiasCredito'], 30)

    def test_rif_con_digito_equivocado_se_rechaza(self):
        with self.assertRaises(mf.ErrorMaestro) as ctx:
            self.g.crear(self._juridico(Documento='G-20000303-9'))
        self.assertIn('digito verificador', str(ctx.exception))

    def test_un_juridico_no_puede_usar_cedula(self):
        with self.assertRaises(mf.ErrorMaestro):
            self.g.crear(self._juridico(Documento='V-12345678'))

    def test_un_juridico_necesita_domicilio_fiscal(self):
        with self.assertRaises(mf.ErrorMaestro):
            self.g.crear(self._juridico(DomicilioFiscal=''))

    def test_documento_duplicado_se_rechaza(self):
        self.g.crear(self._juridico())
        with self.assertRaises(mf.ErrorMaestro) as ctx:
            self.g.crear(self._juridico(RazonSocial='Otra'))
        self.assertIn('Ya existe', str(ctx.exception))

    def test_persona_natural_con_cedula(self):
        cid = self.g.crear({'TipoCliente': 'Natural', 'Documento': '12.345.678',
                            'RazonSocial': 'Maria Perez'})
        c = self.g.obtener(cid)
        self.assertEqual(c['Documento'], 'V-12345678')
        self.assertEqual(c['TipoContribuyente'], 'No contribuyente')
        self.assertEqual(c['CondicionPago'], 'Contado')

    def test_de_contado_no_guarda_credito(self):
        cid = self.g.crear(self._juridico(CondicionPago='Contado'))
        c = self.g.obtener(cid)
        self.assertEqual((c['DiasCredito'], c['LimiteCredito']), (0, 0.0))

    def test_actualizar_conserva_lo_que_no_se_toca(self):
        cid = self.g.crear(self._juridico())
        self.g.actualizar(cid, {'Telefono': '0212-5550000'})
        c = self.g.obtener(cid)
        self.assertEqual(c['Telefono'], '0212-5550000')
        self.assertEqual(c['RazonSocial'], 'Seguros Ejemplo C.A.')

    def test_actualizar_no_se_choca_consigo_mismo(self):
        cid = self.g.crear(self._juridico())
        self.g.actualizar(cid, {'Documento': RIF_SENIAT})  # mismo documento

    def test_desactivar_no_borra(self):
        cid = self.g.crear(self._juridico())
        self.g.desactivar(cid)
        self.assertEqual(self.g.listar(), [])
        self.assertEqual(len(self.g.listar(solo_activos=False)), 1)

    def test_busqueda_por_nombre_o_documento(self):
        self.g.crear(self._juridico())
        self.assertEqual(len(self.g.listar(busqueda='Ejemplo')), 1)
        self.assertEqual(len(self.g.listar(busqueda='20000303')), 1)
        self.assertEqual(len(self.g.listar(busqueda='nadie')), 0)

    def test_comilla_en_el_nombre_no_rompe_el_sql(self):
        cid = self.g.crear(self._juridico(RazonSocial="D'Angelo Seguros"))
        self.assertEqual(self.g.obtener(cid)['RazonSocial'], "D'Angelo Seguros")


class TestClienteDelPaciente(unittest.TestCase):

    def setUp(self):
        self.db = base_con_tablas_viejas()
        mf.asegurar_esquema(self.db)
        self.g = mf.GestorClientes(self.db)
        self.padre = self.g.crear({'TipoCliente': 'Natural', 'Documento': 'V-10000000',
                                   'RazonSocial': 'Padre'})
        self.seguro = self.g.crear({'TipoCliente': 'Aseguradora', 'Documento': RIF_BCV,
                                    'RazonSocial': 'Seguro', 'DomicilioFiscal': 'Caracas'})

    def test_un_paciente_puede_tener_varios_clientes(self):
        self.g.asociar_paciente(self.padre, 77, 'Padre')
        self.g.asociar_paciente(self.seguro, 77, 'Titular')
        self.assertEqual(len(self.g.clientes_de_paciente(77)), 2)

    def test_solo_un_cliente_por_defecto(self):
        self.g.asociar_paciente(self.padre, 77, por_defecto=True)
        self.g.asociar_paciente(self.seguro, 77, por_defecto=True)
        self.assertEqual(self.g.cliente_por_defecto(77)['ClienteID'], self.seguro)
        self.assertEqual(self.g.clientes_de_paciente(77)[0]['ClienteID'], self.seguro)

    def test_sin_por_defecto_no_se_elige_ninguno(self):
        self.g.asociar_paciente(self.padre, 77)
        self.assertIsNone(self.g.cliente_por_defecto(77))

    def test_asociar_dos_veces_actualiza(self):
        self.g.asociar_paciente(self.padre, 77, 'Padre')
        self.g.asociar_paciente(self.padre, 77, 'Representante', por_defecto=True)
        filas = self.g.clientes_de_paciente(77)
        self.assertEqual(len(filas), 1)
        self.assertEqual(filas[0]['Vinculo'], 'Representante')

    def test_cliente_inexistente(self):
        with self.assertRaises(mf.ErrorMaestro):
            self.g.asociar_paciente(999, 77)


class TestProveedores(unittest.TestCase):

    def setUp(self):
        self.db = base_con_tablas_viejas()
        self.g = GestorProveedores(self.db)

    def test_alta_guarda_los_datos_fiscales(self):
        pid = self.g.crear_proveedor({'RazonSocial': 'Reactivos C.A.', 'RIF': 'g200003030',
                                      'ConceptoISLR': 'compras_bienes', 'DiasCredito': 15})
        p = self.g.obtener_proveedor(pid)
        self.assertEqual(p['RIF'], RIF_SENIAT)
        self.assertEqual(p['TipoPersona'], 'PJD')
        self.assertEqual(p['ConceptoISLR'], 'compras_bienes')
        self.assertEqual(p['DiasCredito'], 15)

    def test_sin_rif_no_se_da_de_alta(self):
        with self.assertRaises(ValueError):
            self.g.crear_proveedor({'RazonSocial': 'Sin RIF'})

    def test_rif_invalido_no_se_da_de_alta(self):
        with self.assertRaises(ValueError):
            self.g.crear_proveedor({'RazonSocial': 'Malo', 'RIF': 'J-12345678-0'})
        self.assertEqual(self.db.query("SELECT * FROM Proveedores"), [])

    def test_retencion_de_iva_solo_75_o_100(self):
        with self.assertRaises(mf.ErrorMaestro):
            mf.validar_datos_fiscales_proveedor({'PorcentajeRetencionIVA': 50})
        self.assertEqual(mf.validar_datos_fiscales_proveedor(
            {'PorcentajeRetencionIVA': '100'})['PorcentajeRetencionIVA'], 100.0)

    def test_actualizar_normaliza_el_rif(self):
        pid = self.g.crear_proveedor({'RazonSocial': 'X', 'RIF': RIF_SENIAT})
        self.g.actualizar_proveedor(pid, {'RIF': 'g200001100', 'TipoPersona': 'PJND'})
        p = self.g.obtener_proveedor(pid)
        self.assertEqual((p['RIF'], p['TipoPersona']), (RIF_BCV, 'PJND'))


class TestRegimenIvaDeLaPrueba(unittest.TestCase):

    def test_tasa_segun_regimen(self):
        self.assertEqual(mf.tasa_iva_de_prueba({'RegimenIVA': 'Exento'}), Decimal('0'))
        self.assertEqual(mf.tasa_iva_de_prueba({'RegimenIVA': 'Gravado'}), Decimal('16'))
        self.assertEqual(mf.tasa_iva_de_prueba({'RegimenIVA': 'gravado', 'AlicuotaIVA': 8}),
                         Decimal('8'))
        # Sin marcar es exenta: un servicio medico no causa IVA salvo decision
        self.assertEqual(mf.tasa_iva_de_prueba({'RegimenIVA': None}), Decimal('0'))
        self.assertEqual(mf.tasa_iva_de_prueba({}), Decimal('0'))

    def test_sin_columna_todas_exentas(self):
        db = base_con_tablas_viejas()
        self.assertEqual(mf.tasas_iva_de_pruebas(db, [1, 2]), {1: 0, 2: 0})

    def test_solo_la_marcada_gravada_lleva_iva(self):
        db = base_con_tablas_viejas()
        mf.marcar_regimen_prueba(db, 2, 'Gravado')
        self.assertEqual(mf.tasas_iva_de_pruebas(db, [1, 2]), {1: 0, 2: Decimal('16')})

    def test_con_iva_por_defecto_16_la_prueba_sigue_exenta(self):
        # Es la configuracion real de la clinica (IVAPorDefecto = 16)
        ff = FacturacionFiscal(DBConfig({'IVAPorDefecto': 16}))
        db = base_con_tablas_viejas()
        tasas = mf.tasas_iva_de_pruebas(db, [1])
        t = ff.calcular_totales_factura([{'precio': 100, 'cantidad': 1,
                                          'tasa_iva': float(tasas[1])}])
        self.assertEqual((t['monto_iva'], t['monto_exento']), (0.0, 100.0))

    def test_regimen_desconocido_se_rechaza(self):
        db = base_con_tablas_viejas()
        with self.assertRaises(mf.ErrorMaestro):
            mf.marcar_regimen_prueba(db, 1, 'Reducido')


class DBConfig:
    def __init__(self, config):
        self._config = config

    def query_one(self, sql):
        if 'Configuracion' in sql:
            return dict(self._config)
        return None

    def query(self, sql):
        return []

    def execute(self, sql):
        return None


class TestFacturaConLineasDeDistintoIva(unittest.TestCase):
    """Un laboratorio exento que vende tambien un producto gravado."""

    def setUp(self):
        self.ff = FacturacionFiscal(DBConfig({'IVAPorDefecto': 0,
                                              'TipoContribuyente': 'Ordinario'}))

    def test_servicio_exento_y_producto_gravado(self):
        t = self.ff.calcular_totales_factura([
            {'precio': 100, 'cantidad': 1},                    # prueba: tasa del lab (0)
            {'precio': 10, 'cantidad': 2, 'tasa_iva': 16},     # frascos
        ])
        self.assertEqual(t['monto_exento'], 100.0)
        self.assertEqual(t['base_imponible'], 20.0)
        self.assertEqual(t['monto_iva'], 3.2)
        self.assertEqual(t['total'], 123.2)
        self.assertEqual(t['tasa_iva'], 16.0)

    def test_el_descuento_global_se_reparte_y_cuadra(self):
        t = self.ff.calcular_totales_factura([
            {'precio': 100, 'cantidad': 1},
            {'precio': 33.33, 'cantidad': 1, 'tasa_iva': 16},
        ], descuento_porcentaje=10)
        base_total = Decimal(str(t['monto_exento'])) + Decimal(str(t['base_imponible']))
        self.assertEqual(base_total, Decimal('133.33') - Decimal(str(t['monto_descuento'])))

    def test_sin_tasas_por_linea_sale_igual_que_antes(self):
        ff16 = FacturacionFiscal(DBConfig({'IVAPorDefecto': 16}))
        t = ff16.calcular_totales_factura([{'precio': 100, 'cantidad': 1}],
                                          descuento_porcentaje=5)
        self.assertEqual((t['base_imponible'], t['monto_iva'], t['total']),
                         (95.0, 15.2, 110.2))

    def test_exonerada_anula_cualquier_tasa_de_linea(self):
        t = self.ff.calcular_totales_factura(
            [{'precio': 10, 'cantidad': 1, 'tasa_iva': 16}], es_exonerada=True)
        self.assertEqual((t['monto_iva'], t['monto_exento']), (0.0, 10.0))

    def test_el_desglose_lista_cada_alicuota(self):
        t = self.ff.calcular_totales_factura([
            {'precio': 100, 'cantidad': 1},
            {'precio': 10, 'cantidad': 1, 'tasa_iva': 16},
        ])
        self.assertEqual([d['tasa'] for d in t['desglose_iva']], [0.0, 16.0])


if __name__ == '__main__':
    unittest.main()

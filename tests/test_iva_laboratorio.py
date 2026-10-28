# -*- coding: utf-8 -*-
"""
Pruebas del IVA de un laboratorio clinico.

Los servicios medico-asistenciales privados estan exentos del IVA desde la
sentencia 1505 de la Sala Constitucional del TSJ (5/6/2003), y la
jurisprudencia contencioso-tributaria posterior lo ha aplicado a los
laboratorios clinicos para las actividades propias del laboratorio.

Lo que se protege: que un laboratorio que configura su IVA en cero facture
en cero. Suena obvio, y sin embargo no era lo que pasaba: el modulo leia la
tasa encadenando con 'or', y como en Python el cero es falso, un cero
configurado terminaba facturando al 16%. El paciente pagaba un impuesto que
su servicio no causa.
"""

import os
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.facturacion_fiscal import (ConfiguracionFiscal,
                                        FacturacionFiscal, _tasa_configurada)


class DBFalsa:
    """Lo minimo que FacturacionFiscal consulta al construirse."""

    def __init__(self, config):
        self._config = config

    def query_one(self, sql):
        if 'ConfiguracionLaboratorio' in sql or 'ConfiguracionSistema' in sql:
            return dict(self._config)
        return None

    def query(self, sql):
        return []

    def execute(self, sql):
        return None


class TestLaTasaConfigurada(unittest.TestCase):

    def test_un_cero_configurado_se_respeta(self):
        # Este es el fallo: 0.0 or 16 da 16
        self.assertEqual(_tasa_configurada({'IVAPorDefecto': 0.0}), Decimal('0.0'))

    def test_un_cero_entero_tambien(self):
        self.assertEqual(_tasa_configurada({'IVAPorDefecto': 0}), Decimal('0'))

    def test_una_tasa_normal_se_respeta(self):
        self.assertEqual(_tasa_configurada({'IVAPorDefecto': 16}), Decimal('16'))

    def test_la_tasa_de_laboratorio_manda_sobre_la_general(self):
        d = {'TasaIVALaboratorio': 0, 'IVAPorDefecto': 16}
        self.assertEqual(_tasa_configurada(d), Decimal('0'))

    def test_sin_configurar_cae_a_la_alicuota_general(self):
        self.assertEqual(_tasa_configurada({}), Decimal('16'))
        self.assertEqual(_tasa_configurada(None), Decimal('16'))

    def test_un_nulo_no_es_un_cero(self):
        # NULL en la base es "sin configurar"; cero es una decision
        self.assertEqual(_tasa_configurada({'IVAPorDefecto': None}), Decimal('16'))

    def test_un_valor_ilegible_no_rompe(self):
        self.assertEqual(_tasa_configurada({'IVAPorDefecto': 'x'}), Decimal('16'))


class TestUnServicioExentoNoPagaIva(unittest.TestCase):

    def _ff(self, config):
        return FacturacionFiscal(DBFalsa(config))

    def test_con_la_tasa_en_cero_el_importe_va_a_exento(self):
        # No es "base imponible gravada al 0%": una operacion exenta esta
        # fuera del impuesto, y la factura la marca con (E)
        ff = self._ff({'IVAPorDefecto': 0})
        t = ff.calcular_totales_factura([{'precio': 25000, 'cantidad': 1}])
        self.assertEqual(t['monto_exento'], Decimal('25000.00'))
        self.assertEqual(t['base_imponible'], Decimal('0.00'))
        self.assertEqual(t['monto_iva'], Decimal('0.00'))

    def test_el_paciente_no_paga_iva_de_mas(self):
        ff = self._ff({'IVAPorDefecto': 0})
        t = ff.calcular_totales_factura([{'precio': 25000, 'cantidad': 1}])
        self.assertEqual(t['total'], Decimal('25000.00'))

    def test_un_laboratorio_gravado_sigue_cobrando_su_iva(self):
        # Vender reactivos no esta exento; ahi la alicuota general aplica
        ff = self._ff({'IVAPorDefecto': 16})
        t = ff.calcular_totales_factura([{'precio': 25000, 'cantidad': 1}])
        self.assertEqual(t['monto_iva'], Decimal('4000.00'))
        self.assertEqual(t['base_imponible'], Decimal('25000.00'))

    def test_una_factura_exonerada_sigue_saliendo_exonerada(self):
        ff = self._ff({'IVAPorDefecto': 16})
        t = ff.calcular_totales_factura([{'precio': 25000, 'cantidad': 1}],
                                        es_exonerada=True)
        self.assertEqual(t['monto_iva'], Decimal('0.00'))
        self.assertEqual(t['monto_exento'], Decimal('25000.00'))


class TestLaConstanteNoMiente(unittest.TestCase):
    """
    Estaba en 16% con un comentario que decia "pueden estar exentos". Una
    constante que dice una cosa y un comentario que dice la contraria acaba
    usandose por la constante.
    """

    def test_el_servicio_de_laboratorio_esta_exento(self):
        self.assertEqual(ConfiguracionFiscal.TASA_IVA_LABORATORIO, Decimal('0.00'))

    def test_la_alicuota_general_sigue_siendo_la_general(self):
        # La exencion es del servicio, no de todo lo que venda el negocio
        self.assertEqual(ConfiguracionFiscal.TASA_IVA_GENERAL, Decimal('16.00'))


if __name__ == '__main__':
    unittest.main()

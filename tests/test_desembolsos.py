# -*- coding: utf-8 -*-
"""
Pruebas del reparto de los desembolsos de la clinica.

Lo que se protege: que no se salde una cuenta con dinero que no llego, que lo
aplicado nunca supere lo desembolsado, y que las cuentas se cubran de la mas
antigua a la mas reciente.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.desembolsos_clinica import repartir_desembolso


def cuenta(cid, saldo, paciente='PACIENTE'):
    return {'CuentaCobrarID': cid, 'SaldoPendiente': saldo,
            'NombrePaciente': paciente}


class TestRepartoDesembolso(unittest.TestCase):

    def test_sin_cuentas_no_aplica_nada(self):
        aplic, sobrante = repartir_desembolso(500.0, [])
        self.assertEqual(aplic, [])
        self.assertEqual(sobrante, 500.0)

    def test_cubre_una_cuenta_exacta(self):
        aplic, sobrante = repartir_desembolso(100.0, [cuenta(1, 100.0)])
        self.assertEqual(len(aplic), 1)
        self.assertEqual(aplic[0]['monto'], 100.0)
        self.assertEqual(aplic[0]['saldo_nuevo'], 0.0)
        self.assertTrue(aplic[0]['salda'])
        self.assertEqual(sobrante, 0.0)

    def test_cubre_varias_cuentas_en_orden(self):
        cuentas = [cuenta(1, 100.0), cuenta(2, 50.0), cuenta(3, 30.0)]
        aplic, sobrante = repartir_desembolso(150.0, cuentas)
        self.assertEqual([a['cuenta_id'] for a in aplic], [1, 2])
        self.assertTrue(all(a['salda'] for a in aplic))
        self.assertEqual(sobrante, 0.0)

    def test_la_ultima_cuenta_queda_abonada_en_parte(self):
        cuentas = [cuenta(1, 100.0), cuenta(2, 80.0)]
        aplic, sobrante = repartir_desembolso(130.0, cuentas)
        self.assertEqual(len(aplic), 2)
        self.assertTrue(aplic[0]['salda'])
        self.assertFalse(aplic[1]['salda'])
        self.assertEqual(aplic[1]['monto'], 30.0)
        self.assertEqual(aplic[1]['saldo_nuevo'], 50.0)
        self.assertEqual(sobrante, 0.0)

    def test_nunca_se_aplica_mas_de_lo_desembolsado(self):
        cuentas = [cuenta(i, 100.0) for i in range(1, 6)]
        for monto in (0.0, 1.0, 99.99, 250.0, 500.0, 1000.0):
            aplic, sobrante = repartir_desembolso(monto, cuentas)
            total = round(sum(a['monto'] for a in aplic), 2)
            self.assertLessEqual(total, monto + 0.001,
                                 f"se aplico de mas con {monto}")
            self.assertAlmostEqual(total + sobrante, monto, places=2)

    def test_nunca_se_aplica_mas_que_el_saldo_de_la_cuenta(self):
        aplic, sobrante = repartir_desembolso(500.0, [cuenta(1, 40.0)])
        self.assertEqual(aplic[0]['monto'], 40.0)
        self.assertEqual(aplic[0]['saldo_nuevo'], 0.0)
        self.assertEqual(sobrante, 460.0)

    def test_saldo_nuevo_nunca_es_negativo(self):
        cuentas = [cuenta(1, 10.0), cuenta(2, 20.0)]
        aplic, _ = repartir_desembolso(1000.0, cuentas)
        for a in aplic:
            self.assertGreaterEqual(a['saldo_nuevo'], 0.0)

    def test_se_ignoran_las_cuentas_ya_saldadas(self):
        cuentas = [cuenta(1, 0.0), cuenta(2, 50.0)]
        aplic, sobrante = repartir_desembolso(50.0, cuentas)
        self.assertEqual(len(aplic), 1)
        self.assertEqual(aplic[0]['cuenta_id'], 2)
        self.assertEqual(sobrante, 0.0)

    def test_desembolso_cero_no_toca_nada(self):
        aplic, sobrante = repartir_desembolso(0, [cuenta(1, 100.0)])
        self.assertEqual(aplic, [])
        self.assertEqual(sobrante, 0.0)

    def test_desembolso_negativo_no_toca_nada(self):
        aplic, sobrante = repartir_desembolso(-100.0, [cuenta(1, 100.0)])
        self.assertEqual(aplic, [])
        self.assertEqual(sobrante, 0.0)

    def test_monto_ilegible_no_rompe(self):
        aplic, sobrante = repartir_desembolso('abc', [cuenta(1, 100.0)])
        self.assertEqual(aplic, [])
        self.assertEqual(sobrante, 0.0)

    def test_saldo_ilegible_se_omite_sin_romper(self):
        cuentas = [{'CuentaCobrarID': 1, 'SaldoPendiente': 'xx'},
                   cuenta(2, 25.0)]
        aplic, sobrante = repartir_desembolso(25.0, cuentas)
        self.assertEqual(len(aplic), 1)
        self.assertEqual(aplic[0]['cuenta_id'], 2)

    def test_saldo_nulo_se_omite(self):
        cuentas = [{'CuentaCobrarID': 1, 'SaldoPendiente': None},
                   cuenta(2, 10.0)]
        aplic, _ = repartir_desembolso(10.0, cuentas)
        self.assertEqual([a['cuenta_id'] for a in aplic], [2])

    def test_centavos_no_se_pierden_en_repartos_largos(self):
        # Saldos con centavos: lo aplicado mas el sobrante debe dar el
        # desembolso exacto, sin perder ni inventar un centimo.
        cuentas = [cuenta(i, 33.33) for i in range(1, 11)]
        aplic, sobrante = repartir_desembolso(100.0, cuentas)
        total = round(sum(a['monto'] for a in aplic), 2)
        self.assertAlmostEqual(total + sobrante, 100.0, places=2)
        self.assertLessEqual(total, 100.0 + 0.001)

    def test_el_reparto_conserva_el_total_de_la_deuda(self):
        cuentas = [cuenta(1, 60.0), cuenta(2, 40.0), cuenta(3, 25.0)]
        deuda_inicial = sum(c['SaldoPendiente'] for c in cuentas)
        aplic, _ = repartir_desembolso(75.0, cuentas)
        aplicado = sum(a['monto'] for a in aplic)
        # Lo que queda a deber en las cuentas tocadas, mas las intactas
        tocadas = {a['cuenta_id'] for a in aplic}
        queda = sum(a['saldo_nuevo'] for a in aplic)
        queda += sum(c['SaldoPendiente'] for c in cuentas
                     if c['CuentaCobrarID'] not in tocadas)
        self.assertAlmostEqual(aplicado + queda, deuda_inicial, places=2)


if __name__ == '__main__':
    unittest.main(verbosity=2)

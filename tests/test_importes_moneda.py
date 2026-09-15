# -*- coding: utf-8 -*-
"""
Pruebas de la captura de precios en varias monedas.

Lo que se protege: que "40.000" en pesos no se lea como cuarenta, y que un
precio tecleado en pesos y guardado en dolares vuelva a leerse igual. Los dos
errores mueven el precio por mil o por decenas de pesos sin que nadie lo note.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.tarifas import convertir_a_usd, convertir_desde_usd, leer_importe


class TestLeerImporte(unittest.TestCase):

    def test_cifra_simple(self):
        self.assertEqual(leer_importe('40000'), 40000.0)

    def test_punto_de_miles_en_pesos(self):
        # "40.000" en pesos son cuarenta mil, no cuarenta
        self.assertEqual(leer_importe('40.000'), 40000.0)
        self.assertEqual(leer_importe('1.500'), 1500.0)

    def test_punto_decimal_en_dolares(self):
        # Escribiendo en dolares, el punto es decimal
        self.assertEqual(leer_importe('40.00', separador_miles=False), 40.0)
        self.assertEqual(leer_importe('9.70', separador_miles=False), 9.7)

    def test_dos_decimales_no_son_miles(self):
        # Solo tres cifras detras del punto indican miles
        self.assertEqual(leer_importe('40.00'), 40.0)
        self.assertEqual(leer_importe('40.5'), 40.5)

    def test_miles_y_decimales_juntos(self):
        self.assertEqual(leer_importe('40.000,50'), 40000.5)
        self.assertEqual(leer_importe('1.234.567,89'), 1234567.89)

    def test_formato_anglosajon(self):
        self.assertEqual(leer_importe('40,000.50'), 40000.5)

    def test_coma_decimal(self):
        self.assertEqual(leer_importe('1500,75'), 1500.75)

    def test_varios_puntos_de_miles(self):
        self.assertEqual(leer_importe('1.234.567'), 1234567.0)

    def test_espacios(self):
        self.assertEqual(leer_importe('  40.000  '), 40000.0)

    def test_vacio_es_cero(self):
        self.assertEqual(leer_importe(''), 0.0)
        self.assertEqual(leer_importe('   '), 0.0)

    def test_texto_no_valido(self):
        for v in ('abc', '12abc', '--', None):
            self.assertIsNone(leer_importe(v), repr(v))

    def test_negativo(self):
        self.assertEqual(leer_importe('-500'), -500.0)


class TestConversion(unittest.TestCase):

    def test_pesos_a_dolares(self):
        self.assertEqual(convertir_a_usd(40000, 4000), 10.0)

    def test_sin_tasa_no_convierte(self):
        self.assertEqual(convertir_a_usd(40000, 0), 40000.0)
        self.assertEqual(convertir_a_usd(40000, None), 40000.0)

    def test_ida_y_vuelta_conserva_el_importe(self):
        # Es lo que ve el usuario: teclea en pesos, guarda, y al reabrir
        # tiene que encontrar la misma cifra.
        for tasa in (4000.0, 4123.45, 3987.6, 4250.0):
            for cop in (8700, 12500, 20000, 30000, 40000, 155000):
                usd = convertir_a_usd(cop, tasa)
                vuelta = convertir_desde_usd(usd, tasa)
                self.assertLess(
                    abs(vuelta - cop), 1.0,
                    f"deriva de {abs(vuelta - cop):.2f} COP con tasa {tasa} y {cop}")

    def test_la_precision_es_de_cuatro_decimales(self):
        # Con dos decimales la deriva llegaba a 20 COP por prueba
        usd = convertir_a_usd(12500, 4000)
        self.assertEqual(usd, 3.125)

    def test_texto_no_rompe(self):
        self.assertEqual(convertir_a_usd('x', 4000), 0.0)
        self.assertEqual(convertir_desde_usd('x', 4000), 0.0)

    def test_el_ejemplo_del_convenio_en_pesos(self):
        # 20.000 / 40.000 / 30.000 COP con tasa 4.000
        tasa = 4000.0
        amb = convertir_a_usd(leer_importe('20.000'), tasa)
        cli = convertir_a_usd(leer_importe('40.000'), tasa)
        con = convertir_a_usd(leer_importe('30.000'), tasa)
        self.assertEqual((amb, cli, con), (5.0, 10.0, 7.5))
        # Y la comision en pesos sigue siendo 10.000
        self.assertEqual(convertir_desde_usd(cli - con, tasa), 10000.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)

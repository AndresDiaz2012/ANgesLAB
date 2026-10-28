# -*- coding: utf-8 -*-
"""
Pruebas de los requisitos de contenido de la Providencia SNAT/2026/00093.

Lo que se protege: que la factura diga lo que la norma exige y con el
formato que exige. Es el documento que audita el SENIAT; un formato de
fecha mal puesto no se nota hasta que lo nota un inspector.

Los requisitos estan tomados de resumenes profesionales de la providencia,
no del texto de la Gaceta. Si el contador corrige alguno, estas pruebas son
el sitio donde se ve que cambio.
"""

import os
import sys
import unittest
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import providencia_00093 as prov
from modulos.facturacion_fiscal import monto_en_letras


class TestFechaYHora(unittest.TestCase):
    """Articulo 8.5: fecha en ocho digitos y hora con segundos."""

    def test_la_fecha_va_en_ocho_digitos(self):
        self.assertEqual(prov.fecha_fiscal(datetime(2027, 4, 19)), '19042027')

    def test_el_dia_y_el_mes_llevan_su_cero(self):
        # 1 de marzo es 01032027, no 132027
        self.assertEqual(prov.fecha_fiscal(datetime(2027, 3, 1)), '01032027')
        self.assertEqual(len(prov.fecha_fiscal(datetime(2027, 3, 1))), 8)

    def test_la_hora_lleva_segundos(self):
        # La providencia derogada solo pedia la fecha; de ahi que el
        # programa viniera imprimiendo horas sin segundos.
        self.assertEqual(prov.hora_fiscal(datetime(2027, 4, 19, 15, 7, 3)),
                         '03.07.03 p.m.')

    def test_la_manana_se_distingue_de_la_tarde(self):
        self.assertIn('a.m.', prov.hora_fiscal(datetime(2027, 4, 19, 9, 5, 1)))
        self.assertIn('p.m.', prov.hora_fiscal(datetime(2027, 4, 19, 21, 5, 1)))

    def test_el_mediodia_es_pm_y_la_medianoche_am(self):
        self.assertIn('p.m.', prov.hora_fiscal(datetime(2027, 4, 19, 12, 0, 0)))
        self.assertIn('a.m.', prov.hora_fiscal(datetime(2027, 4, 19, 0, 30, 0)))

    def test_un_valor_que_no_es_fecha_no_rompe(self):
        self.assertEqual(prov.fecha_fiscal(None), '')
        self.assertEqual(prov.hora_fiscal('ayer'), '')


class TestMarcaDeExento(unittest.TestCase):
    """Articulo 8.7: lo exento, exonerado o no gravado se marca con (E)."""

    def test_lo_exento_lleva_la_marca(self):
        self.assertEqual(prov.marca_gravamen(True), '(E)')

    def test_lo_gravado_no_lleva_marca(self):
        # Antes se imprimia una 'G'; la norma solo pide marcar lo exento
        self.assertEqual(prov.marca_gravamen(False), '')


class TestDesglosePorAlicuota(unittest.TestCase):
    """
    Articulos 8.9 y 8.10: la base imponible de CADA alicuota con su
    porcentaje, y el IVA de cada una por separado.
    """

    LINEAS = [
        {'SubTotal': 25000, 'MontoIVA': 4000, 'TasaIVA': 16},
        {'SubTotal': 10000, 'MontoIVA': 1600, 'TasaIVA': 16},
        {'SubTotal': 30000, 'MontoIVA': 0, 'Exonerada': True},
        {'SubTotal': 5000, 'MontoIVA': 400, 'TasaIVA': 8},
    ]

    def test_cada_alicuota_sale_una_sola_vez(self):
        g = prov.desglose_por_alicuota(self.LINEAS, 16)
        self.assertEqual(len(g), 3)

    def test_las_bases_de_una_misma_alicuota_se_suman(self):
        g = {str(x['tasa']): x for x in prov.desglose_por_alicuota(self.LINEAS, 16)}
        self.assertEqual(g['16']['base'], Decimal('35000'))
        self.assertEqual(g['16']['iva'], Decimal('5600'))

    def test_lo_exonerado_va_aparte_y_sin_iva(self):
        exentos = [x for x in prov.desglose_por_alicuota(self.LINEAS, 16)
                   if x['exento']]
        self.assertEqual(len(exentos), 1)
        self.assertEqual(exentos[0]['base'], Decimal('30000'))
        self.assertEqual(exentos[0]['iva'], Decimal('0'))

    def test_lo_exento_se_lista_primero(self):
        # Es como se lee un desglose: lo que no paga, y luego lo que paga
        self.assertTrue(prov.desglose_por_alicuota(self.LINEAS, 16)[0]['exento'])

    def test_una_linea_sin_tasa_propia_usa_la_de_la_factura(self):
        # Las facturas anteriores no guardaban la tasa por linea
        g = prov.desglose_por_alicuota([{'SubTotal': 1000}], 16)
        self.assertEqual(g[0]['tasa'], Decimal('16'))
        self.assertEqual(g[0]['iva'], Decimal('160.00'))

    def test_sin_lineas_no_hay_desglose(self):
        self.assertEqual(prov.desglose_por_alicuota([], 16), [])

    def test_la_etiqueta_dice_el_porcentaje(self):
        g = prov.desglose_por_alicuota([{'SubTotal': 100, 'TasaIVA': 16}], 16)
        self.assertIn('16%', prov.etiqueta_alicuota(g[0]))

    def test_la_suma_del_desglose_es_el_total(self):
        # Si no cuadra, la factura dice un total que su propio desglose no
        # sostiene
        g = prov.desglose_por_alicuota(self.LINEAS, 16)
        base = sum(x['base'] for x in g)
        iva = sum(x['iva'] for x in g)
        self.assertEqual(base, Decimal('70000'))
        self.assertEqual(iva, Decimal('6000'))


class TestLeyendas(unittest.TestCase):

    def test_el_contribuyente_formal_se_detecta(self):
        self.assertTrue(prov.es_contribuyente_formal({'TipoContribuyente': 'Formal'}))
        self.assertFalse(prov.es_contribuyente_formal({'TipoContribuyente': 'Ordinario'}))
        self.assertFalse(prov.es_contribuyente_formal({}))

    def test_la_leyenda_del_articulo_19_se_puede_configurar(self):
        # La redaccion exacta no consta en las fuentes: tiene que poder
        # ponerla el contador sin tocar el programa.
        texto = 'El literal que diga el contador'
        self.assertEqual(prov.leyenda_emision({'LeyendaProvidencia': texto}),
                         texto)

    def test_sin_configurar_sale_una_provisional_que_cita_la_norma(self):
        d = prov.leyenda_emision({})
        self.assertIn(prov.PROVIDENCIA, d)

    def test_una_leyenda_en_blanco_cae_a_la_provisional(self):
        self.assertEqual(prov.leyenda_emision({'LeyendaProvidencia': '   '}),
                         prov.LEYENDA_EMISION_DEFECTO)


class TestMontoEnLetras(unittest.TestCase):
    """
    Solo sabia contar hasta 999: por encima lanzaba IndexError y factura_pdf
    se lo tragaba, de modo que la linea "Son:" no ha salido nunca en una
    factura de verdad.
    """

    def test_los_miles(self):
        self.assertEqual(monto_en_letras(76000, 'VES'),
                         'SETENTA Y SEIS MIL BOLIVARES')

    def test_mil_no_es_un_mil(self):
        self.assertEqual(monto_en_letras(1000, 'VES'), 'MIL BOLIVARES')

    def test_veintiun_mil_lleva_apocope(self):
        self.assertEqual(monto_en_letras(21000, 'VES'), 'VEINTIUN MIL BOLIVARES')

    def test_los_millones(self):
        self.assertEqual(monto_en_letras(1000000, 'VES'), 'UN MILLON BOLIVARES')
        self.assertEqual(monto_en_letras(2500000, 'VES'),
                         'DOS MILLONES QUINIENTOS MIL BOLIVARES')

    def test_cien_a_secas_y_ciento_uno(self):
        self.assertEqual(monto_en_letras(100, 'VES'), 'CIEN BOLIVARES')
        self.assertEqual(monto_en_letras(101, 'VES'), 'CIENTO UNO BOLIVARES')

    def test_los_centavos(self):
        self.assertIn('50/100', monto_en_letras(76000.50, 'COP'))

    def test_cada_moneda_con_su_nombre(self):
        self.assertIn('PESOS COLOMBIANOS', monto_en_letras(10, 'COP'))
        self.assertIn('DOLARES', monto_en_letras(10, 'USD'))
        self.assertIn('BOLIVARES', monto_en_letras(10, 'VES'))

    def test_un_importe_cualquiera_no_lanza(self):
        for n in (0, 1, 999, 1001, 99999, 123456, 9999999):
            self.assertTrue(monto_en_letras(n, 'VES'))

    def test_un_valor_ilegible_no_rompe(self):
        self.assertIn('CERO', monto_en_letras('x', 'VES'))


class TestLaNormaQuedaIdentificada(unittest.TestCase):
    """Para que quien audite sepa contra que norma se escribio esto."""

    def test_se_declara_la_providencia_y_su_gaceta(self):
        self.assertEqual(prov.PROVIDENCIA, 'SNAT/2026/00093')
        self.assertIn('43.484', prov.GACETA)

    def test_consta_que_deroga_las_dos_anteriores(self):
        self.assertIn('SNAT/2011/0071', prov.DEROGA)
        self.assertIn('SNAT/2024/000102', prov.DEROGA)


if __name__ == '__main__':
    unittest.main()

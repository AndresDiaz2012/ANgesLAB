# -*- coding: utf-8 -*-
"""
Pruebas del IGTF segun el tipo de contribuyente.

Solo los sujetos pasivos especiales son agentes de percepcion del IGTF
(Providencia SNAT/2022/000013, G.O. 42.339). Lo que se protege: que un
laboratorio ORDINARIO no le sume el 3% a un pago en divisas. Antes pasaba
en cuanto faltaba la configuracion, porque IGTFActivo valia verdadero por
defecto y el cobro con Divisa o Zelle lo activaba solo.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.facturacion_fiscal import FacturacionFiscal, igtf_corresponde


class DBFalsa:
    def __init__(self, config):
        self._config = config

    def query_one(self, sql):
        if 'ConfiguracionLaboratorio' in sql or 'ConfiguracionSistema' in sql:
            return dict(self._config) if self._config is not None else None
        return None

    def query(self, sql):
        return []

    def execute(self, sql):
        return None


class TestQuienPercibeIgtf(unittest.TestCase):

    def test_sin_configuracion_no_se_cobra(self):
        self.assertFalse(igtf_corresponde(None))
        self.assertFalse(igtf_corresponde({}))

    def test_ordinario_no_cobra_aunque_este_activo(self):
        # El interruptor no crea una obligacion que la ley no da
        self.assertFalse(igtf_corresponde(
            {'TipoContribuyente': 'Ordinario', 'IGTFActivo': True}))

    def test_sin_tipo_y_activo_no_cobra(self):
        self.assertFalse(igtf_corresponde({'IGTFActivo': True}))

    def test_especial_activo_cobra(self):
        self.assertTrue(igtf_corresponde(
            {'TipoContribuyente': 'Especial', 'IGTFActivo': True}))

    def test_especial_apagado_no_cobra(self):
        self.assertFalse(igtf_corresponde(
            {'TipoContribuyente': 'Especial', 'IGTFActivo': False}))

    def test_especial_sin_interruptor_no_cobra(self):
        # Faltar el dato no es encenderlo
        self.assertFalse(igtf_corresponde({'TipoContribuyente': 'Especial'}))

    def test_el_tipo_se_lee_sin_importar_mayusculas(self):
        self.assertTrue(igtf_corresponde(
            {'TipoContribuyente': ' ESPECIAL ', 'IGTFActivo': 1}))


class TestUnPagoEnDivisaDeUnOrdinario(unittest.TestCase):

    def _ff(self, config):
        return FacturacionFiscal(DBFalsa(config))

    def test_zelle_de_un_ordinario_no_suma_igtf(self):
        ff = self._ff({'TipoContribuyente': 'Ordinario', 'IGTFActivo': True})
        monto, total = ff.calcular_igtf(100, forma_pago_nombre='Zelle')
        self.assertEqual(monto, 0.0)
        self.assertEqual(total, 100.0)

    def test_divisa_sin_configurar_no_suma_igtf(self):
        ff = self._ff({})
        monto, total = ff.calcular_igtf(100, forma_pago_nombre='Divisa')
        self.assertEqual((monto, total), (0.0, 100.0))

    def test_ni_forzandolo_lo_cobra_un_ordinario(self):
        ff = self._ff({'TipoContribuyente': 'Ordinario'})
        monto, _ = ff.calcular_igtf(100, aplica_igtf=True)
        self.assertEqual(monto, 0.0)

    def test_un_especial_activo_si_lo_cobra(self):
        ff = self._ff({'TipoContribuyente': 'Especial', 'IGTFActivo': True,
                       'TasaIGTF': 3})
        monto, total = ff.calcular_igtf(100, forma_pago_nombre='Zelle')
        self.assertEqual(monto, 3.0)
        self.assertEqual(total, 103.0)


if __name__ == '__main__':
    unittest.main()

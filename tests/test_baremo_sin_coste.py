# -*- coding: utf-8 -*-
"""
Pruebas de como el baremo cuenta lo que no tiene precio.

Son dos cosas distintas y el documento que se entrega en la clinica tiene
que decir cual:

    sin cargar   falta por pactar ese precio. Hay que preguntarlo.
    sin coste    la prueba se incluye a proposito, como la relacion PSA,
                 que sale de dividir dos resultados ya cobrados.

Meter las dos en el mismo saco hacia que el baremo dijera que quedaba algo
por acordar donde no quedaba nada.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.baremo_pdf import SIN_CARGAR, SIN_COSTE, _importe
from modulos.tarifas import COL_CLINICA, COL_CONVENIO, precio_detalle


class TestElBaremoYElCobroDicenLoMismo(unittest.TestCase):
    """
    El criterio de "sin convenio" tiene que ser uno solo.

    Este es el fallo que se corrigio: precio_detalle distinguia el cero
    deliberado, y listar_baremo no. La misma prueba salia tarifada para
    cobrar y pendiente de tarifar en el papel.
    """

    @staticmethod
    def _criterio_baremo(prueba):
        """Lo que hace listar_baremo con cada fila."""
        from modulos.tarifas import _cargado
        return _cargado(prueba, COL_CONVENIO) is None

    def test_un_cero_deliberado_no_esta_pendiente_en_ninguno_de_los_dos(self):
        gratis = {'Precio': 0.0, COL_CLINICA: 0.0, COL_CONVENIO: 0.0}
        self.assertFalse(precio_detalle(gratis, 'Cirugia Asegurado')['sin_convenio'])
        self.assertFalse(self._criterio_baremo(gratis))

    def test_sin_cargar_esta_pendiente_en_los_dos(self):
        falta = {'Precio': 20000.0, COL_CLINICA: 40000.0, COL_CONVENIO: None}
        self.assertTrue(precio_detalle(falta, 'Cirugia Asegurado')['sin_convenio'])
        self.assertTrue(self._criterio_baremo(falta))

    def test_con_precio_no_esta_pendiente_en_ninguno(self):
        ok = {'Precio': 20000.0, COL_CLINICA: 40000.0, COL_CONVENIO: 30000.0}
        self.assertFalse(precio_detalle(ok, 'Cirugia Asegurado')['sin_convenio'])
        self.assertFalse(self._criterio_baremo(ok))


class TestLoQueSeImprimeSinImporte(unittest.TestCase):

    def test_sin_cargar_sale_un_guion(self):
        self.assertEqual(_importe(0, sin_coste=False), SIN_CARGAR)

    def test_gratis_aposta_lo_dice(self):
        self.assertEqual(_importe(0, sin_coste=True), SIN_COSTE)

    def test_no_son_lo_mismo(self):
        # Si coincidieran, el documento volveria a no distinguirlos
        self.assertNotEqual(SIN_CARGAR, SIN_COSTE)

    def test_un_importe_de_verdad_se_imprime_igual(self):
        self.assertEqual(_importe(30000.0), '30,000.00')
        self.assertEqual(_importe(30000.0, sin_coste=True), '30,000.00')

    def test_un_importe_ilegible_no_rompe(self):
        self.assertEqual(_importe('x'), SIN_CARGAR)


if __name__ == '__main__':
    unittest.main()

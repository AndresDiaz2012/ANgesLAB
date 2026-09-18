# -*- coding: utf-8 -*-
"""
Pruebas de la oferta de paquete de los perfiles.

Lo que se protege: que un perfil con oferta cueste exactamente lo pactado
(la solicitud se factura linea a linea, asi que el reparto tiene que cuadrar
al centimo), y que la oferta ambulatoria no se le aplique nunca a la clinica,
que es el error caro: reclamarle 120.000 donde le corresponden 218.000.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.tarifas import (COL_PERFIL_BASE, COL_PERFIL_CLINICA,
                             COL_PERFIL_CONVENIO, precio_paquete, prorratear)


def perfil(base=120000.0, clinica=190000.0, convenio=150000.0):
    """La oferta que el laboratorio tiene puesta al perfil 20."""
    return {'PerfilID': 19, 'CodigoPerfil': 'P20', 'NombrePerfil': 'Perfil 20',
            COL_PERFIL_BASE: base, COL_PERFIL_CLINICA: clinica,
            COL_PERFIL_CONVENIO: convenio}


CASOS_CLINICA = ('Hospitalizado Particular', 'Hospitalizado Asegurado',
                 'Emergencia Particular', 'Emergencia Asegurado',
                 'Cirugia Particular', 'Cirugia Asegurado')


class TestPrecioPaquete(unittest.TestCase):

    def test_el_paciente_de_calle_paga_la_oferta_ambulatoria(self):
        self.assertEqual(precio_paquete(perfil(), 'Ambulatorio'), 120000.0)

    def test_los_casos_de_clinica_van_por_la_oferta_de_convenio(self):
        for p in CASOS_CLINICA:
            self.assertEqual(precio_paquete(perfil(), p), 150000.0, p)

    def test_nunca_se_factura_lo_que_cobra_la_clinica(self):
        # Los 190.000 los cobra la clinica al paciente; al laboratorio le
        # corresponden 150.000.
        for p in CASOS_CLINICA:
            self.assertNotEqual(precio_paquete(perfil(), p), 190000.0)

    def test_sin_oferta_no_hay_paquete(self):
        # None quiere decir "cobre la suma de las pruebas"
        vacio = {'PerfilID': 1}
        self.assertIsNone(precio_paquete(vacio, 'Ambulatorio'))
        self.assertIsNone(precio_paquete(vacio, 'Cirugia Asegurado'))

    def test_la_oferta_ambulatoria_no_se_le_presta_a_la_clinica(self):
        # Cargada la de calle pero no la de convenio, un paciente de
        # hospitalizacion NO se factura a 120.000: se cobra la suma de los
        # precios de convenio, que es el precio entero. Prestar aqui la
        # oferta de calle le reclamaria a la clinica 98.000 de menos.
        solo_calle = perfil(convenio=None)
        self.assertEqual(precio_paquete(solo_calle, 'Ambulatorio'), 120000.0)
        self.assertIsNone(precio_paquete(solo_calle, 'Hospitalizado Asegurado'))

    def test_la_oferta_de_convenio_no_se_le_presta_al_ambulatorio(self):
        solo_convenio = perfil(base=None)
        self.assertIsNone(precio_paquete(solo_convenio, 'Ambulatorio'))
        self.assertEqual(precio_paquete(solo_convenio, 'Cirugia Asegurado'),
                         150000.0)

    def test_un_cero_borra_la_oferta(self):
        # Es como se vacia la casilla desde la pantalla de precios, y no
        # existe un paquete que valga cero de verdad
        self.assertIsNone(precio_paquete(perfil(base=0), 'Ambulatorio'))

    def test_importe_ilegible_no_rompe(self):
        self.assertIsNone(precio_paquete({COL_PERFIL_BASE: 'x'}, 'Ambulatorio'))


class TestProrrateo(unittest.TestCase):
    """
    El reparto tiene que cuadrar al centimo con el paquete.

    El total de la solicitud sale de sumar sus lineas, y de ahi pasa a la
    cuenta por cobrar y al corte. Si el reparto no cuadra, se reclama una
    cifra distinta de la pactada.
    """

    # Las catorce pruebas del perfil 20, en pesos
    PERFIL_20 = [8000, 8000, 8000, 10000, 8000, 8000, 8000, 20000,
                 8000, 24000, 16000, 8000, 8000, 10000]

    def test_la_suma_cuadra_con_el_paquete(self):
        repartido = prorratear(self.PERFIL_20, 120000)
        self.assertAlmostEqual(sum(repartido), 120000, places=4)

    def test_cuadra_con_importes_que_no_dividen_exacto(self):
        for total in (120000, 99999, 150000, 77777, 1):
            repartido = prorratear(self.PERFIL_20, total)
            self.assertAlmostEqual(sum(repartido), total, places=4,
                                   msg="paquete de %s" % total)

    def test_se_reparte_en_proporcion(self):
        # La hematologia (20.000 de 152.000) se lleva la misma porcion del
        # paquete que tenia de la suma
        repartido = prorratear(self.PERFIL_20, 120000)
        hematologia = repartido[7]
        suma = sum(self.PERFIL_20)
        self.assertAlmostEqual(hematologia, 20000 / suma * 120000, places=2)

    def test_el_orden_de_las_lineas_se_respeta(self):
        # Cada linea es una prueba concreta: si el reparto las reordenara,
        # la solicitud cobraria una prueba al precio de otra
        repartido = prorratear([10, 20, 30], 60)
        self.assertEqual(repartido, [10.0, 20.0, 30.0])

    def test_una_sola_prueba_se_lleva_todo(self):
        self.assertEqual(prorratear([50000], 30000), [30000.0])

    def test_sin_lineas_no_hay_reparto(self):
        self.assertEqual(prorratear([], 120000), [])

    def test_lineas_en_cero_se_reparten_por_igual(self):
        # Un perfil sin precios cargados: no hay proporcion que respetar,
        # pero el paquete se cobra igual y tiene que cuadrar
        repartido = prorratear([0, 0, 0, 0], 100)
        self.assertAlmostEqual(sum(repartido), 100, places=4)
        self.assertEqual(len(repartido), 4)

    def test_importes_ilegibles_no_rompen(self):
        repartido = prorratear([10000, None, 'x'], 9000)
        self.assertAlmostEqual(sum(repartido), 9000, places=4)


class TestLaOfertaRebaja(unittest.TestCase):
    """El paquete tiene que salir por debajo de las pruebas sueltas."""

    def test_el_perfil_20_de_la_clinica(self):
        # 152.000 sueltas contra 120.000 de paquete
        suma = 152000.0
        paquete = precio_paquete(perfil(), 'Ambulatorio')
        self.assertLess(paquete, suma)
        repartido = prorratear([suma], paquete)
        self.assertAlmostEqual(repartido[0], 120000.0, places=2)

    def test_la_comision_de_la_clinica_sobre_el_paquete(self):
        # La clinica cobra 190.000 y nos paga 150.000: se queda 40.000
        p = perfil()
        self.assertEqual(p[COL_PERFIL_CLINICA] - p[COL_PERFIL_CONVENIO], 40000.0)


if __name__ == '__main__':
    unittest.main()

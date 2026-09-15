# -*- coding: utf-8 -*-
"""
Pruebas del cobro por procedencia.

Lo que se protege aqui es que el dinero del seguro no entre a la caja del dia
y que un abono parcial no se registre como pago completo. Son los dos errores
que descuadran el arqueo.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.procedencia import (
    PROCEDENCIAS,
    calcular_cobro,
    descripcion_cuenta,
    es_contado,
    es_credito,
    etiqueta_cobro,
)


class TestClasificacion(unittest.TestCase):
    """Que cada procedencia caiga del lado correcto."""

    def test_aseguradas_son_credito(self):
        for p in ('Asegurado', 'Hospitalizado Asegurado', 'Emergencia Asegurado'):
            self.assertTrue(es_credito(p), f"{p} deberia cobrarse al seguro")

    def test_particulares_son_contado(self):
        for p in ('Ambulatorio', 'Hospitalizado Particular', 'Emergencia Particular'):
            self.assertTrue(es_contado(p), f"{p} deberia cobrarse de contado")

    def test_toda_procedencia_del_combo_esta_clasificada(self):
        # Si se agrega una opcion al combo y no se clasifica, el sistema la
        # trataria como contado en silencio y el seguro entraria a caja.
        for p in PROCEDENCIAS:
            self.assertIsInstance(es_credito(p), bool)

    def test_contado_y_credito_son_excluyentes(self):
        for p in PROCEDENCIAS:
            self.assertNotEqual(es_credito(p), es_contado(p))

    def test_espacios_y_mayusculas_no_cambian_la_clasificacion(self):
        # Un valor guardado con un espacio de mas no puede convertir una
        # solicitud asegurada en efectivo.
        for variante in ('  Asegurado  ', 'ASEGURADO', 'asegurado',
                         'Emergencia  Asegurado'):
            self.assertTrue(es_credito(variante), f"fallo con {variante!r}")

    def test_valor_vacio_o_nulo_se_trata_como_contado(self):
        for v in (None, '', '   '):
            self.assertTrue(es_contado(v))

    def test_procedencia_desconocida_se_trata_como_contado(self):
        self.assertTrue(es_contado('Convenio Empresa X'))


class TestCabenEnLaBase(unittest.TestCase):
    """
    Solicitudes.TipoServicio era TEXT(20) y tres procedencias no cabian:
    guardar una solicitud de hospitalizacion fallaba con "el campo es
    demasiado pequeno". La columna se amplia a 50 al arrancar; esta prueba
    vigila que no se agregue una procedencia que vuelva a no caber.
    """

    LIMITE = 50

    def test_ninguna_procedencia_supera_el_limite(self):
        for p in PROCEDENCIAS:
            self.assertLessEqual(
                len(p), self.LIMITE,
                f"'{p}' tiene {len(p)} caracteres y no cabria en TipoServicio")

    def test_las_largas_siguen_siendo_las_conocidas(self):
        # Si alguna crece, conviene revisar el ancho de la columna
        largas = sorted((len(p), p) for p in PROCEDENCIAS)[-1]
        self.assertLessEqual(largas[0], 30)


class TestCalculoDeCobro(unittest.TestCase):
    """El reparto entre lo que entra a caja y lo que queda a deber."""

    def test_asegurado_no_aporta_nada_a_caja(self):
        cobrado, saldo = calcular_cobro(100.0, 0, 'Asegurado')
        self.assertEqual(cobrado, 0.0)
        self.assertEqual(saldo, 100.0)

    def test_asegurado_ignora_el_abono_tecleado(self):
        # Aunque la casilla traiga un importe, por seguro no entra dinero.
        cobrado, saldo = calcular_cobro(100.0, 100.0, 'Emergencia Asegurado')
        self.assertEqual(cobrado, 0.0)
        self.assertEqual(saldo, 100.0)

    def test_contado_con_abono_cero_no_cobra_nada(self):
        # El cero se toma al pie de la letra: la pantalla rellena la casilla
        # con el total, asi que un cero solo llega si se escribio a proposito.
        # Es lo que permite registrar a quien se lleva el examen sin pagar.
        cobrado, saldo = calcular_cobro(80.0, 0, 'Ambulatorio')
        self.assertEqual(cobrado, 0.0)
        self.assertEqual(saldo, 80.0)

    def test_contado_pagando_todo(self):
        cobrado, saldo = calcular_cobro(80.0, 80.0, 'Ambulatorio')
        self.assertEqual(cobrado, 80.0)
        self.assertEqual(saldo, 0.0)

    def test_sin_documento_no_hay_cobro(self):
        # Un recibo o una factura son el comprobante de que el dinero entro;
        # sin comprobante no se asienta ingreso, aunque se teclee un abono.
        cobrado, saldo = calcular_cobro(100.0, 100.0, 'Ambulatorio',
                                        hay_documento=False)
        self.assertEqual(cobrado, 0.0)
        self.assertEqual(saldo, 100.0)

    def test_sin_documento_tampoco_cobra_a_un_asegurado(self):
        cobrado, saldo = calcular_cobro(100.0, 0, 'Asegurado',
                                        hay_documento=False)
        self.assertEqual(cobrado, 0.0)
        self.assertEqual(saldo, 100.0)

    def test_abono_parcial_cobra_solo_lo_abonado(self):
        cobrado, saldo = calcular_cobro(100.0, 20.0, 'Ambulatorio')
        self.assertEqual(cobrado, 20.0)
        self.assertEqual(saldo, 80.0)

    def test_abono_mayor_que_el_total_no_infla_la_caja(self):
        cobrado, saldo = calcular_cobro(50.0, 70.0, 'Ambulatorio')
        self.assertEqual(cobrado, 50.0)
        self.assertEqual(saldo, 0.0)

    def test_cobrado_mas_saldo_siempre_es_el_total(self):
        casos = [
            (100.0, 0, 'Ambulatorio'),
            (100.0, 100.0, 'Ambulatorio'),
            (100.0, 33.33, 'Ambulatorio'),
            (100.0, 100.0, 'Asegurado'),
            (0.0, 0, 'Ambulatorio'),
            (1.005, 0.5, 'Emergencia Particular'),
        ]
        for total, abonado, proc in casos:
            cobrado, saldo = calcular_cobro(total, abonado, proc)
            self.assertAlmostEqual(cobrado + saldo, round(float(total), 2),
                                   places=2, msg=f"descuadre en {proc} {total}/{abonado}")

    def test_nunca_devuelve_negativos(self):
        for total, abonado, proc in [(100.0, -50.0, 'Ambulatorio'),
                                     (-10.0, 0, 'Ambulatorio'),
                                     (0.0, 25.0, 'Asegurado')]:
            cobrado, saldo = calcular_cobro(total, abonado, proc)
            self.assertGreaterEqual(cobrado, 0.0)
            self.assertGreaterEqual(saldo, -0.001)

    def test_importes_con_texto_no_rompen_el_guardado(self):
        # Los importes llegan de casillas de texto; un valor ilegible no
        # puede tumbar el registro de la solicitud.
        cobrado, saldo = calcular_cobro('abc', 'xyz', 'Ambulatorio')
        self.assertEqual(cobrado, 0.0)
        self.assertEqual(saldo, 0.0)

    def test_dos_decimales(self):
        cobrado, saldo = calcular_cobro(10.0, 3.333333, 'Ambulatorio')
        self.assertEqual(cobrado, 3.33)
        self.assertEqual(saldo, 6.67)


class TestTextos(unittest.TestCase):
    """Lo que ve el usuario en pantalla y en cartera."""

    def test_etiqueta_distingue_los_dos_casos(self):
        self.assertIn('seguro', etiqueta_cobro('Asegurado').lower())
        self.assertIn('contado', etiqueta_cobro('Ambulatorio').lower())

    def test_la_cuenta_del_seguro_se_identifica_como_tal(self):
        obs = descripcion_cuenta('Hospitalizado Asegurado', 'SOL-001')
        self.assertIn('Asegurado', obs)
        self.assertIn('SOL-001', obs)

    def test_la_cuenta_de_particular_habla_de_saldo(self):
        obs = descripcion_cuenta('Ambulatorio', 'SOL-002')
        self.assertIn('Saldo', obs)
        self.assertIn('SOL-002', obs)

    def test_sin_numero_de_solicitud_no_deja_espacios_colgando(self):
        obs = descripcion_cuenta('Ambulatorio')
        self.assertFalse(obs.endswith(' '))


if __name__ == '__main__':
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""
Pruebas del baremo en Excel que se entrega a la administracion.

Lo que se protege: que el libro diga lo que el software cobra. Es un
documento que se negocia y se firma; una formula que calcule un convenio
distinto del que se factura convierte el archivo en una fuente de
discusiones en vez de un acuerdo.
"""

import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.baremo_excel import (COMISION_CLINICA, MOTIVO_PLACEHOLDER,
                                  MOTIVO_SIN_PRECIO, UMBRAL_PLACEHOLDER,
                                  clasificar, generar_baremo_excel)
from modulos.tarifas import COL_CLINICA, COL_CONVENIO

TASA = 3100.0


def fila(clinica_cop=25000.0, convenio_cop=None, nombre='HEMATOLOGIA',
         **extra):
    """Una fila del baremo, en pesos, como la ve la administracion."""
    if convenio_cop is None:
        convenio_cop = math.ceil(clinica_cop * (1 - COMISION_CLINICA))
    f = {'CodigoPrueba': 'HEM001', 'NombrePrueba': nombre,
         'NombreArea': 'Hematologia', 'Precio': 20000.0 / TASA,
         COL_CLINICA: clinica_cop / TASA, COL_CONVENIO: convenio_cop / TASA}
    f.update(extra)
    return f


class TestQueEntraYQueNo(unittest.TestCase):

    def test_una_prueba_con_precio_entra(self):
        entra, _ = clasificar(fila())
        self.assertTrue(entra)

    def test_sin_precio_va_a_excluidos(self):
        entra, motivo = clasificar(fila(clinica_cop=0, convenio_cop=0))
        self.assertFalse(entra)
        self.assertEqual(motivo, MOTIVO_SIN_PRECIO)

    def test_el_placeholder_de_medio_dolar_no_entra(self):
        # El catalogo traia pruebas a 0,05 USD puestas para rellenar; colarlas
        # en un baremo que se firma seria peor que dejarlas fuera.
        p = {COL_CLINICA: 0.05, COL_CONVENIO: 0.04}
        entra, motivo = clasificar(p)
        self.assertFalse(entra)
        self.assertEqual(motivo, MOTIVO_PLACEHOLDER)

    def test_justo_por_encima_del_umbral_si_entra(self):
        p = {COL_CLINICA: UMBRAL_PLACEHOLDER + 0.01, COL_CONVENIO: 0.05}
        self.assertTrue(clasificar(p)[0])

    def test_una_fila_vacia_no_rompe(self):
        entra, motivo = clasificar({})
        self.assertFalse(entra)
        self.assertEqual(motivo, MOTIVO_SIN_PRECIO)


class TestElLibroDiceLoQueSeCobra(unittest.TestCase):
    """
    La columna del convenio lleva formula solo cuando la formula es cierta.

    Un paquete negociado -el perfil 20 se pacto en 150.000, no en el 80% de
    190.000- no obedece a ninguna formula. Ponerle una haria que el
    documento prometiera un importe que el software no factura.
    """

    def _generar(self, filas):
        ruta = os.path.join(tempfile.mkdtemp(), 'baremo.xlsx')
        self.assertIsNotNone(
            generar_baremo_excel(ruta, filas, config_lab={'NombreLaboratorio': 'Lab'},
                                 tasa_cop=TASA))
        from openpyxl import load_workbook
        wb = load_workbook(ruta, data_only=False)
        return wb[[n for n in wb.sheetnames if n.startswith('Base')][0]]

    def test_el_convenio_normal_va_como_formula(self):
        ws = self._generar([fila()])
        self.assertTrue(str(ws.cell(row=9, column=8).value).startswith('='))

    def test_un_precio_pactado_va_con_su_cifra_y_una_nota(self):
        # 190.000 de clinica pero 150.000 pactados, no los 152.000 del 20%
        pactado = fila(clinica_cop=190000.0, convenio_cop=150000.0,
                       nombre='Perfil 20', es_perfil=True)
        ws = self._generar([pactado])
        self.assertEqual(ws.cell(row=9, column=8).value, 150000)
        self.assertTrue(ws.cell(row=9, column=10).value,
                        "un precio fuera de la regla tiene que llevar nota")

    def test_la_formula_del_dolar_cuelga_de_la_tasa(self):
        # Si no apuntara a D5, cambiar la tasa no recalcularia nada
        ws = self._generar([fila()])
        self.assertIn('$D$5', str(ws.cell(row=9, column=7).value))

    def test_la_tasa_queda_en_la_celda_esperada(self):
        ws = self._generar([fila()])
        self.assertEqual(ws['D5'].value, TASA)

    def test_el_precio_en_pesos_es_el_de_la_clinica(self):
        # No el ambulatorio: el ambulatorio no sale en este documento
        ws = self._generar([fila(clinica_cop=25000.0)])
        self.assertEqual(ws.cell(row=9, column=6).value, 25000)

    def test_el_ambulatorio_ya_no_es_un_precio_aparte(self):
        # Hay UN precio: el que paga el paciente, venga de donde venga.
        ws = self._generar([fila(clinica_cop=25000.0)])
        valores = [ws.cell(row=9, column=c).value for c in range(2, 11)]
        self.assertNotIn(20000, valores)

    def test_el_bolivar_cuelga_de_la_tasa_del_bcv(self):
        # Sin apuntar a D6, cambiar la tasa del BCV no recalcularia nada
        ruta = os.path.join(tempfile.mkdtemp(), 'bs.xlsx')
        generar_baremo_excel(ruta, [fila()], tasa_cop=TASA, tasa_bs=849.564)
        from openpyxl import load_workbook
        wb = load_workbook(ruta, data_only=False)
        ws = wb[[n for n in wb.sheetnames if n.startswith('Base')][0]]
        self.assertEqual(ws['D6'].value, 849.564)
        self.assertIn('$D$6', str(ws.cell(row=9, column=9).value))

    def test_sin_tasa_del_bcv_no_se_inventa_el_bolivar(self):
        # Una conversion inventada en un baremo que se firma es peor que
        # una columna vacia
        ws = self._generar([fila()])
        self.assertIsNone(ws.cell(row=9, column=9).value)


class TestLasTresHojas(unittest.TestCase):

    def test_el_libro_trae_base_excluidos_y_notas(self):
        ruta = os.path.join(tempfile.mkdtemp(), 'b.xlsx')
        generar_baremo_excel(ruta, [fila(), fila(clinica_cop=0, convenio_cop=0)],
                             tasa_cop=TASA)
        from openpyxl import load_workbook
        wb = load_workbook(ruta)
        self.assertEqual(len(wb.sheetnames), 3)
        self.assertTrue(wb.sheetnames[0].startswith('Base de trabajo'))
        self.assertIn('Excluidos', wb.sheetnames)
        self.assertIn('Notas', wb.sheetnames)

    def test_el_titulo_de_la_hoja_dice_cuantas_entraron(self):
        ruta = os.path.join(tempfile.mkdtemp(), 'b.xlsx')
        generar_baremo_excel(ruta, [fila(), fila(nombre='OTRA')], tasa_cop=TASA)
        from openpyxl import load_workbook
        self.assertEqual(load_workbook(ruta).sheetnames[0],
                         'Base de trabajo (2)')

    def test_las_excluidas_no_desaparecen(self):
        # El archivo de la administracion lo dice: "No se borraron"
        ruta = os.path.join(tempfile.mkdtemp(), 'b.xlsx')
        generar_baremo_excel(ruta, [fila(clinica_cop=0, convenio_cop=0,
                                         nombre='SIN PRECIO')], tasa_cop=TASA)
        from openpyxl import load_workbook
        we = load_workbook(ruta)['Excluidos']
        self.assertEqual(we.cell(row=6, column=3).value, 'SIN PRECIO')


if __name__ == '__main__':
    unittest.main()

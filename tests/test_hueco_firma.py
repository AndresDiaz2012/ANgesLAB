# -*- coding: utf-8 -*-
"""
Pruebas del hueco de la firma en el pie del informe.

Lo que se protege: que la firma quepa donde el informe dice que cabe. El
bloque se dibujaba en un sitio y la pagina reservaba otro, de modo que la
firma se metia media pulgada dentro de la tabla de resultados y podia
imprimirse encima de un valor.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from reportlab.lib.units import inch

from modulos.formato_pdf import LayoutCalculator

PAPELES = ('Carta', 'Media Carta')

# Proporcion de una firma escaneada vertical, como la del laboratorio
VERTICAL = 579 / 1040.0
APAISADA = 1040 / 579.0


class TestElBloqueCabeEnSuReserva(unittest.TestCase):
    """
    La reserva de la pagina tiene que cubrir el bloque entero.

    Este es el fallo que se corrigio: el bloque llegaba a 1,63 pulgadas del
    borde y la pagina solo reservaba 1,1.
    """

    def test_la_reserva_cubre_el_techo_del_bloque(self):
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            techo = L.firma_base_y + L.firma_img_height
            self.assertGreaterEqual(
                L.margin_bottom, techo,
                "%s: el bloque llega a %.2f y solo se reservan %.2f pulgadas"
                % (papel, techo / inch, L.margin_bottom / inch))

    def test_el_texto_no_pisa_el_pie_de_pagina(self):
        # Bajo el texto de la firma va el numero de orden, el paciente y la
        # fecha: si el bloque baja de mas, se solapan.
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            self.assertGreaterEqual(L.firma_linea_y - L.firma_texto_alto, 0.22 * inch,
                                    "%s: el texto de la firma baja demasiado" % papel)

    def test_sin_bioanalistas_no_se_reserva_el_hueco(self):
        # Un informe sin firma no tiene por que perder pagina
        for papel in PAPELES:
            con = LayoutCalculator(papel, tiene_bioanalistas=True)
            sin = LayoutCalculator(papel, tiene_bioanalistas=False)
            self.assertLess(sin.margin_bottom, con.margin_bottom, papel)

    def test_queda_altura_util_para_resultados(self):
        # La reserva no puede comerse la pagina
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            self.assertGreater(L.get_content_frame_height(), 3 * inch, papel)


class TestUnaFirmaVerticalSeVe(unittest.TestCase):
    """
    El motivo del cambio: el hueco era bajo y una firma vertical salia
    reducida a una mancha del 15% del ancho de su propia linea.
    """

    def _ancho_resultante(self, layout, proporcion):
        """Lo que mide la firma al encajarla sin deformarla."""
        escala = min(layout.firma_img_width / proporcion,
                     layout.firma_img_height)
        return escala * proporcion

    def test_una_firma_vertical_ocupa_un_tercio_largo_de_su_linea(self):
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            ancho = self._ancho_resultante(L, VERTICAL)
            self.assertGreater(
                ancho, 0.30 * L.firma_linea_width,
                "%s: la firma vertical sale al %.0f%% de su linea"
                % (papel, 100 * ancho / L.firma_linea_width))

    def test_una_firma_apaisada_sigue_llenando_el_ancho(self):
        # Ensanchar el hueco no puede estropear el caso que ya funcionaba
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            ancho = self._ancho_resultante(L, APAISADA)
            self.assertAlmostEqual(ancho, L.firma_img_width, delta=1.0,
                                   msg=papel)

    def test_el_hueco_no_es_mas_ancho_que_la_linea(self):
        # La firma no puede sobresalir de su propia raya
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            self.assertLessEqual(L.firma_img_width, L.firma_linea_width, papel)

    def test_caben_las_firmas_que_el_layout_promete(self):
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            ancho_bloque = L.firma_linea_width + 0.3 * inch
            self.assertLessEqual(ancho_bloque * L.max_firmas, L.content_width,
                                 "%s: no caben %d firmas seguidas"
                                 % (papel, L.max_firmas))


if __name__ == '__main__':
    unittest.main()

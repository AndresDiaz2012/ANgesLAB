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
        # La firma monta sobre la linea: parte de su altura queda por
        # debajo, cruzando el nombre, y solo el resto sube. La reserva tiene
        # que cubrir lo que sube.
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            techo = (L.firma_linea_y
                     + L.firma_img_height * (1 - L.firma_solape))
            self.assertGreaterEqual(
                L.margin_bottom, techo,
                "%s: el bloque llega a %.2f y solo se reservan %.2f pulgadas"
                % (papel, techo / inch, L.margin_bottom / inch))

    def test_el_techo_declarado_es_el_real(self):
        # firma_techo es lo que el layout promete; si se separa del calculo,
        # la reserva vuelve a mentir
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            self.assertAlmostEqual(
                L.firma_techo,
                L.firma_linea_y + L.firma_img_height * (1 - L.firma_solape),
                delta=0.5, msg=papel)

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


class TestLaFirmaMontaSobreLaLinea(unittest.TestCase):
    """
    Una firma de verdad arranca sobre la raya y baja cruzando el nombre.

    Apoyada limpiamente encima delata que es una imagen pegada.
    """

    def test_parte_de_la_firma_queda_bajo_la_linea(self):
        from modulos.firma_pie import SOLAPE_LINEA
        self.assertGreater(SOLAPE_LINEA, 0.0)
        self.assertLess(SOLAPE_LINEA, 1.0)

    def test_la_firma_no_baja_tanto_que_tape_el_registro(self):
        # Si bajara entera, en vez de cruzar el nombre lo borraria
        from modulos.firma_pie import SOLAPE_LINEA
        self.assertLessEqual(SOLAPE_LINEA, 0.5)

    def test_el_solape_recupera_pagina(self):
        # Montada sobre la linea, la firma sube menos que su altura, asi que
        # cabe una firma mayor con la misma reserva
        for papel in PAPELES:
            L = LayoutCalculator(papel, tiene_bioanalistas=True)
            sube = L.firma_img_height * (1 - L.firma_solape)
            self.assertLess(sube, L.firma_img_height, papel)

    def test_una_firma_apaisada_tambien_monta_sobre_la_linea(self):
        # El solape se mide sobre lo que la firma ocupa de verdad, no sobre
        # el hueco: con el hueco, una apaisada se hundiria entera.
        from modulos.firma_pie import SOLAPE_LINEA
        alto_hueco = 1.6 * inch
        alto_real = 0.4 * inch          # una firma apaisada llena poco
        y_linea = 0.64 * inch
        y_real = y_linea - alto_real * SOLAPE_LINEA
        y_con_hueco = y_linea - alto_hueco * SOLAPE_LINEA
        self.assertGreater(y_real + alto_real, y_linea,
                           "la firma tiene que asomar por encima de la raya")
        self.assertLess(y_con_hueco + alto_hueco - y_linea,
                        alto_hueco,  # control de cordura
                        "")
        self.assertLess(y_con_hueco, y_real,
                        "usar el hueco la hundiria mas de la cuenta")


if __name__ == '__main__':
    unittest.main()

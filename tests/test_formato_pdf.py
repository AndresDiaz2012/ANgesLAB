# -*- coding: utf-8 -*-
"""
Tests para modulos/formato_pdf.py
Verifica el cálculo proporcional de dimensiones y generación de QR.
"""

import unittest
import sys
import os

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.formato_pdf import (
    LayoutCalculator, QRGenerator, TAMANOS_PAGINA, MEDIA_CARTA,
    REPORTLAB_OK, QR_DISPONIBLE
)


class TestLayoutCalculator(unittest.TestCase):
    """Tests para el cálculo de dimensiones proporcionales."""

    def test_tamanos_pagina_definidos(self):
        """Todos los tamaños de página deben estar definidos."""
        for nombre in ['Carta', 'A4', 'Oficio', 'Media Carta']:
            self.assertIn(nombre, TAMANOS_PAGINA)

    def test_media_carta_dimensiones(self):
        """Media Carta debe ser 396 x 612 pt."""
        self.assertEqual(MEDIA_CARTA, (396, 612))

    def test_layout_carta(self):
        """Layout Carta debe tener dimensiones correctas."""
        layout = LayoutCalculator('Carta')
        self.assertEqual(layout.page_width, 612)
        self.assertEqual(layout.page_height, 792)
        self.assertFalse(layout.es_media_carta)
        self.assertEqual(layout.box_cols, 3)
        self.assertEqual(layout.max_firmas, 3)
        self.assertEqual(layout._font_scale, 1.0)

    def test_layout_a4(self):
        """Layout A4 debe tener dimensiones correctas."""
        layout = LayoutCalculator('A4')
        self.assertAlmostEqual(layout.page_width, 595.28, places=1)
        self.assertAlmostEqual(layout.page_height, 841.89, places=1)
        self.assertFalse(layout.es_media_carta)
        self.assertEqual(layout.box_cols, 3)

    def test_layout_media_carta(self):
        """Layout Media Carta debe tener configuración compacta."""
        layout = LayoutCalculator('Media Carta')
        self.assertEqual(layout.page_width, 396)
        self.assertEqual(layout.page_height, 612)
        self.assertTrue(layout.es_media_carta)
        self.assertEqual(layout.box_cols, 2)
        self.assertEqual(layout.max_firmas, 2)
        self.assertEqual(layout._font_scale, 0.82)

    def test_columnas_suman_ancho_contenido(self):
        """La suma de anchos de columna debe ≈ ancho de contenido."""
        for nombre in ['Carta', 'A4', 'Oficio', 'Media Carta']:
            layout = LayoutCalculator(nombre)
            total = sum(layout.col_widths)
            self.assertAlmostEqual(total, layout.content_width, delta=2,
                                   msg=f"Columnas no suman correctamente en {nombre}")

    def test_content_width_positivo(self):
        """El ancho de contenido debe ser positivo para todos los formatos."""
        for nombre in TAMANOS_PAGINA:
            layout = LayoutCalculator(nombre)
            self.assertGreater(layout.content_width, 0)

    def test_margenes_media_carta_menores(self):
        """Los márgenes de Media Carta deben ser menores que los de Carta."""
        carta = LayoutCalculator('Carta')
        media = LayoutCalculator('Media Carta')
        self.assertLess(media.margin_left, carta.margin_left)
        self.assertLess(media.margin_right, carta.margin_right)

    def test_header_media_carta_menor(self):
        """El header de Media Carta debe ser menor que el de Carta."""
        carta = LayoutCalculator('Carta')
        media = LayoutCalculator('Media Carta')
        self.assertLess(media.header_height, carta.header_height)

    def test_logo_media_carta_menor(self):
        """El logo de Media Carta debe ser menor que el de Carta."""
        carta = LayoutCalculator('Carta')
        media = LayoutCalculator('Media Carta')
        self.assertLess(media.logo_width, carta.logo_width)
        self.assertLess(media.logo_height, carta.logo_height)

    def test_bioanalistas_aumenta_margen_inferior(self):
        """Con bioanalistas, el margen inferior debe ser mayor."""
        sin = LayoutCalculator('Carta', tiene_bioanalistas=False)
        con = LayoutCalculator('Carta', tiene_bioanalistas=True)
        self.assertGreater(con.margin_bottom, sin.margin_bottom)

    def test_content_frame_height_positivo(self):
        """La altura de contenido del frame debe ser positiva."""
        for nombre in TAMANOS_PAGINA:
            layout = LayoutCalculator(nombre, tiene_bioanalistas=True)
            h = layout.get_content_frame_height()
            self.assertGreater(h, 100, msg=f"Frame height demasiado pequeño en {nombre}")

    def test_font_scale_aplicada(self):
        """Las fuentes de media carta deben ser menores que las de carta."""
        carta = LayoutCalculator('Carta')
        media = LayoutCalculator('Media Carta')
        self.assertLess(media.font_titulo_prueba, carta.font_titulo_prueba)
        self.assertLess(media.font_datos_tabla, carta.font_datos_tabla)

    def test_nombre_desconocido_usa_letter(self):
        """Un nombre de papel desconocido debe usar tamaño Letter."""
        layout = LayoutCalculator('Desconocido')
        self.assertEqual(layout.page_width, 612)

    def test_repr(self):
        """__repr__ debe retornar un string descriptivo."""
        layout = LayoutCalculator('A4')
        r = repr(layout)
        self.assertIn('A4', r)
        self.assertIn('595', r)

    def test_qr_size_proporcional(self):
        """El QR de media carta debe ser menor que el de carta."""
        carta = LayoutCalculator('Carta')
        media = LayoutCalculator('Media Carta')
        self.assertLess(media.qr_size, carta.qr_size)


class TestQRGenerator(unittest.TestCase):
    """Tests para la generación de códigos QR."""

    def test_disponible(self):
        """QR debe estar disponible (qrcode instalado)."""
        self.assertTrue(QRGenerator.disponible())

    def test_hash_determinista(self):
        """El hash debe ser determinista para los mismos inputs."""
        h1 = QRGenerator.generar_hash('001', '01/01/2026', 'JUAN')
        h2 = QRGenerator.generar_hash('001', '01/01/2026', 'JUAN')
        self.assertEqual(h1, h2)

    def test_hash_longitud(self):
        """El hash debe tener 12 caracteres."""
        h = QRGenerator.generar_hash('001', '01/01/2026', 'TEST')
        self.assertEqual(len(h), 12)

    def test_hash_diferente_inputs(self):
        """Inputs diferentes deben generar hashes diferentes."""
        h1 = QRGenerator.generar_hash('001', '01/01/2026', 'JUAN')
        h2 = QRGenerator.generar_hash('002', '01/01/2026', 'JUAN')
        self.assertNotEqual(h1, h2)

    def test_generar_qr_image(self):
        """Debe generar una imagen QR como BytesIO."""
        buf = QRGenerator.generar_qr_image('SOL-001', '27/02/2026', 'TEST')
        self.assertIsNotNone(buf)
        self.assertGreater(len(buf.getvalue()), 0)

    def test_generar_qr_image_es_png(self):
        """La imagen QR debe ser formato PNG."""
        buf = QRGenerator.generar_qr_image('SOL-001', '27/02/2026', 'TEST')
        # PNG magic bytes
        self.assertTrue(buf.getvalue().startswith(b'\x89PNG'))

    @unittest.skipUnless(REPORTLAB_OK, "ReportLab no disponible")
    def test_generar_rl_image(self):
        """Debe generar un objeto ReportLab Image."""
        img = QRGenerator.generar_rl_image('SOL-001', '27/02/2026', 'TEST', 60, 60)
        self.assertIsNotNone(img)


if __name__ == '__main__':
    unittest.main()

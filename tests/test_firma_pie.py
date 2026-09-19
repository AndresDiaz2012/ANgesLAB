# -*- coding: utf-8 -*-
"""
Pruebas del bloque de firma del pie del informe.

Lo que se protege: que los tres informes que llevan firma -el de
resultados, el que se envia por correo y el de control- digan exactamente
lo mismo, y que ninguno se quede sin pie porque falte un dato. Una firma
que en un papel dice un numero de registro y en otro dice otro no vale.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.firma_pie import ETIQUETA_REGISTRO, lineas_firma, titulo_de


def bio(**cambios):
    """El bioanalista que firma los informes del laboratorio."""
    base = {'NombreCompleto': 'Filadelfo G. Díaz B.',
            'Cedula': 'V-15353076',
            'NumeroRegistro': '17.421-12.120',
            'TituloProfesional': 'LCDO. BIOANÁLISIS',
            'NombreArea': 'General'}
    base.update(cambios)
    return base


def textos(b):
    return [t for t, _f, _c in lineas_firma(b)]


class TestElFormatoDelLaboratorio(unittest.TestCase):

    def test_nombre_titulo_y_registro_en_ese_orden(self):
        self.assertEqual(textos(bio()),
                         ['Filadelfo G. Díaz B.',
                          'LCDO. BIOANÁLISIS',
                          'N° 17.421-12.120'])

    def test_el_nombre_va_en_negrita_y_el_resto_no(self):
        lineas = lineas_firma(bio())
        self.assertEqual(lineas[0][2], 'nombre')
        self.assertTrue(all(l[2] == 'detalle' for l in lineas[1:]))

    def test_la_cedula_no_se_imprime(self):
        # No aparece en el formato del laboratorio; a un bioanalista se le
        # verifica por su numero de registro. Sigue en la ficha.
        self.assertNotIn('V-15353076', ' '.join(textos(bio())))

    def test_el_registro_se_imprime_tal_como_esta_guardado(self):
        # Los puntos y el guion los pone el colegio profesional, no el
        # programa: reformatear aqui cambiaria el numero de un profesional.
        b = bio(NumeroRegistro='17421 - 12120')
        self.assertIn(ETIQUETA_REGISTRO + '17421 - 12120', textos(b))


class TestCuandoFaltanDatos(unittest.TestCase):
    """Ningun informe puede quedarse sin pie por un campo vacio."""

    def test_sin_titulo_se_usa_el_area(self):
        # Una instalacion que venga de antes no tiene el campo cargado
        b = bio(TituloProfesional=None, NombreArea='Hematología')
        self.assertEqual(titulo_de(b), 'Bioanalista - Hematología')

    def test_sin_titulo_y_area_general_dice_bioanalista(self):
        b = bio(TituloProfesional='', NombreArea='General')
        self.assertEqual(titulo_de(b), 'Bioanalista')

    def test_sin_titulo_ni_area_sigue_diciendo_bioanalista(self):
        self.assertEqual(titulo_de({}), 'Bioanalista')

    def test_el_area_general_no_se_escribe(self):
        # "Bioanalista - General" no dice nada
        b = bio(TituloProfesional=None)
        self.assertNotIn('General', ' '.join(textos(b)))

    def test_sin_registro_no_queda_una_linea_suelta(self):
        # Una linea vacia dejaria un hueco y descuadraria el bloque
        b = bio(NumeroRegistro='')
        self.assertEqual(len(textos(b)), 2)
        self.assertNotIn(ETIQUETA_REGISTRO.strip(), ' '.join(textos(b)))

    def test_una_ficha_vacia_no_rompe(self):
        lineas = lineas_firma({})
        self.assertEqual([t for t, _f, _c in lineas], ['Bioanalista'])

    def test_los_espacios_sobrantes_se_quitan(self):
        b = bio(NombreCompleto='  Filadelfo G. Díaz B.  ')
        self.assertEqual(textos(b)[0], 'Filadelfo G. Díaz B.')

    def test_el_titulo_manda_sobre_el_area(self):
        # Cargado el titulo, el area deja de decidir
        b = bio(NombreArea='Hematología')
        self.assertEqual(titulo_de(b), 'LCDO. BIOANÁLISIS')


class TestLosTresInformesCoinciden(unittest.TestCase):
    """
    El pie es el mismo objeto para los tres sitios que lo pintan.

    Antes estaba copiado tres veces, y una de las copias llegaba a escribir
    "Bioanalista - Area Quimica" a fuego, atribuyendole al firmante un area
    que podia no ser la suya.
    """

    def test_el_mismo_bioanalista_da_las_mismas_lineas(self):
        b = bio()
        self.assertEqual(lineas_firma(b), lineas_firma(dict(b)))

    def test_no_se_inventa_ningun_area(self):
        b = bio(NombreArea='Química')
        self.assertNotIn('Química', ' '.join(textos(b)))


if __name__ == '__main__':
    unittest.main()

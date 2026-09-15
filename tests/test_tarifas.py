# -*- coding: utf-8 -*-
"""
Pruebas del modelo de tarifas del convenio con la clinica.

Lo que se protege: que un paciente que entra por la clinica se facture al
precio de convenio y no al ambulatorio (cobrar de menos al reclamarle a la
clinica es el error caro), que la comision cuadre, y que una prueba sin
convenio cargado no quede facturada en cero.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.tarifas import (
    COL_CLINICA, COL_CONVENIO, TARIFA_AMBULATORIO, TARIFA_CLINICA,
    comision, porcentaje_comision, precio_aplicable, precio_detalle, tarifa_de)


def prueba(base=20000.0, clinica=40000.0, convenio=30000.0):
    """El ejemplo del convenio: hematologia completa."""
    return {'PruebaID': 1, 'NombrePrueba': 'HEMATOLOGIA COMPLETA',
            'Precio': base, COL_CLINICA: clinica, COL_CONVENIO: convenio}


CASOS_CLINICA = ('Hospitalizado Particular', 'Hospitalizado Asegurado',
                 'Emergencia Particular', 'Emergencia Asegurado',
                 'Cirugia Particular', 'Cirugia Asegurado')
CASOS_AMBULATORIOS = ('Ambulatorio', 'Asegurado')


class TestQueTarifaAplica(unittest.TestCase):

    def test_las_areas_de_la_clinica_van_por_convenio(self):
        for p in CASOS_CLINICA:
            self.assertEqual(tarifa_de(p), TARIFA_CLINICA, p)

    def test_el_paciente_de_calle_va_por_ambulatorio(self):
        for p in CASOS_AMBULATORIOS:
            self.assertEqual(tarifa_de(p), TARIFA_AMBULATORIO, p)

    def test_la_tarifa_no_depende_de_quien_pague(self):
        # Particular y asegurado de la misma area pagan igual al laboratorio
        self.assertEqual(tarifa_de('Emergencia Particular'),
                         tarifa_de('Emergencia Asegurado'))


class TestPrecioAplicable(unittest.TestCase):
    """El ejemplo del convenio: 20.000 / 40.000 / 30.000."""

    def test_ambulatorio_paga_el_precio_base(self):
        self.assertEqual(precio_aplicable(prueba(), 'Ambulatorio'), 20000.0)

    def test_todos_los_casos_de_clinica_se_facturan_al_convenio(self):
        for p in CASOS_CLINICA:
            self.assertEqual(precio_aplicable(prueba(), p), 30000.0, p)

    def test_nunca_se_factura_lo_que_cobra_la_clinica(self):
        # Los 40.000 los cobra la clinica al paciente; al laboratorio le
        # corresponden 30.000. Facturar 40.000 seria cobrar de mas.
        for p in CASOS_CLINICA:
            self.assertNotEqual(precio_aplicable(prueba(), p), 40000.0)

    def test_asegurado_de_calle_paga_el_ambulatorio(self):
        # 'Asegurado' a secas no viene de la clinica
        self.assertEqual(precio_aplicable(prueba(), 'Asegurado'), 20000.0)

    def test_sin_convenio_cae_al_ambulatorio_y_no_a_cero(self):
        # Dejarlo en cero regalaria la prueba
        sin = prueba(convenio=0)
        self.assertEqual(precio_aplicable(sin, 'Cirugia Asegurado'), 20000.0)

    def test_sin_convenio_queda_marcado(self):
        d = precio_detalle(prueba(convenio=0), 'Cirugia Asegurado')
        self.assertTrue(d['sin_convenio'])

    def test_con_convenio_no_queda_marcado(self):
        d = precio_detalle(prueba(), 'Cirugia Asegurado')
        self.assertFalse(d['sin_convenio'])

    def test_el_ambulatorio_nunca_se_marca_como_sin_convenio(self):
        d = precio_detalle(prueba(convenio=0), 'Ambulatorio')
        self.assertFalse(d['sin_convenio'])

    def test_importes_ilegibles_no_rompen(self):
        mala = {'Precio': 'x', COL_CLINICA: None, COL_CONVENIO: 'y'}
        self.assertEqual(precio_aplicable(mala, 'Ambulatorio'), 0.0)
        self.assertEqual(precio_aplicable(mala, 'Cirugia Asegurado'), 0.0)

    def test_prueba_sin_columnas_de_convenio(self):
        # Base antigua: solo existe Precio
        vieja = {'Precio': 15000.0}
        self.assertEqual(precio_aplicable(vieja, 'Ambulatorio'), 15000.0)
        self.assertEqual(precio_aplicable(vieja, 'Emergencia Asegurado'), 15000.0)


class TestSinDerivaEnPesos(unittest.TestCase):
    """
    Un precio cargado en pesos tiene que facturarse por esa misma cifra.

    Los precios viven en dolares: redondear al facturar a dos centavos
    desviaba el importe hasta 15 COP por prueba, y un cultivo cargado como
    60.000 COP se facturaba a 59.985.
    """

    TASA = 3100.0

    def _prueba_en_pesos(self, amb, cli, con):
        from modulos.tarifas import convertir_a_usd
        return {'Precio': convertir_a_usd(amb, self.TASA),
                COL_CLINICA: convertir_a_usd(cli, self.TASA),
                COL_CONVENIO: convertir_a_usd(con, self.TASA)}

    def test_el_cultivo_se_factura_por_lo_cargado(self):
        p = self._prueba_en_pesos(60000, 80000, 70000)
        amb = precio_aplicable(p, 'Ambulatorio') * self.TASA
        cli = precio_aplicable(p, 'Hospitalizado Asegurado') * self.TASA
        self.assertLess(abs(amb - 60000), 1.0, f"ambulatorio salio {amb:,.0f}")
        self.assertLess(abs(cli - 70000), 1.0, f"convenio salio {cli:,.0f}")

    def test_la_comision_tampoco_se_desvia(self):
        p = self._prueba_en_pesos(60000, 80000, 70000)
        self.assertLess(abs(comision(p) * self.TASA - 10000), 1.0)

    def test_varios_importes_en_pesos(self):
        for amb, cli, con in ((20000, 40000, 30000), (60000, 80000, 70000),
                              (12500, 25000, 18000), (8700, 15000, 11200)):
            p = self._prueba_en_pesos(amb, cli, con)
            self.assertLess(
                abs(precio_aplicable(p, 'Ambulatorio') * self.TASA - amb), 1.0,
                f"ambulatorio {amb}")
            self.assertLess(
                abs(precio_aplicable(p, 'Cirugia Asegurado') * self.TASA - con), 1.0,
                f"convenio {con}")


class TestComision(unittest.TestCase):

    def test_la_comision_es_la_diferencia(self):
        self.assertEqual(comision(prueba()), 10000.0)

    def test_porcentaje_sobre_lo_que_cobra_la_clinica(self):
        # 10.000 de 40.000 = 25%
        self.assertEqual(porcentaje_comision(prueba()), 25.0)

    def test_sin_convenio_no_hay_comision_calculable(self):
        self.assertEqual(comision(prueba(convenio=0)), 0.0)
        self.assertEqual(comision(prueba(clinica=0)), 0.0)

    def test_comision_nunca_negativa(self):
        # Si alguien carga los precios al reves, no se inventa una comision
        invertida = prueba(clinica=25000.0, convenio=30000.0)
        self.assertEqual(comision(invertida), 0.0)

    def test_detalle_trae_lo_que_paga_el_paciente_en_la_clinica(self):
        d = precio_detalle(prueba(), 'Hospitalizado Asegurado')
        self.assertEqual(d['precio'], 30000.0)          # lo que facturamos
        self.assertEqual(d['precio_paciente'], 40000.0)  # lo que paga en la clinica
        self.assertEqual(d['comision_clinica'], 10000.0)

    def test_en_ambulatorio_no_hay_comision(self):
        d = precio_detalle(prueba(), 'Ambulatorio')
        self.assertEqual(d['comision_clinica'], 0.0)
        self.assertEqual(d['precio_paciente'], 20000.0)


class TestRolDeImpresionBaremo(unittest.TestCase):
    """El baremo debe poder asignarse una impresora en Configuracion."""

    def test_el_rol_existe_y_esta_en_el_panel(self):
        from modulos.impresoras import ORDEN_ROLES, ROLES
        self.assertIn('baremo', ROLES)
        self.assertIn('baremo', ORDEN_ROLES)

    def test_tiene_su_propia_columna(self):
        from modulos.impresoras import ROLES
        self.assertEqual(ROLES['baremo']['columna'], 'ImpresoraBaremo')

    def test_tiene_respaldo(self):
        from modulos.impresoras import ROLES_RESPALDO
        self.assertIn('baremo', ROLES_RESPALDO)

    def test_alias(self):
        from modulos.impresoras import ALIAS_ROLES
        for alias in ('lista_precios', 'precios', 'tarifas'):
            self.assertEqual(ALIAS_ROLES.get(alias), 'baremo')


class TestBaremoPDF(unittest.TestCase):

    def test_genera_el_documento(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("ReportLab no disponible")

        import tempfile
        from modulos.baremo_pdf import generar_baremo_pdf

        filas = [{
            'CodigoPrueba': 'HEM001', 'NombrePrueba': 'HEMATOLOGIA COMPLETA',
            'NombreArea': 'HEMATOLOGIA', 'Precio': 20000.0,
            COL_CLINICA: 40000.0, COL_CONVENIO: 30000.0,
            '_comision': 10000.0, '_pct_comision': 25.0, '_sin_convenio': False,
        }, {
            'CodigoPrueba': 'QUI005', 'NombrePrueba': 'GLICEMIA',
            'NombreArea': 'QUIMICA', 'Precio': 8000.0,
            COL_CLINICA: 0, COL_CONVENIO: 0,
            '_comision': 0, '_pct_comision': 0, '_sin_convenio': True,
        }]
        ruta = os.path.join(tempfile.gettempdir(), 'test_baremo.pdf')
        if os.path.exists(ruta):
            os.remove(ruta)
        salida = generar_baremo_pdf(ruta, filas,
                                    config_lab={'NombreLaboratorio': 'LAB'})
        self.assertEqual(salida, ruta)
        with open(ruta, 'rb') as f:
            self.assertTrue(f.read(5).startswith(b'%PDF'))
        os.remove(ruta)

    def _texto_del_pdf(self, ruta):
        """El texto del PDF, para comprobar que no se filtro un importe."""
        try:
            import fitz  # PyMuPDF, ya es dependencia del sistema
        except ImportError:
            return None
        doc = fitz.open(ruta)
        try:
            return "\n".join(pagina.get_text() for pagina in doc)
        finally:
            doc.close()

    def _filas_ejemplo(self):
        return [{
            'CodigoPrueba': 'HEM001', 'NombrePrueba': 'HEMATOLOGIA COMPLETA',
            'NombreArea': 'HEMATOLOGIA', 'Precio': 20000.0,
            COL_CLINICA: 40000.0, COL_CONVENIO: 30000.0,
            '_comision': 10000.0, '_pct_comision': 25.0, '_sin_convenio': False,
        }]

    def test_el_baremo_de_convenio_no_lleva_el_precio_ambulatorio(self):
        # El precio del paciente de calle es interno: no puede viajar en el
        # papel que se entrega en la clinica.
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("ReportLab no disponible")

        import tempfile
        from modulos.baremo_pdf import generar_baremo_pdf

        ruta = os.path.join(tempfile.gettempdir(), 'test_baremo_convenio.pdf')
        generar_baremo_pdf(ruta, self._filas_ejemplo(),
                           config_lab={'NombreLaboratorio': 'LAB'})
        texto = self._texto_del_pdf(ruta)
        os.remove(ruta)
        if texto is None:
            self.skipTest("PyMuPDF no disponible para leer el PDF")

        self.assertNotIn('20,000.00', texto, "se filtro el precio ambulatorio")
        self.assertNotIn('Ambulatorio', texto)
        # Lo del convenio si tiene que estar
        self.assertIn('40,000.00', texto)
        self.assertIn('30,000.00', texto)

    def test_la_version_interna_si_lo_incluye_y_se_rotula(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("ReportLab no disponible")

        import tempfile
        from modulos.baremo_pdf import generar_baremo_pdf

        ruta = os.path.join(tempfile.gettempdir(), 'test_baremo_interno.pdf')
        generar_baremo_pdf(ruta, self._filas_ejemplo(),
                           config_lab={'NombreLaboratorio': 'LAB'},
                           incluir_ambulatorio=True)
        texto = self._texto_del_pdf(ruta)
        os.remove(ruta)
        if texto is None:
            self.skipTest("PyMuPDF no disponible para leer el PDF")

        self.assertIn('20,000.00', texto)
        self.assertIn('USO INTERNO', texto.upper())

    def test_ambas_versiones_se_generan(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("ReportLab no disponible")
        import tempfile
        from modulos.baremo_pdf import generar_baremo_pdf
        for interno in (False, True):
            ruta = os.path.join(tempfile.gettempdir(),
                                'test_baremo_%s.pdf' % interno)
            self.assertEqual(
                generar_baremo_pdf(ruta, self._filas_ejemplo(),
                                   incluir_ambulatorio=interno), ruta)
            os.remove(ruta)

    def test_baremo_vacio_no_rompe(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("ReportLab no disponible")
        import tempfile
        from modulos.baremo_pdf import generar_baremo_pdf
        ruta = os.path.join(tempfile.gettempdir(), 'test_baremo_vacio.pdf')
        self.assertEqual(generar_baremo_pdf(ruta, []), ruta)
        os.remove(ruta)


if __name__ == '__main__':
    unittest.main(verbosity=2)

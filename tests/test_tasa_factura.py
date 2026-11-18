# -*- coding: utf-8 -*-
"""
Pruebas de la tasa de cambio con la que nace una factura.

El documento fiscal va en bolivares (art. 8 de la SNAT/2026/00093). Una
factura en dolares necesita la tasa BCV del dia para expresar sus importes,
y el programa la guardaba en 1,0: `crear_factura` empezaba en 1.0 y solo
buscaba la tasa si quien llamaba le pasaba un gestor de tasas, cosa que la
pantalla de solicitudes -por donde salen las facturas del laboratorio- no
hace. Consecuencias: el libro de ventas contaba cada dolar como un bolivar,
y el documento que se le manda a la imprenta digital habria llevado importes
en dolares rotulados como VES.

Lo que se protege: que la tasa salga de donde esta guardada, que un 1,0 de
relleno no se tome por una tasa buena, y que sin tasa la factura quede sin
tasa -y por lo tanto sin poder emitirse- en vez de con una inventada.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.facturacion_fiscal import tasa_del_documento
from modulos.tasas_cambio import tasa_guardada
from tests.sqlite_access import DBAccessEnSqlite


def base():
    db = DBAccessEnSqlite()
    db.execute("CREATE TABLE TasasCambio (TasaID INTEGER PRIMARY KEY AUTOINCREMENT, "
               "Moneda TEXT, Tasa REAL, Fecha TEXT, Fuente TEXT)")
    return db


def guardar(db, tasa, fecha='2026-11-18', moneda='USD'):
    db.execute("INSERT INTO TasasCambio (Moneda, Tasa, Fecha, Fuente) "
               "VALUES ('%s', %s, '%s', 'BCV')" % (moneda, tasa, fecha))


class GestorFalso:
    """Como GestorTasasCambio: devuelve 1.0 cuando no encuentra nada."""

    def __init__(self, tasa=1.0):
        self.tasa = tasa

    def get_tasa_actual(self, moneda='USD'):
        return self.tasa


class TestTasaGuardada(unittest.TestCase):

    def test_sin_tabla_no_hay_tasa(self):
        self.assertIsNone(tasa_guardada(DBAccessEnSqlite()))

    def test_sin_filas_no_hay_tasa(self):
        self.assertIsNone(tasa_guardada(base()))

    def test_devuelve_la_ultima(self):
        db = base()
        guardar(db, 36.50, '2026-11-17')
        guardar(db, 41.25, '2026-11-18')
        self.assertEqual(tasa_guardada(db), 41.25)

    def test_una_tasa_en_cero_no_es_tasa(self):
        db = base()
        guardar(db, 0)
        self.assertIsNone(tasa_guardada(db))

    def test_cada_moneda_la_suya(self):
        db = base()
        guardar(db, 41.25)
        guardar(db, 0.0098, moneda='COP_USD')
        self.assertEqual(tasa_guardada(db, 'COP_USD'), 0.0098)


class TestTasaDelDocumento(unittest.TestCase):

    def test_sin_gestor_la_busca_igual(self):
        # Este es el fallo: la pantalla de solicitudes no pasa gestor_tasas
        db = base()
        guardar(db, 41.25)
        self.assertEqual(tasa_del_documento(db), 41.25)

    def test_sin_tasa_devuelve_none_y_no_inventa_uno(self):
        self.assertIsNone(tasa_del_documento(base()))

    def test_el_uno_de_relleno_no_le_gana_a_la_guardada(self):
        db = base()
        guardar(db, 41.25)
        self.assertEqual(tasa_del_documento(db, GestorFalso(1.0)), 41.25)

    def test_la_del_gestor_cuando_es_de_verdad(self):
        db = base()
        guardar(db, 36.50)
        self.assertEqual(tasa_del_documento(db, GestorFalso(41.25)), 41.25)

    def test_un_gestor_roto_no_impide_leer_la_guardada(self):
        class Roto:
            def get_tasa_actual(self, moneda='USD'):
                raise RuntimeError('sin conexion con el BCV')

        db = base()
        guardar(db, 41.25)
        self.assertEqual(tasa_del_documento(db, Roto()), 41.25)

    def test_sin_nada_guardado_vale_la_del_gestor(self):
        self.assertEqual(tasa_del_documento(base(), GestorFalso(41.25)), 41.25)


if __name__ == '__main__':
    unittest.main()

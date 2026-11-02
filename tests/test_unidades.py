# -*- coding: utf-8 -*-
"""
Pruebas del alta de unidades de medida.

Lo que se protege: que el simbolo que entra sea el que se va a imprimir al
lado del resultado, y que no acaben dos entradas que signifiquen lo mismo.
Una lista con "mg/dL" y "mg/dl" se ve igual en el desplegable y produce
informes distintos segun cual se eligio ese dia.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import unidades


class DBFalsa:
    """La tabla Unidades en memoria, con el SQL que el modulo usa."""

    def __init__(self, filas=None):
        self.filas = list(filas or [])
        self._id = max([f['UnidadID'] for f in self.filas] or [0])
        self.sql = []

    def query(self, sql):
        self.sql.append(sql)
        filas = [dict(f) for f in self.filas]
        if 'Activo = True' in sql:
            filas = [f for f in filas if f.get('Activo')]
        return sorted(filas, key=lambda f: f['Simbolo'])

    def execute(self, sql):
        self.sql.append(sql)
        import re
        m = re.search(r"VALUES \('(.*)', '(.*)', '(.*)', '(.*)', True\)$", sql)
        assert m, 'INSERT no previsto: %s' % sql
        self._id += 1
        self.filas.append({
            'UnidadID': self._id,
            'CodigoUnidad': m.group(1),
            'NombreUnidad': m.group(2).replace("''", "'"),
            'Simbolo': m.group(3),
            'TipoUnidad': m.group(4),
            'Activo': True,
        })


def _unidad(uid, simbolo, codigo=None, nombre=None, activo=True):
    return {'UnidadID': uid, 'Simbolo': simbolo,
            'CodigoUnidad': codigo or simbolo, 'NombreUnidad': nombre or simbolo,
            'TipoUnidad': 'LABORATORIO', 'Activo': activo}


class TestElSimbolo(unittest.TestCase):
    """El simbolo se guarda tal cual: es lo que se imprime."""

    def test_se_quitan_los_espacios_de_los_extremos(self):
        # Un espacio al final no se ve y la unidad no se vuelve a encontrar
        self.assertEqual(unidades.normalizar_simbolo('  RU/mL '), 'RU/mL')

    def test_se_colapsan_los_espacios_de_en_medio(self):
        self.assertEqual(unidades.normalizar_simbolo('U  Todd'), 'U Todd')

    def test_no_se_cambian_las_mayusculas(self):
        # mg no es MG, y uU/mL no es UU/mL
        self.assertEqual(unidades.normalizar_simbolo('mg/dL'), 'mg/dL')

    def test_se_conservan_los_caracteres_de_la_unidad(self):
        self.assertEqual(unidades.normalizar_simbolo('10^3/µL'), '10^3/µL')

    def test_vacio_es_vacio(self):
        self.assertEqual(unidades.normalizar_simbolo('   '), '')
        self.assertEqual(unidades.normalizar_simbolo(None), '')


class TestElCodigo(unittest.TestCase):
    """El codigo es un identificador, al estilo de los que ya hay en la tabla."""

    def test_como_los_que_ya_existen(self):
        self.assertEqual(unidades.normalizar_codigo('RU/mL'), 'RU_ML')
        self.assertEqual(unidades.normalizar_codigo('U/mL'), 'U_ML')
        self.assertEqual(unidades.normalizar_codigo('mg/dL'), 'MG_DL')

    def test_los_simbolos_raros_no_dejan_basura(self):
        self.assertEqual(unidades.normalizar_codigo('10^6/uL'), '10_6_UL')
        self.assertEqual(unidades.normalizar_codigo('%'), 'UNIDAD')

    def test_los_acentos_y_el_micro_se_pasan_a_ascii(self):
        self.assertEqual(unidades.normalizar_codigo('10^3/µL'), '10_3_L')

    def test_nunca_queda_vacio(self):
        self.assertEqual(unidades.normalizar_codigo(''), 'UNIDAD')


class TestCrear(unittest.TestCase):

    def test_se_crea_la_unidad(self):
        db = DBFalsa()
        ok, msg, u = unidades.crear(db, 'RU/mL', 'Unidades relativas por mililitro')
        self.assertTrue(ok, msg)
        self.assertEqual(u['Simbolo'], 'RU/mL')
        self.assertEqual(u['CodigoUnidad'], 'RU_ML')
        self.assertEqual(u['NombreUnidad'], 'Unidades relativas por mililitro')
        self.assertTrue(u['Activo'])

    def test_se_rellenan_todos_los_campos(self):
        # El alta automatica del arranque solo ponia el simbolo, y por eso la
        # tabla tiene filas a medias
        db = DBFalsa()
        _, _, u = unidades.crear(db, 'U Todd')
        self.assertTrue(u['CodigoUnidad'])
        self.assertTrue(u['NombreUnidad'])
        self.assertEqual(u['TipoUnidad'], 'LABORATORIO')

    def test_sin_nombre_el_nombre_es_el_simbolo(self):
        db = DBFalsa()
        _, _, u = unidades.crear(db, 'ng/mL')
        self.assertEqual(u['NombreUnidad'], 'ng/mL')

    def test_un_simbolo_vacio_no_crea_nada(self):
        db = DBFalsa()
        ok, msg, u = unidades.crear(db, '   ')
        self.assertFalse(ok)
        self.assertIsNone(u)
        self.assertEqual(db.filas, [])

    def test_el_tipo_se_respeta(self):
        db = DBFalsa()
        _, _, u = unidades.crear(db, 'seg', tipo='Tiempo')
        self.assertEqual(u['TipoUnidad'], 'Tiempo')

    def test_una_comilla_en_el_nombre_no_rompe_el_sql(self):
        db = DBFalsa()
        ok, _, u = unidades.crear(db, 'mOsm/kg', "Osmolalidad 'plasmatica'")
        self.assertTrue(ok)
        self.assertIn("'plasmatica'", u['NombreUnidad'])


class TestElCodigoNoChoca(unittest.TestCase):
    """
    Dos simbolos distintos pueden dar el mismo codigo: '%' y ',' no dejan
    ningun caracter util. El simbolo distingue la unidad, el codigo solo
    tiene que ser unico.
    """

    def test_un_codigo_ya_usado_se_desvia(self):
        db = DBFalsa([_unidad(1, '%', codigo='UNIDAD')])
        ok, _, u = unidades.crear(db, ',')
        self.assertTrue(ok)
        self.assertEqual(u['CodigoUnidad'], 'UNIDAD_2')

    def test_sigue_buscando_hasta_encontrar_libre(self):
        db = DBFalsa([_unidad(1, '%', codigo='UNIDAD'),
                      _unidad(2, ',', codigo='UNIDAD_2')])
        _, _, u = unidades.crear(db, '·')
        self.assertEqual(u['CodigoUnidad'], 'UNIDAD_3')

    def test_un_codigo_libre_se_deja_como_esta(self):
        db = DBFalsa([_unidad(1, 'mg/dL', codigo='MG_DL')])
        _, _, u = unidades.crear(db, 'RU/mL')
        self.assertEqual(u['CodigoUnidad'], 'RU_ML')


class TestNoSeDuplica(unittest.TestCase):
    """
    Dos unidades que significan lo mismo son dos informes distintos. Cuando
    ya existe una equivalente se devuelve ESA, para que la ventana la
    seleccione en vez de crear una gemela.
    """

    def test_el_mismo_simbolo_no_se_repite(self):
        db = DBFalsa([_unidad(1, 'mg/dL')])
        ok, msg, u = unidades.crear(db, 'mg/dL')
        self.assertFalse(ok)
        self.assertEqual(u['UnidadID'], 1)
        self.assertEqual(len(db.filas), 1)

    def test_cambiando_las_mayusculas_tampoco(self):
        db = DBFalsa([_unidad(1, 'mg/dL')])
        ok, _, u = unidades.crear(db, 'MG/DL')
        self.assertFalse(ok)
        self.assertEqual(u['UnidadID'], 1)

    def test_con_espacios_de_mas_tampoco(self):
        db = DBFalsa([_unidad(1, 'mg/dL')])
        ok, _, u = unidades.crear(db, 'mg / dl')
        self.assertFalse(ok)

    def test_una_unidad_distinta_si_entra(self):
        db = DBFalsa([_unidad(1, 'mg/dL')])
        ok, _, _ = unidades.crear(db, 'mg/L')
        self.assertTrue(ok)
        self.assertEqual(len(db.filas), 2)

    def test_el_mensaje_dice_como_se_llama_la_que_habia(self):
        db = DBFalsa([_unidad(1, 'mg/dL')])
        _, msg, _ = unidades.crear(db, 'MG/DL')
        self.assertIn('mg/dL', msg)


class TestBuscarYListar(unittest.TestCase):

    def test_se_encuentra_sin_distinguir_forma(self):
        db = DBFalsa([_unidad(7, 'RU/mL')])
        self.assertEqual(unidades.buscar_por_simbolo(db, 'ru / ml')['UnidadID'], 7)

    def test_lo_que_no_esta_no_se_encuentra(self):
        db = DBFalsa([_unidad(7, 'RU/mL')])
        self.assertIsNone(unidades.buscar_por_simbolo(db, 'pg/mL'))

    def test_un_simbolo_vacio_no_encuentra_nada(self):
        db = DBFalsa([_unidad(7, 'RU/mL')])
        self.assertIsNone(unidades.buscar_por_simbolo(db, ''))

    def test_listar_puede_filtrar_las_inactivas(self):
        db = DBFalsa([_unidad(1, 'mg/dL'), _unidad(2, 'vieja', activo=False)])
        self.assertEqual(len(unidades.listar(db)), 2)
        self.assertEqual(len(unidades.listar(db, solo_activas=True)), 1)


class TestUnaBaseQueFalla(unittest.TestCase):
    """Si la base da error se informa; no se inventa que se guardo."""

    def test_un_error_al_insertar_se_devuelve(self):
        class DBRota(DBFalsa):
            def execute(self, sql):
                raise RuntimeError('tabla bloqueada')

        ok, msg, u = unidades.crear(DBRota(), 'RU/mL')
        self.assertFalse(ok)
        self.assertIsNone(u)
        self.assertIn('tabla bloqueada', msg)

    def test_un_error_al_leer_no_rompe(self):
        class DBRota:
            def query(self, sql):
                raise RuntimeError('sin conexion')

        self.assertEqual(unidades.listar(DBRota()), [])


if __name__ == '__main__':
    unittest.main()

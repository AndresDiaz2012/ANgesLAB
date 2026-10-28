# -*- coding: utf-8 -*-
"""
Pruebas de los rangos de numeros de control (SNAT/2026/00093, art. 9).

Lo que se protege: que no se emita una factura con un numero que nadie
autorizo, y que no se repita un numero en dos facturas. Lo primero lo
detecta una inspeccion; lo segundo no tiene arreglo despues.

La base se simula en memoria: lo que se prueba es la logica de los rangos,
no que Access sepa hacer un UPDATE.
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import rangos_control as rc


class DBFalsa:
    """Una tabla de rangos en memoria, con el minimo de SQL que se usa."""

    def __init__(self):
        self.filas = []
        self._id = 0

    def query_one(self, sql):
        if 'RangoID' in sql and 'SELECT TOP 1' in sql:
            return {'RangoID': 1} if True else None
        return None

    def query(self, sql):
        filas = [dict(f) for f in self.filas]
        if 'Activo] = True' in sql:
            filas = [f for f in filas if f.get('Activo')]
        return sorted(filas, key=lambda f: (f['Identificador'], f['Desde']))

    def execute(self, sql):
        if sql.startswith('INSERT INTO'):
            import re
            vals = re.search(r'VALUES\s*\((.*)\)\s*$', sql, re.S).group(1)
            partes = _partir_valores(vals)
            self._id += 1
            self.filas.append({
                'RangoID': self._id,
                'Identificador': int(partes[0]),
                'Desde': int(partes[1]),
                'Hasta': int(partes[2]),
                'Siguiente': int(partes[3]),
                'FechaAsignacion': datetime.now(),
                'ImprentaNombre': partes[5].strip("'"),
                'ImprentaRIF': partes[6].strip("'"),
                'ImprentaProvidencia': partes[7].strip("'"),
                'Activo': True,
                'Observaciones': partes[9].strip("'"),
            })
            return
        if sql.startswith('UPDATE'):
            import re
            sig = int(re.search(r'\[Siguiente\] = (\d+)', sql).group(1))
            rid = int(re.search(r'\[RangoID\] = (\d+)', sql).group(1))
            for f in self.filas:
                if f['RangoID'] == rid:
                    f['Siguiente'] = sig
            return
        raise AssertionError('SQL no previsto: %s' % sql[:60])


def _partir_valores(texto):
    """Separa los valores de un INSERT respetando las comillas."""
    partes, actual, dentro = [], '', False
    for c in texto:
        if c == "'":
            dentro = not dentro
            actual += c
        elif c == ',' and not dentro:
            partes.append(actual.strip())
            actual = ''
        else:
            actual += c
    partes.append(actual.strip())
    return partes


class BaseRangos(unittest.TestCase):

    def setUp(self):
        self.db = DBFalsa()

    def cargar(self, desde, hasta, ident=0, **kw):
        return rc.registrar_rango(self.db, desde, hasta, identificador=ident, **kw)


class TestCargarRangos(BaseRangos):

    def test_se_carga_un_rango(self):
        ok, msg = self.cargar(1, 1000)
        self.assertTrue(ok, msg)
        self.assertEqual(rc.quedan(self.db), 1000)

    def test_dos_rangos_que_se_solapan_no(self):
        # Dos facturas con el mismo numero de control es justo lo que estos
        # numeros existen para impedir
        self.cargar(1, 1000)
        ok, msg = self.cargar(500, 1500)
        self.assertFalse(ok)
        self.assertIn('solapa', msg)

    def test_un_rango_pegado_al_anterior_si(self):
        self.cargar(1, 1000)
        ok, _ = self.cargar(1001, 2000)
        self.assertTrue(ok)
        self.assertEqual(rc.quedan(self.db), 2000)

    def test_el_mismo_rango_en_otro_identificador_si(self):
        self.cargar(1, 1000, ident=0)
        ok, _ = self.cargar(1, 1000, ident=1)
        self.assertTrue(ok)

    def test_al_reves_no(self):
        ok, msg = self.cargar(1000, 1)
        self.assertFalse(ok)

    def test_mas_de_ocho_digitos_no(self):
        ok, msg = self.cargar(1, 999999999)
        self.assertFalse(ok)
        self.assertIn('ocho digitos', msg)

    def test_identificador_de_mas_de_dos_digitos_no(self):
        ok, _ = self.cargar(1, 10, ident=100)
        self.assertFalse(ok)


class TestGastarNumeros(BaseRangos):

    def test_salen_en_orden(self):
        self.cargar(1, 3)
        nums = [rc.tomar_numero(self.db)['numero'] for _ in range(3)]
        self.assertEqual(nums, ['00-00000001', '00-00000002', '00-00000003'])

    def test_ninguno_se_repite(self):
        self.cargar(1, 50)
        nums = [rc.tomar_numero(self.db)['numero'] for _ in range(50)]
        self.assertEqual(len(set(nums)), 50)

    def test_agotado_devuelve_none_y_no_inventa(self):
        # Poner un numero fuera del rango autorizado es peor que no facturar
        self.cargar(1, 2)
        rc.tomar_numero(self.db)
        rc.tomar_numero(self.db)
        self.assertIsNone(rc.tomar_numero(self.db))

    def test_sigue_por_el_segundo_rango(self):
        self.cargar(1, 2)
        self.cargar(3, 4)
        nums = [rc.tomar_numero(self.db)['numero'] for _ in range(4)]
        self.assertEqual(nums[-1], '00-00000004')

    def test_dice_cuantos_quedan(self):
        self.cargar(1, 10)
        self.assertEqual(rc.tomar_numero(self.db)['quedan'], 9)

    def test_sin_rango_cargado_no_da_numero(self):
        self.assertIsNone(rc.tomar_numero(self.db))


class TestReconstruirUnaFacturaVieja(BaseRangos):
    """
    Una factura se reimprime meses despues y tiene que volver a salir con el
    rango y la fecha que llevaba, no con los del rango vigente entonces.
    """

    def test_se_encuentra_el_rango_de_un_numero_emitido(self):
        self.cargar(1, 1000, imprenta={'nombre': 'IMPRENTA CA',
                                       'rif': 'J-1', 'providencia': 'P-1'})
        d = rc.datos_del_numero(self.db, '00-00000500')
        self.assertEqual((d['desde'], d['hasta']), (1, 1000))
        self.assertEqual(d['imprenta_nombre'], 'IMPRENTA CA')

    def test_un_numero_de_otro_rango_no_se_confunde(self):
        self.cargar(1, 10)
        self.cargar(11, 20)
        self.assertEqual(rc.datos_del_numero(self.db, '00-00000015')['desde'], 11)

    def test_un_numero_que_no_es_de_ningun_rango(self):
        self.cargar(1, 10)
        self.assertIsNone(rc.datos_del_numero(self.db, '00-00009999'))

    def test_un_numero_ilegible_no_rompe(self):
        self.assertIsNone(rc.datos_del_numero(self.db, 'xxx'))
        self.assertIsNone(rc.datos_del_numero(self.db, None))


class TestFormatoDelNumero(unittest.TestCase):
    """Articulo 9: dos digitos de identificador y hasta ocho de secuencial."""

    def test_dos_mas_ocho(self):
        self.assertEqual(rc.formatear(0, 1), '00-00000001')
        self.assertEqual(rc.formatear(7, 1234), '07-00001234')

    def test_se_parte_de_vuelta(self):
        self.assertEqual(rc.partir('07-00001234'), (7, 1234))

    def test_tolera_el_formato_viejo_sin_guion(self):
        self.assertEqual(rc.partir('0000001234'), (0, 1234))

    def test_el_texto_que_va_en_la_factura(self):
        t = rc.texto_rango({'identificador': 0, 'desde': 1, 'hasta': 1000})
        self.assertIn('desde el N° 00-00000001', t)
        self.assertIn('hasta el N° 00-00001000', t)

    def test_sin_datos_no_escribe_nada(self):
        self.assertEqual(rc.texto_rango(None), '')


if __name__ == '__main__':
    unittest.main()

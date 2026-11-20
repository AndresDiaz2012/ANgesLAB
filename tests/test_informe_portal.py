# -*- coding: utf-8 -*-
"""
Pruebas de la regla del informe de resultados (modulos/informe_resultados.py).

Habia dos codigos respondiendo a la misma pregunta -que parametros salen en
el informe, con que valor, unidad y rango- y no respondian lo mismo. El
informe impreso resolvia bien; el que el paciente abre desde el codigo QR
pedia columnas que no existen en la base (ValorNumerico, ValorTexto,
ResultadosParametros.UnidadID), Access rechazaba la consulta entera, un
`except Exception: pass` se tragaba el error y el PDF salia con el nombre de
las pruebas y ninguna cifra.

Ahora la regla vive una sola vez y los dos informes la usan. Aqui se prueba
la regla: el orden, los parametros sin capturar, la unidad y los cuatro pasos
del rango de referencia.
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import informe_resultados as ir
from modulos.envio_resultados import GeneradorPDF
from tests.sqlite_access import DBAccessEnSqlite

PRUEBA = 7


def base():
    """Las tablas del informe, con los nombres de columna de la base real."""
    db = DBAccessEnSqlite()
    db.execute("CREATE TABLE ResultadosParametros (ResultadoParamID INTEGER PRIMARY KEY "
               "AUTOINCREMENT, DetalleID INTEGER, ParametroID INTEGER, Valor TEXT, "
               "Estado TEXT, FechaCaptura TEXT, UsuarioCaptura TEXT, ValorReferencia TEXT, "
               "FueraDeRango INTEGER, TipoAlerta TEXT)")
    db.execute("CREATE TABLE Parametros (ParametroID INTEGER PRIMARY KEY, CodigoParametro TEXT, "
               "NombreParametro TEXT, UnidadID INTEGER, Observaciones TEXT, Seccion TEXT)")
    db.execute("CREATE TABLE Unidades (UnidadID INTEGER PRIMARY KEY, CodigoUnidad TEXT, "
               "NombreUnidad TEXT, Simbolo TEXT)")
    db.execute("CREATE TABLE ParametrosPrueba (ParametroPruebaID INTEGER PRIMARY KEY "
               "AUTOINCREMENT, PruebaID INTEGER, ParametroID INTEGER, Secuencia INTEGER)")
    db.execute("CREATE TABLE Solicitudes (SolicitudID INTEGER PRIMARY KEY, PacienteID INTEGER)")
    db.execute("CREATE TABLE Pacientes (PacienteID INTEGER PRIMARY KEY, Sexo TEXT, "
               "FechaNacimiento TEXT)")
    db.execute("INSERT INTO Unidades VALUES (1, 'GDL', 'gramos por decilitro', 'g/dL')")
    db.execute("INSERT INTO Unidades VALUES (2, 'PCT', 'por ciento', '%')")
    # HEMATOCRITO va primero en esta prueba; OBSERVACIONES no tiene unidad
    db.execute("INSERT INTO Parametros VALUES (10, 'HB', 'HEMOGLOBINA', 1, "
               "'12.0 - 15.0 g/dL', 'SERIE ROJA')")
    db.execute("INSERT INTO Parametros VALUES (11, 'HTO', 'HEMATOCRITO', 2, "
               "'36 - 47 %', 'SERIE ROJA')")
    db.execute("INSERT INTO Parametros VALUES (12, 'OBS', 'OBSERVACIONES', NULL, NULL, NULL)")
    db.execute("INSERT INTO Parametros VALUES (13, 'VCM', 'VCM', NULL, '( 80 - 100 ) fL', NULL)")
    for secuencia, pid in ((1, 11), (2, 10), (3, 12), (4, 13)):
        db.execute("INSERT INTO ParametrosPrueba (PruebaID, ParametroID, Secuencia) "
                   "VALUES (%d, %d, %d)" % (PRUEBA, pid, secuencia))
    return db


def capturar(db, detalle, parametro, valor, referencia='', fuera=0):
    db.execute("INSERT INTO ResultadosParametros (DetalleID, ParametroID, Valor, "
               "ValorReferencia, FueraDeRango) VALUES (%d, %d, '%s', '%s', %d)"
               % (detalle, parametro, valor, referencia, fuera))


class GestorRefFalso:
    """Como valores_referencia: devuelve la variante por edad y sexo, o None."""

    def __init__(self, variantes=None):
        self.variantes = variantes or {}
        self.pedidos = None

    def resolver_lote(self, parametro_ids, sexo, fecha_nacimiento):
        self.pedidos = (list(parametro_ids), sexo, fecha_nacimiento)
        return {pid: self.variantes.get(pid) for pid in parametro_ids}


def filas(db, detalle=500, **kw):
    return ir.parametros_del_informe(db, detalle, PRUEBA, **kw)


class TestQueSaleEnElInforme(unittest.TestCase):

    def setUp(self):
        self.db = base()

    def test_el_valor_la_unidad_y_el_rango(self):
        capturar(self.db, 500, 10, '12.4')
        f = filas(self.db)[0]
        self.assertEqual((f['nombre'], f['valor'], f['unidad'], f['referencia']),
                         ('HEMOGLOBINA', '12.4', 'g/dL', '12.0 - 15.0 g/dL'))
        self.assertEqual(f['seccion'], 'SERIE ROJA')

    def test_un_parametro_sin_capturar_no_se_imprime(self):
        capturar(self.db, 500, 10, '12.4')
        capturar(self.db, 500, 11, '')
        capturar(self.db, 500, 12, '   ')
        self.assertEqual([f['nombre'] for f in filas(self.db)], ['HEMOGLOBINA'])

    def test_el_orden_es_el_de_la_prueba(self):
        capturar(self.db, 500, 10, '12.4')
        capturar(self.db, 500, 11, '42')
        self.assertEqual([f['nombre'] for f in filas(self.db)],
                         ['HEMATOCRITO', 'HEMOGLOBINA'])

    def test_un_valor_de_texto_es_un_resultado(self):
        capturar(self.db, 500, 12, 'Muestra hemolizada')
        f = filas(self.db)[0]
        self.assertEqual(f['valor'], 'Muestra hemolizada')
        self.assertEqual(f['unidad'], '')

    def test_lo_de_otro_detalle_no_se_mezcla(self):
        capturar(self.db, 500, 10, '12.4')
        capturar(self.db, 501, 10, '9.5')
        self.assertEqual([f['valor'] for f in filas(self.db)], ['12.4'])

    def test_lo_fuera_de_rango_viene_marcado(self):
        capturar(self.db, 500, 10, '9.5', fuera=1)
        self.assertTrue(filas(self.db)[0]['fuera_de_rango'])

    def test_sin_nada_capturado_no_hay_informe(self):
        self.assertEqual(filas(self.db, detalle=999), [])

    def test_un_resultado_de_otra_prueba_no_entra(self):
        # Un parametro que ya no pertenece a la prueba: no se informa
        capturar(self.db, 500, 99, '1234')
        capturar(self.db, 500, 10, '12.4')
        self.assertEqual([f['nombre'] for f in filas(self.db)], ['HEMOGLOBINA'])


class TestElRangoDeReferencia(unittest.TestCase):
    """Los cuatro pasos, en orden."""

    def setUp(self):
        self.db = base()
        self.fn = datetime(2020, 5, 1)

    def test_manda_la_variante_por_edad_y_sexo(self):
        capturar(self.db, 500, 10, '12.4', '11.0 - 14.0 g/dL')
        g = GestorRefFalso({10: '10.5 - 13.5 g/dL (lactante)'})
        f = filas(self.db, sexo='F', fecha_nacimiento=self.fn, gestor_ref=g)[0]
        self.assertEqual(f['referencia'], '10.5 - 13.5 g/dL (lactante)')
        self.assertEqual(g.pedidos, ([10], 'F', self.fn))

    def test_sin_variante_vale_lo_guardado_al_capturar(self):
        capturar(self.db, 500, 10, '12.4', '11.0 - 14.0 g/dL')
        f = filas(self.db, sexo='F', fecha_nacimiento=self.fn,
                  gestor_ref=GestorRefFalso())[0]
        self.assertEqual(f['referencia'], '11.0 - 14.0 g/dL')

    def test_sin_nada_guardado_vale_el_del_parametro(self):
        capturar(self.db, 500, 10, '12.4')
        f = filas(self.db, sexo='F', fecha_nacimiento=self.fn,
                  gestor_ref=GestorRefFalso())[0]
        self.assertEqual(f['referencia'], '12.0 - 15.0 g/dL')

    def test_sin_fecha_de_nacimiento_no_se_pide_variante(self):
        # Sin edad no hay variante que resolver: lo hacia asi el informe impreso
        capturar(self.db, 500, 10, '12.4')
        g = GestorRefFalso({10: 'no deberia usarse'})
        f = filas(self.db, sexo='F', fecha_nacimiento=None, gestor_ref=g)[0]
        self.assertIsNone(g.pedidos)
        self.assertEqual(f['referencia'], '12.0 - 15.0 g/dL')

    def test_la_unidad_sale_del_rango_si_el_parametro_no_la_tiene(self):
        capturar(self.db, 500, 13, '92')
        self.assertEqual(filas(self.db)[0]['unidad'], 'fL')

    def test_unidad_del_texto(self):
        self.assertEqual(ir.unidad_del_texto('( 70 - 110 ) mg/dL'), 'mg/dL')
        self.assertEqual(ir.unidad_del_texto('12.0 - 17.0 g/dL'), 'g/dL')
        self.assertEqual(ir.unidad_del_texto('37 - 52 %'), '%')
        self.assertEqual(ir.unidad_del_texto('Negativo'), '')
        self.assertEqual(ir.unidad_del_texto(''), '')


class TestElPacienteDeLaSolicitud(unittest.TestCase):

    def test_trae_sexo_y_fecha_de_nacimiento(self):
        db = base()
        db.execute("INSERT INTO Pacientes VALUES (5, 'F', '2020-05-01')")
        db.execute("INSERT INTO Solicitudes VALUES (77, 5)")
        self.assertEqual(ir.paciente_de_solicitud(db, 77), ('F', '2020-05-01'))

    def test_una_solicitud_que_no_existe_no_rompe(self):
        self.assertEqual(ir.paciente_de_solicitud(base(), 404), (None, None))


class TestElInformeDelPortalUsaLaMismaRegla(unittest.TestCase):

    def test_el_portal_delega_en_el_modulo(self):
        db = base()
        capturar(db, 500, 10, '12.4')
        capturar(db, 500, 11, '42')
        delegado = GeneradorPDF(db).resultados_de_detalle(500, PRUEBA)
        self.assertEqual(delegado, ir.parametros_del_informe(db, 500, PRUEBA))
        self.assertEqual([f['nombre'] for f in delegado],
                         ['HEMATOCRITO', 'HEMOGLOBINA'])

    def test_sin_prueba_no_arma_informe(self):
        # Sin la prueba no hay ParametrosPrueba del que sacar el orden
        db = base()
        capturar(db, 500, 10, '12.4')
        self.assertEqual(GeneradorPDF(db).resultados_de_detalle(500, None), [])


if __name__ == '__main__':
    unittest.main()

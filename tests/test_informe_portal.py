# -*- coding: utf-8 -*-
"""
Pruebas del informe de resultados que el paciente abre desde el codigo QR.

El portal decia "Resultados listos", el paciente metia los ultimos cuatro
digitos de su cedula y el PDF que recibia traia el encabezado del
laboratorio, sus datos, el nombre de las once pruebas... y ninguna cifra.

La causa: la consulta de resultados pedia columnas que no existen en la base
-ValorNumerico, ValorTexto y ResultadosParametros.UnidadID-, Access la
rechazaba entera y un `except Exception: pass` se tragaba el error. En la
base los valores estan en ResultadosParametros.Valor, uno solo, y la unidad
sale de Parametros.UnidadID como en el informe impreso.

Lo que se protege: que el informe del portal traiga los valores, su unidad y
su rango de referencia, con los nombres de columna que la base tiene de
verdad.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.envio_resultados import GeneradorPDF
from tests.sqlite_access import DBAccessEnSqlite


def base():
    """Las tablas de resultados con los nombres de columna de la base real."""
    db = DBAccessEnSqlite()
    db.execute("CREATE TABLE ResultadosParametros (ResultadoParamID INTEGER PRIMARY KEY "
               "AUTOINCREMENT, DetalleID INTEGER, ParametroID INTEGER, Valor TEXT, "
               "Estado TEXT, FechaCaptura TEXT, UsuarioCaptura TEXT, ValorReferencia TEXT, "
               "FueraDeRango INTEGER, TipoAlerta TEXT)")
    db.execute("CREATE TABLE Parametros (ParametroID INTEGER PRIMARY KEY, CodigoParametro TEXT, "
               "NombreParametro TEXT, UnidadID INTEGER, Seccion TEXT)")
    db.execute("CREATE TABLE Unidades (UnidadID INTEGER PRIMARY KEY, CodigoUnidad TEXT, "
               "NombreUnidad TEXT, Simbolo TEXT)")
    db.execute("CREATE TABLE ParametrosPrueba (ParametroPruebaID INTEGER PRIMARY KEY "
               "AUTOINCREMENT, PruebaID INTEGER, ParametroID INTEGER, Secuencia INTEGER)")
    db.execute("INSERT INTO Unidades VALUES (1, 'GDL', 'gramos por decilitro', 'g/dL')")
    db.execute("INSERT INTO Unidades VALUES (2, 'PCT', 'por ciento', '%')")
    db.execute("INSERT INTO Parametros VALUES (10, 'HB', 'HEMOGLOBINA', 1, 'General')")
    db.execute("INSERT INTO Parametros VALUES (11, 'HTO', 'HEMATOCRITO', 2, 'General')")
    db.execute("INSERT INTO Parametros VALUES (12, 'OBS', 'OBSERVACIONES', NULL, 'General')")
    # En la prueba 7 el hematocrito va antes que la hemoglobina
    db.execute("INSERT INTO ParametrosPrueba (PruebaID, ParametroID, Secuencia) VALUES (7, 11, 1)")
    db.execute("INSERT INTO ParametrosPrueba (PruebaID, ParametroID, Secuencia) VALUES (7, 10, 2)")
    db.execute("INSERT INTO ParametrosPrueba (PruebaID, ParametroID, Secuencia) VALUES (7, 12, 3)")
    return db


def capturar(db, detalle, parametro, valor, referencia='', fuera=0):
    db.execute("INSERT INTO ResultadosParametros (DetalleID, ParametroID, Valor, "
               "ValorReferencia, FueraDeRango) VALUES (%d, %d, '%s', '%s', %d)"
               % (detalle, parametro, valor, referencia, fuera))


class TestResultadosDelInforme(unittest.TestCase):

    def setUp(self):
        self.db = base()
        self.g = GeneradorPDF(self.db)

    def test_trae_el_valor_la_unidad_y_la_referencia(self):
        capturar(self.db, 500, 10, '12.0', '12.0 - 15.0 g/dL')
        filas = self.g.resultados_de_detalle(500, 7)
        self.assertEqual(len(filas), 1)
        self.assertEqual((filas[0]['NombreParametro'], filas[0]['Valor'],
                          filas[0]['Simbolo'], filas[0]['ValorReferencia']),
                         ('HEMOGLOBINA', '12.0', 'g/dL', '12.0 - 15.0 g/dL'))

    def test_un_parametro_sin_capturar_no_se_imprime(self):
        capturar(self.db, 500, 10, '12.0')
        capturar(self.db, 500, 11, '')
        capturar(self.db, 500, 12, '   ')
        filas = self.g.resultados_de_detalle(500, 7)
        self.assertEqual([f['NombreParametro'] for f in filas], ['HEMOGLOBINA'])

    def test_respeta_el_orden_de_la_prueba(self):
        capturar(self.db, 500, 10, '12.0')
        capturar(self.db, 500, 11, '42')
        filas = self.g.resultados_de_detalle(500, 7)
        self.assertEqual([f['NombreParametro'] for f in filas],
                         ['HEMATOCRITO', 'HEMOGLOBINA'])

    def test_sin_la_prueba_ordena_por_nombre(self):
        capturar(self.db, 500, 10, '12.0')
        capturar(self.db, 500, 11, '42')
        filas = self.g.resultados_de_detalle(500)
        self.assertEqual([f['NombreParametro'] for f in filas],
                         ['HEMATOCRITO', 'HEMOGLOBINA'])

    def test_un_valor_de_texto_vale_igual(self):
        capturar(self.db, 500, 12, 'Muestra hemolizada')
        filas = self.g.resultados_de_detalle(500, 7)
        self.assertEqual(filas[0]['Valor'], 'Muestra hemolizada')
        self.assertFalse(filas[0]['Simbolo'])   # un texto no lleva unidad

    def test_lo_de_otra_solicitud_no_se_mezcla(self):
        capturar(self.db, 500, 10, '12.0')
        capturar(self.db, 501, 10, '9.5')
        self.assertEqual([f['Valor'] for f in self.g.resultados_de_detalle(500, 7)],
                         ['12.0'])

    def test_lo_fuera_de_rango_viene_marcado(self):
        capturar(self.db, 500, 10, '9.5', '12.0 - 15.0 g/dL', fuera=1)
        self.assertTrue(self.g.resultados_de_detalle(500, 7)[0]['FueraDeRango'])

    def test_una_prueba_sin_capturar_no_devuelve_nada(self):
        self.assertEqual(self.g.resultados_de_detalle(999, 7), [])


if __name__ == '__main__':
    unittest.main()

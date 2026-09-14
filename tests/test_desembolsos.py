# -*- coding: utf-8 -*-
"""
Pruebas del control de cartera de asegurados y de los abonos por paciente.

Lo que se protege: que no se abone a un paciente mas de lo que se le debe,
que un paciente ya liberado no vuelva a cobrarse, que el saldo y el estado
queden coherentes, y que un desembolso que cubre a varios pacientes aplique
a cada uno su importe y no uno repartido a ojo.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.desembolsos_clinica import (
    ESTADO_LIBERADA,
    ESTADO_PARCIAL,
    GestorDesembolsos,
)


class DBFalsa:
    """
    Base de datos de mentira: guarda cuentas en memoria y aplica los UPDATE
    que le interesan a estas pruebas. Evita depender de Access para
    comprobar reglas de negocio.
    """

    def __init__(self, cuentas):
        self.cuentas = {c['CuentaCobrarID']: dict(c) for c in cuentas}
        self.sql_ejecutado = []
        self.abonos = []
        self.columnas = {'CuentasPorCobrar.FechaLiberacion': True}

    def query_one(self, sql):
        if 'FROM AbonosCuentaCobrar' in sql or 'FROM [AbonosCuentaCobrar]' in sql:
            return {'AbonoID': 1}
        # Sondeo de existencia de columna
        m = re.search(r"SELECT TOP 1 (\w+) FROM (\w+)", sql)
        if m:
            col, tabla = m.group(1), m.group(2)
            if not self.columnas.get(f"{tabla}.{col}", True):
                raise Exception(f"columna {col} no existe")
            return {col: None}
        m = re.search(r"CuentaCobrarID=(\d+)", sql)
        if m:
            return self.cuentas.get(int(m.group(1)))
        return None

    def query(self, sql):
        return []

    def execute(self, sql):
        self.sql_ejecutado.append(sql)
        if sql.strip().upper().startswith('INSERT INTO [ABONOSCUENTACOBRAR]'):
            self.abonos.append(sql)
            return
        m = re.search(r"UPDATE \[CuentasPorCobrar\] SET (.+) WHERE CuentaCobrarID=(\d+)", sql)
        if m:
            cuenta = self.cuentas.get(int(m.group(2)))
            if cuenta is None:
                return
            for asignacion in m.group(1).split(', '):
                if '=' not in asignacion:
                    continue
                campo, valor = asignacion.split('=', 1)
                valor = valor.strip().strip("'")
                if valor in ('Null', '#'):
                    cuenta[campo.strip()] = None
                elif valor.startswith('#'):
                    cuenta[campo.strip()] = valor
                else:
                    try:
                        cuenta[campo.strip()] = float(valor)
                    except ValueError:
                        cuenta[campo.strip()] = valor


def cuenta(cid, monto, cobrado=0.0, nombre='PACIENTE', estado='Pendiente'):
    return {'CuentaCobrarID': cid, 'PacienteID': 10 + cid,
            'NombrePaciente': nombre, 'MontoOriginal': monto,
            'MontoCobrado': cobrado, 'SaldoPendiente': monto - cobrado,
            'Estado': estado}


class TestAbonoPorPaciente(unittest.TestCase):

    def setUp(self):
        self.db = DBFalsa([
            cuenta(1, 120.0, nombre='ANA'),
            cuenta(2, 80.0, cobrado=30.0, nombre='BRUNO', estado='Parcial'),
            cuenta(3, 50.0, cobrado=50.0, nombre='CARLA', estado='Cobrada'),
        ])
        self.g = GestorDesembolsos(self.db)

    def test_abono_parcial_deja_la_cuenta_abierta(self):
        ok, msg, det = self.g.registrar_abono(1, 40.0, usuario_id=1,
                                              registrar_en_caja=False)
        self.assertTrue(ok, msg)
        self.assertFalse(det['libera'])
        self.assertEqual(det['saldo_nuevo'], 80.0)
        self.assertEqual(self.db.cuentas[1]['Estado'], ESTADO_PARCIAL)
        self.assertEqual(self.db.cuentas[1]['MontoCobrado'], 40.0)

    def test_abono_total_libera_al_paciente(self):
        ok, msg, det = self.g.registrar_abono(1, 120.0, usuario_id=1,
                                              registrar_en_caja=False)
        self.assertTrue(ok, msg)
        self.assertTrue(det['libera'])
        self.assertEqual(det['saldo_nuevo'], 0.0)
        self.assertEqual(self.db.cuentas[1]['Estado'], ESTADO_LIBERADA)
        self.assertIn('LIBERADO', msg)

    def test_al_liberar_se_marca_la_fecha(self):
        self.g.registrar_abono(1, 120.0, usuario_id=1, registrar_en_caja=False)
        update = [s for s in self.db.sql_ejecutado if 'FechaLiberacion' in s]
        self.assertTrue(update, "no se escribio la fecha de liberacion")
        self.assertNotIn('FechaLiberacion=Null', update[0])

    def test_un_abono_parcial_no_marca_fecha_de_liberacion(self):
        self.g.registrar_abono(1, 10.0, usuario_id=1, registrar_en_caja=False)
        update = [s for s in self.db.sql_ejecutado if 'FechaLiberacion' in s]
        self.assertIn('FechaLiberacion=Null', update[0])

    def test_no_se_puede_abonar_mas_de_lo_que_se_debe(self):
        ok, msg, det = self.g.registrar_abono(1, 200.0, usuario_id=1,
                                              registrar_en_caja=False)
        self.assertFalse(ok)
        self.assertIsNone(det)
        self.assertIn('supera', msg.lower())
        self.assertEqual(self.db.cuentas[1]['MontoCobrado'], 0.0)

    def test_respeta_lo_ya_abonado(self):
        # BRUNO debe 50 de 80: 50 lo libera, 51 debe rechazarse.
        ok, _, det = self.g.registrar_abono(2, 50.0, usuario_id=1,
                                            registrar_en_caja=False)
        self.assertTrue(ok)
        self.assertTrue(det['libera'])
        self.assertEqual(self.db.cuentas[2]['MontoCobrado'], 80.0)

    def test_rechaza_pasarse_contando_lo_ya_abonado(self):
        ok, msg, _ = self.g.registrar_abono(2, 51.0, usuario_id=1,
                                            registrar_en_caja=False)
        self.assertFalse(ok)
        self.assertIn('supera', msg.lower())

    def test_paciente_ya_liberado_no_vuelve_a_cobrarse(self):
        ok, msg, det = self.g.registrar_abono(3, 10.0, usuario_id=1,
                                              registrar_en_caja=False)
        self.assertFalse(ok)
        self.assertIn('liberado', msg.lower())
        self.assertIsNone(det)

    def test_importe_cero_o_negativo_se_rechaza(self):
        for monto in (0, -20.0):
            ok, msg, _ = self.g.registrar_abono(1, monto, usuario_id=1,
                                                registrar_en_caja=False)
            self.assertFalse(ok, f"acepto {monto}")
            self.assertIn('mayor que cero', msg)

    def test_importe_ilegible_se_rechaza_sin_romper(self):
        ok, msg, _ = self.g.registrar_abono(1, 'abc', usuario_id=1,
                                            registrar_en_caja=False)
        self.assertFalse(ok)
        self.assertEqual(self.db.cuentas[1]['MontoCobrado'], 0.0)

    def test_cuenta_inexistente(self):
        ok, msg, _ = self.g.registrar_abono(999, 10.0, usuario_id=1,
                                            registrar_en_caja=False)
        self.assertFalse(ok)
        self.assertIn('no se encontro', msg.lower())

    def test_cada_abono_queda_en_el_historial(self):
        self.g.registrar_abono(1, 40.0, usuario_id=7, referencia='TRANSF-1',
                               registrar_en_caja=False)
        self.g.registrar_abono(1, 30.0, usuario_id=7, referencia='TRANSF-2',
                               registrar_en_caja=False)
        self.assertEqual(len(self.db.abonos), 2)
        self.assertIn('TRANSF-1', self.db.abonos[0])
        self.assertIn('TRANSF-2', self.db.abonos[1])

    def test_el_historial_guarda_saldo_antes_y_despues(self):
        self.g.registrar_abono(1, 40.0, usuario_id=1, registrar_en_caja=False)
        self.assertIn('120', self.db.abonos[0])  # saldo anterior
        self.assertIn('80', self.db.abonos[0])   # saldo posterior


class TestDesembolsoVariosPacientes(unittest.TestCase):

    def setUp(self):
        self.db = DBFalsa([
            cuenta(1, 120.0, nombre='ANA'),
            cuenta(2, 80.0, nombre='BRUNO'),
            cuenta(3, 200.0, nombre='CARLA'),
        ])
        self.g = GestorDesembolsos(self.db)

    def test_cada_paciente_recibe_su_importe(self):
        ok, msg, det = self.g.registrar_desembolso(
            [{'cuenta_id': 1, 'monto': 120.0},
             {'cuenta_id': 2, 'monto': 30.0}],
            usuario_id=1, registrar_en_caja=False)
        self.assertTrue(ok, msg)
        self.assertEqual(det['total'], 150.0)
        self.assertEqual(det['liberados'], 1)
        self.assertEqual(self.db.cuentas[1]['SaldoPendiente'], 0.0)
        self.assertEqual(self.db.cuentas[2]['SaldoPendiente'], 50.0)
        # El que no se incluyo no se toca
        self.assertEqual(self.db.cuentas[3]['SaldoPendiente'], 200.0)

    def test_una_linea_invalida_no_impide_las_demas(self):
        ok, msg, det = self.g.registrar_desembolso(
            [{'cuenta_id': 1, 'monto': 500.0},   # se pasa: se rechaza
             {'cuenta_id': 2, 'monto': 80.0}],   # correcta
            usuario_id=1, registrar_en_caja=False)
        self.assertTrue(ok)
        self.assertEqual(det['total'], 80.0)
        self.assertEqual(len(det['errores']), 1)
        self.assertEqual(self.db.cuentas[1]['MontoCobrado'], 0.0)
        self.assertEqual(self.db.cuentas[2]['Estado'], ESTADO_LIBERADA)

    def test_sin_lineas_no_hace_nada(self):
        ok, msg, det = self.g.registrar_desembolso([], usuario_id=1,
                                                   registrar_en_caja=False)
        self.assertFalse(ok)
        self.assertIsNone(det)

    def test_si_todas_las_lineas_fallan_se_informa(self):
        ok, msg, det = self.g.registrar_desembolso(
            [{'cuenta_id': 1, 'monto': 999.0}],
            usuario_id=1, registrar_en_caja=False)
        self.assertFalse(ok)
        self.assertIn('no se aplico', msg.lower())

    def test_las_lineas_en_cero_se_ignoran(self):
        ok, _, det = self.g.registrar_desembolso(
            [{'cuenta_id': 1, 'monto': 0},
             {'cuenta_id': 2, 'monto': 80.0}],
            usuario_id=1, registrar_en_caja=False)
        self.assertTrue(ok)
        self.assertEqual(det['total'], 80.0)
        self.assertEqual(len(det['aplicadas']), 1)

    def test_el_total_es_la_suma_de_lo_aplicado(self):
        ok, _, det = self.g.registrar_desembolso(
            [{'cuenta_id': 1, 'monto': 20.0},
             {'cuenta_id': 2, 'monto': 35.5},
             {'cuenta_id': 3, 'monto': 44.5}],
            usuario_id=1, registrar_en_caja=False)
        self.assertTrue(ok)
        self.assertAlmostEqual(det['total'], 100.0, places=2)
        self.assertAlmostEqual(
            sum(a['monto'] for a in det['aplicadas']), 100.0, places=2)


if __name__ == '__main__':
    unittest.main(verbosity=2)

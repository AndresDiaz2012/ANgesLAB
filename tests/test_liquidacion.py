# -*- coding: utf-8 -*-
"""
Pruebas de la liquidacion de la solicitud.

Lo que se protege: que liquidar dos veces la misma solicitud no duplique la
deuda (pasa al agregarle pruebas), que lo ya abonado por la clinica se
respete, y que la caja solo reciba lo realmente cobrado.
"""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.liquidacion import Liquidador


class DBFalsa:
    """
    Base de mentira: guarda cuentas por cobrar en memoria y entiende los
    INSERT y UPDATE que hace el liquidador.
    """

    def __init__(self, columnas=None):
        self.cuentas = {}          # CuentaCobrarID -> dict
        self._siguiente = 1
        self.sql = []
        self.solicitudes = {}      # SolicitudID -> MontoCobrado
        self.columnas = columnas if columnas is not None else {
            'CuentasPorCobrar.SolicitudID': True,
            'CuentasPorCobrar.TipoProcedencia': True,
            'CuentasPorCobrar.FechaLiberacion': True,
            'Solicitudes.MontoCobrado': True,
        }

    # -- lectura ----------------------------------------------------------
    def query_one(self, sql):
        m = re.search(r"SELECT TOP 1 (\w+) FROM (\w+)", sql)
        if m:
            clave = "%s.%s" % (m.group(2), m.group(1))
            if not self.columnas.get(clave, True):
                raise Exception("no existe " + m.group(1))
            return {m.group(1): None}

        if 'FROM [CuentasPorCobrar]' in sql and 'SolicitudID=' in sql:
            sid = int(re.search(r"SolicitudID=(\d+)", sql).group(1))
            for c in self.cuentas.values():
                if c.get('SolicitudID') == sid:
                    return dict(c)
            return None

        if 'FROM Solicitudes s' in sql:
            return {'PacienteID': 7, 'NombreCompleto': 'PACIENTE PRUEBA'}
        if 'FormasPago' in sql:
            return {'FormaPagoID': 1}
        return None

    def query(self, sql):
        return []

    # -- escritura ---------------------------------------------------------
    def execute(self, sql):
        self.sql.append(sql)

        if sql.startswith('UPDATE [Solicitudes]'):
            sid = int(re.search(r"SolicitudID=(\d+)", sql).group(1))
            self.solicitudes[sid] = float(
                re.search(r"MontoCobrado=([\d.]+)", sql).group(1))
            return

        if sql.startswith('INSERT INTO [CuentasPorCobrar]'):
            cols = [c.strip() for c in
                    re.search(r"\(([^)]*)\) VALUES", sql).group(1).split(',')]
            vals = re.search(r"VALUES \((.*)\)$", sql).group(1)
            partes, actual, dentro = [], '', False
            for ch in vals:
                if ch == "'":
                    dentro = not dentro
                if ch == ',' and not dentro:
                    partes.append(actual.strip())
                    actual = ''
                else:
                    actual += ch
            partes.append(actual.strip())

            fila = {'CuentaCobrarID': self._siguiente}
            for c, v in zip(cols, partes):
                v = v.strip().strip("'")
                if c in ('MontoOriginal', 'MontoCobrado', 'SaldoPendiente',
                         'SolicitudID', 'PacienteID', 'DiasVencida'):
                    try:
                        fila[c] = float(v)
                    except ValueError:
                        fila[c] = None
                else:
                    fila[c] = v
            if fila.get('SolicitudID') is not None:
                fila['SolicitudID'] = int(fila['SolicitudID'])
            self.cuentas[self._siguiente] = fila
            self._siguiente += 1
            return

        if sql.startswith('UPDATE [CuentasPorCobrar]'):
            cid = int(re.search(r"CuentaCobrarID=(\d+)", sql).group(1))
            cuenta = self.cuentas.get(cid)
            if not cuenta:
                return
            for campo in ('MontoOriginal', 'SaldoPendiente'):
                m = re.search(campo + r"=([\d.]+)", sql)
                if m:
                    cuenta[campo] = float(m.group(1))
            m = re.search(r"Estado='([^']*)'", sql)
            if m:
                cuenta['Estado'] = m.group(1)
            return

    # -- ayuda para las pruebas -------------------------------------------
    def cuentas_de(self, sol_id):
        return [c for c in self.cuentas.values() if c.get('SolicitudID') == sol_id]


DOC = {'exito': True, 'numero_recibo': 'REC-001'}


class TestLiquidacionBasica(unittest.TestCase):

    def setUp(self):
        self.db = DBFalsa()
        self.liq = Liquidador(self.db, {'UsuarioID': 1})

    def test_asegurado_no_cobra_y_abre_cuenta(self):
        r = self.liq.liquidar(1, 'S-1', 100.0, 0, 'Hospitalizado Asegurado',
                              DOC, registrar_en_caja=False)
        self.assertTrue(r['es_credito'])
        self.assertEqual(r['cobrado'], 0.0)
        self.assertEqual(r['saldo'], 100.0)
        self.assertEqual(len(self.db.cuentas_de(1)), 1)

    def test_contado_pagado_no_abre_cuenta(self):
        r = self.liq.liquidar(2, 'S-2', 100.0, 100.0, 'Ambulatorio',
                              DOC, registrar_en_caja=False)
        self.assertEqual(r['cobrado'], 100.0)
        self.assertEqual(r['saldo'], 0.0)
        self.assertEqual(len(self.db.cuentas_de(2)), 0)

    def test_abono_parcial_abre_cuenta_por_el_resto(self):
        r = self.liq.liquidar(3, 'S-3', 100.0, 30.0, 'Ambulatorio',
                              DOC, registrar_en_caja=False)
        self.assertEqual(r['cobrado'], 30.0)
        cuentas = self.db.cuentas_de(3)
        self.assertEqual(len(cuentas), 1)
        self.assertEqual(cuentas[0]['SaldoPendiente'], 70.0)

    def test_guarda_lo_cobrado_en_la_solicitud(self):
        self.liq.liquidar(4, 'S-4', 80.0, 80.0, 'Ambulatorio', DOC,
                          registrar_en_caja=False)
        self.assertEqual(self.db.solicitudes.get(4), 80.0)


class TestNoDuplicaLaDeuda(unittest.TestCase):
    """El fallo que motivo sacar esta logica de la ventana."""

    def setUp(self):
        self.db = DBFalsa()
        self.liq = Liquidador(self.db, {'UsuarioID': 1})

    def test_liquidar_dos_veces_no_crea_dos_cuentas(self):
        # Asi ocurre al agregarle pruebas a una solicitud de clinica
        self.liq.liquidar(1, 'S-1', 100.0, 0, 'Hospitalizado Asegurado', DOC,
                          registrar_en_caja=False)
        self.liq.liquidar(1, 'S-1', 150.0, 0, 'Hospitalizado Asegurado', DOC,
                          registrar_en_caja=False)

        cuentas = self.db.cuentas_de(1)
        self.assertEqual(len(cuentas), 1, "se duplico la cuenta por cobrar")
        self.assertEqual(cuentas[0]['SaldoPendiente'], 150.0)

    def test_la_segunda_liquidacion_actualiza(self):
        self.liq.liquidar(1, 'S-1', 100.0, 0, 'Emergencia Asegurado', DOC,
                          registrar_en_caja=False)
        r = self.liq.liquidar(1, 'S-1', 150.0, 0, 'Emergencia Asegurado', DOC,
                              registrar_en_caja=False)
        self.assertEqual(r['cuenta'], 'actualizada')

    def test_sin_cambios_no_toca_la_cuenta(self):
        self.liq.liquidar(1, 'S-1', 100.0, 0, 'Cirugia Asegurado', DOC,
                          registrar_en_caja=False)
        r = self.liq.liquidar(1, 'S-1', 100.0, 0, 'Cirugia Asegurado', DOC,
                              registrar_en_caja=False)
        self.assertEqual(r['cuenta'], 'sin_cambio')

    def test_respeta_lo_que_la_clinica_ya_abono(self):
        # La clinica abona 40 de 100 y despues se le agregan pruebas
        self.liq.liquidar(1, 'S-1', 100.0, 0, 'Hospitalizado Asegurado', DOC,
                          registrar_en_caja=False)
        cuenta = self.db.cuentas_de(1)[0]
        cuenta['MontoCobrado'] = 40.0
        cuenta['SaldoPendiente'] = 60.0

        self.liq.liquidar(1, 'S-1', 150.0, 0, 'Hospitalizado Asegurado', DOC,
                          registrar_en_caja=False)
        cuenta = self.db.cuentas_de(1)[0]
        self.assertEqual(cuenta['MontoOriginal'], 150.0)
        self.assertEqual(cuenta['SaldoPendiente'], 110.0)  # 150 - 40 abonados

    def test_cada_solicitud_tiene_su_cuenta(self):
        self.liq.liquidar(1, 'S-1', 100.0, 0, 'Asegurado', DOC,
                          registrar_en_caja=False)
        self.liq.liquidar(2, 'S-2', 200.0, 0, 'Asegurado', DOC,
                          registrar_en_caja=False)
        self.assertEqual(len(self.db.cuentas_de(1)), 1)
        self.assertEqual(len(self.db.cuentas_de(2)), 1)
        self.assertEqual(len(self.db.cuentas), 2)

    def test_si_deja_de_deberse_la_cuenta_se_salda(self):
        self.liq.liquidar(1, 'S-1', 100.0, 0, 'Ambulatorio', DOC,
                          registrar_en_caja=False)
        self.assertEqual(self.db.cuentas_de(1)[0]['SaldoPendiente'], 100.0)
        # Se corrige: en realidad pago todo
        self.liq.liquidar(1, 'S-1', 100.0, 100.0, 'Ambulatorio', DOC,
                          registrar_en_caja=False)
        self.assertEqual(self.db.cuentas_de(1)[0]['SaldoPendiente'], 0.0)
        self.assertEqual(self.db.cuentas_de(1)[0]['Estado'], 'Cobrada')


class TestSinDocumento(unittest.TestCase):

    def test_sin_documento_no_entra_a_caja(self):
        db = DBFalsa()
        r = Liquidador(db, {'UsuarioID': 1}).liquidar(
            1, 'S-1', 100.0, 100.0, 'Ambulatorio', doc_result=None,
            registrar_en_caja=False)
        self.assertEqual(r['cobrado'], 0.0)
        self.assertEqual(r['saldo'], 100.0)
        self.assertFalse(r['hay_documento'])
        self.assertEqual(len(db.cuentas_de(1)), 1)


class TestBaseAntigua(unittest.TestCase):
    """Una base sin las columnas nuevas no puede tumbar el guardado."""

    def test_sin_columna_solicitudid_no_rompe(self):
        db = DBFalsa(columnas={
            'CuentasPorCobrar.SolicitudID': False,
            'CuentasPorCobrar.TipoProcedencia': False,
            'CuentasPorCobrar.FechaLiberacion': False,
            'Solicitudes.MontoCobrado': False,
        })
        r = Liquidador(db, {'UsuarioID': 1}).liquidar(
            1, 'S-1', 100.0, 0, 'Asegurado', DOC, registrar_en_caja=False)
        self.assertEqual(r['saldo'], 100.0)
        self.assertEqual(len(db.cuentas), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)

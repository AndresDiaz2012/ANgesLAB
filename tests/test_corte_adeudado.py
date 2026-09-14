# -*- coding: utf-8 -*-
"""
Pruebas del corte de adeudado por area.

Lo que se protege: que cada paciente caiga en su area, que dentro de ella se
separe lo asegurado de lo particular, que el ambulatorio no se cuele en el
corte que se le presenta a la clinica, y que los totales cuadren.
"""

import os
import sys
import unittest
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos.corte_adeudado import CorteAdeudado
from modulos.procedencia import (
    AREA_AMBULATORIO, AREA_CIRUGIA, AREA_EMERGENCIA, AREA_HOSPITALIZACION,
    AREAS_CLINICA, PROCEDENCIAS, area_servicio, es_area_clinica, es_credito)


class DBFalsa:
    """Devuelve unas cuentas fijas, sin depender de Access."""

    def __init__(self, cuentas, columnas=None):
        self.cuentas = cuentas
        self.columnas = columnas if columnas is not None else {
            'CuentasPorCobrar.TipoProcedencia': True,
            'CuentasPorCobrar.SolicitudID': True,
        }
        self.ultima_sql = ''

    def query_one(self, sql):
        if 'SELECT TOP 1' in sql:
            for clave, existe in self.columnas.items():
                tabla, col = clave.split('.')
                if col in sql and tabla in sql:
                    if not existe:
                        raise Exception('no existe ' + col)
                    return {col: None}
            return {}
        return None

    def query(self, sql):
        self.ultima_sql = sql
        return list(self.cuentas)


def cuenta(nombre, saldo, proc, monto=None, cobrado=0.0, obs='prueba'):
    return {
        'CuentaCobrarID': abs(hash(nombre)) % 10000,
        'PacienteID': 1,
        'NombrePaciente': nombre,
        'FechaEmision': datetime(2026, 9, 1),
        'MontoOriginal': monto if monto is not None else saldo,
        'MontoCobrado': cobrado,
        'SaldoPendiente': saldo,
        'Estado': 'Pendiente',
        'Observaciones': obs,
        'TipoProcedencia': proc,
    }


class TestAreaDeServicio(unittest.TestCase):
    """El area es independiente de quien paga."""

    def test_hospitalizacion(self):
        for p in ('Hospitalizado Particular', 'Hospitalizado Asegurado'):
            self.assertEqual(area_servicio(p), AREA_HOSPITALIZACION)

    def test_emergencia(self):
        for p in ('Emergencia Particular', 'Emergencia Asegurado'):
            self.assertEqual(area_servicio(p), AREA_EMERGENCIA)

    def test_cirugia(self):
        for p in ('Cirugia Particular', 'Cirugia Asegurado'):
            self.assertEqual(area_servicio(p), AREA_CIRUGIA)

    def test_ambulatorio_y_asegurado_de_calle(self):
        # 'Asegurado' a secas es el que llega por su pie, no viene de un area
        for p in ('Ambulatorio', 'Asegurado'):
            self.assertEqual(area_servicio(p), AREA_AMBULATORIO)
            self.assertFalse(es_area_clinica(p))

    def test_area_y_pago_son_independientes(self):
        # Misma area, distinto pagador
        self.assertEqual(area_servicio('Cirugia Particular'),
                         area_servicio('Cirugia Asegurado'))
        self.assertFalse(es_credito('Cirugia Particular'))
        self.assertTrue(es_credito('Cirugia Asegurado'))

    def test_procedencia_desconocida_no_entra_en_el_corte(self):
        # Algo sin clasificar no puede colarse en lo que se le cobra a la clinica
        self.assertEqual(area_servicio('Convenio Empresa X'), AREA_AMBULATORIO)
        self.assertFalse(es_area_clinica('Convenio Empresa X'))

    def test_toda_procedencia_del_combo_tiene_area(self):
        for p in PROCEDENCIAS:
            self.assertIn(area_servicio(p),
                          (AREA_HOSPITALIZACION, AREA_EMERGENCIA,
                           AREA_CIRUGIA, AREA_AMBULATORIO), p)

    def test_espacios_y_mayusculas_no_cambian_el_area(self):
        for v in ('  CIRUGIA ASEGURADO ', 'cirugia  asegurado'):
            self.assertEqual(area_servicio(v), AREA_CIRUGIA)


class TestCorte(unittest.TestCase):

    def setUp(self):
        self.cuentas = [
            cuenta('HOSP ASEG', 100.0, 'Hospitalizado Asegurado'),
            cuenta('HOSP PART', 50.0, 'Hospitalizado Particular'),
            cuenta('EMER ASEG', 200.0, 'Emergencia Asegurado'),
            cuenta('CIRU ASEG', 300.0, 'Cirugia Asegurado'),
            cuenta('CIRU PART', 25.0, 'Cirugia Particular'),
            cuenta('AMBULATORIO', 40.0, 'Ambulatorio'),
        ]
        self.corte = CorteAdeudado(DBFalsa(self.cuentas))
        self.datos = self.corte.obtener_datos()

    def test_cada_area_suma_lo_suyo(self):
        a = self.datos['areas']
        self.assertEqual(a[AREA_HOSPITALIZACION]['total'], 150.0)
        self.assertEqual(a[AREA_EMERGENCIA]['total'], 200.0)
        self.assertEqual(a[AREA_CIRUGIA]['total'], 325.0)

    def test_separa_asegurado_de_particular(self):
        hosp = self.datos['areas'][AREA_HOSPITALIZACION]
        self.assertEqual(hosp['total_asegurado'], 100.0)
        self.assertEqual(hosp['total_particular'], 50.0)

    def test_el_ambulatorio_no_entra_en_el_corte(self):
        self.assertEqual(self.datos['fuera_del_corte'], 40.0)
        nombres = []
        for area in AREAS_CLINICA:
            for g in ('asegurado', 'particular'):
                nombres += [c['NombrePaciente']
                            for c in self.datos['areas'][area][g]]
        self.assertNotIn('AMBULATORIO', nombres)

    def test_total_general_es_la_suma_de_las_areas(self):
        suma = sum(self.datos['areas'][a]['total'] for a in AREAS_CLINICA)
        self.assertAlmostEqual(self.datos['total_general'], suma, places=2)
        self.assertEqual(self.datos['total_general'], 675.0)

    def test_total_asegurado_mas_particular_es_el_general(self):
        self.assertAlmostEqual(
            self.datos['total_asegurado'] + self.datos['total_particular'],
            self.datos['total_general'], places=2)

    def test_cuenta_los_pacientes_del_corte(self):
        self.assertEqual(self.datos['n_pacientes'], 5)  # el ambulatorio no

    def test_cartera_vacia_no_rompe(self):
        datos = CorteAdeudado(DBFalsa([])).obtener_datos()
        self.assertEqual(datos['total_general'], 0.0)
        self.assertEqual(datos['n_pacientes'], 0)
        for area in AREAS_CLINICA:
            self.assertEqual(datos['areas'][area]['n_pacientes'], 0)

    def test_importe_ilegible_no_tumba_el_corte(self):
        malas = [cuenta('RARO', 'xx', 'Cirugia Asegurado')]
        datos = CorteAdeudado(DBFalsa(malas)).obtener_datos()
        self.assertEqual(datos['total_general'], 0.0)

    def test_sin_columna_de_procedencia_usa_las_observaciones(self):
        # Cuentas creadas antes de que existiera TipoProcedencia
        viejas = [{
            'CuentaCobrarID': 1, 'PacienteID': 1, 'NombrePaciente': 'ANTIGUO',
            'FechaEmision': datetime(2026, 8, 1), 'MontoOriginal': 90.0,
            'MontoCobrado': 0.0, 'SaldoPendiente': 90.0, 'Estado': 'Pendiente',
            'Observaciones': 'Asegurado - Emergencia Asegurado - Solicitud S-1',
        }]
        db = DBFalsa(viejas, columnas={
            'CuentasPorCobrar.TipoProcedencia': False,
            'CuentasPorCobrar.SolicitudID': False,
        })
        datos = CorteAdeudado(db).obtener_datos()
        self.assertEqual(datos['areas'][AREA_EMERGENCIA]['total'], 90.0)

    def test_no_pide_columnas_que_no_existen(self):
        db = DBFalsa([], columnas={
            'CuentasPorCobrar.TipoProcedencia': False,
            'CuentasPorCobrar.SolicitudID': False,
        })
        CorteAdeudado(db).obtener_datos()
        self.assertNotIn('TipoProcedencia', db.ultima_sql)
        self.assertNotIn('SolicitudID', db.ultima_sql)

    def test_por_defecto_solo_lo_que_se_debe(self):
        CorteAdeudado(DBFalsa([])).obtener_datos()
        db = DBFalsa([])
        CorteAdeudado(db).obtener_datos()
        self.assertIn('SaldoPendiente', db.ultima_sql)
        self.assertIn('0.001', db.ultima_sql)

    def test_el_periodo_acota_por_fecha_de_ingreso(self):
        db = DBFalsa([])
        CorteAdeudado(db).obtener_datos(desde=datetime(2026, 9, 1),
                                        hasta=datetime(2026, 9, 30))
        self.assertIn('FechaEmision >=', db.ultima_sql)
        self.assertIn('FechaEmision <=', db.ultima_sql)


class TestPDF(unittest.TestCase):

    def test_genera_el_archivo(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("ReportLab no disponible")

        import tempfile
        cuentas = [
            cuenta('HOSP ASEG', 100.0, 'Hospitalizado Asegurado'),
            cuenta('CIRU PART', 25.0, 'Cirugia Particular'),
        ]
        corte = CorteAdeudado(DBFalsa(cuentas))
        ruta = os.path.join(tempfile.gettempdir(), 'test_corte_angeslab.pdf')
        if os.path.exists(ruta):
            os.remove(ruta)

        salida = corte.generar_pdf(ruta, config_lab={'NombreLaboratorio': 'LAB PRUEBA'})
        self.assertEqual(salida, ruta)
        self.assertTrue(os.path.exists(ruta))
        with open(ruta, 'rb') as f:
            self.assertTrue(f.read(5).startswith(b'%PDF'))
        os.remove(ruta)

    def test_sin_deuda_tambien_genera_documento(self):
        # Un corte en cero es una respuesta valida: "no se debe nada"
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("ReportLab no disponible")

        import tempfile
        ruta = os.path.join(tempfile.gettempdir(), 'test_corte_vacio.pdf')
        if os.path.exists(ruta):
            os.remove(ruta)
        salida = CorteAdeudado(DBFalsa([])).generar_pdf(ruta)
        self.assertEqual(salida, ruta)
        self.assertTrue(os.path.exists(ruta))
        os.remove(ruta)


class TestRolDeImpresion(unittest.TestCase):
    """El corte debe poder asignarse una impresora en Configuracion."""

    def test_el_rol_existe_y_esta_en_el_panel(self):
        from modulos.impresoras import ORDEN_ROLES, ROLES
        self.assertIn('cortes', ROLES)
        self.assertIn('cortes', ORDEN_ROLES)

    def test_tiene_su_propia_columna(self):
        from modulos.impresoras import ROLES
        self.assertEqual(ROLES['cortes']['columna'], 'ImpresoraCortes')
        self.assertEqual(ROLES['cortes']['columna_directo'],
                         'ImpresoraCortesDirecto')

    def test_sale_en_hoja_y_directo(self):
        from modulos.impresoras import ROLES
        self.assertEqual(ROLES['cortes']['papel'], 'hoja')
        self.assertTrue(ROLES['cortes']['directo_defecto'])

    def test_tiene_respaldo_mientras_no_se_le_asigne_impresora(self):
        from modulos.impresoras import ROLES_RESPALDO
        self.assertIn('cortes', ROLES_RESPALDO)

    def test_los_alias_apuntan_al_rol(self):
        from modulos.impresoras import ALIAS_ROLES
        for alias in ('corte', 'corte_adeudado', 'adeudado'):
            self.assertEqual(ALIAS_ROLES.get(alias), 'cortes')


if __name__ == '__main__':
    unittest.main(verbosity=2)

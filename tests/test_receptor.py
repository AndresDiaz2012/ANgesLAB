# -*- coding: utf-8 -*-
"""
Pruebas del ANgesLAB Receptor, el programa que imprime en la sede remota.

Lo que se protege: que ningun informe se pierda. La sede B no tiene base de
datos ni historial; si un PDF desaparece sin imprimirse, nadie puede saber
que existio. Por eso nada se borra, lo impreso se archiva y lo fallido queda
apartado con su motivo.

El ultimo centimetro -mandar los bytes a la impresora- es
modulos.impresoras.enviar_documento, que el programa principal usa a diario.
Aqui se sustituye por uno falso para poder probar todo lo demas sin papel.
"""

import importlib.util
import os
import queue
import shutil
import sys
import tempfile
import time
import types
import unittest

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _RAIZ)

RECEPTOR = os.path.join(_RAIZ, 'receptor', 'ANgesLAB_Receptor.pyw')


def _cargar_receptor(enviar):
    """El modulo del receptor con el motor de impresion sustituido."""
    falso = types.ModuleType('modulos.impresoras')
    falso.enviar_documento = enviar
    falso.listar_impresoras = lambda: (['Impresora de prueba'],
                                       'Impresora de prueba')
    sys.modules['modulos.impresoras'] = falso

    spec = importlib.util.spec_from_file_location('receptor_test', RECEPTOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # Sin esperas largas: la prueba no tiene por que durar medio minuto
    mod.INTERVALO = 0.3
    mod.ESPERA_ESTABLE = 0.2
    return mod


class BaseReceptor(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.mkdtemp(prefix='sede_')
        self.impresos = []
        self.addCleanup(shutil.rmtree, self.carpeta, True)
        self.addCleanup(sys.modules.pop, 'modulos.impresoras', None)

    def _enviar(self, ruta, impresora, copias=1, opciones=None, titulo=None):
        if 'FALLA' in os.path.basename(ruta).upper():
            return {'ok': False, 'error': 'sin papel'}
        self.impresos.append((os.path.basename(ruta), impresora, copias))
        return {'ok': True}

    def _pdf(self, nombre, contenido=b'%PDF-1.4 de prueba'):
        ruta = os.path.join(self.carpeta, nombre)
        with open(ruta, 'wb') as f:
            f.write(contenido)
        return ruta

    def _correr(self, esperados, copias=1, segundos=10):
        mod = _cargar_receptor(self._enviar)
        avisos = queue.Queue()
        r = mod.Receptor(avisos)
        r.arrancar(self.carpeta, 'Impresora de prueba', copias)
        t0 = time.time()
        while time.time() - t0 < segundos and (r.impresos + r.fallidos) < esperados:
            time.sleep(0.2)
        r.detener()
        time.sleep(0.8)
        return r, mod


class TestNoSePierdeNingunInforme(BaseReceptor):

    def test_imprime_lo_que_llega(self):
        self._pdf('2026-000123_PEREZ.pdf')
        r, _ = self._correr(1)
        self.assertEqual(r.impresos, 1)
        self.assertEqual(self.impresos[0][0], '2026-000123_PEREZ.pdf')

    def test_lo_impreso_se_archiva_por_mes(self):
        self._pdf('2026-000123_PEREZ.pdf')
        self._correr(1)
        mes = time.strftime('%Y-%m')
        destino = os.path.join(self.carpeta, 'impresos', mes)
        self.assertTrue(os.path.isdir(destino))
        self.assertEqual(os.listdir(destino), ['2026-000123_PEREZ.pdf'])

    def test_nada_se_borra(self):
        # La sede B no tiene historial: el PDF archivado es la unica prueba
        # de que el informe llego e se imprimio.
        self._pdf('A.pdf')
        self._pdf('B_FALLA.pdf')
        self._correr(2)
        quedan = sum(len(f) for _, _, f in os.walk(self.carpeta))
        self.assertEqual(quedan, 2)

    def test_lo_que_no_se_imprimio_queda_apartado(self):
        self._pdf('2026-9_FALLA.pdf')
        r, _ = self._correr(1)
        self.assertEqual(r.fallidos, 1)
        err = os.path.join(self.carpeta, 'errores')
        self.assertEqual(os.listdir(err), ['2026-9_FALLA.pdf'])

    def test_no_queda_ningun_pdf_sin_atender(self):
        for n in ('A.pdf', 'B.pdf', 'C_FALLA.pdf'):
            self._pdf(n)
        self._correr(3)
        sueltos = [f for f in os.listdir(self.carpeta)
                   if f.lower().endswith('.pdf')]
        self.assertEqual(sueltos, [])


class TestNoImprimeBasura(BaseReceptor):

    def test_no_toca_el_temporal_a_medio_escribir(self):
        # El emisor escribe .tmp y renombra al terminar. Imprimir el .tmp
        # sacaria una hoja cortada.
        self._pdf('a_medias.tmp')
        self._pdf('bueno.pdf')
        r, _ = self._correr(1)
        self.assertEqual(r.impresos, 1)
        self.assertIn('a_medias.tmp', os.listdir(self.carpeta))

    def test_un_archivo_que_sigue_creciendo_no_se_imprime(self):
        mod = _cargar_receptor(self._enviar)
        ruta = self._pdf('creciendo.pdf')

        import threading
        parar = threading.Event()

        def engordar():
            while not parar.is_set():
                with open(ruta, 'ab') as f:
                    f.write(b'x' * 4096)
                time.sleep(0.05)

        h = threading.Thread(target=engordar, daemon=True)
        h.start()
        try:
            self.assertFalse(mod.esta_completo(ruta),
                             "un archivo que crece no puede darse por completo")
        finally:
            parar.set()
            h.join(timeout=2)

    def test_un_archivo_quieto_si_se_considera_completo(self):
        mod = _cargar_receptor(self._enviar)
        ruta = self._pdf('quieto.pdf')
        self.assertTrue(mod.esta_completo(ruta))

    def test_un_archivo_vacio_no_se_imprime(self):
        mod = _cargar_receptor(self._enviar)
        ruta = self._pdf('vacio.pdf', b'')
        self.assertFalse(mod.esta_completo(ruta))


class TestDetallesQueImportan(BaseReceptor):

    def test_respeta_las_copias_configuradas(self):
        self._pdf('A.pdf')
        self._correr(1, copias=3)
        self.assertEqual(self.impresos[0][2], 3)

    def test_dos_informes_iguales_no_se_machacan(self):
        # Una correccion o una reimpresion llegan con el mismo nombre;
        # pisarla borraria la prueba de que la primera se imprimio.
        mod = _cargar_receptor(self._enviar)
        destino = mod.carpeta_destino(self.carpeta, 'impresos')
        a = self._pdf('REPETIDO.pdf')
        mod.mover(a, destino)
        b = self._pdf('REPETIDO.pdf')
        mod.mover(b, destino)
        self.assertEqual(len(os.listdir(destino)), 2)

    def test_sin_carpeta_no_se_muere(self):
        # Drive puede no haber montado la unidad todavia
        mod = _cargar_receptor(self._enviar)
        avisos = queue.Queue()
        r = mod.Receptor(avisos)
        r.arrancar(os.path.join(self.carpeta, 'no_existe'),
                   'Impresora de prueba', 1)
        time.sleep(0.8)
        self.assertTrue(r.activo(), "tiene que seguir esperando, no morirse")
        r.detener()
        time.sleep(0.6)

    def test_la_configuracion_va_y_vuelve(self):
        mod = _cargar_receptor(self._enviar)
        datos = {'carpeta': self.carpeta, 'impresora': 'X', 'copias': 2,
                 'arranque': True}
        original = mod.CONFIG
        mod.CONFIG = os.path.join(self.carpeta, 'cfg.json')
        try:
            self.assertTrue(mod.guardar_config(datos))
            self.assertEqual(mod.cargar_config(), datos)
        finally:
            mod.CONFIG = original

    def test_sin_configuracion_arranca_con_valores_sanos(self):
        mod = _cargar_receptor(self._enviar)
        original = mod.CONFIG
        mod.CONFIG = os.path.join(self.carpeta, 'no_hay.json')
        try:
            d = mod.cargar_config()
            self.assertEqual(d['carpeta'], '')
            self.assertEqual(d['copias'], 1)
        finally:
            mod.CONFIG = original


if __name__ == '__main__':
    unittest.main()

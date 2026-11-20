# -*- coding: utf-8 -*-
"""
Pruebas de la direccion que lleva el codigo QR del recibo.

El QR dice "CONSULTE SUS RESULTADOS" y codifica la URL del portal, que el
telefono del paciente abre al escanearlo. La direccion se averiguaba abriendo
un socket hacia 8.8.8.8 y leyendo que IP habia elegido el sistema, que es la
de la ruta por defecto: con una VPN encendida (en la clinica, Proton VPN) esa
ruta sale por el tunel y la IP era la del tunel, 10.2.0.2. El QR salia con una
direccion que ningun telefono de la sala de espera puede alcanzar, de modo que
al escanearlo no pasaba nada.

Lo que se protege: que la direccion del QR sea la de la red local, no la de un
tunel ni la de una tarjeta sin DHCP.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modulos import portal_resultados as pr


class RedFalsa:
    """Sustituye lo que el modulo le pregunta al sistema sobre la red."""

    def __init__(self, ips, ruta):
        self.ips, self.ruta = ips, ruta
        self._ips_reales = pr._ips_del_equipo
        self._ruta_real = pr._ip_de_la_ruta

    def __enter__(self):
        pr._ips_del_equipo = lambda: list(self.ips)
        pr._ip_de_la_ruta = lambda: self.ruta
        return self

    def __exit__(self, *exc):
        pr._ips_del_equipo = self._ips_reales
        pr._ip_de_la_ruta = self._ruta_real


class TestPrioridadDeLaIP(unittest.TestCase):

    def test_la_lan_de_siempre_es_la_mejor(self):
        self.assertEqual(pr._prioridad_ip('192.168.1.50'), 4)

    def test_una_red_mediana_sirve(self):
        self.assertEqual(pr._prioridad_ip('172.20.5.4'), 3)
        self.assertEqual(pr._prioridad_ip('172.15.5.4'), 1)   # fuera del rango privado

    def test_la_decena_sirve_pero_menos(self):
        self.assertEqual(pr._prioridad_ip('10.2.0.2'), 2)

    def test_el_localhost_no_sirve(self):
        self.assertEqual(pr._prioridad_ip('127.0.0.1'), 0)

    def test_una_tarjeta_sin_dhcp_no_sirve(self):
        self.assertEqual(pr._prioridad_ip('169.254.15.166'), 0)

    def test_lo_que_no_es_una_ip_no_sirve(self):
        for basura in (None, '', 'localhost', '192.168.1', '1.2.3.4.5', 'a.b.c.d'):
            self.assertEqual(pr._prioridad_ip(basura), 0, basura)


class TestIPQueVaEnElQR(unittest.TestCase):

    def test_la_vpn_no_le_gana_a_la_lan(self):
        # El caso de la clinica: Proton VPN con la ruta por defecto
        with RedFalsa(['10.2.0.2', '192.168.123.8'], '10.2.0.2'):
            self.assertEqual(pr.ip_lan(), '192.168.123.8')

    def test_sin_vpn_sale_la_de_la_ruta(self):
        with RedFalsa(['192.168.123.8'], '192.168.123.8'):
            self.assertEqual(pr.ip_lan(), '192.168.123.8')

    def test_entre_dos_de_la_lan_manda_la_de_la_ruta(self):
        with RedFalsa(['192.168.50.7', '192.168.123.8'], '192.168.123.8'):
            self.assertEqual(pr.ip_lan(), '192.168.123.8')

    def test_los_cables_sueltos_no_cuentan(self):
        with RedFalsa(['169.254.15.166', '169.254.12.66', '192.168.123.8'], None):
            self.assertEqual(pr.ip_lan(), '192.168.123.8')

    def test_una_red_de_decena_sirve_si_es_la_unica(self):
        with RedFalsa(['10.0.0.25'], '10.0.0.25'):
            self.assertEqual(pr.ip_lan(), '10.0.0.25')

    def test_sin_nada_util_queda_la_ruta(self):
        with RedFalsa(['127.0.0.1', '169.254.1.1'], '10.2.0.2'):
            self.assertEqual(pr.ip_lan(), '10.2.0.2')

    def test_sin_red_alguna_no_se_cae(self):
        with RedFalsa([], None):
            self.assertEqual(pr.ip_lan(), '127.0.0.1')

    def test_la_url_del_portal_lleva_esa_ip(self):
        g = pr.GestorPortalResultados(None)
        g.cfg = {'activo': True, 'puerto': 8770, 'url_publica': ''}
        with RedFalsa(['10.2.0.2', '192.168.123.8'], '10.2.0.2'):
            self.assertEqual(g.base_url(), 'http://192.168.123.8:8770')

    def test_la_url_publica_manda_sobre_todo(self):
        g = pr.GestorPortalResultados(None)
        g.cfg = {'activo': True, 'puerto': 8770,
                 'url_publica': 'resultados.milab.com'}
        with RedFalsa(['10.2.0.2', '192.168.123.8'], '10.2.0.2'):
            self.assertEqual(g.base_url(), 'http://resultados.milab.com')


if __name__ == '__main__':
    unittest.main()

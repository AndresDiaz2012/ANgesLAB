# -*- coding: utf-8 -*-
"""
================================================================================
TESTS DE SEGURIDAD - ANgesLAB
================================================================================
Suite de pruebas para validar los mecanismos de seguridad del sistema.
Cubre: hashing, sanitizacion SQL, control de intentos, proteccion de credenciales.

Ejecutar: python -m pytest tests/test_seguridad.py -v
================================================================================
"""

import sys
import os
import unittest
import hashlib
import secrets

# Agregar ruta del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from modulos.seguridad_db import (
    SeguridadContrasenas, DatabaseSegura, Validadores,
    ControlIntentos, ProtectorCredenciales
)


class TestSeguridadContrasenas(unittest.TestCase):
    """Tests para hashing de contrasenas PBKDF2."""

    def test_hash_genera_pbkdf2(self):
        """El hash debe usar prefijo pbkdf2:"""
        h, s = SeguridadContrasenas.hash_password('TestPass123')
        self.assertTrue(h.startswith('pbkdf2:'))
        self.assertTrue(len(s) == 64)  # token_hex(32)

    def test_verificacion_correcta(self):
        """Contrasena correcta debe verificar True."""
        h, s = SeguridadContrasenas.hash_password('MiClave$egura1')
        self.assertTrue(SeguridadContrasenas.verificar_password('MiClave$egura1', h, s))

    def test_verificacion_incorrecta(self):
        """Contrasena incorrecta debe verificar False."""
        h, s = SeguridadContrasenas.hash_password('ClaveCorrecta1')
        self.assertFalse(SeguridadContrasenas.verificar_password('ClaveIncorrecta', h, s))

    def test_retrocompat_sha256_legacy(self):
        """Debe verificar hashes SHA-256 legacy (sin prefijo pbkdf2:)."""
        password = 'LegacyPass123'
        salt = secrets.token_hex(32)
        # Generar hash legacy SHA-256
        combined = f"{salt}{password}".encode('utf-8')
        legacy_hash = hashlib.sha256(combined).hexdigest()
        # Debe verificar contra hash legacy
        self.assertTrue(SeguridadContrasenas.verificar_password(password, legacy_hash, salt))

    def test_necesita_rehash_legacy(self):
        """Hash legacy debe marcarse como necesitando rehash."""
        legacy_hash = hashlib.sha256(b'test').hexdigest()
        self.assertTrue(SeguridadContrasenas.necesita_rehash(legacy_hash))

    def test_no_necesita_rehash_pbkdf2(self):
        """Hash PBKDF2 no debe necesitar rehash."""
        h, s = SeguridadContrasenas.hash_password('Test123')
        self.assertFalse(SeguridadContrasenas.necesita_rehash(h))

    def test_hashes_diferentes_con_misma_password(self):
        """Dos hashes de la misma password deben ser diferentes (salt distinto)."""
        h1, s1 = SeguridadContrasenas.hash_password('MismaPass1')
        h2, s2 = SeguridadContrasenas.hash_password('MismaPass1')
        self.assertNotEqual(s1, s2)  # Salts diferentes
        self.assertNotEqual(h1, h2)  # Hashes diferentes

    def test_validar_fortaleza_debil(self):
        """Contrasena debil debe rechazarse."""
        valida, _ = SeguridadContrasenas.validar_fortaleza_password('corta')
        self.assertFalse(valida)

    def test_validar_fortaleza_fuerte(self):
        """Contrasena fuerte debe aceptarse."""
        valida, msg = SeguridadContrasenas.validar_fortaleza_password('MiClave$123')
        self.assertTrue(valida)

    def test_password_temporal_segura(self):
        """Password temporal debe tener longitud suficiente."""
        pwd = SeguridadContrasenas.generar_password_temporal()
        self.assertGreaterEqual(len(pwd), 12)


class TestSanitizacionSQL(unittest.TestCase):
    """Tests para prevencion de SQL Injection."""

    def setUp(self):
        self.db_seg = DatabaseSegura(None)

    def test_sanitizar_string_normal(self):
        """String normal debe quedar entre comillas."""
        result = self.db_seg.sanitizar_valor('Juan Perez')
        self.assertEqual(result, "'Juan Perez'")

    def test_sanitizar_comillas_simples(self):
        """Comillas simples deben escaparse."""
        result = self.db_seg.sanitizar_valor("O'Brien")
        self.assertEqual(result, "'O''Brien'")

    def test_sanitizar_numeros(self):
        """Numeros deben ser string sin comillas."""
        self.assertEqual(self.db_seg.sanitizar_valor(42), '42')
        self.assertEqual(self.db_seg.sanitizar_valor(3.14), '3.14')

    def test_sanitizar_none(self):
        """None debe convertirse a NULL."""
        self.assertEqual(self.db_seg.sanitizar_valor(None), 'NULL')

    def test_sanitizar_booleano(self):
        """Booleanos deben convertirse a True/False."""
        self.assertEqual(self.db_seg.sanitizar_valor(True), 'True')
        self.assertEqual(self.db_seg.sanitizar_valor(False), 'False')

    def test_detectar_drop_table(self):
        """Debe detectar intento de DROP TABLE."""
        with self.assertRaises(ValueError):
            self.db_seg.sanitizar_valor("'; DROP TABLE Usuarios; --")

    def test_detectar_union_select(self):
        """Debe detectar UNION SELECT injection."""
        with self.assertRaises(ValueError):
            self.db_seg.sanitizar_valor("' UNION SELECT * FROM Usuarios --")

    def test_detectar_or_siempre_verdadero(self):
        """Debe detectar OR 1=1."""
        with self.assertRaises(ValueError):
            self.db_seg.sanitizar_valor("' OR 1=1 --")

    def test_identificador_valido(self):
        """Identificador valido debe quedar entre brackets."""
        self.assertEqual(self.db_seg.sanitizar_identificador('NombrePaciente'), '[NombrePaciente]')

    def test_identificador_con_caracteres_invalidos(self):
        """Identificador con caracteres invalidos debe rechazarse."""
        with self.assertRaises(ValueError):
            self.db_seg.sanitizar_identificador('tabla; DROP')

    def test_identificador_palabra_reservada(self):
        """Palabras reservadas SQL deben rechazarse como identificador."""
        with self.assertRaises(ValueError):
            self.db_seg.sanitizar_identificador('DROP')


class TestControlIntentos(unittest.TestCase):
    """Tests para control de intentos de login."""

    def test_primer_intento_no_bloqueado(self):
        """El primer intento nunca debe estar bloqueado."""
        ci = ControlIntentos()
        bloqueado, _ = ci.esta_bloqueado('usuario_nuevo')
        self.assertFalse(bloqueado)

    def test_intentos_restantes_iniciales(self):
        """Debe tener MAX_INTENTOS restantes al inicio."""
        ci = ControlIntentos()
        self.assertEqual(ci.intentos_restantes('usuario_nuevo'), ControlIntentos.MAX_INTENTOS)

    def test_bloqueo_tras_max_intentos(self):
        """Debe bloquearse tras MAX_INTENTOS fallidos."""
        ci = ControlIntentos()
        for _ in range(ControlIntentos.MAX_INTENTOS):
            ci.registrar_intento('test_user', False)
        bloqueado, mins = ci.esta_bloqueado('test_user')
        self.assertTrue(bloqueado)
        self.assertGreater(mins, 0)

    def test_login_exitoso_limpia_historial(self):
        """Login exitoso debe limpiar el historial de intentos."""
        ci = ControlIntentos()
        for _ in range(3):
            ci.registrar_intento('test_user', False)
        ci.registrar_intento('test_user', True)  # Exito
        self.assertEqual(ci.intentos_restantes('test_user'), ControlIntentos.MAX_INTENTOS)

    def test_intentos_decrementan(self):
        """Los intentos restantes deben decrementar con cada fallo."""
        ci = ControlIntentos()
        ci.registrar_intento('test_user', False)
        self.assertEqual(ci.intentos_restantes('test_user'), ControlIntentos.MAX_INTENTOS - 1)
        ci.registrar_intento('test_user', False)
        self.assertEqual(ci.intentos_restantes('test_user'), ControlIntentos.MAX_INTENTOS - 2)


class TestProtectorCredenciales(unittest.TestCase):
    """Tests para proteccion de credenciales."""

    def test_cifrar_descifrar_roundtrip(self):
        """Cifrar y descifrar debe retornar el valor original."""
        pc = ProtectorCredenciales()
        original = 'sk-ant-api-key-test-12345'
        cifrado = pc.cifrar(original)
        descifrado = pc.descifrar(cifrado)
        self.assertEqual(original, descifrado)

    def test_cifrado_no_es_texto_plano(self):
        """El texto cifrado no debe ser igual al original."""
        pc = ProtectorCredenciales()
        original = 'mi-clave-secreta'
        cifrado = pc.cifrar(original)
        self.assertNotEqual(original, cifrado)

    def test_cifrar_texto_vacio(self):
        """Texto vacio debe retornar vacio."""
        pc = ProtectorCredenciales()
        self.assertEqual(pc.cifrar(''), '')
        self.assertEqual(pc.descifrar(''), '')

    def test_descifrar_texto_plano_legacy(self):
        """Texto sin prefijo (legacy) debe retornarse tal cual."""
        pc = ProtectorCredenciales()
        self.assertEqual(pc.descifrar('sk-ant-api-old-key'), 'sk-ant-api-old-key')

    def test_cifrado_tiene_prefijo(self):
        """El texto cifrado debe tener prefijo dpapi: o b64:"""
        pc = ProtectorCredenciales()
        cifrado = pc.cifrar('test-key')
        self.assertTrue(
            cifrado.startswith('dpapi:') or cifrado.startswith('b64:'),
            f"Cifrado no tiene prefijo valido: {cifrado[:20]}"
        )


class TestValidadores(unittest.TestCase):
    """Tests para validadores de datos."""

    def test_email_valido(self):
        self.assertTrue(Validadores.es_email_valido('test@dominio.com'))
        self.assertTrue(Validadores.es_email_valido('usuario.nombre@lab.co'))

    def test_email_invalido(self):
        self.assertFalse(Validadores.es_email_valido(''))
        self.assertFalse(Validadores.es_email_valido('test@'))
        self.assertFalse(Validadores.es_email_valido('sin-arroba'))

    def test_cedula_valida(self):
        self.assertTrue(Validadores.es_cedula_valida('V-12345678'))
        self.assertTrue(Validadores.es_cedula_valida('E-1234567'))

    def test_cedula_invalida(self):
        self.assertFalse(Validadores.es_cedula_valida('123'))
        self.assertFalse(Validadores.es_cedula_valida('X-1234'))

    def test_rif_valido(self):
        self.assertTrue(Validadores.es_rif_valido('J-12345678-9'))
        self.assertTrue(Validadores.es_rif_valido('V-12345678-0'))

    def test_sanitizar_nombre(self):
        """Nombres deben limpiarse de caracteres invalidos."""
        self.assertEqual(Validadores.sanitizar_nombre('Juan Pérez'), 'Juan Pérez')
        self.assertEqual(Validadores.sanitizar_nombre('Test<script>'), 'Testscript')


if __name__ == '__main__':
    unittest.main(verbosity=2)

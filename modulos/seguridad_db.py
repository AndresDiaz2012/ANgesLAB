"""
================================================================================
MODULO DE SEGURIDAD DE BASE DE DATOS - ANgesLAB
================================================================================
Proporciona funciones seguras para interactuar con la base de datos:
- Prevencion de SQL Injection
- Validacion de entradas
- Sanitizacion de datos
- Consultas parametrizadas seguras
- Hashing seguro con PBKDF2 (NIST SP 800-63B)
- Control de intentos de login

Autor: Sistema ANgesLAB
================================================================================
"""

import re
import os
from datetime import datetime, date
from decimal import Decimal
import hashlib
import secrets

# Logging estructurado
try:
    from modulos.logging_config import log_evento, log_auditoria
except ImportError:
    def log_evento(msg, **kw): pass
    def log_auditoria(uid, acc, det, **kw): pass

# ============================================================================
# CLASE PRINCIPAL DE SEGURIDAD
# ============================================================================

class DatabaseSegura:
    """
    Wrapper seguro para la base de datos que previene SQL Injection
    """

    def __init__(self, db_original):
        """
        Inicializa con la instancia de base de datos original

        Parametros:
        - db_original: instancia de la clase Database existente
        """
        self._db = db_original

    # -------------------------------------------------------------------------
    # SANITIZACION DE VALORES
    # -------------------------------------------------------------------------

    @staticmethod
    def sanitizar_valor(valor):
        """
        Sanitiza un valor para uso seguro en SQL

        - Escapa comillas simples
        - Valida tipos de datos
        - Previene inyeccion de caracteres especiales
        """
        if valor is None:
            return "NULL"

        if isinstance(valor, bool):
            return "True" if valor else "False"

        if isinstance(valor, (int, float, Decimal)):
            # Validar que sea un numero real
            try:
                float(valor)
                return str(valor)
            except (ValueError, TypeError):
                raise ValueError(f"Valor numerico invalido: {valor}")

        if isinstance(valor, (datetime, date)):
            return f"#{valor.strftime('%m/%d/%Y %H:%M:%S' if isinstance(valor, datetime) else '%m/%d/%Y')}#"

        # Para strings, sanitizar
        valor_str = str(valor)

        # Remover caracteres potencialmente peligrosos
        # pero mantener los que son validos para datos normales
        valor_str = valor_str.replace("'", "''")  # Escapar comillas simples

        # Detectar patrones de SQL Injection
        patrones_peligrosos = [
            r';\s*--',           # Comentarios SQL
            r';\s*DROP',         # DROP statements
            r';\s*DELETE',       # DELETE sin WHERE
            r';\s*UPDATE',       # UPDATE sin WHERE
            r';\s*INSERT',       # INSERT adicional
            r'UNION\s+SELECT',   # UNION injection
            r'OR\s+1\s*=\s*1',   # Siempre verdadero
            r"OR\s+'.*'\s*=\s*'.*'",  # Siempre verdadero con strings
            r'EXEC\s*\(',        # Ejecucion de procedimientos
            r'xp_',              # Procedimientos extendidos SQL Server
        ]

        for patron in patrones_peligrosos:
            if re.search(patron, valor_str, re.IGNORECASE):
                log_evento(
                    f"SQL Injection detectado: {valor_str[:80]}",
                    nivel='warning', modulo='seguridad', accion='SQL_INJECTION_BLOCKED'
                )
                raise ValueError(f"Patron potencialmente peligroso detectado: {valor_str[:50]}...")

        return f"'{valor_str}'"

    @staticmethod
    def sanitizar_identificador(identificador):
        """
        Sanitiza un nombre de tabla o columna

        Solo permite caracteres alfanumericos y guion bajo
        """
        if not identificador:
            raise ValueError("Identificador vacio")

        # Solo permitir caracteres seguros
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', identificador):
            raise ValueError(f"Identificador invalido: {identificador}")

        # Lista de palabras reservadas que no deberian usarse como identificadores
        palabras_reservadas = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'SELECT', 'EXEC',
                               'EXECUTE', 'TRUNCATE', 'ALTER', 'CREATE', 'GRANT']

        if identificador.upper() in palabras_reservadas:
            raise ValueError(f"Identificador es palabra reservada: {identificador}")

        return f"[{identificador}]"

    # -------------------------------------------------------------------------
    # CONSULTAS SEGURAS
    # -------------------------------------------------------------------------

    def query_segura(self, tabla, campos="*", where=None, order_by=None, limit=None):
        """
        Ejecuta una consulta SELECT de forma segura

        Parametros:
        - tabla: nombre de la tabla
        - campos: lista de campos o "*"
        - where: dict de condiciones {campo: valor}
        - order_by: campo para ordenar
        - limit: numero maximo de registros
        """
        # Sanitizar tabla
        tabla_safe = self.sanitizar_identificador(tabla)

        # Construir campos
        if campos == "*":
            campos_sql = "*"
        elif isinstance(campos, (list, tuple)):
            campos_sql = ", ".join(self.sanitizar_identificador(c) for c in campos)
        else:
            campos_sql = self.sanitizar_identificador(campos)

        # Construir SQL base
        sql = f"SELECT {campos_sql} FROM {tabla_safe}"

        # Agregar WHERE
        if where:
            condiciones = []
            for campo, valor in where.items():
                campo_safe = self.sanitizar_identificador(campo)
                valor_safe = self.sanitizar_valor(valor)
                condiciones.append(f"{campo_safe} = {valor_safe}")
            sql += " WHERE " + " AND ".join(condiciones)

        # Agregar ORDER BY
        if order_by:
            order_safe = self.sanitizar_identificador(order_by)
            sql += f" ORDER BY {order_safe}"

        # Agregar LIMIT (TOP en Access)
        if limit:
            limit_val = int(limit)
            sql = sql.replace("SELECT", f"SELECT TOP {limit_val}", 1)

        return self._db.query(sql)

    def insert_seguro(self, tabla, datos):
        """
        Inserta un registro de forma segura

        Parametros:
        - tabla: nombre de la tabla
        - datos: dict de {campo: valor}
        """
        tabla_safe = self.sanitizar_identificador(tabla)

        campos = []
        valores = []

        for campo, valor in datos.items():
            campos.append(self.sanitizar_identificador(campo))
            valores.append(self.sanitizar_valor(valor))

        sql = f"INSERT INTO {tabla_safe} ({', '.join(campos)}) VALUES ({', '.join(valores)})"
        return self._db.execute(sql)

    def update_seguro(self, tabla, datos, where):
        """
        Actualiza registros de forma segura

        Parametros:
        - tabla: nombre de la tabla
        - datos: dict de {campo: valor} a actualizar
        - where: dict de condiciones {campo: valor}
        """
        if not where:
            raise ValueError("UPDATE sin WHERE no permitido por seguridad")

        tabla_safe = self.sanitizar_identificador(tabla)

        # Construir SET
        sets = []
        for campo, valor in datos.items():
            campo_safe = self.sanitizar_identificador(campo)
            valor_safe = self.sanitizar_valor(valor)
            sets.append(f"{campo_safe} = {valor_safe}")

        # Construir WHERE
        condiciones = []
        for campo, valor in where.items():
            campo_safe = self.sanitizar_identificador(campo)
            valor_safe = self.sanitizar_valor(valor)
            condiciones.append(f"{campo_safe} = {valor_safe}")

        sql = f"UPDATE {tabla_safe} SET {', '.join(sets)} WHERE {' AND '.join(condiciones)}"
        return self._db.execute(sql)

    def delete_seguro(self, tabla, where):
        """
        Elimina registros de forma segura

        Parametros:
        - tabla: nombre de la tabla
        - where: dict de condiciones {campo: valor}
        """
        if not where:
            raise ValueError("DELETE sin WHERE no permitido por seguridad")

        tabla_safe = self.sanitizar_identificador(tabla)

        # Construir WHERE
        condiciones = []
        for campo, valor in where.items():
            campo_safe = self.sanitizar_identificador(campo)
            valor_safe = self.sanitizar_valor(valor)
            condiciones.append(f"{campo_safe} = {valor_safe}")

        sql = f"DELETE FROM {tabla_safe} WHERE {' AND '.join(condiciones)}"
        return self._db.execute(sql)

    def buscar_seguro(self, tabla, campo_busqueda, termino, campos="*"):
        """
        Realiza una busqueda LIKE de forma segura

        Parametros:
        - tabla: nombre de la tabla
        - campo_busqueda: campo donde buscar
        - termino: termino a buscar
        - campos: campos a retornar
        """
        tabla_safe = self.sanitizar_identificador(tabla)
        campo_safe = self.sanitizar_identificador(campo_busqueda)

        # Sanitizar termino de busqueda
        termino_limpio = str(termino).replace("'", "''").replace("%", "").replace("_", "")

        if campos == "*":
            campos_sql = "*"
        elif isinstance(campos, (list, tuple)):
            campos_sql = ", ".join(self.sanitizar_identificador(c) for c in campos)
        else:
            campos_sql = self.sanitizar_identificador(campos)

        sql = f"SELECT {campos_sql} FROM {tabla_safe} WHERE {campo_safe} LIKE '%{termino_limpio}%'"
        return self._db.query(sql)


# ============================================================================
# VALIDADORES DE DATOS
# ============================================================================

class Validadores:
    """Funciones de validacion de datos de entrada"""

    @staticmethod
    def es_email_valido(email):
        """Valida formato de email"""
        patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(patron, email))

    @staticmethod
    def es_telefono_valido(telefono):
        """Valida formato de telefono venezolano"""
        # Acepta formatos: 0412-1234567, 04121234567, +58412-1234567
        patron = r'^(\+58)?0?(412|414|416|424|426|212|261|241|251|281|285|291|292|293|295)\d{7}$'
        telefono_limpio = re.sub(r'[\s\-\(\)]', '', telefono)
        return bool(re.match(patron, telefono_limpio))

    @staticmethod
    def es_cedula_valida(cedula):
        """Valida formato de cedula venezolana"""
        patron = r'^[VvEe]-?\d{6,8}$'
        cedula_limpia = cedula.replace('.', '').replace(' ', '')
        return bool(re.match(patron, cedula_limpia))

    @staticmethod
    def es_rif_valido(rif):
        """Valida formato de RIF venezolano"""
        patron = r'^[VvJjGgEePp]-?\d{8}-?\d$'
        rif_limpio = rif.replace('.', '').replace(' ', '')
        return bool(re.match(patron, rif_limpio))

    @staticmethod
    def sanitizar_nombre(nombre):
        """Sanitiza un nombre (solo letras, espacios y tildes)"""
        # Remover caracteres no permitidos
        permitidos = re.compile(r'[^a-zA-ZáéíóúÁÉÍÓÚñÑüÜ\s\-\.]')
        return permitidos.sub('', nombre).strip()

    @staticmethod
    def sanitizar_numero_documento(documento):
        """Sanitiza un numero de documento"""
        # Solo permitir letras, numeros y guiones
        permitidos = re.compile(r'[^a-zA-Z0-9\-]')
        return permitidos.sub('', documento).upper()

    @staticmethod
    def validar_fecha(fecha_str, formato='%d/%m/%Y'):
        """Valida y convierte una fecha"""
        try:
            return datetime.strptime(fecha_str, formato)
        except ValueError:
            return None

    @staticmethod
    def validar_monto(monto_str):
        """Valida y convierte un monto numerico"""
        try:
            # Remover simbolos de moneda y separadores
            limpio = re.sub(r'[^\d.,\-]', '', str(monto_str))
            # Normalizar separador decimal
            limpio = limpio.replace(',', '.')
            return Decimal(limpio)
        except Exception:
            return None


# ============================================================================
# SEGURIDAD DE CONTRASENAS (PBKDF2 - NIST SP 800-63B)
# ============================================================================

# Prefijo para distinguir hash PBKDF2 del legacy SHA-256
_PBKDF2_PREFIX = 'pbkdf2:'
_PBKDF2_ITERATIONS = 600_000  # OWASP 2024: >=600k para SHA-256


class SeguridadContrasenas:
    """Funciones para manejo seguro de contrasenas con PBKDF2."""

    @staticmethod
    def hash_password(password, salt=None):
        """
        Genera hash seguro usando PBKDF2-HMAC-SHA256 (NIST SP 800-63B).

        Retrocompatible: los hashes nuevos se prefijan con 'pbkdf2:' para
        distinguirlos de los legacy SHA-256.

        Retorna: (hash_con_prefijo, salt)
        """
        if salt is None:
            salt = secrets.token_hex(32)

        # PBKDF2-HMAC-SHA256 con 600k iteraciones
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            _PBKDF2_ITERATIONS
        )
        password_hash = f"{_PBKDF2_PREFIX}{dk.hex()}"
        return password_hash, salt

    @staticmethod
    def verificar_password(password, hash_guardado, salt):
        """
        Verifica contrasena contra hash guardado.
        Soporta tanto PBKDF2 (nuevo) como SHA-256 legacy (retrocompat).
        """
        if hash_guardado.startswith(_PBKDF2_PREFIX):
            # Hash PBKDF2 nuevo
            dk = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                _PBKDF2_ITERATIONS
            )
            hash_calculado = f"{_PBKDF2_PREFIX}{dk.hex()}"
            return secrets.compare_digest(hash_calculado, hash_guardado)
        else:
            # Fallback: hash SHA-256 legacy
            combined = f"{salt}{password}".encode('utf-8')
            hash_obj = hashlib.sha256(combined)
            hash_calculado = hash_obj.hexdigest()
            return secrets.compare_digest(hash_calculado, hash_guardado)

    @staticmethod
    def necesita_rehash(hash_guardado):
        """Verifica si un hash necesita ser actualizado a PBKDF2."""
        return not hash_guardado.startswith(_PBKDF2_PREFIX)

    @staticmethod
    def validar_fortaleza_password(password):
        """
        Valida la fortaleza de una contrasena

        Retorna: (es_valida, mensaje)
        """
        if len(password) < 8:
            return False, "La contrasena debe tener al menos 8 caracteres"

        if not re.search(r'[A-Z]', password):
            return False, "La contrasena debe tener al menos una mayuscula"

        if not re.search(r'[a-z]', password):
            return False, "La contrasena debe tener al menos una minuscula"

        if not re.search(r'\d', password):
            return False, "La contrasena debe tener al menos un numero"

        return True, "Contrasena valida"

    @staticmethod
    def generar_password_temporal():
        """Genera una contrasena temporal segura"""
        # 12 caracteres aleatorios
        return secrets.token_urlsafe(12)


# ============================================================================
# CONTROL DE INTENTOS DE LOGIN
# ============================================================================

class ControlIntentos:
    """
    Controla intentos fallidos de login para prevenir fuerza bruta.
    Bloquea la cuenta tras MAX_INTENTOS fallidos durante VENTANA_MINUTOS.
    """

    MAX_INTENTOS = 5
    VENTANA_MINUTOS = 15

    def __init__(self):
        # {usuario: [(timestamp, exitoso), ...]}
        self._intentos = {}

    def registrar_intento(self, usuario, exitoso):
        """Registra un intento de login."""
        ahora = datetime.now()
        if usuario not in self._intentos:
            self._intentos[usuario] = []
        self._intentos[usuario].append((ahora, exitoso))

        # Limpiar intentos viejos (fuera de la ventana)
        self._limpiar_intentos_viejos(usuario, ahora)

        if exitoso:
            # Login exitoso: limpiar historial
            self._intentos[usuario] = []

    def esta_bloqueado(self, usuario):
        """
        Verifica si un usuario esta bloqueado por intentos fallidos.

        Retorna: (bloqueado, minutos_restantes)
        """
        if usuario not in self._intentos:
            return False, 0

        ahora = datetime.now()
        self._limpiar_intentos_viejos(usuario, ahora)

        # Contar intentos fallidos en la ventana
        fallidos = [t for t, exito in self._intentos.get(usuario, []) if not exito]

        if len(fallidos) >= self.MAX_INTENTOS:
            # Calcular tiempo restante de bloqueo
            primer_fallo = fallidos[0]
            from datetime import timedelta
            fin_bloqueo = primer_fallo + timedelta(minutes=self.VENTANA_MINUTOS)
            if ahora < fin_bloqueo:
                restante = int((fin_bloqueo - ahora).total_seconds() / 60) + 1
                return True, restante
            else:
                # Bloqueo expirado
                self._intentos[usuario] = []
                return False, 0

        return False, 0

    def intentos_restantes(self, usuario):
        """Retorna cuantos intentos le quedan al usuario."""
        if usuario not in self._intentos:
            return self.MAX_INTENTOS

        ahora = datetime.now()
        self._limpiar_intentos_viejos(usuario, ahora)

        fallidos = [t for t, exito in self._intentos.get(usuario, []) if not exito]
        return max(0, self.MAX_INTENTOS - len(fallidos))

    def _limpiar_intentos_viejos(self, usuario, ahora):
        """Elimina intentos fuera de la ventana de tiempo."""
        from datetime import timedelta
        ventana = ahora - timedelta(minutes=self.VENTANA_MINUTOS)
        self._intentos[usuario] = [
            (t, e) for t, e in self._intentos.get(usuario, [])
            if t > ventana
        ]


# Instancia global del control de intentos
control_intentos = ControlIntentos()


# ============================================================================
# AUDITORIA DE SEGURIDAD (BD + Log)
# ============================================================================

class AuditoriaSeguridad:
    """Funciones para registro de auditoria de seguridad en BD y archivo de log."""

    def __init__(self, db):
        self._db = db
        self._tabla_verificada = False

    def _asegurar_tabla(self):
        """Crea la tabla LogAuditoria si no existe."""
        if self._tabla_verificada:
            return
        try:
            self._db.execute("""
                CREATE TABLE LogAuditoria (
                    LogID AUTOINCREMENT PRIMARY KEY,
                    FechaHora DATETIME,
                    UsuarioID INTEGER,
                    Accion TEXT(100),
                    Tabla TEXT(50),
                    RegistroID INTEGER,
                    ValorAnterior MEMO,
                    ValorNuevo MEMO
                )
            """)
        except Exception:
            pass  # Ya existe
        self._tabla_verificada = True

    def registrar_login(self, usuario_id, exitoso, ip=None, equipo=None):
        """Registra un intento de login"""
        accion = 'LOGIN_EXITOSO' if exitoso else 'LOGIN_FALLIDO'
        detalle = f"Intento de login desde {ip or 'local'} equipo {equipo or 'desconocido'}"
        self._registrar(usuario_id, accion, 'Usuarios', usuario_id, detalle)
        log_auditoria(usuario_id, accion, detalle, modulo='login')

    def registrar_cambio_password(self, usuario_id, por_usuario_id):
        """Registra un cambio de contrasena"""
        detalle = "Cambio de contrasena"
        self._registrar(por_usuario_id, 'CAMBIO_PASSWORD', 'Usuarios', usuario_id, detalle)
        log_auditoria(por_usuario_id, 'CAMBIO_PASSWORD', detalle, modulo='seguridad')

    def registrar_acceso_denegado(self, usuario_id, modulo, accion):
        """Registra un intento de acceso denegado"""
        detalle = f"Intento de {accion} sin permisos en {modulo}"
        self._registrar(usuario_id, 'ACCESO_DENEGADO', modulo, None, detalle)
        log_auditoria(usuario_id, 'ACCESO_DENEGADO', detalle, modulo='seguridad')

    def registrar_operacion_sensible(self, usuario_id, tabla, registro_id, operacion, detalle):
        """Registra operaciones sensibles (borrado, modificacion de datos criticos)"""
        self._registrar(usuario_id, f'OP_{operacion}', tabla, registro_id, detalle)
        log_auditoria(usuario_id, f'OP_{operacion}', detalle, modulo=tabla)

    def registrar_resultado(self, usuario_id, detalle_id, param_id, valor_anterior, valor_nuevo, accion='GUARDAR'):
        """Registra modificacion de un resultado de laboratorio."""
        detalle = (
            f"DetalleID={detalle_id} ParamID={param_id} "
            f"Anterior='{valor_anterior or ''}' Nuevo='{valor_nuevo}'"
        )
        self._registrar_con_historia(
            usuario_id, f'RESULTADO_{accion}', 'ResultadosParametros',
            detalle_id, str(valor_anterior or ''), str(valor_nuevo)
        )
        log_auditoria(usuario_id, f'RESULTADO_{accion}', detalle, modulo='resultados')

    def _registrar(self, usuario_id, accion, tabla, registro_id, detalle):
        """Metodo interno para registrar en el log"""
        self._asegurar_tabla()
        try:
            detalle_safe = str(detalle)[:500].replace("'", "''")
            accion_safe = str(accion)[:100].replace("'", "''")
            tabla_safe = str(tabla)[:50].replace("'", "''")
            sql = (
                f"INSERT INTO LogAuditoria (FechaHora, UsuarioID, Accion, Tabla, RegistroID, ValorNuevo) "
                f"VALUES (#{datetime.now().strftime('%m/%d/%Y %H:%M:%S')}#, "
                f"{usuario_id or 'NULL'}, "
                f"'{accion_safe}', "
                f"'{tabla_safe}', "
                f"{registro_id or 'NULL'}, "
                f"'{detalle_safe}')"
            )
            self._db.execute(sql)
        except Exception as e:
            log_evento(f"Error registrando auditoria BD: {e}", nivel='error', modulo='auditoria')

    def _registrar_con_historia(self, usuario_id, accion, tabla, registro_id, valor_anterior, valor_nuevo):
        """Registra con valor anterior y nuevo (para trazabilidad de cambios)."""
        self._asegurar_tabla()
        try:
            anterior_safe = str(valor_anterior)[:500].replace("'", "''")
            nuevo_safe = str(valor_nuevo)[:500].replace("'", "''")
            accion_safe = str(accion)[:100].replace("'", "''")
            tabla_safe = str(tabla)[:50].replace("'", "''")
            sql = (
                f"INSERT INTO LogAuditoria (FechaHora, UsuarioID, Accion, Tabla, RegistroID, ValorAnterior, ValorNuevo) "
                f"VALUES (#{datetime.now().strftime('%m/%d/%Y %H:%M:%S')}#, "
                f"{usuario_id or 'NULL'}, "
                f"'{accion_safe}', "
                f"'{tabla_safe}', "
                f"{registro_id or 'NULL'}, "
                f"'{anterior_safe}', "
                f"'{nuevo_safe}')"
            )
            self._db.execute(sql)
        except Exception as e:
            log_evento(f"Error registrando auditoria con historia: {e}", nivel='error', modulo='auditoria')


# ============================================================================
# PROTECCION DE API KEYS (DPAPI Windows)
# ============================================================================

class ProtectorCredenciales:
    """
    Protege credenciales sensibles usando Windows DPAPI cuando esta disponible.
    Fallback: ofuscacion base64 (no es cifrado real, pero evita lectura casual).
    """

    @staticmethod
    def cifrar(texto_plano):
        """Cifra un texto sensible. Retorna string cifrado."""
        if not texto_plano:
            return ''
        try:
            # Intentar DPAPI (Windows)
            import ctypes
            import ctypes.wintypes

            class DATA_BLOB(ctypes.Structure):
                _fields_ = [
                    ('cbData', ctypes.wintypes.DWORD),
                    ('pbData', ctypes.POINTER(ctypes.c_char)),
                ]

            datos = texto_plano.encode('utf-8')
            blob_in = DATA_BLOB(len(datos), ctypes.cast(ctypes.create_string_buffer(datos, len(datos)), ctypes.POINTER(ctypes.c_char)))
            blob_out = DATA_BLOB()

            if ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(blob_in), None, None, None, None, 0,
                ctypes.byref(blob_out)
            ):
                cifrado = ctypes.string_at(blob_out.pbData, blob_out.cbData)
                ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                import base64
                return 'dpapi:' + base64.b64encode(cifrado).decode('ascii')
        except Exception:
            pass

        # Fallback: ofuscacion base64 con marca
        import base64
        return 'b64:' + base64.b64encode(texto_plano.encode('utf-8')).decode('ascii')

    @staticmethod
    def descifrar(texto_cifrado):
        """Descifra un texto protegido. Retorna texto plano."""
        if not texto_cifrado:
            return ''

        if texto_cifrado.startswith('dpapi:'):
            try:
                import ctypes
                import ctypes.wintypes
                import base64

                class DATA_BLOB(ctypes.Structure):
                    _fields_ = [
                        ('cbData', ctypes.wintypes.DWORD),
                        ('pbData', ctypes.POINTER(ctypes.c_char)),
                    ]

                datos = base64.b64decode(texto_cifrado[6:])
                blob_in = DATA_BLOB(len(datos), ctypes.cast(ctypes.create_string_buffer(datos, len(datos)), ctypes.POINTER(ctypes.c_char)))
                blob_out = DATA_BLOB()

                if ctypes.windll.crypt32.CryptUnprotectData(
                    ctypes.byref(blob_in), None, None, None, None, 0,
                    ctypes.byref(blob_out)
                ):
                    resultado = ctypes.string_at(blob_out.pbData, blob_out.cbData).decode('utf-8')
                    ctypes.windll.kernel32.LocalFree(blob_out.pbData)
                    return resultado
            except Exception:
                pass
            return ''

        if texto_cifrado.startswith('b64:'):
            import base64
            try:
                return base64.b64decode(texto_cifrado[4:]).decode('utf-8')
            except Exception:
                return ''

        # Sin prefijo = texto plano legacy (retrocompatible)
        return texto_cifrado


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("Modulo de Seguridad - ANgesLAB")
    print("=" * 50)

    # Pruebas de sanitizacion
    db_segura = DatabaseSegura(None)

    print("\n--- Pruebas de Sanitizacion ---")
    print(f"Texto normal: {db_segura.sanitizar_valor('Juan Perez')}")
    print(f"Con comillas: {db_segura.sanitizar_valor('O' + chr(39) + 'Brien')}")
    print(f"Numero: {db_segura.sanitizar_valor(123.45)}")
    print(f"Fecha: {db_segura.sanitizar_valor(datetime.now())}")
    print(f"Booleano: {db_segura.sanitizar_valor(True)}")

    # Pruebas de validacion
    print("\n--- Pruebas de Validacion ---")
    print(f"Email valido: {Validadores.es_email_valido('test@email.com')}")
    print(f"Email invalido: {Validadores.es_email_valido('test@')}")
    print(f"Cedula valida: {Validadores.es_cedula_valida('V-12345678')}")
    print(f"RIF valido: {Validadores.es_rif_valido('J-12345678-9')}")

    # Pruebas de contrasenas PBKDF2
    print("\n--- Pruebas de Contrasenas (PBKDF2) ---")
    password = "MiPassword123"
    hash_pass, salt = SeguridadContrasenas.hash_password(password)
    print(f"Hash generado: {hash_pass[:40]}...")
    print(f"Usa PBKDF2: {hash_pass.startswith('pbkdf2:')}")
    print(f"Verificacion correcta: {SeguridadContrasenas.verificar_password(password, hash_pass, salt)}")
    print(f"Verificacion incorrecta: {SeguridadContrasenas.verificar_password('otro', hash_pass, salt)}")

    # Prueba retrocompatibilidad SHA-256 legacy
    print("\n--- Retrocompat SHA-256 legacy ---")
    legacy_salt = secrets.token_hex(32)
    legacy_hash = hashlib.sha256(f"{legacy_salt}{password}".encode()).hexdigest()
    print(f"Verificacion legacy: {SeguridadContrasenas.verificar_password(password, legacy_hash, legacy_salt)}")
    print(f"Necesita rehash: {SeguridadContrasenas.necesita_rehash(legacy_hash)}")

    # Prueba control de intentos
    print("\n--- Control de Intentos ---")
    ci = ControlIntentos()
    for i in range(6):
        ci.registrar_intento('test_user', False)
        bloq, mins = ci.esta_bloqueado('test_user')
        print(f"  Intento {i+1}: bloqueado={bloq}, restantes={ci.intentos_restantes('test_user')}")

    # Prueba proteccion de credenciales
    print("\n--- Proteccion de Credenciales ---")
    pc = ProtectorCredenciales()
    original = "sk-ant-api-key-12345"
    cifrado = pc.cifrar(original)
    descifrado = pc.descifrar(cifrado)
    print(f"Original: {original}")
    print(f"Cifrado: {cifrado[:50]}...")
    print(f"Descifrado correcto: {descifrado == original}")

    # Prueba de deteccion de SQL Injection
    print("\n--- Pruebas de SQL Injection ---")
    try:
        db_segura.sanitizar_valor("'; DROP TABLE Usuarios; --")
    except ValueError as e:
        print(f"Detectado intento de injection: {e}")

    try:
        db_segura.sanitizar_valor("' OR '1'='1")
    except ValueError as e:
        print(f"Detectado intento de injection: {e}")

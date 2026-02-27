# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE AUDITORIA ACTIVA - ANgesLAB
================================================================================
Middleware de auditoria que se integra con el flujo principal de la aplicacion.
Proporciona:
- Registro automatico de operaciones sobre resultados clinicos
- Versionado de resultados (antes/despues de cada modificacion)
- Trazabilidad completa: quien, cuando, que cambio, valor anterior
- Cumplimiento ISO 15189:2022 §8.4 / CLIA 42 CFR 493.1291

Autor: Sistema ANgesLAB
================================================================================
"""

from datetime import datetime

try:
    from modulos.logging_config import log_auditoria, log_evento
except ImportError:
    def log_auditoria(uid, acc, det, **kw): pass
    def log_evento(msg, **kw): pass


class AuditoriaActiva:
    """
    Middleware de auditoria que se activa automaticamente para registrar
    todas las operaciones criticas del laboratorio.
    """

    def __init__(self, db, usuario_id=None):
        self._db = db
        self._usuario_id = usuario_id
        self._tabla_ok = False
        self._asegurar_tablas()

    def set_usuario(self, usuario_id):
        """Actualiza el usuario activo."""
        self._usuario_id = usuario_id

    # -------------------------------------------------------------------------
    # INICIALIZACION DE TABLAS DE AUDITORIA
    # -------------------------------------------------------------------------

    def _asegurar_tablas(self):
        """Crea las tablas de auditoria si no existen."""
        if self._tabla_ok:
            return
        # LogAuditoria (tabla principal)
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

        # HistorialResultados (versionado de resultados clinicos)
        try:
            self._db.execute("""
                CREATE TABLE HistorialResultados (
                    HistorialID AUTOINCREMENT PRIMARY KEY,
                    FechaHora DATETIME,
                    UsuarioID INTEGER,
                    DetalleID INTEGER,
                    ParametroID INTEGER,
                    ValorAnterior TEXT(500),
                    ValorNuevo TEXT(500),
                    EstadoAnterior TEXT(50),
                    EstadoNuevo TEXT(50),
                    Accion TEXT(50),
                    Observacion TEXT(500)
                )
            """)
        except Exception:
            pass  # Ya existe

        self._tabla_ok = True

    # -------------------------------------------------------------------------
    # AUDITORIA DE RESULTADOS (CORE CLINICO)
    # -------------------------------------------------------------------------

    def antes_guardar_resultado(self, detalle_id, param_id):
        """
        Captura el estado actual de un resultado ANTES de modificarlo.
        Debe llamarse antes de cualquier UPDATE en ResultadosParametros.

        Retorna: dict con valores actuales o None si no existe
        """
        try:
            actual = self._db.query_one(
                f"SELECT Valor, Estado FROM ResultadosParametros "
                f"WHERE DetalleID = {int(detalle_id)} AND ParametroID = {int(param_id)}"
            )
            if actual:
                return {
                    'valor': actual.get('Valor', ''),
                    'estado': actual.get('Estado', ''),
                }
        except Exception as e:
            log_evento(f"Error capturando estado anterior: {e}", nivel='error', modulo='auditoria')
        return None

    def despues_guardar_resultado(self, detalle_id, param_id, valor_nuevo,
                                   estado_nuevo, estado_anterior_dict=None,
                                   accion='GUARDAR'):
        """
        Registra el cambio de resultado DESPUES de guardarlo.

        Args:
            detalle_id: ID del detalle de solicitud
            param_id: ID del parametro
            valor_nuevo: Nuevo valor del resultado
            estado_nuevo: Nuevo estado (Capturado, Validado)
            estado_anterior_dict: dict retornado por antes_guardar_resultado()
            accion: GUARDAR, VALIDAR, CORREGIR
        """
        valor_anterior = ''
        estado_anterior = ''
        if estado_anterior_dict:
            valor_anterior = estado_anterior_dict.get('valor', '')
            estado_anterior = estado_anterior_dict.get('estado', '')

        # Solo registrar si hubo un cambio real
        if valor_anterior == valor_nuevo and estado_anterior == estado_nuevo:
            return

        self._registrar_historial_resultado(
            detalle_id, param_id,
            valor_anterior, valor_nuevo,
            estado_anterior, estado_nuevo,
            accion
        )

    def registrar_validacion_masiva(self, detalle_id, usuario_id=None):
        """Registra una validacion masiva de todos los parametros de un detalle."""
        uid = usuario_id or self._usuario_id
        try:
            # Obtener todos los parametros de este detalle
            params = self._db.query(
                f"SELECT ParametroID, Valor, Estado FROM ResultadosParametros "
                f"WHERE DetalleID = {int(detalle_id)}"
            )
            for p in (params or []):
                self._registrar_historial_resultado(
                    detalle_id, p.get('ParametroID'),
                    p.get('Valor', ''), p.get('Valor', ''),
                    p.get('Estado', ''), 'Validado',
                    'VALIDAR'
                )
        except Exception as e:
            log_evento(f"Error en validacion masiva auditoria: {e}", nivel='error', modulo='auditoria')

    def _registrar_historial_resultado(self, detalle_id, param_id,
                                        valor_anterior, valor_nuevo,
                                        estado_anterior, estado_nuevo, accion):
        """Inserta un registro en HistorialResultados y LogAuditoria."""
        uid = self._usuario_id or 0
        ahora = datetime.now().strftime('%m/%d/%Y %H:%M:%S')

        # 1) Tabla HistorialResultados (versionado)
        try:
            va_safe = str(valor_anterior or '')[:500].replace("'", "''")
            vn_safe = str(valor_nuevo or '')[:500].replace("'", "''")
            ea_safe = str(estado_anterior or '')[:50].replace("'", "''")
            en_safe = str(estado_nuevo or '')[:50].replace("'", "''")
            ac_safe = str(accion or '')[:50].replace("'", "''")

            self._db.execute(
                f"INSERT INTO HistorialResultados "
                f"(FechaHora, UsuarioID, DetalleID, ParametroID, "
                f"ValorAnterior, ValorNuevo, EstadoAnterior, EstadoNuevo, Accion) "
                f"VALUES (#{ahora}#, {uid}, {int(detalle_id)}, {int(param_id)}, "
                f"'{va_safe}', '{vn_safe}', '{ea_safe}', '{en_safe}', '{ac_safe}')"
            )
        except Exception as e:
            log_evento(f"Error insertando HistorialResultados: {e}", nivel='error', modulo='auditoria')

        # 2) Log de auditoria archivo
        detalle_log = (
            f"DetalleID={detalle_id} ParamID={param_id} "
            f"'{valor_anterior}' -> '{valor_nuevo}' ({estado_anterior}->{estado_nuevo})"
        )
        log_auditoria(uid, f'RESULTADO_{accion}', detalle_log, modulo='resultados')

    # -------------------------------------------------------------------------
    # AUDITORIA DE OPERACIONES GENERALES
    # -------------------------------------------------------------------------

    def registrar_login(self, usuario_id, exitoso, detalle=''):
        """Registra intento de login."""
        accion = 'LOGIN_EXITOSO' if exitoso else 'LOGIN_FALLIDO'
        self._registrar_log(usuario_id, accion, 'Usuarios', usuario_id, detalle)
        log_auditoria(usuario_id, accion, detalle, modulo='login')

    def registrar_eliminacion(self, tabla, registro_id, detalle=''):
        """Registra una eliminacion de registro."""
        self._registrar_log(self._usuario_id, 'ELIMINAR', tabla, registro_id, detalle)
        log_auditoria(self._usuario_id, 'ELIMINAR', f"{tabla} ID={registro_id} {detalle}", modulo=tabla)

    def registrar_creacion(self, tabla, registro_id, detalle=''):
        """Registra creacion de un registro."""
        self._registrar_log(self._usuario_id, 'CREAR', tabla, registro_id, detalle)
        log_auditoria(self._usuario_id, 'CREAR', f"{tabla} ID={registro_id} {detalle}", modulo=tabla)

    def registrar_modificacion(self, tabla, registro_id, detalle=''):
        """Registra modificacion de un registro."""
        self._registrar_log(self._usuario_id, 'MODIFICAR', tabla, registro_id, detalle)
        log_auditoria(self._usuario_id, 'MODIFICAR', f"{tabla} ID={registro_id} {detalle}", modulo=tabla)

    def registrar_impresion(self, tabla, registro_id, detalle=''):
        """Registra impresion/generacion de un reporte."""
        self._registrar_log(self._usuario_id, 'IMPRIMIR', tabla, registro_id, detalle)
        log_auditoria(self._usuario_id, 'IMPRIMIR', f"{tabla} ID={registro_id} {detalle}", modulo='reportes')

    def registrar_envio(self, tabla, registro_id, detalle=''):
        """Registra envio de resultados (email, WhatsApp)."""
        self._registrar_log(self._usuario_id, 'ENVIAR', tabla, registro_id, detalle)
        log_auditoria(self._usuario_id, 'ENVIAR', f"{tabla} ID={registro_id} {detalle}", modulo='envio')

    def _registrar_log(self, usuario_id, accion, tabla, registro_id, detalle):
        """Inserta en LogAuditoria."""
        self._asegurar_tablas()
        try:
            detalle_safe = str(detalle or '')[:500].replace("'", "''")
            accion_safe = str(accion)[:100].replace("'", "''")
            tabla_safe = str(tabla)[:50].replace("'", "''")
            ahora = datetime.now().strftime('%m/%d/%Y %H:%M:%S')
            self._db.execute(
                f"INSERT INTO LogAuditoria (FechaHora, UsuarioID, Accion, Tabla, RegistroID, ValorNuevo) "
                f"VALUES (#{ahora}#, {usuario_id or 'NULL'}, '{accion_safe}', "
                f"'{tabla_safe}', {registro_id or 'NULL'}, '{detalle_safe}')"
            )
        except Exception as e:
            log_evento(f"Error en log auditoria: {e}", nivel='error', modulo='auditoria')

    # -------------------------------------------------------------------------
    # CONSULTA DE HISTORIAL
    # -------------------------------------------------------------------------

    def obtener_historial_resultado(self, detalle_id, param_id=None):
        """
        Obtiene el historial de cambios de un resultado.

        Retorna: lista de dicts con FechaHora, UsuarioID, ValorAnterior,
                 ValorNuevo, EstadoAnterior, EstadoNuevo, Accion
        """
        try:
            where = f"DetalleID = {int(detalle_id)}"
            if param_id:
                where += f" AND ParametroID = {int(param_id)}"

            return self._db.query(
                f"SELECT * FROM HistorialResultados WHERE {where} ORDER BY FechaHora DESC"
            ) or []
        except Exception:
            return []

    def obtener_log_usuario(self, usuario_id, desde=None, hasta=None, limit=100):
        """
        Obtiene el log de acciones de un usuario.

        Retorna: lista de registros de LogAuditoria
        """
        try:
            where = f"UsuarioID = {int(usuario_id)}"
            if desde:
                where += f" AND FechaHora >= #{desde.strftime('%m/%d/%Y')}#"
            if hasta:
                where += f" AND FechaHora <= #{hasta.strftime('%m/%d/%Y 23:59:59')}#"

            return self._db.query(
                f"SELECT TOP {int(limit)} * FROM LogAuditoria WHERE {where} ORDER BY FechaHora DESC"
            ) or []
        except Exception:
            return []

# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE LOGGING ESTRUCTURADO - ANgesLAB
================================================================================
Proporciona logging centralizado con:
- Rotacion automatica de archivos de log
- Niveles de severidad (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Formato estructurado con timestamp, modulo, usuario, accion
- Archivo de log separado para auditoria clinica

Autor: Sistema ANgesLAB
================================================================================
"""

import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

# Directorio de logs
LOG_DIR = Path(__file__).parent.parent / 'logs'

def _asegurar_directorio_logs():
    """Crea el directorio de logs si no existe."""
    if not LOG_DIR.exists():
        LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# FORMATEADORES
# ============================================================================

class FormatoANgesLAB(logging.Formatter):
    """Formateador personalizado para ANgesLAB."""

    def format(self, record):
        # Agregar campos personalizados si no existen
        if not hasattr(record, 'usuario'):
            record.usuario = '-'
        if not hasattr(record, 'accion'):
            record.accion = '-'
        if not hasattr(record, 'modulo_app'):
            record.modulo_app = record.module
        return super().format(record)


# ============================================================================
# CONFIGURACION CENTRAL
# ============================================================================

_loggers_inicializados = {}

def obtener_logger(nombre='angeslab', usuario_id=None):
    """
    Obtiene un logger configurado para el modulo especificado.

    Args:
        nombre: Nombre del logger (ej. 'angeslab', 'angeslab.seguridad')
        usuario_id: ID del usuario actual (opcional)

    Returns:
        logging.Logger configurado
    """
    if nombre in _loggers_inicializados:
        return _loggers_inicializados[nombre]

    _asegurar_directorio_logs()

    logger = logging.getLogger(nombre)
    logger.setLevel(logging.DEBUG)

    # Evitar duplicar handlers si ya existen
    if logger.handlers:
        _loggers_inicializados[nombre] = logger
        return logger

    # Formato detallado para archivo
    formato_archivo = FormatoANgesLAB(
        '%(asctime)s | %(levelname)-8s | %(modulo_app)-20s | '
        'Usuario:%(usuario)-6s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Formato simple para consola
    formato_consola = logging.Formatter(
        '[%(levelname)s] %(name)s: %(message)s'
    )

    # Handler de archivo rotativo - log general (5 MB, 10 backups)
    ruta_log = LOG_DIR / 'angeslab.log'
    handler_archivo = logging.handlers.RotatingFileHandler(
        str(ruta_log),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=10,
        encoding='utf-8'
    )
    handler_archivo.setLevel(logging.INFO)
    handler_archivo.setFormatter(formato_archivo)
    logger.addHandler(handler_archivo)

    # Handler de archivo rotativo - errores (2 MB, 5 backups)
    ruta_errores = LOG_DIR / 'angeslab_errores.log'
    handler_errores = logging.handlers.RotatingFileHandler(
        str(ruta_errores),
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    handler_errores.setLevel(logging.ERROR)
    handler_errores.setFormatter(formato_archivo)
    logger.addHandler(handler_errores)

    # Handler de consola (solo para desarrollo)
    handler_consola = logging.StreamHandler()
    handler_consola.setLevel(logging.WARNING)
    handler_consola.setFormatter(formato_consola)
    logger.addHandler(handler_consola)

    _loggers_inicializados[nombre] = logger
    return logger


def obtener_logger_auditoria():
    """
    Obtiene el logger especifico para auditoria clinica.
    Este log se mantiene separado y con mayor retencion.
    """
    nombre = 'angeslab.auditoria'
    if nombre in _loggers_inicializados:
        return _loggers_inicializados[nombre]

    _asegurar_directorio_logs()

    logger = logging.getLogger(nombre)
    logger.setLevel(logging.INFO)

    if logger.handlers:
        _loggers_inicializados[nombre] = logger
        return logger

    # Formato de auditoria con campos clinicos
    formato = FormatoANgesLAB(
        '%(asctime)s | AUDIT | %(modulo_app)-15s | '
        'Usuario:%(usuario)-6s | Accion:%(accion)-25s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Archivo de auditoria (10 MB, 30 backups = ~300 MB historico)
    ruta_audit = LOG_DIR / 'auditoria_clinica.log'
    handler = logging.handlers.RotatingFileHandler(
        str(ruta_audit),
        maxBytes=10 * 1024 * 1024,
        backupCount=30,
        encoding='utf-8'
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(formato)
    logger.addHandler(handler)

    _loggers_inicializados[nombre] = logger
    return logger


class LogAdapter(logging.LoggerAdapter):
    """
    Adapter que inyecta usuario_id y modulo en cada mensaje.
    Uso:
        log = LogAdapter(obtener_logger(), usuario_id=5, modulo='resultados')
        log.info("Resultado guardado", extra={'accion': 'GUARDAR_RESULTADO'})
    """

    def __init__(self, logger, usuario_id=None, modulo='general'):
        super().__init__(logger, {})
        self._usuario_id = usuario_id or '-'
        self._modulo = modulo

    def process(self, msg, kwargs):
        extra = kwargs.get('extra', {})
        extra.setdefault('usuario', str(self._usuario_id))
        extra.setdefault('modulo_app', self._modulo)
        extra.setdefault('accion', '-')
        kwargs['extra'] = extra
        return msg, kwargs

    def set_usuario(self, usuario_id):
        """Actualiza el ID de usuario (tras login)."""
        self._usuario_id = usuario_id


# ============================================================================
# FUNCION DE CONVENIENCIA
# ============================================================================

def log_evento(mensaje, nivel='info', usuario_id=None, modulo='general', accion='-'):
    """
    Registra un evento de forma rapida sin crear adapter.

    Args:
        mensaje: Texto del evento
        nivel: 'debug', 'info', 'warning', 'error', 'critical'
        usuario_id: ID del usuario
        modulo: Nombre del modulo
        accion: Tipo de accion realizada
    """
    logger = obtener_logger()
    extra = {
        'usuario': str(usuario_id or '-'),
        'modulo_app': modulo,
        'accion': accion,
    }
    getattr(logger, nivel, logger.info)(mensaje, extra=extra)


def log_auditoria(usuario_id, accion, detalle, modulo='general'):
    """
    Registra un evento de auditoria clinica en el log dedicado.

    Args:
        usuario_id: ID del usuario que realiza la accion
        accion: Tipo de accion (LOGIN, GUARDAR_RESULTADO, VALIDAR, etc.)
        detalle: Descripcion detallada
        modulo: Nombre del modulo
    """
    logger = obtener_logger_auditoria()
    extra = {
        'usuario': str(usuario_id or '-'),
        'modulo_app': modulo,
        'accion': accion,
    }
    logger.info(detalle, extra=extra)

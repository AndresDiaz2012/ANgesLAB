# -*- coding: utf-8 -*-
"""
================================================================================
CIERRE DE PERIODO FISCAL
================================================================================
Un mes declarado no se toca. Si despues de declarar el IVA de octubre
alguien carga una compra con fecha de octubre o anula una retencion de
octubre, el libro del mes deja de cuadrar con lo declarado y nadie se entera
hasta una fiscalizacion.

Cerrado un mes, compras, retenciones, facturas y sus anulaciones con fecha
de ese mes se rechazan. Reabrirlo se puede -hay correcciones legitimas, con
declaracion sustitutiva- pero exige motivo y queda registrado.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime, date

from modulos.compras import _insert, _update, _tabla_existe, _fecha

ABIERTO, CERRADO = 'Abierto', 'Cerrado'

DDL = ("CREATE TABLE [PeriodosFiscales] ([PeriodoID] COUNTER PRIMARY KEY, [Periodo] TEXT(6), "
       "[Estado] TEXT(10), [FechaCierre] DATETIME, [UsuarioCierre] TEXT(50), "
       "[FechaReapertura] DATETIME, [UsuarioReapertura] TEXT(50), [MotivoReapertura] TEXT(255))")


class PeriodoCerrado(ValueError):
    """Se intento registrar algo en un mes cerrado. El mensaje es para el usuario."""


def asegurar_esquema(db):
    if not _tabla_existe(db, 'PeriodosFiscales'):
        db.execute(DDL)
        return True
    return False


def periodo(fecha):
    f = _fecha(fecha) if not isinstance(fecha, (date, datetime)) else fecha
    return '%04d%02d' % (f.year, f.month)


def _validar(per):
    per = str(per or '').strip()
    if len(per) != 6 or not per.isdigit() or not 1 <= int(per[4:]) <= 12:
        raise ValueError('El periodo es AAAAMM, por ejemplo 202611.')
    return per


def _fila(db, per):
    return db.query_one("SELECT * FROM [PeriodosFiscales] WHERE Periodo='%s'" % per)


def esta_cerrado(db, fecha_o_periodo):
    """True si el mes de esa fecha (o ese AAAAMM) esta cerrado."""
    if not _tabla_existe(db, 'PeriodosFiscales'):
        return False
    per = fecha_o_periodo if isinstance(fecha_o_periodo, str) and len(fecha_o_periodo) == 6 \
        and fecha_o_periodo.isdigit() else periodo(fecha_o_periodo)
    fila = _fila(db, per)
    return bool(fila and fila.get('Estado') == CERRADO)


def verificar_abierto(db, fecha, que='la operacion'):
    """Lanza PeriodoCerrado si el mes de 'fecha' esta cerrado."""
    if fecha is None:
        return
    if esta_cerrado(db, fecha):
        per = periodo(fecha)
        raise PeriodoCerrado('El periodo %s/%s esta cerrado: no se puede registrar %s con esa '
                             'fecha. Si hay que corregir lo declarado, reabra el periodo con su '
                             'motivo.' % (per[4:], per[:4], que))


def cerrar(db, per, usuario=''):
    asegurar_esquema(db)
    per = _validar(per)
    if per >= periodo(date.today()):
        raise ValueError('Solo se cierran meses ya terminados.')
    fila = _fila(db, per)
    if fila and fila.get('Estado') == CERRADO:
        raise ValueError('El periodo ya esta cerrado.')
    datos = {'Estado': CERRADO, 'FechaCierre': datetime.now(), 'UsuarioCierre': str(usuario)[:50]}
    if fila:
        _update(db, 'PeriodosFiscales', datos, "Periodo='%s'" % per)
    else:
        _insert(db, 'PeriodosFiscales', dict(datos, Periodo=per))


def reabrir(db, per, motivo, usuario=''):
    asegurar_esquema(db)
    per = _validar(per)
    if not str(motivo or '').strip():
        raise ValueError('Reabrir un periodo declarado exige el motivo.')
    fila = _fila(db, per)
    if not fila or fila.get('Estado') != CERRADO:
        raise ValueError('El periodo no esta cerrado.')
    _update(db, 'PeriodosFiscales', {'Estado': ABIERTO, 'FechaReapertura': datetime.now(),
                                     'UsuarioReapertura': str(usuario)[:50],
                                     'MotivoReapertura': str(motivo)[:255]}, "Periodo='%s'" % per)


def listar(db):
    asegurar_esquema(db)
    return db.query("SELECT * FROM [PeriodosFiscales] ORDER BY Periodo DESC") or []

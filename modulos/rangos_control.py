# -*- coding: utf-8 -*-
"""
================================================================================
RANGOS DE NUMEROS DE CONTROL - PROVIDENCIA SNAT/2026/00093, ART. 9
================================================================================
Los numeros de control de las facturas digitales no se los inventa el
programa: se los ASIGNA la imprenta digital o el proveedor tecnologico
autorizado, por rangos, y el emisor los va gastando en orden.

    N° de Control  desde el N° 00-00000001  hasta el N° 00-00001000

Hasta ahora ANgesLAB deducia el siguiente numero del mayor que hubiera en
la tabla de facturas. Con la norma derogada bastaba; con esta no, por dos
razones:

  - El rango lo fija un tercero. Si la imprenta asigna del 1 al 1.000 y el
    programa sigue contando hasta el 1.001, ese documento esta fuera del
    rango autorizado.
  - El numero tiene que poder AGOTARSE. Deduciendolo del ultimo usado nunca
    se agota, de modo que nadie se entera de que hay que pedir mas hasta que
    lo dice una inspeccion.

Por eso los rangos se guardan: con lo que la imprenta asigno, desde cuando,
y cuanto queda. El programa avisa antes de quedarse sin numeros, que es la
unica forma de que eso no pare la facturacion un martes por la manana.

FORMATO DEL NUMERO (art. 9)

Dos digitos de identificador y hasta ocho de secuencial:

    00-00000001
    ^^ ^^^^^^^^
    |  secuencial, hasta 8 digitos
    identificador de 2, empieza en 00

La primera asignacion empieza en identificador 00 y secuencial 1. Al agotar
los ocho digitos se pasa al identificador siguiente.

SIN RANGO CARGADO

El programa NO inventa uno. Devuelve None y quien llama decide: avisar al
usuario y no emitir, que es lo correcto, en vez de poner un numero que
nadie autorizo.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.rangos_control')
except Exception:  # pragma: no cover
    import logging
    _log = logging.getLogger('angeslab.rangos_control')


TABLA = 'RangosControl'

# Cuando queden menos de estos numeros se avisa. Suficiente para pedir un
# rango nuevo sin prisa; pedirlo el dia que se agota es quedarse parado.
AVISO_QUEDAN = 50

SECUENCIAL_MAXIMO = 99999999  # ocho digitos (art. 9)
IDENTIFICADOR_MAXIMO = 99     # dos digitos


def formatear(identificador, secuencial):
    """El numero de control como se imprime: 00-00000001."""
    return '%02d-%08d' % (int(identificador), int(secuencial))


def partir(numero):
    """
    (identificador, secuencial) de un numero de control, o None.

    Tolera que venga sin guion, que es como lo guardaban algunas versiones.
    """
    texto = str(numero or '').strip()
    if not texto:
        return None
    try:
        if '-' in texto:
            ident, sec = texto.split('-', 1)
            return int(ident), int(sec)
        # Sin guion: los dos primeros digitos son el identificador
        if len(texto) > 8:
            return int(texto[:-8]), int(texto[-8:])
        return 0, int(texto)
    except (TypeError, ValueError):
        return None


def asegurar_tabla(db):
    """Crea la tabla de rangos si falta. Devuelve True si esta lista."""
    try:
        db.query_one("SELECT TOP 1 [RangoID] FROM [%s]" % TABLA)
        return True
    except Exception:
        pass
    try:
        db.execute(
            "CREATE TABLE [%s] ("
            "[RangoID] COUNTER PRIMARY KEY, "
            "[Identificador] INTEGER, "
            "[Desde] LONG, "
            "[Hasta] LONG, "
            "[Siguiente] LONG, "
            "[FechaAsignacion] DATETIME, "
            "[ImprentaNombre] TEXT(200), "
            "[ImprentaRIF] TEXT(50), "
            "[ImprentaProvidencia] TEXT(100), "
            "[Activo] BIT, "
            "[Observaciones] TEXT(255))" % TABLA)
        _log.info("Tabla %s creada", TABLA)
        return True
    except Exception as e:
        _log.error("No se pudo crear la tabla %s: %s", TABLA, e)
        return False


def registrar_rango(db, desde, hasta, identificador=0, fecha=None,
                    imprenta=None, observaciones=''):
    """
    Anota un rango recien asignado por la imprenta.

    Devuelve (ok, mensaje). No se admite un rango que se solape con otro ya
    cargado: dos facturas con el mismo numero de control es justo lo que
    estos numeros existen para impedir.
    """
    if not asegurar_tabla(db):
        return False, 'No se pudo preparar la tabla de rangos.'

    try:
        desde, hasta = int(desde), int(hasta)
        identificador = int(identificador or 0)
    except (TypeError, ValueError):
        return False, 'Los numeros del rango no son validos.'

    if desde < 1 or hasta < desde:
        return False, 'El rango tiene que ir de menor a mayor y empezar en 1 o mas.'
    if hasta > SECUENCIAL_MAXIMO:
        return False, ('El secuencial no puede pasar de %d: son ocho digitos.'
                       % SECUENCIAL_MAXIMO)
    if identificador < 0 or identificador > IDENTIFICADOR_MAXIMO:
        return False, 'El identificador son dos digitos: de 00 a 99.'

    for r in listar_rangos(db):
        if int(r.get('Identificador') or 0) != identificador:
            continue
        if int(r['Desde']) <= hasta and desde <= int(r['Hasta']):
            return False, ('El rango se solapa con el %s - %s ya cargado.'
                           % (formatear(identificador, r['Desde']),
                              formatear(identificador, r['Hasta'])))

    imprenta = imprenta or {}
    cuando = fecha or datetime.now()
    try:
        db.execute(
            "INSERT INTO [%s] ([Identificador], [Desde], [Hasta], [Siguiente], "
            "[FechaAsignacion], [ImprentaNombre], [ImprentaRIF], "
            "[ImprentaProvidencia], [Activo], [Observaciones]) VALUES "
            "(%d, %d, %d, %d, #%s#, '%s', '%s', '%s', True, '%s')"
            % (TABLA, identificador, desde, hasta, desde,
               cuando.strftime('%m/%d/%Y %H:%M:%S'),
               _esc(imprenta.get('nombre')), _esc(imprenta.get('rif')),
               _esc(imprenta.get('providencia')), _esc(observaciones)))
    except Exception as e:
        _log.error("No se pudo registrar el rango: %s", e)
        return False, 'No se pudo guardar el rango: %s' % e

    return True, ('Rango %s - %s cargado (%d numeros).'
                  % (formatear(identificador, desde),
                     formatear(identificador, hasta), hasta - desde + 1))


def _esc(valor):
    return str(valor or '').replace("'", "''")[:200]


def listar_rangos(db, solo_activos=False):
    """Los rangos cargados, del mas antiguo al mas nuevo."""
    if not asegurar_tabla(db):
        return []
    sql = "SELECT * FROM [%s]" % TABLA
    if solo_activos:
        sql += " WHERE [Activo] = True"
    sql += " ORDER BY [Identificador], [Desde]"
    try:
        return db.query(sql) or []
    except Exception as e:
        _log.error("No se pudieron leer los rangos: %s", e)
        return []


def rango_vigente(db):
    """
    El rango del que toca gastar, o None si no queda ninguno.

    Se gasta en orden: el mas antiguo que todavia tenga numeros.
    """
    for r in listar_rangos(db, solo_activos=True):
        try:
            if int(r['Siguiente']) <= int(r['Hasta']):
                return r
        except (TypeError, ValueError, KeyError):
            continue
    return None


def quedan(db):
    """Cuantos numeros de control quedan sin gastar en total."""
    total = 0
    for r in listar_rangos(db, solo_activos=True):
        try:
            total += max(0, int(r['Hasta']) - int(r['Siguiente']) + 1)
        except (TypeError, ValueError, KeyError):
            continue
    return total


def tomar_numero(db):
    """
    Saca el siguiente numero de control y lo da por gastado.

    Devuelve dict con numero, identificador, secuencial, rango y cuantos
    quedan; o None si no hay rango cargado, que es cuando NO hay que emitir.

    Marcar el numero como gastado antes de que la factura exista es
    deliberado: si algo falla despues, se pierde un numero y queda un hueco
    -explicable y auditable-, mientras que repetir un numero en dos facturas
    no tiene arreglo.
    """
    r = rango_vigente(db)
    if not r:
        return None

    try:
        secuencial = int(r['Siguiente'])
        identificador = int(r.get('Identificador') or 0)
    except (TypeError, ValueError, KeyError):
        return None

    try:
        db.execute("UPDATE [%s] SET [Siguiente] = %d WHERE [RangoID] = %d"
                   % (TABLA, secuencial + 1, int(r['RangoID'])))
    except Exception as e:
        _log.error("No se pudo avanzar el rango: %s", e)
        return None

    restan = quedan(db)
    if 0 < restan <= AVISO_QUEDAN:
        _log.warning("Quedan %d numeros de control: pida un rango nuevo",
                     restan)

    return {
        'numero': formatear(identificador, secuencial),
        'identificador': identificador,
        'secuencial': secuencial,
        'desde': int(r['Desde']),
        'hasta': int(r['Hasta']),
        'fecha_asignacion': r.get('FechaAsignacion'),
        'imprenta_nombre': r.get('ImprentaNombre') or '',
        'imprenta_rif': r.get('ImprentaRIF') or '',
        'imprenta_providencia': r.get('ImprentaProvidencia') or '',
        'quedan': restan,
    }


def datos_del_numero(db, numero_control):
    """
    El rango al que pertenece un numero ya emitido, para reimprimir.

    Una factura se reimprime meses despues y tiene que volver a salir con el
    mismo rango y la misma fecha de asignacion que llevaba: son datos del
    documento, no del momento en que se imprime.
    """
    partes = partir(numero_control)
    if not partes:
        return None
    identificador, secuencial = partes
    for r in listar_rangos(db):
        try:
            if (int(r.get('Identificador') or 0) == identificador
                    and int(r['Desde']) <= secuencial <= int(r['Hasta'])):
                return {
                    'desde': int(r['Desde']),
                    'hasta': int(r['Hasta']),
                    'identificador': identificador,
                    'fecha_asignacion': r.get('FechaAsignacion'),
                    'imprenta_nombre': r.get('ImprentaNombre') or '',
                    'imprenta_rif': r.get('ImprentaRIF') or '',
                    'imprenta_providencia': r.get('ImprentaProvidencia') or '',
                }
        except (TypeError, ValueError, KeyError):
            continue
    return None


def texto_rango(datos):
    """
    Como se escribe el rango en la factura (art. 9).

        N° de Control desde el N° 00-00000001 hasta el N° 00-00001000
    """
    if not datos:
        return ''
    ident = int(datos.get('identificador') or 0)
    return ('N° de Control desde el N° %s hasta el N° %s'
            % (formatear(ident, datos['desde']),
               formatear(ident, datos['hasta'])))

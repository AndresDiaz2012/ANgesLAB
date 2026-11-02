# -*- coding: utf-8 -*-
"""
================================================================================
UNIDADES DE MEDIDA
================================================================================
Dar de alta una unidad desde el programa, sin tocar la base a mano.

El desplegable de unidades de un parametro es de solo lectura y se llena de
la tabla Unidades. Hasta ahora, cada unidad nueva -una RU/mL de un
inmunoensayo, una U Todd de una ASLO- habia que insertarla por script. Un
laboratorio incorpora reactivos nuevos cada pocos meses, asi que eso iba a
pasar otra vez.

POR QUE VALIDA Y NO SOLO INSERTA

Porque el simbolo de la unidad se imprime en el informe que firma el
bioanalista, al lado del resultado. Dos entradas que digan "mg/dL" y
"mg/dl" se ven iguales en el desplegable y producen informes distintos; y
una unidad escrita con un espacio de mas al final no se vuelve a encontrar
nunca. Lo que entra aqui, entra limpio.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import re
import unicodedata

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.unidades')
except Exception:  # pragma: no cover
    import logging
    _log = logging.getLogger('angeslab.unidades')


# Como las tiene clasificadas la tabla. 'LABORATORIO' es el que llevan las
# unidades de resultado, que son las que se dan de alta desde aqui.
TIPO_DEFECTO = 'LABORATORIO'
TIPOS = ('LABORATORIO', 'Concentracion', 'Actividad', 'Proporcion',
         'Recuento', 'Tiempo', 'Velocidad', 'General')

LARGO_SIMBOLO = 50
LARGO_NOMBRE = 100


def normalizar_simbolo(texto):
    """
    El simbolo tal como se va a guardar e imprimir.

    Solo se quitan los espacios de los extremos y se colapsan los de en
    medio. NO se cambian mayusculas ni se quitan acentos: en una unidad cada
    caracter significa algo -mg no es MG, y uU/mL no es UU/mL- y
    "corregirlo" seria inventarse otra unidad.
    """
    return ' '.join(str(texto or '').split())[:LARGO_SIMBOLO]


def normalizar_codigo(simbolo):
    """
    El codigo interno a partir del simbolo, al estilo de los que ya hay:

        U/mL    -> U_ML
        RU/mL   -> RU_ML
        10^6/uL -> 10_6_UL

    Es un identificador, no se imprime, asi que aqui si se pasa a mayusculas
    y se quitan acentos.
    """
    t = unicodedata.normalize('NFKD', str(simbolo or ''))
    t = t.encode('ascii', 'ignore').decode('ascii').upper()
    t = re.sub(r'[^A-Z0-9]+', '_', t).strip('_')
    return t[:50] or 'UNIDAD'


def _comparable(simbolo):
    """
    Para detectar duplicados: sin espacios, sin acentos y en minuscula.

    Asi "mg/dL", "mg / dl" y "MG/DL" se reconocen como la misma unidad
    aunque se guarden tal cual se escribieron.
    """
    bruto = re.sub(r'\s+', '', str(simbolo or '')).lower()
    t = unicodedata.normalize('NFKD', bruto)
    t = t.encode('ascii', 'ignore').decode('ascii')
    # Un simbolo que sea todo signos fuera de ASCII -un punto medio, una mu
    # suelta- se queda en nada al pasarlo a ascii, y entonces no se
    # encontraria ni a si mismo. En ese caso se compara tal cual.
    return t or bruto


def listar(db, solo_activas=False):
    """Las unidades, ordenadas por simbolo como las muestra el desplegable."""
    sql = "SELECT UnidadID, CodigoUnidad, NombreUnidad, Simbolo, TipoUnidad, Activo FROM Unidades"
    if solo_activas:
        sql += " WHERE Activo = True"
    sql += " ORDER BY Simbolo"
    try:
        return db.query(sql) or []
    except Exception as e:
        _log.error("No se pudieron leer las unidades: %s", e)
        return []


def buscar_por_simbolo(db, simbolo):
    """La unidad que ya tenga ese simbolo, mirando sin distinguir forma."""
    objetivo = _comparable(simbolo)
    if not objetivo:
        return None
    for u in listar(db):
        if _comparable(u.get('Simbolo')) == objetivo:
            return u
    return None


def _codigo_libre(db, base):
    """
    Un codigo que no choque con otro ya usado.

    Un simbolo como '%' o ',' no deja ningun caracter util, asi que todos
    caerian en el mismo codigo. El que distingue la unidad es el simbolo; el
    codigo solo tiene que ser unico.
    """
    usados = set()
    for u in listar(db):
        usados.add(str(u.get('CodigoUnidad') or '').upper())
    if base not in usados:
        return base
    for n in range(2, 1000):
        candidato = '%s_%d' % (base[:45], n)
        if candidato not in usados:
            return candidato
    return base


def crear(db, simbolo, nombre='', tipo=TIPO_DEFECTO):
    """
    Da de alta una unidad.

    Devuelve (ok, mensaje, unidad). Si ya existe una equivalente NO la
    duplica: devuelve ok=False y la que habia, para que quien llama la
    seleccione en vez de crear una gemela.
    """
    simbolo = normalizar_simbolo(simbolo)
    if not simbolo:
        return False, 'Escriba el símbolo de la unidad.', None

    ya = buscar_por_simbolo(db, simbolo)
    if ya:
        return False, ('Esa unidad ya existe como «%s».' % ya.get('Simbolo')), ya

    nombre = ' '.join(str(nombre or '').split())[:LARGO_NOMBRE] or simbolo
    tipo = (str(tipo or '').strip() or TIPO_DEFECTO)[:50]
    codigo = _codigo_libre(db, normalizar_codigo(simbolo))

    def _esc(v):
        return str(v).replace("'", "''")

    try:
        db.execute(
            "INSERT INTO Unidades (CodigoUnidad, NombreUnidad, Simbolo, "
            "TipoUnidad, Activo) VALUES ('%s', '%s', '%s', '%s', True)"
            % (_esc(codigo), _esc(nombre), _esc(simbolo), _esc(tipo)))
    except Exception as e:
        _log.error("No se pudo crear la unidad '%s': %s", simbolo, e)
        return False, 'No se pudo guardar la unidad: %s' % e, None

    creada = buscar_por_simbolo(db, simbolo)
    _log.info("Unidad creada: %s (%s)", simbolo, codigo)
    return True, 'Unidad «%s» creada.' % simbolo, creada

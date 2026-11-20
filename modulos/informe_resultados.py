# -*- coding: utf-8 -*-
"""
================================================================================
QUE DICE EL INFORME DE RESULTADOS - UNA SOLA FUENTE
================================================================================
Habia dos codigos que respondian a la misma pregunta -que parametros salen en
el informe de una prueba, con que valor, unidad y rango de referencia- y no
respondian lo mismo:

  ANgesLAB.pyw        el informe que se imprime y se entrega. Resolvia bien:
                      orden por ParametrosPrueba.Secuencia, unidad por
                      Parametros.UnidadID y referencia por edad y sexo.
  envio_resultados.py el informe que el paciente abre desde el codigo QR.
                      Pedia columnas que no existen (ValorNumerico,
                      ValorTexto, ResultadosParametros.UnidadID), la consulta
                      fallaba entera y el PDF salia con el nombre de cada
                      prueba y ninguna cifra. Corregido el 20/11/2026, pero
                      quedaba como una segunda version que iba a separarse
                      otra vez.

Aqui vive la regla, una sola vez. Los dos informes la usan y el que la cambie
los cambia a los dos. El diseño de cada PDF sigue siendo suyo: uno va en papel
tamaño carta y el otro se lee en un telefono.

LA REGLA

  1. Los parametros son los de la prueba (ParametrosPrueba), en el orden de su
     Secuencia: es el orden en que el bioanalista los captura y en que el
     medico espera leerlos.
  2. Un parametro sin valor capturado no se imprime. Una fila en blanco en un
     informe se lee como un resultado.
  3. El valor es ResultadosParametros.Valor, uno solo, sea cifra o texto
     ('Muestra hemolizada' es un resultado tanto como 12.4).
  4. La unidad sale de Parametros.UnidadID -> Unidades.Simbolo.
  5. El rango de referencia, por este orden: la variante que corresponde a la
     edad y el sexo del paciente (valores_referencia), si no la del calculo
     automatico cuando el parametro es calculado (calculos_automaticos), si
     no lo que se guardo al capturar (ResultadosParametros.ValorReferencia),
     si no el valor base del parametro (Parametros.Observaciones). Un rango
     de adulto en el informe de un recien nacido no es un detalle de forma.
  5b. Si el parametro no tiene unidad asignada, se toma la que venga al final
     del texto del rango: "( 70 - 110 ) mg/dL" informa en mg/dL.
  6. Lo que quedo fuera de rango viene marcado (FueraDeRango), para que el
     informe lo señale. Un valor alto sin señalar se lee como normal.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import re
from datetime import datetime

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.informe')
except Exception:  # pragma: no cover - respaldo si falta el modulo
    import logging as _logging
    _log = _logging.getLogger('angeslab.informe')


def _texto(valor):
    return str(valor if valor is not None else '').strip()


def simbolos_de_unidad(db):
    """{UnidadID: simbolo}. Una consulta en vez de una por parametro."""
    tabla = {}
    try:
        for u in db.query("SELECT UnidadID, Simbolo FROM Unidades") or []:
            tabla[int(u['UnidadID'])] = _texto(u.get('Simbolo'))
    except Exception as e:
        _log.warning("No se pudieron leer las unidades: %s", e)
    return tabla


def parametros_de_prueba(db, prueba_id):
    """Los parametros que componen una prueba, en el orden del informe."""
    return db.query(f"""
        SELECT pp.ParametroID, pp.Secuencia,
               par.NombreParametro, par.UnidadID,
               par.Observaciones AS ValorRefBase, par.Seccion
        FROM ParametrosPrueba pp
        INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID
        WHERE pp.PruebaID = {int(prueba_id)}
        ORDER BY pp.Secuencia
    """) or []


def valores_capturados(db, detalle_id):
    """{ParametroID: fila} con lo que el bioanalista capturo de esa prueba."""
    filas = db.query(f"""
        SELECT ParametroID, Valor, ValorReferencia, FueraDeRango
        FROM ResultadosParametros
        WHERE DetalleID = {int(detalle_id)}
    """) or []
    return {int(f['ParametroID']): f for f in filas if f.get('ParametroID') is not None}


def _referencias(db, parametro_ids, sexo, fecha_nacimiento, gestor_ref):
    """
    La variante de rango que corresponde a la edad y el sexo del paciente.

    Sin fecha de nacimiento no hay edad que resolver y se devuelve vacio, que
    es lo que hacia el informe impreso: deja que decidan los pasos 5b y 5c de
    la regla.
    """
    if not fecha_nacimiento or not parametro_ids:
        return {}
    gestor = gestor_ref
    if gestor is None:
        try:
            from modulos.valores_referencia import GestorValoresReferencia
            gestor = GestorValoresReferencia(db)
        except Exception as e:
            _log.warning("Valores de referencia por edad y sexo no disponibles: %s", e)
            return {}
    try:
        return gestor.resolver_lote(parametro_ids, sexo, fecha_nacimiento) or {}
    except Exception as e:
        _log.warning("No se pudieron resolver los rangos por edad y sexo: %s", e)
        return {}


def _referencia_de_calculo(nombre_parametro, sexo, fecha_nacimiento):
    """
    El rango de un parametro calculado (VCM, HCM, indices), que no vive en la
    tabla de parametros sino en calculos_automaticos, con su propio ajuste
    por sexo y edad.
    """
    try:
        from modulos.calculos_automaticos import obtener_calculador
        calc = obtener_calculador()
        nombre = calc.normalizar_nombre(nombre_parametro or '')
        if not nombre:
            return ''
        edad = None
        if fecha_nacimiento:
            hoy = datetime.now()
            edad = (hoy.year - fecha_nacimiento.year
                    - ((hoy.month, hoy.day) < (fecha_nacimiento.month, fecha_nacimiento.day)))
        return _texto(calc.obtener_referencia_calculo(nombre, sexo, edad))
    except Exception as e:
        _log.warning("Referencia de calculo de %s no resuelta: %s", nombre_parametro, e)
        return ''


def unidad_del_texto(referencia):
    """
    La unidad que viene al final del texto de un rango, para los parametros
    que no tienen unidad asignada: "( 70 - 110 ) mg/dL" -> "mg/dL".
    """
    if not referencia:
        return ''
    m = re.search(
        r'[\d\)\s]'                        # despues de digito, cierre o espacio
        r'\s+'
        r'([a-zA-Zµμ%/\^°×x]'              # inicio de la unidad
        r'[a-zA-Z0-9µμ%/\^°×³⁶⁹·.\- ]*'
        r')$',
        referencia)
    return m.group(1).strip() if m else ''


def parametros_del_informe(db, detalle_id, prueba_id, sexo=None, fecha_nacimiento=None,
                           gestor_ref=None, unidades=None):
    """
    Lo que el informe dice de una prueba: una fila por parametro con valor.

    Cada fila: parametro_id, nombre, seccion, secuencia, valor, unidad,
    referencia, fuera_de_rango. El orden y el contenido son los de LA REGLA
    de la cabecera de este modulo.

    'unidades' es el diccionario de simbolos_de_unidad(); se pasa cuando se
    recorren varias pruebas de una misma solicitud, para no releerlo.
    """
    parametros = parametros_de_prueba(db, prueba_id)
    if not parametros:
        return []
    if unidades is None:
        unidades = simbolos_de_unidad(db)
    capturados = valores_capturados(db, detalle_id)

    con_valor = [p for p in parametros
                 if _texto(capturados.get(int(p['ParametroID']), {}).get('Valor'))]
    refs = _referencias(db, [int(p['ParametroID']) for p in con_valor],
                        sexo, fecha_nacimiento, gestor_ref)

    # Un valor capturado para un parametro que ya no pertenece a la prueba no
    # sale en el informe (el impreso tampoco lo saca). Que se vea en el log,
    # porque es un resultado que alguien escribio y nadie lee.
    sobrantes = set(capturados) - {int(p['ParametroID']) for p in parametros}
    if sobrantes:
        _log.warning("Detalle %s: %d resultado(s) capturados en parametros que ya no son "
                     "de la prueba %s: %s", detalle_id, len(sobrantes), prueba_id,
                     sorted(sobrantes))

    filas = []
    for p in con_valor:
        pid = int(p['ParametroID'])
        cap = capturados.get(pid, {})
        referencia = _texto(refs.get(pid))
        if not referencia:
            referencia = _referencia_de_calculo(p.get('NombreParametro'),
                                                sexo, fecha_nacimiento)
        if not referencia:
            referencia = _texto(cap.get('ValorReferencia'))
        if not referencia:
            referencia = _texto(p.get('ValorRefBase'))
        unidad = unidades.get(int(p['UnidadID'])) if p.get('UnidadID') else ''
        if not unidad:
            unidad = unidad_del_texto(referencia)
        filas.append({
            'parametro_id': pid,
            'nombre': _texto(p.get('NombreParametro')),
            'seccion': _texto(p.get('Seccion')),
            'secuencia': p.get('Secuencia'),
            'valor': _texto(cap.get('Valor')),
            'unidad': unidad,
            'referencia': referencia,
            'fuera_de_rango': bool(cap.get('FueraDeRango')),
        })
    return filas


def paciente_de_solicitud(db, solicitud_id):
    """
    Sexo y fecha de nacimiento del paciente de una solicitud, que es lo que
    hace falta para resolver los rangos de referencia.
    """
    fila = db.query_one(f"""
        SELECT p.Sexo, p.FechaNacimiento
        FROM Solicitudes s
        LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
        WHERE s.SolicitudID = {int(solicitud_id)}
    """)
    if not fila:
        return None, None
    return fila.get('Sexo'), fila.get('FechaNacimiento')

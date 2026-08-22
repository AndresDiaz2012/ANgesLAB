# -*- coding: utf-8 -*-
"""
================================================================================
ENVIO DE RESULTADOS A SEDES REMOTAS - ANgesLAB
================================================================================
Deja el PDF del informe en una carpeta sincronizada para que la sede que toma
las muestras lo imprima en papel.

Como funciona el circuito completo
-----------------------------------
    Sede A (procesa)                     Sede B (toma muestras)
    ----------------                     ----------------------
    valida el resultado
    pulsa «Enviar a sede»
        |                                 ANgesLAB Receptor vigilando
        v                                        |
    PDF a la carpeta  --- Drive/OneDrive --->  lo ve llegar
                                                 |
                                             imprime  ->  papel

La sede B no tiene ANgesLAB ni base de datos: solo el receptor, que unicamente
sabe imprimir. Por eso el resultado no se puede alterar de camino, y por eso
esto se hace con archivos y no dando acceso remoto a la base.

Por que es un boton y no automatico
------------------------------------
Porque no todos los pacientes vienen de la sede remota. El catalogo no tiene
campo de sede, asi que enviar automaticamente todo lo validado imprimiria en B
el trabajo entero del laboratorio. Quien atiende sabe de donde vino cada
paciente; el programa no. Cuando exista el campo de sede esto podra ser
automatico, y la funcion de envio no habra que reescribirla.

Por que se escribe con nombre temporal
---------------------------------------
El archivo se crea como .tmp y se renombra a .pdf al terminar. El renombrado es
atomico dentro del mismo disco, asi que el receptor nunca llega a ver un PDF a
medio escribir. Sin esto, con una carpeta sincronizada, saldrian hojas en
blanco o cortadas y nadie se enteraria.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import json
import logging
import os
import re
import shutil
import unicodedata
from datetime import datetime

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.envio_sede')
except Exception:
    _log = logging.getLogger('angeslab.envio_sede')
    _log.addHandler(logging.NullHandler())


# Columna donde se guardan las sedes, como lista JSON
COLUMNA_SEDES = 'SedesRemotas'


# ══════════════════════════════════════════════════════════════════════════
#  Configuracion de las sedes
# ══════════════════════════════════════════════════════════════════════════
def _asegurar_columna(db):
    """Crea la columna si la instalacion viene de una version anterior."""
    try:
        db.query_one(f"SELECT TOP 1 [{COLUMNA_SEDES}] FROM ConfiguracionLaboratorio")
        return True
    except Exception:
        try:
            db.execute(f"ALTER TABLE ConfiguracionLaboratorio ADD COLUMN [{COLUMNA_SEDES}] MEMO")
            _log.info("Columna %s creada", COLUMNA_SEDES)
            return True
        except Exception as e:
            _log.warning("No se pudo crear la columna %s: %s", COLUMNA_SEDES, e)
            return False


def listar_sedes(db):
    """
    Sedes configuradas: [{'nombre': str, 'carpeta': str}, ...].

    Nunca lanza: si la configuracion esta corrupta se devuelve vacia y el
    usuario la vuelve a poner, que es mejor que impedirle imprimir.
    """
    _asegurar_columna(db)
    try:
        fila = db.query_one("SELECT * FROM ConfiguracionLaboratorio") or {}
        crudo = fila.get(COLUMNA_SEDES)
    except Exception as e:
        _log.warning("No se pudo leer la configuracion de sedes: %s", e)
        return []

    if not crudo:
        return []
    try:
        datos = json.loads(crudo)
    except Exception as e:
        _log.warning("Configuracion de sedes ilegible: %s", e)
        return []

    salida = []
    for s in datos if isinstance(datos, list) else []:
        if not isinstance(s, dict):
            continue
        nombre = str(s.get('nombre') or '').strip()
        carpeta = str(s.get('carpeta') or '').strip()
        if nombre and carpeta:
            salida.append({'nombre': nombre, 'carpeta': carpeta})
    return salida


def guardar_sedes(db, sedes):
    """Persiste la lista de sedes. Devuelve True si se guardo."""
    if not _asegurar_columna(db):
        return False
    limpias = []
    for s in sedes or []:
        nombre = str(s.get('nombre') or '').strip()
        carpeta = str(s.get('carpeta') or '').strip()
        if nombre and carpeta:
            limpias.append({'nombre': nombre, 'carpeta': carpeta})
    texto = json.dumps(limpias, ensure_ascii=False)
    try:
        db.execute(
            f"UPDATE ConfiguracionLaboratorio SET [{COLUMNA_SEDES}] = "
            f"'{texto.replace(chr(39), chr(39) * 2)}'")
        return True
    except Exception as e:
        _log.error("No se pudieron guardar las sedes: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════════
#  Envio
# ══════════════════════════════════════════════════════════════════════════
def _limpiar(texto, largo=40):
    """
    Deja un texto utilizable como nombre de archivo en Windows.

    Se quitan los acentos a proposito: el nombre viaja por una carpeta
    sincronizada hasta otro equipo, que puede tener otra configuracion
    regional, y una tilde mal codificada convierte el archivo en ilocalizable.
    """
    t = unicodedata.normalize('NFKD', str(texto or ''))
    t = t.encode('ascii', 'ignore').decode('ascii')
    t = re.sub(r'[^A-Za-z0-9 _-]', '', t).strip()
    t = re.sub(r'\s+', '_', t)
    return t[:largo].upper() or 'SIN_DATO'


def nombre_de_archivo(numero_solicitud, paciente):
    """
    Nombre con el que el documento llega a la sede.

    Importa mas de lo que parece: es lo unico que ve quien recibe. Con el
    numero de solicitud y el apellido puede casar el papel con su paciente sin
    abrir el PDF.
    """
    return f"{_limpiar(numero_solicitud, 30)}_{_limpiar(paciente)}.pdf"


def enviar_a_sede(pdf_origen, sede, numero_solicitud='', paciente=''):
    """
    Copia el informe a la carpeta de la sede.

    Args:
        pdf_origen: ruta del PDF ya generado.
        sede: dict con 'nombre' y 'carpeta'.
        numero_solicitud, paciente: para componer el nombre del archivo.

    Returns dict:
        ok       - True si el archivo quedo completo en la carpeta
        destino  - ruta final
        error    - motivo cuando ok es False
    """
    salida = {'ok': False, 'destino': '', 'error': ''}

    if not pdf_origen or not os.path.exists(pdf_origen):
        salida['error'] = 'No se encontro el PDF del informe'
        return salida

    carpeta = (sede or {}).get('carpeta') or ''
    if not carpeta:
        salida['error'] = 'La sede no tiene carpeta configurada'
        return salida

    if not os.path.isdir(carpeta):
        # Caso corriente y con arreglo conocido: Drive todavia no ha montado la
        # unidad, o el equipo esta sin red. Conviene decirlo tal cual.
        salida['error'] = (f'No se puede acceder a la carpeta de la sede:\n{carpeta}\n\n'
                           'Compruebe que la carpeta sincronizada este disponible.')
        return salida

    nombre = nombre_de_archivo(numero_solicitud, paciente)
    destino = os.path.join(carpeta, nombre)

    # Si ya existe se conserva el anterior: puede ser una version previa del
    # informe que la sede ya imprimio, y sobrescribirla sin dejar rastro
    # impediria saber que se entrego primero.
    if os.path.exists(destino):
        marca = datetime.now().strftime('%Y%m%d_%H%M%S')
        destino = os.path.join(carpeta, f'{nombre[:-4]}_{marca}.pdf')

    temporal = destino + '.tmp'
    try:
        shutil.copyfile(pdf_origen, temporal)
        # El renombrado es atomico en el mismo disco: el receptor no llega a
        # ver nunca un PDF a medio escribir
        os.replace(temporal, destino)
    except Exception as e:
        try:
            if os.path.exists(temporal):
                os.remove(temporal)
        except Exception:
            pass
        salida['error'] = f'No se pudo copiar el informe: {e}'
        _log.error("Envio a sede '%s' fallido: %s", (sede or {}).get('nombre'), e)
        return salida

    salida.update({'ok': True, 'destino': destino})
    _log.info("Informe %s enviado a la sede '%s': %s",
              numero_solicitud, sede.get('nombre'), destino)
    return salida

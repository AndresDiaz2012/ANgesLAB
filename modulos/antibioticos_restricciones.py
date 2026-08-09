# -*- coding: utf-8 -*-
"""
RESTRICCIONES DE ANTIBIOTICOS POR EDAD Y CONDICION - ANgesLAB
=============================================================
Igual que los valores de referencia se ajustan a edad y sexo, los
antibioticos informados en un antibiograma no son aplicables por igual a
todos los pacientes: hay familias contraindicadas en niños, en recien
nacidos y en embarazadas.

Este modulo NO oculta resultados. El antibiograma se informa completo
—suprimir un resultado seria falsear el informe— y lo que se agrega es la
advertencia de aplicabilidad al lado de cada antibiotico, para que el
medico tratante decida.

Niveles de restriccion
----------------------
    seguro          sin restriccion conocida para esa condicion
    precaucion      utilizable valorando riesgo/beneficio
    evitar          preferir alternativa; usar solo si no hay opcion
    contraindicado  no debe emplearse en esa condicion

Base
----
Restricciones ampliamente aceptadas en la literatura clinica y en las
fichas tecnicas de los productos (toxicidad sobre cartilago de las
fluoroquinolonas, tincion dental de las tetraciclinas, sindrome gris del
cloranfenicol, ototoxicidad fetal de los aminoglucosidos, antagonismo del
folato de las sulfamidas, teratogenicidad de los azoles sistemicos).

IMPORTANTE: la informacion es ORIENTATIVA y no sustituye el criterio del
medico tratante, que decide segun el cuadro clinico, la gravedad, la
disponibilidad de alternativas y la relacion riesgo/beneficio.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import unicodedata
from datetime import datetime, date

# ---------------------------------------------------------------------------
# Niveles
# ---------------------------------------------------------------------------
SEGURO = 'seguro'
PRECAUCION = 'precaucion'
EVITAR = 'evitar'
CONTRAINDICADO = 'contraindicado'

# Orden de gravedad para quedarse con la restriccion mas fuerte
_GRAVEDAD = {SEGURO: 0, PRECAUCION: 1, EVITAR: 2, CONTRAINDICADO: 3}

# Marca que se imprime junto al antibiotico en el reporte
MARCA = {
    SEGURO: '',
    PRECAUCION: '*',
    EVITAR: '**',
    CONTRAINDICADO: '***',
}

ETIQUETA = {
    SEGURO: 'Sin restricción',
    PRECAUCION: 'Precaución',
    EVITAR: 'Evitar',
    CONTRAINDICADO: 'Contraindicado',
}

DIAS_ANIO = 365.25

# ---------------------------------------------------------------------------
# Catalogo
# ---------------------------------------------------------------------------
# Por antibiotico:
#   grupo      familia a la que pertenece
#   pediatria  {'nivel', 'edad_min_anios' o 'edad_min_dias', 'motivo'}
#              la restriccion aplica cuando el paciente es MENOR a esa edad
#   embarazo   {'nivel', 'motivo'}
# Un antibiotico ausente del catalogo se informa sin advertencia.
RESTRICCIONES = {
    # ---- Fluoroquinolonas -------------------------------------------------
    'CIPROFLOXACINA': {
        'grupo': 'Fluoroquinolonas',
        'pediatria': {'nivel': EVITAR, 'edad_min_anios': 18,
                      'motivo': 'Toxicidad sobre cartílago de crecimiento y tendón'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Artropatía fetal descrita en modelos animales'},
    },
    'LEVOFLOXACINA': {
        'grupo': 'Fluoroquinolonas',
        'pediatria': {'nivel': EVITAR, 'edad_min_anios': 18,
                      'motivo': 'Toxicidad sobre cartílago de crecimiento y tendón'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Artropatía fetal descrita en modelos animales'},
    },
    'MOXIFLOXACINA': {
        'grupo': 'Fluoroquinolonas',
        'pediatria': {'nivel': EVITAR, 'edad_min_anios': 18,
                      'motivo': 'Toxicidad sobre cartílago de crecimiento y tendón'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Artropatía fetal descrita en modelos animales'},
    },
    'NORFLOXACINA': {
        'grupo': 'Fluoroquinolonas',
        'pediatria': {'nivel': EVITAR, 'edad_min_anios': 18,
                      'motivo': 'Toxicidad sobre cartílago de crecimiento y tendón'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Artropatía fetal descrita en modelos animales'},
    },

    # ---- Tetraciclinas ----------------------------------------------------
    'TETRACICLINA': {
        'grupo': 'Tetraciclinas',
        'pediatria': {'nivel': CONTRAINDICADO, 'edad_min_anios': 8,
                      'motivo': 'Tinción dental permanente e hipoplasia del esmalte'},
        'embarazo': {'nivel': CONTRAINDICADO,
                     'motivo': 'Afecta dentadura y hueso fetal; hepatotoxicidad materna'},
    },
    'DOXICICLINA': {
        'grupo': 'Tetraciclinas',
        'pediatria': {'nivel': CONTRAINDICADO, 'edad_min_anios': 8,
                      'motivo': 'Tinción dental permanente e hipoplasia del esmalte'},
        'embarazo': {'nivel': CONTRAINDICADO,
                     'motivo': 'Afecta dentadura y hueso fetal'},
    },
    'TIGECICLINA': {
        'grupo': 'Glicilciclinas',
        'pediatria': {'nivel': CONTRAINDICADO, 'edad_min_anios': 18,
                      'motivo': 'No autorizada en menores; efectos de clase tetraciclina'},
        'embarazo': {'nivel': CONTRAINDICADO,
                     'motivo': 'Efectos de clase tetraciclina sobre hueso y dentadura fetal'},
    },

    # ---- Aminoglucosidos --------------------------------------------------
    'GENTAMICINA': {
        'grupo': 'Aminoglucosidos',
        'pediatria': {'nivel': PRECAUCION, 'edad_min_anios': 18,
                      'motivo': 'Requiere ajuste de dosis y control de función renal'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Ototoxicidad y nefrotoxicidad fetal'},
    },
    'AMIKACINA': {
        'grupo': 'Aminoglucosidos',
        'pediatria': {'nivel': PRECAUCION, 'edad_min_anios': 18,
                      'motivo': 'Requiere ajuste de dosis y control de función renal'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Ototoxicidad y nefrotoxicidad fetal'},
    },
    'TOBRAMICINA': {
        'grupo': 'Aminoglucosidos',
        'pediatria': {'nivel': PRECAUCION, 'edad_min_anios': 18,
                      'motivo': 'Requiere ajuste de dosis y control de función renal'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Ototoxicidad y nefrotoxicidad fetal'},
    },

    # ---- Sulfamidas y afines ---------------------------------------------
    'TRIMETOPRIM/SULFAMETOXAZOL': {
        'grupo': 'Sulfamidas',
        'pediatria': {'nivel': CONTRAINDICADO, 'edad_min_dias': 60,
                      'motivo': 'Riesgo de kernícterus en el lactante menor de 2 meses'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Antagonista del folato en el 1er trimestre; kernícterus a término'},
    },

    # ---- Fenicoles --------------------------------------------------------
    'CLORANFENICOL': {
        'grupo': 'Fenicoles',
        'pediatria': {'nivel': CONTRAINDICADO, 'edad_min_dias': 30,
                      'motivo': 'Síndrome gris del recién nacido'},
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Síndrome gris si el parto es próximo; aplasia medular'},
    },

    # ---- Nitrofuranos -----------------------------------------------------
    'NITROFURANTOINA': {
        'grupo': 'Nitrofuranos',
        'pediatria': {'nivel': CONTRAINDICADO, 'edad_min_dias': 30,
                      'motivo': 'Anemia hemolítica por inmadurez enzimática'},
        'embarazo': {'nivel': PRECAUCION,
                     'motivo': 'Evitar a término (38-42 sem) por hemólisis neonatal'},
    },

    # ---- Macrolidos -------------------------------------------------------
    'CLARITROMICINA': {
        'grupo': 'Macrolidos',
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Embriotoxicidad en modelos animales'},
    },

    # ---- Nitroimidazoles --------------------------------------------------
    'METRONIDAZOL': {
        'grupo': 'Nitroimidazoles',
        'embarazo': {'nivel': PRECAUCION,
                     'motivo': 'Evitar en el 1er trimestre'},
    },

    # ---- Oxazolidinonas y lipopeptidos -----------------------------------
    'LINEZOLID': {
        'grupo': 'Oxazolidinonas',
        'embarazo': {'nivel': PRECAUCION, 'motivo': 'Datos clínicos limitados'},
    },
    'DAPTOMICINA': {
        'grupo': 'Lipopeptidos',
        'embarazo': {'nivel': PRECAUCION, 'motivo': 'Datos clínicos limitados'},
    },

    # ---- Glucopeptidos ----------------------------------------------------
    'VANCOMICINA': {
        'grupo': 'Glucopeptidos',
        'embarazo': {'nivel': PRECAUCION,
                     'motivo': 'Vigilar función renal y auditiva'},
    },
    'TEICOPLANINA': {
        'grupo': 'Glucopeptidos',
        'embarazo': {'nivel': PRECAUCION, 'motivo': 'Datos clínicos limitados'},
    },

    # ---- Polimixinas ------------------------------------------------------
    'COLISTINA': {
        'grupo': 'Polimixinas',
        'pediatria': {'nivel': PRECAUCION, 'edad_min_anios': 18,
                      'motivo': 'Nefrotoxicidad; reservar a multirresistentes'},
        'embarazo': {'nivel': PRECAUCION, 'motivo': 'Datos clínicos limitados'},
    },

    # ---- Rifamicinas ------------------------------------------------------
    'RIFAMPICINA': {
        'grupo': 'Rifamicinas',
        'embarazo': {'nivel': PRECAUCION,
                     'motivo': 'Riesgo de hemorragia neonatal en el 3er trimestre'},
    },

    # ---- Antifungicos -----------------------------------------------------
    'FLUCONAZOL': {
        'grupo': 'Azoles',
        'embarazo': {'nivel': EVITAR,
                     'motivo': 'Teratogénico a dosis altas o tratamiento prolongado'},
    },
    'ITRACONAZOL': {
        'grupo': 'Azoles',
        'embarazo': {'nivel': CONTRAINDICADO, 'motivo': 'Teratogénico'},
    },
    'VORICONAZOL': {
        'grupo': 'Azoles',
        'embarazo': {'nivel': CONTRAINDICADO, 'motivo': 'Teratogénico'},
    },
    'FLUCITOSINA': {
        'grupo': 'Antimetabolitos',
        'embarazo': {'nivel': CONTRAINDICADO, 'motivo': 'Teratogénico'},
    },
}

# Palabras que, en el diagnostico u observaciones, indican gestacion
_CLAVES_EMBARAZO = (
    'EMBARAZ', 'GESTAN', 'GESTACION', 'GRAVIDEZ', 'PRENATAL',
    'SEMANAS DE GESTACION', 'PRIMIGESTA', 'MULTIGESTA', 'PUERPER',
)
_CLAVES_NO_EMBARAZO = ('NO EMBARAZ', 'DESCARTAR EMBARAZ', 'SIN EMBARAZ')


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def _norm(texto):
    """Mayusculas, sin acentos y sin espacios sobrantes."""
    t = ' '.join(str(texto or '').strip().split()).upper()
    return ''.join(c for c in unicodedata.normalize('NFD', t)
                   if unicodedata.category(c) != 'Mn')


def _edad_dias(fecha_nacimiento, referencia=None):
    """Edad en dias. Acepta datetime, date, pywintypes o texto."""
    if not fecha_nacimiento:
        return None
    fn = fecha_nacimiento
    if isinstance(fn, str):
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
            try:
                fn = datetime.strptime(fn[:10], fmt)
                break
            except ValueError:
                continue
        else:
            return None
    try:
        if isinstance(fn, datetime):
            fn = fn.date()
        elif not isinstance(fn, date):
            fn = date(fn.year, fn.month, fn.day)
        hoy = referencia or date.today()
        if isinstance(hoy, datetime):
            hoy = hoy.date()
        dias = (hoy - fn).days
        return dias if dias >= 0 else None
    except Exception:
        return None


def detectar_embarazo(*textos):
    """Busca indicios de gestacion en el diagnostico u observaciones.

    Es una ayuda, no un dato clinico: el sistema no tiene campo de
    gestacion. Devuelve True solo ante una mencion afirmativa.
    """
    for texto in textos:
        t = _norm(texto)
        if not t:
            continue
        if any(neg in t for neg in _CLAVES_NO_EMBARAZO):
            continue
        if any(clave in t for clave in _CLAVES_EMBARAZO):
            return True
    return False


def _buscar_ficha(nombre):
    """Localiza la ficha del antibiotico tolerando variantes de escritura."""
    n = _norm(nombre)
    if not n:
        return None
    if n in RESTRICCIONES:
        return RESTRICCIONES[n]
    # Coincidencia por prefijo: 'CIPROFLOXACINA 5 MCG' -> 'CIPROFLOXACINA'
    for clave, ficha in RESTRICCIONES.items():
        if n.startswith(clave) or clave in n:
            return ficha
    return None


# ---------------------------------------------------------------------------
# Evaluacion
# ---------------------------------------------------------------------------
def evaluar_antibiotico(nombre, fecha_nacimiento=None, sexo=None,
                        embarazada=False, edad_dias=None):
    """Evalua la aplicabilidad de un antibiotico a un paciente concreto.

    Devuelve dict con:
        nombre, grupo, nivel, marca, motivos (lista), aplica_pediatria,
        aplica_embarazo
    """
    ficha = _buscar_ficha(nombre)
    resultado = {
        'nombre': nombre,
        'grupo': (ficha or {}).get('grupo', ''),
        'nivel': SEGURO,
        'marca': '',
        'motivos': [],
        'aplica_pediatria': False,
        'aplica_embarazo': False,
    }
    if not ficha:
        return resultado

    if edad_dias is None:
        edad_dias = _edad_dias(fecha_nacimiento)

    # --- Restriccion pediatrica ------------------------------------------
    ped = ficha.get('pediatria')
    if ped and edad_dias is not None:
        limite = ped.get('edad_min_dias')
        if limite is None and ped.get('edad_min_anios') is not None:
            limite = ped['edad_min_anios'] * DIAS_ANIO
        if limite is not None and edad_dias < limite:
            resultado['nivel'] = ped['nivel']
            resultado['aplica_pediatria'] = True
            resultado['motivos'].append(
                f"{_texto_edad(ped)}: {ped['motivo']}")

    # --- Restriccion en gestacion ----------------------------------------
    emb = ficha.get('embarazo')
    if emb and embarazada:
        if _GRAVEDAD[emb['nivel']] > _GRAVEDAD[resultado['nivel']]:
            resultado['nivel'] = emb['nivel']
        resultado['aplica_embarazo'] = True
        resultado['motivos'].append(f"Gestación: {emb['motivo']}")

    resultado['marca'] = MARCA[resultado['nivel']]
    return resultado


def _texto_edad(ped):
    """Describe el limite de edad de una restriccion pediatrica."""
    if ped.get('edad_min_dias') is not None:
        dias = ped['edad_min_dias']
        if dias < 32:
            return f"Menor de {dias} días"
        return f"Menor de {int(round(dias / 30.0))} meses"
    return f"Menor de {ped.get('edad_min_anios')} años"


def evaluar_lista(nombres, fecha_nacimiento=None, sexo=None, embarazada=False):
    """Evalua varios antibioticos. Devuelve lista de dicts."""
    edad = _edad_dias(fecha_nacimiento)
    return [evaluar_antibiotico(n, sexo=sexo, embarazada=embarazada,
                                edad_dias=edad)
            for n in nombres]


def hay_restricciones(evaluaciones):
    """True si alguna evaluacion trae restriccion."""
    return any(e['nivel'] != SEGURO for e in evaluaciones)


def resumen_paciente(fecha_nacimiento=None, embarazada=False):
    """Frase que explica por que se aplican las advertencias."""
    partes = []
    edad = _edad_dias(fecha_nacimiento)
    if edad is not None:
        anios = edad / DIAS_ANIO
        if edad < 30:
            partes.append(f"recién nacido ({edad} días)")
        elif anios < 1:
            partes.append(f"lactante ({int(edad / 30.0)} meses)")
        elif anios < 18:
            partes.append(f"paciente pediátrico ({int(anios)} años)")
    if embarazada:
        partes.append('gestación')
    return ' / '.join(partes)


LEYENDA = [
    (PRECAUCION, 'Utilizable valorando riesgo/beneficio'),
    (EVITAR, 'Preferir alternativa'),
    (CONTRAINDICADO, 'No debe emplearse en este paciente'),
]

DESCARGO = (
    'Las advertencias de aplicabilidad son ORIENTATIVAS y se basan en la edad '
    'del paciente y en la condición registrada en la solicitud. No sustituyen '
    'el criterio del médico tratante, que decide según el cuadro clínico, la '
    'gravedad y las alternativas disponibles.'
)

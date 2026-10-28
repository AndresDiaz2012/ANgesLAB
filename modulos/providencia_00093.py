# -*- coding: utf-8 -*-
"""
================================================================================
PROVIDENCIA SNAT/2026/00093 - REQUISITOS DE CONTENIDO DE LA FACTURA
================================================================================
Lo que la factura tiene que DECIR segun la providencia vigente, en un solo
sitio.

    Providencia Administrativa SNAT/2026/00093
    Gaceta Oficial N° 43.484 del 21 de octubre de 2026
    Entra en vigor el 19 de abril de 2027 (180 dias continuos)

Deroga la SNAT/2011/0071, sobre la que estaba escrito este modulo de
facturacion, y la SNAT/2024/000102.

POR QUE UN MODULO APARTE

Porque el formato de una fecha en una factura no es una decision de
programacion: es un requisito legal con un articulo detras. Repartido por el
codigo, el dia que cambie la norma hay que buscarlo en seis sitios y alguno
se queda sin cambiar. Aqui, cada constante lleva al lado el articulo que la
exige, y quien audite puede comprobarlo sin leer el resto del programa.

QUE CUBRE ESTE MODULO Y QUE NO

Cubre el CONTENIDO del documento: que datos lleva y con que formato. Eso se
puede programar y comprobar aqui mismo.

NO cubre la emision digital en si. La providencia obliga a emitir a traves
del portal o la app del SENIAT, de una imprenta digital autorizada o de un
proveedor tecnologico, y eso exige integrarse con esa plataforma. A la fecha
de escribir esto su API no esta publicada, asi que no hay contra que
programar. Cuando exista, lo que hay aqui sigue valiendo: son los datos que
esa plataforma va a pedir.

ADVERTENCIA SOBRE LAS FUENTES

Los requisitos de este modulo se tomaron de resumenes profesionales de la
providencia, no del texto de la Gaceta. Lo que esta aqui se corresponde con
lo que esas fuentes citan del articulo 8, pero antes de dar por buena una
factura conviene que un contador contraste el texto oficial. Donde la
redaccion exacta no consta -la leyenda del articulo 19- se deja
configurable en vez de inventarla.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from decimal import Decimal

# ══════════════════════════════════════════════════════════════════════════
#  Identificacion de la norma
# ══════════════════════════════════════════════════════════════════════════
PROVIDENCIA = 'SNAT/2026/00093'
GACETA = 'N° 43.484'
FECHA_GACETA = '21/10/2026'
ENTRADA_EN_VIGOR = '19/04/2027'

DEROGA = ('SNAT/2011/0071', 'SNAT/2024/000102')


# ══════════════════════════════════════════════════════════════════════════
#  Articulo 8 - Formato de fecha y hora
# ══════════════════════════════════════════════════════════════════════════
# La fecha va en ocho digitos y la hora con segundos y marca de a.m./p.m.
# La hora es nueva: la providencia derogada solo pedia la fecha, y de ahi
# que el programa viniera imprimiendo horas sin segundos.
def fecha_fiscal(valor):
    """La fecha en los ocho digitos que pide el articulo 8: DDMMAAAA."""
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d%m%Y')
    return ''


def hora_fiscal(valor):
    """
    La hora con segundos y a.m./p.m.: HH.MM.SS a.m.

    Con puntos y no con dos puntos porque asi la citan las fuentes
    (HH.MM.SS). En minusculas y con puntos, como se escribe en castellano.
    """
    if not hasattr(valor, 'strftime'):
        return ''
    marca = 'a.m.' if valor.hour < 12 else 'p.m.'
    return '%s %s' % (valor.strftime('%I.%M.%S'), marca)


def fecha_hora_fiscal(valor):
    """Las dos juntas, como van impresas en la factura."""
    f, h = fecha_fiscal(valor), hora_fiscal(valor)
    return ('%s  %s' % (f, h)).strip()


# ══════════════════════════════════════════════════════════════════════════
#  Articulo 8.7 - Renglones exentos, exonerados o no gravados
# ══════════════════════════════════════════════════════════════════════════
# Se marcan con (E). Antes se usaba una columna con G o E; la providencia
# pide la marca entre parentesis.
MARCA_EXENTO = '(E)'
MARCA_GRAVADO = ''


def marca_gravamen(exento):
    return MARCA_EXENTO if exento else MARCA_GRAVADO


# ══════════════════════════════════════════════════════════════════════════
#  Articulo 8 (paragrafo unico) y articulo 19 - Leyendas obligatorias
# ══════════════════════════════════════════════════════════════════════════
# El contribuyente formal del IVA tiene que decirlo en la factura.
LEYENDA_CONTRIBUYENTE_FORMAL = 'Contribuyentes Formales del IVA'

# El articulo 19 exige que la factura indique que se emite conforme a esta
# providencia. La redaccion EXACTA no consta en las fuentes consultadas, asi
# que no se inventa: se deja un texto por defecto que dice el hecho, y la
# configuracion del laboratorio puede sustituirlo por el literal que indique
# el contador. Inventar aqui una formula legal seria peor que dejarla a la
# vista para que alguien la corrija.
LEYENDA_EMISION_DEFECTO = (
    'Documento emitido conforme a la Providencia Administrativa %s, '
    'Gaceta Oficial %s.' % (PROVIDENCIA, GACETA))

# Clave en ConfiguracionLaboratorio donde se guarda el literal definitivo
CAMPO_LEYENDA = 'LeyendaProvidencia'


def leyenda_emision(config_lab=None):
    """El literal del articulo 19: el configurado, o el provisional."""
    texto = (config_lab or {}).get(CAMPO_LEYENDA)
    texto = str(texto or '').strip()
    return texto or LEYENDA_EMISION_DEFECTO


def es_contribuyente_formal(config_lab=None):
    tipo = str((config_lab or {}).get('TipoContribuyente') or '').lower()
    return 'formal' in tipo


# ══════════════════════════════════════════════════════════════════════════
#  Articulo 8.9 y 8.10 - Base imponible e IVA POR ALICUOTA
# ══════════════════════════════════════════════════════════════════════════
def _d(valor):
    try:
        return Decimal(str(valor if valor is not None else 0))
    except Exception:
        return Decimal('0')


def desglose_por_alicuota(detalles, tasa_por_defecto=None):
    """
    Agrupa las lineas por alicuota, que es como la factura debe mostrarlas.

    La providencia pide la base imponible de CADA alicuota con su porcentaje
    y el IVA de cada una por separado. El programa venia guardando una sola
    tasa por factura, lo que bastaba mientras todo se facturara al 16%; con
    una exenta y una gravada en el mismo documento, el total salia bien pero
    el desglose no se podia reconstruir.

    Cada linea aporta su propia tasa si la trae (TasaIVA); si no, se le
    aplica la de la factura, que es como estaban guardadas las anteriores.

    Devuelve una lista de dicts ordenada por tasa:
        {'tasa': Decimal, 'base': Decimal, 'iva': Decimal, 'exento': bool}
    """
    grupos = {}
    for d in detalles or []:
        exento = bool(d.get('Exonerada'))
        if exento:
            tasa = Decimal('0')
        elif d.get('TasaIVA') is not None:
            tasa = _d(d.get('TasaIVA'))
        else:
            tasa = _d(tasa_por_defecto)

        base = _d(d.get('SubTotal'))
        iva = _d(d.get('MontoIVA'))
        # Sin IVA guardado se calcula: las lineas viejas no lo traen por linea
        if not iva and tasa and not exento:
            iva = (base * tasa / Decimal('100')).quantize(Decimal('0.01'))

        clave = (exento, tasa)
        g = grupos.setdefault(clave, {'tasa': tasa, 'base': Decimal('0'),
                                      'iva': Decimal('0'), 'exento': exento})
        g['base'] += base
        g['iva'] += iva

    # Lo exento primero y luego por tasa, que es como se lee un desglose
    return sorted(grupos.values(), key=lambda g: (not g['exento'], g['tasa']))


def etiqueta_alicuota(grupo):
    """Como se rotula cada renglon del desglose en el papel."""
    if grupo.get('exento') or not grupo.get('tasa'):
        return 'Exento / exonerado / no gravado'
    return 'Base imponible %s%%' % _fmt_pct(grupo['tasa'])


def _fmt_pct(tasa):
    t = _d(tasa)
    entero = t.quantize(Decimal('1')) == t
    return ('%d' % t) if entero else ('%.2f' % t)

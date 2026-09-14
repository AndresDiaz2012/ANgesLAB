# -*- coding: utf-8 -*-
"""
================================================================================
COMPARAR CATALOGOS DE DOS BASES - ANgesLAB
================================================================================
Dice exactamente en que se diferencian el catalogo de dos bases de datos.

Para que sirve
--------------
Cuando alguien trabaja el catalogo en un equipo (corrige valores normales,
mueve pruebas de area, arregla parametros) y esos arreglos hay que llevarlos a
la base principal, lo primero es SABER que cambio. Copiar una base encima de la
otra es la forma rapida de perder pacientes, resultados o facturacion.

Este script no modifica nada. Solo lee y compara.

Uso
---
    python scripts/comparar_catalogos.py  base_principal.accdb  base_de_ella.accdb

Que hace primero
----------------
Antes del catalogo cuenta los datos OPERATIVOS de cada base (pacientes,
solicitudes, resultados, facturas). Eso es lo que decide la estrategia: la base
que tiene el trabajo real del laboratorio es la que manda, y la otra aporta
solo su catalogo.

Como compara
------------
Por codigo de negocio, NO por identificador. Los identificadores son
autonumericos y en dos bases que llevan meses separadas ya no significan lo
mismo: la prueba 412 de una puede ser otra distinta en la otra. Compararlas por
identificador daria un informe lleno de diferencias falsas.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import os
import sys


# --- Tablas operativas: sirven para saber cual base es la que se usa ---------
TABLAS_OPERATIVAS = [
    'Pacientes', 'Solicitudes', 'DetalleSolicitudes', 'Resultados',
    'ResultadosParametros', 'Facturas', 'Recibos', 'Cotizaciones',
    'MovimientosCaja',
]

# --- Catalogo: (tabla, SQL, clave de negocio, columnas a comparar) ----------
# La clave es lo que identifica la misma fila en las dos bases.
#
# Ojo con las columnas que terminan en ID: son autonumericos y NO significan lo
# mismo en dos bases distintas. El area 7 de una puede ser otra en la otra, y
# compararlas daria "cambio de area" en cientos de pruebas que nadie movio. Por
# eso el SQL las traduce a su codigo (_Area, _TipoMuestra, _Unidad) y lo que se
# compara es eso.
CATALOGO = [
    ('Areas',
     'SELECT * FROM Areas',
     ('CodigoArea',),
     ['NombreArea', 'Descripcion', 'Secuencia', 'Activo']),

    ('Pruebas',
     'SELECT p.*, a.CodigoArea AS _Area, tm.CodigoTipoMuestra AS _TipoMuestra '
     'FROM ((Pruebas p LEFT JOIN Areas a ON p.AreaID = a.AreaID) '
     'LEFT JOIN TiposMuestra tm ON p.TipoMuestraID = tm.TipoMuestraID)',
     ('CodigoPrueba',),
     ['NombrePrueba', 'NombreCorto', '_Area', 'Precio', 'Activo',
      '_TipoMuestra', 'TuboRecomendado', 'RequiereAyuno', 'HorasAyuno',
      'Metodologia', 'ValorReferencia', 'UnidadMedida']),

    ('Parametros',
     'SELECT pa.*, u.CodigoUnidad AS _Unidad '
     'FROM (Parametros pa LEFT JOIN Unidades u ON pa.UnidadID = u.UnidadID)',
     ('CodigoParametro',),
     ['NombreParametro', 'NombreCorto', '_Unidad', 'TipoResultado',
      'ValorMinimo', 'ValorMaximo', 'Decimales', 'Observaciones',
      'Seccion', 'Activo']),

    ('Unidades',
     'SELECT * FROM Unidades',
     ('CodigoUnidad',),
     ['NombreUnidad', 'Simbolo', 'TipoUnidad', 'Activo']),

    ('Perfiles',
     'SELECT * FROM Perfiles',
     ('CodigoPerfil',),
     ['NombrePerfil', 'Descripcion', 'Activo']),

    # Los valores normales son lo que mas cuesta rehacer a mano, y lo que mas
    # dano hace si se pierde: van por parametro, sexo y tramo de edad.
    ('ValoresReferencia',
     'SELECT v.*, pa.CodigoParametro AS _Param '
     'FROM (ValoresReferencia v INNER JOIN Parametros pa '
     'ON v.ParametroID = pa.ParametroID)',
     ('_Param', 'SexoAplica', 'EdadMinima', 'EdadMaxima'),
     ['ValorMinimo', 'ValorMaximo', 'ValorTexto', 'Interpretacion']),
]

# Tablas de union: se comparan como conjuntos de pares de codigos, porque sus
# identificadores propios no significan nada fuera de su base.
UNIONES = [
    ('ParametrosPrueba', 'Pruebas', 'PruebaID', 'CodigoPrueba',
     'Parametros', 'ParametroID', 'CodigoParametro'),
    ('PruebasEnPerfil', 'Perfiles', 'PerfilID', 'CodigoPerfil',
     'Pruebas', 'PruebaID', 'CodigoPrueba'),
]


def conectar(ruta):
    import win32com.client
    cn = win32com.client.Dispatch('ADODB.Connection')
    cn.Open(f'Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta};')
    return cn


def consultar(cn, sql):
    """Filas como lista de diccionarios. Devuelve None si la tabla no existe."""
    try:
        rs = cn.Execute(sql)[0]
    except Exception:
        return None
    filas = []
    try:
        cols = [rs.Fields(i).Name for i in range(rs.Fields.Count)]
        while not rs.EOF:
            filas.append({c: rs.Fields(c).Value for c in cols})
            rs.MoveNext()
    finally:
        try:
            rs.Close()
        except Exception:
            pass
    return filas


def contar(cn, tabla):
    filas = consultar(cn, f'SELECT COUNT(*) AS n FROM [{tabla}]')
    if filas is None:
        return None
    return filas[0]['n']


def columnas_de(cn, tabla):
    try:
        rs = cn.Execute(f'SELECT TOP 1 * FROM [{tabla}]')[0]
        cols = {rs.Fields(i).Name for i in range(rs.Fields.Count)}
        rs.Close()
        return cols
    except Exception:
        return set()


def normalizar(v):
    """
    Para comparar sin ruido.

    Un texto con espacios de sobra o un None frente a cadena vacia no son un
    cambio real, y si aparecen como tales el informe se llena de falsos
    positivos que hacen que nadie lo lea entero.
    """
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'S' if v else 'N'
    if isinstance(v, (int, float)):
        f = float(v)
        return str(int(f)) if f == int(f) else f'{f:.6g}'
    return ' '.join(str(v).split()).strip().upper()


def clave_de(fila, claves):
    return tuple(normalizar(fila.get(k)) for k in claves)


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------
def titulo(txt):
    print()
    print('=' * 78)
    print('  ' + txt)
    print('=' * 78)


def comparar_operativo(cn_a, cn_b, nom_a, nom_b):
    titulo('DATOS OPERATIVOS  -  cual base tiene el trabajo real')
    print(f'  {"tabla":<24} {nom_a:>14} {nom_b:>14}')
    print('  ' + '-' * 54)
    total_a = total_b = 0
    for t in TABLAS_OPERATIVAS:
        a, b = contar(cn_a, t), contar(cn_b, t)
        if a is None and b is None:
            continue
        a = a or 0
        b = b or 0
        total_a += a
        total_b += b
        marca = '   <--' if (a or b) and a != b else ''
        print(f'  {t:<24} {a:>14,} {b:>14,}{marca}')
    print('  ' + '-' * 54)
    print(f'  {"TOTAL":<24} {total_a:>14,} {total_b:>14,}')
    print()
    if total_a and not total_b:
        print(f'  -> El trabajo real esta en {nom_a}. Debe mandar esa, y tomar')
        print(f'     de {nom_b} solo el catalogo.')
    elif total_b and not total_a:
        print(f'  -> El trabajo real esta en {nom_b}. Lo mas probable es que esa')
        print(f'     deba pasar a ser la principal, sin mas.')
    elif total_a and total_b:
        print('  -> CUIDADO: las DOS tienen datos operativos. Se han usado en')
        print('     paralelo, y unirlas no es copiar un catalogo: hay que decidir')
        print('     que se hace con los pacientes y las facturas de cada una.')
    else:
        print('  -> Ninguna tiene datos operativos: son bases de catalogo.')
    return total_a, total_b


def comparar_tabla(cn_a, cn_b, tabla, sql, claves, campos, nom_a, nom_b):
    filas_a = consultar(cn_a, sql)
    filas_b = consultar(cn_b, sql)
    if filas_a is None or filas_b is None:
        print(f'\n  [{tabla}] no existe en una de las dos bases; se omite')
        return None

    # Solo se comparan los campos que existen en AMBAS: una base mas antigua
    # puede no tener columnas anadidas despues
    comunes = (columnas_de(cn_a, tabla) & columnas_de(cn_b, tabla))
    campos = [c for c in campos
              if c.startswith('_') or c in comunes]

    idx_a = {clave_de(f, claves): f for f in filas_a}
    idx_b = {clave_de(f, claves): f for f in filas_b}

    solo_b = sorted(set(idx_b) - set(idx_a))
    solo_a = sorted(set(idx_a) - set(idx_b))
    cambiados = []
    for k in sorted(set(idx_a) & set(idx_b)):
        difs = []
        for c in campos:
            va, vb = normalizar(idx_a[k].get(c)), normalizar(idx_b[k].get(c))
            if va != vb:
                difs.append((c, idx_a[k].get(c), idx_b[k].get(c)))
        if difs:
            cambiados.append((k, difs))

    print()
    print(f'  {tabla}:  {len(filas_a)} en {nom_a}  |  {len(filas_b)} en {nom_b}')
    print(f'     solo en {nom_b} (nuevas): {len(solo_b)}')
    print(f'     solo en {nom_a} (faltan en la otra): {len(solo_a)}')
    print(f'     con diferencias: {len(cambiados)}')

    return {'tabla': tabla, 'solo_b': solo_b, 'solo_a': solo_a,
            'cambiados': cambiados, 'idx_a': idx_a, 'idx_b': idx_b}


def detallar(resultado, nom_a, nom_b, limite=25):
    if not resultado:
        return
    t = resultado['tabla']
    if resultado['solo_b']:
        print(f'\n  --- {t}: solo en {nom_b} (habria que crearlas) ---')
        for k in resultado['solo_b'][:limite]:
            fila = resultado['idx_b'][k]
            desc = fila.get('NombrePrueba') or fila.get('NombreParametro') \
                or fila.get('NombreArea') or fila.get('NombrePerfil') \
                or fila.get('NombreUnidad') or ''
            print(f'      {"|".join(k):<28} {desc}')
        if len(resultado['solo_b']) > limite:
            print(f'      ... y {len(resultado["solo_b"]) - limite} mas')

    if resultado['solo_a']:
        print(f'\n  --- {t}: solo en {nom_a} (ella no las tiene) ---')
        for k in resultado['solo_a'][:limite]:
            fila = resultado['idx_a'][k]
            desc = fila.get('NombrePrueba') or fila.get('NombreParametro') \
                or fila.get('NombreArea') or fila.get('NombrePerfil') \
                or fila.get('NombreUnidad') or ''
            print(f'      {"|".join(k):<28} {desc}')
        if len(resultado['solo_a']) > limite:
            print(f'      ... y {len(resultado["solo_a"]) - limite} mas')

    if resultado['cambiados']:
        print(f'\n  --- {t}: diferencias campo a campo ---')
        for k, difs in resultado['cambiados'][:limite]:
            print(f'      {"|".join(k)}')
            for campo, va, vb in difs:
                print(f'          {campo:<22} {nom_a}: {str(va)[:28]:<30} {nom_b}: {str(vb)[:28]}')
        if len(resultado['cambiados']) > limite:
            print(f'      ... y {len(resultado["cambiados"]) - limite} mas')


def comparar_union(cn_a, cn_b, tabla, t1, c1, k1, t2, c2, k2, nom_a, nom_b):
    """
    Compara una tabla de union traduciendo los identificadores a codigos.

    Sin esa traduccion el resultado no significa nada: los identificadores de
    una base no son los de la otra.
    """
    sql = (f'SELECT p1.[{k1}] AS a, p2.[{k2}] AS b '
           f'FROM ([{tabla}] u INNER JOIN [{t1}] p1 ON u.[{c1}] = p1.[{c1}]) '
           f'INNER JOIN [{t2}] p2 ON u.[{c2}] = p2.[{c2}]')
    fa, fb = consultar(cn_a, sql), consultar(cn_b, sql)
    if fa is None or fb is None:
        print(f'\n  [{tabla}] no se pudo comparar')
        return
    sa = {(normalizar(r['a']), normalizar(r['b'])) for r in fa}
    sb = {(normalizar(r['a']), normalizar(r['b'])) for r in fb}
    print()
    print(f'  {tabla}:  {len(sa)} en {nom_a}  |  {len(sb)} en {nom_b}')
    print(f'     asignaciones nuevas en {nom_b}: {len(sb - sa)}')
    print(f'     que ella quito o no tiene:      {len(sa - sb)}')
    for par in sorted(sb - sa)[:15]:
        print(f'        + {par[0]}  ->  {par[1]}')
    if len(sb - sa) > 15:
        print(f'        ... y {len(sb - sa) - 15} mas')


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        print('Faltan las dos bases a comparar.')
        return 1

    ruta_a, ruta_b = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    for r in (ruta_a, ruta_b):
        if not os.path.exists(r):
            print(f'No existe: {r}')
            return 1

    nom_a, nom_b = 'PRINCIPAL', 'DE ELLA'
    print(f'  {nom_a}: {ruta_a}')
    print(f'  {nom_b}: {ruta_b}')

    cn_a, cn_b = conectar(ruta_a), conectar(ruta_b)
    try:
        comparar_operativo(cn_a, cn_b, nom_a, nom_b)

        titulo('CATALOGO  -  resumen')
        resultados = []
        for tabla, sql, claves, campos in CATALOGO:
            resultados.append(
                comparar_tabla(cn_a, cn_b, tabla, sql, claves, campos,
                               nom_a, nom_b))

        titulo('ASIGNACIONES (que parametro va en que prueba)')
        for u in UNIONES:
            comparar_union(cn_a, cn_b, *u, nom_a=nom_a, nom_b=nom_b)

        titulo('CATALOGO  -  detalle')
        for r in resultados:
            detallar(r, nom_a, nom_b)

        titulo('QUE HACER CON ESTO')
        print('  Este informe no cambia nada. Sirve para decidir.')
        print()
        print('  Revise sobre todo las diferencias campo a campo: ahi estan los')
        print('  valores normales y las unidades corregidos, que es lo que mas')
        print('  cuesta rehacer a mano y lo que mas dano hace si se pierde.')
    finally:
        for cn in (cn_a, cn_b):
            try:
                cn.Close()
            except Exception:
                pass
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
================================================================================
APLICAR EL CATALOGO DEL LABORATORIO - ANgesLAB
================================================================================
Trae a la base de este proyecto los arreglos de catalogo hechos en el
laboratorio, para que el producto los lleve de fabrica.

Que trae y que NO
-----------------
TRAE, de la tabla Parametros:
    Observaciones (los valores de referencia que se imprimen), Seccion (como se
    agrupan en el informe), TipoResultado, unidad, nombre corto y decimales.
    Mas los parametros que alli existen y aqui no, enganchados a su prueba.

NO TOCA la tabla Pruebas. El trabajo preanalitico de aqui —tubo recomendado,
horas de ayuno, tipo de muestra— y la reclasificacion de areas no existen en la
base del laboratorio, y sobrescribirlos con sus vacios seria perderlos. Los
precios tampoco: los de aqui (2,22) son de catalogo y los suyos son sus tarifas
reales, que no deben viajar en el producto a otros laboratorios.

TAMPOCO crea las 78 "pruebas nuevas" que aparecen en la comparacion. No son
nuevas: son las mismas de aqui con el codigo anterior a la renumeracion.
Crearlas duplicaria 75 pruebas del catalogo.

Por que se empareja por nombre
-------------------------------
Los identificadores y los codigos NO significan lo mismo en las dos bases. El
parametro 27 es LINFOCITOS aqui y Brucella Abortus alla. Emparejar por codigo
mezclaria parametros distintos y meteria valores de referencia equivocados en
el informe del paciente.

Uso
---
    python scripts/aplicar_catalogo_laboratorio.py  lab.accdb            (simula)
    python scripts/aplicar_catalogo_laboratorio.py  lab.accdb  --aplicar

Sin --aplicar no escribe nada: enumera lo que haria. Con --aplicar hace antes
una copia de seguridad en backups\\.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import os
import shutil
import sys
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESTINO = os.path.join(BASE, 'ANgesLAB.accdb')
BACKUPS = os.path.join(BASE, 'backups')

# Campos de Parametros que se traen del laboratorio.
# Decidido con el usuario el 2026-08-21: en los casos dudosos manda el
# laboratorio, incluidos ANTIGENO DE SUPERFICIE y NT-PROBNP.
CAMPOS = ['Observaciones', 'Seccion', 'TipoResultado', 'NombreCorto',
          'ValorMinimo', 'ValorMaximo', 'Decimales']


def conectar(ruta):
    import win32com.client
    cn = win32com.client.Dispatch('ADODB.Connection')
    cn.Open(f'Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta};')
    return cn


def consultar(cn, sql):
    rs = cn.Execute(sql)[0]
    cols = [rs.Fields(i).Name for i in range(rs.Fields.Count)]
    filas = []
    while not rs.EOF:
        filas.append({c: rs.Fields(c).Value for c in cols})
        rs.MoveNext()
    rs.Close()
    return filas


def uno(cn, sql):
    filas = consultar(cn, sql)
    return filas[0] if filas else None


def nom(v):
    return ' '.join(str(v or '').split()).strip().upper()


def sql_valor(v):
    """Literal SQL para Access."""
    if v is None or (isinstance(v, str) and v.strip() == ''):
        return 'Null'
    if isinstance(v, bool):
        return 'True' if v else 'False'
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def igual(a, b):
    return nom(a) == nom(b)


# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    origen = os.path.abspath(sys.argv[1])
    aplicar = '--aplicar' in sys.argv

    if not os.path.exists(origen):
        print(f'No existe: {origen}')
        return 1
    if not os.path.exists(DESTINO):
        print(f'No existe la base destino: {DESTINO}')
        return 1

    print('=' * 78)
    print('  ' + ('APLICANDO' if aplicar else 'SIMULACION (no se escribe nada)'))
    print(f'  origen  (laboratorio): {origen}')
    print(f'  destino (producto)   : {DESTINO}')
    print('=' * 78)

    if aplicar:
        os.makedirs(BACKUPS, exist_ok=True)
        copia = os.path.join(
            BACKUPS,
            f'ANgesLAB_antes_catalogo_lab_{datetime.now():%Y%m%d_%H%M%S}.accdb')
        shutil.copyfile(DESTINO, copia)
        print(f'\n  Copia de seguridad: {os.path.basename(copia)}')

    cn_o, cn_d = conectar(origen), conectar(DESTINO)
    try:
        SQL = ('SELECT pa.*, u.CodigoUnidad AS _U '
               'FROM (Parametros pa LEFT JOIN Unidades u ON pa.UnidadID = u.UnidadID)')
        origen_por_nombre = {}
        for r in consultar(cn_o, SQL):
            origen_por_nombre.setdefault(nom(r['NombreParametro']), []).append(r)
        destino_por_nombre = {}
        for r in consultar(cn_d, SQL):
            destino_por_nombre.setdefault(nom(r['NombreParametro']), []).append(r)

        # Unidades del destino, por codigo, para traducir la de origen
        unidades = {nom(u['CodigoUnidad']): u['UnidadID']
                    for u in consultar(cn_d, 'SELECT UnidadID, CodigoUnidad FROM Unidades')}

        # --- 1) Actualizar los parametros que existen en las dos -----------
        print('\n--- Parametros actualizados ---')
        actualizados = ambiguos = 0
        for clave, lista_o in sorted(origen_por_nombre.items()):
            lista_d = destino_por_nombre.get(clave)
            if not lista_d:
                continue
            if len(lista_o) != 1 or len(lista_d) != 1:
                # Nombre repetido: no hay forma segura de saber cual con cual
                ambiguos += 1
                continue

            o, d = lista_o[0], lista_d[0]
            sets, detalle = [], []
            for c in CAMPOS:
                if not igual(o.get(c), d.get(c)):
                    sets.append(f'[{c}] = {sql_valor(o.get(c))}')
                    detalle.append(f'{c}: {str(d.get(c))[:22]!r} -> {str(o.get(c))[:22]!r}')

            # La unidad se traduce por codigo; el identificador no vale
            if not igual(o.get('_U'), d.get('_U')):
                destino_id = unidades.get(nom(o.get('_U'))) if o.get('_U') else None
                if o.get('_U') and destino_id is None:
                    detalle.append(f'unidad {o.get("_U")}: NO existe aqui, se omite')
                else:
                    sets.append(f'[UnidadID] = {sql_valor(destino_id)}')
                    detalle.append(f'unidad: {d.get("_U")!r} -> {o.get("_U")!r}')

            if not sets:
                continue
            actualizados += 1
            print(f'  {str(d["NombreParametro"])[:44]:<46} ({d["CodigoParametro"]})')
            for x in detalle:
                print(f'      {x}')
            if aplicar:
                cn_d.Execute(f'UPDATE Parametros SET {", ".join(sets)} '
                             f'WHERE ParametroID = {d["ParametroID"]}')

        # --- 2) Crear los parametros que solo tiene el laboratorio ---------
        print('\n--- Parametros nuevos ---')
        codigos_usados = {nom(r['CodigoParametro'])
                          for l in destino_por_nombre.values() for r in l}
        creados = 0
        for clave, lista_o in sorted(origen_por_nombre.items()):
            if clave in destino_por_nombre:
                continue
            o = lista_o[0]

            # Su codigo puede estar ocupado aqui por OTRO parametro
            codigo = str(o['CodigoParametro'] or '').strip()
            if not codigo or nom(codigo) in codigos_usados:
                base_cod = (nom(codigo) or 'PAR')[:12]
                i = 2
                while nom(f'{base_cod}_{i}') in codigos_usados:
                    i += 1
                codigo = f'{base_cod}_{i}'
            codigos_usados.add(nom(codigo))

            # A que prueba pertenece alla, y si esa prueba existe aqui
            prueba = uno(cn_o, f'''SELECT pr.NombrePrueba, pr.CodigoPrueba FROM
                ((ParametrosPrueba pp INNER JOIN Pruebas pr ON pp.PruebaID = pr.PruebaID))
                WHERE pp.ParametroID = {o['ParametroID']}''')
            nombre_prueba = prueba['NombrePrueba'] if prueba else None
            prueba_origen_cod = prueba['CodigoPrueba'] if prueba else None
            destino_prueba = None
            if nombre_prueba:
                destino_prueba = uno(cn_d,
                                     'SELECT PruebaID, CodigoPrueba FROM Pruebas '
                                     f"WHERE UCase(Trim(NombrePrueba)) = '{nom(nombre_prueba)}'")
            # Si el nombre no casa, se prueba por codigo: aqui se renombraron
            # pruebas que alla conservan el nombre viejo (HEMOGLOBINA
            # GLUCOSILADA A1C paso a llamarse HEMOGLOBINA GLICADA (HBA1C)),
            # y sin este respaldo el parametro nuevo quedaria suelto.
            if destino_prueba is None and prueba_origen_cod:
                destino_prueba = uno(cn_d,
                                     'SELECT PruebaID, CodigoPrueba FROM Pruebas '
                                     f"WHERE UCase(Trim(CodigoPrueba)) = '{nom(prueba_origen_cod)}'")

            creados += 1
            print(f'  {str(o["NombreParametro"])[:44]:<46} codigo {codigo}')
            print(f'      prueba: {str(nombre_prueba)[:40]}'
                  f'  -> {"se engancha a " + str(destino_prueba["CodigoPrueba"]) if destino_prueba else "SIN prueba aqui, quedaria suelto"}')

            if not aplicar:
                continue

            unidad_id = unidades.get(nom(o.get('_U'))) if o.get('_U') else None
            campos = ['CodigoParametro', 'NombreParametro', 'NombreCorto',
                      'TipoResultado', 'Observaciones', 'Seccion',
                      'ValorMinimo', 'ValorMaximo', 'Decimales', 'UnidadID', 'Activo']
            valores = [sql_valor(codigo), sql_valor(o.get('NombreParametro')),
                       sql_valor(o.get('NombreCorto')), sql_valor(o.get('TipoResultado')),
                       sql_valor(o.get('Observaciones')), sql_valor(o.get('Seccion')),
                       sql_valor(o.get('ValorMinimo')), sql_valor(o.get('ValorMaximo')),
                       sql_valor(o.get('Decimales')), sql_valor(unidad_id), 'True']
            cn_d.Execute(f'INSERT INTO Parametros ({", ".join("["+c+"]" for c in campos)}) '
                         f'VALUES ({", ".join(valores)})')

            nuevo = uno(cn_d, 'SELECT ParametroID FROM Parametros '
                              f"WHERE CodigoParametro = {sql_valor(codigo)}")
            if nuevo and destino_prueba:
                # Se coloca al final de la prueba; el orden fino lo ajusta quien
                # revise el informe, que es quien sabe donde va
                sec = uno(cn_d, 'SELECT MAX(Secuencia) AS s FROM ParametrosPrueba '
                                f'WHERE PruebaID = {destino_prueba["PruebaID"]}')
                siguiente = int((sec or {}).get('s') or 0) + 1
                cn_d.Execute(
                    'INSERT INTO ParametrosPrueba (PruebaID, ParametroID, Secuencia, Obligatorio) '
                    f'VALUES ({destino_prueba["PruebaID"]}, {nuevo["ParametroID"]}, '
                    f'{siguiente}, False)')

        print('\n' + '=' * 78)
        print(f'  parametros actualizados : {actualizados}')
        print(f'  parametros creados      : {creados}')
        if ambiguos:
            print(f'  omitidos por nombre repetido: {ambiguos}')
        print(f'  Pruebas: NO se toca (preanalitico, areas y precios se conservan)')
        if not aplicar:
            print('\n  Esto fue una SIMULACION. Repita con --aplicar para escribir.')
    finally:
        for cn in (cn_o, cn_d):
            try:
                cn.Close()
            except Exception:
                pass
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
================================================================================
CORREGIR QUE PARAMETRO VA EN QUE PRUEBA - ANgesLAB
================================================================================
Arregla las asignaciones parametro->prueba tomando como referencia la base del
laboratorio, prueba por prueba y solo donde se ha decidido.

Por que hizo falta
------------------
El catalogo de aqui tenia parametros enganchados a la prueba equivocada. El
caso mas claro: la prueba TP (Tiempo de Protrombina) mostraba como unico
parametro "GLICEMIA 300 MIN". Eso no lo arregla ningun informe; sale mal
siempre. En el laboratorio se corrigieron con meses de uso real delante.

Dos modos, elegidos uno a uno
------------------------------
REEMPLAZAR  la lista de la prueba pasa a ser la del laboratorio: se quitan los
            parametros que no deberian estar y se ponen los que faltan.
SUMAR       solo se anaden los que faltan; no se quita nada de lo de aqui.

La distincion importa. En HEMATOLOGIA COMPLETA y en VSG el catalogo de aqui
tiene mas parametros que el del laboratorio —los contajes absolutos, la VSG por
horas con indice de Katz— y son trabajo deliberado nuestro: ahi reemplazar
seria perderlos. Por eso ninguna prueba se toca sin figurar en la lista.

Nada se borra de Parametros: solo se quita o se pone la fila de union en
ParametrosPrueba. El parametro sigue existiendo y en su sitio si estaba en otra
prueba.

Uso
---
    python scripts/corregir_parametros_prueba.py  lab.accdb            (simula)
    python scripts/corregir_parametros_prueba.py  lab.accdb  --aplicar

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

# Decidido con el usuario el 2026-08-22 sobre la lista de las 27 pruebas cuyos
# parametros diferian. Se identifica la prueba por su CODIGO en esta base.
#
# REEMPLAZAR: aqui el parametro enganchado es de otra prueba.
# SUMAR:      el laboratorio tiene uno que falta, y lo de aqui se conserva.
#
# Queda FUERA, a proposito:
#   129 HELICOBACTER PILORY  - aqui MONOTEST, alla CITOMEGALOVIRUS IGG. Las dos
#       parecen equivocadas; pendiente de preguntar en el laboratorio.
#   HEM001, HEMA004, QUIM002 y el perfil de resistencia a insulina - el catalogo
#       de aqui tiene mas y es trabajo nuestro.
#   Las 7 que dependen del reactivo (T3/T4 totales o libres, TSH o TSH ultra,
#       coproanalisis, urocultivo, TPT) - pendientes del criterio del laboratorio.
DECISIONES = [
    ('120',     'REEMPLAZAR', 'TP: tenia GLICEMIA 300 MIN'),
    ('64',      'REEMPLAZAR', 'DENGUE IgG-IgM: tenia DESARROLLO y GRAM'),
    ('131',     'REEMPLAZAR', 'CITOMEGALOVIRUS IgM: tenia el IgG'),
    ('130',     'REEMPLAZAR', 'CITOMEGALOVIRUS IgG: tenia HELICOBACTER IgM'),
    ('136',     'REEMPLAZAR', 'ASLO CUANTITATIVO: tenia TOXOPLASMA IgG'),
    ('104',     'REEMPLAZAR', 'GLICEMIA 30 MIN: tenia la glicemia generica'),
    ('105',     'REEMPLAZAR', 'GLICEMIA 60 MIN: tenia la glicemia generica'),
    ('106',     'REEMPLAZAR', 'GLICEMIA 90 MIN: tenia la glicemia generica'),
    ('107',     'REEMPLAZAR', 'GLICEMIA 120 MIN: tenia la glicemia generica'),
    ('QUI023',  'REEMPLAZAR', 'TROPONINA: el laboratorio usa TROPONINA I'),
    ('201',     'REEMPLAZAR', 'INSULINA POST PANDRIAL: tenia la insulina basal'),

    ('18',      'SUMAR',      'ANTIGENOS FEBRILES: falta PROTEUS OX-19'),
    ('3',       'SUMAR',      'ELECTROLITOS: falta CALCIO IONICO'),
    ('QUIM004', 'SUMAR',      'PERFIL RENAL: falta ACIDO URICO'),
    ('COAG002', 'SUMAR',      'TP + INR: faltan ISI y RAZON'),
]


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


def esc(v):
    return str(v).replace("'", "''")


def parametros_de(cn, codigo_prueba):
    """{nombre normalizado: fila} de los parametros de una prueba."""
    filas = consultar(cn, f"""
        SELECT pp.ParametroPruebaID, pp.Secuencia, par.ParametroID,
               par.NombreParametro
        FROM (ParametrosPrueba pp
        INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID)
        INNER JOIN Pruebas pr ON pp.PruebaID = pr.PruebaID
        WHERE UCase(Trim(pr.CodigoPrueba)) = '{esc(nom(codigo_prueba))}'
        ORDER BY pp.Secuencia""")
    return {nom(f['NombreParametro']): f for f in filas}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    origen = os.path.abspath(sys.argv[1])
    aplicar = '--aplicar' in sys.argv

    if not os.path.exists(origen):
        print(f'No existe: {origen}')
        return 1

    print('=' * 78)
    print('  ' + ('APLICANDO' if aplicar else 'SIMULACION (no se escribe nada)'))
    print('=' * 78)

    if aplicar:
        os.makedirs(BACKUPS, exist_ok=True)
        copia = os.path.join(
            BACKUPS,
            f'ANgesLAB_antes_paramprueba_{datetime.now():%Y%m%d_%H%M%S}.accdb')
        shutil.copyfile(DESTINO, copia)
        print(f'  Copia de seguridad: {os.path.basename(copia)}\n')

    cn_o, cn_d = conectar(origen), conectar(DESTINO)
    quitadas = puestas = creados = 0
    avisos = []
    try:
        pruebas_origen = {nom(r['NombrePrueba']): r
                          for r in consultar(cn_o, 'SELECT CodigoPrueba, NombrePrueba FROM Pruebas')}
        parametros_destino = {nom(r['NombreParametro']): r
                              for r in consultar(cn_d, 'SELECT ParametroID, NombreParametro FROM Parametros')}
        for codigo, modo, motivo in DECISIONES:
            prueba = uno(cn_d, 'SELECT PruebaID, CodigoPrueba, NombrePrueba FROM Pruebas '
                               f"WHERE UCase(Trim(CodigoPrueba)) = '{esc(nom(codigo))}'")
            if not prueba:
                avisos.append(f'La prueba {codigo} no existe aqui; se omite')
                continue

            # En el laboratorio la prueba puede tener otro codigo: se busca por
            # nombre. La comparacion se hace en Python y no en SQL porque
            # UCase(Trim(...)) de Access no colapsa los espacios interiores, y
            # varios nombres del catalogo los llevan dobles: "GLICEMIA  30
            # MINUTOS" no casaba con "GLICEMIA 30 MINUTOS".
            prueba_o = pruebas_origen.get(nom(prueba['NombrePrueba']))
            if not prueba_o:
                avisos.append(f'{prueba["NombrePrueba"]}: no se encuentra en el laboratorio')
                continue

            aqui = parametros_de(cn_d, prueba['CodigoPrueba'])
            alla = parametros_de(cn_o, prueba_o['CodigoPrueba'])

            sobran = [] if modo == 'SUMAR' else sorted(set(aqui) - set(alla))
            faltan = sorted(set(alla) - set(aqui))
            if not sobran and not faltan:
                continue

            print(f'  [{modo}] {prueba["NombrePrueba"]}  ({codigo})')
            print(f'      {motivo}')

            # Se resuelve TODO lo que hay que poner ANTES de quitar nada. Si
            # un parametro no se puede resolver y ya se hubiera borrado el
            # anterior, la prueba se quedaria sin ningun parametro: peor que
            # como estaba.
            a_poner, sin_resolver = [], []
            for clave in faltan:
                destino = parametros_destino.get(clave)
                if destino:
                    a_poner.append((clave, destino, False))
                    continue
                # No existe aqui: se crea copiando la definicion del laboratorio,
                # que es de donde viene la decision de usarlo
                origen_par = uno(cn_o, 'SELECT * FROM Parametros WHERE '
                                       f'ParametroID = {alla[clave]["ParametroID"]}')
                if origen_par:
                    a_poner.append((clave, origen_par, True))
                else:
                    sin_resolver.append(clave)

            if sin_resolver:
                for clave in sin_resolver:
                    avisos.append(f'{prueba["NombrePrueba"]}: no se pudo resolver '
                                  f'"{alla[clave]["NombreParametro"]}"')
                print('      !  se OMITE esta prueba entera: no se puede completar '
                      'la sustitucion sin dejarla incompleta')
                print()
                continue

            for clave in sobran:
                print(f'      -  quita  {aqui[clave]["NombreParametro"]}')
                quitadas += 1
                if aplicar:
                    cn_d.Execute('DELETE FROM ParametrosPrueba WHERE '
                                 f'ParametroPruebaID = {aqui[clave]["ParametroPruebaID"]}')

            for clave, fila, hay_que_crear in a_poner:
                if hay_que_crear:
                    print(f'      *  crea   {fila["NombreParametro"]} (no existia aqui)')
                    creados += 1
                else:
                    print(f'      +  pone   {fila["NombreParametro"]}')
                puestas += 1
                if not aplicar:
                    continue

                parametro_id = fila.get('ParametroID')
                if hay_que_crear:
                    codigo_nuevo = str(fila.get('CodigoParametro') or '').strip()
                    if not codigo_nuevo or nom(codigo_nuevo) in {nom(r['CodigoParametro'])
                            for r in consultar(cn_d, 'SELECT CodigoParametro FROM Parametros')}:
                        codigo_nuevo = (nom(codigo_nuevo) or 'PAR')[:12] + '_2'
                    cn_d.Execute(
                        'INSERT INTO Parametros (CodigoParametro, NombreParametro, '
                        'TipoResultado, Observaciones, Seccion, Decimales, Activo) VALUES ('
                        f"'{esc(codigo_nuevo)}', '{esc(fila['NombreParametro'])}', "
                        f"'{esc(fila.get('TipoResultado') or 'NUMERICO')}', "
                        f"'{esc(fila.get('Observaciones') or '')}', "
                        f"'{esc(fila.get('Seccion') or '')}', "
                        f"{int(fila.get('Decimales') or 2)}, True)")
                    creado = uno(cn_d, 'SELECT ParametroID FROM Parametros WHERE '
                                       f"CodigoParametro = '{esc(codigo_nuevo)}'")
                    parametro_id = creado['ParametroID']
                    parametros_destino[clave] = {'ParametroID': parametro_id,
                                                 'NombreParametro': fila['NombreParametro']}

                sec = uno(cn_d, 'SELECT MAX(Secuencia) AS s FROM ParametrosPrueba '
                                f'WHERE PruebaID = {prueba["PruebaID"]}')
                siguiente = int((sec or {}).get('s') or 0) + 1
                cn_d.Execute(
                    'INSERT INTO ParametrosPrueba '
                    '(PruebaID, ParametroID, Secuencia, Obligatorio) VALUES '
                    f'({prueba["PruebaID"]}, {parametro_id}, {siguiente}, False)')
            print()

        print('=' * 78)
        print(f'  asignaciones quitadas: {quitadas}')
        print(f'  asignaciones puestas : {puestas}')
        print(f'  parametros creados   : {creados}')
        if avisos:
            print('\n  Avisos:')
            for a in avisos:
                print(f'    - {a}')
        if not aplicar:
            print('\n  SIMULACION. Repita con --aplicar para escribir.')
    finally:
        for cn in (cn_o, cn_d):
            try:
                cn.Close()
            except Exception:
                pass
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
================================================================================
HOJA DE REVISION DE CAMBIOS DE CATALOGO - ANgesLAB
================================================================================
Saca a un CSV, diferencia por diferencia, lo que cambia entre dos bases, para
poder decidir cual se queda.

Por que una hoja y no un traspaso automatico
---------------------------------------------
Porque no todo lo que difiere es una mejora. En la comparacion del 2026-08-21
aparecieron, mezclados: correcciones buenas (calcio ionico que faltaba,
toxoplasma en UI/mL), cambios de criterio legitimos (T3 y T4 en pmol/L, que
dependen del analizador) y errores claros (LINFOCITOS con valor de referencia
"NEGATIVO", troponina con un cero de mas).

Un traspaso automatico habria metido los tres grupos por igual. Un valor de
referencia equivocado no se nota al importarlo: se nota cuando un informe sale
mal, y para entonces ya salio.

Uso
---
    python scripts/revisar_cambios_catalogo.py  aqui.accdb  la_de_ella.accdb  salida.csv

Despues se abre el CSV en Excel, se rellena la columna DECISION con
    AQUI  /  ELLA  /  (vacio = no tocar)
y esa misma hoja sirve de entrada para aplicar solo lo aprobado.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import csv
import os
import sys


# (tabla, SQL, clave, campos, columna con el nombre legible)
BLOQUES = [
    ('Parametros',
     'SELECT pa.*, u.CodigoUnidad AS _Unidad '
     'FROM (Parametros pa LEFT JOIN Unidades u ON pa.UnidadID = u.UnidadID)',
     'CodigoParametro',
     ['NombreParametro', '_Unidad', 'TipoResultado', 'Observaciones',
      'Seccion', 'ValorMinimo', 'ValorMaximo', 'Decimales', 'Activo'],
     'NombreParametro'),

    ('Pruebas',
     'SELECT p.*, a.CodigoArea AS _Area, tm.CodigoTipoMuestra AS _TipoMuestra '
     'FROM ((Pruebas p LEFT JOIN Areas a ON p.AreaID = a.AreaID) '
     'LEFT JOIN TiposMuestra tm ON p.TipoMuestraID = tm.TipoMuestraID)',
     'CodigoPrueba',
     ['NombrePrueba', '_Area', 'Precio', 'Activo', '_TipoMuestra',
      'TuboRecomendado', 'RequiereAyuno', 'HorasAyuno', 'Metodologia'],
     'NombrePrueba'),
]

# Campos donde el cambio merece mirarse con cuidado: son los que acaban
# impresos en el informe del paciente.
CRITICOS = {'Observaciones', 'ValorMinimo', 'ValorMaximo', '_Unidad',
            'TipoResultado', 'NombreParametro', 'NombrePrueba'}


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


def normalizar(v):
    if v is None:
        return ''
    if isinstance(v, bool):
        return 'S' if v else 'N'
    if isinstance(v, (int, float)):
        f = float(v)
        return str(int(f)) if f == int(f) else f'{f:.6g}'
    return ' '.join(str(v).split()).strip()


def para_celda(v):
    """Los saltos de linea dentro de una celda hacen ilegible el CSV en Excel."""
    return normalizar(v).replace('\r', ' ').replace('\n', ' | ')


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    ruta_a, ruta_b, salida = (os.path.abspath(sys.argv[1]),
                              os.path.abspath(sys.argv[2]),
                              os.path.abspath(sys.argv[3]))

    cn_a, cn_b = conectar(ruta_a), conectar(ruta_b)
    filas_csv = []
    try:
        for tabla, sql, clave, campos, etiqueta in BLOQUES:
            A = {normalizar(r[clave]).upper(): r for r in consultar(cn_a, sql)}
            B = {normalizar(r[clave]).upper(): r for r in consultar(cn_b, sql)}

            for k in sorted(set(A) & set(B)):
                for campo in campos:
                    va, vb = normalizar(A[k].get(campo)), normalizar(B[k].get(campo))
                    if va == vb:
                        continue
                    filas_csv.append({
                        'TABLA': tabla,
                        'CODIGO': k,
                        'NOMBRE': para_celda(A[k].get(etiqueta)),
                        'CAMPO': campo,
                        'VALOR_AQUI': para_celda(A[k].get(campo)),
                        'VALOR_ELLA': para_celda(B[k].get(campo)),
                        'REVISAR': 'SI' if campo in CRITICOS else '',
                        'DECISION': '',
                    })

            for k in sorted(set(B) - set(A)):
                filas_csv.append({
                    'TABLA': tabla,
                    'CODIGO': k,
                    'NOMBRE': para_celda(B[k].get(etiqueta)),
                    'CAMPO': '(NO EXISTE AQUI)',
                    'VALOR_AQUI': '',
                    'VALOR_ELLA': 'fila completa',
                    'REVISAR': 'SI',
                    'DECISION': '',
                })
    finally:
        for cn in (cn_a, cn_b):
            try:
                cn.Close()
            except Exception:
                pass

    # utf-8-sig para que Excel respete los acentos al abrirlo de doble clic
    with open(salida, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, delimiter=';', fieldnames=[
            'TABLA', 'CODIGO', 'NOMBRE', 'CAMPO',
            'VALOR_AQUI', 'VALOR_ELLA', 'REVISAR', 'DECISION'])
        w.writeheader()
        w.writerows(filas_csv)

    criticos = sum(1 for r in filas_csv if r['REVISAR'] == 'SI')
    print(f'  {len(filas_csv)} diferencias escritas en:')
    print(f'    {salida}')
    print(f'  De ellas, {criticos} marcadas REVISAR=SI: son las que acaban')
    print('  impresas en el informe del paciente.')
    print()
    print('  Abra el CSV, rellene DECISION con AQUI o ELLA en cada fila que')
    print('  quiera resolver, y deje en blanco lo que no haya que tocar.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

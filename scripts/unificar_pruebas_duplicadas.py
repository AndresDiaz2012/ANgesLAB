# -*- coding: utf-8 -*-
"""
================================================================================
UNIFICAR PRUEBAS DUPLICADAS - ANgesLAB
================================================================================
Deja una sola prueba activa por cada nombre repetido del catalogo.

El problema
-----------
El catalogo tenia 12 nombres repartidos en 25 pruebas. Se distinguian por un
punto final, un espacio de mas o dos puntos: "CREATININA EN ORINA PARCIAL" y
"CREATININA EN ORINA PARCIAL.", "Helicobacter pilory en Heces:" y
"Helicobacter pilory en Heces.". Quien pide la prueba ve tres opciones que
parecen iguales, y como cada copia tiene parametros distintos —o ninguno— el
informe sale distinto segun cual eligio.

Se DESACTIVAN, no se borran
----------------------------
`Activo = False` las saca del buscador, del catalogo y de las solicitudes
nuevas, que es lo que hace falta. Borrarlas romperia cualquier solicitud
antigua que las referencie, y en la base del laboratorio hay seis meses de
trabajo: una prueba desactivada sigue explicando que se le hizo a un paciente
en marzo.

Antes de desactivar comprueba que la prueba no este usada en solicitudes,
facturas, cotizaciones, perfiles ni listas de precios. Si lo esta, la deja y
avisa.

Como se elige la que se queda
------------------------------
La que tiene parametros, y entre esas la del codigo por area (URO017, SER014,
COAG002...), que es la convencion vigente del catalogo. Los codigos numericos
sueltos son los heredados.

Uso
---
    python scripts/unificar_pruebas_duplicadas.py            (simula)
    python scripts/unificar_pruebas_duplicadas.py --aplicar

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

# (se_queda, [se_desactivan], motivo)
# Revisado uno a uno el 2026-08-22 mirando que parametros tiene cada copia.
DECISIONES = [
    ('SER014',   ['174'],       'ANTI DNA: se queda la de codigo por area'),
    ('URO017',   ['246'],       'CREATININA EN ORINA PARCIAL: la otra no tiene parametros'),
    ('SER007',   ['286'],       'HEPATITIS C: la otra no tiene parametros'),
    ('REN003',   ['REN002'],    'RELACION ACIDO URICO/CREATININA: la otra no tiene parametros'),
    ('REN006',   ['REN005'],    'RELACION CALCIO/CREATININA: la otra no tiene parametros'),
    ('REN007',   ['REN001'],    'RELACION FOSFORO/CREATININA: el mismo parametro dos veces'),
    ('COPRO002', ['257'],       'SANGRE OCULTA EN HECES: la otra no tiene parametros'),
    ('URO042',   ['247'],       'UREA EN ORINA PARCIAL: la otra no tiene parametros'),

    # La "8 TP INR" tenia 23 parametros de UROANALISIS (color, olor, densidad,
    # pH...). Esta corrupta de arriba abajo; en el laboratorio la eliminaron.
    ('COAG002',  ['8'],         'TP INR: la otra tenia parametros de uroanalisis'),

    # De las tres de heces, la unica activa no tiene parametros y las otras dos
    # ya estaban inactivas (una con "," como parametro). Se conserva la activa
    # y se le pone su parametro, que estaba huerfano.
    ('101',      ['292', '293'], 'HELICOBACTER EN HECES: tres copias por la puntuacion'),
]

# Parametro que hay que poner a una prueba que se queda sin ninguno.
# El "Helicobacter pilory en heces" existia pero estaba colgado de la prueba 289,
# que alguien borro: no lo veia nadie. Se le devuelve a la prueba que si esta.
COMPLETAR = [
    ('101', '538', 'HELICOBACTER PILORY EN HECES estaba activa y sin parametros'),
]

# Queda FUERA a proposito:
#   LIQUIDO ORGANICO CITOQUIMICO (15 y 71). Las DOS estan mal: la 15 tiene
#   parametros de aclaramiento de creatinina y la 71 de microbiologia. Ninguna
#   tiene los de un citoquimico. Hay que preguntarlo en el laboratorio.
#   CULTIVO DE ESPUTO (MIC009 y 26): la 26 ya estaba inactiva.

TABLAS_USO = ['DetalleSolicitudes', 'DetalleFacturas', 'DetalleCotizaciones',
              'PruebasEnPerfil', 'Precios', 'PruebasSolicitadas']


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


def esc(v):
    return str(v).replace("'", "''")


def prueba_por_codigo(cn, codigo):
    return uno(cn, 'SELECT PruebaID, CodigoPrueba, NombrePrueba, Activo FROM Pruebas '
                   f"WHERE UCase(Trim(CodigoPrueba)) = '{esc(str(codigo).strip().upper())}'")


def usos_de(cn, prueba_id):
    """Cuantas veces se referencia la prueba en datos operativos."""
    total = 0
    for t in TABLAS_USO:
        try:
            r = uno(cn, f'SELECT COUNT(*) AS n FROM [{t}] WHERE PruebaID = {prueba_id}')
            total += int((r or {}).get('n') or 0)
        except Exception:
            pass          # la tabla puede no existir en instalaciones antiguas
    return total


def main():
    aplicar = '--aplicar' in sys.argv
    print('=' * 78)
    print('  ' + ('APLICANDO' if aplicar else 'SIMULACION (no se escribe nada)'))
    print('=' * 78)

    if aplicar:
        os.makedirs(BACKUPS, exist_ok=True)
        copia = os.path.join(
            BACKUPS, f'ANgesLAB_antes_duplicadas_{datetime.now():%Y%m%d_%H%M%S}.accdb')
        shutil.copyfile(DESTINO, copia)
        print(f'  Copia de seguridad: {os.path.basename(copia)}\n')

    cn = conectar(DESTINO)
    desactivadas = completadas = 0
    avisos = []
    try:
        for se_queda, se_van, motivo in DECISIONES:
            queda = prueba_por_codigo(cn, se_queda)
            if not queda:
                avisos.append(f'No existe la prueba {se_queda}; se omite el grupo')
                continue

            print(f'  {motivo}')
            print(f'     SE QUEDA   {queda["CodigoPrueba"]:<10} {queda["NombrePrueba"]}')

            if not queda['Activo'] and aplicar:
                # No tendria sentido dejar activa solo a la que se descarta
                cn.Execute(f'UPDATE Pruebas SET Activo = True WHERE PruebaID = {queda["PruebaID"]}')
                print('                (se reactiva: era la elegida y estaba inactiva)')

            for cod in se_van:
                otra = prueba_por_codigo(cn, cod)
                if not otra:
                    avisos.append(f'No existe la prueba {cod}')
                    continue
                usos = usos_de(cn, otra['PruebaID'])
                if usos:
                    # Nunca se toca una prueba que alguien ya pidio
                    print(f'     SE DEJA    {otra["CodigoPrueba"]:<10} {otra["NombrePrueba"]}'
                          f'   (usada {usos} vez/veces, no se toca)')
                    avisos.append(f'{otra["CodigoPrueba"]} esta en uso ({usos}); '
                                  'se dejo activa')
                    continue
                if not otra['Activo']:
                    print(f'     ya inactiva {otra["CodigoPrueba"]:<9} {otra["NombrePrueba"]}')
                    continue
                print(f'     DESACTIVA  {otra["CodigoPrueba"]:<10} {otra["NombrePrueba"]}')
                desactivadas += 1
                if aplicar:
                    cn.Execute('UPDATE Pruebas SET Activo = False '
                               f'WHERE PruebaID = {otra["PruebaID"]}')
            print()

        print('  --- pruebas activas que se quedaban sin parametros ---')
        for cod_prueba, cod_param, motivo in COMPLETAR:
            prueba = prueba_por_codigo(cn, cod_prueba)
            par = uno(cn, 'SELECT ParametroID, NombreParametro FROM Parametros '
                          f"WHERE UCase(Trim(CodigoParametro)) = '{esc(cod_param.upper())}'")
            if not prueba or not par:
                avisos.append(f'No se pudo completar {cod_prueba} con {cod_param}')
                continue
            ya = uno(cn, 'SELECT COUNT(*) AS n FROM ParametrosPrueba '
                         f'WHERE PruebaID = {prueba["PruebaID"]}')
            if int((ya or {}).get('n') or 0) > 0:
                continue
            print(f'  {motivo}')
            print(f'     {prueba["CodigoPrueba"]:<10} +  {par["NombreParametro"]}')
            completadas += 1
            if aplicar:
                cn.Execute('INSERT INTO ParametrosPrueba '
                           '(PruebaID, ParametroID, Secuencia, Obligatorio) '
                           f'VALUES ({prueba["PruebaID"]}, {par["ParametroID"]}, 1, False)')

        # --- asignaciones colgadas de pruebas que ya no existen --------------
        # Access no tiene claves foraneas declaradas: al borrar una prueba sus
        # filas de ParametrosPrueba se quedan ahi, apuntando a un PruebaID que
        # ya no existe. No se ven en ningun sitio y no dan error, pero falsean
        # cualquier recuento de parametros y estorban al depurar.
        print('  --- asignaciones colgadas de pruebas borradas ---')
        huerfanas = consultar(cn, '''SELECT pp.ParametroPruebaID, pp.PruebaID, p.NombreParametro
            FROM ParametrosPrueba pp INNER JOIN Parametros p ON pp.ParametroID = p.ParametroID
            WHERE pp.PruebaID NOT IN (SELECT PruebaID FROM Pruebas) ORDER BY pp.PruebaID''')
        for h in huerfanas:
            print(f'     BORRA fila {h["ParametroPruebaID"]:<5} (prueba {h["PruebaID"]}, '
                  f'ya no existe)  {h["NombreParametro"]}')
        if aplicar and huerfanas:
            cn.Execute('DELETE FROM ParametrosPrueba WHERE PruebaID NOT IN '
                       '(SELECT PruebaID FROM Pruebas)')
        if not huerfanas:
            print('     ninguna')
        print()

        print()
        print('=' * 78)
        print(f'  pruebas desactivadas : {desactivadas}')
        print(f'  pruebas completadas  : {completadas}')
        print(f'  filas colgadas       : {len(huerfanas)}')
        if avisos:
            print('\n  Avisos:')
            for a in avisos:
                print(f'    - {a}')
        if not aplicar:
            print('\n  SIMULACION. Repita con --aplicar para escribir.')
    finally:
        try:
            cn.Close()
        except Exception:
            pass
    return 0


if __name__ == '__main__':
    sys.exit(main())

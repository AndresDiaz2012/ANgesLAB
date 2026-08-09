# -*- coding: utf-8 -*-
"""
migracion_area_renal.py
=======================
Crea el area RENAL (ID 14) y traslada a ella las relaciones calculadas de
orina, que estaban repartidas entre Uroanalisis y Quimica.

Por que:
  Las relaciones calcio/creatinina, fosforo/creatinina, albumina/creatinina
  y acido urico/creatinina no son un examen de orina mas: son indices de
  funcion renal calculados a partir de dos analitos. Estaban mezcladas con
  el uroanalisis, y una de ellas (RELACION FOSFORO /CREATININA) conservaba
  el codigo TIR054, delatando que en su dia estuvo en Tiroides.

Los codigos de las pruebas trasladadas se renumeran a REN0xx: dejar codigos
URO o TIR en un area Renal reproduce el mismo problema. Ninguno de esos
codigos esta referenciado en el codigo fuente (se verifico antes).

El AreaID 14 se agrega tambien a AREAS_REQUERIDAS en ANgesLAB.pyw, de modo
que cada instalacion crea el area sola al arrancar; este script solo hace
falta para trasladar las pruebas.

Caracteristicas:
  - Idempotente: no vuelve a mover lo ya movido.
  - Copia de seguridad automatica antes de escribir.
  - Modo simulacion por defecto.

Uso:
    python migracion_area_renal.py                 # simulacion
    python migracion_area_renal.py --aplicar       # aplica los cambios

IMPORTANTE: ejecutar con ANgesLAB CERRADO.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    import win32com.client
except ImportError:
    print("ERROR: falta pywin32.  pip install pywin32")
    sys.exit(1)

AREA_RENAL = 14
AREA_CODIGO = 'REN'
AREA_NOMBRE = 'Renal'
AREA_SECUENCIA = 12

# Nombres exactos de las relaciones calculadas que pasan a Renal.
# Se listan las dos variantes (antigua y nueva) que conviven en el catalogo.
RELACIONES = [
    'RELACION CALCIO / CREATININA',
    'RELACION CALCIO/CREATININA',
    'RELACION FOSFORO / CREATININA',
    'RELACION  FOSFORO /CREATININA',
    'RELACION ALBUMINA/CREATININA',
    'RELACION ACIDO URICO /  CREATININA',
    'RELACION ACIDO URICO/CREATININA',
]


def norm(t):
    return ' '.join(str(t or '').upper().split())


def conectar(ruta):
    cn = win32com.client.Dispatch('ADODB.Connection')
    cn.Open(f'Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta};')
    return cn


def consultar(cn, sql):
    rs = cn.Execute(sql)[0]
    cols = [rs.Fields(i).Name for i in range(rs.Fields.Count)]
    filas = []
    while not rs.EOF:
        filas.append({k: rs.Fields(i).Value for i, k in enumerate(cols)})
        rs.MoveNext()
    rs.Close()
    return filas


def uno(cn, sql):
    filas = consultar(cn, sql)
    return filas[0] if filas else None


def respaldar(ruta):
    destino_dir = BASE_DIR / 'backups'
    destino_dir.mkdir(exist_ok=True)
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = destino_dir / f'ANgesLAB_antes_area_renal_{marca}.accdb'
    shutil.copy2(ruta, destino)
    return destino


def main():
    args = list(sys.argv[1:])
    aplicar = '--aplicar' in args
    args = [a for a in args if not a.startswith('--')]
    ruta = Path(args[0]).resolve() if args else (BASE_DIR / 'ANgesLAB.accdb')

    if not ruta.exists():
        print(f"ERROR: no se encontro la base de datos:\n  {ruta}")
        return 1

    print("=" * 72)
    print("  AREA RENAL: RELACIONES CALCULADAS DE ORINA")
    print("=" * 72)
    print(f"Base de datos : {ruta}")
    print(f"Modo          : {'APLICAR CAMBIOS' if aplicar else 'SIMULACION (no escribe)'}")
    print()

    if aplicar:
        print(f"Copia de seguridad: {respaldar(ruta)}\n")

    cn = conectar(str(ruta))
    acciones = []

    # ---- 1. Area -----------------------------------------------------------
    area = uno(cn, f"SELECT AreaID, CodigoArea, NombreArea FROM Areas "
                   f"WHERE AreaID = {AREA_RENAL}")
    if not area:
        acciones.append(f"crear el area {AREA_RENAL} {AREA_CODIGO} '{AREA_NOMBRE}'")
        if aplicar:
            cn.Execute(
                f"INSERT INTO Areas (AreaID, CodigoArea, NombreArea, Secuencia, Activo) "
                f"VALUES ({AREA_RENAL}, '{AREA_CODIGO}', '{AREA_NOMBRE}', "
                f"{AREA_SECUENCIA}, True)")
    else:
        print(f"-- El area {AREA_RENAL} ya existe: "
              f"{area['CodigoArea']} / {area['NombreArea']}")

    # 'General' se corre al final del listado
    gen = uno(cn, "SELECT AreaID, Secuencia FROM Areas WHERE CodigoArea = 'GEN'")
    if gen and gen.get('Secuencia') != 13:
        acciones.append("mover 'General' al final del listado (secuencia 13)")
        if aplicar:
            cn.Execute(f"UPDATE Areas SET Secuencia = 13 WHERE AreaID = {gen['AreaID']}")

    # ---- 2. Traslado de las relaciones -------------------------------------
    pruebas = consultar(cn, "SELECT PruebaID, CodigoPrueba, NombrePrueba, AreaID "
                            "FROM Pruebas WHERE Activo = True")
    buscadas = {norm(n) for n in RELACIONES}
    objetivo = [p for p in pruebas if norm(p['NombrePrueba']) in buscadas]

    if not objetivo:
        print("[AVISO] No se encontro ninguna relacion calculada en el catalogo.")

    secuencia = 1
    for p in sorted(objetivo, key=lambda x: str(x['NombrePrueba'])):
        nuevo_codigo = f"REN{secuencia:03d}"
        secuencia += 1
        cambia_area = p['AreaID'] != AREA_RENAL
        cambia_codigo = str(p['CodigoPrueba'] or '') != nuevo_codigo

        if not cambia_area and not cambia_codigo:
            continue

        detalle = []
        if cambia_area:
            detalle.append(f"area {p['AreaID']} -> {AREA_RENAL}")
        if cambia_codigo:
            detalle.append(f"codigo {p['CodigoPrueba']} -> {nuevo_codigo}")
        acciones.append(f"{p['NombrePrueba']}  ({', '.join(detalle)})")

        if aplicar:
            cn.Execute(f"UPDATE Pruebas SET AreaID = {AREA_RENAL}, "
                       f"CodigoPrueba = '{nuevo_codigo}' "
                       f"WHERE PruebaID = {p['PruebaID']}")

    print()
    if not acciones:
        cn.Close()
        print("No hay nada que hacer: el catalogo ya esta actualizado.")
        return 0

    print(f"-- Cambios ({len(acciones)})")
    for a in acciones:
        print(f"     {a}")
    print()

    cn.Close()
    if not aplicar:
        print("Simulacion terminada. Nada fue modificado.")
        print("Para aplicar los cambios ejecute:")
        print("    python migracion_area_renal.py --aplicar")
    else:
        print("Listo.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

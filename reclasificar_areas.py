# -*- coding: utf-8 -*-
"""
reclasificar_areas.py
=====================
Convierte el area 8 de "Tiroides" en "Hormonas" y saca de ella las pruebas
que no son hormonales, reubicandolas en su area correcta.

Por que el AreaID 8 no cambia:
  Los IDs 1,2,5,6,7,8,9,10 estan fijos en plantillas_reportes.py,
  form_inf_config.py, etiquetas.py, hojas_trabajo.py e ia_interpretacion.py.
  Cambiar el ID romperia los reportes; por eso se renombra el area 8 en vez
  de crear una nueva. Las pruebas de tiroides SON hormonales, asi que
  permanecen en ella junto con el resto de hormonas.

Criterio de reubicacion (sigue la convencion ya usada en este catalogo):
  - Autoanticuerpos e infecciosas  -> Serologia   (como ANA, factor reumatoideo)
  - Marcadores tumorales, vitaminas, apolipoproteinas, PCR, BNP -> Quimica
    (como CA 125, CA 19-9, CEA, Proteina C Reactiva)
  - Morfologia y contajes celulares -> Hematologia
  - Plasmodium y malaria           -> Parasitologia (como Gota Gruesa)
  - Examen directo con KOH         -> Microbiologia (como KOH - Hongos)
  - Anticoagulante lupico          -> Coagulacion
  - Urogen                         -> Uroanalisis

Todo lo que no aparezca en la lista se queda en Hormonas.

Caracteristicas:
  - Idempotente: solo actua sobre pruebas que siguen en el area 8.
  - Copia de seguridad automatica antes de escribir.
  - Modo simulacion por defecto.

Uso:
    python reclasificar_areas.py                       # simulacion
    python reclasificar_areas.py --aplicar             # aplica los cambios
    python reclasificar_areas.py --aplicar "D:\\ANgesLab\\ANgesLAB.accdb"

IMPORTANTE: ejecutar con ANgesLAB CERRADO.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import sys
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

try:
    import win32com.client
except ImportError:
    print("ERROR: falta pywin32.  pip install pywin32")
    sys.exit(1)

AREA_HORMONAS = 8
AREA_NOMBRE = 'Hormonas'
AREA_CODIGO = 'HOR'
AREA_SECUENCIA = 6

# AreaID de destino -> nombres exactos que deben salir del area 8
REUBICACIONES = {
    9: [  # Serologia
        'ANTI PEPTIDO CITRULINADO (ANTI CCP)',
        'ANTI RO-52',
        'ANTI RO-60',
        'ANTI-ACTINA',
        'ANTI-AG CITOSOLICO HEPATICO',
        'ANTI-AG. SOLUBLE HEPATICO/AG DE HIGADO Y PANCREAS',
        'ANTI-DESMINA',
        'ANTI-GLIADINA DEAMINADA IgA GLIADINA 2DA. GENERACION',
        'ANTI-GLIADINA IgA',
        'ANTI-GP200',
        'ANTI-MICROSOMA DE HIGADO Y RIÑON',
        'ANTI-MIOSINA',
        'ANTI-SP100',
        'ANTICUERPOS ANTI-INSULINA',
        'CHAGATEST',
        'HTLV I',
        'HTLV II',
        'VIRUS RESPIRATORIO SYNCYTIAL',
        'VIRUS SINCITIAL RESPIRATORIO Ag',
    ],
    2: [  # Quimica
        '25 OH VITAMINA D',
        'ANION GAP',
        'APO A',
        'APO B1',
        'B2 MICROGLOBULINA TOTAL',
        'CA 72-4',
        'FOLATO',
        'GASES ARTERIALES',
        'NT-PROBNP',
        'PRO BNP',
        'PROCALCITONINA',
        'PROTEINA C REACTIVA ULTRASENSIBLE',
        'RELACION FOSFORO /CREATININA',
        'VITAMINA B12',
    ],
    1: [  # Hematologia
        'CONTAJE ABSOLUTO DE EOSINOFILOS',
        'DESCRIPCION DE PLAQUETAS',
        'DREPANOCITOS',
    ],
    7: [  # Parasitologia
        'Plasmodium falciparum',
        'Plasmodium vivax',
        'TEST DETECCION AG.PALUDISMO/MALARIA',
    ],
    10: [  # Microbiologia
        'KOH',
        'DIRECTO KOH',
    ],
    5: [  # Coagulacion
        'ANTICOAGULANTE LUPICO',
    ],
    6: [  # Uroanalisis
        'UROGEN',
    ],
}


def norm(texto):
    """Normaliza un nombre para comparar: mayusculas y espacios colapsados."""
    return ' '.join(str(texto or '').upper().split())


def conectar(ruta_bd):
    cn = win32com.client.Dispatch('ADODB.Connection')
    cn.Open(f'Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta_bd};')
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


def respaldar(ruta_bd):
    destino_dir = BASE_DIR / 'backups'
    destino_dir.mkdir(exist_ok=True)
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = destino_dir / f'ANgesLAB_antes_areas_{marca}.accdb'
    shutil.copy2(ruta_bd, destino)
    return destino


def main():
    args = list(sys.argv[1:])
    modo_aplicar = '--aplicar' in args
    args = [a for a in args if not a.startswith('--')]
    ruta_bd = Path(args[0]).resolve() if args else (BASE_DIR / 'ANgesLAB.accdb')

    if not ruta_bd.exists():
        print(f"ERROR: no se encontro la base de datos:\n  {ruta_bd}")
        return 1

    print("=" * 74)
    print("  AREA 8: TIROIDES -> HORMONAS  +  RECLASIFICACION DE PRUEBAS")
    print("=" * 74)
    print(f"Base de datos : {ruta_bd}")
    print(f"Modo          : {'APLICAR CAMBIOS' if modo_aplicar else 'SIMULACION (no escribe)'}")
    print()

    cn = conectar(str(ruta_bd))

    # --- Areas disponibles -------------------------------------------------
    areas = {a['AreaID']: a['NombreArea'] for a in consultar(cn, 'SELECT AreaID, NombreArea FROM Areas')}
    faltantes = [aid for aid in REUBICACIONES if aid not in areas]
    if faltantes:
        print(f"ERROR: faltan areas destino en la base de datos: {faltantes}")
        cn.Close()
        return 1

    area8 = consultar(cn, f'SELECT AreaID, CodigoArea, NombreArea FROM Areas WHERE AreaID = {AREA_HORMONAS}')
    if not area8:
        print(f"ERROR: no existe el area {AREA_HORMONAS}.")
        cn.Close()
        return 1
    area8 = area8[0]

    renombrar = (area8['NombreArea'] != AREA_NOMBRE or area8['CodigoArea'] != AREA_CODIGO)
    print("-- Area 8")
    if renombrar:
        print(f"   '{area8['CodigoArea']} / {area8['NombreArea']}'  ->  "
              f"'{AREA_CODIGO} / {AREA_NOMBRE}'")
    else:
        print(f"   ya es '{AREA_CODIGO} / {AREA_NOMBRE}'")
    print()

    # --- Pruebas actualmente en el area 8 ----------------------------------
    pruebas = consultar(
        cn,
        f'SELECT PruebaID, CodigoPrueba, NombrePrueba FROM Pruebas '
        f'WHERE AreaID = {AREA_HORMONAS}')
    por_nombre = {}
    for p in pruebas:
        por_nombre.setdefault(norm(p['NombrePrueba']), []).append(p)

    plan = []          # (prueba_id, nombre, area_destino)
    no_encontradas = []
    for area_destino, nombres in REUBICACIONES.items():
        for nombre in nombres:
            coincidencias = por_nombre.get(norm(nombre))
            if not coincidencias:
                no_encontradas.append(nombre)
                continue
            for p in coincidencias:
                plan.append((p['PruebaID'], p['NombrePrueba'], area_destino))

    ids_a_mover = {pid for pid, _n, _a in plan}
    se_quedan = [p for p in pruebas if p['PruebaID'] not in ids_a_mover]

    # --- Informe -----------------------------------------------------------
    print(f"-- Salen del area 8 ({len(plan)} pruebas)")
    for area_destino in sorted(REUBICACIONES, key=lambda a: areas[a]):
        del_area = [(pid, n) for pid, n, a in plan if a == area_destino]
        if not del_area:
            continue
        print(f"   -> {areas[area_destino]} ({len(del_area)})")
        for pid, nombre in sorted(del_area, key=lambda x: x[1]):
            print(f"        {pid:<5} {nombre}")
    print()

    print(f"-- Se quedan en Hormonas ({len(se_quedan)} pruebas)")
    for p in sorted(se_quedan, key=lambda x: str(x['NombrePrueba'])):
        print(f"        {p['PruebaID']:<5} {p['NombrePrueba']}")
    print()

    if no_encontradas:
        print(f"-- Ya reubicadas o inexistentes ({len(no_encontradas)})")
        for n in no_encontradas:
            print(f"        {n}")
        print()

    print("-" * 74)
    print(f"A reubicar: {len(plan)}   Quedan en Hormonas: {len(se_quedan)}   "
          f"Renombrar area: {'si' if renombrar else 'no'}")
    print("-" * 74)

    if not modo_aplicar:
        cn.Close()
        print("\nSimulacion terminada. Nada fue modificado.")
        print("Para aplicar los cambios ejecute:")
        print("    python reclasificar_areas.py --aplicar")
        return 0

    if not plan and not renombrar:
        cn.Close()
        print("\nNo hay nada que cambiar.")
        return 0

    respaldo = respaldar(ruta_bd)
    print(f"\nCopia de seguridad: {respaldo}")

    movidas = 0
    try:
        if renombrar:
            cn.Execute(
                f"UPDATE Areas SET NombreArea = '{AREA_NOMBRE}', "
                f"CodigoArea = '{AREA_CODIGO}', Secuencia = {AREA_SECUENCIA}, "
                f"Activo = True WHERE AreaID = {AREA_HORMONAS}")
            print(f"Area {AREA_HORMONAS} renombrada a '{AREA_NOMBRE}'.")
        for pid, _nombre, area_destino in plan:
            cn.Execute(f"UPDATE Pruebas SET AreaID = {area_destino} "
                       f"WHERE PruebaID = {pid}")
            movidas += 1
    finally:
        cn.Close()

    print(f"Pruebas reubicadas: {movidas}")
    print("\nListo.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

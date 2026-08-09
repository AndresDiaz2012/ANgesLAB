# -*- coding: utf-8 -*-
"""
reubicar_serologia.py
=====================
Reparte el area Serologia entre las areas nuevas Infecciosas (12) e
Inmunologicas (13), y saca de ella las pruebas que estaban mal ubicadas.

Serologia acumulaba 170 pruebas de naturaleza muy distinta: serologia
infecciosa, autoinmunidad, complemento, inmunoglobulinas e incluso pruebas
de coagulacion. El criterio aplicado es:

  Infecciosas (12)   deteccion de agentes infecciosos y su respuesta
                     inmune: hepatitis, VIH, TORCH, dengue, COVID,
                     Chagas, micoplasma, clamidias, hongos, VDRL...
  Inmunologicas (13) autoanticuerpos, complemento, inmunoglobulinas,
                     crioglobulinas, celulas LE, Coombs e inmunohematologia
  Coagulacion (5)    TP, INR y factor XIII, que nada tienen que hacer en
                     serologia
  Quimica (2)        Proteina C Reactiva cuantitativa y B2 microglobulina
                     (en este catalogo 'PCR' es Proteina C Reactiva: ver
                     'PCR CUANTIFICADA' y 'PCR (ALTA SENSIBILIDAD)' en Quimica)
  Hormonas (8)       anticuerpos anti-peroxidasa tiroidea, junto al resto
                     de autoanticuerpos tiroideos del perfil tiroideo

Lo que NO se toca (queda en Serologia y se reporta al final):
  pruebas de nombre dudoso o ambiguo, para revisarlas a mano.

Caracteristicas:
  - Solo actua sobre pruebas que siguen en Serologia: es idempotente.
  - Copia de seguridad automatica antes de escribir.
  - Modo simulacion por defecto.

Uso:
    python reubicar_serologia.py                    # simulacion
    python reubicar_serologia.py --aplicar          # aplica los cambios

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

AREA_ORIGEN = 9   # Serologia

# AreaID destino -> nombres exactos tal como estan en el catalogo
REUBICACIONES = {
    12: [  # Infecciosas
        'ADENOVIRUS Ag',
        'ADENOVIRUS RESPIRATORIO-AG',
        'ANTICUERPOS  ANTI- RUBEOLA',
        'ANTICUERPOS ANTI-RUBEOLA IGG',
        'ANTICUERPOS ANTI-RUBEOLA IGM',
        'ANTICUERPOS IgG SARS-CoV2',
        'ANTICUERPOS IgG/IgM COVID-19',
        'ANTICUERPOS IgM SARS-CoV2:',
        'ANTIGENO DE SUPERFICIE  (HBVAgS )',
        'ANTIGENO DE SUPERFICIE (HBS AG)',
        'ANTIGENO DE SUPERFICIE (HBVAgSAb)',
        'ANTIGENOS FEBRILES',
        'ANTI-HBVcore',
        'ANTI-HCV',
        'ASLO CUANTITATIVO',
        'ASPERGILLUS FUMIGATUS',
        'CHAGAS',
        'CHAGATEST',
        'CHIKUNGUNYA IgM',
        'CHLAMIDYA TRACHOMATIS IGG',
        'CHLAMYDIA PNEUMONIAE IGG',
        'CHLAMYDIA PNEUMONIAE IGM',
        'CHLAMYDIA TRACHOMATIS IGM',
        'CLAMIDEAS  IGM',
        'COCCIDIOIDES',
        'COVID 19 Ag',
        'COVID-19',
        'DENGUE AG-NS1',
        'DENGUE IgG -  IgM',
        'DENGUE ZIKA CHICUNGUNYA',
        'DETECCION ANTIGENO SARS CoV-2 (COVID-19)',
        'EPSTEIN  BARR  IGG',
        'EPSTEIN  BARR  IGM',
        'ERLICHIA ANTICUERPOS TOTALES',
        'FTA ABS',
        'HAV ANTICUERPOS TOTALES',
        'Helicobacter pilory',
        'HELICOBACTER PYLORI IGG',
        'HELICOBACTER PYLORI IGM',
        'HEPATITIS  "A" IgG  ( HAV IgG )',
        'HEPATITIS  "A" IgM  ( HAV IgM )',
        'HEPATITIS A IGG',
        'HEPATITIS A IGM',
        'HEPATITIS B ANTICORE',
        'HEPATITIS C',
        'HEPATITIS C CUANTIFICADO',
        'HERPES SIMPLE I IgG',
        'HERPES SIMPLE I IgM',
        'HERPES SIMPLE II IgG',
        'HERPES SIMPLE II IgM',
        'HISTOPLASMA',
        'HISTOPLASMA CAPSULATUM (Detección por PCR )',
        'HIV',
        'HIV ( CUALITATIVA)',
        'HIV 1 y 2',
        'HIV 1/2',
        'HIV ELISA 4TA GENERACION',
        'HTLV 1&2',
        'HTLV I',
        'HTLV II',
        'INFLUENZA A - ANTIGENO',
        'INFLUENZA A (VIRUS)',
        'INFLUENZA B - ANTIGENO',
        'INFLUENZA B (VIRUS)',
        'MACHADO GUERREIRO (CHAGAS)',
        'MICOPLASMA IgG',
        'MICOPLASMA IgM',
        'MICOPLASMA PNEUMONIAE Ag',
        'MONOTEST',
        'MYCOPLASMA PNEUMONIAE IGG',
        'MYCOPLASMA PNEUMONIAE IGM',
        'PARACOCCIDIOIDES',
        'PERFIL HEPATITIS',
        'PERFIL TORCH',
        'PNEUMO SCREEN',
        'PROTEUS OX-19',
        'RUBEOLA IgG',
        'RUBEOLA IgM',
        'SARAMPION  IGG',
        'SARAMPION  IGM',
        'TEST DE TOXOPLASMOSIS (HAI)',
        'Toxoplasma gondii  IgM',
        'Toxoplasma gondii IgG',
        'VDRL',
        'Virus Epstein-Barr (IgG)',
        'Virus Epstein-Barr (IgM)',
        'VIRUS RESPIRATORIO SYNCYTIAL',
        'VIRUS SINCITIAL RESPIRATORIO Ag',
    ],
    13: [  # Inmunologicas
        'AGLUTININAS ANTI-RH',
        'ANA',
        'ANCA C (ANTI PR3)',
        'ANCA P (ANTI-MPO)',
        'ANTI DNA',
        'ANTI DNA DOBLE CADENA',
        'ANTI FOSFOLIPIDO IgG',
        'ANTI FOSFOLIPIDO IgM',
        'ANTI PEPTIDO CITRULINADO (ANTI CCP)',
        'ANTI RO-52',
        'ANTI RO-60',
        'ANTI-ACTINA',
        'ANTI-AG CITOSOLICO HEPATICO',
        'ANTI-AG. SOLUBLE HEPATICO/AG DE HIGADO Y PANCREAS',
        'ANTICARDIOLIPINA IgG',
        'ANTICARDIOLIPINA IgM',
        'ANTI-CARDIOLIPINAS IgG',
        'ANTI-CARDIOLIPINAS IgM',
        'ANTICUERPOS ANTI MITOCONDRIALES',
        'ANTICUERPOS ANTI-CITOPLASMA DE NEUTROFILOS (ANCA)',
        'ANTICUERPOS ANTI-DNP',
        'ANTICUERPOS ANTI-INSULINA',
        'ANTICUERPOS ANTI-LA (SSB)',
        'ANTICUERPOS ANTI-MUSCULO LISO (SMA)',
        'ANTICUERPOS ANTIMÚSCULO LISO (SMA)',
        'ANTICUERPOS ANTINUCLEARES (ANA)',
        'ANTICUERPOS ANTINUCLEARES (ANA) SCREEN IgG',
        'ANTICUERPOS ANTI-RIBOSOMAS (ANTI-RIB-P)',
        'ANTICUERPOS ANTI-RNP 70',
        'ANTICUERPOS ANTI-RO (SSA)',
        'ANTICUERPOS ANTI-Sm',
        'ANTI-DESMINA',
        'ANTI-DNA',
        'ANTI-DS DNA IgG',
        'ANTI-GLIADINA DEAMINADA IgA GLIADINA 2DA. GENERACION',
        'ANTI-GLIADINA IgA',
        'ANTI-GLIADINA IgG',
        'ANTI-GP200',
        'ANTI-MICROSOMA DE HIGADO Y RIÑON',
        'ANTI-MIOSINA',
        'ANTI-MITOCONDRIALES',
        'ANTI-MUSCULO LISO',
        'ANTI-SP100',
        'B2 GLICOPROTEINA IgG',
        'B2 GLICOPROTEINA IgM',
        'C3',
        'C4',
        'CADENA LIVIANA KAPPA EN SUERO',
        'CADENA LIVIANA LAMBDA EN SUERO',
        'CARDIOLIPINAS IgG',
        'CARDIOLIPINAS IgM',
        'CELULAS  LE',
        'CH50',
        'COMPLEMENTO C3',
        'COMPLEMENTO C4',
        'COMPLEMENTO CH-50',
        'COOMBS DIRECTO',
        'COOMBS INDIRECTO',
        'COOMS DIRECTO',
        'COOMS INDIRECTO',
        'CRIOGLOBULINAS',
        'EOSINOFILOS EN MOCO NASAL',
        'FACTOR REUMATOIDEO IgG',
        'IgA',
        'IgG',
        'IgM',
        'IGM  SERICA',
        'INMUNOGLOBULINA E',
        'INMUNOGLOBULINA G',
        'INMUNOGLOBULINA M',
        'RA TEST (FACTOR REUMATOIDEO LATEX)',
    ],
    5: [  # Coagulacion
        'FACTOR XIII UREA 5 MOLAR',
        'INR',
        'TP',
    ],
    2: [  # Quimica
        'B2 MICROGLOBULINA.',
        'PCR CUANTITATIVA',
    ],
    8: [  # Hormonas (autoanticuerpos tiroideos del perfil tiroideo)
        'ANTICUERPOS ANTI-PEROXIDASA (TPO)',
    ],
}


def norm(texto):
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
    # El respaldo va junto a la BD que se migra, no junto al script:
    # ejecutado desde la USB dejaba copias de la base del cliente en
    # la memoria, llenandola y sacando datos de pacientes del local.
    destino_dir = Path(ruta_bd).resolve().parent / 'backups'
    destino_dir.mkdir(exist_ok=True)
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = destino_dir / f'ANgesLAB_antes_serologia_{marca}.accdb'
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

    print("=" * 76)
    print("  REPARTO DE SEROLOGIA -> INFECCIOSAS / INMUNOLOGICAS")
    print("=" * 76)
    print(f"Base de datos : {ruta_bd}")
    print(f"Modo          : {'APLICAR CAMBIOS' if modo_aplicar else 'SIMULACION (no escribe)'}")
    print()

    cn = conectar(str(ruta_bd))
    areas = {a['AreaID']: a['NombreArea']
             for a in consultar(cn, 'SELECT AreaID, NombreArea FROM Areas')}
    faltantes = [a for a in REUBICACIONES if a not in areas]
    if faltantes:
        print(f"ERROR: faltan areas destino: {faltantes}")
        cn.Close()
        return 1

    pruebas = consultar(
        cn, f'SELECT PruebaID, NombrePrueba FROM Pruebas WHERE AreaID = {AREA_ORIGEN}')
    por_nombre = {}
    for p in pruebas:
        por_nombre.setdefault(norm(p['NombrePrueba']), []).append(p)

    plan, no_encontradas = [], []
    for destino, nombres in REUBICACIONES.items():
        for nombre in nombres:
            coincidencias = por_nombre.get(norm(nombre))
            if not coincidencias:
                no_encontradas.append(nombre)
                continue
            for p in coincidencias:
                plan.append((p['PruebaID'], p['NombrePrueba'], destino))

    ids = {pid for pid, _n, _d in plan}
    se_quedan = [p for p in pruebas if p['PruebaID'] not in ids]

    for destino in sorted(REUBICACIONES, key=lambda a: areas[a]):
        del_area = [(pid, n) for pid, n, d in plan if d == destino]
        if not del_area:
            continue
        print(f"-- Serologia -> {areas[destino]} ({len(del_area)})")
        for pid, nombre in sorted(del_area, key=lambda x: str(x[1])):
            print(f"      {pid:<5} {nombre}")
        print()

    print(f"-- Se quedan en Serologia ({len(se_quedan)})")
    for p in sorted(se_quedan, key=lambda x: str(x['NombrePrueba'])):
        print(f"      {p['PruebaID']:<5} {p['NombrePrueba']}")
    print()

    if no_encontradas:
        print(f"-- Ya reubicadas o no halladas ({len(no_encontradas)})")
        for n in no_encontradas:
            print(f"      {n}")
        print()

    print("-" * 76)
    print(f"A reubicar: {len(plan)}   Se quedan en Serologia: {len(se_quedan)}")
    print("-" * 76)

    if not modo_aplicar:
        cn.Close()
        print("\nSimulacion terminada. Nada fue modificado.")
        print("Para aplicar los cambios ejecute:")
        print("    python reubicar_serologia.py --aplicar")
        return 0

    if not plan:
        cn.Close()
        print("\nNo hay nada que reubicar.")
        return 0

    respaldo = respaldar(ruta_bd)
    print(f"\nCopia de seguridad: {respaldo}")

    movidas = 0
    try:
        for pid, _nombre, destino in plan:
            cn.Execute(f"UPDATE Pruebas SET AreaID = {destino} WHERE PruebaID = {pid}")
            movidas += 1
    finally:
        cn.Close()

    print(f"Pruebas reubicadas: {movidas}")
    print("\nListo.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

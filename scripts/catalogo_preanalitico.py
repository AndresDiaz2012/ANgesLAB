# -*- coding: utf-8 -*-
"""
catalogo_preanalitico.py
========================
Completa los datos preanaliticos del catalogo: tipo de muestra y ayuno.

Sin esos datos la ventana de Registro de Solicitud no puede decir que tubo
extraer ni avisar del ayuno, por mucho codigo que se escriba. Hoy solo el
5% de las pruebas activas tiene tipo de muestra asignado.

El trabajo es de bioanalista, no de programador. Este script solo lo hace
rapido: propone un valor para cada prueba y deja que se revise en Excel.

Uso:
    python scripts/catalogo_preanalitico.py --exportar
        Genera catalogo_preanalitico.csv con una propuesta por prueba.
        Abrirlo en Excel, corregir la columna TipoMuestra y Ayuno, guardar.

    python scripts/catalogo_preanalitico.py --importar
        Valida el CSV y aplica los cambios. Hace respaldo antes.
        Solo escribe las filas marcadas OK en la columna Aplicar.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import csv
import io
import os
import re
import shutil
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# El script vive en scripts/, la aplicacion un nivel arriba
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

CSV = BASE_DIR / 'catalogo_preanalitico.csv'


def _conectar(ruta):
    import win32com.client
    conn = win32com.client.Dispatch('ADODB.Connection')
    conn.Open(f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta};")
    return conn


def _q(conn, sql):
    rs = conn.Execute(sql)[0]
    cols = [rs.Fields.Item(i).Name for i in range(rs.Fields.Count)]
    out = []
    while not rs.EOF:
        out.append({cols[i]: rs.Fields.Item(i).Value for i in range(len(cols))})
        rs.MoveNext()
    rs.Close()
    return out


def _norm(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]+', ' ', s)


# ── Heuristica de propuesta ────────────────────────────────────────────
# El nombre manda sobre el area: un urocultivo es ORINA aunque este en MIC.
POR_NOMBRE = [
    (('urocultivo', 'uroanalisis', 'orina', 'urinario', 'urogen',
      'microalbuminuria', 'depuracion'), 'ORINA'),
    (('coprocultivo', 'heces', 'copro', 'parasit', 'oxiuros', 'sangre oculta',
      'azucares reductores', 'sudan'), 'HECES'),
    (('esputo', 'bk ', 'baciloscopia'), 'ESPUTO'),
    (('cefalorraquideo', 'lcr'), 'LCR'),
    (('semen', 'espermo', 'seminal'), 'SEMEN'),
    (('exudado', 'secrecion', 'hisopado', 'faringe', 'vaginal', 'uretral',
      'herida', 'absceso'), 'EXUDADO'),
    (('sangre', 'suero', 'plasma', 'hemo', 'serico', 'plasmodium',
      'paludismo', 'malaria', 'gota gruesa'), 'SANGRE'),
]
# Si el nombre no decide, el area propone
POR_AREA = {
    'HEM': 'SANGRE', 'QUI': 'SANGRE', 'COA': 'SANGRE', 'HOR': 'SANGRE',
    'SER': 'SANGRE', 'INF': 'SANGRE', 'INM': 'SANGRE', 'REN': 'SANGRE',
    'URO': 'ORINA', 'PAR': 'HECES', 'MIC': 'EXUDADO', 'GEN': 'SANGRE',
}
# Pruebas que si requieren ayuno (el tipo de muestra es demasiado grueso)
AYUNO = ('glicemia', 'glucosa', 'colesterol', 'trigliceri', 'lipid', 'hdl',
         'ldl', 'vldl', 'insulina', 'curva de tolerancia', 'perfil 20',
         'quimica sanguinea', 'acido urico', 'hierro serico')


def _contiene(texto, clave):
    """Coincidencia por palabra, no por subcadena.

    Sin esto 'copro' casa dentro de 'gliCOPROteina' y la B2 glicoproteina
    acaba propuesta como muestra de heces.
    """
    return re.search(r'\b' + re.escape(clave.strip()), texto) is not None


def proponer(nombre, area):
    n = _norm(nombre)
    for claves, tipo in POR_NOMBRE:
        if any(_contiene(n, k) for k in claves):
            return tipo, 'nombre'
    return POR_AREA.get(area, 'SANGRE'), 'area'


def proponer_ayuno(nombre):
    n = _norm(nombre)
    return ('Si', 8) if any(_contiene(n, k) for k in AYUNO) else ('No', 0)


# ── Exportar ───────────────────────────────────────────────────────────
def exportar(ruta_db):
    conn = _conectar(ruta_db)
    tipos = {t['CodigoTipoMuestra']: t['TipoMuestraID']
             for t in _q(conn, "SELECT TipoMuestraID, CodigoTipoMuestra "
                               "FROM TiposMuestra WHERE Activo=True")}
    filas = _q(conn, """
        SELECT p.PruebaID, p.CodigoPrueba, p.NombrePrueba, p.TipoMuestraID,
               p.RequiereAyuno, p.HorasAyuno, a.CodigoArea
        FROM Pruebas p LEFT JOIN Areas a ON p.AreaID = a.AreaID
        WHERE p.Activo=True
        ORDER BY a.CodigoArea, p.NombrePrueba
    """)
    inverso = {v: k for k, v in tipos.items()}

    pendientes = 0
    with io.open(CSV, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['PruebaID', 'Codigo', 'Area', 'Nombre',
                    'TipoMuestra', 'Ayuno', 'HorasAyuno', 'Origen', 'Aplicar'])
        for f in filas:
            area = f.get('CodigoArea') or '?'
            nombre = f.get('NombrePrueba') or ''
            actual = inverso.get(f.get('TipoMuestraID'))
            if actual:
                tipo, origen, aplicar = actual, 'ya asignado', ''
                ayuno = 'Si' if f.get('RequiereAyuno') else 'No'
                horas = int(f.get('HorasAyuno') or 0)
            else:
                tipo, origen = proponer(nombre, area)
                ayuno, horas = proponer_ayuno(nombre)
                aplicar, pendientes = 'OK', pendientes + 1
            w.writerow([f['PruebaID'], f.get('CodigoPrueba') or '', area,
                        nombre, tipo, ayuno, horas, origen, aplicar])
    conn.Close()

    print(f"Generado: {CSV.name}")
    print(f"  Pruebas activas          : {len(filas)}")
    print(f"  Ya tenian tipo de muestra: {len(filas) - pendientes}")
    print(f"  Con propuesta a revisar  : {pendientes}")
    print(f"\n  Tipos validos: {', '.join(sorted(tipos))}")
    print("\n  Abralo en Excel. Corrija TipoMuestra/Ayuno donde haga falta.")
    print("  Deje 'Aplicar' en OK para escribirla; borrelo para omitirla.")
    print("  Despues:  python scripts/catalogo_preanalitico.py --importar")


# ── Importar ───────────────────────────────────────────────────────────
def importar(ruta_db):
    if not CSV.exists():
        print(f"No existe {CSV.name}. Ejecute primero --exportar.")
        return 1

    conn = _conectar(ruta_db)
    tipos = {t['CodigoTipoMuestra']: t['TipoMuestraID']
             for t in _q(conn, "SELECT TipoMuestraID, CodigoTipoMuestra "
                               "FROM TiposMuestra WHERE Activo=True")}

    cambios, errores = [], []
    with io.open(CSV, encoding='utf-8-sig', newline='') as fh:
        for i, r in enumerate(csv.DictReader(fh, delimiter=';'), 2):
            if (r.get('Aplicar') or '').strip().upper() != 'OK':
                continue
            tipo = (r.get('TipoMuestra') or '').strip().upper()
            if tipo not in tipos:
                errores.append(f"linea {i}: tipo '{tipo}' no existe "
                               f"({r.get('Codigo')})")
                continue
            try:
                pid = int(r['PruebaID'])
                horas = int(float(r.get('HorasAyuno') or 0))
            except ValueError:
                errores.append(f"linea {i}: numero invalido")
                continue
            ayuno = (r.get('Ayuno') or 'No').strip().lower().startswith('s')
            cambios.append((pid, tipos[tipo], ayuno, horas, r.get('Codigo')))

    print(f"Filas marcadas para aplicar: {len(cambios)}")
    if errores:
        print(f"\nERRORES ({len(errores)}) — no se aplica nada hasta corregirlos:")
        for e in errores[:20]:
            print("   ", e)
        conn.Close()
        return 1
    if not cambios:
        print("Nada que aplicar.")
        conn.Close()
        return 0

    conn.Close()
    sello = datetime.now().strftime('%Y%m%d_%H%M%S')
    respaldo = BASE_DIR / 'backups' / f'ANgesLAB_antes_preanalitico_{sello}.accdb'
    respaldo.parent.mkdir(exist_ok=True)
    shutil.copy2(ruta_db, respaldo)
    print(f"Respaldo: backups/{respaldo.name}")

    conn = _conectar(ruta_db)
    for pid, tmid, ayuno, horas, _cod in cambios:
        conn.Execute(
            f"UPDATE Pruebas SET TipoMuestraID={tmid}, "
            f"RequiereAyuno={'True' if ayuno else 'False'}, "
            f"HorasAyuno={horas} WHERE PruebaID={pid}")

    n = _q(conn, "SELECT COUNT(*) AS n FROM Pruebas "
                 "WHERE Activo=True AND TipoMuestraID IS NOT NULL")[0]['n']
    tot = _q(conn, "SELECT COUNT(*) AS n FROM Pruebas WHERE Activo=True")[0]['n']
    conn.Close()
    print(f"\nAplicados {len(cambios)} cambios.")
    print(f"Cobertura de tipo de muestra: {n}/{tot} ({100*n/tot:.0f}%)")
    return 0


if __name__ == '__main__':
    db = BASE_DIR / 'ANgesLAB.accdb'
    if not db.exists():
        print(f"No se encuentra {db}")
        sys.exit(1)
    if '--exportar' in sys.argv:
        exportar(str(db))
    elif '--importar' in sys.argv:
        sys.exit(importar(str(db)))
    else:
        print(__doc__)

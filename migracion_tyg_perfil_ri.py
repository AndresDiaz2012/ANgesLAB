# -*- coding: utf-8 -*-
"""
migracion_tyg_perfil_ri.py
==========================
Agrega los parametros 'Trigliceridos' e 'Indice TyG' a la prueba
"PERFIL DE RESISTENCIA A INSULINA" para habilitar el auto-calculo del
indice TyG (Trigliceridos-Glucosa), complementario del HOMA-IR.

Por que se necesitan AMBOS:
  El auto-calculo trabaja dentro de la MISMA prueba: junta los valores de
  los parametros de ese perfil. El indice TyG = ln[(TG x Glucosa)/2], por lo
  que el perfil debe contener Trigliceridos (entrada) y Glicemia (ya existe).
  'Indice TyG' se deja SIN formula: lo llena el motor de calculos por nombre.

Caracteristicas:
  - Idempotente: se puede ejecutar varias veces sin duplicar.
  - Multi-BD: recibe la ruta de la BD como argumento (o usa la del proyecto).

Uso:
    python migracion_tyg_perfil_ri.py                 # BD del proyecto
    python migracion_tyg_perfil_ri.py "D:\\ANgesLab\\ANgesLAB.accdb"

IMPORTANTE: ejecutar con ANgesLAB CERRADO.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

NOMBRE_PRUEBA = "PERFIL DE RESISTENCIA A INSULINA"

# Parametros a garantizar (idempotencia por CodigoParametro)
PARAM_TRIGLICERIDOS = {
    'CodigoParametro': 'TGL_RI',
    'NombreParametro': 'Triglicéridos',
    'NombreCorto': 'TG',
    'TipoResultado': 'NUMERICO',
    'Observaciones': '< 150',        # valor de referencia (mg/dL)
    'Decimales': 2,
    'EsCalculado': False,
    'unidad_simbolo': 'mg/dL',
    'formula': None,
}
PARAM_TYG = {
    'CodigoParametro': 'IDX_TYG',
    'NombreParametro': 'Índice TyG',
    'NombreCorto': 'TyG',
    'TipoResultado': 'NUMERICO',
    'Observaciones': '< 8.75',       # corte de resistencia a insulina (ln)
    'Decimales': 2,
    'EsCalculado': True,
    'unidad_simbolo': None,          # adimensional
    'formula': None,                 # SIN formula: lo llena el motor por nombre
}


def _resolver_db(argv):
    if len(argv) > 1 and argv[1].strip():
        return Path(argv[1].strip())
    return BASE_DIR / "ANgesLAB.accdb"


def main(argv):
    ruta = _resolver_db(argv)
    if not ruta.exists():
        print(f"[ERROR] No se encontro la base de datos: {ruta}")
        return 1

    try:
        import win32com.client
    except ImportError:
        print("[ERROR] pywin32 no esta instalado.")
        return 1

    print(f"Base de datos: {ruta}")
    conn = win32com.client.Dispatch("ADODB.Connection")
    try:
        conn.Open(f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta};")
    except Exception as e:
        print(f"[ERROR] No se pudo abrir la BD (¿ANgesLAB abierto?): {e}")
        return 1

    def q(sql):
        rs = win32com.client.Dispatch("ADODB.Recordset")
        rs.Open(sql, conn, 1, 1)
        rows = []
        while not rs.EOF:
            rows.append({rs.Fields.Item(i).Name: rs.Fields.Item(i).Value
                         for i in range(rs.Fields.Count)})
            rs.MoveNext()
        rs.Close()
        return rows

    def esc(v):
        return str(v).replace("'", "''")

    try:
        # 1) Localizar la prueba
        pr = q(f"SELECT PruebaID FROM [Pruebas] WHERE [NombrePrueba]='{esc(NOMBRE_PRUEBA)}'")
        if not pr:
            print(f"[ERROR] No existe la prueba '{NOMBRE_PRUEBA}' en esta BD.")
            return 1
        prueba_id = int(pr[0]['PruebaID'])
        print(f"Prueba encontrada: PruebaID={prueba_id}")

        # Seccion comun de los parametros actuales del perfil (para agrupar)
        secs = q(f"SELECT p.[Seccion] AS S FROM ([Parametros] p "
                 f"INNER JOIN [ParametrosPrueba] pp ON p.[ParametroID]=pp.[ParametroID]) "
                 f"WHERE pp.[PruebaID]={prueba_id} AND p.[Seccion] IS NOT NULL")
        seccion = secs[0]['S'] if secs else NOMBRE_PRUEBA

        # Parametros ya vinculados (por nombre normalizado simple)
        actuales = q(f"SELECT p.[ParametroID] AS ID, p.[NombreParametro] AS N "
                     f"FROM ([Parametros] p INNER JOIN [ParametrosPrueba] pp "
                     f"ON p.[ParametroID]=pp.[ParametroID]) WHERE pp.[PruebaID]={prueba_id}")
        nombres_actuales = {str(a['N']).strip().lower() for a in actuales}

        def unidad_id(simbolo):
            if not simbolo:
                return None
            u = q(f"SELECT [UnidadID] FROM [Unidades] WHERE [Simbolo]='{esc(simbolo)}'")
            return int(u[0]['UnidadID']) if u else None

        def sig_secuencia():
            m = q(f"SELECT MAX([Secuencia]) AS M FROM [ParametrosPrueba] WHERE [PruebaID]={prueba_id}")
            return (int(m[0]['M']) if m and m[0]['M'] is not None else 0) + 1

        def obtener_o_crear_parametro(spec):
            """Devuelve ParametroID; crea el parametro si no existe (por codigo)."""
            ex = q(f"SELECT [ParametroID] FROM [Parametros] "
                   f"WHERE [CodigoParametro]='{esc(spec['CodigoParametro'])}'")
            if ex:
                return int(ex[0]['ParametroID'])
            uid = unidad_id(spec['unidad_simbolo'])
            uid_sql = str(uid) if uid is not None else "NULL"
            formula_sql = f"'{esc(spec['formula'])}'" if spec['formula'] else "NULL"
            conn.Execute(
                f"INSERT INTO [Parametros] "
                f"([CodigoParametro],[NombreParametro],[NombreCorto],[UnidadID],"
                f"[TipoResultado],[Decimales],[FormulaCalculo],[Observaciones],"
                f"[Activo],[Seccion],[EsCalculado]) VALUES ("
                f"'{esc(spec['CodigoParametro'])}',"
                f"'{esc(spec['NombreParametro'])}',"
                f"'{esc(spec['NombreCorto'])}',"
                f"{uid_sql},"
                f"'{esc(spec['TipoResultado'])}',"
                f"{int(spec['Decimales'])},"
                f"{formula_sql},"
                f"'{esc(spec['Observaciones'])}',"
                f"True,"
                f"'{esc(seccion)}',"
                f"{'True' if spec['EsCalculado'] else 'False'})"
            )
            nid = q("SELECT @@IDENTITY AS ID")
            return int(nid[0]['ID'])

        def vincular(param_id, nombre):
            """Vincula el parametro a la prueba si no lo esta ya."""
            ya = q(f"SELECT [ParametroPruebaID] FROM [ParametrosPrueba] "
                   f"WHERE [PruebaID]={prueba_id} AND [ParametroID]={param_id}")
            if ya:
                print(f"  = '{nombre}' ya estaba vinculado (sin cambios)")
                return False
            seq = sig_secuencia()
            conn.Execute(
                f"INSERT INTO [ParametrosPrueba] ([PruebaID],[ParametroID],[Secuencia],[Obligatorio]) "
                f"VALUES ({prueba_id},{param_id},{seq},False)"
            )
            print(f"  + '{nombre}' vinculado (Secuencia={seq})")
            return True

        cambios = 0
        for spec in (PARAM_TRIGLICERIDOS, PARAM_TYG):
            # Si ya hay un parametro con ese nombre en la prueba, no duplicar
            if spec['NombreParametro'].strip().lower() in nombres_actuales:
                print(f"  = '{spec['NombreParametro']}' ya presente en la prueba (sin cambios)")
                continue
            pid = obtener_o_crear_parametro(spec)
            if vincular(pid, spec['NombreParametro']):
                cambios += 1

        print(f"[OK] Migracion completada. Cambios aplicados: {cambios}")
        return 0
    finally:
        try:
            conn.Close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main(sys.argv))

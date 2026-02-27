# -*- coding: utf-8 -*-
"""
crear_gtt.py - Script de configuracion: Prueba de Tolerancia a la Glucosa (GTT)
================================================================================
Crea en la base de datos ANgesLAB:
  - Prueba QUIM005 - Tolerancia a la Glucosa (Curva de Glucemia)
  - Parametros habilitables por tiempo: Basal, 30min, 1h, 2h, 3h, 4h
  - Parametro especial: Dosis de carga glucosada (g)

Ejecutar una sola vez:
    python crear_gtt.py

Nota: Area QUI tiene AreaID=2 (hardcodeado en sistema ANgesLAB)
================================================================================
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import win32com.client
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "ANgesLAB.accdb")
CONN_STR = f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={DB_PATH};"

def get_conn():
    conn = win32com.client.Dispatch("ADODB.Connection")
    conn.Open(CONN_STR)
    return conn

def query_one(conn, sql):
    rs = win32com.client.Dispatch("ADODB.Recordset")
    rs.Open(sql, conn)
    if rs.EOF:
        rs.Close()
        return None
    row = {}
    for i in range(rs.Fields.Count):
        f = rs.Fields.Item(i)
        row[f.Name] = f.Value
    rs.Close()
    return row

def execute(conn, sql):
    conn.Execute(sql)

def insert_and_get_id(conn, table, data):
    cols = ', '.join(data.keys())
    vals = []
    for v in data.values():
        if v is None:
            vals.append('NULL')
        elif isinstance(v, bool):
            vals.append('True' if v else 'False')
        elif isinstance(v, (int, float)):
            vals.append(str(v))
        else:
            vals.append(f"'{str(v).replace(chr(39), chr(39)+chr(39))}'")
    sql = f"INSERT INTO [{table}] ({cols}) VALUES ({', '.join(vals)})"
    execute(conn, sql)
    row = query_one(conn, f"SELECT MAX(ParametroID) AS ID FROM Parametros") if table == 'Parametros' else \
          query_one(conn, f"SELECT MAX(PruebaID) AS ID FROM Pruebas") if table == 'Pruebas' else None
    return row['ID'] if row else None


def main():
    conn = get_conn()
    print("=== Creando Prueba de Tolerancia a la Glucosa (GTT) ===\n")

    # ------------------------------------------------------------------
    # 1. Verificar que existe el area QUI (AreaID=2)
    # ------------------------------------------------------------------
    area = query_one(conn, "SELECT AreaID FROM Areas WHERE AreaID = 2")
    if not area:
        print("ERROR: El area Quimica (AreaID=2) no existe. Ejecuta primero la app para crear las areas.")
        conn.Close()
        return
    area_id = 2
    print(f"  Area Quimica OK (AreaID={area_id})")

    # ------------------------------------------------------------------
    # 2. Crear o verificar la prueba GTT
    # ------------------------------------------------------------------
    codigo_prueba = 'QUIM005'
    prueba_existe = query_one(conn, f"SELECT PruebaID FROM Pruebas WHERE CodigoPrueba = '{codigo_prueba}'")

    if prueba_existe:
        prueba_id = prueba_existe['PruebaID']
        print(f"  Prueba {codigo_prueba} ya existe (PruebaID={prueba_id}) - verificando parametros...")
    else:
        execute(conn, f"""
            INSERT INTO Pruebas (CodigoPrueba, NombrePrueba, AreaID, Precio,
                                 Activo, RequiereAyuno, HorasAyuno, Indicaciones)
            VALUES ('{codigo_prueba}', 'Tolerancia a la Glucosa (Curva de Glucemia)',
                    {area_id}, 0, True, True, 8,
                    'Requiere ayuno de 8 horas. Se administra carga glucosada oral.')
        """)
        prueba_row = query_one(conn, "SELECT MAX(PruebaID) AS ID FROM Pruebas")
        prueba_id = prueba_row['ID']
        print(f"  Prueba {codigo_prueba} creada (PruebaID={prueba_id})")

    # ------------------------------------------------------------------
    # 3. Definicion de parametros GTT
    # Formato: (CodigoParam, NombreParam, TipoResultado, ValorRef, Seccion, Secuencia)
    #
    # CODIGOS DE PARAMETROS ESPECIALES:
    #   GTT000 = Dosis de carga glucosada (g) - SIEMPRE visible, TEXTO
    #   GTT001 = Glucosa Basal (ayunas)
    #   GTT002 = Glucosa 30 minutos
    #   GTT003 = Glucosa 1 hora
    #   GTT004 = Glucosa 2 horas
    #   GTT005 = Glucosa 3 horas
    #   GTT006 = Glucosa 4 horas
    #   GTT007 = Interpretacion (texto libre)
    #   GTT008 = Observaciones
    #
    # La SECCION codifica la habilitacion:
    #   'Carga'   -> siempre requerido (dosis)
    #   'Basal'   -> tiempo 0 (siempre incluido)
    #   '30min'   -> habilitado opciones
    #   '1h'      -> habilitado opciones
    #   '2h'      -> habilitado opciones
    #   '3h'      -> habilitado opciones
    #   '4h'      -> habilitado opciones
    #   'Resultado'-> interpretacion y observaciones
    # ------------------------------------------------------------------
    parametros_gtt = [
        # (codigo, nombre, tipo, referencia, seccion, secuencia)
        ('GTT000', 'Dosis de Carga Glucosada',   'TEXTO',    '75g adultos / 1.75 g/kg ninos (max 75g)',  'Carga',     1),
        ('GTT001', 'Glucosa Basal (0 min)',        'NUMERICO', '70 - 100 mg/dL',                           'Basal',     2),
        ('GTT002', 'Glucosa 30 minutos',           'NUMERICO', '< 200 mg/dL',                              '30min',     3),
        ('GTT003', 'Glucosa 1 hora',               'NUMERICO', '< 180 mg/dL',                              '1h',        4),
        ('GTT004', 'Glucosa 2 horas',              'NUMERICO', '< 140 mg/dL (normal) / 140-199 (IGT)',     '2h',        5),
        ('GTT005', 'Glucosa 3 horas',              'NUMERICO', '< 120 mg/dL',                              '3h',        6),
        ('GTT006', 'Glucosa 4 horas',              'NUMERICO', '< 110 mg/dL',                              '4h',        7),
        ('GTT007', 'Interpretacion',               'TEXTO',    'Normal / Tolerancia Alterada / Diabetes',  'Resultado', 8),
        ('GTT008', 'Observaciones',                'TEXTO',    '',                                          'Resultado', 9),
    ]

    # UnidadID para mg/dL
    unidad_mgdl = query_one(conn, "SELECT UnidadID FROM Unidades WHERE Simbolo = 'mg/dL'")
    if not unidad_mgdl:
        unidad_mgdl = query_one(conn, "SELECT UnidadID FROM Unidades WHERE Simbolo LIKE '%mg%dL%'")
    unidad_id_mgdl = unidad_mgdl['UnidadID'] if unidad_mgdl else None
    print(f"  Unidad mg/dL: UnidadID={unidad_id_mgdl}")

    for codigo_p, nombre_p, tipo_p, ref_p, seccion_p, secuencia_p in parametros_gtt:
        # Verificar si el parametro ya existe
        param_existe = query_one(conn, f"SELECT ParametroID FROM Parametros WHERE CodigoParametro = '{codigo_p}'")

        if param_existe:
            param_id = param_existe['ParametroID']
            # Actualizar por si cambio algo
            execute(conn, f"""
                UPDATE Parametros SET
                    NombreParametro = '{nombre_p.replace("'", "''")}',
                    TipoResultado = '{tipo_p}',
                    Observaciones = '{ref_p.replace("'", "''")}',
                    Seccion = '{seccion_p}',
                    Activo = True
                WHERE ParametroID = {param_id}
            """)
            print(f"    Param {codigo_p} ya existe (ID={param_id}) - actualizado")
        else:
            unidad_sql = f"{unidad_id_mgdl}" if (tipo_p == 'NUMERICO' and unidad_id_mgdl) else 'NULL'
            execute(conn, f"""
                INSERT INTO Parametros (CodigoParametro, NombreParametro, TipoResultado,
                                        Observaciones, Seccion, UnidadID, Activo)
                VALUES ('{codigo_p}', '{nombre_p.replace("'", "''")}', '{tipo_p}',
                        '{ref_p.replace("'", "''")}', '{seccion_p}',
                        {unidad_sql}, True)
            """)
            param_row = query_one(conn, "SELECT MAX(ParametroID) AS ID FROM Parametros")
            param_id = param_row['ID']
            print(f"    Param {codigo_p} creado (ID={param_id})")

        # Vincular parametro a la prueba si no existe el vinculo
        vinculo = query_one(conn,
            f"SELECT ParametroPruebaID FROM ParametrosPrueba "
            f"WHERE PruebaID = {prueba_id} AND ParametroID = {param_id}"
        )
        if not vinculo:
            execute(conn, f"""
                INSERT INTO ParametrosPrueba (PruebaID, ParametroID, Secuencia, Obligatorio)
                VALUES ({prueba_id}, {param_id}, {secuencia_p}, True)
            """)
            print(f"      -> Vinculado a prueba (secuencia={secuencia_p})")
        else:
            execute(conn, f"""
                UPDATE ParametrosPrueba SET Secuencia = {secuencia_p}
                WHERE PruebaID = {prueba_id} AND ParametroID = {param_id}
            """)

    print(f"\n=== GTT creada exitosamente ===")
    print(f"   Codigo: {codigo_prueba}")
    print(f"   PruebaID: {prueba_id}")
    print(f"   Area: Quimica (ID=2)")
    print(f"   Parametros: {len(parametros_gtt)}")
    print(f"\nRecuerde configurar el precio en Configuracion > Pruebas")

    conn.Close()


if __name__ == '__main__':
    main()

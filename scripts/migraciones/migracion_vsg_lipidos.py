# -*- coding: utf-8 -*-
"""
migracion_vsg_lipidos.py
========================
Dos ajustes de catalogo:

1. VSG: la prueba solo permitia reportar una lectura. Se pasa a reportar la
   PRIMERA HORA y la SEGUNDA HORA, y se agrega el INDICE DE KATZ como
   parametro calculado.

       Indice de Katz = (VSG 1a hora + (VSG 2a hora / 2)) / 2

   Promedia la primera hora con la mitad de la segunda: corrige la
   aceleracion propia de la segunda lectura y da un valor mas estable.

2. Perfil Lipidico: los lipidos totales ya se calculaban en el motor
   (colesterol total x 1.5 + trigliceridos) pero el perfil no tenia el
   parametro donde escribirlos. Se agrega como calculado.

El motor de calculos rellena ambos automaticamente al capturar resultados;
este script solo crea los parametros en el catalogo.

Caracteristicas:
  - Idempotente: no duplica parametros ya existentes.
  - Copia de seguridad automatica antes de escribir.
  - Modo simulacion por defecto.

Uso:
    python migracion_vsg_lipidos.py                 # simulacion
    python migracion_vsg_lipidos.py --aplicar       # aplica los cambios

IMPORTANTE: ejecutar con ANgesLAB CERRADO.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import shutil
import sys
from datetime import datetime
from pathlib import Path

# El script vive en scripts/migraciones/, la aplicacion dos niveles arriba
BASE_DIR = Path(__file__).resolve().parents[2]

try:
    import win32com.client
except ImportError:
    print("ERROR: falta pywin32.  pip install pywin32")
    sys.exit(1)


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


def esc(texto):
    return str(texto or '').replace("'", "''")


def respaldar(ruta):
    # El respaldo va junto a la BD que se migra, no junto al script:
    # ejecutado desde la USB dejaba copias de la base del cliente en
    # la memoria, llenandola y sacando datos de pacientes del local.
    destino_dir = Path(ruta).resolve().parent / 'backups'
    destino_dir.mkdir(exist_ok=True)
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = destino_dir / f'ANgesLAB_antes_vsg_lipidos_{marca}.accdb'
    shutil.copy2(ruta, destino)
    return destino


def id_unidad(cn, simbolo):
    """Devuelve el UnidadID del simbolo, creandolo si hace falta."""
    fila = uno(cn, f"SELECT UnidadID FROM Unidades WHERE Simbolo = '{esc(simbolo)}'")
    if fila:
        return fila['UnidadID']
    cn.Execute(f"INSERT INTO Unidades (CodigoUnidad, NombreUnidad, Simbolo, Activo) "
               f"VALUES ('{esc(simbolo)[:20]}', '{esc(simbolo)}', "
               f"'{esc(simbolo)}', True)")
    fila = uno(cn, f"SELECT TOP 1 UnidadID FROM Unidades "
                   f"WHERE Simbolo = '{esc(simbolo)}' ORDER BY UnidadID DESC")
    return fila['UnidadID'] if fila else None


def asegurar_parametro(cn, codigo, nombre, unidad, seccion, referencia,
                       es_calculado, aplicar, acciones):
    """Crea el parametro si no existe. Devuelve su ParametroID."""
    fila = uno(cn, f"SELECT ParametroID, NombreParametro FROM Parametros "
                   f"WHERE CodigoParametro = '{esc(codigo)}'")
    if fila:
        return fila['ParametroID']

    acciones.append(f"crear parametro {codigo} - {nombre}")
    if not aplicar:
        return None

    uid = id_unidad(cn, unidad) if unidad else None
    cn.Execute(
        "INSERT INTO Parametros "
        "(CodigoParametro, NombreParametro, TipoResultado, UnidadID, Seccion, "
        " Observaciones, EsCalculado, Decimales, Activo) VALUES ("
        f"'{esc(codigo)}', '{esc(nombre)}', 'NUMERICO', "
        f"{uid if uid else 'NULL'}, '{esc(seccion)}', '{esc(referencia)}', "
        f"{'True' if es_calculado else 'False'}, 1, True)")
    fila = uno(cn, f"SELECT TOP 1 ParametroID FROM Parametros "
                   f"WHERE CodigoParametro = '{esc(codigo)}' ORDER BY ParametroID DESC")
    return fila['ParametroID'] if fila else None


def asegurar_en_prueba(cn, prueba_id, parametro_id, orden, aplicar, acciones, etiqueta):
    """Vincula el parametro a la prueba si aun no lo esta."""
    if parametro_id is None:
        acciones.append(f"vincular {etiqueta} a la prueba {prueba_id}")
        return
    ya = uno(cn, f"SELECT ParametroPruebaID FROM ParametrosPrueba "
                 f"WHERE PruebaID = {prueba_id} AND ParametroID = {parametro_id}")
    if ya:
        return
    acciones.append(f"vincular {etiqueta} a la prueba {prueba_id}")
    if aplicar:
        cn.Execute(f"INSERT INTO ParametrosPrueba (PruebaID, ParametroID, Secuencia) "
                   f"VALUES ({prueba_id}, {parametro_id}, {orden})")


def main():
    args = list(sys.argv[1:])
    aplicar = '--aplicar' in args
    args = [a for a in args if not a.startswith('--')]
    ruta = Path(args[0]).resolve() if args else (BASE_DIR / 'ANgesLAB.accdb')

    if not ruta.exists():
        print(f"ERROR: no se encontro la base de datos:\n  {ruta}")
        return 1

    print("=" * 70)
    print("  VSG POR HORAS + INDICE DE KATZ  |  LIPIDOS TOTALES EN EL PERFIL")
    print("=" * 70)
    print(f"Base de datos : {ruta}")
    print(f"Modo          : {'APLICAR CAMBIOS' if aplicar else 'SIMULACION (no escribe)'}")
    print()

    cn = conectar(str(ruta))
    acciones = []

    # ---- 1. VSG -----------------------------------------------------------
    vsg = uno(cn, "SELECT PruebaID, NombrePrueba FROM Pruebas "
                  "WHERE CodigoPrueba = 'HEMA004'")
    if not vsg:
        print("[AVISO] No se encontro la prueba VSG (HEMA004); se omite.")
    else:
        print(f"-- VSG: prueba {vsg['PruebaID']} ({vsg['NombrePrueba']})")
        p1 = asegurar_parametro(
            cn, 'HEMA_VSG_1H', 'V.S.G. 1a HORA', 'mm/h', 'Otros',
            'H: 0-15 mm/h  M: 0-20 mm/h', False, aplicar, acciones)
        p2 = asegurar_parametro(
            cn, 'HEMA_VSG_2H', 'V.S.G. 2a HORA', 'mm/2h', 'Otros',
            'Segunda lectura', False, aplicar, acciones)
        pk = asegurar_parametro(
            cn, 'HEMA_KATZ', 'INDICE DE KATZ', 'mm', 'Otros',
            'Hasta 10 mm', True, aplicar, acciones)
        asegurar_en_prueba(cn, vsg['PruebaID'], p1, 1, aplicar, acciones, 'V.S.G. 1a HORA')
        asegurar_en_prueba(cn, vsg['PruebaID'], p2, 2, aplicar, acciones, 'V.S.G. 2a HORA')
        asegurar_en_prueba(cn, vsg['PruebaID'], pk, 3, aplicar, acciones, 'INDICE DE KATZ')

        # Retirar el parametro antiguo de lectura unica: queda duplicado con
        # la 1a hora y confunde al capturar. Los resultados ya cargados se
        # trasladan a la 1a hora, porque es esa misma lectura; los informes
        # leen los parametros a traves de ParametrosPrueba, de modo que
        # desvincular sin trasladar los haria desaparecer de una reimpresion.
        viejo = uno(cn, "SELECT ParametroID FROM Parametros "
                        "WHERE CodigoParametro = 'HEMA_VSG'")
        if viejo and p1:
            pid_viejo = viejo['ParametroID']
            ligado = uno(cn, f"SELECT ParametroPruebaID FROM ParametrosPrueba "
                             f"WHERE PruebaID = {vsg['PruebaID']} "
                             f"AND ParametroID = {pid_viejo}")
            if ligado:
                pendientes = consultar(cn, f"""
                    SELECT rp.ResultadoParamID, rp.DetalleID, rp.Valor
                    FROM ResultadosParametros rp
                    INNER JOIN DetalleSolicitudes ds ON rp.DetalleID = ds.DetalleID
                    WHERE rp.ParametroID = {pid_viejo}
                      AND ds.PruebaID = {vsg['PruebaID']}
                """)
                for r in pendientes:
                    ya = uno(cn, f"SELECT ResultadoParamID FROM ResultadosParametros "
                                 f"WHERE DetalleID = {r['DetalleID']} AND ParametroID = {p1}")
                    if ya:
                        acciones.append(
                            f"[omitido] el detalle {r['DetalleID']} ya tiene 1a hora; "
                            f"se conserva el valor antiguo '{r['Valor']}'")
                        continue
                    acciones.append(
                        f"trasladar resultado '{r['Valor']}' del detalle "
                        f"{r['DetalleID']} a V.S.G. 1a HORA")
                    if aplicar:
                        cn.Execute(f"UPDATE ResultadosParametros SET ParametroID = {p1} "
                                   f"WHERE ResultadoParamID = {r['ResultadoParamID']}")

                # Solo se desvincula si no quedan resultados suyos en la prueba
                restantes = uno(cn, f"""
                    SELECT Count(*) AS n FROM ResultadosParametros rp
                    INNER JOIN DetalleSolicitudes ds ON rp.DetalleID = ds.DetalleID
                    WHERE rp.ParametroID = {pid_viejo} AND ds.PruebaID = {vsg['PruebaID']}
                """) if aplicar else {'n': 0}
                if (restantes or {}).get('n', 0) == 0:
                    acciones.append("retirar el parametro antiguo 'V.S.G.' de la prueba VSG")
                    if aplicar:
                        cn.Execute(f"DELETE FROM ParametrosPrueba "
                                   f"WHERE PruebaID = {vsg['PruebaID']} "
                                   f"AND ParametroID = {pid_viejo}")
                else:
                    acciones.append(
                        "[omitido] el parametro antiguo conserva resultados propios; "
                        "no se retira para no ocultarlos en una reimpresion")

    # ---- 1b. Prueba 'INDICE VSG' suelta -----------------------------------
    # El indice ahora se calcula dentro de la propia VSG, de modo que
    # ofrecerlo como prueba aparte duplica el trabajo. Se DESACTIVA, no se
    # borra: las solicitudes que ya la incluyen conservan su historial.
    indice = uno(cn, "SELECT PruebaID, NombrePrueba, Activo FROM Pruebas "
                     "WHERE CodigoPrueba = 'HEM007'")
    if indice and indice.get('Activo'):
        acciones.append(f"desactivar la prueba suelta '{indice['NombrePrueba']}' "
                        f"(ya no hace falta: el indice se calcula en la VSG)")
        if aplicar:
            cn.Execute(f"UPDATE Pruebas SET Activo = False "
                       f"WHERE PruebaID = {indice['PruebaID']}")

    # ---- 2. Perfil lipidico ----------------------------------------------
    perfil = uno(cn, "SELECT PruebaID, NombrePrueba FROM Pruebas "
                     "WHERE CodigoPrueba = 'QUIM002'")
    if not perfil:
        print("[AVISO] No se encontro el Perfil Lipidico (QUIM002); se omite.")
    else:
        print(f"-- Perfil Lipidico: prueba {perfil['PruebaID']} ({perfil['NombrePrueba']})")
        # Reutiliza el parametro que ya existe como prueba suelta
        lt = uno(cn, "SELECT ParametroID FROM Parametros "
                     "WHERE NombreParametro = 'LIPIDOS TOTALES'")
        pid_lt = lt['ParametroID'] if lt else asegurar_parametro(
            cn, 'QUIM_LIPTOT', 'LIPIDOS TOTALES', 'mg/dL', 'Lipidos',
            '400 - 800 mg/dL', True, aplicar, acciones)
        if lt and aplicar:
            # Debe quedar marcado como calculado para que no se pida a mano
            cn.Execute(f"UPDATE Parametros SET EsCalculado = True "
                       f"WHERE ParametroID = {pid_lt}")
        asegurar_en_prueba(cn, perfil['PruebaID'], pid_lt, 8, aplicar, acciones,
                           'LIPIDOS TOTALES')

    print()
    if not acciones:
        cn.Close()
        print("No hay nada que hacer: el catalogo ya esta actualizado.")
        return 0

    print(f"-- Cambios ({len(acciones)})")
    for a in acciones:
        print(f"     {a}")
    print()

    if not aplicar:
        cn.Close()
        print("Simulacion terminada. Nada fue modificado.")
        print("Para aplicar los cambios ejecute:")
        print("    python migracion_vsg_lipidos.py --aplicar")
        return 0

    cn.Close()
    print("Listo.")
    return 0


if __name__ == '__main__':
    # El respaldo se hace antes de abrir la conexion en modo aplicar
    if '--aplicar' in sys.argv:
        _args = [a for a in sys.argv[1:] if not a.startswith('--')]
        _ruta = Path(_args[0]).resolve() if _args else (BASE_DIR / 'ANgesLAB.accdb')
        if _ruta.exists():
            print(f"Copia de seguridad: {respaldar(_ruta)}")
    sys.exit(main())

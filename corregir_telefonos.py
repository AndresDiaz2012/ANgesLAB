# -*- coding: utf-8 -*-
"""
corregir_telefonos.py
=====================
Normaliza los telefonos guardados en Pacientes, Medicos y PacientesVet al
formato internacional que WhatsApp acepta.

Por que se necesita:
  El formulario de registro concatena el codigo de pais con lo que escribe
  el usuario ('+58' + '04121234567'), de modo que un numero correcto queda
  guardado como '+5804121234567' o '+58+584121234567'. WhatsApp rechaza esos
  numeros con "el numero no esta registrado" AUNQUE la linea si tenga
  WhatsApp, y el envio de resultados falla.

Que hace:
  '+58+584147204006' -> '+584147204006'   (codigo de pais duplicado)
  '+5804121234567'   -> '+584121234567'   (0 de tronco sobrante)
  '04247548767'      -> '+584247548767'   (sin codigo de pais)
  '4262758736'       -> '+584262758736'

Que NO hace:
  - No inventa digitos. Un numero incompleto (p.ej. '414000000') se deja
    intacto y se reporta para revisarlo a mano.
  - No toca numeros fijos ni de otros paises que ya esten bien formados.
  - No modifica registros vacios.

Caracteristicas:
  - Idempotente: se puede ejecutar varias veces sin efecto adicional.
  - Copia de seguridad automatica de la BD antes de escribir.
  - Modo simulacion por defecto: no escribe nada hasta pasar --aplicar.

Uso:
    python corregir_telefonos.py                       # simulacion
    python corregir_telefonos.py --aplicar             # aplica los cambios
    python corregir_telefonos.py --aplicar "D:\\ANgesLab\\ANgesLAB.accdb"

IMPORTANTE: ejecutar con ANgesLAB CERRADO.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import sys
import shutil
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    import win32com.client
except ImportError:
    print("ERROR: falta pywin32.  pip install pywin32")
    sys.exit(1)

from modulos.whatsapp_envio import normalizar_telefono, validar_numero_whatsapp

# (tabla, clave primaria, columna de telefono, etiqueta)
TABLAS = [
    ('Pacientes',    'PacienteID',    'Telefono1',           'Pacientes'),
    ('Medicos',      'MedicoID',      'Telefono1',           'Medicos'),
    ('PacientesVet', 'PacienteVetID', 'TelefonoPropietario', 'Pacientes veterinarios'),
]


def conectar(ruta_bd):
    cn = win32com.client.Dispatch('ADODB.Connection')
    cn.Open(f'Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta_bd};')
    return cn


def respaldar(ruta_bd):
    """Copia la BD a backups/ antes de escribir."""
    destino_dir = BASE_DIR / 'backups'
    destino_dir.mkdir(exist_ok=True)
    marca = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = destino_dir / f'ANgesLAB_antes_telefonos_{marca}.accdb'
    shutil.copy2(ruta_bd, destino)
    return destino


def analizar(cn, tabla, pk, col):
    """Devuelve (cambios, sin_cambio, problemas) sin escribir nada."""
    try:
        rs = cn.Execute(f'SELECT {pk}, {col} FROM {tabla}')[0]
    except Exception as e:
        print(f"  [omitida] {tabla}.{col}: {e}")
        return [], [], []

    filas = []
    while not rs.EOF:
        filas.append((rs.Fields(0).Value, str(rs.Fields(1).Value or '')))
        rs.MoveNext()
    rs.Close()

    cambios, sin_cambio, problemas = [], [], []
    for pk_valor, original in filas:
        if not original.strip():
            continue

        normalizado = normalizar_telefono(original)
        valido, motivo = validar_numero_whatsapp(original)

        if not normalizado:
            problemas.append((pk_valor, original, 'No contiene digitos utilizables.'))
            continue
        if not valido:
            # No se adivinan digitos que faltan: se reporta para revision manual
            problemas.append((pk_valor, original, motivo))
            continue

        final = '+' + normalizado
        if final == original.strip():
            sin_cambio.append((pk_valor, original))
        else:
            cambios.append((pk_valor, original, final))

    return cambios, sin_cambio, problemas


def aplicar(cn, tabla, pk, col, cambios):
    aplicados = 0
    for pk_valor, _original, final in cambios:
        cn.Execute(f"UPDATE {tabla} SET {col} = '{final}' WHERE {pk} = {pk_valor}")
        aplicados += 1
    return aplicados


def main():
    args = [a for a in sys.argv[1:]]
    modo_aplicar = '--aplicar' in args
    args = [a for a in args if not a.startswith('--')]
    ruta_bd = Path(args[0]).resolve() if args else (BASE_DIR / 'ANgesLAB.accdb')

    if not ruta_bd.exists():
        print(f"ERROR: no se encontro la base de datos:\n  {ruta_bd}")
        return 1

    print("=" * 68)
    print("  CORRECCION DE TELEFONOS PARA WHATSAPP")
    print("=" * 68)
    print(f"Base de datos : {ruta_bd}")
    print(f"Modo          : {'APLICAR CAMBIOS' if modo_aplicar else 'SIMULACION (no escribe)'}")
    print()

    cn = conectar(str(ruta_bd))

    plan = []
    total_cambios = total_iguales = total_problemas = 0

    for tabla, pk, col, etiqueta in TABLAS:
        cambios, sin_cambio, problemas = analizar(cn, tabla, pk, col)
        plan.append((tabla, pk, col, etiqueta, cambios))
        total_cambios += len(cambios)
        total_iguales += len(sin_cambio)
        total_problemas += len(problemas)

        print(f"-- {etiqueta} ({tabla}.{col})")
        if not (cambios or sin_cambio or problemas):
            print("   sin telefonos registrados")
        for pk_valor, original, final in cambios:
            print(f"   id={pk_valor:<6} {original!r:24} ->  {final}")
        for pk_valor, original in sin_cambio:
            print(f"   id={pk_valor:<6} {original!r:24}     (ya correcto)")
        for pk_valor, original, motivo in problemas:
            print(f"   id={pk_valor:<6} {original!r:24} !!  REVISAR: {motivo}")
        print()

    print("-" * 68)
    print(f"A corregir: {total_cambios}   Ya correctos: {total_iguales}   "
          f"Requieren revision manual: {total_problemas}")
    print("-" * 68)

    if not modo_aplicar:
        cn.Close()
        print("\nSimulacion terminada. Nada fue modificado.")
        print("Para aplicar los cambios ejecute:")
        print("    python corregir_telefonos.py --aplicar")
        return 0

    if total_cambios == 0:
        cn.Close()
        print("\nNo hay nada que corregir.")
        return 0

    respaldo = respaldar(ruta_bd)
    print(f"\nCopia de seguridad: {respaldo}")

    aplicados = 0
    try:
        for tabla, pk, col, _etiqueta, cambios in plan:
            aplicados += aplicar(cn, tabla, pk, col, cambios)
    finally:
        cn.Close()

    print(f"Telefonos corregidos: {aplicados}")
    if total_problemas:
        print(f"\nQuedan {total_problemas} telefono(s) marcados como REVISAR: "
              "estan incompletos o no son celulares.\nCorrijalos desde la ficha "
              "del paciente o del medico.")
    print("\nListo.")
    return 0


if __name__ == '__main__':
    sys.exit(main())

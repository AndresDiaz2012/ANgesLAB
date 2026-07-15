# -*- coding: utf-8 -*-
"""
================================================================================
ACTUALIZADOR ANgesLAB - aplicar_actualizacion.py
================================================================================
Actualiza una instalacion EXISTENTE de ANgesLAB en la PC del cliente, aplicando
las mejoras recientes SIN eliminar el trabajo ya realizado:

  - Indice TyG (resistencia a insulina) + interpretacion IA
  - Tema/imagen profesional de la interfaz
  - Correcciones varias del modulo de calculos

Que hace, en orden:
  1. Detecta la carpeta de instalacion del cliente (registro de Windows o
     C:\\ANgesLAB, o la que se pase como argumento).
  2. RESPALDA la base de datos del cliente antes de cualquier cambio.
  3. Copia SOLO los archivos de codigo actualizados (ANgesLAB.pyw y modulos).
  4. Aplica la migracion de base de datos (agrega Trigliceridos + Indice TyG al
     PERFIL DE RESISTENCIA A INSULINA). La migracion es idempotente y SOLO
     agrega; nunca borra datos.

NUNCA se tocan:
  - ANgesLAB.accdb (la base de datos con pacientes, resultados, facturas...)
  - db_config.json, config_ia.json, backup_config.json (configuracion)
  - logos\\, firmas\\, backups\\, logs\\ (recursos y datos del cliente)

Las rutas de ORIGEN son relativas a este script, de modo que funcione desde
cualquier unidad USB (D:, E:, F:, ...).

Uso:
    python aplicar_actualizacion.py                 # auto-detecta instalacion
    python aplicar_actualizacion.py "C:\\ANgesLAB"   # ruta explicita
    python aplicar_actualizacion.py "C:\\ANgesLAB" --si   # sin confirmacion

IMPORTANTE: el cliente debe CERRAR ANgesLAB antes de ejecutar.

Copyright (c) 2024-2026 ANgesLAB Solutions
================================================================================
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# ORIGEN de los archivos nuevos = carpeta que contiene a 'actualizador'
# (en la USB: D:\ANgesLab ; en el repo: la raiz del proyecto)
SCRIPT_DIR = Path(__file__).resolve().parent
ORIGEN = SCRIPT_DIR.parent

# Archivos de CODIGO que se actualizan (nunca datos ni configuracion)
ARCHIVOS_RAIZ = ['ANgesLAB.pyw', 'VERSION']
# Todos los .py de la carpeta modulos se copian (incluye tema_ui.py nuevo)

# Cosas que JAMAS se sobrescriben en el destino
NO_TOCAR = {
    'angeslab.accdb', 'db_config.json', 'config_ia.json',
    'backup_config.json',
}
CARPETAS_INTOCABLES = {'logos', 'firmas', 'backups', 'logs'}


def log(msg):
    print(msg, flush=True)


def detectar_instalacion_registro():
    """Lee la ruta de instalacion desde el registro de Windows."""
    try:
        import winreg
    except ImportError:
        return None
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            k = winreg.OpenKey(hive, r"Software\ANgesLAB Solutions\ANgesLAB")
            val, _ = winreg.QueryValueEx(k, "InstallPath")
            winreg.CloseKey(k)
            if val and os.path.isdir(val):
                return Path(val)
        except OSError:
            continue
    return None


def resolver_instalacion(argv):
    """Determina la carpeta de instalacion del cliente."""
    # 1) Argumento explicito
    args = [a for a in argv[1:] if not a.startswith('--')]
    if args:
        p = Path(args[0])
        if (p / 'ANgesLAB.pyw').exists():
            return p
        log(f"[AVISO] La ruta indicada no contiene ANgesLAB.pyw: {p}")
    # 2) Registro de Windows
    reg = detectar_instalacion_registro()
    if reg and (reg / 'ANgesLAB.pyw').exists():
        return reg
    # 3) Ruta por defecto del instalador
    for cand in (Path(r"C:\ANgesLAB"), Path(r"C:\ANgesLab")):
        if (cand / 'ANgesLAB.pyw').exists():
            return cand
    return None


def confirmar(auto_si):
    if auto_si:
        return True
    try:
        resp = input("\n¿Aplicar la actualizacion ahora? (S/N): ").strip().lower()
    except EOFError:
        return False
    return resp in ('s', 'si', 'sí', 'y', 'yes')


def respaldar_bd(install: Path):
    """Copia la base de datos del cliente a la carpeta backups."""
    bd = install / 'ANgesLAB.accdb'
    if not bd.exists():
        log("[AVISO] No se encontro ANgesLAB.accdb; se omite el respaldo.")
        return None
    backups = install / 'backups'
    backups.mkdir(exist_ok=True)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    destino = backups / f"ANgesLAB_pre_actualizacion_{ts}.accdb"
    shutil.copy2(bd, destino)
    log(f"  [OK] Respaldo de la base de datos: {destino}")
    return destino


def copiar_codigo(install: Path):
    """Copia archivos de codigo actualizados. Retorna cantidad copiada."""
    copiados = 0

    # Archivos de raiz
    for nombre in ARCHIVOS_RAIZ:
        src = ORIGEN / nombre
        if src.exists() and nombre.lower() not in NO_TOCAR:
            shutil.copy2(src, install / nombre)
            log(f"  [OK] {nombre}")
            copiados += 1

    # Carpeta modulos (solo .py)
    src_mod = ORIGEN / 'modulos'
    dst_mod = install / 'modulos'
    if src_mod.is_dir():
        dst_mod.mkdir(exist_ok=True)
        for py in sorted(src_mod.glob('*.py')):
            shutil.copy2(py, dst_mod / py.name)
            copiados += 1
        log(f"  [OK] modulos/ ({len(list(src_mod.glob('*.py')))} archivos .py)")

    return copiados


def aplicar_migracion(install: Path):
    """Ejecuta la migracion de BD (idempotente) contra la BD del cliente."""
    bd = install / 'ANgesLAB.accdb'
    if not bd.exists():
        log("[AVISO] Sin ANgesLAB.accdb; se omite la migracion de datos.")
        return False
    migracion = ORIGEN / 'migracion_tyg_perfil_ri.py'
    if not migracion.exists():
        log(f"[AVISO] No se encontro el script de migracion: {migracion}")
        return False
    log("  Aplicando migracion de base de datos (Indice TyG)...")
    r = subprocess.run(
        [sys.executable, str(migracion), str(bd)],
        capture_output=True, text=True
    )
    for linea in (r.stdout or '').splitlines():
        log(f"     {linea}")
    if r.returncode != 0:
        log(f"  [AVISO] La migracion termino con codigo {r.returncode}.")
        if r.stderr:
            log(f"     {r.stderr.strip()[:300]}")
        return False
    return True


def registrar_bitacora(install: Path, copiados, migrado):
    try:
        logs = install / 'logs'
        logs.mkdir(exist_ok=True)
        with open(logs / 'actualizaciones.log', 'a', encoding='utf-8') as f:
            ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{ts}] Actualizacion aplicada: {copiados} archivos de "
                    f"codigo; migracion BD={'si' if migrado else 'no'} "
                    f"(Indice TyG + tema profesional).\n")
    except Exception:
        pass


def main(argv):
    log("=" * 66)
    log("   ACTUALIZADOR ANgesLAB  -  Indice TyG + Imagen Profesional")
    log("=" * 66)
    log(f"Origen de archivos nuevos: {ORIGEN}")

    # Validar origen
    if not (ORIGEN / 'ANgesLAB.pyw').exists():
        log(f"[ERROR] No se encuentran los archivos nuevos en: {ORIGEN}")
        log("        Ejecute este actualizador desde la carpeta de la USB.")
        return 1

    # Detectar instalacion
    install = resolver_instalacion(argv)
    if not install:
        log("[ERROR] No se pudo ubicar la instalacion de ANgesLAB.")
        log("        Vuelva a ejecutar indicando la ruta, por ejemplo:")
        log('        python aplicar_actualizacion.py "C:\\ANgesLAB"')
        return 1

    log(f"Instalacion del cliente:   {install}")
    bd = install / 'ANgesLAB.accdb'
    log(f"Base de datos:             {bd}  "
        f"({'existe' if bd.exists() else 'NO existe'})")
    log("")
    log("Se actualizara SOLO el codigo (ANgesLAB.pyw + modulos) y se agregara")
    log("el Indice TyG. NO se modifican datos, configuracion, logos ni firmas.")
    log("IMPORTANTE: ANgesLAB debe estar CERRADO.")

    auto_si = any(a in ('--si', '--yes', '-y') for a in argv[1:])
    if not confirmar(auto_si):
        log("\nActualizacion cancelada por el usuario.")
        return 2

    log("\n[1/3] Respaldando base de datos del cliente...")
    respaldar_bd(install)

    log("\n[2/3] Copiando archivos de codigo actualizados...")
    copiados = copiar_codigo(install)

    log("\n[3/3] Aplicando migracion de base de datos...")
    migrado = aplicar_migracion(install)

    registrar_bitacora(install, copiados, migrado)

    log("\n" + "=" * 66)
    log(f"   ACTUALIZACION COMPLETADA  -  {copiados} archivos de codigo"
        f" | BD: {'migrada' if migrado else 'sin cambios'}")
    log("=" * 66)
    log("Su trabajo (pacientes, resultados, facturas, config) quedo INTACTO.")
    log("Ya puede abrir ANgesLAB normalmente.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except KeyboardInterrupt:
        log("\nInterrumpido.")
        sys.exit(130)

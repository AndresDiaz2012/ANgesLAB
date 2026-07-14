# -*- coding: utf-8 -*-
"""
reset_developer_pwd.py
======================
Script one-shot para restablecer la contrasena del usuario 'developer'
de ANgesLAB. Uso puntual cuando la contrasena original (generada
aleatoriamente en la primera ejecucion) se perdio.

Uso:
    python reset_developer_pwd.py

    Se solicitara la nueva contrasena por teclado (no queda en pantalla).
    Alternativamente puede pasarla por variable de entorno:
        set ANGESLAB_NEW_DEV_PWD=SuPassword & python reset_developer_pwd.py

Requiere: pywin32 (ya instalado por ANgesLAB) y modulos/seguridad_db.py.

IMPORTANTE: Ejecutar con ANgesLAB CERRADO para evitar bloqueos de la BD.
"""

import getpass
import json
import os
import sys
from pathlib import Path

NOMBRE_USUARIO = "developer"

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

try:
    from modulos.seguridad_db import SeguridadContrasenas
except ImportError as e:
    print(f"[ERROR] No se pudo importar modulos.seguridad_db: {e}")
    print("        Ejecute este script desde la carpeta de instalacion de ANgesLAB.")
    sys.exit(1)

try:
    import win32com.client
except ImportError:
    print("[ERROR] pywin32 no esta instalado. Instale con: pip install pywin32")
    sys.exit(1)


def resolver_ruta_db() -> Path:
    """Lee db_config.json si existe, si no usa ANgesLAB.accdb junto al script."""
    default = BASE_DIR / "ANgesLAB.accdb"
    cfg = BASE_DIR / "db_config.json"
    if cfg.exists():
        try:
            with open(cfg, "r", encoding="utf-8") as f:
                data = json.load(f)
            db = (data.get("db_path") or "").strip()
            if db:
                p = Path(db)
                if not p.is_absolute():
                    p = BASE_DIR / p
                if p.exists():
                    return p
        except Exception as e:
            print(f"[AVISO] db_config.json invalido ({e}), usando ruta por defecto.")
    return default


def obtener_nueva_password() -> str:
    """Obtiene la nueva contrasena desde env var o prompt interactivo."""
    pwd = os.environ.get("ANGESLAB_NEW_DEV_PWD", "").strip()
    if pwd:
        return pwd
    print(f"Ingrese la nueva contrasena para '{NOMBRE_USUARIO}':")
    pwd1 = getpass.getpass("  Password: ")
    pwd2 = getpass.getpass("  Repita:   ")
    if pwd1 != pwd2:
        print("[ERROR] Las contrasenas no coinciden.")
        sys.exit(1)
    if len(pwd1) < 6:
        print("[ERROR] Contrasena demasiado corta (minimo 6 caracteres).")
        sys.exit(1)
    return pwd1


def main() -> int:
    ruta_db = resolver_ruta_db()
    if not ruta_db.exists():
        print(f"[ERROR] No se encontro la base de datos en: {ruta_db}")
        return 1

    print(f"Base de datos: {ruta_db}")
    print(f"Usuario a resetear: {NOMBRE_USUARIO}")

    nueva_password = obtener_nueva_password()

    conn = win32com.client.Dispatch("ADODB.Connection")
    try:
        conn.Open(f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta_db};")
    except Exception as e:
        print(f"[ERROR] No se pudo abrir la BD: {e}")
        print("        Asegurese de que ANgesLAB este cerrado.")
        return 1

    try:
        rs = win32com.client.Dispatch("ADODB.Recordset")
        rs.Open(
            f"SELECT UsuarioID FROM Usuarios WHERE NombreUsuario='{NOMBRE_USUARIO}'",
            conn, 1, 1,
        )
        if rs.EOF:
            print(f"[ERROR] No existe el usuario '{NOMBRE_USUARIO}' en la BD.")
            rs.Close()
            return 1
        uid = int(rs.Fields.Item("UsuarioID").Value)
        rs.Close()

        nuevo_hash, nuevo_salt = SeguridadContrasenas.hash_password(nueva_password)
        hash_sql = nuevo_hash.replace("'", "''")
        salt_sql = nuevo_salt.replace("'", "''")

        conn.Execute(
            f"UPDATE Usuarios SET "
            f"PasswordHash='{hash_sql}', "
            f"PasswordSalt='{salt_sql}', "
            f"Password='', "
            f"Activo=True "
            f"WHERE UsuarioID={uid}"
        )
        print(f"[OK] Contrasena de '{NOMBRE_USUARIO}' (UsuarioID={uid}) restablecida.")
        print(f"     Ingrese ahora en ANgesLAB con el usuario: {NOMBRE_USUARIO}")
        return 0
    finally:
        try:
            conn.Close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())

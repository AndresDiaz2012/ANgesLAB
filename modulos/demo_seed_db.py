# -*- coding: utf-8 -*-
"""
ANgesLAB - Script de Siembra de Base de Datos Demo
===================================================
Crea y puebla ANgesLAB_Demo.accdb con datos de muestra.

USO:
    python modulos/demo_seed_db.py

PREREQUISITOS:
    - ANgesLAB.accdb debe existir (se usa como plantilla de estructura)
    - Microsoft ACE OLEDB 12.0 instalado
    - pypiwin32 instalado

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import os
import sys
import shutil
import secrets
import hashlib
from pathlib import Path
from datetime import datetime, date, timedelta

# Ajustar path para imports
APP_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(APP_DIR))

SOURCE_DB = APP_DIR / "ANgesLAB.accdb"
DEMO_DB = APP_DIR / "ANgesLAB_Demo.accdb"


# ==============================================================================
# UTILIDADES DE BASE DE DATOS
# ==============================================================================

def get_connection(db_path):
    import win32com.client
    conn = win32com.client.Dispatch("ADODB.Connection")
    conn_str = f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={db_path};"
    conn.Open(conn_str)
    return conn


def execute(conn, sql):
    try:
        conn.Execute(sql)
    except Exception as e:
        print(f"  SQL Error: {e}")
        print(f"  SQL: {sql[:100]}...")


def query(conn, sql):
    rs = conn.Execute(sql)[0]
    results = []
    if not rs.EOF:
        while not rs.EOF:
            row = {}
            for i in range(rs.Fields.Count):
                row[rs.Fields[i].Name] = rs.Fields[i].Value
            results.append(row)
            rs.MoveNext()
    return results


def query_one(conn, sql):
    results = query(conn, sql)
    return results[0] if results else {}


def escape(val):
    if val is None:
        return "Null"
    if isinstance(val, bool):
        return "True" if val else "False"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (datetime, date)):
        return f"#{val.strftime('%m/%d/%Y')}#"
    return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"


def insert(conn, table, data):
    cols = ", ".join(f"[{k}]" for k in data.keys())
    vals = ", ".join(escape(v) for v in data.values())
    sql = f"INSERT INTO [{table}] ({cols}) VALUES ({vals})"
    conn.Execute(sql)


def hash_password(password):
    """Genera hash SHA-256 con salt (compatible con seguridad_db.py)."""
    salt = secrets.token_hex(32)
    combined = f"{salt}{password}".encode('utf-8')
    pwd_hash = hashlib.sha256(combined).hexdigest()
    return pwd_hash, salt


# ==============================================================================
# PASO 1: CREAR BD DEMO DESDE PLANTILLA
# ==============================================================================

def crear_bd_demo():
    print(f"Copiando estructura desde {SOURCE_DB}...")
    if not SOURCE_DB.exists():
        print(f"ERROR: No se encontro {SOURCE_DB}")
        sys.exit(1)

    if DEMO_DB.exists():
        os.remove(str(DEMO_DB))
        print(f"  BD demo anterior eliminada.")

    shutil.copy2(str(SOURCE_DB), str(DEMO_DB))
    print(f"  BD Demo creada en: {DEMO_DB}")

    conn = get_connection(str(DEMO_DB))

    # Limpiar datos transaccionales (conservar catalogo de Pruebas, Areas, Parametros)
    tablas_limpiar = [
        'ResultadosParametros',
        'DetalleSolicitudes',
        'DetalleFacturas',
        'Facturas',
        'Recibos',
        'Solicitudes',
        'Pacientes',
        'Medicos',
        'Usuarios',
        'Pendientes',
    ]

    for tabla in tablas_limpiar:
        try:
            conn.Execute(f"DELETE FROM [{tabla}]")
            print(f"  Limpiada: {tabla}")
        except Exception as e:
            print(f"  No se pudo limpiar {tabla}: {e}")

    # Limpiar configuracion para insertar la demo
    try:
        conn.Execute("DELETE FROM [ConfiguracionLaboratorio]")
        print(f"  Limpiada: ConfiguracionLaboratorio")
    except Exception as e:
        print(f"  ConfiguracionLaboratorio: {e}")

    conn.Close()
    print()


# ==============================================================================
# PASO 2: CONFIGURACION DEL LABORATORIO
# ==============================================================================

def seed_configuracion(conn):
    print("Sembrando configuracion del laboratorio...")
    insert(conn, 'ConfiguracionLaboratorio', {
        'NombreLaboratorio': 'Laboratorio Clinico Demo',
        'RazonSocial': 'Laboratorio Demo ANgesLAB C.A.',
        'RIF': 'J-40000000-0',
        'Direccion': 'Av. Principal, Torre Medica, Piso 3, Of. 301',
        'Telefono1': '+58 212-555-1234',
        'Telefono2': '+58 414-555-9876',
        'Email': 'demo@laboratorio.com',
    })
    print("  OK - Configuracion del laboratorio creada.")


# ==============================================================================
# PASO 3: USUARIOS
# ==============================================================================

def seed_usuarios(conn):
    print("Creando usuarios...")

    # Usuario demo (auto-login)
    h1, s1 = hash_password('demo')
    insert(conn, 'Usuarios', {
        'NombreCompleto': 'Usuario Demo',
        'NombreUsuario': 'demo',
        'Password': '',
        'PasswordHash': h1,
        'PasswordSalt': s1,
        'Nivel': 'Administrador',
        'Activo': True,
    })

    # Admin (para demostraciones guiadas)
    h2, s2 = hash_password('demo123')
    insert(conn, 'Usuarios', {
        'NombreCompleto': 'Administrador Demo',
        'NombreUsuario': 'admin',
        'Password': '',
        'PasswordHash': h2,
        'PasswordSalt': s2,
        'Nivel': 'Administrador',
        'Activo': True,
    })

    # Developer (necesario para que _asegurar_usuario_admin no falle)
    h3, s3 = hash_password('ANges2741**')
    insert(conn, 'Usuarios', {
        'NombreCompleto': 'Desarrollador ANgesLAB',
        'NombreUsuario': 'developer',
        'Password': '',
        'PasswordHash': h3,
        'PasswordSalt': s3,
        'Nivel': 'Desarrollador',
        'Activo': True,
    })

    print("  OK - Usuarios: demo/demo, admin/demo123, developer")


# ==============================================================================
# PASO 4: MEDICOS
# ==============================================================================

def seed_medicos(conn):
    print("Creando medicos de muestra...")
    medicos = [
        ('DR001', 'Carlos', 'Rodriguez', 'Medicina Interna', '+584141112233', 'c.rodriguez@email.com'),
        ('DR002', 'Maria', 'Lopez', 'Pediatria', '+584242223344', 'm.lopez@email.com'),
        ('DR003', 'Jose', 'Gonzalez', 'Cardiologia', '+584123334455', 'j.gonzalez@email.com'),
    ]
    for cod, nom, ape, esp, tel, email in medicos:
        insert(conn, 'Medicos', {
            'CodigoMedico': cod,
            'Nombres': nom,
            'Apellidos': ape,
            'Especialidad': esp,
            'Telefono1': tel,
            'Email': email,
            'Activo': True,
            'FechaRegistro': datetime.now(),
        })
    print(f"  OK - {len(medicos)} medicos creados.")


# ==============================================================================
# PASO 5: PACIENTES (prefijo DEMO- para no contar contra el limite)
# ==============================================================================

def seed_pacientes(conn):
    print("Creando pacientes de muestra...")
    hoy = date.today()
    pacientes = [
        ('V', 'DEMO-10001', 'Juan Carlos', 'Perez Mendoza', date(1985, 3, 15), 'M', '+584145550001', 'juan.perez@email.com', 'Av. Libertador, Edif. Sol, Apto 4B'),
        ('V', 'DEMO-10002', 'Maria Elena', 'Torres Ruiz', date(1990, 7, 22), 'F', '+584245550002', 'maria.torres@email.com', 'Calle 5, Urb. La Paz, Casa 12'),
        ('V', 'DEMO-10003', 'Luis Alberto', 'Gomez Vargas', date(1975, 11, 8), 'M', '+584125550003', 'luis.gomez@email.com', 'Av. Bolivar, Centro Comercial, Nivel 2'),
        ('V', 'DEMO-10004', 'Ana Sofia', 'Fernandez Castro', date(2001, 1, 30), 'F', '+584165550004', 'ana.fernandez@email.com', 'Calle Principal, Sector Centro, N 45'),
        ('E', 'DEMO-10005', 'Roberto', 'Martinez Silva', date(1968, 9, 5), 'M', '+584265550005', 'roberto.martinez@email.com', 'Av. Las Americas, Residencias El Parque'),
    ]

    pac_ids = []
    for tipo, num, nom, ape, fnac, sexo, tel, email, dir in pacientes:
        insert(conn, 'Pacientes', {
            'TipoDocumento': tipo,
            'NumeroDocumento': num,
            'Nombres': nom,
            'Apellidos': ape,
            'FechaNacimiento': fnac,
            'Sexo': sexo,
            'Telefono1': tel,
            'Email': email,
            'DireccionCompleta': dir,
            'Activo': True,
            'FechaRegistro': hoy,
        })
        row = query_one(conn, f"SELECT PacienteID FROM [Pacientes] WHERE [NumeroDocumento]='{num}'")
        pid = row.get('PacienteID')
        pac_ids.append(pid)
        print(f"  Paciente: {nom} {ape} (ID={pid})")

    print(f"  OK - {len(pacientes)} pacientes creados.")
    return pac_ids


# ==============================================================================
# PASO 6: SOLICITUDES CON DETALLES
# ==============================================================================

def seed_solicitudes(conn, pac_ids):
    print("Creando solicitudes de muestra...")

    # Obtener IDs de medicos
    med_rows = query(conn, "SELECT MedicoID FROM [Medicos] ORDER BY MedicoID")
    med_ids = [r['MedicoID'] for r in med_rows]

    # Obtener pruebas disponibles (del catalogo conservado)
    pru_rows = query(conn, "SELECT PruebaID, CodigoPrueba, NombrePrueba, Precio FROM [Pruebas] WHERE Activo=True ORDER BY PruebaID")

    if not pru_rows:
        print("  AVISO: No hay pruebas en el catalogo. Las solicitudes no tendran detalles.")
        print("  Asegurese de que ANgesLAB.accdb tenga pruebas configuradas.")
        return []

    print(f"  Catalogo: {len(pru_rows)} pruebas disponibles.")

    hoy = date.today()

    # Definir solicitudes demo
    # (indice_paciente, indice_medico, [indices_pruebas], dias_atras, estado)
    solicitudes_def = [
        (0, 0, [0, 1], 5, 'Completada'),
        (1, 1, [2], 3, 'Completada'),
        (2, 0, [0, 2], 2, 'En Proceso'),
        (3, 2, [1, 3] if len(pru_rows) > 3 else [1], 1, 'Pendiente'),
        (4, 1, [0], 0, 'Pendiente'),
    ]

    sol_ids = []
    for i, (pac_idx, med_idx, pru_idxs, dias_atras, estado) in enumerate(solicitudes_def, 1):
        fecha = hoy - timedelta(days=dias_atras)
        pac_id = pac_ids[pac_idx % len(pac_ids)]
        med_id = med_ids[med_idx % len(med_ids)] if med_ids else None

        # Obtener pruebas para esta solicitud
        pruebas_sol = [pru_rows[idx % len(pru_rows)] for idx in pru_idxs]
        subtotal = sum(float(p.get('Precio') or 0) for p in pruebas_sol)

        numero = f'DEMO-{i:04d}'

        insert(conn, 'Solicitudes', {
            'NumeroSolicitud': numero,
            'FechaSolicitud': fecha,
            'HoraSolicitud': '08:30:00',
            'PacienteID': pac_id,
            'MedicoID': med_id,
            'TipoServicio': 'Particular',
            'EstadoSolicitud': estado,
            'PorcentajeDescuento': 0,
            'MontoDescuento': 0,
            'MontoIVA': 0,
            'MontoNeto': subtotal,
            'MontoTotal': subtotal,
            'UsuarioRegistro': 1,
            'FechaRegistro': datetime.combine(fecha, datetime.min.time()),
        })

        row = query_one(conn, f"SELECT SolicitudID FROM [Solicitudes] WHERE [NumeroSolicitud]='{numero}'")
        sol_id = row.get('SolicitudID')
        sol_ids.append(sol_id)

        # Insertar detalles de pruebas
        for prueba in pruebas_sol:
            precio = float(prueba.get('Precio') or 0)
            estado_det = 'Validado' if estado == 'Completada' else ('Capturado' if estado == 'En Proceso' else 'Pendiente')
            insert(conn, 'DetalleSolicitudes', {
                'SolicitudID': sol_id,
                'PruebaID': prueba['PruebaID'],
                'PrecioUnitario': precio,
                'Cantidad': 1,
                'Subtotal': precio,
                'Estado': estado_det,
            })

        print(f"  Solicitud {numero}: {len(pruebas_sol)} prueba(s), estado={estado} (ID={sol_id})")

    print(f"  OK - {len(solicitudes_def)} solicitudes creadas.")
    return sol_ids


# ==============================================================================
# PASO 7: PENDIENTES EN DASHBOARD
# ==============================================================================

def seed_pendientes(conn):
    print("Creando pendientes de ejemplo...")
    pendientes = [
        'Revisar resultados de hematologia del paciente Perez',
        'Llamar al Dr. Rodriguez por solicitud pendiente',
        'Verificar inventario de reactivos',
    ]
    for desc in pendientes:
        try:
            insert(conn, 'Pendientes', {
                'Descripcion': desc,
                'FechaCreacion': datetime.now(),
            })
        except Exception as e:
            print(f"  No se pudo crear pendiente: {e}")
    print(f"  OK - {len(pendientes)} pendientes creados.")


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    print("=" * 60)
    print("ANgesLAB - Creador de Base de Datos Demo")
    print("=" * 60)
    print()

    crear_bd_demo()

    conn = get_connection(str(DEMO_DB))
    try:
        seed_configuracion(conn)
        seed_usuarios(conn)
        seed_medicos(conn)
        pac_ids = seed_pacientes(conn)
        seed_solicitudes(conn, pac_ids)
        seed_pendientes(conn)

        print()
        print("=" * 60)
        print("Base de datos demo creada exitosamente!")
        print(f"  Archivo: {DEMO_DB}")
        print(f"  Credenciales: demo/demo, admin/demo123")
        print("=" * 60)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            conn.Close()
        except:
            pass


if __name__ == "__main__":
    main()

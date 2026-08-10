# -*- coding: utf-8 -*-
"""
crear_plantilla_bd.py
=====================
Genera ANgesLAB_plantilla.accdb: la base de datos que se empaqueta DENTRO
del instalador para equipos nuevos.

Por que hace falta:
  El instalador venia empaquetando la base de trabajo del desarrollador.
  Eso llevaba al cliente los pacientes, resultados y datos del laboratorio
  de otra instalacion, y sobre todo su tabla de Usuarios: el usuario
  'developer' quedaba con una contrasena distinta a la clave de soporte y
  no se podia entrar (ANgesLAB solo fija la clave al CREAR el usuario,
  nunca pisa un hash existente).

Que hace:
  1. Copia la base indicada (por defecto ANgesLAB.accdb del proyecto).
  2. CONSERVA todo el catalogo: pruebas, parametros, valores de
     referencia, areas, unidades, germenes, antimicrobianos, perfiles,
     opciones de captura, roles y permisos.
  3. VACIA los datos operativos y personales: pacientes, solicitudes,
     resultados, facturacion, inventario, auditoria y la configuracion
     propia del laboratorio (nombre, RIF, logo, bioanalistas, precios).
  4. Deja SOLO dos usuarios: 'developer' con la clave de soporte estandar
     (se copia el hash PBKDF2 embebido en ANgesLAB.pyw, nunca la clave en
     texto) y 'admin' con la contrasena inicial documentada.

Uso:
    python crear_plantilla_bd.py                    # usa ANgesLAB.accdb
    python crear_plantilla_bd.py "ruta\\otra.accdb"  # otra base de origen

El archivo generado es el que referencia instalador\\ANgesLAB_Setup.iss.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import re
import shutil
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PLANTILLA = BASE_DIR / 'ANgesLAB_plantilla.accdb'

# --- Tablas que se vacian -----------------------------------------------
# Orden: primero las hijas, despues las padres, para no chocar con las
# relaciones de integridad referencial.
TABLAS_A_VACIAR = [
    # Resultados y solicitudes
    'ResultadosParametros', 'ResultadosMicrobiologia', 'Resultados',
    'HistorialResultados', 'Sensibilidades',
    'DetalleSolicitudes', 'PruebasSolicitadas', 'MuestrasSolicitud',
    'AccesosQR',
    'Solicitudes',
    'ResultadosVet', 'DetalleSolicitudesVet', 'SolicitudesVet',
    'PacientesVet',
    # Facturacion y caja
    'DetalleFacturas', 'Cobros', 'Pagos', 'CuentasPorCobrar',
    'CuentasPorPagar', 'Facturas', 'Recibos',
    'DetalleCotizaciones', 'Cotizaciones',
    'MovimientosCaja', 'CajaChica', 'Gastos',
    # Compras e inventario
    'DetalleCompras', 'Compras', 'MovimientosInventario',
    # Personas
    'Pacientes', 'Medicos', 'Bioanalistas', 'Responsables', 'Receptores',
    # Configuracion propia del laboratorio
    'ConfiguracionLaboratorio', 'ConfiguracionAdministrativa',
    'ListasPrecios', 'Precios', 'TasasCambio', 'CuentasBancarias',
    # Bitacora
    'LogAuditoria', 'Pendientes',
    # Usuarios (se recrean mas abajo)
    'UsuarioRol', 'Usuarios',
]

# --- Tablas de catalogo que NO se tocan (documentacion viva) -------------
TABLAS_CATALOGO = [
    'Areas', 'Pruebas', 'Parametros', 'ParametrosPrueba', 'Unidades',
    'UnidadesParametro', 'ValoresReferencia', 'ValoresReferenciaEdadSexo',
    'OpcionesParametro', 'Perfiles', 'PruebasEnPerfil', 'Germenes',
    'Antimicrobianos', 'TiposMuestra', 'Categorias', 'SubCategorias',
    'CategoriaGastos', 'Bancos', 'FormasPago', 'Roles', 'Permisos',
    'PermisosModulo', 'Marcas', 'Productos', 'Proveedores',
    'ParametrosVet', 'PruebasVet', 'ConfiguracionVet',
    'ConfiguracionSistema', 'ConfiguracionNumeracion',
]


def conectar(ruta):
    import win32com.client
    cn = win32com.client.Dispatch('ADODB.Connection')
    cn.Open(f'Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta};')
    return cn


def contar(cn, tabla):
    """Filas de la tabla, o None si no existe.

    El recordset se guarda en una variable: encadenar
    .Execute(...)[0].Fields(0).Value lo libera antes de leerlo y ADO
    responde 'el objeto ya no es valido' para TODAS las tablas.
    """
    try:
        rs = cn.Execute(f'SELECT COUNT(*) FROM [{tabla}]')[0]
        n = rs.Fields(0).Value
        rs.Close()
        return n
    except Exception:
        return None


def credenciales_developer():
    """Lee de ANgesLAB.pyw el hash de la clave de soporte del developer.

    Se toma del codigo para que plantilla y aplicacion no se desincronicen,
    y para no escribir la contrasena en texto en ningun lado.
    """
    fuente = (BASE_DIR / 'ANgesLAB.pyw').read_text(encoding='utf-8')
    def _constante(nombre):
        m = re.search(nombre + r"\s*=\s*\(([^)]+)\)", fuente)
        if not m:
            raise SystemExit(f'No se encontro {nombre} en ANgesLAB.pyw')
        return ''.join(re.findall(r"'([^']*)'", m.group(1)))
    return _constante('_DEV_HASH_FIJO'), _constante('_DEV_SALT_FIJO')


def hash_admin():
    """Hash PBKDF2 de la contrasena inicial de 'admin' (la misma que crea
    la aplicacion en una base vacia; el cliente debe cambiarla)."""
    sys.path.insert(0, str(BASE_DIR))
    from modulos.seguridad_db import SeguridadContrasenas
    return SeguridadContrasenas.hash_password('admin123')


def main(argv):
    origen = Path(argv[1]).resolve() if len(argv) > 1 else BASE_DIR / 'ANgesLAB.accdb'
    if not origen.exists():
        print(f'ERROR: no existe la base de origen: {origen}')
        return 1

    print('=' * 70)
    print('  PLANTILLA DE BASE DE DATOS PARA EL INSTALADOR')
    print('=' * 70)
    print(f'Origen  : {origen}')
    print(f'Destino : {PLANTILLA}\n')

    shutil.copy2(origen, PLANTILLA)
    cn = conectar(PLANTILLA)

    print('-- Vaciando datos operativos y personales')
    borradas, omitidas = 0, []
    for tabla in TABLAS_A_VACIAR:
        antes = contar(cn, tabla)
        if antes is None:
            omitidas.append(tabla)
            continue
        if antes:
            try:
                cn.Execute(f'DELETE FROM [{tabla}]')
                print(f'   {tabla:<32} {antes:>6} -> {contar(cn, tabla)}')
                borradas += 1
            except Exception as e:
                print(f'   [AVISO] {tabla}: {str(e)[:90]}')
    if omitidas:
        print(f'   (no existen en esta base: {", ".join(omitidas)})')

    print('\n-- Reiniciando contadores de autonumeracion')
    for tabla in TABLAS_A_VACIAR:
        if contar(cn, tabla) == 0:
            try:
                cn.Execute(f'ALTER TABLE [{tabla}] ALTER COLUMN '
                           f'[{tabla[:-1] if tabla.endswith("s") else tabla}ID] '
                           f'COUNTER(1,1)')
            except Exception:
                pass  # nombre de PK distinto: no es critico

    print('\n-- Creando usuarios de fabrica')
    dev_hash, dev_salt = credenciales_developer()
    adm_hash, adm_salt = hash_admin()
    cn.Execute(
        "INSERT INTO [Usuarios] ([NombreCompleto],[NombreUsuario],[Password],"
        "[PasswordHash],[PasswordSalt],[Nivel],[Activo]) VALUES "
        f"('Desarrollador ANgesLAB','developer','','{dev_hash}','{dev_salt}',"
        "'Desarrollador',True)")
    cn.Execute(
        "INSERT INTO [Usuarios] ([NombreCompleto],[NombreUsuario],[Password],"
        "[PasswordHash],[PasswordSalt],[Nivel],[Activo]) VALUES "
        f"('Administrador','admin','','{adm_hash}','{adm_salt}',"
        "'Administrador',True)")
    print('   developer  (clave de soporte del proveedor)')
    print('   admin      (contrasena inicial admin123)')

    print('\n-- Catalogo conservado')
    for tabla in TABLAS_CATALOGO:
        n = contar(cn, tabla)
        if n:
            print(f'   {tabla:<32} {n:>6}')

    cn.Close()
    mb = PLANTILLA.stat().st_size / (1024 * 1024)
    print('\n' + '=' * 70)
    print(f'  PLANTILLA LISTA  -  {borradas} tablas vaciadas  -  {mb:.1f} MB')
    print('=' * 70)
    print('Es la base que empaqueta instalador\\ANgesLAB_Setup.iss.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))

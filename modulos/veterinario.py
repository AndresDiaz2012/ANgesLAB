# -*- coding: utf-8 -*-
"""
Modulo Veterinario - ANgesLAB
================================================================================
Modulo para gestion de pacientes veterinarios (Felinos, Caninos, Bovinos).

Funcionalidades:
- Crear y gestionar tablas veterinarias en la BD
- CRUD de pacientes veterinarios
- Solicitudes veterinarias con numeracion VET-XXX
- Valores de referencia por especie
- Generacion de PDF con datos adaptados

Copyright 2024-2025 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP

# ============================================================================
# CONSTANTES
# ============================================================================

ESPECIES = ['FELINO', 'CANINO', 'BOVINO']

RAZAS = {
    'FELINO': ['Mestizo', 'Persa', 'Siames', 'Maine Coon', 'Angora', 'Bengal', 'Ragdoll', 'Otro'],
    'CANINO': ['Mestizo', 'Pastor Aleman', 'Labrador', 'Golden Retriever', 'Bulldog', 'Poodle',
               'Rottweiler', 'Chihuahua', 'Beagle', 'Pitbull', 'Otro'],
    'BOVINO': ['Mestizo', 'Brahman', 'Holstein', 'Angus', 'Hereford', 'Simmental', 'Charolais', 'Carora', 'Otro'],
}

# Valores de referencia por especie
VALORES_REFERENCIA = {
    # HEMATOLOGIA
    # HEMATOLOGIA - Fuente: MSD Veterinary Manual (Latimer KS, Schalm's Veterinary Hematology)
    'Hematies': {
        'FELINO': {'min': 5.0, 'max': 10.0, 'unidad': 'x10^6/uL'},
        'CANINO': {'min': 5.5, 'max': 8.5, 'unidad': 'x10^6/uL'},
        'BOVINO':  {'min': 5.0, 'max': 10.0, 'unidad': 'x10^6/uL'},
    },
    'Hemoglobina': {
        'FELINO': {'min': 8.0, 'max': 15.0, 'unidad': 'g/dL'},
        'CANINO': {'min': 12.0, 'max': 18.0, 'unidad': 'g/dL'},
        'BOVINO':  {'min': 8.0, 'max': 15.0, 'unidad': 'g/dL'},
    },
    'Hematocrito': {
        'FELINO': {'min': 24, 'max': 45, 'unidad': '%'},
        'CANINO': {'min': 37, 'max': 55, 'unidad': '%'},
        'BOVINO':  {'min': 24, 'max': 46, 'unidad': '%'},
    },
    'VCM': {
        'FELINO': {'min': 39, 'max': 55, 'unidad': 'fL'},
        'CANINO': {'min': 60, 'max': 77, 'unidad': 'fL'},
        'BOVINO':  {'min': 40, 'max': 60, 'unidad': 'fL'},
    },
    'HCM': {
        'FELINO': {'min': 13, 'max': 17, 'unidad': 'pg'},
        'CANINO': {'min': 19, 'max': 25, 'unidad': 'pg'},
        'BOVINO':  {'min': 11, 'max': 17, 'unidad': 'pg'},
    },
    'CHCM': {
        'FELINO': {'min': 30, 'max': 36, 'unidad': 'g/dL'},
        'CANINO': {'min': 32, 'max': 36, 'unidad': 'g/dL'},
        'BOVINO':  {'min': 30, 'max': 36, 'unidad': 'g/dL'},
    },
    'Leucocitos': {
        'FELINO': {'min': 5.5, 'max': 19.5, 'unidad': 'x10^3/uL'},
        'CANINO': {'min': 6.0, 'max': 17.0, 'unidad': 'x10^3/uL'},
        'BOVINO':  {'min': 4.0, 'max': 12.0, 'unidad': 'x10^3/uL'},
    },
    'Plaquetas': {
        'FELINO': {'min': 175, 'max': 500, 'unidad': 'x10^3/uL'},
        'CANINO': {'min': 175, 'max': 500, 'unidad': 'x10^3/uL'},
        'BOVINO':  {'min': 100, 'max': 800, 'unidad': 'x10^3/uL'},
    },
    # QUIMICA CLINICA - Fuente: MSD Veterinary Manual (Kaneko, Clinical Biochemistry of Domestic Animals)
    'Glucosa': {
        'FELINO': {'min': 74, 'max': 159, 'unidad': 'mg/dL'},
        'CANINO': {'min': 74, 'max': 143, 'unidad': 'mg/dL'},
        'BOVINO':  {'min': 40, 'max': 100, 'unidad': 'mg/dL'},
    },
    'Urea': {
        'FELINO': {'min': 30, 'max': 60, 'unidad': 'mg/dL'},
        'CANINO': {'min': 10, 'max': 28, 'unidad': 'mg/dL'},
        'BOVINO':  {'min': 10, 'max': 25, 'unidad': 'mg/dL'},
    },
    'Creatinina': {
        'FELINO': {'min': 0.8, 'max': 2.4, 'unidad': 'mg/dL'},
        'CANINO': {'min': 0.5, 'max': 1.8, 'unidad': 'mg/dL'},
        'BOVINO':  {'min': 0.5, 'max': 2.2, 'unidad': 'mg/dL'},
    },
    'Colesterol': {
        'FELINO': {'min': 89, 'max': 258, 'unidad': 'mg/dL'},
        'CANINO': {'min': 135, 'max': 270, 'unidad': 'mg/dL'},
        'BOVINO':  {'min': 36, 'max': 54, 'unidad': 'mg/dL'},
    },
    'Trigliceridos': {
        'FELINO': {'min': 25, 'max': 160, 'unidad': 'mg/dL'},
        'CANINO': {'min': 50, 'max': 150, 'unidad': 'mg/dL'},
        'BOVINO':  {'min': 12, 'max': 31, 'unidad': 'mg/dL'},
    },
    'ALT': {
        'FELINO': {'min': 12, 'max': 130, 'unidad': 'U/L'},
        'CANINO': {'min': 21, 'max': 102, 'unidad': 'U/L'},
        'BOVINO':  {'min': 31, 'max': 58, 'unidad': 'U/L'},
    },
    'AST': {
        'FELINO': {'min': 12, 'max': 40, 'unidad': 'U/L'},
        'CANINO': {'min': 23, 'max': 66, 'unidad': 'U/L'},
        'BOVINO':  {'min': 60, 'max': 125, 'unidad': 'U/L'},
    },
    'Proteinas Totales': {
        'FELINO': {'min': 5.7, 'max': 7.9, 'unidad': 'g/dL'},
        'CANINO': {'min': 5.2, 'max': 8.2, 'unidad': 'g/dL'},
        'BOVINO':  {'min': 6.7, 'max': 7.5, 'unidad': 'g/dL'},
    },
    'Albumina': {
        'FELINO': {'min': 2.1, 'max': 3.3, 'unidad': 'g/dL'},
        'CANINO': {'min': 2.6, 'max': 3.3, 'unidad': 'g/dL'},
        'BOVINO':  {'min': 2.5, 'max': 3.8, 'unidad': 'g/dL'},
    },
    'Bilirrubina Total': {
        'FELINO': {'min': 0.1, 'max': 0.4, 'unidad': 'mg/dL'},
        'CANINO': {'min': 0.1, 'max': 0.5, 'unidad': 'mg/dL'},
        'BOVINO':  {'min': 0.0, 'max': 1.6, 'unidad': 'mg/dL'},
    },
    'Fosfatasa Alcalina': {
        'FELINO': {'min': 14, 'max': 111, 'unidad': 'U/L'},
        'CANINO': {'min': 23, 'max': 212, 'unidad': 'U/L'},
        'BOVINO':  {'min': 118, 'max': 395, 'unidad': 'U/L'},
    },
}


# ============================================================================
# CLASE PRINCIPAL: GESTOR VETERINARIO
# ============================================================================

class GestorVeterinario:
    """Gestor centralizado para toda la logica veterinaria."""

    def __init__(self, db, usuario=None):
        self.db = db
        self.usuario = usuario or {}
        self._inicializar_tablas()

    # ========================================================================
    # INICIALIZACION DE TABLAS
    # ========================================================================

    def _inicializar_tablas(self):
        """Crea las tablas veterinarias si no existen."""
        # Orden importa: primero tablas base, luego dependientes
        tablas_ordenadas = [
            ('ConfiguracionVet', """
                CREATE TABLE ConfiguracionVet (
                    ConfigVetID AUTOINCREMENT PRIMARY KEY,
                    UltimoNumeroSolicitud INTEGER
                )
            """),
            ('PruebasVet', """
                CREATE TABLE PruebasVet (
                    PruebaVetID AUTOINCREMENT PRIMARY KEY,
                    CodigoPrueba TEXT(20),
                    NombrePrueba TEXT(100),
                    Categoria TEXT(50),
                    Precio DOUBLE,
                    Activo BIT
                )
            """),
            ('PacientesVet', """
                CREATE TABLE PacientesVet (
                    PacienteVetID AUTOINCREMENT PRIMARY KEY,
                    CodigoPaciente TEXT(20),
                    NombreMascota TEXT(100),
                    Especie TEXT(20),
                    Raza TEXT(50),
                    Sexo TEXT(1),
                    FechaNacimiento DATETIME,
                    Peso DOUBLE,
                    Color TEXT(50),
                    NombrePropietario TEXT(100),
                    TelefonoPropietario TEXT(50),
                    EmailPropietario TEXT(100),
                    DireccionPropietario TEXT(255),
                    VeterinarioRemitente TEXT(100),
                    FechaRegistro DATETIME,
                    Activo BIT
                )
            """),
            ('SolicitudesVet', """
                CREATE TABLE SolicitudesVet (
                    SolicitudVetID AUTOINCREMENT PRIMARY KEY,
                    NumeroSolicitud TEXT(30),
                    FechaSolicitud DATETIME,
                    PacienteVetID INTEGER,
                    EstadoSolicitud TEXT(20),
                    Observaciones MEMO,
                    MontoTotal DOUBLE,
                    UsuarioRegistro INTEGER
                )
            """),
            ('DetalleSolicitudesVet', """
                CREATE TABLE DetalleSolicitudesVet (
                    DetalleVetID AUTOINCREMENT PRIMARY KEY,
                    SolicitudVetID INTEGER,
                    PruebaVetID INTEGER,
                    NombrePrueba TEXT(100),
                    PrecioUnitario DOUBLE,
                    Estado TEXT(20)
                )
            """),
            ('ParametrosVet', """
                CREATE TABLE ParametrosVet (
                    ParametroVetID AUTOINCREMENT PRIMARY KEY,
                    PruebaVetID INTEGER,
                    NombreParametro TEXT(100),
                    Unidad TEXT(30),
                    Secuencia INTEGER,
                    EsCalculado BIT
                )
            """),
            ('ResultadosVet', """
                CREATE TABLE ResultadosVet (
                    ResultadoVetID AUTOINCREMENT PRIMARY KEY,
                    DetalleVetID INTEGER,
                    ParametroVetID INTEGER,
                    Valor TEXT(255),
                    Estado TEXT(20),
                    FechaCaptura DATETIME,
                    UsuarioCaptura INTEGER
                )
            """),
        ]

        for nombre, ddl in tablas_ordenadas:
            try:
                self.db.execute(ddl)
                print(f"[VET] Tabla {nombre} creada")
            except Exception as e:
                # La tabla ya existe - esto es normal
                pass

        # Inicializar configuracion si no existe
        try:
            config = self.db.query_one("SELECT * FROM ConfiguracionVet")
            if not config:
                self.db.execute("INSERT INTO ConfiguracionVet (UltimoNumeroSolicitud) VALUES (0)")
                print("[VET] ConfiguracionVet inicializada")
        except Exception as e:
            print(f"[VET] Error inicializando ConfiguracionVet: {e}")

        # Inicializar pruebas y parametros veterinarios si estan vacios
        self._inicializar_pruebas_vet()

    def _inicializar_pruebas_vet(self):
        """Crea las pruebas y parametros veterinarios predeterminados."""
        try:
            count = self.db.count('PruebasVet')
            if count > 0:
                return  # Ya hay pruebas
        except Exception as e:
            print(f"[VET] Error verificando PruebasVet: {e}")
            return

        parametros_hematologia = [
            ('Hematies', 'x10^6/uL', 1, False),
            ('Hemoglobina', 'g/dL', 2, False),
            ('Hematocrito', '%', 3, False),
            ('VCM', 'fL', 4, True),
            ('HCM', 'pg', 5, True),
            ('CHCM', 'g/dL', 6, True),
            ('Leucocitos', 'x10^3/uL', 7, False),
            ('Plaquetas', 'x10^3/uL', 8, False),
        ]

        parametros_quimica = [
            ('Glucosa', 'mg/dL', 1, False),
            ('Urea', 'mg/dL', 2, False),
            ('Creatinina', 'mg/dL', 3, False),
            ('Colesterol', 'mg/dL', 4, False),
            ('Trigliceridos', 'mg/dL', 5, False),
            ('ALT', 'U/L', 6, False),
            ('AST', 'U/L', 7, False),
            ('Proteinas Totales', 'g/dL', 8, False),
            ('Albumina', 'g/dL', 9, False),
            ('Bilirrubina Total', 'mg/dL', 10, False),
            ('Fosfatasa Alcalina', 'U/L', 11, False),
        ]

        try:
            # Insertar pruebas usando SQL directo para evitar problemas con BIT
            self.db.execute("""
                INSERT INTO PruebasVet (CodigoPrueba, NombrePrueba, Categoria, Precio, Activo)
                VALUES ('VET-HEM', 'Hematologia Completa', 'Hematologia', 0, True)
            """)
            self.db.execute("""
                INSERT INTO PruebasVet (CodigoPrueba, NombrePrueba, Categoria, Precio, Activo)
                VALUES ('VET-QC', 'Quimica Clinica', 'Quimica', 0, True)
            """)

            # Obtener IDs de las pruebas recien creadas
            hem = self.db.query_one("SELECT PruebaVetID FROM PruebasVet WHERE CodigoPrueba='VET-HEM'")
            qc = self.db.query_one("SELECT PruebaVetID FROM PruebasVet WHERE CodigoPrueba='VET-QC'")

            if hem:
                hem_id = hem['PruebaVetID']
                for nombre, unidad, seq, calc in parametros_hematologia:
                    calc_val = 'True' if calc else 'False'
                    nombre_safe = nombre.replace("'", "''")
                    self.db.execute(f"""
                        INSERT INTO ParametrosVet (PruebaVetID, NombreParametro, Unidad, Secuencia, EsCalculado)
                        VALUES ({hem_id}, '{nombre_safe}', '{unidad}', {seq}, {calc_val})
                    """)

            if qc:
                qc_id = qc['PruebaVetID']
                for nombre, unidad, seq, calc in parametros_quimica:
                    calc_val = 'True' if calc else 'False'
                    nombre_safe = nombre.replace("'", "''")
                    self.db.execute(f"""
                        INSERT INTO ParametrosVet (PruebaVetID, NombreParametro, Unidad, Secuencia, EsCalculado)
                        VALUES ({qc_id}, '{nombre_safe}', '{unidad}', {seq}, {calc_val})
                    """)

            print("[VET] Pruebas y parametros veterinarios inicializados")
        except Exception as e:
            print(f"[VET] Error inicializando pruebas: {e}")

    # ========================================================================
    # NUMERACION
    # ========================================================================

    def generar_numero_solicitud(self):
        """Genera el siguiente numero de solicitud VET-XXXX."""
        try:
            config = self.db.query_one("SELECT UltimoNumeroSolicitud FROM ConfiguracionVet")
            if config:
                ultimo = config.get('UltimoNumeroSolicitud') or 0
                # Convertir a int por si Access lo devuelve como otro tipo
                ultimo = int(ultimo)
            else:
                ultimo = 0
                # Crear registro de configuracion si no existe
                self.db.execute("INSERT INTO ConfiguracionVet (UltimoNumeroSolicitud) VALUES (0)")

            nuevo = ultimo + 1
            self.db.execute(f"UPDATE ConfiguracionVet SET UltimoNumeroSolicitud = {nuevo}")
            return f"VET-{nuevo:04d}"
        except Exception as e:
            print(f"[VET] Error generando numero: {e}")
            # Fallback: usar timestamp
            return f"VET-{datetime.now().strftime('%H%M%S')}"

    # ========================================================================
    # PACIENTES
    # ========================================================================

    def buscar_pacientes(self, filtro=""):
        """Busca pacientes veterinarios."""
        where = ""
        if filtro:
            filtro_safe = filtro.replace("'", "''")
            where = f"""WHERE NombreMascota LIKE '%{filtro_safe}%'
                        OR NombrePropietario LIKE '%{filtro_safe}%'
                        OR CodigoPaciente LIKE '%{filtro_safe}%'
                        OR Especie LIKE '%{filtro_safe}%'"""
        try:
            return self.db.query(f"""
                SELECT TOP 200 * FROM PacientesVet {where}
                ORDER BY PacienteVetID DESC
            """)
        except Exception as e:
            print(f"[VET] Error buscando pacientes: {e}")
            return []

    def obtener_paciente(self, paciente_id):
        """Obtiene un paciente por ID."""
        try:
            return self.db.query_one(f"SELECT * FROM PacientesVet WHERE PacienteVetID = {paciente_id}")
        except:
            return None

    def guardar_paciente(self, datos, paciente_id=None):
        """Guarda o actualiza un paciente veterinario."""
        if paciente_id:
            self.db.update('PacientesVet', datos, f"PacienteVetID = {paciente_id}")
        else:
            # Generar codigo automatico
            try:
                count = self.db.count('PacientesVet')
                datos['CodigoPaciente'] = f"PVET-{count + 1:04d}"
            except:
                datos['CodigoPaciente'] = f"PVET-{datetime.now().strftime('%H%M%S')}"
            datos['FechaRegistro'] = datetime.now()

            # Construir INSERT con SQL directo para compatibilidad Access
            campos = []
            valores = []
            for k, v in datos.items():
                campos.append(f"[{k}]")
                valores.append(self.db.escape(v))

            # Agregar Activo como True
            campos.append("[Activo]")
            valores.append("True")

            sql = f"INSERT INTO PacientesVet ({', '.join(campos)}) VALUES ({', '.join(valores)})"
            self.db.execute(sql)

    # ========================================================================
    # SOLICITUDES
    # ========================================================================

    def obtener_pruebas_disponibles(self):
        """Obtiene las pruebas veterinarias disponibles."""
        try:
            return self.db.query("""
                SELECT PruebaVetID, CodigoPrueba, NombrePrueba, Categoria, Precio
                FROM PruebasVet
                WHERE Activo <> 0 OR Activo IS NULL
                ORDER BY Categoria, NombrePrueba
            """)
        except Exception as e:
            print(f"[VET] Error obteniendo pruebas: {e}")
            # Fallback sin filtro de activo
            try:
                return self.db.query("""
                    SELECT PruebaVetID, CodigoPrueba, NombrePrueba, Categoria, Precio
                    FROM PruebasVet
                    ORDER BY Categoria, NombrePrueba
                """)
            except:
                return []

    def crear_solicitud(self, paciente_id, pruebas_ids):
        """Crea una nueva solicitud veterinaria con las pruebas seleccionadas."""
        numero = self.generar_numero_solicitud()
        try:
            fecha_now = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            usuario_id = self.usuario.get('UsuarioID', 1)

            self.db.execute(f"""
                INSERT INTO SolicitudesVet
                (NumeroSolicitud, FechaSolicitud, PacienteVetID, EstadoSolicitud, MontoTotal, UsuarioRegistro)
                VALUES ('{numero}', {fecha_now}, {paciente_id}, 'Pendiente', 0, {usuario_id})
            """)

            # Obtener ID de la solicitud recien creada
            sol = self.db.query_one(f"""
                SELECT TOP 1 SolicitudVetID FROM SolicitudesVet
                WHERE NumeroSolicitud = '{numero}'
                ORDER BY SolicitudVetID DESC
            """)
            if not sol:
                print("[VET] No se pudo recuperar la solicitud creada")
                return None

            sol_id = sol['SolicitudVetID']
            monto_total = 0

            for prueba_id in pruebas_ids:
                prueba = self.db.query_one(f"SELECT * FROM PruebasVet WHERE PruebaVetID = {prueba_id}")
                if prueba:
                    precio = prueba.get('Precio') or 0
                    nombre_prueba = (prueba.get('NombrePrueba') or '').replace("'", "''")
                    self.db.execute(f"""
                        INSERT INTO DetalleSolicitudesVet
                        (SolicitudVetID, PruebaVetID, NombrePrueba, PrecioUnitario, Estado)
                        VALUES ({sol_id}, {prueba_id}, '{nombre_prueba}', {precio}, 'Pendiente')
                    """)
                    monto_total += float(precio)

            if monto_total > 0:
                self.db.execute(f"UPDATE SolicitudesVet SET MontoTotal = {monto_total} WHERE SolicitudVetID = {sol_id}")

            print(f"[VET] Solicitud {numero} creada con ID {sol_id}")
            return sol_id
        except Exception as e:
            print(f"[VET] Error creando solicitud: {e}")
            import traceback
            traceback.print_exc()
            return None

    def buscar_solicitudes(self, filtro=""):
        """Busca solicitudes veterinarias."""
        where = ""
        if filtro:
            filtro_safe = filtro.replace("'", "''")
            where = f"""WHERE s.NumeroSolicitud LIKE '%{filtro_safe}%'
                        OR p.NombreMascota LIKE '%{filtro_safe}%'
                        OR p.NombrePropietario LIKE '%{filtro_safe}%'"""
        try:
            return self.db.query(f"""
                SELECT TOP 200 s.SolicitudVetID, s.NumeroSolicitud, s.FechaSolicitud,
                       p.NombreMascota, p.Especie, p.NombrePropietario,
                       s.EstadoSolicitud, s.MontoTotal
                FROM SolicitudesVet s
                LEFT JOIN PacientesVet p ON s.PacienteVetID = p.PacienteVetID
                {where} ORDER BY s.SolicitudVetID DESC
            """)
        except Exception as e:
            print(f"[VET] Error buscando solicitudes: {e}")
            return []

    def obtener_solicitud(self, solicitud_id):
        """Obtiene una solicitud con datos del paciente."""
        try:
            return self.db.query_one(f"""
                SELECT s.*, p.NombreMascota, p.Especie, p.Raza, p.Sexo,
                       p.FechaNacimiento, p.Peso, p.Color,
                       p.NombrePropietario, p.TelefonoPropietario,
                       p.EmailPropietario, p.VeterinarioRemitente
                FROM SolicitudesVet s
                LEFT JOIN PacientesVet p ON s.PacienteVetID = p.PacienteVetID
                WHERE s.SolicitudVetID = {solicitud_id}
            """)
        except:
            return None

    def obtener_detalles_solicitud(self, solicitud_id):
        """Obtiene los detalles (pruebas) de una solicitud."""
        try:
            return self.db.query(f"""
                SELECT d.DetalleVetID, d.PruebaVetID, d.NombrePrueba, d.PrecioUnitario, d.Estado
                FROM DetalleSolicitudesVet d
                WHERE d.SolicitudVetID = {solicitud_id}
                ORDER BY d.DetalleVetID
            """)
        except:
            return []

    def obtener_parametros_prueba(self, prueba_vet_id):
        """Obtiene los parametros de una prueba veterinaria."""
        try:
            return self.db.query(f"""
                SELECT ParametroVetID, NombreParametro, Unidad, Secuencia, EsCalculado
                FROM ParametrosVet
                WHERE PruebaVetID = {prueba_vet_id}
                ORDER BY Secuencia
            """)
        except:
            return []

    # ========================================================================
    # VALORES DE REFERENCIA
    # ========================================================================

    def obtener_referencia(self, nombre_parametro, especie):
        """Obtiene los valores de referencia para un parametro y especie."""
        ref = VALORES_REFERENCIA.get(nombre_parametro, {}).get(especie)
        if ref:
            return f"{ref['min']} - {ref['max']}"
        return '---'

    def obtener_referencia_completa(self, nombre_parametro, especie):
        """Obtiene el dict completo de referencia para un parametro y especie."""
        return VALORES_REFERENCIA.get(nombre_parametro, {}).get(especie)

    def evaluar_resultado(self, nombre_parametro, especie, valor_str):
        """Evalua si un resultado esta dentro del rango de referencia.
        Retorna: 'normal', 'bajo', 'alto' o None si no aplica."""
        ref = self.obtener_referencia_completa(nombre_parametro, especie)
        if not ref:
            return None
        try:
            valor = float(valor_str)
            if valor < ref['min']:
                return 'bajo'
            elif valor > ref['max']:
                return 'alto'
            return 'normal'
        except (ValueError, TypeError):
            return None

    # ========================================================================
    # RESULTADOS
    # ========================================================================

    def guardar_resultado(self, detalle_vet_id, parametro_vet_id, valor, usuario_id=1):
        """Guarda o actualiza un resultado."""
        try:
            valor_safe = str(valor).replace("'", "''")
            fecha_now = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')

            existe = self.db.query_one(f"""
                SELECT ResultadoVetID FROM ResultadosVet
                WHERE DetalleVetID = {detalle_vet_id} AND ParametroVetID = {parametro_vet_id}
            """)
            if existe:
                self.db.execute(f"""
                    UPDATE ResultadosVet SET
                        Valor = '{valor_safe}',
                        Estado = 'Capturado',
                        FechaCaptura = {fecha_now},
                        UsuarioCaptura = {usuario_id}
                    WHERE DetalleVetID = {detalle_vet_id} AND ParametroVetID = {parametro_vet_id}
                """)
            else:
                self.db.execute(f"""
                    INSERT INTO ResultadosVet
                    (DetalleVetID, ParametroVetID, Valor, Estado, FechaCaptura, UsuarioCaptura)
                    VALUES ({detalle_vet_id}, {parametro_vet_id}, '{valor_safe}', 'Capturado', {fecha_now}, {usuario_id})
                """)
            return True
        except Exception as e:
            print(f"[VET] Error guardando resultado: {e}")
            return False

    def obtener_resultado(self, detalle_vet_id, parametro_vet_id):
        """Obtiene un resultado guardado."""
        try:
            return self.db.query_one(f"""
                SELECT Valor FROM ResultadosVet
                WHERE DetalleVetID = {detalle_vet_id} AND ParametroVetID = {parametro_vet_id}
            """)
        except:
            return None

    def ejecutar_calculos_hematologia(self, detalle_vet_id):
        """Calcula VCM, HCM, CHCM a partir de los valores ingresados."""
        try:
            # Obtener parametros del detalle
            detalle = self.db.query_one(f"""
                SELECT PruebaVetID FROM DetalleSolicitudesVet WHERE DetalleVetID = {detalle_vet_id}
            """)
            if not detalle:
                return 0

            parametros = self.obtener_parametros_prueba(detalle['PruebaVetID'])
            param_map = {}  # nombre -> ParametroVetID
            for p in parametros:
                param_map[p['NombreParametro']] = p['ParametroVetID']

            # Obtener valores ingresados
            valores = {}
            for nombre, pid in param_map.items():
                res = self.obtener_resultado(detalle_vet_id, pid)
                if res and res.get('Valor'):
                    try:
                        valores[nombre] = float(res['Valor'])
                    except:
                        pass

            calculados = 0
            hematies = valores.get('Hematies')
            hemoglobina = valores.get('Hemoglobina')
            hematocrito = valores.get('Hematocrito')

            # VCM = (Hematocrito / Hematies) * 10
            if hematocrito and hematies and hematies > 0 and 'VCM' in param_map:
                vcm = round((hematocrito / hematies) * 10, 1)
                self.guardar_resultado(detalle_vet_id, param_map['VCM'], str(vcm),
                                      self.usuario.get('UsuarioID', 1))
                calculados += 1

            # HCM = (Hemoglobina / Hematies) * 10
            if hemoglobina and hematies and hematies > 0 and 'HCM' in param_map:
                hcm = round((hemoglobina / hematies) * 10, 1)
                self.guardar_resultado(detalle_vet_id, param_map['HCM'], str(hcm),
                                      self.usuario.get('UsuarioID', 1))
                calculados += 1

            # CHCM = (Hemoglobina / Hematocrito) * 100
            if hemoglobina and hematocrito and hematocrito > 0 and 'CHCM' in param_map:
                chcm = round((hemoglobina / hematocrito) * 100, 1)
                self.guardar_resultado(detalle_vet_id, param_map['CHCM'], str(chcm),
                                      self.usuario.get('UsuarioID', 1))
                calculados += 1

            return calculados
        except Exception as e:
            print(f"[VET] Error en calculos hematologia: {e}")
            return 0

    def validar_resultados(self, detalle_vet_id):
        """Valida todos los resultados de un detalle."""
        try:
            self.db.execute(f"""
                UPDATE ResultadosVet SET Estado = 'Validado'
                WHERE DetalleVetID = {detalle_vet_id}
            """)
            self.db.update('DetalleSolicitudesVet', {
                'Estado': 'Validado'
            }, f"DetalleVetID = {detalle_vet_id}")
            return True
        except Exception as e:
            print(f"[VET] Error validando: {e}")
            return False

    def solicitudes_pendientes(self):
        """Obtiene solicitudes con resultados pendientes."""
        try:
            return self.db.query("""
                SELECT TOP 100 s.SolicitudVetID, s.NumeroSolicitud,
                       p.NombreMascota, p.Especie, s.EstadoSolicitud
                FROM SolicitudesVet s
                LEFT JOIN PacientesVet p ON s.PacienteVetID = p.PacienteVetID
                WHERE s.EstadoSolicitud IN ('Pendiente', 'En Proceso')
                ORDER BY s.SolicitudVetID DESC
            """)
        except:
            return []


# ============================================================================
# FUNCION FACTORY
# ============================================================================

def crear_gestor_veterinario(db, usuario=None):
    """Crea una instancia del gestor veterinario."""
    return GestorVeterinario(db, usuario)

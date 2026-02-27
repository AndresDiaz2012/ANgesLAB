"""
================================================================================
MODULO DE UTILIDADES DE BASE DE DATOS - ANgesLAB
================================================================================
Proporciona funciones de utilidad para:
- Mantenimiento de base de datos
- Backup y restauracion
- Migracion de datos
- Indices y optimizacion
- Limpieza de datos

Autor: Sistema ANgesLAB
================================================================================
"""

import os
import shutil
from datetime import datetime, timedelta
import json

# ============================================================================
# CONFIGURACION
# ============================================================================

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')

# ============================================================================
# CLASE PRINCIPAL
# ============================================================================

class UtilidadesDB:
    """
    Utilidades de mantenimiento y optimizacion de base de datos
    """

    def __init__(self, db, db_path):
        self.db = db
        self.db_path = db_path

    # -------------------------------------------------------------------------
    # BACKUP Y RESTAURACION
    # -------------------------------------------------------------------------

    def crear_backup(self, nombre_personalizado=None):
        """
        Crea una copia de seguridad de la base de datos

        Args:
            nombre_personalizado: Nombre personalizado para el backup

        Returns:
            Ruta del archivo de backup
        """
        # Crear directorio de backups si no existe
        if not os.path.exists(BACKUP_DIR):
            os.makedirs(BACKUP_DIR)

        # Generar nombre del archivo
        if nombre_personalizado:
            nombre = f"{nombre_personalizado}.accdb"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            nombre = f"ANgesLAB_backup_{timestamp}.accdb"

        ruta_backup = os.path.join(BACKUP_DIR, nombre)

        # Copiar archivo
        shutil.copy2(self.db_path, ruta_backup)

        return ruta_backup

    def listar_backups(self):
        """Lista todos los backups disponibles"""
        if not os.path.exists(BACKUP_DIR):
            return []

        backups = []
        for archivo in os.listdir(BACKUP_DIR):
            if archivo.endswith('.accdb'):
                ruta = os.path.join(BACKUP_DIR, archivo)
                stats = os.stat(ruta)
                backups.append({
                    'nombre': archivo,
                    'ruta': ruta,
                    'fecha': datetime.fromtimestamp(stats.st_mtime),
                    'tamano': stats.st_size
                })

        return sorted(backups, key=lambda x: x['fecha'], reverse=True)

    def restaurar_backup(self, ruta_backup):
        """
        Restaura la base de datos desde un backup

        Args:
            ruta_backup: Ruta del archivo de backup

        Returns:
            True si la restauracion fue exitosa
        """
        if not os.path.exists(ruta_backup):
            raise Exception(f"Archivo de backup no encontrado: {ruta_backup}")

        # Crear backup del estado actual antes de restaurar
        self.crear_backup(f"pre_restauracion_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

        # Restaurar
        shutil.copy2(ruta_backup, self.db_path)

        return True

    def limpiar_backups_antiguos(self, dias=30):
        """
        Elimina backups mas antiguos que el numero de dias especificado

        Args:
            dias: Antiguedad maxima en dias

        Returns:
            Numero de backups eliminados
        """
        fecha_limite = datetime.now() - timedelta(days=dias)
        eliminados = 0

        for backup in self.listar_backups():
            if backup['fecha'] < fecha_limite:
                os.remove(backup['ruta'])
                eliminados += 1

        return eliminados

    # -------------------------------------------------------------------------
    # INDICES Y OPTIMIZACION
    # -------------------------------------------------------------------------

    def crear_indices_recomendados(self):
        """Crea indices recomendados para mejorar rendimiento"""
        indices = [
            ("idx_pacientes_documento", "Pacientes", "NumeroDocumento"),
            ("idx_solicitudes_numero", "Solicitudes", "NumeroSolicitud"),
            ("idx_solicitudes_fecha", "Solicitudes", "FechaSolicitud"),
            ("idx_solicitudes_paciente", "Solicitudes", "PacienteID"),
            ("idx_solicitudes_estado", "Solicitudes", "EstadoSolicitud"),
            ("idx_pruebas_area", "Pruebas", "AreaID"),
            ("idx_pruebas_codigo", "Pruebas", "CodigoPrueba"),
            ("idx_detallesolicitudes_solicitud", "DetalleSolicitudes", "SolicitudID"),
            ("idx_detallesolicitudes_estado", "DetalleSolicitudes", "Estado"),
            ("idx_resultadosparam_detalle", "ResultadosParametros", "DetalleID"),
            ("idx_facturas_numero", "Facturas", "NumeroFactura"),
            ("idx_facturas_fecha", "Facturas", "FechaEmision"),
            ("idx_facturas_paciente", "Facturas", "PacienteID"),
        ]

        creados = 0
        errores = []

        for nombre_idx, tabla, campo in indices:
            try:
                self.db.execute(f"CREATE INDEX {nombre_idx} ON {tabla}({campo})")
                creados += 1
            except Exception as e:
                if "already exists" not in str(e).lower():
                    errores.append(f"{nombre_idx}: {e}")

        return {
            'creados': creados,
            'errores': errores
        }

    def analizar_tablas(self):
        """
        Analiza el tamano y estado de las tablas principales

        Returns:
            Lista con informacion de cada tabla
        """
        tablas_principales = [
            'Pacientes', 'Solicitudes', 'DetalleSolicitudes', 'ResultadosParametros',
            'Pruebas', 'Parametros', 'Areas', 'Facturas', 'Pagos',
            'Medicos', 'Usuarios'
        ]

        analisis = []

        for tabla in tablas_principales:
            try:
                count = self.db.query_one(f"SELECT COUNT(*) as Total FROM {tabla}")
                analisis.append({
                    'tabla': tabla,
                    'registros': count.get('Total', 0) if count else 0,
                    'estado': 'OK'
                })
            except Exception as e:
                analisis.append({
                    'tabla': tabla,
                    'registros': 0,
                    'estado': f'Error: {e}'
                })

        return analisis

    # -------------------------------------------------------------------------
    # LIMPIEZA DE DATOS
    # -------------------------------------------------------------------------

    def limpiar_registros_huerfanos(self):
        """
        Elimina registros huerfanos (sin relacion padre)

        Returns:
            dict con cantidad de registros eliminados por tabla
        """
        eliminados = {}

        # Resultados sin detalle de solicitud
        try:
            self.db.execute("""
                DELETE FROM ResultadosParametros
                WHERE DetalleID NOT IN (SELECT DetalleID FROM DetalleSolicitudes)
            """)
            eliminados['ResultadosParametros'] = 'Limpiados'
        except Exception as e:
            eliminados['ResultadosParametros'] = f'Error: {e}'

        # Detalles de solicitud sin solicitud padre
        try:
            self.db.execute("""
                DELETE FROM DetalleSolicitudes
                WHERE SolicitudID NOT IN (SELECT SolicitudID FROM Solicitudes)
            """)
            eliminados['DetalleSolicitudes'] = 'Limpiados'
        except Exception as e:
            eliminados['DetalleSolicitudes'] = f'Error: {e}'

        # Solicitudes sin paciente
        try:
            self.db.execute("""
                DELETE FROM Solicitudes
                WHERE PacienteID NOT IN (SELECT PacienteID FROM Pacientes)
            """)
            eliminados['Solicitudes'] = 'Limpiados'
        except Exception as e:
            eliminados['Solicitudes'] = f'Error: {e}'

        # Parametros de prueba sin prueba o parametro
        try:
            self.db.execute("""
                DELETE FROM ParametrosPrueba
                WHERE PruebaID NOT IN (SELECT PruebaID FROM Pruebas)
                OR ParametroID NOT IN (SELECT ParametroID FROM Parametros)
            """)
            eliminados['ParametrosPrueba'] = 'Limpiados'
        except Exception as e:
            eliminados['ParametrosPrueba'] = f'Error: {e}'

        return eliminados

    def limpiar_parametros_incorrectos(self, area_id):
        """
        Elimina parametros que no corresponden al area de la prueba

        Args:
            area_id: ID del area a verificar

        Returns:
            Cantidad de relaciones eliminadas
        """
        # Obtener parametros que pertenecen a esta area
        parametros_area = self.db.query(f"""
            SELECT DISTINCT param.ParametroID
            FROM Parametros param
            INNER JOIN ParametrosPrueba pp ON param.ParametroID = pp.ParametroID
            INNER JOIN Pruebas p ON pp.PruebaID = p.PruebaID
            WHERE p.AreaID = {area_id}
        """)

        ids_correctos = [p['ParametroID'] for p in parametros_area]

        if not ids_correctos:
            return 0

        # Eliminar relaciones incorrectas
        try:
            self.db.execute(f"""
                DELETE FROM ParametrosPrueba
                WHERE PruebaID IN (SELECT PruebaID FROM Pruebas WHERE AreaID = {area_id})
                AND ParametroID NOT IN ({','.join(map(str, ids_correctos))})
            """)
            return len(ids_correctos)
        except:
            return 0

    def archivar_datos_antiguos(self, dias=365):
        """
        Archiva datos mas antiguos que el numero de dias especificado

        Args:
            dias: Antiguedad minima para archivar

        Returns:
            Cantidad de registros archivados
        """
        fecha_limite = (datetime.now() - timedelta(days=dias)).strftime('%m/%d/%Y')

        # Crear tablas de archivo si no existen
        tablas_archivo = [
            ("Solicitudes_Archivo", "Solicitudes"),
            ("DetalleSolicitudes_Archivo", "DetalleSolicitudes"),
            ("ResultadosParametros_Archivo", "ResultadosParametros")
        ]

        for tabla_archivo, tabla_origen in tablas_archivo:
            try:
                # Verificar si existe la tabla de archivo
                self.db.query(f"SELECT TOP 1 * FROM {tabla_archivo}")
            except:
                # Crear tabla de archivo
                try:
                    self.db.execute(f"SELECT * INTO {tabla_archivo} FROM {tabla_origen} WHERE 1=0")
                except:
                    pass

        # Archivar solicitudes antiguas
        archivadas = 0
        try:
            solicitudes = self.db.query(f"""
                SELECT SolicitudID FROM Solicitudes
                WHERE FechaSolicitud < #{fecha_limite}#
                AND EstadoSolicitud = 'Entregada'
            """)

            for sol in solicitudes:
                sol_id = sol['SolicitudID']

                # Copiar a archivo
                self.db.execute(f"""
                    INSERT INTO Solicitudes_Archivo
                    SELECT * FROM Solicitudes WHERE SolicitudID = {sol_id}
                """)

                self.db.execute(f"""
                    INSERT INTO DetalleSolicitudes_Archivo
                    SELECT * FROM DetalleSolicitudes WHERE SolicitudID = {sol_id}
                """)

                self.db.execute(f"""
                    INSERT INTO ResultadosParametros_Archivo
                    SELECT r.* FROM ResultadosParametros r
                    INNER JOIN DetalleSolicitudes d ON r.DetalleID = d.DetalleID
                    WHERE d.SolicitudID = {sol_id}
                """)

                # Eliminar de tablas activas
                self.db.execute(f"""
                    DELETE FROM ResultadosParametros WHERE DetalleID IN
                    (SELECT DetalleID FROM DetalleSolicitudes WHERE SolicitudID = {sol_id})
                """)
                self.db.execute(f"DELETE FROM DetalleSolicitudes WHERE SolicitudID = {sol_id}")
                self.db.execute(f"DELETE FROM Solicitudes WHERE SolicitudID = {sol_id}")

                archivadas += 1

        except Exception as e:
            print(f"Error archivando: {e}")

        return archivadas

    # -------------------------------------------------------------------------
    # EXPORTACION E IMPORTACION
    # -------------------------------------------------------------------------

    def exportar_catalogo(self, ruta_archivo):
        """
        Exporta el catalogo de pruebas y parametros a JSON

        Args:
            ruta_archivo: Ruta del archivo de salida

        Returns:
            Cantidad de registros exportados
        """
        catalogo = {
            'areas': [],
            'pruebas': [],
            'parametros': [],
            'relaciones': [],
            'unidades': [],
            'fecha_exportacion': datetime.now().isoformat()
        }

        # Areas
        areas = self.db.query("SELECT * FROM Areas WHERE Activo = True ORDER BY Secuencia")
        catalogo['areas'] = [dict(a) for a in areas]

        # Pruebas
        pruebas = self.db.query("SELECT * FROM Pruebas WHERE Activo = True ORDER BY AreaID, NombrePrueba")
        catalogo['pruebas'] = [dict(p) for p in pruebas]

        # Parametros
        parametros = self.db.query("SELECT * FROM Parametros WHERE Activo = True ORDER BY Seccion, NombreParametro")
        catalogo['parametros'] = [dict(p) for p in parametros]

        # Relaciones
        relaciones = self.db.query("SELECT * FROM ParametrosPrueba ORDER BY PruebaID, Orden")
        catalogo['relaciones'] = [dict(r) for r in relaciones]

        # Unidades
        try:
            unidades = self.db.query("SELECT * FROM Unidades")
            catalogo['unidades'] = [dict(u) for u in unidades]
        except:
            pass

        # Escribir archivo
        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(catalogo, f, indent=2, ensure_ascii=False, default=str)

        total = len(catalogo['areas']) + len(catalogo['pruebas']) + len(catalogo['parametros'])
        return total

    def importar_catalogo(self, ruta_archivo, reemplazar=False):
        """
        Importa catalogo desde archivo JSON

        Args:
            ruta_archivo: Ruta del archivo a importar
            reemplazar: Si True, reemplaza registros existentes

        Returns:
            dict con cantidad de registros importados
        """
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            catalogo = json.load(f)

        importados = {'areas': 0, 'pruebas': 0, 'parametros': 0, 'relaciones': 0}

        # Importar areas
        for area in catalogo.get('areas', []):
            try:
                existente = self.db.query_one(f"SELECT AreaID FROM Areas WHERE CodigoArea = '{area.get('CodigoArea')}'")
                if not existente:
                    self.db.execute(f"""
                        INSERT INTO Areas (CodigoArea, NombreArea, Secuencia, Activo)
                        VALUES ('{area.get('CodigoArea')}', '{area.get('NombreArea')}',
                                {area.get('Secuencia', 0)}, True)
                    """)
                    importados['areas'] += 1
            except:
                pass

        # Importar pruebas
        for prueba in catalogo.get('pruebas', []):
            try:
                existente = self.db.query_one(f"SELECT PruebaID FROM Pruebas WHERE CodigoPrueba = '{prueba.get('CodigoPrueba')}'")
                if not existente:
                    self.db.execute(f"""
                        INSERT INTO Pruebas (CodigoPrueba, NombrePrueba, AreaID, PrecioBase, Activo)
                        VALUES ('{prueba.get('CodigoPrueba')}', '{prueba.get('NombrePrueba')}',
                                {prueba.get('AreaID')}, {prueba.get('PrecioBase', 0)}, True)
                    """)
                    importados['pruebas'] += 1
            except:
                pass

        # Importar parametros
        for param in catalogo.get('parametros', []):
            try:
                cod_safe = str(param.get('CodigoParametro', '')).replace("'", "''")
                existente = self.db.query_one(f"SELECT ParametroID FROM Parametros WHERE CodigoParametro = '{cod_safe}'")
                if not existente:
                    nom_safe = str(param.get('NombreParametro', '')).replace("'", "''")
                    sec_safe = str(param.get('Seccion', '')).replace("'", "''")
                    tipo_safe = str(param.get('TipoDato', 'Texto')).replace("'", "''")
                    unidad_id = param.get('UnidadID', 'Null')
                    valor_ref = str(param.get('ValorRef', '') or '').replace("'", "''")
                    self.db.execute(f"""
                        INSERT INTO Parametros (CodigoParametro, NombreParametro, Seccion, TipoDato,
                                                UnidadID, Observaciones, Activo)
                        VALUES ('{cod_safe}', '{nom_safe}',
                                '{sec_safe}', '{tipo_safe}',
                                {unidad_id}, '{valor_ref}', True)
                    """)
                    importados['parametros'] += 1
            except:
                pass

        return importados

    # -------------------------------------------------------------------------
    # VERIFICACION DE INTEGRIDAD
    # -------------------------------------------------------------------------

    def verificar_integridad(self):
        """
        Verifica la integridad de la base de datos

        Returns:
            Lista de problemas encontrados
        """
        problemas = []

        # 1. Solicitudes sin paciente
        try:
            result = self.db.query_one("""
                SELECT COUNT(*) as Cuenta FROM Solicitudes
                WHERE PacienteID NOT IN (SELECT PacienteID FROM Pacientes)
            """)
            if result and result.get('Cuenta', 0) > 0:
                problemas.append(f"Hay {result['Cuenta']} solicitudes sin paciente valido")
        except Exception as e:
            problemas.append(f"Error verificando solicitudes: {e}")

        # 2. Detalles de solicitud sin solicitud padre
        try:
            result = self.db.query_one("""
                SELECT COUNT(*) as Cuenta FROM DetalleSolicitudes
                WHERE SolicitudID NOT IN (SELECT SolicitudID FROM Solicitudes)
            """)
            if result and result.get('Cuenta', 0) > 0:
                problemas.append(f"Hay {result['Cuenta']} detalles de solicitud huerfanos")
        except Exception as e:
            problemas.append(f"Error verificando detalles de solicitud: {e}")

        # 3. Resultados de parametros sin detalle de solicitud
        try:
            result = self.db.query_one("""
                SELECT COUNT(*) as Cuenta FROM ResultadosParametros
                WHERE DetalleID NOT IN (SELECT DetalleID FROM DetalleSolicitudes)
            """)
            if result and result.get('Cuenta', 0) > 0:
                problemas.append(f"Hay {result['Cuenta']} resultados huerfanos")
        except Exception as e:
            problemas.append(f"Error verificando resultados: {e}")

        # 4. Pruebas sin area
        try:
            result = self.db.query_one("""
                SELECT COUNT(*) as Cuenta FROM Pruebas
                WHERE AreaID NOT IN (SELECT AreaID FROM Areas)
            """)
            if result and result.get('Cuenta', 0) > 0:
                problemas.append(f"Hay {result['Cuenta']} pruebas sin area valida")
        except Exception as e:
            problemas.append(f"Error verificando pruebas: {e}")

        # 5. Parametros mezclados entre areas
        try:
            mezclas = self.db.query("""
                SELECT p.NombrePrueba, a.NombreArea as AreaPrueba,
                       param.NombreParametro, a2.NombreArea as AreaParametro
                FROM Pruebas p
                INNER JOIN Areas a ON p.AreaID = a.AreaID
                INNER JOIN ParametrosPrueba pp ON p.PruebaID = pp.PruebaID
                INNER JOIN Parametros param ON pp.ParametroID = param.ParametroID
                LEFT JOIN (
                    SELECT DISTINCT param2.ParametroID,
                           (SELECT TOP 1 a3.NombreArea
                            FROM ParametrosPrueba pp2
                            INNER JOIN Pruebas p2 ON pp2.PruebaID = p2.PruebaID
                            INNER JOIN Areas a3 ON p2.AreaID = a3.AreaID
                            WHERE pp2.ParametroID = param2.ParametroID) as AreaMasComun
                    FROM Parametros param2
                ) AreaComun ON param.ParametroID = AreaComun.ParametroID
                LEFT JOIN Areas a2 ON AreaComun.AreaMasComun = a2.NombreArea
                WHERE a.NombreArea <> AreaComun.AreaMasComun
                AND AreaComun.AreaMasComun IS NOT NULL
            """)
            if mezclas:
                for m in mezclas[:5]:  # Mostrar solo primeros 5
                    problemas.append(
                        f"Parametro mezclado: {m.get('NombreParametro')} en prueba "
                        f"{m.get('NombrePrueba')} (Area: {m.get('AreaPrueba')}, "
                        f"deberia ser: {m.get('AreaParametro')})"
                    )
                if len(mezclas) > 5:
                    problemas.append(f"... y {len(mezclas) - 5} mas")
        except:
            pass

        # 6. Facturas sin solicitud
        try:
            result = self.db.query_one("""
                SELECT COUNT(*) as Cuenta FROM Facturas
                WHERE SolicitudID IS NOT NULL
                AND SolicitudID NOT IN (SELECT SolicitudID FROM Solicitudes)
            """)
            if result and result.get('Cuenta', 0) > 0:
                problemas.append(f"Hay {result['Cuenta']} facturas con solicitud invalida")
        except Exception as e:
            problemas.append(f"Error verificando facturas: {e}")

        return problemas


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("Modulo de Utilidades de Base de Datos - ANgesLAB")
    print("=" * 50)
    print("\nFunciones disponibles:")
    print("  - crear_backup()")
    print("  - listar_backups()")
    print("  - restaurar_backup(ruta)")
    print("  - crear_indices_recomendados()")
    print("  - analizar_tablas()")
    print("  - limpiar_registros_huerfanos()")
    print("  - verificar_integridad()")
    print("  - exportar_catalogo(ruta)")
    print("  - importar_catalogo(ruta)")

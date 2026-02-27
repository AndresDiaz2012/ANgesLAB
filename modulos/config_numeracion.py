"""
Módulo de Configuración de Numeración de Solicitudes
ANgesLAB - Sistema de Gestión de Laboratorio Clínico

Este módulo maneja la configuración y generación de números de solicitud
con diferentes modos de numeración según las necesidades del laboratorio.

Copyright © 2024-2025 ANgesLAB Solutions
"""

from datetime import datetime, timedelta
from enum import Enum


class TipoNumeracion(Enum):
    """
    Tipos de numeración disponibles para las solicitudes.
    """
    DIARIA = "diaria"           # Se resetea automáticamente cada día
    ANUAL = "anual"             # Se resetea cada año (comportamiento actual)
    CINCO_ANIOS = "cinco_anios" # Continuo por 5 años, reseteable manualmente


class ConfiguradorNumeracion:
    """
    Clase para gestionar la configuración de numeración de solicitudes.
    """

    def __init__(self, db_connection):
        """
        Inicializa el configurador de numeración.

        Args:
            db_connection: Conexión a la base de datos
        """
        self.db = db_connection
        self._inicializar_configuracion()

    def _inicializar_configuracion(self):
        """
        Inicializa la configuración si no existe en la base de datos.
        """
        try:
            config = self.obtener_configuracion()
            if not config:
                # Crear configuración por defecto (modo anual, compatible con sistema actual)
                fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
                self.db.execute(f"""
                    INSERT INTO ConfiguracionNumeracion
                    (TipoNumeracion, UltimoNumero, FechaUltimoReseteo, FormatoNumero, LongitudNumero, FechaCreacion)
                    VALUES ('anual', 0, {fecha_actual}, 'AAAA-NNNNNN', 6, {fecha_actual})
                """)
                print("Configuración de numeración inicializada en modo anual")
        except Exception as e:
            print(f"Error al inicializar configuración: {e}")

    def obtener_configuracion(self):
        """
        Obtiene la configuración actual de numeración.

        Returns:
            dict: Diccionario con la configuración actual
        """
        try:
            result = self.db.query_one("""
                SELECT * FROM ConfiguracionNumeracion
                ORDER BY FechaCreacion DESC
            """)
            return result
        except Exception as e:
            print(f"Error al obtener configuración: {e}")
            return None

    def actualizar_configuracion(self, tipo_numeracion, resetear=False):
        """
        Actualiza el tipo de numeración.

        Args:
            tipo_numeracion (TipoNumeracion): Nuevo tipo de numeración
            resetear (bool): Si se debe resetear el contador al cambiar
        """
        try:
            if resetear:
                ultimo_numero = 0
                fecha_reseteo_str = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            else:
                config = self.obtener_configuracion()
                ultimo_numero = config.get('UltimoNumero', 0) if config else 0
                fecha_reseteo = config.get('FechaUltimoReseteo') if config else datetime.now()

                # Formatear fecha para Access
                if isinstance(fecha_reseteo, datetime):
                    fecha_reseteo_str = fecha_reseteo.strftime('#%m/%d/%Y %H:%M:%S#')
                else:
                    fecha_reseteo_str = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')

            fecha_creacion = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            formato = self._obtener_formato(tipo_numeracion)

            # Eliminar configuración anterior y crear nueva
            self.db.execute("DELETE FROM ConfiguracionNumeracion")
            self.db.execute(f"""
                INSERT INTO ConfiguracionNumeracion
                (TipoNumeracion, UltimoNumero, FechaUltimoReseteo, FormatoNumero, LongitudNumero, FechaCreacion)
                VALUES ('{tipo_numeracion.value}', {ultimo_numero}, {fecha_reseteo_str}, '{formato}', 6, {fecha_creacion})
            """)

            return True
        except Exception as e:
            print(f"Error al actualizar configuración: {e}")
            return False

    def _obtener_formato(self, tipo_numeracion):
        """
        Obtiene el formato de numeración según el tipo.

        Args:
            tipo_numeracion (TipoNumeracion): Tipo de numeración

        Returns:
            str: Formato de numeración
        """
        if tipo_numeracion == TipoNumeracion.DIARIA:
            return 'AAAAMMDD-NNNNNN'
        elif tipo_numeracion == TipoNumeracion.ANUAL:
            return 'AAAA-NNNNNN'
        else:  # CINCO_ANIOS
            return 'NNNNNN'

    def necesita_reseteo_automatico(self):
        """
        Verifica si es necesario hacer un reseteo automático según el tipo de numeración.

        Returns:
            bool: True si necesita reseteo, False en caso contrario
        """
        try:
            config = self.obtener_configuracion()
            if not config:
                return False

            tipo = config.get('TipoNumeracion')
            fecha_ultimo_reseteo = config.get('FechaUltimoReseteo')

            if not fecha_ultimo_reseteo:
                return True

            # Convertir fecha_ultimo_reseteo a datetime sin timezone
            if isinstance(fecha_ultimo_reseteo, str):
                fecha_ultimo_reseteo = datetime.strptime(fecha_ultimo_reseteo, '%Y-%m-%d %H:%M:%S')
            elif hasattr(fecha_ultimo_reseteo, 'replace'):
                # Si la fecha tiene timezone info, quitarla
                fecha_ultimo_reseteo = fecha_ultimo_reseteo.replace(tzinfo=None)

            ahora = datetime.now()

            # Verificar según el tipo de numeración
            if tipo == TipoNumeracion.DIARIA.value:
                # Resetear si es un día diferente
                return fecha_ultimo_reseteo.date() < ahora.date()
            elif tipo == TipoNumeracion.ANUAL.value:
                # Resetear si es un año diferente
                return fecha_ultimo_reseteo.year < ahora.year
            else:  # CINCO_ANIOS
                # Verificar si han pasado 5 años
                fecha_limite = fecha_ultimo_reseteo + timedelta(days=365*5)
                return ahora >= fecha_limite

        except Exception as e:
            print(f"Error al verificar necesidad de reseteo: {e}")
            return False

    def resetear_contador(self, manual=False):
        """
        Resetea el contador de numeración.

        Args:
            manual (bool): Si el reseteo es manual (para modo 5 años)

        Returns:
            bool: True si se reseteo correctamente
        """
        try:
            config = self.obtener_configuracion()
            if not config:
                return False

            tipo = config.get('TipoNumeracion')

            # Para modo 5 años, preguntar confirmación si es automático
            if tipo == TipoNumeracion.CINCO_ANIOS.value and not manual:
                # Este caso se maneja desde la interfaz
                return False

            # Resetear el contador
            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            self.db.execute(f"""
                UPDATE ConfiguracionNumeracion
                SET UltimoNumero = 0,
                    FechaUltimoReseteo = {fecha_actual}
            """)

            return True
        except Exception as e:
            print(f"Error al resetear contador: {e}")
            return False

    def generar_numero_solicitud(self):
        """
        Genera el siguiente número de solicitud según la configuración actual.

        Returns:
            str: Número de solicitud generado
        """
        try:
            # Verificar si necesita reseteo automático
            if self.necesita_reseteo_automatico():
                config = self.obtener_configuracion()
                tipo = config.get('TipoNumeracion')

                # Para modo 5 años, no resetear automáticamente
                if tipo != TipoNumeracion.CINCO_ANIOS.value:
                    self.resetear_contador()

            # Obtener configuración actual
            config = self.obtener_configuracion()
            if not config:
                # Fallback al sistema antiguo
                return self._generar_numero_legado()

            tipo = config.get('TipoNumeracion')
            ultimo_numero = config.get('UltimoNumero', 0)
            longitud = config.get('LongitudNumero', 6)

            # Incrementar el número
            nuevo_numero = ultimo_numero + 1

            # Actualizar en la base de datos
            self.db.execute(f"""
                UPDATE ConfiguracionNumeracion
                SET UltimoNumero = {nuevo_numero}
            """)

            # Formatear según el tipo de numeración
            return self._formatear_numero(tipo, nuevo_numero, longitud)

        except Exception as e:
            print(f"Error al generar número de solicitud: {e}")
            # Fallback al sistema antiguo en caso de error
            return self._generar_numero_legado()

    def _formatear_numero(self, tipo, numero, longitud):
        """
        Formatea el número de solicitud según el tipo de numeración.

        Args:
            tipo (str): Tipo de numeración
            numero (int): Número a formatear
            longitud (int): Longitud del número

        Returns:
            str: Número formateado
        """
        ahora = datetime.now()
        num_str = str(numero).zfill(longitud)

        if tipo == TipoNumeracion.DIARIA.value:
            # Formato: AAAAMMDD-NNNNNN
            fecha_str = ahora.strftime('%Y%m%d')
            return f"{fecha_str}-{num_str}"
        elif tipo == TipoNumeracion.ANUAL.value:
            # Formato: AAAA-NNNNNN
            anio = ahora.strftime('%Y')
            return f"{anio}-{num_str}"
        else:  # CINCO_ANIOS
            # Formato: NNNNNN (solo número)
            return num_str

    def _generar_numero_legado(self):
        """
        Genera número de solicitud usando el sistema legado (anual).
        Método de respaldo en caso de error en el nuevo sistema.

        Returns:
            str: Número en formato AAAA-NNNNNN
        """
        anio = datetime.now().strftime('%Y')

        result = self.db.query_one(f"""
            SELECT MAX(NumeroSolicitud) as Ultimo
            FROM Solicitudes
            WHERE NumeroSolicitud LIKE '{anio}-%'
        """)

        if result and result.get('Ultimo'):
            try:
                partes = str(result['Ultimo']).split('-')
                ultimo_num = int(partes[1]) if len(partes) >= 2 else 0
                nuevo_num = ultimo_num + 1
            except (IndexError, ValueError, TypeError):
                nuevo_num = 1
        else:
            nuevo_num = 1

        return f"{anio}-{nuevo_num:06d}"

    def obtener_estadisticas(self):
        """
        Obtiene estadísticas sobre la numeración actual.

        Returns:
            dict: Estadísticas de numeración
        """
        try:
            config = self.obtener_configuracion()
            if not config:
                return None

            tipo = config.get('TipoNumeracion')
            ultimo_numero = config.get('UltimoNumero', 0)
            fecha_reseteo = config.get('FechaUltimoReseteo')

            # Calcular información adicional
            ahora = datetime.now()

            # Convertir fecha_reseteo a datetime sin timezone
            if isinstance(fecha_reseteo, str):
                fecha_reseteo = datetime.strptime(fecha_reseteo, '%Y-%m-%d %H:%M:%S')
            elif hasattr(fecha_reseteo, 'replace'):
                # Si la fecha tiene timezone info, quitarla
                fecha_reseteo = fecha_reseteo.replace(tzinfo=None)

            dias_desde_reseteo = (ahora - fecha_reseteo).days if fecha_reseteo else 0

            # Para modo 5 años, calcular cuántos días faltan
            dias_hasta_reseteo = None
            if tipo == TipoNumeracion.CINCO_ANIOS.value:
                fecha_limite = fecha_reseteo + timedelta(days=365*5)
                dias_hasta_reseteo = (fecha_limite - ahora).days

            return {
                'tipo': tipo,
                'ultimo_numero': ultimo_numero,
                'fecha_ultimo_reseteo': fecha_reseteo,
                'dias_desde_reseteo': dias_desde_reseteo,
                'dias_hasta_reseteo': dias_hasta_reseteo,
                'proximo_numero': self._formatear_numero(tipo, ultimo_numero + 1, 6)
            }

        except Exception as e:
            print(f"Error al obtener estadísticas: {e}")
            return None

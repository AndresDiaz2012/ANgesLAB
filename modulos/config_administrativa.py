"""
Módulo de Configuración Administrativa
ANgesLAB - Sistema de Gestión de Laboratorio Clínico

Este módulo maneja toda la configuración administrativa del laboratorio.

Copyright © 2024-2026 ANgesLAB Solutions
"""

import logging
from datetime import datetime
import os
import shutil


class ConfiguradorAdministrativo:
    """
    Clase para gestionar la configuración administrativa del laboratorio.
    """

    def __init__(self, db_connection):
        """
        Inicializa el configurador administrativo.

        Args:
            db_connection: Conexión a la base de datos
        """
        self.db = db_connection
        self._inicializar_configuracion()

    # Todas las columnas que el sistema necesita en ConfiguracionLaboratorio
    _COLUMNAS_REQUERIDAS = {
        # Información básica
        'NombreLaboratorio': 'TEXT(200)',
        'RazonSocial': 'TEXT(200)',
        'RIF': 'TEXT(50)',
        'Direccion': 'MEMO',
        'Telefono1': 'TEXT(50)',
        'Telefono2': 'TEXT(50)',
        'WhatsApp': 'TEXT(50)',
        'Email': 'TEXT(100)',
        'SitioWeb': 'TEXT(200)',
        # Logo
        'RutaLogo': 'TEXT(255)',
        'MostrarLogo': 'BIT',
        'FormaLogo': 'TEXT(20)',
        # Impresión
        'FormatoImpresion': 'TEXT(20)',
        'TamanoPapel': 'TEXT(20)',
        'Orientacion': 'TEXT(20)',
        'MargenSuperior': 'DOUBLE',
        'MargenInferior': 'DOUBLE',
        'MargenIzquierdo': 'DOUBLE',
        'MargenDerecho': 'DOUBLE',
        # Resultados
        'MostrarValoresReferencia': 'BIT',
        'MostrarUnidades': 'BIT',
        'MostrarMetodo': 'BIT',
        'ResaltarAnormales': 'BIT',
        'ColorAlto': 'TEXT(10)',
        'ColorBajo': 'TEXT(10)',
        'ColorEncabezadoTabla': 'TEXT(10)',
        'UsarColoresTabla': 'BIT',
        # Financiera
        'MonedaPrincipal': 'TEXT(10)',
        'SimboloMoneda': 'TEXT(5)',
        'DecimalesPrecios': 'INTEGER',
        'IVAPorDefecto': 'DOUBLE',
        'DescuentoMaximo': 'DOUBLE',
        # IGTF / Fiscal SENIAT
        'IGTFActivo': 'BIT',
        'TasaIGTF': 'DOUBLE',
        'TipoContribuyente': 'TEXT(20)',
        # Firma
        'NombreDirector': 'TEXT(200)',
        'TituloDirector': 'TEXT(200)',
        'MostrarFirma': 'BIT',
        'TextoAutorizacion': 'MEMO',
        # Textos
        'HorarioAtencion': 'MEMO',
        'TextoEncabezado': 'MEMO',
        'TextoPiePagina': 'MEMO',
        'NotasResultados': 'MEMO',
        # Auditoría
        'FechaActualizacion': 'DATETIME',
    }

    def _inicializar_configuracion(self):
        """Inicializa la configuración si no existe y asegura que todas las columnas existan."""
        try:
            config = self.obtener_configuracion()
            if not config:
                # Intentar crear un registro inicial
                try:
                    self.db.execute("INSERT INTO ConfiguracionLaboratorio (NombreLaboratorio) VALUES ('Mi Laboratorio')")
                except Exception:
                    pass
                config = self.obtener_configuracion()
                if not config:
                    print("Advertencia: No hay configuración administrativa.")
                    return

            # Verificar y agregar columnas faltantes
            self._asegurar_columnas()
        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al inicializar configuración administrativa: %s", e)

    def _asegurar_columnas(self):
        """Verifica que todas las columnas requeridas existan en la tabla."""
        for col, tipo in self._COLUMNAS_REQUERIDAS.items():
            try:
                self.db.query_one(f"SELECT TOP 1 [{col}] FROM ConfiguracionLaboratorio")
            except Exception:
                # Columna no existe, agregarla
                try:
                    self.db.execute(f"ALTER TABLE ConfiguracionLaboratorio ADD COLUMN [{col}] {tipo}")
                except Exception:
                    pass  # Puede fallar si la columna ya existe con otro nombre

    def obtener_configuracion(self):
        """
        Obtiene la configuración actual del laboratorio.

        Returns:
            dict: Diccionario con la configuración actual
        """
        try:
            result = self.db.query_one("""
                SELECT * FROM ConfiguracionLaboratorio
                ORDER BY ID DESC
            """)
            return result
        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al obtener configuración: %s", e)
            return None

    def actualizar_informacion_basica(self, datos):
        """
        Actualiza la información básica del laboratorio.

        Args:
            datos (dict): Diccionario con los datos a actualizar
        """
        try:
            campos = []
            valores = []

            # Campos de información básica
            campos_permitidos = [
                'NombreLaboratorio', 'RazonSocial', 'RIF',
                'Direccion', 'Telefono1', 'Telefono2',
                'WhatsApp', 'Email', 'SitioWeb'
            ]

            for campo in campos_permitidos:
                if campo in datos:
                    valor = datos[campo]
                    if valor is None or valor == '':
                        campos.append(f"{campo} = NULL")
                    else:
                        # Escapar comillas simples
                        valor_escapado = str(valor).replace("'", "''")
                        campos.append(f"{campo} = '{valor_escapado}'")

            if not campos:
                return False

            # Agregar auditoría
            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha_actual}")

            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar información básica: %s", e)
            return False

    def actualizar_configuracion_impresion(self, datos):
        """
        Actualiza la configuración de impresión.

        Args:
            datos (dict): Diccionario con la configuración de impresión
        """
        try:
            campos = []

            if 'FormatoImpresion' in datos:
                campos.append(f"FormatoImpresion = '{datos['FormatoImpresion']}'")
            if 'TamanoPapel' in datos:
                campos.append(f"TamanoPapel = '{datos['TamanoPapel']}'")
            if 'Orientacion' in datos:
                campos.append(f"Orientacion = '{datos['Orientacion']}'")
            if 'MargenSuperior' in datos:
                campos.append(f"MargenSuperior = {datos['MargenSuperior']}")
            if 'MargenInferior' in datos:
                campos.append(f"MargenInferior = {datos['MargenInferior']}")
            if 'MargenIzquierdo' in datos:
                campos.append(f"MargenIzquierdo = {datos['MargenIzquierdo']}")
            if 'MargenDerecho' in datos:
                campos.append(f"MargenDerecho = {datos['MargenDerecho']}")
            if 'MostrarLogo' in datos:
                campos.append(f"MostrarLogo = {datos['MostrarLogo']}")
            if 'FormaLogo' in datos:
                campos.append(f"FormaLogo = '{datos['FormaLogo']}'")

            if not campos:
                return False

            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha_actual}")

            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar configuración de impresión: %s", e)
            return False

    def actualizar_configuracion_resultados(self, datos):
        """
        Actualiza la configuración de visualización de resultados.

        Args:
            datos (dict): Configuración de resultados
        """
        try:
            campos = []

            campos_bool = [
                'MostrarValoresReferencia', 'MostrarUnidades',
                'MostrarMetodo', 'ResaltarAnormales'
            ]

            for campo in campos_bool:
                if campo in datos:
                    campos.append(f"{campo} = {datos[campo]}")

            if 'ColorAlto' in datos:
                campos.append(f"ColorAlto = '{datos['ColorAlto']}'")
            if 'ColorBajo' in datos:
                campos.append(f"ColorBajo = '{datos['ColorBajo']}'")
            if 'ColorEncabezadoTabla' in datos:
                campos.append(f"ColorEncabezadoTabla = '{datos['ColorEncabezadoTabla']}'")
            if 'UsarColoresTabla' in datos:
                campos.append(f"UsarColoresTabla = {datos['UsarColoresTabla']}")

            if not campos:
                return False

            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha_actual}")

            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar configuración de resultados: %s", e)
            return False

    def actualizar_configuracion_financiera(self, datos):
        """
        Actualiza la configuración financiera.

        Args:
            datos (dict): Configuración financiera
        """
        try:
            campos = []

            if 'MonedaPrincipal' in datos:
                campos.append(f"MonedaPrincipal = '{datos['MonedaPrincipal']}'")
            if 'SimboloMoneda' in datos:
                campos.append(f"SimboloMoneda = '{datos['SimboloMoneda']}'")
            if 'DecimalesPrecios' in datos:
                campos.append(f"DecimalesPrecios = {datos['DecimalesPrecios']}")
            if 'IVAPorDefecto' in datos:
                campos.append(f"IVAPorDefecto = {datos['IVAPorDefecto']}")
            if 'DescuentoMaximo' in datos:
                campos.append(f"DescuentoMaximo = {datos['DescuentoMaximo']}")

            if not campos:
                return False

            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha_actual}")

            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar configuración financiera: %s", e)
            return False

    def actualizar_configuracion_fiscal(self, datos):
        """
        Actualiza la configuracion fiscal (IGTF, tipo contribuyente).

        Args:
            datos (dict): Configuracion fiscal
        """
        try:
            campos = []

            if 'IGTFActivo' in datos:
                campos.append(f"IGTFActivo = {datos['IGTFActivo']}")
            if 'TasaIGTF' in datos:
                campos.append(f"TasaIGTF = {datos['TasaIGTF']}")
            if 'TipoContribuyente' in datos:
                tipo = str(datos['TipoContribuyente']).replace("'", "''")
                campos.append(f"TipoContribuyente = '{tipo}'")

            if not campos:
                return False

            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha_actual}")

            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar configuracion fiscal: %s", e)
            return False

    def actualizar_configuracion_tasas(self, datos):
        """
        Actualiza configuracion de tasas de cambio en ConfiguracionAdministrativa.

        Args:
            datos (dict): TasaCOP_USD, TasaCambio, etc.
        """
        try:
            campos = []

            if 'TasaCOP_USD' in datos:
                campos.append(f"TasaCOP_USD = {datos['TasaCOP_USD']}")
            if 'TasaCambio' in datos:
                campos.append(f"TasaCambio = {datos['TasaCambio']}")

            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha}")

            if not campos:
                return False

            sql = f"""
                UPDATE ConfiguracionAdministrativa
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar tasas: %s", e)
            return False

    def actualizar_firma_autorizacion(self, datos):
        """
        Actualiza información de firma y autorización.

        Args:
            datos (dict): Datos de firma
        """
        try:
            campos = []

            if 'NombreDirector' in datos:
                nombre = datos['NombreDirector'].replace("'", "''")
                campos.append(f"NombreDirector = '{nombre}'")
            if 'TituloDirector' in datos:
                titulo = datos['TituloDirector'].replace("'", "''")
                campos.append(f"TituloDirector = '{titulo}'")
            if 'MostrarFirma' in datos:
                campos.append(f"MostrarFirma = {datos['MostrarFirma']}")
            if 'TextoAutorizacion' in datos:
                texto = datos['TextoAutorizacion'].replace("'", "''")
                campos.append(f"TextoAutorizacion = '{texto}'")

            if not campos:
                return False

            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha_actual}")

            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar firma: %s", e)
            return False

    def guardar_logo(self, ruta_origen):
        """
        Guarda el logo del laboratorio.

        Args:
            ruta_origen (str): Ruta del archivo de logo a guardar

        Returns:
            str: Ruta donde se guardó el logo, o None si hubo error
        """
        try:
            # Crear directorio de logos si no existe
            dir_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            dir_logos = os.path.join(dir_base, "logos")

            if not os.path.exists(dir_logos):
                os.makedirs(dir_logos)

            # Obtener extensión del archivo
            _, extension = os.path.splitext(ruta_origen)

            # Nombre del archivo de destino
            nombre_destino = f"logo_laboratorio{extension}"
            ruta_destino = os.path.join(dir_logos, nombre_destino)

            # Copiar el archivo
            shutil.copy2(ruta_origen, ruta_destino)

            # Actualizar en la base de datos
            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET RutaLogo = '{ruta_destino.replace("'", "''")}',
                    FechaActualizacion = {fecha_actual}
            """

            self.db.execute(sql)

            return ruta_destino

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al guardar logo: %s", e)
            return None

    def obtener_ruta_logo(self):
        """
        Obtiene la ruta del logo del laboratorio.

        Returns:
            str: Ruta del logo, o None si no existe
        """
        try:
            config = self.obtener_configuracion()
            if config and config.get('RutaLogo'):
                ruta = config['RutaLogo']
                if os.path.exists(ruta):
                    return ruta
            return None
        except Exception:
            return None

    def actualizar_textos_personalizados(self, datos):
        """
        Actualiza textos personalizados.

        Args:
            datos (dict): Textos personalizados
        """
        try:
            campos = []

            if 'TextoEncabezado' in datos:
                texto = datos['TextoEncabezado'].replace("'", "''")
                campos.append(f"TextoEncabezado = '{texto}'")
            if 'TextoPiePagina' in datos:
                texto = datos['TextoPiePagina'].replace("'", "''")
                campos.append(f"TextoPiePagina = '{texto}'")
            if 'NotasResultados' in datos:
                texto = datos['NotasResultados'].replace("'", "''")
                campos.append(f"NotasResultados = '{texto}'")
            if 'HorarioAtencion' in datos:
                texto = datos['HorarioAtencion'].replace("'", "''")
                campos.append(f"HorarioAtencion = '{texto}'")

            if not campos:
                return False

            fecha_actual = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            campos.append(f"FechaActualizacion = {fecha_actual}")

            sql = f"""
                UPDATE ConfiguracionLaboratorio
                SET {', '.join(campos)}
            """

            self.db.execute(sql)
            return True

        except Exception as e:
            logging.getLogger("angeslab.config_administrativa").warning("Error al actualizar textos: %s", e)
            return False

    def obtener_formato_precio(self):
        """
        Obtiene el formato para mostrar precios según la configuración.

        Returns:
            tuple: (símbolo_moneda, decimales)
        """
        try:
            config = self.obtener_configuracion()
            if config:
                simbolo = config.get('SimboloMoneda', '$')
                decimales = config.get('DecimalesPrecios', 2)
                return (simbolo, decimales)
            return ('$', 2)
        except Exception:
            return ('$', 2)

    def formatear_precio(self, monto):
        """
        Formatea un precio según la configuración.

        Args:
            monto (float): Monto a formatear

        Returns:
            str: Precio formateado
        """
        simbolo, decimales = self.obtener_formato_precio()
        return f"{simbolo}{monto:,.{decimales}f}"

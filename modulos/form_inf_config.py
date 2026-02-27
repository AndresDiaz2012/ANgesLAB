"""
================================================================================
MODULO DE CONFIGURACION DE FORMULARIOS (Form_Inf) - ANgesLAB
================================================================================
Gestiona las configuraciones de impresion y presentacion de reportes.
Cada Form_Inf define como se presenta la informacion en un reporte especifico.

Funcionalidades:
- Crear y editar configuraciones de formularios
- Definir plantillas HTML personalizadas
- Configurar margenes, orientacion y tamano de papel
- Asociar formularios a areas clinicas
- Exportar e importar configuraciones

Autor: Sistema ANgesLAB
================================================================================
"""

from datetime import datetime
import json
import os

# ============================================================================
# CONFIGURACIONES POR DEFECTO
# ============================================================================

CONFIGURACIONES_DEFECTO = {
    'Form_Inf_Comprobante': {
        'codigo': 'Form_Inf_Comprobante',
        'nombre': 'Comprobante de Solicitud',
        'tipo_reporte': 'Recepcion',
        'area_id': None,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'margen_superior': 1.0,
        'margen_inferior': 1.0,
        'margen_izquierdo': 1.5,
        'margen_derecho': 1.5,
        'incluir_logo': True,
        'incluir_codigo_barras': True,
        'mostrar_precios': True,
        'secciones': ['encabezado', 'paciente', 'pruebas', 'totales', 'instrucciones']
    },
    'Form_Inf_Boleta': {
        'codigo': 'Form_Inf_Boleta',
        'nombre': 'Boleta de Muestra',
        'tipo_reporte': 'Etiqueta',
        'area_id': None,
        'tamano_papel': 'Personalizado',
        'ancho_personalizado': 10,
        'alto_personalizado': 5,
        'orientacion': 'Horizontal',
        'margen_superior': 0.3,
        'margen_inferior': 0.3,
        'margen_izquierdo': 0.3,
        'margen_derecho': 0.3,
        'incluir_codigo_barras': True,
        'secciones': ['codigo', 'paciente', 'fecha', 'areas']
    },
    'Form_Inf_Hematologia': {
        'codigo': 'Form_Inf_Hematologia',
        'nombre': 'Resultado de Hematologia',
        'tipo_reporte': 'Resultado',
        'area_id': 1,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'margen_superior': 1.0,
        'margen_inferior': 1.5,
        'margen_izquierdo': 1.5,
        'margen_derecho': 1.5,
        'incluir_logo': True,
        'incluir_firma': True,
        'secciones': ['encabezado', 'paciente', 'serie_roja', 'serie_blanca', 'plaquetas', 'observaciones', 'firma'],
        'mostrar_referencia': True,
        'resaltar_anormales': True,
        'color_alto': '#FF0000',
        'color_bajo': '#0000FF'
    },
    'Form_Inf_PerfilLipidico': {
        'codigo': 'Form_Inf_PerfilLipidico',
        'nombre': 'Perfil Lipidico',
        'tipo_reporte': 'Resultado',
        'area_id': 2,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'margen_superior': 1.0,
        'margen_inferior': 1.5,
        'margen_izquierdo': 1.5,
        'margen_derecho': 1.5,
        'incluir_logo': True,
        'incluir_firma': True,
        'secciones': ['encabezado', 'paciente', 'resultados', 'interpretacion', 'grafico_riesgo', 'firma'],
        'mostrar_referencia': True,
        'incluir_grafico': True,
        'resaltar_anormales': True
    },
    'Form_Inf_Renal': {
        'codigo': 'Form_Inf_Renal',
        'nombre': 'Perfil Renal',
        'tipo_reporte': 'Resultado',
        'area_id': 2,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'secciones': ['encabezado', 'paciente', 'resultados', 'observaciones', 'firma'],
        'mostrar_referencia': True,
        'incluir_firma': True
    },
    'Form_Inf_Hepatico': {
        'codigo': 'Form_Inf_Hepatico',
        'nombre': 'Perfil Hepatico',
        'tipo_reporte': 'Resultado',
        'area_id': 2,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'secciones': ['encabezado', 'paciente', 'enzimas', 'bilirrubinas', 'observaciones', 'firma'],
        'mostrar_referencia': True,
        'incluir_firma': True
    },
    'Form_Inf_Orina': {
        'codigo': 'Form_Inf_Orina',
        'nombre': 'Examen de Orina',
        'tipo_reporte': 'Resultado',
        'area_id': 6,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'secciones': ['encabezado', 'paciente', 'fisico', 'quimico', 'sedimento', 'observaciones', 'firma'],
        'mostrar_referencia': True,
        'incluir_firma': True,
        'formato_sedimento': 'tabla'
    },
    'Form_Inf_Heces': {
        'codigo': 'Form_Inf_Heces',
        'nombre': 'Examen de Heces (Coproanalisis)',
        'tipo_reporte': 'Resultado',
        'area_id': 7,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'secciones': ['encabezado', 'paciente', 'macroscopico', 'quimico', 'microscopico', 'parasitologia', 'observaciones', 'firma'],
        'mostrar_referencia': True,
        'incluir_firma': True
    },
    'Form_Inf_Tiroides': {
        'codigo': 'Form_Inf_Tiroides',
        'nombre': 'Perfil Tiroideo',
        'tipo_reporte': 'Resultado',
        'area_id': 8,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'secciones': ['encabezado', 'paciente', 'resultados', 'interpretacion', 'firma'],
        'mostrar_referencia': True,
        'incluir_interpretacion': True,
        'incluir_firma': True
    },
    'Form_Inf_Serologia': {
        'codigo': 'Form_Inf_Serologia',
        'nombre': 'Resultado de Serologia',
        'tipo_reporte': 'Resultado',
        'area_id': 9,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'margen_superior': 1.0,
        'margen_inferior': 1.5,
        'margen_izquierdo': 1.5,
        'margen_derecho': 1.5,
        'incluir_logo': True,
        'incluir_firma': True,
        'secciones': ['encabezado', 'paciente', 'antigenos_febriles', 'otros_serologicos', 'observaciones', 'firma'],
        'mostrar_referencia': True,
        'resaltar_anormales': True
    },
    'Form_Inf_AntigenosFebriles': {
        'codigo': 'Form_Inf_AntigenosFebriles',
        'nombre': 'Antigenos Febriles',
        'tipo_reporte': 'Resultado',
        'area_id': 9,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'margen_superior': 1.0,
        'margen_inferior': 1.5,
        'margen_izquierdo': 1.5,
        'margen_derecho': 1.5,
        'incluir_logo': True,
        'incluir_firma': True,
        'secciones': [
            'encabezado', 'paciente', 'metodo',
            'salmonella_typhi', 'salmonella_paratyphi',
            'brucella', 'proteus',
            'observaciones', 'interpretacion', 'firma'
        ],
        'mostrar_referencia': True,
        'resaltar_anormales': True,
        'formato_titulacion': 'tabla'
    },
    'Form_Inf_Microbiologia': {
        'codigo': 'Form_Inf_Microbiologia',
        'nombre': 'Resultado de Microbiologia / Bacteriologia',
        'tipo_reporte': 'Resultado',
        'area_id': 10,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'margen_superior': 1.0,
        'margen_inferior': 1.5,
        'margen_izquierdo': 1.5,
        'margen_derecho': 1.5,
        'incluir_logo': True,
        'incluir_firma': True,
        'secciones': [
            'encabezado', 'paciente', 'datos_muestra', 'tipo_muestra',
            'coloracion_gram', 'coloracion_acido_resistente', 'examen_directo',
            'cultivo', 'identificacion_germen', 'recuento_colonias',
            'antibiograma', 'observaciones', 'firma'
        ],
        'mostrar_referencia': True,
        'resaltar_anormales': True,
        'formato_antibiograma': 'tabla'
    },
    'Form_Inf_Factura': {
        'codigo': 'Form_Inf_Factura',
        'nombre': 'Factura Fiscal',
        'tipo_reporte': 'Factura',
        'area_id': None,
        'tamano_papel': 'Carta',
        'orientacion': 'Vertical',
        'margen_superior': 1.0,
        'margen_inferior': 1.0,
        'margen_izquierdo': 1.0,
        'margen_derecho': 1.0,
        'incluir_logo': True,
        'formato_fiscal': 'Venezuela',
        'incluir_control': True,
        'secciones': ['encabezado_fiscal', 'cliente', 'detalle', 'totales', 'pie_fiscal']
    },
    'Form_Inf_Recibo': {
        'codigo': 'Form_Inf_Recibo',
        'nombre': 'Recibo de Caja',
        'tipo_reporte': 'Recibo',
        'area_id': None,
        'tamano_papel': 'Media_Carta',
        'orientacion': 'Vertical',
        'incluir_logo': True,
        'monto_en_letras': True,
        'secciones': ['encabezado', 'receptor', 'monto', 'concepto', 'firma_cajero']
    },
    'Form_Inf_LibroVentas': {
        'codigo': 'Form_Inf_LibroVentas',
        'nombre': 'Libro de Ventas',
        'tipo_reporte': 'Fiscal',
        'area_id': None,
        'tamano_papel': 'Oficio',
        'orientacion': 'Horizontal',
        'secciones': ['encabezado_periodo', 'tabla_facturas', 'totales', 'resumen_iva']
    }
}


# ============================================================================
# CLASE PRINCIPAL
# ============================================================================

class FormInfConfig:
    """
    Gestiona las configuraciones de formularios de impresion
    """

    def __init__(self, db):
        self.db = db
        self._inicializar_tabla()

    def _inicializar_tabla(self):
        """Crea la tabla de configuraciones si no existe"""
        try:
            # Verificar si existe la tabla
            self.db.query("SELECT TOP 1 * FROM FormulariosReporte")
        except:
            # Crear tabla si no existe
            try:
                self.db.execute("""
                    CREATE TABLE FormulariosReporte (
                        FormularioID AUTOINCREMENT PRIMARY KEY,
                        Codigo TEXT(50) UNIQUE,
                        Nombre TEXT(100),
                        TipoReporte TEXT(50),
                        AreaID INTEGER,
                        TamanoPapel TEXT(20),
                        Orientacion TEXT(20),
                        MargenSuperior DOUBLE,
                        MargenInferior DOUBLE,
                        MargenIzquierdo DOUBLE,
                        MargenDerecho DOUBLE,
                        ConfiguracionJSON MEMO,
                        PlantillaHTML MEMO,
                        Activo BIT DEFAULT True,
                        FechaCreacion DATETIME,
                        FechaModificacion DATETIME
                    )
                """)
            except:
                pass  # Tabla ya existe o error de permisos

    # -------------------------------------------------------------------------
    # CRUD DE CONFIGURACIONES
    # -------------------------------------------------------------------------

    def obtener_configuracion(self, codigo):
        """
        Obtiene la configuracion de un formulario por codigo

        Args:
            codigo: Codigo del formulario (ej: 'Form_Inf_Hematologia')

        Returns:
            dict con la configuracion o None si no existe
        """
        try:
            result = self.db.query_one(f"""
                SELECT * FROM FormulariosReporte WHERE Codigo = '{codigo}'
            """)

            if result:
                config = dict(result)
                # Parsear JSON de configuracion
                if config.get('ConfiguracionJSON'):
                    try:
                        config['configuracion'] = json.loads(config['ConfiguracionJSON'])
                    except:
                        config['configuracion'] = {}
                return config
        except:
            pass

        # Retornar configuracion por defecto si existe
        return CONFIGURACIONES_DEFECTO.get(codigo)

    def guardar_configuracion(self, codigo, config):
        """
        Guarda o actualiza una configuracion de formulario

        Args:
            codigo: Codigo del formulario
            config: dict con la configuracion
        """
        config_json = json.dumps(config.get('configuracion', config))
        plantilla = config.get('plantilla_html', '')
        nombre = config.get('nombre', codigo)
        tipo = config.get('tipo_reporte', 'Resultado')
        area_id = config.get('area_id')
        tamano = config.get('tamano_papel', 'Carta')
        orientacion = config.get('orientacion', 'Vertical')
        m_sup = config.get('margen_superior', 1.0)
        m_inf = config.get('margen_inferior', 1.0)
        m_izq = config.get('margen_izquierdo', 1.5)
        m_der = config.get('margen_derecho', 1.5)

        try:
            # Verificar si existe
            existente = self.db.query_one(f"SELECT FormularioID FROM FormulariosReporte WHERE Codigo = '{codigo}'")

            if existente:
                # Actualizar
                self.db.execute(f"""
                    UPDATE FormulariosReporte SET
                        Nombre = '{nombre}',
                        TipoReporte = '{tipo}',
                        AreaID = {area_id if area_id else 'NULL'},
                        TamanoPapel = '{tamano}',
                        Orientacion = '{orientacion}',
                        MargenSuperior = {m_sup},
                        MargenInferior = {m_inf},
                        MargenIzquierdo = {m_izq},
                        MargenDerecho = {m_der},
                        ConfiguracionJSON = '{config_json.replace("'", "''")}',
                        PlantillaHTML = '{plantilla.replace("'", "''")}',
                        FechaModificacion = Now()
                    WHERE Codigo = '{codigo}'
                """)
            else:
                # Insertar
                self.db.execute(f"""
                    INSERT INTO FormulariosReporte
                    (Codigo, Nombre, TipoReporte, AreaID, TamanoPapel, Orientacion,
                     MargenSuperior, MargenInferior, MargenIzquierdo, MargenDerecho,
                     ConfiguracionJSON, PlantillaHTML, Activo, FechaCreacion)
                    VALUES
                    ('{codigo}', '{nombre}', '{tipo}', {area_id if area_id else 'NULL'},
                     '{tamano}', '{orientacion}', {m_sup}, {m_inf}, {m_izq}, {m_der},
                     '{config_json.replace("'", "''")}', '{plantilla.replace("'", "''")}',
                     True, Now())
                """)

            return True
        except Exception as e:
            print(f"Error guardando configuracion: {e}")
            return False

    def listar_formularios(self, tipo_reporte=None, area_id=None):
        """
        Lista todos los formularios disponibles

        Args:
            tipo_reporte: Filtrar por tipo (Resultado, Factura, etc.)
            area_id: Filtrar por area clinica

        Returns:
            Lista de formularios
        """
        where = "WHERE Activo = True"
        if tipo_reporte:
            where += f" AND TipoReporte = '{tipo_reporte}'"
        if area_id:
            where += f" AND (AreaID = {area_id} OR AreaID IS NULL)"

        try:
            formularios = self.db.query(f"""
                SELECT FormularioID, Codigo, Nombre, TipoReporte, AreaID
                FROM FormulariosReporte
                {where}
                ORDER BY TipoReporte, Nombre
            """)
            return formularios
        except:
            # Retornar lista de configuraciones por defecto
            resultado = []
            for codigo, config in CONFIGURACIONES_DEFECTO.items():
                if tipo_reporte and config.get('tipo_reporte') != tipo_reporte:
                    continue
                if area_id and config.get('area_id') != area_id and config.get('area_id') is not None:
                    continue
                resultado.append({
                    'Codigo': codigo,
                    'Nombre': config.get('nombre', codigo),
                    'TipoReporte': config.get('tipo_reporte', 'Resultado'),
                    'AreaID': config.get('area_id')
                })
            return resultado

    def eliminar_configuracion(self, codigo):
        """Elimina (desactiva) una configuracion"""
        try:
            self.db.execute(f"""
                UPDATE FormulariosReporte SET Activo = False WHERE Codigo = '{codigo}'
            """)
            return True
        except:
            return False

    # -------------------------------------------------------------------------
    # OBTENCION DE PLANTILLAS
    # -------------------------------------------------------------------------

    def obtener_plantilla(self, area_id):
        """
        Obtiene la plantilla por defecto para un area

        Args:
            area_id: ID del area clinica

        Returns:
            Configuracion del formulario para esa area
        """
        # Mapeo de areas a formularios
        mapeo_areas = {
            1: 'Form_Inf_Hematologia',
            2: 'Form_Inf_PerfilLipidico',  # Quimica tiene varios, usar lipidos por defecto
            5: 'Form_Inf_Coagulacion',
            6: 'Form_Inf_Orina',
            7: 'Form_Inf_Heces',
            8: 'Form_Inf_Tiroides',
            9: 'Form_Inf_Serologia',
            10: 'Form_Inf_Microbiologia'
        }

        codigo = mapeo_areas.get(area_id, 'Form_Inf_Resultado')
        return self.obtener_configuracion(codigo)

    def obtener_plantilla_por_prueba(self, prueba_id):
        """
        Obtiene la plantilla apropiada para una prueba especifica

        Args:
            prueba_id: ID de la prueba

        Returns:
            Configuracion del formulario
        """
        # Obtener area de la prueba
        prueba = self.db.query_one(f"""
            SELECT AreaID, CodigoPrueba FROM Pruebas WHERE PruebaID = {prueba_id}
        """)

        if prueba:
            # Buscar plantilla especifica para la prueba
            especifica = self.db.query_one(f"""
                SELECT * FROM FormulariosReporte
                WHERE ConfiguracionJSON LIKE '%{prueba.get('CodigoPrueba', '')}%'
                AND Activo = True
            """)

            if especifica:
                return especifica

            # Usar plantilla del area
            return self.obtener_plantilla(prueba.get('AreaID'))

        return self.obtener_configuracion('Form_Inf_Resultado')

    # -------------------------------------------------------------------------
    # CONFIGURACION DE IMPRESION
    # -------------------------------------------------------------------------

    def obtener_config_impresion(self, codigo):
        """
        Obtiene la configuracion de impresion de un formulario

        Returns:
            dict con configuracion de impresion
        """
        config = self.obtener_configuracion(codigo)
        if not config:
            return {
                'tamano_papel': 'Carta',
                'orientacion': 'Vertical',
                'margenes': {'superior': 1.0, 'inferior': 1.0, 'izquierdo': 1.5, 'derecho': 1.5}
            }

        return {
            'tamano_papel': config.get('tamano_papel', config.get('TamanoPapel', 'Carta')),
            'orientacion': config.get('orientacion', config.get('Orientacion', 'Vertical')),
            'margenes': {
                'superior': config.get('margen_superior', config.get('MargenSuperior', 1.0)),
                'inferior': config.get('margen_inferior', config.get('MargenInferior', 1.0)),
                'izquierdo': config.get('margen_izquierdo', config.get('MargenIzquierdo', 1.5)),
                'derecho': config.get('margen_derecho', config.get('MargenDerecho', 1.5))
            },
            'ancho_personalizado': config.get('ancho_personalizado'),
            'alto_personalizado': config.get('alto_personalizado')
        }

    # -------------------------------------------------------------------------
    # INICIALIZACION DE FORMULARIOS POR DEFECTO
    # -------------------------------------------------------------------------

    def inicializar_formularios_defecto(self):
        """
        Carga los formularios por defecto en la base de datos
        """
        print("Inicializando formularios por defecto...")

        for codigo, config in CONFIGURACIONES_DEFECTO.items():
            existente = self.obtener_configuracion(codigo)
            if not existente or existente == config:  # Es el default, no de BD
                self.guardar_configuracion(codigo, config)
                print(f"  - {codigo}: OK")

        print("Formularios inicializados.")

    # -------------------------------------------------------------------------
    # EXPORTACION E IMPORTACION
    # -------------------------------------------------------------------------

    def exportar_configuraciones(self, ruta_archivo):
        """
        Exporta todas las configuraciones a un archivo JSON
        """
        formularios = self.listar_formularios()
        configs = []

        for form in formularios:
            config = self.obtener_configuracion(form.get('Codigo'))
            if config:
                configs.append(config)

        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            json.dump(configs, f, indent=2, ensure_ascii=False, default=str)

        return len(configs)

    def importar_configuraciones(self, ruta_archivo):
        """
        Importa configuraciones desde un archivo JSON
        """
        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            configs = json.load(f)

        importados = 0
        for config in configs:
            codigo = config.get('Codigo') or config.get('codigo')
            if codigo:
                self.guardar_configuracion(codigo, config)
                importados += 1

        return importados


# ============================================================================
# UTILIDADES PARA GENERACION DE HTML
# ============================================================================

class GeneradorHTML:
    """Utilidades para generar HTML de reportes"""

    @staticmethod
    def aplicar_plantilla(plantilla_html, datos):
        """
        Aplica datos a una plantilla HTML con marcadores {{variable}}

        Args:
            plantilla_html: HTML con marcadores
            datos: dict con los valores

        Returns:
            HTML con valores reemplazados
        """
        resultado = plantilla_html

        for clave, valor in datos.items():
            marcador = '{{' + clave + '}}'
            resultado = resultado.replace(marcador, str(valor) if valor else '')

        return resultado

    @staticmethod
    def generar_tabla(datos, columnas, clases=''):
        """
        Genera una tabla HTML

        Args:
            datos: lista de diccionarios
            columnas: lista de tuplas (campo, titulo, alineacion)
            clases: clases CSS adicionales

        Returns:
            HTML de la tabla
        """
        html = f'<table class="{clases}">\n<thead>\n<tr>'

        for campo, titulo, alineacion in columnas:
            html += f'<th style="text-align:{alineacion};">{titulo}</th>'

        html += '</tr>\n</thead>\n<tbody>\n'

        for fila in datos:
            html += '<tr>'
            for campo, titulo, alineacion in columnas:
                valor = fila.get(campo, '')
                html += f'<td style="text-align:{alineacion};">{valor}</td>'
            html += '</tr>\n'

        html += '</tbody>\n</table>'
        return html

    @staticmethod
    def generar_seccion(titulo, contenido):
        """Genera una seccion con titulo"""
        return f'''
        <div class="section-title">{titulo}</div>
        <div class="section-content">
            {contenido}
        </div>
        '''


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("Modulo de Configuracion de Formularios - ANgesLAB")
    print("=" * 50)
    print("\nFormularios disponibles por defecto:")

    for codigo, config in CONFIGURACIONES_DEFECTO.items():
        print(f"  {codigo}")
        print(f"    - Tipo: {config.get('tipo_reporte')}")
        print(f"    - Area: {config.get('area_id', 'General')}")
        print(f"    - Secciones: {', '.join(config.get('secciones', []))}")
        print()

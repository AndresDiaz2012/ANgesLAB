# 02 - Arquitectura del Sistema

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 2.1 Vista general

ANgesLAB es una aplicacion de escritorio monolitica construida con Python y Tkinter, siguiendo un patron de arquitectura **MVC simplificado** donde:

- **Modelo**: Capa de acceso a datos via ADODB COM sobre Microsoft Access
- **Vista**: Interfaz grafica Tkinter con navegacion por sidebar y pestanas
- **Controlador**: Logica de negocio encapsulada en modulos Python especializados

```
+------------------------------------------------------------------+
|                        ANgesLAB.pyw                               |
|                    (Controlador principal)                         |
|  +-------------------+  +------------------+  +-----------------+ |
|  |   LoginWindow     |  | MainApplication  |  |    Database     | |
|  | (Autenticacion)   |  | (Orquestador UI) |  |  (ADODB/COM)   | |
|  +-------------------+  +------------------+  +-----------------+ |
+------------------------------------------------------------------+
           |                       |                      |
           v                       v                      v
+------------------------------------------------------------------+
|                         modulos/                                  |
|  +---------------------+  +-------------------+  +-------------+ |
|  | Clinicos            |  | Administrativos   |  | Soporte     | |
|  | - historial_clinico |  | - facturacion     |  | - auditoria | |
|  | - ia_interpretacion |  | - inventario      |  | - seguridad | |
|  | - calculos_auto     |  | - equipos         |  | - logging   | |
|  | - valores_ref       |  | - cotizaciones    |  | - utilidades| |
|  | - graficas          |  | - config_admin    |  | - formato   | |
|  | - gtt_captura/rep   |  | - tasas_cambio    |  | - splash    | |
|  | - veterinario       |  | - ventana_admin   |  | - etiquetas | |
|  +---------------------+  +-------------------+  +-------------+ |
+------------------------------------------------------------------+
           |                       |                      |
           v                       v                      v
+------------------------------------------------------------------+
|                     ANgesLAB.accdb                                |
|               (Microsoft Access Database)                         |
|            50+ tablas | ADODB/OLEDB 12.0                         |
+------------------------------------------------------------------+
```

## 2.2 Stack tecnologico

| Capa               | Tecnologia                          | Version      |
|---------------------|-------------------------------------|-------------|
| Lenguaje            | Python                              | >= 3.8      |
| GUI Framework       | Tkinter (tk/ttk)                    | Built-in    |
| Base de datos       | Microsoft Access (.accdb)           | 2016+       |
| Driver BD           | ADODB via win32com.client (COM)     | pywin32 306 |
| PDF                 | ReportLab                           | >= 4.0      |
| Imagenes            | Pillow (PIL)                        | >= 10.0     |
| Graficas            | Matplotlib + FigureCanvasTkAgg      | >= 3.8      |
| Calculos            | NumPy                               | >= 1.26     |
| QR                  | qrcode[pil]                         | >= 7.4      |
| HTTP                | requests                            | >= 2.31     |
| Tasas de cambio     | pyBCV                               | >= 0.2      |
| IA Cloud            | anthropic SDK / openai SDK          | Opcional    |
| IA Local            | Ollama (HTTP localhost:11434)        | Opcional    |
| Instalador          | Inno Setup                          | 6.x         |
| Control de versiones| Git                                 | 2.x         |

## 2.3 Estructura de archivos

```
ANgesLab/
|-- ANgesLAB.pyw                  # Aplicacion principal (~17,000 lineas)
|-- ANgesLAB.accdb                # Base de datos
|-- ANgesLAB.vbs                  # Lanzador Windows (oculta consola)
|-- VERSION                       # Archivo de version (2.0.0)
|-- requirements.txt              # Dependencias Python
|-- db_config.json                # Ruta de BD (soporte LAN)
|-- backup_config.json            # Configuracion de backups automaticos
|-- config_ia.json                # Configuracion de proveedores IA
|-- LICENSE                       # Licencia del software
|
|-- modulos/                      # 36 modulos Python
|   |-- __init__.py
|   |-- auditoria.py              # Middleware de auditoria activa
|   |-- calculos_automaticos.py   # Motor de calculos clinicos (50+)
|   |-- config_administrativa.py  # Gestor de configuracion administrativa
|   |-- config_numeracion.py      # Secuencias de numeracion de documentos
|   |-- cotizaciones.py           # Gestion de cotizaciones
|   |-- envio_resultados.py       # Entrega por email/WhatsApp/impresion
|   |-- equipos.py                # Gestion de equipos de laboratorio
|   |-- etiquetas.py              # Generacion de etiquetas de muestras
|   |-- facturacion_fiscal.py     # Facturacion conforme SENIAT
|   |-- flujo_trabajo.py          # Maquina de estados de solicitudes
|   |-- form_inf_config.py        # Configuracion de formularios de reporte
|   |-- formato_pdf.py            # Calculador de layout PDF + QR
|   |-- gestor_solicitudes.py     # CRUD de solicitudes con permisos
|   |-- graficas_historial.py     # Graficas matplotlib de evolucion
|   |-- gtt_captura.py            # Formulario GTT (tolerancia glucosa)
|   |-- gtt_reporte.py            # Reporte PDF de curva GTT
|   |-- historial_clinico.py      # Historial clinico y tendencias
|   |-- hojas_trabajo.py          # Hojas de trabajo por area
|   |-- ia_interpretacion.py      # Motor IA: reglas + Ollama + Cloud
|   |-- inventario.py             # Gestion de inventario y lotes
|   |-- logging_config.py         # Configuracion centralizada de logs
|   |-- modulo_administrativo.py  # Funciones administrativas
|   |-- plantillas_reportes.py    # 25+ plantillas de reportes PDF
|   |-- reportes_especificaciones.py # Reportes por especificacion de area
|   |-- reportes_resultados.py    # Generacion de reportes de resultados
|   |-- seguridad_db.py           # Seguridad BD, hashing, intentos login
|   |-- splash_screen.py          # Pantalla de carga inicial
|   |-- tasas_cambio.py           # Gestor de tasas de cambio BCV
|   |-- utilidades_db.py          # Utilidades BD: backup, restauracion, indices
|   |-- valores_referencia.py     # Valores de referencia edad/sexo
|   |-- ventana_administrativa.py # Interfaz administrativa (20+ tablas)
|   |-- ventana_config_administrativa.py
|   |-- ventana_config_numeracion.py
|   |-- ventana_configuracion_completa.py
|   +-- veterinario.py            # Modulo veterinario completo
|
|-- assets/                       # Recursos graficos UI
|   |-- angeslab_icon.ico         # Icono Windows
|   |-- angeslab_icon_256.png     # Icono login
|   |-- angeslab_icon_512.png     # Icono alta resolucion
|   |-- fondo.png                 # Fondo UI
|   +-- laboratorio-clinico-2.png # Imagen branding
|
|-- logos/                        # Logos organizacionales
|   |-- logo_laboratorio.png
|   +-- logo_laboratorio.jpg
|
|-- firmas/                       # Firmas digitales de bioanalistas
|   +-- firma_bioanalista_1.png
|
|-- backups/                      # Backups automaticos (.accdb)
|-- logs/                         # Logs de aplicacion y auditoria
|-- tests/                        # Tests unitarios
|   |-- test_formato_pdf.py
|   +-- test_seguridad.py
|
+-- instalador/                   # Componentes del instalador
    |-- ANgesLAB_Setup.iss        # Script Inno Setup
    |-- COMPILAR_INSTALADOR.bat
    |-- instalar_dependencias.bat
    |-- instalar_dependencias_ia.bat
    +-- output/
        +-- ANgesLAB_Setup_v2.0.exe
```

## 2.4 Patron de conexion a base de datos

La clase `Database` en `ANgesLAB.pyw` encapsula toda la conectividad:

```
Aplicacion --> Database.connect()
                  |
                  v
            win32com.client.Dispatch('ADODB.Connection')
                  |
                  v
            Provider=Microsoft.ACE.OLEDB.12.0
                  |
                  v
            ANgesLAB.accdb (local o ruta LAN via db_config.json)
```

**Caracteristicas del patron**:
- Conexion singleton reutilizable
- Escape automatico de comillas simples (prevencion SQL injection)
- Manejo de tipos: fechas, nulos, booleanos adaptados a Access
- AUTOINCREMENT de Access: no permite forzar PK en INSERT, requiere UPDATE post-insercion

## 2.5 Patron de modulos

Cada modulo en `modulos/` sigue un patron consistente:

1. **Clase gestora**: Recibe instancia de `Database` en constructor
2. **Factory function**: `crear_gestor_xxx(db)` para instanciacion conveniente
3. **Flag de disponibilidad**: Constantes `XXXX_DISPONIBLE` para degradacion gracil de dependencias opcionales
4. **Aseguramiento de tablas**: Metodo `_asegurar_tablas()` ejecuta DDL si las tablas no existen
5. **Migracion de columnas**: Metodo `_migrar_columnas()` ejecuta ALTER TABLE para nuevas columnas

## 2.6 Flujo principal de la aplicacion

```
1. main()
   |
   2. SplashScreen (carga visual)
   |
   3. LoginWindow
   |   - Valida credenciales (PBKDF2)
   |   - Registra auditoria de login
   |   - Control de intentos fallidos
   |
   4. MainApplication.__init__()
   |   - Inicializa Database
   |   - Carga configuracion del laboratorio
   |   - Asegura tablas y columnas (migracion automatica)
   |   - Inicializa modulos (gestor_solicitudes, auditoria, etc.)
   |   - Verifica backup automatico
   |   - Arranca timeout de sesion (20 min)
   |
   5. Interfaz principal (sidebar + area de contenido)
       - Navegacion por secciones
       - CRUD de pacientes, solicitudes, resultados
       - Generacion de reportes PDF
       - Facturacion y cobros
       - Historial clinico + IA
```

## 2.7 Formatos de reporte PDF

El sistema soporta multiples formatos de pagina con escalado proporcional automatico:

| Formato      | Dimensiones (pt)  | Uso tipico                    |
|--------------|-------------------|-------------------------------|
| Carta        | 612 x 792         | Reportes clinicos estandar    |
| A4           | 595.28 x 841.89   | Reportes internacionales      |
| Oficio       | 612 x 1008        | Documentos legales/fiscales   |
| Media Carta  | 396 x 612         | Recibos compactos             |

La clase `LayoutCalculator` en `formato_pdf.py` ajusta automaticamente margenes, tamanos de fuente y espaciado segun el formato seleccionado.

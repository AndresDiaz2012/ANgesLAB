# 10 - Despliegue e Infraestructura

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 10.1 Requisitos del entorno

### Hardware minimo

| Componente    | Minimo                          | Recomendado                     |
|---------------|----------------------------------|---------------------------------|
| Procesador    | Intel Core i3 / AMD equivalent   | Intel Core i5 o superior       |
| RAM           | 4 GB                             | 8 GB                           |
| Disco         | 500 MB libres (app + BD)         | 2 GB (con backups)             |
| Pantalla      | 1366 x 768                       | 1920 x 1080                    |
| Red           | No requerida (opcional para LAN, BCV, IA cloud) | LAN para multi-estacion |

### Software requerido

| Software                          | Version     | Obligatorio | Notas                        |
|-----------------------------------|-------------|-------------|------------------------------|
| Windows                           | 7 / 10 / 11 | Si         | Solo Windows soportado       |
| Python                            | >= 3.8       | Si         | Runtime de la aplicacion     |
| Microsoft Access Database Engine  | 2016 (64-bit)| Si         | Driver OLEDB 12.0            |
| Ollama                            | Ultima       | No         | Para IA local                |

---

## 10.2 Metodos de instalacion

### 10.2.1 Instalador automatico (recomendado)

| Propiedad          | Valor                                    |
|--------------------|------------------------------------------|
| Herramienta        | Inno Setup 6.x                           |
| Script             | instalador/ANgesLAB_Setup.iss            |
| Ejecutable         | instalador/output/ANgesLAB_Setup_v2.0.exe |
| Compilacion        | instalador/COMPILAR_INSTALADOR.bat        |

El instalador realiza:
1. Copia de archivos de la aplicacion al directorio de destino
2. Instalacion de dependencias Python (instalar_dependencias.bat)
3. Instalacion opcional de dependencias IA (instalar_dependencias_ia.bat)
4. Creacion de acceso directo en el escritorio
5. Registro en programas instalados de Windows

### 10.2.2 Instalacion manual

```bash
# 1. Clonar o copiar el directorio del proyecto
# 2. Instalar dependencias base
pip install -r requirements.txt

# 3. (Opcional) Instalar dependencias IA
pip install anthropic openai pyBCV

# 4. Verificar Access Database Engine
# Descargar de: microsoft.com/en-us/download/details.aspx?id=54920

# 5. Ejecutar
python ANgesLAB.pyw
# o doble clic en ANgesLAB.vbs (oculta ventana de consola)
```

---

## 10.3 Archivos de configuracion

### 10.3.1 db_config.json

Ruta de la base de datos. Permite apuntar a un archivo en red LAN.

```json
{
  "db_path": "ANgesLAB.accdb"
}
```

Para uso en red:

```json
{
  "db_path": "\\\\SERVIDOR\\laboratorio\\ANgesLAB.accdb"
}
```

### 10.3.2 backup_config.json

Configuracion del sistema de backups automaticos.

```json
{
  "activo": true,
  "frecuencia": "diario",
  "retener_dias": 30,
  "ultima_backup": "2026-04-06T21:52:31"
}
```

| Campo          | Valores                  | Descripcion                            |
|----------------|--------------------------|----------------------------------------|
| activo         | true / false             | Activar/desactivar backups automaticos |
| frecuencia     | "diario" / "semanal"     | Periodicidad de ejecucion              |
| retener_dias   | Numero entero            | Dias antes de eliminar backups viejos  |
| ultima_backup  | ISO 8601                 | Marca temporal del ultimo backup       |

### 10.3.3 config_ia.json

Configuracion de proveedores de inteligencia artificial.

```json
{
  "proveedor_ia": "reglas",
  "claude_api_key": "",
  "openai_api_key": "",
  "ollama_url": "http://localhost:11434",
  "ollama_modelo": "llama3.2"
}
```

### 10.3.4 VERSION

Archivo plano con la version del software:

```
2.0.0
```

---

## 10.4 Sistema de backups

### 10.4.1 Backups automaticos

| Parametro            | Valor por defecto                      |
|----------------------|----------------------------------------|
| Directorio           | backups/                               |
| Formato de nombre    | ANgesLAB_backup_YYYYMMDD_HHMMSS.accdb  |
| Frecuencia           | Diario (configurable)                  |
| Retencion            | 30 dias (configurable)                 |
| Verificacion         | Al iniciar MainApplication             |

### 10.4.2 Flujo de backup automatico

```
MainApplication.__init__()
    |
    v
_verificar_backup_automatico()
    |-- Lee backup_config.json
    |-- Compara ultima_backup con fecha/hora actual
    |-- Si toca (segun frecuencia):
    |   |-- Ejecuta crear_backup()
    |   |-- Ejecuta limpiar_backups_antiguos()
    |   |-- Actualiza ultima_backup en config
    |-- Si no toca: no-op
```

### 10.4.3 Restauracion

| Paso | Accion                                                     |
|------|-------------------------------------------------------------|
| 1    | Seleccionar backup de la lista (listar_backups)             |
| 2    | El sistema crea backup de seguridad del estado actual       |
| 3    | Reemplaza ANgesLAB.accdb con el backup seleccionado         |
| 4    | Reinicia la conexion a base de datos                        |

### 10.4.4 Mantenimiento de base de datos

| Operacion                      | Metodo                              | Frecuencia sugerida |
|--------------------------------|-------------------------------------|---------------------|
| Verificar integridad           | verificar_integridad()              | Mensual             |
| Crear indices optimizados      | crear_indices_recomendados()        | Post-instalacion    |
| Archivar datos antiguos        | archivar_datos_antiguos()           | Trimestral          |
| Limpiar registros huerfanos    | limpiar_registros_huerfanos()       | Trimestral          |
| Analizar tamano de tablas      | analizar_tablas()                   | Mensual             |
| Exportar catalogo              | exportar_catalogo()                 | Pre-actualizacion   |

---

## 10.5 Migracion automatica de esquema

El sistema implementa migracion automatica de base de datos al iniciar:

### 10.5.1 Aseguramiento de tablas

Cada modulo con tablas propias implementa `_asegurar_tablas()` o `_crear_tablas_XXX()` que ejecuta `CREATE TABLE IF NOT EXISTS` equivalente (verificacion previa de existencia en Access).

### 10.5.2 Migracion de columnas

El metodo `_migrar_columnas_fiscales()` y similares ejecutan `ALTER TABLE ADD COLUMN` para nuevas columnas, con manejo de error silencioso si la columna ya existe.

### 10.5.3 Columnas migradas automaticamente

| Tabla                          | Columnas nuevas                                      |
|--------------------------------|------------------------------------------------------|
| Facturas                       | MontoIGTF, TasaIGTF, AplicaIGTF, MonedaFactura, TasaCambioDia, MontoTotalBs, MontoTotalUSD, TipoDocumento, FacturaAfectadaID |
| Cobros                         | MontoIGTF, AplicaIGTF, MonedaPago                     |
| ConfiguracionAdministrativa    | TasaCOP_USD, IGTFPorDefecto, UltimaActualizacionBCV   |
| ConfiguracionLaboratorio       | IGTFActivo, TasaIGTF, TipoContribuyente               |

---

## 10.6 Estructura de directorios en produccion

```
C:\ANgesLAB\                      (o ruta de instalacion elegida)
|-- ANgesLAB.pyw                  # Ejecutable principal
|-- ANgesLAB.vbs                  # Lanzador sin consola
|-- ANgesLAB.accdb                # Base de datos
|-- VERSION                       # Version del software
|-- requirements.txt              # Dependencias
|-- db_config.json                # Config de BD
|-- backup_config.json            # Config de backups
|-- config_ia.json                # Config de IA
|
|-- modulos/                      # 36 modulos Python
|-- assets/                       # Iconos e imagenes
|-- logos/                        # Logos del laboratorio
|-- firmas/                       # Firmas digitales
|-- backups/                      # Backups automaticos
|-- logs/                         # Logs de aplicacion
|   |-- angeslab.log
|   |-- angeslab_errores.log
|   +-- auditoria_clinica.log
|-- tests/                        # Tests unitarios
+-- docs/                         # Documentacion (PRD)
    +-- PRD/                      # Este documento
```

---

## 10.7 Lanzamiento de la aplicacion

### 10.7.1 Metodo directo (desarrollo)

```bash
python ANgesLAB.pyw
```

### 10.7.2 Metodo sin consola (produccion)

Doble clic en `ANgesLAB.vbs`, que ejecuta:

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "pythonw ANgesLAB.pyw", 0, False
```

### 10.7.3 Acceso directo

`crear_acceso_directo.vbs` genera un shortcut en el escritorio del usuario.

---

## 10.8 Logs y monitoreo

### Archivos de log

| Archivo                      | Contenido                    | Tamano max | Rotacion     |
|------------------------------|------------------------------|------------|--------------|
| logs/angeslab.log            | Actividad general            | 5 MB       | 5 archivos   |
| logs/angeslab_errores.log    | Solo errores                 | 5 MB       | 5 archivos   |
| logs/auditoria_clinica.log   | Auditoria clinica            | 10 MB      | 10 archivos  |

### Niveles de log

| Nivel    | Uso                                           |
|----------|-----------------------------------------------|
| DEBUG    | Detalle de operaciones (solo desarrollo)       |
| INFO     | Operaciones normales, flujos completados       |
| WARNING  | Situaciones anomalas no criticas               |
| ERROR    | Errores que impiden una operacion              |
| CRITICAL | Errores que comprometen la estabilidad         |

---

## 10.9 Procedimiento de actualizacion

| Paso | Accion                                                          |
|------|-----------------------------------------------------------------|
| 1    | Crear backup manual de ANgesLAB.accdb                           |
| 2    | Exportar catalogo actual (exportar_catalogo)                    |
| 3    | Reemplazar archivos .pyw y modulos/ con nueva version           |
| 4    | Ejecutar pip install -r requirements.txt (nuevas dependencias)  |
| 5    | Iniciar aplicacion (migracion de esquema automatica)            |
| 6    | Verificar integridad de BD                                      |
| 7    | Actualizar VERSION si no viene en el paquete                    |

> **Nota**: La migracion de esquema es automatica. Al iniciar la nueva version, el sistema ejecuta `ALTER TABLE` y `CREATE TABLE` segun sea necesario. No se requiere intervencion manual sobre la base de datos.

---

## 10.10 Consideraciones de red (LAN)

### Configuracion multi-estacion

```
[Estacion 1] --\
[Estacion 2] ---+--> \\SERVIDOR\laboratorio\ANgesLAB.accdb
[Estacion 3] --/
```

| Parametro              | Valor                                          |
|------------------------|------------------------------------------------|
| Cada estacion tiene    | Copia local de .pyw, modulos/, assets/          |
| BD compartida          | Una sola copia en servidor via ruta UNC          |
| Concurrencia           | Limitada por MS Access (bloqueo a nivel pagina)  |
| Usuarios simultaneos   | Recomendado < 10 (limite practico de Access)     |
| Backup                 | Solo una estacion debe ejecutar backup automatico |

### Limitaciones conocidas

- MS Access no soporta transacciones ACID completas en red
- Posibles conflictos de bloqueo con alta concurrencia
- Se recomienda SQL Server para despliegues con > 10 usuarios simultaneos

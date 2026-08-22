# 09 - Integraciones Externas

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 9.1 Resumen de integraciones

| ID      | Integracion          | Tipo        | Obligatoria | Estado       |
|---------|----------------------|-------------|-------------|--------------|
| INT-001 | Microsoft Access     | Base datos  | Si          | Implementado |
| INT-002 | BCV (pyBCV)          | API REST    | No          | Implementado |
| INT-003 | Claude API           | API REST    | No          | Implementado |
| INT-004 | OpenAI API           | API REST    | No          | Implementado |
| INT-005 | Ollama               | API local   | No          | Implementado |
| INT-006 | SMTP (Email)         | Protocolo   | No          | Implementado |
| INT-007 | WhatsApp             | URL Scheme  | No          | Implementado |

---

## 9.2 INT-001: Microsoft Access (ADODB/COM)

### Descripcion

Conectividad principal a la base de datos mediante COM Automation de Windows.

### Configuracion

| Parametro        | Valor                                      |
|------------------|--------------------------------------------|
| Provider         | Microsoft.ACE.OLEDB.12.0                   |
| Archivo          | ANgesLAB.accdb (configurable en db_config.json) |
| Interfaz         | win32com.client.Dispatch('ADODB.Connection') |
| Dependencia      | pywin32 >= 306                             |
| Prerrequisito    | Microsoft Access Database Engine 2016      |

### Patron de uso

```python
conn = win32com.client.Dispatch('ADODB.Connection')
conn.Open(f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={ruta_accdb}")
rs = conn.Execute("SELECT * FROM Pacientes WHERE PacienteID = 1")
```

### Soporte LAN

El archivo `db_config.json` permite configurar la ruta de la base de datos para uso en red local:

```json
{
  "db_path": "\\\\SERVIDOR\\compartido\\ANgesLAB.accdb"
}
```

---

## 9.3 INT-002: Banco Central de Venezuela (BCV)

### Descripcion

Consulta automatica de tasas de cambio oficiales publicadas por el BCV.

### Configuracion

| Parametro                  | Valor                          |
|----------------------------|--------------------------------|
| Libreria                   | pyBCV >= 0.2                   |
| Flag de disponibilidad     | PYBCV_DISPONIBLE               |
| Cache en memoria           | 1 hora TTL                     |
| Tabla de persistencia      | TasasCambio                    |
| Monedas consultadas        | USD, EUR, CNY, TRY, RUB, JPY  |
| Fallback sin internet      | Ultima tasa en BD -> default 1.0 |

### Flujo de actualizacion

```
1. Verificar cache en memoria (TTL 1h)
   |-- Si vigente: retornar tasa en cache
   |-- Si expirado o vacio:
       |
       2. Consultar API pyBCV
          |-- Si exitoso: guardar en TasasCambio + cache, retornar
          |-- Si falla:
              |
              3. Consultar ultima tasa en BD
                 |-- Si existe: retornar
                 |-- Si no existe: retornar 1.0 (default)
```

### Tasa COP

La tasa COP no la publica BCV directamente. Se maneja como tasa manual `TasaCOP_USD` almacenada en `ConfiguracionAdministrativa`. Las conversiones COP pasan por USD como moneda puente:
- COP -> USD (manual) -> VES (BCV)

---

## 9.4 INT-003: Claude API (Anthropic)

### Descripcion

Interpretacion clinica avanzada de resultados de laboratorio usando Claude.

### Configuracion

| Parametro        | Valor                              |
|------------------|------------------------------------|
| Libreria         | anthropic >= 0.18                  |
| API Key          | config_ia.json -> claude_api_key   |
| Modelo sugerido  | Claude 4.5 Sonnet / Claude Opus   |
| Proveedor config | config_ia.json -> proveedor_ia: "claude" |

### Estructura del prompt

```
SISTEMA: Eres un asistente de interpretacion de resultados de laboratorio
         clinico. Tu interpretacion es ORIENTATIVA para el medico tratante.

CONTEXTO CLINICO:
- Diagnostico presuntivo: [del campo Solicitudes.DiagnosticoPresuntivo]
- Observaciones: [del campo Solicitudes.Observaciones]
- Sexo: [M/F]
- Edad: [calculada desde FechaNacimiento]

RESULTADOS:
[Tabla de parametros con valor, unidad, referencia, estado]

Proporciona una interpretacion clinica estructurada.
```

### Manejo de errores

- Verificacion de conectividad previa
- Timeout configurable
- Fallback a motor de reglas locales si API no disponible

---

## 9.5 INT-004: OpenAI API

### Descripcion

Alternativa a Claude para interpretacion clinica, usando GPT-4o-mini.

### Configuracion

| Parametro        | Valor                                |
|------------------|--------------------------------------|
| Libreria         | openai (ultima version)              |
| API Key          | config_ia.json -> openai_api_key     |
| Modelo           | gpt-4o-mini                          |
| Proveedor config | config_ia.json -> proveedor_ia: "openai" |

### Consideraciones

- Mas economico que GPT-4 con rendimiento adecuado para interpretacion clinica
- Mismo formato de prompt que Claude API
- Fallback identico al de Claude

---

## 9.6 INT-005: Ollama (LLM Local)

### Descripcion

Servidor de LLM local para interpretacion clinica sin conexion a internet ni costos de API.

### Configuracion

| Parametro        | Valor                                |
|------------------|--------------------------------------|
| URL base         | http://localhost:11434 (configurable) |
| Modelo default   | llama3.2                             |
| Protocolo        | HTTP REST                            |
| Dependencia      | Ollama instalado localmente          |
| Proveedor config | config_ia.json -> proveedor_ia: "ollama" |

### Verificacion de disponibilidad

El sistema verifica la conexion a Ollama antes de intentar la interpretacion:

```
GET http://localhost:11434/api/tags
   |-- 200 OK: Ollama disponible, listar modelos
   |-- Error/timeout: Ollama no disponible, fallback a reglas
```

### Endpoint de generacion

```
POST http://localhost:11434/api/generate
{
  "model": "llama3.2",
  "prompt": "[prompt clinico construido]",
  "stream": false
}
```

---

## 9.7 INT-006: Email (SMTP)

### Descripcion

Envio de resultados de laboratorio por correo electronico con PDF adjunto.

### Configuracion

| Parametro        | Fuente                                  |
|------------------|-----------------------------------------|
| Servidor SMTP    | ConfiguracionLaboratorio (en BD)        |
| Puerto           | ConfiguracionLaboratorio                |
| Email remitente  | ConfiguracionLaboratorio.Email          |
| Credenciales     | ConfiguracionLaboratorio                |

### Flujo de envio

```
1. Generar PDF de resultados
2. Construir email MimeMultipart
   |-- De: Email del laboratorio
   |-- Para: Email del paciente
   |-- Asunto: "Resultados de Laboratorio - [NombreLab]"
   |-- Cuerpo: Texto informativo
   |-- Adjunto: PDF de resultados
3. Enviar via smtplib (SMTP/TLS)
4. Registrar envio en auditoria (ENVIAR)
```

### Dependencia

- `smtplib` (biblioteca estandar Python, no requiere instalacion)
- `email.mime` (biblioteca estandar Python)

---

## 9.8 INT-007: WhatsApp

### Descripcion

Comparticion de resultados via WhatsApp usando URL scheme del navegador.

### Implementacion

```python
url = f"https://wa.me/{telefono_sanitizado}?text={mensaje_codificado}"
webbrowser.open(url)
```

### Limitaciones

- No adjunta PDF directamente (limitacion de URL scheme)
- Abre WhatsApp Web/Desktop con mensaje pre-redactado
- El usuario debe adjuntar manualmente el PDF si es necesario
- Requiere que el paciente tenga WhatsApp asociado al numero registrado

---

## 9.9 Cascada de proveedores IA

El sistema implementa una estrategia de cascada para la interpretacion clinica:

```
Nivel 1: Motor de reglas clinicas locales (siempre disponible, offline)
    |
    v (si configurado)
Nivel 2: Ollama (LLM local, sin costo, requiere instalacion)
    |
    v (si falla o no configurado)
Nivel 3: OpenAI GPT-4o-mini o Claude API (cloud, requiere API key + internet)
    |
    v (si falla o no configurado)
Fallback: Solo resultado del motor de reglas locales
```

### Prioridad configurable

El campo `proveedor_ia` en `config_ia.json` determina cual proveedor se intenta primero:
- `"reglas"`: Solo reglas locales (default, 100% offline)
- `"ollama"`: Ollama primero, fallback a reglas
- `"openai"`: OpenAI primero, fallback a reglas
- `"claude"`: Claude primero, fallback a reglas

---

## 9.10 Matriz de disponibilidad

| Integracion      | Sin internet | Sin Access Engine | Sin API key | Sin Ollama |
|------------------|-------------|-------------------|-------------|------------|
| MS Access        | Funciona    | **No funciona**   | Funciona    | Funciona   |
| BCV              | Fallback BD | Funciona          | Funciona    | Funciona   |
| Claude           | No funciona | Funciona          | No funciona | Funciona   |
| OpenAI           | No funciona | Funciona          | No funciona | Funciona   |
| Ollama           | Funciona    | Funciona          | Funciona    | No funciona|
| Reglas clinicas  | Funciona    | Funciona          | Funciona    | Funciona   |
| Email            | No funciona | Funciona          | Funciona    | Funciona   |
| WhatsApp         | No funciona | Funciona          | Funciona    | Funciona   |

> **Principio de diseno**: El sistema opera 100% funcional sin internet. Las integraciones cloud son mejoras opcionales que degradan gracilmente.

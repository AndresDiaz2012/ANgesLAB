# 01 - Vision del Producto

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 1.1 Proposito

ANgesLAB es un **Sistema de Informacion de Laboratorio (LIS)** disenado para la gestion integral de laboratorios clinicos en Venezuela. El sistema cubre el ciclo completo desde la recepcion de pacientes hasta la entrega de resultados, incluyendo facturacion fiscal, inventario, equipos, historial clinico e interpretacion asistida por inteligencia artificial.

## 1.2 Declaracion de vision

> Proveer a laboratorios clinicos una herramienta de escritorio robusta, auditable y conforme a la normativa venezolana, que optimice la operacion diaria, garantice la trazabilidad de resultados y facilite la toma de decisiones clinicas mediante tecnologia de IA.

## 1.3 Alcance del producto

### Dentro del alcance

| Area                        | Descripcion                                                        |
|-----------------------------|--------------------------------------------------------------------|
| Gestion de pacientes        | Registro, busqueda, historial demografico y clinico                |
| Solicitudes de laboratorio  | Creacion, seguimiento, flujo de estados, validacion                |
| Catalogo de pruebas         | 10 areas clinicas, parametros, valores de referencia por edad/sexo |
| Captura de resultados       | Entrada manual, calculos automaticos (50+), validacion de rangos   |
| Reportes PDF                | 25+ plantillas clinicas y administrativas, QR, firmas digitales    |
| Facturacion fiscal          | Facturas, NC, ND, libros de ventas conforme a SENIAT               |
| Multi-moneda                | VES, USD, COP con tasas BCV automaticas                            |
| Cumplimiento tributario     | IVA (16%), IGTF (3%), retenciones ISLR                             |
| Administracion financiera   | Caja, cuentas por cobrar/pagar, gastos, comisiones medicas         |
| Inventario                  | Insumos, reactivos, lotes, alertas de stock minimo y vencimiento   |
| Equipos                     | Registro, mantenimiento preventivo, alertas de calibracion         |
| Historial clinico           | Evolucion temporal, tendencias, alertas de valores criticos         |
| IA clinica                  | Interpretacion por reglas locales + LLM (Ollama/OpenAI/Claude)     |
| Graficas de evolucion       | Visualizacion matplotlib de parametros en el tiempo                |
| Modulo veterinario          | Pacientes animales con catalogos y referencias por especie         |
| Auditoria                   | Trazabilidad completa: quien, cuando, que, antes/despues           |
| Seguridad                   | PBKDF2, roles RBAC, bloqueo de cuentas, timeout de sesion          |
| Backups automaticos         | Copias diarias con retencion configurable y restauracion           |
| Entrega de resultados       | Email SMTP, WhatsApp, impresion directa                            |
| Cotizaciones                | Presupuestos convertibles a solicitudes                            |

### Fuera del alcance (version actual)

- Conexion con analizadores automaticos (interfacing LIS-HIS)
- Facturacion electronica SENIAT en tiempo real
- Aplicacion web o movil
- Integracion con sistemas de historia medica electronica (HCE) externos
- Soporte para bases de datos SQL Server / PostgreSQL

## 1.4 Objetivos estrategicos

| ID    | Objetivo                                  | Metrica de exito                                    |
|-------|-------------------------------------------|-----------------------------------------------------|
| OE-01 | Reducir tiempo de emision de resultados   | < 5 min desde validacion hasta PDF disponible        |
| OE-02 | Garantizar trazabilidad completa          | 100% de modificaciones registradas en auditoria      |
| OE-03 | Cumplimiento fiscal total                 | 0 observaciones en auditoria SENIAT                  |
| OE-04 | Continuidad operativa                     | Backup automatico diario, restauracion < 10 min      |
| OE-05 | Asistencia clinica con IA                 | Interpretacion disponible offline (reglas locales)   |
| OE-06 | Soporte multi-moneda en tiempo real       | Tasas BCV actualizadas automaticamente cada hora      |

## 1.5 Usuarios y stakeholders

| Rol                  | Descripcion                                          | Nivel de acceso     |
|----------------------|------------------------------------------------------|---------------------|
| Administrador        | Configuracion total del sistema                      | Total               |
| Desarrollador        | Acceso avanzado para mantenimiento tecnico            | Total + debug       |
| Bioanalista          | Captura y validacion de resultados clinicos           | Clinico completo    |
| Recepcion            | Registro de pacientes, solicitudes, caja              | Operativo limitado  |
| Facturador           | Emision de facturas, cobros, libros fiscales          | Financiero          |
| Consulta             | Visualizacion de datos sin modificacion               | Solo lectura        |

## 1.6 Restricciones

| Restriccion                        | Justificacion                                                  |
|------------------------------------|----------------------------------------------------------------|
| Solo Windows (7/10/11)             | Dependencia de Microsoft Access via COM (pywin32)               |
| Base de datos MS Access (.accdb)   | Simplicidad de despliegue, sin servidor de BD requerido         |
| Python 3.8+                        | Runtime minimo para dependencias (reportlab, matplotlib)        |
| Conexion a internet opcional       | Solo necesaria para BCV, IA cloud; funciona 100% offline        |
| Microsoft Access Database Engine   | Driver OLEDB 12.0 requerido para conectividad                   |

## 1.7 Supuestos

1. El laboratorio opera bajo normativa fiscal venezolana vigente (SENIAT).
2. Los usuarios cuentan con estaciones Windows con Python 3.8+ o el instalador provee el runtime.
3. La base de datos no superara 2 GB (limite de Access), suficiente para operacion de laboratorio mediano.
4. Las tasas de cambio BCV son la referencia oficial para conversiones multi-moneda.
5. La interpretacion por IA es orientativa y no sustituye el criterio del medico tratante.

## 1.8 Dependencias externas

| Dependencia       | Version   | Tipo       | Proposito                              |
|-------------------|-----------|------------|----------------------------------------|
| Python            | >= 3.8    | Runtime    | Lenguaje base                          |
| reportlab         | >= 4.0    | Obligatoria| Generacion de PDF                      |
| Pillow            | >= 10.0   | Obligatoria| Procesamiento de imagenes              |
| pywin32           | >= 306    | Obligatoria| Acceso COM a MS Access                 |
| matplotlib        | >= 3.8    | Obligatoria| Graficas de evolucion                  |
| numpy             | >= 1.26   | Obligatoria| Calculos numericos                     |
| requests          | >= 2.31   | Obligatoria| HTTP para APIs                         |
| qrcode            | >= 7.4    | Opcional   | Codigos QR en reportes                 |
| pyBCV             | >= 0.2    | Opcional   | Tasas de cambio BCV automaticas        |
| anthropic         | >= 0.18   | Opcional   | API de Claude para IA clinica          |
| openai            | latest    | Opcional   | API de GPT-4o-mini para IA clinica     |

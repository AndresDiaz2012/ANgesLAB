# ANgesLAB - Documento de Requisitos de Producto (PRD)

---

| Campo                  | Detalle                                                |
|------------------------|--------------------------------------------------------|
| **Producto**           | ANgesLAB - Sistema de Informacion de Laboratorio (LIS) |
| **Version del PRD**    | 1.0.0                                                  |
| **Version del Software** | 2.0.0                                                |
| **Fecha de emision**   | 2026-04-07                                             |
| **Clasificacion**      | Confidencial - Uso interno                             |
| **Propietario**        | ANgesLAB                                               |
| **Estado**             | Vigente                                                |

---

## Control de versiones del documento

| Version | Fecha      | Autor          | Descripcion del cambio          |
|---------|------------|----------------|---------------------------------|
| 1.0.0   | 2026-04-07 | Equipo ANgesLAB | Emision inicial del PRD completo |

---

## Indice general

| #  | Documento                          | Archivo                            | Descripcion                                                       |
|----|------------------------------------|------------------------------------|-------------------------------------------------------------------|
| 01 | Vision del Producto                | `01_VISION_PRODUCTO.md`            | Proposito, alcance, objetivos estrategicos, stakeholders          |
| 02 | Arquitectura del Sistema           | `02_ARQUITECTURA_SISTEMA.md`       | Stack tecnologico, patrones, estructura de codigo, dependencias   |
| 03 | Requisitos Funcionales             | `03_REQUISITOS_FUNCIONALES.md`     | Funcionalidades por modulo con criterios de aceptacion            |
| 04 | Requisitos No Funcionales          | `04_REQUISITOS_NO_FUNCIONALES.md`  | Seguridad, rendimiento, usabilidad, mantenibilidad                |
| 05 | Modelo de Datos                    | `05_MODELO_DATOS.md`               | Esquema de base de datos, tablas, relaciones, indices             |
| 06 | Seguridad y Auditoria              | `06_SEGURIDAD_AUDITORIA.md`       | Autenticacion, roles, permisos, trazabilidad, cifrado             |
| 07 | Cumplimiento Regulatorio           | `07_CUMPLIMIENTO_REGULATORIO.md`   | SENIAT, IVA, IGTF, ISLR, ISO 15189, CLIA                        |
| 08 | Detalle de Modulos                 | `08_MODULOS_DETALLE.md`            | Especificacion tecnica de cada modulo del sistema                 |
| 09 | Integraciones Externas             | `09_INTEGRACIONES_EXTERNAS.md`     | BCV, Claude API, Ollama, OpenAI, SMTP, WhatsApp                  |
| 10 | Despliegue e Infraestructura       | `10_DESPLIEGUE_INFRAESTRUCTURA.md` | Instalacion, configuracion, backups, mantenimiento                |

---

## Documentos complementarios

| Documento              | Archivo              | Descripcion                                  |
|------------------------|----------------------|----------------------------------------------|
| Historial de cambios   | `CHANGELOG.md`       | Registro de cambios del PRD entre versiones   |

---

## Convenciones del documento

- **REQ-F-XXX**: Requisito funcional (XXX = numero secuencial)
- **REQ-NF-XXX**: Requisito no funcional
- **REQ-S-XXX**: Requisito de seguridad
- **REQ-R-XXX**: Requisito regulatorio
- **MOD-XXX**: Identificador de modulo
- **TBL-XXX**: Identificador de tabla de base de datos
- **INT-XXX**: Identificador de integracion externa

### Prioridades

| Codigo | Significado | Descripcion                                      |
|--------|-------------|--------------------------------------------------|
| P0     | Critica     | El sistema no puede operar sin esta funcionalidad |
| P1     | Alta        | Necesaria para operacion normal del laboratorio   |
| P2     | Media       | Mejora significativa de productividad             |
| P3     | Baja        | Mejora incremental, puede diferirse               |

### Estados de implementacion

| Estado        | Descripcion                           |
|---------------|---------------------------------------|
| Implementado  | Funcionalidad completa y en produccion |
| Parcial       | Implementado con limitaciones          |
| Planificado   | Aprobado, pendiente de desarrollo      |
| Propuesto     | En evaluacion                          |

---

> **Nota de auditoria**: Este documento y sus secciones constituyen el registro formal de requisitos del producto ANgesLAB. Cualquier modificacion debe ser registrada en la tabla de control de versiones y en el archivo `CHANGELOG.md`.

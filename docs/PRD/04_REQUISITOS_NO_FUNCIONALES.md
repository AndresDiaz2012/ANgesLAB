# 04 - Requisitos No Funcionales

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 4.1 Seguridad

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-001 | Hashing de contrasenas con PBKDF2-HMAC-SHA256 (600,000 iteraciones) | P0        | Implementado |
| REQ-NF-002 | Salt unico por usuario almacenado en BD                             | P0        | Implementado |
| REQ-NF-003 | Bloqueo de cuenta tras 5 intentos fallidos en 15 minutos            | P0        | Implementado |
| REQ-NF-004 | Timeout de sesion por inactividad (20 minutos)                      | P0        | Implementado |
| REQ-NF-005 | Escape automatico de comillas simples en queries SQL                | P0        | Implementado |
| REQ-NF-006 | Validacion de entrada: cedula, email, telefono, RIF, nombres        | P0        | Implementado |
| REQ-NF-007 | Contrasena minima: 8 caracteres, mayuscula, minuscula, digito       | P1        | Implementado |
| REQ-NF-008 | Migracion automatica de hashes legacy (SHA-256) a PBKDF2            | P1        | Implementado |
| REQ-NF-009 | Registro de todo acceso denegado en log de auditoria                | P0        | Implementado |

### Referencia normativa

- NIST SP 800-63B (Autenticacion digital - PBKDF2 600k iteraciones)
- OWASP Top 10 (Prevencion de inyeccion SQL, validacion de entradas)

---

## 4.2 Rendimiento

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-010 | Tiempo de inicio de aplicacion < 10 segundos (splash screen)        | P1        | Implementado |
| REQ-NF-011 | Busqueda de pacientes < 2 segundos para base de datos < 50,000 registros | P1  | Implementado |
| REQ-NF-012 | Generacion de PDF de resultados < 5 segundos                        | P1        | Implementado |
| REQ-NF-013 | Interpretacion IA local (reglas) < 1 segundo                        | P1        | Implementado |
| REQ-NF-014 | Cache de tasas BCV con TTL de 1 hora para evitar consultas excesivas | P2       | Implementado |
| REQ-NF-015 | Indices de BD optimizados para consultas frecuentes (13 indices)     | P1        | Implementado |

### Indices implementados

| Indice                     | Tabla                  | Columna(s)           |
|----------------------------|------------------------|----------------------|
| idx_pacientes_documento    | Pacientes              | NumeroDocumento      |
| idx_pacientes_nombre       | Pacientes              | NombreCompleto       |
| idx_solicitudes_paciente   | Solicitudes            | PacienteID           |
| idx_solicitudes_fecha      | Solicitudes            | FechaSolicitud       |
| idx_solicitudes_numero     | Solicitudes            | NumeroSolicitud      |
| idx_detalles_solicitud     | DetalleSolicitudes     | SolicitudID          |
| idx_detalles_prueba        | DetalleSolicitudes     | PruebaID             |
| idx_resultados_detalle     | ResultadosParametros   | DetalleID            |
| idx_resultados_parametro   | ResultadosParametros   | ParametroID          |
| idx_pruebas_area           | Pruebas                | AreaID               |
| idx_pruebas_codigo         | Pruebas                | CodigoPrueba         |
| idx_parametros_codigo      | Parametros             | CodigoParametro      |
| idx_auditoria_fecha        | LogAuditoria           | FechaHora            |

---

## 4.3 Disponibilidad y resiliencia

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-020 | Backup automatico diario con retencion configurable (default 30 dias) | P0      | Implementado |
| REQ-NF-021 | Restauracion de backup en < 10 minutos                              | P1        | Implementado |
| REQ-NF-022 | Backup de seguridad previo a restauracion                           | P0        | Implementado |
| REQ-NF-023 | Operacion 100% offline (sin dependencia de internet)                 | P0        | Implementado |
| REQ-NF-024 | Degradacion gracil: funcionalidades opcionales (IA, BCV, QR) no impiden operacion base | P0 | Implementado |
| REQ-NF-025 | Verificacion de integridad de BD (registros huerfanos, referencias rotas) | P2 | Implementado |
| REQ-NF-026 | Archivado automatico de solicitudes > 365 dias entregadas           | P2        | Implementado |

---

## 4.4 Usabilidad

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-030 | Interfaz nativa Windows con tematica profesional                    | P0        | Implementado |
| REQ-NF-031 | Navegacion por sidebar con secciones logicas                        | P0        | Implementado |
| REQ-NF-032 | Ventana responsiva que se adapta a resolucion de pantalla           | P1        | Implementado |
| REQ-NF-033 | Splash screen con indicador de progreso durante carga               | P2        | Implementado |
| REQ-NF-034 | Mensajes de error descriptivos y accionables                        | P1        | Implementado |
| REQ-NF-035 | Atajos de navegacion entre secciones frecuentes                     | P3        | Implementado |

---

## 4.5 Mantenibilidad

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-040 | Modularizacion: logica de negocio separada en 36 modulos Python    | P0        | Implementado |
| REQ-NF-041 | Migracion automatica de esquema (ALTER TABLE al iniciar)            | P0        | Implementado |
| REQ-NF-042 | Aseguramiento automatico de tablas al primer uso                    | P0        | Implementado |
| REQ-NF-043 | Logging centralizado con rotacion automatica                        | P1        | Implementado |
| REQ-NF-044 | Separacion de logs: general, errores, auditoria clinica             | P1        | Implementado |
| REQ-NF-045 | Exportacion/importacion de catalogo de pruebas en JSON              | P2        | Implementado |
| REQ-NF-046 | Archivo VERSION para control de version del software                | P1        | Implementado |

---

## 4.6 Compatibilidad

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-050 | Compatible con Windows 7, 10 y 11                                   | P0        | Implementado |
| REQ-NF-051 | Python 3.8 como version minima soportada                            | P0        | Implementado |
| REQ-NF-052 | Microsoft Access Database Engine 2016 (64-bit recomendado)          | P0        | Implementado |
| REQ-NF-053 | Soporte para BD en ruta local o red LAN (configurable)              | P1        | Implementado |

---

## 4.7 Auditabilidad

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-060 | Registro de todas las acciones criticas con marca temporal           | P0        | Implementado |
| REQ-NF-061 | Almacenamiento de valor anterior y nuevo en cada modificacion       | P0        | Implementado |
| REQ-NF-062 | Versionamiento completo de resultados clinicos                      | P0        | Implementado |
| REQ-NF-063 | Trazabilidad de logins exitosos y fallidos                          | P0        | Implementado |
| REQ-NF-064 | Registro de impresiones y envios de resultados                      | P1        | Implementado |
| REQ-NF-065 | Consulta de historial de auditoria por usuario y fecha              | P1        | Implementado |

### Referencia normativa

- ISO 15189:2022 seccion 8.4 (Gestion de informacion de laboratorio)
- CLIA 42 CFR 493.1291 (Trazabilidad de resultados)

---

## 4.8 Escalabilidad

| ID         | Requisito                                                          | Prioridad | Estado       |
|------------|---------------------------------------------------------------------|-----------|--------------|
| REQ-NF-070 | Base de datos soporta hasta 2 GB (limite MS Access)                 | P0        | Implementado |
| REQ-NF-071 | Archivado automatico para mantener BD dentro de limites             | P2        | Implementado |
| REQ-NF-072 | Estructura preparada para migracion futura a SQL Server              | P3        | Planificado  |

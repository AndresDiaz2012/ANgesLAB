# 03 - Requisitos Funcionales

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 3.1 Gestion de pacientes

| ID        | Requisito                                                | Prioridad | Estado       |
|-----------|----------------------------------------------------------|-----------|--------------|
| REQ-F-001 | Registrar pacientes con datos demograficos completos     | P0        | Implementado |
| REQ-F-002 | Buscar pacientes por cedula, nombre o numero de documento | P0        | Implementado |
| REQ-F-003 | Editar datos de pacientes existentes con auditoria       | P0        | Implementado |
| REQ-F-004 | Validar formato de cedula venezolana (V/E-XXXXXXX)       | P1        | Implementado |
| REQ-F-005 | Registrar alergias, enfermedades cronicas y observaciones | P2        | Implementado |
| REQ-F-006 | Asociar medico habitual al paciente                      | P2        | Implementado |
| REQ-F-007 | Desactivar pacientes sin eliminar datos historicos        | P1        | Implementado |

### Campos del paciente

- PacienteID (autoincremental)
- NumeroDocumento (cedula/RIF, validado)
- NombreCompleto (sanitizado)
- FechaNacimiento, Sexo
- Telefono (validado), Email (validado), Direccion
- MedicoHabitualID (FK a Medicos)
- Alergias, EnfermedadesCronicas, Observaciones
- Activo, FechaRegistro

---

## 3.2 Solicitudes de laboratorio

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-010 | Crear solicitud nueva asociada a un paciente                 | P0        | Implementado |
| REQ-F-011 | Agregar multiples pruebas de diferentes areas a una solicitud | P0        | Implementado |
| REQ-F-012 | Detectar solicitudes del mismo dia y ofrecer agregar a existente | P1     | Implementado |
| REQ-F-013 | Calcular monto total automaticamente segun precios de pruebas | P0       | Implementado |
| REQ-F-014 | Aplicar descuentos por convenio/seguro                        | P1        | Implementado |
| REQ-F-015 | Generar numero de solicitud secuencial configurable           | P0        | Implementado |
| REQ-F-016 | Registrar diagnostico presuntivo y observaciones              | P1        | Implementado |
| REQ-F-017 | Eliminar solicitud con verificacion de resultados existentes  | P1        | Implementado |
| REQ-F-018 | Generar comprobante de solicitud (PDF)                        | P0        | Implementado |

### Flujo de estados de la solicitud

```
Pendiente --> Recibida --> Procesando --> Completada --> Entregada
    |                                                       |
    +---------------------- Cancelada <---------------------+
```

| Estado      | Descripcion                                     | Transiciones permitidas        |
|-------------|--------------------------------------------------|-------------------------------|
| Pendiente   | Solicitud creada, muestras no recibidas          | Recibida, Cancelada            |
| Recibida    | Muestras recibidas en laboratorio                | Procesando, Cancelada          |
| Procesando  | Al menos un resultado ingresado                  | Completada                     |
| Completada  | Todos los resultados validados                   | Entregada                      |
| Entregada   | Resultados entregados al paciente                | (Estado final)                 |
| Cancelada   | Solicitud anulada con motivo registrado          | (Estado final)                 |

---

## 3.3 Catalogo de pruebas y parametros

| ID        | Requisito                                                     | Prioridad | Estado       |
|-----------|---------------------------------------------------------------|-----------|--------------|
| REQ-F-020 | Mantener catalogo de pruebas por area clinica                 | P0        | Implementado |
| REQ-F-021 | Definir parametros con tipo de dato, unidad y referencia      | P0        | Implementado |
| REQ-F-022 | Asociar multiples parametros a una prueba con orden secuencial | P0       | Implementado |
| REQ-F-023 | Soportar valores de referencia estratificados por edad y sexo  | P0       | Implementado |
| REQ-F-024 | Activar/desactivar pruebas sin eliminar datos historicos       | P1       | Implementado |
| REQ-F-025 | Asignar precio base por prueba                                 | P0       | Implementado |

### Areas clinicas soportadas

| AreaID | Codigo | Nombre          | Descripcion                                    |
|--------|--------|-----------------|------------------------------------------------|
| 1      | HEM    | Hematologia     | Hemograma, VSG, reticulocitos                  |
| 2      | QUI    | Quimica         | Glicemia, perfil lipidico, renal, hepatico     |
| 5      | COA    | Coagulacion     | PT, PTT, INR, fibrinogeno                      |
| 6      | URO    | Uroanalisis     | Examen fisico, quimico y microscopico de orina |
| 7      | PAR    | Parasitologia   | Coproanalisis, heces seriado                   |
| 8      | TIR    | Tiroides        | TSH, T3, T4, hormonas endocrinas               |
| 9      | SER    | Serologia       | HIV, hepatitis, TORCH, autoinmunidad           |
| 10     | MIC    | Microbiologia   | Cultivos (orina, sangre, heces, secreciones)   |
| 29     | GEN    | General         | Drogas, liquidos organicos, espermograma        |

> **Nota critica**: Los AreaID 1,2,5,6,7,8,9,10 estan hardcodeados en plantillas_reportes.py, form_inf_config.py y ANgesLAB.pyw. Cualquier cambio requiere actualizacion coordinada.

### Grupos de referencia por edad

| Grupo            | Rango de edad         |
|------------------|-----------------------|
| Recien nacido    | 0 - 28 dias           |
| Lactante         | 29 dias - 2 anos      |
| Pediatrico       | 2 - 12 anos           |
| Adolescente      | 12 - 18 anos          |
| Adulto           | 18 - 65 anos          |
| Adulto mayor     | > 65 anos             |

---

## 3.4 Captura y validacion de resultados

| ID        | Requisito                                                     | Prioridad | Estado       |
|-----------|---------------------------------------------------------------|-----------|--------------|
| REQ-F-030 | Ingresar resultados parametro por parametro                   | P0        | Implementado |
| REQ-F-031 | Soportar resultados numericos y de texto libre                | P0        | Implementado |
| REQ-F-032 | Validar valores contra rangos de referencia en tiempo real     | P0        | Implementado |
| REQ-F-033 | Detectar y alertar valores criticos (fuera de rango)          | P0        | Implementado |
| REQ-F-034 | Ejecutar calculos automaticos al ingresar valores primarios   | P0        | Implementado |
| REQ-F-035 | Registrar version anterior al modificar un resultado          | P0        | Implementado |
| REQ-F-036 | Formulario especializado para GTT (6 puntos temporales)       | P1        | Implementado |
| REQ-F-037 | Formulario especializado para cultivos microbiologicos        | P1        | Implementado |

### Calculos automaticos implementados (50+)

| Categoria          | Calculos                                                        |
|--------------------|-----------------------------------------------------------------|
| Hematologia        | VCM, HCM, CHCM, RDW, indices eritrocitarios                    |
| Perfil lipidico    | LDL (Friedewald), VLDL, colesterol no-HDL, indice aterogenico  |
| Funcion renal      | TFGe (CKD-EPI), depuracion creatinina, BUN                     |
| Funcion hepatica   | Bilirrubina indirecta, relacion AST/ALT                        |
| Endocrinologia     | HOMA-IR, HOMA-B (resistencia insulinica)                       |
| Urologia           | Indices PSA (libre/total)                                       |
| Antropometria      | IMC, superficie corporal                                        |
| Coagulacion        | INR a partir de TP                                              |
| Electrolitos       | Anion gap, osmolaridad serica calculada                         |

---

## 3.5 Reportes PDF

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-040 | Generar reporte de resultados por solicitud                  | P0        | Implementado |
| REQ-F-041 | Incluir encabezado con datos del laboratorio, RIF y logo     | P0        | Implementado |
| REQ-F-042 | Incluir codigo QR con informacion de la solicitud            | P2        | Implementado |
| REQ-F-043 | Incluir firma digital del bioanalista responsable            | P0        | Implementado |
| REQ-F-044 | Soportar 4 formatos de pagina (Carta, A4, Oficio, Media Carta) | P1     | Implementado |
| REQ-F-045 | Resaltar valores fuera de rango en reportes                  | P0        | Implementado |
| REQ-F-046 | Generar reportes agrupados por area clinica                  | P1        | Implementado |
| REQ-F-047 | Generar PDF de interpretacion IA con disclaimer              | P2        | Implementado |

### Catalogo de plantillas de reporte

| Codigo | Tipo           | Descripcion                              |
|--------|----------------|------------------------------------------|
| R01    | Clinico        | Comprobante de solicitud                 |
| R02    | Clinico        | Boleta/recibo principal                  |
| R03    | Operativo      | Lista diaria de pacientes                |
| R11    | Operativo      | Etiquetas de muestras                    |
| R13    | Clinico        | Hematologia completa                     |
| R18    | Clinico        | Perfil lipidico                          |
| R19    | Clinico        | Perfil renal                             |
| R20    | Clinico        | Perfil hepatico                          |
| R26    | Clinico        | Uroanalisis                              |
| R29    | Clinico        | Coproanalisis                            |
| R31    | Clinico        | Antigenos febriles                       |
| R32    | Clinico        | Serologia general                        |
| R40-R48B | Clinico     | Cultivos microbiologicos (9 variantes)   |
| R44    | Fiscal         | Factura fiscal                           |
| R45    | Fiscal         | Recibo de caja                           |
| R48    | Fiscal         | Libro de ventas                          |
| R55    | Ejecutivo      | Dashboard ejecutivo                      |
| R58    | Ejecutivo      | Pruebas mas solicitadas                  |

---

## 3.6 Facturacion fiscal

| ID        | Requisito                                                     | Prioridad | Estado       |
|-----------|---------------------------------------------------------------|-----------|--------------|
| REQ-F-050 | Generar facturas fiscales con numeracion secuencial           | P0        | Implementado |
| REQ-F-051 | Calcular IVA al 16% sobre servicios de laboratorio            | P0        | Implementado |
| REQ-F-052 | Calcular IGTF al 3% sobre pagos en divisa/Zelle               | P0        | Implementado |
| REQ-F-053 | Emitir notas de credito referenciando factura original         | P1        | Implementado |
| REQ-F-054 | Emitir notas de debito referenciando factura original          | P1        | Implementado |
| REQ-F-055 | Generar libro de ventas en formato SENIAT                      | P0        | Implementado |
| REQ-F-056 | Soportar facturacion multi-moneda (VES, USD, COP)              | P0        | Implementado |
| REQ-F-057 | Registrar cobros con deteccion automatica de IGTF              | P0        | Implementado |
| REQ-F-058 | Calcular retenciones de IVA (75% ordinario, 100% especial)     | P1        | Implementado |
| REQ-F-059 | Calcular retenciones de ISLR segun tipo de actividad           | P1        | Implementado |
| REQ-F-060 | Anular facturas con registro de auditoria                      | P1        | Implementado |
| REQ-F-061 | Generar resumen fiscal por periodo                             | P1        | Implementado |

---

## 3.7 Administracion financiera

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-070 | Apertura y cierre de caja con conciliacion                   | P0        | Implementado |
| REQ-F-071 | Registro de movimientos de caja (ingresos/egresos)           | P0        | Implementado |
| REQ-F-072 | Gestion de cuentas por cobrar con vencimiento                | P1        | Implementado |
| REQ-F-073 | Gestion de cuentas por pagar con proveedores                 | P1        | Implementado |
| REQ-F-074 | Registro y categorizacion de gastos                          | P1        | Implementado |
| REQ-F-075 | Dashboard financiero con KPIs                                | P2        | Implementado |
| REQ-F-076 | Gestion de cuentas bancarias                                 | P1        | Implementado |
| REQ-F-077 | Calculo de comisiones medicas                                | P2        | Implementado |
| REQ-F-078 | Soporte para multiples formas de pago                        | P0        | Implementado |

---

## 3.8 Inventario

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-080 | Registro de insumos y reactivos con codigo interno           | P1        | Implementado |
| REQ-F-081 | Control de stock con entradas, salidas y consumos            | P1        | Implementado |
| REQ-F-082 | Trazabilidad de lotes con fecha de vencimiento               | P1        | Implementado |
| REQ-F-083 | Alertas de stock minimo                                      | P1        | Implementado |
| REQ-F-084 | Alertas de lotes proximos a vencer                           | P2        | Implementado |
| REQ-F-085 | Valoracion de inventario                                     | P2        | Implementado |
| REQ-F-086 | Asociacion de insumos con proveedores y areas                | P2        | Implementado |

---

## 3.9 Equipos de laboratorio

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-090 | Registro de equipos con numero de serie y area               | P1        | Implementado |
| REQ-F-091 | Programacion de mantenimiento preventivo                     | P1        | Implementado |
| REQ-F-092 | Registro historico de mantenimientos realizados               | P1        | Implementado |
| REQ-F-093 | Alertas de mantenimiento proximo (7 dias anticipacion)        | P2        | Implementado |
| REQ-F-094 | Seguimiento de costos de mantenimiento                        | P2        | Implementado |
| REQ-F-095 | Estados de equipo: activo/inactivo/en mantenimiento           | P1        | Implementado |

---

## 3.10 Historial clinico y tendencias

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-100 | Visualizar historial completo de resultados por paciente     | P0        | Implementado |
| REQ-F-101 | Comparar resultados entre solicitudes (ultima vs anterior)   | P1        | Implementado |
| REQ-F-102 | Detectar tendencias (mejorando/empeorando/estable)           | P1        | Implementado |
| REQ-F-103 | Calcular delta porcentual entre mediciones                   | P2        | Implementado |
| REQ-F-104 | Generar graficas de evolucion temporal por parametro          | P1        | Implementado |
| REQ-F-105 | Mostrar banner de tendencia global del paciente              | P2        | Implementado |
| REQ-F-106 | Incluir diagnostico presuntivo y observaciones en historial  | P1        | Implementado |

---

## 3.11 Inteligencia artificial clinica

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-110 | Interpretar resultados con motor de reglas clinicas locales  | P1        | Implementado |
| REQ-F-111 | Soportar interpretacion via Ollama (LLM local)               | P2        | Implementado |
| REQ-F-112 | Soportar interpretacion via Claude API                       | P2        | Implementado |
| REQ-F-113 | Soportar interpretacion via OpenAI GPT-4o-mini               | P2        | Implementado |
| REQ-F-114 | Cascada automatica: reglas -> Ollama -> Cloud                 | P2        | Implementado |
| REQ-F-115 | Incluir contexto clinico (Dx, observaciones) en prompt IA    | P1        | Implementado |
| REQ-F-116 | Generar PDF de interpretacion con disclaimer legal            | P1        | Implementado |
| REQ-F-117 | Copiar texto de interpretacion al portapapeles                | P3        | Implementado |
| REQ-F-118 | Funcionar 100% offline con motor de reglas locales            | P0        | Implementado |

---

## 3.12 Modulo veterinario

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-120 | Registrar pacientes animales con especie, raza y propietario | P2        | Implementado |
| REQ-F-121 | Catalogo de pruebas veterinarias independiente                | P2        | Implementado |
| REQ-F-122 | Valores de referencia por especie (felino, canino, bovino)    | P2        | Implementado |
| REQ-F-123 | Flujo completo: solicitud -> resultados -> reporte            | P2        | Implementado |

---

## 3.13 Cotizaciones

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-130 | Crear cotizaciones con lista de pruebas y precios            | P2        | Implementado |
| REQ-F-131 | Convertir cotizacion aprobada en solicitud                   | P2        | Implementado |
| REQ-F-132 | Generar PDF de cotizacion                                    | P2        | Implementado |
| REQ-F-133 | Flujo de estados: pendiente -> aprobada -> convertida/cancelada | P2     | Implementado |

---

## 3.14 Entrega de resultados

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-140 | Enviar resultados por correo electronico (SMTP)              | P1        | Implementado |
| REQ-F-141 | Compartir resultados via WhatsApp (URL pre-construida)       | P2        | Implementado |
| REQ-F-142 | Impresion directa de reportes PDF                            | P0        | Implementado |
| REQ-F-143 | Registrar en auditoria cada envio/impresion de resultados    | P1        | Implementado |

---

## 3.15 Configuracion del sistema

| ID        | Requisito                                                    | Prioridad | Estado       |
|-----------|--------------------------------------------------------------|-----------|--------------|
| REQ-F-150 | Configurar datos del laboratorio (nombre, RIF, direccion)    | P0        | Implementado |
| REQ-F-151 | Configurar formato de numeracion de documentos               | P1        | Implementado |
| REQ-F-152 | Configurar tasas de cambio (automatica BCV + manual)         | P0        | Implementado |
| REQ-F-153 | Configurar parametros fiscales (IVA, IGTF, tipo contribuyente) | P0     | Implementado |
| REQ-F-154 | Configurar proveedor de IA (reglas/Ollama/OpenAI/Claude)     | P2        | Implementado |
| REQ-F-155 | Configurar backups automaticos (frecuencia, retencion)       | P1        | Implementado |
| REQ-F-156 | Configurar ruta de base de datos (local/LAN)                 | P1        | Implementado |
| REQ-F-157 | Gestionar logos, firmas y branding                           | P1        | Implementado |

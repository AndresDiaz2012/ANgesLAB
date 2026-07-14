# 05 - Modelo de Datos

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 5.1 Motor de base de datos

| Propiedad          | Valor                                      |
|--------------------|--------------------------------------------|
| Motor              | Microsoft Access 2016+                     |
| Archivo            | ANgesLAB.accdb                             |
| Driver             | Microsoft.ACE.OLEDB.12.0                   |
| Acceso             | ADODB via win32com.client (COM)            |
| Limite de tamano   | 2 GB                                       |
| Soporte LAN        | Si, via db_config.json                     |

---

## 5.2 Diagrama de relaciones (Entidad-Relacion simplificado)

```
Pacientes (1) ----< (N) Solicitudes (1) ----< (N) DetalleSolicitudes
                                                        |
                                                        | (N)
                                                        v
Pruebas (1) ----< (N) ParametrosPrueba (N) >---- (1) Parametros
                                                        |
                                                        | (1)
                                                        v
                                              ResultadosParametros
                                                        |
                                                        | (N)
                                                        v
                                              HistorialResultados

Solicitudes (1) ----< (N) Facturas (1) ----< (N) Cobros

Usuarios (1) ----< (N) UsuarioRol (N) >---- (1) Roles
                                                   |
                                                   | (1)
                                                   v
                                             PermisosModulo

Insumos (1) ----< (N) MovimientosInventario
Insumos (1) ----< (N) LotesInsumo

Equipos (1) ----< (N) MantenimientosEquipo
```

---

## 5.3 Tablas del nucleo clinico

### TBL-001: Pacientes

| Columna                | Tipo          | Nulo | Descripcion                          |
|------------------------|---------------|------|--------------------------------------|
| PacienteID             | AUTOINCREMENT | No   | Clave primaria                       |
| NumeroDocumento        | TEXT(20)      | No   | Cedula o RIF (validado V/E-XXXXXXX)  |
| NombreCompleto         | TEXT(100)     | No   | Nombre sanitizado                    |
| FechaNacimiento        | DATETIME      | Si   | Para calculo de edad y referencias   |
| Sexo                   | TEXT(1)       | Si   | M/F para referencias sex-specific    |
| Telefono               | TEXT(20)      | Si   | Validado                             |
| Email                  | TEXT(100)     | Si   | Validado                             |
| Direccion              | TEXT(255)     | Si   |                                      |
| MedicoHabitualID       | LONG          | Si   | FK a Medicos                         |
| Alergias               | MEMO          | Si   |                                      |
| EnfermedadesCronicas   | MEMO          | Si   |                                      |
| Observaciones          | MEMO          | Si   |                                      |
| Activo                 | BIT           | No   | Default TRUE                         |
| FechaRegistro          | DATETIME      | No   | Automatico                           |

### TBL-002: Solicitudes

| Columna                | Tipo          | Nulo | Descripcion                          |
|------------------------|---------------|------|--------------------------------------|
| SolicitudID            | AUTOINCREMENT | No   | Clave primaria                       |
| NumeroSolicitud        | TEXT(20)      | No   | Secuencial configurable              |
| PacienteID             | LONG          | No   | FK a Pacientes                       |
| FechaSolicitud         | DATETIME      | No   |                                      |
| EstadoSolicitud        | TEXT(20)      | No   | Pendiente/Recibida/Procesando/etc    |
| MontoTotal             | DOUBLE        | Si   | Calculado desde detalles             |
| DiagnosticoPresuntivo  | MEMO          | Si   | Del medico solicitante               |
| Observaciones          | MEMO          | Si   |                                      |
| UsuarioID              | LONG          | Si   | FK a Usuarios (quien creo)           |
| MedicoID               | LONG          | Si   | FK a Medicos                         |

### TBL-003: DetalleSolicitudes

| Columna       | Tipo          | Nulo | Descripcion                          |
|---------------|---------------|------|--------------------------------------|
| DetalleID     | AUTOINCREMENT | No   | Clave primaria                       |
| SolicitudID   | LONG          | No   | FK a Solicitudes                     |
| PruebaID      | LONG          | No   | FK a Pruebas                         |
| Estado        | TEXT(20)      | No   | Solicitada/Recibida/Procesando/etc   |
| Precio        | DOUBLE        | Si   | Precio al momento de solicitar       |

### TBL-004: ResultadosParametros

| Columna          | Tipo          | Nulo | Descripcion                          |
|------------------|---------------|------|--------------------------------------|
| ResultadoParamID | AUTOINCREMENT | No   | Clave primaria                       |
| DetalleID        | LONG          | No   | FK a DetalleSolicitudes              |
| ParametroID      | LONG          | No   | FK a Parametros                      |
| Valor            | TEXT(255)     | Si   | Resultado (numerico o texto)         |
| ValorReferencia  | TEXT(255)     | Si   | Rango de referencia aplicado         |
| Estado           | TEXT(20)      | Si   | Pendiente/Capturado/Validado         |

### TBL-005: Pruebas

| Columna       | Tipo          | Nulo | Descripcion                          |
|---------------|---------------|------|--------------------------------------|
| PruebaID      | AUTOINCREMENT | No   | Clave primaria                       |
| CodigoPrueba  | TEXT(20)      | No   | Codigo unico (ej: HEM001)           |
| NombrePrueba  | TEXT(100)     | No   |                                      |
| AreaID        | LONG          | No   | FK a Areas                           |
| PrecioBase    | DOUBLE        | Si   |                                      |
| Activo        | BIT           | No   | Default TRUE                         |

### TBL-006: Parametros

| Columna          | Tipo          | Nulo | Descripcion                          |
|------------------|---------------|------|--------------------------------------|
| ParametroID      | AUTOINCREMENT | No   | Clave primaria                       |
| CodigoParametro  | TEXT(20)      | No   | Codigo unico                         |
| NombreParametro  | TEXT(100)     | No   |                                      |
| Seccion          | TEXT(50)      | Si   | Agrupacion visual en reporte         |
| TipoResultado    | TEXT(20)      | Si   | Numerico/Texto/Seleccion             |
| UnidadID         | LONG          | Si   | FK a Unidades                        |
| Observaciones    | MEMO          | Si   | Notas de referencia base             |
| Activo           | BIT           | No   | Default TRUE                         |

### TBL-007: ParametrosPrueba

| Columna          | Tipo          | Nulo | Descripcion                          |
|------------------|---------------|------|--------------------------------------|
| ParametroPruebaID| AUTOINCREMENT | No   | Clave primaria                       |
| PruebaID         | LONG          | No   | FK a Pruebas                         |
| ParametroID      | LONG          | No   | FK a Parametros                      |
| Orden            | INTEGER       | Si   | Secuencia de aparicion               |

### TBL-008: Areas

| Columna     | Tipo          | Nulo | Descripcion                          |
|-------------|---------------|------|--------------------------------------|
| AreaID      | AUTOINCREMENT | No   | Clave primaria (IDs hardcodeados)    |
| CodigoArea  | TEXT(10)      | No   | Codigo unico (HEM, QUI, etc.)       |
| NombreArea  | TEXT(50)      | No   |                                      |
| Secuencia   | INTEGER       | Si   | Orden de aparicion                   |
| Activo      | BIT           | No   | Default TRUE                         |

### TBL-009: Unidades

| Columna   | Tipo          | Nulo | Descripcion                          |
|-----------|---------------|------|--------------------------------------|
| UnidadID  | AUTOINCREMENT | No   | Clave primaria                       |
| Simbolo   | TEXT(30)      | No   | ej: g/dL, mg/dL, x10^3/uL           |

### TBL-010: ValoresReferenciaEdadSexo

| Columna              | Tipo          | Nulo | Descripcion                          |
|----------------------|---------------|------|--------------------------------------|
| ValoresReferenciaID  | AUTOINCREMENT | No   | Clave primaria                       |
| ParametroID          | LONG          | No   | FK a Parametros                      |
| Sexo                 | TEXT(1)       | Si   | M/F/NULL(ambos)                      |
| EdadMinima           | DOUBLE        | Si   | En anos                              |
| EdadMaxima           | DOUBLE        | Si   | En anos                              |
| ValorMinimo          | DOUBLE        | Si   |                                      |
| ValorMaximo          | DOUBLE        | Si   |                                      |
| Unidad               | TEXT(30)      | Si   |                                      |

---

## 5.4 Tablas de auditoria y versionamiento

### TBL-011: LogAuditoria

| Columna        | Tipo          | Nulo | Descripcion                          |
|----------------|---------------|------|--------------------------------------|
| LogID          | AUTOINCREMENT | No   | Clave primaria                       |
| FechaHora      | DATETIME      | No   | Marca temporal del evento            |
| UsuarioID      | LONG          | Si   | FK a Usuarios                        |
| Accion         | TEXT(50)      | No   | LOGIN_EXITOSO, CREAR, MODIFICAR, etc |
| Tabla          | TEXT(50)      | Si   | Tabla afectada                       |
| RegistroID     | LONG          | Si   | ID del registro afectado             |
| ValorAnterior  | MEMO          | Si   | Estado antes del cambio              |
| ValorNuevo     | MEMO          | Si   | Estado despues del cambio            |

### Acciones auditadas

| Accion                | Descripcion                                    |
|-----------------------|------------------------------------------------|
| LOGIN_EXITOSO         | Inicio de sesion exitoso                       |
| LOGIN_FALLIDO         | Intento de login fallido                       |
| CAMBIO_PASSWORD       | Cambio de contrasena                           |
| ACCESO_DENEGADO       | Intento de acceso sin permisos                 |
| CREAR                 | Creacion de registro                           |
| MODIFICAR             | Modificacion de registro                       |
| ELIMINAR              | Eliminacion de registro                        |
| IMPRIMIR              | Impresion de reporte                           |
| ENVIAR                | Envio de resultados                            |
| RESULTADO_GUARDAR     | Guardado de resultado clinico                  |
| RESULTADO_VALIDAR     | Validacion de resultado                        |
| RESULTADO_CORREGIR    | Correccion de resultado ya validado            |

### TBL-012: HistorialResultados

| Columna         | Tipo          | Nulo | Descripcion                          |
|-----------------|---------------|------|--------------------------------------|
| HistorialID     | AUTOINCREMENT | No   | Clave primaria                       |
| FechaHora       | DATETIME      | No   | Marca temporal                       |
| UsuarioID       | LONG          | Si   | FK a Usuarios                        |
| DetalleID       | LONG          | No   | FK a DetalleSolicitudes              |
| ParametroID     | LONG          | No   | FK a Parametros                      |
| ValorAnterior   | TEXT(255)     | Si   |                                      |
| ValorNuevo      | TEXT(255)     | Si   |                                      |
| EstadoAnterior  | TEXT(20)      | Si   |                                      |
| EstadoNuevo     | TEXT(20)      | Si   |                                      |
| Accion          | TEXT(20)      | No   | GUARDAR/VALIDAR/CORREGIR             |
| Observacion     | MEMO          | Si   |                                      |

---

## 5.5 Tablas fiscales y financieras

### TBL-013: Facturas

| Columna            | Tipo          | Nulo | Descripcion                          |
|--------------------|---------------|------|--------------------------------------|
| FacturaID          | AUTOINCREMENT | No   | Clave primaria                       |
| NumeroFactura      | TEXT(20)      | No   | FAC-YYYY-NNNNNN                      |
| FechaEmision       | DATETIME      | No   |                                      |
| PacienteID         | LONG          | No   | FK a Pacientes                       |
| SolicitudID        | LONG          | Si   | FK a Solicitudes                     |
| SubTotal           | DOUBLE        | Si   |                                      |
| MontoIVA           | DOUBLE        | Si   |                                      |
| MontoTotal         | DOUBLE        | Si   |                                      |
| MontoIGTF          | DOUBLE        | Si   | Impuesto grandes transacciones       |
| TasaIGTF           | DOUBLE        | Si   | Porcentaje IGTF aplicado             |
| AplicaIGTF         | BIT           | Si   | Flag de aplicacion                   |
| MonedaFactura      | TEXT(3)       | Si   | USD/VES/COP                          |
| TasaCambioDia      | DOUBLE        | Si   | Tasa BCV del dia de emision          |
| MontoTotalBs       | DOUBLE        | Si   | Total en bolivares                   |
| MontoTotalUSD      | DOUBLE        | Si   | Total en dolares                     |
| TipoDocumento      | TEXT(10)      | Si   | Factura/NC/ND                        |
| FacturaAfectadaID  | LONG          | Si   | FK a Facturas (para NC/ND)           |
| Estado             | TEXT(20)      | Si   | Activa/Anulada                       |

### TBL-014: Cobros

| Columna        | Tipo          | Nulo | Descripcion                          |
|----------------|---------------|------|--------------------------------------|
| CobroID        | AUTOINCREMENT | No   | Clave primaria                       |
| FacturaID      | LONG          | No   | FK a Facturas                        |
| MontoCobrado   | DOUBLE        | No   |                                      |
| FechaCobro     | DATETIME      | No   |                                      |
| FormaPagoID    | LONG          | Si   | FK a FormasPago                      |
| Referencia     | TEXT(50)      | Si   | Numero de referencia bancaria        |
| MontoIGTF      | DOUBLE        | Si   | IGTF del cobro                       |
| AplicaIGTF     | BIT           | Si   |                                      |
| MonedaPago     | TEXT(3)       | Si   | Moneda usada para pagar              |

### TBL-015: TasasCambio

| Columna        | Tipo          | Nulo | Descripcion                          |
|----------------|---------------|------|--------------------------------------|
| TasaID         | AUTOINCREMENT | No   | Clave primaria                       |
| Fecha          | DATETIME      | No   | Fecha de la tasa                     |
| Moneda         | TEXT(3)       | No   | USD, EUR, COP, etc.                  |
| Tasa           | DOUBLE        | No   | Valor de la tasa (Bs por unidad)     |
| FuenteAPI      | TEXT(20)      | Si   | BCV, Manual, etc.                    |
| FechaConsulta  | DATETIME      | Si   | Cuando se consulto la API            |

### TBL-016: CajaChica

| Columna          | Tipo          | Nulo | Descripcion                          |
|------------------|---------------|------|--------------------------------------|
| CajaID           | AUTOINCREMENT | No   | Clave primaria                       |
| FechaApertura    | DATETIME      | No   |                                      |
| FechaCierre      | DATETIME      | Si   |                                      |
| MontoApertura    | DOUBLE        | No   |                                      |
| EfectivoInicial  | DOUBLE        | Si   |                                      |
| EfectivoFinal    | DOUBLE        | Si   |                                      |
| TotalIngresos    | DOUBLE        | Si   |                                      |
| TotalEgresos     | DOUBLE        | Si   |                                      |
| Diferencia       | DOUBLE        | Si   | Cuadre de caja                       |
| Estado           | TEXT(20)      | Si   | Abierta/Cerrada                      |
| UsuarioID        | LONG          | Si   | FK a Usuarios                        |

### TBL-017: CuentasPorCobrar

| Columna          | Tipo          | Nulo | Descripcion                          |
|------------------|---------------|------|--------------------------------------|
| CuentaCobrarID   | AUTOINCREMENT | No   | Clave primaria                       |
| FacturaID        | LONG          | Si   | FK a Facturas                        |
| PacienteID       | LONG          | Si   | FK a Pacientes                       |
| NombrePaciente   | TEXT(100)     | Si   |                                      |
| FechaEmision     | DATETIME      | Si   |                                      |
| FechaVencimiento | DATETIME      | Si   |                                      |
| MontoOriginal    | DOUBLE        | Si   |                                      |
| MontoCobrado     | DOUBLE        | Si   |                                      |
| SaldoPendiente   | DOUBLE        | Si   |                                      |
| DiasVencida      | INTEGER       | Si   |                                      |
| Estado           | TEXT(20)      | Si   | Pendiente/Parcial/Pagada/Vencida     |

### TBL-018: RetencionesISLR

| Columna          | Tipo          | Nulo | Descripcion                          |
|------------------|---------------|------|--------------------------------------|
| RetencionID      | AUTOINCREMENT | No   | Clave primaria                       |
| ProveedorID      | LONG          | Si   | FK a Proveedores                     |
| NumeroDocumento  | TEXT(30)      | Si   |                                      |
| FechaDocumento   | DATETIME      | Si   |                                      |
| MontoDocumento   | DOUBLE        | Si   |                                      |
| TipoActividad    | TEXT(50)      | Si   | Servicios salud, honorarios, etc.    |
| TasaRetencion    | DOUBLE        | Si   | Porcentaje aplicado                  |
| MontoRetencion   | DOUBLE        | Si   |                                      |
| Periodo          | TEXT(10)      | Si   | YYYY-MM                              |

---

## 5.6 Tablas de seguridad y acceso

### TBL-019: Usuarios

| Columna         | Tipo          | Nulo | Descripcion                          |
|-----------------|---------------|------|--------------------------------------|
| UsuarioID       | AUTOINCREMENT | No   | Clave primaria                       |
| NombreUsuario   | TEXT(50)      | No   | Login unico                          |
| NombreCompleto  | TEXT(100)     | No   |                                      |
| ContrasenaHash  | TEXT(255)     | No   | PBKDF2-HMAC-SHA256                   |
| Salt            | TEXT(64)      | No   | Salt unico por usuario               |
| Email           | TEXT(100)     | Si   |                                      |
| Activo          | BIT           | No   | Default TRUE                         |

### TBL-020: Roles

| Columna       | Tipo          | Nulo | Descripcion                          |
|---------------|---------------|------|--------------------------------------|
| RolID         | AUTOINCREMENT | No   | Clave primaria                       |
| NombreRol     | TEXT(50)      | No   |                                      |
| Descripcion   | TEXT(255)     | Si   |                                      |
| NivelAcceso   | INTEGER       | Si   | Jerarquia numerica                   |
| Activo        | BIT           | No   | Default TRUE                         |

### TBL-021: PermisosModulo

| Columna        | Tipo          | Nulo | Descripcion                          |
|----------------|---------------|------|--------------------------------------|
| PermisoID      | AUTOINCREMENT | No   | Clave primaria                       |
| RolID          | LONG          | No   | FK a Roles                           |
| NombreModulo   | TEXT(50)      | No   | Nombre del modulo protegido          |
| PuedeVer       | BIT           | Si   |                                      |
| PuedeCrear     | BIT           | Si   |                                      |
| PuedeEditar    | BIT           | Si   |                                      |
| PuedeEliminar  | BIT           | Si   |                                      |
| PuedeExportar  | BIT           | Si   |                                      |

---

## 5.7 Tablas de inventario y equipos

### TBL-022: Insumos

| Columna        | Tipo          | Nulo | Descripcion                          |
|----------------|---------------|------|--------------------------------------|
| InsumoID       | AUTOINCREMENT | No   | Clave primaria                       |
| Nombre         | TEXT(100)     | No   |                                      |
| Tipo           | TEXT(50)      | Si   | Reactivo/Consumible/Material         |
| Unidad         | TEXT(20)      | Si   |                                      |
| CodigoInterno  | TEXT(20)      | Si   |                                      |
| Marca          | TEXT(50)      | Si   |                                      |
| StockActual    | DOUBLE        | Si   |                                      |
| StockMinimo    | DOUBLE        | Si   | Umbral para alerta                   |
| CostoUnitario  | DOUBLE        | Si   |                                      |
| ProveedorID    | LONG          | Si   | FK a Proveedores                     |
| AreaID         | LONG          | Si   | FK a Areas                           |
| Activo         | BIT           | No   | Default TRUE                         |

### TBL-023: Equipos

| Columna                      | Tipo          | Nulo | Descripcion                     |
|------------------------------|---------------|------|---------------------------------|
| EquipoID                     | AUTOINCREMENT | No   | Clave primaria                  |
| Nombre                       | TEXT(100)     | No   |                                 |
| Marca                        | TEXT(50)      | Si   |                                 |
| Modelo                       | TEXT(50)      | Si   |                                 |
| NumeroSerie                  | TEXT(50)      | Si   |                                 |
| AreaID                       | LONG          | Si   | FK a Areas                      |
| Estado                       | TEXT(20)      | Si   | Activo/Inactivo/Mantenimiento   |
| FechaAdquisicion             | DATETIME      | Si   |                                 |
| UltimoMantenimiento          | DATETIME      | Si   |                                 |
| ProximoMantenimiento         | DATETIME      | Si   |                                 |
| FrecuenciaMantenimientoDias  | INTEGER       | Si   |                                 |

---

## 5.8 Tablas veterinarias

### TBL-024: PacientesVet

| Columna              | Tipo          | Nulo | Descripcion                          |
|----------------------|---------------|------|--------------------------------------|
| PacienteVetID        | AUTOINCREMENT | No   | Clave primaria                       |
| CodigoPaciente       | TEXT(20)      | Si   |                                      |
| NombreMascota        | TEXT(50)      | No   |                                      |
| Especie              | TEXT(30)      | No   | Felino/Canino/Bovino                 |
| Raza                 | TEXT(50)      | Si   |                                      |
| Sexo                 | TEXT(1)       | Si   | M/H                                  |
| FechaNacimiento      | DATETIME      | Si   |                                      |
| Peso                 | DOUBLE        | Si   | En kg                                |
| Color                | TEXT(30)      | Si   |                                      |
| NombrePropietario    | TEXT(100)     | No   |                                      |
| TelefonoPropietario  | TEXT(20)      | Si   |                                      |
| EmailPropietario     | TEXT(100)     | Si   |                                      |

---

## 5.9 Tablas de configuracion

### TBL-025: ConfiguracionLaboratorio

| Columna               | Tipo          | Nulo | Descripcion                          |
|-----------------------|---------------|------|--------------------------------------|
| NombreLaboratorio     | TEXT(200)     | Si   |                                      |
| RIF                   | TEXT(20)      | Si   | Registro fiscal                      |
| Direccion             | TEXT(255)     | Si   |                                      |
| Telefono              | TEXT(20)      | Si   |                                      |
| Email                 | TEXT(100)     | Si   |                                      |
| TasaIVALaboratorio    | DOUBLE        | Si   | Default 16%                          |
| IGTFActivo            | BIT           | Si   |                                      |
| TasaIGTF              | DOUBLE        | Si   | Default 3%                           |
| TipoContribuyente     | TEXT(20)      | Si   | Ordinario/Especial                   |

### TBL-026: ConfiguracionAdministrativa

| Columna                  | Tipo          | Nulo | Descripcion                       |
|--------------------------|---------------|------|-----------------------------------|
| MontoMaximoCajaChica     | DOUBLE        | Si   |                                   |
| DiasVencimiento          | INTEGER       | Si   | Default 30                        |
| AlertaDias               | INTEGER       | Si   | Dias antes de alertar             |
| RequiereAprobacionGastos | BIT           | Si   |                                   |
| TasaCOP_USD              | DOUBLE        | Si   | Tasa manual COP/USD               |
| IGTFPorDefecto           | BIT           | Si   |                                   |
| UltimaActualizacionBCV   | DATETIME      | Si   |                                   |

### TBL-027: ConfiguracionNumeracion

| Columna            | Tipo          | Nulo | Descripcion                          |
|--------------------|---------------|------|--------------------------------------|
| TipoNumeracion     | TEXT(30)      | No   | Solicitud/Factura/NC/ND/Recibo       |
| PrefijoCodigo      | TEXT(10)      | Si   |                                      |
| ProximoNumero      | LONG          | Si   |                                      |
| AnnoInicio         | INTEGER       | Si   |                                      |
| UltimoNumeroUsado  | LONG          | Si   |                                      |

---

## 5.10 Consideraciones tecnicas de Access

| Aspecto                    | Comportamiento                                                    |
|----------------------------|-------------------------------------------------------------------|
| AUTOINCREMENT              | No permite forzar PK en INSERT; usar UPDATE post-insercion        |
| Tipos booleanos            | BIT: True=-1, False=0                                             |
| Fechas                     | DATETIME con formato #MM/DD/YYYY HH:MM:SS#                       |
| Texto largo                | MEMO (equivalente a TEXT sin limite)                               |
| Concurrencia               | Bloqueo a nivel de pagina; no ideal para alta concurrencia         |
| Tamano maximo              | 2 GB por archivo .accdb                                            |
| Unicode                    | Soporte completo UTF-16                                            |
| Null handling              | Requiere Is Null / Is Not Null en WHERE                            |

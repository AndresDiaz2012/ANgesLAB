# 06 - Seguridad y Auditoria

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 6.1 Autenticacion

### 6.1.1 Hashing de contrasenas

| Propiedad        | Valor                                              |
|------------------|----------------------------------------------------|
| Algoritmo        | PBKDF2-HMAC-SHA256                                 |
| Iteraciones      | 600,000 (conforme NIST SP 800-63B)                |
| Salt             | 32 bytes aleatorios unicos por usuario              |
| Almacenamiento   | ContrasenaHash + Salt en tabla Usuarios             |
| Legacy           | SHA-256 simple (migrado automaticamente al login)   |

### 6.1.2 Control de acceso al login

| Parametro                   | Valor                                  |
|-----------------------------|----------------------------------------|
| Intentos maximos            | 5 en ventana de 15 minutos             |
| Accion al exceder           | Bloqueo temporal de la cuenta           |
| Registro                    | LOGIN_EXITOSO y LOGIN_FALLIDO en log   |
| Validacion de fortaleza     | Min 8 chars, mayuscula, minuscula, digito |
| Generacion temporal         | Contrasena aleatoria para reset         |

### 6.1.3 Sesion

| Parametro                   | Valor                                  |
|-----------------------------|----------------------------------------|
| Timeout por inactividad     | 20 minutos                             |
| Deteccion                   | Monitoreo de actividad de mouse/teclado |
| Accion al expirar           | Retorno automatico a pantalla de login  |

---

## 6.2 Autorizacion (RBAC)

### 6.2.1 Roles predefinidos

| Rol              | NivelAcceso | Descripcion                                     |
|------------------|-------------|--------------------------------------------------|
| Administrador    | Maximo      | Acceso total a todas las funcionalidades          |
| Desarrollador    | Maximo+     | Acceso total + herramientas de debug              |
| Bioanalista      | Alto        | Captura, validacion, reportes, historial          |
| Recepcion        | Medio       | Pacientes, solicitudes, caja, dashboard financiero|
| Facturador       | Medio       | Facturacion, cobros, libros fiscales              |
| Consulta         | Bajo        | Solo lectura en todas las secciones               |

### 6.2.2 Matriz de permisos por modulo

| Modulo              | Admin | Bioanalista | Recepcion | Facturador | Consulta |
|---------------------|-------|-------------|-----------|------------|----------|
| Pacientes           | VCEED | VCE         | VCE       | V          | V        |
| Solicitudes         | VCEED | VCE         | VCE       | V          | V        |
| Resultados          | VCEED | VCEE        | V         | V          | V        |
| Pruebas/Parametros  | VCEED | V           | -         | -          | V        |
| Facturacion         | VCEED | V           | V         | VCEE       | V        |
| Caja                | VCEED | -           | VCE       | VCE        | V        |
| Inventario          | VCEED | VCE         | -         | -          | V        |
| Equipos             | VCEED | VCE         | -         | -          | V        |
| Configuracion       | VCEED | -           | -         | -          | -        |
| Auditoria           | V     | -           | -         | -          | -        |
| Usuarios/Roles      | VCEED | -           | -         | -          | -        |

> **Leyenda**: V=Ver, C=Crear, E=Editar, D=Eliminar, X=Exportar. "-" = Sin acceso.

### 6.2.3 Modelo de datos de permisos

```
Usuarios --(N:M via UsuarioRol)--> Roles --(1:N)--> PermisosModulo
```

Cada `PermisosModulo` define flags booleanos: `PuedeVer`, `PuedeCrear`, `PuedeEditar`, `PuedeEliminar`, `PuedeExportar`.

---

## 6.3 Validacion de entradas

| Tipo de dato       | Validacion                                             | Modulo           |
|--------------------|--------------------------------------------------------|------------------|
| Cedula             | Formato V/E-XXXXXXX, sin puntos ni espacios           | seguridad_db.py  |
| Email              | Patron RFC 5322 simplificado                           | seguridad_db.py  |
| Telefono           | Numerico, longitud valida                              | seguridad_db.py  |
| RIF                | Formato J/V/E/G-XXXXXXXXX                              | seguridad_db.py  |
| Nombre             | Sanitizacion: sin caracteres especiales peligrosos      | seguridad_db.py  |
| Numero documento   | Sanitizacion de inyeccion                              | seguridad_db.py  |
| Queries SQL        | Escape automatico de comillas simples en Database       | ANgesLAB.pyw     |

---

## 6.4 Auditoria activa

### 6.4.1 Componentes del sistema de auditoria

| Componente                | Archivo                | Funcion                                     |
|---------------------------|------------------------|----------------------------------------------|
| AuditoriaActiva           | auditoria.py           | Middleware de registro automatico             |
| AuditoriaSeguridad        | seguridad_db.py        | Eventos de seguridad (login, acceso denegado) |
| logging_config            | logging_config.py      | Infraestructura de logs centralizada          |
| HistorialResultados       | (tabla BD)             | Versionamiento de resultados clinicos         |

### 6.4.2 Eventos auditados

| Categoria            | Eventos                                                     |
|----------------------|-------------------------------------------------------------|
| Autenticacion        | Login exitoso, login fallido, cambio de contrasena           |
| Acceso               | Acceso denegado por falta de permisos                        |
| Datos clinicos       | Guardar, validar, corregir resultados                        |
| Datos administrativos| Crear, modificar, eliminar registros                         |
| Operaciones          | Imprimir reporte, enviar resultado, generar factura          |
| Validacion masiva    | Validacion de multiples resultados en una operacion          |

### 6.4.3 Estructura de un registro de auditoria

```
{
  "LogID": 12345,
  "FechaHora": "2026-04-07 14:30:22",
  "UsuarioID": 3,
  "Accion": "RESULTADO_CORREGIR",
  "Tabla": "ResultadosParametros",
  "RegistroID": 4567,
  "ValorAnterior": "4.5",
  "ValorNuevo": "4.8"
}
```

### 6.4.4 Consultas de auditoria

| Metodo                          | Descripcion                                      |
|---------------------------------|--------------------------------------------------|
| obtener_historial_resultado()   | Historial completo de cambios de un resultado    |
| obtener_log_usuario()           | Todas las acciones de un usuario con filtro fecha |
| registrar_validacion_masiva()   | Registro batch de validaciones                   |

---

## 6.5 Logging de aplicacion

### 6.5.1 Archivos de log

| Archivo                  | Contenido                              | Rotacion            |
|--------------------------|----------------------------------------|---------------------|
| logs/angeslab.log        | Actividad general de la aplicacion     | RotatingFileHandler |
| logs/angeslab_errores.log| Solo eventos de error                  | RotatingFileHandler |
| logs/auditoria_clinica.log| Auditoria clinica separada            | RotatingFileHandler |

### 6.5.2 Formato de log

```
[2026-04-07 14:30:22] [INFO] [modulo.clase] Usuario: admin | Accion: VALIDAR | Tabla: ResultadosParametros | ID: 4567
```

### 6.5.3 Referencia normativa

| Norma                        | Seccion     | Requisito cubierto                          |
|------------------------------|-------------|---------------------------------------------|
| ISO 15189:2022               | 8.4         | Gestion de informacion de laboratorio        |
| CLIA 42 CFR                  | 493.1291    | Trazabilidad de resultados                   |
| NIST SP 800-63B              | 5.1.1.2     | Hashing de credenciales                      |
| OWASP Top 10                 | A03:2021    | Prevencion de inyeccion                      |

---

## 6.6 Proteccion de datos del paciente

| Medida                                  | Implementacion                                  |
|-----------------------------------------|-------------------------------------------------|
| Acceso basado en rol                    | Solo usuarios autorizados ven datos clinicos     |
| Auditoria de acceso                     | Todo acceso a datos queda registrado             |
| No eliminacion fisica                   | Pacientes se desactivan, no se borran            |
| Versionamiento de resultados            | Cambios preservan valor anterior                 |
| Timeout de sesion                       | Prevencion de acceso no autorizado               |
| Validacion de entradas                  | Proteccion contra inyeccion y datos malformados  |
| Backup con retencion                    | Proteccion contra perdida de datos               |

---

## 6.7 Creacion automatica de usuario administrador

Al primer inicio del sistema, si no existe ningun usuario en la tabla `Usuarios`, el metodo `_asegurar_usuario_admin()` crea un usuario administrador por defecto:

| Campo             | Valor por defecto              |
|-------------------|-------------------------------|
| NombreUsuario     | admin                          |
| NombreCompleto    | Administrador del Sistema      |
| Contrasena        | (generada con PBKDF2)         |
| Rol               | Administrador                  |
| Activo            | True                           |

> **Nota de seguridad**: El usuario debe cambiar la contrasena del administrador inmediatamente despues de la primera instalacion.

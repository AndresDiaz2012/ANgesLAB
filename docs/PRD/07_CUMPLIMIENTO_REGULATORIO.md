# 07 - Cumplimiento Regulatorio

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 7.1 Marco regulatorio aplicable

| Normativa                          | Ambito                                | Estado       |
|------------------------------------|---------------------------------------|--------------|
| Providencia SNAT/2011/0071         | Facturacion general                   | Implementado |
| Providencia SNAT/2024/000102       | Facturacion digital                   | Implementado |
| Providencia SNAT/2022/000013       | IGTF en facturas                      | Implementado |
| Ley de IVA vigente                 | Impuesto al valor agregado            | Implementado |
| Decreto 1.808                      | Retenciones de ISLR                   | Implementado |
| ISO 15189:2022 seccion 8.4         | Gestion de informacion de laboratorio | Parcial      |
| CLIA 42 CFR 493.1291               | Trazabilidad de resultados            | Parcial      |
| NIST SP 800-63B                    | Autenticacion digital                 | Implementado |

---

## 7.2 Impuesto al Valor Agregado (IVA)

### 7.2.1 Tasas configuradas

| Tipo              | Tasa   | Aplicacion                              |
|-------------------|--------|-----------------------------------------|
| General           | 16%    | Servicios de laboratorio (por defecto)  |
| Reducida          | 8%     | Configurable para servicios especificos |
| Productos de lujo | 31%    | No aplica a laboratorio clinico          |
| Exento            | 0%     | Configurable por prueba                  |

### 7.2.2 Retenciones de IVA

| Tipo de contribuyente | Retencion | Base legal                              |
|-----------------------|-----------|-----------------------------------------|
| Ordinario             | 75%       | Ley de IVA, Art. 11                     |
| Especial              | 100%      | Ley de IVA, Agentes de retencion        |

### 7.2.3 Implementacion

- La tasa IVA se configura en `ConfiguracionLaboratorio.TasaIVALaboratorio`
- El tipo de contribuyente se configura en `ConfiguracionLaboratorio.TipoContribuyente`
- `facturacion_fiscal.py` calcula IVA y retencion automaticamente
- El libro de ventas agrupa transacciones por periodo fiscal

---

## 7.3 Impuesto a las Grandes Transacciones Financieras (IGTF)

### 7.3.1 Configuracion

| Parametro                    | Valor por defecto | Configurable |
|------------------------------|-------------------|--------------|
| Tasa IGTF                    | 3%                | Si           |
| IGTF activo                  | Si                | Si           |
| Formas de pago que aplican   | Divisa, Zelle     | Hardcodeado  |

### 7.3.2 Logica de aplicacion

```
REQ-R-001: El IGTF se aplica automaticamente cuando la forma de pago
           es 'Divisa' o 'Zelle', conforme a la Providencia SNAT/2022/000013.

REQ-R-002: El monto IGTF se calcula sobre el monto total de la factura
           (incluyendo IVA) y se registra en campos separados:
           - Facturas.MontoIGTF
           - Facturas.TasaIGTF
           - Facturas.AplicaIGTF

REQ-R-003: En el cobro, el IGTF se detecta automaticamente por la forma
           de pago seleccionada y se registra en:
           - Cobros.MontoIGTF
           - Cobros.AplicaIGTF
```

### 7.3.3 Campos en factura

La factura almacena el total con y sin IGTF para transparencia:
- `MontoTotal`: Subtotal + IVA (sin IGTF)
- `MontoIGTF`: Monto del impuesto IGTF
- `TasaIGTF`: Porcentaje aplicado
- Total a pagar = MontoTotal + MontoIGTF

---

## 7.4 Retenciones de ISLR (Decreto 1.808)

### 7.4.1 Tasas por tipo de actividad

| Tipo de actividad          | Tasa   | REQ-R     |
|----------------------------|--------|-----------|
| Servicios de salud         | 1%     | REQ-R-010 |
| Honorarios profesionales   | 3%     | REQ-R-011 |
| Servicios generales        | 2%     | REQ-R-012 |
| Compra de bienes           | 1%     | REQ-R-013 |
| Alquiler de inmuebles      | 3%     | REQ-R-014 |
| Comisiones comerciales     | 3%     | REQ-R-015 |
| Transporte/fletes          | 1%     | REQ-R-016 |
| Publicidad y propaganda    | 5%     | REQ-R-017 |

### 7.4.2 Registro

- Tabla `RetencionesISLR` almacena cada retencion con proveedor, documento, monto, tasa y periodo
- Generacion de reportes de retenciones por periodo fiscal

---

## 7.5 Facturacion conforme SENIAT

### 7.5.1 Numeracion de documentos fiscales

| Tipo documento   | Formato               | Ejemplo              |
|------------------|-----------------------|----------------------|
| Factura          | FAC-YYYY-NNNNNN       | FAC-2026-000145      |
| Nota de credito  | NC-YYYY-NNNNNN        | NC-2026-000012       |
| Nota de debito   | ND-YYYY-NNNNNN        | ND-2026-000003       |
| Numero de control| 00-NNNNNNNN           | 00-00000145          |

### 7.5.2 Requisitos de factura

| REQ-R     | Requisito                                                           | Estado       |
|-----------|---------------------------------------------------------------------|--------------|
| REQ-R-020 | Numero de factura secuencial sin saltos                             | Implementado |
| REQ-R-021 | Numero de control secuencial                                        | Implementado |
| REQ-R-022 | Datos del contribuyente emisor (razon social, RIF, direccion)       | Implementado |
| REQ-R-023 | Datos del receptor (nombre, cedula/RIF)                              | Implementado |
| REQ-R-024 | Fecha de emision                                                     | Implementado |
| REQ-R-025 | Descripcion detallada de servicios                                   | Implementado |
| REQ-R-026 | Desglose de subtotal, IVA y total                                    | Implementado |
| REQ-R-027 | Desglose de IGTF cuando aplique                                     | Implementado |
| REQ-R-028 | Anulacion con registro de motivo                                     | Implementado |

### 7.5.3 Notas de credito y debito

| REQ-R     | Requisito                                                           | Estado       |
|-----------|---------------------------------------------------------------------|--------------|
| REQ-R-030 | NC debe referenciar numero de factura original                      | Implementado |
| REQ-R-031 | ND debe referenciar numero de factura original                      | Implementado |
| REQ-R-032 | NC/ND afectan los totales del periodo fiscal                        | Implementado |

### 7.5.4 Libro de ventas

| REQ-R     | Requisito                                                           | Estado       |
|-----------|---------------------------------------------------------------------|--------------|
| REQ-R-040 | Generacion de libro de ventas por periodo mensual                   | Implementado |
| REQ-R-041 | Incluir: fecha, tipo documento, numero, cliente, RIF, base, IVA, IGTF | Implementado |
| REQ-R-042 | Distinguir entre ventas gravadas, exentas y no sujetas              | Implementado |
| REQ-R-043 | Incluir tasa de cambio del dia para facturas en moneda extranjera   | Implementado |
| REQ-R-044 | Totales acumulados por periodo                                       | Implementado |

---

## 7.6 Multi-moneda y tasas de cambio

### 7.6.1 Monedas soportadas

| Moneda | Codigo | Fuente de tasa              |
|--------|--------|-----------------------------|
| VES    | VES    | Moneda base (bolivares)     |
| USD    | USD    | BCV automatico o manual     |
| EUR    | EUR    | BCV automatico              |
| COP    | COP    | Derivado via USD (manual)   |

### 7.6.2 Requisitos regulatorios de conversion

| REQ-R     | Requisito                                                           | Estado       |
|-----------|---------------------------------------------------------------------|--------------|
| REQ-R-050 | Toda factura en moneda extranjera debe registrar tasa BCV del dia   | Implementado |
| REQ-R-051 | Facturas almacenan monto dual (MontoTotalBs + MontoTotalUSD)        | Implementado |
| REQ-R-052 | Libro de ventas refleja montos en bolivares al tipo de cambio oficial| Implementado |

---

## 7.7 Normativa clinica (ISO 15189 / CLIA)

### 7.7.1 Trazabilidad de resultados

| REQ-R     | Requisito                                                           | Estado       |
|-----------|---------------------------------------------------------------------|--------------|
| REQ-R-060 | Todo resultado tiene historial de versiones completo                | Implementado |
| REQ-R-061 | Registrar quien capturo, quien valido y quien corrigio              | Implementado |
| REQ-R-062 | Preservar valor anterior en toda correccion                         | Implementado |
| REQ-R-063 | Marca temporal en todas las operaciones de resultado                | Implementado |

### 7.7.2 Valores de referencia

| REQ-R     | Requisito                                                           | Estado       |
|-----------|---------------------------------------------------------------------|--------------|
| REQ-R-070 | Valores de referencia estratificados por edad y sexo                | Implementado |
| REQ-R-071 | Alertas automaticas de valores fuera de rango                       | Implementado |
| REQ-R-072 | Valores de referencia incluidos en reporte del paciente             | Implementado |

### 7.7.3 Controles de calidad

| REQ-R     | Requisito                                                           | Estado       |
|-----------|---------------------------------------------------------------------|--------------|
| REQ-R-080 | Registro de mantenimiento preventivo de equipos                     | Implementado |
| REQ-R-081 | Alertas de calibracion y mantenimiento proximo                      | Implementado |
| REQ-R-082 | Trazabilidad de lotes de reactivos                                  | Implementado |

---

## 7.8 Matriz de cumplimiento resumen

| Normativa                    | Cobertura | Observaciones                          |
|------------------------------|-----------|----------------------------------------|
| SENIAT Facturacion           | Alta      | Falta facturacion electronica en linea  |
| IVA                          | Completa  | Tasas y retenciones implementadas       |
| IGTF                         | Completa  | Deteccion automatica por forma de pago  |
| ISLR                         | Completa  | 8 tipos de actividad configurados       |
| ISO 15189:2022               | Parcial   | Auditoria y trazabilidad implementadas  |
| CLIA 42 CFR 493              | Parcial   | Versionamiento de resultados completo   |
| NIST SP 800-63B              | Completa  | PBKDF2-600k, salt, bloqueo             |

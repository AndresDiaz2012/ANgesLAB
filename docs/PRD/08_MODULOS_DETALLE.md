# 08 - Detalle de Modulos

**PRD ANgesLAB v1.0.0** | Fecha: 2026-04-07

---

## 8.1 Inventario de modulos

| ID       | Modulo                          | Archivo                              | Lineas aprox | Tipo          |
|----------|---------------------------------|--------------------------------------|-------------|---------------|
| MOD-001  | Aplicacion principal            | ANgesLAB.pyw                         | 17,000      | Core          |
| MOD-002  | Auditoria activa                | modulos/auditoria.py                 | ~400        | Soporte       |
| MOD-003  | Calculos automaticos            | modulos/calculos_automaticos.py      | ~600        | Clinico       |
| MOD-004  | Configuracion administrativa    | modulos/config_administrativa.py     | ~500        | Admin         |
| MOD-005  | Configuracion numeracion        | modulos/config_numeracion.py         | ~300        | Admin         |
| MOD-006  | Cotizaciones                    | modulos/cotizaciones.py              | ~400        | Operativo     |
| MOD-007  | Envio de resultados             | modulos/envio_resultados.py          | ~500        | Operativo     |
| MOD-008  | Gestion de equipos              | modulos/equipos.py                   | ~400        | Admin         |
| MOD-009  | Etiquetas de muestras           | modulos/etiquetas.py                 | ~300        | Operativo     |
| MOD-010  | Facturacion fiscal              | modulos/facturacion_fiscal.py        | ~800        | Fiscal        |
| MOD-011  | Flujo de trabajo                | modulos/flujo_trabajo.py             | ~400        | Core          |
| MOD-012  | Configuracion de formularios    | modulos/form_inf_config.py           | ~500        | Configuracion |
| MOD-013  | Formato PDF                     | modulos/formato_pdf.py               | ~400        | Soporte       |
| MOD-014  | Gestor de solicitudes           | modulos/gestor_solicitudes.py        | ~500        | Core          |
| MOD-015  | Graficas de historial           | modulos/graficas_historial.py        | ~400        | Clinico       |
| MOD-016  | Captura GTT                     | modulos/gtt_captura.py               | ~400        | Clinico       |
| MOD-017  | Reporte GTT                     | modulos/gtt_reporte.py               | ~300        | Clinico       |
| MOD-018  | Historial clinico               | modulos/historial_clinico.py         | ~600        | Clinico       |
| MOD-019  | Hojas de trabajo                | modulos/hojas_trabajo.py             | ~300        | Operativo     |
| MOD-020  | IA interpretacion               | modulos/ia_interpretacion.py         | ~800        | Clinico       |
| MOD-021  | Inventario                      | modulos/inventario.py                | ~500        | Admin         |
| MOD-022  | Logging                         | modulos/logging_config.py            | ~200        | Soporte       |
| MOD-023  | Modulo administrativo           | modulos/modulo_administrativo.py     | ~400        | Admin         |
| MOD-024  | Plantillas de reportes          | modulos/plantillas_reportes.py       | ~1,500      | Reportes      |
| MOD-025  | Reportes especificaciones       | modulos/reportes_especificaciones.py | ~400        | Reportes      |
| MOD-026  | Reportes de resultados          | modulos/reportes_resultados.py       | ~600        | Reportes      |
| MOD-027  | Seguridad BD                    | modulos/seguridad_db.py              | ~500        | Seguridad     |
| MOD-028  | Splash screen                   | modulos/splash_screen.py             | ~150        | UI            |
| MOD-029  | Tasas de cambio                 | modulos/tasas_cambio.py              | ~400        | Fiscal        |
| MOD-030  | Utilidades BD                   | modulos/utilidades_db.py             | ~600        | Soporte       |
| MOD-031  | Valores de referencia           | modulos/valores_referencia.py        | ~400        | Clinico       |
| MOD-032  | Ventana administrativa          | modulos/ventana_administrativa.py    | ~1,200      | Admin UI      |
| MOD-033  | Config administrativa (ventana) | modulos/ventana_config_administrativa.py | ~600   | Admin UI      |
| MOD-034  | Config numeracion (ventana)     | modulos/ventana_config_numeracion.py | ~300        | Admin UI      |
| MOD-035  | Configuracion completa          | modulos/ventana_configuracion_completa.py | ~500  | Admin UI      |
| MOD-036  | Veterinario                     | modulos/veterinario.py               | ~600        | Clinico       |

---

## 8.2 MOD-001: Aplicacion principal (ANgesLAB.pyw)

### Clases principales

| Clase             | Responsabilidad                                               |
|-------------------|---------------------------------------------------------------|
| Database          | Conectividad ADODB, CRUD, escape SQL, manejo de tipos         |
| LoginWindow       | Autenticacion, control de intentos, branding                  |
| MainApplication   | Orquestador UI, inicializacion de modulos, timeout de sesion  |

### Secciones de la interfaz (sidebar)

| Seccion         | Elementos                                                    |
|-----------------|--------------------------------------------------------------|
| Inicio          | Dashboard con metricas clave                                 |
| Registro        | Pacientes, Medicos                                           |
| Operacion       | Solicitudes, Cotizaciones, Pruebas*, Parametros*, Resultados, Historial |
| Informes        | Reportes                                                     |
| Administrativo  | Caja, Dashboard financiero, CxC, CxP, Gastos, Comisiones, Inventario, Equipos, Etiquetas, Hojas de trabajo |
| Configuracion   | Configuracion, Red LAN/DB, Backup automatico                 |
| VET             | Pacientes Vet, Solicitudes Vet, Resultados Vet               |

> *Solo visible para rol Administrador/Desarrollador

### Metodos criticos

| Metodo                            | Funcion                                              |
|-----------------------------------|------------------------------------------------------|
| _asegurar_usuario_admin()         | Crea admin por defecto en primera ejecucion          |
| _asegurar_areas_clinicas()        | Garantiza existencia de las 10 areas base            |
| _verificar_backup_automatico()    | Ejecuta backup si toca segun configuracion           |
| _calcular_alerta()                | Parser robusto de numeros con separador miles espanol |
| _ejecutar_ia_clinica()            | Orquesta interpretacion IA con datos del paciente    |
| _crear_pdf_interpretacion_ia()    | Genera PDF de interpretacion con disclaimer          |
| eliminar_prueba()                 | Eliminacion en cascada con FK                        |

---

## 8.3 MOD-003: Calculos automaticos

### Clase: CalculadorLaboratorio

Motor de calculos clinicos con 50+ formulas implementadas.

| Categoria          | Calculos                                    | Formula base                          |
|--------------------|---------------------------------------------|---------------------------------------|
| Hematologia        | VCM                                         | (Hto / RBC) x 10                     |
| Hematologia        | HCM                                         | (Hb / RBC) x 10                      |
| Hematologia        | CHCM                                        | (Hb / Hto) x 100                     |
| Lipidos            | VLDL                                        | Trigliceridos / 5                     |
| Lipidos            | LDL (Friedewald)                            | CT - HDL - VLDL                       |
| Lipidos            | Colesterol no-HDL                           | CT - HDL                              |
| Lipidos            | Indice aterogenico                          | CT / HDL                              |
| Renal              | TFGe (CKD-EPI)                              | Formula CKD-EPI 2021                  |
| Renal              | Depuracion creatinina                       | Cockcroft-Gault                       |
| Renal              | BUN                                         | Urea / 2.14                           |
| Hepatico           | Bilirrubina indirecta                       | BT - BD                               |
| Hepatico           | Relacion AST/ALT                            | AST / ALT                             |
| Endocrino          | HOMA-IR                                     | (Glucosa x Insulina) / 405           |
| Endocrino          | HOMA-B                                      | (360 x Insulina) / (Glucosa - 63)    |
| Urologia           | PSA libre/total                             | (PSA libre / PSA total) x 100        |
| Antropometria      | IMC                                         | Peso / Talla^2                        |
| Antropometria      | Superficie corporal                         | Mosteller: sqrt(Peso x Talla / 3600) |
| Coagulacion        | INR                                         | (TP paciente / TP control)^ISI        |
| Electrolitos       | Anion gap                                   | Na - (Cl + HCO3)                     |
| Electrolitos       | Osmolaridad serica                          | 2(Na) + Glu/18 + BUN/2.8            |

---

## 8.4 MOD-010: Facturacion fiscal

### Clase: FacturacionFiscal

| Metodo                          | Funcion                                              |
|---------------------------------|------------------------------------------------------|
| crear_factura()                 | Crea factura con IVA, IGTF, multi-moneda             |
| crear_nota_credito()            | NC referenciando factura original                    |
| crear_nota_debito()             | ND referenciando factura original                    |
| registrar_cobro()               | Registra pago con deteccion IGTF automatica          |
| calcular_totales_factura()      | Subtotal + IVA + IGTF por forma de pago              |
| calcular_igtf()                 | IGTF segun forma de pago                             |
| calcular_retencion_iva()        | 75% ordinario / 100% especial                        |
| generar_libro_ventas()          | Libro de ventas por periodo SENIAT                   |
| resumen_fiscal_periodo()        | Totales fiscales del periodo                         |
| anular_factura()                | Anulacion con motivo y auditoria                     |

### Clase: ConfiguracionFiscal

| Constante                  | Valor                         |
|----------------------------|-------------------------------|
| TASA_IVA_GENERAL           | 16%                           |
| TASA_IVA_REDUCIDA          | 8%                            |
| TASA_IVA_LUJO              | 31%                           |
| TASA_IGTF                  | 3%                            |
| FORMAS_PAGO_IGTF           | {'Divisa', 'Zelle'}          |
| RETENCION_IVA_ORDINARIO    | 75%                           |
| RETENCION_IVA_ESPECIAL     | 100%                          |

---

## 8.5 MOD-018: Historial clinico

### Clase: GestorHistorialClinico

| Metodo                           | Funcion                                              |
|----------------------------------|------------------------------------------------------|
| obtener_resumen_paciente()       | Resumen con pruebas frecuentes y alertas             |
| obtener_historial_paciente()     | Historial completo con Dx y observaciones            |
| obtener_tendencias_globales()    | Compara 2 ultimas solicitudes: mejorando/empeorando  |
| preparar_datos_para_ia()         | Empaqueta datos clinicos para prompt IA              |
| _obtener_alertas_ultima_solicitud() | Parametros fuera de rango en ultima solicitud     |
| _verificar_fuera_de_rango()      | Parser numerico con manejo de miles espanol          |

### Flujo de datos clinicos hacia IA

```
obtener_historial_paciente()
    |
    v
preparar_datos_para_ia()
    |-- Obtiene DiagnosticoPresuntivo, Observaciones de Solicitudes
    |-- Obtiene Sexo, FechaNacimiento de Pacientes
    |-- Empaqueta en paciente_info
    |
    v
ia_interpretacion._construir_prompt_clinico()
    |-- Incluye "CONTEXTO CLINICO" en prompt LLM
    |
    v
Interpretacion con disclaimer legal
```

---

## 8.6 MOD-020: IA interpretacion

### Clase: MotorReglasClinicas

Motor offline de reglas clinicas cubriendo las principales areas:

| Area         | Parametros interpretados                                      |
|--------------|---------------------------------------------------------------|
| Hematologia  | RBC, WBC, Hb, Hto, VCM, HCM, CHCM, PLT, diferencial        |
| Quimica      | Glucosa, CT, HDL, LDL, TG, creatinina, urea, acido urico    |
| Coagulacion  | PT, PTT, INR                                                  |
| Uroanalisis  | Hallazgos quimicos y microscopicos                            |
| Tiroides     | TSH, T3, T4                                                   |
| Serologia    | Anticuerpos y antigenos                                       |

Reglas especiales implementadas:
- WBC: umbrales en /mm3 (4000-11000)
- PLT: umbrales en /mm3 (150000-400000), grados de trombocitopenia
- Acido urico: sex-specific (H>7.0, M>6.0 mg/dL)
- HDL: sex-specific (H<40, M<50 mg/dL, ATP III)

### Clase: InterpretadorClinico

| Metodo                    | Funcion                                              |
|---------------------------|------------------------------------------------------|
| interpretar_completo()    | Cascada: reglas -> Ollama -> Cloud                   |
| _interpretar_con_reglas() | Motor local de reglas clinicas                       |
| _interpretar_con_ollama() | LLM local via HTTP localhost:11434                   |
| _interpretar_con_cloud()  | Claude API o OpenAI GPT-4o-mini                      |
| _construir_prompt_clinico()| Prompt con datos, contexto clinico y disclaimer     |

### Clase: ConfigIA

| Campo               | Valores posibles                    | Default          |
|---------------------|-------------------------------------|------------------|
| proveedor_ia        | reglas / ollama / openai / claude   | reglas           |
| claude_api_key      | sk-ant-...                          | (vacio)          |
| openai_api_key      | sk-...                              | (vacio)          |
| ollama_url          | URL                                 | localhost:11434  |
| ollama_modelo       | nombre modelo                       | llama3.2         |

---

## 8.7 MOD-029: Tasas de cambio

### Clase: GestorTasasCambio

| Metodo                    | Funcion                                              |
|---------------------------|------------------------------------------------------|
| actualizar_tasas_bcv()    | Consulta API pyBCV y guarda en TasasCambio           |
| obtener_tasa()            | Lee tasa vigente (cache 1h -> BD -> default 1.0)     |
| usd_to_bs()              | Conversion USD a bolivares                           |
| bs_to_usd()              | Conversion bolivares a USD                           |
| cop_to_usd()             | Conversion COP a USD (tasa manual)                   |
| usd_to_cop()             | Conversion USD a COP                                 |
| cop_to_bs()              | Conversion COP a bolivares (via USD)                 |
| bs_to_cop()              | Conversion bolivares a COP (via USD)                 |
| convertir()              | Conversion generica entre cualquier par              |
| get_tasas_historicas()    | Historico de tasas para graficas                     |

### Monedas soportadas por BCV

USD, EUR, CNY, TRY, RUB, JPY (la COP se deriva manualmente desde USD)

---

## 8.8 MOD-030: Utilidades de base de datos

### Clase: UtilidadesDB

| Metodo                            | Funcion                                              |
|-----------------------------------|------------------------------------------------------|
| crear_backup()                    | Copia timestamped de .accdb                          |
| listar_backups()                  | Lista con metadatos (tamano, fecha)                  |
| restaurar_backup()                | Restaura con backup previo de seguridad              |
| limpiar_backups_antiguos()        | Limpieza por retencion (default 30 dias)             |
| verificar_integridad()            | Verifica integridad referencial                      |
| crear_indices_recomendados()      | Crea 13 indices optimizados                          |
| analizar_tablas()                 | Reporte de tamanos y estado de tablas                |
| archivar_datos_antiguos()         | Archiva solicitudes > 365 dias entregadas            |
| limpiar_registros_huerfanos()     | Limpia registros sin padre referencial               |
| exportar_catalogo()               | Exporta areas/pruebas/parametros a JSON              |
| importar_catalogo()               | Importa catalogo desde JSON                          |

---

## 8.9 MOD-036: Veterinario

### Clase: GestorVeterinario

| Funcionalidad              | Descripcion                                           |
|----------------------------|-------------------------------------------------------|
| Pacientes animales         | Registro con especie, raza, peso, color, propietario  |
| Especies soportadas        | Felino, Canino, Bovino                                |
| Catalogo de pruebas        | Independiente del catalogo humano                     |
| Parametros por especie     | Valores de referencia especificos                     |
| Solicitudes veterinarias   | Flujo completo paralelo al humano                     |
| Resultados veterinarios    | Captura y reporte independiente                       |

---

## 8.10 MOD-024: Plantillas de reportes

### 25+ plantillas categorizadas

| Categoria        | Plantillas                                                    |
|------------------|---------------------------------------------------------------|
| Clinicas (12)    | R13 Hematologia, R18 Lipidos, R19 Renal, R20 Hepatico, R26 Uroanalisis, R29 Copro, R31 Febriles, R32 Serologia |
| Microbiologia (9)| R40-R48B: Cultivo general, urocultivo, hemocultivo, coprocultivo, secreciones, heridas, baciloscopia, micologia, conjuntival |
| Operativos (3)   | R01 Comprobante, R02 Boleta, R03 Lista diaria, R11 Etiquetas |
| Fiscales (3)     | R44 Factura fiscal, R45 Recibo caja, R48 Libro ventas        |
| Ejecutivos (2)   | R55 Dashboard, R58 Pruebas mas solicitadas                   |

Cada plantilla usa `LayoutCalculator` para escalado proporcional automatico entre formatos de pagina.

# ANgesLAB — ERP Administrativo y Fiscal (Especificación)

Fecha: 08/11/2026 · Autor: Andres Diaz

> Copia versionada de la especificación. El original editable está en Claude:
> https://claude.ai/artifact/XeBZUnUJitCfsc315MdJc5
> Si se cambia allí, hay que actualizar este archivo en el mismo commit que el código que lo siga.

## 1. Propósito y alcance

ANgesLAB tendrá un ERP administrativo y fiscal propio de un laboratorio clínico: cada bolívar que entra o sale queda en un documento fiscal válido, en un libro y en un reporte, sin hojas de cálculo aparte. La meta es llegar al **19/04/2027**, fecha en que entra en vigor la Providencia SNAT/2026/00093, con todo funcionando y probado.

**Dentro del alcance:** servicios (pruebas y perfiles), productos (reactivos e insumos), clientes, proveedores, compras, inventario, cuentas por pagar, cuentas por cobrar, caja, facturación electrónica (por imprenta digital o máquina fiscal), retenciones de IVA e ISLR, libros fiscales y reportes de gestión.

**Fuera del alcance:** contabilidad general completa (plan de cuentas, mayor, balances), nómina y activos fijos. El ERP exporta lo que el contador necesita para llevarlos en su propio sistema.

### Principios de diseño

1. **El documento fiscal es inmutable.** Una factura emitida no se edita ni se borra: se corrige con nota de crédito o de débito, y se anula solo por el procedimiento previsto.
2. **Una sola fuente por dato.** El precio vive en el servicio, la tasa en `TasasCambio` y el rango de control en `rangos_control`. Ningún módulo guarda su propia copia.
3. **Cada regla fiscal lleva su artículo.** Como ya hace `providencia_00093.py`: constante, artículo y fuente juntos, para que un auditor lo compruebe sin leer el resto.
4. **El bolívar es la moneda legal.** Se opera en USD, VES o COP, pero todo documento fiscal y todo libro se expresa en bolívares a la tasa BCV del día de la operación, con la divisa como referencia.
5. **El medio de emisión es intercambiable.** El ERP prepara el documento una sola vez; un adaptador lo emite por imprenta digital o máquina fiscal, según la configuración de cada sede.
6. **Nada fiscal sin prueba automática.** Cada cálculo (IVA, IGTF, retenciones, libros) tiene casos en `tests/` antes de llegar a la clínica.

## 2. Estado actual y brechas

La versión 2.6.0 ya cubría buena parte del cálculo fiscal. Lo que falta es el circuito de compras, un maestro de clientes distinto del paciente y la emisión por un medio autorizado.

| Área | Lo que existe (módulo) | Brecha principal |
| --- | --- | --- |
| Servicios | Pruebas, perfiles, `tarifas.py` con precio en cuatro monedas, listas de precios por procedencia | Falta código fiscal de servicio, marca de exento por ítem y vigencia de precios con historial |
| Productos | `inventario.py`: insumos, lotes, movimientos, alertas de mínimo y vencimiento | No hay costo promedio ponderado ni consumo automático por prueba realizada |
| Clientes | Pacientes, `Seguros`, procedencias y convenios | El cliente fiscal (quien recibe la factura) no está separado del paciente; falta RIF validado y tipo de contribuyente |
| Proveedores | `GestorProveedores`: alta, edición y baja | Falta tipo de contribuyente, porcentaje de retención de IVA y concepto ISLR por proveedor |
| Compras | Nada propio; solo `CuentasPorPagar` manual | Falta orden de compra, recepción y registro de la factura del proveedor |
| Cuentas por pagar | `GestorCuentasPorPagar`: crear cuenta y registrar pago | Falta vencimientos, abonos parciales con historial, retenciones aplicadas al pago y antigüedad de saldos |
| Retenciones | `calcular_retencion_iva`, `RetencionesISLR` con tasas del Decreto 1.808 | El sustraendo está en 0 para todos los conceptos; no se generan comprobantes ni los archivos de declaración (TXT de IVA, XML de ISLR) |
| Facturación | `facturacion_fiscal.py`, `factura_pdf.py`, `providencia_00093.py`, `rangos_control.py`, notas de crédito y débito | No hay integración con imprenta digital ni con máquina fiscal; la factura solo se genera como PDF |
| Cobros y caja | Caja, `liquidacion.py`, cuentas por cobrar, cartera de asegurados, corte de adeudado | Falta conciliar retenciones que nos hacen los clientes especiales y cuentas bancarias. Además, el IGTF estaba encendido por defecto y se sumaba solo al cobrar con Divisa o Zelle: un contribuyente ordinario no debe cobrarlo (corregido en 2.7.0) |
| Reportes | Libro de ventas, libro de compras, resumen fiscal, dashboard financiero | Falta el resumen para la declaración de IVA (forma 30), IGTF por período y reportes de gestión por área y procedencia |

`docs/PRD/07_CUMPLIMIENTO_REGULATORIO.md` citaba como vigentes las providencias SNAT/2011/0071 y SNAT/2024/000102, ya derogadas, y listaba el IVA del laboratorio al 16 %. Se corrigió en 2.7.0.

## 3. Marco normativo SENIAT

La norma que manda es la Providencia SNAT/2026/00093, que entra en vigor el 19/04/2027. Permite emitir por el portal o la app del SENIAT, por imprenta digital o proveedor tecnológico autorizado, o por máquina fiscal autorizada. Las formas impresas de imprenta quedan solo para contingencias. El resto de las reglas viene de la Ley de IVA, la del IGTF, el Decreto 1.808 y sus providencias.

| Norma | Qué regula | Efecto en el ERP |
| --- | --- | --- |
| [Providencia SNAT/2026/00093](https://finanzasdigital.com/seniat-levanta-uso-obligatorio-maquinas-fiscales-gaceta-oficial/) (G.O. 43.484, 21/10/2026; vigente desde 19/04/2027) | Contenido de la factura y medios de emisión; deroga SNAT/2011/0071 y SNAT/2024/000102 | Requisitos del art. 8, número de control por rangos (art. 9), leyenda del art. 19, emisión por imprenta digital o máquina fiscal, formato de contingencia. Cambiar de medio se notifica a la Gerencia Regional |
| [Providencia SNAT/2026/00084](https://www.forvismazars.com/ve/es/insights/forvis-mazars-insights/fmi-0726-derogatoria-de-sistemas-homologados) (G.O. 43.435, 12/08/2026) | Deroga la homologación de software de facturación (SNAT/2024/000121) | ANgesLAB no necesita homologarse; siguen exigibles la integridad, la trazabilidad y los requisitos formales del documento |
| Ley de IVA y su Reglamento | Alícuotas, exenciones, libros de compras y ventas, débitos y créditos fiscales | Servicio del laboratorio exento (TSJ, sentencia 1505 de 2003); productos gravados al 16 %; libros mensuales; resumen para la declaración |
| [Providencia SNAT/2025/000054](https://www.forvismazars.com/ve/es/insights/forvis-mazars-insights/fmi-0825-providencia-agentes-de-retencion-del-iva) (G.O. 43.171, vigente desde 01/08/2025) | Agentes de retención de IVA; deroga SNAT/2015/0049 | El laboratorio es ordinario: no retiene IVA a sus proveedores. Solo recibe la retención de sus clientes especiales cuando una factura lleva IVA (venta de productos) |
| Ley del IGTF y [Providencia SNAT/2022/000013](https://www.forvismazars.com/ve/es/insights/forvis-mazars-insights/designacion-de-los-spe) (G.O. 42.339) | 3 % sobre pagos en divisas o cripto recibidos sin intermediación bancaria | Solo los contribuyentes especiales perciben el IGTF. El laboratorio es ordinario y no lo cobra: queda como parámetro apagado, por si cambia su calificación |
| Decreto 1.808 (Reglamento de retenciones de ISLR) | Retenciones de ISLR por concepto, con porcentaje y sustraendo | Retención al pagar honorarios, servicios, alquileres o fletes; comprobante al proveedor; archivo XML de declaración mensual |

El laboratorio es **contribuyente ordinario**. Queda abierto para el contador: el texto exacto de la leyenda del artículo 19 (hoy configurable en `LeyendaProvidencia`). Los requisitos de la 00093 se tomaron de resúmenes profesionales: antes de la puesta en marcha hay que contrastarlos con la Gaceta oficial.

## 4. Maestros

Cuatro maestros alimentan todo lo demás. Ningún documento se emite sin que su servicio o producto, su cliente o su proveedor estén completos y validados.

### 4.1 Servicio

Es lo que el laboratorio vende: una prueba, un perfil o un servicio auxiliar (toma a domicilio, informe urgente, envío a sede). Un perfil es un servicio compuesto: se factura como una línea y su precio no tiene que ser la suma de sus pruebas.

| Campo | Regla |
| --- | --- |
| Código y nombre | Únicos; el nombre es el que se imprime en la factura |
| Tipo | Prueba, perfil o servicio auxiliar |
| Área | Hematología, química, etc.; sirve para los reportes por área |
| Régimen de IVA | Exento por defecto (servicio médico-asistencial); gravado solo si el contador lo indica, con su alícuota |
| Precio base | En USD, con su conversión a VES y COP por la tasa del día (`tarifas.py`) |
| Precios por lista | Por procedencia o convenio, con fecha de vigencia; el cambio de precio no borra el anterior |
| Insumos que consume | Receta: qué reactivos y materiales gasta cada prueba, para descontarlos del inventario |
| Activo | Un servicio inactivo no se puede facturar, pero sigue apareciendo en documentos viejos |

### 4.2 Producto

Es lo que el laboratorio compra y, rara vez, vende: reactivos, materiales, insumos de oficina. Un producto vendido (por ejemplo, un frasco recolector) se factura con IVA al 16 %.

| Campo | Regla |
| --- | --- |
| Código, nombre y unidad | Unidad de compra y de consumo, con su factor (caja de 100 = 100 unidades) |
| Tipo | Reactivo, material, insumo general, producto para la venta |
| Régimen de IVA | Gravado 16 % por defecto; exento o reducido según lo indique el contador |
| Control | Por lote y fecha de vencimiento para reactivos; existencia mínima y máxima |
| Costo | Promedio ponderado, recalculado en cada recepción |
| Proveedores habituales | Uno o varios, con su código de catálogo y último precio |

### 4.3 Cliente

El cliente es quien recibe la factura, que no siempre es el paciente: un paciente puede facturarse a sí mismo, a un familiar, a una empresa o a un seguro.

| Campo | Regla |
| --- | --- |
| Tipo | Persona natural, persona jurídica, aseguradora, clínica en convenio |
| Identificación | RIF (J, G, V, E, P) con dígito verificador, o cédula para personas naturales |
| Razón social y domicilio fiscal | Obligatorios en la factura |
| Tipo de contribuyente | Ordinario, especial o no contribuyente; un cliente especial nos retiene IVA y ese comprobante hay que cargarlo |
| Condición de pago | Contado o crédito con días de plazo y límite |
| Lista de precios | La de su convenio, si tiene |
| Pacientes asociados | Los pacientes que factura este cliente (titular y beneficiarios de un seguro, empleados de una empresa) |

### 4.4 Proveedor

| Campo | Regla |
| --- | --- |
| RIF, razón social y domicilio fiscal | Obligatorios; RIF validado |
| Tipo de persona | Natural residente, natural no residente, jurídica domiciliada o no domiciliada; define la tabla del Decreto 1.808 |
| Tipo de contribuyente | Ordinario o especial; decidiría la retención de IVA si el laboratorio llegara a ser agente |
| Concepto ISLR por defecto | Por ejemplo, honorarios, servicios, alquiler, fletes; se puede cambiar en cada factura |
| Condición de pago | Días de crédito |
| Cuentas bancarias | Para pagarle |
| Productos que suministra | Con su código de catálogo |

## 5. Compras e inventario

Toda compra termina en tres registros a la vez: la entrada al inventario, la línea en el libro de compras y la cuenta por pagar. Se carga una vez, en la recepción de la factura del proveedor, y el resto se deriva.

### 5.1 Circuito de compra

1. **Requisición (opcional).** El área pide insumos; el sistema la propone sola cuando un producto baja de su mínimo.
2. **Orden de compra.** Proveedor, productos, cantidades y precio pactado, en USD o VES. Estados: borrador, aprobada, recibida parcial, recibida, anulada. Solo el rol administrativo la aprueba.
3. **Recepción.** Lo que llegó, por lote y vencimiento. Una recepción parcial deja la orden abierta. La recepción mueve existencias y recalcula el costo promedio.
4. **Factura del proveedor.** Se registra con su número, número de control, fecha, base, IVA y total, tal como viene. El sistema compara contra la orden y la recepción y avisa si el precio o la cantidad difieren.
5. **Retenciones.** El sistema calcula la retención de ISLR que corresponda y emite el comprobante (sección 6). No hay retención de IVA: el laboratorio es ordinario.
6. **Cuenta por pagar.** Queda creada por el neto a pagar, con su vencimiento según la condición del proveedor.

Una compra de servicios (alquiler, mantenimiento de equipos, honorarios) salta los pasos 1 a 3: se registra directo la factura del proveedor con su concepto de gasto.

### 5.2 Inventario

- **Entradas:** recepciones de compra, ajustes positivos, devoluciones de un área.
- **Salidas:** consumo por prueba realizada (descuento automático según la receta del servicio), consumo manual de un área, vencimiento, merma, devolución al proveedor.
- **Ajustes:** solo con motivo y usuario; quedan en `LogAuditoria`.
- **Lotes:** salida por FEFO (primero el que vence antes).
- **Toma física:** conteo por área, comparación con el teórico y ajuste aprobado.
- **Alertas:** bajo mínimo, vencimiento en 30 días (configurable) y lotes vencidos con existencia.
- **Valorización:** a costo promedio ponderado, en USD y en VES a la tasa de cierre.

## 6. Cuentas por pagar y retenciones

Cada factura de proveedor crea una cuenta por pagar por el neto: total menos retención de ISLR. Como contribuyente ordinario, el laboratorio no retiene IVA. Las retenciones no son un descuento del proveedor: son una deuda del laboratorio con el SENIAT y se controlan aparte hasta que se enteran.

### 6.1 Cuentas por pagar

- **Origen:** factura de proveedor, nota de débito del proveedor o gasto recurrente (alquiler, servicios públicos).
- **Estados:** pendiente, abonada, pagada, anulada. Una nota de crédito del proveedor rebaja el saldo.
- **Pagos:** totales o parciales, en USD o VES, desde caja o cuenta bancaria, con referencia. Cada pago guarda la tasa del día y la diferencia en cambio.
- **Programación:** vista de vencimientos de la semana y del mes, para decidir qué pagar.
- **Antigüedad de saldos:** por vencer, 1–30, 31–60, 61–90 y más de 90 días, por proveedor.

### 6.2 Retención de IVA (apagada: el laboratorio es ordinario)

No aplica hoy. Se programa detrás de un parámetro apagado, y se enciende solo si el SENIAT califica al laboratorio como contribuyente especial. En ese caso funcionaría así:

- **Cálculo:** IVA de la factura × 75 %, o × 100 % si el proveedor no está inscrito en el RIF, no muestra el IVA discriminado o la factura no cumple requisitos.
- **Comprobante:** numerado por año, mes y secuencia, uno por factura, entregado al proveedor en PDF.
- **Declaración:** por período quincenal, archivo TXT para el portal del SENIAT y resumen para enterar.

### 6.3 Retención de ISLR (Decreto 1.808)

- **Cálculo:** base × porcentaje del concepto − sustraendo, según el tipo de persona del proveedor. Hoy `RETENCIONES_ISLR` tiene todos los sustraendos en cero: hay que cargar la tabla completa del decreto, con la unidad de cálculo vigente como parámetro, no como constante.
- **Cuándo:** al pagar o abonar en cuenta, lo que ocurra primero. Ser ordinario no exime de retener ISLR: el contador debe confirmar que el laboratorio es agente por su forma jurídica (compañía o firma personal).
- **Comprobante:** uno por pago, entregado al proveedor.
- **Declaración:** archivo XML mensual con el formato del portal del SENIAT.

### 6.4 Retenciones que nos hacen

Cuando un cliente especial (una aseguradora, una empresa) le paga al laboratorio, le retiene IVA si la factura lo tuvo, e ISLR por el servicio. El sistema registra el comprobante recibido contra la factura y la cuenta por cobrar: el saldo del cliente baja y la retención queda como crédito a descontar en la declaración.

## 7. Facturación electrónica

El ERP arma el documento fiscal una sola vez y lo entrega a un **emisor** intercambiable: imprenta digital, máquina fiscal o, en contingencia, forma impresa de imprenta. Cada sede elige su emisor en la configuración. La factura solo existe fiscalmente cuando el emisor la confirma con su número de control.

### 7.1 Documentos

| Documento | Cuándo | Regla clave |
| --- | --- | --- |
| Factura | Al liquidar una solicitud, o al facturar en lote a un cliente a crédito (seguro, convenio) | Una solicitud se factura una sola vez; en lote, una línea por paciente o por servicio, a elección del cliente |
| Nota de crédito | Devolución, descuento posterior, prueba no realizada, error en el monto | Siempre referida a una factura emitida; no puede superar su saldo |
| Nota de débito | Cargo posterior: prueba añadida, diferencia de precio | Siempre referida a una factura emitida |
| Anulación | Error antes de entregar el documento al cliente | Conserva número y número de control, marcada como anulada; nunca se borra |
| Recibo no fiscal | Abono o anticipo antes de facturar | Se aplica a la factura cuando se emite |

### 7.2 Contenido (art. 8 de la SNAT/2026/00093)

`providencia_00093.py` ya concentra los requisitos de contenido. Todo documento lleva:

- Datos del emisor: razón social, RIF, domicilio fiscal y, si aplica, la leyenda de contribuyente formal.
- Datos del cliente: razón social o nombre, RIF o cédula, domicilio.
- Número de documento correlativo y número de control del rango asignado (art. 9).
- Fecha en ocho dígitos (DDMMAAAA) y hora con segundos y a.m./p.m.
- Descripción, cantidad, precio unitario e importe por línea, con la marca (E) en lo exento.
- Base imponible e IVA por alícuota, total exento y total general en bolívares.
- Si se cobra en divisa: monto en divisa y tasa BCV usada. Sin IGTF, porque el laboratorio es ordinario.
- Leyenda del artículo 19 (texto definido por el contador).
- En notas de crédito y débito: número, control y fecha de la factura afectada, y el motivo.

### 7.3 Ciclo de vida

Estados del documento: **borrador → enviado → emitido** (con número de control) o **rechazado** (vuelve a borrador con el motivo). Un emitido solo puede pasar a **anulado** o recibir notas. Si el emisor no responde, el documento queda **pendiente de confirmación** y se reintenta; nunca se emite dos veces el mismo documento: cada envío lleva un identificador único que el emisor reconoce.

### 7.4 Emisores

- **Imprenta digital o proveedor tecnológico.** Adaptador por API: envía el documento, recibe número de control, código de verificación y PDF o enlace. El proveedor contratado es The Factory HKA (detalle en 7.6); el adaptador se escribe genérico para poder cambiar de proveedor sin tocar el resto.
- **Máquina fiscal.** Adaptador para impresora fiscal autorizada conectada a la PC. Emite factura y notas, lee el número que asigna la máquina, y saca reporte X y cierre Z diario. El cierre Z se guarda y se cuadra contra el libro de ventas.
- **Contingencia.** Si se cae el emisor principal, el usuario autorizado activa la contingencia: se usan formas impresas de imprenta autorizada, cuyo rango también se carga en `rangos_control`. Al volver, esos documentos se registran en el sistema y quedan marcados como de contingencia.

### 7.5 Entrega y conservación

El cliente recibe el PDF por correo o WhatsApp (`whatsapp_envio.py`) y puede pedirlo impreso. El sistema guarda el documento, la respuesta del emisor y su PDF durante el plazo de conservación del Código Orgánico Tributario, con copia en los respaldos.

### 7.6 Integración con The Factory HKA

HKA expone una API REST con token: ANgesLAB se autentica, envía el documento en JSON y recibe el número de control que HKA asigna de su rango. Con HKA, `rangos_control` deja de llevar la cuenta del número de control de la factura digital: se guarda el `rangoAsignado` que devuelve cada emisión y se usa solo para avisar cuando queda poco.

| Método (POST) | Uso en ANgesLAB |
| --- | --- |
| `/api/Autenticacion` | Usuario y clave del contrato; devuelve un token válido 12 horas. Se renueva solo al vencer o ante un 401 |
| `/api/Emision` | Envía el `documentoElectronico` (encabezado, comprador, totales, ítems, otra moneda). Devuelve serie, número de documento, número de control, fecha y hora de asignación y rango |
| `/api/Anular` | Serie, tipo y número, motivo, fecha y hora de anulación |
| `/api/Descarga` | Trae el PDF o XML del documento emitido, para guardarlo y enviarlo al cliente |
| Envío y rastreo de correo | HKA puede enviar el documento al correo del cliente y reportar si llegó |

**Correspondencia con el modelo de datos.** Cada `DocumentosFiscales` guarda la serie, el número de control, la fecha y hora de asignación y la respuesta completa de HKA. Al enviar, `transaccionId` lleva el identificador único de ANgesLAB: si se pierde la respuesta, antes de reenviar se consulta el estado del documento, y así no se duplica la factura. El wiki público no documenta un método de consulta de estado: hay que confirmarlo con HKA.

**Mapeo fiscal del laboratorio.** Las pruebas van como servicio exento; los productos vendidos, gravados al 16 %; el comprador, con RIF o cédula y domicilio desde el maestro de clientes; `totalesOtraMoneda`, con el monto en USD y la tasa BCV. El IGTF va siempre en cero, porque el laboratorio es ordinario.

**Ambientes.** Se programa y se prueba contra `demoemisionv2.thefactoryhka.com.ve`, y se pasa a producción con las credenciales del contrato. La configuración del emisor guarda el ambiente (prueba o producción), la URL, el usuario y la clave cifrada.

**Lo que falta pedir a HKA:** credenciales del ambiente demo, URL de producción, catálogos de tipos de documento, formas de pago y tipos de identificación, y la tabla de códigos de error. La documentación pública de su wiki los muestra incompletos.

## 8. Cuentas por cobrar y caja

La cadena del cobro ya existe y se respeta: procedencia → tarifa → solicitud → `liquidacion.py` → caja o cuenta por cobrar. El ERP le añade la factura como paso obligatorio y separa al cliente del paciente.

### 8.1 Cuentas por cobrar

- **Origen:** factura a crédito, o solicitud de un paciente asegurado pendiente de facturar al seguro.
- **Cartera de asegurados:** se mantiene el control paciente por paciente de `desembolsos_clinica.py`; cada desembolso se aplica a pacientes concretos.
- **Cobros:** totales o parciales, en cualquier moneda, con la retención recibida (sección 6.4) como forma de pago adicional.
- **Diferencial cambiario:** si se facturó en VES con referencia en USD y se cobra días después, la diferencia se emite como nota de débito o de crédito, según la política que fije el contador.
- **Antigüedad y estados de cuenta:** por cliente, con envío en PDF.

### 8.2 Caja y bancos

- **Caja:** apertura, movimientos y cierre por usuario y turno (ya existe). El cierre se cuadra por forma de pago: efectivo VES, efectivo USD, punto de venta, pago móvil, transferencia, Zelle.
- **Cuentas bancarias:** cada cobro y pago no en efectivo va a una cuenta. Conciliación mensual contra el estado de cuenta importado en Excel o CSV.
- **Depósitos y traspasos:** de caja a banco, entre cuentas, con su comprobante.
- **IGTF:** no se cobra, porque el laboratorio es ordinario. Desde la versión 2.7.0 el programa solo lo calcula si el laboratorio es especial y además lo tiene activado; un ordinario nunca suma el 3 %.

## 9. Reportes

Todo reporte sale en pantalla, PDF y Excel, filtrable por fechas y sede. Los fiscales usan solo documentos emitidos y respetan el período; un documento de un período cerrado no cambia el reporte de ese período.

### 9.1 Fiscales

| Reporte | Frecuencia | Contenido |
| --- | --- | --- |
| Libro de ventas | Mensual | Una línea por documento: fecha, RIF y nombre del cliente, número, control, documento afectado, total, exento, base e IVA por alícuota, retención recibida |
| Libro de compras | Mensual | Igual, por factura de proveedor, con el IVA retenido y el número de comprobante |
| Resumen para la declaración de IVA | Mensual | Débitos, créditos, retenciones soportadas y excedentes, en el orden de la planilla del SENIAT |
| Retenciones de IVA practicadas | Quincenal | No aplica mientras el laboratorio sea ordinario |
| Retenciones de ISLR practicadas | Mensual | Detalle y archivo XML para el portal |
| IGTF percibido | Quincenal | No aplica mientras el laboratorio sea ordinario |
| Cuadre de máquina fiscal | Diario | Cierre Z contra ventas del sistema, con diferencias |
| Control de números de control | A pedido | Rangos cargados, usados, anulados y disponibles; aviso cuando quede menos del 10 % |

### 9.2 De gestión

| Reporte | Para qué sirve |
| --- | --- |
| Ventas por área, servicio y procedencia | Qué se vende y de dónde vienen los pacientes |
| Ventas por convenio y aseguradora | Cuánto pesa cada convenio y cuánto debe |
| Antigüedad de cuentas por cobrar y por pagar | Qué cobrar y qué pagar primero |
| Flujo de caja proyectado | Cobros y pagos esperados en las próximas cuatro semanas |
| Costo por prueba | Insumos consumidos según receta frente al precio cobrado |
| Compras por proveedor y producto | Concentración de compras y variación de precios |
| Inventario valorizado y vencimientos | Dinero inmovilizado y pérdidas por vencimiento |
| Gastos por categoría | Estructura de gastos del mes frente al anterior |
| Estado de resultados simple | Ventas menos costo de insumos menos gastos, por mes |

## 10. Modelo de datos

Se crean 12 tablas y se amplían 8, sobre la base Access actual. Todos los cambios se aplican con migraciones idempotentes (como ya hacen `asegurar_tabla` y `asegurar_esquema`), para que una instalación existente se actualice sin perder datos.

| Tabla | Estado | Campos principales |
| --- | --- | --- |
| `Clientes` | Nueva (2.7.0) | Tipo, RIF o cédula, razón social, domicilio fiscal, tipo de contribuyente, condición de pago, lista de precios |
| `ClientePacientes` | Nueva (2.7.0) | Cliente, paciente, parentesco o vínculo, por defecto |
| `Proveedores` | Ampliada (2.7.0) | Tipo de persona, tipo de contribuyente, % retención IVA, concepto ISLR, días de crédito |
| `Pruebas` (servicios) | Ampliada (2.7.0) | Régimen de IVA, alícuota |
| `RecetaServicio` | Nueva (2.8.0) | Prueba, producto, cantidad por prueba, fecha desde la que se descuenta |
| `LotesProducto` | Nueva (2.8.0) | Producto, lote, vencimiento, cantidad inicial y actual, costo, compra de origen |
| `Insumos` / `Productos` | Ampliar | Tipo, unidad de compra y consumo, factor, régimen de IVA, costo promedio |
| `OrdenesCompra` y `DetalleOrdenCompra` | Nuevas (2.8.0) | Proveedor, estado, moneda, líneas con cantidad pedida y recibida |
| `Compras` y `DetalleCompras` (ya venían en la base del instalador) | Ampliadas (2.8.0) | Factura del proveedor con la recepción: número, control, fecha, exento, base, IVA, total, moneda y tasa, orden de origen; líneas con lote, vencimiento y costo en USD |
| `Pagos` (ya venía en la base del instalador) | Ampliada (2.8.0) | Historial de abonos a cuentas por pagar |
| `RetencionesIVA` | Nueva | Factura de proveedor, comprobante, período, %, monto, fecha de enteramiento |
| `RetencionesISLR` | Ampliar | Concepto, tipo de persona, sustraendo, comprobante, pago asociado |
| `RetencionesRecibidas` | Nueva | Factura propia, cliente, tipo (IVA o ISLR), comprobante, monto |
| `CuentasPorPagar` | Ampliada (2.8.0) | Proveedor y compra de origen; el historial de abonos está en `Pagos` |
| `DocumentosFiscales` | Nueva (reemplaza la factura actual) | Tipo, número, control, cliente, documento afectado, estado, emisor, identificador de envío, respuesta del emisor, totales en VES y divisa, tasa |
| `EmisoresFiscales` | Nueva | Sede, tipo (imprenta digital, máquina fiscal, contingencia), parámetros de conexión, activo |
| `CierresZ` | Nueva | Máquina, fecha, número de cierre, totales leídos, diferencia con el sistema |
| `PeriodosFiscales` | Nueva | Mes, estado (abierto o cerrado), quién y cuándo lo cerró |

Las tablas de solicitudes, caja, cuentas por cobrar, tasas de cambio, rangos de control y auditoría se mantienen como están y se enlazan por clave a las nuevas.

## 11. Roles, controles y auditoría

Nadie puede cerrar sola una operación que mueve dinero: quien la registra no es quien la aprueba. Los roles se montan sobre `Roles`, `UsuarioRol` y `PermisosModulo`, que ya existen.

| Rol | Puede | No puede |
| --- | --- | --- |
| Recepción / caja | Liquidar solicitudes, facturar al contado, cobrar, abrir y cerrar su caja | Anular documentos, emitir notas, tocar precios |
| Facturación | Facturar a crédito y en lote, emitir notas de crédito y débito, registrar retenciones recibidas | Aprobar compras, pagar proveedores |
| Compras / almacén | Crear órdenes, registrar recepciones, ajustar inventario con motivo | Aprobar sus propias órdenes, pagar |
| Administración | Aprobar órdenes y anulaciones, pagar proveedores, emitir comprobantes de retención, cerrar períodos | Borrar documentos emitidos (nadie puede) |
| Contador (solo lectura) | Ver y exportar libros, retenciones y reportes | Modificar nada |

### Controles

- **Período cerrado:** cerrado un mes, no se registra ni se modifica nada con fecha de ese mes. Reabrirlo exige rol de administración y queda en la auditoría.
- **Numeración sin huecos:** el número de documento y el de control se toman en la misma transacción que guarda el documento; si falla, no se consume el número.
- **Precio bloqueado:** el precio facturado sale de la tarifa vigente; cambiarlo en la factura exige permiso y motivo.
- **Doble verificación de RIF:** formato y dígito verificador antes de guardar un cliente o proveedor.
- **Auditoría:** toda creación, anulación, ajuste, cambio de precio y cambio de configuración fiscal queda en `LogAuditoria` con usuario, fecha, valor anterior y nuevo.

## 12. Plan de implementación

Cinco fases de unas seis semanas cada una, en el orden en que dependen entre sí: sin maestros no hay compras, sin compras no hay retenciones, y la emisión necesita todo lo anterior. La fase 5 deja tres semanas de piloto antes del 19/04/2027.

| Fase | Fechas | Contenido | Estado |
| --- | --- | --- | --- |
| 1 · Maestros | nov–dic 2026 | Clientes separados del paciente, proveedores fiscales, servicios con régimen de IVA, RIF validado, PRD corregido | Entregada en 2.7.0 |
| 2 · Compras e inventario | dic 2026–ene 2027 | Órdenes, recepciones, facturas de proveedor, costo promedio, consumo por receta, cuentas por pagar | Entregada en 2.8.0 |
| 3 · Retenciones | ene–feb 2027 | ISLR con sustraendo, comprobantes y archivo XML; retenciones de IVA e ISLR recibidas de clientes | Pendiente |
| 4 · Emisión fiscal | feb–mar 2027 | Documentos fiscales con ciclo de vida, adaptador de máquina fiscal, de imprenta digital (HKA) y contingencia | Pendiente |
| 5 · Reportes y piloto | mar–abr 2027 | Libros, resumen de IVA, reportes de gestión, cierre de período y piloto en el laboratorio | Pendiente |
| **19/04/2027** | | Entra en vigor la SNAT/2026/00093: todo en producción | |

Cada fase se entrega como una versión etiquetada en `main`, con sus pruebas, y solo pasa a la siguiente si cumple su criterio:

1. **Maestros:** se puede facturar a un cliente distinto del paciente, y no se guarda ningún RIF inválido. Entregada en la versión 2.7.0 (08/11/2026): maestros de clientes y proveedores con sus pantallas, RIF con dígito verificador y régimen de IVA por prueba. Falta que la factura use el cliente: eso entra con la emisión (fase 4).
2. **Compras e inventario:** una compra registrada aparece en inventario, libro de compras y cuentas por pagar con los mismos montos. Entregada en la versión 2.8.0 (08/11/2026): órdenes con aprobación por otro usuario, factura de proveedor que mueve inventario por lote (FEFO, costo promedio), libro de compras y cuenta por pagar a la vez; recetas por prueba con descuento automático; pagos con historial y antigüedad de saldos. La recepción y la factura se registran en un solo paso, que es como llega la mercancía al laboratorio. También se corrigió que la pantalla de Proveedores no funcionaba con la base del instalador (sin columna RIF) y que el libro de compras suponía IVA al 16 % en todo monto.
3. **Retenciones:** los comprobantes y archivos de un mes de prueba coinciden con el cálculo manual del contador.
4. **Emisión fiscal:** se emiten factura, nota de crédito y nota de débito por cada emisor configurado, y una caída simulada pasa a contingencia sin duplicar documentos.
5. **Reportes y piloto:** un mes completo del laboratorio cuadra entre libros, caja, bancos y cierres Z.

### Decisiones pendientes

- [ ] Confirmar con el contador que el laboratorio es agente de retención de ISLR según su forma jurídica.
- [ ] Pedir a The Factory HKA credenciales del ambiente demo, URL de producción, catálogos y tabla de códigos de error.
- [ ] Elegir el modelo de máquina fiscal que se va a soportar primero.
- [ ] Obtener del contador el texto de la leyenda del art. 19 y validar los requisitos contra la Gaceta 43.484.
- [ ] Definir la política de diferencial cambiario en cuentas por cobrar.

### Fuentes

- [Finanzas Digital: SENIAT levanta el uso obligatorio de máquinas fiscales (SNAT/2026/00093)](https://finanzasdigital.com/seniat-levanta-uso-obligatorio-maquinas-fiscales-gaceta-oficial/)
- [Finanzas Digital: la Providencia 0093 impone la facturación digital](https://finanzasdigital.com/providencia-0093-impone-facturacion-digital-venezuela-avdt/)
- [Forvis Mazars FMI 07-26: derogatoria de sistemas homologados (SNAT/2026/00084)](https://www.forvismazars.com/ve/es/insights/forvis-mazars-insights/fmi-0726-derogatoria-de-sistemas-homologados)
- [Forvis Mazars FMI 08-25: agentes de retención del IVA (SNAT/2025/000054)](https://www.forvismazars.com/ve/es/insights/forvis-mazars-insights/fmi-0825-providencia-agentes-de-retencion-del-iva)
- [Forvis Mazars: designación de los SPE como agentes de percepción del IGTF (SNAT/2022/000013)](https://www.forvismazars.com/ve/es/insights/forvis-mazars-insights/designacion-de-los-spe)
- [Wiki The Factory HKA Venezuela: manual de integración REST](https://wiki.thefactoryhka.com.ve/doku.php?id=manual_de_integracion_venezuela)
- [Wiki The Factory HKA Venezuela: método de emisión](https://wiki.thefactoryhka.com.ve/doku.php?id=restapiemision)
- [Wiki The Factory HKA Venezuela: autenticación](https://wiki.thefactoryhka.com.ve/doku.php?id=restapiautenticacionvenezuela)

# -*- coding: utf-8 -*-
"""
================================================================================
PROCEDENCIA DE LA SOLICITUD
================================================================================
Decide como se liquida una solicitud segun por donde ingresa el paciente.

Hay dos formas de cobrar y no deben mezclarse:

  CONTADO   El paciente paga en el momento. El dinero entra a la caja del dia.
            Si paga solo una parte, a la caja entra lo abonado y el resto
            queda como cuenta por cobrar a su nombre.

  CREDITO   Ingresa por un seguro. El laboratorio presta el servicio hoy y
            cobra despues, cuando el seguro liquide. NO entra dinero a la
            caja: se registra una cuenta por cobrar por el total.

Registrar en caja lo que todavia no se ha cobrado descuadra el arqueo del dia
y hace figurar como ingreso un dinero que aun no existe.

Para cambiar la clasificacion de una procedencia basta editar el conjunto
PROCEDENCIAS_CREDITO. No hay reglas de cobro repartidas por el resto del
codigo: todo pasa por aqui.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

# Procedencias que se cobran al seguro (no generan ingreso de caja).
# Deben coincidir con los valores del combo "Procedencia" de Nueva Solicitud.
PROCEDENCIAS_CREDITO = {
    'Asegurado',
    'Hospitalizado Asegurado',
    'Emergencia Asegurado',
    'Cirugia Asegurado',
}

# Valores que ofrece el combo de la pantalla de solicitud.
PROCEDENCIAS = [
    'Ambulatorio',
    'Hospitalizado Particular',
    'Hospitalizado Asegurado',
    'Emergencia Particular',
    'Emergencia Asegurado',
    'Cirugia Particular',
    'Cirugia Asegurado',
    'Asegurado',
]

# ---------------------------------------------------------------------------
# Areas de servicio de la clinica
# ---------------------------------------------------------------------------
# Una cosa es QUIEN paga (particular o seguro) y otra DE DONDE viene el
# paciente. El corte de adeudado que se le reporta a la clinica va por area,
# con el asegurado y el particular separados dentro de cada una, asi que las
# dos clasificaciones tienen que poder consultarse por separado.

AREA_HOSPITALIZACION = 'Hospitalizacion'
AREA_EMERGENCIA = 'Emergencia'
AREA_CIRUGIA = 'Cirugia'
AREA_AMBULATORIO = 'Ambulatorio'

# Areas que entran en el corte que se le presenta a la clinica. El paciente
# de calle no forma parte de ese corte.
AREAS_CLINICA = (AREA_HOSPITALIZACION, AREA_EMERGENCIA, AREA_CIRUGIA)

_AREAS_POR_PROCEDENCIA = {
    'hospitalizado particular': AREA_HOSPITALIZACION,
    'hospitalizado asegurado': AREA_HOSPITALIZACION,
    'emergencia particular': AREA_EMERGENCIA,
    'emergencia asegurado': AREA_EMERGENCIA,
    'cirugia particular': AREA_CIRUGIA,
    'cirugia asegurado': AREA_CIRUGIA,
    'ambulatorio': AREA_AMBULATORIO,
    'asegurado': AREA_AMBULATORIO,
}


def area_servicio(tipo_servicio):
    """
    De donde viene el paciente: hospitalizacion, emergencia, cirugia o
    ambulatorio. Es independiente de quien pague.

    'Asegurado' a secas se cuenta como ambulatorio: es el asegurado que
    llega por su pie, sin pasar por ninguna de las areas de la clinica.

    Una procedencia que no se reconozca cae en ambulatorio, para que nunca
    se cuele en el corte de la clinica algo que no le corresponde cobrar.
    """
    return _AREAS_POR_PROCEDENCIA.get(_normalizar(tipo_servicio),
                                      AREA_AMBULATORIO)


def detectar_procedencia(texto):
    """
    Encuentra la procedencia nombrada dentro de un texto libre.

    Las cuentas por cobrar creadas antes de que existiera la columna
    TipoProcedencia llevan la procedencia dentro de las observaciones, con
    la forma "Asegurado - Emergencia Asegurado - Solicitud S-1". Sin esto,
    esas cuentas no se reconocerian y quedarian fuera del corte que se le
    cobra a la clinica.

    Devuelve '' si no reconoce ninguna.
    """
    objetivo = _normalizar(texto)
    if not objetivo:
        return ''
    # De la mas larga a la mas corta: "Asegurado" esta contenido dentro de
    # "Emergencia Asegurado", y quedarse con la corta daria el area
    # equivocada.
    for candidata in sorted(PROCEDENCIAS, key=len, reverse=True):
        if _normalizar(candidata) in objetivo:
            return candidata
    return ''


def es_area_clinica(tipo_servicio):
    """True si la solicitud entra en el corte que se le reporta a la clinica."""
    return area_servicio(tipo_servicio) in AREAS_CLINICA

# Dias de plazo para cobrarle al seguro.
# Decimales con los que se escribe cualquier importe en la base.
#
# Cuatro y no dos, por dos razones que apuntan al mismo sitio: el campo
# CURRENCY de Access guarda exactamente cuatro, y los precios viven en
# dolares, donde un centavo son 31 pesos. Redondear a dos hacia que una
# solicitud de 150.000 COP abriera la cuenta por cobrar en 150.009, de modo
# que lo que se le reclamaba a la clinica no cuadraba con lo facturado.
#
# Las cifras que solo se muestran o se imprimen si van a dos: ahi el que lee
# quiere pesos y centimos, no diezmilesimas de dolar.
DECIMALES_IMPORTE = 4

DIAS_CREDITO_SEGURO = 30


def _normalizar(tipo_servicio):
    """Deja el texto comparable: sin espacios de sobra y con mayusculas fijas."""
    return ' '.join(str(tipo_servicio or '').split()).strip().lower()


def es_credito(tipo_servicio):
    """
    True si la solicitud se le cobra a un seguro y por tanto NO entra
    dinero a la caja al registrarla.

    Se compara normalizado para que un espacio de mas o una diferencia de
    mayusculas no haga que una solicitud asegurada entre como efectivo.
    """
    objetivo = _normalizar(tipo_servicio)
    return any(_normalizar(p) == objetivo for p in PROCEDENCIAS_CREDITO)


def es_contado(tipo_servicio):
    """True si el paciente paga en el momento (particular/efectivo)."""
    return not es_credito(tipo_servicio)


def etiqueta_cobro(tipo_servicio):
    """Texto corto para mostrar al usuario como se va a liquidar."""
    return 'Credito (seguro)' if es_credito(tipo_servicio) else 'Contado'


def calcular_cobro(total, abonado, tipo_servicio, hay_documento=True):
    """
    Reparte el importe de una solicitud entre lo cobrado y lo que queda a deber.

    Devuelve la tupla (cobrado, saldo). Ver DECIMALES_IMPORTE: se
    redondean con la misma precision con la que se guardan, para que la
    cuenta por cobrar diga exactamente lo que dice la solicitud.

    Lo abonado se toma al pie de la letra: si dice cero, se cobro cero. La
    pantalla rellena esa casilla con el total en cuanto la procedencia es de
    contado, de modo que el cero solo aparece cuando alguien lo escribe a
    proposito. Antes se interpretaba un cero como pago completo para que un
    descuido no dejara la caja vacia, pero eso hacia que el mismo valor
    significara dos cosas distintas y que no hubiera forma de registrar a un
    particular que se lleva el examen sin pagar.

    Sin documento emitido no hay cobro: un recibo o una factura son el
    comprobante de que el dinero entro, y sin comprobante no se puede
    asentar un ingreso de caja. Lo que no se cobra queda como saldo.

    Es el unico calculo de cobro del sistema: el recibo, la caja y la cuenta
    por cobrar salen todos de aqui, de modo que no puedan contradecirse.
    """
    try:
        total = float(total or 0)
    except (TypeError, ValueError):
        total = 0.0
    try:
        abonado = float(abonado or 0)
    except (TypeError, ValueError):
        abonado = 0.0

    # Un importe negativo no tiene sentido en una solicitud y colandose hasta
    # la caja se anotaria como un ingreso en negativo, es decir una salida de
    # dinero sin respaldo.
    total = max(0.0, total)
    abonado = max(0.0, abonado)

    if es_credito(tipo_servicio) or not hay_documento:
        cobrado = 0.0
    else:
        cobrado = min(abonado, total)

    return (round(cobrado, DECIMALES_IMPORTE),
            round(total - cobrado, DECIMALES_IMPORTE))


def descripcion_cuenta(tipo_servicio, numero_solicitud=''):
    """
    Observacion que queda escrita en la cuenta por cobrar, para que en
    cartera se sepa de donde viene la deuda sin abrir la solicitud.
    """
    ref = f" {numero_solicitud}".rstrip()
    if es_credito(tipo_servicio):
        return f"Asegurado - {tipo_servicio} - Solicitud{ref}"
    return f"Saldo pendiente - {tipo_servicio} - Solicitud{ref}"

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
}

# Valores que ofrece el combo de la pantalla de solicitud.
PROCEDENCIAS = [
    'Ambulatorio',
    'Hospitalizado Particular',
    'Hospitalizado Asegurado',
    'Emergencia Particular',
    'Emergencia Asegurado',
    'Asegurado',
]

# Dias de plazo para cobrarle al seguro.
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

    Devuelve la tupla (cobrado, saldo), ambos redondeados a dos decimales.

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

    return round(cobrado, 2), round(total - cobrado, 2)


def descripcion_cuenta(tipo_servicio, numero_solicitud=''):
    """
    Observacion que queda escrita en la cuenta por cobrar, para que en
    cartera se sepa de donde viene la deuda sin abrir la solicitud.
    """
    ref = f" {numero_solicitud}".rstrip()
    if es_credito(tipo_servicio):
        return f"Asegurado - {tipo_servicio} - Solicitud{ref}"
    return f"Saldo pendiente - {tipo_servicio} - Solicitud{ref}"

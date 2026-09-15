# -*- coding: utf-8 -*-
"""
================================================================================
LIQUIDACION DE LA SOLICITUD
================================================================================
Unico sitio donde se decide que pasa con el dinero de una solicitud: cuanto
entra a la caja del dia y cuanto queda por cobrar.

La cadena completa del cobro es esta, y cada eslabon hereda del anterior:

    procedencia  ->  tarifa       (tarifas.py: que precio se aplica)
                 ->  DetalleSolicitudes.PrecioUnitario
                 ->  Solicitudes.MontoTotal
                 ->  liquidacion  (aqui: caja o cuenta por cobrar)
                 ->  CuentasPorCobrar
                 ->  corte de adeudado / cartera de asegurados

Como todo lo posterior hereda del precio guardado en el detalle, el precio
tiene que quedar bien AL GUARDAR. Despues ya no se recalcula: la factura, el
recibo y el corte leen lo que hay.

Esta logica vivia dentro de la ventana principal, donde no se podia probar.
Al traerla aqui se pudo cerrar el agujero que tenia: abria una cuenta por
cobrar nueva cada vez que se la llamaba, de modo que agregarle pruebas a una
solicitud de clinica dejaba dos cuentas y duplicaba la deuda.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime, timedelta

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.liquidacion')
except Exception:  # pragma: no cover
    import logging
    _log = logging.getLogger('angeslab.liquidacion')

try:
    from modulos.procedencia import (DIAS_CREDITO_SEGURO, calcular_cobro,
                                     descripcion_cuenta, es_credito)
except Exception:  # pragma: no cover
    DIAS_CREDITO_SEGURO = 30

    def es_credito(_tipo):
        return False

    def calcular_cobro(total, abonado, _tipo, hay_documento=True):
        try:
            total = max(0.0, float(total or 0))
        except (TypeError, ValueError):
            total = 0.0
        cobrado = total if hay_documento else 0.0
        return round(cobrado, 2), round(total - cobrado, 2)

    def descripcion_cuenta(tipo, numero=''):
        return "Solicitud " + str(numero)


def _fecha_access(momento):
    return momento.strftime('#%m/%d/%Y %H:%M:%S#')


def _txt(valor, limite=255):
    return str(valor if valor is not None else '').replace("'", "''")[:limite]


def _f(valor):
    try:
        return float(valor if valor is not None else 0)
    except (TypeError, ValueError):
        return 0.0


class Liquidador:
    """Asienta el cobro de una solicitud: caja y/o cuenta por cobrar."""

    def __init__(self, db, usuario=None):
        self.db = db
        self.usuario = usuario or {}
        self._columnas = {}

    # ------------------------------------------------------------- esquema

    def _tiene_columna(self, tabla, columna):
        clave = tabla + '.' + columna
        if clave not in self._columnas:
            try:
                self.db.query_one("SELECT TOP 1 " + columna + " FROM " + tabla)
                self._columnas[clave] = True
            except Exception:
                self._columnas[clave] = False
        return self._columnas[clave]

    # --------------------------------------------------------------- cuenta

    def cuenta_de_solicitud(self, sol_id):
        """
        La cuenta por cobrar de esa solicitud, si ya existe.

        Es lo que evita abrir una segunda cuenta al volver a liquidar la
        misma solicitud, por ejemplo al agregarle pruebas.
        """
        if not self._tiene_columna('CuentasPorCobrar', 'SolicitudID'):
            return None
        try:
            return self.db.query_one(
                "SELECT * FROM [CuentasPorCobrar] "
                "WHERE SolicitudID=" + str(int(sol_id)))
        except Exception:
            return None

    def _guardar_cuenta(self, sol_id, numero, saldo, tipo_servicio):
        """
        Deja la cuenta por cobrar acorde con el saldo actual.

        Si la solicitud ya tenia cuenta se ACTUALIZA; solo se crea una nueva
        cuando no habia. Lo ya abonado se respeta: una solicitud a la que se
        le agregan pruebas despues de que la clinica abonara algo sube su
        deuda, no se reinicia.

        Devuelve (accion, cuenta_id) con accion 'creada', 'actualizada' o
        'sin_cambio'.
        """
        existente = self.cuenta_de_solicitud(sol_id)
        ahora = datetime.now()

        if existente:
            cuenta_id = existente.get('CuentaCobrarID')
            abonado = _f(existente.get('MontoCobrado'))
            nuevo_saldo = round(max(0.0, saldo - abonado), 2)
            if (abs(_f(existente.get('MontoOriginal')) - saldo) < 0.005
                    and abs(_f(existente.get('SaldoPendiente')) - nuevo_saldo) < 0.005):
                return 'sin_cambio', cuenta_id

            estado = 'Cobrada' if nuevo_saldo <= 0.001 else (
                'Parcial' if abonado > 0.001 else 'Pendiente')
            sets = ["MontoOriginal=" + str(round(saldo, 2)),
                    "SaldoPendiente=" + str(nuevo_saldo),
                    "Estado='" + estado + "'"]
            if self._tiene_columna('CuentasPorCobrar', 'FechaLiberacion'):
                sets.append("FechaLiberacion="
                            + (_fecha_access(ahora) if nuevo_saldo <= 0.001 else 'Null'))
            try:
                self.db.execute("UPDATE [CuentasPorCobrar] SET " + ", ".join(sets)
                                + " WHERE CuentaCobrarID=" + str(int(cuenta_id)))
                _log.info("Cuenta %s de la solicitud %s actualizada a %.2f",
                          cuenta_id, numero, saldo)
                return 'actualizada', cuenta_id
            except Exception as e:
                _log.error("No se pudo actualizar la cuenta %s: %s", cuenta_id, e)
                raise

        # No habia cuenta: crearla
        paciente = self.db.query_one(
            "SELECT p.PacienteID, p.Nombres & ' ' & p.Apellidos AS NombreCompleto "
            "FROM Solicitudes s LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID "
            "WHERE s.SolicitudID = " + str(int(sol_id)))
        pac_id = (paciente or {}).get('PacienteID') or 'Null'
        nombre = _txt((paciente or {}).get('NombreCompleto') or '', 200).strip() \
            or 'Sin nombre'

        credito = es_credito(tipo_servicio)
        # El seguro paga a plazo; el saldo de un particular se considera
        # vencido de inmediato, porque se esperaba el pago en el mostrador.
        vence = ahora + timedelta(days=DIAS_CREDITO_SEGURO if credito else 0)
        obs = _txt(descripcion_cuenta(tipo_servicio, numero))

        cols = ["PacienteID", "NombrePaciente", "FechaEmision", "FechaVencimiento",
                "MontoOriginal", "MontoCobrado", "SaldoPendiente", "DiasVencida",
                "Estado", "Observaciones"]
        vals = [str(pac_id), "'" + nombre + "'", _fecha_access(ahora),
                vence.strftime('#%m/%d/%Y#'), str(round(saldo, 2)), "0",
                str(round(saldo, 2)), "0", "'Pendiente'", "'" + obs + "'"]

        # En bases antiguas estas columnas pueden no existir todavia; se
        # omiten en vez de romper el guardado de la solicitud.
        if self._tiene_columna('CuentasPorCobrar', 'SolicitudID'):
            cols.insert(0, "SolicitudID")
            vals.insert(0, str(int(sol_id)))
        if self._tiene_columna('CuentasPorCobrar', 'TipoProcedencia'):
            cols.append("TipoProcedencia")
            vals.append("'" + _txt(tipo_servicio, 50) + "'")

        self.db.execute("INSERT INTO [CuentasPorCobrar] (" + ", ".join(cols)
                        + ") VALUES (" + ", ".join(vals) + ")")
        _log.info("Cuenta por cobrar creada para la solicitud %s: %.2f",
                  numero, saldo)
        return 'creada', None

    # ------------------------------------------------------------ caja

    def _asentar_en_caja(self, monto, numero, doc_result, forma_pago_texto):
        """Devuelve (ok, aviso). El aviso es lo que hay que mostrar si algo falla."""
        try:
            from modulos.modulo_administrativo import GestorCajaChica
        except ImportError:
            return False, ("El módulo administrativo no está disponible: "
                           "el ingreso no se registró en caja.")

        try:
            gestor = GestorCajaChica(self.db)
            caja = gestor.obtener_caja_abierta()
            if not caja:
                # Antes esto se ignoraba en silencio y el dinero no quedaba
                # registrado en ningun lado.
                _log.warning("Solicitud %s: cobro de %.2f sin caja abierta",
                             numero, monto)
                return False, (f"No hay una caja abierta: el ingreso de "
                               f"{monto:,.2f} NO quedó registrado. Ábrala en el "
                               f"módulo administrativo y regístrelo a mano.")

            texto = forma_pago_texto or 'Efectivo'
            fp = self.db.query_one(
                "SELECT FormaPagoID FROM [FormasPago] WHERE Nombre LIKE '%"
                + _txt(texto, 40) + "%' AND Activo=True")
            doc = doc_result or {}
            doc_num = doc.get('numero_recibo') or doc.get('numero_factura') or ''
            doc_tipo = 'Recibo' if doc.get('numero_recibo') else 'Factura'

            gestor.registrar_movimiento(caja['CajaID'], {
                'Tipo': 'Ingreso',
                'Categoria': 'Pago de solicitud',
                'Descripcion': (doc_tipo + ' ' + doc_num).strip(),
                'Monto': monto,
                'FormaPagoID': fp['FormaPagoID'] if fp else 'Null',
                'Referencia': doc_num or numero,
                'FacturaID': doc.get('factura_id', 'Null'),
            }, self.usuario.get('UsuarioID', 1))
            return True, ''
        except Exception as e:
            _log.error("Solicitud %s: fallo al registrar en caja: %s", numero, e)
            return False, f"No se pudo registrar el ingreso en caja: {e}"

    # ------------------------------------------------------------ principal

    def liquidar(self, sol_id, numero, total, abonado, tipo_servicio,
                 doc_result=None, forma_pago_texto=None, registrar_en_caja=True):
        """
        Asienta el cobro de una solicitud.

        Reglas, que son las mismas para toda la aplicacion:

          - Asegurado: no toca la caja; el total queda por cobrar.
          - Sin documento emitido: tampoco hay ingreso, porque el recibo o la
            factura son el comprobante de que el dinero entro.
          - De contado con documento: entra lo realmente abonado, y lo que
            falte queda por cobrar.

        Se puede llamar varias veces sobre la misma solicitud (al agregarle
        pruebas, por ejemplo): la cuenta por cobrar se actualiza en vez de
        duplicarse.

        Devuelve un dict con lo asentado.
        """
        hay_documento = bool(doc_result and doc_result.get('exito'))
        credito = es_credito(tipo_servicio)
        cobrado, saldo = calcular_cobro(total, abonado, tipo_servicio,
                                        hay_documento)

        resumen = {
            'es_credito': credito,
            'hay_documento': hay_documento,
            'cobrado': cobrado,
            'saldo': saldo,
            'en_caja': False,
            'cuenta': None,
            'avisos': [],
        }

        # Cuanto se cobro de esta solicitud
        if self._tiene_columna('Solicitudes', 'MontoCobrado'):
            try:
                self.db.execute("UPDATE [Solicitudes] SET MontoCobrado="
                                + str(cobrado) + " WHERE SolicitudID="
                                + str(int(sol_id)))
            except Exception as e:
                _log.warning("No se pudo guardar MontoCobrado de %s: %s", numero, e)

        # Ingreso de caja, solo por lo realmente cobrado
        if cobrado > 0 and registrar_en_caja:
            ok, aviso = self._asentar_en_caja(cobrado, numero, doc_result,
                                              forma_pago_texto)
            resumen['en_caja'] = ok
            if aviso:
                resumen['avisos'].append(aviso)

        # Cuenta por cobrar por lo que queda debiendose
        if saldo > 0.01:
            try:
                accion, _cid = self._guardar_cuenta(sol_id, numero, saldo,
                                                    tipo_servicio)
                resumen['cuenta'] = accion
            except Exception as e:
                resumen['avisos'].append(
                    f"No se pudo registrar la cuenta por cobrar de "
                    f"{saldo:,.2f}: {e}")
        else:
            # Ya no se debe nada: si habia cuenta abierta, cerrarla
            existente = self.cuenta_de_solicitud(sol_id)
            if existente and _f(existente.get('SaldoPendiente')) > 0.001:
                try:
                    self._guardar_cuenta(sol_id, numero, 0.0, tipo_servicio)
                    resumen['cuenta'] = 'saldada'
                except Exception as e:
                    _log.warning("No se pudo cerrar la cuenta de %s: %s", numero, e)

        return resumen


def crear_liquidador(db, usuario=None):
    """Fabrica, al estilo del resto de modulos."""
    return Liquidador(db, usuario)

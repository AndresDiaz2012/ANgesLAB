# -*- coding: utf-8 -*-
"""
================================================================================
CARTERA DE ASEGURADOS Y DESEMBOLSOS DE LA CLINICA
================================================================================
Control paciente por paciente de lo que la clinica adeuda al laboratorio.

Como funciona el convenio:

  1. El paciente asegurado se atiende. No paga en el mostrador, asi que no
     entra dinero a la caja: queda una cuenta por cobrar a su nombre, con su
     fecha de ingreso (ver procedencia.py).

  2. La administracion de la clinica cobra al seguro y va desembolsando al
     laboratorio.

  3. Cada desembolso se aplica **a los pacientes concretos que la clinica
     esta pagando**, con su importe. No se reparte a ojo ni por antiguedad:
     el laboratorio tiene que poder decir, de cada paciente, cuanto se le
     debe todavia, cuanto le han ido abonando y en que fecha quedo liberado.

  4. Cuando una cuenta queda en cero se marca su fecha de liberacion. Desde
     ese momento el paciente sale de la lista de pendientes pero conserva su
     historial.

Cada abono queda registrado por separado en AbonosCuentaCobrar, de modo que
un paciente que se paga en tres veces conserva las tres fechas y sus
importes, no solo el saldo final.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime

try:
    from modulos.procedencia import DECIMALES_IMPORTE
except Exception:  # pragma: no cover
    DECIMALES_IMPORTE = 4

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.desembolsos')
except Exception:  # pragma: no cover - respaldo si falta el modulo de logging
    import logging
    _log = logging.getLogger('angeslab.desembolsos')


# Estados de una cuenta
ESTADO_PENDIENTE = 'Pendiente'   # no ha abonado nada
ESTADO_PARCIAL = 'Parcial'       # va pagando
ESTADO_LIBERADA = 'Cobrada'      # saldada por completo

ESTADOS_ABIERTOS = (ESTADO_PENDIENTE, ESTADO_PARCIAL)

# Filtros de la vista de control
FILTRO_PENDIENTES = 'pendientes'   # sin abonar nada
FILTRO_ABONANDO = 'abonando'       # con abonos pero con saldo
FILTRO_ABIERTAS = 'abiertas'       # las dos anteriores
FILTRO_LIBERADAS = 'liberadas'     # ya saldadas
FILTRO_TODAS = 'todas'


def _f(valor, por_defecto=0.0):
    """Lee un importe sin que un dato ilegible tumbe el cobro."""
    try:
        return float(valor if valor is not None else por_defecto)
    except (TypeError, ValueError):
        return por_defecto


def _fecha_access(momento):
    return momento.strftime('#%m/%d/%Y %H:%M:%S#')


def _txt(valor, limite=255):
    return str(valor if valor is not None else '').replace("'", "''")[:limite]


class GestorDesembolsos:
    """Cartera de asegurados: consulta, abonos por paciente y liberacion."""

    def __init__(self, db):
        self.db = db
        self._cache_columnas = {}

    # ------------------------------------------------------------- esquema

    def _tiene_columna(self, tabla, columna):
        """Comprueba una vez si la columna existe, para no pedirla de mas."""
        clave = f"{tabla}.{columna}"
        if clave not in self._cache_columnas:
            try:
                self.db.query_one(f"SELECT TOP 1 {columna} FROM {tabla}")
                self._cache_columnas[clave] = True
            except Exception:
                self._cache_columnas[clave] = False
        return self._cache_columnas[clave]

    def asegurar_esquema(self):
        """
        Crea lo que hace falta para el control por paciente.

        Se llama al abrir la cartera, de modo que una instalacion que venia
        de una version anterior quede al dia sin intervencion.
        """
        # Fecha en que la cuenta quedo saldada
        if not self._tiene_columna('CuentasPorCobrar', 'FechaLiberacion'):
            try:
                self.db.execute("ALTER TABLE CuentasPorCobrar "
                                "ADD COLUMN FechaLiberacion DATETIME")
                self._cache_columnas['CuentasPorCobrar.FechaLiberacion'] = True
                _log.info("Columna CuentasPorCobrar.FechaLiberacion creada")
            except Exception as e:
                _log.warning("No se pudo crear FechaLiberacion: %s", e)

        # Historial de abonos: un paciente puede pagarse en varias veces
        try:
            self.db.query_one("SELECT TOP 1 AbonoID FROM AbonosCuentaCobrar")
        except Exception:
            try:
                self.db.execute(
                    "CREATE TABLE AbonosCuentaCobrar ("
                    "AbonoID AUTOINCREMENT PRIMARY KEY, "
                    "CuentaCobrarID LONG, "
                    "PacienteID LONG, "
                    "NombrePaciente TEXT(200), "
                    "FechaAbono DATETIME, "
                    "Monto CURRENCY, "
                    "SaldoAnterior CURRENCY, "
                    "SaldoPosterior CURRENCY, "
                    "FormaPagoID LONG, "
                    "Referencia TEXT(120), "
                    "Origen TEXT(40), "
                    "UsuarioID LONG, "
                    "Observaciones TEXT(255))")
                _log.info("Tabla AbonosCuentaCobrar creada")
            except Exception as e:
                _log.warning("No se pudo crear AbonosCuentaCobrar: %s", e)

    # --------------------------------------------------------------- leer

    def listar_cartera(self, filtro=FILTRO_ABIERTAS, solo_asegurados=True,
                       texto=None, desde=None, hasta=None):
        """
        Cartera de asegurados para la vista de control.

        Args:
            filtro: cual de los FILTRO_* aplicar.
            texto: busca por nombre de paciente.
            desde/hasta: acotan por fecha de ingreso (FechaEmision).

        Devuelve las cuentas mas antiguas primero, que es el orden en que
        conviene reclamarlas.
        """
        tiene_proc = self._tiene_columna('CuentasPorCobrar', 'TipoProcedencia')
        tiene_lib = self._tiene_columna('CuentasPorCobrar', 'FechaLiberacion')

        campos = ["CuentaCobrarID", "SolicitudID", "PacienteID", "NombrePaciente",
                  "FechaEmision", "FechaVencimiento", "MontoOriginal",
                  "MontoCobrado", "SaldoPendiente", "Estado", "Observaciones"]
        # Nombrar una columna inexistente tumba la consulta entera y la
        # cartera apareceria vacia, asi que solo se piden si existen.
        if tiene_proc:
            campos.append("TipoProcedencia")
        if tiene_lib:
            campos.append("FechaLiberacion")

        sql = f"SELECT {', '.join(campos)} FROM [CuentasPorCobrar] WHERE 1=1"

        if solo_asegurados:
            if tiene_proc:
                sql += " AND TipoProcedencia LIKE '%Asegurado%'"
            else:
                sql += " AND Observaciones LIKE 'Asegurado%'"

        saldo = "IIF(SaldoPendiente IS NULL, 0, SaldoPendiente)"
        cobrado = "IIF(MontoCobrado IS NULL, 0, MontoCobrado)"

        if filtro == FILTRO_PENDIENTES:
            sql += f" AND {saldo} > 0.001 AND {cobrado} <= 0.001"
        elif filtro == FILTRO_ABONANDO:
            sql += f" AND {saldo} > 0.001 AND {cobrado} > 0.001"
        elif filtro == FILTRO_ABIERTAS:
            sql += f" AND {saldo} > 0.001"
        elif filtro == FILTRO_LIBERADAS:
            sql += f" AND {saldo} <= 0.001"
        # FILTRO_TODAS no anade condicion

        if texto:
            sql += f" AND NombrePaciente LIKE '%{_txt(texto, 80)}%'"
        if desde:
            sql += f" AND FechaEmision >= {_fecha_access(desde)}"
        if hasta:
            sql += f" AND FechaEmision <= {_fecha_access(hasta)}"

        sql += " ORDER BY FechaEmision, NombrePaciente"

        try:
            return self.db.query(sql) or []
        except Exception as e:
            _log.error("No se pudo listar la cartera: %s", e)
            return []

    def obtener_cuenta(self, cuenta_id):
        try:
            return self.db.query_one(
                f"SELECT * FROM [CuentasPorCobrar] WHERE CuentaCobrarID={int(cuenta_id)}")
        except Exception as e:
            _log.error("No se pudo leer la cuenta %s: %s", cuenta_id, e)
            return None

    def historial_abonos(self, cuenta_id):
        """Los abonos de un paciente, del mas reciente al mas antiguo."""
        try:
            return self.db.query(
                f"SELECT * FROM [AbonosCuentaCobrar] "
                f"WHERE CuentaCobrarID={int(cuenta_id)} "
                f"ORDER BY FechaAbono DESC") or []
        except Exception:
            return []

    def resumen_cartera(self, solo_asegurados=True):
        """Cifras para las tarjetas de la vista de control."""
        abiertas = self.listar_cartera(FILTRO_ABIERTAS, solo_asegurados)
        pendientes = [c for c in abiertas if _f(c.get('MontoCobrado')) <= 0.001]
        abonando = [c for c in abiertas if _f(c.get('MontoCobrado')) > 0.001]
        liberadas = self.listar_cartera(FILTRO_LIBERADAS, solo_asegurados)

        return {
            'total_pendiente': round(sum(_f(c.get('SaldoPendiente')) for c in abiertas), 2),
            'n_abiertas': len(abiertas),
            'n_sin_abonar': len(pendientes),
            'n_abonando': len(abonando),
            'n_liberadas': len(liberadas),
            'total_abonado': round(sum(_f(c.get('MontoCobrado')) for c in abiertas), 2),
        }

    # ------------------------------------------------------------ escribir

    def registrar_abono(self, cuenta_id, monto, usuario_id, forma_pago_id=None,
                        referencia='', origen='Desembolso clinica',
                        observaciones='', registrar_en_caja=True):
        """
        Aplica lo que la clinica desembolsa **por un paciente concreto**.

        Devuelve (exito, mensaje, detalle).

        El importe no puede pasar del saldo de esa cuenta: si la clinica
        manda de mas por un paciente, ese excedente corresponde a otro y hay
        que aplicarlo en su propia cuenta, no inflar esta.
        """
        cuenta = self.obtener_cuenta(cuenta_id)
        if not cuenta:
            return False, "No se encontro la cuenta del paciente.", None

        saldo = round(_f(cuenta.get('SaldoPendiente')), DECIMALES_IMPORTE)
        if saldo <= 0.001:
            return False, (f"{cuenta.get('NombrePaciente', 'El paciente')} ya esta "
                           f"liberado: no tiene saldo pendiente."), None

        monto = round(_f(monto), DECIMALES_IMPORTE)
        if monto <= 0:
            return False, "El importe debe ser mayor que cero.", None
        if monto > saldo + 0.001:
            return False, (f"El importe ({monto:,.2f}) supera lo que se le debe a "
                           f"{cuenta.get('NombrePaciente', 'este paciente')} "
                           f"({saldo:,.2f})."), None

        cobrado_nuevo = round(_f(cuenta.get('MontoCobrado')) + monto,
                              DECIMALES_IMPORTE)
        saldo_nuevo = round(saldo - monto, DECIMALES_IMPORTE)
        libera = saldo_nuevo <= 0.001
        estado = ESTADO_LIBERADA if libera else ESTADO_PARCIAL
        ahora = datetime.now()

        sets = [f"MontoCobrado={cobrado_nuevo}",
                f"SaldoPendiente={saldo_nuevo}",
                f"Estado='{estado}'"]
        if self._tiene_columna('CuentasPorCobrar', 'FechaLiberacion'):
            # Si vuelve a quedar saldo (una anulacion posterior), la fecha de
            # liberacion deja de tener sentido y se limpia.
            sets.append(f"FechaLiberacion={_fecha_access(ahora) if libera else 'Null'}")

        try:
            self.db.execute(f"UPDATE [CuentasPorCobrar] SET {', '.join(sets)} "
                            f"WHERE CuentaCobrarID={int(cuenta_id)}")
        except Exception as e:
            _log.error("Abono en cuenta %s: %s", cuenta_id, e)
            return False, f"No se pudo registrar el abono: {e}", None

        self._guardar_historial(cuenta, monto, saldo, saldo_nuevo, forma_pago_id,
                                referencia, origen, usuario_id, observaciones, ahora)

        aviso_caja = ''
        if registrar_en_caja:
            aviso_caja = self._asentar_en_caja(
                monto, usuario_id, referencia, forma_pago_id,
                cuenta.get('NombrePaciente', ''), ahora)

        detalle = {
            'cuenta_id': cuenta_id,
            'paciente': cuenta.get('NombrePaciente', ''),
            'monto': monto,
            'saldo_anterior': saldo,
            'saldo_nuevo': saldo_nuevo,
            'libera': libera,
            'aviso_caja': aviso_caja,
        }

        nombre = cuenta.get('NombrePaciente', 'El paciente')
        if libera:
            msg = f"{nombre}: abonados {monto:,.2f}. Queda LIBERADO."
        else:
            msg = f"{nombre}: abonados {monto:,.2f}. Sigue debiendo {saldo_nuevo:,.2f}."
        if aviso_caja:
            msg += " " + aviso_caja

        _log.info("Abono de %.2f en cuenta %s (%s) por usuario %s",
                  monto, cuenta_id, nombre, usuario_id)

        return True, msg, detalle

    def registrar_desembolso(self, lineas, usuario_id, referencia='',
                             forma_pago_id=None, registrar_en_caja=True):
        """
        Aplica un desembolso que cubre a varios pacientes de una vez.

        Args:
            lineas: lista de dicts {cuenta_id, monto}. Cada paciente lleva su
                    importe: el desembolso no se reparte solo.

        Devuelve (exito, mensaje, detalle). Las lineas que fallan no impiden
        que se apliquen las demas, y se informan una por una.

        Se asienta un unico ingreso de caja por el total aplicado, porque a
        la caja llego un solo pago de la clinica, aunque cubra a varios
        pacientes.
        """
        if not lineas:
            return False, "No se indico ningun paciente.", None

        aplicadas, errores = [], []
        ahora = datetime.now()

        for linea in lineas:
            cuenta_id = linea.get('cuenta_id')
            monto = round(_f(linea.get('monto')), DECIMALES_IMPORTE)
            if monto <= 0:
                continue
            # Cada abono se registra sin tocar caja: el ingreso se asienta
            # una sola vez al final, por el total del desembolso.
            ok, msg, det = self.registrar_abono(
                cuenta_id, monto, usuario_id, forma_pago_id=forma_pago_id,
                referencia=referencia, origen='Desembolso clinica',
                registrar_en_caja=False)
            if ok:
                aplicadas.append(det)
            else:
                errores.append(msg)

        if not aplicadas:
            return False, ("No se aplico ningun abono. " + " ".join(errores)).strip(), None

        total = round(sum(a['monto'] for a in aplicadas), DECIMALES_IMPORTE)
        liberados = [a for a in aplicadas if a['libera']]

        aviso_caja = ''
        if registrar_en_caja and total > 0:
            aviso_caja = self._asentar_en_caja(
                total, usuario_id, referencia, forma_pago_id,
                f"{len(aplicadas)} paciente(s)", ahora)

        partes = [f"Desembolso aplicado: {total:,.2f} sobre {len(aplicadas)} "
                  f"paciente(s); {len(liberados)} liberado(s)."]
        if aviso_caja:
            partes.append(aviso_caja)
        if errores:
            partes.append("No se aplicaron: " + " ".join(errores))

        detalle = {
            'aplicadas': aplicadas,
            'total': total,
            'liberados': len(liberados),
            'errores': errores,
            'aviso_caja': aviso_caja,
        }
        return True, " ".join(partes), detalle

    # ---------------------------------------------------------------- apoyo

    def _guardar_historial(self, cuenta, monto, saldo_ant, saldo_nuevo,
                           forma_pago_id, referencia, origen, usuario_id,
                           observaciones, momento):
        """
        Deja constancia del abono. Si falla no se deshace el cobro: el saldo
        ya quedo bien y perder la linea de historial es el mal menor.
        """
        try:
            pac_id = cuenta.get('PacienteID')
            self.db.execute(
                "INSERT INTO [AbonosCuentaCobrar] (CuentaCobrarID, PacienteID, "
                "NombrePaciente, FechaAbono, Monto, SaldoAnterior, SaldoPosterior, "
                "FormaPagoID, Referencia, Origen, UsuarioID, Observaciones) VALUES ("
                f"{int(cuenta.get('CuentaCobrarID'))}, "
                f"{int(pac_id) if pac_id else 'Null'}, "
                f"'{_txt(cuenta.get('NombrePaciente'), 200)}', "
                f"{_fecha_access(momento)}, {monto}, {saldo_ant}, {saldo_nuevo}, "
                f"{int(forma_pago_id) if forma_pago_id else 'Null'}, "
                f"'{_txt(referencia, 120)}', '{_txt(origen, 40)}', "
                f"{int(usuario_id) if usuario_id else 'Null'}, "
                f"'{_txt(observaciones, 255)}')")
        except Exception as e:
            _log.warning("No se pudo guardar el historial del abono: %s", e)

    def _asentar_en_caja(self, monto, usuario_id, referencia, forma_pago_id,
                         concepto, momento):
        """Devuelve '' si todo fue bien, o el aviso que hay que mostrar."""
        try:
            from modulos.modulo_administrativo import GestorCajaChica
            gestor_caja = GestorCajaChica(self.db)
            caja = gestor_caja.obtener_caja_abierta()
            if not caja:
                _log.warning("Abono de %.2f sin caja abierta", monto)
                return (f"ATENCION: no hay caja abierta, asi que el ingreso de "
                        f"{monto:,.2f} no quedo registrado en caja. La cuenta si "
                        f"se actualizo: registre el ingreso al abrir la caja.")

            ref = referencia or f"Desembolso {momento.strftime('%d/%m/%Y')}"
            ok, msg = gestor_caja.registrar_movimiento(caja['CajaID'], {
                'Tipo': 'Ingreso',
                'Categoria': 'Desembolso de la clinica',
                'Descripcion': f"Desembolso - {concepto}",
                'Monto': monto,
                'FormaPagoID': forma_pago_id if forma_pago_id else 'Null',
                'Referencia': ref,
                'FacturaID': 'Null',
            }, usuario_id)
            if not ok:
                return f"ATENCION: la cuenta se actualizo pero la caja rechazo el ingreso: {msg}"
            return ''
        except Exception as e:
            _log.error("Abono: fallo al asentar en caja: %s", e)
            return (f"ATENCION: la cuenta se actualizo pero el ingreso de "
                    f"{monto:,.2f} no pudo registrarse en caja: {e}")


def crear_gestor_desembolsos(db):
    """Fabrica, al estilo del resto de modulos."""
    return GestorDesembolsos(db)

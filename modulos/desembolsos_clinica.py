# -*- coding: utf-8 -*-
"""
================================================================================
DESEMBOLSOS DE LA CLINICA
================================================================================
Salda la cartera de pacientes asegurados a medida que la administracion de la
clinica va desembolsando al laboratorio.

Como funciona el convenio:

  1. El paciente asegurado se atiende. No paga en el mostrador, asi que no
     entra dinero a la caja: queda una cuenta por cobrar (ver procedencia.py).

  2. La clinica cobra al seguro y despues desembolsa al laboratorio, casi
     siempre por varias atenciones a la vez y no atencion por atencion.

  3. Ese desembolso se reparte aqui entre las cuentas pendientes, de la mas
     antigua a la mas reciente, y recien entonces entra el dinero a la caja.

Un desembolso puede no alcanzar para todo lo pendiente: la ultima cuenta que
toca queda abonada en parte y conserva su saldo. Nunca se salda una cuenta con
dinero que no llego.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.desembolsos')
except Exception:  # pragma: no cover - respaldo si falta el modulo de logging
    import logging
    _log = logging.getLogger('angeslab.desembolsos')

try:
    from modulos.procedencia import es_credito
except Exception:  # pragma: no cover
    def es_credito(_tipo):
        return False


# Estados que todavia deben dinero
ESTADOS_ABIERTOS = ('Pendiente', 'Parcial')


def repartir_desembolso(monto, cuentas):
    """
    Reparte un desembolso entre cuentas pendientes, de la mas antigua a la mas
    nueva.

    Args:
        monto: importe desembolsado por la clinica.
        cuentas: lista de dicts con al menos CuentaCobrarID y SaldoPendiente,
                 ya ordenada por antiguedad.

    Returns:
        (aplicaciones, sobrante) donde aplicaciones es una lista de dicts
        {cuenta_id, monto, saldo_anterior, saldo_nuevo, salda}.

    El calculo va aparte de la escritura en la base para poder mostrarle al
    usuario que se va a saldar antes de confirmar, y para poder probarlo sin
    tocar la base.
    """
    try:
        restante = round(max(0.0, float(monto or 0)), 2)
    except (TypeError, ValueError):
        restante = 0.0

    aplicaciones = []
    for cuenta in cuentas or []:
        if restante <= 0.001:
            break
        try:
            saldo = round(float(cuenta.get('SaldoPendiente', 0) or 0), 2)
        except (TypeError, ValueError):
            continue
        if saldo <= 0.001:
            continue

        aplicado = round(min(restante, saldo), 2)
        restante = round(restante - aplicado, 2)
        aplicaciones.append({
            'cuenta_id': cuenta.get('CuentaCobrarID'),
            'paciente': cuenta.get('NombrePaciente', ''),
            'monto': aplicado,
            'saldo_anterior': saldo,
            'saldo_nuevo': round(saldo - aplicado, 2),
            'salda': (saldo - aplicado) <= 0.001,
        })

    return aplicaciones, round(restante, 2)


class GestorDesembolsos:
    """Cartera de asegurados y aplicacion de los desembolsos de la clinica."""

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------ leer

    def _tiene_columna_procedencia(self):
        try:
            self.db.query_one("SELECT TOP 1 TipoProcedencia FROM CuentasPorCobrar")
            return True
        except Exception:
            return False

    def listar_pendientes(self, solo_asegurados=True):
        """
        Cuentas con saldo, de la mas antigua a la mas reciente.

        Con solo_asegurados se devuelve unicamente lo que le toca desembolsar
        a la clinica, para no aplicar su dinero a la deuda de un particular.

        Las bases que todavia no tienen la columna TipoProcedencia se filtran
        por el texto de las observaciones, que es como quedaron marcadas las
        cuentas creadas antes de anadirla.
        """
        tiene_proc = self._tiene_columna_procedencia()

        campos = ["CuentaCobrarID", "SolicitudID", "PacienteID", "NombrePaciente",
                  "FechaEmision", "FechaVencimiento", "MontoOriginal",
                  "MontoCobrado", "SaldoPendiente", "Estado", "Observaciones"]
        # Solo se pide si existe: en una base antigua nombrarla tumbaria la
        # consulta entera y la cartera apareceria vacia.
        if tiene_proc:
            campos.append("TipoProcedencia")

        estados = ', '.join(f"'{e}'" for e in ESTADOS_ABIERTOS)
        sql = (f"SELECT {', '.join(campos)} "
               "FROM [CuentasPorCobrar] "
               f"WHERE Estado IN ({estados}) "
               "AND IIF(SaldoPendiente IS NULL, 0, SaldoPendiente) > 0.001")

        if solo_asegurados:
            if tiene_proc:
                sql += " AND TipoProcedencia LIKE '%Asegurado%'"
            else:
                sql += " AND Observaciones LIKE 'Asegurado%'"

        sql += " ORDER BY FechaEmision"

        try:
            return self.db.query(sql) or []
        except Exception as e:
            _log.error("No se pudo listar la cartera pendiente: %s", e)
            return []

    def total_pendiente(self, solo_asegurados=True):
        """Cuanto debe la clinica en total."""
        return round(sum(float(c.get('SaldoPendiente', 0) or 0)
                         for c in self.listar_pendientes(solo_asegurados)), 2)

    def previsualizar(self, monto, solo_asegurados=True):
        """
        Que saldaria un desembolso, sin escribir nada.

        Sirve para enseñarle al usuario el reparto antes de que confirme.
        """
        cuentas = self.listar_pendientes(solo_asegurados)
        return repartir_desembolso(monto, cuentas)

    # --------------------------------------------------------------- escribir

    def registrar_desembolso(self, monto, usuario_id, referencia='',
                             forma_pago_id=None, solo_asegurados=True,
                             registrar_en_caja=True):
        """
        Aplica un desembolso de la clinica a la cartera y lo asienta en caja.

        Devuelve (exito, mensaje, detalle) donde detalle trae las
        aplicaciones, el total aplicado y el sobrante.

        El dinero entra a la caja aqui, que es cuando llega de verdad: al
        registrar la solicitud del asegurado no habia entrado nada.
        """
        cuentas = self.listar_pendientes(solo_asegurados)
        aplicaciones, sobrante = repartir_desembolso(monto, cuentas)

        if not aplicaciones:
            if not cuentas:
                return False, "No hay cuentas de asegurados pendientes de cobro.", None
            return False, "El monto indicado no alcanza a cubrir ninguna cuenta.", None

        aplicado_total = round(sum(a['monto'] for a in aplicaciones), 2)
        saldadas = sum(1 for a in aplicaciones if a['salda'])
        fecha = datetime.now()

        # Aplicar cuenta por cuenta
        errores = []
        aplicadas_ok = []
        for ap in aplicaciones:
            estado = 'Cobrada' if ap['salda'] else 'Parcial'
            try:
                cobrado_previo = self._cobrado_actual(ap['cuenta_id'])
                nuevo_cobrado = round(cobrado_previo + ap['monto'], 2)
                self.db.execute(
                    f"UPDATE [CuentasPorCobrar] SET "
                    f"MontoCobrado={nuevo_cobrado}, "
                    f"SaldoPendiente={ap['saldo_nuevo']}, "
                    f"Estado='{estado}' "
                    f"WHERE CuentaCobrarID={ap['cuenta_id']}")
                aplicadas_ok.append(ap)
            except Exception as e:
                _log.error("Desembolso: fallo al aplicar en cuenta %s: %s",
                           ap['cuenta_id'], e)
                errores.append(f"cuenta #{ap['cuenta_id']}: {e}")

        if not aplicadas_ok:
            return False, "No se pudo aplicar el desembolso: " + "; ".join(errores), None

        # El dinero entra a caja por lo que se aplico de verdad
        aplicado_real = round(sum(a['monto'] for a in aplicadas_ok), 2)
        aviso_caja = ''
        if registrar_en_caja and aplicado_real > 0:
            aviso_caja = self._asentar_en_caja(aplicado_real, usuario_id,
                                               referencia, forma_pago_id,
                                               len(aplicadas_ok), fecha)

        detalle = {
            'aplicaciones': aplicadas_ok,
            'aplicado': aplicado_real,
            'sobrante': sobrante,
            'saldadas': saldadas,
            'errores': errores,
            'aviso_caja': aviso_caja,
        }

        partes = [f"Desembolso aplicado: {aplicado_real:,.2f} "
                  f"sobre {len(aplicadas_ok)} cuenta(s), {saldadas} saldada(s)."]
        if sobrante > 0.001:
            partes.append(f"Sobran {sobrante:,.2f} sin aplicar: "
                          f"ya no hay mas saldo pendiente.")
        if aviso_caja:
            partes.append(aviso_caja)
        if errores:
            partes.append("Con incidencias: " + "; ".join(errores))

        _log.info("Desembolso de clinica: %.2f aplicado a %d cuenta(s) por usuario %s",
                  aplicado_real, len(aplicadas_ok), usuario_id)

        return True, " ".join(partes), detalle

    # ---------------------------------------------------------------- apoyo

    def _cobrado_actual(self, cuenta_id):
        fila = self.db.query_one(
            f"SELECT MontoCobrado FROM [CuentasPorCobrar] "
            f"WHERE CuentaCobrarID={cuenta_id}")
        try:
            return float((fila or {}).get('MontoCobrado', 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _asentar_en_caja(self, monto, usuario_id, referencia, forma_pago_id, n_cuentas, fecha):
        """
        Registra el ingreso. Devuelve '' si todo fue bien, o el aviso a mostrar.

        Si no hay caja abierta se avisa: el reparto ya quedo hecho y el dinero
        no puede quedar sin registrar sin que nadie se entere.
        """
        try:
            from modulos.modulo_administrativo import GestorCajaChica
            gestor_caja = GestorCajaChica(self.db)
            caja = gestor_caja.obtener_caja_abierta()
            if not caja:
                _log.warning("Desembolso de %.2f sin caja abierta", monto)
                return (f"ATENCION: no hay caja abierta, asi que el ingreso de "
                        f"{monto:,.2f} no quedo registrado en caja. Las cuentas "
                        f"si se saldaron: registre el ingreso a mano al abrirla.")

            ref = referencia or f"Desembolso {fecha.strftime('%d/%m/%Y')}"
            ok, msg = gestor_caja.registrar_movimiento(caja['CajaID'], {
                'Tipo': 'Ingreso',
                'Categoria': 'Desembolso de la clinica',
                'Descripcion': f"Desembolso sobre {n_cuentas} cuenta(s) de asegurados",
                'Monto': monto,
                'FormaPagoID': forma_pago_id if forma_pago_id else 'Null',
                'Referencia': ref,
                'FacturaID': 'Null',
            }, usuario_id)
            if not ok:
                return f"ATENCION: las cuentas se saldaron pero la caja rechazo el ingreso: {msg}"
            return ''
        except Exception as e:
            _log.error("Desembolso: fallo al asentar en caja: %s", e)
            return (f"ATENCION: las cuentas se saldaron pero el ingreso de "
                    f"{monto:,.2f} no pudo registrarse en caja: {e}")


def crear_gestor_desembolsos(db):
    """Fabrica, al estilo del resto de modulos."""
    return GestorDesembolsos(db)

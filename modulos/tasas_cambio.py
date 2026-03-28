# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE TASAS DE CAMBIO - ANgesLAB
================================================================================
Gestion de tasas de cambio con integracion BCV (Banco Central de Venezuela).

Funcionalidades:
- Consulta automatica de tasas BCV via pyBCV
- Almacenamiento historico de tasas en base de datos
- Conversiones entre monedas (USD, VES/Bs, COP, EUR)
- Cache en memoria con TTL de 1 hora
- Degradacion gracil si pyBCV no esta instalado

Dependencias opcionales:
- pyBCV (pip install pyBCV) para consulta automatica

Autor: Sistema ANgesLAB
================================================================================
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

# Verificar disponibilidad de pyBCV
try:
    from pyBCV import Currency as _BCV_Currency
    PYBCV_DISPONIBLE = True
except ImportError:
    PYBCV_DISPONIBLE = False

# Monedas que publica el BCV
MONEDAS_BCV = ['USD', 'EUR', 'CNY', 'TRY', 'RUB', 'JPY']

# TTL del cache en segundos (1 hora)
_CACHE_TTL = 3600


class GestorTasasCambio:
    """
    Gestiona tasas de cambio: API BCV, almacenamiento historico, conversiones.
    """

    def __init__(self, db):
        self.db = db
        self._cache = {}  # {moneda: (tasa_float, datetime_consulta)}
        self._asegurar_tabla()

    # =========================================================================
    # INFRAESTRUCTURA DB
    # =========================================================================

    def _asegurar_tabla(self):
        """Crea la tabla TasasCambio si no existe."""
        try:
            self.db.query("SELECT TOP 1 TasaID FROM TasasCambio")
        except Exception:
            try:
                self.db.execute("""
                    CREATE TABLE TasasCambio (
                        TasaID        AUTOINCREMENT PRIMARY KEY,
                        Fecha         DATETIME NOT NULL,
                        Moneda        TEXT(10) NOT NULL,
                        Tasa          DOUBLE NOT NULL,
                        FuenteAPI     TEXT(50) DEFAULT 'BCV',
                        FechaConsulta DATETIME
                    )
                """)
                logging.getLogger("angeslab.tasas_cambio").debug("[TASAS] Tabla TasasCambio creada")
            except Exception as e:
                logging.getLogger("angeslab.tasas_cambio").warning("[TASAS] Error creando tabla TasasCambio: %s", e)

    # =========================================================================
    # CONSULTA BCV
    # =========================================================================

    def actualizar_tasas_bcv(self):
        """
        Consulta tasas actuales del BCV via pyBCV.

        Returns:
            dict: {moneda: tasa} con las tasas obtenidas
        Raises:
            RuntimeError: si pyBCV no esta instalado
            Exception: si falla la consulta al BCV
        """
        # Importar en tiempo de ejecucion para detectar instalaciones recientes
        try:
            from pyBCV import Currency as _Currency
        except ImportError:
            raise RuntimeError(
                "pyBCV no esta instalado.\n\n"
                "Ejecute en una terminal:\n"
                "  pip install pyBCV"
            )

        currency = _Currency()
        tasas_raw = currency.get_rate()

        tasas = {}
        ahora = datetime.now()

        if isinstance(tasas_raw, dict):
            for moneda in MONEDAS_BCV:
                valor = tasas_raw.get(moneda)
                if valor is not None:
                    try:
                        tasa_float = float(str(valor).replace(',', '.'))
                        self._guardar_tasa(moneda, tasa_float, 'BCV')
                        self._cache[moneda] = (tasa_float, ahora)
                        tasas[moneda] = tasa_float
                    except (ValueError, TypeError):
                        pass
        else:
            # pyBCV puede retornar formatos distintos segun la version
            # Intentar obtener monedas individuales
            for moneda in ['USD', 'EUR']:
                try:
                    valor = currency.get_rate(currency_code=moneda, prettify=False)
                    if valor is not None:
                        tasa_float = float(str(valor).replace(',', '.'))
                        self._guardar_tasa(moneda, tasa_float, 'BCV')
                        self._cache[moneda] = (tasa_float, ahora)
                        tasas[moneda] = tasa_float
                except Exception:
                    pass

        if not tasas:
            raise RuntimeError("No se obtuvieron tasas del BCV")

        return tasas

    # =========================================================================
    # ALMACENAMIENTO
    # =========================================================================

    def _guardar_tasa(self, moneda, tasa, fuente='BCV'):
        """Guarda una tasa en la tabla TasasCambio."""
        try:
            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            moneda_esc = moneda.replace("'", "''")
            fuente_esc = fuente.replace("'", "''")
            self.db.execute(
                f"INSERT INTO TasasCambio (Fecha, Moneda, Tasa, FuenteAPI, FechaConsulta) "
                f"VALUES ({fecha}, '{moneda_esc}', {tasa}, '{fuente_esc}', {fecha})"
            )
        except Exception as e:
            logging.getLogger("angeslab.tasas_cambio").warning("[TASAS] Error guardando tasa {moneda}: %s", e)

    def guardar_tasa_manual(self, moneda, tasa):
        """
        Guarda una tasa ingresada manualmente (ej: COP/USD).

        Args:
            moneda: codigo de moneda (ej: 'COP_USD')
            tasa: valor de la tasa
        """
        tasa_float = float(tasa)
        self._guardar_tasa(moneda, tasa_float, 'Manual')
        self._cache[moneda] = (tasa_float, datetime.now())

    # =========================================================================
    # CONSULTAS
    # =========================================================================

    def get_tasa_actual(self, moneda='USD'):
        """
        Obtiene la tasa mas reciente para una moneda.

        Cadena de fallback: cache en memoria → DB → 1.0

        Args:
            moneda: codigo de moneda (USD, EUR, COP_USD, etc.)

        Returns:
            float: tasa de cambio
        """
        # 1. Cache en memoria (si tiene menos de 1 hora)
        if moneda in self._cache:
            tasa, timestamp = self._cache[moneda]
            if (datetime.now() - timestamp).total_seconds() < _CACHE_TTL:
                return tasa

        # 2. Consultar DB
        try:
            moneda_esc = moneda.replace("'", "''")
            result = self.db.query_one(
                f"SELECT TOP 1 Tasa FROM TasasCambio "
                f"WHERE Moneda='{moneda_esc}' "
                f"ORDER BY Fecha DESC"
            )
            if result and result.get('Tasa'):
                tasa = float(result['Tasa'])
                self._cache[moneda] = (tasa, datetime.now())
                return tasa
        except Exception:
            pass

        # 3. Fallback
        logging.getLogger("angeslab.tasas_cambio").debug("[TASAS] Sin tasa para %s, usando 1.0", moneda)
        return 1.0

    def get_tasa_fecha(self, moneda, fecha):
        """
        Obtiene la tasa vigente para una fecha especifica.

        Args:
            moneda: codigo de moneda
            fecha: datetime o date

        Returns:
            float: tasa de cambio para esa fecha
        """
        try:
            moneda_esc = moneda.replace("'", "''")
            fecha_str = fecha.strftime('%m/%d/%Y')
            result = self.db.query_one(
                f"SELECT TOP 1 Tasa FROM TasasCambio "
                f"WHERE Moneda='{moneda_esc}' AND Fecha <= #{fecha_str} 23:59:59# "
                f"ORDER BY Fecha DESC"
            )
            if result and result.get('Tasa'):
                return float(result['Tasa'])
        except Exception:
            pass

        return self.get_tasa_actual(moneda)

    def get_tasas_historicas(self, moneda='USD', dias=30):
        """
        Obtiene tasas historicas para graficas/reportes.

        Args:
            moneda: codigo de moneda
            dias: cantidad de dias hacia atras

        Returns:
            list: [{fecha, tasa}, ...]
        """
        try:
            fecha_inicio = (datetime.now() - timedelta(days=dias)).strftime('%m/%d/%Y')
            moneda_esc = moneda.replace("'", "''")
            rows = self.db.query(
                f"SELECT Fecha, Tasa FROM TasasCambio "
                f"WHERE Moneda='{moneda_esc}' AND Fecha >= #{fecha_inicio}# "
                f"ORDER BY Fecha ASC"
            )
            return [{'fecha': r['Fecha'], 'tasa': float(r['Tasa'])} for r in (rows or [])]
        except Exception:
            return []

    def get_ultima_actualizacion(self):
        """
        Obtiene la fecha/hora de la ultima actualizacion BCV.

        Returns:
            datetime o None
        """
        try:
            result = self.db.query_one(
                "SELECT TOP 1 FechaConsulta FROM TasasCambio "
                "WHERE FuenteAPI='BCV' ORDER BY FechaConsulta DESC"
            )
            if result and result.get('FechaConsulta'):
                return result['FechaConsulta']
        except Exception:
            pass
        return None

    # =========================================================================
    # CONVERSIONES
    # =========================================================================

    def usd_to_bs(self, monto_usd, tasa=None):
        """
        Convierte USD a Bolivares.

        Args:
            monto_usd: monto en dolares
            tasa: tasa USD/Bs (si None, usa la actual)

        Returns:
            float: monto en bolivares
        """
        if tasa is None:
            tasa = self.get_tasa_actual('USD')
        resultado = Decimal(str(monto_usd)) * Decimal(str(tasa))
        return float(resultado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def bs_to_usd(self, monto_bs, tasa=None):
        """
        Convierte Bolivares a USD.

        Args:
            monto_bs: monto en bolivares
            tasa: tasa USD/Bs (si None, usa la actual)

        Returns:
            float: monto en dolares
        """
        if tasa is None:
            tasa = self.get_tasa_actual('USD')
        if tasa == 0:
            return 0.0
        resultado = Decimal(str(monto_bs)) / Decimal(str(tasa))
        return float(resultado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def cop_to_usd(self, monto_cop, tasa_cop_usd=None):
        """
        Convierte COP a USD.

        Args:
            monto_cop: monto en pesos colombianos
            tasa_cop_usd: cuantos COP por 1 USD (si None, usa la guardada)

        Returns:
            float: monto en dolares
        """
        if tasa_cop_usd is None:
            tasa_cop_usd = self.get_tasa_actual('COP_USD')
        if tasa_cop_usd == 0:
            return 0.0
        resultado = Decimal(str(monto_cop)) / Decimal(str(tasa_cop_usd))
        return float(resultado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def usd_to_cop(self, monto_usd, tasa_cop_usd=None):
        """
        Convierte USD a COP.

        Args:
            monto_usd: monto en dolares
            tasa_cop_usd: cuantos COP por 1 USD

        Returns:
            float: monto en pesos colombianos
        """
        if tasa_cop_usd is None:
            tasa_cop_usd = self.get_tasa_actual('COP_USD')
        resultado = Decimal(str(monto_usd)) * Decimal(str(tasa_cop_usd))
        return float(resultado.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def cop_to_bs(self, monto_cop, tasa_cop_usd=None, tasa_usd_bs=None):
        """
        Convierte COP a Bolivares (via USD como intermedio).

        Args:
            monto_cop: monto en pesos colombianos
            tasa_cop_usd: COP por USD
            tasa_usd_bs: Bs por USD

        Returns:
            float: monto en bolivares
        """
        monto_usd = self.cop_to_usd(monto_cop, tasa_cop_usd)
        return self.usd_to_bs(monto_usd, tasa_usd_bs)

    def bs_to_cop(self, monto_bs, tasa_cop_usd=None, tasa_usd_bs=None):
        """
        Convierte Bolivares a COP (via USD como intermedio).

        Args:
            monto_bs: monto en bolivares
            tasa_cop_usd: COP por USD
            tasa_usd_bs: Bs por USD

        Returns:
            float: monto en pesos colombianos
        """
        monto_usd = self.bs_to_usd(monto_bs, tasa_usd_bs)
        return self.usd_to_cop(monto_usd, tasa_cop_usd)

    def convertir(self, monto, moneda_origen, moneda_destino):
        """
        Conversion generica entre monedas soportadas.

        Args:
            monto: monto a convertir
            moneda_origen: 'USD', 'VES', 'COP', 'EUR'
            moneda_destino: 'USD', 'VES', 'COP', 'EUR'

        Returns:
            float: monto convertido
        """
        if moneda_origen == moneda_destino:
            return float(monto)

        # Normalizar VES/Bs
        origen = 'VES' if moneda_origen in ('VES', 'Bs', 'Bs.') else moneda_origen
        destino = 'VES' if moneda_destino in ('VES', 'Bs', 'Bs.') else moneda_destino

        # USD <-> VES
        if origen == 'USD' and destino == 'VES':
            return self.usd_to_bs(monto)
        if origen == 'VES' and destino == 'USD':
            return self.bs_to_usd(monto)

        # COP <-> USD
        if origen == 'COP' and destino == 'USD':
            return self.cop_to_usd(monto)
        if origen == 'USD' and destino == 'COP':
            return self.usd_to_cop(monto)

        # COP <-> VES (via USD)
        if origen == 'COP' and destino == 'VES':
            return self.cop_to_bs(monto)
        if origen == 'VES' and destino == 'COP':
            return self.bs_to_cop(monto)

        # EUR <-> VES
        if origen == 'EUR' and destino == 'VES':
            tasa_eur = self.get_tasa_actual('EUR')
            return float(Decimal(str(monto)) * Decimal(str(tasa_eur)))
        if origen == 'VES' and destino == 'EUR':
            tasa_eur = self.get_tasa_actual('EUR')
            if tasa_eur == 0:
                return 0.0
            return float(Decimal(str(monto)) / Decimal(str(tasa_eur)))

        # EUR <-> USD (via VES como intermedio)
        if origen == 'EUR' and destino == 'USD':
            bs = self.convertir(monto, 'EUR', 'VES')
            return self.bs_to_usd(bs)
        if origen == 'USD' and destino == 'EUR':
            bs = self.usd_to_bs(monto)
            return self.convertir(bs, 'VES', 'EUR')

        # No soportado
        logging.getLogger("angeslab.tasas_cambio").debug("[TASAS] Conversion %s->%s no soportada", origen, destino)
        return float(monto)


# ============================================================================
# FUNCION DE CONVENIENCIA
# ============================================================================

def crear_gestor_tasas(db):
    """Crea una instancia de GestorTasasCambio."""
    return GestorTasasCambio(db)

# -*- coding: utf-8 -*-
"""
================================================================================
TARIFAS: QUE PRECIO SE APLICA EN CADA CASO
================================================================================
El laboratorio maneja dos tarifas y una liquidacion, porque el paciente que
llega por su pie y el que llega por la clinica no pagan lo mismo ni le dejan
al laboratorio lo mismo.

Por cada prueba hay tres importes:

  PRECIO AMBULATORIO   Lo que paga el paciente que viene por su cuenta. Es
  (Pruebas.Precio)     lo que cobra el laboratorio en su mostrador, y entra
                       integro a su caja.

  PRECIO CLINICA       Lo que la clinica le cobra al paciente que viene de
  (PrecioClinica)      hospitalizacion, emergencia o cirugia, sea asegurado
                       o particular. Para el laboratorio es INFORMATIVO: ese
                       dinero lo cobra la clinica, no el.

  PRECIO CONVENIO      Lo que la clinica le paga al laboratorio por esa
  (PrecioConvenio)     prueba. Es el ingreso real del laboratorio en los
                       casos de clinica, y por tanto lo que hay que valorar
                       en la solicitud y reclamar en el corte.

La diferencia entre los dos ultimos es la comision que se queda la clinica
por facturar y cobrar. Con el ejemplo del convenio:

    Hematologia completa     ambulatorio   20.000
                             clinica       40.000   <- lo paga el paciente
                             convenio      30.000   <- lo recibe el laboratorio
                             comision      10.000   <- se la queda la clinica

Valorar una solicitud de hospitalizacion al precio ambulatorio deja al
laboratorio cobrando 20.000 donde le corresponden 30.000. Por eso el precio
no se elige por quien paga, sino por el AREA de donde viene el paciente: en
cuanto entra por la clinica se aplica el convenio, sea asegurado o no.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.tarifas')
except Exception:  # pragma: no cover
    import logging
    _log = logging.getLogger('angeslab.tarifas')

try:
    from modulos.procedencia import es_area_clinica
except Exception:  # pragma: no cover
    def es_area_clinica(_tipo):
        return False


# Nombres de las columnas que se agregan a Pruebas
COL_CLINICA = 'PrecioClinica'
COL_CONVENIO = 'PrecioConvenio'

# Tarifas
TARIFA_AMBULATORIO = 'ambulatorio'
TARIFA_CLINICA = 'clinica'


def _f(valor):
    try:
        return float(valor if valor is not None else 0)
    except (TypeError, ValueError):
        return 0.0


def leer_importe(texto, separador_miles=True):
    """
    Lee un importe tecleado a mano. Devuelve None si no se entiende.

    El problema esta en el punto: en pesos "40.000" son cuarenta mil, pero en
    dolares "40.00" son cuarenta. Se resuelve por el numero de cifras que
    siguen al punto: tres significa separador de miles. Confundirlos
    multiplica o divide un precio por mil sin que nadie lo note.

    Args:
        separador_miles: False cuando se teclea en una moneda con centavos
            (dolares), donde un punto suele ser decimal.

    Acepta 40.000,50 / 40000.50 / 40000,50 / 40 000.
    """
    if texto is None:
        return None
    limpio = str(texto).strip().replace(' ', '').replace('\u00a0', '')
    if not limpio:
        return 0.0

    negativo = limpio.startswith('-')
    if negativo:
        limpio = limpio[1:]

    if ',' in limpio and '.' in limpio:
        # El ultimo separador que aparece es el decimal
        if limpio.rfind(',') > limpio.rfind('.'):
            limpio = limpio.replace('.', '').replace(',', '.')
        else:
            limpio = limpio.replace(',', '')
    elif ',' in limpio:
        # Una coma con tres cifras detras tambien puede ser de miles
        ent, _, dec = limpio.rpartition(',')
        limpio = (ent + dec) if (len(dec) == 3 and separador_miles and ent) \
            else limpio.replace(',', '.')
    elif limpio.count('.') > 1:
        limpio = limpio.replace('.', '')
    elif '.' in limpio:
        ent, _, dec = limpio.partition('.')
        if len(dec) == 3 and separador_miles and ent:
            limpio = ent + dec

    try:
        valor = float(limpio)
    except ValueError:
        return None
    return -valor if negativo else valor


def convertir_a_usd(valor, tasa):
    """
    Pasa a dolares un importe tecleado en otra moneda.

    La tasa es cuantas unidades de esa moneda vale un dolar. Sin tasa (o con
    tasa cero) se devuelve el valor tal cual: es lo que corresponde cuando ya
    venia en dolares.
    """
    try:
        valor = float(valor)
        tasa = float(tasa or 0)
    except (TypeError, ValueError):
        return 0.0
    if tasa <= 0:
        return round(valor, 4)
    # Cuatro decimales: con dos, un precio en pesos se desviaba hasta 20 COP
    # al convertirlo y volverlo a leer.
    return round(valor / tasa, 4)


def convertir_desde_usd(valor_usd, tasa):
    """Pasa un importe en dolares a la moneda de la tasa."""
    try:
        valor_usd = float(valor_usd)
        tasa = float(tasa or 0)
    except (TypeError, ValueError):
        return 0.0
    return round(valor_usd * tasa, 4) if tasa > 0 else round(valor_usd, 4)


def tarifa_de(tipo_servicio):
    """
    Que tarifa corresponde a una procedencia.

    Depende del area, no de quien pague: el asegurado y el particular que
    entran por emergencia van los dos por el convenio de la clinica.
    """
    return TARIFA_CLINICA if es_area_clinica(tipo_servicio) else TARIFA_AMBULATORIO


def precio_aplicable(prueba, tipo_servicio):
    """
    Cuanto se le factura a la solicitud por esta prueba.

    Args:
        prueba: dict con Precio y, si existen, PrecioConvenio/PrecioClinica.
        tipo_servicio: la procedencia de la solicitud.

    En los casos de clinica se cobra el precio de convenio, que es lo que la
    clinica le va a pagar al laboratorio. Si esa prueba no tiene convenio
    cargado se recurre al precio ambulatorio: es preferible cobrar de menos
    que dejar la prueba en cero y regalarla, pero conviene revisarlo, y por
    eso precio_detalle() lo marca como pendiente.
    """
    base = _f(prueba.get('Precio'))
    # Cuatro decimales, los mismos con los que se guarda: redondear aqui a
    # dos centavos de dolar desviaba el precio hasta 15 COP por prueba, y un
    # cultivo cargado como 60.000 COP se facturaba a 59.985.
    if tarifa_de(tipo_servicio) == TARIFA_AMBULATORIO:
        return round(base, 4)
    convenio = _f(prueba.get(COL_CONVENIO))
    return round(convenio if convenio > 0 else base, 4)


def precio_detalle(prueba, tipo_servicio):
    """
    El precio aplicable y el porque, para poder mostrarlo o avisar.

    Devuelve un dict con la tarifa usada, el importe, si hubo que recurrir al
    precio ambulatorio por falta de convenio, y cuanto cobraria la clinica al
    paciente.
    """
    base = _f(prueba.get('Precio'))
    convenio = _f(prueba.get(COL_CONVENIO))
    clinica = _f(prueba.get(COL_CLINICA))
    tarifa = tarifa_de(tipo_servicio)

    if tarifa == TARIFA_AMBULATORIO:
        return {
            'tarifa': tarifa,
            'precio': round(base, 4),
            'sin_convenio': False,
            'precio_paciente': round(base, 4),
            'comision_clinica': 0.0,
        }

    sin_convenio = convenio <= 0
    aplicado = base if sin_convenio else convenio
    return {
        'tarifa': tarifa,
        'precio': round(aplicado, 4),
        'sin_convenio': sin_convenio,
        'precio_paciente': round(clinica if clinica > 0 else aplicado, 4),
        'comision_clinica': round(max(0.0, clinica - aplicado), 4) if clinica > 0 else 0.0,
    }


def comision(prueba):
    """Lo que se queda la clinica por esta prueba, o 0 si no aplica."""
    clinica = _f(prueba.get(COL_CLINICA))
    convenio = _f(prueba.get(COL_CONVENIO))
    if clinica <= 0 or convenio <= 0:
        return 0.0
    return round(max(0.0, clinica - convenio), 4)


def porcentaje_comision(prueba):
    """La comision como porcentaje de lo que cobra la clinica al paciente."""
    clinica = _f(prueba.get(COL_CLINICA))
    if clinica <= 0:
        return 0.0
    return round(comision(prueba) / clinica * 100, 1)


class GestorTarifas:
    """Lee y mantiene las tres tarifas de cada prueba."""

    def __init__(self, db):
        self.db = db
        self._columnas_ok = False

    def asegurar_columnas(self):
        """
        Crea PrecioClinica y PrecioConvenio si faltan.

        Se llama al abrir la lista de precios y antes de valorar una
        solicitud, para que una instalacion que venia de antes quede al dia
        sin intervencion.
        """
        if self._columnas_ok:
            return
        for col in (COL_CLINICA, COL_CONVENIO):
            try:
                self.db.query_one("SELECT TOP 1 " + col + " FROM Pruebas")
                continue
            except Exception:
                pass
            try:
                self.db.execute(
                    "ALTER TABLE Pruebas ADD COLUMN " + col + " CURRENCY")
                _log.info("Columna de tarifas creada: %s", col)
            except Exception as e:
                _log.warning("No se pudo crear la columna '%s': %s", col, e)
        self._columnas_ok = True

    def tiene_columnas(self):
        try:
            self.db.query_one("SELECT TOP 1 " + COL_CONVENIO + " FROM Pruebas")
            return True
        except Exception:
            return False

    def obtener_prueba(self, prueba_id):
        """Una prueba con sus tres precios, o None."""
        campos = "PruebaID, CodigoPrueba, NombrePrueba, Precio"
        if self.tiene_columnas():
            campos += ", " + COL_CLINICA + ", " + COL_CONVENIO
        try:
            return self.db.query_one(
                "SELECT " + campos + " FROM Pruebas WHERE PruebaID=" + str(int(prueba_id)))
        except Exception as e:
            _log.error("No se pudo leer la prueba %s: %s", prueba_id, e)
            return None

    def precio_para(self, prueba_id, tipo_servicio):
        """Cuanto facturar por esta prueba en una solicitud de esa procedencia."""
        prueba = self.obtener_prueba(prueba_id)
        if not prueba:
            return 0.0
        return precio_aplicable(prueba, tipo_servicio)

    def listar_baremo(self, solo_activas=True, area_id=None, texto=None):
        """
        El baremo completo: cada prueba con sus tres precios y la comision.

        Ordenado por area y nombre, que es como se lee un baremo.
        """
        tiene = self.tiene_columnas()
        campos = ["p.PruebaID", "p.CodigoPrueba", "p.NombrePrueba",
                  "p.Precio", "p.Activo", "a.NombreArea"]
        if tiene:
            campos.append("p." + COL_CLINICA)
            campos.append("p." + COL_CONVENIO)

        sql = ("SELECT " + ", ".join(campos) + " FROM Pruebas p "
               "LEFT JOIN Areas a ON p.AreaID = a.AreaID WHERE 1=1")
        if solo_activas:
            sql += " AND p.Activo = True"
        if area_id:
            sql += " AND p.AreaID = " + str(int(area_id))
        if texto:
            seguro = str(texto).replace("'", "''").replace('%', '')
            sql += (" AND (p.NombrePrueba LIKE '%" + seguro + "%'"
                    " OR p.CodigoPrueba LIKE '%" + seguro + "%')")
        sql += " ORDER BY a.NombreArea, p.NombrePrueba"

        try:
            filas = self.db.query(sql) or []
        except Exception as e:
            _log.error("No se pudo leer el baremo: %s", e)
            return []

        for f in filas:
            f['_comision'] = comision(f)
            f['_pct_comision'] = porcentaje_comision(f)
            f['_sin_convenio'] = _f(f.get(COL_CONVENIO)) <= 0
        return filas

    def guardar_precios(self, prueba_id, precio=None, precio_clinica=None,
                        precio_convenio=None):
        """
        Actualiza las tarifas de una prueba. Solo escribe lo que se le pasa.

        Devuelve (exito, mensaje).
        """
        self.asegurar_columnas()
        sets = []

        for valor, columna, etiqueta in (
                (precio, 'Precio', 'ambulatorio'),
                (precio_clinica, COL_CLINICA, 'de clinica'),
                (precio_convenio, COL_CONVENIO, 'de convenio')):
            if valor is None:
                continue
            try:
                # Cuatro decimales, no dos: un precio tecleado en pesos se
                # guarda convertido a dolares, y redondear a dos centavos
                # desviaba hasta 20 COP por prueba. El campo es CURRENCY, que
                # guarda cuatro decimales exactos.
                v = round(float(valor), 4)
            except (TypeError, ValueError):
                return False, "El precio " + etiqueta + " no es un importe valido."
            if v < 0:
                return False, "El precio " + etiqueta + " no puede ser negativo."
            sets.append(columna + "=" + str(v))

        if not sets:
            return False, "No se indico ningun precio."

        try:
            self.db.execute("UPDATE Pruebas SET " + ", ".join(sets)
                            + " WHERE PruebaID=" + str(int(prueba_id)))
            return True, "Precios actualizados."
        except Exception as e:
            _log.error("No se pudieron guardar los precios de %s: %s", prueba_id, e)
            return False, "No se pudieron guardar los precios: " + str(e)

    def resumen(self, solo_activas=True):
        """Cifras para encabezar la pantalla del baremo."""
        filas = self.listar_baremo(solo_activas=solo_activas)
        con_convenio = [f for f in filas if not f['_sin_convenio']]
        sin_precio = [f for f in filas if _f(f.get('Precio')) <= 0]
        return {
            'total': len(filas),
            'con_convenio': len(con_convenio),
            'sin_convenio': len(filas) - len(con_convenio),
            'sin_precio_base': len(sin_precio),
            'comision_media': round(
                sum(f['_pct_comision'] for f in con_convenio) / len(con_convenio), 1)
            if con_convenio else 0.0,
        }


def crear_gestor_tarifas(db):
    """Fabrica, al estilo del resto de modulos."""
    return GestorTarifas(db)

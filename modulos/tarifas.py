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

# Las mismas tres tarifas, pero del perfil entero: la oferta de paquete.
# Un perfil vale por defecto lo que suman sus pruebas, pero se pactan
# paquetes por debajo de esa suma (el perfil 20 sale en 120.000 donde sus
# catorce pruebas sueltas suman 152.000). Cargado aqui, ese precio manda.
COL_PERFIL_BASE = 'PrecioPerfil'
COL_PERFIL_CLINICA = 'PrecioClinicaPerfil'
COL_PERFIL_CONVENIO = 'PrecioConvenioPerfil'

# Tarifas
TARIFA_AMBULATORIO = 'ambulatorio'
TARIFA_CLINICA = 'clinica'


def _f(valor):
    try:
        return float(valor if valor is not None else 0)
    except (TypeError, ValueError):
        return 0.0


def _cargado(prueba, columna):
    """
    El importe si esta cargado, None si nunca se puso.

    Un cero puesto a proposito no es lo mismo que un precio sin cargar. Hay
    pruebas que se incluyen sin coste, como las relaciones que salen de
    dividir dos resultados ya cobrados; sin esta distincion el sistema las
    tomaria por pendientes de tarifar y avisaria cada vez que se pidieran.

    En la base, sin cargar es NULL; gratis a proposito es 0.
    """
    if columna not in prueba:
        return None
    valor = prueba.get(columna)
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


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

    Un convenio puesto en cero SI se respeta: es una prueba que se incluye
    sin coste, no una que falte por tarifar.
    """
    base = _f(prueba.get('Precio'))
    # Cuatro decimales, los mismos con los que se guarda: redondear aqui a
    # dos centavos de dolar desviaba el precio hasta 15 COP por prueba, y un
    # cultivo cargado como 60.000 COP se facturaba a 59.985.
    if tarifa_de(tipo_servicio) == TARIFA_AMBULATORIO:
        return round(base, 4)
    convenio = _cargado(prueba, COL_CONVENIO)
    return round(base if convenio is None else convenio, 4)


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

    # Pendiente de tarifar es no tener valor; un cero deliberado esta tarifado
    convenio_cargado = _cargado(prueba, COL_CONVENIO)
    sin_convenio = convenio_cargado is None
    aplicado = base if sin_convenio else convenio_cargado
    return {
        'tarifa': tarifa,
        'precio': round(aplicado, 4),
        'sin_convenio': sin_convenio,
        'precio_paciente': round(clinica if clinica > 0 else aplicado, 4),
        'comision_clinica': round(max(0.0, clinica - aplicado), 4) if clinica > 0 else 0.0,
    }


def precio_paquete(perfil, tipo_servicio):
    """
    Lo que cuesta el perfil como paquete, o None si no hay oferta cargada.

    Sin oferta el perfil vale lo que suman sus pruebas, que es el
    comportamiento de siempre.

    Cada tarifa tiene SU oferta y no se cubren entre si. Si esta cargada la
    ambulatoria pero no la de convenio, un paciente de hospitalizacion no se
    factura con el paquete de la calle: se le cobra a la clinica la suma de
    los precios de convenio, que es el precio entero. Prestar aqui la oferta
    ambulatoria le reclamaria a la clinica 120.000 donde le corresponden
    218.000, y ese es justo el error que este modulo existe para evitar.

    Un cero no es un paquete gratis: es la forma natural de borrar la oferta
    desde la pantalla de precios, y asi se entiende.
    """
    columna = (COL_PERFIL_BASE if tarifa_de(tipo_servicio) == TARIFA_AMBULATORIO
               else COL_PERFIL_CONVENIO)
    valor = _cargado(perfil, columna)
    if valor is None or valor <= 0:
        return None
    return round(valor, 4)


def prorratear(precios, total):
    """
    Reparte el precio del paquete entre las pruebas que lo componen.

    La solicitud se factura linea a linea: el total sale de sumar lo que
    vale cada prueba, y de ahi pasa a la cuenta por cobrar y al corte. Para
    que un perfil con oferta cueste lo pactado sin romper esa cadena, cada
    linea se ajusta en la misma proporcion en vez de meter un descuento
    aparte que habria que arrastrar por los cuatro sitios.

    Repartir en proporcion y no a partes iguales mantiene el detalle
    defendible: si la clinica pregunta por que la hematologia aparece en
    15.789 y no en 20.000, la respuesta es que el paquete rebaja un 21% y
    cada prueba lo lleva encima.

    La ultima linea absorbe el resto del redondeo, asi que la suma cuadra
    con el paquete al centimo. Sin eso, catorce redondeos de cuatro
    decimales dejan la solicitud descuadrada contra lo que se pacto.
    """
    valores = [_f(x) for x in precios]
    if not valores:
        return []
    objetivo = round(_f(total), 4)
    suma = sum(valores)
    if suma <= 0:
        # Sin precios individuales solo cabe repartir a partes iguales
        ajustados = [round(objetivo / len(valores), 4)] * len(valores)
    else:
        ajustados = [round(v * objetivo / suma, 4) for v in valores]
    ajustados[-1] = round(ajustados[-1] + (objetivo - sum(ajustados)), 4)
    return ajustados


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
        self._columnas_perfil_ok = False

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

    def asegurar_columnas_perfiles(self):
        """
        Crea las tres columnas de oferta de paquete en Perfiles si faltan.

        Quedan en NULL, que es 'sin oferta': hasta que alguien cargue un
        paquete, cada perfil sigue costando lo que suman sus pruebas, tal
        como venia funcionando.
        """
        if self._columnas_perfil_ok:
            return
        for col in (COL_PERFIL_BASE, COL_PERFIL_CLINICA, COL_PERFIL_CONVENIO):
            try:
                self.db.query_one("SELECT TOP 1 " + col + " FROM Perfiles")
                continue
            except Exception:
                pass
            try:
                self.db.execute(
                    "ALTER TABLE Perfiles ADD COLUMN " + col + " CURRENCY")
                _log.info("Columna de oferta de perfil creada: %s", col)
            except Exception as e:
                _log.warning("No se pudo crear la columna '%s': %s", col, e)
        self._columnas_perfil_ok = True

    def tiene_columnas_perfiles(self):
        try:
            self.db.query_one(
                "SELECT TOP 1 " + COL_PERFIL_CONVENIO + " FROM Perfiles")
            return True
        except Exception:
            return False

    def obtener_perfil(self, perfil_id):
        """Un perfil con su oferta de paquete, o None."""
        campos = "PerfilID, CodigoPerfil, NombrePerfil, Descripcion, Activo"
        if self.tiene_columnas_perfiles():
            campos += (", " + COL_PERFIL_BASE + ", " + COL_PERFIL_CLINICA
                       + ", " + COL_PERFIL_CONVENIO)
        try:
            return self.db.query_one(
                "SELECT " + campos + " FROM Perfiles WHERE PerfilID="
                + str(int(perfil_id)))
        except Exception as e:
            _log.error("No se pudo leer el perfil %s: %s", perfil_id, e)
            return None

    def pruebas_de_perfil(self, perfil_id, solo_activas=True):
        """
        Las pruebas del perfil con sus tres precios.

        Solo las activas, que son las que de verdad entran en la solicitud
        cuando se pide el perfil. Contar aqui una prueba dada de baja pondria
        en el baremo un precio que nunca se llega a cobrar.
        """
        campos = "p.PruebaID, p.CodigoPrueba, p.NombrePrueba, p.Precio"
        if self.tiene_columnas():
            campos += ", p." + COL_CLINICA + ", p." + COL_CONVENIO
        sql = ("SELECT " + campos + " FROM PruebasEnPerfil pp "
               "INNER JOIN Pruebas p ON pp.PruebaID = p.PruebaID "
               "WHERE pp.PerfilID = " + str(int(perfil_id)))
        if solo_activas:
            sql += " AND p.Activo = True"
        try:
            return self.db.query(sql) or []
        except Exception as e:
            _log.warning("Perfil %s: no se pudieron leer sus pruebas: %s",
                         perfil_id, e)
            return []

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
            # Mismo criterio que el motor de cobro (ver precio_detalle): sin
            # tarifar es NO TENER VALOR. Un cero puesto a proposito -la
            # relacion PSA sale de dividir dos resultados ya cobrados- esta
            # tarifado, y marcarlo como pendiente pondria en el documento que
            # se entrega en la clinica que hay algo por acordar donde no lo
            # hay.
            cargado = _cargado(f, COL_CONVENIO)
            f['_sin_convenio'] = cargado is None
            f['_sin_coste'] = cargado == 0
        return filas

    def listar_perfiles(self, solo_activos=True):
        """
        Los perfiles con lo que cuesta cada uno, para el baremo.

        Un perfil vale lo que suman sus pruebas, salvo que tenga cargada una
        oferta de paquete: entonces vale el paquete. Lo que sale aqui es el
        precio que se va a cobrar de verdad, no la suma teorica, para que el
        papel que se entrega en la clinica diga la misma cifra que la
        solicitud.

        Devuelve filas con la misma forma que listar_baremo() mas:
            n_pruebas     cuantas pruebas incluye
            es_perfil     para distinguirlas al pintar
            es_oferta     True si el precio viene de un paquete pactado
            suma_*        lo que sumarian las pruebas sueltas
        """
        tiene = self.tiene_columnas()
        tiene_perf = self.tiene_columnas_perfiles()

        campos = "PerfilID, CodigoPerfil, NombrePerfil, Descripcion"
        if tiene_perf:
            campos += (", " + COL_PERFIL_BASE + ", " + COL_PERFIL_CLINICA
                       + ", " + COL_PERFIL_CONVENIO)
        sql_perfiles = "SELECT " + campos + " FROM Perfiles"
        if solo_activos:
            sql_perfiles += " WHERE Activo = True"
        sql_perfiles += " ORDER BY NombrePerfil"

        try:
            perfiles = self.db.query(sql_perfiles) or []
        except Exception as e:
            _log.error("No se pudieron leer los perfiles: %s", e)
            return []

        filas = []
        for perf in perfiles:
            pruebas = self.pruebas_de_perfil(perf['PerfilID'])
            if not pruebas:
                continue

            suma_base = sum(_f(x.get('Precio')) for x in pruebas)
            suma_clinica = (sum(_f(x.get(COL_CLINICA)) for x in pruebas)
                            if tiene else 0.0)
            # El convenio de cada prueba, con el respaldo al ambulatorio de
            # las que no lo tengan: es lo que se facturaria de verdad.
            suma_convenio = sum(precio_aplicable(x, 'Hospitalizado Asegurado')
                                for x in pruebas)

            paq_base = precio_paquete(perf, 'Ambulatorio')
            paq_convenio = precio_paquete(perf, 'Hospitalizado Asegurado')
            paq_clinica = _cargado(perf, COL_PERFIL_CLINICA)
            if paq_clinica is not None and paq_clinica <= 0:
                paq_clinica = None

            base = suma_base if paq_base is None else paq_base
            convenio = suma_convenio if paq_convenio is None else paq_convenio
            # Lo que la clinica le cobra al paciente es informativo: si hay
            # paquete de convenio pero nadie cargo lo que cobra la clinica,
            # se muestra la suma para no inventar una comision.
            clinica = suma_clinica if paq_clinica is None else paq_clinica

            sin_conv = (any(_cargado(x, COL_CONVENIO) is None for x in pruebas)
                        if tiene else True)
            sin_coste = convenio == 0 and not sin_conv

            fila = {
                'PruebaID': None,
                'CodigoPrueba': perf.get('CodigoPerfil') or '',
                'NombrePrueba': perf.get('NombrePerfil') or '',
                'NombreArea': 'PERFILES',
                'Precio': round(base, 4),
                COL_CLINICA: round(clinica, 4),
                COL_CONVENIO: round(convenio, 4),
                'Activo': True,
                'PerfilID': perf['PerfilID'],
                'n_pruebas': len(pruebas),
                'es_perfil': True,
                'es_oferta': paq_base is not None or paq_convenio is not None,
                'suma_base': round(suma_base, 4),
                'suma_clinica': round(suma_clinica, 4),
                'suma_convenio': round(suma_convenio, 4),
            }
            fila['_comision'] = (round(max(0.0, clinica - convenio), 4)
                                 if clinica else 0.0)
            fila['_pct_comision'] = (round(fila['_comision'] / clinica * 100, 1)
                                     if clinica else 0.0)
            fila['_sin_convenio'] = sin_conv
            fila['_sin_coste'] = sin_coste
            filas.append(fila)
        return filas

    def guardar_precios_perfil(self, perfil_id, precio=None,
                               precio_clinica=None, precio_convenio=None):
        """
        Carga la oferta de paquete de un perfil. Solo escribe lo que recibe.

        Un cero borra esa oferta: el perfil vuelve a costar lo que suman sus
        pruebas. Es lo que espera quien vacia la casilla en la pantalla de
        precios, y no existe un paquete que valga cero de verdad.

        Devuelve (exito, mensaje).
        """
        self.asegurar_columnas_perfiles()
        sets = []

        for valor, columna, etiqueta in (
                (precio, COL_PERFIL_BASE, 'ambulatorio'),
                (precio_clinica, COL_PERFIL_CLINICA, 'de clinica'),
                (precio_convenio, COL_PERFIL_CONVENIO, 'de convenio')):
            if valor is None:
                continue
            try:
                # Cuatro decimales, los mismos que las pruebas: el precio se
                # teclea en pesos y se guarda en dolares.
                v = round(float(valor), 4)
            except (TypeError, ValueError):
                return False, "El precio " + etiqueta + " no es un importe valido."
            if v < 0:
                return False, "El precio " + etiqueta + " no puede ser negativo."
            sets.append(columna + "=" + ("NULL" if v == 0 else str(v)))

        if not sets:
            return False, "No se indico ningun precio."

        try:
            self.db.execute("UPDATE Perfiles SET " + ", ".join(sets)
                            + " WHERE PerfilID=" + str(int(perfil_id)))
            return True, "Oferta del perfil actualizada."
        except Exception as e:
            _log.error("No se pudo guardar la oferta del perfil %s: %s",
                       perfil_id, e)
            return False, "No se pudo guardar la oferta: " + str(e)

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

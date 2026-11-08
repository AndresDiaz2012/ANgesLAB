# -*- coding: utf-8 -*-
"""
================================================================================
MAESTROS FISCALES - CLIENTE, PROVEEDOR Y REGIMEN DE IVA DEL SERVICIO
================================================================================
Fase 1 de la especificacion del ERP administrativo: los datos que todo
documento fiscal necesita y que hasta ahora no tenian donde vivir.

CLIENTE NO ES PACIENTE

La factura va a nombre de quien la paga, que no siempre es quien se hizo la
prueba: un padre paga la de su hijo, una empresa la de sus empleados, una
aseguradora la de sus afiliados. Hasta ahora el programa facturaba al
paciente porque no tenia otro sitio de donde sacar un RIF y un domicilio
fiscal. Aqui nace ese sitio: la tabla Clientes, y ClientePacientes para
saber a quien se le suele facturar cada paciente.

EL RIF SE COMPRUEBA ENTERO

validar_rif() en facturacion_fiscal solo mira el formato. Un RIF con un
digito cambiado tiene formato correcto y es de otra persona -o de nadie-, y
una factura a un RIF inexistente no le sirve al cliente para deducir nada.
rif_valido() comprueba tambien el digito verificador, con el algoritmo del
SENIAT (modulo 11, pesos 4-3-2-7-6-5-4-3-2 sobre letra y ocho digitos).

EL REGIMEN DE IVA ES DE CADA SERVICIO

El servicio del laboratorio esta exento (TSJ, sentencia 1505/2003), pero un
frasco recolector que se vende esta gravado al 16%. Con una sola tasa por
laboratorio no se podia facturar las dos cosas juntas. Cada prueba lleva
ahora RegimenIVA: 'Exento', 'Gravado' o vacio. Vacio significa "lo que diga
la configuracion del laboratorio", de modo que una instalacion que no toque
nada factura exactamente igual que antes.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import re
from datetime import datetime
from decimal import Decimal

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.maestros_fiscales')
except Exception:  # pragma: no cover - respaldo si falta el modulo
    import logging as _logging
    _log = _logging.getLogger('angeslab.maestros_fiscales')


# ══════════════════════════════════════════════════════════════════════════
#  RIF
# ══════════════════════════════════════════════════════════════════════════
# Valor de la letra en el calculo del digito verificador
_VALOR_LETRA = {'V': 1, 'E': 2, 'J': 3, 'P': 4, 'G': 5}
_PESOS = (4, 3, 2, 7, 6, 5, 4, 3, 2)

# Letras que corresponden a una persona juridica o un ente publico
LETRAS_JURIDICAS = ('J', 'G')


def normalizar_rif(texto):
    """
    El RIF en la forma que se imprime: J-12345678-9. None si no se entiende.

    Acepta lo que la gente escribe: 'j123456789', 'J-12345678-9',
    'J 12.345.678 9'. Si los digitos son menos de ocho se rellenan con ceros
    a la izquierda, que es como el SENIAT los numera.
    """
    if texto is None:
        return None
    # Con el digito separado (J-1234567-0) se sabe donde termina el cuerpo,
    # asi que se puede rellenar con ceros sin adivinar
    separado = re.match(r'^\s*([VEJPGvejpg])[\s\-]*([\d\.]{1,10})[\s\-/]+(\d)\s*$',
                        str(texto))
    if separado:
        cuerpo = separado.group(2).replace('.', '')
        if 1 <= len(cuerpo) <= 8:
            return '%s-%s-%s' % (separado.group(1).upper(), cuerpo.zfill(8),
                                 separado.group(3))
        return None
    limpio = re.sub(r'[\s\.\-_/]', '', str(texto)).upper()
    m = re.match(r'^([VEJPG])(\d{1,9})$', limpio)
    if not m:
        return None
    letra, numeros = m.group(1), m.group(2)
    if len(numeros) < 9:
        # Sin digito verificador no hay RIF completo
        return None
    cuerpo, digito = numeros[:-1], numeros[-1]
    return '%s-%s-%s' % (letra, cuerpo.zfill(8), digito)


def digito_verificador(letra, cuerpo):
    """El digito verificador que corresponde a una letra y ocho digitos."""
    valores = [_VALOR_LETRA[letra.upper()]] + [int(c) for c in str(cuerpo).zfill(8)]
    suma = sum(v * p for v, p in zip(valores, _PESOS))
    resto = 11 - (suma % 11)
    return 0 if resto >= 10 else resto


def rif_valido(texto):
    """True si el RIF tiene formato correcto Y su digito verificador cuadra."""
    rif = normalizar_rif(texto)
    if not rif:
        return False
    letra, cuerpo, digito = rif.split('-')
    return digito_verificador(letra, cuerpo) == int(digito)


def normalizar_cedula(texto):
    """La cedula como V-12345678. None si no se entiende."""
    if texto is None:
        return None
    limpio = re.sub(r'[\s\.\-_]', '', str(texto)).upper()
    m = re.match(r'^([VE])?(\d{5,9})$', limpio)
    if not m:
        return None
    return '%s-%s' % (m.group(1) or 'V', m.group(2))


# ══════════════════════════════════════════════════════════════════════════
#  Catalogos cerrados
# ══════════════════════════════════════════════════════════════════════════
TIPOS_CLIENTE = ('Natural', 'Juridica', 'Aseguradora', 'Convenio')
TIPOS_CONTRIBUYENTE = ('Ordinario', 'Especial', 'No contribuyente')
CONDICIONES_PAGO = ('Contado', 'Credito')

# Tipo de persona del proveedor: decide que tabla del Decreto 1.808 aplica
TIPOS_PERSONA = ('PNR', 'PNNR', 'PJD', 'PJND')
DESCRIPCION_TIPO_PERSONA = {
    'PNR': 'Persona natural residente',
    'PNNR': 'Persona natural no residente',
    'PJD': 'Persona juridica domiciliada',
    'PJND': 'Persona juridica no domiciliada',
}

REGIMENES_IVA = ('Exento', 'Gravado')
ALICUOTA_GENERAL = Decimal('16')


def _esc(valor, limite=255):
    return str('' if valor is None else valor).replace("'", "''")[:limite]


def _fecha_access(momento=None):
    return (momento or datetime.now()).strftime('#%m/%d/%Y %H:%M:%S#')


def _tiene_columna(db, tabla, columna):
    try:
        db.query("SELECT TOP 1 [%s] FROM [%s]" % (columna, tabla))
        return True
    except Exception:
        return False


def _tabla_existe(db, tabla):
    try:
        db.query("SELECT TOP 1 * FROM [%s]" % tabla)
        return True
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════
#  Esquema
# ══════════════════════════════════════════════════════════════════════════
DDL_CLIENTES = (
    "CREATE TABLE [Clientes] ("
    "[ClienteID] COUNTER PRIMARY KEY, "
    "[TipoCliente] TEXT(20), "
    "[Documento] TEXT(20), "
    "[RazonSocial] TEXT(200), "
    "[DomicilioFiscal] TEXT(255), "
    "[Telefono] TEXT(50), "
    "[Email] TEXT(100), "
    "[TipoContribuyente] TEXT(20), "
    "[CondicionPago] TEXT(10), "
    "[DiasCredito] INTEGER, "
    "[LimiteCredito] DOUBLE, "
    "[ListaPreciosID] INTEGER, "
    "[SeguroID] INTEGER, "
    "[Observaciones] TEXT(255), "
    "[Activo] BIT, "
    "[FechaCreacion] DATETIME)")

DDL_CLIENTE_PACIENTES = (
    "CREATE TABLE [ClientePacientes] ("
    "[ClientePacienteID] COUNTER PRIMARY KEY, "
    "[ClienteID] INTEGER, "
    "[PacienteID] INTEGER, "
    "[Vinculo] TEXT(50), "
    "[PorDefecto] BIT, "
    "[FechaCreacion] DATETIME)")

# Columnas que la fase 1 anade a tablas que ya existen
COLUMNAS_PROVEEDORES = {
    'TipoPersona': 'TEXT(4)',
    'PorcentajeRetencionIVA': 'DOUBLE',
    'ConceptoISLR': 'TEXT(50)',
    'DiasCredito': 'INTEGER',
}
COLUMNAS_PRUEBAS = {
    'RegimenIVA': 'TEXT(10)',
    'AlicuotaIVA': 'DOUBLE',
}


def asegurar_esquema(db):
    """
    Crea lo que falte. Se puede llamar en cada arranque: no toca lo que ya
    existe y no borra nada. Devuelve la lista de cambios hechos.
    """
    hechos = []
    for tabla, ddl in (('Clientes', DDL_CLIENTES),
                       ('ClientePacientes', DDL_CLIENTE_PACIENTES)):
        if _tabla_existe(db, tabla):
            continue
        try:
            db.execute(ddl)
            hechos.append('tabla %s' % tabla)
        except Exception as e:
            _log.error("No se pudo crear la tabla %s: %s", tabla, e)

    for tabla, columnas in (('Proveedores', COLUMNAS_PROVEEDORES),
                            ('Pruebas', COLUMNAS_PRUEBAS)):
        if not _tabla_existe(db, tabla):
            continue
        for col, tipo in columnas.items():
            if _tiene_columna(db, tabla, col):
                continue
            try:
                db.execute("ALTER TABLE [%s] ADD COLUMN [%s] %s" % (tabla, col, tipo))
                hechos.append('%s.%s' % (tabla, col))
            except Exception as e:
                _log.error("No se pudo anadir %s.%s: %s", tabla, col, e)

    if hechos:
        _log.info("Maestros fiscales: %s", ', '.join(hechos))
    return hechos


# ══════════════════════════════════════════════════════════════════════════
#  Clientes
# ══════════════════════════════════════════════════════════════════════════
class ErrorMaestro(ValueError):
    """Un dato que no se puede guardar. El mensaje es para el usuario."""


def documento_cliente(tipo_cliente, documento):
    """
    El documento normalizado, o ErrorMaestro si no sirve.

    Una persona juridica, una aseguradora o un convenio se identifican con
    RIF, y el RIF tiene que ser valido. Una persona natural puede dar su RIF
    o, si no lo tiene, su cedula.
    """
    texto = str(documento or '').strip()
    if not texto:
        raise ErrorMaestro('El RIF o la cedula es obligatorio.')
    rif = normalizar_rif(texto)
    if rif:
        if not rif_valido(rif):
            raise ErrorMaestro('El RIF %s no es valido: el digito verificador no '
                               'corresponde. Reviselo contra el documento.' % rif)
        if tipo_cliente != 'Natural' and rif[0] not in LETRAS_JURIDICAS:
            raise ErrorMaestro('Un cliente de tipo %s se identifica con un RIF J o G.'
                               % tipo_cliente)
        return rif
    if tipo_cliente == 'Natural':
        cedula = normalizar_cedula(texto)
        if cedula:
            return cedula
    raise ErrorMaestro('"%s" no es un RIF%s valido.'
                       % (texto, ' ni una cedula' if tipo_cliente == 'Natural' else ''))


class GestorClientes:
    """Alta, edicion y consulta del cliente fiscal."""

    def __init__(self, db):
        self.db = db

    def _validar(self, datos, cliente_id=None):
        tipo = datos.get('TipoCliente') or 'Natural'
        if tipo not in TIPOS_CLIENTE:
            raise ErrorMaestro('Tipo de cliente desconocido: %s' % tipo)
        razon = str(datos.get('RazonSocial') or '').strip()
        if not razon:
            raise ErrorMaestro('La razon social o el nombre es obligatorio.')
        documento = documento_cliente(tipo, datos.get('Documento'))

        existente = self.buscar_por_documento(documento)
        if existente and existente.get('ClienteID') != cliente_id:
            raise ErrorMaestro('Ya existe un cliente con el documento %s: %s.'
                               % (documento, existente.get('RazonSocial')))

        contrib = datos.get('TipoContribuyente') or (
            'No contribuyente' if tipo == 'Natural' and documento[0] in 'VE'
            and documento.count('-') == 1 else 'Ordinario')
        if contrib not in TIPOS_CONTRIBUYENTE:
            raise ErrorMaestro('Tipo de contribuyente desconocido: %s' % contrib)

        condicion = datos.get('CondicionPago') or 'Contado'
        if condicion not in CONDICIONES_PAGO:
            raise ErrorMaestro('Condicion de pago desconocida: %s' % condicion)
        try:
            dias = int(datos.get('DiasCredito') or 0)
            limite = float(datos.get('LimiteCredito') or 0)
        except (TypeError, ValueError):
            raise ErrorMaestro('Los dias y el limite de credito tienen que ser numeros.')
        if dias < 0 or limite < 0:
            raise ErrorMaestro('Los dias y el limite de credito no pueden ser negativos.')
        if condicion == 'Contado':
            dias, limite = 0, 0.0

        domicilio = str(datos.get('DomicilioFiscal') or '').strip()
        if tipo != 'Natural' and not domicilio:
            # La factura a una persona juridica sin domicilio fiscal no cumple
            raise ErrorMaestro('El domicilio fiscal es obligatorio para un cliente %s.'
                               % tipo.lower())

        return {
            'TipoCliente': tipo, 'Documento': documento, 'RazonSocial': razon,
            'DomicilioFiscal': domicilio, 'Telefono': datos.get('Telefono'),
            'Email': datos.get('Email'), 'TipoContribuyente': contrib,
            'CondicionPago': condicion, 'DiasCredito': dias,
            'LimiteCredito': limite, 'ListaPreciosID': datos.get('ListaPreciosID'),
            'SeguroID': datos.get('SeguroID'),
            'Observaciones': datos.get('Observaciones'),
        }

    @staticmethod
    def _sql_valor(campo, valor):
        if campo in ('DiasCredito',):
            return str(int(valor or 0))
        if campo in ('LimiteCredito',):
            return repr(float(valor or 0))
        if campo in ('ListaPreciosID', 'SeguroID'):
            return 'NULL' if valor in (None, '') else str(int(valor))
        return "'%s'" % _esc(valor)

    def crear(self, datos):
        """Guarda un cliente nuevo. Devuelve su ClienteID."""
        fila = self._validar(datos)
        campos = list(fila.keys())
        valores = [self._sql_valor(c, fila[c]) for c in campos]
        self.db.execute(
            "INSERT INTO [Clientes] (%s, [Activo], [FechaCreacion]) VALUES (%s, True, %s)"
            % (', '.join('[%s]' % c for c in campos), ', '.join(valores),
               _fecha_access()))
        nuevo = self.buscar_por_documento(fila['Documento'])
        return (nuevo or {}).get('ClienteID', 0)

    def actualizar(self, cliente_id, datos):
        actual = self.obtener(cliente_id)
        if not actual:
            raise ErrorMaestro('El cliente %s no existe.' % cliente_id)
        mezcla = dict(actual)
        mezcla.update({k: v for k, v in datos.items() if v is not None})
        fila = self._validar(mezcla, cliente_id=int(cliente_id))
        sets = ', '.join('[%s]=%s' % (c, self._sql_valor(c, v)) for c, v in fila.items())
        self.db.execute("UPDATE [Clientes] SET %s WHERE ClienteID=%d"
                        % (sets, int(cliente_id)))

    def desactivar(self, cliente_id):
        """No se borra: sus facturas viejas lo siguen nombrando."""
        self.db.execute("UPDATE [Clientes] SET Activo=False WHERE ClienteID=%d"
                        % int(cliente_id))

    def obtener(self, cliente_id):
        return self.db.query_one("SELECT * FROM [Clientes] WHERE ClienteID=%d"
                                 % int(cliente_id)) or {}

    def buscar_por_documento(self, documento):
        doc = normalizar_rif(documento) or normalizar_cedula(documento) or str(documento or '')
        return self.db.query_one("SELECT * FROM [Clientes] WHERE Documento='%s'"
                                 % _esc(doc, 20))

    def listar(self, solo_activos=True, busqueda=None):
        where = []
        if solo_activos:
            where.append('Activo=True')
        if busqueda:
            term = _esc(busqueda, 100).replace('%', '').replace('_', '')
            where.append("(RazonSocial LIKE '%%%s%%' OR Documento LIKE '%%%s%%')"
                         % (term, term))
        sql = 'SELECT * FROM [Clientes]'
        if where:
            sql += ' WHERE ' + ' AND '.join(where)
        return self.db.query(sql + ' ORDER BY RazonSocial') or []

    # ── Pacientes que factura este cliente ─────────────────────────────
    def asociar_paciente(self, cliente_id, paciente_id, vinculo='', por_defecto=False):
        """
        Anota que este cliente paga las pruebas de este paciente. Si es el
        cliente por defecto, deja de serlo cualquier otro del paciente: solo
        puede haber uno al que se le facture sin preguntar.
        """
        cliente_id, paciente_id = int(cliente_id), int(paciente_id)
        if not self.obtener(cliente_id):
            raise ErrorMaestro('El cliente %s no existe.' % cliente_id)
        if por_defecto:
            self.db.execute("UPDATE [ClientePacientes] SET PorDefecto=False "
                            "WHERE PacienteID=%d" % paciente_id)
        ya = self.db.query_one(
            "SELECT * FROM [ClientePacientes] WHERE ClienteID=%d AND PacienteID=%d"
            % (cliente_id, paciente_id))
        if ya:
            self.db.execute(
                "UPDATE [ClientePacientes] SET Vinculo='%s', PorDefecto=%s "
                "WHERE ClientePacienteID=%d"
                % (_esc(vinculo, 50), 'True' if por_defecto else 'False',
                   int(ya['ClientePacienteID'])))
            return
        self.db.execute(
            "INSERT INTO [ClientePacientes] ([ClienteID], [PacienteID], [Vinculo], "
            "[PorDefecto], [FechaCreacion]) VALUES (%d, %d, '%s', %s, %s)"
            % (cliente_id, paciente_id, _esc(vinculo, 50),
               'True' if por_defecto else 'False', _fecha_access()))

    def clientes_de_paciente(self, paciente_id):
        """Los clientes que pagan a este paciente, el de por defecto primero."""
        filas = self.db.query(
            "SELECT c.*, cp.Vinculo, cp.PorDefecto FROM [ClientePacientes] AS cp "
            "INNER JOIN [Clientes] AS c ON cp.ClienteID = c.ClienteID "
            "WHERE cp.PacienteID=%d AND c.Activo=True" % int(paciente_id)) or []
        return sorted(filas, key=lambda f: (not f.get('PorDefecto'),
                                            str(f.get('RazonSocial') or '')))

    def cliente_por_defecto(self, paciente_id):
        filas = self.clientes_de_paciente(paciente_id)
        return filas[0] if filas and filas[0].get('PorDefecto') else None


# ══════════════════════════════════════════════════════════════════════════
#  Proveedores: los datos fiscales que decide cada pago
# ══════════════════════════════════════════════════════════════════════════
def validar_datos_fiscales_proveedor(datos):
    """
    Normaliza y comprueba los datos fiscales de un proveedor. Devuelve el
    dict listo para guardar o lanza ErrorMaestro.

    El laboratorio es contribuyente ordinario y no retiene IVA, pero el
    porcentaje se guarda igual: si el SENIAT lo califica como especial, los
    proveedores ya tienen el dato y no hay que recorrerlos uno por uno.
    """
    salida = {}
    if 'RIF' in datos and datos.get('RIF') not in (None, ''):
        rif = normalizar_rif(datos['RIF'])
        if not rif or not rif_valido(rif):
            raise ErrorMaestro('El RIF del proveedor no es valido: %s' % datos['RIF'])
        salida['RIF'] = rif
    if datos.get('TipoPersona') not in (None, ''):
        if datos['TipoPersona'] not in TIPOS_PERSONA:
            raise ErrorMaestro('Tipo de persona desconocido: %s' % datos['TipoPersona'])
        salida['TipoPersona'] = datos['TipoPersona']
    elif salida.get('RIF'):
        # Lo que se deduce del RIF; la residencia la confirma el usuario
        salida['TipoPersona'] = 'PJD' if salida['RIF'][0] in LETRAS_JURIDICAS else 'PNR'
    if datos.get('TipoContribuyente') not in (None, ''):
        if datos['TipoContribuyente'] not in ('Ordinario', 'Especial'):
            raise ErrorMaestro('Un proveedor es contribuyente Ordinario o Especial.')
        salida['TipoContribuyente'] = datos['TipoContribuyente']
    if datos.get('PorcentajeRetencionIVA') not in (None, ''):
        pct = float(datos['PorcentajeRetencionIVA'])
        if pct not in (75.0, 100.0):
            raise ErrorMaestro('La retencion de IVA es del 75% o del 100%.')
        salida['PorcentajeRetencionIVA'] = pct
    if datos.get('ConceptoISLR') not in (None, ''):
        salida['ConceptoISLR'] = str(datos['ConceptoISLR'])[:50]
    if datos.get('DiasCredito') not in (None, ''):
        dias = int(datos['DiasCredito'])
        if dias < 0:
            raise ErrorMaestro('Los dias de credito no pueden ser negativos.')
        salida['DiasCredito'] = dias
    return salida


# ══════════════════════════════════════════════════════════════════════════
#  Regimen de IVA del servicio
# ══════════════════════════════════════════════════════════════════════════
def tasa_iva_de_prueba(fila):
    """
    La tasa de IVA de una prueba, o None si la decide la configuracion.

    'Exento' -> 0; 'Gravado' -> su AlicuotaIVA o la general (16%); vacio o
    desconocido -> None, y la factura usa la tasa del laboratorio como
    siempre. Asi una base que no tiene la columna, o una prueba que nadie ha
    marcado, factura igual que antes.
    """
    if not fila:
        return None
    regimen = str(fila.get('RegimenIVA') or '').strip().capitalize()
    if regimen == 'Exento':
        return Decimal('0')
    if regimen == 'Gravado':
        alicuota = fila.get('AlicuotaIVA')
        try:
            valor = Decimal(str(alicuota)) if alicuota not in (None, '') else ALICUOTA_GENERAL
        except Exception:
            valor = ALICUOTA_GENERAL
        return valor if valor > 0 else ALICUOTA_GENERAL
    return None


def tasas_iva_de_pruebas(db, prueba_ids):
    """
    {PruebaID: tasa} para las pruebas con regimen marcado. Las que no lo
    tienen no aparecen. Sin la columna en la base devuelve {}.
    """
    ids = sorted({int(i) for i in prueba_ids if i not in (None, '')})
    if not ids or not _tiene_columna(db, 'Pruebas', 'RegimenIVA'):
        return {}
    try:
        filas = db.query(
            "SELECT PruebaID, RegimenIVA, AlicuotaIVA FROM [Pruebas] WHERE PruebaID IN (%s)"
            % ', '.join(str(i) for i in ids)) or []
    except Exception as e:
        _log.warning("No se pudo leer el regimen de IVA: %s", e)
        return {}
    salida = {}
    for f in filas:
        tasa = tasa_iva_de_prueba(f)
        if tasa is not None:
            salida[int(f['PruebaID'])] = tasa
    return salida


def marcar_regimen_prueba(db, prueba_id, regimen, alicuota=None):
    """Fija el regimen de IVA de una prueba ('Exento', 'Gravado' o None)."""
    if regimen not in (None, '') and regimen not in REGIMENES_IVA:
        raise ErrorMaestro('Regimen de IVA desconocido: %s' % regimen)
    if regimen == 'Gravado' and alicuota not in (None, ''):
        if float(alicuota) <= 0:
            raise ErrorMaestro('Una prueba gravada necesita una alicuota mayor que cero.')
    asegurar_esquema(db)
    db.execute(
        "UPDATE [Pruebas] SET RegimenIVA=%s, AlicuotaIVA=%s WHERE PruebaID=%d"
        % ("NULL" if not regimen else "'%s'" % regimen,
           "NULL" if regimen != 'Gravado' or alicuota in (None, '') else repr(float(alicuota)),
           int(prueba_id)))

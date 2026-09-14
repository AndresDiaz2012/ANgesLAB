# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE VALORES DE REFERENCIA POR EDAD/SEXO - ANgesLAB
================================================================================
Gestiona valores de referencia diferenciados por grupo etario y sexo.

Grupos soportados:
- RN (Recien Nacido): 0-28 dias
- Lactante: 1 mes - 2 anos
- Pediatrico: 2-12 anos
- Adolescente: 12-18 anos
- Adulto M/F: 18-60 anos (diferenciado por sexo)
- Adulto Mayor M/F: 60+ anos

El resolver selecciona automaticamente el valor de referencia apropiado
segun la edad y sexo del paciente. Si no hay variante configurada,
retorna None para que el caller use el valor generico de Parametros.Observaciones.

Autor: Sistema ANgesLAB
================================================================================
"""

import logging
from datetime import datetime


# ============================================================================
# CONSTANTES: GRUPOS ETARIOS
# ============================================================================

# (clave, edad_min_dias, edad_max_dias, sexo, descripcion_humana)
GRUPOS_ETARIOS = [
    ('RN',              0,      28,    None, 'Recien Nacido (0-28 dias)'),
    ('Lactante',       29,     730,    None, 'Lactante (1m - 2a)'),
    ('Pediatrico',    731,    4380,    None, 'Pediatrico (2 - 12a)'),
    ('Adolescente',  4381,    6570,    None, 'Adolescente (12 - 18a)'),
    ('Adulto',       6571,   21900,     'M', 'Adulto Masculino (18 - 60a)'),
    ('Adulto',       6571,   21900,     'F', 'Adulto Femenino (18 - 60a)'),
    ('AdultoMayor', 21901,   43800,     'M', 'Adulto Mayor M (60+)'),
    ('AdultoMayor', 21901,   43800,     'F', 'Adulto Mayor F (60+)'),
]

# Plantillas para el UI (sin sexo fijo, para mostrar en dropdowns)
PLANTILLAS_GRUPOS = [
    ('RN',              0,      28,   None, 'Recien Nacido (0-28 dias)'),
    ('Lactante',       29,     730,   None, 'Lactante (1m - 2a)'),
    ('Pediatrico',    731,    4380,   None, 'Pediatrico (2 - 12a)'),
    ('Adolescente',  4381,    6570,   None, 'Adolescente (12 - 18a)'),
    ('Adulto_M',     6571,   21900,    'M', 'Adulto Masculino (18 - 60a)'),
    ('Adulto_F',     6571,   21900,    'F', 'Adulto Femenino (18 - 60a)'),
    ('AdultoMayor_M', 21901, 43800,   'M', 'Adulto Mayor M (60+)'),
    ('AdultoMayor_F', 21901, 43800,   'F', 'Adulto Mayor F (60+)'),
]


class GestorValoresReferencia:
    """
    Gestiona valores de referencia diferenciados por edad y sexo.

    Uso principal:
        gestor = GestorValoresReferencia(db)
        ref = gestor.resolver_valor_referencia(param_id, 'M', fecha_nac)
        # ref = "13.0 - 17.0 g/dL" (adulto masculino)
        # o None si no hay variante → caller usa Parametros.Observaciones
    """

    def __init__(self, db):
        self.db = db
        self._cache = {}  # {(param_id, sexo, edad_dias_bucket): valor_ref}
        self._params_con_variantes = None  # set de ParametroIDs con variantes
        self._asegurar_tabla()

    # =========================================================================
    # INFRAESTRUCTURA DB
    # =========================================================================

    def _asegurar_tabla(self):
        """Crea la tabla ValoresReferenciaEdadSexo si no existe."""
        try:
            self.db.query("SELECT TOP 1 RefID FROM ValoresReferenciaEdadSexo")
        except Exception:
            try:
                self.db.execute("""
                    CREATE TABLE ValoresReferenciaEdadSexo (
                        RefID         AUTOINCREMENT PRIMARY KEY,
                        ParametroID   LONG NOT NULL,
                        GrupoEtario   TEXT(30) NOT NULL,
                        EdadMinDias   LONG,
                        EdadMaxDias   LONG,
                        Sexo          TEXT(1),
                        ValorReferencia TEXT(200) NOT NULL,
                        Prioridad     INTEGER DEFAULT 0,
                        Activo        BIT DEFAULT TRUE,
                        FechaCreacion DATETIME
                    )
                """)
                logging.getLogger("angeslab.valores_referencia").debug("[VALREF] Tabla ValoresReferenciaEdadSexo creada")
            except Exception as e:
                logging.getLogger("angeslab.valores_referencia").warning("[VALREF] Error creando tabla: %s", e)

    # =========================================================================
    # RESOLVER: NUCLEO DEL MODULO
    # =========================================================================

    def resolver_valor_referencia(self, parametro_id, sexo, fecha_nacimiento):
        """
        Resuelve el valor de referencia apropiado para un paciente.

        Args:
            parametro_id: int - ID del parametro
            sexo: str - 'M' o 'F' (o None)
            fecha_nacimiento: datetime - fecha de nacimiento del paciente

        Returns:
            str - ValorReferencia especifico, o None si no hay variante
        """
        edad_dias = self._calcular_edad_dias(fecha_nacimiento)
        if edad_dias is None:
            return None

        # Verificacion rapida: este parametro tiene variantes?
        if not self._tiene_variantes_cached(parametro_id):
            return None

        # Revisar cache
        sexo_norm = str(sexo).strip().upper()[:1] if sexo else None
        cache_key = (parametro_id, sexo_norm, edad_dias)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Query: buscar la mejor variante
        resultado = self._buscar_variante(parametro_id, sexo_norm, edad_dias)

        # Guardar en cache
        self._cache[cache_key] = resultado
        return resultado

    def resolver_lote(self, parametro_ids, sexo, fecha_nacimiento):
        """
        Resuelve valores de referencia para multiples parametros a la vez.

        Args:
            parametro_ids: list[int] - IDs de parametros
            sexo: str - 'M' o 'F'
            fecha_nacimiento: datetime

        Returns:
            dict - {parametro_id: valor_ref_texto_o_None}
        """
        resultado = {}
        for pid in parametro_ids:
            resultado[pid] = self.resolver_valor_referencia(pid, sexo, fecha_nacimiento)
        return resultado

    def _buscar_variante(self, parametro_id, sexo_norm, edad_dias):
        """
        Busca la mejor variante en la base de datos.

        Prioridad: sexo-especifico (Prioridad alta) > generico (Prioridad baja)
        """
        try:
            # Construir condicion de sexo
            if sexo_norm in ('M', 'F'):
                sexo_cond = f"(Sexo IS NULL OR Sexo = '{sexo_norm}')"
            else:
                sexo_cond = "Sexo IS NULL"

            sql = (
                f"SELECT TOP 1 ValorReferencia "
                f"FROM ValoresReferenciaEdadSexo "
                f"WHERE ParametroID = {parametro_id} "
                f"  AND EdadMinDias <= {edad_dias} "
                f"  AND EdadMaxDias >= {edad_dias} "
                f"  AND {sexo_cond} "
                f"  AND Activo = True "
                f"ORDER BY Prioridad DESC"
            )
            row = self.db.query_one(sql)
            if row and row.get('ValorReferencia'):
                return str(row['ValorReferencia']).strip()
        except Exception as e:
            logging.getLogger("angeslab.valores_referencia").warning("[VALREF] Error buscando variante: %s", e)

        return None

    def _tiene_variantes_cached(self, parametro_id):
        """Verifica rapidamente si un parametro tiene variantes configuradas."""
        if self._params_con_variantes is None:
            self._cargar_set_variantes()
        return parametro_id in self._params_con_variantes

    def _cargar_set_variantes(self):
        """Carga el set de ParametroIDs que tienen al menos una variante activa."""
        self._params_con_variantes = set()
        try:
            rows = self.db.query(
                "SELECT DISTINCT ParametroID FROM ValoresReferenciaEdadSexo "
                "WHERE Activo = True"
            )
            if rows:
                for r in rows:
                    self._params_con_variantes.add(r['ParametroID'])
        except Exception:
            pass

    @staticmethod
    def _calcular_edad_dias(fecha_nacimiento):
        """Calcula la edad en dias desde la fecha de nacimiento.
        Maneja datetime, pywintypes.datetime, strings, etc."""
        if not fecha_nacimiento:
            return None
        try:
            fn = fecha_nacimiento

            if isinstance(fn, str):
                # Intentar parsear formatos comunes
                for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                    try:
                        fn = datetime.strptime(fn[:10], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None
            elif hasattr(fn, 'year') and hasattr(fn, 'month') and hasattr(fn, 'day'):
                # Convertir pywintypes.datetime u otros objetos date-like a datetime puro
                fn = datetime(fn.year, fn.month, fn.day)
            else:
                return None

            hoy = datetime.now()
            delta = hoy - fn
            return max(0, delta.days)
        except Exception:
            return None

    @staticmethod
    def clasificar_grupo_etario(edad_dias, sexo=None):
        """
        Clasifica un paciente en su grupo etario.

        Returns:
            str - nombre del grupo (ej: 'Pediatrico', 'Adulto M')
        """
        if edad_dias is None:
            return 'Desconocido'

        sexo_norm = str(sexo).strip().upper()[:1] if sexo else ''

        for grupo, min_d, max_d, g_sexo, desc in GRUPOS_ETARIOS:
            if min_d <= edad_dias <= max_d:
                if g_sexo is None or g_sexo == sexo_norm:
                    sufijo = f" {sexo_norm}" if g_sexo else ""
                    return f"{grupo}{sufijo}"

        return 'Adulto'  # Fallback

    # =========================================================================
    # CRUD PARA UI DE GESTION
    # =========================================================================

    def obtener_variantes(self, parametro_id):
        """
        Obtiene todas las variantes configuradas para un parametro.

        Returns:
            list[dict] - variantes con RefID, GrupoEtario, Sexo, etc.
        """
        try:
            rows = self.db.query(
                f"SELECT * FROM ValoresReferenciaEdadSexo "
                f"WHERE ParametroID = {parametro_id} "
                f"ORDER BY EdadMinDias, Prioridad DESC"
            )
            return rows or []
        except Exception:
            return []

    def guardar_variante(self, parametro_id, grupo_etario, edad_min_dias,
                         edad_max_dias, sexo, valor_referencia, prioridad=None):
        """
        Inserta una nueva variante de valor de referencia.

        Args:
            parametro_id: int
            grupo_etario: str (ej: 'RN', 'Adulto', 'Pediatrico')
            edad_min_dias: int
            edad_max_dias: int
            sexo: str ('M', 'F') o None (ambos)
            valor_referencia: str (ej: "13.0 - 17.0 g/dL")
            prioridad: int (None = auto: 10 si sexo especifico, 0 si generico)

        Returns:
            bool - True si se guardo correctamente
        """
        try:
            if prioridad is None:
                prioridad = 10 if sexo else 0

            grupo_esc = str(grupo_etario).replace("'", "''")
            valor_esc = str(valor_referencia).replace("'", "''")
            sexo_sql = f"'{sexo}'" if sexo else "NULL"
            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')

            sql = (
                f"INSERT INTO ValoresReferenciaEdadSexo "
                f"(ParametroID, GrupoEtario, EdadMinDias, EdadMaxDias, "
                f"Sexo, ValorReferencia, Prioridad, Activo, FechaCreacion) "
                f"VALUES ({parametro_id}, '{grupo_esc}', {edad_min_dias}, "
                f"{edad_max_dias}, {sexo_sql}, '{valor_esc}', "
                f"{prioridad}, True, {fecha})"
            )
            self.db.execute(sql)

            # Invalidar caches
            self._invalidar_cache(parametro_id)

            return True
        except Exception as e:
            logging.getLogger("angeslab.valores_referencia").warning("[VALREF] Error guardando variante: %s", e)
            return False

    def actualizar_variante(self, ref_id, valor_referencia):
        """
        Actualiza el valor de referencia de una variante existente.

        Args:
            ref_id: int - ID de la variante
            valor_referencia: str - nuevo valor

        Returns:
            bool
        """
        try:
            valor_esc = str(valor_referencia).replace("'", "''")
            self.db.execute(
                f"UPDATE ValoresReferenciaEdadSexo "
                f"SET ValorReferencia = '{valor_esc}' "
                f"WHERE RefID = {ref_id}"
            )
            self._invalidar_cache_total()
            return True
        except Exception as e:
            logging.getLogger("angeslab.valores_referencia").warning("[VALREF] Error actualizando variante: %s", e)
            return False

    def eliminar_variante(self, ref_id):
        """
        Elimina (desactiva) una variante.

        Args:
            ref_id: int - ID de la variante

        Returns:
            bool
        """
        try:
            self.db.execute(
                f"UPDATE ValoresReferenciaEdadSexo "
                f"SET Activo = False "
                f"WHERE RefID = {ref_id}"
            )
            self._invalidar_cache_total()
            return True
        except Exception as e:
            logging.getLogger("angeslab.valores_referencia").warning("[VALREF] Error eliminando variante: %s", e)
            return False

    def tiene_variantes(self, parametro_id):
        """Retorna True si el parametro tiene variantes activas configuradas."""
        try:
            row = self.db.query_one(
                f"SELECT TOP 1 RefID FROM ValoresReferenciaEdadSexo "
                f"WHERE ParametroID = {parametro_id} AND Activo = True"
            )
            return row is not None
        except Exception:
            return False

    # =========================================================================
    # CACHE
    # =========================================================================

    def _invalidar_cache(self, parametro_id):
        """Invalida cache para un parametro especifico."""
        keys_to_remove = [k for k in self._cache if k[0] == parametro_id]
        for k in keys_to_remove:
            del self._cache[k]
        # Recargar set de variantes
        self._params_con_variantes = None

    def _invalidar_cache_total(self):
        """Invalida todo el cache."""
        self._cache.clear()
        self._params_con_variantes = None


# ============================================================================
# FUNCIONES DE CONVENIENCIA
# ============================================================================

_gestor_singleton = None


def obtener_gestor(db):
    """Obtiene (o crea) la instancia singleton del gestor."""
    global _gestor_singleton
    if _gestor_singleton is None:
        _gestor_singleton = GestorValoresReferencia(db)
    return _gestor_singleton


def resolver_referencia(db, parametro_id, sexo, fecha_nacimiento):
    """Funcion de conveniencia para resolver un valor de referencia."""
    return obtener_gestor(db).resolver_valor_referencia(
        parametro_id, sexo, fecha_nacimiento
    )


# ============================================================================
# VALORES DE REFERENCIA PREDETERMINADOS POR EDAD/SEXO
# ============================================================================
# Formato: CodigoParametro → lista de (grupo_etario, edad_min, edad_max, sexo, valor_referencia)
# Fuentes: bibliografía clínica estándar (Wallach, Tietz, OMS)

VALORES_PREDETERMINADOS = {
    # ── HEMATOLOGÍA ──────────────────────────────────────────────────────
    # Hemoglobina
    'HEM001': [
        ('RN',         0,     28, None, '14.0 - 24.0 g/dL'),
        ('Lactante',  29,    730, None, '10.0 - 15.0 g/dL'),
        ('Pediatrico', 731, 4380, None, '11.5 - 14.5 g/dL'),
        ('Adolescente', 4381, 6570, None, '12.0 - 16.0 g/dL'),
        ('Adulto',   6571, 21900,  'M', '13.0 - 17.0 g/dL'),
        ('Adulto',   6571, 21900,  'F', '12.0 - 15.0 g/dL'),
        ('AdultoMayor', 21901, 43800, 'M', '12.5 - 17.0 g/dL'),
        ('AdultoMayor', 21901, 43800, 'F', '11.5 - 15.0 g/dL'),
    ],
    # Hematocrito
    'HEM002': [
        ('RN',         0,     28, None, '44 - 64 %'),
        ('Lactante',  29,    730, None, '30 - 45 %'),
        ('Pediatrico', 731, 4380, None, '35 - 45 %'),
        ('Adolescente', 4381, 6570, None, '36 - 46 %'),
        ('Adulto',   6571, 21900,  'M', '40 - 54 %'),
        ('Adulto',   6571, 21900,  'F', '36 - 47 %'),
        ('AdultoMayor', 21901, 43800, 'M', '38 - 52 %'),
        ('AdultoMayor', 21901, 43800, 'F', '35 - 46 %'),
    ],
    # Globulos Rojos (Eritrocitos)
    'HEM003': [
        ('RN',         0,     28, None, '4.0 - 6.0 mill/mm³'),
        ('Lactante',  29,    730, None, '3.5 - 5.5 mill/mm³'),
        ('Pediatrico', 731, 4380, None, '4.0 - 5.2 mill/mm³'),
        ('Adulto',   6571, 21900,  'M', '4.5 - 5.5 mill/mm³'),
        ('Adulto',   6571, 21900,  'F', '4.0 - 5.0 mill/mm³'),
    ],
    # Globulos Blancos (Leucocitos)
    'HEM004': [
        ('RN',         0,     28, None, '9000 - 30000 /mm³'),
        ('Lactante',  29,    730, None, '6000 - 17500 /mm³'),
        ('Pediatrico', 731, 4380, None, '5000 - 13000 /mm³'),
        ('Adolescente', 4381, 6570, None, '4500 - 11000 /mm³'),
        ('Adulto',   6571, 43800, None, '4000 - 11000 /mm³'),
    ],
    # Plaquetas
    'HEM005': [
        ('RN',         0,     28, None, '150000 - 450000 /mm³'),
        ('Pediatrico', 731, 4380, None, '150000 - 400000 /mm³'),
        ('Adulto',   6571, 43800, None, '150000 - 400000 /mm³'),
    ],
    # VCM
    'HEM008': [
        ('RN',         0,     28, None, '95 - 121 fL'),
        ('Lactante',  29,    730, None, '70 - 86 fL'),
        ('Pediatrico', 731, 4380, None, '75 - 87 fL'),
        ('Adulto',   6571, 43800, None, '80 - 100 fL'),
    ],
    # HCM
    'HEM009': [
        ('RN',         0,     28, None, '31 - 37 pg'),
        ('Lactante',  29,    730, None, '23 - 31 pg'),
        ('Adulto',   6571, 43800, None, '27 - 33 pg'),
    ],
    # CHCM
    'HEM010': [
        ('RN',         0,     28, None, '30 - 36 g/dL'),
        ('Adulto',   6571, 43800, None, '32 - 36 g/dL'),
    ],
    # VSG (Velocidad de Sedimentacion)
    'HEM015': [
        ('Pediatrico', 731, 4380, None, '0 - 10 mm/h'),
        ('Adulto',   6571, 21900,  'M', '0 - 15 mm/h'),
        ('Adulto',   6571, 21900,  'F', '0 - 20 mm/h'),
        ('AdultoMayor', 21901, 43800, 'M', '0 - 20 mm/h'),
        ('AdultoMayor', 21901, 43800, 'F', '0 - 30 mm/h'),
    ],

    # ── QUÍMICA CLÍNICA ──────────────────────────────────────────────────
    # Glicemia
    'QUIM001': [
        ('RN',         0,     28, None, '40 - 60 mg/dL'),
        ('Lactante',  29,    730, None, '60 - 100 mg/dL'),
        ('Pediatrico', 731, 4380, None, '70 - 100 mg/dL'),
        ('Adulto',   6571, 43800, None, '70 - 110 mg/dL'),
    ],
    # Urea
    'QUIM002': [
        ('Pediatrico', 731, 4380, None, '5 - 18 mg/dL'),
        ('Adulto',   6571, 21900, None, '15 - 45 mg/dL'),
        ('AdultoMayor', 21901, 43800, None, '17 - 50 mg/dL'),
    ],
    # Creatinina
    'QUIM003': [
        ('Pediatrico', 731, 4380, None, '0.3 - 0.7 mg/dL'),
        ('Adolescente', 4381, 6570, None, '0.5 - 1.0 mg/dL'),
        ('Adulto',   6571, 21900,  'M', '0.7 - 1.3 mg/dL'),
        ('Adulto',   6571, 21900,  'F', '0.6 - 1.1 mg/dL'),
        ('AdultoMayor', 21901, 43800, None, '0.6 - 1.4 mg/dL'),
    ],
    # Acido Urico
    'QUIM004': [
        ('Pediatrico', 731, 4380, None, '2.0 - 5.5 mg/dL'),
        ('Adulto',   6571, 21900,  'M', '3.4 - 7.0 mg/dL'),
        ('Adulto',   6571, 21900,  'F', '2.4 - 6.0 mg/dL'),
    ],
    # Colesterol Total
    'QUIM005': [
        ('Pediatrico', 731, 4380, None, '< 170 mg/dL'),
        ('Adulto',   6571, 43800, None, '< 200 mg/dL'),
    ],
    # Trigliceridos
    'QUIM006': [
        ('Pediatrico', 731, 4380, None, '< 150 mg/dL'),
        ('Adulto',   6571, 43800, None, '< 150 mg/dL'),
    ],
    # HDL
    'QUIM007': [
        ('Adulto',   6571, 21900,  'M', '> 40 mg/dL'),
        ('Adulto',   6571, 21900,  'F', '> 50 mg/dL'),
    ],
    # LDL
    'QUIM008': [
        ('Adulto',   6571, 43800, None, '< 130 mg/dL'),
    ],
    # VLDL
    'QUIM009': [
        ('Adulto',   6571, 43800, None, '< 30 mg/dL'),
    ],
    # Bilirrubina Total
    'QUIM010': [
        ('RN',         0,     28, None, '1.0 - 12.0 mg/dL'),
        ('Lactante',  29,    730, None, '0.2 - 1.2 mg/dL'),
        ('Adulto',   6571, 43800, None, '0.2 - 1.2 mg/dL'),
    ],
    # Bilirrubina Directa
    'QUIM011': [
        ('Adulto',   6571, 43800, None, '0.0 - 0.3 mg/dL'),
    ],
    # Bilirrubina Indirecta
    'QUIM012': [
        ('Adulto',   6571, 43800, None, '0.1 - 0.9 mg/dL'),
    ],
    # TGO/AST
    'QUIM013': [
        ('Pediatrico', 731, 4380, None, '10 - 40 U/L'),
        ('Adulto',   6571, 21900,  'M', '10 - 40 U/L'),
        ('Adulto',   6571, 21900,  'F', '10 - 35 U/L'),
    ],
    # TGP/ALT
    'QUIM014': [
        ('Pediatrico', 731, 4380, None, '7 - 35 U/L'),
        ('Adulto',   6571, 21900,  'M', '7 - 56 U/L'),
        ('Adulto',   6571, 21900,  'F', '7 - 45 U/L'),
    ],
    # Fosfatasa Alcalina
    'QUIM015': [
        ('Pediatrico', 731, 4380, None, '100 - 400 U/L'),
        ('Adolescente', 4381, 6570, None, '100 - 390 U/L'),
        ('Adulto',   6571, 21900,  'M', '40 - 130 U/L'),
        ('Adulto',   6571, 21900,  'F', '35 - 105 U/L'),
    ],
    # GGT
    'QUIM016': [
        ('Adulto',   6571, 21900,  'M', '8 - 61 U/L'),
        ('Adulto',   6571, 21900,  'F', '5 - 36 U/L'),
    ],
    # Proteinas Totales
    'QUIM017': [
        ('RN',         0,     28, None, '4.6 - 7.0 g/dL'),
        ('Pediatrico', 731, 4380, None, '6.0 - 8.0 g/dL'),
        ('Adulto',   6571, 43800, None, '6.4 - 8.3 g/dL'),
    ],
    # Albumina
    'QUIM018': [
        ('Adulto',   6571, 43800, None, '3.5 - 5.0 g/dL'),
    ],
    # Globulina
    'QUIM019': [
        ('Adulto',   6571, 43800, None, '2.0 - 3.5 g/dL'),
    ],
    # Calcio
    'QUIM020': [
        ('RN',         0,     28, None, '7.6 - 10.4 mg/dL'),
        ('Pediatrico', 731, 4380, None, '8.8 - 10.8 mg/dL'),
        ('Adulto',   6571, 43800, None, '8.5 - 10.5 mg/dL'),
    ],
    # Fosforo
    'QUIM021': [
        ('Pediatrico', 731, 4380, None, '4.5 - 6.5 mg/dL'),
        ('Adulto',   6571, 43800, None, '2.5 - 4.5 mg/dL'),
    ],
    # Hierro Serico
    'QUIM022': [
        ('Adulto',   6571, 21900,  'M', '65 - 175 ug/dL'),
        ('Adulto',   6571, 21900,  'F', '50 - 170 ug/dL'),
    ],
    # Sodio
    'QUIM030': [
        ('RN',         0,     28, None, '134 - 146 mEq/L'),
        ('Adulto',   6571, 43800, None, '136 - 145 mEq/L'),
    ],
    # Potasio
    'QUIM031': [
        ('RN',         0,     28, None, '3.7 - 5.9 mEq/L'),
        ('Lactante',  29,    730, None, '3.5 - 6.0 mEq/L'),
        ('Adulto',   6571, 43800, None, '3.5 - 5.1 mEq/L'),
    ],
    # Cloro
    'QUIM032': [
        ('Adulto',   6571, 43800, None, '98 - 106 mEq/L'),
    ],
    # Amilasa
    'QUIM040': [
        ('Adulto',   6571, 43800, None, '28 - 100 U/L'),
    ],
    # Lipasa
    'QUIM041': [
        ('Adulto',   6571, 43800, None, '0 - 160 U/L'),
    ],
    # LDH
    'QUIM050': [
        ('Pediatrico', 731, 4380, None, '150 - 500 U/L'),
        ('Adulto',   6571, 43800, None, '120 - 246 U/L'),
    ],

    # ── COAGULACIÓN ──────────────────────────────────────────────────────
    'COAG001': [
        ('RN',         0,     28, None, '11.0 - 16.0 seg'),
        ('Adulto',   6571, 43800, None, '11.0 - 13.5 seg'),
    ],
    'COAG002': [
        ('RN',         0,     28, None, '25.0 - 60.0 seg'),
        ('Adulto',   6571, 43800, None, '25.0 - 35.0 seg'),
    ],

    # ── TIROIDES / HORMONAS ──────────────────────────────────────────────
    'TIR001': [
        ('RN',         0,     28, None, '1.0 - 39.0 uUI/mL'),
        ('Pediatrico', 731, 4380, None, '0.7 - 6.4 uUI/mL'),
        ('Adulto',   6571, 43800, None, '0.4 - 4.0 uUI/mL'),
    ],
    'TIR002': [
        ('RN',         0,     28, None, '2.0 - 5.0 ng/dL'),
        ('Adulto',   6571, 43800, None, '0.8 - 1.8 ng/dL'),
    ],
    'TIR003': [
        ('RN',         0,     28, None, '70 - 220 ng/dL'),
        ('Adulto',   6571, 43800, None, '60 - 180 ng/dL'),
    ],
}


def _buscar_parametro(db, codigo, nombre_alt=None):
    """Busca un parametro por codigo o por nombre alternativo."""
    # 1. Buscar por CodigoParametro exacto
    param = db.query_one(
        f"SELECT ParametroID FROM Parametros "
        f"WHERE CodigoParametro = '{codigo}'"
    )
    if param:
        return param['ParametroID']
    # 2. Fallback: buscar por nombre con LIKE (acepta variantes)
    if nombre_alt:
        nombre_esc = nombre_alt.replace("'", "''")
        # Buscar coincidencia exacta primero
        param = db.query_one(
            f"SELECT TOP 1 ParametroID FROM Parametros "
            f"WHERE NombreParametro LIKE '{nombre_esc}'"
        )
        if param:
            return param['ParametroID']
        # Buscar coincidencia parcial (el nombre empieza igual)
        param = db.query_one(
            f"SELECT TOP 1 ParametroID FROM Parametros "
            f"WHERE NombreParametro LIKE '{nombre_esc}%'"
        )
        if param:
            return param['ParametroID']
        # Buscar conteniendo el nombre
        param = db.query_one(
            f"SELECT TOP 1 ParametroID FROM Parametros "
            f"WHERE NombreParametro LIKE '%{nombre_esc}%'"
        )
        if param:
            return param['ParametroID']
    return None


def cargar_valores_predeterminados(db):
    """
    Carga los valores de referencia predeterminados por edad/sexo para los
    parametros que existan en la base de datos y que aun no tengan variantes.

    Busca por CodigoParametro primero, luego por NombreParametro como fallback.

    Returns:
        tuple (insertados, omitidos, no_encontrados)
    """
    gestor = obtener_gestor(db)
    insertados = 0
    omitidos = 0
    no_encontrados = 0

    for codigo, variantes in VALORES_PREDETERMINADOS.items():
        # Obtener nombre alternativo del mapa
        nombre_alt = _NOMBRES_PARAMETROS.get(codigo)
        param_id = _buscar_parametro(db, codigo, nombre_alt)

        if not param_id:
            no_encontrados += 1
            logging.getLogger("angeslab.valores_referencia").debug("[VALREF] No encontrado: %s / %s", codigo, nombre_alt)
            continue

        # Si ya tiene variantes, no sobrescribir
        if gestor.tiene_variantes(param_id):
            omitidos += 1
            continue

        # Insertar todas las variantes
        for grupo, e_min, e_max, sexo, valor in variantes:
            gestor.guardar_variante(param_id, grupo, e_min, e_max, sexo, valor)

        insertados += 1

    return insertados, omitidos, no_encontrados


# Mapeo codigo → lista de nombres alternativos para fallback de busqueda
# Se prueban en orden hasta encontrar uno que exista en la BD
_NOMBRES_PARAMETROS = {
    'HEM001': 'Hemoglobina',
    'HEM002': 'Hematocrito',
    'HEM003': 'Globulos Rojos',
    'HEM004': 'Globulos Blancos',
    'HEM005': 'Plaquetas',
    'HEM008': 'V.C.M',
    'HEM009': 'H.C.M',
    'HEM010': 'C.H.C.M',
    'HEM015': 'V.S.G',
    'QUIM001': 'Glicemia',
    'QUIM002': 'Urea',
    'QUIM003': 'Creatinina',
    'QUIM004': 'Acido Urico',
    'QUIM005': 'Colesterol Total',
    'QUIM006': 'Trigliceridos',
    'QUIM007': 'HDL',
    'QUIM008': 'LDL',
    'QUIM009': 'VLDL',
    'QUIM010': 'Bilirrubina Total',
    'QUIM011': 'Bilirrubina Directa',
    'QUIM012': 'Bilirrubina Indirecta',
    'QUIM013': 'TGO',
    'QUIM014': 'TGP',
    'QUIM015': 'Fosfatasa Alcalina',
    'QUIM016': 'GGT',
    'QUIM017': 'Proteinas Totales',
    'QUIM018': 'Albumina',
    'QUIM019': 'Globulina',
    'QUIM020': 'Calcio',
    'QUIM021': 'Fosforo',
    'QUIM022': 'Hierro',
    'QUIM030': 'Sodio',
    'QUIM031': 'Potasio',
    'QUIM032': 'Cloro',
    'QUIM040': 'Amilasa',
    'QUIM041': 'Lipasa',
    'QUIM050': 'LDH',
    'COAG001': 'Tiempo de Protrombina',
    'COAG002': 'Tiempo Parcial de Tromboplastina',
    'TIR001': 'TSH',
    'TIR002': 'T4 Libre',
    'TIR003': 'T3',
}

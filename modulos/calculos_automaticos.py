"""
Módulo de Cálculos Automáticos para Laboratorio Clínico
========================================================
Sistema robusto de fórmulas y cálculos automáticos para parámetros derivados.

Incluye:
- Hematología (índices eritrocitarios)
- Perfil Lipídico (VLDL, LDL, índices de riesgo)
- Función Renal (depuración de creatinina, eGFR)
- Marcadores Prostáticos (índice PSA)
- Proteínas (globulina, relación A/G)
- Bilirrubinas (fraccionadas)
- Orina 24 horas (depuraciones y excreciones)
- Electrolitos (anion gap, osmolaridad)
- Metabolismo (HOMA-IR, índice TyG)
- Y más...

Copyright (c) 2024-2025 ANgesLAB Solutions
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Any, List, Tuple


class CalculadorLaboratorio:
    """
    Motor de cálculos automáticos para parámetros de laboratorio clínico.

    Detecta automáticamente qué cálculos aplicar según los parámetros disponibles
    y actualiza los valores calculados en tiempo real.
    """

    # Mapeo de nombres de parámetros a nombres normalizados
    # Esto permite flexibilidad en cómo se nombran los parámetros
    # IMPORTANTE: Todos los alias deben estar en minúsculas
    ALIAS_PARAMETROS = {
        # =====================================================================
        # HEMATOLOGÍA - Incluye todos los nombres posibles de la BD
        # =====================================================================
        'hematies': [
            'hematies', 'hematíes', 'hematìes', 'eritrocitos',
            'globulos rojos', 'glóbulos rojos', 'globulos  rojos',
            'rbc', 'gr', 'g.r.', 'red blood cells',
            'recuento de globulos rojos', 'recuento globulos rojos',
            'contaje de hematies', 'contaje hematies',
            'eritrocitos (gr)', 'hematies (gr)'
        ],
        'hemoglobina': [
            'hemoglobina', 'hemoglobina.', 'hemoglobina:',
            'hb', 'hgb', 'hb.', 'hemoglobin',
            'hemoglobina (hb)', 'hemoglobina(hb)', 'hb (hemoglobina)'
        ],
        'hematocrito': [
            'hematocrito', 'hematocrito.', 'hematocrito:',
            'hto', 'hct', 'hto.', 'hematócrito',
            'hematocrito (hto)', 'hematocrito(hto)'
        ],
        'vcm': [
            'vcm', 'v.c.m.', 'v.c.m', 'v. c. m.', 'v c m',
            'vgm', 'mcv', 'volumen corpuscular medio',
            'vol. corp. medio', 'volumen corp. medio',
            'vcm (vol. corp. medio)', 'vcm (volumen corpuscular medio)',
            'indice vcm', 'índice vcm'
        ],
        'hcm': [
            'hcm', 'h.c.m.', 'h.c.m', 'h. c. m.', 'h c m',
            'hgm', 'mch', 'hemoglobina corpuscular media',
            'hb. corp. media', 'hb corp media',
            'hcm (hb. corp. media)', 'hcm (hemoglobina corpuscular media)',
            'indice hcm', 'índice hcm'
        ],
        'chcm': [
            'chcm', 'c.h.c.m.', 'c.h.c.m', 'c. h. c. m.', 'c h c m',
            'cgmh', 'mchc',
            'concentracion de hemoglobina corpuscular media',
            'conc. hb. corp. media', 'conc hb corp media',
            'conc hemoglobina corpuscular media',
            'chcm (conc. hb. corp. media)',
            'concentracion hemoglobina corpuscular media',
            'indice chcm', 'índice chcm'
        ],
        'rdw': [
            'rdw', 'r.d.w.', 'ade', 'adre', 'ancho de distribucion eritrocitaria',
            'ancho dist. eritrocitaria'
        ],
        'vpm': [
            'vpm', 'v.p.m.', 'mpv', 'volumen plaquetario medio'
        ],
        'leucocitos': [
            'leucocitos', 'wbc', 'gb', 'globulos blancos', 'glóbulos blancos',
            'white blood cells', 'leucos'
        ],
        'plaquetas': [
            'plaquetas', 'plaquetas.', 'plt', 'contaje de plaquetas', 'recuento plaquetas',
            'platelets', 'trombocitos'
        ],
        'vsg': [
            'vsg', 'v.s.g.', 'velocidad de sedimentacion', 'velocidad de sedimentación',
            'vsg  ( wintrobe)', 'vsg (wintrobe)', 'eritrosedimentacion'
        ],

        # =====================================================================
        # PERFIL LIPÍDICO
        # =====================================================================
        'colesterol_total': [
            'colesterol', 'colesterol total', 'ct', 'col. total', 'cholesterol',
            'colesterol serico', 'colesterol sérico', 'col total', 'col.total',
            'colesterol t', 'colesterol (total)', 'total cholesterol'
        ],
        'trigliceridos': [
            'trigliceridos', 'triglicéridos', 'tg', 'tgl', 'triglycerides',
            'trigliceridos sericos', 'triglicéridos séricos', 'triglic',
            'trig', 'trigli', 'triglicerido'
        ],
        'hdl': [
            'hdl', 'hdl colesterol', 'hdl-colesterol', 'colesterol hdl', 'hdl-c',
            'hdl-col', 'c-hdl', 'hdl cholesterol', 'colesterol hdl-c',
            'hdl col', 'hdl-colesterol (bueno)', 'colesterol bueno',
            'hdl (colesterol bueno)', 'lipoproteina alta densidad'
        ],
        'ldl': [
            'ldl', 'ldl colesterol', 'ldl-colesterol', 'colesterol ldl', 'ldl-c',
            'ldl-col', 'c-ldl', 'ldl cholesterol', 'colesterol ldl-c',
            'ldl col', 'ldl-colesterol (malo)', 'colesterol malo',
            'ldl (colesterol malo)', 'lipoproteina baja densidad',
            'ldl (calculado)', 'ldl calculado'
        ],
        'vldl': [
            'vldl', 'vldl colesterol', 'vldl-colesterol', 'colesterol vldl', 'vldl-c',
            'vldl-col', 'c-vldl', 'lipoproteina muy baja densidad',
            'vldl (calculado)', 'vldl calculado'
        ],
        'indice_ct_hdl': [
            'rel colesterol / hdl', 'rel colesterol/hdl', 'relacion colesterol/hdl',
            'razon ct/hdl', 'indice ct/hdl', 'ct/hdl', 'indice aterogenico',
            'índice aterogénico', 'riesgo coronario', 'indice de riesgo',
            'relacion ct/hdl', 'indice de castelli', 'castelli i',
            'riesgo cardiovascular', 'indice colesterol/hdl'
        ],
        'indice_ldl_hdl': [
            'rel ldl / hdl', 'rel ldl/hdl', 'relacion ldl/hdl', 'razon ldl/hdl',
            'indice ldl/hdl', 'ldl/hdl', 'castelli ii', 'indice castelli ii',
            'relacion ldl hdl', 'riesgo ldl/hdl'
        ],
        'indice_hdl_ldl_vldl': [
            'colesterol hdl/(ldl+vldl)', 'hdl/(ldl+vldl)', 'relacion hdl/ldl+vldl',
            'indice hdl/(ldl+vldl)', 'relacion hdl sobre ldl vldl',
            'indice protector'
        ],
        'lipidos_totales': [
            'lipidos totales', 'lípidos totales', 'total lipidos',
            'lipidos', 'perfil lipidico total'
        ],
        'colesterol_no_hdl': [
            'colesterol no hdl', 'no hdl colesterol', 'col no hdl', 'no-hdl',
            'colesterol no-hdl', 'non hdl cholesterol'
        ],

        # =====================================================================
        # FUNCIÓN RENAL
        # =====================================================================
        'creatinina': [
            'creatinina', 'creatinina serica', 'creatinina en suero', 'creat', 'cr',
            'creatinine'
        ],
        'urea': [
            'urea', 'urea serica', 'nitrogeno ureico'
        ],
        'bun': [
            'bun', 'nitrogeno ureico (bun)', 'nitrogeno ureico', 'n. ureico'
        ],
        'acido_urico': [
            'acido urico', 'ácido úrico', 'ac. urico', 'au', 'uric acid'
        ],
        'depuracion_creatinina': [
            'depuracion de creatinina', 'depuración de creatinina', 'clearance de creatinina',
            'clearence de creatinina', 'dcr', 'aclaramiento de creatinina',
            'depuracion corregida (sc)'
        ],
        'egfr': [
            'egfr', 'tfg', 'tfge', 'filtrado glomerular', 'tasa de filtrado glomerular',
            'gfr'
        ],

        # =====================================================================
        # PSA (MARCADORES PROSTÁTICOS)
        # =====================================================================
        'psa_total': [
            'psa total', 'psa', 'antigeno prostatico especifico', 'antígeno prostático',
            'psa-total'
        ],
        'psa_libre': [
            'psa libre', 'psa-libre', 'free psa'
        ],
        'indice_psa': [
            'relacion psa libre/total', 'relación psa libre/total', 'indice psa',
            'indice psa (l/t)', 'índice psa', 'psa libre/total', 'ratio psa'
        ],

        # =====================================================================
        # PROTEÍNAS
        # =====================================================================
        'proteinas_totales': [
            'proteinas totales', 'proteínas totales', 'pt', 'prot. totales',
            'total proteins'
        ],
        'albumina': [
            'albumina', 'albúmina', 'alb', 'albumin'
        ],
        'globulina': [
            'globulina', 'globulinas', 'glob', 'globulin'
        ],
        'relacion_ag': [
            'relacion a/g', 'relación a/g', 'indice a/g', 'índice a/g', 'a/g',
            'relacion albumina/globulinas', 'relación albúmina/globulinas',
            'relacion albumina/globulina'
        ],

        # =====================================================================
        # BILIRRUBINAS
        # =====================================================================
        'bilirrubina_total': [
            'bilirrubina total', 'bt', 'bili total', 'bilirrubina', 'total bilirubin'
        ],
        'bilirrubina_directa': [
            'bilirrubina directa', 'bd', 'bili directa', 'bilirrubina conjugada',
            'direct bilirubin'
        ],
        'bilirrubina_indirecta': [
            'bilirrubina indirecta', 'bi', 'bili indirecta', 'bilirrubina no conjugada',
            'indirect bilirubin'
        ],

        # =====================================================================
        # ELECTROLITOS
        # =====================================================================
        'sodio': [
            'sodio', 'na', 'na+', 'sodium', 'sodio serico', 'na serico'
        ],
        'potasio': [
            'potasio', 'k', 'k+', 'potassium', 'potasio serico', 'k serico'
        ],
        'cloro': [
            'cloro', 'cl', 'cl-', 'cloruro', 'cloruros', 'chloride', 'cloro serico'
        ],
        'calcio': [
            'calcio', 'ca', 'ca++', 'ca2+', 'calcium', 'calcio serico', 'ca total'
        ],
        'calcio_ionico': [
            'calcio ionico', 'calcio iónico', 'ca ionico', 'ca++', 'ca ionizado'
        ],
        'fosforo': [
            'fosforo', 'fósforo', 'p', 'fosfato', 'phosphorus', 'fosforo serico'
        ],
        'magnesio': [
            'magnesio', 'mg', 'mg++', 'magnesium', 'magnesio serico'
        ],
        'bicarbonato': [
            'bicarbonato', 'hco3', 'hco3-', 'co2 total', 'total co2', 'co2'
        ],
        'anion_gap': [
            'anion gap', 'brecha anionica', 'brecha aniónica', 'gap anionico'
        ],
        'osmolaridad': [
            'osmolaridad', 'osmolaridad calculada', 'osm', 'osmolarity'
        ],

        # =====================================================================
        # GLUCOSA / METABOLISMO
        # =====================================================================
        'glucosa': [
            'glucosa', 'glicemia', 'glicemia basal', 'glucemia', 'glucose',
            'glucosa basal', 'glicemia en ayunas', 'glucosa en ayunas'
        ],
        'insulina': [
            'insulina', 'insulina basal', 'insulin', 'insulina   basal',
            'insulina en ayunas'
        ],
        'homa_ir': [
            'homa-ir', 'homa ir', 'homa', 'indice homa', 'índice homa'
        ],
        'hba1c': [
            'hba1c', 'hemoglobina glicosilada', 'hemoglobina glucosilada',
            'hemoglobina glicada', 'a1c', 'hb glicosilada'
        ],

        # =====================================================================
        # ORINA Y FUNCIÓN RENAL EN ORINA
        # =====================================================================
        'volumen_orina_24h': [
            'volumen 24h', 'volumen orina 24h', 'volumen orina 24 h', 'diuresis 24h',
            'volumen de orina', 'vol. orina 24h', 'volumen', 'diuresis', 'vol orina',
            'volumen de orina 24h', 'volumen de orina 24 horas', 'volumen orina',
            'vol. 24h', 'volumen 24 horas', 'diuresis de 24 horas', 'volumen (ml)',
            'volumen en ml', 'volumen de muestra'
        ],
        'creatinina_orina': [
            'creatinina orina', 'creatinina urinaria', 'creatinina en orina',
            'creatinina en orina 24h.', 'creatinina en orina 24h',
            'creatinina en orina.24h', 'creatinina en orina parcial.',
            'creatinina en orina parcial', 'creat. orina', 'cr orina',
            'creatinina en orina de 24 horas', 'creatinina orina 24h'
        ],
        'proteinas_orina': [
            'proteinas orina', 'proteinuria', 'proteinas en orina',
            'proteinuria de 24 horas', 'proteinuria de 18 horas',
            'proteinas'
        ],
        'calcio_orina': [
            'calcio orina', 'calciuria', 'calcio en orina', 'calcio en orina palcial',
            'ca en orina', 'calcio urinario'
        ],
        'acido_urico_orina': [
            'acido urico orina', 'uricosuria', 'acido urico en orina 24 h',
            'acido urico en orina parcial', 'ac. urico orina'
        ],
        'sodio_orina': [
            'sodio orina', 'natriuria', 'sodio en orina parcial', 'sodio orina 24h.',
            'na en orina'
        ],
        'potasio_orina': [
            'potasio orina', 'kaliuria', 'potasio en orina', 'potasio en orina 24h.',
            'potasio en orina parcial', 'k en orina'
        ],
        'cloro_orina': [
            'cloro orina', 'cloruria', 'cloro en orina', 'cl en orina'
        ],
        'magnesio_orina': [
            'magnesio orina', 'magnesio en orina de 24 horas', 'mg en orina'
        ],
        'microalbuminuria': [
            'microalbuminuria', 'microalbumina', 'albumina en orina', 'alb en orina'
        ],
        'relacion_ca_cr': [
            'relacion calcio / creatinina', 'relacion calcio/creatinina',
            'relación calcio/creatinina', 'indice ca/cr', 'ca/cr'
        ],
        'relacion_acido_urico_cr': [
            'relacion acido urico /  creatinina', 'relacion acido urico/creatinina',
            'au/cr'
        ],

        # =====================================================================
        # COAGULACIÓN
        # =====================================================================
        'tp': [
            'tp', 'tp.', 'tiempo de protrombina', 'tiempo de protrombina (tp)',
            'prothrombin time', 'pt'
        ],
        'tp_control': [
            'tp control', 'control tp', 'tp corregido'
        ],
        'inr': [
            'inr', 'rin', 'international normalized ratio'
        ],
        'tp_actividad': [
            'tp actividad', 'actividad de protrombina', '% actividad',
            'actividad tp', 'porcentaje de actividad'
        ],
        'tpt': [
            'tpt', 'ttp', 'ttpa', 'tiempo parcial tromboplastina',
            'tiempo parcial de tromboplastina', 'tiempo parcial de tromboplastina (tpt)',
            'aptt'
        ],
        'tpt_control': [
            'tpt control', 'tpt corregido', 'control tpt'
        ],
        'tiempo_sangria': [
            'tiempo de sangria', 'tiempo de sangría', 'tiempo de sangria  ( duke)',
            'ts', 'bleeding time'
        ],
        'tiempo_coagulacion': [
            'tiempo de coagulacion', 'tiempo de coagulación', 'tc',
            'clotting time'
        ],
        'fibrinogeno': [
            'fibrinogeno', 'fibrinógeno', 'fibrinogen'
        ],
        'dimero_d': [
            'dimero d', 'dímero d', 'd-dimero', 'd-dimer'
        ],
        'retraccion_coagulo': [
            'retraccion del coagulo', 'retracción del coágulo',
            'tiempo de retraccion del cuagulo'
        ],

        # =====================================================================
        # HORMONAS TIROIDEAS
        # =====================================================================
        'tsh': [
            'tsh', 'tirotropina', 'hormona estimulante tiroides', 'thyroid stimulating hormone'
        ],
        't3_total': [
            't3 total', 't3', 'triyodotironina total'
        ],
        't4_total': ['t4 total', 't4'],
        't3_libre': ['t3 libre', 'ft3'],
        't4_libre': ['t4 libre', 'ft4'],

        # Datos del paciente (para cálculos)
        'edad': [
            'edad', 'edad (años)', 'edad del paciente', 'años', 'age',
            'edad en años', 'edad paciente'
        ],
        'peso': [
            'peso', 'peso (kg)', 'peso del paciente', 'peso corporal', 'weight',
            'peso en kg', 'peso paciente', 'peso actual'
        ],
        'talla': [
            'talla', 'estatura', 'altura', 'talla (cm)', 'height',
            'estatura (cm)', 'talla del paciente', 'altura del paciente'
        ],
        'sexo': [
            'sexo', 'genero', 'género', 'sex', 'gender', 'sexo del paciente'
        ],
        'superficie_corporal': [
            'superficie corporal', 'sc', 'bsa', 'superficie corporal (m2)',
            'area corporal', 'área corporal', 'body surface area'
        ],

        # =====================================================================
        # MICROBIOLOGÍA / BACTERIOLOGÍA
        # =====================================================================
        'tipo_muestra': [
            'tipo de muestra', 'tipo muestra', 'muestra', 'specimen type',
            'sample type'
        ],
        'resultado_cultivo': [
            'resultado del cultivo', 'resultado cultivo', 'cultivo',
            'crecimiento', 'desarrollo bacteriano', 'culture result'
        ],
        'germen_aislado': [
            'germen aislado', 'germen', 'microorganismo', 'agente etiologico',
            'agente etiológico', 'organismo aislado', 'bacteria aislada',
            'bacteria identificada', 'identificacion', 'identificación',
            'isolated organism', 'pathogen'
        ],
        'recuento_colonias': [
            'recuento de colonias', 'recuento colonias', 'ufc/ml', 'ufc',
            'unidades formadoras de colonias', 'colony count', 'cfu/ml'
        ],
        'coloracion_gram': [
            'coloracion de gram', 'coloración de gram', 'gram', 'tincion de gram',
            'tinción de gram', 'gram stain'
        ],
        'metodo_cultivo': [
            'metodo', 'método', 'medio de cultivo', 'medio', 'tecnica',
            'técnica', 'culture method'
        ],
        'tiempo_incubacion': [
            'tiempo de incubacion', 'tiempo de incubación', 'incubacion',
            'incubación', 'tiempo incubacion', 'horas de incubacion'
        ],
        'temperatura_incubacion': [
            'temperatura', 'temperatura de incubacion', 'temperatura incubacion'
        ],
    }

    def __init__(self, db_connection=None):
        """
        Inicializa el calculador.

        Args:
            db_connection: Conexión a la base de datos (opcional)
        """
        self.db = db_connection
        self._cache_parametros = {}

    def normalizar_nombre(self, nombre: str) -> Optional[str]:
        """
        Normaliza el nombre de un parámetro a su forma canónica.

        Args:
            nombre: Nombre del parámetro a normalizar

        Returns:
            Nombre normalizado o None si no se encuentra
        """
        nombre_lower = nombre.lower().strip()

        for nombre_canonico, aliases in self.ALIAS_PARAMETROS.items():
            if nombre_lower in aliases or nombre_lower == nombre_canonico:
                return nombre_canonico

        return None

    def _to_float(self, valor: Any) -> Optional[float]:
        """Convierte un valor a float de forma segura."""
        if valor is None or valor == '':
            return None
        try:
            # Limpiar el valor
            if isinstance(valor, str):
                valor = valor.replace(',', '.').strip()
                # Remover caracteres no numéricos excepto punto y signo
                valor = re.sub(r'[^\d.\-]', '', valor)
            return float(valor)
        except (ValueError, TypeError):
            return None

    def _redondear(self, valor: float, decimales: int = 2) -> float:
        """Redondea un valor a los decimales especificados."""
        if valor is None:
            return None
        return float(Decimal(str(valor)).quantize(Decimal(10) ** -decimales, rounding=ROUND_HALF_UP))

    # =========================================================================
    # CÁLCULOS DE HEMATOLOGÍA
    # =========================================================================

    def calcular_vcm(self, hematocrito: float, hematies: float) -> Optional[float]:
        """
        Calcula el Volumen Corpuscular Medio (VCM).

        Fórmula: VCM = (Hematocrito × 10) / Hematíes (millones/µL)
        Valor normal: 80-100 fL

        Args:
            hematocrito: Hematocrito en %
            hematies: Hematíes en millones/µL

        Returns:
            VCM en femtolitros (fL)
        """
        hto = self._to_float(hematocrito)
        hem = self._to_float(hematies)

        if hto is None or hem is None or hem == 0:
            return None

        vcm = (hto * 10) / hem
        return self._redondear(vcm, 2)

    def calcular_hcm(self, hemoglobina: float, hematies: float) -> Optional[float]:
        """
        Calcula la Hemoglobina Corpuscular Media (HCM).

        Fórmula: HCM = (Hemoglobina × 10) / Hematíes (millones/µL)
        Valor normal: 26-33 pg

        Args:
            hemoglobina: Hemoglobina en g/dL
            hematies: Hematíes en millones/µL

        Returns:
            HCM en picogramos (pg)
        """
        hb = self._to_float(hemoglobina)
        hem = self._to_float(hematies)

        if hb is None or hem is None or hem == 0:
            return None

        hcm = (hb * 10) / hem
        return self._redondear(hcm, 2)

    def calcular_chcm(self, hemoglobina: float, hematocrito: float) -> Optional[float]:
        """
        Calcula la Concentración de Hemoglobina Corpuscular Media (CHCM).

        Fórmula: CHCM = (Hemoglobina / Hematocrito) × 100
        Valor normal: 31-36 g/dL

        Args:
            hemoglobina: Hemoglobina en g/dL
            hematocrito: Hematocrito en %

        Returns:
            CHCM en g/dL
        """
        hb = self._to_float(hemoglobina)
        hto = self._to_float(hematocrito)

        if hb is None or hto is None or hto == 0:
            return None

        chcm = (hb / hto) * 100
        return self._redondear(chcm, 2)

    def calcular_indices_eritrocitarios(self, hematies: float, hemoglobina: float,
                                        hematocrito: float) -> Dict[str, float]:
        """
        Calcula todos los índices eritrocitarios.

        Returns:
            Diccionario con VCM, HCM y CHCM
        """
        return {
            'vcm': self.calcular_vcm(hematocrito, hematies),
            'hcm': self.calcular_hcm(hemoglobina, hematies),
            'chcm': self.calcular_chcm(hemoglobina, hematocrito)
        }

    # =========================================================================
    # CÁLCULOS DE PERFIL LIPÍDICO
    # =========================================================================

    def calcular_vldl(self, trigliceridos: float) -> Optional[float]:
        """
        Calcula el colesterol VLDL.

        Fórmula: VLDL = Triglicéridos / 5 (si TG < 400 mg/dL)
        Valor normal: 2-30 mg/dL

        Args:
            trigliceridos: Triglicéridos en mg/dL

        Returns:
            VLDL en mg/dL o None si TG >= 400
        """
        tg = self._to_float(trigliceridos)

        if tg is None:
            return None

        # La fórmula de Friedewald no es válida para TG >= 400
        if tg >= 400:
            return None

        vldl = tg / 5
        return self._redondear(vldl, 2)

    def calcular_ldl(self, colesterol_total: float, hdl: float,
                     trigliceridos: float = None, vldl: float = None) -> Optional[float]:
        """
        Calcula el colesterol LDL usando la fórmula de Friedewald.

        Fórmula: LDL = Colesterol Total - HDL - VLDL
        Donde VLDL = TG/5 (si no se proporciona)
        Valor óptimo: < 100 mg/dL

        Args:
            colesterol_total: Colesterol total en mg/dL
            hdl: HDL-Colesterol en mg/dL
            trigliceridos: Triglicéridos en mg/dL (opcional si se da VLDL)
            vldl: VLDL en mg/dL (opcional, se calcula si no se proporciona)

        Returns:
            LDL en mg/dL
        """
        ct = self._to_float(colesterol_total)
        hdl_val = self._to_float(hdl)

        if ct is None or hdl_val is None:
            return None

        # Calcular o usar VLDL
        if vldl is not None:
            vldl_val = self._to_float(vldl)
        elif trigliceridos is not None:
            vldl_val = self.calcular_vldl(trigliceridos)
        else:
            return None

        if vldl_val is None:
            return None

        ldl = ct - hdl_val - vldl_val
        return self._redondear(ldl, 2)

    def calcular_indice_ct_hdl(self, colesterol_total: float, hdl: float) -> Optional[float]:
        """
        Calcula el índice de riesgo Colesterol Total / HDL.

        Valor favorable: < 4.5

        Args:
            colesterol_total: Colesterol total en mg/dL
            hdl: HDL-Colesterol en mg/dL

        Returns:
            Índice CT/HDL
        """
        ct = self._to_float(colesterol_total)
        hdl_val = self._to_float(hdl)

        if ct is None or hdl_val is None or hdl_val == 0:
            return None

        indice = ct / hdl_val
        return self._redondear(indice, 2)

    def calcular_indice_ldl_hdl(self, ldl: float, hdl: float) -> Optional[float]:
        """
        Calcula el índice de riesgo LDL / HDL.

        Valor favorable: < 3.55

        Args:
            ldl: LDL-Colesterol en mg/dL
            hdl: HDL-Colesterol en mg/dL

        Returns:
            Índice LDL/HDL
        """
        ldl_val = self._to_float(ldl)
        hdl_val = self._to_float(hdl)

        if ldl_val is None or hdl_val is None or hdl_val == 0:
            return None

        indice = ldl_val / hdl_val
        return self._redondear(indice, 2)

    def calcular_indice_hdl_ldl_vldl(self, hdl: float, ldl: float, vldl: float) -> Optional[float]:
        """
        Calcula el índice HDL / (LDL + VLDL).

        Valor favorable: > 0.34

        Args:
            hdl: HDL-Colesterol en mg/dL
            ldl: LDL-Colesterol en mg/dL
            vldl: VLDL-Colesterol en mg/dL

        Returns:
            Índice HDL/(LDL+VLDL)
        """
        hdl_val = self._to_float(hdl)
        ldl_val = self._to_float(ldl)
        vldl_val = self._to_float(vldl)

        if hdl_val is None or ldl_val is None or vldl_val is None:
            return None

        denominador = ldl_val + vldl_val
        if denominador == 0:
            return None

        indice = hdl_val / denominador
        return self._redondear(indice, 2)

    def calcular_lipidos_totales(self, colesterol_total: float, trigliceridos: float,
                                  fosfolipidos: float = None) -> Optional[float]:
        """
        Calcula los lípidos totales.

        Fórmula aproximada: CT + TG + Fosfolípidos (o CT × 1.5 + TG si no hay fosfolípidos)
        Valor normal: 400-800 mg/dL
        """
        ct = self._to_float(colesterol_total)
        tg = self._to_float(trigliceridos)

        if ct is None or tg is None:
            return None

        if fosfolipidos is not None:
            fl = self._to_float(fosfolipidos)
            if fl is not None:
                return self._redondear(ct + tg + fl, 2)

        # Aproximación
        lipidos = ct * 1.5 + tg
        return self._redondear(lipidos, 2)

    def calcular_colesterol_no_hdl(self, colesterol_total: float, hdl: float) -> Optional[float]:
        """
        Calcula el colesterol no-HDL.

        Fórmula: Colesterol no-HDL = Colesterol Total - HDL

        Es un mejor predictor de riesgo cardiovascular que el LDL porque
        incluye todas las lipoproteínas aterogénicas (LDL + VLDL + IDL + Lp(a))

        Valores de referencia:
        - Óptimo: < 130 mg/dL
        - Cercano al óptimo: 130-159 mg/dL
        - Limítrofe alto: 160-189 mg/dL
        - Alto: 190-219 mg/dL
        - Muy alto: >= 220 mg/dL

        Args:
            colesterol_total: Colesterol total en mg/dL
            hdl: HDL-Colesterol en mg/dL

        Returns:
            Colesterol no-HDL en mg/dL
        """
        ct = self._to_float(colesterol_total)
        hdl_val = self._to_float(hdl)

        if ct is None or hdl_val is None:
            return None

        col_no_hdl = ct - hdl_val
        return self._redondear(col_no_hdl, 2)

    def calcular_perfil_lipidico_completo(self, colesterol_total: float, trigliceridos: float,
                                          hdl: float) -> Dict[str, float]:
        """
        Calcula todos los parámetros derivados del perfil lipídico.

        Parámetros de entrada requeridos:
        - Colesterol Total (mg/dL)
        - Triglicéridos (mg/dL)
        - HDL Colesterol (mg/dL)

        Returns:
            Diccionario con VLDL, LDL, índices de riesgo y colesterol no-HDL
        """
        vldl = self.calcular_vldl(trigliceridos)
        ldl = self.calcular_ldl(colesterol_total, hdl, trigliceridos)
        col_no_hdl = self.calcular_colesterol_no_hdl(colesterol_total, hdl)

        return {
            'vldl': vldl,
            'ldl': ldl,
            'colesterol_no_hdl': col_no_hdl,
            'indice_ct_hdl': self.calcular_indice_ct_hdl(colesterol_total, hdl),
            'indice_ldl_hdl': self.calcular_indice_ldl_hdl(ldl, hdl) if ldl else None,
            'indice_hdl_ldl_vldl': self.calcular_indice_hdl_ldl_vldl(hdl, ldl, vldl) if ldl and vldl else None,
            'lipidos_totales': self.calcular_lipidos_totales(colesterol_total, trigliceridos)
        }

    # =========================================================================
    # CÁLCULOS DE FUNCIÓN RENAL
    # =========================================================================

    def calcular_depuracion_creatinina_cockcroft(self, creatinina: float, edad: int,
                                                   peso: float, sexo: str) -> Optional[float]:
        """
        Calcula la depuración de creatinina usando la fórmula de Cockcroft-Gault.

        Fórmula Hombres: ((140 - Edad) × Peso) / (72 × Creatinina)
        Fórmula Mujeres: ((140 - Edad) × Peso × 0.85) / (72 × Creatinina)

        Args:
            creatinina: Creatinina sérica en mg/dL
            edad: Edad en años
            peso: Peso en kg
            sexo: 'M' para masculino, 'F' para femenino

        Returns:
            Depuración de creatinina en mL/min
        """
        cr = self._to_float(creatinina)
        edad_val = self._to_float(edad)
        peso_val = self._to_float(peso)

        if cr is None or edad_val is None or peso_val is None or cr == 0:
            return None

        dcr = ((140 - edad_val) * peso_val) / (72 * cr)

        # Factor de corrección para mujeres
        if sexo and sexo.upper() in ['F', 'FEMENINO', 'MUJER']:
            dcr *= 0.85

        return self._redondear(dcr, 2)

    def calcular_egfr_ckd_epi(self, creatinina: float, edad: int, sexo: str,
                              es_afroamericano: bool = False) -> Optional[float]:
        """
        Calcula la tasa de filtración glomerular estimada usando CKD-EPI 2021.

        Args:
            creatinina: Creatinina sérica en mg/dL
            edad: Edad en años
            sexo: 'M' para masculino, 'F' para femenino
            es_afroamericano: Si el paciente es afroamericano (para fórmula 2009)

        Returns:
            eGFR en mL/min/1.73m²
        """
        cr = self._to_float(creatinina)
        edad_val = self._to_float(edad)

        if cr is None or edad_val is None or cr <= 0:
            return None

        es_mujer = sexo and sexo.upper() in ['F', 'FEMENINO', 'MUJER']

        # CKD-EPI 2021 (sin raza)
        if es_mujer:
            if cr <= 0.7:
                egfr = 142 * ((cr / 0.7) ** -0.241) * (0.9938 ** edad_val) * 1.012
            else:
                egfr = 142 * ((cr / 0.7) ** -1.200) * (0.9938 ** edad_val) * 1.012
        else:
            if cr <= 0.9:
                egfr = 142 * ((cr / 0.9) ** -0.302) * (0.9938 ** edad_val)
            else:
                egfr = 142 * ((cr / 0.9) ** -1.200) * (0.9938 ** edad_val)

        return self._redondear(egfr, 2)

    def calcular_bun_a_urea(self, bun: float) -> Optional[float]:
        """
        Convierte BUN a Urea.

        Fórmula: Urea = BUN × 2.14
        """
        bun_val = self._to_float(bun)
        if bun_val is None:
            return None
        return self._redondear(bun_val * 2.14, 2)

    def calcular_urea_a_bun(self, urea: float) -> Optional[float]:
        """
        Convierte Urea a BUN.

        Fórmula: BUN = Urea / 2.14
        """
        urea_val = self._to_float(urea)
        if urea_val is None:
            return None
        return self._redondear(urea_val / 2.14, 2)

    def calcular_relacion_bun_creatinina(self, bun: float, creatinina: float) -> Optional[float]:
        """
        Calcula la relación BUN/Creatinina.

        Valor normal: 10-20
        > 20: Sugiere causas prerrenales
        < 10: Sugiere causas intrínsecas
        """
        bun_val = self._to_float(bun)
        cr = self._to_float(creatinina)

        if bun_val is None or cr is None or cr == 0:
            return None

        return self._redondear(bun_val / cr, 2)

    # =========================================================================
    # CÁLCULOS DE PSA
    # =========================================================================

    def calcular_indice_psa(self, psa_libre: float, psa_total: float) -> Optional[float]:
        """
        Calcula el índice PSA libre/total.

        Fórmula: (PSA Libre / PSA Total) × 100

        Interpretación:
        - > 25%: Bajo riesgo de cáncer
        - 10-25%: Riesgo intermedio
        - < 10%: Alto riesgo de cáncer

        Args:
            psa_libre: PSA libre en ng/mL
            psa_total: PSA total en ng/mL

        Returns:
            Índice PSA en porcentaje
        """
        libre = self._to_float(psa_libre)
        total = self._to_float(psa_total)

        if libre is None or total is None or total == 0:
            return None

        indice = (libre / total) * 100
        return self._redondear(indice, 2)

    def calcular_densidad_psa(self, psa_total: float, volumen_prostatico: float) -> Optional[float]:
        """
        Calcula la densidad de PSA.

        Fórmula: PSA Total / Volumen prostático

        Valor normal: < 0.15 ng/mL/cc
        """
        psa = self._to_float(psa_total)
        vol = self._to_float(volumen_prostatico)

        if psa is None or vol is None or vol == 0:
            return None

        return self._redondear(psa / vol, 3)

    # =========================================================================
    # CÁLCULOS DE PROTEÍNAS
    # =========================================================================

    def calcular_globulina(self, proteinas_totales: float, albumina: float) -> Optional[float]:
        """
        Calcula la globulina.

        Fórmula: Globulina = Proteínas Totales - Albúmina
        Valor normal: 2.0-3.5 g/dL

        Args:
            proteinas_totales: Proteínas totales en g/dL
            albumina: Albúmina en g/dL

        Returns:
            Globulina en g/dL
        """
        pt = self._to_float(proteinas_totales)
        alb = self._to_float(albumina)

        if pt is None or alb is None:
            return None

        globulina = pt - alb
        return self._redondear(globulina, 2)

    def calcular_relacion_ag(self, albumina: float, globulina: float = None,
                              proteinas_totales: float = None) -> Optional[float]:
        """
        Calcula la relación Albúmina/Globulina.

        Valor normal: 1.1-2.5

        Args:
            albumina: Albúmina en g/dL
            globulina: Globulina en g/dL (o se calcula si se da proteínas totales)
            proteinas_totales: Proteínas totales en g/dL (opcional)

        Returns:
            Relación A/G
        """
        alb = self._to_float(albumina)

        if alb is None:
            return None

        if globulina is not None:
            glob = self._to_float(globulina)
        elif proteinas_totales is not None:
            glob = self.calcular_globulina(proteinas_totales, albumina)
        else:
            return None

        if glob is None or glob == 0:
            return None

        return self._redondear(alb / glob, 2)

    # =========================================================================
    # CÁLCULOS DE BILIRRUBINAS
    # =========================================================================

    def calcular_bilirrubina_indirecta(self, bilirrubina_total: float,
                                        bilirrubina_directa: float) -> Optional[float]:
        """
        Calcula la bilirrubina indirecta.

        Fórmula: BI = BT - BD
        Valor normal: 0.1-0.8 mg/dL

        Args:
            bilirrubina_total: Bilirrubina total en mg/dL
            bilirrubina_directa: Bilirrubina directa en mg/dL

        Returns:
            Bilirrubina indirecta en mg/dL
        """
        bt = self._to_float(bilirrubina_total)
        bd = self._to_float(bilirrubina_directa)

        if bt is None or bd is None:
            return None

        bi = bt - bd
        return self._redondear(bi, 2)

    def calcular_bilirrubina_total(self, bilirrubina_directa: float,
                                    bilirrubina_indirecta: float) -> Optional[float]:
        """
        Calcula la bilirrubina total.

        Fórmula: BT = BD + BI
        """
        bd = self._to_float(bilirrubina_directa)
        bi = self._to_float(bilirrubina_indirecta)

        if bd is None or bi is None:
            return None

        return self._redondear(bd + bi, 2)

    # =========================================================================
    # CÁLCULOS DE ELECTROLITOS
    # =========================================================================

    def calcular_anion_gap(self, sodio: float, cloro: float, bicarbonato: float,
                           potasio: float = None) -> Optional[float]:
        """
        Calcula el Anion Gap.

        Fórmula: AG = Na - (Cl + HCO3) [sin K]
        Fórmula: AG = (Na + K) - (Cl + HCO3) [con K]

        Valor normal: 8-12 mEq/L (sin K), 10-20 mEq/L (con K)

        Args:
            sodio: Sodio en mEq/L
            cloro: Cloro en mEq/L
            bicarbonato: Bicarbonato en mEq/L
            potasio: Potasio en mEq/L (opcional)

        Returns:
            Anion Gap en mEq/L
        """
        na = self._to_float(sodio)
        cl = self._to_float(cloro)
        hco3 = self._to_float(bicarbonato)

        if na is None or cl is None or hco3 is None:
            return None

        if potasio is not None:
            k = self._to_float(potasio)
            if k is not None:
                ag = (na + k) - (cl + hco3)
                return self._redondear(ag, 2)

        ag = na - (cl + hco3)
        return self._redondear(ag, 2)

    def calcular_osmolaridad(self, sodio: float, glucosa: float, bun: float,
                              urea: float = None) -> Optional[float]:
        """
        Calcula la osmolaridad plasmática calculada.

        Fórmula: Osm = 2×Na + Glucosa/18 + BUN/2.8

        Valor normal: 280-295 mOsm/kg

        Args:
            sodio: Sodio en mEq/L
            glucosa: Glucosa en mg/dL
            bun: BUN en mg/dL (o se calcula de urea)
            urea: Urea en mg/dL (opcional, se convierte a BUN)

        Returns:
            Osmolaridad en mOsm/kg
        """
        na = self._to_float(sodio)
        glu = self._to_float(glucosa)

        if na is None or glu is None:
            return None

        if bun is not None:
            bun_val = self._to_float(bun)
        elif urea is not None:
            bun_val = self.calcular_urea_a_bun(urea)
        else:
            return None

        if bun_val is None:
            return None

        osm = (2 * na) + (glu / 18) + (bun_val / 2.8)
        return self._redondear(osm, 2)

    def calcular_calcio_corregido(self, calcio: float, albumina: float) -> Optional[float]:
        """
        Calcula el calcio corregido por albúmina.

        Fórmula: Ca corregido = Ca medido + 0.8 × (4 - Albúmina)

        Args:
            calcio: Calcio sérico en mg/dL
            albumina: Albúmina en g/dL

        Returns:
            Calcio corregido en mg/dL
        """
        ca = self._to_float(calcio)
        alb = self._to_float(albumina)

        if ca is None or alb is None:
            return None

        ca_corr = ca + 0.8 * (4 - alb)
        return self._redondear(ca_corr, 2)

    # =========================================================================
    # CÁLCULOS DE METABOLISMO (GLUCOSA/INSULINA)
    # =========================================================================

    def calcular_homa_ir(self, glucosa: float, insulina: float) -> Optional[float]:
        """
        Calcula el índice HOMA-IR (Homeostatic Model Assessment for Insulin Resistance).

        Fórmula: HOMA-IR = (Glucosa × Insulina) / 405

        Donde:
        - Glucosa en mg/dL
        - Insulina en µU/mL

        Interpretación:
        - < 2.5: Normal
        - 2.5-5.0: Resistencia a insulina leve
        - > 5.0: Resistencia a insulina significativa

        Args:
            glucosa: Glucosa en ayunas en mg/dL
            insulina: Insulina en ayunas en µU/mL

        Returns:
            Índice HOMA-IR
        """
        glu = self._to_float(glucosa)
        ins = self._to_float(insulina)

        if glu is None or ins is None:
            return None

        homa = (glu * ins) / 405
        return self._redondear(homa, 2)

    def calcular_homa_beta(self, glucosa: float, insulina: float) -> Optional[float]:
        """
        Calcula el índice HOMA-β (función de células beta).

        Fórmula: HOMA-β = (360 × Insulina) / (Glucosa - 63)

        Args:
            glucosa: Glucosa en mg/dL
            insulina: Insulina en µU/mL

        Returns:
            Índice HOMA-β en %
        """
        glu = self._to_float(glucosa)
        ins = self._to_float(insulina)

        if glu is None or ins is None or glu <= 63:
            return None

        homa_beta = (360 * ins) / (glu - 63)
        return self._redondear(homa_beta, 2)

    def calcular_indice_tyg(self, trigliceridos: float, glucosa: float) -> Optional[float]:
        """
        Calcula el índice TyG (Triglicéridos-Glucosa).

        Fórmula: TyG = Ln[(TG × Glucosa) / 2]

        Donde TG y Glucosa están en mg/dL

        Valor de corte para resistencia a insulina: > 4.5
        """
        import math

        tg = self._to_float(trigliceridos)
        glu = self._to_float(glucosa)

        if tg is None or glu is None or tg <= 0 or glu <= 0:
            return None

        tyg = math.log((tg * glu) / 2)
        return self._redondear(tyg, 2)

    # =========================================================================
    # CÁLCULOS DE ORINA 24 HORAS
    # =========================================================================

    def calcular_depuracion_creatinina_orina(self, creatinina_orina: float,
                                              volumen_orina: float,
                                              creatinina_serica: float,
                                              superficie_corporal: float = None) -> Optional[float]:
        """
        Calcula la depuración de creatinina medida.

        Fórmula: DCr = (Cr orina × Volumen) / (Cr sérica × 1440)

        Se puede corregir por superficie corporal:
        DCr corregida = DCr × (1.73 / SC)

        Args:
            creatinina_orina: Creatinina en orina en mg/dL
            volumen_orina: Volumen de orina en 24h en mL
            creatinina_serica: Creatinina sérica en mg/dL
            superficie_corporal: Superficie corporal en m² (opcional)

        Returns:
            Depuración de creatinina en mL/min
        """
        cr_o = self._to_float(creatinina_orina)
        vol = self._to_float(volumen_orina)
        cr_s = self._to_float(creatinina_serica)

        if cr_o is None or vol is None or cr_s is None or cr_s == 0:
            return None

        # Convertir creatinina orina a mg/mL si está en mg/dL
        dcr = (cr_o * vol) / (cr_s * 1440)

        # Corregir por superficie corporal si se proporciona
        if superficie_corporal is not None:
            sc = self._to_float(superficie_corporal)
            if sc and sc > 0:
                dcr = dcr * (1.73 / sc)

        return self._redondear(dcr, 2)

    def calcular_excrecion_24h(self, concentracion: float, volumen: float) -> Optional[float]:
        """
        Calcula la excreción de una sustancia en 24 horas.

        Fórmula: Excreción 24h = (Concentración × Volumen) / 100

        Args:
            concentracion: Concentración en mg/dL
            volumen: Volumen en mL

        Returns:
            Excreción en mg/24h
        """
        conc = self._to_float(concentracion)
        vol = self._to_float(volumen)

        if conc is None or vol is None:
            return None

        excrecion = (conc * vol) / 100
        return self._redondear(excrecion, 2)

    def calcular_proteinuria_24h(self, proteinas_orina: float, volumen: float) -> Optional[float]:
        """
        Calcula la proteinuria en 24 horas.

        Valor normal: < 150 mg/24h
        Proteinuria significativa: > 300 mg/24h
        Síndrome nefrótico: > 3500 mg/24h
        """
        return self.calcular_excrecion_24h(proteinas_orina, volumen)

    def calcular_calciuria_24h(self, calcio_orina: float, volumen: float) -> Optional[float]:
        """
        Calcula la calciuria en 24 horas.

        Valor normal: 100-300 mg/24h
        Hipercalciuria: > 300 mg/24h (hombres), > 250 mg/24h (mujeres)
        """
        return self.calcular_excrecion_24h(calcio_orina, volumen)

    def calcular_relacion_calcio_creatinina(self, calcio_orina: float,
                                             creatinina_orina: float) -> Optional[float]:
        """
        Calcula la relación calcio/creatinina en orina.

        Valor normal: < 0.2 mg/mg

        Args:
            calcio_orina: Calcio en orina en mg/dL
            creatinina_orina: Creatinina en orina en mg/dL

        Returns:
            Relación Ca/Cr
        """
        ca = self._to_float(calcio_orina)
        cr = self._to_float(creatinina_orina)

        if ca is None or cr is None or cr == 0:
            return None

        return self._redondear(ca / cr, 3)

    def calcular_relacion_proteina_creatinina(self, proteinas_orina: float,
                                               creatinina_orina: float) -> Optional[float]:
        """
        Calcula la relación proteína/creatinina en orina.

        Valor normal: < 0.2 mg/mg
        Proteinuria significativa: > 0.5 mg/mg
        """
        prot = self._to_float(proteinas_orina)
        cr = self._to_float(creatinina_orina)

        if prot is None or cr is None or cr == 0:
            return None

        return self._redondear(prot / cr, 3)

    def calcular_relacion_albumina_creatinina(self, albumina_orina: float,
                                               creatinina_orina: float) -> Optional[float]:
        """
        Calcula la relación albúmina/creatinina (ACR).

        Valores:
        - Normal: < 30 mg/g
        - Microalbuminuria: 30-300 mg/g
        - Macroalbuminuria: > 300 mg/g

        Args:
            albumina_orina: Albúmina en orina en mg/L
            creatinina_orina: Creatinina en orina en g/L

        Returns:
            Relación ACR en mg/g
        """
        alb = self._to_float(albumina_orina)
        cr = self._to_float(creatinina_orina)

        if alb is None or cr is None or cr == 0:
            return None

        return self._redondear(alb / cr, 2)

    # =========================================================================
    # CÁLCULOS DE COAGULACIÓN
    # =========================================================================

    def calcular_inr(self, tp_paciente: float, tp_control: float, isi: float = 1.0) -> Optional[float]:
        """
        Calcula el INR (International Normalized Ratio).

        Fórmula: INR = (TP paciente / TP control) ^ ISI

        Args:
            tp_paciente: TP del paciente en segundos
            tp_control: TP control en segundos
            isi: Índice de Sensibilidad Internacional (por defecto 1.0)

        Returns:
            INR
        """
        tp_p = self._to_float(tp_paciente)
        tp_c = self._to_float(tp_control)
        isi_val = self._to_float(isi) or 1.0

        if tp_p is None or tp_c is None or tp_c == 0:
            return None

        inr = (tp_p / tp_c) ** isi_val
        return self._redondear(inr, 2)

    def calcular_tp_actividad(self, tp_paciente: float, tp_control: float) -> Optional[float]:
        """
        Calcula la actividad de protrombina.

        Fórmula aproximada basada en curva de dilución

        Args:
            tp_paciente: TP del paciente en segundos
            tp_control: TP control en segundos

        Returns:
            Actividad en %
        """
        tp_p = self._to_float(tp_paciente)
        tp_c = self._to_float(tp_control)

        if tp_p is None or tp_c is None or tp_p == 0:
            return None

        # Fórmula aproximada: Actividad = (Control / Paciente) × 100
        actividad = (tp_c / tp_p) * 100
        return self._redondear(actividad, 1)

    # =========================================================================
    # CÁLCULOS MISCELÁNEOS
    # =========================================================================

    def calcular_superficie_corporal(self, peso: float, talla: float) -> Optional[float]:
        """
        Calcula la superficie corporal usando la fórmula de Du Bois.

        Fórmula: SC = 0.007184 × Peso^0.425 × Talla^0.725

        Args:
            peso: Peso en kg
            talla: Talla en cm

        Returns:
            Superficie corporal en m²
        """
        p = self._to_float(peso)
        t = self._to_float(talla)

        if p is None or t is None or p <= 0 or t <= 0:
            return None

        sc = 0.007184 * (p ** 0.425) * (t ** 0.725)
        return self._redondear(sc, 2)

    def calcular_imc(self, peso: float, talla: float) -> Optional[float]:
        """
        Calcula el Índice de Masa Corporal.

        Fórmula: IMC = Peso / (Talla en metros)²

        Args:
            peso: Peso en kg
            talla: Talla en cm

        Returns:
            IMC en kg/m²
        """
        p = self._to_float(peso)
        t = self._to_float(talla)

        if p is None or t is None or t <= 0:
            return None

        t_metros = t / 100
        imc = p / (t_metros ** 2)
        return self._redondear(imc, 2)

    # =========================================================================
    # DETECCIÓN Y EJECUCIÓN AUTOMÁTICA DE CÁLCULOS
    # =========================================================================

    def detectar_calculos_aplicables(self, valores: Dict[str, Any], debug: bool = False) -> List[Tuple[str, str, callable]]:
        """
        Detecta qué cálculos se pueden aplicar según los valores disponibles.

        Args:
            valores: Diccionario con los valores de parámetros {nombre: valor}
            debug: Si True, imprime información de debug

        Returns:
            Lista de tuplas (nombre_calculo, parametro_destino, funcion_calculo)
        """
        calculos = []

        # Normalizar nombres de parámetros
        valores_norm = {}
        nombres_originales = {}  # Para debug

        for nombre, valor in valores.items():
            nombre_lower = nombre.lower().strip()
            nombre_n = self.normalizar_nombre(nombre)

            if nombre_n:
                valores_norm[nombre_n] = valor
                nombres_originales[nombre_n] = nombre
                if debug:
                    print(f"  [ALIAS] '{nombre}' -> '{nombre_n}' = {valor}")
            else:
                if debug:
                    print(f"  [SIN ALIAS] '{nombre}' = {valor}")

            # También guardar el nombre original en minúsculas
            valores_norm[nombre_lower] = valor

        if debug:
            print(f"\n  Parámetros normalizados disponibles: {list(valores_norm.keys())}")
            print(f"  Buscando hematies: {'hematies' in valores_norm}")
            print(f"  Buscando hemoglobina: {'hemoglobina' in valores_norm}")
            print(f"  Buscando hematocrito: {'hematocrito' in valores_norm}")

        # Hematología - Verificar con debug
        tiene_hematies = 'hematies' in valores_norm
        tiene_hemoglobina = 'hemoglobina' in valores_norm
        tiene_hematocrito = 'hematocrito' in valores_norm

        if tiene_hematies and tiene_hemoglobina and tiene_hematocrito:
            # Capturar los valores actuales para las lambdas
            hto_val = valores_norm.get('hematocrito')
            hem_val = valores_norm.get('hematies')
            hb_val = valores_norm.get('hemoglobina')

            if debug:
                print(f"  [HEMATOLOGIA] Hematies={hem_val}, Hemoglobina={hb_val}, Hematocrito={hto_val}")

            calculos.append(('VCM', 'vcm', lambda hto=hto_val, hem=hem_val: self.calcular_vcm(hto, hem)))
            calculos.append(('HCM', 'hcm', lambda hb=hb_val, hem=hem_val: self.calcular_hcm(hb, hem)))
            calculos.append(('CHCM', 'chcm', lambda hb=hb_val, hto=hto_val: self.calcular_chcm(hb, hto)))
        elif debug:
            print(f"  [HEMATOLOGIA] No se puede calcular - Falta: " +
                  f"{'hematies ' if not tiene_hematies else ''}" +
                  f"{'hemoglobina ' if not tiene_hemoglobina else ''}" +
                  f"{'hematocrito' if not tiene_hematocrito else ''}")

        # Perfil Lipídico - Cálculos completos
        # Capturar valores para las lambdas
        tg_val = valores_norm.get('trigliceridos')
        ct_val = valores_norm.get('colesterol_total')
        hdl_val = valores_norm.get('hdl')

        # VLDL solo requiere triglicéridos
        if tg_val is not None:
            calculos.append(('VLDL', 'vldl', lambda tg=tg_val: self.calcular_vldl(tg)))

        # Colesterol no-HDL solo requiere CT y HDL
        if ct_val is not None and hdl_val is not None:
            calculos.append(('Colesterol no-HDL', 'colesterol_no_hdl', lambda ct=ct_val, hdl=hdl_val: self.calcular_colesterol_no_hdl(ct, hdl)))
            calculos.append(('Índice CT/HDL', 'indice_ct_hdl', lambda ct=ct_val, hdl=hdl_val: self.calcular_indice_ct_hdl(ct, hdl)))

        # Cálculos que requieren CT, HDL y TG
        if all(k in valores_norm for k in ['colesterol_total', 'hdl', 'trigliceridos']):
            # Calcular VLDL y LDL primero para usarlos en otros cálculos
            vldl_calc = self.calcular_vldl(tg_val)
            ldl_calc = self.calcular_ldl(ct_val, hdl_val, tg_val)

            calculos.append(('LDL', 'ldl', lambda ct=ct_val, hdl=hdl_val, tg=tg_val: self.calcular_ldl(ct, hdl, tg)))
            calculos.append(('Lípidos Totales', 'lipidos_totales', lambda ct=ct_val, tg=tg_val: self.calcular_lipidos_totales(ct, tg)))

            # Agregar Índice LDL/HDL (usa LDL calculado)
            if ldl_calc is not None:
                calculos.append(('Índice LDL/HDL', 'indice_ldl_hdl', lambda ldl=ldl_calc, hdl=hdl_val: self.calcular_indice_ldl_hdl(ldl, hdl)))

            # Agregar Índice HDL/(LDL+VLDL) (usa LDL y VLDL calculados)
            if ldl_calc is not None and vldl_calc is not None:
                calculos.append(('Índice HDL/(LDL+VLDL)', 'indice_hdl_ldl_vldl', lambda hdl=hdl_val, ldl=ldl_calc, vldl=vldl_calc: self.calcular_indice_hdl_ldl_vldl(hdl, ldl, vldl)))

        # PSA
        if all(k in valores_norm for k in ['psa_libre', 'psa_total']):
            calculos.append(('Índice PSA', 'indice_psa', lambda: self.calcular_indice_psa(
                valores_norm.get('psa_libre'), valores_norm.get('psa_total'))))

        # Proteínas
        if all(k in valores_norm for k in ['proteinas_totales', 'albumina']):
            calculos.append(('Globulina', 'globulina', lambda: self.calcular_globulina(
                valores_norm.get('proteinas_totales'), valores_norm.get('albumina'))))
            calculos.append(('Relación A/G', 'relacion_ag', lambda: self.calcular_relacion_ag(
                valores_norm.get('albumina'), proteinas_totales=valores_norm.get('proteinas_totales'))))

        # Bilirrubinas - Total y Fraccionada
        if all(k in valores_norm for k in ['bilirrubina_total', 'bilirrubina_directa']):
            calculos.append(('Bilirrubina Indirecta', 'bilirrubina_indirecta', lambda: self.calcular_bilirrubina_indirecta(
                valores_norm.get('bilirrubina_total'), valores_norm.get('bilirrubina_directa'))))

        # Calcular BT a partir de BD + BI (caso inverso)
        if all(k in valores_norm for k in ['bilirrubina_directa', 'bilirrubina_indirecta']) and 'bilirrubina_total' not in valores_norm:
            calculos.append(('Bilirrubina Total', 'bilirrubina_total', lambda: self.calcular_bilirrubina_total(
                valores_norm.get('bilirrubina_directa'), valores_norm.get('bilirrubina_indirecta'))))

        # Electrolitos
        if all(k in valores_norm for k in ['sodio', 'cloro', 'bicarbonato']):
            calculos.append(('Anion Gap', 'anion_gap', lambda: self.calcular_anion_gap(
                valores_norm.get('sodio'), valores_norm.get('cloro'), valores_norm.get('bicarbonato'),
                valores_norm.get('potasio'))))

        if all(k in valores_norm for k in ['sodio', 'glucosa']) and any(k in valores_norm for k in ['bun', 'urea']):
            calculos.append(('Osmolaridad', 'osmolaridad', lambda: self.calcular_osmolaridad(
                valores_norm.get('sodio'), valores_norm.get('glucosa'),
                valores_norm.get('bun'), valores_norm.get('urea'))))

        # Calcio corregido
        if all(k in valores_norm for k in ['calcio', 'albumina']):
            calculos.append(('Calcio Corregido', 'calcio_corregido', lambda: self.calcular_calcio_corregido(
                valores_norm.get('calcio'), valores_norm.get('albumina'))))

        # HOMA-IR
        if all(k in valores_norm for k in ['glucosa', 'insulina']):
            calculos.append(('HOMA-IR', 'homa_ir', lambda: self.calcular_homa_ir(
                valores_norm.get('glucosa'), valores_norm.get('insulina'))))
            calculos.append(('HOMA-β', 'homa_beta', lambda: self.calcular_homa_beta(
                valores_norm.get('glucosa'), valores_norm.get('insulina'))))

        # Índice TyG
        if all(k in valores_norm for k in ['trigliceridos', 'glucosa']):
            calculos.append(('Índice TyG', 'indice_tyg', lambda: self.calcular_indice_tyg(
                valores_norm.get('trigliceridos'), valores_norm.get('glucosa'))))

        # Coagulación
        if all(k in valores_norm for k in ['tp', 'tp_control']):
            calculos.append(('INR', 'inr', lambda: self.calcular_inr(
                valores_norm.get('tp'), valores_norm.get('tp_control'))))
            calculos.append(('TP Actividad', 'tp_actividad', lambda: self.calcular_tp_actividad(
                valores_norm.get('tp'), valores_norm.get('tp_control'))))

        # Relación BUN/Creatinina
        if all(k in valores_norm for k in ['bun', 'creatinina']):
            calculos.append(('Relación BUN/Cr', 'relacion_bun_cr', lambda: self.calcular_relacion_bun_creatinina(
                valores_norm.get('bun'), valores_norm.get('creatinina'))))

        # =====================================================================
        # DEPURACIÓN DE CREATININA Y FUNCIÓN RENAL
        # =====================================================================

        # Depuración de Creatinina - Cockcroft-Gault (usa datos del paciente)
        # Requiere: creatinina sérica, edad, peso, sexo
        if all(k in valores_norm for k in ['creatinina', 'edad', 'peso', 'sexo']):
            cr_val = valores_norm.get('creatinina')
            edad_val = valores_norm.get('edad')
            peso_val = valores_norm.get('peso')
            sexo_val = valores_norm.get('sexo')
            if debug:
                print(f"  [DEPURACION CG] creatinina={cr_val}, edad={edad_val}, peso={peso_val}, sexo={sexo_val}")
            calculos.append(('Depuración Creatinina (C-G)', 'depuracion_creatinina',
                lambda cr=cr_val, edad=edad_val, peso=peso_val, sexo=sexo_val:
                    self.calcular_depuracion_creatinina_cockcroft(cr, edad, peso, sexo)))

        # eGFR - CKD-EPI (usa datos del paciente)
        # Requiere: creatinina sérica, edad, sexo
        if all(k in valores_norm for k in ['creatinina', 'edad', 'sexo']):
            cr_val = valores_norm.get('creatinina')
            edad_val = valores_norm.get('edad')
            sexo_val = valores_norm.get('sexo')
            if debug:
                print(f"  [eGFR] creatinina={cr_val}, edad={edad_val}, sexo={sexo_val}")
            calculos.append(('eGFR (CKD-EPI)', 'egfr',
                lambda cr=cr_val, edad=edad_val, sexo=sexo_val:
                    self.calcular_egfr_ckd_epi(cr, edad, sexo)))

        # =====================================================================
        # SUPERFICIE CORPORAL E IMC
        # =====================================================================

        # Superficie Corporal (Du Bois) - Requiere peso y talla
        # IMPORTANTE: Calcular ANTES de la depuración por orina para que esté disponible
        superficie_calculada = None
        if all(k in valores_norm for k in ['peso', 'talla']):
            peso_val = valores_norm.get('peso')
            talla_val = valores_norm.get('talla')
            if debug:
                print(f"  [SUPERFICIE] peso={peso_val}, talla={talla_val}")
            # Calcular la superficie para usarla en la depuración corregida
            superficie_calculada = self.calcular_superficie_corporal(peso_val, talla_val)
            calculos.append(('Superficie Corporal', 'superficie_corporal',
                lambda p=peso_val, t=talla_val: self.calcular_superficie_corporal(p, t)))
            # También calcular IMC
            calculos.append(('IMC', 'imc',
                lambda p=peso_val, t=talla_val: self.calcular_imc(p, t)))

        # Depuración de Creatinina medida (orina 24h)
        # Requiere: creatinina en orina, volumen orina 24h, creatinina sérica
        if all(k in valores_norm for k in ['creatinina_orina', 'volumen_orina_24h', 'creatinina']):
            cr_orina = valores_norm.get('creatinina_orina')
            vol_orina = valores_norm.get('volumen_orina_24h')
            cr_serica = valores_norm.get('creatinina')
            # Usar superficie calculada o la que venga en valores
            sc = superficie_calculada or valores_norm.get('superficie_corporal')
            if debug:
                print(f"  [DEPURACION ORINA] cr_orina={cr_orina}, vol={vol_orina}, cr_serica={cr_serica}, sc={sc}")
            calculos.append(('Depuración Creatinina (Orina)', 'depuracion_creatinina',
                lambda cr_o=cr_orina, vol=vol_orina, cr_s=cr_serica, superficie=sc:
                    self.calcular_depuracion_creatinina_orina(cr_o, vol, cr_s, superficie)))

        # Orina - Relaciones
        if all(k in valores_norm for k in ['calcio_orina', 'creatinina_orina']):
            calculos.append(('Relación Ca/Cr', 'relacion_ca_cr', lambda: self.calcular_relacion_calcio_creatinina(
                valores_norm.get('calcio_orina'), valores_norm.get('creatinina_orina'))))

        if all(k in valores_norm for k in ['proteinas_orina', 'creatinina_orina']):
            calculos.append(('Relación Prot/Cr', 'relacion_prot_cr', lambda: self.calcular_relacion_proteina_creatinina(
                valores_norm.get('proteinas_orina'), valores_norm.get('creatinina_orina'))))

        return calculos

    def ejecutar_calculos(self, valores: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta todos los cálculos aplicables y retorna los resultados.

        Args:
            valores: Diccionario con los valores de parámetros {nombre: valor}

        Returns:
            Diccionario con los valores calculados {parametro: valor}
        """
        resultados = {}
        calculos = self.detectar_calculos_aplicables(valores)

        for nombre, parametro, funcion in calculos:
            try:
                resultado = funcion()
                if resultado is not None:
                    resultados[parametro] = resultado
            except Exception as e:
                print(f"Error en cálculo {nombre}: {e}")

        return resultados


# Instancia global del calculador
calculador = CalculadorLaboratorio()


def obtener_calculador():
    """Retorna la instancia global del calculador."""
    return calculador

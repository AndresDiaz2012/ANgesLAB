# -*- coding: utf-8 -*-
"""
ia_interpretacion.py - Motor de interpretacion clinica con multiples proveedores.

Nivel 1 (siempre disponible): Motor local de reglas clinicas por area.
Nivel 2 (LLM local opcional):  Ollama con modelos como llama3.2, mistral.
Nivel 3 (online opcional):     OpenAI GPT-4o-mini (rapido y economico).
Nivel 4 (online opcional):     Claude API (Anthropic).

La cascada es: reglas locales → (enriquece con) proveedor LLM configurado.
IMPORTANTE: Toda interpretacion es ORIENTATIVA para el personal medico.
"""

import re
import json
import socket
from datetime import datetime

# Requests para Ollama y verificacion de internet (sin dependencia critica)
try:
    import requests
    REQUESTS_DISPONIBLE = True
except ImportError:
    REQUESTS_DISPONIBLE = False

# OpenAI SDK para GPT-4o-mini (recomendado: rapido y economico)
try:
    import openai as _openai_module
    OPENAI_DISPONIBLE = True
except ImportError:
    OPENAI_DISPONIBLE = False

# Anthropic SDK para Claude API
try:
    import anthropic
    ANTHROPIC_DISPONIBLE = True
except ImportError:
    ANTHROPIC_DISPONIBLE = False


# ============================================================
# DISCLAIMER MEDICO (aparece siempre)
# ============================================================

DISCLAIMER = (
    "AVISO IMPORTANTE: Esta interpretacion es generada automaticamente con "
    "fines orientativos para el personal de laboratorio. NO constituye un "
    "diagnostico medico. La evaluacion clinica definitiva es responsabilidad "
    "exclusiva del medico tratante, quien debe correlacionar estos resultados "
    "con la historia clinica completa del paciente."
)


# ============================================================
# REGLAS CLINICAS LOCALES
# ============================================================

class MotorReglasClinicas:
    """
    Motor de reglas clinicas basadas en evidencia para interpretacion
    de resultados de laboratorio por area. Funciona completamente offline.
    """

    # Umbrales para hematologia (valores adultos de referencia general)
    # UNIDADES: los conteos celulares (GB, PLT) se almacenan en /mm3 (= /uL)
    # Es decir: leucocitos normales 4000-11000 /mm3, plaquetas 150000-400000 /mm3
    HB_ANEMIA_H = 13.0      # g/dL - hombre
    HB_ANEMIA_M = 12.0      # g/dL - mujer
    MCV_MICRO = 80           # fL - limite inferior (microcitosis)
    MCV_MACRO = 100          # fL - limite superior (macrocitosis)
    MCH_HIPOCR = 27          # pg - limite inferior (hipocromia)
    WBC_LEUCO_ALTO = 11000   # /mm3 - leucocitosis  (equivale a 11.0 x10^3/uL)
    WBC_LEUCO_BAJO = 4000    # /mm3 - leucopenia    (equivale a  4.0 x10^3/uL)
    PLT_TROMB_BAJO = 150000  # /mm3 - trombocitopenia (equivale a 150 x10^3/uL)
    PLT_TROMB_ALTO = 400000  # /mm3 - trombocitosis   (equivale a 400 x10^3/uL)

    def interpretar_hematologia(self, resultados_dict, sexo=''):
        """
        Interpreta un hemograma completo.
        Args:
            resultados_dict: {nombre_parametro_lower: (valor_numerico, fuera_rango)}
            sexo: str - 'M'/'Masculino'/'F'/'Femenino' para umbrales sexo-especificos
        Returns:
            list[str] de hallazgos clinicos
        """
        hallazgos = []
        obs = []

        hb = self._obtener_valor(resultados_dict, ['hemoglobina', 'hb', 'hgb'])
        hto = self._obtener_valor(resultados_dict, ['hematocrito', 'hto', 'hct'])
        mcv = self._obtener_valor(resultados_dict, ['mcv', 'vcm', 'volumen corpuscular medio'])
        mch = self._obtener_valor(resultados_dict, ['mch', 'hcm', 'hemoglobina corpuscular media'])
        wbc = self._obtener_valor(resultados_dict, ['leucocitos', 'wbc', 'glóbulos blancos', 'globulos blancos'])
        plt = self._obtener_valor(resultados_dict, ['plaquetas', 'plt', 'trombocitos'])
        rdw = self._obtener_valor(resultados_dict, ['rdw', 'ancho de distribucion eritrocitaria'])
        neut = self._obtener_valor(resultados_dict, ['neutrófilos', 'neutrofilos', 'neutrophils', 'neutrofilo %', 'neutrofilos %'])
        linf = self._obtener_valor(resultados_dict, ['linfocitos', 'lymphocytes', 'linfocito %', 'linfocitos %'])

        # Determinar umbral de anemia segun sexo (OMS)
        es_masculino = str(sexo).strip().upper() in ('M', 'MASCULINO', 'MALE')
        umbral_hb = self.HB_ANEMIA_H if es_masculino else self.HB_ANEMIA_M
        umbral_hto_bajo = 40 if es_masculino else 36

        # --- ANEMIA ---
        if hb is not None and hb < umbral_hb:
            gravedad = ''
            if hb < 7:
                gravedad = ' severa'
            elif hb < 10:
                gravedad = ' moderada'
            elif hb < 12:
                gravedad = ' leve'

            if mcv is not None:
                if mcv < self.MCV_MICRO:
                    tipo = 'microcítica'
                    if mch is not None and mch < self.MCH_HIPOCR:
                        tipo += ' hipocrómica'
                    obs.append(
                        f"Anemia{gravedad} {tipo} (Hb: {hb}, MCV: {mcv}). "
                        "Considerar: ferropenia, talasemia, anemia de enfermedad crónica."
                    )
                elif mcv > self.MCV_MACRO:
                    obs.append(
                        f"Anemia{gravedad} macrocítica (Hb: {hb}, MCV: {mcv}). "
                        "Considerar: déficit de vitamina B12/folato, hepatopatía, hipotiroidismo."
                    )
                else:
                    obs.append(
                        f"Anemia{gravedad} normocítica (Hb: {hb}, MCV: {mcv}). "
                        "Considerar: anemia de enfermedad crónica, pérdida aguda de sangre, "
                        "hemólisis, insuficiencia renal."
                    )
            else:
                obs.append(f"Hemoglobina reducida ({hb} g/dL). Evaluar tipo de anemia con índices eritrocitarios.")

            if rdw is not None and rdw > 14.5:
                obs.append("RDW elevado sugiere anisocitosis, compatible con ferropenia o déficit de B12/folato.")

            hallazgos.append('anemia_detectada')

        # Hemoglobina normal pero hematocrito bajo
        if hb is not None and hb >= umbral_hb and hto is not None and hto < umbral_hto_bajo:
            obs.append(f"Hematocrito reducido ({hto}%) con Hb en límite. Monitorear.")

        # --- LEUCOCITOS ---
        if wbc is not None:
            if wbc > self.WBC_LEUCO_ALTO:
                obs.append(
                    f"Leucocitosis ({wbc:,.0f} /mm³). "
                    "Causas frecuentes: infección bacteriana aguda, inflamación, "
                    "estrés fisiológico. Evaluar diferencial."
                )
                if neut is not None and neut > 75:
                    obs.append("Neutrofilia predominante: compatible con infección bacteriana o respuesta inflamatoria aguda.")
                if linf is not None and linf > 45:
                    obs.append("Linfocitosis: considerar infección viral, enfermedad linfoproliferativa.")
                hallazgos.append('leucocitosis')
            elif wbc < self.WBC_LEUCO_BAJO:
                obs.append(
                    f"Leucopenia ({wbc:,.0f} /mm³). "
                    "Causas: infección viral, medicamentos (quimioterapia, antibióticos), "
                    "enfermedades autoinmunes, aplasia medular."
                )
                if neut is not None and neut < 45:
                    obs.append("Neutropenia relativa: riesgo incrementado de infecciones bacterianas.")
                hallazgos.append('leucopenia')

        # --- PLAQUETAS ---
        if plt is not None:
            if plt < self.PLT_TROMB_BAJO:
                grado = 'leve' if plt >= 100000 else ('moderada' if plt >= 50000 else 'severa')
                obs.append(
                    f"Trombocitopenia {grado} ({plt:,.0f} /mm³). "
                    "Causas: PTI, hiperesplenismo, infecciones virales (dengue, VIH), "
                    "medicamentos, coagulopatía de consumo."
                )
                hallazgos.append('trombocitopenia')
            elif plt > self.PLT_TROMB_ALTO:
                obs.append(
                    f"Trombocitosis ({plt:,.0f} /mm³). "
                    "Causas reactivas: infección, inflamación, deficiencia de hierro. "
                    "Si >1.000.000: descartar trombocitemia esencial."
                )
                hallazgos.append('trombocitosis')

        if not obs:
            obs.append("Parámetros hematológicos dentro de límites normales en los valores evaluados.")

        return obs

    def interpretar_quimica(self, resultados_dict, sexo=''):
        """Interpreta química sanguínea (glucosa, lípidos, función renal y hepática)."""
        obs = []
        es_masculino = str(sexo).strip().upper() in ('M', 'MASCULINO', 'MALE')

        glucosa = self._obtener_valor(resultados_dict, ['glucosa', 'glucose', 'glicemia', 'glucemia'])
        hba1c = self._obtener_valor(resultados_dict, ['hemoglobina glicosilada', 'hba1c', 'a1c'])
        creat = self._obtener_valor(resultados_dict, ['creatinina', 'creatinine'])
        bun = self._obtener_valor(resultados_dict, ['bun', 'nitrogeno ureico', 'urea nitrógeno'])
        urea = self._obtener_valor(resultados_dict, ['urea'])
        tgo = self._obtener_valor(resultados_dict, ['tgo', 'ast', 'aspartato aminotransferasa', 'transaminasa oxalacetica'])
        tgp = self._obtener_valor(resultados_dict, ['tgp', 'alt', 'alanina aminotransferasa', 'transaminasa piruvica'])
        bilis_t = self._obtener_valor(resultados_dict, ['bilirrubina total', 'bilirubin total'])
        bilis_d = self._obtener_valor(resultados_dict, ['bilirrubina directa', 'bilirubin directa', 'bilirrubina conjugada'])
        col_t = self._obtener_valor(resultados_dict, ['colesterol total', 'cholesterol total', 'colesterol'])
        ldl = self._obtener_valor(resultados_dict, ['ldl', 'colesterol ldl', 'ldl colesterol'])
        hdl = self._obtener_valor(resultados_dict, ['hdl', 'colesterol hdl', 'hdl colesterol'])
        trig = self._obtener_valor(resultados_dict, ['triglicéridos', 'trigliceridos', 'triglycerides'])
        acido_urico = self._obtener_valor(resultados_dict, ['ácido úrico', 'acido urico', 'uric acid'])

        # --- GLUCOSA ---
        if glucosa is not None:
            if glucosa >= 126:
                obs.append(
                    f"Glucemia en ayunas elevada ({glucosa} mg/dL). "
                    "Compatible con Diabetes Mellitus (criterio ADA: glucosa ≥126 mg/dL en ayunas). "
                    "Se requiere confirmación con segunda medición y evaluación clínica."
                )
            elif glucosa >= 100:
                obs.append(
                    f"Glucemia en ayunas limítrofe ({glucosa} mg/dL). "
                    "Compatible con prediabetes / glucosa alterada en ayunas (100-125 mg/dL). "
                    "Recomendable cambios en estilo de vida y seguimiento periódico."
                )
            elif glucosa < 70:
                obs.append(
                    f"Hipoglucemia ({glucosa} mg/dL). "
                    "Evaluar ayuno prolongado, medicamentos hipoglucemiantes, insulinoma."
                )

        if hba1c is not None:
            if hba1c >= 6.5:
                obs.append(f"HbA1c elevada ({hba1c}%): diagnóstico de Diabetes Mellitus (≥6.5%).")
            elif hba1c >= 5.7:
                obs.append(f"HbA1c en rango de prediabetes ({hba1c}%, rango: 5.7-6.4%).")

        # --- FUNCION RENAL ---
        renal_alterado = False
        # Creatinina: umbral sexo-especifico (H: 1.3, M: 1.0 mg/dL)
        umbral_creat = 1.3 if es_masculino else 1.0
        if creat is not None and creat > umbral_creat:
            obs.append(
                f"Creatinina elevada ({creat} mg/dL, límite: {umbral_creat}). "
                "Sugiere reducción de filtrado glomerular. "
                "Evaluar: deshidratación, nefropatía, obstrucción urinaria, rabdomiólisis."
            )
            renal_alterado = True
        if bun is not None and bun > 20:
            obs.append(
                f"BUN elevado ({bun} mg/dL). "
                "Puede indicar insuficiencia renal, deshidratación, sangrado gastrointestinal."
            )
            renal_alterado = True
        if urea is not None and urea > 50:
            obs.append(f"Urea elevada ({urea} mg/dL). Compatible con disfunción renal o deshidratación.")
            renal_alterado = True
        if renal_alterado and creat is not None and creat > 0 and bun is not None:
            ratio = bun / creat
            if ratio > 20:
                obs.append(
                    f"Relación BUN/Creatinina elevada ({ratio:.1f}). "
                    "Sugiere causa prerrenal (deshidratación, sangrado GI)."
                )
            elif ratio < 10:
                obs.append("Relación BUN/Creatinina baja. Considerar causa intrarrenal.")

        umbral_urico = 7.0 if es_masculino else 6.0  # H: 3.4-7.0, M: 2.4-6.0 mg/dL
        if acido_urico is not None and acido_urico > umbral_urico:
            obs.append(
                f"Hiperuricemia ({acido_urico} mg/dL, límite: {umbral_urico}). "
                "Asociada a gota, síndrome metabólico, enfermedad renal crónica."
            )

        # --- FUNCION HEPATICA ---
        hepatico_alterado = False
        if tgo is not None and tgo > 40:
            factor = tgo / 40
            grado = 'leve' if factor < 3 else ('moderada' if factor < 10 else 'marcada')
            obs.append(
                f"TGO/AST elevado ({tgo} U/L, {factor:.1f}x VN) - elevación {grado}. "
                "Etiología: hepatitis, hepatopatía alcohólica, cardiopatía isquémica, miopatía."
            )
            hepatico_alterado = True
        if tgp is not None and tgp > 41:
            factor = tgp / 41
            grado = 'leve' if factor < 3 else ('moderada' if factor < 10 else 'marcada')
            obs.append(
                f"TGP/ALT elevado ({tgp} U/L, {factor:.1f}x VN) - elevación {grado}. "
                "TGP es más específica del hígado; niveles marcados sugieren daño hepatocelular agudo."
            )
            hepatico_alterado = True
        if hepatico_alterado and tgo is not None and tgp is not None and tgp > 0:
            ratio_de_ritis = tgo / tgp
            if ratio_de_ritis > 2:
                obs.append(
                    f"Relación TGO/TGP > 2 ({ratio_de_ritis:.1f}): "
                    "sugestivo de hepatopatía alcohólica."
                )

        if bilis_t is not None and bilis_t > 1.2:
            if bilis_d is not None and bilis_d > 0.4:
                tipo_bil = "directa (conjugada): evaluar colestasis, obstrucción biliar, hepatitis"
            else:
                tipo_bil = "indirecta (no conjugada): evaluar hemólisis, síndrome de Gilbert"
            obs.append(
                f"Hiperbilirrubinemia (BilT: {bilis_t} mg/dL). "
                f"Predominio {tipo_bil}."
            )

        # --- PERFIL LIPIDICO ---
        dislipi = []
        if col_t is not None:
            if col_t >= 240:
                dislipi.append(f"Hipercolesterolemia ({col_t} mg/dL > 240)")
            elif col_t >= 200:
                dislipi.append(f"Colesterol total limítrofe ({col_t} mg/dL, 200-239)")
        if ldl is not None:
            if ldl >= 160:
                dislipi.append(f"LDL elevado ({ldl} mg/dL ≥ 160)")
            elif ldl >= 130:
                dislipi.append(f"LDL limítrofe ({ldl} mg/dL, 130-159)")
        if hdl is not None:
            umbral_hdl = 40 if es_masculino else 50  # H: <40 riesgo, M: <50 riesgo (ATP III)
            if hdl < umbral_hdl:
                dislipi.append(f"HDL bajo ({hdl} mg/dL < {umbral_hdl}) — factor de riesgo cardiovascular")
        if trig is not None:
            if trig >= 500:
                dislipi.append(f"Hipertrigliceridemia severa ({trig} mg/dL ≥ 500, riesgo pancreatitis)")
            elif trig >= 200:
                dislipi.append(f"Hipertrigliceridemia ({trig} mg/dL ≥ 200)")
            elif trig >= 150:
                dislipi.append(f"Triglicéridos limítrofes ({trig} mg/dL, 150-199)")

        if dislipi:
            obs.append(
                "Alteraciones en perfil lipídico: " + "; ".join(dislipi) + ". "
                "Evaluar riesgo cardiovascular global y considerar modificaciones del estilo de vida."
            )

        if not obs:
            obs.append("Parámetros de química sanguínea evaluados dentro de los límites de referencia.")

        return obs

    def interpretar_coagulacion(self, resultados_dict):
        """Interpreta pruebas de coagulación."""
        obs = []

        tp = self._obtener_valor(resultados_dict, ['tiempo de protrombina', 'tp', 'pt', 'protrombina'])
        tpt = self._obtener_valor(resultados_dict, ['tiempo parcial tromboplastina', 'tpt', 'aptt', 'tptt', 'ptt'])
        inr = self._obtener_valor(resultados_dict, ['inr', 'razón normalizada internacional'])
        fibrin = self._obtener_valor(resultados_dict, ['fibrinógeno', 'fibrinogen', 'fibrinogeno'])
        dd = self._obtener_valor(resultados_dict, ['dímero d', 'dimero d', 'd-dimer'])

        if tp is not None and tp > 14:
            obs.append(
                f"Tiempo de protrombina prolongado ({tp} seg). "
                "Sugiere: déficit de factores vía extrínseca (II, V, VII, X), "
                "disfunción hepática, déficit de vitamina K, anticoagulación oral."
            )
        if tpt is not None and tpt > 40:
            obs.append(
                f"TPT prolongado ({tpt} seg). "
                "Sugiere: déficit de factores vía intrínseca (VIII, IX, XI, XII), "
                "hemofilia A/B, anticoagulante lúpico, heparina."
            )
        if inr is not None:
            if inr > 3.0:
                obs.append(
                    f"INR elevado ({inr}). "
                    "Si bajo tratamiento anticoagulante: sobreanticoagulación, riesgo hemorrágico. "
                    "Sin anticoagulante: hepatopatía severa o coagulopatía."
                )
            elif inr > 1.5:
                obs.append(
                    f"INR limítrofe ({inr}). Monitorear si está en anticoagulación oral."
                )
        if fibrin is not None and fibrin < 200:
            obs.append(
                f"Fibrinógeno bajo ({fibrin} mg/dL). "
                "Considerar: CID, hepatopatía severa, hiperfibrinólisis."
            )
        if dd is not None and dd > 0.5:
            obs.append(
                f"Dímero D elevado ({dd} µg/mL FEU). "
                "Sugiere activación de la coagulación/fibrinólisis. "
                "Evaluar: TVP, TEP, CID, infección severa, cirugía reciente."
            )

        if not obs:
            obs.append("Pruebas de coagulación dentro de parámetros normales.")

        return obs

    def interpretar_uroanalis(self, resultados_dict):
        """Interpreta el uroanálisis completo."""
        obs = []

        glucosuria = self._obtener_valor_texto(resultados_dict,
            ['glucosa orina', 'glucosuria', 'glucosa en orina', 'glucose urine'])
        proteinuria = self._obtener_valor_texto(resultados_dict,
            ['proteínas orina', 'proteinuria', 'proteinas', 'protein urine'])
        leucocituria = self._obtener_valor(resultados_dict,
            ['leucocitos orina', 'leucocitos campo', 'leucocitos/campo', 'wbc orina'])
        hematuria = self._obtener_valor(resultados_dict,
            ['hematíes', 'eritrocitos orina', 'eritrocitos/campo', 'rbc orina', 'hematies'])
        bacterias = self._obtener_valor_texto(resultados_dict,
            ['bacterias', 'bacteria', 'bacteria orina'])
        nitritos = self._obtener_valor_texto(resultados_dict, ['nitritos', 'nitrites'])
        cetonas = self._obtener_valor_texto(resultados_dict, ['cetonas', 'cuerpos cetónicos', 'ketones'])
        densidad = self._obtener_valor(resultados_dict, ['densidad', 'gravedad específica'])
        ph_orina = self._obtener_valor(resultados_dict, ['ph orina', 'ph'])

        # Infeccion urinaria
        itu_indicators = 0
        if leucocituria is not None and leucocituria > 5:
            obs.append(f"Leucocituria ({leucocituria}/campo). Sugiere proceso inflamatorio/infeccioso urinario.")
            itu_indicators += 1
        if bacterias and str(bacterias).lower() not in ('negativo', 'ninguna', 'no', 'ausente', '0', ''):
            obs.append(f"Bacteriuria presente. Considerar infección urinaria.")
            itu_indicators += 1
        if nitritos and str(nitritos).lower() in ('positivo', '+', '++', 'presente'):
            obs.append("Nitritos positivos: alta especificidad para bacteriuria gram-negativa (E.coli, Klebsiella).")
            itu_indicators += 1
        if itu_indicators >= 2:
            obs.append("Cuadro compatible con Infección del Tracto Urinario (ITU). Correlacionar con clínica y considerar urocultivo.")

        # Glucosuria
        if glucosuria and str(glucosuria).lower() not in ('negativo', 'no', 'ausente', '0', ''):
            obs.append(
                "Glucosuria: presencia de glucosa en orina. "
                "Causas: diabetes mellitus descompensada (umbral renal superado), "
                "glucosuria renal (déficit tubular). Correlacionar con glucemia."
            )

        # Proteinuria
        if proteinuria and str(proteinuria).lower() not in ('negativo', 'trazas', 'no', 'ausente', '0', ''):
            nivel = str(proteinuria).count('+')
            if nivel >= 3:
                obs.append("Proteinuria marcada (3+ o más). Considerar síndrome nefrótico, glomerulonefritis.")
            elif nivel >= 1:
                obs.append("Proteinuria: vigilar enfermedad renal crónica, hipertensión, diabetes nefropática.")

        # Hematuria
        if hematuria is not None and hematuria > 3:
            obs.append(
                f"Hematuria ({hematuria}/campo). "
                "Diagnóstico diferencial: litiasis renal, infección urinaria, "
                "glomerulonefritis, traumatismo, neoplasia urinaria."
            )

        # Cetonas
        if cetonas and str(cetonas).lower() not in ('negativo', 'no', 'ausente', '0', ''):
            obs.append(
                "Cetonuria: cuerpos cetónicos en orina. "
                "Evaluar: cetoacidosis diabética, ayuno prolongado, dieta baja en carbohidratos."
            )

        # Densidad
        if densidad is not None:
            if densidad > 1.030:
                obs.append(f"Densidad urinaria elevada ({densidad}). Compatible con deshidratación o orina concentrada.")
            elif densidad < 1.005:
                obs.append(f"Densidad urinaria baja ({densidad}). Sugiere hiposmolalidad o ingesta excesiva de líquidos.")

        if not obs:
            obs.append("Uroanálisis sin hallazgos significativos en los parámetros evaluados.")

        return obs

    def interpretar_tiroides(self, resultados_dict):
        """Interpreta perfil tiroideo."""
        obs = []

        tsh = self._obtener_valor(resultados_dict, ['tsh', 'tirotropina', 'hormona estimulante tiroides'])
        t4l = self._obtener_valor(resultados_dict, ['t4 libre', 't4l', 'tiroxina libre', 'free t4', 'ft4'])
        t4t = self._obtener_valor(resultados_dict, ['t4 total', 't4 total', 'tiroxina total'])
        t3l = self._obtener_valor(resultados_dict, ['t3 libre', 't3l', 'triyodotironina libre', 'free t3', 'ft3'])
        t3t = self._obtener_valor(resultados_dict, ['t3 total', 'triyodotironina total'])
        anti_tpo = self._obtener_valor(resultados_dict, ['anti-tpo', 'anticuerpos antiperoxidasa', 'tpo ab', 'anti tpo'])
        anti_tg = self._obtener_valor(resultados_dict, ['anti-tiroglobulina', 'anticuerpos antitiroglobulina', 'tg ab'])
        tsi = self._obtener_valor(resultados_dict, ['tsi', 'trab', 'anticuerpos receptor tsh'])

        if tsh is not None:
            if tsh > 4.5:
                if (t4l is not None and t4l < 0.8) or (t4t is not None and t4t < 5):
                    obs.append(
                        f"Hipotiroidismo primario franco (TSH: {tsh} µU/mL, T4L baja). "
                        "Causas frecuentes: tiroiditis de Hashimoto, tiroidectomía, ablación con I-131."
                    )
                else:
                    obs.append(
                        f"Hipotiroidismo subclínico (TSH: {tsh} µU/mL con T4L normal). "
                        "Vigilar síntomas y anticuerpos tiroideos. Considerar tratamiento si TSH > 10."
                    )
            elif tsh < 0.4:
                if (t4l is not None and t4l > 1.8) or (t3l is not None and t3l > 4.4):
                    obs.append(
                        f"Hipertiroidismo franco (TSH: {tsh} µU/mL, T4L/T3L elevada). "
                        "Considerar: enfermedad de Graves, bocio multinodular tóxico, adenoma tóxico."
                    )
                else:
                    obs.append(
                        f"Hipertiroidismo subclínico (TSH: {tsh} µU/mL con T4L normal). "
                        "Vigilar arritmias, pérdida ósea. Descartar causa exógena."
                    )

        if anti_tpo is not None and anti_tpo > 35:
            obs.append(
                f"Anti-TPO positivos ({anti_tpo} IU/mL). "
                "Sugiere tiroiditis autoinmune (Hashimoto o Graves). "
                "Correlacionar con función tiroidea y clínica."
            )
        if anti_tg is not None and anti_tg > 115:
            obs.append(
                f"Anti-Tiroglobulina positivos ({anti_tg} IU/mL). "
                "Anticuerpos tiroideos positivos. Evaluar en conjunto con anti-TPO y función tiroidea."
            )
        if tsi is not None and tsi > 1.75:
            obs.append(
                f"TSI/TRAb positivos ({tsi}): anticuerpos estimulantes del receptor de TSH. "
                "Altamente sugestivo de enfermedad de Graves."
            )

        if not obs:
            obs.append("Función tiroidea dentro de parámetros normales en los valores evaluados.")

        return obs

    def interpretar_serologia(self, resultados_dict):
        """Interpreta marcadores serológicos (virales, infecciosos, autoinmunes)."""
        obs = []

        hbsag = self._obtener_valor_texto(resultados_dict, ['hbsag', 'antígeno superficie hepatitis b', 'ag hbs'])
        anti_hcv = self._obtener_valor_texto(resultados_dict, ['anti-hcv', 'anticuerpos hepatitis c', 'anti hcv'])
        anti_hiv = self._obtener_valor_texto(resultados_dict, ['anti-hiv', 'vih', 'hiv', 'anti vih', 'anti-vih'])
        vdrl = self._obtener_valor_texto(resultados_dict, ['vdrl', 'rpr', 'serología sífilis'])
        toxo_igg = self._obtener_valor_texto(resultados_dict, ['toxoplasma igg', 'toxoplasmosis igg'])
        toxo_igm = self._obtener_valor_texto(resultados_dict, ['toxoplasma igm', 'toxoplasmosis igm'])
        rubeo_igg = self._obtener_valor_texto(resultados_dict, ['rubeola igg', 'rubella igg'])
        rubeo_igm = self._obtener_valor_texto(resultados_dict, ['rubeola igm', 'rubella igm'])
        cmv_igm = self._obtener_valor_texto(resultados_dict, ['cmv igm', 'citomegalovirus igm'])
        pcr = self._obtener_valor(resultados_dict, ['proteína c reactiva', 'pcr', 'crp', 'proteina c reactiva'])
        ana = self._obtener_valor_texto(resultados_dict, ['ana', 'anticuerpos antinucleares', 'antinucleares'])

        positivo_set = {'positivo', 'reactivo', '+', 'detectado', 'present', 'reactive', 'positive'}

        def es_positivo(val):
            return val and str(val).lower().strip() in positivo_set

        if es_positivo(hbsag):
            obs.append(
                "HBsAg REACTIVO: Portador de antígeno de superficie de Hepatitis B. "
                "Requiere confirmación, evaluación de carga viral (HBV-DNA), "
                "función hepática y derivación a hepatología."
            )
        if es_positivo(anti_hcv):
            obs.append(
                "Anti-HCV REACTIVO: Exposición a virus Hepatitis C. "
                "Confirmar con HCV-RNA (carga viral) para distinguir infección activa de resuelta. "
                "Derivar a hepatología."
            )
        if es_positivo(anti_hiv):
            obs.append(
                "Anti-VIH REACTIVO en prueba de tamizaje. "
                "DEBE confirmarse con Western Blot / prueba confirmatoria. "
                "Asesoría confidencial y derivación inmediata a infectología."
            )
        if es_positivo(vdrl):
            obs.append(
                "VDRL/RPR REACTIVO: Prueba reagínica positiva para sífilis. "
                "Confirmar con prueba treponémica (FTA-ABS, TPHA). "
                "Evaluar estadio y tratar según protocolo."
            )

        # TORCH
        if es_positivo(toxo_igm):
            obs.append("Toxoplasma IgM positivo: infección reciente/activa posible. Correlacionar clínicamente. Crítico en embarazo.")
        elif es_positivo(toxo_igg):
            obs.append("Toxoplasma IgG positivo: infección previa/exposición. Inmunidad adquirida (sin IgM activa).")

        if es_positivo(rubeo_igm):
            obs.append("Rubéola IgM positivo: infección aguda. Crítico en primer trimestre de embarazo (riesgo síndrome congénito).")
        if es_positivo(cmv_igm):
            obs.append("CMV IgM positivo: infección activa por Citomegalovirus. Vigilar en inmunosuprimidos y embarazo.")

        # PCR
        if pcr is not None and pcr > 5:
            grado = 'leve' if pcr < 20 else ('moderada' if pcr < 80 else 'severa')
            obs.append(
                f"PCR elevada ({pcr} mg/L) — inflamación {grado}. "
                "Biomarcador inespecífico. Causas: infección bacteriana, vasculitis, trauma, "
                "infarto, neoplasia, enfermedad autoinmune."
            )

        # ANA
        if ana and str(ana).lower() not in ('negativo', 'no detectado', 'no', ''):
            obs.append(
                f"ANA positivos ({ana}). "
                "Evaluar patrón y título. Asociados a: LES, SSc, síndrome de Sjögren, EMTC. "
                "Correlacionar con clínica y anticuerpos específicos (anti-dsDNA, anti-Sm)."
            )

        if not obs:
            obs.append("Marcadores serológicos evaluados sin hallazgos positivos significativos.")

        return obs

    # ----------------------------------------------------------
    # UTILIDADES INTERNAS
    # ----------------------------------------------------------

    @staticmethod
    def _normalizar_nombre(nombre):
        """Normaliza un nombre de parametro para comparacion (sin acentos, lowercase, stripped)."""
        n = nombre.lower().strip()
        for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'),
                      ('ñ', 'n'), ('ü', 'u')]:
            n = n.replace(a, b)
        return n

    def _obtener_valor(self, resultados_dict, nombres_posibles):
        """
        Busca el valor numerico de un parametro por nombre (case-insensitive).
        Usa coincidencia EXACTA normalizada, no substring, para evitar falsos positivos
        como 'glucosa' matcheando 'glucosa orina'.
        """
        # Primera pasada: buscar coincidencia exacta
        for nombre in nombres_posibles:
            clave = self._normalizar_nombre(nombre)
            for k, v in resultados_dict.items():
                k_norm = self._normalizar_nombre(k)
                if clave == k_norm:
                    val = v[0] if isinstance(v, tuple) else v
                    try:
                        return float(str(val).replace(',', '.').strip())
                    except (ValueError, TypeError):
                        pass
        # Segunda pasada: buscar si el nombre del dict COMIENZA con la clave
        # (para manejar variantes como "hemoglobina (hgb)")
        for nombre in nombres_posibles:
            clave = self._normalizar_nombre(nombre)
            if len(clave) < 3:  # Evitar matches parciales para claves muy cortas
                continue
            for k, v in resultados_dict.items():
                k_norm = self._normalizar_nombre(k)
                if k_norm.startswith(clave + ' ') or k_norm.startswith(clave + '('):
                    val = v[0] if isinstance(v, tuple) else v
                    try:
                        return float(str(val).replace(',', '.').strip())
                    except (ValueError, TypeError):
                        pass
        return None

    def _obtener_valor_texto(self, resultados_dict, nombres_posibles):
        """
        Busca el valor de texto de un parametro por nombre (case-insensitive).
        Usa coincidencia EXACTA normalizada, no substring.
        """
        # Primera pasada: coincidencia exacta
        for nombre in nombres_posibles:
            clave = self._normalizar_nombre(nombre)
            for k, v in resultados_dict.items():
                k_norm = self._normalizar_nombre(k)
                if clave == k_norm:
                    val = v[0] if isinstance(v, tuple) else v
                    if val is not None:
                        return str(val).strip()
        # Segunda pasada: startswith para variantes
        for nombre in nombres_posibles:
            clave = self._normalizar_nombre(nombre)
            if len(clave) < 3:
                continue
            for k, v in resultados_dict.items():
                k_norm = self._normalizar_nombre(k)
                if k_norm.startswith(clave + ' ') or k_norm.startswith(clave + '('):
                    val = v[0] if isinstance(v, tuple) else v
                    if val is not None:
                        return str(val).strip()
        return None


# ============================================================
# CLASE PRINCIPAL: InterpretadorClinico
# ============================================================

class InterpretadorClinico:
    """
    Motor de interpretacion clinica con triple nivel de fallback:
    Reglas locales (siempre) -> Ollama (opcional) -> Claude API (opcional).
    """

    # IDs de areas (hardcodeados segun MEMORY.md)
    AREA_HEMATOLOGIA = 1
    AREA_QUIMICA = 2
    AREA_COAGULACION = 5
    AREA_UROANALIS = 6
    AREA_PARASITOLOGIA = 7
    AREA_TIROIDES = 8
    AREA_SEROLOGIA = 9
    AREA_MICROBIOLOGIA = 10
    AREA_GENERAL = 29

    def __init__(self, config=None):
        """
        Args:
            config: dict con keys opcionales:
                'claude_api_key': str
                'ollama_url': str (default: http://localhost:11434)
                'ollama_modelo': str (default: llama3.2)
                'proveedor_ia': 'reglas' | 'ollama' | 'claude'
        """
        self.config = config or {}
        self.motor_reglas = MotorReglasClinicas()

    # ----------------------------------------------------------
    # VERIFICACION DE CONECTIVIDAD
    # ----------------------------------------------------------

    def verificar_conexion_internet(self, host='8.8.8.8', port=53, timeout=2):
        """Verifica conectividad a internet (DNS Google)."""
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((host, port))
            return True
        except (socket.error, OSError):
            return False
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

    def verificar_ollama(self, url=None):
        """Verifica si Ollama esta corriendo y disponible."""
        if not REQUESTS_DISPONIBLE:
            return False
        url_base = url or self.config.get('ollama_url', 'http://localhost:11434')
        try:
            r = requests.get(f'{url_base}/api/tags', timeout=3)
            return r.status_code == 200
        except Exception:
            return False

    def verificar_claude(self):
        """Verifica si Claude API es accesible (requiere API key)."""
        api_key = self.config.get('claude_api_key', '')
        return bool(api_key and api_key.startswith('sk-ant-'))

    def estado_proveedores(self):
        """
        Retorna el estado de todos los proveedores.
        Returns:
            dict: {'reglas': True, 'ollama': bool, 'claude': bool, 'internet': bool}
        """
        tiene_internet = self.verificar_conexion_internet()
        return {
            'reglas': True,
            'ollama': self.verificar_ollama(),
            'claude': self.verificar_claude() and tiene_internet,
            'internet': tiene_internet,
        }

    # ----------------------------------------------------------
    # INTERPRETACION PRINCIPAL
    # ----------------------------------------------------------

    def interpretar_completo(self, area_id, resultados_parametros, paciente_info=None,
                              prueba_nombre='', historial_previo=None):
        """
        Genera una interpretacion clinica completa con el mejor proveedor disponible.

        Args:
            area_id: int - ID del area clinica
            resultados_parametros: list[dict] con:
                {'nombre': str, 'valor': str, 'valor_referencia': str,
                 'fuera_rango': str, 'tipo_alerta': str, 'unidad': str}
            paciente_info: dict con 'Nombres', 'Apellidos', 'FechaNacimiento', 'Sexo'
            prueba_nombre: str - nombre de la prueba
            historial_previo: dict - datos de evolucion previa (opcional)

        Returns:
            dict:
                'hallazgos': list[str] - hallazgos principales
                'interpretacion_reglas': list[str] - texto de reglas locales
                'interpretacion_ia': str - texto de IA (Ollama/Claude) o ''
                'proveedor_usado': str - 'reglas' | 'ollama' | 'claude'
                'parametros_alterados': list[dict]
                'tiene_alertas_criticas': bool
                'resumen_ejecutivo': str
                'motor_ia_disponible': bool
        """
        resultado = {
            'hallazgos': [],
            'interpretacion_reglas': [],
            'interpretacion_ia': '',
            'proveedor_usado': 'reglas',
            'parametros_alterados': [],
            'tiene_alertas_criticas': False,
            'resumen_ejecutivo': '',
            'motor_ia_disponible': False,
            'error': None,
        }

        # Normalizar resultados a dict para motor de reglas
        resultados_norm = {}
        params_alterados = []
        tiene_criticos = False

        for p in resultados_parametros:
            nombre = str(p.get('nombre', '')).lower().strip()
            valor = p.get('valor', '')
            unidad = p.get('unidad', '')
            ref = p.get('valor_referencia', '')
            fuera = p.get('fuera_rango', '') or ''
            alerta = p.get('tipo_alerta', '') or ''

            resultados_norm[nombre] = (valor, fuera)

            if fuera and str(fuera).lower() not in ('', 'none', 'normal'):
                alteration = {
                    'nombre': p.get('nombre', ''),
                    'valor': valor,
                    'unidad': unidad,
                    'referencia': ref,
                    'estado': fuera,
                    'alerta': alerta,
                }
                params_alterados.append(alteration)
                if 'critico' in str(alerta).lower():
                    tiene_criticos = True

        resultado['parametros_alterados'] = params_alterados
        resultado['tiene_alertas_criticas'] = tiene_criticos

        # Extraer sexo del paciente para reglas sexo-especificas
        sexo_paciente = ''
        if paciente_info:
            sexo_paciente = paciente_info.get('Sexo', paciente_info.get('sexo', ''))

        # Reglas locales segun area
        obs_reglas = self._aplicar_reglas_area(area_id, resultados_norm, sexo_paciente)
        resultado['interpretacion_reglas'] = obs_reglas

        # Resumen ejecutivo rapido
        n_alterados = len(params_alterados)
        if n_alterados == 0:
            resultado['resumen_ejecutivo'] = f"Resultados de {prueba_nombre} dentro de rangos normales."
        elif n_alterados == 1:
            resultado['resumen_ejecutivo'] = (
                f"1 parámetro alterado en {prueba_nombre}: {params_alterados[0]['nombre']}."
            )
        else:
            nombres_alt = ', '.join(p['nombre'] for p in params_alterados[:3])
            if n_alterados > 3:
                nombres_alt += f' y {n_alterados - 3} más'
            resultado['resumen_ejecutivo'] = (
                f"{n_alterados} parámetros alterados en {prueba_nombre}: {nombres_alt}."
            )
        if tiene_criticos:
            resultado['resumen_ejecutivo'] += " ⚠️ VALORES CRÍTICOS PRESENTES."

        # Intentar IA si hay parametros alterados y proveedor configurado
        proveedor_config = self.config.get('proveedor_ia', 'reglas')

        if params_alterados and proveedor_config != 'reglas':
            prompt = self._construir_prompt_clinico(
                area_id, resultados_parametros, paciente_info,
                prueba_nombre, obs_reglas, historial_previo
            )

            if proveedor_config == 'ollama' and self.verificar_ollama():
                ia_texto = self._interpretar_ollama(prompt)
                if ia_texto:
                    resultado['interpretacion_ia'] = ia_texto
                    resultado['proveedor_usado'] = 'ollama'
                    resultado['motor_ia_disponible'] = True

            elif proveedor_config == 'claude' and self.verificar_claude():
                if self.verificar_conexion_internet():
                    ia_texto = self._interpretar_claude(prompt)
                    if ia_texto:
                        resultado['interpretacion_ia'] = ia_texto
                        resultado['proveedor_usado'] = 'claude'
                        resultado['motor_ia_disponible'] = True
        elif proveedor_config != 'reglas':
            resultado['motor_ia_disponible'] = False

        return resultado

    # ----------------------------------------------------------
    # REGLAS POR AREA
    # ----------------------------------------------------------

    def _aplicar_reglas_area(self, area_id, resultados_norm, sexo=''):
        """Aplica las reglas clinicas del motor local segun area."""
        try:
            if area_id == self.AREA_HEMATOLOGIA:
                return self.motor_reglas.interpretar_hematologia(resultados_norm, sexo=sexo)
            elif area_id == self.AREA_QUIMICA:
                return self.motor_reglas.interpretar_quimica(resultados_norm, sexo=sexo)
            elif area_id == self.AREA_COAGULACION:
                return self.motor_reglas.interpretar_coagulacion(resultados_norm)
            elif area_id == self.AREA_UROANALIS:
                return self.motor_reglas.interpretar_uroanalis(resultados_norm)
            elif area_id == self.AREA_TIROIDES:
                return self.motor_reglas.interpretar_tiroides(resultados_norm)
            elif area_id == self.AREA_SEROLOGIA:
                return self.motor_reglas.interpretar_serologia(resultados_norm)
            elif area_id == self.AREA_MICROBIOLOGIA:
                return ["Resultados de microbiología disponibles. Evaluar antibiograma y sensibilidad para orientar tratamiento antibiótico."]
            elif area_id == self.AREA_PARASITOLOGIA:
                return ["Revisar informe de parasitología. Identificar parásito y estadio para definir tratamiento antiparasitario."]
            else:
                return self._reglas_generales(resultados_norm)
        except Exception as e:
            return [f"Interpretación de reglas no disponible para esta área ({e})."]

    def _reglas_generales(self, resultados_norm):
        """Reglas genericas para areas sin reglas especificas."""
        obs = []
        for nombre, (valor, fuera_rango) in resultados_norm.items():
            if fuera_rango and str(fuera_rango).lower() not in ('', 'none', 'normal'):
                estado = 'elevado' if str(fuera_rango).lower() in ('alto', 'criticoalto') else 'bajo'
                obs.append(f"{nombre.capitalize()}: valor {estado} ({valor}). Evaluar con contexto clínico.")
        if not obs:
            obs.append("Parámetros evaluados dentro de los rangos de referencia.")
        return obs

    # ----------------------------------------------------------
    # CONSTRUCCION DE PROMPT PARA LLM
    # ----------------------------------------------------------

    def _construir_prompt_clinico(self, area_id, resultados_parametros, paciente_info,
                                   prueba_nombre, obs_reglas, historial_previo=None):
        """Construye el prompt para enviar al LLM (Ollama o Claude)."""

        nombres_areas = {
            1: 'Hematología', 2: 'Química Sanguínea', 5: 'Coagulación',
            6: 'Uroanálisis', 7: 'Parasitología', 8: 'Tiroides/Hormonal',
            9: 'Serología', 10: 'Microbiología', 29: 'General'
        }
        area_nombre = nombres_areas.get(area_id, f'Área {area_id}')

        # Info del paciente (anonimizada - solo edad, sexo y contexto clinico)
        info_pac = ""
        contexto_clinico = ""
        if paciente_info:
            sexo = paciente_info.get('Sexo', paciente_info.get('sexo', ''))
            fnac = paciente_info.get('FechaNacimiento', paciente_info.get('fecha_nacimiento'))
            edad = ""
            if fnac:
                try:
                    if isinstance(fnac, str):
                        fnac = datetime.strptime(fnac[:10], '%Y-%m-%d')
                    edad = f"{(datetime.now() - fnac).days // 365} años"
                except Exception:
                    pass
            if sexo or edad:
                info_pac = f"Paciente: {sexo or 'sexo no especificado'}, {edad or 'edad no especificada'}."

            # Contexto clinico de la solicitud
            ctx_partes = []
            diagnostico = str(paciente_info.get('DiagnosticoPresuntivo', '') or '').strip()
            obs_sol = str(paciente_info.get('ObservacionesSolicitud', '') or '').strip()
            if diagnostico:
                ctx_partes.append(f"Diagnóstico presuntivo / motivo de consulta: {diagnostico}")
            if obs_sol:
                ctx_partes.append(f"Observaciones clínicas del solicitante: {obs_sol}")
            if ctx_partes:
                contexto_clinico = "\nCONTEXTO CLÍNICO:\n" + "\n".join(ctx_partes)

        # Tabla de resultados
        tabla_resultados = []
        for p in resultados_parametros:
            estado = ""
            fuera = str(p.get('fuera_rango', '') or '').lower()
            if 'criticoalto' in fuera:
                estado = " [CRITICO-ALTO]"
            elif 'criticobajo' in fuera:
                estado = " [CRITICO-BAJO]"
            elif 'alto' in fuera:
                estado = " [ALTO]"
            elif 'bajo' in fuera:
                estado = " [BAJO]"
            linea = (
                f"  - {p.get('nombre', '')}: {p.get('valor', '')} "
                f"{p.get('unidad', '')} (Ref: {p.get('valor_referencia', 'N/D')}){estado}"
            )
            tabla_resultados.append(linea)

        # Historial previo resumido
        historial_str = ""
        if historial_previo and historial_previo.get('mediciones'):
            n_prev = len(historial_previo['mediciones'])
            if n_prev > 1:
                historial_str = (
                    f"\nHistorial: {n_prev} mediciones previas disponibles. "
                    f"Primera: {historial_previo['mediciones'][0].get('fecha', 'N/D')}, "
                    f"Última: {historial_previo['mediciones'][-1].get('fecha', 'N/D')}."
                )

        # Interpretacion de reglas
        reglas_str = "\n".join(f"  - {o}" for o in obs_reglas[:5]) if obs_reglas else "  (ninguna)"

        prompt = f"""Eres un asistente de laboratorio clínico especializado en interpretación de resultados.
Analiza los siguientes resultados de {prueba_nombre} ({area_nombre}) y proporciona una interpretación clínica orientativa.

{info_pac}
{contexto_clinico}
{historial_str}

RESULTADOS DE LABORATORIO:
{chr(10).join(tabla_resultados)}

ANÁLISIS PRELIMINAR DEL SISTEMA:
{reglas_str}

Por favor proporciona:
1. INTERPRETACIÓN CLÍNICA: Análisis integrado de los hallazgos en el contexto clínico del paciente
2. CONSIDERACIONES DIAGNÓSTICAS: Posibles condiciones a evaluar (en orden de probabilidad)
3. OBSERVACIONES: Correlaciones clínicas relevantes o pruebas complementarias sugeridas

IMPORTANTE: Esta es información orientativa para el personal de laboratorio. El diagnóstico definitivo lo realiza el médico tratante.
Responde de forma concisa, clara y en español. Usa términos médicos precisos pero comprensibles."""

        return prompt

    # ----------------------------------------------------------
    # LLAMADAS A LLM
    # ----------------------------------------------------------

    def _interpretar_ollama(self, prompt):
        """Envia el prompt a Ollama y retorna la respuesta."""
        if not REQUESTS_DISPONIBLE:
            return None
        url_base = self.config.get('ollama_url', 'http://localhost:11434')
        modelo = self.config.get('ollama_modelo', 'llama3.2')
        try:
            resp = requests.post(
                f'{url_base}/api/generate',
                json={'model': modelo, 'prompt': prompt, 'stream': False},
                timeout=120
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get('response', '').strip()
            return None
        except Exception as e:
            print(f"[IA] Error Ollama: {e}")
            return None

    def _interpretar_claude(self, prompt):
        """Envia el prompt a Claude API y retorna la respuesta."""
        if not ANTHROPIC_DISPONIBLE:
            return None
        api_key = self.config.get('claude_api_key', '')
        if not api_key:
            return None
        try:
            modelo_claude = self.config.get('claude_modelo', 'claude-haiku-4-5-20251001')
            cliente = anthropic.Anthropic(api_key=api_key)
            mensaje = cliente.messages.create(
                model=modelo_claude,
                max_tokens=1024,
                messages=[{'role': 'user', 'content': prompt}]
            )
            return mensaje.content[0].text.strip()
        except Exception as e:
            print(f"[IA] Error Claude API: {e}")
            return None

    # ----------------------------------------------------------
    # FORMATEO DE REPORTE
    # ----------------------------------------------------------

    def formatear_reporte_texto(self, interpretacion, prueba_nombre='', fecha=None):
        """
        Formatea el resultado de interpretar_completo() como texto plano
        para mostrar en ScrolledText o exportar.

        Returns:
            list[tuple]: [(texto, tag_estilo), ...] donde tag_estilo es uno de:
                'titulo', 'seccion', 'normal', 'alerta', 'critico', 'ia', 'disclaimer'
        """
        partes = []
        fecha_str = (fecha or datetime.now()).strftime('%d/%m/%Y %H:%M') if isinstance(fecha, datetime) else (
            datetime.now().strftime('%d/%m/%Y %H:%M'))

        partes.append((f"INTERPRETACIÓN CLÍNICA — {prueba_nombre}\n", 'titulo'))
        partes.append((f"Generada el {fecha_str}\n\n", 'normal'))

        # Resumen ejecutivo
        partes.append(("RESUMEN\n", 'seccion'))
        partes.append((interpretacion.get('resumen_ejecutivo', '') + "\n\n", 'normal'))

        # Parametros alterados
        params = interpretacion.get('parametros_alterados', [])
        if params:
            partes.append(("PARÁMETROS ALTERADOS\n", 'seccion'))
            for p in params:
                alerta = str(p.get('alerta', '')).lower()
                tag = 'critico' if 'critico' in alerta else 'alerta'
                estado_txt = p.get('estado', '')
                linea = (
                    f"  • {p['nombre']}: {p['valor']} {p.get('unidad', '')} "
                    f"(Ref: {p.get('referencia', 'N/D')}) — {estado_txt.upper()}\n"
                )
                partes.append((linea, tag))
            partes.append(("\n", 'normal'))

        # Interpretacion de reglas locales
        obs_reglas = interpretacion.get('interpretacion_reglas', [])
        if obs_reglas:
            partes.append(("ANÁLISIS CLINICO (MOTOR LOCAL)\n", 'seccion'))
            for obs in obs_reglas:
                partes.append((f"  • {obs}\n", 'normal'))
            partes.append(("\n", 'normal'))

        # Interpretacion IA (si disponible)
        ia_texto = interpretacion.get('interpretacion_ia', '')
        proveedor = interpretacion.get('proveedor_usado', 'reglas')
        if ia_texto:
            label_prov = 'OLLAMA (LLM LOCAL)' if proveedor == 'ollama' else 'CLAUDE IA (ONLINE)'
            partes.append((f"INTERPRETACION IA — {label_prov}\n", 'seccion_ia'))
            partes.append((ia_texto + "\n\n", 'ia'))
        elif proveedor == 'reglas' and self.config.get('proveedor_ia', 'reglas') != 'reglas':
            partes.append(("IA AVANZADA\n", 'seccion'))
            partes.append(("Motor de IA no disponible. Se muestra análisis por reglas clínicas locales.\n\n", 'normal'))

        # Disclaimer
        partes.append(("─" * 60 + "\n", 'normal'))
        partes.append(("⚠️  " + DISCLAIMER + "\n", 'disclaimer'))

        return partes

    def formatear_reporte_plano(self, interpretacion, prueba_nombre='', fecha=None):
        """
        Retorna el reporte como texto plano (para exportar a PDF sin tags).
        """
        partes = self.formatear_reporte_texto(interpretacion, prueba_nombre, fecha)
        return ''.join(texto for texto, _ in partes)


# ============================================================
# GESTION DE CONFIGURACION
# ============================================================

class ConfigIA:
    """Maneja la lectura/escritura de la configuracion de IA en config_ia.json.
    Las API keys se almacenan protegidas con DPAPI/ofuscacion."""

    DEFAULTS = {
        'proveedor_ia': 'reglas',
        'claude_api_key': '',
        'claude_modelo': 'claude-haiku-4-5-20251001',
        'ollama_url': 'http://localhost:11434',
        'ollama_modelo': 'llama3.2',
        'ia_activa': True,
    }

    def __init__(self, ruta_archivo=None):
        from pathlib import Path
        if ruta_archivo:
            self.ruta = Path(ruta_archivo)
        else:
            # Buscar en el directorio del modulo o en el directorio padre
            modulo_dir = Path(__file__).parent
            self.ruta = modulo_dir.parent / 'config_ia.json'
        # Cargar protector de credenciales
        self._protector = None
        try:
            from modulos.seguridad_db import ProtectorCredenciales
            self._protector = ProtectorCredenciales()
        except ImportError:
            pass

    def leer(self):
        """Lee la configuracion. Retorna defaults si el archivo no existe.
        Descifra la API key si esta protegida."""
        try:
            if self.ruta.exists():
                with open(self.ruta, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Completar con defaults si faltan claves
                config = {**self.DEFAULTS, **data}
                # Descifrar API key si esta protegida
                api_key = config.get('claude_api_key', '')
                if api_key and self._protector and not api_key.startswith('sk-'):
                    config['claude_api_key'] = self._protector.descifrar(api_key)
                return config
        except Exception as e:
            print(f"[ConfigIA] Error al leer configuracion: {e}")
        return dict(self.DEFAULTS)

    def guardar(self, config):
        """Guarda la configuracion en disco. Protege la API key."""
        try:
            datos = {k: v for k, v in config.items() if k in self.DEFAULTS}
            # Cifrar la API key antes de guardar
            api_key = datos.get('claude_api_key', '')
            if api_key and self._protector:
                datos['claude_api_key'] = self._protector.cifrar(api_key)
            with open(self.ruta, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigIA] Error al guardar configuracion: {e}")
            return False


# ============================================================
# FUNCION DE CONVENIENCIA
# ============================================================

def crear_interpretador(ruta_config=None):
    """
    Crea un InterpretadorClinico cargando la configuracion desde disco.
    """
    cfg_mgr = ConfigIA(ruta_config)
    config = cfg_mgr.leer()
    return InterpretadorClinico(config), cfg_mgr

# -*- coding: utf-8 -*-
"""
formato_pdf.py - Motor de layout proporcional y código QR para reportes PDF
============================================================================
Proporciona escalado automático de dimensiones para los formatos:
  - Carta  (Letter)  : 8.5" × 11"    (612 × 792 pt)
  - A4               : 8.27" × 11.69" (595.28 × 841.89 pt)
  - Oficio (Legal)   : 8.5" × 14"    (612 × 1008 pt)
  - Media Carta (½L) : 5.5" × 8.5"   (396 × 612 pt)

Autor: ANgesLAB
Fecha: 2026-02
"""

import hashlib
import io
import os
from datetime import datetime

try:
    from reportlab.lib.pagesizes import letter, legal, A4
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import Image as RLImage
    REPORTLAB_OK = True
except ImportError:
    REPORTLAB_OK = False

# Tamaño de Media Carta (Half Letter): 5.5" × 8.5"
MEDIA_CARTA = (396, 612)

# ── Constantes de página ─────────────────────────────────────────────────
TAMANOS_PAGINA = {
    'Carta':       letter,       # (612, 792)
    'A4':          A4,           # (595.28, 841.89)
    'Oficio':      legal,        # (612, 1008)
    'Media Carta': MEDIA_CARTA,  # (396, 612)
}

# Referencia base: Carta (Letter) 612 pt ancho
_REF_WIDTH = 612.0


# ══════════════════════════════════════════════════════════════════════════
#  LayoutCalculator  -  Dimensiones proporcionales para cualquier formato
# ══════════════════════════════════════════════════════════════════════════
class LayoutCalculator:
    """
    Calcula todas las dimensiones del PDF proporcionalmente al tamaño
    de página seleccionado, usando Carta como referencia base.

    Uso:
        layout = LayoutCalculator('A4')
        doc = BaseDocTemplate(filename, pagesize=layout.page_size)
        # Luego usar layout.margin_left, layout.col_widths, etc.
    """

    def __init__(self, tamano_papel='Carta', tiene_bioanalistas=False):
        """
        Args:
            tamano_papel: 'Carta', 'A4', 'Oficio' o 'Media Carta'
            tiene_bioanalistas: True si hay firmas de bioanalista (footer grande)
        """
        self.nombre = tamano_papel
        self.page_size = TAMANOS_PAGINA.get(tamano_papel, letter)
        self.page_width = self.page_size[0]
        self.page_height = self.page_size[1]
        self.es_media_carta = (tamano_papel == 'Media Carta')
        self._tiene_bio = tiene_bioanalistas

        # Factor de escala horizontal relativo a Carta
        self._sx = self.page_width / _REF_WIDTH

        self._calcular_dimensiones()

    def _calcular_dimensiones(self):
        """Calcula todas las dimensiones proporcionalmente."""

        # ── Márgenes ──────────────────────────────────────────────────
        if self.es_media_carta:
            self.margin_left   = 0.25 * inch
            self.margin_right  = 0.25 * inch
            self.margin_top    = 0.2  * inch
            self.margin_bottom = 0.9 * inch if self._tiene_bio else 0.3 * inch
        else:
            self.margin_left   = 0.35 * inch
            self.margin_right  = 0.35 * inch
            self.margin_top    = 0.25 * inch
            self.margin_bottom = 1.1 * inch if self._tiene_bio else 0.35 * inch

        # Ancho de contenido disponible
        self.content_width = self.page_width - self.margin_left - self.margin_right

        # ── Escalas de fuente ─────────────────────────────────────────
        if self.es_media_carta:
            self._font_scale = 0.82
        else:
            self._font_scale = 1.0

        # Fuentes del header (estilo moderno Clínica Santiago)
        self.font_lab_nombre  = self._fs(11)  # Nombre laboratorio (bold, prominente)
        self.font_lab_detalle = self._fs(7.5) # Dirección, teléfono, etc.
        self.font_lab_pie     = self._fs(6.5) # Texto sutil pie de header
        self.font_orden_label = self._fs(8)   # "ORDEN NO." label
        self.font_orden_valor = self._fs(10)  # Número de orden (bold)
        self.font_pac_nombre  = self._fs(9)   # Nombre paciente (bold)
        self.font_pac_label   = self._fs(7.5) # Labels "Cédula:", "Edad:"
        self.font_pac_valor   = self._fs(7.5) # Valores paciente
        self.font_informe_titulo = self._fs(10) # "Informe de resultados"

        # Fuentes del cuerpo
        self.font_titulo_prueba = self._fs(9)   # Título de prueba
        self.font_header_tabla  = self._fs(9)   # Header de tabla resultados
        self.font_datos_tabla   = self._fs(8)   # Datos de tabla
        self.font_seccion       = self._fs(9)   # Nombre de sección

        # Fuentes del footer
        self.font_bio_nombre  = self._fs(7)   # Nombre bioanalista
        self.font_bio_detalle = self._fs(6.5) # CI, Registro
        self.font_bio_area    = self._fs(6)   # Área
        self.font_generado    = self._fs(7)   # "Documento generado..."

        # ── Header (estilo moderno: logo + info lab + orden + nombre + barra + datos) ──
        if self.es_media_carta:
            self.header_height = 1.85 * inch
            self.logo_width    = 1.50 * inch
            self.logo_height   = 1.50 * inch
            self.info_section_height = 0.65 * inch  # Altura de referencia para layout
        else:
            self.header_height = 2.10 * inch
            self.logo_width    = 2.20 * inch
            self.logo_height   = 2.20 * inch
            self.info_section_height = 0.85 * inch  # Altura de referencia para layout

        # Posición info laboratorio (a la derecha del logo)
        self.info_lab_x_offset = self.logo_width + 0.15 * inch
        self.info_line_height  = self._fs(10)  # interlineado info lab (más compacto)

        # Máximo caracteres de dirección por línea (proporcional)
        self.max_chars_direccion = int(70 * self._sx) if not self.es_media_carta else 40

        # ── Datos del Paciente (layout 2 columnas bajo barra separadora) ──
        if self.es_media_carta:
            self.pac_row_spacing = 0.10 * inch  # interlineado muy compacto
            self.pac_col2_x = self.content_width * 0.52  # columna derecha
            self.pac_val_offset_col1 = 1.15 * inch
            self.pac_val_offset_col2 = 1.10 * inch
        else:
            self.pac_row_spacing = 0.11 * inch  # interlineado compacto
            self.pac_col2_x = self.content_width * 0.52
            self.pac_val_offset_col1 = 1.35 * inch
            self.pac_val_offset_col2 = 1.25 * inch

        # Truncamiento de texto
        self.max_nombre_chars = 50 if not self.es_media_carta else 28
        self.max_medico_chars = 35 if not self.es_media_carta else 20

        # ── QR Code ───────────────────────────────────────────────────
        if self.es_media_carta:
            self.qr_size = 0.65 * inch
        else:
            self.qr_size = 0.85 * inch

        # ── Columnas de Tabla de Resultados (genérica) ────────────────
        # Proporciones: Descripción=0.385, Resultado=0.185, Unidad=0.123, Ref=0.308
        self.col_widths = [
            self.content_width * 0.385,
            self.content_width * 0.185,
            self.content_width * 0.123,
            self.content_width * 0.308,
        ]

        # ── Columnas de Microbiología ─────────────────────────────────
        # Secciones normales: Nombre=0.385, Valor=0.308, Unidad=0.123, Ref=0.185
        self.micro_col_widths = [
            self.content_width * 0.385,
            self.content_width * 0.308,
            self.content_width * 0.123,
            self.content_width * 0.185,
        ]
        # Antibiograma: Antibiótico=0.462, Resultado=0.231, Interpretación=0.308
        self.atb_col_widths = [
            self.content_width * 0.462,
            self.content_width * 0.231,
            self.content_width * 0.308,
        ]

        # ── Columnas de GTT ───────────────────────────────────────────
        self.gtt_col_widths = [
            self.content_width * 0.315,
            self.content_width * 0.180,
            self.content_width * 0.165,
            self.content_width * 0.340,
        ]
        # Gráfica GTT
        self.gtt_grafica_width  = self.content_width - 0.3 * inch
        self.gtt_grafica_height = 3.3 * inch if not self.es_media_carta else 2.2 * inch

        # ── Firmas / Footer ───────────────────────────────────────────
        if self.es_media_carta:
            self.firma_img_width  = 0.9 * inch
            self.firma_img_height = 0.3 * inch
            self.firma_linea_width = 1.1 * inch
            self.max_firmas = 2  # Máximo 2 firmas en media carta
        else:
            self.firma_img_width  = 1.2 * inch
            self.firma_img_height = 0.4 * inch
            self.firma_linea_width = 1.5 * inch
            self.max_firmas = 3  # Máximo 3 firmas en formatos grandes

        # ── Espaciadores ──────────────────────────────────────────────
        self.space_after_prueba = 0.08 * inch if not self.es_media_carta else 0.05 * inch
        self.space_before_titulo = 2 if not self.es_media_carta else 2
        self.space_after_titulo = 1 if not self.es_media_carta else 1

    def _fs(self, base_size):
        """Aplica factor de escala a un tamaño de fuente base."""
        return round(base_size * self._font_scale, 1)

    def get_content_frame_height(self):
        """Retorna la altura disponible para contenido (flowables)."""
        return self.page_height - self.margin_top - self.header_height - self.margin_bottom

    def __repr__(self):
        return (f"LayoutCalculator('{self.nombre}', {self.page_width:.0f}×"
                f"{self.page_height:.0f}pt, content={self.content_width:.0f}pt)")


# ══════════════════════════════════════════════════════════════════════════
#  QRGenerator  -  Código QR de verificación para reportes
# ══════════════════════════════════════════════════════════════════════════
try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False

try:
    from PIL import Image as PILImage
    PIL_DISPONIBLE = True
except ImportError:
    PIL_DISPONIBLE = False


class QRGenerator:
    """
    Genera códigos QR de verificación para reportes de laboratorio.

    El QR contiene texto estructurado legible al escanearlo:
        Laboratorio / Orden / Paciente / Cédula / Fecha / Hash

    El hash SHA-256 (12 primeros chars) permite verificar autenticidad.
    """

    @staticmethod
    def disponible():
        """Retorna True si las dependencias QR están instaladas."""
        return QR_DISPONIBLE and PIL_DISPONIBLE

    @staticmethod
    def generar_hash(numero_solicitud, fecha_solicitud, nombre_paciente):
        """Genera hash SHA-256 truncado de 12 caracteres."""
        contenido = f"{numero_solicitud}|{fecha_solicitud}|{nombre_paciente}"
        return hashlib.sha256(contenido.encode('utf-8')).hexdigest()[:12].upper()

    @staticmethod
    def generar_contenido_qr(numero_solicitud, fecha_solicitud, nombre_paciente,
                              cedula='', nombre_lab='', estado=''):
        """
        Genera el contenido textual del QR con información legible.

        Al escanear con cualquier teléfono mostrará los datos del reporte
        de forma clara y verificable, incluyendo si los resultados están listos.
        """
        hash_verificacion = QRGenerator.generar_hash(
            numero_solicitud, fecha_solicitud, nombre_paciente
        )

        # Determinar estado legible para el QR
        estado_upper = (estado or '').strip().lower()
        if estado_upper in ('completada', 'entregada'):
            estado_qr = 'RESULTADOS LISTOS'
        else:
            estado_qr = 'EN PROCESO'

        lineas = []
        if nombre_lab:
            lineas.append(nombre_lab)
        lineas.append(f"Orden: {numero_solicitud}")
        lineas.append(f"Paciente: {nombre_paciente}")
        if cedula:
            lineas.append(f"C.I.: {cedula}")
        lineas.append(f"Fecha: {fecha_solicitud}")
        lineas.append(f"Estado: {estado_qr}")
        lineas.append(f"Verificacion: {hash_verificacion}")

        return '\n'.join(lineas)

    @staticmethod
    def generar_qr_image(numero_solicitud, fecha_solicitud, nombre_paciente,
                          size_px=150, cedula='', nombre_lab='', estado=''):
        """
        Genera imagen QR y retorna un ImageReader listo para ReportLab.

        Args:
            numero_solicitud: Número de la solicitud
            fecha_solicitud: Fecha en formato dd/mm/yyyy
            nombre_paciente: Nombre completo del paciente
            size_px: Tamaño en píxeles de la imagen
            cedula: Cédula del paciente
            nombre_lab: Nombre del laboratorio
            estado: Estado de la solicitud

        Returns:
            ImageReader con la imagen PNG, o None si no está disponible
        """
        if not QRGenerator.disponible():
            return None

        try:
            contenido_qr = QRGenerator.generar_contenido_qr(
                numero_solicitud, fecha_solicitud, nombre_paciente,
                cedula, nombre_lab, estado
            )

            qr = qrcode.QRCode(
                version=None,
                error_correction=ERROR_CORRECT_M,
                box_size=6,
                border=2,
            )
            qr.add_data(contenido_qr)
            qr.make(fit=True)

            img = qr.make_image(fill_color="black", back_color="white")

            # Redimensionar al tamaño deseado
            img = img.resize((size_px, size_px), PILImage.NEAREST)

            buf = io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            # Envolver en ImageReader para compatibilidad con canvas.drawImage
            if REPORTLAB_OK:
                return ImageReader(buf)
            return buf

        except Exception:
            return None

    @staticmethod
    def generar_rl_image(numero_solicitud, fecha_solicitud, nombre_paciente, width, height,
                          cedula='', nombre_lab='', estado=''):
        """
        Genera un objeto ReportLab Image listo para insertar en flowables.

        Args:
            width: Ancho en puntos ReportLab
            height: Alto en puntos ReportLab

        Returns:
            reportlab.platypus.Image o None
        """
        if not REPORTLAB_OK:
            return None

        buf = QRGenerator.generar_qr_image(
            numero_solicitud, fecha_solicitud, nombre_paciente,
            cedula=cedula, nombre_lab=nombre_lab, estado=estado
        )
        if buf is None:
            return None

        try:
            return RLImage(buf, width=width, height=height)
        except Exception:
            return None


def dibujar_qr_en_header(canvas, layout, numero_solicitud, fecha_solicitud, nombre_paciente,
                          cedula='', nombre_lab='', estado=''):
    """
    Dibuja el QR de verificación en la esquina superior derecha del header.

    Al escanear el QR se muestra:
      - Nombre del laboratorio
      - Número de orden
      - Nombre del paciente
      - Cédula
      - Fecha
      - Estado (RESULTADOS LISTOS / EN PROCESO)
      - Código de verificación (hash)
    """
    if not QRGenerator.disponible():
        return

    buf = QRGenerator.generar_qr_image(
        numero_solicitud, fecha_solicitud, nombre_paciente,
        cedula=cedula, nombre_lab=nombre_lab, estado=estado
    )
    if buf is None:
        return

    try:
        qr_x = layout.page_width - layout.margin_right - layout.qr_size
        qr_y = layout.page_height - layout.margin_top - layout.qr_size - 0.1 * inch

        canvas.drawImage(
            buf, qr_x, qr_y,
            width=layout.qr_size, height=layout.qr_size,
            preserveAspectRatio=True, mask='auto'
        )

        # Texto pequeño debajo del QR
        canvas.setFont('Helvetica', layout._fs(5))
        canvas.drawCentredString(
            qr_x + layout.qr_size / 2,
            qr_y - 0.08 * inch,
            "Verificación QR"
        )
    except Exception:
        pass  # QR es opcional, no detener el PDF si falla


# ══════════════════════════════════════════════════════════════════════════
#  Función de utilidad
# ══════════════════════════════════════════════════════════════════════════
def obtener_layout(tamano_papel='Carta', tiene_bioanalistas=False):
    """Función de conveniencia para crear un LayoutCalculator."""
    return LayoutCalculator(tamano_papel, tiene_bioanalistas)

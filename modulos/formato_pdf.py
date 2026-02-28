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
            self.margin_left   = 0.35 * inch
            self.margin_right  = 0.35 * inch
            self.margin_top    = 0.3  * inch
            self.margin_bottom = 1.1 * inch if self._tiene_bio else 0.4 * inch
        else:
            self.margin_left   = 0.5 * inch
            self.margin_right  = 0.5 * inch
            self.margin_top    = 0.4 * inch
            self.margin_bottom = 1.3 * inch if self._tiene_bio else 0.5 * inch

        # Ancho de contenido disponible
        self.content_width = self.page_width - self.margin_left - self.margin_right

        # ── Escalas de fuente ─────────────────────────────────────────
        if self.es_media_carta:
            self._font_scale = 0.82
        else:
            self._font_scale = 1.0

        # Fuentes del header
        self.font_lab_nombre  = self._fs(10)  # Nombre laboratorio
        self.font_lab_detalle = self._fs(8)   # Dirección, teléfono, etc.
        self.font_lab_pie     = self._fs(7)   # "Impreso por ANgesLAB..."
        self.font_pac_label   = self._fs(8)   # Labels "NOMBRE:", "CÉDULA:"
        self.font_pac_valor   = self._fs(8)   # Valores paciente

        # Fuentes del cuerpo
        self.font_titulo_prueba = self._fs(11)  # Título de prueba
        self.font_header_tabla  = self._fs(9)   # Header de tabla resultados
        self.font_datos_tabla   = self._fs(8)   # Datos de tabla
        self.font_seccion       = self._fs(9)   # Nombre de sección

        # Fuentes del footer
        self.font_bio_nombre  = self._fs(7)   # Nombre bioanalista
        self.font_bio_detalle = self._fs(6.5) # CI, Registro
        self.font_bio_area    = self._fs(6)   # Área
        self.font_generado    = self._fs(7)   # "Documento generado..."

        # ── Header ────────────────────────────────────────────────────
        if self.es_media_carta:
            self.header_height = 1.65 * inch
            self.logo_width    = 0.85 * inch
            self.logo_height   = 0.7  * inch
        else:
            self.header_height = 2.0 * inch
            self.logo_width    = 1.2 * inch
            self.logo_height   = 1.0 * inch

        # Posición info laboratorio (a la derecha del logo)
        self.info_lab_x_offset = self.logo_width + 0.2 * inch  # desde margin_left
        self.info_line_height  = self._fs(11)  # interlineado info lab

        # Máximo caracteres de dirección por línea (proporcional)
        self.max_chars_direccion = int(70 * self._sx) if not self.es_media_carta else 40

        # ── Cuadro de Datos del Paciente ──────────────────────────────
        if self.es_media_carta:
            self.box_height = 0.85 * inch   # Más alto para 2 columnas
            self.box_y_offset = self.logo_height + 0.25 * inch
            self.box_row_spacing = 0.18 * inch
            self.box_cols = 2  # 2 columnas en media carta
            # Posiciones de columnas (relativas a margin_left)
            self.box_col1_x = 0.08 * inch
            self.box_col2_x = self.content_width * 0.50
            self.box_col3_x = self.box_col2_x  # No se usa en 2 cols
            self.box_val_offset = 0.5 * inch
        else:
            self.box_height = 0.7 * inch
            self.box_y_offset = self.logo_height + 0.35 * inch
            self.box_row_spacing = 0.22 * inch
            self.box_cols = 3  # 3 columnas en formato normal
            # Posiciones de columnas (proporcionales al ancho)
            self.box_col1_x = 0.1 * inch
            self.box_col2_x = self.content_width * 0.38
            self.box_col3_x = self.content_width * 0.70
            self.box_val_offset = 0.55 * inch

        # Truncamiento de texto en cuadro paciente
        self.max_nombre_chars = 35 if not self.es_media_carta else 22
        self.max_medico_chars = 25 if not self.es_media_carta else 18

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
        self.space_after_prueba = 0.15 * inch if not self.es_media_carta else 0.10 * inch
        self.space_before_titulo = 12 if not self.es_media_carta else 8
        self.space_after_titulo = 8 if not self.es_media_carta else 5

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

    El QR contiene:
        ANGESLAB|NumeroSolicitud|FechaSolicitud|Hash12

    El hash SHA-256 (12 primeros chars) se calcula desde:
        "{NumeroSolicitud}|{FechaSolicitud}|{NombrePaciente}"

    Esto permite verificar la autenticidad del reporte impreso.
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
    def generar_qr_image(numero_solicitud, fecha_solicitud, nombre_paciente, size_px=150):
        """
        Genera imagen QR y retorna un BytesIO listo para ReportLab.

        Args:
            numero_solicitud: Número de la solicitud
            fecha_solicitud: Fecha en formato dd/mm/yyyy
            nombre_paciente: Nombre completo del paciente
            size_px: Tamaño en píxeles de la imagen

        Returns:
            io.BytesIO con la imagen PNG, o None si no está disponible
        """
        if not QRGenerator.disponible():
            return None

        try:
            hash_verificacion = QRGenerator.generar_hash(
                numero_solicitud, fecha_solicitud, nombre_paciente
            )

            contenido_qr = f"ANGESLAB|{numero_solicitud}|{fecha_solicitud}|{hash_verificacion}"

            qr = qrcode.QRCode(
                version=1,
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
            return buf

        except Exception:
            return None

    @staticmethod
    def generar_rl_image(numero_solicitud, fecha_solicitud, nombre_paciente, width, height):
        """
        Genera un objeto ReportLab Image listo para insertar en el canvas.

        Args:
            width: Ancho en puntos ReportLab
            height: Alto en puntos ReportLab

        Returns:
            reportlab.platypus.Image o None
        """
        if not REPORTLAB_OK:
            return None

        buf = QRGenerator.generar_qr_image(
            numero_solicitud, fecha_solicitud, nombre_paciente
        )
        if buf is None:
            return None

        try:
            return RLImage(buf, width=width, height=height)
        except Exception:
            return None


def dibujar_qr_en_header(canvas, layout, numero_solicitud, fecha_solicitud, nombre_paciente):
    """
    Dibuja el QR de verificación en la esquina superior derecha del header.

    Args:
        canvas: ReportLab canvas object
        layout: LayoutCalculator instance
        numero_solicitud: Número de solicitud
        fecha_solicitud: Fecha formateada dd/mm/yyyy
        nombre_paciente: Nombre completo
    """
    if not QRGenerator.disponible():
        return

    buf = QRGenerator.generar_qr_image(
        numero_solicitud, fecha_solicitud, nombre_paciente
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

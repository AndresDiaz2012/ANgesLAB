# -*- coding: utf-8 -*-
"""
================================================================================
FACTURA FISCAL EN PDF (SENIAT) - ANgesLAB
================================================================================
Genera el PDF de facturas, notas de credito y notas de debito con los datos
que exige la normativa venezolana.

Requisitos cubiertos (Providencia SNAT/2011/0071, art. 30, y concordantes):

  a) Denominacion del documento: FACTURA / NOTA DE CREDITO / NOTA DE DEBITO
  b) Numeracion consecutiva y unica
  c) Numero de Control ("00-NNNNNNNN")
  d) Datos del emisor: nombre o razon social, domicilio fiscal y RIF
  e) Fecha (y hora) de emision
  f) Datos del adquiriente: nombre o razon social y RIF/C.I.
  g) Descripcion de los servicios, cantidad, precio unitario y valor total
  h) Especificacion de los renglones exentos o exonerados
  i) Base imponible, alicuota aplicable y monto del IVA por separado
  j) Valor total de la operacion incluido el impuesto
  k) Condicion de la operacion (contado / credito)
  l) Datos del proveedor autorizado o imprenta autorizada y su providencia
  m) En NC/ND: numero y fecha de la factura que se afecta

Ademas:
  - IGTF discriminado (Providencia SNAT/2022/000013)
  - Tipo de contribuyente (Ordinario / Especial)
  - Equivalencia en Bs. y tasa de cambio del dia cuando la factura es en
    divisas (art. 25 Ley de IVA / Providencia SNAT/2024/000102)
  - Monto total expresado en letras

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import os
import logging
import tempfile
from datetime import datetime
from decimal import Decimal

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.factura_pdf')
except Exception:
    _log = logging.getLogger('angeslab.factura_pdf')
    _log.addHandler(logging.NullHandler())

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, HRFlowable, KeepTogether)
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False

try:
    from modulos.facturacion_fiscal import monto_en_letras
except Exception:
    def monto_en_letras(monto, moneda='VES'):
        return ''


# Denominación legal según el tipo de documento
DENOMINACION = {
    'Factura': 'FACTURA',
    'NC': 'NOTA DE CRÉDITO',
    'ND': 'NOTA DE DÉBITO',
}

SIMBOLO_MONEDA = {'USD': '$', 'VES': 'Bs.', 'Bs': 'Bs.', 'COP': 'COL$'}

_COLOR_TEXTO = colors.HexColor('#1a1a1a') if REPORTLAB_DISPONIBLE else None
_COLOR_LINEA = colors.HexColor('#555555') if REPORTLAB_DISPONIBLE else None
_COLOR_CABECERA = colors.HexColor('#e8e8e8') if REPORTLAB_DISPONIBLE else None


def _f(valor):
    """Convierte a float de forma segura (Access devuelve Decimal y None)."""
    if valor is None:
        return 0.0
    try:
        return float(valor)
    except (TypeError, ValueError):
        return 0.0


def _fecha(valor, con_hora=False):
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d/%m/%Y %I:%M %p' if con_hora else '%d/%m/%Y')
    return str(valor or '')[:10]


class GeneradorFacturaPDF:
    """Genera el PDF fiscal de una factura, nota de crédito o nota de débito."""

    ANCHO_UTIL = letter[0] - 32 * mm if REPORTLAB_DISPONIBLE else 0

    def __init__(self, db):
        self.db = db
        self._config = None

    # ------------------------------------------------------------------ datos
    def _cargar_config(self):
        if self._config is None:
            try:
                self._config = self.db.query_one(
                    "SELECT * FROM ConfiguracionLaboratorio") or {}
            except Exception:
                self._config = {}
        return self._config

    def _obtener_factura(self, factura_id):
        """Factura + datos del adquiriente."""
        fac = self.db.query_one(
            f"SELECT f.*, p.Nombres, p.Apellidos, p.NumeroDocumento, "
            f"p.TipoDocumento AS TipoDocPaciente, p.DireccionCompleta, "
            f"p.Telefono1, p.Email "
            f"FROM [Facturas] AS f "
            f"LEFT JOIN [Pacientes] AS p ON f.PacienteID = p.PacienteID "
            f"WHERE f.FacturaID={int(factura_id)}")
        if not fac:
            raise ValueError(f"Factura no encontrada: {factura_id}")
        return fac

    def _obtener_detalles(self, factura_id):
        return self.db.query(
            f"SELECT d.*, pr.CodigoPrueba "
            f"FROM [DetalleFacturas] AS d "
            f"LEFT JOIN [Pruebas] AS pr ON d.PruebaID = pr.PruebaID "
            f"WHERE d.FacturaID={int(factura_id)} "
            f"ORDER BY d.DetalleFacturaID") or []

    def _factura_afectada(self, factura_afectada_id):
        """Documento original al que se refiere una NC o ND."""
        if not factura_afectada_id:
            return None
        try:
            return self.db.query_one(
                f"SELECT NumeroFactura, NumeroControl, FechaEmision "
                f"FROM [Facturas] WHERE FacturaID={int(factura_afectada_id)}")
        except Exception:
            return None

    # ------------------------------------------------------------- estilos
    @staticmethod
    def _estilo(nombre, **kw):
        base = dict(fontName='Helvetica', fontSize=8, leading=10,
                    textColor=_COLOR_TEXTO)
        base.update(kw)
        return ParagraphStyle(nombre, **base)

    # ------------------------------------------------------------- secciones
    def _bloque_emisor(self, cfg, tipo_doc, fac):
        """Datos del emisor y denominación del documento (requisitos a-e)."""
        s_lab = self._estilo('lab', fontSize=13, leading=16,
                             fontName='Helvetica-Bold', spaceAfter=2)
        s_dat = self._estilo('dat', fontSize=7.5, leading=9.5)
        s_den = self._estilo('den', fontSize=14, leading=17,
                             fontName='Helvetica-Bold', alignment=TA_CENTER)
        s_num = self._estilo('num', fontSize=9, fontName='Helvetica-Bold',
                             alignment=TA_CENTER, leading=12)

        izq = [Paragraph(str(cfg.get('NombreLaboratorio') or 'LABORATORIO').upper(), s_lab)]
        razon = cfg.get('RazonSocial')
        if razon and razon != cfg.get('NombreLaboratorio'):
            izq.append(Paragraph(str(razon), s_dat))
        izq.append(Paragraph(f"<b>R.I.F.:</b> {cfg.get('RIF') or '—'}", s_dat))
        if cfg.get('Direccion'):
            izq.append(Paragraph(f"<b>Domicilio fiscal:</b> {cfg.get('Direccion')}", s_dat))
        contacto = ' · '.join(str(x) for x in (cfg.get('Telefono1'),
                                               cfg.get('Email')) if x)
        if contacto:
            izq.append(Paragraph(contacto, s_dat))
        tipo_contrib = cfg.get('TipoContribuyente') or 'Ordinario'
        izq.append(Paragraph(f"<b>Contribuyente:</b> {tipo_contrib}", s_dat))

        # Recuadro con la denominación, el número y el número de control
        der = [
            Paragraph(DENOMINACION.get(tipo_doc, 'FACTURA'), s_den),
            Spacer(1, 3),
            Paragraph(f"N° {fac.get('NumeroFactura') or '—'}", s_num),
            Paragraph(f"N° de Control: {fac.get('NumeroControl') or '—'}", s_num),
            Spacer(1, 2),
            Paragraph(f"Fecha de emisión:<br/>{_fecha(fac.get('FechaEmision'), True)}",
                      self._estilo('fe', fontSize=7.5, alignment=TA_CENTER, leading=10)),
        ]

        tabla = Table([[izq, der]], colWidths=[self.ANCHO_UTIL * 0.62,
                                               self.ANCHO_UTIL * 0.38])
        tabla.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (1, 0), (1, 0), 1, _COLOR_TEXTO),
            ('LEFTPADDING', (0, 0), (0, 0), 0),
            ('LEFTPADDING', (1, 0), (1, 0), 6),
            ('RIGHTPADDING', (1, 0), (1, 0), 6),
            ('TOPPADDING', (1, 0), (1, 0), 6),
            ('BOTTOMPADDING', (1, 0), (1, 0), 6),
        ]))
        return tabla

    def _bloque_adquiriente(self, fac):
        """Datos del receptor (requisito f) y condición de la operación (k)."""
        s_lbl = self._estilo('albl', fontSize=7.5, fontName='Helvetica-Bold')
        s_val = self._estilo('aval', fontSize=8)

        nombre = f"{fac.get('Nombres') or ''} {fac.get('Apellidos') or ''}".strip() or '—'
        tipo_doc_pac = (fac.get('TipoDocPaciente') or 'V').strip()
        documento = fac.get('NumeroDocumento') or '—'
        if documento != '—' and not documento.upper().startswith(
                ('V', 'E', 'J', 'G', 'P')):
            documento = f"{tipo_doc_pac}-{documento}"

        filas = [
            [Paragraph('Nombre o razón social:', s_lbl), Paragraph(nombre, s_val),
             Paragraph('C.I. / R.I.F.:', s_lbl), Paragraph(documento, s_val)],
            [Paragraph('Domicilio:', s_lbl),
             Paragraph(str(fac.get('DireccionCompleta') or '—'), s_val),
             Paragraph('Teléfono:', s_lbl),
             Paragraph(str(fac.get('Telefono1') or '—'), s_val)],
            [Paragraph('Condición de pago:', s_lbl),
             Paragraph(str(fac.get('CondicionPago') or fac.get('TipoFactura')
                           or 'Contado'), s_val),
             Paragraph('Moneda:', s_lbl),
             Paragraph(str(fac.get('MonedaFactura') or 'USD'), s_val)],
        ]
        aw = self.ANCHO_UTIL
        tabla = Table(filas, colWidths=[aw * 0.16, aw * 0.44, aw * 0.14, aw * 0.26])
        tabla.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 0.6, _COLOR_LINEA),
            ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#bbbbbb')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ]))
        return tabla

    def _tabla_detalle(self, detalles, simbolo, exonerada):
        """Descripción, cantidad, precio y total (requisitos g-h)."""
        s_h = self._estilo('dh', fontSize=7.5, fontName='Helvetica-Bold',
                           alignment=TA_CENTER)
        s_l = self._estilo('dl', fontSize=7.5)
        s_c = self._estilo('dc', fontSize=7.5, alignment=TA_CENTER)
        s_r = self._estilo('dr', fontSize=7.5, alignment=TA_RIGHT)

        datos = [[Paragraph('Código', s_h), Paragraph('Descripción del servicio', s_h),
                  Paragraph('Cant.', s_h), Paragraph('Precio Unit.', s_h),
                  Paragraph('G/E', s_h), Paragraph('Total', s_h)]]

        for d in detalles:
            cantidad = int(_f(d.get('Cantidad')) or 1)
            precio = _f(d.get('PrecioUnitario'))
            total = _f(d.get('SubTotal')) or precio * cantidad
            # G = gravado, E = exento/exonerado (requisito h)
            gravamen = 'E' if (exonerada or d.get('Exonerada')) else 'G'
            datos.append([
                Paragraph(str(d.get('CodigoPrueba') or ''), s_c),
                Paragraph(str(d.get('Descripcion') or ''), s_l),
                Paragraph(str(cantidad), s_c),
                Paragraph(f"{simbolo} {precio:,.2f}", s_r),
                Paragraph(gravamen, s_c),
                Paragraph(f"{simbolo} {total:,.2f}", s_r),
            ])

        aw = self.ANCHO_UTIL
        tabla = Table(datos, colWidths=[aw * 0.10, aw * 0.46, aw * 0.07,
                                        aw * 0.16, aw * 0.05, aw * 0.16],
                      repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), _COLOR_CABECERA),
            ('BOX', (0, 0), (-1, -1), 0.6, _COLOR_LINEA),
            ('LINEBELOW', (0, 0), (-1, 0), 0.6, _COLOR_LINEA),
            ('INNERGRID', (0, 1), (-1, -1), 0.25, colors.HexColor('#cccccc')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return tabla

    def _bloque_totales(self, fac, simbolo):
        """Base imponible, alícuota, IVA, IGTF y total (requisitos i-j)."""
        s_l = self._estilo('tl', fontSize=8, alignment=TA_RIGHT)
        s_v = self._estilo('tv', fontSize=8, alignment=TA_RIGHT)
        s_lb = self._estilo('tlb', fontSize=9, fontName='Helvetica-Bold',
                            alignment=TA_RIGHT)
        s_vb = self._estilo('tvb', fontSize=9, fontName='Helvetica-Bold',
                            alignment=TA_RIGHT)

        subtotal = _f(fac.get('SubTotal'))
        descuento = _f(fac.get('MontoDescuento'))
        base = _f(fac.get('BaseImponible'))
        exento = _f(fac.get('MontoExento'))
        tasa_iva = _f(fac.get('TasaIVA'))
        iva = _f(fac.get('MontoIVA'))
        igtf = _f(fac.get('MontoIGTF'))
        tasa_igtf = _f(fac.get('TasaIGTF'))
        total = _f(fac.get('MontoTotal'))

        # Si no viene base imponible calculada, derivarla del subtotal
        if not base and not exento:
            base = max(subtotal - descuento, 0)

        filas = [(f"Subtotal:", subtotal, False)]
        if descuento:
            filas.append((f"Descuento ({_f(fac.get('PorcentajeDescuento')):.2f}%):",
                          -descuento, False))
        if exento:
            filas.append(("Monto exento / exonerado:", exento, False))
        filas.append(("Base imponible:", base, False))
        filas.append((f"IVA {tasa_iva:.2f}%:", iva, False))
        if igtf:
            # MontoTotal no incluye el IGTF: se suma aparte para el total a pagar
            filas.append((f"IGTF {tasa_igtf:.2f}%:", igtf, False))
            total += igtf
        filas.append(("TOTAL A PAGAR:", total, True))

        datos = []
        for etiqueta, valor, fuerte in filas:
            datos.append([
                Paragraph(etiqueta, s_lb if fuerte else s_l),
                Paragraph(f"{simbolo} {valor:,.2f}", s_vb if fuerte else s_v),
            ])

        aw = self.ANCHO_UTIL
        tabla = Table(datos, colWidths=[aw * 0.28, aw * 0.20])
        tabla.setStyle(TableStyle([
            ('LINEABOVE', (0, len(datos) - 1), (-1, len(datos) - 1), 0.8, _COLOR_TEXTO),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ]))

        # Alinear el bloque de totales a la derecha
        contenedor = Table([['', tabla]], colWidths=[aw * 0.52, aw * 0.48])
        contenedor.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ]))
        return contenedor, total

    def _bloque_conversion(self, fac, total, simbolo):
        """Equivalencia en bolívares y tasa del día (facturas en divisas)."""
        moneda = (fac.get('MonedaFactura') or 'USD').upper()
        tasa = _f(fac.get('TasaCambioDia'))
        total_bs = _f(fac.get('MontoTotalBs'))
        if moneda in ('VES', 'BS', 'BS.') or not tasa or tasa <= 1:
            return None
        if not total_bs:
            total_bs = total * tasa
        s = self._estilo('conv', fontSize=8, alignment=TA_RIGHT)
        return Paragraph(
            f"Tasa de cambio del día (BCV): {tasa:,.4f} Bs./{simbolo}  ·  "
            f"<b>Equivalente en bolívares: Bs. {total_bs:,.2f}</b>", s)

    def _bloque_afectada(self, afectada, tipo_doc):
        """Referencia al documento afectado por una NC/ND (requisito m)."""
        if not afectada:
            return None
        s = self._estilo('afe', fontSize=8)
        etiqueta = ('Nota de crédito' if tipo_doc == 'NC' else 'Nota de débito')
        return Paragraph(
            f"<b>{etiqueta} que afecta a la factura N° "
            f"{afectada.get('NumeroFactura') or '—'}</b> "
            f"(N° de control {afectada.get('NumeroControl') or '—'}) "
            f"emitida el {_fecha(afectada.get('FechaEmision'))}.", s)

    def _bloque_pie(self, cfg):
        """Datos del proveedor/imprenta autorizada (requisito l)."""
        s = self._estilo('pie', fontSize=6.5, leading=8.5,
                         textColor=colors.HexColor('#444444'))
        nombre = cfg.get('ImprentaNombre')
        rif = cfg.get('ImprentaRIF')
        prov = cfg.get('ImprentaProvidencia')
        fecha_prov = cfg.get('ImprentaFechaProvidencia')

        if nombre or rif or prov:
            partes = ['Documento elaborado por medios propios.']
            if nombre:
                partes.append(f"Proveedor autorizado: {nombre}")
            if rif:
                partes.append(f"R.I.F.: {rif}")
            if prov:
                texto = f"Providencia Administrativa N° {prov}"
                if fecha_prov:
                    texto += f" de fecha {_fecha(fecha_prov)}"
                partes.append(texto)
            texto_pie = ' · '.join(partes)
        else:
            # Sin datos configurados se advierte, en vez de omitir el requisito
            texto_pie = ('Documento elaborado por medios propios. '
                         'Faltan los datos del proveedor autorizado y su '
                         'Providencia Administrativa: complételos en '
                         'Configuración → Administrativa → Financiera.')
        return Paragraph(texto_pie, s)

    # ------------------------------------------------------------- generación
    def generar(self, factura_id, ruta_salida=None):
        """
        Genera el PDF fiscal de la factura.

        Returns:
            Ruta del PDF generado.
        """
        if not REPORTLAB_DISPONIBLE:
            raise RuntimeError("ReportLab no está instalado")

        fac = self._obtener_factura(factura_id)
        detalles = self._obtener_detalles(factura_id)
        cfg = self._cargar_config()

        tipo_doc = (fac.get('TipoDocumento') or 'Factura').strip() or 'Factura'
        moneda = (fac.get('MonedaFactura') or 'USD').upper()
        simbolo = SIMBOLO_MONEDA.get(moneda, cfg.get('SimboloMoneda') or '$')
        exonerada = bool(fac.get('EstaExonerada'))

        if not ruta_salida:
            nombre = str(fac.get('NumeroFactura') or f'FAC-{factura_id}')
            ruta_salida = os.path.join(
                tempfile.gettempdir(),
                f"{nombre.replace('/', '-')}.pdf")

        story = []
        story.append(self._bloque_emisor(cfg, tipo_doc, fac))
        story.append(Spacer(1, 8))

        afectada = self._bloque_afectada(
            self._factura_afectada(fac.get('FacturaAfectadaID')), tipo_doc)
        if afectada:
            story.append(afectada)
            story.append(Spacer(1, 6))

        story.append(self._bloque_adquiriente(fac))
        story.append(Spacer(1, 8))
        story.append(self._tabla_detalle(detalles, simbolo, exonerada))
        story.append(Spacer(1, 6))

        totales, total = self._bloque_totales(fac, simbolo)
        story.append(totales)

        conversion = self._bloque_conversion(fac, total, simbolo)
        if conversion:
            story.append(Spacer(1, 4))
            story.append(conversion)

        # Monto en letras
        letras = ''
        try:
            letras = monto_en_letras(total, moneda) or ''
        except Exception:
            pass
        if letras:
            story.append(Spacer(1, 6))
            story.append(Paragraph(
                f"<b>Son:</b> {letras}",
                self._estilo('letras', fontSize=8)))

        if exonerada and fac.get('NumeroExoneracion'):
            story.append(Spacer(1, 4))
            story.append(Paragraph(
                f"<b>Operación exonerada.</b> Providencia de exoneración N° "
                f"{fac.get('NumeroExoneracion')}"
                + (f" de fecha {_fecha(fac.get('FechaExoneracion'))}"
                   if fac.get('FechaExoneracion') else ''),
                self._estilo('exo', fontSize=8)))

        if fac.get('Observaciones'):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Observaciones:</b> {fac['Observaciones']}",
                                   self._estilo('obs', fontSize=7.5)))

        if fac.get('Anulada'):
            story.append(Spacer(1, 8))
            story.append(Paragraph(
                "*** DOCUMENTO ANULADO ***"
                + (f" Motivo: {fac.get('MotivoAnulacion')}"
                   if fac.get('MotivoAnulacion') else ''),
                self._estilo('anu', fontSize=11, fontName='Helvetica-Bold',
                             alignment=TA_CENTER,
                             textColor=colors.HexColor('#c62828'))))

        story.append(Spacer(1, 14))
        story.append(HRFlowable(width='100%', thickness=0.5, color=_COLOR_LINEA))
        story.append(Spacer(1, 4))
        story.append(self._bloque_pie(cfg))

        doc = SimpleDocTemplate(
            ruta_salida, pagesize=letter,
            leftMargin=16 * mm, rightMargin=16 * mm,
            topMargin=14 * mm, bottomMargin=14 * mm,
            title=f"{DENOMINACION.get(tipo_doc, 'FACTURA')} {fac.get('NumeroFactura', '')}",
            author=str(cfg.get('NombreLaboratorio') or 'ANgesLAB'))
        doc.build(story)

        _log.info("PDF fiscal generado: %s", ruta_salida)
        return ruta_salida


def crear_generador_factura_pdf(db):
    """Factory del generador de facturas en PDF."""
    return GeneradorFacturaPDF(db)


def generar_pdf_factura(db, factura_id, ruta_salida=None):
    """Atajo: genera el PDF de una factura y devuelve su ruta."""
    return GeneradorFacturaPDF(db).generar(factura_id, ruta_salida)

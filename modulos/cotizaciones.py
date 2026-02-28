# -*- coding: utf-8 -*-
"""
cotizaciones.py - Módulo de Cotizaciones / Presupuestos para ANgesLAB
======================================================================
Permite generar cotizaciones de servicios de laboratorio, imprimirlas
en PDF y convertirlas directamente en solicitudes.

Autor: ANgesLAB
Fecha: 2026-02
"""

from datetime import datetime, timedelta
import tempfile
import os

# ── ReportLab ────────────────────────────────────────────────────────────────
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    )
    _RL_OK = True
except ImportError:
    _RL_OK = False


# ─────────────────────────────────────────────────────────────────────────────
#  GestorCotizaciones
# ─────────────────────────────────────────────────────────────────────────────

class GestorCotizaciones:
    """CRUD de cotizaciones y conversión a solicitud."""

    def __init__(self, db, user):
        self.db   = db
        self.user = user
        self._asegurar_tablas()

    # ── Infraestructura DB ────────────────────────────────────────────────────

    def _asegurar_tablas(self):
        try:
            self.db.query("SELECT TOP 1 CotizacionID FROM Cotizaciones")
        except Exception:
            self.db.execute("""
                CREATE TABLE Cotizaciones (
                    CotizacionID   AUTOINCREMENT PRIMARY KEY,
                    NumeroCotizacion TEXT(20),
                    PacienteID     INTEGER,
                    MedicoID       INTEGER,
                    FechaCotizacion DATETIME,
                    FechaVencimiento DATETIME,
                    SubTotal       CURRENCY,
                    Descuento      CURRENCY DEFAULT 0,
                    Total          CURRENCY,
                    Estado         TEXT(20) DEFAULT 'Pendiente',
                    Observaciones  TEXT(255),
                    UsuarioID      INTEGER,
                    SolicitudID    INTEGER
                )
            """)
        try:
            self.db.query("SELECT TOP 1 DetalleCotizacionID FROM DetalleCotizaciones")
        except Exception:
            self.db.execute("""
                CREATE TABLE DetalleCotizaciones (
                    DetalleCotizacionID AUTOINCREMENT PRIMARY KEY,
                    CotizacionID   INTEGER,
                    PruebaID       INTEGER,
                    Descripcion    TEXT(255),
                    PrecioUnitario CURRENCY,
                    Cantidad       INTEGER DEFAULT 1,
                    SubTotal       CURRENCY
                )
            """)

    def _generar_numero(self):
        anio = datetime.now().year
        r = self.db.query_one(
            f"SELECT MAX(NumeroCotizacion) AS Ult FROM Cotizaciones "
            f"WHERE NumeroCotizacion LIKE 'COT-{anio}-%'"
        )
        try:
            n = int((r or {}).get('Ult', f'COT-{anio}-000000').split('-')[-1]) + 1
        except Exception:
            n = 1
        return f"COT-{anio}-{n:06d}"

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def crear_cotizacion(self, paciente_id, pruebas, medico_id=None,
                         descuento=0.0, observaciones='', dias_vigencia=15):
        """
        Crea una cotización.

        Args:
            paciente_id: ID del paciente
            pruebas: list[dict] con {id, nombre, precio}
            medico_id: ID del médico (opcional)
            descuento: descuento monetario
            observaciones: texto libre
            dias_vigencia: días hasta vencimiento

        Returns:
            dict con {exito, cotizacion_id, numero, mensaje}
        """
        try:
            numero = self._generar_numero()
            ahora  = datetime.now()
            vence  = ahora + timedelta(days=dias_vigencia)
            subtotal = sum(float(p.get('precio', 0)) for p in pruebas)
            total    = max(subtotal - float(descuento), 0)

            self.db.insert('Cotizaciones', {
                'NumeroCotizacion': numero,
                'PacienteID':      paciente_id,
                'MedicoID':        medico_id,
                'FechaCotizacion': ahora,
                'FechaVencimiento':vence,
                'SubTotal':        subtotal,
                'Descuento':       descuento,
                'Total':           total,
                'Estado':          'Pendiente',
                'Observaciones':   observaciones,
                'UsuarioID':       self.user.get('UsuarioID', 1),
            })
            cot = self.db.query_one(
                f"SELECT CotizacionID FROM Cotizaciones WHERE NumeroCotizacion='{numero}'"
            )
            if not cot:
                return {'exito': False, 'mensaje': 'No se pudo obtener ID de la cotización'}
            cot_id = cot['CotizacionID']

            for p in pruebas:
                precio = float(p.get('precio', 0))
                self.db.insert('DetalleCotizaciones', {
                    'CotizacionID':   cot_id,
                    'PruebaID':       p.get('id'),
                    'Descripcion':    p.get('nombre', ''),
                    'PrecioUnitario': precio,
                    'Cantidad':       1,
                    'SubTotal':       precio,
                })

            return {'exito': True, 'cotizacion_id': cot_id, 'numero': numero,
                    'total': total, 'mensaje': 'Cotización creada exitosamente'}
        except Exception as e:
            return {'exito': False, 'mensaje': str(e)}

    def listar_cotizaciones(self, filtro='', estado='Todos'):
        """Lista cotizaciones con filtro opcional."""
        where_parts = []
        if filtro:
            where_parts.append(
                f"(c.NumeroCotizacion LIKE '%{filtro}%' "
                f"OR p.Nombres LIKE '%{filtro}%' "
                f"OR p.Apellidos LIKE '%{filtro}%' "
                f"OR p.NumeroDocumento LIKE '%{filtro}%')"
            )
        if estado and estado != 'Todos':
            where_parts.append(f"c.Estado = '{estado}'")
        where = ('WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

        sql = f"""
            SELECT c.CotizacionID, c.NumeroCotizacion, c.FechaCotizacion,
                   c.FechaVencimiento, c.Total, c.Estado,
                   p.Nombres & ' ' & p.Apellidos AS Paciente,
                   p.NumeroDocumento,
                   c.SolicitudID
              FROM Cotizaciones c
              LEFT JOIN Pacientes p ON c.PacienteID = p.PacienteID
              {where}
             ORDER BY c.CotizacionID DESC
        """
        return self.db.query(sql) or []

    def obtener_detalle(self, cotizacion_id):
        """Retorna la cotización y sus ítems."""
        cot = self.db.query_one(
            f"""SELECT c.*,
                       p.Nombres & ' ' & p.Apellidos AS NombrePaciente,
                       p.NumeroDocumento, p.Telefono1,
                       m.Nombres & ' ' & m.Apellidos AS NombreMedico
                  FROM Cotizaciones c
                  LEFT JOIN Pacientes p ON c.PacienteID = p.PacienteID
                  LEFT JOIN Medicos   m ON c.MedicoID   = m.MedicoID
                 WHERE c.CotizacionID = {cotizacion_id}"""
        )
        items = self.db.query(
            f"SELECT * FROM DetalleCotizaciones WHERE CotizacionID={cotizacion_id}"
        ) or []
        return cot, items

    def anular_cotizacion(self, cotizacion_id):
        self.db.update('Cotizaciones', {'Estado': 'Anulada'}, f"CotizacionID={cotizacion_id}")

    def convertir_a_solicitud(self, cotizacion_id):
        """
        Convierte una cotización aceptada en solicitud.

        Returns:
            dict {exito, solicitud_id, numero_solicitud, mensaje}
        """
        try:
            cot, items = self.obtener_detalle(cotizacion_id)
            if not cot:
                return {'exito': False, 'mensaje': 'Cotización no encontrada'}
            if cot.get('Estado') == 'Convertida':
                return {'exito': False, 'mensaje': 'Ya fue convertida en solicitud'}
            if not items:
                return {'exito': False, 'mensaje': 'La cotización no tiene ítems'}

            # Generar número de solicitud
            anio = datetime.now().year
            r = self.db.query_one(
                f"SELECT MAX(NumeroSolicitud) AS Ult FROM Solicitudes "
                f"WHERE NumeroSolicitud LIKE '{anio}-%'"
            )
            try:
                n = int((r or {}).get('Ult', f'{anio}-000000').split('-')[-1]) + 1
            except Exception:
                n = 1
            num_sol = f"{anio}-{n:06d}"

            sol_data = {
                'NumeroSolicitud':    num_sol,
                'PacienteID':         cot['PacienteID'],
                'FechaSolicitud':     datetime.now(),
                'EstadoSolicitud':    'Pendiente',
                'MontoTotal':         float(cot.get('Total') or 0),
                'UsuarioRegistro':    self.user.get('UsuarioID', 1),
                'FechaRegistro':      datetime.now(),
            }
            if cot.get('MedicoID'):
                sol_data['MedicoID'] = cot['MedicoID']
            self.db.insert('Solicitudes', sol_data)
            sol = self.db.query_one(
                f"SELECT SolicitudID FROM Solicitudes WHERE NumeroSolicitud='{num_sol}'"
            )
            if not sol:
                return {'exito': False, 'mensaje': 'Error al crear solicitud'}
            sol_id = sol['SolicitudID']

            for it in items:
                self.db.insert('DetalleSolicitudes', {
                    'SolicitudID':    sol_id,
                    'PruebaID':       it.get('PruebaID'),
                    'PrecioUnitario': float(it.get('PrecioUnitario') or 0),
                    'Cantidad':       1,
                    'Subtotal':       float(it.get('SubTotal') or 0),
                    'Estado':         'Pendiente',
                })

            self.db.update('Cotizaciones',
                           {'Estado': 'Convertida', 'SolicitudID': sol_id},
                           f"CotizacionID={cotizacion_id}")

            return {'exito': True, 'solicitud_id': sol_id,
                    'numero_solicitud': num_sol, 'mensaje': 'Solicitud creada exitosamente'}
        except Exception as e:
            return {'exito': False, 'mensaje': str(e)}

    # ── PDF ──────────────────────────────────────────────────────────────────

    def generar_pdf(self, cotizacion_id, config_lab=None):
        """
        Genera el PDF de la cotización.

        Returns:
            ruta_pdf o None si hay error.
        """
        if not _RL_OK:
            return None

        cot, items = self.obtener_detalle(cotizacion_id)
        if not cot:
            return None

        cfg     = config_lab or {}
        simbolo = cfg.get('SimboloMoneda', '$')

        # Estilos
        def P(txt, **kw):
            s = ParagraphStyle('_', fontName='Helvetica', fontSize=9,
                               leading=12, **kw)
            return Paragraph(str(txt or ''), s)

        def PB(txt, **kw):
            kw.setdefault('fontName', 'Helvetica-Bold')
            return P(txt, **kw)

        story = []

        # Encabezado laboratorio
        if cfg.get('NombreLaboratorio'):
            story.append(PB(cfg['NombreLaboratorio'].upper(),
                            fontSize=14, alignment=TA_CENTER))
        if cfg.get('Direccion'):
            story.append(P(cfg['Direccion'], fontSize=8, alignment=TA_CENTER))
        tel_parts = []
        if cfg.get('Telefono1'):
            tel_parts.append(f"Tel: {cfg['Telefono1']}")
        if cfg.get('WhatsApp'):
            tel_parts.append(f"WhatsApp: {cfg['WhatsApp']}")
        if tel_parts:
            story.append(P(' | '.join(tel_parts), fontSize=8, alignment=TA_CENTER))

        story.append(HRFlowable(width='100%', thickness=0.5,
                                color=colors.black, spaceAfter=6, spaceBefore=4))

        # Título
        story.append(PB('COTIZACIÓN / PRESUPUESTO', fontSize=14, alignment=TA_CENTER,
                        spaceAfter=4))
        story.append(HRFlowable(width='100%', thickness=0.5,
                                color=colors.black, spaceAfter=8))

        # Datos de la cotización
        fecha_cot  = cot.get('FechaCotizacion', datetime.now())
        fecha_venc = cot.get('FechaVencimiento')
        if hasattr(fecha_cot, 'strftime'):
            fecha_cot_str  = fecha_cot.strftime('%d/%m/%Y')
        else:
            fecha_cot_str  = str(fecha_cot)[:10]
        if hasattr(fecha_venc, 'strftime'):
            fecha_venc_str = fecha_venc.strftime('%d/%m/%Y')
        else:
            fecha_venc_str = str(fecha_venc)[:10] if fecha_venc else '—'

        datos_meta = [
            [PB('Cotización N°:'), P(cot.get('NumeroCotizacion', ''))],
            [PB('Fecha:'),         P(fecha_cot_str)],
            [PB('Válida hasta:'),  P(fecha_venc_str)],
            [PB('Paciente:'),      P(cot.get('NombrePaciente', ''))],
            [PB('C.I. / Doc.:'),   P(cot.get('NumeroDocumento', '') or '')],
        ]
        if cot.get('NombreMedico'):
            datos_meta.append([PB('Médico ref.:'), P(cot['NombreMedico'])])
        if cot.get('Observaciones'):
            datos_meta.append([PB('Observaciones:'), P(cot['Observaciones'])])

        tbl_meta = Table(datos_meta, colWidths=[4.5 * cm, 12 * cm])
        tbl_meta.setStyle(TableStyle([
            ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING',  (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING',(0,0),(-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(tbl_meta)
        story.append(Spacer(1, 10))

        # Tabla de ítems
        col_w = [1.2 * cm, 9.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm]
        header = [PB('#'), PB('Descripción'), PB('Cant.'), PB('Precio Unit.'), PB('Subtotal')]
        filas  = [header]
        for i, it in enumerate(items, 1):
            precio = float(it.get('PrecioUnitario') or 0)
            cant   = int(it.get('Cantidad') or 1)
            sub    = float(it.get('SubTotal') or precio * cant)
            filas.append([
                P(str(i), alignment=TA_CENTER),
                P(it.get('Descripcion', '')),
                P(str(cant), alignment=TA_CENTER),
                P(f"{simbolo} {precio:,.2f}", alignment=TA_RIGHT),
                P(f"{simbolo} {sub:,.2f}", alignment=TA_RIGHT),
            ])

        tbl_items = Table(filas, colWidths=col_w)
        tbl_items.setStyle(TableStyle([
            ('BACKGROUND',   (0, 0), (-1, 0), colors.HexColor('#1565c0')),
            ('TEXTCOLOR',    (0, 0), (-1, 0), colors.white),
            ('LINEBELOW',    (0, 0), (-1, 0), 1,   colors.white),
            ('ROWBACKGROUNDS',(0,1),(-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
            ('LINEBELOW',    (0, 1), (-1, -1), 0.3, colors.lightgrey),
            ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING',   (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
            ('LEFTPADDING',  (0, 0), (-1, -1), 4),
        ]))
        story.append(tbl_items)
        story.append(Spacer(1, 8))

        # Totales
        subtotal  = float(cot.get('SubTotal')  or 0)
        descuento = float(cot.get('Descuento') or 0)
        total     = float(cot.get('Total')     or subtotal)

        tot_data = []
        tot_data.append([PB('Sub-Total:'), P(f"{simbolo} {subtotal:,.2f}", alignment=TA_RIGHT)])
        if descuento:
            tot_data.append([PB('Descuento:'), P(f"- {simbolo} {descuento:,.2f}", alignment=TA_RIGHT)])
        tot_data.append([PB('TOTAL:', fontSize=11), PB(f"{simbolo} {total:,.2f}", fontSize=11, alignment=TA_RIGHT)])

        tbl_tot = Table(tot_data, colWidths=[14 * cm, 4.2 * cm])
        tbl_tot.setStyle(TableStyle([
            ('ALIGN',       (1, 0), (1, -1), 'RIGHT'),
            ('LINEABOVE',   (0, -1),(-1, -1), 1, colors.black),
            ('TOPPADDING',  (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING',(0,0),(-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(tbl_tot)
        story.append(Spacer(1, 20))

        # Pie
        pie_txt = ("Esta cotización es válida hasta la fecha indicada. "
                   "Los precios pueden variar según disponibilidad de reactivos.")
        story.append(P(pie_txt, fontSize=8, alignment=TA_CENTER,
                       textColor=colors.grey))

        # Generar
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix='cotizacion_')
        tmp.close()
        doc = SimpleDocTemplate(
            tmp.name, pagesize=letter,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2*cm, bottomMargin=2*cm
        )
        doc.build(story)
        return tmp.name

# -*- coding: utf-8 -*-
"""
Ventana de Reportes fiscales y de gestion, y cierre de periodo (fase 5).

Cada reporte se ve en pantalla y se exporta a Excel. La logica esta en
reportes.py y periodos.py.

Copyright 2024-2026 ANgesLAB Solutions
"""

import tkinter as tk
from datetime import date, timedelta
from decimal import Decimal
from tkinter import ttk, messagebox, filedialog

from modulos import reportes as rp, periodos
from modulos.ventana_maestros import COLORS, _tabla, _boton
from modulos.ventana_compras import _campo, _fmt, _fecha_txt


def _celda(v):
    if isinstance(v, Decimal):
        return _fmt(v)
    if isinstance(v, date):
        return v.strftime('%d/%m/%Y')
    return '' if v is None else v


def _excel(nombre, encabezado, filas, pie=None):
    import openpyxl
    ruta = filedialog.asksaveasfilename(defaultextension='.xlsx', initialfile=nombre + '.xlsx')
    if not ruta:
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = nombre[:30]
    ws.append(list(encabezado))
    for f in filas:
        ws.append([float(v) if isinstance(v, Decimal) else v for v in f])
    for f in pie or []:
        ws.append([float(v) if isinstance(v, Decimal) else v for v in f])
    wb.save(ruta)
    messagebox.showinfo('Exportado', 'Guardado en\n%s' % ruta)


class Reporte:
    """Una pestana: filtros, tabla, resumen y exportacion."""

    def __init__(self, nb, titulo, columnas, anchos, producir, con_fechas=True, con_periodo=False):
        self.pag = tk.Frame(nb, bg='white')
        nb.add(self.pag, text='  %s  ' % titulo)
        self.titulo, self.columnas, self.producir = titulo, columnas, producir
        filtro = tk.Frame(self.pag, bg='white')
        filtro.pack(fill='x')
        hoy = date.today()
        self.e_desde = self.e_hasta = self.e_per = None
        if con_fechas:
            self.e_desde = _campo(filtro, 'Desde', 12, hoy.replace(day=1).strftime('%d/%m/%Y'))
            self.e_hasta = _campo(filtro, 'Hasta', 12, hoy.strftime('%d/%m/%Y'))
        if con_periodo:
            previo = hoy.replace(day=1) - timedelta(days=1)
            self.e_per = _campo(filtro, 'Periodo (AAAAMM)', 8, periodos.periodo(previo))
        self.extra = filtro
        tk.Button(filtro, text='Ver', bg=COLORS['primary'], fg='white', relief='flat', padx=12,
                  command=self.ver).pack(side='left', padx=6, pady=(16, 0))
        tk.Button(filtro, text='Excel', bg=COLORS['success'], fg='white', relief='flat', padx=12,
                  command=self.exportar).pack(side='left', pady=(16, 0))
        self.tree = _tabla(self.pag, columnas, anchos)
        self.lbl = tk.Label(self.pag, text='', bg='white', font=('Segoe UI', 10, 'bold'),
                            justify='left')
        self.lbl.pack(anchor='w', pady=4)
        self.filas, self.pie = [], []

    def args(self):
        a = {}
        if self.e_desde:
            a['desde'], a['hasta'] = self.e_desde.get(), self.e_hasta.get()
        if self.e_per:
            a['periodo'] = self.e_per.get().strip()
        return a

    def ver(self):
        try:
            self.filas, self.pie, texto = self.producir(**self.args())
        except Exception as e:
            messagebox.showerror(self.titulo, str(e))
            return
        for i in self.tree.get_children():
            self.tree.delete(i)
        for f in self.filas:
            self.tree.insert('', 'end', values=[_celda(v) for v in f])
        self.lbl.config(text=texto)

    def exportar(self):
        if not self.filas:
            self.ver()
        _excel(self.titulo.replace(' ', '_').lower(), self.columnas, self.filas, self.pie)


def show_reportes(db, app, usuario=''):
    app.clear_content()
    app.set_title('Reportes fiscales y de gestion')
    area = app.setup_scrollable_content()
    nb = ttk.Notebook(area)
    nb.pack(fill='both', expand=True, padx=12, pady=8)

    def libro(desde, hasta):
        l = rp.libro_ventas(db, desde, hasta)
        filas = [(r['n'], r['fecha'], r['rif'], r['razon_social'], r['tipo'], r['numero_factura'],
                  r['numero_control'], r['factura_afectada'], r['total'], r['exento'],
                  r['base_imponible'], r['alicuota'], r['iva'], r['iva_retenido']) for r in l['registros']]
        t = l['totales']
        pie = [('', '', '', 'TOTALES', '', '', '', '', t['total'], t['exento'], t['base'], '',
                t['iva'], t['retenido'])]
        return filas, pie, 'Bs: total %s  exento %s  base %s  IVA %s  IVA retenido %s' % (
            _fmt(t['total']), _fmt(t['exento']), _fmt(t['base']), _fmt(t['iva']), _fmt(t['retenido']))
    Reporte(nb, 'Libro de ventas', ('N', 'Fecha', 'RIF/CI', 'Razon social', 'Tipo', 'Documento',
                                    'Control', 'Afecta a', 'Total Bs', 'Exento', 'Base', 'Alic. %',
                                    'IVA', 'IVA retenido'),
            (35, 80, 95, 180, 90, 110, 90, 90, 85, 80, 80, 50, 70, 80), libro)

    r_iva = None

    def iva(periodo):
        exc = r_iva.e_exc.get().replace(',', '.') or 0
        ret = r_iva.e_ret.get().replace(',', '.') or 0
        r = rp.resumen_iva(db, periodo, exc, ret)
        etiquetas = [('Ventas exentas', 'ventas_exentas'), ('Ventas gravadas (base)', 'ventas_base'),
                     ('Debitos fiscales', 'debitos_fiscales'), ('Compras exentas', 'compras_exentas'),
                     ('Compras gravadas (base)', 'compras_base'), ('Creditos fiscales', 'creditos_fiscales'),
                     ('Excedente del mes anterior', 'excedente_anterior'),
                     ('Cuota tributaria', 'cuota_tributaria'),
                     ('Retenciones de IVA del mes', 'retenciones_mes'),
                     ('Retenciones de meses anteriores', 'retenciones_anteriores'),
                     ('IVA A PAGAR', 'iva_a_pagar'), ('Excedente para el mes siguiente', 'excedente_siguiente'),
                     ('Retenciones por descontar el mes siguiente', 'retenciones_por_descontar_siguiente')]
        filas = [(e, r[k]) for e, k in etiquetas]
        return filas, [], 'Resumen de trabajo para el contador (Bs). No sustituye la planilla del SENIAT.'
    r_iva = Reporte(nb, 'Resumen de IVA', ('Concepto', 'Bs'), (360, 160), iva, con_fechas=False,
                    con_periodo=True)
    r_iva.e_exc = _campo(r_iva.extra, 'Excedente anterior Bs', 10)
    r_iva.e_ret = _campo(r_iva.extra, 'Retenciones por descontar Bs', 10)

    def por_area(desde, hasta):
        r = rp.ventas_por_area(db, desde, hasta)
        total = sum((x['importe'] for x in r), Decimal('0'))
        return [(x['area'], x['pruebas'], x['importe']) for x in r], [('TOTAL', '', total)], \
            'Desde las solicitudes no anuladas. Total %s' % _fmt(total)
    Reporte(nb, 'Ventas por area', ('Area', 'Pruebas', 'Importe'), (300, 100, 120), por_area)

    def por_proc(desde, hasta):
        r = rp.ventas_por_procedencia(db, desde, hasta)
        total = sum((x['importe'] for x in r), Decimal('0'))
        return [(x['procedencia'], x['solicitudes'], x['importe']) for x in r], [('TOTAL', '', total)], \
            'Total %s' % _fmt(total)
    Reporte(nb, 'Ventas por procedencia', ('Procedencia', 'Solicitudes', 'Importe'),
            (300, 100, 120), por_proc)

    def costo():
        r = rp.costo_por_prueba(db)
        perdida = [x['prueba'] for x in r if x['margen'] < 0]
        return [(x['prueba'], x['precio'], x['costo'], x['margen'],
                 '' if x['margen_pct'] is None else '%s%%' % x['margen_pct']) for x in r], [], \
            ('Cuestan mas de lo que se cobran: %s' % ', '.join(perdida)) if perdida else \
            'Solo pruebas con receta. Costo a precio promedio de compra.'
    Reporte(nb, 'Costo por prueba', ('Prueba', 'Precio', 'Costo insumos', 'Margen', 'Margen %'),
            (300, 90, 110, 90, 80), costo, con_fechas=False)

    def resultados(desde, hasta):
        r = rp.estado_resultados(db, desde, hasta)
        filas = [('Ingresos (solicitudes)', r['ingresos']), ('Consumo de insumos', -r['consumo_insumos']),
                 ('Margen bruto', r['margen_bruto'])]
        filas += [('  Gasto: %s' % g['categoria'], -g['monto']) for g in r['gastos']]
        filas += [('Total gastos', -r['total_gastos']), ('RESULTADO', r['resultado'])]
        return filas, [], 'En la moneda del laboratorio. No reemplaza la contabilidad.'
    Reporte(nb, 'Estado de resultados', ('Concepto', 'Monto'), (360, 160), resultados)

    # ── cierre de periodo ──────────────────────────────────────────────
    pag = tk.Frame(nb, bg='white')
    nb.add(pag, text='  Cierre de periodo  ')
    tk.Label(pag, text='Un mes declarado no se toca: cerrado, no admite compras, retenciones ni '
             'facturas (ni sus anulaciones) con fecha de ese mes. Reabrir exige motivo.',
             bg='white', fg=COLORS['text_light'], font=('Segoe UI', 10)).pack(anchor='w', pady=4)
    fila = tk.Frame(pag, bg='white')
    fila.pack(fill='x')
    previo = date.today().replace(day=1) - timedelta(days=1)
    e_per = _campo(fila, 'Periodo (AAAAMM)', 8, periodos.periodo(previo))
    tree = _tabla(pag, ('Periodo', 'Estado', 'Cerrado', 'Por', 'Reabierto', 'Por', 'Motivo'),
                  (80, 80, 130, 80, 130, 80, 360))

    def cargar():
        for i in tree.get_children():
            tree.delete(i)
        for p in periodos.listar(db):
            tree.insert('', 'end', values=(
                p['Periodo'], p['Estado'], _fecha_txt(p.get('FechaCierre')), p.get('UsuarioCierre') or '',
                _fecha_txt(p.get('FechaReapertura')), p.get('UsuarioReapertura') or '',
                p.get('MotivoReapertura') or ''))

    def cerrar():
        if not messagebox.askyesno('Cerrar periodo', 'Cerrar %s? Ya no se podra registrar nada con '
                                   'fecha de ese mes.' % e_per.get()):
            return
        try:
            periodos.cerrar(db, e_per.get(), usuario)
        except ValueError as e:
            messagebox.showerror('No se cerro', str(e))
        cargar()

    def reabrir():
        from modulos.ventana_administrativa import _pedir_texto
        motivo = _pedir_texto(pag, 'Reabrir periodo', 'Motivo (p. ej. declaracion sustitutiva):')
        if not motivo:
            return
        try:
            periodos.reabrir(db, e_per.get(), motivo, usuario)
        except ValueError as e:
            messagebox.showerror('No se reabrio', str(e))
        cargar()

    b = tk.Frame(pag, bg='white')
    b.pack(fill='x', pady=6)
    _boton(b, 'Cerrar periodo', COLORS['danger'], cerrar)
    _boton(b, 'Reabrir', COLORS['text_light'], reabrir)
    cargar()

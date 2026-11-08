# -*- coding: utf-8 -*-
"""
Ventana de Retenciones recibidas (fase 3 del ERP administrativo).

Se carga el comprobante que entrega el cliente agente de retencion; se
aplica a la cuenta por cobrar y queda en el total del mes para la
declaracion. La logica esta en retenciones.py.

Copyright 2024-2026 ANgesLAB Solutions
"""

import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

from modulos import retenciones as rt
from modulos.ventana_maestros import COLORS, _tabla, _boton
from modulos.ventana_compras import _campo, _combo, _fmt, _fecha_txt


def _cuentas_abiertas(db):
    try:
        return db.query(
            "SELECT c.CuentaCobrarID, c.NombrePaciente, c.SaldoPendiente, c.FacturaID, "
            "f.NumeroFactura, f.MontoIVA FROM [CuentasPorCobrar] AS c "
            "LEFT JOIN [Facturas] AS f ON c.FacturaID = f.FacturaID "
            "WHERE c.SaldoPendiente > 0 ORDER BY c.CuentaCobrarID DESC") or []
    except Exception:
        return []


def show_retenciones(db, app, usuario='', usuario_id=0):
    g = rt.GestorRetenciones(db, usuario, usuario_id)
    app.clear_content()
    app.set_title('Retenciones recibidas')
    area = app.setup_scrollable_content()
    pag = tk.Frame(area, bg='white')
    pag.pack(fill='both', expand=True, padx=12, pady=8)
    tk.Label(pag, text='Comprobantes que le entregan al laboratorio sus clientes agentes de '
             'retencion. Rebajan la cuenta del cliente (sin pasar por caja) y se descuentan '
             'en la declaracion. El laboratorio no retiene a nadie.',
             bg='white', fg=COLORS['text_light'], font=('Segoe UI', 10),
             wraplength=1000, justify='left').pack(anchor='w')

    cuentas = []

    def etiquetas_cuentas():
        cuentas[:] = _cuentas_abiertas(db)
        return ['#%s  %s  %s  saldo %s' % (
            c['CuentaCobrarID'], c.get('NombrePaciente') or '',
            ('Fact. %s' % c['NumeroFactura']) if c.get('NumeroFactura') else 'sin factura',
            _fmt(c.get('SaldoPendiente'))) for c in cuentas] or ['(no hay cuentas abiertas)']
    f1 = tk.Frame(pag, bg='white')
    f1.pack(fill='x')
    c_tipo = _combo(f1, 'Tipo', list(rt.TIPOS), 5)
    e_num = _campo(f1, 'N. comprobante', 18)
    e_fecha = _campo(f1, 'Fecha (dd/mm/aaaa)', 12, date.today().strftime('%d/%m/%Y'))
    e_rif = _campo(f1, 'RIF del agente', 14)
    e_nom = _campo(f1, 'Nombre del agente', 26)
    f2 = tk.Frame(pag, bg='white')
    f2.pack(fill='x')
    c_cta = _combo(f2, 'Cuenta por cobrar retenida', etiquetas_cuentas(), 60)
    e_pct = _campo(f2, '% (IVA: 75 o 100)', 6)
    e_monto = _campo(f2, 'o monto retenido Bs', 12)
    e_tasa = _campo(f2, 'Tasa Bs/USD (si no hay factura)', 10)

    f3 = tk.Frame(pag, bg='white')
    f3.pack(fill='x', pady=(10, 0))
    hoy = date.today()
    e_per = _campo(f3, 'Periodo (AAAAMM)', 8, '%04d%02d' % (hoy.year, hoy.month))
    lbl = tk.Label(f3, text='', bg='white', font=('Segoe UI', 10, 'bold'))
    tree = _tabla(pag, ('ID', 'Tipo', 'Comprobante', 'Fecha', 'Agente', 'RIF', 'Factura',
                        '%', 'Retenido Bs', 'Aplicado'),
                  (40, 50, 140, 85, 200, 100, 90, 50, 100, 80))

    def cargar():
        for i in tree.get_children():
            tree.delete(i)
        r = g.resumen_periodo(e_per.get().strip())
        for f in r['detalle']:
            tree.insert('', 'end', iid=str(f['RetencionID']), values=(
                f['RetencionID'], f['Tipo'], f['NumeroComprobante'],
                _fecha_txt(f.get('FechaComprobante')), f.get('AgenteNombre') or '',
                f.get('AgenteRIF'), f.get('NumeroFactura') or '', _fmt(f.get('Porcentaje')),
                _fmt(f.get('MontoRetenido')), _fmt(f.get('MontoAplicado'))))
        lbl.config(text='Para la declaracion del periodo: IVA retenido %s Bs   ISLR retenido %s Bs'
                   % (_fmt(r['iva_retenido']), _fmt(r['islr_retenido'])))

    def registrar():
        i = c_cta.current()
        cuenta = cuentas[i] if cuentas and 0 <= i < len(cuentas) else None
        if not cuenta:
            messagebox.showerror('Falta', 'Elija la cuenta por cobrar retenida.')
            return
        datos = {'tipo': c_tipo.get(), 'numero_comprobante': e_num.get(), 'fecha': e_fecha.get(),
                 'agente_rif': e_rif.get(), 'agente_nombre': e_nom.get(),
                 'cuenta_cobrar_id': cuenta['CuentaCobrarID'], 'factura_id': cuenta.get('FacturaID'),
                 'porcentaje': e_pct.get().replace(',', '.'),
                 'monto_retenido': e_monto.get().replace(',', '.'),
                 'tasa': e_tasa.get().replace(',', '.')}
        try:
            g.registrar(datos)
        except rt.ErrorRetencion as e:
            messagebox.showerror('No se registro', str(e))
            return
        except Exception as e:
            messagebox.showerror('Error', 'No se pudo registrar: %s' % e)
            return
        messagebox.showinfo('Registrada', 'Retencion registrada y aplicada a la cuenta.')
        for e in (e_num, e_pct, e_monto):
            e.delete(0, 'end')
        pos = c_cta.current()
        c_cta['values'] = etiquetas_cuentas()
        c_cta.current(min(max(pos, 0), len(c_cta['values']) - 1))
        cargar()

    def anular():
        s = tree.selection()
        if not s:
            messagebox.showwarning('Seleccione', 'Seleccione un comprobante.')
            return
        from modulos.ventana_administrativa import _pedir_texto
        motivo = _pedir_texto(pag, 'Anular retencion', 'Motivo:')
        if not motivo:
            return
        try:
            g.anular(int(s[0]), motivo)
        except rt.ErrorRetencion as e:
            messagebox.showerror('No se anulo', str(e))
        c_cta['values'] = etiquetas_cuentas()
        cargar()

    def exportar():
        import openpyxl
        r = g.resumen_periodo(e_per.get().strip())
        ruta = filedialog.asksaveasfilename(defaultextension='.xlsx',
                                            initialfile='retenciones_%s.xlsx' % r['periodo'])
        if not ruta:
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Retenciones %s' % r['periodo']
        ws.append(['Tipo', 'Comprobante', 'Fecha', 'Agente', 'RIF agente', 'Factura',
                   'Base Bs', '%', 'Retenido Bs'])
        for f in r['detalle']:
            ws.append([f['Tipo'], f['NumeroComprobante'], _fecha_txt(f.get('FechaComprobante')),
                       f.get('AgenteNombre'), f.get('AgenteRIF'), f.get('NumeroFactura'),
                       f.get('BaseRetencion'), f.get('Porcentaje'), f.get('MontoRetenido')])
        ws.append([])
        ws.append(['IVA retenido', r['iva_retenido']])
        ws.append(['ISLR retenido', r['islr_retenido']])
        wb.save(ruta)
        messagebox.showinfo('Exportado', 'Guardado en\n%s' % ruta)

    tk.Button(f3, text='Ver periodo', bg=COLORS['primary'], fg='white', relief='flat',
              padx=10, command=cargar).pack(side='left', padx=6, pady=(16, 0))
    lbl.pack(side='left', padx=12, pady=(16, 0))
    botones = tk.Frame(pag, bg='white')
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Registrar comprobante', COLORS['primary'], registrar)
    _boton(botones, 'Anular', COLORS['danger'], anular)
    _boton(botones, 'Exportar a Excel', COLORS['success'], exportar)
    cargar()

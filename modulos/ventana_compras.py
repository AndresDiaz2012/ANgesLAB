# -*- coding: utf-8 -*-
"""
Ventana de Compras (fase 2 del ERP administrativo).

Pestanas: registrar la factura del proveedor con la mercancia, ordenes de
compra, compras registradas con el libro de compras, recetas de consumo por
prueba y cuentas por pagar por antiguedad.

La logica esta en compras.py, donde se prueba. Aqui solo se piden los datos
y se muestra el mensaje del gestor tal cual cuando algo no se puede guardar.

Copyright 2024-2026 ANgesLAB Solutions
"""

import logging
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

from modulos import compras as cp
from modulos.ventana_maestros import COLORS, _tabla, _boton

_log = logging.getLogger('angeslab.ventana_compras')

IVAS = ['0', '16', '8', '31']


def _tasa_bcv(db):
    try:
        from modulos.tasas_cambio import GestorTasasCambio
        return float(GestorTasasCambio(db).get_tasa_actual('USD') or 0)
    except Exception:
        return 0.0


def _proveedores(db):
    from modulos.modulo_administrativo import GestorProveedores
    return GestorProveedores(db).listar_proveedores()


def _productos(db):
    return db.query("SELECT ProductoID, NombreProducto, UnidadMedida FROM [Productos] "
                    "WHERE Activo=True ORDER BY NombreProducto") or []


def _etiqueta_prov(p):
    return '%s  (%s)' % (p.get('RazonSocial', ''), p.get('RIF') or 's/RIF')


def _fmt(v):
    try:
        return '{:,.2f}'.format(float(v or 0))
    except Exception:
        return str(v)


def _fecha_txt(v):
    try:
        f = cp._fecha(v)
        return f.strftime('%d/%m/%Y') if f else ''
    except Exception:
        return str(v or '')


def _campo(parent, etiqueta, ancho=16, valor=''):
    marco = tk.Frame(parent, bg='white')
    marco.pack(side='left', padx=6, pady=4)
    tk.Label(marco, text=etiqueta, font=('Segoe UI', 9), bg='white',
             fg=COLORS['text_light']).pack(anchor='w')
    e = ttk.Entry(marco, font=('Segoe UI', 10), width=ancho)
    e.pack(anchor='w')
    if valor not in (None, ''):
        e.insert(0, str(valor))
    return e


def _combo(parent, etiqueta, valores, ancho=30):
    marco = tk.Frame(parent, bg='white')
    marco.pack(side='left', padx=6, pady=4)
    tk.Label(marco, text=etiqueta, font=('Segoe UI', 9), bg='white',
             fg=COLORS['text_light']).pack(anchor='w')
    c = ttk.Combobox(marco, values=valores, state='readonly', font=('Segoe UI', 10), width=ancho)
    c.pack(anchor='w')
    if valores:
        c.set(valores[0])
    return c


class EditorLineas:
    """Tabla de lineas (producto, cantidad, precio, IVA, lote, vence) con alta y baja."""

    def __init__(self, parent, db, con_lote=True):
        self.db = db
        self.con_lote = con_lote
        self.lineas = []
        self.productos = _productos(db)
        self._por_nombre = {p['NombreProducto']: p for p in self.productos}

        alta = tk.Frame(parent, bg='white')
        alta.pack(fill='x')
        self.c_prod = _combo(alta, 'Producto', list(self._por_nombre), 32)
        self.e_cant = _campo(alta, 'Cantidad', 8)
        self.e_precio = _campo(alta, 'Precio unitario', 10)
        self.c_iva = _combo(alta, 'IVA %', IVAS, 4)
        if con_lote:
            self.e_lote = _campo(alta, 'Lote', 10)
            self.e_vence = _campo(alta, 'Vence (dd/mm/aaaa)', 12)
        tk.Button(alta, text='Agregar', bg=COLORS['primary'], fg='white', relief='flat',
                  padx=10, command=self.agregar).pack(side='left', padx=6, pady=(16, 0))
        tk.Button(alta, text='Quitar', bg=COLORS['danger'], fg='white', relief='flat',
                  padx=10, command=self.quitar).pack(side='left', pady=(16, 0))

        cols = ('Producto', 'Cantidad', 'Precio', 'IVA %', 'Importe') + \
            (('Lote', 'Vence') if con_lote else ())
        self.tree = _tabla(parent, cols, (240, 70, 80, 50, 90) + ((90, 90) if con_lote else ()))
        self.tree.configure(height=6)
        self.lbl_total = tk.Label(parent, text='', font=('Segoe UI', 10, 'bold'), bg='white',
                                  fg=COLORS['text'])
        self.lbl_total.pack(anchor='e')

    def agregar(self, producto_id=None, cantidad=None, precio=None, iva=None,
                detalle_orden_id=None):
        try:
            if producto_id is None:
                prod = self._por_nombre.get(self.c_prod.get())
                if not prod:
                    raise ValueError('Elija un producto.')
                producto_id = prod['ProductoID']
                cantidad = float(self.e_cant.get().replace(',', '.'))
                precio = float(self.e_precio.get().replace(',', '.'))
                iva = self.c_iva.get()
            nombre = next((p['NombreProducto'] for p in self.productos
                           if int(p['ProductoID']) == int(producto_id)), str(producto_id))
        except ValueError as e:
            messagebox.showerror('Linea', str(e) if str(e) else 'Cantidad y precio tienen que ser numeros.')
            return
        linea = {'producto_id': int(producto_id), 'cantidad': cantidad, 'precio': precio,
                 'iva': iva or '0', 'detalle_orden_id': detalle_orden_id}
        if self.con_lote:
            linea['lote'] = self.e_lote.get().strip() if detalle_orden_id is None else ''
            linea['vence'] = self.e_vence.get().strip() if detalle_orden_id is None else ''
        self.lineas.append(linea)
        self._pintar(nombre_nuevo=nombre)
        for e in (self.e_cant, self.e_precio) + ((self.e_lote, self.e_vence) if self.con_lote else ()):
            e.delete(0, 'end')

    def quitar(self):
        sel = self.tree.selection()
        if sel:
            del self.lineas[int(sel[0])]
            self._pintar()

    def editar_lote_seleccionado(self, lote, vence):
        sel = self.tree.selection()
        if sel:
            self.lineas[int(sel[0])].update(lote=lote, vence=vence)
            self._pintar()

    def limpiar(self):
        self.lineas = []
        self._pintar()

    def _pintar(self, nombre_nuevo=None):
        for i in self.tree.get_children():
            self.tree.delete(i)
        nombres = {int(p['ProductoID']): p['NombreProducto'] for p in self.productos}
        for i, l in enumerate(self.lineas):
            importe = float(l['cantidad']) * float(l['precio'])
            fila = (nombres.get(l['producto_id'], l['producto_id']), l['cantidad'],
                    _fmt(l['precio']), l['iva'], _fmt(importe))
            if self.con_lote:
                fila += (l.get('lote', ''), l.get('vence', ''))
            self.tree.insert('', 'end', iid=str(i), values=fila)
        try:
            t = cp.GestorCompras.totales(cp.GestorCompras._lineas_validas(
                [dict(l, vence=None) for l in self.lineas])) if self.lineas else None
        except cp.ErrorCompra:
            t = None
        self.lbl_total.config(text='' if not t else
                              'Exento %s   Base %s   IVA %s   TOTAL %s' % (
                                  _fmt(t['exento']), _fmt(t['base']), _fmt(t['iva']),
                                  _fmt(t['total'])))


# ══════════════════════════════════════════════════════════════════════════
def show_compras(db, app, usuario=''):
    cp.asegurar_esquema(db)
    app.clear_content()
    app.set_title('Compras e inventario')
    area = app.setup_scrollable_content()
    nb = ttk.Notebook(area)
    nb.pack(fill='both', expand=True, padx=12, pady=8)
    gestor = cp.GestorCompras(db, usuario)

    paginas = {}
    for nombre in ('Registrar factura', 'Ordenes de compra', 'Compras registradas',
                   'Recetas por prueba', 'Por pagar'):
        f = tk.Frame(nb, bg='white')
        nb.add(f, text='  %s  ' % nombre)
        paginas[nombre] = f

    # Cada pestana devuelve como recargarse: al cambiar de pestana se ve lo
    # que se acaba de registrar en otra
    recargas = [
        _pestana_factura(paginas['Registrar factura'], db, gestor),
        _pestana_ordenes(paginas['Ordenes de compra'], db, gestor, usuario),
        _pestana_compras(paginas['Compras registradas'], db, gestor),
        _pestana_recetas(paginas['Recetas por prueba'], db, usuario),
        _pestana_por_pagar(paginas['Por pagar'], db),
    ]

    def al_cambiar(_evento):
        fn = recargas[nb.index(nb.select())]
        if fn:
            try:
                fn()
            except Exception as e:
                _log.warning('Recarga de pestana: %s', e)
    nb.bind('<<NotebookTabChanged>>', al_cambiar)


# ── Registrar factura ─────────────────────────────────────────────────────
def _pestana_factura(pag, db, gestor):
    tk.Label(pag, text='La mercancia entra al inventario, la factura al libro de compras y '
             'la deuda a cuentas por pagar, todo de una vez.', bg='white',
             fg=COLORS['text_light'], font=('Segoe UI', 10)).pack(anchor='w', padx=8, pady=4)
    provs = _proveedores(db)
    etiquetas = [_etiqueta_prov(p) for p in provs]
    fila1 = tk.Frame(pag, bg='white')
    fila1.pack(fill='x', padx=4)
    c_prov = _combo(fila1, 'Proveedor', etiquetas, 40)
    c_orden = _combo(fila1, 'Orden de compra (opcional)', ['(sin orden)'], 22)
    fila2 = tk.Frame(pag, bg='white')
    fila2.pack(fill='x', padx=4)
    e_num = _campo(fila2, 'N. factura', 12)
    e_ctrl = _campo(fila2, 'N. control', 14)
    e_fecha = _campo(fila2, 'Fecha (dd/mm/aaaa)', 12, date.today().strftime('%d/%m/%Y'))
    c_moneda = _combo(fila2, 'Moneda', list(cp.MONEDAS), 5)
    e_tasa = _campo(fila2, 'Tasa BCV (Bs/USD)', 10, _tasa_bcv(db) or '')
    editor = EditorLineas(pag, db, con_lote=True)
    ordenes = {}

    def proveedor_actual():
        i = c_prov.current()
        return provs[i] if 0 <= i < len(provs) else None

    def cargar_ordenes(*_):
        p = proveedor_actual()
        ordenes.clear()
        valores = ['(sin orden)']
        if p:
            for o in gestor.ordenes_pendientes(p['ProveedorID']):
                ordenes[o['NumeroOrden']] = o
                valores.append(o['NumeroOrden'])
        c_orden['values'] = valores
        c_orden.set(valores[0])

    def cargar_lineas_orden(*_):
        o = ordenes.get(c_orden.get())
        if not o:
            return
        editor.limpiar()
        orden = gestor.obtener_orden(o['OrdenCompraID'])
        c_moneda.set(orden.get('Moneda') or 'USD')
        for l in orden['lineas']:
            pendiente = float(l.get('Cantidad') or 0) - float(l.get('CantidadRecibida') or 0)
            if pendiente > 0:
                editor.agregar(l['ProductoID'], pendiente, l.get('PrecioUnitario'),
                               '%g' % float(l.get('PorcentajeIVA') or 0), l['DetalleOrdenID'])
        messagebox.showinfo('Orden cargada', 'Se cargaron las cantidades pendientes de la orden. '
                            'Corrija lo que haya llegado distinto y anote lote y vencimiento '
                            'de cada linea (seleccionela y use "Lote de la linea").')

    def lote_de_linea():
        dlg = tk.Toplevel(pag)
        dlg.title('Lote y vencimiento')
        dlg.grab_set()
        e_l = _campo(dlg, 'Lote', 14)
        e_v = _campo(dlg, 'Vence (dd/mm/aaaa)', 12)

        def ok():
            editor.editar_lote_seleccionado(e_l.get().strip(), e_v.get().strip())
            dlg.destroy()
        tk.Button(dlg, text='Aplicar', command=ok, bg=COLORS['primary'], fg='white',
                  relief='flat').pack(side='left', padx=8, pady=(16, 0))

    def guardar():
        p = proveedor_actual()
        if not p:
            messagebox.showerror('Falta', 'Elija el proveedor.')
            return
        o = ordenes.get(c_orden.get())
        factura = {'proveedor_id': p['ProveedorID'], 'numero': e_num.get(),
                   'numero_control': e_ctrl.get(), 'fecha': e_fecha.get(),
                   'moneda': c_moneda.get(), 'tasa': e_tasa.get().replace(',', '.'),
                   'orden_id': o['OrdenCompraID'] if o else None}
        try:
            r = gestor.registrar_compra(factura, editor.lineas)
            if r['compra_id'] is None:
                if not messagebox.askyesno(
                        'La factura no cuadra con la orden',
                        '\n'.join(r['avisos']) + '\n\nRegistrar igual?'):
                    return
                r = gestor.registrar_compra(factura, editor.lineas, confirmar_avisos=True)
        except cp.ErrorCompra as e:
            messagebox.showerror('No se registro', str(e))
            return
        except Exception as e:
            _log.error('Error registrando compra: %s', e)
            messagebox.showerror('Error', 'No se pudo registrar: %s' % e)
            return
        messagebox.showinfo('Compra registrada', 'Compra %s registrada. Total %s %s.\n'
                            'Ya esta en inventario, libro de compras y cuentas por pagar.'
                            % (r['numero'], _fmt(r['totales']['total']), factura['moneda']))
        editor.limpiar()
        for e in (e_num, e_ctrl):
            e.delete(0, 'end')
        cargar_ordenes()

    c_prov.bind('<<ComboboxSelected>>', cargar_ordenes)
    c_orden.bind('<<ComboboxSelected>>', cargar_lineas_orden)
    cargar_ordenes()
    botones = tk.Frame(pag, bg='white')
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Registrar compra', COLORS['primary'], guardar)
    _boton(botones, 'Lote de la linea', COLORS['text_light'], lote_de_linea)
    return cargar_ordenes


# ── Ordenes ───────────────────────────────────────────────────────────────
def _pestana_ordenes(pag, db, gestor, usuario):
    tree = _tabla(pag, ('ID', 'Numero', 'Fecha', 'Proveedor', 'Moneda', 'Total', 'Estado',
                        'Creo', 'Aprobo'), (40, 120, 90, 220, 60, 90, 110, 80, 80))

    def cargar():
        for i in tree.get_children():
            tree.delete(i)
        for o in gestor.listar_ordenes():
            tree.insert('', 'end', iid=str(o['OrdenCompraID']), values=(
                o['OrdenCompraID'], o.get('NumeroOrden'), _fecha_txt(o.get('FechaOrden')),
                o.get('RazonSocial'), o.get('Moneda'), _fmt(o.get('MontoTotal')),
                o.get('Estado'), o.get('UsuarioCrea') or '', o.get('UsuarioAprueba') or ''))

    def sel():
        s = tree.selection()
        if not s:
            messagebox.showwarning('Seleccione', 'Seleccione una orden.')
        return int(s[0]) if s else None

    def accion(fn, *args):
        try:
            fn(*args)
        except cp.ErrorCompra as e:
            messagebox.showerror('No se pudo', str(e))
        cargar()

    def nueva(sugerida=False):
        provs = _proveedores(db)
        dlg = tk.Toplevel(pag)
        dlg.title('Nueva orden de compra')
        dlg.configure(bg='white')
        dlg.geometry('900x480')
        dlg.grab_set()
        fila = tk.Frame(dlg, bg='white')
        fila.pack(fill='x')
        c_prov = _combo(fila, 'Proveedor', [_etiqueta_prov(p) for p in provs], 40)
        c_mon = _combo(fila, 'Moneda', list(cp.MONEDAS), 5)
        e_obs = _campo(fila, 'Observaciones', 30)
        ed = EditorLineas(dlg, db, con_lote=False)
        if sugerida:
            for p in gestor.productos_bajo_minimo():
                ed.agregar(p['ProductoID'], p['CantidadSugerida'],
                           p.get('UltimoPrecioCompra') or 0, '0')

        def guardar():
            i = c_prov.current()
            if i < 0:
                messagebox.showerror('Falta', 'Elija el proveedor.', parent=dlg)
                return
            try:
                gestor.crear_orden(provs[i]['ProveedorID'], ed.lineas, c_mon.get(), e_obs.get())
            except cp.ErrorCompra as e:
                messagebox.showerror('No se guardo', str(e), parent=dlg)
                return
            dlg.destroy()
            cargar()
        tk.Button(dlg, text='Guardar orden', bg=COLORS['primary'], fg='white', relief='flat',
                  padx=16, pady=4, command=guardar).pack(pady=6)

    def anular():
        oid = sel()
        if oid is None:
            return
        from modulos.ventana_administrativa import _pedir_texto
        motivo = _pedir_texto(pag, 'Anular orden', 'Motivo de la anulacion:')
        if motivo:
            accion(gestor.anular_orden, oid, motivo)

    botones = tk.Frame(pag, bg='white')
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Nueva orden', COLORS['primary'], nueva)
    _boton(botones, 'Sugerir desde minimos', COLORS['text_light'], lambda: nueva(True))
    _boton(botones, 'Aprobar', COLORS['success'],
           lambda: (lambda o: o is not None and accion(gestor.aprobar_orden, o))(sel()))
    _boton(botones, 'Anular', COLORS['danger'], anular)
    _boton(botones, 'Actualizar', COLORS['text_light'], cargar)
    cargar()
    return cargar


# ── Compras registradas y libro ───────────────────────────────────────────
def _pestana_compras(pag, db, gestor):
    filtro = tk.Frame(pag, bg='white')
    filtro.pack(fill='x')
    hoy = date.today()
    e_desde = _campo(filtro, 'Desde', 12, hoy.replace(day=1).strftime('%d/%m/%Y'))
    e_hasta = _campo(filtro, 'Hasta', 12, hoy.strftime('%d/%m/%Y'))
    tree = _tabla(pag, ('ID', 'Compra', 'Fecha fact.', 'Proveedor', 'Factura', 'Control',
                        'Moneda', 'Exento', 'Base', 'IVA', 'Total', 'Pago'),
                  (40, 120, 85, 180, 80, 95, 55, 75, 75, 70, 80, 70))
    lbl = tk.Label(pag, text='', bg='white', font=('Segoe UI', 10, 'bold'))
    lbl.pack(anchor='e')

    def cargar():
        for i in tree.get_children():
            tree.delete(i)
        try:
            filas = gestor.listar_compras(e_desde.get(), e_hasta.get())
        except cp.ErrorCompra as e:
            messagebox.showerror('Fechas', str(e))
            return
        for c in filas:
            tree.insert('', 'end', iid=str(c['CompraID']), values=(
                c['CompraID'], c.get('NumeroCompra'), _fecha_txt(c.get('FechaFacturaProveedor')),
                c.get('RazonSocial'), c.get('NumeroFacturaProveedor'), c.get('NumeroControl'),
                c.get('Moneda'), _fmt(c.get('MontoExento')), _fmt(c.get('BaseImponible')),
                _fmt(c.get('MontoIVA')), _fmt(c.get('MontoTotal')), c.get('EstadoPago')))
        libro = cp.libro_compras(db, e_desde.get(), e_hasta.get())['totales']
        lbl.config(text='Libro de compras (Bs): exento %s  base %s  IVA %s  total %s' % (
            _fmt(libro['total_exento']), _fmt(libro['base_imponible']),
            _fmt(libro['iva_soportado']), _fmt(libro['total_compras'])))

    def anular():
        s = tree.selection()
        if not s:
            messagebox.showwarning('Seleccione', 'Seleccione una compra.')
            return
        from modulos.ventana_administrativa import _pedir_texto
        motivo = _pedir_texto(pag, 'Anular compra', 'Motivo de la anulacion:')
        if not motivo:
            return
        try:
            gestor.anular_compra(int(s[0]), motivo)
        except cp.ErrorCompra as e:
            messagebox.showerror('No se anulo', str(e))
        cargar()

    def exportar():
        try:
            import openpyxl
            libro = cp.libro_compras(db, e_desde.get(), e_hasta.get())
        except Exception as e:
            messagebox.showerror('Error', str(e))
            return
        ruta = filedialog.asksaveasfilename(defaultextension='.xlsx',
                                            initialfile='libro_compras.xlsx')
        if not ruta:
            return
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Libro de compras'
        ws.append(['N', 'Fecha', 'RIF', 'Razon social', 'N. factura', 'N. control',
                   'Total Bs', 'Exento Bs', 'Base Bs', 'Alicuota %', 'IVA Bs', 'IVA retenido Bs'])
        for r in libro['registros']:
            ws.append([r['n'], r['fecha'], r['rif'], r['razon_social'], r['numero_factura'],
                       r['numero_control'], r['total'], r['exento'], r['base_imponible'],
                       r['alicuota'], r['iva'], r['retencion_iva']])
        t = libro['totales']
        ws.append(['', '', '', 'TOTALES', '', '', t['total_compras'], t['total_exento'],
                   t['base_imponible'], '', t['iva_soportado'], t['retencion_iva']])
        wb.save(ruta)
        messagebox.showinfo('Exportado', 'Libro de compras guardado en\n%s' % ruta)

    tk.Button(filtro, text='Buscar', bg=COLORS['primary'], fg='white', relief='flat',
              padx=10, command=cargar).pack(side='left', padx=6, pady=(16, 0))
    botones = tk.Frame(pag, bg='white')
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Libro de compras a Excel', COLORS['success'], exportar)
    _boton(botones, 'Anular compra', COLORS['danger'], anular)
    cargar()
    return cargar


# ── Recetas ───────────────────────────────────────────────────────────────
def _pestana_recetas(pag, db, usuario):
    rec = cp.GestorRecetas(db, usuario)
    tk.Label(pag, text='Que reactivos y materiales gasta cada prueba. Se descuentan solos al '
             'capturar o validar la prueba, desde el dia en que se define la receta.',
             bg='white', fg=COLORS['text_light'], font=('Segoe UI', 10)).pack(anchor='w', padx=8)
    pruebas = db.query("SELECT PruebaID, NombrePrueba FROM [Pruebas] WHERE Activo=True "
                       "ORDER BY NombrePrueba") or []
    por_nombre = {p['NombrePrueba']: p['PruebaID'] for p in pruebas}
    fila = tk.Frame(pag, bg='white')
    fila.pack(fill='x')
    c_prueba = _combo(fila, 'Prueba', list(por_nombre), 40)
    productos = _productos(db)
    prod_nombre = {p['NombreProducto']: p['ProductoID'] for p in productos}
    c_prod = _combo(fila, 'Producto', list(prod_nombre), 30)
    e_cant = _campo(fila, 'Cantidad por prueba', 8)
    tree = _tabla(pag, ('Producto', 'Cantidad', 'Unidad', 'Desde'), (300, 90, 80, 120))
    tree.configure(height=8)
    actual = []

    def cargar(*_):
        actual.clear()
        for i in tree.get_children():
            tree.delete(i)
        pid = por_nombre.get(c_prueba.get())
        if not pid:
            return
        for r in rec.receta(pid):
            actual.append((r['ProductoID'], r['Cantidad']))
            tree.insert('', 'end', values=(r.get('NombreProducto'), r['Cantidad'],
                                           r.get('UnidadMedida') or '', _fecha_txt(r.get('FechaDesde'))))

    def guardar(nuevos):
        pid = por_nombre.get(c_prueba.get())
        if not pid:
            return
        try:
            rec.definir_receta(pid, nuevos)
        except cp.ErrorCompra as e:
            messagebox.showerror('No se guardo', str(e))
        cargar()

    def agregar():
        prod = prod_nombre.get(c_prod.get())
        try:
            cant = float(e_cant.get().replace(',', '.'))
        except ValueError:
            messagebox.showerror('Cantidad', 'La cantidad tiene que ser un numero.')
            return
        guardar([a for a in actual if a[0] != prod] + [(prod, cant)])

    def quitar():
        s = tree.selection()
        if s:
            i = tree.index(s[0])
            guardar([a for j, a in enumerate(actual) if j != i])

    def descontar():
        n = rec.consumir_pendientes()
        messagebox.showinfo('Consumo', 'Se descontaron los reactivos de %d pruebas.' % n)

    c_prueba.bind('<<ComboboxSelected>>', cargar)
    botones = tk.Frame(pag, bg='white')
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Agregar a la receta', COLORS['primary'], agregar)
    _boton(botones, 'Quitar', COLORS['danger'], quitar)
    _boton(botones, 'Descontar consumos ahora', COLORS['success'], descontar)
    cargar()
    return None


# ── Por pagar ─────────────────────────────────────────────────────────────
def _pestana_por_pagar(pag, db):
    tk.Label(pag, text='Antiguedad de saldos (USD)', bg='white', font=('Segoe UI', 11, 'bold')
             ).pack(anchor='w', padx=8, pady=(6, 0))
    tramos = [t[0] for t in cp.TRAMOS]
    tree = _tabla(pag, ('Proveedor',) + tuple(tramos) + ('Total',),
                  (240,) + (90,) * len(tramos) + (100,))
    tree.configure(height=7)
    tk.Label(pag, text='Vencen en los proximos 7 dias o ya vencieron', bg='white',
             font=('Segoe UI', 11, 'bold')).pack(anchor='w', padx=8)
    t_venc = _tabla(pag, ('ID', 'Proveedor', 'Documento', 'Vence', 'Saldo'),
                    (40, 260, 120, 100, 100))
    t_venc.configure(height=6)

    def cargar():
        for t in (tree, t_venc):
            for i in t.get_children():
                t.delete(i)
        for prov, fila in cp.antiguedad_saldos(db).items():
            tree.insert('', 'end', values=(prov,) + tuple(_fmt(fila[t]) for t in tramos)
                        + (_fmt(fila['Total']),))
        for c in cp.vencimientos(db, 7):
            t_venc.insert('', 'end', iid=str(c['CuentaPagarID']), values=(
                c['CuentaPagarID'], c.get('ProveedorNombre'), c.get('NumeroDocumento'),
                _fecha_txt(c.get('FechaVencimiento')), _fmt(c.get('SaldoPendiente'))))

    def historial():
        s = t_venc.selection()
        if not s:
            messagebox.showwarning('Seleccione', 'Seleccione una cuenta de la lista de vencimientos.')
            return
        pagos = cp.historial_pagos(db, int(s[0]))
        texto = '\n'.join('%s  %s  %s  ref. %s' % (p.get('NumeroPago'), _fecha_txt(p.get('FechaPago')),
                                                   _fmt(p.get('MontoPagado')),
                                                   p.get('NumeroReferencia') or '-')
                          for p in pagos) or 'Sin pagos registrados.'
        messagebox.showinfo('Pagos de la cuenta %s' % s[0], texto)

    botones = tk.Frame(pag, bg='white')
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Historial de pagos', COLORS['primary'], historial)
    _boton(botones, 'Actualizar', COLORS['text_light'], cargar)
    cargar()
    return cargar

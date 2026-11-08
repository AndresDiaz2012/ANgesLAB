# -*- coding: utf-8 -*-
"""
Ventana de Facturacion electronica (fase 4 del ERP administrativo).

Arriba, el emisor: HKA con su ambiente, usuario y clave (cifrada al
guardar), y un boton para probar la conexion. Abajo, la bandeja de lo que
falta: facturas sin emitir, rechazadas o que quedaron sin respuesta, con
emitir o reintentar, pasar a contingencia y anular. La logica esta en
emision.py.

Copyright 2024-2026 ANgesLAB Solutions
"""

import tkinter as tk
from tkinter import ttk, messagebox

from modulos import emision as em
from modulos.ventana_maestros import COLORS, _tabla, _boton
from modulos.ventana_compras import _campo, _combo, _fmt, _fecha_txt


def show_emision(db, app, usuario_id=0):
    em.asegurar_esquema(db)
    app.clear_content()
    app.set_title('Facturacion electronica')
    area = app.setup_scrollable_content()
    pag = tk.Frame(area, bg='white')
    pag.pack(fill='both', expand=True, padx=12, pady=8)

    # ── emisor ─────────────────────────────────────────────────────────
    marco = tk.LabelFrame(pag, text='  Emisor: The Factory HKA (imprenta digital)  ', bg='white',
                          font=('Segoe UI', 10, 'bold'), padx=8, pady=6)
    marco.pack(fill='x')
    lbl_estado = tk.Label(marco, text='', bg='white', font=('Segoe UI', 10))
    lbl_estado.pack(anchor='w')
    fila = tk.Frame(marco, bg='white')
    fila.pack(fill='x')
    actual = em.emisor_activo(db) or {}
    c_amb = _combo(fila, 'Ambiente', ['Prueba', 'Produccion'], 11)
    if actual.get('Ambiente'):
        c_amb.set(actual['Ambiente'])
    e_url = _campo(fila, 'URL (vacio = demo de HKA en Prueba)', 36, actual.get('URLBase') or '')
    e_usr = _campo(fila, 'Usuario HKA', 16, actual.get('Usuario') or '')
    e_clave = _campo(fila, 'Clave HKA', 16)
    e_clave.configure(show='*')
    e_serie = _campo(fila, 'Serie', 5, actual.get('Serie') or '')
    e_suc = _campo(fila, 'Sucursal', 5, actual.get('Sucursal') or '')

    def pintar_estado():
        fila_e = em.emisor_activo(db)
        if fila_e and fila_e.get('Tipo') == em.TIPO_HKA:
            lbl_estado.config(fg=COLORS['success'], text='Emitiendo con HKA, ambiente %s (%s).'
                              % (fila_e.get('Ambiente'), fila_e.get('URLBase')))
        else:
            lbl_estado.config(fg=COLORS['danger'], text='Sin imprenta digital: el numero de '
                              'control lo pone el programa, como hasta ahora. Desde el 19/04/2027 '
                              'hace falta HKA.')

    def guardar():
        try:
            em.guardar_emisor_hka(db, e_usr.get(), e_clave.get(), c_amb.get(), e_url.get(),
                                  e_serie.get(), e_suc.get())
        except em.ErrorEmision as e:
            messagebox.showerror('No se guardo', str(e))
            return
        e_clave.delete(0, 'end')
        pintar_estado()
        messagebox.showinfo('Guardado', 'HKA queda como emisor. Las facturas nuevas nacen '
                            'pendientes y toman el numero de control de HKA al emitirse.')

    def probar():
        fila_e = em.emisor_activo(db)
        if not fila_e or fila_e.get('Tipo') != em.TIPO_HKA:
            messagebox.showwarning('Sin HKA', 'Guarde primero los datos de HKA.')
            return
        try:
            em.EmisorHKA.desde_configuracion(fila_e)._obtener_token(forzar=True)
        except em.ErrorEmision as e:
            messagebox.showerror('Sin conexion', str(e))
            return
        messagebox.showinfo('Conexion correcta', 'HKA acepto el usuario y la clave.')

    b = tk.Frame(marco, bg='white')
    b.pack(fill='x', pady=4)
    _boton(b, 'Guardar emisor', COLORS['primary'], guardar)
    _boton(b, 'Probar conexion', COLORS['text_light'], probar)
    pintar_estado()

    # ── bandeja ────────────────────────────────────────────────────────
    tk.Label(pag, text='Facturas por emitir, rechazadas o sin respuesta', bg='white',
             font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(10, 0))
    tree = _tabla(pag, ('ID', 'Numero', 'Fecha', 'Tipo', 'Total', 'Moneda', 'Estado', 'Intentos',
                        'Mensaje'), (40, 130, 85, 50, 80, 55, 85, 60, 420))

    def cargar():
        for i in tree.get_children():
            tree.delete(i)
        try:
            filas = em.GestorEmision(db).pendientes()
        except Exception as e:
            messagebox.showerror('Error', str(e))
            return
        for f in filas:
            tree.insert('', 'end', iid=str(f['FacturaID']), values=(
                f['FacturaID'], f.get('NumeroFactura'), _fecha_txt(f.get('FechaEmision')),
                f.get('TipoDocumento') or 'Factura', _fmt(f.get('MontoTotal')),
                f.get('MonedaFactura') or '', f.get('EstadoEmision') or 'Pendiente',
                f.get('IntentosEmision') or 0, f.get('MensajeEmisor') or ''))

    def seleccion():
        s = tree.selection()
        if not s:
            messagebox.showwarning('Seleccione', 'Seleccione una factura.')
        return int(s[0]) if s else None

    def emitir(contingencia=False):
        fid = seleccion()
        if fid is None:
            return
        if contingencia and not messagebox.askyesno(
                'Contingencia', 'Se usara el siguiente numero del talonario impreso de '
                'contingencia. Solo para cuando HKA no responde (falla electrica, sin '
                'internet). Continuar?'):
            return
        try:
            control = em.GestorEmision(db).emitir(fid, contingencia=contingencia)
        except em.ErrorConexion as e:
            messagebox.showwarning('Sin respuesta', str(e))
        except em.ErrorEmision as e:
            messagebox.showerror('No se emitio', str(e))
        else:
            messagebox.showinfo('Emitida', 'Numero de control: %s' % control)
        cargar()

    def anular():
        fid = seleccion()
        if fid is None:
            return
        from modulos.ventana_administrativa import _pedir_texto
        motivo = _pedir_texto(pag, 'Anular factura', 'Motivo de la anulacion:')
        if not motivo:
            return
        try:
            em.GestorEmision(db).anular(fid, motivo, usuario_id)
        except em.ErrorEmision as e:
            messagebox.showerror('No se anulo', str(e))
        cargar()

    botones = tk.Frame(pag, bg='white')
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Emitir / reintentar', COLORS['primary'], emitir)
    _boton(botones, 'Emitir en contingencia', COLORS['text_light'], lambda: emitir(True))
    _boton(botones, 'Anular', COLORS['danger'], anular)
    _boton(botones, 'Actualizar', COLORS['text_light'], cargar)
    cargar()

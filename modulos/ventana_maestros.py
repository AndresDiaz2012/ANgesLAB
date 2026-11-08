# -*- coding: utf-8 -*-
"""
Ventanas de los maestros fiscales: Clientes y Proveedores.

La logica y las validaciones viven en maestros_fiscales.py y en
GestorProveedores, donde se pueden probar. Aqui solo se pide el dato y se
muestra el error tal como lo redacta el gestor: el usuario lee por que no se
guardo ("el digito verificador no corresponde") y no un codigo.

Copyright 2024-2026 ANgesLAB Solutions
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox

from modulos.maestros_fiscales import (
    GestorClientes, ErrorMaestro, asegurar_esquema,
    TIPOS_CLIENTE, TIPOS_CONTRIBUYENTE, CONDICIONES_PAGO,
    TIPOS_PERSONA, DESCRIPCION_TIPO_PERSONA,
)

_log = logging.getLogger('angeslab.ventana_maestros')

COLORS = {
    'primary': '#1e3a5f', 'success': '#27ae60', 'danger': '#e74c3c',
    'bg': '#f0f4f8', 'text': '#2c3e50', 'text_light': '#7f8c8d',
}

# Conceptos de ISLR que ya conoce facturacion_fiscal (Decreto 1.808)
try:
    from modulos.facturacion_fiscal import ConfiguracionFiscal
    CONCEPTOS_ISLR = [''] + list(ConfiguracionFiscal.RETENCIONES_ISLR.keys())
except Exception:  # pragma: no cover
    CONCEPTOS_ISLR = ['']


class DialogoFicha:
    """
    Formulario generico de alta y edicion.

    campos: lista de (clave, etiqueta, tipo, opciones); tipo 'entry' o 'combo'.
    guardar: funcion que recibe el dict y guarda; si lanza ErrorMaestro o
    ValueError el mensaje se muestra y el formulario sigue abierto con lo
    escrito, para corregir sin volver a teclearlo todo.
    """

    def __init__(self, parent, titulo, campos, guardar, valores=None):
        self.ok = False
        self._guardar_fn = guardar
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(titulo)
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        alto = 140 + 58 * len(campos)
        x = (self.dialog.winfo_screenwidth() - 520) // 2
        y = max(20, (self.dialog.winfo_screenheight() - alto) // 2)
        self.dialog.geometry('520x%d+%d+%d' % (alto, x, y))

        header = tk.Frame(self.dialog, bg=COLORS['primary'], height=46)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text=titulo, font=('Segoe UI', 13, 'bold'),
                 bg=COLORS['primary'], fg='white').pack(pady=10)

        cuerpo = tk.Frame(self.dialog, bg='white')
        cuerpo.pack(fill='both', expand=True, padx=25, pady=10)
        self.widgets = {}
        valores = valores or {}
        for clave, etiqueta, tipo, opciones in campos:
            tk.Label(cuerpo, text=etiqueta, font=('Segoe UI', 10),
                     bg='white').pack(anchor='w', pady=(4, 1))
            if tipo == 'combo':
                w = ttk.Combobox(cuerpo, values=opciones, state='readonly',
                                 font=('Segoe UI', 10), width=40)
                valor = valores.get(clave)
                w.set(valor if valor in opciones else (opciones[0] if opciones else ''))
            else:
                w = ttk.Entry(cuerpo, font=('Segoe UI', 10), width=50)
                valor = valores.get(clave)
                if valor not in (None, ''):
                    w.insert(0, str(valor))
            w.pack(anchor='w', fill='x')
            self.widgets[clave] = w

        botones = tk.Frame(self.dialog, bg='white')
        botones.pack(side='bottom', fill='x', padx=25, pady=12)
        tk.Button(botones, text='Guardar', font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=20, pady=6,
                  cursor='hand2', command=self._guardar).pack(side='left')
        tk.Button(botones, text='Cancelar', font=('Segoe UI', 11),
                  bg=COLORS['text_light'], fg='white', relief='flat', padx=20, pady=6,
                  cursor='hand2', command=self.dialog.destroy).pack(side='right')
        self.dialog.wait_window()

    def _guardar(self):
        datos = {k: w.get().strip() for k, w in self.widgets.items()}
        try:
            self._guardar_fn(datos)
        except (ErrorMaestro, ValueError) as e:
            messagebox.showerror('No se guardo', str(e), parent=self.dialog)
            return
        except Exception as e:
            _log.error('Error guardando ficha: %s', e)
            messagebox.showerror('Error', 'No se pudo guardar: %s' % e,
                                 parent=self.dialog)
            return
        self.ok = True
        self.dialog.destroy()


def _tabla(parent, columnas, anchos):
    marco = tk.Frame(parent, bg='white')
    marco.pack(fill='both', expand=True, pady=8)
    tree = ttk.Treeview(marco, columns=columnas, show='headings', height=16)
    for c, a in zip(columnas, anchos):
        tree.heading(c, text=c)
        tree.column(c, width=a, anchor='w')
    barra = ttk.Scrollbar(marco, orient='vertical', command=tree.yview)
    tree.configure(yscrollcommand=barra.set)
    tree.pack(side='left', fill='both', expand=True)
    barra.pack(side='right', fill='y')
    return tree


def _barra_busqueda(parent, al_buscar):
    fila = tk.Frame(parent, bg=COLORS['bg'])
    fila.pack(fill='x', pady=(0, 4))
    tk.Label(fila, text='Buscar (nombre o RIF):', font=('Segoe UI', 10),
             bg=COLORS['bg']).pack(side='left')
    entrada = ttk.Entry(fila, font=('Segoe UI', 10), width=30)
    entrada.pack(side='left', padx=6)
    entrada.bind('<Return>', lambda _e: al_buscar())
    inactivos = tk.BooleanVar(value=False)
    ttk.Checkbutton(fila, text='Ver inactivos', variable=inactivos,
                    command=al_buscar).pack(side='left', padx=10)
    tk.Button(fila, text='Buscar', font=('Segoe UI', 10), bg=COLORS['primary'],
              fg='white', relief='flat', padx=10, command=al_buscar).pack(side='left')
    return entrada, inactivos


def _boton(parent, texto, color, accion):
    tk.Button(parent, text=texto, font=('Segoe UI', 11, 'bold'), bg=color,
              fg='white', relief='flat', padx=18, pady=6, cursor='hand2',
              command=accion).pack(side='left', padx=5)


# ══════════════════════════════════════════════════════════════════════════
#  Clientes
# ══════════════════════════════════════════════════════════════════════════
CAMPOS_CLIENTE = [
    ('TipoCliente', 'Tipo de cliente', 'combo', list(TIPOS_CLIENTE)),
    ('Documento', 'RIF (J-12345678-9) o cedula', 'entry', None),
    ('RazonSocial', 'Razon social o nombre', 'entry', None),
    ('DomicilioFiscal', 'Domicilio fiscal', 'entry', None),
    ('Telefono', 'Telefono', 'entry', None),
    ('Email', 'Correo (para enviar la factura)', 'entry', None),
    ('TipoContribuyente', 'Tipo de contribuyente (vacio = segun el documento)', 'combo',
     [''] + list(TIPOS_CONTRIBUYENTE)),
    ('CondicionPago', 'Condicion de pago', 'combo', list(CONDICIONES_PAGO)),
    ('DiasCredito', 'Dias de credito', 'entry', None),
    ('LimiteCredito', 'Limite de credito (USD)', 'entry', None),
]


def show_clientes(db, app):
    asegurar_esquema(db)
    gestor = GestorClientes(db)
    app.clear_content()
    app.set_title('Clientes')
    area = app.setup_scrollable_content()
    main = tk.Frame(area, bg=COLORS['bg'])
    main.pack(fill='both', expand=True, padx=20, pady=10)
    tk.Label(main, text='Quien recibe la factura: persona, empresa, aseguradora o '
             'convenio. El RIF se comprueba con su digito verificador.',
             font=('Segoe UI', 10), bg=COLORS['bg'], fg=COLORS['text_light']).pack(anchor='w')

    columnas = ('ID', 'Documento', 'Razon social', 'Tipo', 'Contribuyente',
                'Condicion', 'Dias', 'Activo')
    tree = None

    def cargar():
        for i in tree.get_children():
            tree.delete(i)
        filas = gestor.listar(solo_activos=not inactivos.get(),
                              busqueda=entrada.get().strip() or None)
        for c in filas:
            tree.insert('', 'end', iid=str(c['ClienteID']), values=(
                c['ClienteID'], c.get('Documento', ''), c.get('RazonSocial', ''),
                c.get('TipoCliente', ''), c.get('TipoContribuyente', ''),
                c.get('CondicionPago', ''), c.get('DiasCredito') or 0,
                'Si' if c.get('Activo') else 'No'))

    entrada, inactivos = _barra_busqueda(main, lambda: cargar())
    tree = _tabla(main, columnas, (50, 120, 260, 100, 120, 90, 50, 60))

    def seleccionado():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Seleccione', 'Seleccione un cliente de la tabla.')
            return None
        return int(sel[0])

    def nuevo():
        if DialogoFicha(app.root, 'Nuevo cliente', CAMPOS_CLIENTE, gestor.crear).ok:
            cargar()

    def editar():
        cid = seleccionado()
        if cid is None:
            return
        if DialogoFicha(app.root, 'Editar cliente', CAMPOS_CLIENTE,
                        lambda d: gestor.actualizar(cid, d),
                        valores=gestor.obtener(cid)).ok:
            cargar()

    def desactivar():
        cid = seleccionado()
        if cid is None:
            return
        if messagebox.askyesno('Desactivar', 'El cliente no se borra: sus facturas '
                               'lo siguen nombrando. Solo deja de ofrecerse. Continuar?'):
            gestor.desactivar(cid)
            cargar()

    botones = tk.Frame(main, bg=COLORS['bg'])
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Nuevo cliente', COLORS['primary'], nuevo)
    _boton(botones, 'Editar', COLORS['success'], editar)
    _boton(botones, 'Desactivar', COLORS['danger'], desactivar)
    cargar()


# ══════════════════════════════════════════════════════════════════════════
#  Proveedores
# ══════════════════════════════════════════════════════════════════════════
_PERSONAS = ['%s - %s' % (k, DESCRIPCION_TIPO_PERSONA[k]) for k in TIPOS_PERSONA]

CAMPOS_PROVEEDOR = [
    ('RazonSocial', 'Razon social', 'entry', None),
    ('RIF', 'RIF (J-12345678-9)', 'entry', None),
    ('Direccion', 'Domicilio fiscal', 'entry', None),
    ('Telefono', 'Telefono', 'entry', None),
    ('Email', 'Correo', 'entry', None),
    ('Contacto', 'Persona de contacto', 'entry', None),
    ('TipoPersona', 'Tipo de persona (tabla del Decreto 1.808)', 'combo', [''] + _PERSONAS),
    ('TipoContribuyente', 'Tipo de contribuyente', 'combo', ['Ordinario', 'Especial']),
    ('ConceptoISLR', 'Concepto de ISLR por defecto', 'combo', CONCEPTOS_ISLR),
    ('DiasCredito', 'Dias de credito', 'entry', None),
]


def _datos_proveedor(datos):
    """Del formulario al gestor: el combo de persona trae la descripcion."""
    datos = dict(datos)
    if datos.get('TipoPersona'):
        datos['TipoPersona'] = datos['TipoPersona'].split(' - ')[0]
    return datos


def _valores_proveedor(fila):
    fila = dict(fila or {})
    tp = fila.get('TipoPersona')
    if tp in DESCRIPCION_TIPO_PERSONA:
        fila['TipoPersona'] = '%s - %s' % (tp, DESCRIPCION_TIPO_PERSONA[tp])
    return fila


def show_proveedores(db, app):
    from modulos.modulo_administrativo import GestorProveedores
    asegurar_esquema(db)
    gestor = GestorProveedores(db)
    app.clear_content()
    app.set_title('Proveedores')
    area = app.setup_scrollable_content()
    main = tk.Frame(area, bg=COLORS['bg'])
    main.pack(fill='both', expand=True, padx=20, pady=10)
    tk.Label(main, text='El tipo de persona y el concepto deciden la retencion de ISLR '
             'al pagarle. El laboratorio es ordinario: no retiene IVA.',
             font=('Segoe UI', 10), bg=COLORS['bg'], fg=COLORS['text_light']).pack(anchor='w')

    columnas = ('ID', 'RIF', 'Razon social', 'Persona', 'Contribuyente',
                'Concepto ISLR', 'Dias', 'Activo')
    tree = None

    def cargar():
        for i in tree.get_children():
            tree.delete(i)
        for p in gestor.listar_proveedores(solo_activos=not inactivos.get(),
                                           busqueda=entrada.get().strip() or None):
            tree.insert('', 'end', iid=str(p['ProveedorID']), values=(
                p['ProveedorID'], p.get('RIF', ''), p.get('RazonSocial', ''),
                p.get('TipoPersona') or '', p.get('TipoContribuyente') or '',
                p.get('ConceptoISLR') or '', p.get('DiasCredito') or 0,
                'Si' if p.get('Activo') else 'No'))

    entrada, inactivos = _barra_busqueda(main, lambda: cargar())
    tree = _tabla(main, columnas, (50, 120, 260, 70, 110, 150, 50, 60))

    def seleccionado():
        sel = tree.selection()
        if not sel:
            messagebox.showwarning('Seleccione', 'Seleccione un proveedor de la tabla.')
            return None
        return int(sel[0])

    def nuevo():
        if DialogoFicha(app.root, 'Nuevo proveedor', CAMPOS_PROVEEDOR,
                        lambda d: gestor.crear_proveedor(_datos_proveedor(d))).ok:
            cargar()

    def editar():
        pid = seleccionado()
        if pid is None:
            return
        if DialogoFicha(app.root, 'Editar proveedor', CAMPOS_PROVEEDOR,
                        lambda d: gestor.actualizar_proveedor(pid, _datos_proveedor(d)),
                        valores=_valores_proveedor(gestor.obtener_proveedor(pid))).ok:
            cargar()

    def desactivar():
        pid = seleccionado()
        if pid is None:
            return
        if messagebox.askyesno('Desactivar', 'El proveedor no se borra. Continuar?'):
            gestor.desactivar_proveedor(pid)
            cargar()

    botones = tk.Frame(main, bg=COLORS['bg'])
    botones.pack(fill='x', pady=6)
    _boton(botones, 'Nuevo proveedor', COLORS['primary'], nuevo)
    _boton(botones, 'Editar', COLORS['success'], editar)
    _boton(botones, 'Desactivar', COLORS['danger'], desactivar)
    cargar()

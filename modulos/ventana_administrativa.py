# -*- coding: utf-8 -*-
"""
Ventana Administrativa - UI del Modulo Administrativo/Contable
ANgesLAB - Sistema de Gestion de Laboratorio Clinico

Vistas:
- show_caja: Gestion de caja chica (apertura, movimientos, cierre)
- show_dashboard_financiero: Dashboard con KPIs financieros
- show_cuentas_cobrar: Cuentas por cobrar (cartera de clientes)
- show_cuentas_pagar: Cuentas por pagar (proveedores)
- show_gastos: Registro y control de gastos

Copyright 2024-2026 ANgesLAB Solutions
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

try:
    from modulos.modulo_administrativo import (
        GestorCajaChica,
        GestorCuentasPorCobrar,
        GestorCuentasPorPagar,
        GestorGastos,
        ResumenFinanciero
    )
except ImportError:
    raise ImportError("Se requiere modulos.modulo_administrativo para la ventana administrativa")


# Colores consistentes con ANgesLAB.pyw
COLORS = {
    'bg': '#f8fafc',
    'sidebar': '#0f172a',
    'primary': '#0891b2',
    'secondary': '#06b6d4',
    'success': '#059669',
    'warning': '#d97706',
    'danger': '#dc2626',
    'info': '#7c3aed',
    'text': '#0f172a',
    'text_light': '#64748b',
    'white': '#ffffff',
    'border': '#e2e8f0',
    'accent': '#0d9488',
}


class VentanaAdministrativa:
    """Controlador de UI para el modulo administrativo/contable."""

    def __init__(self, db, user):
        self.db = db
        self.user = user
        self.gestor_caja = GestorCajaChica(db)
        self.gestor_cxc = GestorCuentasPorCobrar(db)
        self.gestor_cxp = GestorCuentasPorPagar(db)
        self.gestor_gastos = GestorGastos(db)
        self.resumen = ResumenFinanciero(db)

    # ------------------------------------------------------------------
    # Helpers de permisos
    # ------------------------------------------------------------------
    def _puede_acceder(self):
        return self.user.get('Nivel', 'Consulta') in (
            'Desarrollador', 'Administrador', 'Facturador', 'Recepcion')

    def _puede_operar_caja(self):
        return self.user.get('Nivel') in ('Desarrollador', 'Administrador')

    def _puede_registrar_movimientos(self):
        return self.user.get('Nivel') in ('Desarrollador', 'Administrador', 'Facturador')

    def _es_solo_lectura(self):
        return self.user.get('Nivel') == 'Recepcion'

    # ------------------------------------------------------------------
    # Helpers de UI
    # ------------------------------------------------------------------
    def _obtener_formas_pago(self):
        try:
            return self.db.query("SELECT * FROM [FormasPago] WHERE Activo=True ORDER BY Nombre")
        except:
            return []

    def _obtener_categorias(self):
        try:
            return self.db.query("SELECT * FROM [CategoriaGastos] WHERE Activo=True ORDER BY Nombre")
        except:
            return []

    def _crear_tarjeta_kpi(self, parent, icon, label, value, color, formato_moneda=True):
        card = tk.Frame(parent, bg='white', highlightbackground=COLORS['border'],
                        highlightthickness=1)
        card.pack(side='left', expand=True, fill='both', padx=6, pady=5)

        inner = tk.Frame(card, bg='white')
        inner.pack(padx=15, pady=12, fill='both', expand=True)

        tk.Label(inner, text=icon, font=('Segoe UI', 20), bg='white', fg=color).pack(anchor='w')

        if formato_moneda:
            valor_texto = f"${float(value):,.2f}"
        else:
            valor_texto = str(value)

        tk.Label(inner, text=valor_texto, font=('Segoe UI', 18, 'bold'),
                 bg='white', fg=COLORS['text']).pack(anchor='w')
        tk.Label(inner, text=label, font=('Segoe UI', 9),
                 bg='white', fg=COLORS['text_light']).pack(anchor='w')
        tk.Frame(card, bg=color, height=3).pack(fill='x', side='bottom')
        return card

    def _crear_tabla(self, parent, columnas, anchos=None):
        """Crea un Treeview con scrollbar."""
        frame_tabla = tk.Frame(parent, bg='white')
        frame_tabla.pack(fill='both', expand=True, padx=10, pady=5)

        scroll_y = ttk.Scrollbar(frame_tabla, orient='vertical')
        scroll_y.pack(side='right', fill='y')

        tree = ttk.Treeview(frame_tabla, columns=columnas, show='headings',
                            yscrollcommand=scroll_y.set, height=12)
        scroll_y.config(command=tree.yview)

        for i, col in enumerate(columnas):
            ancho = anchos[i] if anchos and i < len(anchos) else 100
            tree.heading(col, text=col)
            tree.column(col, width=ancho, minwidth=50)

        tree.pack(fill='both', expand=True)

        tree.tag_configure('ingreso', foreground=COLORS['success'])
        tree.tag_configure('egreso', foreground=COLORS['danger'])
        tree.tag_configure('anulado', foreground='#aaaaaa')
        tree.tag_configure('vencida', background='#fef2f2')

        return tree

    # ==================================================================
    # VISTA 1: CAJA CHICA
    # ==================================================================
    def show_caja(self, app):
        if not self._puede_acceder():
            messagebox.showwarning("Acceso Denegado",
                                   "No tiene permisos para acceder al modulo administrativo.")
            return

        app.clear_content()
        app.set_title("💰 Caja")
        scrollable = app.setup_scrollable_content()

        main_frame = tk.Frame(scrollable, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        caja = self.gestor_caja.obtener_caja_abierta()

        if not caja:
            self._mostrar_caja_cerrada(main_frame, app)
        else:
            self._mostrar_caja_abierta(main_frame, app, caja)

    def _mostrar_caja_cerrada(self, parent, app):
        # Estado
        estado_frame = tk.Frame(parent, bg='#fef2f2', highlightbackground=COLORS['danger'],
                                highlightthickness=1)
        estado_frame.pack(fill='x', pady=(0, 15))
        tk.Label(estado_frame, text="🔴  CAJA CERRADA", font=('Segoe UI', 14, 'bold'),
                 bg='#fef2f2', fg=COLORS['danger']).pack(pady=15)
        tk.Label(estado_frame, text="No hay una caja abierta para el dia de hoy",
                 font=('Segoe UI', 10), bg='#fef2f2', fg=COLORS['text_light']).pack(pady=(0, 15))

        if not self._puede_operar_caja():
            tk.Label(parent, text="Contacte al administrador para abrir la caja.",
                     font=('Segoe UI', 11), bg=COLORS['bg'], fg=COLORS['text_light']).pack(pady=20)
            return

        # Formulario apertura
        form_frame = tk.LabelFrame(parent, text="  Abrir Caja  ", font=('Segoe UI', 12, 'bold'),
                                   bg='white', fg=COLORS['text'], padx=20, pady=15)
        form_frame.pack(fill='x', pady=10)

        row1 = tk.Frame(form_frame, bg='white')
        row1.pack(fill='x', pady=8)
        tk.Label(row1, text="Monto de Apertura ($):", font=('Segoe UI', 11),
                 bg='white', width=22, anchor='w').pack(side='left')
        entry_monto = ttk.Entry(row1, font=('Segoe UI', 12), width=20)
        entry_monto.pack(side='left', padx=10)
        entry_monto.insert(0, "0.00")

        row2 = tk.Frame(form_frame, bg='white')
        row2.pack(fill='x', pady=8)
        tk.Label(row2, text="Efectivo Inicial ($):", font=('Segoe UI', 11),
                 bg='white', width=22, anchor='w').pack(side='left')
        entry_efectivo = ttk.Entry(row2, font=('Segoe UI', 12), width=20)
        entry_efectivo.pack(side='left', padx=10)
        entry_efectivo.insert(0, "0.00")

        def abrir_caja():
            try:
                monto = float(entry_monto.get().replace(',', ''))
                efectivo = float(entry_efectivo.get().replace(',', ''))
            except ValueError:
                messagebox.showerror("Error", "Ingrese montos validos.")
                return
            if monto < 0 or efectivo < 0:
                messagebox.showerror("Error", "Los montos no pueden ser negativos.")
                return

            exito, msg = self.gestor_caja.abrir_caja(monto, efectivo,
                                                      self.user.get('UsuarioID', 1))
            if exito:
                messagebox.showinfo("Caja Abierta", msg)
                self.show_caja(app)
            else:
                messagebox.showerror("Error", msg)

        tk.Button(form_frame, text="✅  ABRIR CAJA", font=('Segoe UI', 12, 'bold'),
                  bg=COLORS['success'], fg='white', relief='flat', padx=30, pady=10,
                  cursor='hand2', command=abrir_caja).pack(pady=15)

    def _mostrar_caja_abierta(self, parent, app, caja):
        caja_id = caja.get('CajaID')

        # Estado
        estado_frame = tk.Frame(parent, bg='#ecfdf5', highlightbackground=COLORS['success'],
                                highlightthickness=1)
        estado_frame.pack(fill='x', pady=(0, 10))
        info_row = tk.Frame(estado_frame, bg='#ecfdf5')
        info_row.pack(fill='x', padx=20, pady=12)

        tk.Label(info_row, text="🟢  CAJA ABIERTA", font=('Segoe UI', 13, 'bold'),
                 bg='#ecfdf5', fg=COLORS['success']).pack(side='left')

        fecha_apertura = caja.get('FechaApertura', '')
        if fecha_apertura:
            try:
                if isinstance(fecha_apertura, datetime):
                    fecha_str = fecha_apertura.strftime('%d/%m/%Y %H:%M')
                else:
                    fecha_str = str(fecha_apertura)
            except:
                fecha_str = str(fecha_apertura)
        else:
            fecha_str = 'N/A'

        monto_apertura = float(caja.get('MontoApertura', 0) or 0)
        tk.Label(info_row, text=f"Apertura: {fecha_str}  |  Monto: ${monto_apertura:,.2f}",
                 font=('Segoe UI', 10), bg='#ecfdf5', fg=COLORS['text_light']).pack(side='right')

        # KPI Cards
        total_ingresos = float(caja.get('TotalIngresos', 0) or 0)
        total_egresos = float(caja.get('TotalEgresos', 0) or 0)
        efectivo_inicial = float(caja.get('EfectivoInicial', 0) or 0)
        efectivo_esperado = efectivo_inicial + total_ingresos - total_egresos
        balance = total_ingresos - total_egresos

        cards_frame = tk.Frame(parent, bg=COLORS['bg'])
        cards_frame.pack(fill='x', pady=5)
        self._crear_tarjeta_kpi(cards_frame, "📈", "Total Ingresos", total_ingresos, COLORS['success'])
        self._crear_tarjeta_kpi(cards_frame, "📉", "Total Egresos", total_egresos, COLORS['danger'])
        self._crear_tarjeta_kpi(cards_frame, "💵", "Efectivo Esperado", efectivo_esperado, COLORS['primary'])
        self._crear_tarjeta_kpi(cards_frame, "💰", "Balance", balance,
                                COLORS['success'] if balance >= 0 else COLORS['danger'])

        # Botones de accion
        if self._puede_registrar_movimientos():
            btn_frame = tk.Frame(parent, bg=COLORS['bg'])
            btn_frame.pack(fill='x', pady=10)

            tk.Button(btn_frame, text="➕ Registrar Ingreso", font=('Segoe UI', 11, 'bold'),
                      bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                      cursor='hand2',
                      command=lambda: self._registrar_movimiento(app, caja_id, 'Ingreso')
                      ).pack(side='left', padx=5)

            tk.Button(btn_frame, text="➖ Registrar Egreso", font=('Segoe UI', 11, 'bold'),
                      bg=COLORS['danger'], fg='white', relief='flat', padx=20, pady=8,
                      cursor='hand2',
                      command=lambda: self._registrar_movimiento(app, caja_id, 'Egreso')
                      ).pack(side='left', padx=5)

            if self._puede_operar_caja():
                tk.Button(btn_frame, text="🔒 Cerrar Caja", font=('Segoe UI', 11, 'bold'),
                          bg=COLORS['warning'], fg='white', relief='flat', padx=20, pady=8,
                          cursor='hand2',
                          command=lambda: self._cerrar_caja(app, caja_id)
                          ).pack(side='right', padx=5)

        # Tabla de movimientos
        tk.Label(parent, text="Movimientos del Dia", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', padx=10, pady=(15, 5))

        columnas = ('Hora', 'Tipo', 'Categoria', 'Descripcion', 'Monto', 'Forma Pago', 'Referencia')
        anchos = (80, 70, 120, 200, 100, 110, 100)
        tree = self._crear_tabla(parent, columnas, anchos)

        movimientos = self.gestor_caja.obtener_movimientos_caja(caja_id)
        for mov in movimientos:
            fecha = mov.get('Fecha', '')
            try:
                if isinstance(fecha, datetime):
                    hora = fecha.strftime('%H:%M:%S')
                else:
                    hora = str(fecha).split(' ')[-1] if ' ' in str(fecha) else str(fecha)
            except:
                hora = str(fecha)

            tipo = mov.get('Tipo', '')
            monto = float(mov.get('Monto', 0) or 0)
            anulado = mov.get('Anulado', False)

            tag = 'anulado' if anulado else ('ingreso' if tipo == 'Ingreso' else 'egreso')
            prefijo = '[ANULADO] ' if anulado else ''

            tree.insert('', 'end', values=(
                hora,
                prefijo + tipo,
                mov.get('Categoria', ''),
                mov.get('Descripcion', ''),
                f"${monto:,.2f}",
                mov.get('FormaPago', ''),
                mov.get('Referencia', ''),
            ), tags=(tag,))

    def _registrar_movimiento(self, app, caja_id, tipo):
        dialogo = DialogoMovimientoCaja(app.root, self.db, tipo)
        if dialogo.resultado:
            exito, msg = self.gestor_caja.registrar_movimiento(
                caja_id, dialogo.resultado, self.user.get('UsuarioID', 1))
            if exito:
                messagebox.showinfo("Exito", msg)
                self.show_caja(app)
            else:
                messagebox.showerror("Error", msg)

    def _cerrar_caja(self, app, caja_id):
        caja = self.gestor_caja.obtener_caja_abierta()
        if not caja:
            messagebox.showerror("Error", "No hay caja abierta.")
            return

        resumen = self.gestor_caja.obtener_resumen_caja(caja_id)
        dialogo = DialogoCierreCaja(app.root, caja, resumen)
        if dialogo.resultado:
            exito, msg = self.gestor_caja.cerrar_caja(
                caja_id, dialogo.resultado['efectivo_final'],
                dialogo.resultado['observaciones'], self.user.get('UsuarioID', 1))
            if exito:
                messagebox.showinfo("Caja Cerrada", msg)
                self.show_caja(app)
            else:
                messagebox.showerror("Error", msg)

    # ==================================================================
    # VISTA 2: DASHBOARD FINANCIERO
    # ==================================================================
    def show_dashboard_financiero(self, app):
        if not self._puede_acceder():
            messagebox.showwarning("Acceso Denegado",
                                   "No tiene permisos para acceder al modulo administrativo.")
            return

        app.clear_content()
        app.set_title("📊 Dashboard Financiero")
        scrollable = app.setup_scrollable_content()

        main_frame = tk.Frame(scrollable, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        indicadores = self.resumen.indicadores_clave()

        # KPIs del dia
        tk.Label(main_frame, text="Resumen del Dia", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', pady=(0, 5))

        row_dia = tk.Frame(main_frame, bg=COLORS['bg'])
        row_dia.pack(fill='x', pady=5)
        self._crear_tarjeta_kpi(row_dia, "📈", "Ingresos Hoy",
                                indicadores.get('ingresos_hoy', 0), COLORS['success'])
        self._crear_tarjeta_kpi(row_dia, "📉", "Egresos Hoy",
                                indicadores.get('egresos_hoy', 0), COLORS['danger'])
        self._crear_tarjeta_kpi(row_dia, "💰", "Saldo Hoy",
                                indicadores.get('saldo_hoy', 0), COLORS['primary'])

        # KPIs del mes
        tk.Label(main_frame, text="Resumen del Mes", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', pady=(15, 5))

        row_mes = tk.Frame(main_frame, bg=COLORS['bg'])
        row_mes.pack(fill='x', pady=5)
        self._crear_tarjeta_kpi(row_mes, "📈", "Ingresos Mes",
                                indicadores.get('ingresos_mes', 0), COLORS['success'])
        self._crear_tarjeta_kpi(row_mes, "📉", "Egresos Mes",
                                indicadores.get('egresos_mes', 0), COLORS['danger'])
        self._crear_tarjeta_kpi(row_mes, "💰", "Saldo Mes",
                                indicadores.get('saldo_mes', 0), COLORS['primary'])

        # Cartera
        tk.Label(main_frame, text="Estado de Cartera", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', pady=(15, 5))

        cartera_frame = tk.Frame(main_frame, bg=COLORS['bg'])
        cartera_frame.pack(fill='x', pady=5)

        # CxC
        cxc_frame = tk.LabelFrame(cartera_frame, text="  Cuentas por Cobrar  ",
                                   font=('Segoe UI', 10, 'bold'), bg='white',
                                   fg=COLORS['text'], padx=15, pady=10)
        cxc_frame.pack(side='left', expand=True, fill='both', padx=(0, 5))

        cxc_total = float(indicadores.get('cxc_total', 0) or 0)
        tk.Label(cxc_frame, text=f"Total Pendiente: ${cxc_total:,.2f}",
                 font=('Segoe UI', 12, 'bold'), bg='white',
                 fg=COLORS['warning'] if cxc_total > 0 else COLORS['success']).pack(anchor='w', pady=5)

        resumen_cxc = self.gestor_cxc.obtener_resumen_cartera()
        vencidas = sum(float(resumen_cxc.get(k, 0) or 0)
                       for k in ['30_dias', '60_dias', '90_dias', 'mas_90'])
        tk.Label(cxc_frame, text=f"Vencidas: ${vencidas:,.2f}",
                 font=('Segoe UI', 10), bg='white',
                 fg=COLORS['danger'] if vencidas > 0 else COLORS['text_light']).pack(anchor='w')

        # CxP
        cxp_frame = tk.LabelFrame(cartera_frame, text="  Cuentas por Pagar  ",
                                   font=('Segoe UI', 10, 'bold'), bg='white',
                                   fg=COLORS['text'], padx=15, pady=10)
        cxp_frame.pack(side='left', expand=True, fill='both', padx=(5, 0))

        cxp_total = float(indicadores.get('cxp_total', 0) or 0)
        tk.Label(cxp_frame, text=f"Total Pendiente: ${cxp_total:,.2f}",
                 font=('Segoe UI', 12, 'bold'), bg='white',
                 fg=COLORS['warning'] if cxp_total > 0 else COLORS['success']).pack(anchor='w', pady=5)

        resumen_cxp = self.gestor_cxp.obtener_resumen()
        cxp_vencidas = float(resumen_cxp.get('vencidas', 0) or 0)
        tk.Label(cxp_frame, text=f"Vencidas: ${cxp_vencidas:,.2f}",
                 font=('Segoe UI', 10), bg='white',
                 fg=COLORS['danger'] if cxp_vencidas > 0 else COLORS['text_light']).pack(anchor='w')

        # Desglose por forma de pago
        tk.Label(main_frame, text="Ingresos por Forma de Pago (Hoy)",
                 font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', pady=(15, 5))

        hoy = datetime.now().strftime('%m/%d/%Y')
        desglose = self.resumen.desglose_ingresos_por_forma_pago(hoy, hoy)

        if desglose:
            cols = ('Forma de Pago', 'Total', 'Cantidad')
            tree = self._crear_tabla(main_frame, cols, (200, 150, 100))
            tree.configure(height=6)
            for d in desglose:
                nombre = d.get('Nombre', 'N/A') or 'N/A'
                total = float(d.get('Total', 0) or 0)
                cant = int(d.get('Cantidad', 0) or 0)
                tree.insert('', 'end', values=(nombre, f"${total:,.2f}", cant))
        else:
            tk.Label(main_frame, text="Sin movimientos registrados hoy",
                     font=('Segoe UI', 10), bg=COLORS['bg'],
                     fg=COLORS['text_light']).pack(anchor='w', padx=10, pady=5)

        # Estado caja
        caja = self.gestor_caja.obtener_caja_abierta()
        caja_text = "🟢 Caja Abierta" if caja else "🔴 Sin Caja Abierta"
        caja_color = COLORS['success'] if caja else COLORS['text_light']
        tk.Label(main_frame, text=caja_text, font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['bg'], fg=caja_color).pack(anchor='w', pady=(15, 5))

        # Boton actualizar
        tk.Button(main_frame, text="🔄 Actualizar", font=('Segoe UI', 10),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=5,
                  cursor='hand2',
                  command=lambda: self.show_dashboard_financiero(app)).pack(pady=10)

    # ==================================================================
    # VISTA 3: CUENTAS POR COBRAR
    # ==================================================================
    def show_cuentas_cobrar(self, app):
        if not self._puede_acceder() or self._es_solo_lectura():
            messagebox.showwarning("Acceso Denegado",
                                   "No tiene permisos para esta seccion.")
            return

        app.clear_content()
        app.set_title("💳 Cuentas por Cobrar")
        scrollable = app.setup_scrollable_content()

        main_frame = tk.Frame(scrollable, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Aging cards
        resumen = self.gestor_cxc.obtener_resumen_cartera()

        tk.Label(main_frame, text="Resumen de Cartera", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', pady=(0, 5))

        aging_frame = tk.Frame(main_frame, bg=COLORS['bg'])
        aging_frame.pack(fill='x', pady=5)

        self._crear_tarjeta_kpi(aging_frame, "✅", "Vigente",
                                resumen.get('vigente', 0), COLORS['success'])
        self._crear_tarjeta_kpi(aging_frame, "⚠️", "1-30 dias",
                                resumen.get('30_dias', 0), COLORS['warning'])
        self._crear_tarjeta_kpi(aging_frame, "🔶", "31-60 dias",
                                resumen.get('60_dias', 0), '#ea580c')
        self._crear_tarjeta_kpi(aging_frame, "🔴", "61-90 dias",
                                resumen.get('90_dias', 0), COLORS['danger'])
        self._crear_tarjeta_kpi(aging_frame, "⛔", "+90 dias",
                                resumen.get('mas_90', 0), '#7f1d1d')

        # Filtros
        filtro_frame = tk.LabelFrame(main_frame, text="  Filtros  ", font=('Segoe UI', 10),
                                      bg='white', fg=COLORS['text'], padx=10, pady=8)
        filtro_frame.pack(fill='x', pady=10)

        filtro_inner = tk.Frame(filtro_frame, bg='white')
        filtro_inner.pack(fill='x')

        tk.Label(filtro_inner, text="Estado:", font=('Segoe UI', 10),
                 bg='white').pack(side='left', padx=(0, 5))
        combo_estado = ttk.Combobox(filtro_inner, font=('Segoe UI', 10), width=12,
                                     state='readonly')
        combo_estado['values'] = ['Todos', 'Pendiente', 'Parcial', 'Cobrada']
        combo_estado.set('Todos')
        combo_estado.pack(side='left', padx=5)

        tk.Label(filtro_inner, text="Paciente:", font=('Segoe UI', 10),
                 bg='white').pack(side='left', padx=(15, 5))
        entry_paciente = ttk.Entry(filtro_inner, font=('Segoe UI', 10), width=20)
        entry_paciente.pack(side='left', padx=5)

        var_vencidas = tk.BooleanVar()
        ttk.Checkbutton(filtro_inner, text="Solo vencidas", variable=var_vencidas).pack(
            side='left', padx=15)

        # Tabla
        columnas = ('ID', 'Factura', 'Paciente', 'F. Emision', 'F. Vencimiento',
                     'Monto', 'Cobrado', 'Saldo', 'Dias Venc.', 'Estado')
        anchos = (40, 80, 150, 90, 90, 90, 90, 90, 70, 80)
        tree = self._crear_tabla(main_frame, columnas, anchos)

        def cargar_datos():
            for item in tree.get_children():
                tree.delete(item)

            estado = combo_estado.get()
            estado = None if estado == 'Todos' else estado
            paciente = entry_paciente.get().strip() or None
            solo_vencidas = var_vencidas.get()

            cuentas = self.gestor_cxc.listar_cuentas(estado, paciente, solo_vencidas)
            for c in cuentas:
                dias = int(c.get('DiasVencida', 0) or 0)
                tag = 'vencida' if dias > 0 and c.get('Estado') != 'Cobrada' else ''
                monto_orig = float(c.get('MontoOriginal', 0) or 0)
                monto_cobrado = float(c.get('MontoCobrado', 0) or 0)
                saldo = float(c.get('SaldoPendiente', 0) or 0)

                fecha_e = c.get('FechaEmision', '')
                fecha_v = c.get('FechaVencimiento', '')
                try:
                    if isinstance(fecha_e, datetime):
                        fecha_e = fecha_e.strftime('%d/%m/%Y')
                    if isinstance(fecha_v, datetime):
                        fecha_v = fecha_v.strftime('%d/%m/%Y')
                except:
                    pass

                tree.insert('', 'end', iid=str(c.get('CuentaCobrarID', '')),
                            values=(
                                c.get('CuentaCobrarID', ''),
                                c.get('FacturaID', ''),
                                c.get('NombrePaciente', ''),
                                fecha_e,
                                fecha_v,
                                f"${monto_orig:,.2f}",
                                f"${monto_cobrado:,.2f}",
                                f"${saldo:,.2f}",
                                dias,
                                c.get('Estado', ''),
                            ), tags=(tag,) if tag else ())

        tk.Button(filtro_inner, text="🔍 Buscar", font=('Segoe UI', 10),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=10, pady=3,
                  cursor='hand2', command=cargar_datos).pack(side='left', padx=10)

        cargar_datos()

        # Botones
        if self._puede_registrar_movimientos():
            btn_frame = tk.Frame(main_frame, bg=COLORS['bg'])
            btn_frame.pack(fill='x', pady=10)

            def registrar_cobro():
                sel = tree.selection()
                if not sel:
                    messagebox.showwarning("Seleccione", "Seleccione una cuenta de la tabla.")
                    return
                cuenta_id = int(sel[0])
                cuenta = self.db.query_one(
                    f"SELECT * FROM [CuentasPorCobrar] WHERE CuentaCobrarID={cuenta_id}")
                if not cuenta:
                    messagebox.showerror("Error", "Cuenta no encontrada.")
                    return
                if cuenta.get('Estado') == 'Cobrada':
                    messagebox.showinfo("Info", "Esta cuenta ya esta totalmente cobrada.")
                    return

                formas = self._obtener_formas_pago()
                dialogo = DialogoRegistrarCobro(app.root, cuenta, formas)
                if dialogo.resultado:
                    exito, msg = self.gestor_cxc.registrar_cobro(
                        cuenta_id, dialogo.resultado['monto'],
                        dialogo.resultado['forma_pago_id'],
                        dialogo.resultado.get('referencia', ''))
                    if exito:
                        messagebox.showinfo("Exito", msg)
                        cargar_datos()
                    else:
                        messagebox.showerror("Error", msg)

            tk.Button(btn_frame, text="💵 Registrar Cobro", font=('Segoe UI', 11, 'bold'),
                      bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                      cursor='hand2', command=registrar_cobro).pack(side='left', padx=5)

    # ==================================================================
    # VISTA 4: CUENTAS POR PAGAR
    # ==================================================================
    def show_cuentas_pagar(self, app):
        if not self._puede_operar_caja():
            messagebox.showwarning("Acceso Denegado",
                                   "No tiene permisos para esta seccion.")
            return

        app.clear_content()
        app.set_title("📋 Cuentas por Pagar")
        scrollable = app.setup_scrollable_content()

        main_frame = tk.Frame(scrollable, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Resumen
        resumen_cxp = self.gestor_cxp.obtener_resumen()

        tk.Label(main_frame, text="Resumen", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', pady=(0, 5))

        cards_frame = tk.Frame(main_frame, bg=COLORS['bg'])
        cards_frame.pack(fill='x', pady=5)

        self._crear_tarjeta_kpi(cards_frame, "💰", "Total Pendiente",
                                resumen_cxp.get('total', 0), COLORS['warning'])
        self._crear_tarjeta_kpi(cards_frame, "📅", "Por Vencer",
                                resumen_cxp.get('por_vencer', 0), COLORS['primary'])
        self._crear_tarjeta_kpi(cards_frame, "⚠️", "Vencidas",
                                resumen_cxp.get('vencidas', 0), COLORS['danger'])
        self._crear_tarjeta_kpi(cards_frame, "#️⃣", "Cantidad",
                                resumen_cxp.get('cantidad', 0), COLORS['info'],
                                formato_moneda=False)

        # Filtros
        filtro_frame = tk.LabelFrame(main_frame, text="  Filtros  ", font=('Segoe UI', 10),
                                      bg='white', fg=COLORS['text'], padx=10, pady=8)
        filtro_frame.pack(fill='x', pady=10)

        filtro_inner = tk.Frame(filtro_frame, bg='white')
        filtro_inner.pack(fill='x')

        tk.Label(filtro_inner, text="Estado:", font=('Segoe UI', 10),
                 bg='white').pack(side='left', padx=(0, 5))
        combo_estado = ttk.Combobox(filtro_inner, font=('Segoe UI', 10), width=12,
                                     state='readonly')
        combo_estado['values'] = ['Todos', 'Pendiente', 'Parcial', 'Pagada']
        combo_estado.set('Todos')
        combo_estado.pack(side='left', padx=5)

        tk.Label(filtro_inner, text="Proveedor:", font=('Segoe UI', 10),
                 bg='white').pack(side='left', padx=(15, 5))
        entry_proveedor = ttk.Entry(filtro_inner, font=('Segoe UI', 10), width=20)
        entry_proveedor.pack(side='left', padx=5)

        # Tabla
        columnas = ('ID', 'Proveedor', 'RIF', 'Documento', 'F. Emision', 'Vencimiento',
                     'Monto', 'Pagado', 'Saldo', 'Estado')
        anchos = (40, 150, 90, 90, 90, 90, 90, 90, 90, 80)
        tree = self._crear_tabla(main_frame, columnas, anchos)

        def cargar_datos():
            for item in tree.get_children():
                tree.delete(item)

            estado = combo_estado.get()
            estado = None if estado == 'Todos' else estado
            proveedor = entry_proveedor.get().strip() or None

            cuentas = self.gestor_cxp.listar_cuentas(estado, proveedor)
            for c in cuentas:
                monto = float(c.get('MontoOriginal', 0) or 0)
                pagado = float(c.get('MontoPagado', 0) or 0)
                saldo = float(c.get('SaldoPendiente', 0) or 0)

                fecha_e = c.get('FechaEmision', '')
                fecha_v = c.get('FechaVencimiento', '')
                try:
                    if isinstance(fecha_e, datetime):
                        fecha_e = fecha_e.strftime('%d/%m/%Y')
                    if isinstance(fecha_v, datetime):
                        fecha_v = fecha_v.strftime('%d/%m/%Y')
                except:
                    pass

                tree.insert('', 'end', iid=str(c.get('CuentaPagarID', '')),
                            values=(
                                c.get('CuentaPagarID', ''),
                                c.get('ProveedorNombre', ''),
                                c.get('ProveedorRIF', ''),
                                c.get('NumeroDocumento', ''),
                                fecha_e, fecha_v,
                                f"${monto:,.2f}", f"${pagado:,.2f}",
                                f"${saldo:,.2f}",
                                c.get('Estado', ''),
                            ))

        tk.Button(filtro_inner, text="🔍 Buscar", font=('Segoe UI', 10),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=10, pady=3,
                  cursor='hand2', command=cargar_datos).pack(side='left', padx=10)

        cargar_datos()

        # Botones
        btn_frame = tk.Frame(main_frame, bg=COLORS['bg'])
        btn_frame.pack(fill='x', pady=10)

        def nueva_cxp():
            dialogo = DialogoNuevaCxP(app.root, self.db)
            if dialogo.resultado:
                exito, msg = self.gestor_cxp.crear_cuenta(dialogo.resultado)
                if exito:
                    messagebox.showinfo("Exito", msg)
                    cargar_datos()
                else:
                    messagebox.showerror("Error", msg)

        def registrar_pago():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Seleccione", "Seleccione una cuenta de la tabla.")
                return
            cuenta_id = int(sel[0])
            cuenta = self.db.query_one(
                f"SELECT * FROM [CuentasPorPagar] WHERE CuentaPagarID={cuenta_id}")
            if not cuenta:
                messagebox.showerror("Error", "Cuenta no encontrada.")
                return
            if cuenta.get('Estado') == 'Pagada':
                messagebox.showinfo("Info", "Esta cuenta ya esta totalmente pagada.")
                return

            formas = self._obtener_formas_pago()
            dialogo = DialogoRegistrarPago(app.root, cuenta, formas)
            if dialogo.resultado:
                exito, msg = self.gestor_cxp.registrar_pago(
                    cuenta_id, dialogo.resultado['monto'],
                    dialogo.resultado['forma_pago_id'],
                    dialogo.resultado.get('referencia', ''))
                if exito:
                    messagebox.showinfo("Exito", msg)
                    cargar_datos()
                else:
                    messagebox.showerror("Error", msg)

        tk.Button(btn_frame, text="➕ Nueva Cuenta por Pagar", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=nueva_cxp).pack(side='left', padx=5)

        tk.Button(btn_frame, text="💵 Registrar Pago", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=registrar_pago).pack(side='left', padx=5)

    # ==================================================================
    # VISTA 5: GASTOS
    # ==================================================================
    def show_gastos(self, app):
        if not self._puede_operar_caja():
            messagebox.showwarning("Acceso Denegado",
                                   "No tiene permisos para esta seccion.")
            return

        app.clear_content()
        app.set_title("💸 Control de Gastos")
        scrollable = app.setup_scrollable_content()

        main_frame = tk.Frame(scrollable, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True, padx=20, pady=10)

        # Filtros
        filtro_frame = tk.LabelFrame(main_frame, text="  Filtros  ", font=('Segoe UI', 10),
                                      bg='white', fg=COLORS['text'], padx=10, pady=8)
        filtro_frame.pack(fill='x', pady=(0, 10))

        filtro_inner = tk.Frame(filtro_frame, bg='white')
        filtro_inner.pack(fill='x')

        tk.Label(filtro_inner, text="Desde:", font=('Segoe UI', 10),
                 bg='white').pack(side='left', padx=(0, 5))
        entry_desde = ttk.Entry(filtro_inner, font=('Segoe UI', 10), width=12)
        entry_desde.pack(side='left', padx=5)
        entry_desde.insert(0, datetime.now().strftime('%d/%m/%Y'))

        tk.Label(filtro_inner, text="Hasta:", font=('Segoe UI', 10),
                 bg='white').pack(side='left', padx=(10, 5))
        entry_hasta = ttk.Entry(filtro_inner, font=('Segoe UI', 10), width=12)
        entry_hasta.pack(side='left', padx=5)
        entry_hasta.insert(0, datetime.now().strftime('%d/%m/%Y'))

        tk.Label(filtro_inner, text="Categoria:", font=('Segoe UI', 10),
                 bg='white').pack(side='left', padx=(10, 5))
        categorias = self._obtener_categorias()
        nombres_cat = ['Todas'] + [c.get('Nombre', '') for c in categorias]
        combo_cat = ttk.Combobox(filtro_inner, font=('Segoe UI', 10), width=18,
                                  state='readonly', values=nombres_cat)
        combo_cat.set('Todas')
        combo_cat.pack(side='left', padx=5)

        # Tabla
        columnas = ('ID', 'Fecha', 'Categoria', 'Descripcion', 'Monto',
                     'Forma Pago', 'Referencia', 'Beneficiario')
        anchos = (40, 90, 120, 180, 90, 100, 90, 130)
        tree = self._crear_tabla(main_frame, columnas, anchos)

        def cargar_datos():
            for item in tree.get_children():
                tree.delete(item)

            # Parsear fechas
            fecha_desde = None
            fecha_hasta = None
            try:
                fd = entry_desde.get().strip()
                if fd:
                    parts = fd.split('/')
                    fecha_desde = f"{parts[1]}/{parts[0]}/{parts[2]}"
            except:
                pass
            try:
                fh = entry_hasta.get().strip()
                if fh:
                    parts = fh.split('/')
                    fecha_hasta = f"{parts[1]}/{parts[0]}/{parts[2]}"
            except:
                pass

            cat_sel = combo_cat.get()
            cat_id = None
            if cat_sel != 'Todas':
                for c in categorias:
                    if c.get('Nombre') == cat_sel:
                        cat_id = c.get('CategoriaID')
                        break

            gastos = self.gestor_gastos.listar_gastos(fecha_desde, fecha_hasta, cat_id)
            for g in gastos:
                fecha = g.get('Fecha', '')
                try:
                    if isinstance(fecha, datetime):
                        fecha = fecha.strftime('%d/%m/%Y')
                except:
                    pass

                monto = float(g.get('Monto', 0) or 0)
                tree.insert('', 'end', iid=str(g.get('GastoID', '')),
                            values=(
                                g.get('GastoID', ''),
                                fecha,
                                g.get('CategoriaGasto', ''),
                                g.get('Descripcion', ''),
                                f"${monto:,.2f}",
                                g.get('FormaPago', ''),
                                g.get('Referencia', ''),
                                g.get('BeneficiarioNombre', ''),
                            ))

        tk.Button(filtro_inner, text="🔍 Filtrar", font=('Segoe UI', 10),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=10, pady=3,
                  cursor='hand2', command=cargar_datos).pack(side='left', padx=10)

        cargar_datos()

        # Botones
        btn_frame = tk.Frame(main_frame, bg=COLORS['bg'])
        btn_frame.pack(fill='x', pady=10)

        def nuevo_gasto():
            dialogo = DialogoNuevoGasto(app.root, self.db, self.user.get('UsuarioID', 1))
            if dialogo.resultado:
                exito, msg = self.gestor_gastos.registrar_gasto(
                    dialogo.resultado, self.user.get('UsuarioID', 1))
                if exito:
                    messagebox.showinfo("Exito", msg)
                    cargar_datos()
                else:
                    messagebox.showerror("Error", msg)

        def anular_gasto():
            sel = tree.selection()
            if not sel:
                messagebox.showwarning("Seleccione", "Seleccione un gasto de la tabla.")
                return
            gasto_id = int(sel[0])

            motivo = _pedir_texto(app.root, "Motivo de Anulacion",
                                  "Ingrese el motivo de la anulacion:")
            if motivo:
                exito, msg = self.gestor_gastos.anular_gasto(gasto_id, motivo)
                if exito:
                    messagebox.showinfo("Exito", msg)
                    cargar_datos()
                else:
                    messagebox.showerror("Error", msg)

        tk.Button(btn_frame, text="➕ Nuevo Gasto", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=nuevo_gasto).pack(side='left', padx=5)

        tk.Button(btn_frame, text="🚫 Anular Gasto", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['danger'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=anular_gasto).pack(side='left', padx=5)

        # Resumen por categoria
        tk.Label(main_frame, text="Resumen por Categoria", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['bg'], fg=COLORS['text']).pack(anchor='w', pady=(15, 5))

        resumen_cat = self.gestor_gastos.resumen_gastos_por_categoria()
        if resumen_cat:
            cols_r = ('Categoria', 'Total', 'Cantidad')
            tree_r = self._crear_tabla(main_frame, cols_r, (200, 150, 100))
            tree_r.configure(height=6)
            for r in resumen_cat:
                nombre = r.get('Nombre', 'Sin categoria') or 'Sin categoria'
                total = float(r.get('Total', 0) or 0)
                cant = int(r.get('Cantidad', 0) or 0)
                tree_r.insert('', 'end', values=(nombre, f"${total:,.2f}", cant))
        else:
            tk.Label(main_frame, text="Sin gastos registrados",
                     font=('Segoe UI', 10), bg=COLORS['bg'],
                     fg=COLORS['text_light']).pack(anchor='w', padx=10)


# ======================================================================
# DIALOGOS MODALES
# ======================================================================

def _pedir_texto(parent, titulo, mensaje):
    """Dialogo simple para pedir un texto al usuario."""
    resultado = [None]
    dialog = tk.Toplevel(parent)
    dialog.title(titulo)
    dialog.configure(bg='white')
    dialog.grab_set()
    dialog.focus_set()

    ancho, alto = 400, 200
    x = (dialog.winfo_screenwidth() - ancho) // 2
    y = (dialog.winfo_screenheight() - alto) // 2
    dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
    dialog.resizable(False, False)

    tk.Label(dialog, text=mensaje, font=('Segoe UI', 11), bg='white',
             wraplength=360).pack(padx=20, pady=(20, 10))

    entry = ttk.Entry(dialog, font=('Segoe UI', 11), width=40)
    entry.pack(padx=20, pady=5)
    entry.focus_set()

    btn_frame = tk.Frame(dialog, bg='white')
    btn_frame.pack(pady=15)

    def aceptar():
        resultado[0] = entry.get().strip()
        dialog.destroy()

    tk.Button(btn_frame, text="Aceptar", font=('Segoe UI', 10), bg=COLORS['primary'],
              fg='white', relief='flat', padx=15, pady=5, command=aceptar).pack(side='left', padx=5)
    tk.Button(btn_frame, text="Cancelar", font=('Segoe UI', 10), bg=COLORS['text_light'],
              fg='white', relief='flat', padx=15, pady=5,
              command=dialog.destroy).pack(side='left', padx=5)

    dialog.wait_window()
    return resultado[0]


class DialogoMovimientoCaja:
    """Dialogo para registrar un ingreso o egreso en caja."""

    def __init__(self, parent, db, tipo='Ingreso'):
        self.resultado = None
        self.db = db
        self.tipo = tipo

        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Registrar {tipo}")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        ancho, alto = 480, 450
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

        self._crear_ui()
        self.dialog.wait_window()

    def _crear_ui(self):
        color_header = COLORS['success'] if self.tipo == 'Ingreso' else COLORS['danger']

        header = tk.Frame(self.dialog, bg=color_header, height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text=f"{'➕' if self.tipo == 'Ingreso' else '➖'} Registrar {self.tipo}",
                 font=('Segoe UI', 13, 'bold'), bg=color_header, fg='white').pack(pady=12)

        content = tk.Frame(self.dialog, bg='white')
        content.pack(fill='both', expand=True, padx=25, pady=15)

        # Monto
        tk.Label(content, text="Monto ($):", font=('Segoe UI', 11), bg='white').pack(
            anchor='w', pady=(0, 3))
        self.entry_monto = ttk.Entry(content, font=('Segoe UI', 12), width=20)
        self.entry_monto.pack(anchor='w', pady=(0, 10))
        self.entry_monto.focus_set()

        # Forma de pago
        tk.Label(content, text="Forma de Pago:", font=('Segoe UI', 11), bg='white').pack(
            anchor='w', pady=(0, 3))
        formas = []
        self.formas_map = {}
        try:
            fp_list = self.db.query("SELECT * FROM [FormasPago] WHERE Activo=True ORDER BY Nombre")
            for fp in fp_list:
                nombre = fp.get('Nombre', '')
                formas.append(nombre)
                self.formas_map[nombre] = fp.get('FormaPagoID')
        except:
            formas = ['Efectivo', 'Transferencia', 'Punto de Venta']

        self.combo_pago = ttk.Combobox(content, font=('Segoe UI', 11), width=25,
                                        state='readonly', values=formas)
        if formas:
            self.combo_pago.set(formas[0])
        self.combo_pago.pack(anchor='w', pady=(0, 10))

        # Referencia
        tk.Label(content, text="Referencia:", font=('Segoe UI', 11), bg='white').pack(
            anchor='w', pady=(0, 3))
        self.entry_ref = ttk.Entry(content, font=('Segoe UI', 11), width=30)
        self.entry_ref.pack(anchor='w', pady=(0, 10))

        # Categoria
        tk.Label(content, text="Categoria:", font=('Segoe UI', 11), bg='white').pack(
            anchor='w', pady=(0, 3))
        if self.tipo == 'Ingreso':
            cats = ['Pago de solicitud', 'Cobro de factura', 'Abono a cuenta', 'Otro ingreso']
        else:
            cats = []
            try:
                cat_list = self.db.query(
                    "SELECT Nombre FROM [CategoriaGastos] WHERE Activo=True ORDER BY Nombre")
                cats = [c.get('Nombre', '') for c in cat_list]
            except:
                cats = ['Material', 'Servicios', 'Otros']

        self.combo_cat = ttk.Combobox(content, font=('Segoe UI', 11), width=25,
                                       state='readonly', values=cats)
        if cats:
            self.combo_cat.set(cats[0])
        self.combo_cat.pack(anchor='w', pady=(0, 10))

        # Descripcion
        tk.Label(content, text="Descripcion:", font=('Segoe UI', 11), bg='white').pack(
            anchor='w', pady=(0, 3))
        self.entry_desc = ttk.Entry(content, font=('Segoe UI', 11), width=35)
        self.entry_desc.pack(anchor='w', pady=(0, 10))

        # Botones
        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=15)

        tk.Button(btn_frame, text="✅ Guardar", font=('Segoe UI', 11, 'bold'),
                  bg=color_header, fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self._guardar).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                  bg=COLORS['text_light'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self.dialog.destroy).pack(side='right', padx=5)

    def _guardar(self):
        try:
            monto = float(self.entry_monto.get().replace(',', ''))
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto valido.", parent=self.dialog)
            return
        if monto <= 0:
            messagebox.showerror("Error", "El monto debe ser mayor a cero.", parent=self.dialog)
            return

        forma_pago = self.combo_pago.get()
        forma_pago_id = self.formas_map.get(forma_pago, 'Null')

        self.resultado = {
            'Tipo': self.tipo,
            'Monto': monto,
            'FormaPagoID': forma_pago_id,
            'Referencia': self.entry_ref.get().strip(),
            'Categoria': self.combo_cat.get(),
            'Descripcion': self.entry_desc.get().strip(),
        }
        self.dialog.destroy()


class DialogoCierreCaja:
    """Dialogo para cerrar la caja con cuadre."""

    def __init__(self, parent, caja, resumen):
        self.resultado = None
        self.caja = caja

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Cerrar Caja")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        ancho, alto = 500, 520
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

        self._crear_ui(resumen)
        self.dialog.wait_window()

    def _crear_ui(self, resumen):
        header = tk.Frame(self.dialog, bg=COLORS['warning'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="🔒 Cierre de Caja", font=('Segoe UI', 13, 'bold'),
                 bg=COLORS['warning'], fg='white').pack(pady=12)

        content = tk.Frame(self.dialog, bg='white')
        content.pack(fill='both', expand=True, padx=25, pady=15)

        efectivo_inicial = float(self.caja.get('EfectivoInicial', 0) or 0)
        total_ingresos = float(self.caja.get('TotalIngresos', 0) or 0)
        total_egresos = float(self.caja.get('TotalEgresos', 0) or 0)
        self.esperado = efectivo_inicial + total_ingresos - total_egresos

        # Resumen
        resumen_frame = tk.LabelFrame(content, text="  Resumen del Dia  ",
                                       font=('Segoe UI', 10, 'bold'), bg='white',
                                       fg=COLORS['text'], padx=15, pady=10)
        resumen_frame.pack(fill='x', pady=(0, 10))

        datos = [
            ("Efectivo Inicial:", f"${efectivo_inicial:,.2f}"),
            ("Total Ingresos:", f"${total_ingresos:,.2f}"),
            ("Total Egresos:", f"${total_egresos:,.2f}"),
            ("Efectivo Esperado:", f"${self.esperado:,.2f}"),
        ]
        for label, valor in datos:
            row = tk.Frame(resumen_frame, bg='white')
            row.pack(fill='x', pady=2)
            tk.Label(row, text=label, font=('Segoe UI', 10), bg='white',
                     width=18, anchor='w').pack(side='left')
            tk.Label(row, text=valor, font=('Segoe UI', 10, 'bold'), bg='white',
                     anchor='e').pack(side='right')

        # Desglose por forma de pago
        desglose = resumen.get('desglose', [])
        if desglose:
            desg_frame = tk.LabelFrame(content, text="  Desglose por Forma de Pago  ",
                                        font=('Segoe UI', 9), bg='white',
                                        fg=COLORS['text_light'], padx=10, pady=5)
            desg_frame.pack(fill='x', pady=(0, 10))
            for d in desglose:
                nombre = d.get('Nombre', 'N/A') or 'N/A'
                tipo = d.get('Tipo', '')
                total = float(d.get('Total', 0) or 0)
                row = tk.Frame(desg_frame, bg='white')
                row.pack(fill='x', pady=1)
                tk.Label(row, text=f"{nombre} ({tipo}):", font=('Segoe UI', 9),
                         bg='white', anchor='w').pack(side='left')
                tk.Label(row, text=f"${total:,.2f}", font=('Segoe UI', 9, 'bold'),
                         bg='white', anchor='e').pack(side='right')

        # Efectivo final
        ef_frame = tk.Frame(content, bg='white')
        ef_frame.pack(fill='x', pady=10)
        tk.Label(ef_frame, text="Efectivo Final ($):", font=('Segoe UI', 11, 'bold'),
                 bg='white').pack(anchor='w')
        self.entry_efectivo = ttk.Entry(ef_frame, font=('Segoe UI', 14), width=20)
        self.entry_efectivo.pack(anchor='w', pady=5)
        self.entry_efectivo.focus_set()

        # Diferencia (auto-calculo)
        self.lbl_diferencia = tk.Label(content, text="Diferencia: $0.00",
                                        font=('Segoe UI', 12, 'bold'), bg='white',
                                        fg=COLORS['text'])
        self.lbl_diferencia.pack(anchor='w', pady=5)

        def calcular_diferencia(*args):
            try:
                ef = float(self.entry_efectivo.get().replace(',', ''))
                dif = ef - self.esperado
                color = COLORS['success'] if abs(dif) < 0.01 else (
                    COLORS['danger'] if dif < 0 else COLORS['warning'])
                self.lbl_diferencia.config(text=f"Diferencia: ${dif:,.2f}", fg=color)
            except:
                self.lbl_diferencia.config(text="Diferencia: ---", fg=COLORS['text_light'])

        self.entry_efectivo.bind('<KeyRelease>', calcular_diferencia)

        # Observaciones
        tk.Label(content, text="Observaciones:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(5, 3))
        self.txt_obs = tk.Text(content, font=('Segoe UI', 10), height=3, width=40,
                                relief='solid', borderwidth=1)
        self.txt_obs.pack(fill='x', pady=(0, 5))

        # Botones
        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=15)

        tk.Button(btn_frame, text="🔒 Cerrar Caja", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['warning'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self._cerrar).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                  bg=COLORS['text_light'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self.dialog.destroy).pack(side='right', padx=5)

    def _cerrar(self):
        try:
            efectivo_final = float(self.entry_efectivo.get().replace(',', ''))
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto valido.", parent=self.dialog)
            return

        dif = efectivo_final - self.esperado
        if abs(dif) > 0.01:
            if not messagebox.askyesno("Confirmar",
                                        f"La caja tiene una diferencia de ${dif:,.2f}.\n"
                                        f"¿Desea cerrar de todas formas?",
                                        parent=self.dialog):
                return

        self.resultado = {
            'efectivo_final': efectivo_final,
            'observaciones': self.txt_obs.get('1.0', 'end-1c').strip(),
        }
        self.dialog.destroy()


class DialogoRegistrarCobro:
    """Dialogo para registrar cobro de cuenta por cobrar."""

    def __init__(self, parent, cuenta, formas_pago):
        self.resultado = None
        self.cuenta = cuenta

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Registrar Cobro")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        ancho, alto = 450, 380
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

        self._crear_ui(formas_pago)
        self.dialog.wait_window()

    def _crear_ui(self, formas_pago):
        header = tk.Frame(self.dialog, bg=COLORS['success'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="💵 Registrar Cobro", font=('Segoe UI', 13, 'bold'),
                 bg=COLORS['success'], fg='white').pack(pady=12)

        content = tk.Frame(self.dialog, bg='white')
        content.pack(fill='both', expand=True, padx=25, pady=15)

        paciente = self.cuenta.get('NombrePaciente', 'N/A')
        saldo = float(self.cuenta.get('SaldoPendiente', 0) or 0)

        tk.Label(content, text=f"Paciente: {paciente}", font=('Segoe UI', 10),
                 bg='white', fg=COLORS['text']).pack(anchor='w', pady=3)
        tk.Label(content, text=f"Saldo Pendiente: ${saldo:,.2f}",
                 font=('Segoe UI', 12, 'bold'), bg='white', fg=COLORS['warning']).pack(
            anchor='w', pady=(3, 15))

        tk.Label(content, text="Monto a Cobrar ($):", font=('Segoe UI', 11),
                 bg='white').pack(anchor='w', pady=(0, 3))
        self.entry_monto = ttk.Entry(content, font=('Segoe UI', 12), width=20)
        self.entry_monto.pack(anchor='w', pady=(0, 10))
        self.entry_monto.insert(0, f"{saldo:.2f}")
        self.entry_monto.focus_set()

        tk.Label(content, text="Forma de Pago:", font=('Segoe UI', 11),
                 bg='white').pack(anchor='w', pady=(0, 3))

        nombres_fp = [f.get('Nombre', '') for f in formas_pago]
        self.formas_map = {f.get('Nombre', ''): f.get('FormaPagoID') for f in formas_pago}
        self.combo_pago = ttk.Combobox(content, font=('Segoe UI', 11), width=25,
                                        state='readonly', values=nombres_fp)
        if nombres_fp:
            self.combo_pago.set(nombres_fp[0])
        self.combo_pago.pack(anchor='w', pady=(0, 10))

        tk.Label(content, text="Referencia:", font=('Segoe UI', 11),
                 bg='white').pack(anchor='w', pady=(0, 3))
        self.entry_ref = ttk.Entry(content, font=('Segoe UI', 11), width=30)
        self.entry_ref.pack(anchor='w', pady=(0, 10))

        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=15)

        tk.Button(btn_frame, text="✅ Cobrar", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self._guardar).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                  bg=COLORS['text_light'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self.dialog.destroy).pack(side='right', padx=5)

    def _guardar(self):
        try:
            monto = float(self.entry_monto.get().replace(',', ''))
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto valido.", parent=self.dialog)
            return

        saldo = float(self.cuenta.get('SaldoPendiente', 0) or 0)
        if monto <= 0:
            messagebox.showerror("Error", "El monto debe ser mayor a cero.", parent=self.dialog)
            return
        if monto > saldo:
            messagebox.showerror("Error",
                                  f"El monto (${monto:,.2f}) excede el saldo (${saldo:,.2f}).",
                                  parent=self.dialog)
            return

        forma = self.combo_pago.get()
        self.resultado = {
            'monto': monto,
            'forma_pago_id': self.formas_map.get(forma, 1),
            'referencia': self.entry_ref.get().strip(),
        }
        self.dialog.destroy()


class DialogoNuevaCxP:
    """Dialogo para crear nueva cuenta por pagar."""

    def __init__(self, parent, db):
        self.resultado = None
        self.db = db

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Nueva Cuenta por Pagar")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        ancho, alto = 500, 520
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

        self._crear_ui()
        self.dialog.wait_window()

    def _crear_ui(self):
        header = tk.Frame(self.dialog, bg=COLORS['primary'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="➕ Nueva Cuenta por Pagar", font=('Segoe UI', 13, 'bold'),
                 bg=COLORS['primary'], fg='white').pack(pady=12)

        content = tk.Frame(self.dialog, bg='white')
        content.pack(fill='both', expand=True, padx=25, pady=15)

        campos = [
            ("Proveedor:", 'proveedor', 30),
            ("RIF Proveedor:", 'rif', 15),
            ("Nro. Documento:", 'documento', 20),
            ("Monto ($):", 'monto', 15),
            ("Dias Vencimiento:", 'dias_venc', 10),
        ]

        self.entries = {}
        for label, key, width in campos:
            tk.Label(content, text=label, font=('Segoe UI', 10), bg='white').pack(
                anchor='w', pady=(5, 2))
            entry = ttk.Entry(content, font=('Segoe UI', 11), width=width)
            entry.pack(anchor='w', pady=(0, 5))
            self.entries[key] = entry

        self.entries['dias_venc'].insert(0, "30")

        # Categoria
        tk.Label(content, text="Categoria:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(5, 2))
        cats = []
        self.cat_map = {}
        try:
            cat_list = self.db.query(
                "SELECT CategoriaID, Nombre FROM [CategoriaGastos] WHERE Activo=True ORDER BY Nombre")
            for c in cat_list:
                cats.append(c.get('Nombre', ''))
                self.cat_map[c.get('Nombre', '')] = c.get('CategoriaID')
        except:
            cats = ['Otros']

        self.combo_cat = ttk.Combobox(content, font=('Segoe UI', 11), width=25,
                                       state='readonly', values=cats)
        if cats:
            self.combo_cat.set(cats[0])
        self.combo_cat.pack(anchor='w', pady=(0, 5))

        # Observaciones
        tk.Label(content, text="Observaciones:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(5, 2))
        self.txt_obs = tk.Text(content, font=('Segoe UI', 10), height=2, width=40,
                                relief='solid', borderwidth=1)
        self.txt_obs.pack(fill='x', pady=(0, 5))

        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=15)

        tk.Button(btn_frame, text="✅ Guardar", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self._guardar).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                  bg=COLORS['text_light'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self.dialog.destroy).pack(side='right', padx=5)

    def _guardar(self):
        proveedor = self.entries['proveedor'].get().strip()
        if not proveedor:
            messagebox.showerror("Error", "Ingrese el nombre del proveedor.", parent=self.dialog)
            return

        try:
            monto = float(self.entries['monto'].get().replace(',', ''))
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto valido.", parent=self.dialog)
            return
        if monto <= 0:
            messagebox.showerror("Error", "El monto debe ser mayor a cero.", parent=self.dialog)
            return

        try:
            dias = int(self.entries['dias_venc'].get())
        except ValueError:
            dias = 30

        cat_sel = self.combo_cat.get()
        cat_id = self.cat_map.get(cat_sel)

        self.resultado = {
            'ProveedorNombre': proveedor,
            'ProveedorRIF': self.entries['rif'].get().strip(),
            'NumeroDocumento': self.entries['documento'].get().strip(),
            'MontoOriginal': monto,
            'DiasVencimiento': dias,
            'CategoriaGastoID': cat_id,
            'Observaciones': self.txt_obs.get('1.0', 'end-1c').strip(),
        }
        self.dialog.destroy()


class DialogoRegistrarPago:
    """Dialogo para registrar pago a cuenta por pagar."""

    def __init__(self, parent, cuenta, formas_pago):
        self.resultado = None
        self.cuenta = cuenta

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Registrar Pago")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        ancho, alto = 450, 380
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

        self._crear_ui(formas_pago)
        self.dialog.wait_window()

    def _crear_ui(self, formas_pago):
        header = tk.Frame(self.dialog, bg=COLORS['success'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="💵 Registrar Pago", font=('Segoe UI', 13, 'bold'),
                 bg=COLORS['success'], fg='white').pack(pady=12)

        content = tk.Frame(self.dialog, bg='white')
        content.pack(fill='both', expand=True, padx=25, pady=15)

        proveedor = self.cuenta.get('ProveedorNombre', 'N/A')
        saldo = float(self.cuenta.get('SaldoPendiente', 0) or 0)

        tk.Label(content, text=f"Proveedor: {proveedor}", font=('Segoe UI', 10),
                 bg='white', fg=COLORS['text']).pack(anchor='w', pady=3)
        tk.Label(content, text=f"Saldo Pendiente: ${saldo:,.2f}",
                 font=('Segoe UI', 12, 'bold'), bg='white', fg=COLORS['warning']).pack(
            anchor='w', pady=(3, 15))

        tk.Label(content, text="Monto a Pagar ($):", font=('Segoe UI', 11),
                 bg='white').pack(anchor='w', pady=(0, 3))
        self.entry_monto = ttk.Entry(content, font=('Segoe UI', 12), width=20)
        self.entry_monto.pack(anchor='w', pady=(0, 10))
        self.entry_monto.insert(0, f"{saldo:.2f}")
        self.entry_monto.focus_set()

        tk.Label(content, text="Forma de Pago:", font=('Segoe UI', 11),
                 bg='white').pack(anchor='w', pady=(0, 3))

        nombres_fp = [f.get('Nombre', '') for f in formas_pago]
        self.formas_map = {f.get('Nombre', ''): f.get('FormaPagoID') for f in formas_pago}
        self.combo_pago = ttk.Combobox(content, font=('Segoe UI', 11), width=25,
                                        state='readonly', values=nombres_fp)
        if nombres_fp:
            self.combo_pago.set(nombres_fp[0])
        self.combo_pago.pack(anchor='w', pady=(0, 10))

        tk.Label(content, text="Referencia:", font=('Segoe UI', 11),
                 bg='white').pack(anchor='w', pady=(0, 3))
        self.entry_ref = ttk.Entry(content, font=('Segoe UI', 11), width=30)
        self.entry_ref.pack(anchor='w', pady=(0, 10))

        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=15)

        tk.Button(btn_frame, text="✅ Pagar", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self._guardar).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                  bg=COLORS['text_light'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self.dialog.destroy).pack(side='right', padx=5)

    def _guardar(self):
        try:
            monto = float(self.entry_monto.get().replace(',', ''))
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto valido.", parent=self.dialog)
            return

        saldo = float(self.cuenta.get('SaldoPendiente', 0) or 0)
        if monto <= 0:
            messagebox.showerror("Error", "El monto debe ser mayor a cero.", parent=self.dialog)
            return
        if monto > saldo:
            messagebox.showerror("Error",
                                  f"El monto (${monto:,.2f}) excede el saldo (${saldo:,.2f}).",
                                  parent=self.dialog)
            return

        forma = self.combo_pago.get()
        self.resultado = {
            'monto': monto,
            'forma_pago_id': self.formas_map.get(forma, 1),
            'referencia': self.entry_ref.get().strip(),
        }
        self.dialog.destroy()


class DialogoNuevoGasto:
    """Dialogo para registrar un nuevo gasto."""

    def __init__(self, parent, db, usuario_id):
        self.resultado = None
        self.db = db
        self.usuario_id = usuario_id

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Nuevo Gasto")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        ancho, alto = 500, 520
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

        self._crear_ui()
        self.dialog.wait_window()

    def _crear_ui(self):
        header = tk.Frame(self.dialog, bg=COLORS['danger'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="💸 Registrar Gasto", font=('Segoe UI', 13, 'bold'),
                 bg=COLORS['danger'], fg='white').pack(pady=12)

        content = tk.Frame(self.dialog, bg='white')
        content.pack(fill='both', expand=True, padx=25, pady=15)

        # Categoria
        tk.Label(content, text="Categoria:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(0, 2))
        cats = []
        self.cat_map = {}
        try:
            cat_list = self.db.query(
                "SELECT CategoriaID, Nombre FROM [CategoriaGastos] WHERE Activo=True ORDER BY Nombre")
            for c in cat_list:
                cats.append(c.get('Nombre', ''))
                self.cat_map[c.get('Nombre', '')] = c.get('CategoriaID')
        except:
            cats = ['Otros']

        self.combo_cat = ttk.Combobox(content, font=('Segoe UI', 11), width=25,
                                       state='readonly', values=cats)
        if cats:
            self.combo_cat.set(cats[0])
        self.combo_cat.pack(anchor='w', pady=(0, 8))

        # Descripcion
        tk.Label(content, text="Descripcion:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(0, 2))
        self.entry_desc = ttk.Entry(content, font=('Segoe UI', 11), width=35)
        self.entry_desc.pack(anchor='w', pady=(0, 8))

        # Monto
        tk.Label(content, text="Monto ($):", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(0, 2))
        self.entry_monto = ttk.Entry(content, font=('Segoe UI', 12), width=15)
        self.entry_monto.pack(anchor='w', pady=(0, 8))
        self.entry_monto.focus_set()

        # Forma de pago
        tk.Label(content, text="Forma de Pago:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(0, 2))
        formas = []
        self.formas_map = {}
        try:
            fp_list = self.db.query("SELECT * FROM [FormasPago] WHERE Activo=True ORDER BY Nombre")
            for fp in fp_list:
                nombre = fp.get('Nombre', '')
                formas.append(nombre)
                self.formas_map[nombre] = fp.get('FormaPagoID')
        except:
            formas = ['Efectivo']

        self.combo_pago = ttk.Combobox(content, font=('Segoe UI', 11), width=25,
                                        state='readonly', values=formas)
        if formas:
            self.combo_pago.set(formas[0])
        self.combo_pago.pack(anchor='w', pady=(0, 8))

        # Referencia
        tk.Label(content, text="Referencia:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(0, 2))
        self.entry_ref = ttk.Entry(content, font=('Segoe UI', 11), width=25)
        self.entry_ref.pack(anchor='w', pady=(0, 8))

        # Beneficiario
        tk.Label(content, text="Beneficiario:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(0, 2))
        self.entry_benef = ttk.Entry(content, font=('Segoe UI', 11), width=30)
        self.entry_benef.pack(anchor='w', pady=(0, 5))

        tk.Label(content, text="RIF Beneficiario:", font=('Segoe UI', 10), bg='white').pack(
            anchor='w', pady=(0, 2))
        self.entry_rif = ttk.Entry(content, font=('Segoe UI', 11), width=15)
        self.entry_rif.pack(anchor='w', pady=(0, 5))

        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=25, pady=15)

        tk.Button(btn_frame, text="✅ Guardar", font=('Segoe UI', 11, 'bold'),
                  bg=COLORS['danger'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self._guardar).pack(side='left', padx=5)
        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                  bg=COLORS['text_light'], fg='white', relief='flat', padx=20, pady=8,
                  cursor='hand2', command=self.dialog.destroy).pack(side='right', padx=5)

    def _guardar(self):
        try:
            monto = float(self.entry_monto.get().replace(',', ''))
        except ValueError:
            messagebox.showerror("Error", "Ingrese un monto valido.", parent=self.dialog)
            return
        if monto <= 0:
            messagebox.showerror("Error", "El monto debe ser mayor a cero.", parent=self.dialog)
            return

        cat_sel = self.combo_cat.get()
        forma = self.combo_pago.get()

        self.resultado = {
            'CategoriaGastoID': self.cat_map.get(cat_sel),
            'Descripcion': self.entry_desc.get().strip(),
            'Monto': monto,
            'FormaPagoID': self.formas_map.get(forma, 1),
            'Referencia': self.entry_ref.get().strip(),
            'BeneficiarioNombre': self.entry_benef.get().strip(),
            'BeneficiarioRIF': self.entry_rif.get().strip(),
        }
        self.dialog.destroy()


# ======================================================================
# FUNCION FACTORY
# ======================================================================

def _inicializar_tablas_administrativas(db):
    """Crea las tablas administrativas si no existen (auto-migracion)."""

    def _tabla_existe(nombre):
        try:
            db.query(f"SELECT TOP 1 * FROM [{nombre}]")
            return True
        except:
            return False

    tablas = [
        ('Roles', """
            CREATE TABLE Roles (
                RolID AUTOINCREMENT PRIMARY KEY,
                NombreRol TEXT(50) NOT NULL,
                Descripcion TEXT(200),
                NivelAcceso INTEGER DEFAULT 0,
                Activo YESNO DEFAULT TRUE
            )
        """),
        ('PermisosModulo', """
            CREATE TABLE PermisosModulo (
                PermisoID AUTOINCREMENT PRIMARY KEY,
                RolID INTEGER NOT NULL,
                NombreModulo TEXT(50) NOT NULL,
                PuedeVer YESNO DEFAULT FALSE,
                PuedeCrear YESNO DEFAULT FALSE,
                PuedeEditar YESNO DEFAULT FALSE,
                PuedeEliminar YESNO DEFAULT FALSE,
                PuedeExportar YESNO DEFAULT FALSE
            )
        """),
        ('UsuarioRol', """
            CREATE TABLE UsuarioRol (
                UsuarioRolID AUTOINCREMENT PRIMARY KEY,
                UsuarioID INTEGER NOT NULL,
                RolID INTEGER NOT NULL,
                Activo YESNO DEFAULT TRUE
            )
        """),
        ('FormasPago', """
            CREATE TABLE FormasPago (
                FormaPagoID AUTOINCREMENT PRIMARY KEY,
                Nombre TEXT(50) NOT NULL,
                Activo YESNO DEFAULT TRUE,
                RequiereBanco YESNO DEFAULT FALSE,
                RequiereReferencia YESNO DEFAULT FALSE
            )
        """),
        ('Bancos', """
            CREATE TABLE Bancos (
                BancoID AUTOINCREMENT PRIMARY KEY,
                Nombre TEXT(100) NOT NULL,
                Codigo TEXT(10),
                Activo YESNO DEFAULT TRUE
            )
        """),
        ('CuentasBancarias', """
            CREATE TABLE CuentasBancarias (
                CuentaID AUTOINCREMENT PRIMARY KEY,
                BancoID INTEGER NOT NULL,
                NumeroCuenta TEXT(30),
                TipoCuenta TEXT(20),
                Titular TEXT(200),
                SaldoActual CURRENCY DEFAULT 0,
                Activo YESNO DEFAULT TRUE
            )
        """),
        ('CategoriaGastos', """
            CREATE TABLE CategoriaGastos (
                CategoriaID AUTOINCREMENT PRIMARY KEY,
                Nombre TEXT(100) NOT NULL,
                Descripcion TEXT(200),
                Activo YESNO DEFAULT TRUE
            )
        """),
        ('CajaChica', """
            CREATE TABLE CajaChica (
                CajaID AUTOINCREMENT PRIMARY KEY,
                FechaApertura DATETIME,
                FechaCierre DATETIME,
                MontoApertura CURRENCY DEFAULT 0,
                EfectivoInicial CURRENCY DEFAULT 0,
                EfectivoFinal CURRENCY DEFAULT 0,
                TotalIngresos CURRENCY DEFAULT 0,
                TotalEgresos CURRENCY DEFAULT 0,
                Diferencia CURRENCY DEFAULT 0,
                Estado TEXT(20) DEFAULT 'Abierta',
                UsuarioApertura INTEGER,
                UsuarioCierre INTEGER,
                Observaciones MEMO
            )
        """),
        ('MovimientosCaja', """
            CREATE TABLE MovimientosCaja (
                MovimientoID AUTOINCREMENT PRIMARY KEY,
                CajaID INTEGER NOT NULL,
                Fecha DATETIME,
                Tipo TEXT(10) NOT NULL,
                Categoria TEXT(100),
                Descripcion TEXT(200),
                Monto CURRENCY DEFAULT 0,
                FormaPagoID INTEGER,
                Referencia TEXT(50),
                FacturaID INTEGER,
                UsuarioID INTEGER,
                Anulado YESNO DEFAULT FALSE,
                MotivoAnulacion TEXT(200)
            )
        """),
        ('CuentasPorCobrar', """
            CREATE TABLE CuentasPorCobrar (
                CuentaCobrarID AUTOINCREMENT PRIMARY KEY,
                FacturaID INTEGER,
                PacienteID INTEGER,
                NombrePaciente TEXT(200),
                FechaEmision DATETIME,
                FechaVencimiento DATETIME,
                MontoOriginal CURRENCY DEFAULT 0,
                MontoCobrado CURRENCY DEFAULT 0,
                SaldoPendiente CURRENCY DEFAULT 0,
                DiasVencida INTEGER DEFAULT 0,
                Estado TEXT(20) DEFAULT 'Pendiente',
                Observaciones MEMO
            )
        """),
        ('CuentasPorPagar', """
            CREATE TABLE CuentasPorPagar (
                CuentaPagarID AUTOINCREMENT PRIMARY KEY,
                ProveedorNombre TEXT(200) NOT NULL,
                ProveedorRIF TEXT(20),
                NumeroDocumento TEXT(50),
                FechaEmision DATETIME,
                FechaVencimiento DATETIME,
                MontoOriginal CURRENCY DEFAULT 0,
                MontoPagado CURRENCY DEFAULT 0,
                SaldoPendiente CURRENCY DEFAULT 0,
                CategoriaGastoID INTEGER,
                Estado TEXT(20) DEFAULT 'Pendiente',
                Observaciones MEMO
            )
        """),
        ('Gastos', """
            CREATE TABLE Gastos (
                GastoID AUTOINCREMENT PRIMARY KEY,
                Fecha DATETIME,
                CategoriaGastoID INTEGER,
                Descripcion TEXT(200),
                Monto CURRENCY DEFAULT 0,
                FormaPagoID INTEGER,
                Referencia TEXT(50),
                BeneficiarioNombre TEXT(200),
                BeneficiarioRIF TEXT(20),
                CajaID INTEGER,
                UsuarioID INTEGER,
                Anulado YESNO DEFAULT FALSE,
                MotivoAnulacion TEXT(200)
            )
        """),
        ('ConfiguracionAdministrativa', """
            CREATE TABLE ConfiguracionAdministrativa (
                ConfigID AUTOINCREMENT PRIMARY KEY,
                MontoMaximoCajaChica CURRENCY DEFAULT 5000,
                DiasVencimiento INTEGER DEFAULT 30,
                AlertaDias INTEGER DEFAULT 7,
                RequiereAprobacionGastos YESNO DEFAULT FALSE,
                MontoAprobacionMinimo CURRENCY DEFAULT 1000,
                PermitirCajaDescuadrada YESNO DEFAULT FALSE,
                MonedaSecundaria TEXT(10) DEFAULT 'USD',
                TasaCambio DOUBLE DEFAULT 1,
                FechaActualizacion DATETIME
            )
        """),
    ]

    creadas = 0
    for nombre, ddl in tablas:
        if not _tabla_existe(nombre):
            try:
                db.execute(ddl)
                print(f"[ADMIN] Tabla {nombre} creada")
                creadas += 1
            except Exception as e:
                print(f"[ADMIN] Error creando tabla {nombre}: {e}")

    # Insertar datos iniciales si se crearon tablas nuevas
    if creadas > 0:
        _insertar_datos_iniciales_admin(db)

    return creadas


def _insertar_datos_iniciales_admin(db):
    """Inserta datos iniciales en las tablas administrativas recien creadas."""

    # Roles
    try:
        count = db.query_one("SELECT COUNT(*) AS Total FROM [Roles]")
        if (count or {}).get('Total', 0) == 0:
            roles = [
                ("Administrador", "Acceso completo al sistema", 100),
                ("Facturador", "Gestion de facturacion y caja", 50),
                ("Bioanalista", "Acceso a resultados y reportes", 30),
                ("Recepcion", "Registro de pacientes y solicitudes", 20),
                ("Consulta", "Solo lectura del sistema", 10),
            ]
            for nombre, desc, nivel in roles:
                try:
                    db.execute(
                        f"INSERT INTO [Roles] (NombreRol, Descripcion, NivelAcceso, Activo) "
                        f"VALUES ('{nombre}', '{desc}', {nivel}, True)"
                    )
                except:
                    pass
            print("[ADMIN] Roles iniciales insertados")
    except:
        pass

    # Formas de pago
    try:
        count = db.query_one("SELECT COUNT(*) AS Total FROM [FormasPago]")
        if (count or {}).get('Total', 0) == 0:
            formas = [
                ("Efectivo", False, False),
                ("Transferencia", True, True),
                ("Punto de Venta", True, True),
                ("Zelle", False, True),
                ("Pago Movil", True, True),
                ("Cheque", True, True),
                ("Divisa", False, False),
            ]
            for nombre, req_banco, req_ref in formas:
                try:
                    db.execute(
                        f"INSERT INTO [FormasPago] (Nombre, Activo, RequiereBanco, RequiereReferencia) "
                        f"VALUES ('{nombre}', True, {req_banco}, {req_ref})"
                    )
                except:
                    pass
            print("[ADMIN] Formas de pago insertadas")
    except:
        pass

    # Bancos Venezuela
    try:
        count = db.query_one("SELECT COUNT(*) AS Total FROM [Bancos]")
        if (count or {}).get('Total', 0) == 0:
            bancos = [
                ("Banco de Venezuela", "0102"), ("Banesco", "0134"),
                ("Banco Mercantil", "0105"), ("Banco Provincial (BBVA)", "0108"),
                ("Banco Nacional de Credito (BNC)", "0191"),
                ("Banco del Tesoro", "0163"), ("Banco Bicentenario", "0175"),
                ("Banco Exterior", "0115"), ("Banco Caroni", "0128"),
                ("Banco Sofitasa", "0137"), ("Banco Plaza", "0138"),
                ("Banco Fondo Comun (BFC)", "0151"), ("100% Banco", "0156"),
                ("Banco Activo", "0171"), ("Bancamiga", "0172"),
                ("Banplus", "0174"), ("Mi Banco", "0169"),
            ]
            for nombre, codigo in bancos:
                try:
                    db.execute(
                        f"INSERT INTO [Bancos] (Nombre, Codigo, Activo) "
                        f"VALUES ('{nombre}', '{codigo}', True)"
                    )
                except:
                    pass
            print("[ADMIN] Bancos insertados")
    except:
        pass

    # Categorias de gastos
    try:
        count = db.query_one("SELECT COUNT(*) AS Total FROM [CategoriaGastos]")
        if (count or {}).get('Total', 0) == 0:
            categorias = [
                ("Material de Laboratorio", "Tubos, jeringas, guantes y material descartable"),
                ("Reactivos", "Reactivos quimicos y biologicos para analisis"),
                ("Servicios Publicos", "Electricidad, agua, internet, telefono"),
                ("Alquiler", "Alquiler del local o espacio de trabajo"),
                ("Nomina", "Sueldos, salarios y beneficios del personal"),
                ("Mantenimiento de Equipos", "Reparacion y mantenimiento de equipos"),
                ("Papeleria y Oficina", "Material de oficina, impresion y papeleria"),
                ("Transporte", "Gastos de transporte y envios"),
                ("Impuestos y Tasas", "Impuestos municipales, ISLR y tasas gubernamentales"),
                ("Otros Gastos", "Gastos varios no clasificados"),
            ]
            for nombre, desc in categorias:
                try:
                    db.execute(
                        f"INSERT INTO [CategoriaGastos] (Nombre, Descripcion, Activo) "
                        f"VALUES ('{nombre}', '{desc}', True)"
                    )
                except:
                    pass
            print("[ADMIN] Categorias de gastos insertadas")
    except:
        pass

    # Configuracion administrativa
    try:
        count = db.query_one("SELECT COUNT(*) AS Total FROM [ConfiguracionAdministrativa]")
        if (count or {}).get('Total', 0) == 0:
            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            db.execute(
                f"INSERT INTO [ConfiguracionAdministrativa] "
                f"(MontoMaximoCajaChica, DiasVencimiento, AlertaDias, "
                f"RequiereAprobacionGastos, MontoAprobacionMinimo, PermitirCajaDescuadrada, "
                f"MonedaSecundaria, TasaCambio, FechaActualizacion) "
                f"VALUES (5000, 30, 7, False, 1000, False, 'USD', 1, {fecha})"
            )
            print("[ADMIN] Configuracion administrativa inicializada")
    except:
        pass

    # Permisos por modulo
    try:
        count = db.query_one("SELECT COUNT(*) AS Total FROM [PermisosModulo]")
        if (count or {}).get('Total', 0) == 0:
            modulos = [
                'caja_chica', 'facturacion', 'cuentas_cobrar',
                'cuentas_pagar', 'gastos', 'resumen_financiero', 'roles_permisos'
            ]
            permisos_por_rol = {
                1: (True, True, True, True, True),    # Administrador
                2: (True, True, True, False, True),    # Facturador
                3: (True, False, False, False, True),   # Bioanalista
                4: (True, True, False, False, False),   # Recepcion
                5: (True, False, False, False, False),  # Consulta
            }
            for rol_id, (ver, crear, editar, eliminar, exportar) in permisos_por_rol.items():
                for modulo in modulos:
                    if modulo == 'roles_permisos' and rol_id != 1:
                        v = c = e = el = ex = False
                    else:
                        v, c, e, el, ex = ver, crear, editar, eliminar, exportar
                    try:
                        db.execute(
                            f"INSERT INTO [PermisosModulo] "
                            f"(RolID, NombreModulo, PuedeVer, PuedeCrear, PuedeEditar, PuedeEliminar, PuedeExportar) "
                            f"VALUES ({rol_id}, '{modulo}', {v}, {c}, {e}, {el}, {ex})"
                        )
                    except:
                        pass
            print("[ADMIN] Permisos por modulo insertados")
    except:
        pass


def crear_ventana_administrativa(db, user):
    """Crea instancia de VentanaAdministrativa, creando tablas si no existen."""
    try:
        # Verificar si las tablas existen
        db.query("SELECT TOP 1 * FROM [CajaChica]")
    except:
        # Las tablas no existen: crearlas automaticamente
        print("[ADMIN] Tablas administrativas no encontradas. Creando automaticamente...")
        try:
            _inicializar_tablas_administrativas(db)
        except Exception as e:
            print(f"[ADMIN] Error en auto-migracion: {e}")
            return None

    try:
        return VentanaAdministrativa(db, user)
    except Exception as e:
        print(f"[ADMIN] Error creando VentanaAdministrativa: {e}")
        return None

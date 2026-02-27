# -*- coding: utf-8 -*-
"""
gtt_captura.py - Formulario especializado de captura para la
                 Prueba de Tolerancia a la Glucosa (GTT)
================================================================================
Funcionalidades:
  - Especificacion de la dosis de carga glucosada (g)
  - Checkboxes para habilitar/deshabilitar cada tiempo del estudio
    (Basal, 30min, 1h, 2h, 3h, 4h)
  - Validacion de valores numericos y alertas fuera de rango
  - Vista previa de la curva en tiempo real dentro del formulario

Uso:
    from modulos.gtt_captura import abrir_formulario_gtt
    abrir_formulario_gtt(parent, db, detalle_id, on_guardado=None)
================================================================================
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# ============================================================================
# CONSTANTES
# ============================================================================

# Codigo de la prueba GTT
CODIGO_GTT = 'QUIM005'

# Tiempos del estudio: (clave_seccion, etiqueta_display, codigo_param)
TIEMPOS_GTT = [
    ('Basal',  'Basal (0 min)',    'GTT001', True),   # siempre habilitado
    ('30min',  '30 minutos',       'GTT002', False),
    ('1h',     '1 hora',           'GTT003', False),
    ('2h',     '2 horas',          'GTT004', True),   # 2h es el mas importante diagnostico
    ('3h',     '3 horas',          'GTT005', False),
    ('4h',     '4 horas',          'GTT006', False),
]

# Valor de referencia para alertas por tiempo (limite_alto para simplificar)
LIMITES_ALERTA = {
    'GTT001': (70.0, 100.0),    # basal: 70-100
    'GTT002': (None, 200.0),    # 30min: < 200
    'GTT003': (None, 180.0),    # 1h:    < 180
    'GTT004': (None, 140.0),    # 2h:    < 140 normal
    'GTT005': (None, 120.0),    # 3h:    < 120
    'GTT006': (None, 110.0),    # 4h:    < 110
}

# Colores UI
COLOR_NORMAL  = '#ffffff'
COLOR_ALTO    = '#fff3e0'
COLOR_MUY_ALTO = '#ffebee'
COLOR_TITULO  = '#1565c0'
COLOR_HEADER  = '#e3f2fd'
COLOR_HABILITADO   = '#ffffff'
COLOR_DESHABILITADO = '#f5f5f5'


# ============================================================================
# FUNCION PRINCIPAL DE APERTURA
# ============================================================================

def abrir_formulario_gtt(parent, db, detalle_id, on_guardado=None):
    """
    Abre el dialogo especializado de captura GTT.

    Args:
        parent: ventana tk padre
        db: objeto Database de ANgesLAB
        detalle_id: ID del detalle de la solicitud
        on_guardado: callback opcional que se llama al guardar exitosamente
    """
    ventana = FormularioGTT(parent, db, detalle_id, on_guardado)
    ventana.grab_set()
    parent.wait_window(ventana)


# ============================================================================
# CLASE DEL FORMULARIO
# ============================================================================

class FormularioGTT(tk.Toplevel):
    """Dialogo de captura de la Prueba de Tolerancia a la Glucosa."""

    def __init__(self, parent, db, detalle_id, on_guardado=None):
        super().__init__(parent)
        self.db = db
        self.detalle_id = detalle_id
        self.on_guardado = on_guardado

        self.title("Curva de Glucemia - Tolerancia a la Glucosa (GTT)")
        self.resizable(True, True)
        self.geometry("680x680")
        self.configure(bg='white')

        # --- Estado ---
        self._param_ids = {}      # codigo -> ParametroID
        self._entries = {}        # codigo -> Entry widget
        self._check_vars = {}     # clave_seccion -> BooleanVar
        self._entry_frames = {}   # codigo -> Frame contenedor
        self._val_labels = {}     # codigo -> Label de validacion
        self._dosis_var = tk.StringVar(value='75')

        self._cargar_param_ids()
        self._cargar_valores_existentes()
        self._build_ui()
        self._restaurar_estado_checks()
        self._dibujar_grafica_preview()

    # ------------------------------------------------------------------
    # CARGA DE DATOS DESDE DB
    # ------------------------------------------------------------------

    def _cargar_param_ids(self):
        """Carga los ParametroIDs de los parametros GTT para este detalle."""
        # Obtener PruebaID del detalle
        det = self.db.query_one(
            f"SELECT PruebaID FROM DetalleSolicitudes WHERE DetalleID = {self.detalle_id}"
        )
        if not det:
            return
        prueba_id = det['PruebaID']

        # Cargar parametros de la prueba
        params = self.db.query(
            f"SELECT par.ParametroID, par.CodigoParametro, par.NombreParametro, "
            f"par.Seccion, par.Observaciones AS ValorRef "
            f"FROM ParametrosPrueba pp "
            f"INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID "
            f"WHERE pp.PruebaID = {prueba_id} "
            f"ORDER BY pp.Secuencia"
        ) or []

        for p in params:
            self._param_ids[p['CodigoParametro']] = p['ParametroID']

    def _cargar_valores_existentes(self):
        """Carga valores ya capturados (para edicion)."""
        self._valores_existentes = {}
        for codigo, param_id in self._param_ids.items():
            rp = self.db.query_one(
                f"SELECT Valor, ValorReferencia, FueraDeRango, TipoAlerta "
                f"FROM ResultadosParametros "
                f"WHERE DetalleID = {self.detalle_id} AND ParametroID = {param_id}"
            )
            if rp:
                self._valores_existentes[codigo] = rp

        # Dosis existente
        dosis_rp = self._valores_existentes.get('GTT000')
        if dosis_rp and dosis_rp.get('Valor'):
            self._dosis_var.set(str(dosis_rp['Valor']))

    # ------------------------------------------------------------------
    # CONSTRUCCION DE UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # ---- Titulo ----
        title_bar = tk.Frame(self, bg=COLOR_TITULO)
        title_bar.pack(fill='x')
        tk.Label(title_bar,
                 text="  📊  Curva de Glucemia - Tolerancia a la Glucosa",
                 font=('Segoe UI', 13, 'bold'), bg=COLOR_TITULO, fg='white'
                 ).pack(side='left', pady=12, padx=10)

        # ---- Contenedor con scroll ----
        outer = tk.Frame(self, bg='white')
        outer.pack(fill='both', expand=True, padx=15, pady=10)

        canvas = tk.Canvas(outer, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        self._scroll_frame = tk.Frame(canvas, bg='white')
        self._scroll_frame.bind(
            '<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )
        self._canvas_win = canvas.create_window((0, 0), window=self._scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind('<Configure>', lambda e: canvas.itemconfig(self._canvas_win, width=e.width))

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>',
            lambda ev: canvas.yview_scroll(int(-1*(ev.delta/120)), 'units')))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

        sf = self._scroll_frame

        # ---- Seccion: Dosis de carga ----
        self._build_seccion_dosis(sf)

        # ---- Seccion: Tiempos habilitables ----
        self._build_seccion_tiempos(sf)

        # ---- Seccion: Interpretacion y observaciones ----
        self._build_seccion_interpretacion(sf)

        # ---- Preview de la curva ----
        self._build_preview_grafica(sf)

        # ---- Botones ----
        btn_frame = tk.Frame(self, bg='white')
        btn_frame.pack(fill='x', padx=15, pady=(5, 10))

        tk.Button(btn_frame, text="💾 Guardar Resultados",
                  font=('Segoe UI', 10, 'bold'), bg=COLOR_TITULO, fg='white',
                  relief='flat', padx=20, pady=8, cursor='hand2',
                  command=self._guardar).pack(side='right', padx=5)

        tk.Button(btn_frame, text="Cancelar",
                  font=('Segoe UI', 10), bg='#e2e8f0', fg='#333',
                  relief='flat', padx=14, pady=8, cursor='hand2',
                  command=self.destroy).pack(side='right', padx=5)

        tk.Button(btn_frame, text="🔄 Actualizar gráfica",
                  font=('Segoe UI', 9), bg='#e8f5e9', fg='#2e7d32',
                  relief='flat', padx=12, pady=6, cursor='hand2',
                  command=self._dibujar_grafica_preview).pack(side='left', padx=5)

    def _build_seccion_dosis(self, parent):
        f = tk.LabelFrame(parent, text=" 💉 Carga Glucosada ",
                          font=('Segoe UI', 10, 'bold'), bg='white',
                          fg=COLOR_TITULO)
        f.pack(fill='x', pady=(0, 8))

        row = tk.Frame(f, bg='white')
        row.pack(fill='x', padx=12, pady=8)

        tk.Label(row, text="Dosis de carga glucosada (g):",
                 font=('Segoe UI', 10), bg='white').pack(side='left')

        dosis_entry = tk.Entry(row, textvariable=self._dosis_var,
                               font=('Segoe UI', 11, 'bold'), width=8,
                               relief='flat', highlightthickness=1,
                               highlightbackground='#90caf9', justify='center')
        dosis_entry.pack(side='left', padx=10, ipady=4)

        # Botones rapidos de dosis
        for dosis_val in ['50', '75', '100']:
            tk.Button(row, text=f"{dosis_val}g",
                      font=('Segoe UI', 9), bg='#e3f2fd', fg='#1565c0',
                      relief='flat', padx=8, cursor='hand2',
                      command=lambda d=dosis_val: self._dosis_var.set(d)
                      ).pack(side='left', padx=2)

        tk.Label(row, text="  (estándar: 75g adulto, 1.75g/kg niños)",
                 font=('Segoe UI', 8), bg='white', fg='#666').pack(side='left')

    def _build_seccion_tiempos(self, parent):
        f = tk.LabelFrame(parent, text=" ⏱ Mediciones de Glucosa ",
                          font=('Segoe UI', 10, 'bold'), bg='white',
                          fg=COLOR_TITULO)
        f.pack(fill='x', pady=(0, 8))

        # Encabezado
        eh = tk.Frame(f, bg=COLOR_HEADER)
        eh.pack(fill='x', padx=5, pady=(5, 0))
        tk.Label(eh, text="✓ Habilitar", font=('Segoe UI', 8, 'bold'),
                 bg=COLOR_HEADER, width=10).pack(side='left', padx=5, pady=4)
        tk.Label(eh, text="Tiempo", font=('Segoe UI', 8, 'bold'),
                 bg=COLOR_HEADER, width=14).pack(side='left', padx=5)
        tk.Label(eh, text="Resultado (mg/dL)", font=('Segoe UI', 8, 'bold'),
                 bg=COLOR_HEADER, width=18).pack(side='left', padx=5)
        tk.Label(eh, text="Referencia", font=('Segoe UI', 8, 'bold'),
                 bg=COLOR_HEADER, width=28).pack(side='left', padx=5)
        tk.Label(eh, text="Estado", font=('Segoe UI', 8, 'bold'),
                 bg=COLOR_HEADER, width=10).pack(side='left', padx=5)

        for i, (clave, etiqueta, codigo, default_hab) in enumerate(TIEMPOS_GTT):
            var = tk.BooleanVar(value=default_hab)
            self._check_vars[clave] = var
            self._build_fila_tiempo(f, i, clave, etiqueta, codigo, var)

    def _build_fila_tiempo(self, parent, idx, clave, etiqueta, codigo, check_var):
        bg = '#fafafa' if idx % 2 == 0 else 'white'
        row_frame = tk.Frame(parent, bg=bg)
        row_frame.pack(fill='x', padx=5, pady=1)
        self._entry_frames[codigo] = row_frame

        # Basal siempre habilitado (no tiene checkbox funcional)
        if clave == 'Basal':
            tk.Label(row_frame, text="✔ Siempre", font=('Segoe UI', 8),
                     bg='#e8f5e9', fg='#2e7d32', width=10).pack(side='left', padx=5, pady=4)
        else:
            chk = tk.Checkbutton(row_frame, variable=check_var, bg=bg,
                                 font=('Segoe UI', 9), cursor='hand2',
                                 command=lambda c=codigo, v=check_var: self._toggle_tiempo(c, v))
            chk.pack(side='left', padx=15, pady=4)

        tk.Label(row_frame, text=etiqueta, font=('Segoe UI', 9, 'bold'),
                 bg=bg, width=14, anchor='w').pack(side='left', padx=5)

        entry = tk.Entry(row_frame, font=('Segoe UI', 11), width=10,
                         relief='flat', highlightthickness=1,
                         highlightbackground='#90caf9', justify='center')
        entry.pack(side='left', padx=5, ipady=4)
        entry.bind('<KeyRelease>', lambda e, c=codigo: self._on_valor_cambia(c))
        self._entries[codigo] = entry

        # Valor de referencia
        limites = LIMITES_ALERTA.get(codigo)
        if limites:
            lim_bajo, lim_alto = limites
            if lim_bajo and lim_alto:
                ref_txt = f"{lim_bajo} - {lim_alto} mg/dL"
            elif lim_alto:
                ref_txt = f"< {lim_alto} mg/dL"
            else:
                ref_txt = ""
        else:
            ref_txt = ""

        tk.Label(row_frame, text=ref_txt, font=('Segoe UI', 8),
                 bg=bg, fg='#1565c0', width=28, anchor='w').pack(side='left', padx=5)

        # Label de estado/alerta
        val_lbl = tk.Label(row_frame, text="", font=('Segoe UI', 8, 'bold'),
                           bg=bg, width=10, anchor='w')
        val_lbl.pack(side='left', padx=5)
        self._val_labels[codigo] = val_lbl

        # Restaurar valor existente si hay
        rp_existente = self._valores_existentes.get(codigo)
        if rp_existente and rp_existente.get('Valor'):
            entry.insert(0, str(rp_existente['Valor']))
            self._on_valor_cambia(codigo)

        # Aplicar estado inicial (habilitado/deshabilitado)
        self._aplicar_estado_entry(codigo, check_var.get() if clave != 'Basal' else True)

    def _build_seccion_interpretacion(self, parent):
        f = tk.LabelFrame(parent, text=" 📝 Interpretación y Observaciones ",
                          font=('Segoe UI', 10, 'bold'), bg='white',
                          fg=COLOR_TITULO)
        f.pack(fill='x', pady=(0, 8))

        # Interpretacion
        row1 = tk.Frame(f, bg='white')
        row1.pack(fill='x', padx=12, pady=(8, 4))
        tk.Label(row1, text="Interpretación:", font=('Segoe UI', 9, 'bold'),
                 bg='white', width=15, anchor='w').pack(side='left')

        opciones_interp = [
            "", "Normal",
            "Intolerancia a la Glucosa (IGT)",
            "Diabetes Mellitus",
            "Hipoglucemia Reactiva",
            "Glucemia en Ayunas Alterada (IFG)",
            "Sospecha de Síndrome de Dumping",
        ]
        self._combo_interp = ttk.Combobox(row1, font=('Segoe UI', 9),
                                           values=opciones_interp,
                                           state='normal', width=40)
        self._combo_interp.pack(side='left', padx=5)

        # Pre-cargar interpretacion existente
        interp_existente = self._valores_existentes.get('GTT007')
        if interp_existente and interp_existente.get('Valor'):
            self._combo_interp.set(str(interp_existente['Valor']))

        # Observaciones
        row2 = tk.Frame(f, bg='white')
        row2.pack(fill='x', padx=12, pady=(4, 8))
        tk.Label(row2, text="Observaciones:", font=('Segoe UI', 9, 'bold'),
                 bg='white', width=15, anchor='w').pack(side='left', anchor='n', pady=2)
        self._text_obs = tk.Text(row2, font=('Segoe UI', 9), height=3, width=50,
                                 relief='flat', highlightthickness=1,
                                 highlightbackground='#ccc', wrap='word')
        self._text_obs.pack(side='left', padx=5)

        # Pre-cargar observaciones existentes
        obs_existente = self._valores_existentes.get('GTT008')
        if obs_existente and obs_existente.get('Valor'):
            self._text_obs.insert('1.0', str(obs_existente['Valor']))

    def _build_preview_grafica(self, parent):
        self._preview_frame = tk.LabelFrame(parent, text=" 📈 Vista Previa de la Curva ",
                                            font=('Segoe UI', 10, 'bold'), bg='white',
                                            fg='#2e7d32')
        self._preview_frame.pack(fill='x', pady=(0, 8))

        self._canvas_grafica = tk.Canvas(self._preview_frame, bg='white',
                                          height=180, highlightthickness=0)
        self._canvas_grafica.pack(fill='x', padx=10, pady=8)

    # ------------------------------------------------------------------
    # LOGICA DE INTERACCION
    # ------------------------------------------------------------------

    def _restaurar_estado_checks(self):
        """Restaura el estado de los checkboxes segun los valores guardados."""
        for clave, etiqueta, codigo, default_hab in TIEMPOS_GTT:
            if clave == 'Basal':
                continue
            var = self._check_vars[clave]
            # Si hay valor guardado, habilitar automaticamente
            rp = self._valores_existentes.get(codigo)
            if rp and rp.get('Valor'):
                var.set(True)
            self._aplicar_estado_entry(codigo, var.get())

    def _toggle_tiempo(self, codigo, var):
        """Habilita/deshabilita una fila de tiempo."""
        self._aplicar_estado_entry(codigo, var.get())
        if not var.get():
            # Limpiar el entry al deshabilitar
            entry = self._entries.get(codigo)
            if entry:
                entry.delete(0, 'end')
            lbl = self._val_labels.get(codigo)
            if lbl:
                lbl.config(text='', fg='#9e9e9e')

    def _aplicar_estado_entry(self, codigo, habilitado):
        """Aplica visualmente el estado habilitado/deshabilitado al entry."""
        entry = self._entries.get(codigo)
        if not entry:
            return
        if habilitado:
            entry.config(state='normal',
                         bg=COLOR_HABILITADO,
                         highlightbackground='#90caf9')
        else:
            entry.config(state='disabled',
                         bg=COLOR_DESHABILITADO,
                         highlightbackground='#ddd')

    def _on_valor_cambia(self, codigo):
        """Valida el valor ingresado y actualiza la etiqueta de estado."""
        entry = self._entries.get(codigo)
        lbl = self._val_labels.get(codigo)
        if not entry or not lbl:
            return

        val_txt = entry.get().strip().replace(',', '.')
        if not val_txt:
            lbl.config(text='', fg='#9e9e9e')
            entry.config(bg=COLOR_HABILITADO)
            return

        try:
            val = float(val_txt)
        except ValueError:
            lbl.config(text='⚠ No num.', fg='#f57f17')
            entry.config(bg='#fff9c4')
            return

        limites = LIMITES_ALERTA.get(codigo)
        if not limites:
            lbl.config(text='OK', fg='#2e7d32')
            entry.config(bg=COLOR_HABILITADO)
            return

        lim_bajo, lim_alto = limites
        if lim_bajo and val < lim_bajo:
            lbl.config(text=f'↓ Bajo', fg='#1565c0')
            entry.config(bg='#e3f2fd')
        elif lim_alto and val > lim_alto:
            # Determinar severidad
            if val > lim_alto * 1.5:
                lbl.config(text=f'↑↑ Critico', fg='#c62828')
                entry.config(bg=COLOR_MUY_ALTO)
            else:
                lbl.config(text=f'↑ Alto', fg='#e65100')
                entry.config(bg=COLOR_ALTO)
        else:
            lbl.config(text='✓ Normal', fg='#2e7d32')
            entry.config(bg='#f1f8e9')

    def _dibujar_grafica_preview(self):
        """Dibuja la curva de glucemia en el canvas de preview usando solo tkinter."""
        c = self._canvas_grafica
        c.delete('all')

        # Recolectar puntos habilitados con valor
        puntos = []  # [(minutos, valor_float, etiqueta)]
        tiempos_min = {'Basal': 0, '30min': 30, '1h': 60, '2h': 120, '3h': 180, '4h': 240}
        for clave, etiqueta, codigo, _ in TIEMPOS_GTT:
            var = self._check_vars.get(clave)
            if var and not var.get() and clave != 'Basal':
                continue
            entry = self._entries.get(codigo)
            if not entry:
                continue
            val_txt = entry.get().strip().replace(',', '.')
            try:
                val = float(val_txt)
                puntos.append((tiempos_min[clave], val, etiqueta))
            except (ValueError, TypeError):
                continue

        W = c.winfo_reqwidth() or 600
        H = 180
        pad_left = 55
        pad_right = 20
        pad_top = 15
        pad_bottom = 35

        area_w = W - pad_left - pad_right
        area_h = H - pad_top - pad_bottom

        # Referencia de tiempo maxima
        max_min = 240

        # Calcular rango Y
        all_vals = [v for _, v, _ in puntos]
        # Incluir lineas de referencia en el rango
        ref_vals = [100.0, 140.0, 180.0, 200.0]
        if all_vals:
            y_min_data = min(min(all_vals), 60)
            y_max_data = max(max(all_vals + ref_vals) + 20, 220)
        else:
            y_min_data, y_max_data = 50, 250

        def to_canvas(minutos, valor):
            cx = pad_left + (minutos / max_min) * area_w
            cy = pad_top + area_h - ((valor - y_min_data) / (y_max_data - y_min_data)) * area_h
            return cx, cy

        # --- Fondo ---
        c.create_rectangle(pad_left, pad_top, W - pad_right, H - pad_bottom,
                           fill='#fafafa', outline='#ccc')

        # --- Lineas horizontales de referencia ---
        referencias = [
            (100.0, '#66bb6a', '100'),   # normal basal
            (140.0, '#ffa726', '140'),   # limite 2h normal/IGT
            (180.0, '#ef5350', '180'),   # limite 1h
            (200.0, '#c62828', '200'),   # limite diabetes
        ]
        for ref_val, ref_color, ref_label in referencias:
            if y_min_data <= ref_val <= y_max_data:
                _, ry = to_canvas(0, ref_val)
                c.create_line(pad_left, ry, W - pad_right, ry,
                              fill=ref_color, dash=(4, 3), width=1)
                c.create_text(pad_left - 4, ry, text=ref_label,
                              font=('Segoe UI', 7), anchor='e', fill=ref_color)

        # --- Ejes ---
        c.create_line(pad_left, pad_top, pad_left, H - pad_bottom, fill='#333', width=1)
        c.create_line(pad_left, H - pad_bottom, W - pad_right, H - pad_bottom, fill='#333', width=1)

        # --- Etiquetas eje X ---
        for min_val, label in [(0, '0'), (30, '30'), (60, '1h'), (120, '2h'), (180, '3h'), (240, '4h')]:
            cx = pad_left + (min_val / max_min) * area_w
            c.create_line(cx, H - pad_bottom, cx, H - pad_bottom + 4, fill='#666')
            c.create_text(cx, H - pad_bottom + 10, text=label,
                          font=('Segoe UI', 7), fill='#555', anchor='n')

        c.create_text(pad_left + area_w // 2, H - 5,
                      text="Tiempo (minutos)", font=('Segoe UI', 7), fill='#555')

        # --- Etiqueta eje Y ---
        c.create_text(10, pad_top + area_h // 2, text="mg/dL",
                      font=('Segoe UI', 7), fill='#555', angle=90)

        if len(puntos) < 1:
            c.create_text(W // 2, H // 2,
                          text="Ingrese valores para ver la curva",
                          font=('Segoe UI', 9), fill='#aaa')
            return

        # --- Dibujar la curva ---
        coords_px = [to_canvas(m, v) for m, v, _ in puntos]

        if len(coords_px) >= 2:
            flat = []
            for x, y in coords_px:
                flat += [x, y]
            c.create_line(*flat, fill='#1565c0', width=2, smooth=True)

        # --- Puntos y etiquetas ---
        for (m, v, etq), (cx, cy) in zip(puntos, coords_px):
            limites = LIMITES_ALERTA.get(
                next((cod for cl, _, cod, _ in TIEMPOS_GTT if tiempos_min.get(cl) == m), None)
            )
            if limites:
                _, lim_alto = limites
                if lim_alto and v > lim_alto:
                    punto_color = '#c62828' if v > lim_alto * 1.2 else '#e65100'
                else:
                    punto_color = '#2e7d32'
            else:
                punto_color = '#1565c0'

            c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                          fill=punto_color, outline='white', width=1)
            # Etiqueta valor encima del punto
            offset_y = -12 if cy > pad_top + 18 else 12
            c.create_text(cx, cy + offset_y, text=f"{v:.0f}",
                          font=('Segoe UI', 8, 'bold'), fill=punto_color)

        # Leyenda compacta
        c.create_rectangle(W - pad_right - 95, pad_top, W - pad_right, pad_top + 50,
                           fill='white', outline='#ccc')
        items_ley = [
            ('#66bb6a', '100 (basal normal)'),
            ('#ffa726', '140 (limite 2h)'),
            ('#c62828', '200 (DM)'),
        ]
        for j, (col, lbl) in enumerate(items_ley):
            lx = W - pad_right - 90
            ly = pad_top + 8 + j * 14
            c.create_line(lx, ly + 4, lx + 12, ly + 4, fill=col, width=2, dash=(4, 2))
            c.create_text(lx + 15, ly + 4, text=lbl, font=('Segoe UI', 6),
                         fill='#555', anchor='w')

    # ------------------------------------------------------------------
    # GUARDADO
    # ------------------------------------------------------------------

    def _guardar(self):
        """Valida y guarda todos los valores en ResultadosParametros."""
        # Validar dosis
        dosis_txt = self._dosis_var.get().strip()
        if not dosis_txt:
            messagebox.showwarning("Validación", "Debe especificar la dosis de carga glucosada.",
                                   parent=self)
            return

        # Recolectar todos los valores a guardar
        valores_guardar = {}  # codigo -> (valor_str, fuera_rango, tipo_alerta)

        # Dosis (GTT000)
        valores_guardar['GTT000'] = (dosis_txt, False, '')

        # Tiempos
        for clave, etiqueta, codigo, _ in TIEMPOS_GTT:
            var = self._check_vars.get(clave)
            habilitado = True if clave == 'Basal' else (var.get() if var else False)
            entry = self._entries.get(codigo)
            if not entry:
                continue

            if not habilitado:
                valores_guardar[codigo] = ('', False, '')
                continue

            val_txt = entry.get().strip().replace(',', '.')
            if not val_txt:
                continue  # no capturado, no guardar

            # Calcular fuera de rango
            try:
                val_num = float(val_txt)
                limites = LIMITES_ALERTA.get(codigo)
                if limites:
                    lim_bajo, lim_alto = limites
                    if lim_bajo and val_num < lim_bajo:
                        fuera = True
                        tipo = 'Bajo'
                    elif lim_alto and val_num > lim_alto * 1.5:
                        fuera = True
                        tipo = 'CriticoAlto'
                    elif lim_alto and val_num > lim_alto:
                        fuera = True
                        tipo = 'Alto'
                    else:
                        fuera = False
                        tipo = ''
                else:
                    fuera, tipo = False, ''
            except (ValueError, TypeError):
                fuera, tipo = False, ''

            valores_guardar[codigo] = (val_txt, fuera, tipo)

        # Interpretacion (GTT007) y Observaciones (GTT008)
        interp_val = self._combo_interp.get().strip()
        valores_guardar['GTT007'] = (interp_val, False, '')

        obs_val = self._text_obs.get('1.0', 'end').strip()
        valores_guardar['GTT008'] = (obs_val, False, '')

        # Guardar en DB
        try:
            ahora = datetime.now().strftime("'%Y-%m-%d %H:%M:%S'")
            for codigo, (valor, fuera, tipo) in valores_guardar.items():
                param_id = self._param_ids.get(codigo)
                if not param_id:
                    continue

                # Obtener valor de referencia del parametro
                par_info = self.db.query_one(
                    f"SELECT Observaciones FROM Parametros WHERE ParametroID = {param_id}"
                )
                val_ref = (par_info or {}).get('Observaciones') or ''

                # Verificar si ya existe registro
                existe = self.db.query_one(
                    f"SELECT ResultadoParamID FROM ResultadosParametros "
                    f"WHERE DetalleID = {self.detalle_id} AND ParametroID = {param_id}"
                )

                valor_escaped = str(valor).replace("'", "''")
                val_ref_escaped = str(val_ref).replace("'", "''")
                fuera_sql = 'True' if fuera else 'False'
                tipo_sql = f"'{tipo}'" if tipo else 'NULL'

                if existe:
                    rid = existe['ResultadoParamID']
                    self.db.execute(f"""
                        UPDATE ResultadosParametros SET
                            Valor = '{valor_escaped}',
                            ValorReferencia = '{val_ref_escaped}',
                            FueraDeRango = {fuera_sql},
                            TipoAlerta = {tipo_sql},
                            FechaCaptura = {ahora}
                        WHERE ResultadoParamID = {rid}
                    """)
                else:
                    self.db.execute(f"""
                        INSERT INTO ResultadosParametros
                            (DetalleID, ParametroID, Valor, ValorReferencia,
                             FueraDeRango, TipoAlerta, FechaCaptura)
                        VALUES ({self.detalle_id}, {param_id}, '{valor_escaped}',
                                '{val_ref_escaped}', {fuera_sql}, {tipo_sql}, {ahora})
                    """)

            # Actualizar estado del detalle
            self.db.execute(f"""
                UPDATE DetalleSolicitudes SET Estado = 'Capturado'
                WHERE DetalleID = {self.detalle_id}
            """)

            messagebox.showinfo("Guardado", "Resultados de la Curva de Glucemia guardados correctamente.",
                                parent=self)
            if self.on_guardado:
                self.on_guardado()
            self.destroy()

        except Exception as e:
            messagebox.showerror("Error al guardar",
                                 f"Ocurrió un error al guardar los resultados:\n{e}",
                                 parent=self)


def es_prueba_gtt(prueba_row):
    """Retorna True si la prueba dada es la GTT."""
    return (
        (prueba_row.get('CodigoPrueba') or '').upper() == CODIGO_GTT or
        'TOLERANCIA' in (prueba_row.get('NombrePrueba') or '').upper()
    )

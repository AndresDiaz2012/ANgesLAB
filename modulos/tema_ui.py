# -*- coding: utf-8 -*-
"""
================================================================================
MOTOR DE TEMA PROFESIONAL - ANgesLAB
================================================================================
Sistema de diseño centralizado que da a la interfaz una imagen profesional,
cohesiva y competitiva en el sector salud, SIN alterar la lógica de negocio.

Aplica un tema ttk completo sobre 'clam' que restiliza globalmente:
    - Treeview (tablas)      -> encabezados con color de marca, filas amplias,
                                selección de alto contraste
    - Notebook (pestañas)    -> pestañas planas modernas
    - Button / Entry / Combo -> variantes de marca con estados hover/focus
    - Scrollbar / Progressbar / LabelFrame

El tema lee la MISMA paleta que usa el resto de la app (se le pasa el dict
COLORS) y deriva internamente los tonos que faltan, de modo que exista una
sola fuente de verdad para el color.

Copyright (c) 2024-2026 ANgesLAB Solutions
================================================================================
"""

from tkinter import ttk

FUENTE = 'Segoe UI'

# ---------------------------------------------------------------------------
# Tokens derivados: se agregan a la paleta base si no vienen definidos.
# Mantienen la identidad cyan/teal + slate profundo, añadiendo profundidad.
# ---------------------------------------------------------------------------
_TOKENS_DERIVADOS = {
    'primary_dark':   '#0e7490',   # cyan profundo (hover/pressed)
    'primary_light':  '#22d3ee',   # cyan brillante (acentos)
    'primary_soft':   '#e0f2fe',   # cyan muy claro (fondos suaves)
    'surface':        '#ffffff',   # superficie de tarjetas
    'surface_alt':    '#f1f5f9',   # superficie alterna / hover suave
    'row_alt':        '#f8fafc',   # fila alterna en tablas
    'hover':          '#f1f5f9',   # hover genérico claro
    'heading_bg':     '#1e293b',   # fondo de encabezados de tabla
    'heading_hover':  '#0891b2',   # hover de encabezado de tabla
    'shadow':         '#cbd5e1',   # sombra simulada (bordes suaves)
    'sidebar_active': '#0891b2',   # item activo del menú lateral
    'text_muted':     '#94a3b8',   # texto terciario
}


def paleta_completa(colors):
    """Devuelve una copia de la paleta con los tokens derivados garantizados.

    No sobrescribe valores que ya existan en `colors`; solo rellena los que
    falten. Así la app conserva su identidad y gana los tonos que el tema
    profesional necesita.
    """
    completa = dict(_TOKENS_DERIVADOS)
    completa.update(colors or {})
    # Garantizar que las claves derivadas existan aunque colors traiga otras
    for k, v in _TOKENS_DERIVADOS.items():
        completa.setdefault(k, v)
    return completa


def aplicar_tema_profesional(colors, root=None):
    """Configura el tema ttk profesional a partir de la paleta `colors`.

    Args:
        colors: dict de la paleta (el COLORS de la app).
        root: ventana raíz opcional (para option_add de widgets tk clásicos).

    Returns:
        El objeto ttk.Style configurado.
    """
    C = paleta_completa(colors)
    style = ttk.Style()

    # 'clam' es el tema base más flexible para personalización de colores.
    try:
        style.theme_use('clam')
    except Exception:
        pass

    # -----------------------------------------------------------------------
    # BASE
    # -----------------------------------------------------------------------
    style.configure('.',
                    font=(FUENTE, 10),
                    background=C['bg'],
                    foreground=C['text'],
                    focuscolor=C['bg'])

    # -----------------------------------------------------------------------
    # TREEVIEW (tablas) — el widget de mayor presencia en la app
    # -----------------------------------------------------------------------
    style.configure('Treeview',
                    background=C['surface'],
                    fieldbackground=C['surface'],
                    foreground=C['text'],
                    rowheight=32,
                    font=(FUENTE, 10),
                    borderwidth=0,
                    relief='flat')
    style.map('Treeview',
              background=[('selected', C['primary'])],
              foreground=[('selected', '#ffffff')])

    style.configure('Treeview.Heading',
                    background=C['heading_bg'],
                    foreground='#ffffff',
                    font=(FUENTE, 10, 'bold'),
                    relief='flat',
                    borderwidth=0,
                    padding=(10, 9))
    style.map('Treeview.Heading',
              background=[('active', C['heading_hover']),
                          ('pressed', C['primary_dark'])],
              foreground=[('active', '#ffffff')])

    # -----------------------------------------------------------------------
    # NOTEBOOK (pestañas)
    # -----------------------------------------------------------------------
    style.configure('TNotebook',
                    background=C['bg'],
                    borderwidth=0,
                    tabmargins=(2, 6, 2, 0))
    style.configure('TNotebook.Tab',
                    background=C['border'],
                    foreground=C['text_light'],
                    font=(FUENTE, 10, 'bold'),
                    padding=(18, 9),
                    borderwidth=0)
    style.map('TNotebook.Tab',
              background=[('selected', C['surface']),
                          ('active', C['surface_alt'])],
              foreground=[('selected', C['primary']),
                          ('active', C['text'])],
              expand=[('selected', (0, 0, 0, 0))])

    # -----------------------------------------------------------------------
    # BOTONES — base + variantes semánticas de marca
    # -----------------------------------------------------------------------
    style.configure('TButton',
                    font=(FUENTE, 10, 'bold'),
                    padding=(14, 8),
                    borderwidth=0,
                    relief='flat',
                    focuscolor='none',
                    background=C['primary'],
                    foreground='#ffffff')
    style.map('TButton',
              background=[('active', C['primary_dark']),
                          ('pressed', C['primary_dark']),
                          ('disabled', C['border'])],
              foreground=[('disabled', C['text_muted'])])

    _variantes_boton = {
        'Primary.TButton': (C['primary'], C['primary_dark']),
        'Success.TButton': (C['success'], '#047857'),
        'Warning.TButton': (C['warning'], '#b45309'),
        'Danger.TButton':  (C['danger'],  '#b91c1c'),
        'Info.TButton':    (C['info'],    '#6d28d9'),
    }
    for nombre, (base, hover) in _variantes_boton.items():
        style.configure(nombre,
                        font=(FUENTE, 10, 'bold'),
                        padding=(14, 8),
                        borderwidth=0,
                        relief='flat',
                        focuscolor='none',
                        background=base,
                        foreground='#ffffff')
        style.map(nombre,
                  background=[('active', hover), ('pressed', hover)])

    # Botón "fantasma" (contorno) para acciones secundarias
    style.configure('Ghost.TButton',
                    font=(FUENTE, 10, 'bold'),
                    padding=(14, 8),
                    borderwidth=1,
                    relief='flat',
                    focuscolor='none',
                    background=C['surface'],
                    foreground=C['primary'])
    style.map('Ghost.TButton',
              background=[('active', C['primary_soft'])],
              bordercolor=[('!disabled', C['primary'])])

    # -----------------------------------------------------------------------
    # ENTRADAS Y COMBOS
    # -----------------------------------------------------------------------
    style.configure('TEntry',
                    fieldbackground=C['surface'],
                    foreground=C['text'],
                    bordercolor=C['border'],
                    lightcolor=C['border'],
                    darkcolor=C['border'],
                    borderwidth=1,
                    relief='flat',
                    padding=6)
    style.map('TEntry',
              bordercolor=[('focus', C['primary'])],
              lightcolor=[('focus', C['primary'])],
              darkcolor=[('focus', C['primary'])])

    style.configure('TCombobox',
                    fieldbackground=C['surface'],
                    background=C['surface'],
                    foreground=C['text'],
                    bordercolor=C['border'],
                    arrowcolor=C['primary'],
                    borderwidth=1,
                    relief='flat',
                    padding=5)
    style.map('TCombobox',
              fieldbackground=[('readonly', C['surface'])],
              bordercolor=[('focus', C['primary'])],
              foreground=[('disabled', C['text_muted'])])

    style.configure('TSpinbox',
                    fieldbackground=C['surface'],
                    foreground=C['text'],
                    bordercolor=C['border'],
                    arrowcolor=C['primary'],
                    borderwidth=1,
                    relief='flat',
                    padding=5)
    style.map('TSpinbox', bordercolor=[('focus', C['primary'])])

    # -----------------------------------------------------------------------
    # SCROLLBARS — delgadas y modernas
    # -----------------------------------------------------------------------
    for orient in ('Vertical.TScrollbar', 'Horizontal.TScrollbar'):
        style.configure(orient,
                        background=C['border'],
                        troughcolor=C['bg'],
                        borderwidth=0,
                        arrowcolor=C['text_light'],
                        relief='flat')
        style.map(orient,
                  background=[('active', C['text_light']),
                              ('pressed', C['primary'])])

    # -----------------------------------------------------------------------
    # PROGRESSBAR
    # -----------------------------------------------------------------------
    style.configure('TProgressbar',
                    background=C['primary'],
                    troughcolor=C['border'],
                    borderwidth=0,
                    thickness=8)
    style.configure('Success.Horizontal.TProgressbar',
                    background=C['success'], troughcolor=C['border'], borderwidth=0)

    # -----------------------------------------------------------------------
    # LABELFRAME (marcos con título)
    # -----------------------------------------------------------------------
    style.configure('TLabelframe',
                    background=C['surface'],
                    borderwidth=1,
                    relief='solid',
                    bordercolor=C['border'])
    style.configure('TLabelframe.Label',
                    background=C['surface'],
                    foreground=C['primary'],
                    font=(FUENTE, 11, 'bold'))

    # -----------------------------------------------------------------------
    # FRAMES / LABELS ttk auxiliares
    # -----------------------------------------------------------------------
    style.configure('TFrame', background=C['bg'])
    style.configure('Card.TFrame',
                    background=C['surface'],
                    relief='flat',
                    borderwidth=0)
    style.configure('TLabel', background=C['bg'], foreground=C['text'])
    style.configure('Title.TLabel',
                    background=C['bg'], foreground=C['text'],
                    font=(FUENTE, 18, 'bold'))
    style.configure('Subtitle.TLabel',
                    background=C['bg'], foreground=C['text_light'],
                    font=(FUENTE, 10))
    style.configure('TCheckbutton', background=C['bg'], foreground=C['text'])
    style.map('TCheckbutton', foreground=[('active', C['primary'])])
    style.configure('TRadiobutton', background=C['bg'], foreground=C['text'])
    style.map('TRadiobutton', foreground=[('active', C['primary'])])

    # -----------------------------------------------------------------------
    # Ajustes globales para widgets tk clásicos (tooltips de color de selección)
    # -----------------------------------------------------------------------
    if root is not None:
        try:
            root.option_add('*Entry.selectBackground', C['primary'])
            root.option_add('*Entry.selectForeground', '#ffffff')
            root.option_add('*Text.selectBackground', C['primary'])
            root.option_add('*Text.selectForeground', '#ffffff')
        except Exception:
            pass

    return style

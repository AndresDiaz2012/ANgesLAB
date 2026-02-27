"""
Ventana de Configuración Administrativa
ANgesLAB - Sistema de Gestión de Laboratorio Clínico

Interfaz gráfica para gestionar toda la configuración administrativa del laboratorio.

Copyright © 2024-2025 ANgesLAB Solutions
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, colorchooser
from modulos.config_administrativa import ConfiguradorAdministrativo


class VentanaConfigAdministrativa:
    """
    Ventana para configurar todos los aspectos administrativos del laboratorio.
    """

    def __init__(self, parent, db, callback_guardar=None):
        """
        Inicializa la ventana de configuración administrativa.

        Args:
            parent: Ventana padre
            db: Conexión a la base de datos
            callback_guardar: Función a llamar después de guardar exitosamente
        """
        self.db = db
        self.configurador = ConfiguradorAdministrativo(db)
        self.callback_guardar = callback_guardar

        # Crear ventana
        self.win = tk.Toplevel(parent)
        self.win.title("Configuración Administrativa del Laboratorio")

        # Hacer ventana responsiva
        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()

        width = min(int(screen_width * 0.85), 1100)
        height = min(int(screen_height * 0.85), 750)
        width = max(width, 900)
        height = max(height, 650)

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.win.geometry(f"{width}x{height}+{x}+{y}")
        self.win.resizable(True, True)
        self.win.minsize(900, 650)
        self.win.grab_set()
        self.win.focus_set()

        self._crear_interfaz()
        self._cargar_configuracion()

    def _crear_interfaz(self):
        """Crea la interfaz con pestañas."""
        # Contenedor principal
        main_container = ttk.Frame(self.win, padding="10")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Título
        titulo_frame = ttk.Frame(main_container)
        titulo_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            titulo_frame,
            text="⚙️ Configuración Administrativa del Laboratorio",
            font=('Segoe UI', 16, 'bold')
        ).pack(side=tk.LEFT)

        # Notebook con pestañas
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Crear pestañas
        self._crear_tab_informacion()
        self._crear_tab_impresion()
        self._crear_tab_resultados()
        self._crear_tab_financiera()
        self._crear_tab_firma()
        self._crear_tab_textos()

        # Botones de acción (fijos abajo)
        btn_frame = ttk.Frame(main_container, relief="raised", borderwidth=1, padding="10")
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame,
            text="💾 Guardar Todos los Cambios",
            command=self._guardar_todo,
            style='Accent.TButton'
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            btn_frame,
            text="✗ Cancelar",
            command=self.win.destroy
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            btn_frame,
            text="🔄 Recargar",
            command=self._cargar_configuracion
        ).pack(side=tk.LEFT, padx=5)

    def _crear_tab_informacion(self):
        """Crea la pestaña de información del laboratorio."""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text="📋 Información General")

        # Scroll
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Contenido
        # Nombre y Razón Social
        ttk.Label(scrollable_frame, text="Nombre del Laboratorio:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, sticky='w', pady=5)
        self.entry_nombre = ttk.Entry(scrollable_frame, width=60, font=('Segoe UI', 10))
        self.entry_nombre.grid(row=0, column=1, sticky='ew', pady=5, padx=5)

        ttk.Label(scrollable_frame, text="Razón Social:", font=('Segoe UI', 10, 'bold')).grid(row=1, column=0, sticky='w', pady=5)
        self.entry_razon = ttk.Entry(scrollable_frame, width=60, font=('Segoe UI', 10))
        self.entry_razon.grid(row=1, column=1, sticky='ew', pady=5, padx=5)

        ttk.Label(scrollable_frame, text="RIF / NIT:", font=('Segoe UI', 10, 'bold')).grid(row=2, column=0, sticky='w', pady=5)
        self.entry_rif = ttk.Entry(scrollable_frame, width=60, font=('Segoe UI', 10))
        self.entry_rif.grid(row=2, column=1, sticky='ew', pady=5, padx=5)

        # Dirección
        ttk.Label(scrollable_frame, text="Dirección:", font=('Segoe UI', 10, 'bold')).grid(row=3, column=0, sticky='nw', pady=5)
        self.text_direccion = tk.Text(scrollable_frame, width=60, height=3, font=('Segoe UI', 10), wrap='word')
        self.text_direccion.grid(row=3, column=1, sticky='ew', pady=5, padx=5)

        # Teléfonos
        ttk.Label(scrollable_frame, text="Teléfono 1:", font=('Segoe UI', 10, 'bold')).grid(row=4, column=0, sticky='w', pady=5)
        self.entry_tel1 = ttk.Entry(scrollable_frame, width=60, font=('Segoe UI', 10))
        self.entry_tel1.grid(row=4, column=1, sticky='ew', pady=5, padx=5)

        ttk.Label(scrollable_frame, text="Teléfono 2:", font=('Segoe UI', 10, 'bold')).grid(row=5, column=0, sticky='w', pady=5)
        self.entry_tel2 = ttk.Entry(scrollable_frame, width=60, font=('Segoe UI', 10))
        self.entry_tel2.grid(row=5, column=1, sticky='ew', pady=5, padx=5)

        # Email y Web
        ttk.Label(scrollable_frame, text="Email:", font=('Segoe UI', 10, 'bold')).grid(row=6, column=0, sticky='w', pady=5)
        self.entry_email = ttk.Entry(scrollable_frame, width=60, font=('Segoe UI', 10))
        self.entry_email.grid(row=6, column=1, sticky='ew', pady=5, padx=5)

        ttk.Label(scrollable_frame, text="Sitio Web:", font=('Segoe UI', 10, 'bold')).grid(row=7, column=0, sticky='w', pady=5)
        self.entry_web = ttk.Entry(scrollable_frame, width=60, font=('Segoe UI', 10))
        self.entry_web.grid(row=7, column=1, sticky='ew', pady=5, padx=5)

        # Logo
        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=8, column=0, columnspan=2, sticky='ew', pady=15)

        ttk.Label(scrollable_frame, text="Logo del Laboratorio:", font=('Segoe UI', 11, 'bold')).grid(row=9, column=0, columnspan=2, sticky='w', pady=5)

        # Frame para controles del logo
        logo_frame = ttk.Frame(scrollable_frame)
        logo_frame.grid(row=10, column=0, columnspan=2, sticky='ew', pady=5)

        self.label_logo = ttk.Label(logo_frame, text="No se ha seleccionado logo", foreground='gray')
        self.label_logo.pack(side=tk.LEFT, padx=5)

        ttk.Button(logo_frame, text="📁 Seleccionar Logo", command=self._seleccionar_logo).pack(side=tk.LEFT, padx=5)

        self.check_mostrar_logo = ttk.Checkbutton(logo_frame, text="Mostrar logo en PDFs")
        self.check_mostrar_logo.pack(side=tk.LEFT, padx=15)
        self.var_mostrar_logo = tk.BooleanVar(value=True)
        self.check_mostrar_logo.configure(variable=self.var_mostrar_logo)

        # Forma del logo en PDFs
        forma_frame = ttk.Frame(scrollable_frame)
        forma_frame.grid(row=11, column=0, columnspan=2, sticky='ew', pady=10)

        ttk.Label(forma_frame, text="Forma del logo en PDFs:", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        self.combo_forma_logo = ttk.Combobox(forma_frame, values=['Cuadrado', 'Circular', 'Redondeado', 'Original'],
                                             state='readonly', width=15)
        self.combo_forma_logo.set('Cuadrado')
        self.combo_forma_logo.pack(side=tk.LEFT, padx=5)

        ttk.Label(forma_frame, text="ℹ️", font=('Segoe UI', 12), foreground='blue').pack(side=tk.LEFT, padx=2)
        ttk.Label(forma_frame, text="Define cómo se verá el logo en los reportes PDF",
                 font=('Segoe UI', 9), foreground='gray').pack(side=tk.LEFT, padx=5)

        # Frame dedicado para la vista previa del logo
        self.logo_preview_frame = ttk.Frame(scrollable_frame, relief='solid', borderwidth=1)
        self.logo_preview_frame.grid(row=12, column=0, columnspan=2, pady=10)

        # Label para la vista previa (se actualizará dinámicamente)
        self.logo_preview_label = ttk.Label(self.logo_preview_frame, text="Vista previa del logo aparecerá aquí",
                                           foreground='gray', padding=20)
        self.logo_preview_label.pack()

        scrollable_frame.columnconfigure(1, weight=1)

        # Guardar referencia al tab y a la imagen actual
        self.logo_ruta_temporal = None
        self.logo_preview_photo = None  # Mantener referencia a la imagen para evitar garbage collection

    def _crear_tab_con_scroll(self, titulo_tab):
        """Crea una pestaña con scrolling.

        Retorna: (tab_frame, scrollable_frame) para agregar widgets
        """
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text=titulo_tab)

        # Scroll
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return tab, scrollable_frame

    def _crear_tab_impresion(self):
        """Crea la pestaña de configuración de impresión."""
        tab, scrollable_frame = self._crear_tab_con_scroll("🖨️ Impresión")

        row = 0

        # Formato de impresión
        ttk.Label(scrollable_frame, text="Formato de Resultados:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.var_formato = tk.StringVar(value="Completa")
        ttk.Radiobutton(scrollable_frame, text="Hoja Completa (formato estándar)", variable=self.var_formato, value="Completa").grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        ttk.Radiobutton(scrollable_frame, text="Media Hoja (formato compacto)", variable=self.var_formato, value="MediaHoja").grid(row=row, column=0, sticky='w', padx=20)
        row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=15)
        row += 1

        # Tamaño de papel
        ttk.Label(scrollable_frame, text="Tamaño de Papel:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.combo_papel = ttk.Combobox(scrollable_frame, state='readonly', width=30)
        self.combo_papel['values'] = ('Carta (8.5" x 11")', 'A4 (21cm x 29.7cm)', 'Oficio (8.5" x 13")')
        self.combo_papel.grid(row=row, column=0, sticky='w', padx=20, pady=5)
        row += 1

        # Orientación
        ttk.Label(scrollable_frame, text="Orientación:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.var_orientacion = tk.StringVar(value="Vertical")
        ttk.Radiobutton(scrollable_frame, text="Vertical (Portrait)", variable=self.var_orientacion, value="Vertical").grid(row=row, column=0, sticky='w', padx=20)
        row += 1
        ttk.Radiobutton(scrollable_frame, text="Horizontal (Landscape)", variable=self.var_orientacion, value="Horizontal").grid(row=row, column=0, sticky='w', padx=20)
        row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=15)
        row += 1

        # Márgenes
        ttk.Label(scrollable_frame, text="Márgenes (cm):", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        margenes_frame = ttk.Frame(scrollable_frame)
        margenes_frame.grid(row=row, column=0, sticky='w', padx=20)

        ttk.Label(margenes_frame, text="Superior:").grid(row=0, column=0, sticky='w', padx=5)
        self.spin_margen_sup = ttk.Spinbox(margenes_frame, from_=0.5, to=5.0, increment=0.5, width=10)
        self.spin_margen_sup.grid(row=0, column=1, padx=5)

        ttk.Label(margenes_frame, text="Inferior:").grid(row=0, column=2, sticky='w', padx=5)
        self.spin_margen_inf = ttk.Spinbox(margenes_frame, from_=0.5, to=5.0, increment=0.5, width=10)
        self.spin_margen_inf.grid(row=0, column=3, padx=5)

        ttk.Label(margenes_frame, text="Izquierdo:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.spin_margen_izq = ttk.Spinbox(margenes_frame, from_=0.5, to=5.0, increment=0.5, width=10)
        self.spin_margen_izq.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(margenes_frame, text="Derecho:").grid(row=1, column=2, sticky='w', padx=5, pady=5)
        self.spin_margen_der = ttk.Spinbox(margenes_frame, from_=0.5, to=5.0, increment=0.5, width=10)
        self.spin_margen_der.grid(row=1, column=3, padx=5, pady=5)

    def _crear_tab_resultados(self):
        """Crea la pestaña de configuración de visualización de resultados."""
        tab, scrollable_frame = self._crear_tab_con_scroll("📊 Resultados")

        row = 0

        ttk.Label(scrollable_frame, text="Visualización de Resultados:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.var_valores_ref = tk.BooleanVar(value=True)
        ttk.Checkbutton(scrollable_frame, text="Mostrar valores de referencia", variable=self.var_valores_ref).grid(row=row, column=0, sticky='w', padx=20)
        row += 1

        self.var_unidades = tk.BooleanVar(value=True)
        ttk.Checkbutton(scrollable_frame, text="Mostrar unidades de medida", variable=self.var_unidades).grid(row=row, column=0, sticky='w', padx=20)
        row += 1

        self.var_metodo = tk.BooleanVar(value=False)
        ttk.Checkbutton(scrollable_frame, text="Mostrar método de análisis", variable=self.var_metodo).grid(row=row, column=0, sticky='w', padx=20)
        row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=15)
        row += 1

        # Resaltado de valores anormales
        ttk.Label(scrollable_frame, text="Resaltado de Valores Anormales:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.var_resaltar = tk.BooleanVar(value=True)
        ttk.Checkbutton(scrollable_frame, text="Resaltar valores fuera de rango", variable=self.var_resaltar).grid(row=row, column=0, sticky='w', padx=20)
        row += 1

        colores_frame = ttk.Frame(tab)
        colores_frame.grid(row=row, column=0, sticky='w', padx=40, pady=10)

        ttk.Label(colores_frame, text="Color para valores ALTOS:").grid(row=0, column=0, sticky='w')
        self.btn_color_alto = tk.Button(colores_frame, text="  ", bg="#FF0000", width=5, command=lambda: self._seleccionar_color('alto'))
        self.btn_color_alto.grid(row=0, column=1, padx=10)
        self.color_alto = "#FF0000"

        ttk.Label(colores_frame, text="Color para valores BAJOS:").grid(row=1, column=0, sticky='w', pady=5)
        self.btn_color_bajo = tk.Button(colores_frame, text="  ", bg="#0000FF", width=5, command=lambda: self._seleccionar_color('bajo'))
        self.btn_color_bajo.grid(row=1, column=1, padx=10, pady=5)
        self.color_bajo = "#0000FF"

    def _crear_tab_financiera(self):
        """Crea la pestaña de configuración financiera."""
        tab, scrollable_frame = self._crear_tab_con_scroll("💰 Financiera")

        row = 0

        # Moneda
        ttk.Label(scrollable_frame, text="Configuración de Moneda:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        mon_frame = ttk.Frame(scrollable_frame)
        mon_frame.grid(row=row, column=0, sticky='w', padx=20, pady=5)

        ttk.Label(mon_frame, text="Moneda Principal:").grid(row=0, column=0, sticky='w', padx=5)
        self.combo_moneda = ttk.Combobox(mon_frame, state='readonly', width=15)
        self.combo_moneda['values'] = ('USD', 'VES', 'EUR', 'COP', 'MXN')
        self.combo_moneda.grid(row=0, column=1, padx=5)

        ttk.Label(mon_frame, text="Símbolo:").grid(row=0, column=2, sticky='w', padx=15)
        self.entry_simbolo = ttk.Entry(mon_frame, width=10)
        self.entry_simbolo.grid(row=0, column=3, padx=5)

        ttk.Label(mon_frame, text="Decimales:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.spin_decimales = ttk.Spinbox(mon_frame, from_=0, to=4, width=15)
        self.spin_decimales.grid(row=1, column=1, padx=5, pady=5)

        row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=15)
        row += 1

        # IVA y Descuentos
        ttk.Label(scrollable_frame, text="Impuestos y Descuentos:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        imp_frame = ttk.Frame(scrollable_frame)
        imp_frame.grid(row=row, column=0, sticky='w', padx=20)

        ttk.Label(imp_frame, text="IVA por Defecto (%):").grid(row=0, column=0, sticky='w', padx=5)
        self.spin_iva = ttk.Spinbox(imp_frame, from_=0, to=100, increment=0.5, width=15)
        self.spin_iva.grid(row=0, column=1, padx=5)

        ttk.Label(imp_frame, text="Descuento Máximo (%):").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.spin_desc_max = ttk.Spinbox(imp_frame, from_=0, to=100, increment=5, width=15)
        self.spin_desc_max.grid(row=1, column=1, padx=5, pady=5)

    def _crear_tab_firma(self):
        """Crea la pestaña de firma y autorización."""
        tab, scrollable_frame = self._crear_tab_con_scroll("✍️ Firma")

        row = 0

        ttk.Label(scrollable_frame, text="Información del Director/Responsable:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        ttk.Label(scrollable_frame, text="Nombre Completo:").grid(row=row, column=0, sticky='w', padx=20, pady=5)
        self.entry_director = ttk.Entry(scrollable_frame, width=50)
        self.entry_director.grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        ttk.Label(scrollable_frame, text="Título/Especialidad:").grid(row=row, column=0, sticky='w', padx=20, pady=5)
        self.entry_titulo = ttk.Entry(scrollable_frame, width=50)
        self.entry_titulo.grid(row=row, column=1, sticky='w', pady=5)
        row += 1

        self.var_mostrar_firma = tk.BooleanVar(value=True)
        ttk.Checkbutton(scrollable_frame, text="Mostrar firma en resultados", variable=self.var_mostrar_firma).grid(row=row, column=0, columnspan=2, sticky='w', padx=20, pady=10)
        row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky='ew', pady=15)
        row += 1

        ttk.Label(scrollable_frame, text="Texto de Autorización:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='nw', pady=10)
        row += 1

        self.text_autorizacion = tk.Text(scrollable_frame, width=60, height=4, wrap='word')
        self.text_autorizacion.grid(row=row, column=0, columnspan=2, sticky='ew', padx=20, pady=5)
        row += 1

        ttk.Label(scrollable_frame, text="Ejemplo: 'Resultados válidos solo con firma y sello del laboratorio'", foreground='gray', font=('Segoe UI', 9)).grid(row=row, column=0, columnspan=2, sticky='w', padx=20)

    def _crear_tab_textos(self):
        """Crea la pestaña de textos personalizados."""
        tab, scrollable_frame = self._crear_tab_con_scroll("📝 Textos")

        row = 0

        # Horario
        ttk.Label(scrollable_frame, text="Horario de Atención:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.text_horario = tk.Text(scrollable_frame, width=60, height=3, wrap='word')
        self.text_horario.grid(row=row, column=0, sticky='ew', padx=20, pady=5)
        row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, sticky='ew', pady=15)
        row += 1

        # Encabezado
        ttk.Label(scrollable_frame, text="Texto de Encabezado:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.text_encabezado = tk.Text(scrollable_frame, width=60, height=3, wrap='word')
        self.text_encabezado.grid(row=row, column=0, sticky='ew', padx=20, pady=5)
        row += 1

        ttk.Separator(scrollable_frame, orient='horizontal').grid(row=row, column=0, sticky='ew', pady=15)
        row += 1

        # Pie de página
        ttk.Label(scrollable_frame, text="Texto de Pie de Página:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.text_pie = tk.Text(scrollable_frame, width=60, height=3, wrap='word')
        self.text_pie.grid(row=row, column=0, sticky='ew', padx=20, pady=5)
        row += 1

        ttk.Separator(tab, orient='horizontal').grid(row=row, column=0, sticky='ew', pady=15)
        row += 1

        # Notas
        ttk.Label(tab, text="Notas para Resultados:", font=('Segoe UI', 11, 'bold')).grid(row=row, column=0, sticky='w', pady=10)
        row += 1

        self.text_notas = tk.Text(tab, width=60, height=4, wrap='word')
        self.text_notas.grid(row=row, column=0, sticky='ew', padx=20, pady=5)

        scrollable_frame.columnconfigure(0, weight=1)

    def _seleccionar_logo(self):
        """Permite seleccionar un archivo de logo."""
        filename = filedialog.askopenfilename(
            title="Seleccionar Logo del Laboratorio",
            filetypes=[
                ("Imágenes", "*.png *.jpg *.jpeg *.gif *.bmp"),
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("Todos los archivos", "*.*")
            ]
        )

        if filename:
            self.logo_ruta_temporal = filename
            nombre_archivo = filename.split('/')[-1].split('\\')[-1]  # Funciona en Windows y Unix
            self.label_logo.config(text=f"Seleccionado: {nombre_archivo}", foreground='green')

            # Mostrar vista previa del logo
            self._mostrar_preview_logo(filename)

    def _mostrar_preview_logo(self, ruta_imagen):
        """Muestra una vista previa del logo seleccionado."""
        try:
            # Importar PIL para manejar imágenes
            from PIL import Image, ImageTk

            # IMPORTANTE: Limpiar vista previa anterior
            # Destruir el label anterior para evitar superposición
            if self.logo_preview_label:
                self.logo_preview_label.destroy()

            # Limpiar referencia a imagen anterior para liberar memoria
            self.logo_preview_photo = None

            # Cargar y redimensionar la imagen
            img = Image.open(ruta_imagen)

            # Calcular nuevo tamaño manteniendo proporción (máximo 200x200)
            max_size = 200
            img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # Convertir a PhotoImage para Tkinter
            self.logo_preview_photo = ImageTk.PhotoImage(img)

            # Crear NUEVO label para la vista previa
            self.logo_preview_label = ttk.Label(self.logo_preview_frame, image=self.logo_preview_photo)
            self.logo_preview_label.pack(padx=10, pady=10)

        except ImportError:
            # Si PIL no está disponible, mostrar mensaje
            if self.logo_preview_label:
                self.logo_preview_label.destroy()

            self.logo_preview_label = ttk.Label(
                self.logo_preview_frame,
                text="PIL/Pillow no instalado.\nEjecute: pip install Pillow",
                foreground='orange',
                padding=20
            )
            self.logo_preview_label.pack()

        except Exception as e:
            # Error al cargar la imagen
            if self.logo_preview_label:
                self.logo_preview_label.destroy()

            self.logo_preview_label = ttk.Label(
                self.logo_preview_frame,
                text=f"Error al cargar imagen:\n{str(e)}",
                foreground='red',
                padding=20
            )
            self.logo_preview_label.pack()

    def _seleccionar_color(self, tipo):
        """Permite seleccionar un color."""
        color_actual = self.color_alto if tipo == 'alto' else self.color_bajo
        color = colorchooser.askcolor(color=color_actual)

        if color[1]:  # color[1] es el valor hexadecimal
            if tipo == 'alto':
                self.color_alto = color[1]
                self.btn_color_alto.config(bg=color[1])
            else:
                self.color_bajo = color[1]
                self.btn_color_bajo.config(bg=color[1])

    def _cargar_configuracion(self):
        """Carga la configuración actual en la interfaz."""
        try:
            config = self.configurador.obtener_configuracion()

            if not config:
                messagebox.showwarning(
                    "Sin Configuración",
                    "No se encontró configuración administrativa.\n"
                    "Por favor, ejecute el script:\n"
                    "scripts/agregar_config_administrativa.py"
                )
                return

            # Información general
            self.entry_nombre.delete(0, tk.END)
            self.entry_nombre.insert(0, config.get('NombreLaboratorio') or '')

            self.entry_razon.delete(0, tk.END)
            self.entry_razon.insert(0, config.get('RazonSocial') or '')

            self.entry_rif.delete(0, tk.END)
            self.entry_rif.insert(0, config.get('RIF') or '')

            self.text_direccion.delete('1.0', tk.END)
            self.text_direccion.insert('1.0', config.get('Direccion') or '')

            self.entry_tel1.delete(0, tk.END)
            self.entry_tel1.insert(0, config.get('Telefono1') or '')

            self.entry_tel2.delete(0, tk.END)
            self.entry_tel2.insert(0, config.get('Telefono2') or '')

            self.entry_email.delete(0, tk.END)
            self.entry_email.insert(0, config.get('Email') or '')

            self.entry_web.delete(0, tk.END)
            self.entry_web.insert(0, config.get('SitioWeb') or '')

            # Logo
            if config.get('RutaLogo'):
                import os
                ruta_logo = config['RutaLogo']
                nombre_archivo = ruta_logo.split('\\')[-1].split('/')[-1]
                self.label_logo.config(text=f"Logo actual: {nombre_archivo}", foreground='blue')

                # Mostrar vista previa del logo existente si el archivo existe
                if os.path.exists(ruta_logo):
                    self._mostrar_preview_logo(ruta_logo)
                else:
                    # Limpiar vista previa si el archivo no existe
                    if self.logo_preview_label:
                        self.logo_preview_label.destroy()

                    self.logo_preview_label = ttk.Label(
                        self.logo_preview_frame,
                        text=f"Logo no encontrado:\n{nombre_archivo}",
                        foreground='red',
                        padding=20
                    )
                    self.logo_preview_label.pack()

            self.var_mostrar_logo.set(config.get('MostrarLogo', True))

            # Forma del logo
            forma_logo = config.get('FormaLogo', 'Cuadrado')
            self.combo_forma_logo.set(forma_logo)

            # Impresión
            self.var_formato.set(config.get('FormatoImpresion', 'Completa'))

            papel = config.get('TamanoPapel', 'Carta')
            if papel == 'Carta':
                self.combo_papel.current(0)
            elif papel == 'A4':
                self.combo_papel.current(1)
            else:
                self.combo_papel.current(2)

            self.var_orientacion.set(config.get('Orientacion', 'Vertical'))

            self.spin_margen_sup.delete(0, tk.END)
            self.spin_margen_sup.insert(0, config.get('MargenSuperior', 2.0))

            self.spin_margen_inf.delete(0, tk.END)
            self.spin_margen_inf.insert(0, config.get('MargenInferior', 2.0))

            self.spin_margen_izq.delete(0, tk.END)
            self.spin_margen_izq.insert(0, config.get('MargenIzquierdo', 2.5))

            self.spin_margen_der.delete(0, tk.END)
            self.spin_margen_der.insert(0, config.get('MargenDerecho', 2.5))

            # Resultados
            self.var_valores_ref.set(config.get('MostrarValoresReferencia', True))
            self.var_unidades.set(config.get('MostrarUnidades', True))
            self.var_metodo.set(config.get('MostrarMetodo', False))
            self.var_resaltar.set(config.get('ResaltarAnormales', True))

            self.color_alto = config.get('ColorAlto', '#FF0000')
            self.btn_color_alto.config(bg=self.color_alto)

            self.color_bajo = config.get('ColorBajo', '#0000FF')
            self.btn_color_bajo.config(bg=self.color_bajo)

            # Financiera
            self.combo_moneda.set(config.get('MonedaPrincipal', 'USD'))

            self.entry_simbolo.delete(0, tk.END)
            self.entry_simbolo.insert(0, config.get('SimboloMoneda', '$'))

            self.spin_decimales.delete(0, tk.END)
            self.spin_decimales.insert(0, config.get('DecimalesPrecios', 2))

            self.spin_iva.delete(0, tk.END)
            self.spin_iva.insert(0, config.get('IVAPorDefecto', 16.0))

            self.spin_desc_max.delete(0, tk.END)
            self.spin_desc_max.insert(0, config.get('DescuentoMaximo', 50.0))

            # Firma
            self.entry_director.delete(0, tk.END)
            self.entry_director.insert(0, config.get('NombreDirector') or '')

            self.entry_titulo.delete(0, tk.END)
            self.entry_titulo.insert(0, config.get('TituloDirector') or '')

            self.var_mostrar_firma.set(config.get('MostrarFirma', True))

            self.text_autorizacion.delete('1.0', tk.END)
            self.text_autorizacion.insert('1.0', config.get('TextoAutorizacion') or '')

            # Textos
            self.text_horario.delete('1.0', tk.END)
            self.text_horario.insert('1.0', config.get('HorarioAtencion') or '')

            self.text_encabezado.delete('1.0', tk.END)
            self.text_encabezado.insert('1.0', config.get('TextoEncabezado') or '')

            self.text_pie.delete('1.0', tk.END)
            self.text_pie.insert('1.0', config.get('TextoPiePagina') or '')

            self.text_notas.delete('1.0', tk.END)
            self.text_notas.insert('1.0', config.get('NotasResultados') or '')

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar configuración: {e}")

    def _guardar_todo(self):
        """Guarda todas las configuraciones."""
        try:
            # Información básica
            datos_info = {
                'NombreLaboratorio': self.entry_nombre.get().strip(),
                'RazonSocial': self.entry_razon.get().strip(),
                'RIF': self.entry_rif.get().strip(),
                'Direccion': self.text_direccion.get('1.0', tk.END).strip(),
                'Telefono1': self.entry_tel1.get().strip(),
                'Telefono2': self.entry_tel2.get().strip(),
                'Email': self.entry_email.get().strip(),
                'SitioWeb': self.entry_web.get().strip()
            }

            self.configurador.actualizar_informacion_basica(datos_info)

            # Logo
            if self.logo_ruta_temporal:
                self.configurador.guardar_logo(self.logo_ruta_temporal)

            # Impresión
            papel_map = {0: 'Carta', 1: 'A4', 2: 'Oficio'}
            datos_imp = {
                'FormatoImpresion': self.var_formato.get(),
                'TamanoPapel': papel_map.get(self.combo_papel.current(), 'Carta'),
                'Orientacion': self.var_orientacion.get(),
                'MargenSuperior': float(self.spin_margen_sup.get()),
                'MargenInferior': float(self.spin_margen_inf.get()),
                'MargenIzquierdo': float(self.spin_margen_izq.get()),
                'MargenDerecho': float(self.spin_margen_der.get()),
                'MostrarLogo': self.var_mostrar_logo.get(),
                'FormaLogo': self.combo_forma_logo.get()
            }

            self.configurador.actualizar_configuracion_impresion(datos_imp)

            # Resultados
            datos_res = {
                'MostrarValoresReferencia': self.var_valores_ref.get(),
                'MostrarUnidades': self.var_unidades.get(),
                'MostrarMetodo': self.var_metodo.get(),
                'ResaltarAnormales': self.var_resaltar.get(),
                'ColorAlto': self.color_alto,
                'ColorBajo': self.color_bajo
            }

            self.configurador.actualizar_configuracion_resultados(datos_res)

            # Financiera
            datos_fin = {
                'MonedaPrincipal': self.combo_moneda.get(),
                'SimboloMoneda': self.entry_simbolo.get(),
                'DecimalesPrecios': int(self.spin_decimales.get()),
                'IVAPorDefecto': float(self.spin_iva.get()),
                'DescuentoMaximo': float(self.spin_desc_max.get())
            }

            self.configurador.actualizar_configuracion_financiera(datos_fin)

            # Firma
            datos_firma = {
                'NombreDirector': self.entry_director.get().strip(),
                'TituloDirector': self.entry_titulo.get().strip(),
                'MostrarFirma': self.var_mostrar_firma.get(),
                'TextoAutorizacion': self.text_autorizacion.get('1.0', tk.END).strip()
            }

            self.configurador.actualizar_firma_autorizacion(datos_firma)

            # Textos
            datos_textos = {
                'HorarioAtencion': self.text_horario.get('1.0', tk.END).strip(),
                'TextoEncabezado': self.text_encabezado.get('1.0', tk.END).strip(),
                'TextoPiePagina': self.text_pie.get('1.0', tk.END).strip(),
                'NotasResultados': self.text_notas.get('1.0', tk.END).strip()
            }

            self.configurador.actualizar_textos_personalizados(datos_textos)

            messagebox.showinfo(
                "Éxito",
                "Configuración guardada correctamente.\n\n"
                "Los cambios se aplicarán inmediatamente en la interfaz."
            )

            # Llamar al callback si existe
            if self.callback_guardar:
                try:
                    self.callback_guardar()
                except Exception as callback_error:
                    print(f"Error en callback: {callback_error}")

            # Cerrar la ventana
            self.win.destroy()

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar configuración: {e}")


def abrir_ventana_config_administrativa(parent, db, callback_guardar=None):
    """
    Función de conveniencia para abrir la ventana de configuración administrativa.

    Args:
        parent: Ventana padre
        db: Conexión a la base de datos
        callback_guardar: Función a llamar después de guardar exitosamente
    """
    VentanaConfigAdministrativa(parent, db, callback_guardar)

"""
Ventana de Configuración Completa
ANgesLAB - Sistema de Gestión de Laboratorio Clínico

Configuración integral del sistema con todas las opciones:
- Información del Sistema
- Numeración de Solicitudes
- Precios
- Personalización (Nombre, Logo, Usuario, Contraseña)
- Impresión
- Resetear Base de Datos

Copyright © 2024-2026 ANgesLAB Solutions
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
from datetime import datetime
import os


class VentanaConfiguracionCompleta:
    """
    Ventana completa de configuración del sistema.
    """

    def __init__(self, parent, db, user, callback_actualizar=None):
        """
        Args:
            parent: Ventana padre
            db: Conexión a la base de datos
            user: Datos del usuario actual
            callback_actualizar: Función a llamar tras guardar cambios
        """
        self.db = db
        self.user = user
        self.callback_actualizar = callback_actualizar

        # Crear ventana
        self.win = tk.Toplevel(parent)
        self.win.title("⚙️ Configuración del Sistema - ANgesLAB")

        # Hacer ventana responsiva
        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()

        width = min(int(screen_width * 0.9), 1200)
        height = min(int(screen_height * 0.9), 800)
        width = max(width, 1000)
        height = max(height, 700)

        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.win.geometry(f"{width}x{height}+{x}+{y}")
        self.win.resizable(True, True)
        self.win.minsize(1000, 700)
        self.win.grab_set()
        self.win.focus_set()

        self._crear_interfaz()

    def _crear_interfaz(self):
        """Crea la interfaz con pestañas."""
        # Contenedor principal
        main_container = ttk.Frame(self.win, padding="15")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Título
        titulo_frame = ttk.Frame(main_container)
        titulo_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            titulo_frame,
            text="⚙️ Configuración del Sistema",
            font=('Segoe UI', 18, 'bold')
        ).pack(side=tk.LEFT)

        # Notebook con pestañas
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Crear pestañas según nivel de acceso
        # Jerarquía: Desarrollador > Administrador > Usuarios
        es_dev = self.user.get('Nivel') == 'Desarrollador'
        es_admin_o_dev = self.user.get('Nivel') in ('Administrador', 'Desarrollador')

        self._crear_tab_informacion()
        if es_admin_o_dev:
            self._crear_tab_numeracion()
            self._crear_tab_precios()
        self._crear_tab_personalizacion()
        if es_admin_o_dev:
            self._crear_tab_usuarios()
            self._crear_tab_bioanalistas()
        self._crear_tab_impresion()
        # Resetear BD: SOLO Desarrollador (protege integridad del producto)
        if es_dev:
            self._crear_tab_resetear_bd()

        # Botones de acción (fijos abajo)
        btn_frame = ttk.Frame(main_container, relief="raised", borderwidth=1, padding="10")
        btn_frame.pack(fill=tk.X)

        ttk.Button(
            btn_frame,
            text="✗ Cerrar",
            command=self.win.destroy
        ).pack(side=tk.RIGHT, padx=5)

        ttk.Button(
            btn_frame,
            text="🔄 Recargar",
            command=self._cargar_todo
        ).pack(side=tk.LEFT, padx=5)

        # Cargar configuración inicial
        self._cargar_personalizacion()

    def _crear_tab_con_scroll(self, titulo_tab):
        """Crea una pestaña con scrolling."""
        tab = ttk.Frame(self.notebook, padding="15")
        self.notebook.add(tab, text=titulo_tab)

        # Canvas para scrolling
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

        # Mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        return tab, scrollable_frame

    def _crear_tab_informacion(self):
        """Pestaña 1: Información del Sistema"""
        tab, frame = self._crear_tab_con_scroll("📊 Información del Sistema")

        # Info del sistema
        ttk.Label(frame, text="Información del Sistema", font=('Segoe UI', 14, 'bold')).grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 20))

        info = [
            ("Versión:", "1.0.0"),
            ("Base de datos:", "ANgesLAB.accdb"),
            ("Usuario actual:", self.user.get('NombreCompleto', 'N/A')),
            ("Nombre de usuario:", self.user.get('NombreUsuario', 'N/A')),
            ("Nivel de acceso:", self.user.get('Nivel', 'Administrador')),
            ("Última actualización:", datetime.now().strftime('%d/%m/%Y %H:%M')),
        ]

        row = 1
        for label, value in info:
            ttk.Label(frame, text=label, font=('Segoe UI', 10, 'bold')).grid(
                row=row, column=0, sticky='w', pady=5, padx=(0, 20))
            ttk.Label(frame, text=value, font=('Segoe UI', 10)).grid(
                row=row, column=1, sticky='w', pady=5)
            row += 1

        # Separador
        ttk.Separator(frame, orient='horizontal').grid(
            row=row, column=0, columnspan=2, sticky='ew', pady=20)
        row += 1

        # Estadísticas
        ttk.Label(frame, text="Estadísticas de la Base de Datos", font=('Segoe UI', 14, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky='w', pady=(0, 20))
        row += 1

        stats = [
            ("Pacientes registrados:", self.db.count('Pacientes')),
            ("Médicos registrados:", self.db.count('Medicos')),
            ("Pruebas disponibles:", self.db.count('Pruebas')),
            ("Solicitudes totales:", self.db.count('Solicitudes')),
            ("Áreas clínicas:", self.db.count('Areas')),
        ]

        for label, value in stats:
            ttk.Label(frame, text=label, font=('Segoe UI', 10, 'bold')).grid(
                row=row, column=0, sticky='w', pady=5, padx=(0, 20))
            ttk.Label(frame, text=f"{value:,}", font=('Segoe UI', 10)).grid(
                row=row, column=1, sticky='w', pady=5)
            row += 1

    def _crear_tab_numeracion(self):
        """Pestaña 2: Numeración de Solicitudes"""
        tab, frame = self._crear_tab_con_scroll("🔢 Numeración")

        ttk.Label(frame, text="Configuración de Numeración de Solicitudes",
                 font=('Segoe UI', 14, 'bold')).grid(row=0, column=0, columnspan=2, sticky='w', pady=(0, 20))

        ttk.Label(frame, text="Esta configuración se encuentra en:",
                 font=('Segoe UI', 10)).grid(row=1, column=0, sticky='w', pady=10)

        ttk.Label(frame, text="⚙️ Configuración Administrativa > Numeración",
                 font=('Segoe UI', 10, 'italic'), foreground='blue').grid(row=2, column=0, sticky='w')

        # Botón para abrir configuración de numeración
        def abrir_config_numeracion():
            try:
                from modulos.ventana_config_numeracion import abrir_ventana_config_numeracion
                abrir_ventana_config_numeracion(self.win, self.db)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo abrir configuración de numeración:\n{e}")

        ttk.Button(frame, text="📝 Configurar Numeración de Solicitudes",
                  command=abrir_config_numeracion).grid(row=3, column=0, sticky='w', pady=20)

    def _crear_tab_precios(self):
        """Pestaña 3: Gestión de Precios"""
        tab, frame = self._crear_tab_con_scroll("💰 Precios")

        # Título
        ttk.Label(frame, text="Gestión de Precios de Pruebas",
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 10))

        # Instrucciones
        ttk.Label(frame, text="Seleccione una prueba de la lista y haga clic en 'Editar Precio' para modificar su valor.",
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 20))

        # Filtro por área
        filtro_frame = ttk.Frame(frame)
        filtro_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(filtro_frame, text="Filtrar por Área:",
                 font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        self.combo_filtro_area = ttk.Combobox(filtro_frame, state='readonly',
                                               width=35, font=('Segoe UI', 10))
        self.combo_filtro_area.pack(side=tk.LEFT, padx=(0, 10))
        self.combo_filtro_area.bind('<<ComboboxSelected>>', lambda e: self._cargar_precios())

        # Cargar áreas en el combobox
        self._areas_precios = []  # Lista de (AreaID, NombreArea)
        try:
            areas = self.db.query("SELECT AreaID, NombreArea FROM Areas ORDER BY NombreArea")
            self._areas_precios = [(a['AreaID'], a['NombreArea']) for a in areas]
        except Exception:
            pass
        nombres_areas = ['Todas las áreas'] + [a[1] for a in self._areas_precios]
        self.combo_filtro_area['values'] = nombres_areas
        self.combo_filtro_area.current(0)

        # Botones de acción (arriba de la lista)
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=(0, 10))

        ttk.Button(btn_frame, text="💵 Editar Precio",
                  command=self._editar_precio,
                  width=20).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="🔄 Actualizar Lista",
                  command=self._cargar_precios,
                  width=20).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="📈 Aplicar Incremento %",
                  command=lambda: self._aplicar_porcentaje_precios('incremento'),
                  width=22).pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="📉 Aplicar Descuento %",
                  command=lambda: self._aplicar_porcentaje_precios('descuento'),
                  width=22).pack(side=tk.LEFT, padx=5)

        # Lista de pruebas con precios
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill='both', expand=True, pady=10)

        cols = ('Código', 'Prueba', 'Área', 'Precio')
        self.tree_precios = ttk.Treeview(tree_frame, columns=cols, show='headings',
                                          height=20, selectmode='extended')

        # Configurar columnas
        self.tree_precios.heading('Código', text='Código')
        self.tree_precios.heading('Prueba', text='Nombre de la Prueba')
        self.tree_precios.heading('Área', text='Área')
        self.tree_precios.heading('Precio', text='Precio (USD)')

        self.tree_precios.column('Código', width=100, anchor='center')
        self.tree_precios.column('Prueba', width=350, anchor='w')
        self.tree_precios.column('Área', width=150, anchor='w')
        self.tree_precios.column('Precio', width=120, anchor='e')

        # Scrollbar
        scrollbar_precios = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree_precios.yview)
        self.tree_precios.configure(yscrollcommand=scrollbar_precios.set)

        self.tree_precios.pack(side=tk.LEFT, fill='both', expand=True)
        scrollbar_precios.pack(side=tk.RIGHT, fill='y')

        # Doble clic también edita
        self.tree_precios.bind('<Double-1>', lambda e: self._editar_precio())

        # Información adicional
        info_frame = ttk.Frame(frame)
        info_frame.pack(fill='x', pady=(10, 0))

        ttk.Label(info_frame, text="💡 Consejo: Haga doble clic en una prueba para editar su precio. "
                 "Seleccione varias pruebas (Ctrl+clic) para aplicar incremento/descuento solo a esas.",
                 font=('Segoe UI', 9), foreground='gray').pack(anchor='w')

        # Cargar precios
        self._cargar_precios()

    def _crear_tab_personalizacion(self):
        """Pestaña 4: Personalización"""
        tab, frame = self._crear_tab_con_scroll("🎨 Personalización")

        es_dev = self.user.get('Nivel') == 'Desarrollador'
        es_admin = self.user.get('Nivel') == 'Administrador'

        ttk.Label(frame, text="Personalización del Sistema",
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 5))
        ttk.Label(frame, text="Información general del laboratorio que aparecerá en reportes, facturas e impresiones.",
                 font=('Segoe UI', 10), foreground='gray').pack(anchor='w', pady=(0, 15))

        # ====== Información del Laboratorio ======
        if es_dev:
            # DESARROLLADOR: Acceso completo para editar datos del laboratorio
            info_frame = ttk.LabelFrame(frame, text="  Información del Laboratorio  ", padding=15)
            info_frame.pack(fill='x', pady=(0, 15))

            # Fila 1: Nombre
            f1 = ttk.Frame(info_frame)
            f1.pack(fill='x', pady=5)
            ttk.Label(f1, text="Nombre del Laboratorio:", font=('Segoe UI', 10, 'bold'), width=22, anchor='w').pack(side='left')
            self.entry_nombre_lab = ttk.Entry(f1, width=50, font=('Segoe UI', 10))
            self.entry_nombre_lab.pack(side='left', fill='x', expand=True, padx=(5, 0))

            # Fila 2: RIF
            f2 = ttk.Frame(info_frame)
            f2.pack(fill='x', pady=5)
            ttk.Label(f2, text="RIF:", font=('Segoe UI', 10, 'bold'), width=22, anchor='w').pack(side='left')
            self.entry_rif = ttk.Entry(f2, width=30, font=('Segoe UI', 10))
            self.entry_rif.pack(side='left', padx=(5, 0))

            # Fila 3: Dirección
            f3 = ttk.Frame(info_frame)
            f3.pack(fill='x', pady=5)
            ttk.Label(f3, text="Dirección:", font=('Segoe UI', 10, 'bold'), width=22, anchor='w').pack(side='left')
            self.entry_direccion = ttk.Entry(f3, width=60, font=('Segoe UI', 10))
            self.entry_direccion.pack(side='left', fill='x', expand=True, padx=(5, 0))

            # Fila 4: Teléfono + WhatsApp
            f4 = ttk.Frame(info_frame)
            f4.pack(fill='x', pady=5)
            ttk.Label(f4, text="Teléfono:", font=('Segoe UI', 10, 'bold'), width=22, anchor='w').pack(side='left')
            self.entry_telefono = ttk.Entry(f4, width=20, font=('Segoe UI', 10))
            self.entry_telefono.pack(side='left', padx=(5, 15))
            ttk.Label(f4, text="WhatsApp:", font=('Segoe UI', 10, 'bold')).pack(side='left')
            self.entry_whatsapp = ttk.Entry(f4, width=20, font=('Segoe UI', 10))
            self.entry_whatsapp.pack(side='left', padx=(5, 0))

            # Botones de edicion
            btn_f = ttk.Frame(info_frame)
            btn_f.pack(fill='x', pady=(15, 5))
            ttk.Button(btn_f, text="💾 Guardar Información del Laboratorio",
                      command=self._guardar_info_laboratorio).pack(side='left', padx=5)
            ttk.Button(btn_f, text="📁 Configurar Logo y Formato",
                      command=self._abrir_config_administrativa).pack(side='left', padx=5)

            ttk.Label(info_frame, text="Estos datos aparecerán en los encabezados de reportes de resultados, facturas e impresiones.",
                     font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(5, 0))

        elif es_admin:
            # ADMINISTRADOR: Solo lectura - puede ver pero NO editar los datos del laboratorio
            info_frame = ttk.LabelFrame(frame, text="  Información del Laboratorio (Solo Lectura)  ", padding=15)
            info_frame.pack(fill='x', pady=(0, 15))

            ttk.Label(info_frame,
                     text="Los datos del laboratorio son configurados por el proveedor del software.\n"
                          "Contacte al soporte técnico para modificar esta información.",
                     font=('Segoe UI', 10), foreground='#b45309',
                     wraplength=500, justify='left').pack(anchor='w', pady=(0, 10))

            # Mostrar datos en modo lectura (entries deshabilitados)
            campos_lectura = [
                ("Nombre del Laboratorio:", 'entry_nombre_lab', 50),
                ("RIF:", 'entry_rif', 30),
                ("Dirección:", 'entry_direccion', 60),
                ("Teléfono:", 'entry_telefono', 20),
                ("WhatsApp:", 'entry_whatsapp', 20),
            ]
            for etiqueta, attr_name, ancho in campos_lectura:
                fila = ttk.Frame(info_frame)
                fila.pack(fill='x', pady=3)
                ttk.Label(fila, text=etiqueta, font=('Segoe UI', 10, 'bold'),
                         width=22, anchor='w').pack(side='left')
                entry = ttk.Entry(fila, width=ancho, font=('Segoe UI', 10), state='readonly')
                entry.pack(side='left', fill='x', expand=True, padx=(5, 0))
                setattr(self, attr_name, entry)

        else:
            # Otros niveles: crear entries ocultos para evitar errores en _cargar_personalizacion
            self.entry_nombre_lab = ttk.Entry(frame)
            self.entry_rif = ttk.Entry(frame)
            self.entry_direccion = ttk.Entry(frame)
            self.entry_telefono = ttk.Entry(frame)
            self.entry_whatsapp = ttk.Entry(frame)

        # ====== Cambiar Mi Contraseña (todos) ======
        pass_frame = ttk.LabelFrame(frame, text="  Cambiar Mi Contraseña  ", padding=15)
        pass_frame.pack(fill='x', pady=(0, 15))

        ttk.Label(pass_frame, text=f"Usuario: {self.user.get('NombreUsuario', 'N/A')}",
                 font=('Segoe UI', 10, 'bold'), foreground='blue').pack(anchor='w', pady=(0, 10))

        pf1 = ttk.Frame(pass_frame)
        pf1.pack(fill='x', pady=3)
        ttk.Label(pf1, text="Contraseña actual:", width=20, anchor='w').pack(side='left')
        self.entry_pass_actual = ttk.Entry(pf1, width=30, show="*", font=('Segoe UI', 10))
        self.entry_pass_actual.pack(side='left', padx=(5, 0))

        pf2 = ttk.Frame(pass_frame)
        pf2.pack(fill='x', pady=3)
        ttk.Label(pf2, text="Nueva contraseña:", width=20, anchor='w').pack(side='left')
        self.entry_pass_nueva = ttk.Entry(pf2, width=30, show="*", font=('Segoe UI', 10))
        self.entry_pass_nueva.pack(side='left', padx=(5, 0))

        pf3 = ttk.Frame(pass_frame)
        pf3.pack(fill='x', pady=3)
        ttk.Label(pf3, text="Confirmar contraseña:", width=20, anchor='w').pack(side='left')
        self.entry_pass_confirmar = ttk.Entry(pf3, width=30, show="*", font=('Segoe UI', 10))
        self.entry_pass_confirmar.pack(side='left', padx=(5, 0))

        ttk.Button(pass_frame, text="🔒 Cambiar Mi Contraseña",
                  command=self._cambiar_contrasena).pack(anchor='w', pady=(15, 0))

    def _crear_tab_usuarios(self):
        """Pestaña: Gestión de Usuarios (solo Administrador)"""
        tab, frame = self._crear_tab_con_scroll("👥 Usuarios")

        ttk.Label(frame, text="Gestión de Usuarios",
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 5))
        ttk.Label(frame, text="Administre los usuarios del sistema y sus niveles de acceso.",
                 font=('Segoe UI', 10), foreground='gray').pack(anchor='w', pady=(0, 15))

        # Toolbar
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill='x', pady=(0, 10))

        ttk.Button(toolbar, text="➕ Nuevo Usuario",
                  command=self._nuevo_usuario).pack(side='left', padx=5)
        ttk.Button(toolbar, text="✏️ Editar Usuario",
                  command=self._editar_usuario).pack(side='left', padx=5)
        ttk.Button(toolbar, text="🔑 Cambiar Contraseña",
                  command=self._cambiar_contrasena_usuario).pack(side='left', padx=5)
        ttk.Button(toolbar, text="🔄 Refrescar",
                  command=self._cargar_usuarios).pack(side='left', padx=5)

        # Treeview de usuarios
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill='both', expand=True, pady=5)

        cols = ('ID', 'NombreCompleto', 'NombreUsuario', 'Nivel', 'Activo')
        self.tree_usuarios = ttk.Treeview(tree_frame, columns=cols, show='headings', height=10)
        self.tree_usuarios.heading('ID', text='ID')
        self.tree_usuarios.heading('NombreCompleto', text='Nombre Completo')
        self.tree_usuarios.heading('NombreUsuario', text='Usuario')
        self.tree_usuarios.heading('Nivel', text='Nivel')
        self.tree_usuarios.heading('Activo', text='Activo')
        self.tree_usuarios.column('ID', width=50, anchor='center')
        self.tree_usuarios.column('NombreCompleto', width=250)
        self.tree_usuarios.column('NombreUsuario', width=150)
        self.tree_usuarios.column('Nivel', width=120, anchor='center')
        self.tree_usuarios.column('Activo', width=80, anchor='center')

        scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree_usuarios.yview)
        self.tree_usuarios.configure(yscrollcommand=scroll.set)
        self.tree_usuarios.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        # Info
        texto_niveles = "Niveles: Desarrollador | Administrador | Facturador | Recepcion | Bioanalista | Consulta" \
            if self.user.get('Nivel') == 'Desarrollador' \
            else "Niveles: Administrador | Facturador | Recepcion | Bioanalista | Consulta"
        ttk.Label(frame, text=texto_niveles,
                 font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(10, 0))

        self._cargar_usuarios()

    def _cargar_usuarios(self):
        """Carga la lista de usuarios en el Treeview."""
        if not hasattr(self, 'tree_usuarios'):
            return
        for item in self.tree_usuarios.get_children():
            self.tree_usuarios.delete(item)
        try:
            usuarios = self.db.query("SELECT UsuarioID, NombreCompleto, NombreUsuario, Nivel, Activo FROM Usuarios ORDER BY UsuarioID")
            for u in usuarios:
                activo = "Sí" if u.get('Activo') else "No"
                nivel = u.get('Nivel') or 'Administrador'
                self.tree_usuarios.insert('', 'end', values=(
                    u['UsuarioID'], u.get('NombreCompleto', ''),
                    u.get('NombreUsuario', ''), nivel, activo
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar usuarios:\n{e}")

    def _nuevo_usuario(self):
        """Ventana para crear un nuevo usuario."""
        win = tk.Toplevel(self.win)
        win.title("Nuevo Usuario")
        win.geometry("400x350")
        win.grab_set()
        win.focus_set()
        win.resizable(False, False)

        # Centrar
        x = (win.winfo_screenwidth() - 400) // 2
        y = (win.winfo_screenheight() - 350) // 2
        win.geometry(f"400x350+{x}+{y}")

        main_f = ttk.Frame(win, padding=20)
        main_f.pack(fill='both', expand=True)

        ttk.Label(main_f, text="Crear Nuevo Usuario", font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(0, 15))

        ttk.Label(main_f, text="Nombre Completo:").pack(anchor='w', pady=(5, 2))
        entry_nombre = ttk.Entry(main_f, width=40, font=('Segoe UI', 10))
        entry_nombre.pack(anchor='w')

        ttk.Label(main_f, text="Nombre de Usuario:").pack(anchor='w', pady=(10, 2))
        entry_usuario = ttk.Entry(main_f, width=30, font=('Segoe UI', 10))
        entry_usuario.pack(anchor='w')

        ttk.Label(main_f, text="Contraseña:").pack(anchor='w', pady=(10, 2))
        entry_pass = ttk.Entry(main_f, width=30, show="*", font=('Segoe UI', 10))
        entry_pass.pack(anchor='w')

        ttk.Label(main_f, text="Confirmar Contraseña:").pack(anchor='w', pady=(5, 2))
        entry_pass_confirm = ttk.Entry(main_f, width=30, show="*", font=('Segoe UI', 10))
        entry_pass_confirm.pack(anchor='w')

        ttk.Label(main_f, text="Nivel:").pack(anchor='w', pady=(10, 2))
        # Niveles disponibles según el nivel del usuario actual
        niveles_disponibles = ['Administrador', 'Facturador', 'Recepcion', 'Bioanalista', 'Consulta']
        # Solo el Desarrollador puede crear otros Desarrolladores
        if self.user.get('Nivel') == 'Desarrollador':
            niveles_disponibles.insert(0, 'Desarrollador')
        combo_nivel = ttk.Combobox(main_f, values=niveles_disponibles,
                                    state='readonly', width=20, font=('Segoe UI', 10))
        combo_nivel.pack(anchor='w')
        combo_nivel.set('Recepcion')

        def guardar():
            from modulos.seguridad_db import SeguridadContrasenas

            nombre = entry_nombre.get().strip()
            usuario = entry_usuario.get().strip()
            pwd = entry_pass.get().strip()
            pwd_confirm = entry_pass_confirm.get().strip()
            nivel = combo_nivel.get()

            if not nombre or not usuario or not pwd:
                messagebox.showwarning("Aviso", "Complete todos los campos", parent=win)
                return

            if pwd != pwd_confirm:
                messagebox.showerror("Error", "Las contraseñas no coinciden", parent=win)
                return

            if len(pwd) < 4:
                messagebox.showwarning("Aviso", "La contraseña debe tener al menos 4 caracteres", parent=win)
                return

            if not nivel:
                messagebox.showwarning("Aviso", "Seleccione un nivel", parent=win)
                return

            # Verificar que no exista el usuario
            try:
                existente = self.db.query_one(
                    f"SELECT UsuarioID FROM Usuarios WHERE NombreUsuario='{usuario.replace(chr(39), chr(39)+chr(39))}'"
                )
                if existente:
                    messagebox.showerror("Error", "Ya existe un usuario con ese nombre", parent=win)
                    return

                # Generar hash de la contraseña
                pwd_hash, pwd_salt = SeguridadContrasenas.hash_password(pwd)

                self.db.insert('Usuarios', {
                    'NombreCompleto': nombre,
                    'NombreUsuario': usuario,
                    'Password': '',
                    'PasswordHash': pwd_hash,
                    'PasswordSalt': pwd_salt,
                    'Nivel': nivel,
                    'Activo': True
                })
                messagebox.showinfo("Éxito", f"Usuario '{usuario}' creado correctamente", parent=win)
                win.destroy()
                self._cargar_usuarios()
            except Exception as e:
                messagebox.showerror("Error", f"Error al crear usuario:\n{e}", parent=win)

        ttk.Button(main_f, text="💾 Crear Usuario", command=guardar).pack(anchor='w', pady=(20, 0))
        entry_nombre.focus()

    def _editar_usuario(self):
        """Ventana para editar un usuario existente (nivel, activo)."""
        sel = self.tree_usuarios.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un usuario de la lista")
            return

        values = self.tree_usuarios.item(sel[0])['values']
        user_id = values[0]
        nombre_actual = values[1]
        usuario_actual = values[2]
        nivel_actual = values[3]
        activo_actual = values[4] == "Sí"

        win = tk.Toplevel(self.win)
        win.title(f"Editar Usuario - {nombre_actual}")
        win.geometry("400x350")
        win.grab_set()
        win.focus_set()
        win.resizable(False, False)

        x = (win.winfo_screenwidth() - 400) // 2
        y = (win.winfo_screenheight() - 350) // 2
        win.geometry(f"400x350+{x}+{y}")

        main_f = ttk.Frame(win, padding=20)
        main_f.pack(fill='both', expand=True)

        ttk.Label(main_f, text=f"Editar: {nombre_actual}", font=('Segoe UI', 13, 'bold')).pack(anchor='w', pady=(0, 15))

        # Protección: solo un Desarrollador puede editar a otro Desarrollador
        if nivel_actual == 'Desarrollador' and self.user.get('Nivel') != 'Desarrollador':
            ttk.Label(main_f, text="No tiene permisos para editar un usuario Desarrollador.",
                     font=('Segoe UI', 10), foreground='red').pack(anchor='w', pady=20)
            ttk.Button(main_f, text="Cerrar", command=win.destroy).pack(anchor='w')
            return

        ttk.Label(main_f, text="Nombre Completo:").pack(anchor='w', pady=(5, 2))
        entry_nombre = ttk.Entry(main_f, width=40, font=('Segoe UI', 10))
        entry_nombre.pack(anchor='w')
        entry_nombre.insert(0, nombre_actual)

        ttk.Label(main_f, text="Nombre de Usuario:").pack(anchor='w', pady=(10, 2))
        entry_usuario = ttk.Entry(main_f, width=30, font=('Segoe UI', 10))
        entry_usuario.pack(anchor='w')
        entry_usuario.insert(0, usuario_actual)

        ttk.Label(main_f, text="Nivel:").pack(anchor='w', pady=(10, 2))
        niveles_disponibles = ['Administrador', 'Facturador', 'Recepcion', 'Bioanalista', 'Consulta']
        if self.user.get('Nivel') == 'Desarrollador':
            niveles_disponibles.insert(0, 'Desarrollador')
        combo_nivel = ttk.Combobox(main_f, values=niveles_disponibles,
                                    state='readonly', width=20, font=('Segoe UI', 10))
        combo_nivel.pack(anchor='w')
        # Compatibilidad: mapear nivel 'Operador' antiguo a 'Recepcion'
        nivel_set = nivel_actual if nivel_actual in niveles_disponibles else 'Recepcion'
        combo_nivel.set(nivel_set)

        var_activo = tk.BooleanVar(value=activo_actual)
        ttk.Checkbutton(main_f, text="Usuario Activo", variable=var_activo).pack(anchor='w', pady=(15, 0))

        def guardar():
            nombre = entry_nombre.get().strip()
            usuario = entry_usuario.get().strip()
            nivel = combo_nivel.get()

            if not nombre or not usuario:
                messagebox.showwarning("Aviso", "Complete todos los campos", parent=win)
                return

            # Verificar que no quede sin administradores/desarrolladores
            if nivel not in ('Administrador', 'Desarrollador') or not var_activo.get():
                try:
                    admins = self.db.query(
                        f"SELECT UsuarioID FROM Usuarios WHERE (Nivel='Administrador' OR Nivel='Desarrollador') AND Activo=True AND UsuarioID<>{user_id}"
                    )
                    if not admins:
                        messagebox.showerror("Error",
                            "Debe existir al menos un usuario Administrador o Desarrollador activo.\n"
                            "No puede desactivar o cambiar el nivel del ultimo usuario con privilegios.",
                            parent=win)
                        return
                except:
                    pass

            try:
                # Verificar nombre de usuario único
                existente = self.db.query_one(
                    f"SELECT UsuarioID FROM Usuarios WHERE NombreUsuario='{usuario.replace(chr(39), chr(39)+chr(39))}' AND UsuarioID<>{user_id}"
                )
                if existente:
                    messagebox.showerror("Error", "Ya existe otro usuario con ese nombre", parent=win)
                    return

                self.db.update('Usuarios', {
                    'NombreCompleto': nombre,
                    'NombreUsuario': usuario,
                    'Nivel': nivel,
                    'Activo': var_activo.get()
                }, f"UsuarioID={user_id}")

                messagebox.showinfo("Éxito", "Usuario actualizado correctamente", parent=win)
                win.destroy()
                self._cargar_usuarios()
            except Exception as e:
                messagebox.showerror("Error", f"Error al actualizar usuario:\n{e}", parent=win)

        ttk.Button(main_f, text="💾 Guardar Cambios", command=guardar).pack(anchor='w', pady=(20, 0))

    def _cambiar_contrasena_usuario(self):
        """Cambia la contraseña de un usuario seleccionado."""
        sel = self.tree_usuarios.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un usuario de la lista")
            return

        values = self.tree_usuarios.item(sel[0])['values']
        user_id = values[0]
        nombre = values[1]
        nivel_usuario = values[3] if len(values) > 3 else ''

        # Protección: solo un Desarrollador puede cambiar contraseña de otro Desarrollador
        if nivel_usuario == 'Desarrollador' and self.user.get('Nivel') != 'Desarrollador':
            messagebox.showerror("Acceso Denegado",
                "No tiene permisos para cambiar la contraseña de un usuario Desarrollador.")
            return

        win = tk.Toplevel(self.win)
        win.title(f"Cambiar Contraseña - {nombre}")
        win.geometry("380x220")
        win.grab_set()
        win.focus_set()
        win.resizable(False, False)

        x = (win.winfo_screenwidth() - 380) // 2
        y = (win.winfo_screenheight() - 220) // 2
        win.geometry(f"380x220+{x}+{y}")

        main_f = ttk.Frame(win, padding=20)
        main_f.pack(fill='both', expand=True)

        ttk.Label(main_f, text=f"Nueva contraseña para: {nombre}",
                 font=('Segoe UI', 11, 'bold')).pack(anchor='w', pady=(0, 15))

        ttk.Label(main_f, text="Nueva contraseña:").pack(anchor='w', pady=(5, 2))
        entry_pass = ttk.Entry(main_f, width=30, show="*", font=('Segoe UI', 10))
        entry_pass.pack(anchor='w')
        entry_pass.focus()

        ttk.Label(main_f, text="Confirmar contraseña:").pack(anchor='w', pady=(10, 2))
        entry_confirm = ttk.Entry(main_f, width=30, show="*", font=('Segoe UI', 10))
        entry_confirm.pack(anchor='w')

        def guardar():
            from modulos.seguridad_db import SeguridadContrasenas

            nueva = entry_pass.get()
            confirmar = entry_confirm.get()
            if not nueva:
                messagebox.showwarning("Aviso", "Ingrese una contraseña", parent=win)
                return
            if nueva != confirmar:
                messagebox.showerror("Error", "Las contraseñas no coinciden", parent=win)
                return
            if len(nueva) < 4:
                messagebox.showwarning("Aviso", "La contraseña debe tener al menos 4 caracteres", parent=win)
                return
            try:
                # Generar hash seguro
                pwd_hash, pwd_salt = SeguridadContrasenas.hash_password(nueva)
                self.db.execute(
                    f"UPDATE Usuarios SET PasswordHash='{pwd_hash}', "
                    f"PasswordSalt='{pwd_salt}', Password='' "
                    f"WHERE UsuarioID={user_id}"
                )
                messagebox.showinfo("Éxito", "Contraseña actualizada correctamente", parent=win)
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Error al cambiar contraseña:\n{e}", parent=win)

        ttk.Button(main_f, text="🔒 Cambiar Contraseña", command=guardar).pack(anchor='w', pady=(15, 0))

    def _crear_tab_impresion(self):
        """Pestaña 5: Configuración de Impresión"""
        tab, frame = self._crear_tab_con_scroll("🖨️ Impresión")

        # --- Título ---
        ttk.Label(frame, text="Configuración de Impresión",
                 font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 5))
        ttk.Label(frame, text="Configure las impresoras y el formato de impresión para resultados e informes.",
                 font=('Segoe UI', 10), foreground='gray').pack(anchor='w', pady=(0, 20))

        # --- Obtener impresoras disponibles ---
        self._impresoras_disponibles = self._obtener_impresoras()

        # ============================================
        # Sección 1: Impresora para Resultados
        # ============================================
        sec1 = ttk.LabelFrame(frame, text="  🧾 Impresora para Resultados  ", padding=15)
        sec1.pack(fill='x', pady=(0, 15))

        ttk.Label(sec1, text="Seleccione la impresora donde se enviarán los resultados de laboratorio:",
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 10))

        combo_frame1 = ttk.Frame(sec1)
        combo_frame1.pack(fill='x', pady=5)

        ttk.Label(combo_frame1, text="Impresora:", font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(0, 10))
        self.combo_impresora_resultados = ttk.Combobox(
            combo_frame1, values=self._impresoras_disponibles,
            state='readonly', width=50, font=('Segoe UI', 10))
        self.combo_impresora_resultados.pack(side='left', fill='x', expand=True, padx=(0, 10))

        ttk.Button(combo_frame1, text="🔄", width=3,
                  command=self._refrescar_impresoras).pack(side='left')

        # ============================================
        # Sección 2: Impresora para Informes
        # ============================================
        sec2 = ttk.LabelFrame(frame, text="  📄 Impresora para Informes  ", padding=15)
        sec2.pack(fill='x', pady=(0, 15))

        ttk.Label(sec2, text="Seleccione la impresora donde se enviarán los informes y reportes del laboratorio:",
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 10))

        combo_frame2 = ttk.Frame(sec2)
        combo_frame2.pack(fill='x', pady=5)

        ttk.Label(combo_frame2, text="Impresora:", font=('Segoe UI', 10, 'bold')).pack(side='left', padx=(0, 10))
        self.combo_impresora_informes = ttk.Combobox(
            combo_frame2, values=self._impresoras_disponibles,
            state='readonly', width=50, font=('Segoe UI', 10))
        self.combo_impresora_informes.pack(side='left', fill='x', expand=True, padx=(0, 10))

        ttk.Button(combo_frame2, text="🔄", width=3,
                  command=self._refrescar_impresoras).pack(side='left')

        # ============================================
        # Sección 3: Formato de impresión
        # ============================================
        sec3 = ttk.LabelFrame(frame, text="  📐 Formato de Impresión  ", padding=15)
        sec3.pack(fill='x', pady=(0, 15))

        ttk.Label(sec3, text="Seleccione el formato de página para la impresión de resultados:",
                 font=('Segoe UI', 10)).pack(anchor='w', pady=(0, 10))

        formato_frame = ttk.Frame(sec3)
        formato_frame.pack(fill='x', pady=5)

        self.var_formato_impresion = tk.StringVar(value='Completa')

        fmt_completa = ttk.Radiobutton(formato_frame, text="📄 Hoja Completa (Carta / A4)",
                                       variable=self.var_formato_impresion, value='Completa')
        fmt_completa.pack(anchor='w', pady=3, padx=10)

        fmt_media = ttk.Radiobutton(formato_frame, text="📃 Media Hoja (mitad de página)",
                                     variable=self.var_formato_impresion, value='Media')
        fmt_media.pack(anchor='w', pady=3, padx=10)

        # ============================================
        # Sección 4: Información de impresoras
        # ============================================
        sec4 = ttk.LabelFrame(frame, text="  ℹ️ Impresoras Detectadas en el Sistema  ", padding=15)
        sec4.pack(fill='x', pady=(0, 15))

        # TreeView con info de impresoras
        tree_frame = ttk.Frame(sec4)
        tree_frame.pack(fill='x', pady=5)

        cols_imp = ('Nombre', 'Estado', 'Predeterminada')
        self.tree_impresoras = ttk.Treeview(tree_frame, columns=cols_imp, show='headings', height=5)
        self.tree_impresoras.heading('Nombre', text='Nombre de la Impresora')
        self.tree_impresoras.heading('Estado', text='Estado')
        self.tree_impresoras.heading('Predeterminada', text='Predeterminada')
        self.tree_impresoras.column('Nombre', width=350)
        self.tree_impresoras.column('Estado', width=120, anchor='center')
        self.tree_impresoras.column('Predeterminada', width=120, anchor='center')

        scroll_imp = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree_impresoras.yview)
        self.tree_impresoras.configure(yscrollcommand=scroll_imp.set)
        self.tree_impresoras.pack(side='left', fill='x', expand=True)
        scroll_imp.pack(side='right', fill='y')

        self._cargar_info_impresoras()

        # ============================================
        # Botones de acción
        # ============================================
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill='x', pady=15)

        ttk.Button(btn_frame, text="💾 Guardar Configuración de Impresión",
                  command=self._guardar_config_impresion, width=35).pack(side='left', padx=5)

        ttk.Button(btn_frame, text="🖨️ Imprimir Página de Prueba",
                  command=self._imprimir_pagina_prueba, width=30).pack(side='left', padx=5)

        ttk.Button(btn_frame, text="🔄 Detectar Impresoras",
                  command=self._refrescar_impresoras, width=22).pack(side='left', padx=5)

        # Info
        ttk.Label(frame, text="💡 Si no aparece su impresora, verifique que esté conectada e instalada en Windows.",
                 font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(5, 0))

        # Cargar configuración guardada
        self._cargar_config_impresion()

    def _crear_tab_resetear_bd(self):
        """Pestaña 6: Resetear Base de Datos"""
        tab, frame = self._crear_tab_con_scroll("⚠️ Resetear BD")

        ttk.Label(frame, text="⚠️ Resetear Base de Datos",
                 font=('Segoe UI', 14, 'bold'), foreground='red').grid(
            row=0, column=0, columnspan=2, sticky='w', pady=(0, 10))

        ttk.Label(frame, text="ADVERTENCIA: Estas acciones son IRREVERSIBLES",
                 font=('Segoe UI', 11, 'bold'), foreground='red').grid(
            row=1, column=0, columnspan=2, sticky='w', pady=(0, 20))

        ttk.Label(frame, text="Seleccione qué datos desea eliminar de la base de datos:",
                 font=('Segoe UI', 10)).grid(row=2, column=0, sticky='w', pady=10)

        row = 3

        # Botón 1: Eliminar solo pacientes
        btn_frame1 = ttk.Frame(frame, relief='solid', borderwidth=1, padding=15)
        btn_frame1.grid(row=row, column=0, sticky='ew', pady=10, padx=5)
        row += 1

        ttk.Label(btn_frame1, text="👥 Eliminar Solo Pacientes",
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(btn_frame1, text="Se eliminarán todos los pacientes registrados",
                 font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(5, 10))
        ttk.Button(btn_frame1, text="🗑️ Eliminar Pacientes",
                  command=lambda: self._resetear_bd('pacientes')).pack(anchor='w')

        # Botón 2: Eliminar solo médicos
        btn_frame2 = ttk.Frame(frame, relief='solid', borderwidth=1, padding=15)
        btn_frame2.grid(row=row, column=0, sticky='ew', pady=10, padx=5)
        row += 1

        ttk.Label(btn_frame2, text="🩺 Eliminar Solo Médicos",
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(btn_frame2, text="Se eliminarán todos los médicos registrados",
                 font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(5, 10))
        ttk.Button(btn_frame2, text="🗑️ Eliminar Médicos",
                  command=lambda: self._resetear_bd('medicos')).pack(anchor='w')

        # Botón 3: Eliminar solo solicitudes
        btn_frame3 = ttk.Frame(frame, relief='solid', borderwidth=1, padding=15)
        btn_frame3.grid(row=row, column=0, sticky='ew', pady=10, padx=5)
        row += 1

        ttk.Label(btn_frame3, text="📋 Eliminar Solo Solicitudes",
                 font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(btn_frame3, text="Se eliminarán todas las solicitudes y resultados",
                 font=('Segoe UI', 9), foreground='gray').pack(anchor='w', pady=(5, 10))
        ttk.Button(btn_frame3, text="🗑️ Eliminar Solicitudes",
                  command=lambda: self._resetear_bd('solicitudes')).pack(anchor='w')

        # Botón 4: Eliminar TODO
        btn_frame4 = ttk.Frame(frame, relief='solid', borderwidth=2, padding=15)
        btn_frame4.grid(row=row, column=0, sticky='ew', pady=10, padx=5)
        btn_frame4.configure(style='Danger.TFrame')
        row += 1

        ttk.Label(btn_frame4, text="⚠️ ELIMINAR TODO (Pacientes, Médicos y Solicitudes)",
                 font=('Segoe UI', 12, 'bold'), foreground='red').pack(anchor='w')
        ttk.Label(btn_frame4, text="Se eliminarán TODOS los pacientes, médicos y solicitudes",
                 font=('Segoe UI', 9), foreground='red').pack(anchor='w', pady=(5, 10))
        ttk.Button(btn_frame4, text="⚠️ ELIMINAR TODO",
                  command=lambda: self._resetear_bd('todo')).pack(anchor='w')

        frame.columnconfigure(0, weight=1)

    # ============================================================
    # MÉTODOS DE CARGA Y GUARDADO
    # ============================================================

    def _cargar_todo(self):
        """Recarga toda la configuración"""
        self._cargar_precios()
        self._cargar_personalizacion()

    def _cargar_precios(self):
        """Carga los precios de las pruebas, opcionalmente filtrados por área"""
        # Limpiar árbol
        for item in self.tree_precios.get_children():
            self.tree_precios.delete(item)

        # Determinar filtro de área
        filtro_idx = self.combo_filtro_area.current()
        where_area = ""
        if filtro_idx > 0 and filtro_idx <= len(self._areas_precios):
            area_id = self._areas_precios[filtro_idx - 1][0]
            where_area = f" WHERE p.AreaID = {area_id}"

        # Cargar pruebas
        try:
            pruebas = self.db.query(f"""
                SELECT p.CodigoPrueba, p.NombrePrueba, p.Precio, a.NombreArea
                FROM Pruebas p LEFT JOIN Areas a ON p.AreaID = a.AreaID
                {where_area}
                ORDER BY p.NombrePrueba
            """)

            for p in pruebas:
                precio = p.get('Precio') or 0
                area = p.get('NombreArea') or 'Sin área'
                self.tree_precios.insert('', 'end', values=(
                    p['CodigoPrueba'],
                    p['NombrePrueba'],
                    area,
                    f"${precio:.2f}"
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar precios:\n{e}")

    def _cargar_personalizacion(self):
        """Carga la configuración de personalización"""
        try:
            config = self.db.query_one("SELECT * FROM ConfiguracionLaboratorio")
            if config:
                campos = [
                    (self.entry_nombre_lab, config.get('NombreLaboratorio') or ''),
                    (self.entry_rif, config.get('RIF') or ''),
                    (self.entry_direccion, config.get('Direccion') or ''),
                    (self.entry_telefono, config.get('Telefono1') or ''),
                    (self.entry_whatsapp, config.get('WhatsApp') or config.get('Telefono2') or ''),
                ]
                for entry, valor in campos:
                    try:
                        # Si esta en readonly, cambiar temporalmente para insertar
                        estado_actual = str(entry.cget('state'))
                        if estado_actual == 'readonly':
                            entry.configure(state='normal')
                            entry.delete(0, tk.END)
                            entry.insert(0, valor)
                            entry.configure(state='readonly')
                        else:
                            entry.delete(0, tk.END)
                            entry.insert(0, valor)
                    except:
                        pass
        except:
            pass

    def _editar_precio(self):
        """Edita el precio de una prueba"""
        sel = self.tree_precios.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione una prueba")
            return

        codigo = self.tree_precios.item(sel[0])['values'][0]
        nombre = self.tree_precios.item(sel[0])['values'][1]
        precio_actual = str(self.tree_precios.item(sel[0])['values'][3]).replace('$', '')

        # Ventana para editar precio
        win = tk.Toplevel(self.win)
        win.title(f"Editar Precio - {nombre}")
        win.geometry("400x200")
        win.grab_set()
        win.focus_set()

        ttk.Label(win, text=f"Prueba: {nombre}", font=('Segoe UI', 11, 'bold')).pack(pady=10)
        ttk.Label(win, text="Nuevo precio:").pack(pady=5)

        entry_precio = ttk.Entry(win, width=20, font=('Segoe UI', 12))
        entry_precio.insert(0, precio_actual)
        entry_precio.pack(pady=5)
        entry_precio.focus()

        def guardar():
            try:
                nuevo_precio = float(entry_precio.get().strip())
                self.db.execute(f"""
                    UPDATE Pruebas
                    SET Precio = {nuevo_precio}
                    WHERE CodigoPrueba = '{codigo}'
                """)
                messagebox.showinfo("Éxito", "Precio actualizado correctamente")
                win.destroy()
                self._cargar_precios()
            except ValueError:
                messagebox.showerror("Error", "Ingrese un precio válido")
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar:\n{e}")

        ttk.Button(win, text="💾 Guardar", command=guardar).pack(pady=20)

    def _aplicar_porcentaje_precios(self, tipo):
        """
        Aplica un incremento o descuento porcentual a los precios.

        Args:
            tipo: 'incremento' o 'descuento'
        """
        # Determinar pruebas afectadas
        seleccion = self.tree_precios.selection()
        if seleccion:
            # Solo las seleccionadas
            codigos = [self.tree_precios.item(item)['values'][0] for item in seleccion]
            modo = "seleccionadas"
        else:
            # Todas las visibles
            todos = self.tree_precios.get_children()
            if not todos:
                messagebox.showwarning("Aviso", "No hay pruebas en la lista.")
                return
            codigos = [self.tree_precios.item(item)['values'][0] for item in todos]
            modo = "visibles"

        # Pedir porcentaje
        etiqueta = "incremento" if tipo == 'incremento' else "descuento"
        porcentaje = simpledialog.askfloat(
            f"Aplicar {etiqueta.capitalize()}",
            f"Ingrese el porcentaje de {etiqueta} a aplicar\n"
            f"({len(codigos)} pruebas {modo}):",
            minvalue=0.01, maxvalue=100.0,
            parent=self.win
        )

        if porcentaje is None:
            return

        # Calcular factor
        if tipo == 'incremento':
            factor = 1 + (porcentaje / 100)
        else:
            factor = 1 - (porcentaje / 100)

        # Obtener precios actuales para preview
        codigos_str = ", ".join(f"'{str(c).replace(chr(39), chr(39)+chr(39))}'" for c in codigos)
        try:
            pruebas = self.db.query(f"""
                SELECT CodigoPrueba, NombrePrueba, Precio
                FROM Pruebas
                WHERE CodigoPrueba IN ({codigos_str})
            """)
        except Exception as e:
            messagebox.showerror("Error", f"Error al consultar pruebas:\n{e}")
            return

        if not pruebas:
            messagebox.showwarning("Aviso", "No se encontraron pruebas para actualizar.")
            return

        # Preparar preview (mostrar primeras 5)
        preview_lines = []
        for p in pruebas[:5]:
            precio_ant = p.get('Precio') or 0
            precio_nuevo = round(precio_ant * factor, 2)
            preview_lines.append(f"  {p['NombrePrueba'][:30]}: ${precio_ant:.2f} -> ${precio_nuevo:.2f}")
        if len(pruebas) > 5:
            preview_lines.append(f"  ... y {len(pruebas) - 5} pruebas más")

        preview = "\n".join(preview_lines)
        signo = "+" if tipo == 'incremento' else "-"

        confirmar = messagebox.askyesno(
            f"Confirmar {etiqueta.capitalize()}",
            f"Se aplicará {signo}{porcentaje:.2f}% a {len(pruebas)} pruebas:\n\n"
            f"{preview}\n\n"
            f"¿Desea continuar?"
        )

        if not confirmar:
            return

        # Ejecutar UPDATE
        try:
            self.db.execute(f"""
                UPDATE Pruebas
                SET Precio = ROUND(Precio * {factor}, 2)
                WHERE CodigoPrueba IN ({codigos_str})
            """)
            messagebox.showinfo("Éxito",
                              f"{etiqueta.capitalize()} de {signo}{porcentaje:.2f}% aplicado "
                              f"a {len(pruebas)} pruebas.")
            self._cargar_precios()
        except Exception as e:
            messagebox.showerror("Error", f"Error al aplicar {etiqueta}:\n{e}")

    def _verificar_clave_admin(self, titulo="Acceso Administrador"):
        """Verifica que el usuario logueado sea Administrador o Desarrollador."""
        if self.user.get('Nivel') not in ('Administrador', 'Desarrollador'):
            messagebox.showerror("Acceso Denegado", "Esta operación requiere nivel Administrador o superior")
            return False
        return True

    def _guardar_nombre_laboratorio(self):
        """Guarda el nombre del laboratorio (compatibilidad)"""
        self._guardar_info_laboratorio()

    def _guardar_info_laboratorio(self):
        """Guarda toda la información del laboratorio (SOLO Desarrollador)"""
        if self.user.get('Nivel') != 'Desarrollador':
            messagebox.showerror("Acceso Denegado",
                "Solo el Desarrollador puede modificar los datos del laboratorio.\n"
                "Contacte al proveedor del software para realizar cambios.")
            return
        try:
            nombre = self.entry_nombre_lab.get().strip()
            if not nombre:
                messagebox.showwarning("Aviso", "Ingrese un nombre para el laboratorio")
                return

            rif = self.entry_rif.get().strip()
            direccion = self.entry_direccion.get().strip()
            telefono = self.entry_telefono.get().strip()
            whatsapp = self.entry_whatsapp.get().strip()

            def esc(val):
                if not val:
                    return "NULL"
                return f"'{val.replace(chr(39), chr(39)+chr(39))}'"

            self.db.execute(f"""
                UPDATE ConfiguracionLaboratorio
                SET NombreLaboratorio = {esc(nombre)},
                    RIF = {esc(rif)},
                    Direccion = {esc(direccion)},
                    Telefono1 = {esc(telefono)},
                    WhatsApp = {esc(whatsapp)}
            """)

            messagebox.showinfo("Éxito", "Información del laboratorio actualizada correctamente")

            if self.callback_actualizar:
                self.callback_actualizar()

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar:\n{e}")

    def _cambiar_usuario(self):
        """Cambia el nombre de usuario"""
        if not self._verificar_clave_admin():
            return
        nuevo_usuario = self.entry_nuevo_usuario.get().strip()
        if not nuevo_usuario:
            messagebox.showwarning("Aviso", "Ingrese un nuevo nombre de usuario")
            return

        # Confirmar
        if not messagebox.askyesno("Confirmar",
                                   f"¿Está seguro de cambiar el nombre de usuario a:\n\n{nuevo_usuario}?"):
            return

        try:
            # Actualizar en BD
            user_id = self.user.get('UsuarioID')
            self.db.execute(f"""
                UPDATE Usuarios
                SET NombreUsuario = '{nuevo_usuario.replace("'", "''")}'
                WHERE UsuarioID = {user_id}
            """)

            messagebox.showinfo("Éxito",
                              "Nombre de usuario actualizado correctamente.\n"
                              "Por favor, inicie sesión nuevamente.")

            # Cerrar ventana y volver al login
            self.win.destroy()
            if self.callback_actualizar:
                self.callback_actualizar()

        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar usuario:\n{e}")

    def _cambiar_contrasena(self):
        """Cambia la contraseña del usuario actual (no requiere nivel admin)"""
        pass_actual = self.entry_pass_actual.get()
        pass_nueva = self.entry_pass_nueva.get()
        pass_confirmar = self.entry_pass_confirmar.get()

        # Validaciones
        if not pass_actual:
            messagebox.showwarning("Aviso", "Ingrese la contraseña actual")
            return

        if not pass_nueva:
            messagebox.showwarning("Aviso", "Ingrese la nueva contraseña")
            return

        if pass_nueva != pass_confirmar:
            messagebox.showerror("Error", "Las contraseñas no coinciden")
            return

        if len(pass_nueva) < 4:
            messagebox.showwarning("Aviso", "La contraseña debe tener al menos 4 caracteres")
            return

        # Verificar contraseña actual
        try:
            user_id = self.user.get('UsuarioID')
            user_actual = self.db.query_one(f"""
                SELECT * FROM Usuarios
                WHERE UsuarioID = {user_id} AND Password = '{pass_actual.replace("'", "''")}'
            """)

            if not user_actual:
                messagebox.showerror("Error", "La contraseña actual es incorrecta")
                return

            # Confirmar
            if not messagebox.askyesno("Confirmar", "¿Está seguro de cambiar la contraseña?"):
                return

            # Actualizar contraseña
            self.db.execute(f"""
                UPDATE Usuarios
                SET Password = '{pass_nueva.replace("'", "''")}'
                WHERE UsuarioID = {user_id}
            """)

            messagebox.showinfo("Éxito",
                              "Contraseña actualizada correctamente.\n"
                              "Por favor, inicie sesión nuevamente.")

            # Limpiar campos
            self.entry_pass_actual.delete(0, tk.END)
            self.entry_pass_nueva.delete(0, tk.END)
            self.entry_pass_confirmar.delete(0, tk.END)

        except Exception as e:
            messagebox.showerror("Error", f"Error al cambiar contraseña:\n{e}")

    def _abrir_config_administrativa(self):
        """Abre la configuración administrativa (SOLO Desarrollador)"""
        if self.user.get('Nivel') != 'Desarrollador':
            messagebox.showerror("Acceso Denegado",
                "Solo el Desarrollador puede configurar logo y formato.\n"
                "Contacte al proveedor del software para realizar cambios.")
            return
        try:
            from modulos.ventana_config_administrativa import abrir_ventana_config_administrativa
            abrir_ventana_config_administrativa(self.win, self.db, self.callback_actualizar)
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir configuración administrativa:\n{e}")

    def _resetear_bd(self, tipo):
        """
        Resetea la base de datos según el tipo (SOLO Desarrollador)

        Args:
            tipo: 'pacientes', 'medicos', 'solicitudes', 'todo'
        """
        if self.user.get('Nivel') != 'Desarrollador':
            messagebox.showerror("Acceso Denegado",
                "Solo el Desarrollador puede resetear la base de datos.")
            return

        # Mensajes según tipo
        mensajes = {
            'pacientes': {
                'titulo': 'Eliminar Todos los Pacientes',
                'advertencia': '⚠️ Se eliminarán TODOS los pacientes registrados.\n\n'
                              'Esta acción NO SE PUEDE DESHACER.\n\n'
                              '¿Está COMPLETAMENTE SEGURO?',
                'query': 'DELETE FROM Pacientes',
                'exito': 'Todos los pacientes han sido eliminados'
            },
            'medicos': {
                'titulo': 'Eliminar Todos los Médicos',
                'advertencia': '⚠️ Se eliminarán TODOS los médicos registrados.\n\n'
                              'Esta acción NO SE PUEDE DESHACER.\n\n'
                              '¿Está COMPLETAMENTE SEGURO?',
                'query': 'DELETE FROM Medicos',
                'exito': 'Todos los médicos han sido eliminados'
            },
            'solicitudes': {
                'titulo': 'Eliminar Todas las Solicitudes',
                'advertencia': '⚠️ Se eliminarán TODAS las solicitudes y resultados.\n\n'
                              'Esto incluye:\n'
                              '  • Todas las solicitudes\n'
                              '  • Todos los resultados\n'
                              '  • Todos los detalles\n\n'
                              'Esta acción NO SE PUEDE DESHACER.\n\n'
                              '¿Está COMPLETAMENTE SEGURO?',
                'queries': [
                    'DELETE FROM ResultadosParametros',
                    'DELETE FROM DetalleSolicitudes',
                    'DELETE FROM DetalleSolicitudes',
                    'DELETE FROM ResultadosParametros',
                    'DELETE FROM Solicitudes'
                ],
                'exito': 'Todas las solicitudes han sido eliminadas'
            },
            'todo': {
                'titulo': '⚠️ ELIMINAR TODO ⚠️',
                'advertencia': '⚠️⚠️⚠️ ADVERTENCIA CRÍTICA ⚠️⚠️⚠️\n\n'
                              'Se eliminarán:\n'
                              '  • TODOS los pacientes\n'
                              '  • TODOS los médicos\n'
                              '  • TODAS las solicitudes\n'
                              '  • TODOS los resultados\n\n'
                              'Esta acción NO SE PUEDE DESHACER.\n'
                              'Perderá TODA la información clínica.\n\n'
                              '¿Está ABSOLUTAMENTE SEGURO?',
                'queries': [
                    'DELETE FROM ResultadosParametros',
                    'DELETE FROM DetalleSolicitudes',
                    'DELETE FROM DetalleSolicitudes',
                    'DELETE FROM ResultadosParametros',
                    'DELETE FROM Solicitudes',
                    'DELETE FROM Pacientes',
                    'DELETE FROM Medicos'
                ],
                'exito': 'Toda la información ha sido eliminada'
            }
        }

        info = mensajes.get(tipo)
        if not info:
            return

        # Primera confirmación
        if not messagebox.askokcancel(info['titulo'], info['advertencia']):
            return

        # Segunda confirmación (más estricta para "todo")
        if tipo == 'todo':
            respuesta = messagebox.askquestion(
                "⚠️ ÚLTIMA CONFIRMACIÓN ⚠️",
                "Esta es su ÚLTIMA oportunidad.\n\n"
                "Si continúa, perderá TODA la información.\n\n"
                "¿Desea REALMENTE continuar?",
                icon='warning'
            )
            if respuesta != 'yes':
                messagebox.showinfo("Cancelado", "Operación cancelada")
                return

        try:
            # Ejecutar query(s)
            if 'query' in info:
                self.db.execute(info['query'])
            elif 'queries' in info:
                for query in info['queries']:
                    try:
                        self.db.execute(query)
                    except:
                        pass  # Algunas pueden fallar si no hay datos

            messagebox.showinfo("Completado", info['exito'])

            # Actualizar interfaz
            if self.callback_actualizar:
                self.callback_actualizar()

        except Exception as e:
            messagebox.showerror("Error", f"Error al resetear base de datos:\n{e}")

    # ============================================================
    # MÉTODOS DE IMPRESORAS
    # ============================================================

    def _obtener_impresoras(self):
        """Obtiene la lista de impresoras instaladas en Windows."""
        impresoras = []
        try:
            import win32print
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            lista = win32print.EnumPrinters(flags, None, 2)
            for printer_info in lista:
                impresoras.append(printer_info['pPrinterName'])
        except ImportError:
            # Fallback si win32print no está disponible
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'printer', 'get', 'name'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Saltar encabezado
                        name = line.strip()
                        if name:
                            impresoras.append(name)
            except Exception:
                pass
        except Exception:
            pass

        if not impresoras:
            impresoras = ['(No se detectaron impresoras)']

        return impresoras

    def _obtener_impresora_predeterminada(self):
        """Obtiene el nombre de la impresora predeterminada de Windows."""
        try:
            import win32print
            return win32print.GetDefaultPrinter()
        except Exception:
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'printer', 'where', 'default=TRUE', 'get', 'name'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:
                        name = line.strip()
                        if name:
                            return name
            except Exception:
                pass
        return ''

    def _cargar_info_impresoras(self):
        """Carga la información de impresoras en el TreeView."""
        for item in self.tree_impresoras.get_children():
            self.tree_impresoras.delete(item)

        predeterminada = self._obtener_impresora_predeterminada()

        try:
            import win32print
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            lista = win32print.EnumPrinters(flags, None, 2)
            for printer_info in lista:
                nombre = printer_info['pPrinterName']
                # Interpretar status
                status_code = printer_info.get('Status', 0)
                if status_code == 0:
                    estado = 'Disponible'
                elif status_code & 1:
                    estado = 'En pausa'
                elif status_code & 2:
                    estado = 'Error'
                elif status_code & 4:
                    estado = 'Eliminando'
                elif status_code & 0x400:
                    estado = 'Sin conexión'
                else:
                    estado = 'Disponible'

                es_default = 'Si' if nombre == predeterminada else 'No'
                self.tree_impresoras.insert('', 'end', values=(nombre, estado, es_default))
        except ImportError:
            # Fallback
            for nombre in self._impresoras_disponibles:
                if nombre != '(No se detectaron impresoras)':
                    es_default = 'Si' if nombre == predeterminada else 'No'
                    self.tree_impresoras.insert('', 'end', values=(nombre, 'Desconocido', es_default))
        except Exception:
            pass

    def _refrescar_impresoras(self):
        """Refresca la lista de impresoras disponibles."""
        self._impresoras_disponibles = self._obtener_impresoras()
        self.combo_impresora_resultados['values'] = self._impresoras_disponibles
        self.combo_impresora_informes['values'] = self._impresoras_disponibles
        self._cargar_info_impresoras()
        messagebox.showinfo("Impresoras", "Lista de impresoras actualizada.")

    def _cargar_config_impresion(self):
        """Carga la configuración de impresión guardada en la BD."""
        try:
            config = self.db.query_one("SELECT * FROM ConfiguracionLaboratorio")
            if config:
                # Impresora de resultados
                imp_resultados = config.get('ImpresoraResultados') or ''
                if imp_resultados and imp_resultados in self._impresoras_disponibles:
                    self.combo_impresora_resultados.set(imp_resultados)
                else:
                    # Usar predeterminada
                    pred = self._obtener_impresora_predeterminada()
                    if pred in self._impresoras_disponibles:
                        self.combo_impresora_resultados.set(pred)

                # Impresora de informes
                imp_informes = config.get('ImpresoraInformes') or ''
                if imp_informes and imp_informes in self._impresoras_disponibles:
                    self.combo_impresora_informes.set(imp_informes)
                else:
                    pred = self._obtener_impresora_predeterminada()
                    if pred in self._impresoras_disponibles:
                        self.combo_impresora_informes.set(pred)

                # Formato de impresión
                formato = config.get('FormatoImpresion') or 'Completa'
                self.var_formato_impresion.set(formato)
        except Exception:
            # Si no existen los campos, usar predeterminada
            pred = self._obtener_impresora_predeterminada()
            if pred in self._impresoras_disponibles:
                self.combo_impresora_resultados.set(pred)
                self.combo_impresora_informes.set(pred)

    def _guardar_config_impresion(self):
        """Guarda la configuración de impresión en la BD."""
        imp_resultados = self.combo_impresora_resultados.get()
        imp_informes = self.combo_impresora_informes.get()
        formato = self.var_formato_impresion.get()

        if not imp_resultados or imp_resultados == '(No se detectaron impresoras)':
            messagebox.showwarning("Aviso", "Seleccione una impresora para resultados.")
            return

        if not imp_informes or imp_informes == '(No se detectaron impresoras)':
            messagebox.showwarning("Aviso", "Seleccione una impresora para informes.")
            return

        try:
            # Intentar agregar columnas si no existen
            self._asegurar_campos_impresora()

            imp_resultados_esc = imp_resultados.replace("'", "''")
            imp_informes_esc = imp_informes.replace("'", "''")

            self.db.execute(f"""
                UPDATE ConfiguracionLaboratorio
                SET ImpresoraResultados = '{imp_resultados_esc}',
                    ImpresoraInformes = '{imp_informes_esc}',
                    FormatoImpresion = '{formato}'
            """)

            messagebox.showinfo("Éxito",
                              f"Configuración de impresión guardada:\n\n"
                              f"Resultados: {imp_resultados}\n"
                              f"Informes: {imp_informes}\n"
                              f"Formato: Hoja {formato}")

            if self.callback_actualizar:
                self.callback_actualizar()

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar configuración de impresión:\n{e}")

    def _asegurar_campos_impresora(self):
        """Agrega los campos de impresora a la BD si no existen."""
        campos = [
            ("ImpresoraResultados", "TEXT(255)"),
            ("ImpresoraInformes", "TEXT(255)")
        ]
        for campo, tipo in campos:
            try:
                self.db.execute(f"""
                    ALTER TABLE ConfiguracionLaboratorio
                    ADD COLUMN {campo} {tipo}
                """)
            except Exception:
                pass  # Ya existe

    def _imprimir_pagina_prueba(self):
        """Imprime una página de prueba en la impresora seleccionada."""
        impresora = self.combo_impresora_resultados.get()
        if not impresora or impresora == '(No se detectaron impresoras)':
            messagebox.showwarning("Aviso", "Seleccione una impresora primero.")
            return

        if not messagebox.askyesno("Página de Prueba",
                                    f"Se enviará una página de prueba a:\n\n{impresora}\n\n¿Desea continuar?"):
            return

        try:
            import win32print
            import win32ui

            # Crear documento de prueba
            hprinter = win32print.OpenPrinter(impresora)
            try:
                pdc = win32ui.CreateDC()
                pdc.CreatePrinterDC(impresora)
                pdc.StartDoc("ANgesLAB - Página de Prueba")
                pdc.StartPage()

                # Obtener dimensiones de la página
                page_width = pdc.GetDeviceCaps(110)   # HORZRES
                page_height = pdc.GetDeviceCaps(111)   # VERTRES

                # Dibujar contenido de prueba
                y = 100

                # Título
                font_title = win32ui.CreateFont({
                    'name': 'Arial',
                    'height': 60,
                    'weight': 700,
                })
                pdc.SelectObject(font_title)
                pdc.TextOut(100, y, "ANgesLAB - Página de Prueba")
                y += 100

                # Línea separadora
                pdc.MoveTo(100, y)
                pdc.LineTo(page_width - 100, y)
                y += 50

                # Información
                font_normal = win32ui.CreateFont({
                    'name': 'Arial',
                    'height': 40,
                    'weight': 400,
                })
                pdc.SelectObject(font_normal)

                from datetime import datetime as dt
                lineas = [
                    f"Impresora: {impresora}",
                    f"Fecha: {dt.now().strftime('%d/%m/%Y %H:%M:%S')}",
                    "",
                    "Si puede leer este texto, la impresora está",
                    "configurada correctamente para ANgesLAB.",
                    "",
                    "Sistema de Gestión de Laboratorio Clínico",
                    "ANgesLAB v1.0.0",
                ]

                for linea in lineas:
                    pdc.TextOut(100, y, linea)
                    y += 60

                # Línea final
                y += 40
                pdc.MoveTo(100, y)
                pdc.LineTo(page_width - 100, y)

                pdc.EndPage()
                pdc.EndDoc()
                pdc.DeleteDC()

                messagebox.showinfo("Éxito",
                                  f"Página de prueba enviada a:\n{impresora}")

            finally:
                win32print.ClosePrinter(hprinter)

        except ImportError:
            messagebox.showerror("Error",
                               "No se pudo imprimir la página de prueba.\n\n"
                               "Se requiere la librería pywin32.\n"
                               "Ejecute: pip install pywin32")
        except Exception as e:
            messagebox.showerror("Error", f"Error al imprimir página de prueba:\n{e}")


    # ================================================================
    # PESTAÑA: BIOANALISTAS
    # ================================================================

    def _crear_tab_bioanalistas(self):
        """Pestaña: Gestión de Bioanalistas que validan pruebas por área."""
        tab, frame = self._crear_tab_con_scroll("🔬 Bioanalistas")

        # Título
        ttk.Label(
            frame, text="Gestión de Bioanalistas",
            font=('Segoe UI', 14, 'bold')
        ).pack(anchor='w', pady=(0, 5))

        ttk.Label(
            frame,
            text="Registre los bioanalistas que validan las pruebas en cada área clínica.\n"
                 "Su firma y datos aparecerán al final de los reportes PDF de resultados.",
            font=('Segoe UI', 10),
            foreground='gray'
        ).pack(anchor='w', pady=(0, 15))

        # Barra de herramientas
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill='x', pady=(0, 10))

        ttk.Button(
            toolbar, text="➕ Nuevo Bioanalista",
            command=self._nuevo_bioanalista, width=22
        ).pack(side='left', padx=(0, 5))

        ttk.Button(
            toolbar, text="✏️ Editar",
            command=self._editar_bioanalista, width=12
        ).pack(side='left', padx=5)

        ttk.Button(
            toolbar, text="🗑️ Desactivar",
            command=self._desactivar_bioanalista, width=14
        ).pack(side='left', padx=5)

        ttk.Button(
            toolbar, text="🔄 Refrescar",
            command=self._cargar_bioanalistas, width=12
        ).pack(side='left', padx=5)

        # Treeview de bioanalistas
        tree_frame = ttk.Frame(frame)
        tree_frame.pack(fill='both', expand=True, pady=5)

        cols = ('ID', 'NombreCompleto', 'Cedula', 'NumeroRegistro', 'Area', 'Activo', 'Firma')
        self.tree_bioanalistas = ttk.Treeview(
            tree_frame, columns=cols, show='headings', height=8
        )

        # Configurar columnas
        self.tree_bioanalistas.heading('ID', text='ID')
        self.tree_bioanalistas.heading('NombreCompleto', text='Nombre Completo')
        self.tree_bioanalistas.heading('Cedula', text='Cédula')
        self.tree_bioanalistas.heading('NumeroRegistro', text='No. Registro')
        self.tree_bioanalistas.heading('Area', text='Área Clínica')
        self.tree_bioanalistas.heading('Activo', text='Activo')
        self.tree_bioanalistas.heading('Firma', text='Firma')

        self.tree_bioanalistas.column('ID', width=40, anchor='center')
        self.tree_bioanalistas.column('NombreCompleto', width=200)
        self.tree_bioanalistas.column('Cedula', width=100, anchor='center')
        self.tree_bioanalistas.column('NumeroRegistro', width=120, anchor='center')
        self.tree_bioanalistas.column('Area', width=150)
        self.tree_bioanalistas.column('Activo', width=60, anchor='center')
        self.tree_bioanalistas.column('Firma', width=80, anchor='center')

        scroll_bio = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree_bioanalistas.yview)
        self.tree_bioanalistas.configure(yscrollcommand=scroll_bio.set)
        self.tree_bioanalistas.pack(side='left', fill='both', expand=True)
        scroll_bio.pack(side='right', fill='y')

        # Bind selección para preview de firma
        self.tree_bioanalistas.bind('<<TreeviewSelect>>', self._on_bioanalista_select)

        # Preview de firma
        preview_frame = ttk.LabelFrame(frame, text="Vista previa de firma digital", padding="10")
        preview_frame.pack(fill='x', pady=(10, 5))

        self.lbl_firma_preview = ttk.Label(
            preview_frame, text="Seleccione un bioanalista para ver su firma",
            font=('Segoe UI', 9), foreground='gray'
        )
        self.lbl_firma_preview.pack(pady=10)
        self._firma_preview_image = None  # Mantener referencia a la imagen

        # Leyenda
        ttk.Label(
            frame,
            text="💡 La firma del bioanalista aparecerá al final de los resultados PDF del área asignada.\n"
                 "     Si un área no tiene bioanalista, se usa la firma del Director configurada en Personalización.",
            font=('Segoe UI', 9),
            foreground='gray'
        ).pack(anchor='w', pady=(5, 0))

        # Cargar datos iniciales
        self._cargar_bioanalistas()

    def _cargar_bioanalistas(self):
        """Carga los bioanalistas desde la BD al Treeview."""
        for item in self.tree_bioanalistas.get_children():
            self.tree_bioanalistas.delete(item)

        try:
            bioanalistas = self.db.query(
                "SELECT b.BioanalistaID, b.NombreCompleto, b.Cedula, b.NumeroRegistro, "
                "b.AreaID, b.RutaFirma, b.Activo, a.NombreArea "
                "FROM Bioanalistas b LEFT JOIN Areas a ON b.AreaID = a.AreaID "
                "ORDER BY b.NombreCompleto"
            )
        except Exception:
            # Si la tabla no existe aún, intentar crearla
            try:
                self.db.execute(
                    "CREATE TABLE Bioanalistas ("
                    "BioanalistaID AUTOINCREMENT PRIMARY KEY, "
                    "NombreCompleto TEXT(200), "
                    "Cedula TEXT(20), "
                    "NumeroRegistro TEXT(50), "
                    "AreaID LONG, "
                    "RutaFirma TEXT(500), "
                    "Activo BIT DEFAULT TRUE)"
                )
                bioanalistas = []
            except Exception:
                bioanalistas = []

        if not bioanalistas:
            self.tree_bioanalistas.insert('', 'end', iid='placeholder', values=(
                '', 'No hay bioanalistas registrados. Use "Nuevo" para agregar.', '', '', '', '', ''
            ))
            return

        for bio in bioanalistas:
            bid = bio.get('BioanalistaID', '')
            nombre = bio.get('NombreCompleto', '')
            cedula = bio.get('Cedula', '')
            registro = bio.get('NumeroRegistro', '')
            area = bio.get('NombreArea', 'Sin asignar')
            activo = '✓' if bio.get('Activo') else '✗'
            ruta_firma = bio.get('RutaFirma', '')
            tiene_firma = '✓' if ruta_firma and os.path.exists(
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ruta_firma)
            ) else '—'

            self.tree_bioanalistas.insert('', 'end', iid=str(bid), values=(
                bid, nombre, cedula, registro, area, activo, tiene_firma
            ))

    def _on_bioanalista_select(self, event=None):
        """Muestra preview de la firma del bioanalista seleccionado."""
        sel = self.tree_bioanalistas.selection()
        if not sel:
            self.lbl_firma_preview.configure(
                text="Seleccione un bioanalista para ver su firma",
                image='', compound='text'
            )
            self._firma_preview_image = None
            return

        bid = sel[0]

        # Ignorar click en fila placeholder
        if bid == 'placeholder' or not bid.isdigit():
            self.lbl_firma_preview.configure(
                text="Seleccione un bioanalista para ver su firma",
                image='', compound='text'
            )
            self._firma_preview_image = None
            return

        try:
            bio = self.db.query_one(
                f"SELECT RutaFirma, NombreCompleto FROM Bioanalistas WHERE BioanalistaID={bid}"
            )
        except Exception:
            return

        if not bio or not bio.get('RutaFirma'):
            self.lbl_firma_preview.configure(
                text=f"{bio.get('NombreCompleto', '')} — Sin firma digital cargada",
                image='', compound='text'
            )
            self._firma_preview_image = None
            return

        # Construir ruta absoluta
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ruta_abs = os.path.join(base_dir, bio['RutaFirma'])

        if not os.path.exists(ruta_abs):
            self.lbl_firma_preview.configure(
                text=f"{bio.get('NombreCompleto', '')} — Archivo de firma no encontrado",
                image='', compound='text'
            )
            self._firma_preview_image = None
            return

        try:
            from PIL import Image, ImageTk
            img = Image.open(ruta_abs)
            # Redimensionar manteniendo proporción (máximo 250x80)
            max_w, max_h = 250, 80
            ratio = min(max_w / img.width, max_h / img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.LANCZOS)
            self._firma_preview_image = ImageTk.PhotoImage(img)
            self.lbl_firma_preview.configure(
                text=f"  {bio.get('NombreCompleto', '')}",
                image=self._firma_preview_image,
                compound='top'
            )
        except ImportError:
            self.lbl_firma_preview.configure(
                text=f"{bio.get('NombreCompleto', '')} — Firma: {os.path.basename(ruta_abs)}\n"
                     f"(Instale Pillow para vista previa: pip install Pillow)",
                image='', compound='text'
            )
            self._firma_preview_image = None
        except Exception as e:
            self.lbl_firma_preview.configure(
                text=f"Error cargando firma: {e}",
                image='', compound='text'
            )
            self._firma_preview_image = None

    def _obtener_areas(self):
        """Obtiene las áreas clínicas disponibles para el combobox."""
        try:
            areas = self.db.query("SELECT AreaID, NombreArea FROM Areas ORDER BY NombreArea")
            return {a['NombreArea']: a['AreaID'] for a in areas}
        except Exception:
            return {}

    def _nuevo_bioanalista(self):
        """Abre diálogo para crear un nuevo bioanalista."""
        win = tk.Toplevel(self.win)
        win.title("Nuevo Bioanalista")
        win.geometry("500x580")
        win.resizable(False, False)
        win.transient(self.win)
        win.grab_set()

        # Centrar
        win.update_idletasks()
        x = self.win.winfo_x() + (self.win.winfo_width() - 500) // 2
        y = self.win.winfo_y() + (self.win.winfo_height() - 580) // 2
        win.geometry(f"+{x}+{y}")

        main = ttk.Frame(win, padding="20")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Nuevo Bioanalista", font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 15))

        # Campos
        campos_frame = ttk.LabelFrame(main, text="Datos del Bioanalista", padding="15")
        campos_frame.pack(fill='x', pady=(0, 10))

        # Nombre Completo
        ttk.Label(campos_frame, text="Nombre Completo:", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky='w', pady=5)
        entry_nombre = ttk.Entry(campos_frame, width=40)
        entry_nombre.grid(row=0, column=1, pady=5, padx=(10, 0), sticky='ew')

        # Cédula
        ttk.Label(campos_frame, text="Cédula:", font=('Segoe UI', 10, 'bold')).grid(
            row=1, column=0, sticky='w', pady=5)
        entry_cedula = ttk.Entry(campos_frame, width=40)
        entry_cedula.grid(row=1, column=1, pady=5, padx=(10, 0), sticky='ew')

        # Número de Registro
        ttk.Label(campos_frame, text="No. Registro (MSDS):", font=('Segoe UI', 10, 'bold')).grid(
            row=2, column=0, sticky='w', pady=5)
        entry_registro = ttk.Entry(campos_frame, width=40)
        entry_registro.grid(row=2, column=1, pady=5, padx=(10, 0), sticky='ew')

        # Área Clínica
        ttk.Label(campos_frame, text="Área Clínica:", font=('Segoe UI', 10, 'bold')).grid(
            row=3, column=0, sticky='w', pady=5)
        areas_dict = self._obtener_areas()
        area_names = list(areas_dict.keys())
        combo_area = ttk.Combobox(campos_frame, values=area_names, state='readonly', width=37)
        combo_area.grid(row=3, column=1, pady=5, padx=(10, 0), sticky='ew')
        if area_names:
            combo_area.current(0)

        # Activo
        var_activo = tk.BooleanVar(value=True)
        ttk.Checkbutton(campos_frame, text="Activo", variable=var_activo).grid(
            row=4, column=0, columnspan=2, sticky='w', pady=5)

        campos_frame.columnconfigure(1, weight=1)

        # Firma Digital
        firma_frame = ttk.LabelFrame(main, text="Firma Digital (imagen PNG/JPG)", padding="15")
        firma_frame.pack(fill='x', pady=(0, 10))

        ruta_firma_var = tk.StringVar(value='')
        firma_preview_ref = [None]  # Referencia mutable para la imagen

        lbl_ruta = ttk.Label(firma_frame, text="Sin firma seleccionada", foreground='gray')
        lbl_ruta.pack(anchor='w')

        lbl_preview = ttk.Label(firma_frame, text="")
        lbl_preview.pack(pady=5)

        def seleccionar_firma():
            ruta = filedialog.askopenfilename(
                parent=win,
                title="Seleccionar imagen de firma",
                filetypes=[
                    ("Imágenes", "*.png *.jpg *.jpeg *.bmp"),
                    ("PNG", "*.png"),
                    ("JPEG", "*.jpg *.jpeg"),
                    ("Todos", "*.*")
                ]
            )
            if ruta:
                ruta_firma_var.set(ruta)
                lbl_ruta.configure(text=os.path.basename(ruta), foreground='black')
                # Mostrar preview
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(ruta)
                    max_w, max_h = 200, 60
                    ratio = min(max_w / img.width, max_h / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    firma_preview_ref[0] = ImageTk.PhotoImage(img)
                    lbl_preview.configure(image=firma_preview_ref[0])
                except Exception:
                    lbl_preview.configure(text="(Vista previa no disponible)", image='')

        ttk.Button(firma_frame, text="📁 Cargar imagen de firma...",
                   command=seleccionar_firma).pack(anchor='w', pady=(5, 0))

        # Botones
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill='x', pady=(10, 0))

        def guardar():
            nombre = entry_nombre.get().strip()
            cedula = entry_cedula.get().strip()
            registro = entry_registro.get().strip()
            area_sel = combo_area.get()
            activo = var_activo.get()

            if not nombre:
                messagebox.showwarning("Campos requeridos", "El nombre completo es obligatorio.", parent=win)
                entry_nombre.focus_set()
                return

            if not cedula:
                messagebox.showwarning("Campos requeridos", "La cédula es obligatoria.", parent=win)
                entry_cedula.focus_set()
                return

            if not registro:
                messagebox.showwarning("Campos requeridos", "El número de registro es obligatorio.", parent=win)
                entry_registro.focus_set()
                return

            if not area_sel or area_sel not in areas_dict:
                messagebox.showwarning("Campos requeridos", "Seleccione un área clínica.", parent=win)
                return

            area_id = areas_dict[area_sel]

            # Procesar firma
            ruta_firma_rel = ''
            ruta_firma_orig = ruta_firma_var.get()
            if ruta_firma_orig and os.path.exists(ruta_firma_orig):
                try:
                    import shutil
                    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    firmas_dir = os.path.join(base_dir, 'firmas')
                    if not os.path.exists(firmas_dir):
                        os.makedirs(firmas_dir)

                    # Obtener próximo ID
                    try:
                        max_id = self.db.query_one("SELECT MAX(BioanalistaID) AS MaxID FROM Bioanalistas")
                        next_id = (max_id['MaxID'] or 0) + 1 if max_id else 1
                    except Exception:
                        next_id = 1

                    ext = os.path.splitext(ruta_firma_orig)[1].lower()
                    if ext not in ('.png', '.jpg', '.jpeg', '.bmp'):
                        ext = '.png'
                    nombre_archivo = f"firma_bioanalista_{next_id}{ext}"
                    destino = os.path.join(firmas_dir, nombre_archivo)
                    shutil.copy2(ruta_firma_orig, destino)
                    ruta_firma_rel = f"firmas/{nombre_archivo}"
                except Exception as e:
                    messagebox.showwarning("Advertencia",
                                          f"No se pudo copiar la firma:\n{e}\n\nEl bioanalista se guardará sin firma.",
                                          parent=win)

            try:
                self.db.insert('Bioanalistas', {
                    'NombreCompleto': nombre,
                    'Cedula': cedula,
                    'NumeroRegistro': registro,
                    'AreaID': area_id,
                    'RutaFirma': ruta_firma_rel,
                    'Activo': activo
                })
                messagebox.showinfo("Éxito", f"Bioanalista '{nombre}' registrado correctamente.", parent=win)
                win.destroy()
                self._cargar_bioanalistas()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el bioanalista:\n{e}", parent=win)

        ttk.Button(btn_frame, text="💾 Guardar", command=guardar, width=20).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=win.destroy, width=15).pack(side='right', padx=5)

        entry_nombre.focus_set()

    def _editar_bioanalista(self):
        """Abre diálogo para editar el bioanalista seleccionado."""
        sel = self.tree_bioanalistas.selection()
        if not sel:
            messagebox.showwarning("Selección", "Seleccione un bioanalista de la lista para editar.")
            return

        if sel[0] == 'placeholder' or not sel[0].isdigit():
            messagebox.showwarning("Selección", "Seleccione un bioanalista válido de la lista.")
            return

        bid = sel[0]
        try:
            bio = self.db.query_one(
                f"SELECT * FROM Bioanalistas WHERE BioanalistaID={bid}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo obtener los datos:\n{e}")
            return

        if not bio:
            messagebox.showerror("Error", "Bioanalista no encontrado.")
            return

        win = tk.Toplevel(self.win)
        win.title("Editar Bioanalista")
        win.geometry("500x580")
        win.resizable(False, False)
        win.transient(self.win)
        win.grab_set()

        # Centrar
        win.update_idletasks()
        x = self.win.winfo_x() + (self.win.winfo_width() - 500) // 2
        y = self.win.winfo_y() + (self.win.winfo_height() - 580) // 2
        win.geometry(f"+{x}+{y}")

        main = ttk.Frame(win, padding="20")
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Editar Bioanalista", font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 15))

        # Campos
        campos_frame = ttk.LabelFrame(main, text="Datos del Bioanalista", padding="15")
        campos_frame.pack(fill='x', pady=(0, 10))

        # Nombre Completo
        ttk.Label(campos_frame, text="Nombre Completo:", font=('Segoe UI', 10, 'bold')).grid(
            row=0, column=0, sticky='w', pady=5)
        entry_nombre = ttk.Entry(campos_frame, width=40)
        entry_nombre.grid(row=0, column=1, pady=5, padx=(10, 0), sticky='ew')
        entry_nombre.insert(0, bio.get('NombreCompleto', ''))

        # Cédula
        ttk.Label(campos_frame, text="Cédula:", font=('Segoe UI', 10, 'bold')).grid(
            row=1, column=0, sticky='w', pady=5)
        entry_cedula = ttk.Entry(campos_frame, width=40)
        entry_cedula.grid(row=1, column=1, pady=5, padx=(10, 0), sticky='ew')
        entry_cedula.insert(0, bio.get('Cedula', ''))

        # Número de Registro
        ttk.Label(campos_frame, text="No. Registro (MSDS):", font=('Segoe UI', 10, 'bold')).grid(
            row=2, column=0, sticky='w', pady=5)
        entry_registro = ttk.Entry(campos_frame, width=40)
        entry_registro.grid(row=2, column=1, pady=5, padx=(10, 0), sticky='ew')
        entry_registro.insert(0, bio.get('NumeroRegistro', ''))

        # Área Clínica
        ttk.Label(campos_frame, text="Área Clínica:", font=('Segoe UI', 10, 'bold')).grid(
            row=3, column=0, sticky='w', pady=5)
        areas_dict = self._obtener_areas()
        area_names = list(areas_dict.keys())
        combo_area = ttk.Combobox(campos_frame, values=area_names, state='readonly', width=37)
        combo_area.grid(row=3, column=1, pady=5, padx=(10, 0), sticky='ew')

        # Pre-seleccionar área actual
        area_id_actual = bio.get('AreaID')
        for nombre_area, aid in areas_dict.items():
            if aid == area_id_actual:
                combo_area.set(nombre_area)
                break

        # Activo
        var_activo = tk.BooleanVar(value=bool(bio.get('Activo', True)))
        ttk.Checkbutton(campos_frame, text="Activo", variable=var_activo).grid(
            row=4, column=0, columnspan=2, sticky='w', pady=5)

        campos_frame.columnconfigure(1, weight=1)

        # Firma Digital
        firma_frame = ttk.LabelFrame(main, text="Firma Digital (imagen PNG/JPG)", padding="15")
        firma_frame.pack(fill='x', pady=(0, 10))

        ruta_firma_var = tk.StringVar(value='')
        firma_preview_ref = [None]
        firma_cambio = [False]  # Track si se cambió la firma

        # Mostrar firma actual si existe
        ruta_actual = bio.get('RutaFirma', '')
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        if ruta_actual:
            lbl_ruta = ttk.Label(firma_frame, text=f"Actual: {os.path.basename(ruta_actual)}", foreground='green')
        else:
            lbl_ruta = ttk.Label(firma_frame, text="Sin firma cargada", foreground='gray')
        lbl_ruta.pack(anchor='w')

        lbl_preview = ttk.Label(firma_frame, text="")
        lbl_preview.pack(pady=5)

        # Mostrar preview de firma actual
        if ruta_actual:
            ruta_abs = os.path.join(base_dir, ruta_actual)
            if os.path.exists(ruta_abs):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(ruta_abs)
                    max_w, max_h = 200, 60
                    ratio = min(max_w / img.width, max_h / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    firma_preview_ref[0] = ImageTk.PhotoImage(img)
                    lbl_preview.configure(image=firma_preview_ref[0])
                except Exception:
                    pass

        def seleccionar_firma():
            ruta = filedialog.askopenfilename(
                parent=win,
                title="Seleccionar imagen de firma",
                filetypes=[
                    ("Imágenes", "*.png *.jpg *.jpeg *.bmp"),
                    ("PNG", "*.png"),
                    ("JPEG", "*.jpg *.jpeg"),
                    ("Todos", "*.*")
                ]
            )
            if ruta:
                ruta_firma_var.set(ruta)
                firma_cambio[0] = True
                lbl_ruta.configure(text=f"Nueva: {os.path.basename(ruta)}", foreground='blue')
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(ruta)
                    max_w, max_h = 200, 60
                    ratio = min(max_w / img.width, max_h / img.height)
                    new_size = (int(img.width * ratio), int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)
                    firma_preview_ref[0] = ImageTk.PhotoImage(img)
                    lbl_preview.configure(image=firma_preview_ref[0])
                except Exception:
                    lbl_preview.configure(text="(Vista previa no disponible)", image='')

        btn_firma_frame = ttk.Frame(firma_frame)
        btn_firma_frame.pack(anchor='w', pady=(5, 0))
        ttk.Button(btn_firma_frame, text="📁 Cambiar firma...",
                   command=seleccionar_firma).pack(side='left')

        # Botones
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill='x', pady=(10, 0))

        def guardar():
            nombre = entry_nombre.get().strip()
            cedula = entry_cedula.get().strip()
            registro = entry_registro.get().strip()
            area_sel = combo_area.get()
            activo = var_activo.get()

            if not nombre:
                messagebox.showwarning("Campos requeridos", "El nombre completo es obligatorio.", parent=win)
                return
            if not cedula:
                messagebox.showwarning("Campos requeridos", "La cédula es obligatoria.", parent=win)
                return
            if not registro:
                messagebox.showwarning("Campos requeridos", "El número de registro es obligatorio.", parent=win)
                return
            if not area_sel or area_sel not in areas_dict:
                messagebox.showwarning("Campos requeridos", "Seleccione un área clínica.", parent=win)
                return

            area_id = areas_dict[area_sel]

            # Procesar firma nueva si se cambió
            ruta_firma_rel = ruta_actual  # Mantener la anterior por defecto
            if firma_cambio[0]:
                ruta_firma_orig = ruta_firma_var.get()
                if ruta_firma_orig and os.path.exists(ruta_firma_orig):
                    try:
                        import shutil
                        firmas_dir = os.path.join(base_dir, 'firmas')
                        if not os.path.exists(firmas_dir):
                            os.makedirs(firmas_dir)

                        ext = os.path.splitext(ruta_firma_orig)[1].lower()
                        if ext not in ('.png', '.jpg', '.jpeg', '.bmp'):
                            ext = '.png'
                        nombre_archivo = f"firma_bioanalista_{bid}{ext}"
                        destino = os.path.join(firmas_dir, nombre_archivo)
                        shutil.copy2(ruta_firma_orig, destino)
                        ruta_firma_rel = f"firmas/{nombre_archivo}"
                    except Exception as e:
                        messagebox.showwarning("Advertencia",
                                              f"No se pudo copiar la firma:\n{e}",
                                              parent=win)

            try:
                self.db.execute(
                    f"UPDATE Bioanalistas SET "
                    f"NombreCompleto={self.db.escape(nombre)}, "
                    f"Cedula={self.db.escape(cedula)}, "
                    f"NumeroRegistro={self.db.escape(registro)}, "
                    f"AreaID={area_id}, "
                    f"RutaFirma={self.db.escape(ruta_firma_rel)}, "
                    f"Activo={activo} "
                    f"WHERE BioanalistaID={bid}"
                )
                messagebox.showinfo("Éxito", f"Bioanalista '{nombre}' actualizado correctamente.", parent=win)
                win.destroy()
                self._cargar_bioanalistas()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo actualizar el bioanalista:\n{e}", parent=win)

        ttk.Button(btn_frame, text="💾 Guardar Cambios", command=guardar, width=20).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=win.destroy, width=15).pack(side='right', padx=5)

    def _desactivar_bioanalista(self):
        """Desactiva el bioanalista seleccionado (no lo elimina físicamente)."""
        sel = self.tree_bioanalistas.selection()
        if not sel:
            messagebox.showwarning("Selección", "Seleccione un bioanalista de la lista.")
            return

        if sel[0] == 'placeholder' or not sel[0].isdigit():
            messagebox.showwarning("Selección", "Seleccione un bioanalista válido de la lista.")
            return

        bid = sel[0]
        try:
            bio = self.db.query_one(
                f"SELECT NombreCompleto, Activo FROM Bioanalistas WHERE BioanalistaID={bid}"
            )
        except Exception:
            return

        if not bio:
            return

        nombre = bio.get('NombreCompleto', '')
        esta_activo = bio.get('Activo', True)

        if esta_activo:
            confirmar = messagebox.askyesno(
                "Confirmar Desactivación",
                f"¿Desactivar al bioanalista '{nombre}'?\n\n"
                "Su firma dejará de aparecer en los reportes PDF.\n"
                "Puede reactivarlo más tarde editándolo."
            )
            if confirmar:
                try:
                    self.db.execute(f"UPDATE Bioanalistas SET Activo=False WHERE BioanalistaID={bid}")
                    messagebox.showinfo("Éxito", f"Bioanalista '{nombre}' desactivado.")
                    self._cargar_bioanalistas()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo desactivar:\n{e}")
        else:
            # Reactivar
            confirmar = messagebox.askyesno(
                "Confirmar Reactivación",
                f"¿Reactivar al bioanalista '{nombre}'?\n\n"
                "Su firma volverá a aparecer en los reportes PDF."
            )
            if confirmar:
                try:
                    self.db.execute(f"UPDATE Bioanalistas SET Activo=True WHERE BioanalistaID={bid}")
                    messagebox.showinfo("Éxito", f"Bioanalista '{nombre}' reactivado.")
                    self._cargar_bioanalistas()
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo reactivar:\n{e}")


def abrir_ventana_configuracion_completa(parent, db, user, callback_actualizar=None):
    """
    Función de conveniencia para abrir la ventana de configuración completa.
    """
    VentanaConfiguracionCompleta(parent, db, user, callback_actualizar)

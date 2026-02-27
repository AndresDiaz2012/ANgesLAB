"""
Ventana de Configuración de Numeración de Solicitudes
ANgesLAB - Sistema de Gestión de Laboratorio Clínico

Interfaz gráfica para configurar el sistema de numeración de solicitudes.

Copyright © 2024-2025 ANgesLAB Solutions
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from modulos.config_numeracion import ConfiguradorNumeracion, TipoNumeracion


class VentanaConfigNumeracion:
    """
    Ventana para configurar el sistema de numeración de solicitudes.
    """

    def __init__(self, parent, db):
        """
        Inicializa la ventana de configuración.

        Args:
            parent: Ventana padre (Tk o Toplevel)
            db: Conexión a la base de datos
        """
        self.db = db
        self.configurador = ConfiguradorNumeracion(db)

        # Crear ventana
        self.win = tk.Toplevel(parent)
        self.win.title("Configuración de Numeración de Solicitudes")

        # Hacer ventana responsiva - 80% de la pantalla o máximo 900x700
        screen_width = self.win.winfo_screenwidth()
        screen_height = self.win.winfo_screenheight()

        # Calcular tamaño: 80% de la pantalla pero máximo 900x700
        width = min(int(screen_width * 0.8), 900)
        height = min(int(screen_height * 0.8), 700)

        # Mínimos para que sea usable
        width = max(width, 600)
        height = max(height, 500)

        # Centrar ventana
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.win.geometry(f"{width}x{height}+{x}+{y}")
        self.win.resizable(True, True)  # Permitir redimensionar
        self.win.minsize(600, 500)  # Tamaño mínimo
        self.win.grab_set()
        self.win.focus_set()

        self._crear_interfaz()
        self._cargar_configuracion_actual()

    def _crear_interfaz(self):
        """
        Crea la interfaz de la ventana.
        """
        # Contenedor principal con 2 secciones: contenido (con scroll) y botones (fijos)
        container = ttk.Frame(self.win)
        container.pack(fill=tk.BOTH, expand=True)

        # Área de contenido con scroll (parte superior)
        content_area = ttk.Frame(container)
        content_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # Canvas y Scrollbar para el contenido
        canvas = tk.Canvas(content_area, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_area, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding="20")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Empaquetar canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Usar scrollable_frame como main_frame
        main_frame = scrollable_frame

        # Habilitar scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Área de botones fija (parte inferior) - FUERA del scroll
        button_area = ttk.Frame(container, padding="10", relief="raised", borderwidth=1)
        button_area.pack(side=tk.BOTTOM, fill=tk.X)

        # Guardar referencia para usar después
        self.button_area = button_area

        # Título
        titulo = ttk.Label(
            main_frame,
            text="Configuración del Sistema de Numeración",
            font=('Arial', 16, 'bold')
        )
        titulo.pack(pady=(0, 20))

        # Frame de configuración actual
        frame_actual = ttk.LabelFrame(
            main_frame,
            text="Configuración Actual",
            padding="15"
        )
        frame_actual.pack(fill=tk.X, pady=(0, 20))

        self.lbl_tipo_actual = ttk.Label(frame_actual, text="Tipo: Cargando...")
        self.lbl_tipo_actual.pack(anchor=tk.W)

        self.lbl_ultimo_numero = ttk.Label(frame_actual, text="Último número: Cargando...")
        self.lbl_ultimo_numero.pack(anchor=tk.W)

        self.lbl_proximo_numero = ttk.Label(frame_actual, text="Próximo número: Cargando...")
        self.lbl_proximo_numero.pack(anchor=tk.W)

        self.lbl_fecha_reseteo = ttk.Label(frame_actual, text="Último reseteo: Cargando...")
        self.lbl_fecha_reseteo.pack(anchor=tk.W)

        self.lbl_info_adicional = ttk.Label(frame_actual, text="")
        self.lbl_info_adicional.pack(anchor=tk.W)

        # Frame de selección de tipo
        frame_tipo = ttk.LabelFrame(
            main_frame,
            text="Seleccionar Tipo de Numeración",
            padding="15"
        )
        frame_tipo.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Variable para el tipo seleccionado
        self.tipo_var = tk.StringVar()

        # Opción 1: Numeración Diaria
        frame_diaria = ttk.Frame(frame_tipo)
        frame_diaria.pack(fill=tk.X, pady=5)

        rb_diaria = ttk.Radiobutton(
            frame_diaria,
            text="Numeración Diaria (Reseteo automático cada día)",
            variable=self.tipo_var,
            value=TipoNumeracion.DIARIA.value
        )
        rb_diaria.pack(anchor=tk.W)

        desc_diaria = ttk.Label(
            frame_diaria,
            text="   • Formato: AAAAMMDD-NNNNNN (Ej: 20260127-000001)\n"
                 "   • El contador se resetea automáticamente cada día\n"
                 "   • Útil para laboratorios con alta rotación diaria",
            foreground="gray"
        )
        desc_diaria.pack(anchor=tk.W, padx=(20, 0))

        # Separador
        ttk.Separator(frame_tipo, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Opción 2: Numeración Anual
        frame_anual = ttk.Frame(frame_tipo)
        frame_anual.pack(fill=tk.X, pady=5)

        rb_anual = ttk.Radiobutton(
            frame_anual,
            text="Numeración Anual (Reseteo automático cada año)",
            variable=self.tipo_var,
            value=TipoNumeracion.ANUAL.value
        )
        rb_anual.pack(anchor=tk.W)

        desc_anual = ttk.Label(
            frame_anual,
            text="   • Formato: AAAA-NNNNNN (Ej: 2026-000001)\n"
                 "   • El contador se resetea automáticamente cada año\n"
                 "   • Modo por defecto - Compatible con sistema anterior",
            foreground="gray"
        )
        desc_anual.pack(anchor=tk.W, padx=(20, 0))

        # Separador
        ttk.Separator(frame_tipo, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # Opción 3: Numeración de 5 años
        frame_cinco = ttk.Frame(frame_tipo)
        frame_cinco.pack(fill=tk.X, pady=5)

        rb_cinco = ttk.Radiobutton(
            frame_cinco,
            text="Numeración Continua (5 años con reseteo manual)",
            variable=self.tipo_var,
            value=TipoNumeracion.CINCO_ANIOS.value
        )
        rb_cinco.pack(anchor=tk.W)

        desc_cinco = ttk.Label(
            frame_cinco,
            text="   • Formato: NNNNNN (Ej: 000001)\n"
                 "   • Numeración continua sin reseteo automático\n"
                 "   • Al llegar a 5 años, se solicita confirmación para resetear o continuar\n"
                 "   • Opción de reseteo manual disponible en cualquier momento",
            foreground="gray"
        )
        desc_cinco.pack(anchor=tk.W, padx=(20, 0))

        # Frame de opciones adicionales
        frame_opciones = ttk.Frame(frame_tipo)
        frame_opciones.pack(fill=tk.X, pady=(10, 0))

        self.chk_resetear_var = tk.BooleanVar(value=False)
        chk_resetear = ttk.Checkbutton(
            frame_opciones,
            text="Resetear contador al cambiar de tipo (comenzar desde 1)",
            variable=self.chk_resetear_var
        )
        chk_resetear.pack(anchor=tk.W)

        # Botones secundarios (en el área scrollable)
        frame_botones_sec = ttk.Frame(main_frame)
        frame_botones_sec.pack(fill=tk.X, pady=(10, 10))

        btn_resetear_manual = ttk.Button(
            frame_botones_sec,
            text="Resetear Contador Manualmente",
            command=self._resetear_manual
        )
        btn_resetear_manual.pack(side=tk.LEFT, padx=(0, 10))

        btn_estadisticas = ttk.Button(
            frame_botones_sec,
            text="Ver Estadísticas",
            command=self._mostrar_estadisticas
        )
        btn_estadisticas.pack(side=tk.LEFT)

        # BOTONES PRINCIPALES (en el área fija inferior) - SIEMPRE VISIBLES
        frame_acciones = ttk.Frame(self.button_area)
        frame_acciones.pack(fill=tk.X, expand=True)

        btn_guardar = ttk.Button(
            frame_acciones,
            text="✓ Guardar Configuración",
            command=self._guardar_configuracion,
            style='Accent.TButton'
        )
        btn_guardar.pack(side=tk.RIGHT, padx=5)

        btn_cancelar = ttk.Button(
            frame_acciones,
            text="✗ Cancelar",
            command=self.win.destroy
        )
        btn_cancelar.pack(side=tk.RIGHT, padx=5)

    def _cargar_configuracion_actual(self):
        """
        Carga y muestra la configuración actual.
        """
        try:
            config = self.configurador.obtener_configuracion()

            if config:
                tipo = config.get('TipoNumeracion')
                ultimo_numero = config.get('UltimoNumero', 0)
                fecha_reseteo = config.get('FechaUltimoReseteo')

                # Mostrar tipo
                tipo_texto = {
                    TipoNumeracion.DIARIA.value: "Numeración Diaria",
                    TipoNumeracion.ANUAL.value: "Numeración Anual",
                    TipoNumeracion.CINCO_ANIOS.value: "Numeración Continua (5 años)"
                }
                self.lbl_tipo_actual.config(text=f"Tipo: {tipo_texto.get(tipo, tipo)}")

                # Mostrar último número
                self.lbl_ultimo_numero.config(text=f"Último número generado: {ultimo_numero}")

                # Calcular y mostrar próximo número
                stats = self.configurador.obtener_estadisticas()
                if stats:
                    self.lbl_proximo_numero.config(
                        text=f"Próximo número: {stats.get('proximo_numero', 'N/A')}"
                    )

                # Mostrar fecha de reseteo
                if fecha_reseteo:
                    if isinstance(fecha_reseteo, str):
                        fecha_reseteo = datetime.strptime(fecha_reseteo, '%Y-%m-%d %H:%M:%S')
                    self.lbl_fecha_reseteo.config(
                        text=f"Último reseteo: {fecha_reseteo.strftime('%d/%m/%Y %H:%M')}"
                    )

                # Información adicional según el tipo
                info_adicional = ""
                if tipo == TipoNumeracion.DIARIA.value:
                    dias = stats.get('dias_desde_reseteo', 0)
                    if dias == 0:
                        info_adicional = "El contador se reseteará mañana"
                    else:
                        info_adicional = f"Días desde último reseteo: {dias}"
                elif tipo == TipoNumeracion.ANUAL.value:
                    info_adicional = "El contador se reseteará el 1 de enero"
                elif tipo == TipoNumeracion.CINCO_ANIOS.value:
                    dias_restantes = stats.get('dias_hasta_reseteo', 0)
                    if dias_restantes > 0:
                        anios = dias_restantes // 365
                        dias = dias_restantes % 365
                        info_adicional = f"Tiempo hasta reseteo automático: {anios} años y {dias} días"
                    else:
                        info_adicional = "Se recomienda resetear el contador"

                self.lbl_info_adicional.config(text=info_adicional)

                # Seleccionar el tipo actual en los radiobuttons
                self.tipo_var.set(tipo)

            else:
                messagebox.showwarning(
                    "Configuración no encontrada",
                    "No se encontró configuración de numeración.\n"
                    "Se creará una configuración por defecto al guardar."
                )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al cargar configuración: {e}"
            )

    def _guardar_configuracion(self):
        """
        Guarda la nueva configuración.
        """
        try:
            tipo_seleccionado = self.tipo_var.get()

            if not tipo_seleccionado:
                messagebox.showwarning(
                    "Selección requerida",
                    "Por favor, seleccione un tipo de numeración"
                )
                return

            # Confirmar cambio
            config_actual = self.configurador.obtener_configuracion()
            if config_actual and config_actual.get('TipoNumeracion') != tipo_seleccionado:
                respuesta = messagebox.askyesno(
                    "Confirmar cambio",
                    "¿Está seguro que desea cambiar el tipo de numeración?\n\n"
                    "Este cambio afectará la forma en que se generan los números de solicitud."
                )
                if not respuesta:
                    return

            # Confirmar reseteo si está marcado
            resetear = self.chk_resetear_var.get()
            if resetear:
                respuesta = messagebox.askyesno(
                    "Confirmar reseteo",
                    "¿Está seguro que desea resetear el contador?\n\n"
                    "El próximo número de solicitud será 1."
                )
                if not respuesta:
                    resetear = False

            # Actualizar configuración
            tipo_enum = TipoNumeracion(tipo_seleccionado)
            exito = self.configurador.actualizar_configuracion(tipo_enum, resetear)

            if exito:
                messagebox.showinfo(
                    "Configuración guardada",
                    "La configuración de numeración se guardó correctamente.\n\n"
                    "Los cambios se aplicarán en la próxima solicitud generada."
                )
                self._cargar_configuracion_actual()
            else:
                messagebox.showerror(
                    "Error",
                    "No se pudo guardar la configuración"
                )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al guardar configuración: {e}"
            )

    def _resetear_manual(self):
        """
        Resetea manualmente el contador.
        """
        try:
            respuesta = messagebox.askyesnocancel(
                "Resetear Contador",
                "¿Está seguro que desea resetear el contador manualmente?\n\n"
                "El próximo número de solicitud será 1.\n\n"
                "Esta acción no se puede deshacer."
            )

            if respuesta:
                exito = self.configurador.resetear_contador(manual=True)

                if exito:
                    messagebox.showinfo(
                        "Contador reseteado",
                        "El contador se reseteó correctamente.\n"
                        "El próximo número de solicitud será 1."
                    )
                    self._cargar_configuracion_actual()
                else:
                    messagebox.showerror(
                        "Error",
                        "No se pudo resetear el contador"
                    )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al resetear contador: {e}"
            )

    def _mostrar_estadisticas(self):
        """
        Muestra estadísticas detalladas de numeración.
        """
        try:
            stats = self.configurador.obtener_estadisticas()

            if stats:
                tipo_texto = {
                    TipoNumeracion.DIARIA.value: "Numeración Diaria",
                    TipoNumeracion.ANUAL.value: "Numeración Anual",
                    TipoNumeracion.CINCO_ANIOS.value: "Numeración Continua (5 años)"
                }

                mensaje = f"Estadísticas de Numeración\n\n"
                mensaje += f"Tipo: {tipo_texto.get(stats['tipo'], stats['tipo'])}\n"
                mensaje += f"Último número: {stats['ultimo_numero']}\n"
                mensaje += f"Próximo número: {stats['proximo_numero']}\n"
                mensaje += f"Días desde último reseteo: {stats['dias_desde_reseteo']}\n"

                if stats.get('dias_hasta_reseteo') is not None:
                    dias = stats['dias_hasta_reseteo']
                    if dias > 0:
                        anios = dias // 365
                        dias_restantes = dias % 365
                        mensaje += f"Tiempo hasta reseteo: {anios} años y {dias_restantes} días\n"
                    else:
                        mensaje += "Reseteo recomendado\n"

                messagebox.showinfo("Estadísticas", mensaje)
            else:
                messagebox.showwarning(
                    "Sin estadísticas",
                    "No se pudieron obtener las estadísticas"
                )

        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Error al obtener estadísticas: {e}"
            )


def abrir_ventana_config_numeracion(parent, db):
    """
    Función de conveniencia para abrir la ventana de configuración.

    Args:
        parent: Ventana padre
        db: Conexión a la base de datos
    """
    VentanaConfigNumeracion(parent, db)

# -*- coding: utf-8 -*-
"""
Ventana de Configuración del Portal de Resultados QR
ANgesLAB - Sistema de Gestión de Laboratorio Clínico

Permite activar el portal, elegir el puerto, definir una URL pública y
probar el enlace que verá el paciente al escanear el código QR.

Copyright © 2024-2026 ANgesLAB Solutions
"""

import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser

from modulos.portal_resultados import (
    ConfigPortal, ip_lan, qr_disponible,
    iniciar_portal, detener_portal, portal_en_ejecucion,
    crear_gestor_portal,
)


class VentanaConfigPortal:
    """Configuración del portal de consulta de resultados por QR."""

    def __init__(self, parent, db, nombre_lab='LABORATORIO'):
        self.db = db
        self.nombre_lab = nombre_lab
        self.cfg = ConfigPortal.cargar()

        self.win = tk.Toplevel(parent)
        self.win.title("Portal de Resultados QR")
        self.win.configure(bg='white')
        ancho, alto = 620, 620
        x = (self.win.winfo_screenwidth() - ancho) // 2
        y = max(0, (self.win.winfo_screenheight() - alto) // 2)
        self.win.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.win.minsize(560, 560)
        self.win.grab_set()
        self.win.focus_set()

        self._crear_interfaz()
        self._cargar()
        self._refrescar_estado()

    # ------------------------------------------------------------------ UI
    def _seccion(self, padre, titulo):
        lf = ttk.LabelFrame(padre, text=titulo, padding=12)
        lf.pack(fill='x', pady=(0, 12))
        return lf

    def _crear_interfaz(self):
        cont = ttk.Frame(self.win, padding=16)
        cont.pack(fill='both', expand=True)

        tk.Label(cont, text="Portal de Resultados por Código QR",
                 font=('Segoe UI', 14, 'bold'), bg='white',
                 fg='#0f172a').pack(anchor='w')
        tk.Label(cont,
                 text=("El paciente escanea el QR de su etiqueta o recibo y "
                       "consulta si sus resultados\nestán listos, con acceso "
                       "al PDF cuando ya fueron validados."),
                 font=('Segoe UI', 9), bg='white', fg='#64748b',
                 justify='left').pack(anchor='w', pady=(2, 14))

        # ── Estado ────────────────────────────────────────────────────────
        sec_estado = self._seccion(cont, "Estado del servicio")
        self.lbl_estado = tk.Label(sec_estado, text="", font=('Segoe UI', 10, 'bold'),
                                   bg='white', anchor='w')
        self.lbl_estado.pack(fill='x')
        self.lbl_url = tk.Label(sec_estado, text="", font=('Consolas', 10),
                                bg='white', fg='#0891b2', anchor='w')
        self.lbl_url.pack(fill='x', pady=(4, 0))
        self.lbl_qr = tk.Label(sec_estado, text="", font=('Segoe UI', 9),
                               bg='white', fg='#64748b', anchor='w')
        self.lbl_qr.pack(fill='x', pady=(4, 0))

        # ── Opciones ──────────────────────────────────────────────────────
        sec_opt = self._seccion(cont, "Configuración")

        self.var_activo = tk.BooleanVar(value=True)
        ttk.Checkbutton(sec_opt, variable=self.var_activo,
                        text="Activar el portal (el QR abrirá la página de consulta)"
                        ).grid(row=0, column=0, columnspan=2, sticky='w', pady=3)

        ttk.Label(sec_opt, text="Puerto:").grid(row=1, column=0, sticky='w', pady=3)
        self.var_puerto = tk.StringVar(value='8770')
        ttk.Entry(sec_opt, textvariable=self.var_puerto, width=10
                  ).grid(row=1, column=1, sticky='w', pady=3)

        ttk.Label(sec_opt, text="URL pública:").grid(row=2, column=0, sticky='w', pady=3)
        self.var_url = tk.StringVar()
        ttk.Entry(sec_opt, textvariable=self.var_url, width=42
                  ).grid(row=2, column=1, sticky='w', pady=3)
        ttk.Label(sec_opt,
                  text="Opcional. Déjelo vacío para usar la IP de la red local.",
                  foreground='#64748b').grid(row=3, column=1, sticky='w')

        ttk.Label(sec_opt, text="Vigencia del QR:").grid(row=4, column=0, sticky='w', pady=3)
        self.var_dias = tk.StringVar(value='90')
        fila_dias = ttk.Frame(sec_opt)
        fila_dias.grid(row=4, column=1, sticky='w', pady=3)
        ttk.Entry(fila_dias, textvariable=self.var_dias, width=8).pack(side='left')
        ttk.Label(fila_dias, text=" días").pack(side='left')

        self.var_doc = tk.BooleanVar(value=True)
        ttk.Checkbutton(sec_opt, variable=self.var_doc,
                        text="Pedir la cédula del paciente antes de mostrar el PDF"
                        ).grid(row=5, column=0, columnspan=2, sticky='w', pady=(8, 3))

        # ── Prueba ────────────────────────────────────────────────────────
        sec_test = self._seccion(cont, "Probar")
        ttk.Label(sec_test, text="N° de solicitud (ID):").grid(row=0, column=0, sticky='w')
        self.var_sol = tk.StringVar()
        ttk.Entry(sec_test, textvariable=self.var_sol, width=10
                  ).grid(row=0, column=1, sticky='w', padx=(6, 10))
        ttk.Button(sec_test, text="Abrir en el navegador",
                   command=self._probar).grid(row=0, column=2, sticky='w')
        self.lbl_test = tk.Label(sec_test, text="", font=('Segoe UI', 9),
                                 bg='white', fg='#64748b', anchor='w')
        self.lbl_test.grid(row=1, column=0, columnspan=3, sticky='w', pady=(6, 0))

        tk.Label(cont,
                 text=("Nota: si el paciente consulta desde fuera del "
                       "laboratorio, Windows Firewall debe permitir el puerto\n"
                       "y el router redirigirlo hacia este equipo."),
                 font=('Segoe UI', 8), bg='white', fg='#94a3b8',
                 justify='left').pack(anchor='w', pady=(0, 10))

        # ── Botones ───────────────────────────────────────────────────────
        barra = ttk.Frame(cont)
        barra.pack(fill='x', side='bottom')
        ttk.Button(barra, text="Cerrar", command=self.win.destroy).pack(side='right')
        ttk.Button(barra, text="Guardar y aplicar",
                   command=self._guardar).pack(side='right', padx=(0, 8))

    # -------------------------------------------------------------- datos
    def _cargar(self):
        self.var_activo.set(bool(self.cfg.get('activo', True)))
        self.var_puerto.set(str(self.cfg.get('puerto', 8770)))
        self.var_url.set(self.cfg.get('url_publica', '') or '')
        self.var_dias.set(str(self.cfg.get('dias_validez', 90)))
        self.var_doc.set(bool(self.cfg.get('requiere_documento', True)))

    def _base_url(self):
        publica = (self.var_url.get() or '').strip().rstrip('/')
        if publica:
            if not publica.startswith(('http://', 'https://')):
                publica = 'http://' + publica
            return publica
        return f"http://{ip_lan()}:{self.var_puerto.get().strip() or '8770'}"

    def _refrescar_estado(self):
        if portal_en_ejecucion():
            self.lbl_estado.config(text="● Portal en ejecución", fg='#059669')
        elif self.var_activo.get():
            self.lbl_estado.config(
                text="● Portal detenido (guarde para iniciarlo)", fg='#d97706')
        else:
            self.lbl_estado.config(text="● Portal desactivado", fg='#64748b')

        self.lbl_url.config(text=self._base_url() + "/r/<código>")
        self.lbl_qr.config(
            text=("Generación de QR disponible." if qr_disponible() else
                  "Falta la librería 'qrcode' o 'Pillow': los QR no se imprimirán."),
            fg=('#64748b' if qr_disponible() else '#dc2626'))

    # ------------------------------------------------------------ acciones
    def _validar(self):
        try:
            puerto = int(self.var_puerto.get().strip())
            if not (1024 <= puerto <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("Puerto inválido",
                                 "Use un puerto entre 1024 y 65535.",
                                 parent=self.win)
            return None
        try:
            dias = int(self.var_dias.get().strip())
            if dias < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror("Vigencia inválida",
                                 "Indique un número de días mayor que cero.",
                                 parent=self.win)
            return None
        return puerto, dias

    def _guardar(self):
        validado = self._validar()
        if not validado:
            return
        puerto, dias = validado

        self.cfg.update({
            'activo': bool(self.var_activo.get()),
            'puerto': puerto,
            'url_publica': (self.var_url.get() or '').strip(),
            'dias_validez': dias,
            'requiere_documento': bool(self.var_doc.get()),
        })
        if not ConfigPortal.guardar(self.cfg):
            messagebox.showerror("Error", "No se pudo guardar la configuración.",
                                 parent=self.win)
            return

        detener_portal()
        if self.cfg['activo']:
            servidor = iniciar_portal(self.db, self.nombre_lab)
            if not servidor:
                messagebox.showwarning(
                    "Portal no iniciado",
                    f"No se pudo abrir el puerto {puerto}.\n\n"
                    "Puede estar ocupado por otro programa. Pruebe con otro "
                    "puerto (por ejemplo 8771).",
                    parent=self.win)
            else:
                messagebox.showinfo("Portal activo",
                                    f"El portal está disponible en:\n{self._base_url()}",
                                    parent=self.win)
        else:
            messagebox.showinfo("Guardado",
                                "El portal quedó desactivado. Los códigos QR "
                                "seguirán imprimiéndose con la información "
                                "en texto.", parent=self.win)
        self._refrescar_estado()

    def _probar(self):
        sol = (self.var_sol.get() or '').strip()
        if not sol.isdigit():
            messagebox.showinfo("Probar", "Escriba el ID numérico de una solicitud.",
                                parent=self.win)
            return
        try:
            gestor = crear_gestor_portal(self.db)
            url = gestor.url_solicitud(int(sol))
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el enlace:\n{e}",
                                 parent=self.win)
            return
        if not url:
            messagebox.showwarning("Probar",
                                   "No se pudo crear el código de acceso para "
                                   "esa solicitud.", parent=self.win)
            return
        self.lbl_test.config(text=url)
        webbrowser.open(url)


def abrir_ventana_config_portal(parent, db, nombre_lab='LABORATORIO'):
    """Abre la ventana de configuración del portal QR."""
    return VentanaConfigPortal(parent, db, nombre_lab)

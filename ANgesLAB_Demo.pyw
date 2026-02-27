# -*- coding: utf-8 -*-
"""
ANgesLAB - VERSION DEMO COMERCIAL
==================================
Punto de entrada para la version demo promocional.
NO modifica ningun archivo de produccion.

Para ejecutar: pythonw ANgesLAB_Demo.pyw

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import os
import sys
import importlib.util
from pathlib import Path

# ===========================================================================
# 1. CONFIGURAR ENTORNO
# ===========================================================================

APP_DIR = Path(__file__).parent
sys.path.insert(0, str(APP_DIR))

# ===========================================================================
# 2. IMPORTAR ANgesLAB.pyw COMO MODULO (sin ejecutar main)
# ===========================================================================

spec = importlib.util.spec_from_file_location(
    "angeslab_main",
    str(APP_DIR / "ANgesLAB.pyw")
)
angeslab = importlib.util.module_from_spec(spec)
sys.modules["angeslab_main"] = angeslab
spec.loader.exec_module(angeslab)

# ===========================================================================
# 3. IMPORTAR CONFIGURACION DEMO
# ===========================================================================

from modulos.demo_config import (
    DemoConfig, demo_config,
    DEMO_PURCHASE_MSG, DEMO_VERSION, DEMO_CONTACT_INFO,
    DEMO_CONTACTO_TELEFONO, DEMO_CONTACTO_EMAIL,
)

import tkinter as tk
from tkinter import messagebox

# ===========================================================================
# 4. REDIRIGIR BASE DE DATOS AL ARCHIVO DEMO
# ===========================================================================

DEMO_DB_PATH = str(APP_DIR / "ANgesLAB_Demo.accdb")
angeslab.db.db_path = DEMO_DB_PATH
angeslab.db.close()

# ===========================================================================
# 5. VERIFICAR EXPIRACION
# ===========================================================================

def _verificar_expiracion():
    """Muestra dialogo si la demo ha expirado y sale."""
    if demo_config.is_expired:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Demo Expirada",
            f"La version demo de ANgesLAB ha expirado.\n\n"
            f"Fecha de vencimiento: {demo_config.expiry_date.strftime('%d/%m/%Y')}\n\n"
            f"Para adquirir la licencia completa:\n"
            f"  Tel:   {DEMO_CONTACTO_TELEFONO}\n"
            f"  Email: {DEMO_CONTACTO_EMAIL}",
            parent=root
        )
        root.destroy()
        sys.exit(0)

# ===========================================================================
# 6. PARCHE: SPLASH SCREEN CON TEXTO "VERSION DEMO"
# ===========================================================================

try:
    from modulos import splash_screen as _splash_mod

    _original_SplashScreen_init = _splash_mod.SplashScreen.__init__

    def _demo_splash_init(self, duration=4000):
        _original_SplashScreen_init(self, duration)
        try:
            # Texto DEMO en esquina inferior derecha
            self.canvas.create_text(
                self.width - 15, self.height - 15,
                text="VERSION DEMO",
                font=('Segoe UI', 11, 'bold'),
                fill='#f59e0b',
                anchor='se'
            )
            # Texto de contacto en la parte inferior
            self.canvas.create_text(
                self.width // 2, self.height - 40,
                text=f"Evaluacion gratuita | {DEMO_CONTACT_INFO}",
                font=('Segoe UI', 8),
                fill='#94a3b8',
                anchor='center'
            )
        except Exception:
            pass

    _splash_mod.SplashScreen.__init__ = _demo_splash_init
except Exception as e:
    print(f"Demo: No se pudo personalizar splash: {e}")

# ===========================================================================
# 7. PARCHE: AUTO-LOGIN (sin pedir credenciales)
# ===========================================================================

_original_LoginWindow_run = angeslab.LoginWindow.run

def _demo_login_run(self):
    """En modo demo, auto-login sin mostrar ventana."""
    try:
        self.root.destroy()
    except Exception:
        pass

    # Buscar usuario demo en la BD
    try:
        user = angeslab.db.query_one(
            "SELECT * FROM [Usuarios] WHERE [NombreUsuario]='demo' AND [Activo]=True"
        )
        if user:
            return user
    except Exception as e:
        print(f"Demo: Error buscando usuario demo: {e}")

    # Fallback si no existe en BD
    return {
        'UsuarioID': 999,
        'NombreCompleto': 'Usuario Demo',
        'NombreUsuario': 'demo',
        'Nivel': 'Administrador',
        'Activo': True,
    }

angeslab.LoginWindow.run = _demo_login_run

# ===========================================================================
# 8. PARCHE: BARRA DE DEMO EN LA UI PRINCIPAL
# ===========================================================================

_original_setup_ui = angeslab.MainApplication.setup_ui

def _demo_setup_ui(self):
    """Agrega la barra de demo despues del setup original."""
    _original_setup_ui(self)
    _agregar_banda_demo(self)


def _agregar_banda_demo(app):
    """Inserta barra ambar en la parte superior con info de demo."""
    try:
        banner_text = demo_config.get_banner_text()
        color_banner = '#f59e0b' if not demo_config.is_expired else '#dc2626'

        banner_frame = tk.Frame(app.main_area, bg=color_banner, height=28)
        banner_frame.pack(fill='x', before=app.header)
        banner_frame.pack_propagate(False)

        tk.Label(
            banner_frame,
            text=banner_text,
            font=('Segoe UI', 8, 'bold'),
            bg=color_banner,
            fg='white',
            anchor='w'
        ).pack(side='left', fill='x', expand=True, padx=8)

        # Boton de compra
        btn_comprar = tk.Button(
            banner_frame,
            text="  Adquirir licencia completa  ",
            font=('Segoe UI', 8, 'bold'),
            bg='#0f172a',
            fg='white',
            relief='flat',
            cursor='hand2',
            activebackground='#1e293b',
            activeforeground='white',
            command=lambda: _mostrar_info_compra(app.root)
        )
        btn_comprar.pack(side='right', padx=5, pady=3)

        # Titulo de ventana
        app.root.title(
            f"ANgesLAB {DEMO_VERSION} - VERSION DEMO - "
            f"{demo_config.days_remaining} dias restantes"
        )
    except Exception as e:
        print(f"Demo: Error en banda: {e}")


def _mostrar_info_compra(parent=None):
    messagebox.showinfo("Adquirir ANgesLAB", DEMO_PURCHASE_MSG, parent=parent)

angeslab.MainApplication.setup_ui = _demo_setup_ui

# ===========================================================================
# 9. PARCHE: TITULO DE VENTANA
# ===========================================================================

_original_app_run = angeslab.MainApplication.run

def _demo_app_run(self):
    try:
        self.root.title(
            f"ANgesLAB {DEMO_VERSION} - VERSION DEMO - "
            f"{demo_config.days_remaining} dias restantes"
        )
    except Exception:
        pass
    _original_app_run(self)

angeslab.MainApplication.run = _demo_app_run

# ===========================================================================
# 10. PARCHE: LIMITE DE PACIENTES
# ===========================================================================

_original_form_paciente = angeslab.MainApplication.form_paciente

def _demo_form_paciente(self, paciente_id=None):
    """Verifica limite antes de crear nuevo paciente."""
    if paciente_id is None:  # Solo al crear nuevo
        permitido, mensaje = demo_config.check_patient_limit(angeslab.db)
        if not permitido:
            messagebox.showwarning("Limite Demo", mensaje, parent=self.root)
            return
    _original_form_paciente(self, paciente_id)

angeslab.MainApplication.form_paciente = _demo_form_paciente

# ===========================================================================
# 11. PARCHE: LIMITE DE SOLICITUDES
# ===========================================================================

_original_guardar_solicitud = angeslab.MainApplication.guardar_solicitud_completa

def _demo_guardar_solicitud(self, win):
    """Verifica limite antes de crear nueva solicitud."""
    if self.modo_solicitud != 'agregar':
        permitido, mensaje = demo_config.check_solicitud_limit(angeslab.db)
        if not permitido:
            messagebox.showwarning("Limite Demo", mensaje, parent=win)
            return
    _original_guardar_solicitud(self, win)

angeslab.MainApplication.guardar_solicitud_completa = _demo_guardar_solicitud

# ===========================================================================
# 12. PARCHE: DESHABILITAR MODULOS RESTRINGIDOS
# ===========================================================================

def _demo_modulo_no_disponible(self, nombre_modulo="Este modulo"):
    """Muestra mensaje generico de modulo no disponible en demo."""
    messagebox.showinfo(
        "No disponible en Demo",
        f"{nombre_modulo} no esta disponible en la version demo.\n\n"
        f"{DEMO_PURCHASE_MSG}",
        parent=self.root
    )

def _demo_show_config(self):
    _demo_modulo_no_disponible(self, "Configuracion del Sistema")

def _demo_show_admin(self):
    _demo_modulo_no_disponible(self, "El modulo Administrativo")

# Deshabilitar configuracion
angeslab.MainApplication.show_config = _demo_show_config

# Deshabilitar modulos administrativos/financieros
for _metodo in ['show_caja', 'show_dashboard_financiero',
                'show_cuentas_cobrar', 'show_cuentas_pagar',
                'show_gastos', 'show_config_old']:
    if hasattr(angeslab.MainApplication, _metodo):
        setattr(angeslab.MainApplication, _metodo, _demo_show_admin)

# ===========================================================================
# 13. PARCHE: WATERMARK EN PDFs
# ===========================================================================

def _agregar_watermark_pdf(pdf_path):
    """
    Agrega marca de agua DEMO a un PDF existente.
    Usa pypdf para merge. Si no esta disponible, se omite silenciosamente.
    """
    try:
        try:
            from pypdf import PdfWriter, PdfReader
        except ImportError:
            try:
                from PyPDF2 import PdfWriter, PdfReader
            except ImportError:
                print("Demo: pypdf/PyPDF2 no instalado, watermark omitido")
                return

        import io
        from reportlab.pdfgen import canvas as rl_canvas
        from reportlab.lib import colors

        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        for page in reader.pages:
            pw = float(page.mediabox.width)
            ph = float(page.mediabox.height)

            # Crear overlay
            packet = io.BytesIO()
            c = rl_canvas.Canvas(packet, pagesize=(pw, ph))

            # Marca de agua diagonal
            c.saveState()
            c.setFont('Helvetica-Bold', 72)
            c.setFillColor(colors.Color(0.9, 0.1, 0.1, alpha=0.10))
            c.translate(pw / 2, ph / 2)
            c.rotate(45)
            c.drawCentredString(0, 0, "DEMO")
            c.restoreState()

            # Banner inferior
            c.saveState()
            c.setFont('Helvetica-Bold', 7)
            c.setFillColor(colors.Color(0.6, 0.4, 0.0, alpha=0.85))
            banner = (
                f"VERSION DEMO - Licencia completa: "
                f"{DEMO_CONTACTO_EMAIL} | {DEMO_CONTACTO_TELEFONO}"
            )
            c.drawCentredString(pw / 2, 15, banner)
            c.restoreState()

            c.save()
            packet.seek(0)

            overlay = PdfReader(packet)
            page.merge_page(overlay.pages[0])
            writer.add_page(page)

        with open(pdf_path, 'wb') as f:
            writer.write(f)

    except Exception as e:
        print(f"Demo: Error en watermark: {e}")


# Parchar generacion de PDF humano
_original_generar_pdf = angeslab.MainApplication.generar_pdf_resultados

def _demo_generar_pdf(self, guardar_como=False):
    pdf_path = _original_generar_pdf(self, guardar_como)
    if pdf_path and os.path.exists(str(pdf_path)):
        _agregar_watermark_pdf(str(pdf_path))
    return pdf_path

angeslab.MainApplication.generar_pdf_resultados = _demo_generar_pdf

# Parchar generacion de PDF veterinario
if hasattr(angeslab.MainApplication, 'generar_pdf_resultado_vet'):
    _original_generar_pdf_vet = angeslab.MainApplication.generar_pdf_resultado_vet

    def _demo_generar_pdf_vet(self, guardar_como=False):
        pdf_path = _original_generar_pdf_vet(self, guardar_como)
        if pdf_path and os.path.exists(str(pdf_path)):
            _agregar_watermark_pdf(str(pdf_path))
        return pdf_path

    angeslab.MainApplication.generar_pdf_resultado_vet = _demo_generar_pdf_vet

# ===========================================================================
# 14. PARCHE: DESHABILITAR LOGOUT (en demo no tiene sentido)
# ===========================================================================

_original_logout = angeslab.MainApplication.logout

def _demo_logout(self):
    """En demo, cerrar sesion cierra la aplicacion directamente."""
    if messagebox.askyesno(
        "Cerrar Demo",
        "Desea cerrar la version demo de ANgesLAB?\n\n"
        f"Para adquirir la licencia completa:\n"
        f"  {DEMO_CONTACTO_TELEFONO}\n"
        f"  {DEMO_CONTACTO_EMAIL}",
        parent=self.root
    ):
        self.root.destroy()

angeslab.MainApplication.logout = _demo_logout

# ===========================================================================
# 15. MAIN DEMO
# ===========================================================================

def _asegurar_usuario_demo():
    """Garantiza que exista el usuario 'demo' en la BD."""
    try:
        existe = angeslab.db.query_one(
            "SELECT UsuarioID FROM [Usuarios] WHERE [NombreUsuario]='demo'"
        )
        if not existe:
            from modulos.seguridad_db import SeguridadContrasenas
            h, s = SeguridadContrasenas.hash_password('demo')
            angeslab.db.insert('Usuarios', {
                'NombreCompleto': 'Usuario Demo',
                'NombreUsuario': 'demo',
                'Password': '',
                'PasswordHash': h,
                'PasswordSalt': s,
                'Nivel': 'Administrador',
                'Activo': True,
            })
    except Exception as e:
        print(f"Demo: No se pudo crear usuario demo: {e}")


def main_demo():
    """Punto de entrada de la version demo."""
    # Incrementar contador de arranques
    demo_config.increment_launch_count()

    # Verificar expiracion
    _verificar_expiracion()

    # Asegurar usuario demo
    _asegurar_usuario_demo()

    # Ejecutar la app (splash -> login parcheado -> app parcheada)
    angeslab.main()


if __name__ == "__main__":
    main_demo()

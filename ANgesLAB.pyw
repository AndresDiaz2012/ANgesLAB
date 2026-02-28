# -*- coding: utf-8 -*-
"""
ANgesLAB - Sistema de Gestión para Laboratorios Clínicos
Versión 1.0.0 - Aplicación Completa
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date
import os
import sys
import webbrowser
import smtplib
import tempfile
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

# Importar reportlab para generar PDFs
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, legal, landscape, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, KeepTogether
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Importar motor de layout proporcional y QR
try:
    from modulos.formato_pdf import LayoutCalculator, QRGenerator, dibujar_qr_en_header, MEDIA_CARTA
    FORMATO_PDF_DISPONIBLE = True
except ImportError:
    FORMATO_PDF_DISPONIBLE = False

# Importar PIL para manejar imágenes
try:
    from PIL import Image as PILImage, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# Importar módulos de configuración de numeración
try:
    from modulos.config_numeracion import ConfiguradorNumeracion, TipoNumeracion
    from modulos.ventana_config_numeracion import abrir_ventana_config_numeracion
    CONFIG_NUMERACION_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar configuración de numeración: {e}")
    CONFIG_NUMERACION_DISPONIBLE = False

# Importar módulos de configuración administrativa
try:
    from modulos.config_administrativa import ConfiguradorAdministrativo
    from modulos.ventana_config_administrativa import abrir_ventana_config_administrativa
    CONFIG_ADMINISTRATIVA_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar configuración administrativa: {e}")
    CONFIG_ADMINISTRATIVA_DISPONIBLE = False

# Importar módulo de cálculos automáticos
try:
    from modulos.calculos_automaticos import CalculadorLaboratorio, obtener_calculador
    CALCULOS_AUTOMATICOS_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar cálculos automáticos: {e}")
    CALCULOS_AUTOMATICOS_DISPONIBLE = False

# Importar módulo de gestión de solicitudes
try:
    from modulos.gestor_solicitudes import (
        GestorSolicitudes,
        DialogoSolicitudExistente,
        DialogoTipoDocumento,
        DialogoAgregarPruebas,
        crear_gestor_solicitudes
    )
    GESTOR_SOLICITUDES_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar gestor de solicitudes: {e}")
    GESTOR_SOLICITUDES_DISPONIBLE = False

# Importar módulo veterinario
try:
    from modulos.veterinario import GestorVeterinario, crear_gestor_veterinario, ESPECIES, RAZAS, VALORES_REFERENCIA
    VETERINARIO_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar módulo veterinario: {e}")
    VETERINARIO_DISPONIBLE = False

# Importar módulo de historial clínico
try:
    from modulos.historial_clinico import GestorHistorialClinico, crear_gestor_historial
    HISTORIAL_CLINICO_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar historial clínico: {e}")
    HISTORIAL_CLINICO_DISPONIBLE = False

# Importar módulo de cotizaciones
try:
    from modulos.cotizaciones import GestorCotizaciones
    COTIZACIONES_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar módulo de cotizaciones: {e}")
    COTIZACIONES_DISPONIBLE = False

# Importar módulo de interpretación IA clínica
try:
    from modulos.ia_interpretacion import InterpretadorClinico, ConfigIA, crear_interpretador
    IA_INTERPRETACION_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar IA interpretación: {e}")
    IA_INTERPRETACION_DISPONIBLE = False

# Importar módulo de gráficas de historial
try:
    from modulos.graficas_historial import GraficasHistorial, MATPLOTLIB_DISPONIBLE, crear_gestor_graficas
    GRAFICAS_HISTORIAL_DISPONIBLE = MATPLOTLIB_DISPONIBLE
    if not MATPLOTLIB_DISPONIBLE:
        print("Advertencia: matplotlib no instalado. Gráficas deshabilitadas.")
except ImportError as e:
    print(f"Advertencia: No se pudo importar gráficas de historial: {e}")
    GRAFICAS_HISTORIAL_DISPONIBLE = False
    MATPLOTLIB_DISPONIBLE = False

try:
    from modulos.gtt_captura import abrir_formulario_gtt, es_prueba_gtt
    from modulos.gtt_reporte import (generar_pdf_gtt, mostrar_opciones_impresion_gtt,
                                      verificar_dependencias as gtt_verificar_deps)
    GTT_DISPONIBLE = True
except ImportError:
    GTT_DISPONIBLE = False

# Importar ventana administrativa
try:
    from modulos.ventana_administrativa import crear_ventana_administrativa
    VENTANA_ADMIN_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar ventana administrativa: {e}")
    VENTANA_ADMIN_DISPONIBLE = False

# Importar módulo de auditoría activa
try:
    from modulos.auditoria import AuditoriaActiva
    AUDITORIA_DISPONIBLE = True
except ImportError as e:
    print(f"Advertencia: No se pudo importar auditoría: {e}")
    AUDITORIA_DISPONIBLE = False

# Importar logging estructurado
try:
    from modulos.logging_config import obtener_logger, log_evento, log_auditoria
    LOGGING_DISPONIBLE = True
    _logger = obtener_logger('angeslab')
except ImportError:
    LOGGING_DISPONIBLE = False
    _logger = None

# Importar control de intentos de login
try:
    from modulos.seguridad_db import control_intentos
except ImportError:
    control_intentos = None

# ============================================================
# MÓDULO DE BASE DE DATOS
# ============================================================

class Database:
    def __init__(self):
        # ── Soporte Red LAN: leer ruta desde db_config.json si existe ─────────
        import json as _json
        _cfg_path = Path(__file__).parent / "db_config.json"
        _default  = str(Path(__file__).parent / "ANgesLAB.accdb")
        if _cfg_path.exists():
            try:
                with open(_cfg_path, 'r', encoding='utf-8') as _f:
                    _cfg = _json.load(_f)
                self.db_path = _cfg.get('db_path', _default) or _default
            except Exception:
                self.db_path = _default
        else:
            self.db_path = _default
        self.conn = None

    @staticmethod
    def guardar_ruta_db(nueva_ruta: str):
        """Guarda la ruta de la base de datos en db_config.json (soporte LAN)."""
        import json as _json
        cfg_path = Path(__file__).parent / "db_config.json"
        with open(cfg_path, 'w', encoding='utf-8') as f:
            _json.dump({'db_path': nueva_ruta}, f, ensure_ascii=False, indent=2)

    def connect(self):
        import win32com.client
        if self.conn is None:
            conn_str = f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={self.db_path};"
            self.conn = win32com.client.Dispatch("ADODB.Connection")
            self.conn.Open(conn_str)
        return self.conn

    def close(self):
        if self.conn:
            self.conn.Close()
            self.conn = None

    def execute(self, sql):
        self.connect()
        return self.conn.Execute(sql)

    def query(self, sql):
        rs = self.execute(sql)[0]
        results = []
        if not rs.EOF:
            while not rs.EOF:
                row = {}
                for i in range(rs.Fields.Count):
                    row[rs.Fields[i].Name] = rs.Fields[i].Value
                results.append(row)
                rs.MoveNext()
        return results

    def query_one(self, sql):
        results = self.query(sql)
        return results[0] if results else None

    def escape(self, val):
        if val is None:
            return "Null"
        if isinstance(val, bool):
            return "True" if val else "False"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, (datetime, date)):
            return f"#{val.strftime('%m/%d/%Y')}#"
        return f"'{str(val).replace(chr(39), chr(39)+chr(39))}'"

    def insert(self, table, data):
        cols = ", ".join(f"[{k}]" for k in data.keys())
        vals = ", ".join(self.escape(v) for v in data.values())
        sql = f"INSERT INTO [{table}] ({cols}) VALUES ({vals})"
        self.execute(sql)

    def update(self, table, data, where):
        sets = ", ".join(f"[{k}]={self.escape(v)}" for k, v in data.items())
        sql = f"UPDATE [{table}] SET {sets} WHERE {where}"
        self.execute(sql)

    def delete(self, table, where):
        sql = f"DELETE FROM [{table}] WHERE {where}"
        self.execute(sql)

    def count(self, table, where=None):
        sql = f"SELECT COUNT(*) FROM [{table}]"
        if where:
            sql += f" WHERE {where}"
        rs = self.execute(sql)[0]
        return rs.Fields[0].Value or 0

db = Database()

# ============================================================
# ESTILOS Y COLORES
# ============================================================

COLORS = {
    'bg': '#f8fafc',              # Fondo limpio
    'sidebar': '#0f172a',          # Azul oscuro profundo
    'sidebar_hover': '#1e293b',    # Hover sidebar
    'primary': '#0891b2',          # Cyan corporativo
    'secondary': '#06b6d4',        # Cyan claro
    'success': '#059669',          # Verde esmeralda
    'warning': '#d97706',          # Ámbar
    'danger': '#dc2626',           # Rojo
    'info': '#7c3aed',             # Violeta
    'text': '#0f172a',             # Texto oscuro
    'text_light': '#64748b',       # Texto secundario
    'white': '#ffffff',
    'border': '#e2e8f0',           # Bordes sutiles
    'accent': '#0d9488',           # Verde azulado (científico)
}

# ============================================================
# VENTANA DE LOGIN
# ============================================================

class LoginWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ANgesLAB - Iniciar Sesión")
        self.root.geometry("450x650")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS['sidebar'])
        self.center_window(450, 650)

        self.user_data = None
        self.setup_ui()

    def center_window(self, w, h):
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f'{w}x{h}+{x}+{y}')

    def _cargar_logo_microscopio(self, size=160):
        """Carga la imagen del microscopio para el login."""
        if not PIL_AVAILABLE:
            return None
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'microscopio_logo.png')
            if os.path.exists(logo_path):
                img = PILImage.open(logo_path)
                img = img.resize((size, size), PILImage.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error cargando logo: {e}")
        return None

    def setup_ui(self):
        bg_color = COLORS['sidebar']

        # Frame para el logo
        logo_frame = tk.Frame(self.root, bg=bg_color)
        logo_frame.pack(pady=(25, 8))

        # Cargar imagen del microscopio
        self._logo_image = self._cargar_logo_microscopio(size=140)
        if self._logo_image:
            logo_label = tk.Label(logo_frame, image=self._logo_image, bg=bg_color)
            logo_label.pack()
        else:
            tk.Label(logo_frame, text="🔬", font=('Segoe UI Emoji', 64),
                    bg=bg_color, fg=COLORS['primary']).pack()

        # Título
        title_frame = tk.Frame(self.root, bg=bg_color)
        title_frame.pack(fill='x', pady=(8, 3))

        tk.Label(title_frame, text="ANgesLAB", font=('Segoe UI', 28, 'bold'),
                bg=bg_color, fg='white').pack()

        # Línea decorativa
        line_canvas = tk.Canvas(self.root, width=150, height=4, bg=bg_color, highlightthickness=0)
        line_canvas.pack(pady=4)
        line_canvas.create_line(0, 2, 75, 2, fill=COLORS['primary'], width=2)
        line_canvas.create_line(75, 2, 150, 2, fill=COLORS['accent'], width=2)

        tk.Label(title_frame, text="Sistema de Laboratorio Clínico", font=('Segoe UI', 10),
                bg=bg_color, fg='#94a3b8').pack(pady=(3, 0))

        # Formulario
        form_frame = tk.Frame(self.root, bg=bg_color)
        form_frame.pack(fill='x', padx=50, pady=12)

        # Usuario
        tk.Label(form_frame, text="Usuario", font=('Segoe UI', 10),
                bg=bg_color, fg='#94a3b8').pack(anchor='w', pady=(8, 4))
        self.entry_user = tk.Entry(form_frame, font=('Segoe UI', 12), width=30,
                                   bg='#1e293b', fg='white', insertbackground='white',
                                   relief='flat', highlightthickness=1,
                                   highlightbackground='#334155', highlightcolor=COLORS['primary'])
        self.entry_user.pack(fill='x', ipady=10)

        # Contraseña
        tk.Label(form_frame, text="Contraseña", font=('Segoe UI', 10),
                bg=bg_color, fg='#94a3b8').pack(anchor='w', pady=(12, 4))
        self.entry_pass = tk.Entry(form_frame, font=('Segoe UI', 12), width=30, show='●',
                                   bg='#1e293b', fg='white', insertbackground='white',
                                   relief='flat', highlightthickness=1,
                                   highlightbackground='#334155', highlightcolor=COLORS['primary'])
        self.entry_pass.pack(fill='x', ipady=10)

        # Botón
        btn_frame = tk.Frame(self.root, bg=bg_color)
        btn_frame.pack(fill='x', padx=50, pady=25)

        btn = tk.Button(btn_frame, text="Iniciar Sesión", font=('Segoe UI', 13, 'bold'),
                       bg=COLORS['primary'], fg='white', relief='flat', cursor='hand2',
                       activebackground=COLORS['accent'], activeforeground='white',
                       command=self.login)
        btn.pack(fill='x', ipady=14)

        # Efecto hover en botón
        def on_enter(e):
            btn.config(bg=COLORS['accent'])
        def on_leave(e):
            btn.config(bg=COLORS['primary'])
        btn.bind('<Enter>', on_enter)
        btn.bind('<Leave>', on_leave)

        # Footer
        tk.Label(self.root, text="© 2024-2026 ANgesLAB Solutions",
                font=('Segoe UI', 8), bg=bg_color, fg='#475569').pack(side='bottom', pady=15)

        self.entry_pass.bind('<Return>', lambda e: self.login())
        self.entry_user.focus()

    def login(self):
        user = self.entry_user.get().strip()
        pwd = self.entry_pass.get().strip()

        if not user or not pwd:
            messagebox.showerror("Error", "Ingrese usuario y contrasena")
            return

        # Verificar bloqueo por intentos fallidos
        if control_intentos:
            bloqueado, mins = control_intentos.esta_bloqueado(user)
            if bloqueado:
                messagebox.showerror(
                    "Cuenta bloqueada",
                    f"Demasiados intentos fallidos.\nIntente nuevamente en {mins} minuto(s)."
                )
                if LOGGING_DISPONIBLE:
                    log_evento(f"Login bloqueado para '{user}' ({mins} min restantes)",
                              nivel='warning', modulo='login', accion='LOGIN_BLOQUEADO')
                return

        try:
            # Buscar usuario por nombre (sin incluir password en la query)
            usuario_safe = user.replace("'", "''")
            result = db.query_one(
                f"SELECT * FROM [Usuarios] WHERE [NombreUsuario]='{usuario_safe}' AND [Activo]=True"
            )

            if not result:
                # Registrar intento fallido (usuario inexistente)
                if control_intentos:
                    control_intentos.registrar_intento(user, False)
                    restantes = control_intentos.intentos_restantes(user)
                    if restantes > 0:
                        messagebox.showerror("Error",
                            f"Usuario o contrasena incorrectos\n({restantes} intentos restantes)")
                    else:
                        messagebox.showerror("Cuenta bloqueada",
                            "Demasiados intentos fallidos.\nIntente nuevamente en 15 minutos.")
                else:
                    messagebox.showerror("Error", "Usuario o contrasena incorrectos")
                if LOGGING_DISPONIBLE:
                    log_evento(f"Login fallido: usuario '{user}' no encontrado",
                              nivel='warning', modulo='login', accion='LOGIN_FALLIDO')
                return

            autenticado = False

            # Verificar si la BD tiene columnas de hash
            hash_guardado = result.get('PasswordHash', '') or ''
            salt_guardado = result.get('PasswordSalt', '') or ''

            if hash_guardado and salt_guardado:
                # Verificar contra hash almacenado (metodo seguro)
                try:
                    from modulos.seguridad_db import SeguridadContrasenas
                    autenticado = SeguridadContrasenas.verificar_password(pwd, hash_guardado, salt_guardado)
                    # Rehash a PBKDF2 si usa hash legacy SHA-256
                    if autenticado and SeguridadContrasenas.necesita_rehash(hash_guardado):
                        try:
                            nuevo_hash, nuevo_salt = SeguridadContrasenas.hash_password(pwd)
                            db.execute(
                                f"UPDATE [Usuarios] SET [PasswordHash]='{nuevo_hash}', "
                                f"[PasswordSalt]='{nuevo_salt}' "
                                f"WHERE [UsuarioID]={result['UsuarioID']}"
                            )
                        except Exception:
                            pass
                except Exception as eh:
                    if LOGGING_DISPONIBLE:
                        log_evento(f"Error verificando hash: {eh}", nivel='error', modulo='login')

            if not autenticado:
                # Fallback: contrasena legacy en texto plano
                pwd_legacy = result.get('Password', '') or ''
                if pwd_legacy and pwd == pwd_legacy:
                    autenticado = True
                    # Migrar a hash PBKDF2 inmediatamente
                    try:
                        from modulos.seguridad_db import SeguridadContrasenas
                        nuevo_hash, nuevo_salt = SeguridadContrasenas.hash_password(pwd)
                        db.execute(
                            f"UPDATE [Usuarios] SET [PasswordHash]='{nuevo_hash}', "
                            f"[PasswordSalt]='{nuevo_salt}', [Password]='' "
                            f"WHERE [UsuarioID]={result['UsuarioID']}"
                        )
                        if LOGGING_DISPONIBLE:
                            log_evento(f"Contrasena migrada a PBKDF2 para UsuarioID={result['UsuarioID']}",
                                      nivel='info', modulo='seguridad', accion='MIGRACION_HASH')
                    except Exception:
                        pass

            if autenticado:
                # Registrar intento exitoso
                if control_intentos:
                    control_intentos.registrar_intento(user, True)
                self.user_data = result
                try:
                    db.execute(
                        f"UPDATE [Usuarios] SET [UltimoAcceso]="
                        f"#{datetime.now().strftime('%m/%d/%Y')}# "
                        f"WHERE [UsuarioID]={result['UsuarioID']}"
                    )
                except Exception:
                    pass
                # Registrar login exitoso en auditoria
                if LOGGING_DISPONIBLE:
                    log_auditoria(result.get('UsuarioID'), 'LOGIN_EXITOSO',
                                  f"Login de '{user}' exitoso", modulo='login')
                self.root.destroy()
            else:
                # Registrar intento fallido
                if control_intentos:
                    control_intentos.registrar_intento(user, False)
                    restantes = control_intentos.intentos_restantes(user)
                    if restantes > 0:
                        messagebox.showerror("Error",
                            f"Usuario o contrasena incorrectos\n({restantes} intentos restantes)")
                    else:
                        messagebox.showerror("Cuenta bloqueada",
                            "Demasiados intentos fallidos.\nIntente nuevamente en 15 minutos.")
                else:
                    messagebox.showerror("Error", "Usuario o contrasena incorrectos")
                if LOGGING_DISPONIBLE:
                    log_auditoria(result.get('UsuarioID'), 'LOGIN_FALLIDO',
                                  f"Login fallido para '{user}'", modulo='login')
        except Exception as e:
            messagebox.showerror("Error de conexion", str(e))

    def run(self):
        self.root.mainloop()
        return self.user_data

# ============================================================
# UTILIDADES PARA VENTANAS RESPONSIVAS
# ============================================================

def hacer_ventana_responsiva(ventana, ancho_deseado, alto_deseado, min_ancho=400, min_alto=300, permitir_redimensionar=True):
    """
    Hace que una ventana sea responsiva según la resolución de pantalla.

    Args:
        ventana: La ventana Toplevel a hacer responsiva
        ancho_deseado: Ancho deseado de la ventana
        alto_deseado: Alto deseado de la ventana
        min_ancho: Ancho mínimo permitido
        min_alto: Alto mínimo permitido
        permitir_redimensionar: Si se permite redimensionar la ventana

    Returns:
        tuple: (ancho_final, alto_final)
    """
    screen_width = ventana.winfo_screenwidth()
    screen_height = ventana.winfo_screenheight()

    # Calcular el tamaño máximo (90% de la pantalla)
    max_width = int(screen_width * 0.9)
    max_height = int(screen_height * 0.9)

    # Ajustar el tamaño deseado al máximo disponible
    width = min(ancho_deseado, max_width)
    height = min(alto_deseado, max_height)

    # Aplicar mínimos
    width = max(width, min_ancho)
    height = max(height, min_alto)

    # Centrar ventana
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    ventana.geometry(f"{width}x{height}+{x}+{y}")
    ventana.resizable(permitir_redimensionar, permitir_redimensionar)

    if permitir_redimensionar:
        ventana.minsize(min_ancho, min_alto)

    return width, height

# ============================================================
# APLICACIÓN PRINCIPAL
# ============================================================

class MainApplication:
    def __init__(self, user_data):
        self.user = user_data
        self.root = tk.Tk()
        self.root.state('zoomed')
        self.root.configure(bg=COLORS['bg'])

        # Asegurar campo Nivel en tabla Usuarios
        try:
            db.execute("ALTER TABLE Usuarios ADD COLUMN Nivel TEXT(20) DEFAULT 'Administrador'")
        except:
            pass  # Ya existe
        try:
            db.execute("UPDATE Usuarios SET Nivel = 'Administrador' WHERE Nivel IS NULL")
        except:
            pass

        # Asegurar campo WhatsApp en ConfiguracionLaboratorio
        try:
            db.execute("ALTER TABLE ConfiguracionLaboratorio ADD COLUMN WhatsApp TEXT(50)")
        except:
            pass

        # Asegurar tabla Bioanalistas para firma digital por area
        self._asegurar_tabla_bioanalistas()

        # Recargar datos del usuario para obtener el campo Nivel
        try:
            user_fresh = db.query_one(f"SELECT * FROM Usuarios WHERE UsuarioID={self.user['UsuarioID']}")
            if user_fresh:
                self.user = user_fresh
        except:
            pass

        # Mapear nivel 'Operador' antiguo a 'Recepcion' para compatibilidad
        if self.user.get('Nivel') == 'Operador':
            self.user['Nivel'] = 'Recepcion'

        # Inicializar auditoría activa
        self.auditoria = None
        try:
            if AUDITORIA_DISPONIBLE:
                self.auditoria = AuditoriaActiva(db, self.user.get('UsuarioID'))
                if LOGGING_DISPONIBLE:
                    log_evento(
                        f"Sesion iniciada: {self.user.get('NombreUsuario')} (Nivel: {self.user.get('Nivel')})",
                        nivel='info', modulo='sesion',
                        usuario_id=self.user.get('UsuarioID'), accion='SESION_INICIO'
                    )
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar auditoría: {e}")

        # Configurar timeout de sesión por inactividad (20 minutos)
        self._SESSION_TIMEOUT_MS = 20 * 60 * 1000  # 20 minutos en milisegundos
        self._session_timer_id = None
        self._iniciar_session_timeout()

        # Inicializar configurador de numeración
        try:
            if CONFIG_NUMERACION_DISPONIBLE:
                self.config_numeracion = ConfiguradorNumeracion(db)
            else:
                self.config_numeracion = None
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar configurador de numeración: {e}")
            self.config_numeracion = None

        # Inicializar configurador administrativo
        try:
            if CONFIG_ADMINISTRATIVA_DISPONIBLE:
                self.config_administrativa = ConfiguradorAdministrativo(db)
            else:
                self.config_administrativa = None
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar configurador administrativo: {e}")
            self.config_administrativa = None

        # Cargar configuración administrativa
        self.config_lab = None
        self.logo_path = None
        if self.config_administrativa:
            try:
                self.config_lab = self.config_administrativa.obtener_configuracion()
                self.logo_path = self.config_administrativa.obtener_ruta_logo()
            except:
                pass

        # Inicializar gestor de solicitudes
        self.gestor_solicitudes = None
        try:
            if GESTOR_SOLICITUDES_DISPONIBLE:
                self.gestor_solicitudes = GestorSolicitudes(db, self.user)
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar gestor de solicitudes: {e}")
            self.gestor_solicitudes = None

        # Inicializar gestor veterinario
        self.gestor_vet = None
        try:
            if VETERINARIO_DISPONIBLE:
                self.gestor_vet = crear_gestor_veterinario(db, self.user)
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar gestor veterinario: {e}")
            self.gestor_vet = None

        # Inicializar gestor de historial clínico
        self.gestor_historial = None
        try:
            if HISTORIAL_CLINICO_DISPONIBLE:
                self.gestor_historial = crear_gestor_historial(db, self.user)
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar historial clínico: {e}")
            self.gestor_historial = None

        # Inicializar ventana administrativa
        self.ventana_admin = None
        try:
            if VENTANA_ADMIN_DISPONIBLE:
                self.ventana_admin = crear_ventana_administrativa(db, self.user)
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar ventana administrativa: {e}")
            self.ventana_admin = None

        # Inicializar gestor de cotizaciones
        self.gestor_cotizaciones = None
        try:
            if COTIZACIONES_DISPONIBLE:
                self.gestor_cotizaciones = GestorCotizaciones(db, self.user)
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar cotizaciones: {e}")
            self.gestor_cotizaciones = None

        # Variables para el modo de solicitud (nueva o agregar a existente)
        self.modo_solicitud = 'nueva'  # 'nueva' o 'agregar'
        self.solicitud_existente_id = None

        # Actualizar título de la ventana con nombre del laboratorio
        nombre_lab = "ANgesLAB"
        if self.config_lab and self.config_lab.get('NombreLaboratorio'):
            nombre_lab = self.config_lab['NombreLaboratorio']
        self.root.title(f"{nombre_lab} - {user_data.get('NombreCompleto', 'Usuario')}")

        self.setup_styles()
        self.setup_ui()
        self.show_dashboard()

        # Iniciar backup automático 5 segundos después del arranque
        self._backup_timer = None
        self.root.after(5000, self._verificar_backup_automatico)

    # ── Backup automático ────────────────────────────────────────────────────

    def _leer_config_backup(self):
        import json as _j
        ruta = Path(__file__).parent / "backup_config.json"
        default = {'activo': True, 'frecuencia': 'diario', 'retener_dias': 30, 'ultima_backup': ''}
        if ruta.exists():
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    return {**default, **_j.load(f)}
            except Exception:
                pass
        return default

    def _guardar_config_backup(self, cfg):
        import json as _j
        ruta = Path(__file__).parent / "backup_config.json"
        with open(ruta, 'w', encoding='utf-8') as f:
            _j.dump(cfg, f, ensure_ascii=False, indent=2)

    def _verificar_backup_automatico(self):
        """Verifica si corresponde hacer un backup y lo ejecuta en segundo plano."""
        import threading
        def _hacer_backup():
            try:
                cfg = self._leer_config_backup()
                if not cfg.get('activo', True):
                    return
                frecuencia  = cfg.get('frecuencia', 'diario')
                ultima_str  = cfg.get('ultima_backup', '')
                hacer_ahora = not ultima_str
                if not hacer_ahora and ultima_str:
                    from datetime import datetime as _dt
                    delta = datetime.now() - _dt.fromisoformat(ultima_str)
                    hacer_ahora = (frecuencia == 'diario' and delta.days >= 1) or \
                                  (frecuencia == 'semanal' and delta.days >= 7)
                if hacer_ahora:
                    from modulos.utilidades_db import UtilidadesDB
                    util = UtilidadesDB(db, db.db_path)
                    util.crear_backup()
                    util.limpiar_backups_antiguos(cfg.get('retener_dias', 30))
                    cfg['ultima_backup'] = datetime.now().isoformat()
                    self._guardar_config_backup(cfg)
                    print(f"[Backup automático] realizado a las {datetime.now():%H:%M:%S}")
            except Exception as e:
                print(f"[Backup automático] error: {e}")
            # Reprogramar en la UI thread cada hora
            self.root.after(3600 * 1000, self._verificar_backup_automatico)
        threading.Thread(target=_hacer_backup, daemon=True).start()

    def show_config_backup(self):
        """Ventana de configuración de backup automático."""
        import json as _j
        win = tk.Toplevel(self.root)
        win.title("🗄️ Backup Automático")
        win.grab_set()
        win.configure(bg='white')
        hacer_ventana_responsiva(win, 440, 310, min_ancho=400, min_alto=280)

        tk.Frame(win, bg='#2e7d32', height=50).pack(fill='x')
        tk.Label(win, text="🗄️ Configuración de Backup Automático",
                 font=('Segoe UI', 12, 'bold'), bg='#2e7d32', fg='white').place(x=0, y=10, relwidth=1)

        cfg = self._leer_config_backup()
        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=25, pady=20)

        activo_var = tk.BooleanVar(value=cfg.get('activo', True))
        tk.Checkbutton(frame, text="Backup automático activo", variable=activo_var,
                       font=('Segoe UI', 10), bg='white').pack(anchor='w')

        tk.Label(frame, text="Frecuencia:", font=('Segoe UI', 10, 'bold'), bg='white').pack(anchor='w', pady=(12, 2))
        frec_var = tk.StringVar(value=cfg.get('frecuencia', 'diario'))
        frec_frame = tk.Frame(frame, bg='white')
        frec_frame.pack(anchor='w')
        for val, lbl in [('diario', 'Diario'), ('semanal', 'Semanal')]:
            tk.Radiobutton(frec_frame, text=lbl, variable=frec_var, value=val,
                           font=('Segoe UI', 10), bg='white').pack(side='left', padx=8)

        tk.Label(frame, text="Retener backups (días):", font=('Segoe UI', 10, 'bold'), bg='white').pack(anchor='w', pady=(12, 2))
        retener_var = tk.IntVar(value=cfg.get('retener_dias', 30))
        tk.Spinbox(frame, from_=7, to=365, textvariable=retener_var,
                   font=('Segoe UI', 10), width=8).pack(anchor='w')

        ultima = cfg.get('ultima_backup', '')
        if ultima:
            try:
                ultima_fmt = datetime.fromisoformat(ultima).strftime('%d/%m/%Y %H:%M')
            except Exception:
                ultima_fmt = ultima
            tk.Label(frame, text=f"Último backup: {ultima_fmt}",
                     font=('Segoe UI', 8), bg='white', fg='#555').pack(anchor='w', pady=(10, 0))

        def guardar():
            nuevo = {'activo': activo_var.get(), 'frecuencia': frec_var.get(),
                     'retener_dias': retener_var.get(), 'ultima_backup': cfg.get('ultima_backup', '')}
            self._guardar_config_backup(nuevo)
            messagebox.showinfo("Guardado", "Configuración de backup guardada.", parent=win)
            win.destroy()

        def hacer_ahora():
            try:
                from modulos.utilidades_db import UtilidadesDB
                util = UtilidadesDB(db, db.db_path)
                ruta = util.crear_backup()
                cfg['ultima_backup'] = datetime.now().isoformat()
                self._guardar_config_backup(cfg)
                messagebox.showinfo("Backup", f"Backup creado:\n{ruta}", parent=win)
                win.destroy()
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=win)

        btn_f = tk.Frame(win, bg='white')
        btn_f.pack(fill='x', padx=25, pady=(0, 15))
        tk.Button(btn_f, text="🔄 Hacer ahora", font=('Segoe UI', 9),
                  bg='#1976d2', fg='white', relief='flat', padx=10,
                  command=hacer_ahora).pack(side='left')
        tk.Button(btn_f, text="❌ Cancelar", font=('Segoe UI', 10),
                  bg='#95a5a6', fg='white', relief='flat', padx=15,
                  command=win.destroy).pack(side='right', padx=5)
        tk.Button(btn_f, text="💾 Guardar", font=('Segoe UI', 10, 'bold'),
                  bg='#2e7d32', fg='white', relief='flat', padx=15,
                  command=guardar).pack(side='right')

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Treeview', rowheight=28, font=('Segoe UI', 10))
        style.configure('Treeview.Heading', font=('Segoe UI', 10, 'bold'))

    def _create_menu_button(self, parent, icon, text, command, indent=False):
        """Crea un botón de menú en el sidebar."""
        padx = 30 if indent else 15
        btn = tk.Button(parent, text=f"  {icon}  {text}", font=('Segoe UI', 11),
                       bg=COLORS['sidebar'], fg='white', relief='flat',
                       anchor='w', padx=padx, pady=10, cursor='hand2',
                       activebackground=COLORS['sidebar_hover'], command=command)
        btn.pack(fill='x')
        btn.bind('<Enter>', lambda e, b=btn: b.config(bg=COLORS['sidebar_hover']))
        btn.bind('<Leave>', lambda e, b=btn: b.config(bg=COLORS['sidebar']))
        return btn

    def _create_menu_section(self, title, items, expanded=True):
        """Crea una sección colapsable en el sidebar."""
        indicator = "▼" if expanded else "▶"

        # Header clickeable
        header = tk.Label(self.sidebar, text=f"  {indicator}  {title}",
                         font=('Segoe UI', 9, 'bold'), bg=COLORS['sidebar'],
                         fg='#95a5a6', anchor='w', padx=15, pady=5, cursor='hand2')
        header.pack(fill='x')
        header.bind('<Enter>', lambda e: header.config(fg='#bdc3c7'))
        header.bind('<Leave>', lambda e: header.config(fg='#95a5a6'))

        # Frame contenedor de items
        items_frame = tk.Frame(self.sidebar, bg=COLORS['sidebar'])
        if expanded:
            items_frame.pack(fill='x')

        for icon, text, cmd in items:
            self._create_menu_button(items_frame, icon, text, cmd, indent=True)

        self.menu_sections[title] = {
            'header': header,
            'frame': items_frame,
            'expanded': expanded,
        }

        header.bind('<Button-1>', lambda e, t=title: self._toggle_section(t))

    def _toggle_section(self, title):
        """Alterna visibilidad de una sección del menú."""
        section = self.menu_sections[title]
        if section['expanded']:
            section['frame'].pack_forget()
            section['header'].config(text=f"  ▶  {title}")
            section['expanded'] = False
        else:
            # Re-insertar en la posición correcta (después del header)
            section['frame'].pack(fill='x', after=section['header'])
            section['header'].config(text=f"  ▼  {title}")
            section['expanded'] = True

    def _cargar_logo_sidebar(self, size=70):
        """Carga la imagen del microscopio para el sidebar."""
        if not PIL_AVAILABLE:
            return None
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'microscopio_logo.png')
            if os.path.exists(logo_path):
                img = PILImage.open(logo_path)
                img = img.resize((size, size), PILImage.Resampling.LANCZOS)
                return ImageTk.PhotoImage(img)
        except Exception as e:
            print(f"Error cargando logo sidebar: {e}")
        return None

    def es_admin(self):
        """Verifica si el usuario actual tiene nivel Administrador o Desarrollador."""
        return self.user.get('Nivel') in ('Administrador', 'Desarrollador')

    def es_desarrollador(self):
        """Verifica si el usuario actual tiene nivel Desarrollador."""
        return self.user.get('Nivel') == 'Desarrollador'

    # ================================================================
    # SESSION TIMEOUT POR INACTIVIDAD
    # ================================================================

    def _iniciar_session_timeout(self):
        """Inicia el monitor de inactividad de sesion."""
        # Cancelar timer anterior si existe
        if self._session_timer_id:
            try:
                self.root.after_cancel(self._session_timer_id)
            except Exception:
                pass
        self._session_timer_id = self.root.after(self._SESSION_TIMEOUT_MS, self._session_expirada)

        # Vincular eventos de actividad del usuario para resetear el timer
        self.root.bind_all('<Key>', self._resetear_session_timeout, add='+')
        self.root.bind_all('<Button>', self._resetear_session_timeout, add='+')
        self.root.bind_all('<Motion>', self._resetear_session_timeout, add='+')
        self.root.bind_all('<MouseWheel>', self._resetear_session_timeout, add='+')

    def _resetear_session_timeout(self, event=None):
        """Resetea el timer de sesion cuando el usuario interactua."""
        if self._session_timer_id:
            try:
                self.root.after_cancel(self._session_timer_id)
            except Exception:
                pass
        self._session_timer_id = self.root.after(self._SESSION_TIMEOUT_MS, self._session_expirada)

    def _session_expirada(self):
        """Se ejecuta cuando la sesion expira por inactividad."""
        if LOGGING_DISPONIBLE:
            log_auditoria(
                self.user.get('UsuarioID'), 'SESION_TIMEOUT',
                f"Sesion expirada por inactividad ({self._SESSION_TIMEOUT_MS // 60000} min)",
                modulo='sesion'
            )
        messagebox.showwarning(
            "Sesión expirada",
            "Su sesión ha expirado por inactividad.\nDebe iniciar sesión nuevamente."
        )
        self.root.destroy()

    def setup_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=COLORS['sidebar'], width=230)
        self.sidebar.pack(side='left', fill='y')
        self.sidebar.pack_propagate(False)

        # Logo frame
        logo_frame = tk.Frame(self.sidebar, bg=COLORS['sidebar'])
        logo_frame.pack(fill='x', pady=(18, 8))

        # Cargar imagen del microscopio para sidebar (tamaño visible)
        self._sidebar_logo_image = self._cargar_logo_sidebar(size=70)
        if self._sidebar_logo_image:
            logo_label = tk.Label(logo_frame, image=self._sidebar_logo_image, bg=COLORS['sidebar'])
            logo_label.pack()
        else:
            # Fallback: usar emoji si no se puede cargar la imagen
            tk.Label(logo_frame, text="🔬", font=('Segoe UI Emoji', 36),
                    bg=COLORS['sidebar'], fg=COLORS['primary']).pack()

        # Nombre del laboratorio
        nombre_lab = "ANgesLAB"
        if self.config_lab and self.config_lab.get('NombreLaboratorio'):
            nombre_lab = self.config_lab['NombreLaboratorio']
            if len(nombre_lab) > 20:
                nombre_lab = nombre_lab[:17] + "..."

        tk.Label(logo_frame, text=nombre_lab, font=('Segoe UI', 13, 'bold'),
                bg=COLORS['sidebar'], fg='white', wraplength=200).pack(pady=(5, 2))

        # Línea decorativa con gradiente
        line_canvas = tk.Canvas(logo_frame, width=120, height=3,
                               bg=COLORS['sidebar'], highlightthickness=0)
        line_canvas.pack(pady=3)
        line_canvas.create_line(0, 1, 60, 1, fill=COLORS['primary'], width=2)
        line_canvas.create_line(60, 1, 120, 1, fill=COLORS['accent'], width=2)

        tk.Label(logo_frame, text="v1.0", font=('Segoe UI', 8),
                bg=COLORS['sidebar'], fg=COLORS['primary']).pack()

        tk.Frame(self.sidebar, bg=COLORS['sidebar_hover'], height=1).pack(fill='x', padx=15, pady=10)

        # Menú
        self.menu_sections = {}

        # Inicio (botón directo)
        self._create_menu_button(self.sidebar, "📊", "Inicio", self.show_dashboard)

        # Separador
        tk.Frame(self.sidebar, bg=COLORS['sidebar_hover'], height=1).pack(fill='x', padx=15, pady=5)

        # Sección Registro (expandida)
        self._create_menu_section("Registro", [
            ("👥", "Pacientes", self.show_pacientes),
            ("🩺", "Médicos", self.show_medicos),
        ], expanded=True)

        # Sección Operación (expandida) - filtrada por nivel
        items_operacion = [
            ("📋", "Solicitudes", self.show_solicitudes),
            ("🧾", "Cotizaciones", self.show_cotizaciones),
        ]
        if self.es_admin():
            items_operacion.append(("🧪", "Pruebas", self.show_pruebas))
            items_operacion.append(("🔧", "Parámetros", self.show_parametros))
        items_operacion.append(("📝", "Resultados", self.show_resultados))
        items_operacion.append(("📊", "Historial", self.show_historial_clinico))

        self._create_menu_section("Operación", items_operacion, expanded=True)

        # Sección Informes (colapsada)
        self._create_menu_section("Informes", [
            ("📈", "Reportes", self.show_reportes),
        ], expanded=False)

        # Sección Administrativo (colapsada) - solo para niveles con acceso
        nivel_usuario = self.user.get('Nivel', 'Consulta')
        if nivel_usuario in ('Desarrollador', 'Administrador', 'Facturador', 'Recepcion'):
            if nivel_usuario == 'Recepcion':
                items_admin = [
                    ("💰", "Caja", self.show_caja),
                    ("📊", "Dashboard Financiero", self.show_dashboard_financiero),
                ]
            else:
                items_admin = [
                    ("💰", "Caja", self.show_caja),
                    ("📊", "Dashboard Financiero", self.show_dashboard_financiero),
                    ("💳", "Cuentas por Cobrar", self.show_cuentas_cobrar),
                    ("📋", "Cuentas por Pagar", self.show_cuentas_pagar),
                    ("💸", "Gastos", self.show_gastos),
                    ("🩺", "Comisiones Médicos", self.show_comisiones_medico),
                ]
            self._create_menu_section("Administrativo", items_admin, expanded=False)

        # Separador
        tk.Frame(self.sidebar, bg=COLORS['sidebar_hover'], height=1).pack(fill='x', padx=15, pady=5)

        # Configuración
        self._create_menu_section("Config", [
            ("⚙️", "Configuración", self.show_config),
            ("🌐", "Red LAN / DB", self.show_config_red_lan),
            ("🗄️", "Backup Auto", self.show_config_backup),
        ], expanded=False)

        # Separador VET
        tk.Frame(self.sidebar, bg=COLORS['sidebar_hover'], height=1).pack(fill='x', padx=15, pady=5)

        # Sección VET
        self._create_menu_section("VET", [
            ("🐕", "Pacientes Vet", self.show_pacientes_vet),
            ("📋", "Solicitudes Vet", self.show_solicitudes_vet),
            ("📊", "Resultados Vet", self.show_resultados_vet),
        ], expanded=False)

        # Usuario/Logout
        tk.Frame(self.sidebar, bg=COLORS['sidebar']).pack(expand=True, fill='both')

        user_frame = tk.Frame(self.sidebar, bg='#0c1222')
        user_frame.pack(fill='x', side='bottom')
        tk.Label(user_frame, text=f"👤 {self.user.get('NombreCompleto', '')[:18]}",
                font=('Segoe UI', 9), bg='#0c1222', fg='#94a3b8').pack(pady=(10, 2))
        nivel_color = COLORS['success'] if self.es_admin() else COLORS['primary']
        tk.Label(user_frame, text=f"[{self.user.get('Nivel', 'Administrador')}]",
                font=('Segoe UI', 8), bg='#0c1222', fg=nivel_color).pack(pady=(0, 5))
        tk.Button(user_frame, text="Cerrar Sesión", font=('Segoe UI', 9),
                 bg=COLORS['danger'], fg='white', relief='flat', cursor='hand2',
                 activebackground='#b91c1c',
                 command=self.logout).pack(fill='x', padx=10, pady=(0, 10))

        # Área principal
        self.main_area = tk.Frame(self.root, bg=COLORS['bg'])
        self.main_area.pack(side='right', expand=True, fill='both')

        # Header
        self.header = tk.Frame(self.main_area, bg='white', height=60)
        self.header.pack(fill='x')
        self.header.pack_propagate(False)

        self.header_title = tk.Label(self.header, text="Inicio", font=('Segoe UI', 18, 'bold'),
                                     bg='white', fg=COLORS['text'])
        self.header_title.pack(side='left', padx=25, pady=12)

        # Información del laboratorio en el header (centro)
        if self.config_lab:
            header_center = tk.Frame(self.header, bg='white')
            header_center.pack(side='right', padx=15)

            # Mostrar RIF si está disponible
            if self.config_lab.get('RIF'):
                tk.Label(header_center, text=f"RIF: {self.config_lab['RIF']}",
                        font=('Segoe UI', 9), bg='white',
                        fg=COLORS['text_light']).pack(side='top', anchor='e')

            # Mostrar razón social si está disponible
            if self.config_lab.get('RazonSocial'):
                razon = self.config_lab['RazonSocial']
                if len(razon) > 40:
                    razon = razon[:37] + "..."
                tk.Label(header_center, text=razon,
                        font=('Segoe UI', 9), bg='white',
                        fg=COLORS['text_light']).pack(side='top', anchor='e')

        self.time_label = tk.Label(self.header, font=('Segoe UI', 10), bg='white', fg=COLORS['text_light'])
        self.time_label.pack(side='right', padx=25)
        self.update_time()

        # Contenido
        self.content = tk.Frame(self.main_area, bg=COLORS['bg'])
        self.content.pack(expand=True, fill='both', padx=20, pady=20)

        # Imagen de fondo
        self._bg_image_ref = None
        self._bg_original = None
        self._load_background_image()

    def update_time(self):
        self.time_label.config(text=datetime.now().strftime("%d/%m/%Y  %H:%M:%S"))
        self.root.after(1000, self.update_time)

    def _load_background_image(self):
        """Carga la imagen de fondo para uso posterior en canvas."""
        if not PIL_AVAILABLE:
            return
        try:
            bg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'laboratorio-clinico-2.png')
            if not os.path.exists(bg_path):
                return
            self._bg_original = PILImage.open(bg_path)
        except Exception:
            self._bg_original = None

    def _apply_background_to_canvas(self, canvas):
        """Aplica la imagen de fondo a un canvas y la redimensiona con el."""
        if not self._bg_original:
            return

        def _resize_bg(event=None):
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 10 or h < 10:
                return
            img = self._bg_original.copy()
            img_ratio = img.width / img.height
            area_ratio = w / h
            if img_ratio > area_ratio:
                new_h = h
                new_w = int(h * img_ratio)
            else:
                new_w = w
                new_h = int(w / img_ratio)
            img = img.resize((new_w, new_h), PILImage.LANCZOS)
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))
            overlay = PILImage.new('RGBA', (w, h), (236, 240, 241, 180))
            img = img.convert('RGBA')
            img = PILImage.alpha_composite(img, overlay)
            img = img.convert('RGB')
            self._bg_image_ref = ImageTk.PhotoImage(img)
            canvas.delete('bg_image')
            canvas.create_image(w // 2, h // 2, image=self._bg_image_ref, tag='bg_image')
            canvas.tag_lower('bg_image')

        canvas.bind('<Configure>', _resize_bg)

    def clear_content(self):
        for w in self.content.winfo_children():
            w.destroy()

    def setup_scrollable_content(self):
        """
        Configura un área de contenido con scrolling automático.
        Debe llamarse después de clear_content().

        Retorna: Frame scrollable donde agregar widgets
        """
        # Canvas para scrolling
        canvas = tk.Canvas(self.content, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content, orient="vertical", command=canvas.yview)

        # Frame scrollable
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg'])

        # Configurar scroll region automático
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        # Crear ventana en canvas
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Empaquetar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel para scroll suave
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)

        # Imagen de fondo en el canvas
        self._apply_background_to_canvas(canvas)

        # Guardar referencia al canvas para uso posterior
        self.current_canvas = canvas
        self.current_scrollable_frame = scrollable_frame

        return scrollable_frame

    def set_title(self, title):
        self.header_title.config(text=title)

    def recargar_configuracion(self):
        """Recarga la configuración administrativa y actualiza la interfaz"""
        if self.config_administrativa:
            try:
                # Recargar configuración
                self.config_lab = self.config_administrativa.obtener_configuracion()
                self.logo_path = self.config_administrativa.obtener_ruta_logo()

                # Actualizar título de la ventana
                nombre_lab = "ANgesLAB"
                if self.config_lab and self.config_lab.get('NombreLaboratorio'):
                    nombre_lab = self.config_lab['NombreLaboratorio']
                self.root.title(f"{nombre_lab} - {self.user.get('NombreCompleto', 'Usuario')}")

                # Actualizar solo los elementos que cambian, sin recrear toda la interfaz
                # Esto evita problemas de redimensionamiento

                # Actualizar nombre del laboratorio en el sidebar
                # Buscar el frame del logo en sidebar
                for widget in self.sidebar.winfo_children():
                    if isinstance(widget, tk.Frame):
                        # Buscar labels dentro del frame
                        for child in widget.winfo_children():
                            if isinstance(child, tk.Label):
                                # Si el texto no es el microscopio ni la versión, es el nombre
                                texto = child.cget('text')
                                if texto != "🔬" and texto != "v1.0":
                                    # Actualizar nombre del laboratorio
                                    nombre_truncado = nombre_lab
                                    if len(nombre_truncado) > 20:
                                        nombre_truncado = nombre_truncado[:17] + "..."
                                    child.config(text=nombre_truncado)
                                    break
                        break

                # Actualizar información en el header si existe
                # Buscar el frame del header center
                for widget in self.header.winfo_children():
                    if isinstance(widget, tk.Frame) and widget != self.header_title.master:
                        # Actualizar labels de RIF y Razón Social
                        for child in widget.winfo_children():
                            widget.destroy()

                        # Recrear labels con nueva información
                        if self.config_lab:
                            if self.config_lab.get('RIF'):
                                tk.Label(widget, text=f"RIF: {self.config_lab['RIF']}",
                                        font=('Segoe UI', 9), bg='white',
                                        fg=COLORS['text_light']).pack(side='top', anchor='e')

                            if self.config_lab.get('RazonSocial'):
                                razon = self.config_lab['RazonSocial']
                                if len(razon) > 40:
                                    razon = razon[:37] + "..."
                                tk.Label(widget, text=razon,
                                        font=('Segoe UI', 9), bg='white',
                                        fg=COLORS['text_light']).pack(side='top', anchor='e')

                messagebox.showinfo("Éxito", "Configuración actualizada correctamente.\nLos cambios se han aplicado.")
            except Exception as e:
                print(f"Error al recargar configuración: {e}")
                messagebox.showerror("Error", f"No se pudo recargar la configuración:\n{e}")

    # ============================================================
    # DASHBOARD
    # ============================================================

    def show_dashboard(self):
        self.clear_content()
        self.set_title("📊 Inicio")

        # Configurar contenido scrollable
        scrollable = self.setup_scrollable_content()

        # Stats
        stats_frame = tk.Frame(scrollable, bg=COLORS['bg'])
        stats_frame.pack(fill='x', pady=(0, 20))

        stats = [
            ("👥", "Pacientes", db.count('Pacientes'), COLORS['primary']),
            ("📋", "Solicitudes", db.count('Solicitudes'), COLORS['success']),
            ("🧪", "Pruebas", db.count('Pruebas'), COLORS['warning']),
            ("🩺", "Médicos", db.count('Medicos'), COLORS['danger']),
        ]

        for icon, label, value, color in stats:
            card = tk.Frame(stats_frame, bg='white')
            card.pack(side='left', expand=True, fill='both', padx=8, pady=5)

            inner = tk.Frame(card, bg='white')
            inner.pack(padx=20, pady=15, fill='both', expand=True)

            tk.Label(inner, text=icon, font=('Segoe UI', 28), bg='white', fg=color).pack(anchor='w')
            tk.Label(inner, text=f"{value:,}", font=('Segoe UI', 32, 'bold'), bg='white', fg=COLORS['text']).pack(anchor='w')
            tk.Label(inner, text=label, font=('Segoe UI', 11), bg='white', fg=COLORS['text_light']).pack(anchor='w')
            tk.Frame(card, bg=color, height=4).pack(fill='x', side='bottom')

        # Solicitudes recientes
        recent = tk.LabelFrame(scrollable, text=" 📋 Últimas Solicitudes ", font=('Segoe UI', 11, 'bold'),
                              bg='white', fg=COLORS['text'])
        recent.pack(fill='both', expand=True)

        cols = ('Número', 'Fecha', 'Paciente', 'Estado', 'Total')
        tree = ttk.Treeview(recent, columns=cols, show='headings', height=12)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=120 if c != 'Paciente' else 200)
        tree.pack(fill='both', expand=True, padx=10, pady=10)

        try:
            data = db.query("""
                SELECT TOP 15 s.NumeroSolicitud, s.FechaSolicitud,
                       p.Nombres & ' ' & p.Apellidos AS Paciente,
                       s.EstadoSolicitud, s.MontoTotal
                FROM Solicitudes s LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                ORDER BY s.SolicitudID DESC
            """)
            for r in data:
                tree.insert('', 'end', values=(
                    r['NumeroSolicitud'] or '',
                    r['FechaSolicitud'].strftime('%d/%m/%Y') if r['FechaSolicitud'] else '',
                    r['Paciente'] or 'N/A',
                    r['EstadoSolicitud'] or 'Pendiente',
                    f"${r['MontoTotal']:,.2f}" if r['MontoTotal'] else '$0.00'
                ))
        except Exception as e:
            print(f"Error: {e}")

        # ============================================================
        # AGENDA DE PENDIENTES
        # ============================================================
        self._asegurar_tabla_pendientes()

        pend_frame = tk.LabelFrame(scrollable, text=" 📝 Asuntos Pendientes / Agenda ",
                                    font=('Segoe UI', 11, 'bold'), bg='white', fg=COLORS['text'])
        pend_frame.pack(fill='both', expand=True, pady=(15, 0))

        # Fila para agregar nuevo pendiente
        add_frame = tk.Frame(pend_frame, bg='white')
        add_frame.pack(fill='x', padx=10, pady=(10, 5))

        self.entry_nuevo_pendiente = tk.Entry(add_frame, font=('Segoe UI', 11), relief='flat',
                                               bg='white', highlightthickness=1,
                                               highlightbackground=COLORS['border'])
        self.entry_nuevo_pendiente.pack(side='left', fill='x', expand=True, padx=(0, 8), ipady=6)
        self.entry_nuevo_pendiente.insert(0, "Ej: Comprar reactivos, reportar urocultivos...")
        self.entry_nuevo_pendiente.config(fg='gray')

        def _on_focus_in(e):
            if self.entry_nuevo_pendiente.get() == "Ej: Comprar reactivos, reportar urocultivos...":
                self.entry_nuevo_pendiente.delete(0, tk.END)
                self.entry_nuevo_pendiente.config(fg='black')

        def _on_focus_out(e):
            if not self.entry_nuevo_pendiente.get().strip():
                self.entry_nuevo_pendiente.insert(0, "Ej: Comprar reactivos, reportar urocultivos...")
                self.entry_nuevo_pendiente.config(fg='gray')

        self.entry_nuevo_pendiente.bind('<FocusIn>', _on_focus_in)
        self.entry_nuevo_pendiente.bind('<FocusOut>', _on_focus_out)
        self.entry_nuevo_pendiente.bind('<Return>', lambda e: self._agregar_pendiente())

        tk.Button(add_frame, text="➕ Agregar", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat',
                 padx=15, pady=5, cursor='hand2',
                 command=self._agregar_pendiente).pack(side='left')

        # Tabla de pendientes
        tree_pend_frame = tk.Frame(pend_frame, bg='white')
        tree_pend_frame.pack(fill='both', expand=True, padx=10, pady=(5, 5))

        pend_cols = ('Descripción', 'Fecha')
        self.tree_pendientes = ttk.Treeview(tree_pend_frame, columns=pend_cols,
                                             show='headings', height=8)
        self.tree_pendientes.heading('Descripción', text='Descripción', anchor='w')
        self.tree_pendientes.heading('Fecha', text='Fecha de Registro', anchor='center')
        self.tree_pendientes.column('Descripción', width=450, anchor='w')
        self.tree_pendientes.column('Fecha', width=150, anchor='center')

        vsb_pend = ttk.Scrollbar(tree_pend_frame, orient='vertical', command=self.tree_pendientes.yview)
        self.tree_pendientes.configure(yscrollcommand=vsb_pend.set)
        self.tree_pendientes.pack(side='left', fill='both', expand=True)
        vsb_pend.pack(side='right', fill='y')

        # Botón para completar/eliminar
        btn_pend_frame = tk.Frame(pend_frame, bg='white')
        btn_pend_frame.pack(fill='x', padx=10, pady=(0, 10))

        tk.Button(btn_pend_frame, text="✔ Completar seleccionado",
                 font=('Segoe UI', 10), bg=COLORS['danger'], fg='white',
                 relief='flat', padx=12, pady=4, cursor='hand2',
                 command=self._completar_pendiente).pack(side='left')

        tk.Label(btn_pend_frame,
                text="Seleccione un pendiente y presione 'Completar' para eliminarlo de la lista",
                font=('Segoe UI', 9), fg=COLORS['text_light'],
                bg='white').pack(side='left', padx=15)

        self._cargar_pendientes()

    def _asegurar_tabla_bioanalistas(self):
        """Crea la tabla Bioanalistas en la BD si no existe."""
        try:
            db.query("SELECT TOP 1 BioanalistaID FROM Bioanalistas")
        except Exception:
            try:
                db.execute(
                    "CREATE TABLE Bioanalistas ("
                    "BioanalistaID AUTOINCREMENT PRIMARY KEY, "
                    "NombreCompleto TEXT(200), "
                    "Cedula TEXT(20), "
                    "NumeroRegistro TEXT(50), "
                    "AreaID LONG, "
                    "RutaFirma TEXT(500), "
                    "Activo BIT DEFAULT TRUE)"
                )
            except Exception as e:
                print(f"Error creando tabla Bioanalistas: {e}")

        # Asegurar areas clinicas requeridas con IDs fijos y nomenclatura uniforme
        # Los AreaID 1,2,5,6,7,8,9,10 estan hardcodeados en plantillas y formularios
        self._asegurar_areas_clinicas()

        # Siempre actualizar catalogo de Microbiologia (agrega pruebas/parametros faltantes)
        try:
            self._crear_catalogo_microbiologia()
        except Exception:
            pass

        # Asegurar directorio de firmas
        try:
            import os
            firmas_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'firmas')
            if not os.path.exists(firmas_dir):
                os.makedirs(firmas_dir)
        except Exception:
            pass

    def _asegurar_areas_clinicas(self):
        """
        Garantiza que existan exactamente las areas clinicas requeridas con los AreaIDs
        correctos (hardcodeados en plantillas y formularios) y nomenclatura uniforme.
        Corrige nombres inconsistentes y elimina duplicados innecesarios.
        """
        # Areas requeridas: (AreaID, CodigoArea, NombreArea, Secuencia)
        # IDs 1,2,5,6,7,8,9,10 estan fijos en plantillas_reportes.py y form_inf_config.py
        AREAS_REQUERIDAS = [
            (1,  'HEM', 'Hematología',    1),
            (2,  'QUI', 'Química',         2),
            (5,  'COA', 'Coagulación',     3),
            (6,  'URO', 'Uroanálisis',     4),
            (7,  'PAR', 'Parasitología',   5),
            (8,  'TIR', 'Tiroides',        6),
            (9,  'SER', 'Serología',       7),
            (10, 'MIC', 'Microbiología',   8),
        ]
        # El area 'General' no tiene ID fijo; se usa para bioanalistas sin area especifica
        AREA_GENERAL = ('GEN', 'General', 9)

        try:
            for area_id, codigo, nombre, secuencia in AREAS_REQUERIDAS:
                existente = db.query_one(
                    f"SELECT AreaID, NombreArea, CodigoArea FROM Areas WHERE AreaID = {area_id}"
                )
                if existente:
                    # Corregir nombre/codigo si difieren (normalizar)
                    if existente.get('NombreArea') != nombre or existente.get('CodigoArea') != codigo:
                        db.execute(
                            f"UPDATE Areas SET NombreArea = '{nombre}', "
                            f"CodigoArea = '{codigo}', Secuencia = {secuencia}, Activo = True "
                            f"WHERE AreaID = {area_id}"
                        )
                else:
                    # Verificar si existe con el nombre pero diferente ID (duplicado)
                    # Nombres alternativos conocidos por inconsistencias históricas
                    nombres_alt = [nombre, nombre.replace('í', 'i').replace('é', 'e')
                                   .replace('ó', 'o').replace('á', 'a').replace('ú', 'u'),
                                   nombre.upper()]
                    for n_alt in nombres_alt:
                        dup = db.query_one(
                            f"SELECT AreaID FROM Areas WHERE NombreArea = '{n_alt}'"
                        )
                        if dup and dup['AreaID'] != area_id:
                            # Reasignar pruebas al ID correcto y eliminar el duplicado
                            dup_id = dup['AreaID']
                            db.execute(
                                f"UPDATE Pruebas SET AreaID = {area_id} WHERE AreaID = {dup_id}"
                            )
                            db.execute(f"DELETE FROM Areas WHERE AreaID = {dup_id}")
                            break
                    # Insertar con el ID correcto usando INSERT con valor de AUTOINCREMENT forzado
                    try:
                        db.execute(
                            f"INSERT INTO Areas (AreaID, CodigoArea, NombreArea, Secuencia, Activo) "
                            f"VALUES ({area_id}, '{codigo}', '{nombre}', {secuencia}, True)"
                        )
                    except Exception:
                        # Si no acepta AreaID explicito (AUTOINCREMENT), insertar sin ID
                        # y luego no podemos garantizar el ID - solo loggear
                        print(f"Advertencia: no se pudo crear area '{nombre}' con AreaID={area_id}")

            # Area General (sin ID fijo)
            codigo_gen, nombre_gen, sec_gen = AREA_GENERAL
            existe_gen = db.query_one(
                f"SELECT AreaID FROM Areas WHERE CodigoArea = '{codigo_gen}' "
                f"OR NombreArea = '{nombre_gen}'"
            )
            if not existe_gen:
                db.execute(
                    f"INSERT INTO Areas (CodigoArea, NombreArea, Secuencia, Activo) "
                    f"VALUES ('{codigo_gen}', '{nombre_gen}', {sec_gen}, True)"
                )
            else:
                db.execute(
                    f"UPDATE Areas SET CodigoArea = '{codigo_gen}', NombreArea = '{nombre_gen}', "
                    f"Secuencia = {sec_gen} WHERE AreaID = {existe_gen['AreaID']}"
                )

        except Exception as e:
            print(f"Error asegurando areas clinicas: {e}")

    def _crear_catalogo_microbiologia(self):
        """
        Crea el catalogo completo de pruebas y parametros de Microbiologia/Bacteriologia.
        Incluye paneles de antibioticos diferenciados por tipo de muestra segun CLSI.
        """
        try:
            # Obtener el AreaID de Microbiologia por ID fijo (10)
            area = db.query_one("SELECT AreaID FROM Areas WHERE AreaID = 10")
            if not area:
                return
            area_id = area['AreaID']

            # Opciones de sensibilidad para antibiograma (CLSI/EUCAST)
            opciones_sensibilidad = ['S', 'I', 'R', 'SENSIBLE', 'INTERMEDIO', 'RESISTENTE', 'SDD']

            # =================================================================
            # PANELES DE ANTIBIOTICOS DIFERENCIADOS POR TIPO DE MUESTRA (CLSI)
            # =================================================================

            # Panel urinario (Enterobacterias urinarias)
            atb_urinario = [
                'Amikacina', 'Amoxicilina/Ac. Clavulanico', 'Ampicilina',
                'Ampicilina/Sulbactam', 'Cefalexina', 'Cefazolina',
                'Cefepime', 'Cefotaxima', 'Ceftazidima', 'Ceftriaxona',
                'Cefuroxima', 'Ciprofloxacina', 'Ertapenem',
                'Fosfomicina', 'Gentamicina', 'Imipenem',
                'Levofloxacina', 'Meropenem', 'Nitrofurantoina',
                'Norfloxacina', 'Piperacilina/Tazobactam',
                'Tobramicina', 'Trimetoprim/Sulfametoxazol',
            ]

            # Panel sangre/hemocultivo (amplio espectro)
            atb_hemocultivo = [
                'Amikacina', 'Amoxicilina/Ac. Clavulanico', 'Ampicilina',
                'Ampicilina/Sulbactam', 'Aztreonam', 'Cefazolina',
                'Cefepime', 'Cefotaxima', 'Ceftazidima', 'Ceftriaxona',
                'Ciprofloxacina', 'Clindamicina', 'Colistina',
                'Daptomicina', 'Ertapenem', 'Eritromicina',
                'Gentamicina', 'Imipenem', 'Levofloxacina',
                'Linezolid', 'Meropenem', 'Oxacilina',
                'Penicilina', 'Piperacilina/Tazobactam',
                'Rifampicina', 'Teicoplanina', 'Tigeciclina',
                'Tobramicina', 'Trimetoprim/Sulfametoxazol',
                'Vancomicina',
            ]

            # Panel enteropatogenos (coprocultivo)
            atb_coprocultivo = [
                'Amoxicilina/Ac. Clavulanico', 'Ampicilina', 'Azitromicina',
                'Ceftriaxona', 'Ciprofloxacina', 'Cloranfenicol',
                'Levofloxacina', 'Tetraciclina',
                'Trimetoprim/Sulfametoxazol',
            ]

            # Panel secreciones / tejidos blandos
            atb_secreciones = [
                'Amikacina', 'Amoxicilina/Ac. Clavulanico', 'Ampicilina',
                'Ampicilina/Sulbactam', 'Cefazolina', 'Cefepime',
                'Cefotaxima', 'Ceftazidima', 'Ceftriaxona',
                'Ciprofloxacina', 'Clindamicina', 'Dicloxacilina',
                'Eritromicina', 'Gentamicina', 'Imipenem',
                'Levofloxacina', 'Linezolid', 'Meropenem',
                'Metronidazol', 'Oxacilina', 'Penicilina',
                'Piperacilina/Tazobactam', 'Rifampicina',
                'Trimetoprim/Sulfametoxazol', 'Vancomicina',
            ]

            # Panel respiratorio (esputo, secrecion faringea)
            atb_respiratorio = [
                'Amoxicilina/Ac. Clavulanico', 'Ampicilina',
                'Azitromicina', 'Cefepime', 'Cefotaxima',
                'Ceftriaxona', 'Cefuroxima', 'Ciprofloxacina',
                'Claritromicina', 'Clindamicina', 'Eritromicina',
                'Gentamicina', 'Imipenem', 'Levofloxacina',
                'Linezolid', 'Meropenem', 'Moxifloxacina',
                'Oxacilina', 'Penicilina',
                'Piperacilina/Tazobactam',
                'Trimetoprim/Sulfametoxazol', 'Vancomicina',
            ]

            # Panel genital (vaginal, uretral)
            atb_genital = [
                'Amoxicilina/Ac. Clavulanico', 'Ampicilina',
                'Azitromicina', 'Ceftriaxona', 'Ciprofloxacina',
                'Clindamicina', 'Doxiciclina', 'Eritromicina',
                'Gentamicina', 'Levofloxacina', 'Metronidazol',
                'Penicilina', 'Tetraciclina',
                'Trimetoprim/Sulfametoxazol',
            ]

            # Panel otico/ocular
            atb_otico = [
                'Amikacina', 'Amoxicilina/Ac. Clavulanico',
                'Ceftazidima', 'Ceftriaxona', 'Ciprofloxacina',
                'Clindamicina', 'Eritromicina', 'Gentamicina',
                'Levofloxacina', 'Oxacilina',
                'Piperacilina/Tazobactam',
                'Trimetoprim/Sulfametoxazol', 'Vancomicina',
            ]

            # Panel liquidos corporales (LCR, pleural, etc.)
            atb_liquidos = [
                'Amikacina', 'Ampicilina', 'Cefepime', 'Cefotaxima',
                'Ceftazidima', 'Ceftriaxona', 'Ciprofloxacina',
                'Cloranfenicol', 'Gentamicina', 'Imipenem',
                'Levofloxacina', 'Linezolid', 'Meropenem',
                'Oxacilina', 'Penicilina',
                'Piperacilina/Tazobactam', 'Rifampicina',
                'Trimetoprim/Sulfametoxazol', 'Vancomicina',
            ]

            # Panel cateter (piel/dispositivo)
            atb_cateter = [
                'Cefazolina', 'Cefepime', 'Ciprofloxacina',
                'Clindamicina', 'Daptomicina', 'Eritromicina',
                'Gentamicina', 'Imipenem', 'Levofloxacina',
                'Linezolid', 'Meropenem', 'Oxacilina',
                'Piperacilina/Tazobactam', 'Rifampicina',
                'Teicoplanina', 'Trimetoprim/Sulfametoxazol',
                'Vancomicina',
            ]

            # Panel antimicotico (para cultivos de hongos)
            atb_antimicotico = [
                'Anfotericina B', 'Caspofungina', 'Fluconazol',
                'Flucitosina', 'Itraconazol', 'Micafungina',
                'Voriconazol',
            ]

            # =================================================================
            # DEFINICION COMPLETA DE PRUEBAS DE MICROBIOLOGIA
            # =================================================================
            pruebas_micro = {
                # -----------------------------------------------------------
                # MIC001 - UROCULTIVO
                # -----------------------------------------------------------
                'MIC001': {
                    'nombre': 'Urocultivo',
                    'parametros': [
                        # Datos de la muestra
                        ('MIC001-01', 'Tipo de Muestra', 'TEXTO', 'Orina', 'Datos de Muestra', None),
                        ('MIC001-02', 'Metodo de Recoleccion', 'TEXTO', 'Chorro medio / Cateterizada / Puncion suprapubica', 'Datos de Muestra', None),
                        ('MIC001-03', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC001-04', 'Temperatura de Incubacion', 'TEXTO', '35-37 C', 'Datos de Muestra', None),
                        ('MIC001-05', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC001-06', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC001-07', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC001-08', 'Bacterias en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC001-09', 'Celulas Epiteliales', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC001-10', 'Levaduras', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC001-11', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC001-12', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC001-13', 'Segundo Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC001-14', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        # Recuento
                        ('MIC001-15', 'Recuento de Colonias', 'TEXTO', '>100,000 UFC/mL = Significativo', 'Recuento de Colonias', None),
                        # Observaciones
                        ('MIC001-16', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_urinario
                },

                # -----------------------------------------------------------
                # MIC002 - HEMOCULTIVO
                # -----------------------------------------------------------
                'MIC002': {
                    'nombre': 'Hemocultivo',
                    'parametros': [
                        # Datos de la muestra
                        ('MIC002-01', 'Tipo de Muestra', 'TEXTO', 'Sangre venosa', 'Datos de Muestra', None),
                        ('MIC002-02', 'Numero de Muestra', 'TEXTO', '1ra / 2da / 3ra muestra', 'Datos de Muestra', None),
                        ('MIC002-03', 'Volumen de Sangre', 'TEXTO', 'Adultos: 8-10 mL / Pediatricos: 1-3 mL', 'Datos de Muestra', None),
                        ('MIC002-04', 'Frasco', 'TEXTO', 'Aerobio / Anaerobio / Ambos', 'Datos de Muestra', None),
                        ('MIC002-05', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC002-06', 'Temperatura de Incubacion', 'TEXTO', '35-37 C', 'Datos de Muestra', None),
                        ('MIC002-07', 'Tiempo de Incubacion', 'TEXTO', '24-48-72 horas / 5-7 dias', 'Datos de Muestra', None),
                        ('MIC002-08', 'Fecha de Positividad', 'TEXTO', '', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC002-09', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC002-10', 'Morfologia en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC002-11', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        ('MIC002-12', 'Resultado Preliminar (24h)', 'TEXTO', '', 'Resultado del Cultivo', None),
                        ('MIC002-13', 'Resultado Preliminar (48h)', 'TEXTO', '', 'Resultado del Cultivo', None),
                        ('MIC002-14', 'Resultado Final', 'TEXTO', '', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC002-15', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC002-16', 'Segundo Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC002-17', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        # Observaciones
                        ('MIC002-18', 'Interpretacion Clinica', 'TEXTO', '', 'Observaciones', None),
                        ('MIC002-19', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_hemocultivo
                },

                # -----------------------------------------------------------
                # MIC003 - COPROCULTIVO
                # -----------------------------------------------------------
                'MIC003': {
                    'nombre': 'Coprocultivo',
                    'parametros': [
                        # Datos de la muestra
                        ('MIC003-01', 'Tipo de Muestra', 'TEXTO', 'Heces', 'Datos de Muestra', None),
                        ('MIC003-02', 'Aspecto de la Muestra', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC003-03', 'Consistencia', 'TEXTO', 'Formada / Blanda / Liquida / Mucosa / Sanguinolenta', 'Datos de Muestra', None),
                        ('MIC003-04', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC003-05', 'Temperatura de Incubacion', 'TEXTO', '35-37 C', 'Datos de Muestra', None),
                        ('MIC003-06', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC003-07', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC003-08', 'Leucocitos Fecales', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC003-09', 'Eritrocitos Fecales', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC003-10', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        ('MIC003-11', 'Busqueda de Salmonella', 'TEXTO', '', 'Resultado del Cultivo', None),
                        ('MIC003-12', 'Busqueda de Shigella', 'TEXTO', '', 'Resultado del Cultivo', None),
                        ('MIC003-13', 'Busqueda de Campylobacter', 'TEXTO', '', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC003-14', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC003-15', 'Serotipo', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC003-16', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        # Observaciones
                        ('MIC003-17', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_coprocultivo
                },

                # -----------------------------------------------------------
                # MIC004 - CULTIVO DE SECRECION (GENERAL)
                # -----------------------------------------------------------
                'MIC004': {
                    'nombre': 'Cultivo de Secrecion',
                    'parametros': [
                        ('MIC004-01', 'Tipo de Muestra', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC004-02', 'Sitio Anatomico', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC004-03', 'Aspecto de la Muestra', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC004-04', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC004-05', 'Temperatura de Incubacion', 'TEXTO', '35-37 C', 'Datos de Muestra', None),
                        ('MIC004-06', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC004-07', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC004-08', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC004-09', 'Celulas Epiteliales', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC004-10', 'Bacterias en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC004-11', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC004-12', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC004-13', 'Segundo Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC004-14', 'Recuento de Colonias', 'TEXTO', '', 'Recuento de Colonias', None),
                        ('MIC004-15', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        # Observaciones
                        ('MIC004-16', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_secreciones
                },

                # -----------------------------------------------------------
                # MIC005 - CULTIVO DE SECRECION FARINGEA
                # -----------------------------------------------------------
                'MIC005': {
                    'nombre': 'Cultivo de Secrecion Faringea',
                    'parametros': [
                        ('MIC005-01', 'Tipo de Muestra', 'TEXTO', 'Secrecion faringea / amigdalina', 'Datos de Muestra', None),
                        ('MIC005-02', 'Aspecto', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC005-03', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC005-04', 'Temperatura de Incubacion', 'TEXTO', '35-37 C', 'Datos de Muestra', None),
                        ('MIC005-05', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC005-06', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC005-07', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC005-08', 'Celulas Epiteliales', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC005-09', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        ('MIC005-10', 'Beta Hemolisis', 'TEXTO', 'Positiva / Negativa', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC005-11', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC005-12', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        # Observaciones
                        ('MIC005-13', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_respiratorio
                },

                # -----------------------------------------------------------
                # MIC006 - CULTIVO DE SECRECION VAGINAL
                # -----------------------------------------------------------
                'MIC006': {
                    'nombre': 'Cultivo de Secrecion Vaginal',
                    'parametros': [
                        ('MIC006-01', 'Tipo de Muestra', 'TEXTO', 'Secrecion vaginal / endocervical', 'Datos de Muestra', None),
                        ('MIC006-02', 'Aspecto', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC006-03', 'pH Vaginal', 'TEXTO', 'Normal: 3.8 - 4.5', 'Datos de Muestra', None),
                        ('MIC006-04', 'Prueba de KOH (Whiff Test)', 'TEXTO', 'Positivo / Negativo', 'Datos de Muestra', None),
                        ('MIC006-05', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC006-06', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram / Nugent
                        ('MIC006-07', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC006-08', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC006-09', 'Celulas Epiteliales', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC006-10', 'Celulas Clave (Clue Cells)', 'TEXTO', 'Presentes / Ausentes', 'Coloracion de Gram', None),
                        ('MIC006-11', 'Lactobacilos (Flora Doderlein)', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC006-12', 'Levaduras / Pseudohifas', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC006-13', 'Trichomonas vaginalis', 'TEXTO', 'No se observan / Presentes', 'Coloracion de Gram', None),
                        ('MIC006-14', 'Score de Nugent', 'TEXTO', '0-3 Normal / 4-6 Intermedio / 7-10 Vaginosis', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC006-15', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC006-16', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC006-17', 'Segundo Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC006-18', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        # Observaciones
                        ('MIC006-19', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_genital
                },

                # -----------------------------------------------------------
                # MIC007 - CULTIVO DE SECRECION OTICA
                # -----------------------------------------------------------
                'MIC007': {
                    'nombre': 'Cultivo de Secrecion Otica',
                    'parametros': [
                        ('MIC007-01', 'Tipo de Muestra', 'TEXTO', 'Secrecion otica', 'Datos de Muestra', None),
                        ('MIC007-02', 'Oido', 'TEXTO', 'Derecho / Izquierdo / Ambos', 'Datos de Muestra', None),
                        ('MIC007-03', 'Aspecto', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC007-04', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC007-05', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC007-06', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC007-07', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC007-08', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC007-09', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC007-10', 'Segundo Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC007-11', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC007-12', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_otico
                },

                # -----------------------------------------------------------
                # MIC008 - CULTIVO DE SECRECION URETRAL
                # -----------------------------------------------------------
                'MIC008': {
                    'nombre': 'Cultivo de Secrecion Uretral',
                    'parametros': [
                        ('MIC008-01', 'Tipo de Muestra', 'TEXTO', 'Secrecion uretral', 'Datos de Muestra', None),
                        ('MIC008-02', 'Aspecto', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC008-03', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC008-04', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC008-05', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC008-06', 'Leucocitos en Gram', 'TEXTO', '>5 PMN/campo = Uretritis', 'Coloracion de Gram', None),
                        ('MIC008-07', 'Diplococos Gram Negativos Intracelulares', 'TEXTO', 'Presentes / Ausentes', 'Coloracion de Gram', None),
                        ('MIC008-08', 'Celulas Epiteliales', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC008-09', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC008-10', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC008-11', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC008-12', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_genital
                },

                # -----------------------------------------------------------
                # MIC009 - CULTIVO DE ESPUTO
                # -----------------------------------------------------------
                'MIC009': {
                    'nombre': 'Cultivo de Esputo',
                    'parametros': [
                        ('MIC009-01', 'Tipo de Muestra', 'TEXTO', 'Esputo / Aspirado bronquial / Lavado broncoalveolar', 'Datos de Muestra', None),
                        ('MIC009-02', 'Aspecto', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC009-03', 'Calidad de la Muestra (Murray-Washington)', 'TEXTO', 'Grupo 1-5 / Apta / No apta', 'Datos de Muestra', None),
                        ('MIC009-04', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC009-05', 'Temperatura de Incubacion', 'TEXTO', '35-37 C', 'Datos de Muestra', None),
                        ('MIC009-06', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC009-07', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC009-08', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC009-09', 'Celulas Epiteliales', 'TEXTO', '<10/campo = muestra apta', 'Coloracion de Gram', None),
                        ('MIC009-10', 'Bacterias en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC009-11', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC009-12', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC009-13', 'Segundo Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC009-14', 'Recuento de Colonias', 'TEXTO', '', 'Recuento de Colonias', None),
                        ('MIC009-15', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC009-16', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_respiratorio
                },

                # -----------------------------------------------------------
                # MIC010 - CULTIVO DE LIQUIDOS CORPORALES
                # -----------------------------------------------------------
                'MIC010': {
                    'nombre': 'Cultivo de Liquidos Corporales',
                    'parametros': [
                        ('MIC010-01', 'Tipo de Muestra', 'TEXTO', 'LCR / Pleural / Ascitico / Sinovial / Pericardico', 'Datos de Muestra', None),
                        ('MIC010-02', 'Aspecto', 'TEXTO', 'Claro / Turbio / Hemorrágico / Xantocromico', 'Datos de Muestra', None),
                        ('MIC010-03', 'Volumen Recibido', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC010-04', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC010-05', 'Temperatura de Incubacion', 'TEXTO', '35-37 C', 'Datos de Muestra', None),
                        ('MIC010-06', 'Tiempo de Incubacion', 'TEXTO', '24-48-72 horas / 5-7 dias', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC010-07', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC010-08', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC010-09', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC010-10', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC010-11', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC010-12', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_liquidos
                },

                # -----------------------------------------------------------
                # MIC011 - CULTIVO DE PUNTA DE CATETER
                # -----------------------------------------------------------
                'MIC011': {
                    'nombre': 'Cultivo de Punta de Cateter',
                    'parametros': [
                        ('MIC011-01', 'Tipo de Muestra', 'TEXTO', 'Punta de cateter', 'Datos de Muestra', None),
                        ('MIC011-02', 'Tipo de Cateter', 'TEXTO', 'Central / Periferico / PICC / Port-a-Cath', 'Datos de Muestra', None),
                        ('MIC011-03', 'Metodo', 'TEXTO', 'Semicuantitativo (Maki) / Cuantitativo', 'Datos de Muestra', None),
                        ('MIC011-04', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Resultado del cultivo
                        ('MIC011-05', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        ('MIC011-06', 'Recuento de Colonias', 'TEXTO', '>15 UFC = Significativo (Maki)', 'Recuento de Colonias', None),
                        # Identificacion
                        ('MIC011-07', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC011-08', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC011-09', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_cateter
                },

                # -----------------------------------------------------------
                # MIC012 - KOH / EXAMEN DIRECTO DE HONGOS
                # -----------------------------------------------------------
                'MIC012': {
                    'nombre': 'KOH - Examen Directo de Hongos',
                    'parametros': [
                        ('MIC012-01', 'Tipo de Muestra', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC012-02', 'Sitio Anatomico', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC012-03', 'Examen Directo (KOH)', 'TEXTO', 'Positivo / Negativo', 'Resultado', None),
                        ('MIC012-04', 'Elementos Micoticos Observados', 'TEXTO', 'Hifas / Esporas / Levaduras / Pseudohifas', 'Resultado', None),
                        ('MIC012-05', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': []  # No aplica antibiograma para KOH
                },

                # -----------------------------------------------------------
                # MIC013 - CULTIVO DE SECRECION DE HERIDA
                # -----------------------------------------------------------
                'MIC013': {
                    'nombre': 'Cultivo de Secrecion de Herida',
                    'parametros': [
                        ('MIC013-01', 'Tipo de Muestra', 'TEXTO', 'Secrecion de herida', 'Datos de Muestra', None),
                        ('MIC013-02', 'Sitio Anatomico', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC013-03', 'Tipo de Herida', 'TEXTO', 'Quirurgica / Traumatica / Quemadura / Ulcera / Absceso', 'Datos de Muestra', None),
                        ('MIC013-04', 'Aspecto', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC013-05', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC013-06', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC013-07', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC013-08', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC013-09', 'Bacterias en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC013-10', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC013-11', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC013-12', 'Segundo Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC013-13', 'Recuento de Colonias', 'TEXTO', '', 'Recuento de Colonias', None),
                        ('MIC013-14', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC013-15', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_secreciones
                },

                # -----------------------------------------------------------
                # MIC014 - CULTIVO DE SECRECION NASAL
                # -----------------------------------------------------------
                'MIC014': {
                    'nombre': 'Cultivo de Secrecion Nasal',
                    'parametros': [
                        ('MIC014-01', 'Tipo de Muestra', 'TEXTO', 'Secrecion nasal / Hisopado nasal', 'Datos de Muestra', None),
                        ('MIC014-02', 'Fosa Nasal', 'TEXTO', 'Derecha / Izquierda / Ambas', 'Datos de Muestra', None),
                        ('MIC014-03', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC014-04', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC014-05', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC014-06', 'Eosinofilos Nasales', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado del cultivo
                        ('MIC014-07', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC014-08', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC014-09', 'Portador SARM', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC014-10', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC014-11', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_respiratorio
                },

                # -----------------------------------------------------------
                # MIC015 - BACILOSCOPIA (BK / BAAR)
                # -----------------------------------------------------------
                'MIC015': {
                    'nombre': 'Baciloscopia (BK/BAAR)',
                    'parametros': [
                        ('MIC015-01', 'Tipo de Muestra', 'TEXTO', 'Esputo / Orina / LCR / Otro', 'Datos de Muestra', None),
                        ('MIC015-02', 'Numero de Muestra', 'TEXTO', '1ra / 2da / 3ra', 'Datos de Muestra', None),
                        ('MIC015-03', 'Aspecto de la Muestra', 'TEXTO', '', 'Datos de Muestra', None),
                        # Coloracion de Ziehl-Neelsen
                        ('MIC015-04', 'Coloracion de Ziehl-Neelsen', 'TEXTO', '', 'Coloracion Acido-Resistente', None),
                        ('MIC015-05', 'Resultado BAAR', 'TEXTO', 'Negativo / Positivo (+) / (++) / (+++)', 'Coloracion Acido-Resistente', None),
                        ('MIC015-06', 'Numero de BAAR Observados', 'TEXTO', 'Segun escala OMS', 'Coloracion Acido-Resistente', None),
                        ('MIC015-07', 'Campos Observados', 'TEXTO', 'Minimo 100 campos', 'Coloracion Acido-Resistente', None),
                        # Observaciones
                        ('MIC015-08', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': []  # No aplica antibiograma para baciloscopia
                },

                # -----------------------------------------------------------
                # MIC016 - CULTIVO MICOLOGICO (HONGOS)
                # -----------------------------------------------------------
                'MIC016': {
                    'nombre': 'Cultivo Micologico',
                    'parametros': [
                        ('MIC016-01', 'Tipo de Muestra', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC016-02', 'Sitio Anatomico', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC016-03', 'Examen Directo (KOH)', 'TEXTO', 'Positivo / Negativo', 'Examen Directo', None),
                        ('MIC016-04', 'Elementos Micoticos en KOH', 'TEXTO', '', 'Examen Directo', None),
                        ('MIC016-05', 'Medio de Cultivo', 'TEXTO', 'Sabouraud / Mycosel / CHROMagar', 'Datos de Muestra', None),
                        ('MIC016-06', 'Temperatura de Incubacion', 'TEXTO', '25-30 C / 35-37 C', 'Datos de Muestra', None),
                        ('MIC016-07', 'Tiempo de Incubacion', 'TEXTO', '7-21 dias', 'Datos de Muestra', None),
                        # Resultado del cultivo
                        ('MIC016-08', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        ('MIC016-09', 'Macroscopia de la Colonia', 'TEXTO', '', 'Resultado del Cultivo', None),
                        ('MIC016-10', 'Microscopia de la Colonia', 'TEXTO', '', 'Resultado del Cultivo', None),
                        # Identificacion
                        ('MIC016-11', 'Hongo Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC016-12', 'Especie', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC016-13', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC016-14', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_antimicotico
                },

                # -----------------------------------------------------------
                # MIC017 - CULTIVO DE SECRECION CONJUNTIVAL (OCULAR)
                # -----------------------------------------------------------
                'MIC017': {
                    'nombre': 'Cultivo de Secrecion Conjuntival',
                    'parametros': [
                        ('MIC017-01', 'Tipo de Muestra', 'TEXTO', 'Secrecion conjuntival / ocular', 'Datos de Muestra', None),
                        ('MIC017-02', 'Ojo', 'TEXTO', 'Derecho / Izquierdo / Ambos', 'Datos de Muestra', None),
                        ('MIC017-03', 'Medio de Cultivo', 'TEXTO', '', 'Datos de Muestra', None),
                        ('MIC017-04', 'Tiempo de Incubacion', 'TEXTO', '24-48 horas', 'Datos de Muestra', None),
                        # Coloracion de Gram
                        ('MIC017-05', 'Coloracion de Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        ('MIC017-06', 'Leucocitos en Gram', 'TEXTO', '', 'Coloracion de Gram', None),
                        # Resultado
                        ('MIC017-07', 'Resultado del Cultivo', 'TEXTO', 'Positivo / Negativo', 'Resultado del Cultivo', None),
                        ('MIC017-08', 'Germen Aislado', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC017-09', 'Metodo de Identificacion', 'TEXTO', '', 'Identificacion del Germen', None),
                        ('MIC017-10', 'Observaciones', 'TEXTO', '', 'Observaciones', None),
                    ],
                    'antibioticos': atb_otico
                },
            }

            # ---------------------------------------------------------------
            # Insertar las pruebas y parametros
            # ---------------------------------------------------------------
            for codigo_prueba, def_prueba in pruebas_micro.items():
                # Verificar si la prueba ya existe
                existe = db.query_one(
                    f"SELECT PruebaID FROM Pruebas WHERE CodigoPrueba = '{codigo_prueba}'"
                )

                if existe:
                    prueba_id = existe['PruebaID']
                    es_nueva = False
                else:
                    # Insertar la prueba nueva
                    db.insert('Pruebas', {
                        'CodigoPrueba': codigo_prueba,
                        'NombrePrueba': def_prueba['nombre'],
                        'AreaID': area_id,
                        'Activo': True
                    })
                    prueba = db.query_one(f"SELECT MAX(PruebaID) as ID FROM Pruebas")
                    prueba_id = prueba['ID']
                    es_nueva = True

                # Obtener secuencia maxima actual para esta prueba
                max_seq = db.query_one(
                    f"SELECT MAX(Secuencia) as MaxSeq FROM ParametrosPrueba WHERE PruebaID = {prueba_id}"
                )
                secuencia = (max_seq['MaxSeq'] or 0) + 1 if max_seq and max_seq['MaxSeq'] else 1

                params_agregados = 0

                # Insertar parametros base de la prueba (solo los que falten)
                for cod_param, nombre_param, tipo, referencia, seccion, formula in def_prueba['parametros']:
                    # Verificar si el parametro existe en la tabla Parametros
                    param_existe = db.query_one(
                        f"SELECT ParametroID FROM Parametros WHERE CodigoParametro = '{cod_param}'"
                    )
                    if param_existe:
                        param_id = param_existe['ParametroID']
                    else:
                        db.insert('Parametros', {
                            'CodigoParametro': cod_param,
                            'NombreParametro': nombre_param,
                            'TipoResultado': tipo,
                            'Observaciones': referencia,
                            'Seccion': seccion,
                            'FormulaCalculo': formula,
                            'Activo': True
                        })
                        nuevo = db.query_one("SELECT MAX(ParametroID) as ID FROM Parametros")
                        param_id = nuevo['ID']

                    # Verificar si ya esta vinculado a esta prueba
                    vinculo_existe = db.query_one(
                        f"SELECT ParametroPruebaID FROM ParametrosPrueba "
                        f"WHERE PruebaID = {prueba_id} AND ParametroID = {param_id}"
                    )
                    if not vinculo_existe:
                        db.insert('ParametrosPrueba', {
                            'PruebaID': prueba_id,
                            'ParametroID': param_id,
                            'Secuencia': secuencia,
                            'Obligatorio': True
                        })
                        secuencia += 1
                        params_agregados += 1

                # Insertar antibioticos como parametros de antibiograma (solo los que falten)
                for idx_atb, antibiotico in enumerate(def_prueba.get('antibioticos', []), 1):
                    # Verificar si este antibiotico ya esta vinculado a esta prueba
                    # Usar db.escape para evitar problemas con caracteres especiales
                    atb_nombre_escaped = antibiotico.replace("'", "''")
                    atb_vinculado = db.query_one(
                        f"SELECT pp.ParametroPruebaID FROM ParametrosPrueba pp "
                        f"INNER JOIN Parametros p ON pp.ParametroID = p.ParametroID "
                        f"WHERE pp.PruebaID = {prueba_id} AND p.NombreParametro = '{atb_nombre_escaped}' "
                        f"AND p.Seccion = 'Antibiograma'"
                    )
                    if atb_vinculado:
                        continue

                    # Generar codigo unico: usar indice del antibiotico (no secuencia) para evitar colisiones
                    # Limpiar nombre para codigo: solo alfanumericos, max 6 chars
                    atb_clean = ''.join(c for c in antibiotico if c.isalpha())[:6].upper()
                    cod_atb = f"{codigo_prueba}-ATB-{atb_clean}{idx_atb:02d}"

                    # Verificar si el codigo ya existe (evitar duplicados)
                    cod_existe = db.query_one(
                        f"SELECT ParametroID FROM Parametros WHERE CodigoParametro = '{cod_atb}'"
                    )
                    if cod_existe:
                        atb_param_id = cod_existe['ParametroID']
                    else:
                        db.insert('Parametros', {
                            'CodigoParametro': cod_atb,
                            'NombreParametro': antibiotico,
                            'TipoResultado': 'TEXTO',
                            'Observaciones': 'S=Sensible / I=Intermedio / R=Resistente / SDD=Dosis Dependiente',
                            'Seccion': 'Antibiograma',
                            'FormulaCalculo': None,
                            'Activo': True
                        })
                        nuevo_atb = db.query_one("SELECT MAX(ParametroID) as ID FROM Parametros")
                        atb_param_id = nuevo_atb['ID']

                        # Crear opciones predefinidas para sensibilidad
                        for orden, opcion in enumerate(opciones_sensibilidad, 1):
                            db.insert('OpcionesParametro', {
                                'ParametroID': atb_param_id,
                                'Valor': opcion,
                                'Orden': orden,
                                'Frecuencia': 0,
                                'Activo': True
                            })

                    # Verificar que el vinculo no exista antes de insertar
                    vinculo_atb_existe = db.query_one(
                        f"SELECT ParametroPruebaID FROM ParametrosPrueba "
                        f"WHERE PruebaID = {prueba_id} AND ParametroID = {atb_param_id}"
                    )
                    if not vinculo_atb_existe:
                        db.insert('ParametrosPrueba', {
                            'PruebaID': prueba_id,
                            'ParametroID': atb_param_id,
                            'Secuencia': secuencia,
                            'Obligatorio': False
                        })
                        secuencia += 1
                        params_agregados += 1

                if params_agregados > 0:
                    estado = 'creada' if es_nueva else 'actualizada'
                    print(f"  Prueba '{def_prueba['nombre']}' ({codigo_prueba}) {estado}: {params_agregados} parametros agregados.")

            print("Catalogo de Microbiologia/Bacteriologia creado exitosamente.")

        except Exception as e:
            print(f"Error creando catalogo de Microbiologia: {e}")

    def _asegurar_tabla_pendientes(self):
        """Crea la tabla Pendientes en la BD si no existe."""
        try:
            db.query("SELECT TOP 1 PendienteID FROM Pendientes")
        except Exception:
            try:
                db.execute(
                    "CREATE TABLE Pendientes ("
                    "PendienteID AUTOINCREMENT PRIMARY KEY, "
                    "Descripcion TEXT(255), "
                    "FechaCreacion DATETIME)"
                )
            except Exception:
                pass

    def _cargar_pendientes(self):
        """Carga los pendientes desde la BD al Treeview."""
        for item in self.tree_pendientes.get_children():
            self.tree_pendientes.delete(item)

        try:
            pendientes = db.query(
                "SELECT PendienteID, Descripcion, FechaCreacion "
                "FROM Pendientes ORDER BY PendienteID DESC"
            )
        except Exception:
            pendientes = []

        if not pendientes:
            self.tree_pendientes.insert('', 'end', iid='vacio', values=(
                'No hay asuntos pendientes. Agregue uno arriba.', ''))
            return

        for p in pendientes:
            pid = p['PendienteID']
            desc = p.get('Descripcion') or ''
            fecha = p.get('FechaCreacion')
            if fecha:
                try:
                    fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
                except Exception:
                    fecha_str = str(fecha)[:16]
            else:
                fecha_str = ''
            self.tree_pendientes.insert('', 'end', iid=str(pid), values=(desc, fecha_str))

    def _agregar_pendiente(self):
        """Agrega un nuevo pendiente a la BD."""
        texto = self.entry_nuevo_pendiente.get().strip()
        if not texto or texto == "Ej: Comprar reactivos, reportar urocultivos...":
            return
        try:
            db.insert('Pendientes', {
                'Descripcion': texto,
                'FechaCreacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            # Quitar el foco del entry antes de restaurar el placeholder
            self.root.focus_set()
            self.entry_nuevo_pendiente.delete(0, tk.END)
            self.entry_nuevo_pendiente.insert(0, "Ej: Comprar reactivos, reportar urocultivos...")
            self.entry_nuevo_pendiente.config(fg='gray')
            self._cargar_pendientes()
        except Exception as e:
            messagebox.showerror("Error", f"Error al agregar pendiente:\n{e}")

    def _completar_pendiente(self):
        """Elimina los pendientes seleccionados del Treeview y la BD."""
        seleccion = self.tree_pendientes.selection()
        if not seleccion:
            messagebox.showinfo("Aviso", "Seleccione un pendiente de la lista para completarlo.")
            return

        ids = [s for s in seleccion if s != 'vacio']
        if not ids:
            return

        for pid in ids:
            try:
                db.delete('Pendientes', f"PendienteID = {pid}")
            except Exception:
                pass

        self._cargar_pendientes()

    # ============================================================
    # PACIENTES
    # ============================================================

    def show_pacientes(self):
        self.clear_content()
        self.set_title("👥 Gestión de Pacientes")

        # Configurar contenido scrollable
        scrollable = self.setup_scrollable_content()

        # Toolbar
        toolbar = tk.Frame(scrollable, bg=COLORS['bg'])
        toolbar.pack(fill='x', pady=(0, 15))

        tk.Button(toolbar, text="➕ Nuevo Paciente", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.form_paciente).pack(side='left', padx=(0, 15))

        tk.Label(toolbar, text="🔍", font=('Segoe UI', 12), bg=COLORS['bg']).pack(side='left')
        self.search_pac = tk.Entry(toolbar, font=('Segoe UI', 11), width=30, relief='flat',
                                   bg='white', highlightthickness=1, highlightbackground=COLORS['border'])
        self.search_pac.pack(side='left', padx=5, ipady=6)
        self.search_pac.bind('<Return>', lambda e: self.buscar_pacientes())

        tk.Button(toolbar, text="Buscar", font=('Segoe UI', 10), bg=COLORS['success'],
                 fg='white', relief='flat', padx=15, cursor='hand2',
                 command=self.buscar_pacientes).pack(side='left', padx=5)

        tk.Button(toolbar, text="🔄 Refrescar", font=('Segoe UI', 10), bg='#95a5a6',
                 fg='white', relief='flat', padx=10, cursor='hand2',
                 command=lambda: self.cargar_pacientes()).pack(side='left', padx=5)

        # Lista
        list_frame = tk.Frame(scrollable, bg='white')
        list_frame.pack(fill='both', expand=True)

        cols = ('ID', 'Documento', 'Nombres', 'Apellidos', 'Teléfono', 'Fecha Reg.')
        self.tree_pac = ttk.Treeview(list_frame, columns=cols, show='headings')

        widths = [50, 120, 170, 170, 120, 100]
        for c, w in zip(cols, widths):
            self.tree_pac.heading(c, text=c)
            self.tree_pac.column(c, width=w)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_pac.yview)
        self.tree_pac.configure(yscrollcommand=vsb.set)

        self.tree_pac.pack(side='left', fill='both', expand=True, padx=(10,0), pady=10)
        vsb.pack(side='right', fill='y', pady=10, padx=(0,10))

        # Doble click para editar
        self.tree_pac.bind('<Double-1>', self.editar_paciente)

        self.cargar_pacientes()

    def cargar_pacientes(self, filtro=""):
        for item in self.tree_pac.get_children():
            self.tree_pac.delete(item)

        where = ""
        if filtro:
            where = f"WHERE Nombres LIKE '%{filtro}%' OR Apellidos LIKE '%{filtro}%' OR NumeroDocumento LIKE '%{filtro}%'"

        try:
            data = db.query(f"""
                SELECT TOP 200 PacienteID, NumeroDocumento, Nombres, Apellidos, Telefono1, FechaRegistro
                FROM Pacientes {where}
                ORDER BY PacienteID DESC
            """)
            for r in data:
                self.tree_pac.insert('', 'end', values=(
                    r['PacienteID'],
                    r['NumeroDocumento'] or '',
                    r['Nombres'] or '',
                    r['Apellidos'] or '',
                    r['Telefono1'] or '',
                    r['FechaRegistro'].strftime('%d/%m/%Y') if r['FechaRegistro'] else ''
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buscar_pacientes(self):
        self.cargar_pacientes(self.search_pac.get().strip())

    def form_paciente(self, paciente_id=None):
        win = tk.Toplevel(self.root)
        win.title("Editar Paciente" if paciente_id else "Nuevo Paciente")
        win.grab_set()
        win.focus_set()
        win.configure(bg='white')

        # Hacer ventana responsiva
        hacer_ventana_responsiva(win, 600, 700, min_ancho=500, min_alto=600)

        # Header
        header = tk.Frame(win, bg=COLORS['primary'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="👤 " + ("Editar" if paciente_id else "Nuevo") + " Paciente",
                font=('Segoe UI', 14, 'bold'), bg=COLORS['primary'], fg='white').pack(pady=12)

        # Frame con scroll
        container = tk.Frame(win, bg='white')
        container.pack(fill='both', expand=True)

        canvas = tk.Canvas(container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        frame = tk.Frame(canvas, bg='white')

        frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=frame, anchor='nw', width=570)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True, padx=15)
        scrollbar.pack(side='right', fill='y')

        # Scroll con rueda del ratón
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind_all('<MouseWheel>', on_mousewheel)

        entries = {}

        # Fila 1: Tipo Documento + Número Documento
        row1 = tk.Frame(frame, bg='white')
        row1.pack(fill='x', pady=5, padx=10)
        tk.Label(row1, text="Tipo Doc:", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        entries['tipo_doc'] = ttk.Combobox(row1, font=('Segoe UI', 10), width=5, values=['V', 'E', 'P', 'J', 'G'])
        entries['tipo_doc'].pack(side='left', ipady=3, padx=(0, 15))
        tk.Label(row1, text="N° Documento*:", font=('Segoe UI', 10), bg='white', anchor='w').pack(side='left')
        entries['num_doc'] = tk.Entry(row1, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                     highlightthickness=1, highlightbackground=COLORS['border'])
        entries['num_doc'].pack(side='left', fill='x', expand=True, ipady=5, padx=(5, 0))

        # Fila 3: Nombres
        row3 = tk.Frame(frame, bg='white')
        row3.pack(fill='x', pady=5, padx=10)
        tk.Label(row3, text="Nombres*:", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        entries['nombres'] = tk.Entry(row3, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                     highlightthickness=1, highlightbackground=COLORS['border'])
        entries['nombres'].pack(side='left', fill='x', expand=True, ipady=5)

        # Fila 4: Apellidos
        row4 = tk.Frame(frame, bg='white')
        row4.pack(fill='x', pady=5, padx=10)
        tk.Label(row4, text="Apellidos*:", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        entries['apellidos'] = tk.Entry(row4, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                       highlightthickness=1, highlightbackground=COLORS['border'])
        entries['apellidos'].pack(side='left', fill='x', expand=True, ipady=5)

        # Fila 5: Fecha Nacimiento y Sexo
        row5 = tk.Frame(frame, bg='white')
        row5.pack(fill='x', pady=5, padx=10)
        tk.Label(row5, text="Fecha Nac:", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        entries['fecha_nac'] = tk.Entry(row5, font=('Segoe UI', 11), width=12, relief='flat', bg='#f8f9fa',
                                       highlightthickness=1, highlightbackground=COLORS['border'])
        entries['fecha_nac'].pack(side='left', ipady=5, padx=(0, 5))
        tk.Label(row5, text="(DD/MM/AAAA)", font=('Segoe UI', 8), bg='white', fg='gray').pack(side='left', padx=(0, 15))
        tk.Label(row5, text="Sexo:", font=('Segoe UI', 10), bg='white', width=6, anchor='w').pack(side='left')
        entries['sexo'] = ttk.Combobox(row5, font=('Segoe UI', 10), width=10, values=['M - Masculino', 'F - Femenino'])
        entries['sexo'].pack(side='left', ipady=3)

        # Fila 6: WhatsApp con código de país (obligatorio si no hay email)
        whatsapp_frame = tk.LabelFrame(frame, text=" WhatsApp (o Email) ", font=('Segoe UI', 10, 'bold'),
                                       bg='#e8f5e9', fg='#2e7d32', relief='solid', bd=1)
        whatsapp_frame.pack(fill='x', pady=(10, 5), padx=10)

        tel_inner = tk.Frame(whatsapp_frame, bg='#e8f5e9')
        tel_inner.pack(fill='x', padx=10, pady=8)

        tk.Label(tel_inner, text="Código País:", font=('Segoe UI', 10), bg='#e8f5e9').pack(anchor='w')
        entries['codigo_pais'] = ttk.Combobox(tel_inner, width=20, font=('Segoe UI', 10), state='readonly')
        entries['codigo_pais']['values'] = [
            '+58 Venezuela',
            '+57 Colombia',
            '+1 USA/Canada',
            '+52 México',
            '+34 España',
            '+593 Ecuador',
            '+51 Perú',
            '+54 Argentina',
            '+56 Chile',
            '+55 Brasil',
            '+507 Panamá'
        ]
        entries['codigo_pais'].set('+58 Venezuela')
        entries['codigo_pais'].pack(anchor='w', pady=(2, 8))

        tk.Label(tel_inner, text="Número (sin código de país):", font=('Segoe UI', 10), bg='#e8f5e9').pack(anchor='w')
        entries['telefono'] = tk.Entry(tel_inner, font=('Segoe UI', 11), width=20, relief='flat', bg='white',
                                      highlightthickness=2, highlightbackground='#4CAF50', highlightcolor='#4CAF50')
        entries['telefono'].pack(anchor='w', ipady=5, pady=(2, 5))
        tk.Label(tel_inner, text="Ej: 4141234567", font=('Segoe UI', 8), bg='#e8f5e9', fg='gray').pack(anchor='w')

        # Fila 7: Email
        row7 = tk.Frame(frame, bg='white')
        row7.pack(fill='x', pady=5, padx=10)
        tk.Label(row7, text="Email:", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        entries['email'] = tk.Entry(row7, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                   highlightthickness=1, highlightbackground=COLORS['border'])
        entries['email'].pack(side='left', fill='x', expand=True, ipady=5)

        # Fila 8: Dirección
        row8 = tk.Frame(frame, bg='white')
        row8.pack(fill='x', pady=5, padx=10)
        tk.Label(row8, text="Dirección:", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        entries['direccion'] = tk.Entry(row8, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                       highlightthickness=1, highlightbackground=COLORS['border'])
        entries['direccion'].pack(side='left', fill='x', expand=True, ipady=5)

        # Cargar datos si es edición
        if paciente_id:
            try:
                pac = db.query_one(f"SELECT * FROM Pacientes WHERE PacienteID={paciente_id}")
                if pac:
                    if pac.get('TipoDocumento'):
                        entries['tipo_doc'].set(pac.get('TipoDocumento'))
                    entries['num_doc'].insert(0, pac.get('NumeroDocumento') or '')
                    entries['nombres'].insert(0, pac.get('Nombres') or '')
                    entries['apellidos'].insert(0, pac.get('Apellidos') or '')
                    if pac.get('FechaNacimiento'):
                        entries['fecha_nac'].insert(0, pac['FechaNacimiento'].strftime('%d/%m/%Y'))
                    if pac.get('Sexo'):
                        s = pac.get('Sexo')
                        entries['sexo'].set('M - Masculino' if s == 'M' else 'F - Femenino')
                    entries['telefono'].insert(0, pac.get('Telefono1') or '')
                    entries['email'].insert(0, pac.get('Email') or '')
                    entries['direccion'].insert(0, pac.get('DireccionCompleta') or '')
            except:
                pass

        def guardar():
            # Validar campos requeridos
            if not entries['num_doc'].get().strip():
                messagebox.showerror("Error", "El N° de Documento es requerido")
                return
            if not entries['nombres'].get().strip():
                messagebox.showerror("Error", "Los nombres son requeridos")
                return
            if not entries['apellidos'].get().strip():
                messagebox.showerror("Error", "Los apellidos son requeridos")
                return

            # Validar que tenga al menos WhatsApp o Email
            tiene_whatsapp = entries['telefono'].get().strip()
            tiene_email = entries['email'].get().strip()
            if not tiene_whatsapp and not tiene_email:
                messagebox.showerror("Error", "Debe ingresar al menos un medio de contacto:\nWhatsApp o Email")
                return

            # Parsear fecha
            fecha_nac = None
            fecha_str = entries['fecha_nac'].get().strip()
            if fecha_str:
                try:
                    fecha_nac = datetime.strptime(fecha_str, '%d/%m/%Y')
                except:
                    messagebox.showerror("Error", "Formato de fecha inválido. Use DD/MM/AAAA")
                    return

            # Obtener sexo
            sexo_val = entries['sexo'].get()
            sexo = sexo_val[0] if sexo_val else None

            # Obtener teléfono con código de país (solo si hay número)
            telefono_completo = ''
            if tiene_whatsapp:
                codigo_pais = entries['codigo_pais'].get().split()[0]  # Obtiene solo el código (+58)
                telefono_completo = codigo_pais + tiene_whatsapp

            data = {
                'TipoDocumento': entries['tipo_doc'].get().strip(),
                'NumeroDocumento': entries['num_doc'].get().strip(),
                'Nombres': entries['nombres'].get().strip(),
                'Apellidos': entries['apellidos'].get().strip(),
                'FechaNacimiento': fecha_nac,
                'Sexo': sexo,
                'Telefono1': telefono_completo,
                'Email': tiene_email,
                'DireccionCompleta': entries['direccion'].get().strip(),
                'Activo': True,
            }

            try:
                if paciente_id:
                    db.update('Pacientes', data, f"PacienteID={paciente_id}")
                    messagebox.showinfo("Éxito", "Paciente actualizado correctamente")
                else:
                    data['FechaRegistro'] = datetime.now()
                    db.insert('Pacientes', data)
                    messagebox.showinfo("Éxito", "Paciente guardado correctamente")
                win.destroy()
                # Refrescar lista si existe
                try:
                    self.cargar_pacientes()
                except:
                    pass
            except Exception as e:
                messagebox.showerror("Error", f"Error al guardar: {e}")

        # Botones - SIEMPRE VISIBLES EN LA PARTE INFERIOR
        btn_frame = tk.Frame(win, bg='#f0f0f0')
        btn_frame.pack(fill='x', side='bottom')

        btn_inner = tk.Frame(btn_frame, bg='#f0f0f0')
        btn_inner.pack(pady=15)

        tk.Button(btn_inner, text="💾 GUARDAR", font=('Segoe UI', 12, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=30, pady=10,
                 cursor='hand2', command=guardar).pack(side='left', padx=10)
        tk.Button(btn_inner, text="❌ Cancelar", font=('Segoe UI', 11),
                 bg='#95a5a6', fg='white', relief='flat', padx=20, pady=10,
                 cursor='hand2', command=win.destroy).pack(side='left', padx=10)

        # Desactivar scroll cuando se cierra
        def on_close():
            canvas.unbind_all('<MouseWheel>')
            win.destroy()
        win.protocol('WM_DELETE_WINDOW', on_close)

    def editar_paciente(self, event):
        sel = self.tree_pac.selection()
        if sel:
            pac_id = self.tree_pac.item(sel[0])['values'][0]
            self.form_paciente(pac_id)

    # ============================================================
    # MÉDICOS
    # ============================================================

    def show_medicos(self):
        self.clear_content()
        self.set_title("🩺 Gestión de Médicos")

        # Configurar contenido scrollable
        scrollable = self.setup_scrollable_content()

        toolbar = tk.Frame(scrollable, bg=COLORS['bg'])
        toolbar.pack(fill='x', pady=(0, 15))

        tk.Button(toolbar, text="➕ Nuevo Médico", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.form_medico).pack(side='left', padx=(0, 10))

        tk.Button(toolbar, text="✏️ Editar", font=('Segoe UI', 10),
                 bg=COLORS['warning'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.editar_medico_seleccionado).pack(side='left', padx=(0, 10))

        tk.Button(toolbar, text="🗑️ Eliminar", font=('Segoe UI', 10),
                 bg=COLORS['danger'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.eliminar_medico).pack(side='left', padx=(0, 15))

        tk.Label(toolbar, text="🔍", font=('Segoe UI', 12), bg=COLORS['bg']).pack(side='left')
        self.search_med = tk.Entry(toolbar, font=('Segoe UI', 11), width=30, relief='flat',
                                   bg='white', highlightthickness=1, highlightbackground=COLORS['border'])
        self.search_med.pack(side='left', padx=5, ipady=6)
        self.search_med.bind('<Return>', lambda e: self.buscar_medicos())

        tk.Button(toolbar, text="Buscar", font=('Segoe UI', 10), bg=COLORS['success'],
                 fg='white', relief='flat', padx=15, cursor='hand2',
                 command=self.buscar_medicos).pack(side='left', padx=5)

        list_frame = tk.Frame(scrollable, bg='white')
        list_frame.pack(fill='both', expand=True)

        cols = ('ID', 'Código', 'Nombres', 'Apellidos', 'Especialidad', 'Teléfono')
        self.tree_med = ttk.Treeview(list_frame, columns=cols, show='headings')

        widths = [50, 80, 150, 150, 150, 100]
        for c, w in zip(cols, widths):
            self.tree_med.heading(c, text=c)
            self.tree_med.column(c, width=w)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_med.yview)
        self.tree_med.configure(yscrollcommand=vsb.set)

        self.tree_med.pack(side='left', fill='both', expand=True, padx=(10,0), pady=10)
        vsb.pack(side='right', fill='y', pady=10, padx=(0,10))

        self.tree_med.bind('<Double-1>', self.editar_medico)
        self.cargar_medicos()

    def cargar_medicos(self, filtro=""):
        for item in self.tree_med.get_children():
            self.tree_med.delete(item)

        where = ""
        if filtro:
            where = f"WHERE Nombres LIKE '%{filtro}%' OR Apellidos LIKE '%{filtro}%' OR CodigoMedico LIKE '%{filtro}%'"

        try:
            data = db.query(f"SELECT MedicoID, CodigoMedico, Nombres, Apellidos, Especialidad, Telefono1 FROM Medicos {where} ORDER BY MedicoID DESC")
            for r in data:
                self.tree_med.insert('', 'end', values=(
                    r['MedicoID'], r['CodigoMedico'] or '', r['Nombres'] or '',
                    r['Apellidos'] or '', r['Especialidad'] or '', r['Telefono1'] or ''
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buscar_medicos(self):
        self.cargar_medicos(self.search_med.get().strip())

    def form_medico(self, medico_id=None):
        win = tk.Toplevel(self.root)
        win.title("Editar Médico" if medico_id else "Nuevo Médico")
        win.grab_set()
        win.focus_set()
        win.configure(bg='white')

        # Hacer ventana responsiva
        hacer_ventana_responsiva(win, 500, 700, min_ancho=450, min_alto=600)

        header = tk.Frame(win, bg=COLORS['danger'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="🩺 " + ("Editar" if medico_id else "Nuevo") + " Médico",
                font=('Segoe UI', 14, 'bold'), bg=COLORS['danger'], fg='white').pack(pady=12)

        # Botones primero (pack side='bottom') para que siempre sean visibles
        btn_frame = tk.Frame(win, bg='white')
        btn_frame.pack(fill='x', side='bottom', padx=30, pady=15)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=30, pady=20)

        entries = {}
        fields = [
            ("Código*:", "codigo", None),
            ("Nombres*:", "nombres", None),
            ("Apellidos*:", "apellidos", None),
            ("Especialidad:", "especialidad", None),
        ]

        for label, key, _ in fields:
            tk.Label(frame, text=label, font=('Segoe UI', 10), bg='white', anchor='w').pack(fill='x', pady=(10, 2))
            entry = tk.Entry(frame, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                            highlightthickness=1, highlightbackground=COLORS['border'])
            entry.pack(fill='x', ipady=6)
            entries[key] = entry

        # Campo de teléfono WhatsApp con código de país (obligatorio si no hay email)
        whatsapp_frame = tk.LabelFrame(frame, text=" WhatsApp (o Email) ", font=('Segoe UI', 10, 'bold'),
                                       bg='#e8f5e9', fg='#2e7d32', relief='solid', bd=1)
        whatsapp_frame.pack(fill='x', pady=(15, 5))

        tel_inner = tk.Frame(whatsapp_frame, bg='#e8f5e9')
        tel_inner.pack(fill='x', padx=10, pady=8)

        tk.Label(tel_inner, text="Código País:", font=('Segoe UI', 10), bg='#e8f5e9').pack(anchor='w')
        entries['codigo_pais'] = ttk.Combobox(tel_inner, width=20, font=('Segoe UI', 10), state='readonly')
        entries['codigo_pais']['values'] = [
            '+58 Venezuela',
            '+57 Colombia',
            '+1 USA/Canada',
            '+52 México',
            '+34 España',
            '+593 Ecuador',
            '+51 Perú',
            '+54 Argentina',
            '+56 Chile',
            '+55 Brasil',
            '+507 Panamá'
        ]
        entries['codigo_pais'].set('+58 Venezuela')
        entries['codigo_pais'].pack(anchor='w', pady=(2, 8))

        tk.Label(tel_inner, text="Número (sin código de país):", font=('Segoe UI', 10), bg='#e8f5e9').pack(anchor='w')
        entries['telefono'] = tk.Entry(tel_inner, font=('Segoe UI', 11), width=20, relief='flat', bg='white',
                                      highlightthickness=2, highlightbackground='#4CAF50', highlightcolor='#4CAF50')
        entries['telefono'].pack(anchor='w', ipady=5, pady=(2, 5))
        tk.Label(tel_inner, text="Este número se usará para enviar resultados por WhatsApp",
                font=('Segoe UI', 8), bg='#e8f5e9', fg='#558b2f').pack(anchor='w')

        # Campo de email
        tk.Label(frame, text="Email:", font=('Segoe UI', 10), bg='white', anchor='w').pack(fill='x', pady=(10, 2))
        entries['email'] = tk.Entry(frame, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                        highlightthickness=1, highlightbackground=COLORS['border'])
        entries['email'].pack(fill='x', ipady=6)

        # Campo de comisión
        tk.Label(frame, text="Comisión (%):", font=('Segoe UI', 10), bg='white', anchor='w').pack(fill='x', pady=(10, 2))
        entries['comision'] = tk.Entry(frame, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                        highlightthickness=1, highlightbackground=COLORS['border'])
        entries['comision'].pack(fill='x', ipady=6)
        entries['comision'].insert(0, '0')
        tk.Label(frame, text="Porcentaje sobre el total de cada solicitud referida por este médico.",
                 font=('Segoe UI', 8), bg='white', fg='#666').pack(anchor='w')

        # Asegurar columna ComisionPorcentaje en Medicos
        try:
            db.execute("ALTER TABLE Medicos ADD COLUMN ComisionPorcentaje DOUBLE DEFAULT 0")
        except Exception:
            pass

        if medico_id:
            try:
                med = db.query_one(f"SELECT * FROM Medicos WHERE MedicoID={medico_id}")
                if med:
                    entries['codigo'].insert(0, med.get('CodigoMedico') or '')
                    entries['nombres'].insert(0, med.get('Nombres') or '')
                    entries['apellidos'].insert(0, med.get('Apellidos') or '')
                    entries['especialidad'].insert(0, med.get('Especialidad') or '')
                    entries['telefono'].insert(0, med.get('Telefono1') or '')
                    entries['email'].insert(0, med.get('Email') or '')
                    entries['comision'].delete(0, 'end')
                    entries['comision'].insert(0, str(med.get('ComisionPorcentaje') or 0))
            except Exception:
                pass

        def guardar():
            if not entries['codigo'].get().strip() or not entries['nombres'].get().strip():
                messagebox.showerror("Error", "Código y nombres son requeridos")
                return

            # Validar que tenga al menos WhatsApp o Email
            tiene_whatsapp = entries['telefono'].get().strip()
            tiene_email = entries['email'].get().strip()
            if not tiene_whatsapp and not tiene_email:
                messagebox.showerror("Error", "Debe ingresar al menos un medio de contacto:\nWhatsApp o Email")
                return

            # Obtener teléfono con código de país (solo si hay número)
            telefono_completo = ''
            if tiene_whatsapp:
                codigo_pais = entries['codigo_pais'].get().split()[0]  # Obtiene solo el código (+58)
                telefono_completo = codigo_pais + tiene_whatsapp

            try:
                _comision = float(entries['comision'].get().strip().replace(',', '.'))
            except Exception:
                _comision = 0.0
            data = {
                'CodigoMedico': entries['codigo'].get().strip(),
                'Nombres': entries['nombres'].get().strip(),
                'Apellidos': entries['apellidos'].get().strip(),
                'Especialidad': entries['especialidad'].get().strip(),
                'Telefono1': telefono_completo,
                'Email': tiene_email,
                'Activo': True,
                'ComisionPorcentaje': _comision,
            }

            try:
                if medico_id:
                    db.update('Medicos', data, f"MedicoID={medico_id}")
                    messagebox.showinfo("Éxito", "Médico actualizado")
                else:
                    data['FechaRegistro'] = datetime.now()
                    db.insert('Medicos', data)
                    messagebox.showinfo("Éxito", "Médico guardado")
                win.destroy()
                self.cargar_medicos()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                 bg='#95a5a6', fg='white', relief='flat', padx=20, pady=8,
                 cursor='hand2', command=win.destroy).pack(side='right', padx=5)
        tk.Button(btn_frame, text="💾 Guardar", font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                 cursor='hand2', command=guardar).pack(side='right', padx=5)

    def editar_medico(self, event):
        sel = self.tree_med.selection()
        if sel:
            self.form_medico(self.tree_med.item(sel[0])['values'][0])

    def editar_medico_seleccionado(self):
        """Edita el médico seleccionado en la lista"""
        sel = self.tree_med.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un médico de la lista para editar")
            return
        medico_id = self.tree_med.item(sel[0])['values'][0]
        self.form_medico(medico_id)

    def eliminar_medico(self):
        """Elimina el médico seleccionado de la base de datos"""
        sel = self.tree_med.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un médico de la lista para eliminar")
            return

        medico_id = self.tree_med.item(sel[0])['values'][0]
        valores = self.tree_med.item(sel[0])['values']
        nombre_medico = f"{valores[2]} {valores[3]}"  # Nombres + Apellidos

        # Verificar si el médico tiene solicitudes asociadas
        try:
            solicitudes = db.query_one(f"SELECT COUNT(*) as Total FROM Solicitudes WHERE MedicoID = {medico_id}")
            total_solicitudes = solicitudes.get('Total', 0) if solicitudes else 0

            if total_solicitudes > 0:
                respuesta = messagebox.askyesno("Confirmar",
                    f"El médico {nombre_medico} tiene {total_solicitudes} solicitud(es) asociada(s).\n\n"
                    "¿Desea desactivarlo en lugar de eliminarlo?\n\n"
                    "(Esto mantendrá el historial pero el médico no aparecerá en nuevas solicitudes)")

                if respuesta:
                    # Desactivar en lugar de eliminar
                    db.update('Medicos', {'Activo': False}, f"MedicoID={medico_id}")
                    messagebox.showinfo("Éxito", f"El médico {nombre_medico} ha sido desactivado")
                    self.cargar_medicos()
                return

            # Si no tiene solicitudes, confirmar eliminación
            respuesta = messagebox.askyesno("Confirmar Eliminación",
                f"¿Está seguro de eliminar al médico?\n\n"
                f"Nombre: {nombre_medico}\n"
                f"Código: {valores[1]}\n"
                f"Especialidad: {valores[4]}\n\n"
                "Esta acción no se puede deshacer.")

            if respuesta:
                db.execute(f"DELETE FROM Medicos WHERE MedicoID = {medico_id}")
                messagebox.showinfo("Éxito", f"El médico {nombre_medico} ha sido eliminado")
                self.cargar_medicos()

        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar médico:\n{str(e)}")

    # ── Cotizaciones ─────────────────────────────────────────────────────────

    def show_cotizaciones(self):
        """Vista de listado y gestión de cotizaciones."""
        if not self.gestor_cotizaciones:
            messagebox.showerror("Error", "Módulo de cotizaciones no disponible.")
            return
        self.clear_content()
        self.set_title("📋 Cotizaciones")

        scrollable, _ = self._crear_frame_scrollable(self.content_frame)

        # Toolbar
        toolbar = tk.Frame(scrollable, bg=COLORS['bg'])
        toolbar.pack(fill='x', padx=20, pady=(15, 5))

        tk.Button(toolbar, text="➕ Nueva Cotización", font=('Segoe UI', 10, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=8,
                  cursor='hand2', command=self.form_cotizacion).pack(side='left', padx=(0, 10))

        tk.Label(toolbar, text="🔍", font=('Segoe UI', 12), bg=COLORS['bg']).pack(side='left')
        self._cot_search = tk.Entry(toolbar, font=('Segoe UI', 10), width=22,
                                    relief='flat', bg='white',
                                    highlightthickness=1, highlightbackground=COLORS['border'])
        self._cot_search.pack(side='left', padx=5, ipady=6)

        estado_var = tk.StringVar(value='Todos')
        ttk.Combobox(toolbar, textvariable=estado_var, width=12,
                     values=['Todos', 'Pendiente', 'Convertida', 'Anulada'],
                     state='readonly', font=('Segoe UI', 10)).pack(side='left', padx=5)

        tk.Button(toolbar, text="Buscar", font=('Segoe UI', 10),
                  bg=COLORS['success'], fg='white', relief='flat', padx=12,
                  command=lambda: self._cargar_cotizaciones(estado_var.get())).pack(side='left', padx=5)

        # Treeview
        cols = ('ID', 'N° Cotización', 'Paciente', 'Cédula', 'Fecha', 'Vence', 'Total', 'Estado')
        tree_f = tk.Frame(scrollable, bg='white')
        tree_f.pack(fill='both', expand=True, padx=20, pady=10)

        self._tree_cot = ttk.Treeview(tree_f, columns=cols, show='headings', height=18)
        widths = {'ID': 40, 'N° Cotización': 130, 'Paciente': 190, 'Cédula': 100,
                  'Fecha': 90, 'Vence': 90, 'Total': 100, 'Estado': 90}
        for c in cols:
            self._tree_cot.heading(c, text=c)
            self._tree_cot.column(c, width=widths.get(c, 100), anchor='center')
        self._tree_cot.column('Paciente', anchor='w')

        vsb = ttk.Scrollbar(tree_f, orient='vertical', command=self._tree_cot.yview)
        self._tree_cot.configure(yscrollcommand=vsb.set)
        self._tree_cot.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # Botones de acción
        acc_f = tk.Frame(scrollable, bg=COLORS['bg'])
        acc_f.pack(fill='x', padx=20, pady=(0, 15))

        tk.Button(acc_f, text="📄 Ver / PDF", font=('Segoe UI', 9),
                  bg='#1565c0', fg='white', relief='flat', padx=12,
                  command=self._ver_cotizacion_pdf).pack(side='left', padx=(0, 8))
        tk.Button(acc_f, text="✅ Convertir a Solicitud", font=('Segoe UI', 9),
                  bg=COLORS['success'], fg='white', relief='flat', padx=12,
                  command=self._convertir_cotizacion).pack(side='left', padx=(0, 8))
        tk.Button(acc_f, text="🚫 Anular", font=('Segoe UI', 9),
                  bg=COLORS['danger'], fg='white', relief='flat', padx=12,
                  command=self._anular_cotizacion).pack(side='left')

        self._cot_estado_var = estado_var
        self._cargar_cotizaciones('Todos')

    def _cargar_cotizaciones(self, estado='Todos'):
        if not hasattr(self, '_tree_cot'):
            return
        for item in self._tree_cot.get_children():
            self._tree_cot.delete(item)
        filtro = self._cot_search.get().strip() if hasattr(self, '_cot_search') else ''
        rows = self.gestor_cotizaciones.listar_cotizaciones(filtro, estado)
        simbolo = (self.config_lab or {}).get('SimboloMoneda', '$')
        for r in rows:
            fecha = r.get('FechaCotizacion')
            vence = r.get('FechaVencimiento')
            fecha_s = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') else str(fecha or '')[:10]
            vence_s = vence.strftime('%d/%m/%Y') if hasattr(vence, 'strftime') else str(vence or '')[:10]
            total   = float(r.get('Total') or 0)
            estado_r = r.get('Estado', '')
            tag = {'Convertida': 'verde', 'Anulada': 'rojo', 'Pendiente': ''}.get(estado_r, '')
            self._tree_cot.insert('', 'end', tags=(tag,), values=(
                r.get('CotizacionID'), r.get('NumeroCotizacion', ''),
                r.get('Paciente', ''), r.get('Cedula', '') or '',
                fecha_s, vence_s, f"{simbolo} {total:,.2f}", estado_r
            ))
        self._tree_cot.tag_configure('verde', foreground='#2e7d32')
        self._tree_cot.tag_configure('rojo',  foreground='#c62828')

    def _cot_seleccionada(self):
        sel = self._tree_cot.selection() if hasattr(self, '_tree_cot') else []
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione una cotización")
            return None
        return self._tree_cot.item(sel[0])['values'][0]

    def _ver_cotizacion_pdf(self):
        cid = self._cot_seleccionada()
        if not cid:
            return
        try:
            ruta = self.gestor_cotizaciones.generar_pdf(cid, self.config_lab)
            if ruta:
                os.startfile(ruta)
            else:
                messagebox.showerror("Error", "No se pudo generar el PDF (ReportLab no disponible).")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _convertir_cotizacion(self):
        cid = self._cot_seleccionada()
        if not cid:
            return
        if not messagebox.askyesno("Confirmar",
                                   "¿Convertir esta cotización en una solicitud?\n"
                                   "Se creará la solicitud con los mismos ítems."):
            return
        r = self.gestor_cotizaciones.convertir_a_solicitud(cid)
        if r['exito']:
            messagebox.showinfo("Éxito",
                                f"Solicitud creada: {r['numero_solicitud']}\n"
                                "La cotización quedó marcada como 'Convertida'.")
            self._cargar_cotizaciones(getattr(self, '_cot_estado_var', tk.StringVar()).get())
        else:
            messagebox.showerror("Error", r['mensaje'])

    def _anular_cotizacion(self):
        cid = self._cot_seleccionada()
        if not cid:
            return
        if messagebox.askyesno("Confirmar", "¿Anular esta cotización?"):
            self.gestor_cotizaciones.anular_cotizacion(cid)
            self._cargar_cotizaciones(getattr(self, '_cot_estado_var', tk.StringVar()).get())

    def form_cotizacion(self):
        """Formulario para crear una nueva cotización."""
        if not self.gestor_cotizaciones:
            messagebox.showerror("Error", "Módulo de cotizaciones no disponible.")
            return

        win = tk.Toplevel(self.root)
        win.title("Nueva Cotización")
        win.grab_set()
        win.configure(bg='white')
        hacer_ventana_responsiva(win, 720, 700, min_ancho=640, min_alto=580)

        tk.Frame(win, bg='#1565c0', height=50).pack(fill='x')
        tk.Label(win, text="📋 Nueva Cotización / Presupuesto",
                 font=('Segoe UI', 13, 'bold'), bg='#1565c0', fg='white').place(x=0, y=10, relwidth=1)

        # ── Botones al fondo ──────────────────────────────────────────────────
        btn_frame = tk.Frame(win, bg='white')
        btn_frame.pack(fill='x', side='bottom', padx=20, pady=12)

        main_f = tk.Frame(win, bg='white')
        main_f.pack(fill='both', expand=True, padx=20, pady=(60, 0))

        # ── Paciente ──────────────────────────────────────────────────────────
        pac_lf = tk.LabelFrame(main_f, text=" Paciente ", bg='white',
                               font=('Segoe UI', 9, 'bold'))
        pac_lf.pack(fill='x', pady=(0, 8))

        pac_row = tk.Frame(pac_lf, bg='white')
        pac_row.pack(fill='x', padx=10, pady=6)

        tk.Label(pac_row, text="Buscar:", font=('Segoe UI', 9), bg='white').pack(side='left')
        pac_search = tk.Entry(pac_row, font=('Segoe UI', 10), width=28,
                              relief='flat', bg='#f8f9fa',
                              highlightthickness=1, highlightbackground='#bbb')
        pac_search.pack(side='left', padx=5, ipady=4)

        pac_var      = tk.StringVar(value='')  # almacena "ID|Nombre"
        pac_id_var   = tk.IntVar(value=0)
        lbl_pac_sel  = tk.Label(pac_lf, text="Ningún paciente seleccionado",
                                font=('Segoe UI', 9, 'italic'), bg='white', fg='#666')
        lbl_pac_sel.pack(anchor='w', padx=10, pady=(0, 6))

        def buscar_pac(event=None):
            q = pac_search.get().strip()
            if not q:
                return
            rows = db.query(
                f"SELECT PacienteID, NombreCompleto, Cedula FROM Pacientes "
                f"WHERE NombreCompleto LIKE '%{q}%' OR Cedula LIKE '%{q}%' "
                f"ORDER BY NombreCompleto"
            ) or []
            if not rows:
                messagebox.showinfo("Sin resultados", "No se encontraron pacientes.", parent=win)
                return
            if len(rows) == 1:
                r = rows[0]
                pac_id_var.set(r['PacienteID'])
                lbl_pac_sel.config(text=f"✅ {r['NombreCompleto']} | C.I. {r.get('Cedula','')}", fg='#2e7d32')
                return
            # múltiples → mini-listado
            sel_win = tk.Toplevel(win)
            sel_win.title("Seleccionar paciente")
            sel_win.grab_set()
            lst = tk.Listbox(sel_win, font=('Segoe UI', 10), width=50, height=min(len(rows), 10))
            lst.pack(padx=10, pady=10)
            for r in rows:
                lst.insert('end', f"{r['NombreCompleto']} | {r.get('Cedula','')}")
            def elegir(event=None):
                idx = lst.curselection()
                if idx:
                    r = rows[idx[0]]
                    pac_id_var.set(r['PacienteID'])
                    lbl_pac_sel.config(text=f"✅ {r['NombreCompleto']} | C.I. {r.get('Cedula','')}", fg='#2e7d32')
                sel_win.destroy()
            lst.bind('<Double-1>', elegir)
            tk.Button(sel_win, text="Seleccionar", command=elegir).pack(pady=(0, 8))

        pac_search.bind('<Return>', buscar_pac)
        tk.Button(pac_row, text="🔍", font=('Segoe UI', 9),
                  bg=COLORS['primary'], fg='white', relief='flat',
                  command=buscar_pac).pack(side='left')

        # ── Pruebas ───────────────────────────────────────────────────────────
        pru_lf = tk.LabelFrame(main_f, text=" Pruebas / Servicios ", bg='white',
                               font=('Segoe UI', 9, 'bold'))
        pru_lf.pack(fill='both', expand=True, pady=(0, 8))

        pru_row = tk.Frame(pru_lf, bg='white')
        pru_row.pack(fill='x', padx=10, pady=6)

        tk.Label(pru_row, text="Buscar prueba:", font=('Segoe UI', 9), bg='white').pack(side='left')
        pru_search = tk.Entry(pru_row, font=('Segoe UI', 10), width=30,
                              relief='flat', bg='#f8f9fa',
                              highlightthickness=1, highlightbackground='#bbb')
        pru_search.pack(side='left', padx=5, ipady=4)

        pruebas_sel = []  # lista de dicts {id, nombre, precio}
        simbolo     = (self.config_lab or {}).get('SimboloMoneda', '$')

        cols_p = ('Prueba', 'Precio')
        tree_p = ttk.Treeview(pru_lf, columns=cols_p, show='headings', height=8)
        tree_p.heading('Prueba', text='Prueba')
        tree_p.heading('Precio', text='Precio')
        tree_p.column('Prueba', width=380)
        tree_p.column('Precio', width=120, anchor='e')
        tree_p.pack(fill='both', expand=True, padx=10, pady=(0, 4))

        lbl_subtotal = tk.Label(pru_lf, text="Sub-Total: —",
                                font=('Segoe UI', 10, 'bold'), bg='white', fg='#1565c0')
        lbl_subtotal.pack(anchor='e', padx=10, pady=(0, 6))

        def actualizar_subtotal():
            st = sum(p['precio'] for p in pruebas_sel)
            lbl_subtotal.config(text=f"Sub-Total: {simbolo} {st:,.2f}")

        def agregar_prueba(event=None):
            q = pru_search.get().strip()
            if not q:
                return
            rows = db.query(
                f"SELECT PruebaID, NombrePrueba, Precio FROM Pruebas "
                f"WHERE (NombrePrueba LIKE '%{q}%' OR CodigoPrueba LIKE '%{q}%') "
                f"AND Activo=True ORDER BY NombrePrueba"
            ) or []
            if not rows:
                messagebox.showinfo("Sin resultados", "No se encontraron pruebas.", parent=win)
                return
            if len(rows) == 1:
                r = rows[0]
                precio = float(r.get('Precio') or 0)
                pruebas_sel.append({'id': r['PruebaID'], 'nombre': r['NombrePrueba'], 'precio': precio})
                tree_p.insert('', 'end', values=(r['NombrePrueba'], f"{simbolo} {precio:,.2f}"))
                actualizar_subtotal()
                pru_search.delete(0, 'end')
                return
            # múltiples
            sel_win = tk.Toplevel(win)
            sel_win.title("Seleccionar prueba")
            sel_win.grab_set()
            lst = tk.Listbox(sel_win, font=('Segoe UI', 10), width=55, height=min(len(rows), 12))
            lst.pack(padx=10, pady=10)
            for r in rows:
                lst.insert('end', f"{r['NombrePrueba']} — {simbolo} {float(r.get('Precio') or 0):,.2f}")
            def elegir(event=None):
                idx = lst.curselection()
                if idx:
                    r = rows[idx[0]]
                    precio = float(r.get('Precio') or 0)
                    pruebas_sel.append({'id': r['PruebaID'], 'nombre': r['NombrePrueba'], 'precio': precio})
                    tree_p.insert('', 'end', values=(r['NombrePrueba'], f"{simbolo} {precio:,.2f}"))
                    actualizar_subtotal()
                    pru_search.delete(0, 'end')
                sel_win.destroy()
            lst.bind('<Double-1>', elegir)
            tk.Button(sel_win, text="Agregar", command=elegir).pack(pady=(0, 8))

        pru_search.bind('<Return>', agregar_prueba)
        tk.Button(pru_row, text="➕ Agregar", font=('Segoe UI', 9),
                  bg=COLORS['primary'], fg='white', relief='flat',
                  command=agregar_prueba).pack(side='left', padx=4)

        def quitar_prueba():
            sel = tree_p.selection()
            if not sel:
                return
            idx = tree_p.index(sel[0])
            if 0 <= idx < len(pruebas_sel):
                pruebas_sel.pop(idx)
            tree_p.delete(sel[0])
            actualizar_subtotal()

        tk.Button(pru_row, text="🗑️ Quitar", font=('Segoe UI', 9),
                  bg=COLORS['danger'], fg='white', relief='flat',
                  command=quitar_prueba).pack(side='left', padx=4)

        # ── Extra ─────────────────────────────────────────────────────────────
        extra_f = tk.Frame(main_f, bg='white')
        extra_f.pack(fill='x', pady=(0, 8))

        tk.Label(extra_f, text="Descuento:", font=('Segoe UI', 9, 'bold'), bg='white').grid(row=0, column=0, sticky='w')
        desc_e = tk.Entry(extra_f, font=('Segoe UI', 10), width=14, relief='flat', bg='#f8f9fa',
                          highlightthickness=1, highlightbackground='#bbb')
        desc_e.insert(0, '0')
        desc_e.grid(row=0, column=1, padx=(4, 20), ipady=4)

        tk.Label(extra_f, text="Días vigencia:", font=('Segoe UI', 9, 'bold'), bg='white').grid(row=0, column=2, sticky='w')
        dias_e = tk.Entry(extra_f, font=('Segoe UI', 10), width=8, relief='flat', bg='#f8f9fa',
                          highlightthickness=1, highlightbackground='#bbb')
        dias_e.insert(0, '15')
        dias_e.grid(row=0, column=3, padx=4, ipady=4)

        tk.Label(extra_f, text="Observaciones:", font=('Segoe UI', 9, 'bold'), bg='white').grid(row=1, column=0, sticky='w', pady=(8,0))
        obs_e = tk.Entry(extra_f, font=('Segoe UI', 10), width=60, relief='flat', bg='#f8f9fa',
                         highlightthickness=1, highlightbackground='#bbb')
        obs_e.grid(row=1, column=1, columnspan=3, padx=4, ipady=4, pady=(8,0), sticky='ew')

        # ── Guardar ───────────────────────────────────────────────────────────
        def guardar():
            if not pac_id_var.get():
                messagebox.showerror("Error", "Seleccione un paciente.", parent=win)
                return
            if not pruebas_sel:
                messagebox.showerror("Error", "Agregue al menos una prueba.", parent=win)
                return
            try:
                desc = float(desc_e.get().strip().replace(',', '.') or '0')
            except Exception:
                desc = 0.0
            try:
                dias = int(dias_e.get().strip() or '15')
            except Exception:
                dias = 15
            r = self.gestor_cotizaciones.crear_cotizacion(
                paciente_id=pac_id_var.get(),
                pruebas=pruebas_sel,
                descuento=desc,
                observaciones=obs_e.get().strip(),
                dias_vigencia=dias,
            )
            if r['exito']:
                if messagebox.askyesno("Éxito",
                                       f"Cotización {r['numero']} creada.\n"
                                       f"Total: {simbolo} {r['total']:,.2f}\n\n"
                                       "¿Generar PDF ahora?", parent=win):
                    try:
                        ruta = self.gestor_cotizaciones.generar_pdf(r['cotizacion_id'], self.config_lab)
                        if ruta:
                            os.startfile(ruta)
                    except Exception as ep:
                        messagebox.showwarning("PDF", str(ep), parent=win)
                win.destroy()
                if hasattr(self, '_tree_cot'):
                    self._cargar_cotizaciones('Todos')
            else:
                messagebox.showerror("Error", r['mensaje'], parent=win)

        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                  bg='#95a5a6', fg='white', relief='flat', padx=18, pady=8,
                  command=win.destroy).pack(side='right', padx=5)
        tk.Button(btn_frame, text="💾 Guardar Cotización", font=('Segoe UI', 11, 'bold'),
                  bg='#1565c0', fg='white', relief='flat', padx=18, pady=8,
                  command=guardar).pack(side='right')

    # ── Reporte de Comisiones por Médico ─────────────────────────────────────

    def show_comisiones_medico(self):
        """Vista de reporte de comisiones por médico con filtro de período."""
        self.clear_content()
        self.set_title("💰 Comisiones por Médico")

        scrollable, _ = self._crear_frame_scrollable(self.content_frame)

        # ── Filtro de fechas ──────────────────────────────────────────────────
        filtro_f = tk.Frame(scrollable, bg=COLORS['bg'])
        filtro_f.pack(fill='x', padx=20, pady=(15, 5))

        tk.Label(filtro_f, text="Desde:", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['bg'], fg='white').pack(side='left')
        desde_e = tk.Entry(filtro_f, font=('Segoe UI', 10), width=12,
                           relief='flat', bg='white', highlightthickness=1, highlightbackground='#bbb')
        desde_e.pack(side='left', padx=(4, 12), ipady=4)
        desde_e.insert(0, datetime.now().replace(day=1).strftime('%d/%m/%Y'))

        tk.Label(filtro_f, text="Hasta:", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['bg'], fg='white').pack(side='left')
        hasta_e = tk.Entry(filtro_f, font=('Segoe UI', 10), width=12,
                           relief='flat', bg='white', highlightthickness=1, highlightbackground='#bbb')
        hasta_e.pack(side='left', padx=(4, 20), ipady=4)
        hasta_e.insert(0, datetime.now().strftime('%d/%m/%Y'))

        # ── Tabla de resultados ───────────────────────────────────────────────
        table_f = tk.Frame(scrollable, bg='white')
        table_f.pack(fill='both', expand=True, padx=20, pady=10)

        cols = ('Médico', 'Especialidad', '% Comisión', 'N° Solicitudes', 'Total Facturado', 'Comisión Calculada')
        tree = ttk.Treeview(table_f, columns=cols, show='headings', height=20)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=145, anchor='center')
        tree.column('Médico', width=200, anchor='w')
        vsb = ttk.Scrollbar(table_f, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # Totales al pie
        tot_f = tk.Frame(scrollable, bg='#e8f5e9')
        tot_f.pack(fill='x', padx=20, pady=(0, 15))
        lbl_total_fact = tk.Label(tot_f, text="Total facturado: —",
                                  font=('Segoe UI', 11, 'bold'), bg='#e8f5e9')
        lbl_total_fact.pack(side='left', padx=15, pady=8)
        lbl_total_com  = tk.Label(tot_f, text="Total comisiones: —",
                                  font=('Segoe UI', 11, 'bold'), bg='#e8f5e9', fg='#2e7d32')
        lbl_total_com.pack(side='left', padx=15)

        simbolo = (self.config_lab or {}).get('SimboloMoneda', '$')

        def cargar(event=None):
            for item in tree.get_children():
                tree.delete(item)
            try:
                d_str = desde_e.get().strip()
                h_str = hasta_e.get().strip()
                desde_dt = datetime.strptime(d_str, '%d/%m/%Y')
                hasta_dt = datetime.strptime(h_str, '%d/%m/%Y')
                desde_acc = desde_dt.strftime('#%m/%d/%Y#')
                hasta_acc = hasta_dt.strftime('#%m/%d/%Y 23:59:59#')
            except Exception:
                messagebox.showerror("Error", "Formato de fecha inválido. Use DD/MM/AAAA")
                return

            sql = f"""
                SELECT m.MedicoID,
                       m.Nombres & ' ' & m.Apellidos AS NombreMedico,
                       m.Especialidad,
                       Nz(m.ComisionPorcentaje, 0) AS Comision,
                       COUNT(s.SolicitudID) AS NumSolicitudes,
                       Nz(SUM(s.MontoTotal), 0) AS TotalFacturado
                  FROM Medicos m
                  LEFT JOIN Solicitudes s ON s.MedicoID = m.MedicoID
                   AND s.FechaSolicitud BETWEEN {desde_acc} AND {hasta_acc}
                 WHERE m.Activo = True
                 GROUP BY m.MedicoID, m.Nombres, m.Apellidos, m.Especialidad, m.ComisionPorcentaje
                 ORDER BY TotalFacturado DESC
            """
            try:
                rows = db.query(sql) or []
                total_fact = 0.0
                total_com  = 0.0
                for r in rows:
                    tf   = float(r.get('TotalFacturado') or 0)
                    pct  = float(r.get('Comision') or 0)
                    com  = tf * pct / 100
                    nsol = int(r.get('NumSolicitudes') or 0)
                    total_fact += tf
                    total_com  += com
                    tree.insert('', 'end', values=(
                        r.get('NombreMedico', ''),
                        r.get('Especialidad', '') or '',
                        f"{pct:.1f} %",
                        nsol,
                        f"{simbolo} {tf:,.2f}",
                        f"{simbolo} {com:,.2f}",
                    ))
                lbl_total_fact.config(text=f"Total facturado: {simbolo} {total_fact:,.2f}")
                lbl_total_com.config(text=f"Total comisiones: {simbolo} {total_com:,.2f}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(filtro_f, text="🔍 Consultar", font=('Segoe UI', 10, 'bold'),
                  bg=COLORS['success'], fg='white', relief='flat', padx=15, pady=5,
                  command=cargar).pack(side='left')

        cargar()

    # ============================================================
    # PRUEBAS
    # ============================================================

    def show_pruebas(self):
        if not self.es_admin():
            messagebox.showwarning("Acceso Denegado", "Esta función requiere nivel Administrador")
            return
        self.clear_content()
        self.set_title("🧪 Catálogo de Pruebas")

        # Configurar contenido scrollable
        scrollable = self.setup_scrollable_content()

        toolbar = tk.Frame(scrollable, bg=COLORS['bg'])
        toolbar.pack(fill='x', pady=(0, 15))

        tk.Button(toolbar, text="➕ Nueva Prueba", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['warning'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.form_prueba).pack(side='left', padx=(0, 10))

        tk.Button(toolbar, text="✏️ Editar", font=('Segoe UI', 10),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=lambda: self.editar_prueba(None)).pack(side='left', padx=(0, 10))

        tk.Button(toolbar, text="🗑️ Eliminar", font=('Segoe UI', 10),
                 bg=COLORS['danger'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.eliminar_prueba).pack(side='left', padx=(0, 15))

        tk.Label(toolbar, text="🔍", font=('Segoe UI', 12), bg=COLORS['bg']).pack(side='left')
        self.search_pru = tk.Entry(toolbar, font=('Segoe UI', 11), width=30, relief='flat',
                                   bg='white', highlightthickness=1, highlightbackground=COLORS['border'])
        self.search_pru.pack(side='left', padx=5, ipady=6)
        self.search_pru.bind('<Return>', lambda e: self.buscar_pruebas())

        tk.Button(toolbar, text="Buscar", font=('Segoe UI', 10), bg=COLORS['success'],
                 fg='white', relief='flat', padx=15, cursor='hand2',
                 command=self.buscar_pruebas).pack(side='left', padx=5)

        list_frame = tk.Frame(scrollable, bg='white')
        list_frame.pack(fill='both', expand=True)

        cols = ('ID', 'Código', 'Nombre', 'Área', 'Activo')
        self.tree_pru = ttk.Treeview(list_frame, columns=cols, show='headings', selectmode='extended')

        widths = [50, 100, 350, 150, 70]
        for c, w in zip(cols, widths):
            self.tree_pru.heading(c, text=c)
            self.tree_pru.column(c, width=w)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_pru.yview)
        self.tree_pru.configure(yscrollcommand=vsb.set)

        self.tree_pru.pack(side='left', fill='both', expand=True, padx=(10,0), pady=10)
        vsb.pack(side='right', fill='y', pady=10, padx=(0,10))

        self.tree_pru.bind('<Double-1>', self.editar_prueba)
        self.cargar_pruebas()

    def cargar_pruebas(self, filtro=""):
        for item in self.tree_pru.get_children():
            self.tree_pru.delete(item)

        where = ""
        if filtro:
            where = f"WHERE p.NombrePrueba LIKE '%{filtro}%' OR p.CodigoPrueba LIKE '%{filtro}%'"

        try:
            data = db.query(f"""
                SELECT p.PruebaID, p.CodigoPrueba, p.NombrePrueba, a.NombreArea, p.Activo
                FROM Pruebas p LEFT JOIN Areas a ON p.AreaID = a.AreaID
                {where} ORDER BY p.NombrePrueba
            """)
            for r in data:
                self.tree_pru.insert('', 'end', values=(
                    r['PruebaID'], r['CodigoPrueba'] or '', r['NombrePrueba'] or '',
                    r['NombreArea'] or '', 'Sí' if r['Activo'] else 'No'
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buscar_pruebas(self):
        self.cargar_pruebas(self.search_pru.get().strip())

    def form_prueba(self, prueba_id=None):
        win = tk.Toplevel(self.root)
        win.title("Editar Prueba" if prueba_id else "Nueva Prueba")
        win.grab_set()
        win.focus_set()
        win.configure(bg='white')

        # Hacer ventana responsiva
        hacer_ventana_responsiva(win, 500, 400, min_ancho=450, min_alto=350)

        header = tk.Frame(win, bg=COLORS['warning'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="🧪 " + ("Editar" if prueba_id else "Nueva") + " Prueba",
                font=('Segoe UI', 14, 'bold'), bg=COLORS['warning'], fg='white').pack(pady=12)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=30, pady=20)

        tk.Label(frame, text="Código*:", font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=(0, 2))
        entry_codigo = tk.Entry(frame, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                               highlightthickness=1, highlightbackground=COLORS['border'])
        entry_codigo.pack(fill='x', ipady=6)

        tk.Label(frame, text="Nombre*:", font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=(15, 2))
        entry_nombre = tk.Entry(frame, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                               highlightthickness=1, highlightbackground=COLORS['border'])
        entry_nombre.pack(fill='x', ipady=6)

        tk.Label(frame, text="Área:", font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=(15, 2))
        combo_area = ttk.Combobox(frame, font=('Segoe UI', 11), state='readonly')
        combo_area.pack(fill='x', ipady=4)

        # Cargar áreas
        areas = db.query("SELECT AreaID, NombreArea FROM Areas ORDER BY NombreArea")
        area_map = {a['NombreArea']: a['AreaID'] for a in areas}
        combo_area['values'] = list(area_map.keys())

        var_activo = tk.BooleanVar(value=True)
        tk.Checkbutton(frame, text="Activo", variable=var_activo, font=('Segoe UI', 10),
                      bg='white').pack(anchor='w', pady=(15, 0))

        if prueba_id:
            try:
                pru = db.query_one(f"SELECT p.*, a.NombreArea FROM Pruebas p LEFT JOIN Areas a ON p.AreaID=a.AreaID WHERE PruebaID={prueba_id}")
                if pru:
                    entry_codigo.insert(0, pru.get('CodigoPrueba') or '')
                    entry_nombre.insert(0, pru.get('NombrePrueba') or '')
                    if pru.get('NombreArea'):
                        combo_area.set(pru['NombreArea'])
                    var_activo.set(bool(pru.get('Activo')))
            except:
                pass

        def guardar():
            if not entry_codigo.get().strip() or not entry_nombre.get().strip():
                messagebox.showerror("Error", "Código y nombre son requeridos")
                return

            area_id = area_map.get(combo_area.get())

            data = {
                'CodigoPrueba': entry_codigo.get().strip(),
                'NombrePrueba': entry_nombre.get().strip(),
                'AreaID': area_id,
                'Activo': var_activo.get(),
            }

            try:
                if prueba_id:
                    db.update('Pruebas', data, f"PruebaID={prueba_id}")
                    messagebox.showinfo("Éxito", "Prueba actualizada")
                else:
                    db.insert('Pruebas', data)
                    messagebox.showinfo("Éxito", "Prueba guardada")
                win.destroy()
                self.cargar_pruebas()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        btn_frame = tk.Frame(win, bg='white')
        btn_frame.pack(fill='x', padx=30, pady=20)

        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                 bg='#95a5a6', fg='white', relief='flat', padx=20, pady=8,
                 cursor='hand2', command=win.destroy).pack(side='right', padx=5)
        tk.Button(btn_frame, text="💾 Guardar", font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                 cursor='hand2', command=guardar).pack(side='right', padx=5)

    def editar_prueba(self, event):
        sel = self.tree_pru.selection()
        if sel:
            self.form_prueba(self.tree_pru.item(sel[0])['values'][0])

    def eliminar_prueba(self):
        """Elimina una o varias pruebas del catálogo"""
        sel = self.tree_pru.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione una o más pruebas para eliminar")
            return

        # Recopilar info de las pruebas seleccionadas
        pruebas_a_eliminar = []
        for item in sel:
            vals = self.tree_pru.item(item)['values']
            pruebas_a_eliminar.append({
                'id': vals[0],
                'codigo': vals[1],
                'nombre': vals[2]
            })

        # Confirmar eliminación
        if len(pruebas_a_eliminar) == 1:
            msg = f"¿Eliminar la prueba '{pruebas_a_eliminar[0]['nombre']}'?"
        else:
            nombres = "\n".join(f"  - {p['nombre']}" for p in pruebas_a_eliminar)
            msg = f"¿Eliminar {len(pruebas_a_eliminar)} pruebas?\n\n{nombres}"

        msg += "\n\nSe desactivarán las pruebas que estén en uso en solicitudes existentes."

        if not messagebox.askyesno("Confirmar Eliminación", msg, icon='warning'):
            return

        eliminadas = 0
        desactivadas = 0
        errores = []

        for prueba in pruebas_a_eliminar:
            pid = prueba['id']
            try:
                # Verificar si la prueba tiene solicitudes asociadas (no se puede eliminar)
                en_uso = db.query_one(
                    f"SELECT COUNT(*) AS Total FROM DetalleSolicitudes WHERE PruebaID = {pid}"
                )
                total_uso = int((en_uso or {}).get('Total') or 0)

                if total_uso > 0:
                    # Tiene historial de solicitudes: solo desactivar
                    db.update('Pruebas', {'Activo': False}, f"PruebaID = {pid}")
                    desactivadas += 1
                else:
                    # Sin solicitudes: eliminar registros dependientes primero
                    db.execute(f"DELETE FROM ParametrosPrueba WHERE PruebaID = {pid}")
                    db.execute(f"DELETE FROM PruebasEnPerfil WHERE PruebaID = {pid}")
                    db.execute(f"DELETE FROM Pruebas WHERE PruebaID = {pid}")
                    eliminadas += 1
            except Exception as e:
                errores.append(f"{prueba['nombre']}: {e}")

        # Mostrar resultado
        partes = []
        if eliminadas > 0:
            partes.append(f"Se eliminaron {eliminadas} prueba(s) correctamente.")
        if desactivadas > 0:
            partes.append(
                f"Se desactivaron {desactivadas} prueba(s) porque tienen solicitudes "
                f"asociadas (no se pueden eliminar para conservar el historial)."
            )
        if errores:
            partes.append("Errores:\n" + "\n".join(errores))

        msg_resultado = "\n\n".join(partes) if partes else "No se realizó ninguna acción."

        if errores:
            messagebox.showwarning("Resultado", msg_resultado)
        else:
            messagebox.showinfo("Resultado", msg_resultado)

        self.cargar_pruebas()

    # ============================================================
    # SOLICITUDES
    # ============================================================

    def show_solicitudes(self):
        self.clear_content()
        self.set_title("📋 Gestión de Solicitudes")

        # Configurar contenido scrollable
        scrollable = self.setup_scrollable_content()

        toolbar = tk.Frame(scrollable, bg=COLORS['bg'])
        toolbar.pack(fill='x', pady=(0, 15))

        tk.Button(toolbar, text="➕ Nueva Solicitud", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.form_solicitud).pack(side='left', padx=(0, 10))

        tk.Button(toolbar, text="✏️ Editar", font=('Segoe UI', 10),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.editar_solicitud_seleccionada).pack(side='left', padx=(0, 10))

        tk.Button(toolbar, text="🗑️ Eliminar", font=('Segoe UI', 10),
                 bg=COLORS['danger'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.eliminar_solicitud_seleccionada).pack(side='left', padx=(0, 15))

        tk.Label(toolbar, text="🔍", font=('Segoe UI', 12), bg=COLORS['bg']).pack(side='left')
        self.search_sol = tk.Entry(toolbar, font=('Segoe UI', 11), width=30, relief='flat',
                                   bg='white', highlightthickness=1, highlightbackground=COLORS['border'])
        self.search_sol.pack(side='left', padx=5, ipady=6)
        self.search_sol.bind('<Return>', lambda e: self.buscar_solicitudes())

        tk.Button(toolbar, text="Buscar", font=('Segoe UI', 10), bg=COLORS['success'],
                 fg='white', relief='flat', padx=15, cursor='hand2',
                 command=self.buscar_solicitudes).pack(side='left', padx=5)

        list_frame = tk.Frame(scrollable, bg='white')
        list_frame.pack(fill='both', expand=True)

        cols = ('ID', 'Número', 'Fecha', 'Paciente', 'Estado', 'Total')
        self.tree_sol = ttk.Treeview(list_frame, columns=cols, show='headings')

        widths = [50, 150, 100, 250, 100, 100]
        for c, w in zip(cols, widths):
            self.tree_sol.heading(c, text=c)
            self.tree_sol.column(c, width=w)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_sol.yview)
        self.tree_sol.configure(yscrollcommand=vsb.set)

        self.tree_sol.pack(side='left', fill='both', expand=True, padx=(10,0), pady=10)
        vsb.pack(side='right', fill='y', pady=10, padx=(0,10))

        # Bindings
        self.tree_sol.bind('<Double-1>', self.ver_solicitud)

        # Menú contextual (clic derecho)
        self.menu_solicitud = tk.Menu(self.tree_sol, tearoff=0)
        self.menu_solicitud.add_command(label="👁️ Ver Detalles", command=lambda: self.ver_solicitud(None))
        self.menu_solicitud.add_command(label="✏️ Editar Solicitud", command=self.editar_solicitud_seleccionada)
        self.menu_solicitud.add_separator()
        self.menu_solicitud.add_command(label="🗑️ Eliminar Solicitud", command=self.eliminar_solicitud_seleccionada)

        self.tree_sol.bind('<Button-3>', self._mostrar_menu_solicitud)

        self.cargar_solicitudes()

    def cargar_solicitudes(self, filtro=""):
        for item in self.tree_sol.get_children():
            self.tree_sol.delete(item)

        where = ""
        if filtro:
            where = f"WHERE s.NumeroSolicitud LIKE '%{filtro}%' OR p.Nombres LIKE '%{filtro}%' OR p.Apellidos LIKE '%{filtro}%'"

        try:
            data = db.query(f"""
                SELECT TOP 200 s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud,
                       p.Nombres & ' ' & p.Apellidos AS Paciente, s.EstadoSolicitud, s.MontoTotal
                FROM Solicitudes s LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                {where} ORDER BY s.SolicitudID DESC
            """)
            for r in data:
                self.tree_sol.insert('', 'end', values=(
                    r['SolicitudID'],
                    r['NumeroSolicitud'] or '',
                    r['FechaSolicitud'].strftime('%d/%m/%Y') if r['FechaSolicitud'] else '',
                    r['Paciente'] or 'N/A',
                    r['EstadoSolicitud'] or 'Pendiente',
                    f"${r['MontoTotal']:,.2f}" if r['MontoTotal'] else '$0.00'
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buscar_solicitudes(self):
        self.cargar_solicitudes(self.search_sol.get().strip())

    def form_solicitud(self, solicitud_id=None):
        """Ventana principal de Registro de Solicitudes - Núcleo operativo del sistema"""
        win = tk.Toplevel(self.root)
        win.title("Editar Solicitud" if solicitud_id else "Registro de Solicitud de Laboratorio")
        win.configure(bg=COLORS['bg'])
        win.grab_set()
        win.focus_set()

        # Hacer ventana responsiva - grande pero no pantalla completa
        hacer_ventana_responsiva(win, 1400, 900, min_ancho=1000, min_alto=700)

        # Variables para cálculos
        self.sol_pruebas_seleccionadas = []  # Lista de pruebas seleccionadas
        # Reiniciar modo de solicitud al abrir nueva ventana
        self.modo_solicitud = 'nueva'
        self.solicitud_existente_id = None
        self.sol_subtotal = tk.DoubleVar(value=0.0)
        self.sol_descuento_pct = tk.DoubleVar(value=0.0)
        self.sol_descuento_monto = tk.DoubleVar(value=0.0)
        self.sol_iva_pct = tk.DoubleVar(value=16.0)
        self.sol_iva_monto = tk.DoubleVar(value=0.0)
        self.sol_total = tk.DoubleVar(value=0.0)
        self.sol_abonado = tk.DoubleVar(value=0.0)
        self.sol_saldo = tk.DoubleVar(value=0.0)

        # ============================================================
        # HEADER PRINCIPAL (FIJO - NO SE MUEVE CON SCROLL)
        # ============================================================
        header = tk.Frame(win, bg=COLORS['primary'], height=60)
        header.pack(fill='x', side='top')
        header.pack_propagate(False)

        header_left = tk.Frame(header, bg=COLORS['primary'])
        header_left.pack(side='left', fill='y')
        tk.Label(header_left, text="📋 REGISTRO DE SOLICITUD DE LABORATORIO",
                font=('Segoe UI', 16, 'bold'), bg=COLORS['primary'], fg='white').pack(side='left', padx=20, pady=15)

        header_right = tk.Frame(header, bg=COLORS['primary'])
        header_right.pack(side='right', fill='y')
        tk.Label(header_right, text=f"📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                font=('Segoe UI', 11), bg=COLORS['primary'], fg='white').pack(side='right', padx=20, pady=18)

        # ============================================================
        # ÁREA DE CONTENIDO CON SCROLL
        # ============================================================
        # Canvas para scroll
        canvas_container = tk.Frame(win, bg=COLORS['bg'])
        canvas_container.pack(fill='both', expand=True, side='top')

        canvas = tk.Canvas(canvas_container, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_container, orient='vertical', command=canvas.yview)

        # Frame scrollable que contendrá todo el contenido
        scrollable_frame = tk.Frame(canvas, bg=COLORS['bg'])

        scrollable_frame.bind(
            '<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all'))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        # Empaquetar canvas y scrollbar
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Habilitar scroll con rueda del mouse
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # ============================================================
        # CONTENEDOR PRINCIPAL (2 columnas) - AHORA DENTRO DEL CANVAS
        # ============================================================
        main_container = tk.Frame(scrollable_frame, bg=COLORS['bg'])
        main_container.pack(fill='both', expand=True, padx=15, pady=10)

        # COLUMNA IZQUIERDA (Datos principales)
        left_col = tk.Frame(main_container, bg=COLORS['bg'])
        left_col.pack(side='left', fill='both', expand=True, padx=(0, 10))

        # COLUMNA DERECHA (Facturación)
        right_col = tk.Frame(main_container, bg='white', width=350)
        right_col.pack(side='right', fill='y', padx=(10, 0))
        right_col.pack_propagate(False)

        # ============================================================
        # SECCIÓN 1: DATOS DE LA SOLICITUD
        # ============================================================
        sec_datos = tk.LabelFrame(left_col, text=" 📝 Datos de la Solicitud ", font=('Segoe UI', 11, 'bold'),
                                  bg='white', fg=COLORS['text'])
        sec_datos.pack(fill='x', pady=(0, 10))

        datos_frame = tk.Frame(sec_datos, bg='white')
        datos_frame.pack(fill='x', padx=15, pady=10)

        # Fila 1: Número y Fecha
        row1 = tk.Frame(datos_frame, bg='white')
        row1.pack(fill='x', pady=3)

        tk.Label(row1, text="N° Solicitud:", font=('Segoe UI', 10, 'bold'), bg='white', width=14, anchor='w').pack(side='left')

        # Mostrar mensaje de que se generará al guardar
        self.lbl_numero = tk.Label(row1, text="(Se generará al guardar)", font=('Segoe UI', 12, 'bold'), bg='white', fg=COLORS['text_light'])
        self.lbl_numero.pack(side='left', padx=(0, 30))

        tk.Label(row1, text="Fecha:", font=('Segoe UI', 10, 'bold'), bg='white', width=8, anchor='w').pack(side='left')
        self.entry_fecha = tk.Entry(row1, font=('Segoe UI', 10), width=12, relief='flat', bg='#f8f9fa',
                                   highlightthickness=1, highlightbackground=COLORS['border'])
        self.entry_fecha.pack(side='left', ipady=4)
        self.entry_fecha.insert(0, datetime.now().strftime('%d/%m/%Y'))

        tk.Label(row1, text="Hora:", font=('Segoe UI', 10, 'bold'), bg='white', width=6, anchor='e').pack(side='left', padx=(20, 0))
        self.entry_hora = tk.Entry(row1, font=('Segoe UI', 10), width=8, relief='flat', bg='#f8f9fa',
                                  highlightthickness=1, highlightbackground=COLORS['border'])
        self.entry_hora.pack(side='left', ipady=4)
        self.entry_hora.insert(0, datetime.now().strftime('%H:%M'))

        # Fila 2: Estado y Tipo de Atención
        row2 = tk.Frame(datos_frame, bg='white')
        row2.pack(fill='x', pady=3)

        tk.Label(row2, text="Estado:", font=('Segoe UI', 10, 'bold'), bg='white', width=14, anchor='w').pack(side='left')
        self.combo_estado = ttk.Combobox(row2, font=('Segoe UI', 10), width=15, state='readonly')
        self.combo_estado['values'] = ['Pendiente', 'En Proceso', 'Completada', 'Entregada', 'Anulada']
        self.combo_estado.set('Pendiente')
        self.combo_estado.pack(side='left', padx=(0, 30))

        tk.Label(row2, text="Tipo Atención:", font=('Segoe UI', 10, 'bold'), bg='white', width=14, anchor='w').pack(side='left')
        self.combo_tipo = ttk.Combobox(row2, font=('Segoe UI', 10), width=20, state='readonly')
        self.combo_tipo['values'] = ['Particular', 'Convenio', 'Seguro', 'Emergencia', 'Cortesía']
        self.combo_tipo.set('Particular')
        self.combo_tipo.pack(side='left')

        # ============================================================
        # SECCIÓN 2: INFORMACIÓN DEL PACIENTE
        # ============================================================
        sec_paciente = tk.LabelFrame(left_col, text=" 👤 Información del Paciente ", font=('Segoe UI', 11, 'bold'),
                                     bg='white', fg=COLORS['text'])
        sec_paciente.pack(fill='x', pady=(0, 10))

        pac_frame = tk.Frame(sec_paciente, bg='white')
        pac_frame.pack(fill='x', padx=15, pady=10)

        # Búsqueda de paciente
        search_pac = tk.Frame(pac_frame, bg='white')
        search_pac.pack(fill='x', pady=(0, 10))

        tk.Label(search_pac, text="Buscar Paciente:", font=('Segoe UI', 10, 'bold'), bg='white').pack(side='left')
        self.entry_buscar_pac = tk.Entry(search_pac, font=('Segoe UI', 11), width=40, relief='flat', bg='#f8f9fa',
                                        highlightthickness=1, highlightbackground=COLORS['border'])
        self.entry_buscar_pac.pack(side='left', padx=10, ipady=5)

        tk.Button(search_pac, text="🔍 Buscar", font=('Segoe UI', 9), bg=COLORS['primary'], fg='white',
                 relief='flat', padx=10, cursor='hand2', command=self.buscar_paciente_sol).pack(side='left', padx=5)
        tk.Button(search_pac, text="➕ Nuevo", font=('Segoe UI', 9), bg=COLORS['success'], fg='white',
                 relief='flat', padx=10, cursor='hand2', command=self.form_paciente).pack(side='left')

        # Datos del paciente seleccionado
        self.pac_info_frame = tk.Frame(pac_frame, bg='#f8f9fa')
        self.pac_info_frame.pack(fill='x')

        self.lbl_pac_nombre = tk.Label(self.pac_info_frame, text="No se ha seleccionado paciente",
                                       font=('Segoe UI', 11), bg='#f8f9fa', fg=COLORS['text_light'])
        self.lbl_pac_nombre.pack(anchor='w', padx=10, pady=5)

        self.pac_id_seleccionado = None

        # ============================================================
        # SECCIÓN 3: MÉDICO TRATANTE
        # ============================================================
        sec_medico = tk.LabelFrame(left_col, text=" 🩺 Médico Tratante / Remitente ", font=('Segoe UI', 11, 'bold'),
                                   bg='white', fg=COLORS['text'])
        sec_medico.pack(fill='x', pady=(0, 10))

        med_frame = tk.Frame(sec_medico, bg='white')
        med_frame.pack(fill='x', padx=15, pady=10)

        tk.Label(med_frame, text="Médico:", font=('Segoe UI', 10, 'bold'), bg='white').pack(side='left')
        self.combo_medico = ttk.Combobox(med_frame, font=('Segoe UI', 10), width=50)
        self.combo_medico.pack(side='left', padx=10)

        medicos = db.query("SELECT MedicoID, CodigoMedico & ' - ' & Nombres & ' ' & Apellidos & ' (' & IIF(Especialidad IS NULL, '', Especialidad) & ')' AS Nombre FROM Medicos WHERE Activo=True ORDER BY Nombres")
        self.med_map = {m['Nombre']: m['MedicoID'] for m in medicos}
        self.combo_medico['values'] = [''] + list(self.med_map.keys())

        tk.Button(med_frame, text="➕ Nuevo", font=('Segoe UI', 9), bg=COLORS['danger'], fg='white',
                 relief='flat', padx=10, cursor='hand2', command=self.form_medico).pack(side='left')

        # ============================================================
        # SECCIÓN 4: PRUEBAS SOLICITADAS
        # ============================================================
        sec_pruebas = tk.LabelFrame(left_col, text=" 🧪 Pruebas / Estudios Solicitados ", font=('Segoe UI', 11, 'bold'),
                                    bg='white', fg=COLORS['text'])
        sec_pruebas.pack(fill='both', expand=True, pady=(0, 10))

        pruebas_container = tk.Frame(sec_pruebas, bg='white')
        pruebas_container.pack(fill='both', expand=True, padx=15, pady=10)

        # Frame superior: búsqueda y agregar
        top_pruebas = tk.Frame(pruebas_container, bg='white')
        top_pruebas.pack(fill='x', pady=(0, 10))

        tk.Label(top_pruebas, text="Buscar Prueba:", font=('Segoe UI', 10), bg='white').pack(side='left')
        self.entry_buscar_prueba = tk.Entry(top_pruebas, font=('Segoe UI', 10), width=30, relief='flat', bg='#f8f9fa',
                                           highlightthickness=1, highlightbackground=COLORS['border'])
        self.entry_buscar_prueba.pack(side='left', padx=10, ipady=4)
        # Autocompletar mientras escribe
        self.entry_buscar_prueba.bind('<KeyRelease>', lambda e: self.filtrar_pruebas_disponibles())

        tk.Button(top_pruebas, text="🔄 Mostrar Todas", font=('Segoe UI', 9), bg=COLORS['primary'], fg='white',
                 relief='flat', padx=8, cursor='hand2', command=lambda: [self.entry_buscar_prueba.delete(0, 'end'), self.cargar_pruebas_disponibles()]).pack(side='left')

        # Frame con dos listas: Disponibles y Seleccionadas
        listas_frame = tk.Frame(pruebas_container, bg='white')
        listas_frame.pack(fill='both', expand=True)

        # Lista de pruebas disponibles
        disp_frame = tk.Frame(listas_frame, bg='white')
        disp_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))

        tk.Label(disp_frame, text="Pruebas Disponibles:", font=('Segoe UI', 9, 'bold'), bg='white').pack(anchor='w')

        tree_disp_frame = tk.Frame(disp_frame, bg='white')
        tree_disp_frame.pack(fill='both', expand=True)

        cols_disp = ('Código', 'Nombre', 'Precio')
        self.tree_pruebas_disp = ttk.Treeview(tree_disp_frame, columns=cols_disp, show='headings', height=8)
        self.tree_pruebas_disp.heading('Código', text='Código')
        self.tree_pruebas_disp.heading('Nombre', text='Nombre')
        self.tree_pruebas_disp.heading('Precio', text='Precio')
        self.tree_pruebas_disp.column('Código', width=70)
        self.tree_pruebas_disp.column('Nombre', width=200)
        self.tree_pruebas_disp.column('Precio', width=70)

        vsb1 = ttk.Scrollbar(tree_disp_frame, orient='vertical', command=self.tree_pruebas_disp.yview)
        self.tree_pruebas_disp.configure(yscrollcommand=vsb1.set)
        self.tree_pruebas_disp.pack(side='left', fill='both', expand=True)
        vsb1.pack(side='right', fill='y')

        # Botones de agregar/quitar
        btn_frame_pruebas = tk.Frame(listas_frame, bg='white', width=80)
        btn_frame_pruebas.pack(side='left', fill='y', padx=5)

        tk.Button(btn_frame_pruebas, text="➡️ Agregar", font=('Segoe UI', 9), bg=COLORS['success'], fg='white',
                 relief='flat', width=10, cursor='hand2', command=self.agregar_prueba_sol).pack(pady=(40, 5))
        tk.Button(btn_frame_pruebas, text="⬅️ Quitar", font=('Segoe UI', 9), bg=COLORS['danger'], fg='white',
                 relief='flat', width=10, cursor='hand2', command=self.quitar_prueba_sol).pack(pady=5)

        # Lista de pruebas seleccionadas
        sel_frame = tk.Frame(listas_frame, bg='white')
        sel_frame.pack(side='left', fill='both', expand=True, padx=(5, 0))

        tk.Label(sel_frame, text="Pruebas Seleccionadas:", font=('Segoe UI', 9, 'bold'), bg='white').pack(anchor='w')

        tree_sel_frame = tk.Frame(sel_frame, bg='white')
        tree_sel_frame.pack(fill='both', expand=True)

        cols_sel = ('Código', 'Nombre', 'Precio')
        self.tree_pruebas_sel = ttk.Treeview(tree_sel_frame, columns=cols_sel, show='headings', height=8)
        self.tree_pruebas_sel.heading('Código', text='Código')
        self.tree_pruebas_sel.heading('Nombre', text='Nombre')
        self.tree_pruebas_sel.heading('Precio', text='Precio')
        self.tree_pruebas_sel.column('Código', width=70)
        self.tree_pruebas_sel.column('Nombre', width=200)
        self.tree_pruebas_sel.column('Precio', width=70)

        vsb2 = ttk.Scrollbar(tree_sel_frame, orient='vertical', command=self.tree_pruebas_sel.yview)
        self.tree_pruebas_sel.configure(yscrollcommand=vsb2.set)
        self.tree_pruebas_sel.pack(side='left', fill='both', expand=True)
        vsb2.pack(side='right', fill='y')

        # Cargar pruebas disponibles
        self.cargar_pruebas_disponibles()

        # Doble click para agregar
        self.tree_pruebas_disp.bind('<Double-1>', lambda e: self.agregar_prueba_sol())

        # ============================================================
        # SECCIÓN 5: OBSERVACIONES
        # ============================================================
        sec_obs = tk.LabelFrame(left_col, text=" 📝 Observaciones ", font=('Segoe UI', 11, 'bold'),
                                bg='white', fg=COLORS['text'])
        sec_obs.pack(fill='x', pady=(0, 10))

        obs_frame = tk.Frame(sec_obs, bg='white')
        obs_frame.pack(fill='x', padx=15, pady=10)

        # Observaciones clínicas
        tk.Label(obs_frame, text="Diagnóstico / Motivo:", font=('Segoe UI', 9), bg='white').pack(anchor='w')
        self.txt_diagnostico = tk.Text(obs_frame, font=('Segoe UI', 10), height=2, relief='flat', bg='#f8f9fa',
                                       highlightthickness=1, highlightbackground=COLORS['border'])
        self.txt_diagnostico.pack(fill='x', pady=(2, 8))

        tk.Label(obs_frame, text="Observaciones Internas:", font=('Segoe UI', 9), bg='white').pack(anchor='w')
        self.txt_observaciones = tk.Text(obs_frame, font=('Segoe UI', 10), height=2, relief='flat', bg='#f8f9fa',
                                        highlightthickness=1, highlightbackground=COLORS['border'])
        self.txt_observaciones.pack(fill='x')

        # ============================================================
        # COLUMNA DERECHA: FACTURACIÓN
        # ============================================================
        tk.Label(right_col, text="💰 FACTURACIÓN", font=('Segoe UI', 14, 'bold'),
                bg='white', fg=COLORS['text']).pack(pady=10)

        # TASAS DE CAMBIO
        tasas_frame = tk.LabelFrame(right_col, text=" 💱 Tasas de Cambio (Ref: USD) ", font=('Segoe UI', 9, 'bold'),
                                   bg='#fff8e1', fg=COLORS['text'])
        tasas_frame.pack(fill='x', padx=10, pady=5)

        tasas_inner = tk.Frame(tasas_frame, bg='#fff8e1')
        tasas_inner.pack(fill='x', padx=10, pady=8)

        # Tasa Bs
        tk.Label(tasas_inner, text="1 USD =", font=('Segoe UI', 9), bg='#fff8e1').pack(side='left')
        self.entry_tasa_bs = tk.Entry(tasas_inner, font=('Segoe UI', 10), width=10, relief='flat',
                                     highlightthickness=1, highlightbackground=COLORS['border'], justify='right')
        self.entry_tasa_bs.pack(side='left', padx=3, ipady=2)
        self.entry_tasa_bs.insert(0, '50.00')
        self.entry_tasa_bs.bind('<KeyRelease>', lambda e: self.calcular_totales())
        tk.Label(tasas_inner, text="Bs", font=('Segoe UI', 9, 'bold'), bg='#fff8e1', fg='#e65100').pack(side='left', padx=(0, 10))

        # Tasa COP
        tk.Label(tasas_inner, text="=", font=('Segoe UI', 9), bg='#fff8e1').pack(side='left')
        self.entry_tasa_cop = tk.Entry(tasas_inner, font=('Segoe UI', 10), width=10, relief='flat',
                                      highlightthickness=1, highlightbackground=COLORS['border'], justify='right')
        self.entry_tasa_cop.pack(side='left', padx=3, ipady=2)
        self.entry_tasa_cop.insert(0, '4200.00')
        self.entry_tasa_cop.bind('<KeyRelease>', lambda e: self.calcular_totales())
        tk.Label(tasas_inner, text="COP", font=('Segoe UI', 9, 'bold'), bg='#fff8e1', fg='#1565c0').pack(side='left')

        tk.Frame(right_col, bg=COLORS['border'], height=1).pack(fill='x', padx=10, pady=5)

        fact_frame = tk.Frame(right_col, bg='white')
        fact_frame.pack(fill='x', padx=15, pady=5)

        # Subtotal
        row_sub = tk.Frame(fact_frame, bg='white')
        row_sub.pack(fill='x', pady=3)
        tk.Label(row_sub, text="Subtotal:", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        self.lbl_subtotal = tk.Label(row_sub, text="$0.00", font=('Segoe UI', 12, 'bold'), bg='white', fg=COLORS['text'])
        self.lbl_subtotal.pack(side='right')

        # Descuento
        row_desc = tk.Frame(fact_frame, bg='white')
        row_desc.pack(fill='x', pady=3)
        tk.Label(row_desc, text="Descuento (%):", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        self.entry_descuento = tk.Entry(row_desc, font=('Segoe UI', 10), width=6, relief='flat', bg='#f8f9fa',
                                       highlightthickness=1, highlightbackground=COLORS['border'], justify='right')
        self.entry_descuento.pack(side='right', ipady=2)
        self.entry_descuento.insert(0, '0')
        self.entry_descuento.bind('<KeyRelease>', lambda e: self.calcular_totales())

        row_desc_monto = tk.Frame(fact_frame, bg='white')
        row_desc_monto.pack(fill='x', pady=1)
        tk.Label(row_desc_monto, text="", bg='white', width=12).pack(side='left')
        self.lbl_descuento = tk.Label(row_desc_monto, text="-$0.00", font=('Segoe UI', 9), bg='white', fg=COLORS['danger'])
        self.lbl_descuento.pack(side='right')

        # IVA
        row_iva = tk.Frame(fact_frame, bg='white')
        row_iva.pack(fill='x', pady=3)
        tk.Label(row_iva, text="IVA (%):", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        self.entry_iva = tk.Entry(row_iva, font=('Segoe UI', 10), width=6, relief='flat', bg='#f8f9fa',
                                 highlightthickness=1, highlightbackground=COLORS['border'], justify='right')
        self.entry_iva.pack(side='right', ipady=2)
        self.entry_iva.insert(0, '16')
        self.entry_iva.bind('<KeyRelease>', lambda e: self.calcular_totales())

        row_iva_monto = tk.Frame(fact_frame, bg='white')
        row_iva_monto.pack(fill='x', pady=1)
        tk.Label(row_iva_monto, text="", bg='white', width=12).pack(side='left')
        self.lbl_iva = tk.Label(row_iva_monto, text="+$0.00", font=('Segoe UI', 9), bg='white', fg=COLORS['success'])
        self.lbl_iva.pack(side='right')

        tk.Frame(fact_frame, bg=COLORS['border'], height=1).pack(fill='x', pady=8)

        # TOTALES EN 3 MONEDAS
        totales_frame = tk.Frame(fact_frame, bg='#e3f2fd')
        totales_frame.pack(fill='x', pady=5)

        tk.Label(totales_frame, text="TOTAL:", font=('Segoe UI', 11, 'bold'), bg='#e3f2fd').pack(anchor='w', padx=10, pady=(8, 5))

        # USD
        row_usd = tk.Frame(totales_frame, bg='#e3f2fd')
        row_usd.pack(fill='x', padx=10, pady=2)
        tk.Label(row_usd, text="🇺🇸 USD:", font=('Segoe UI', 10, 'bold'), bg='#e3f2fd', width=10, anchor='w').pack(side='left')
        self.lbl_total_usd = tk.Label(row_usd, text="$0.00", font=('Segoe UI', 14, 'bold'), bg='#e3f2fd', fg='#2e7d32')
        self.lbl_total_usd.pack(side='right')

        # Bs
        row_bs = tk.Frame(totales_frame, bg='#e3f2fd')
        row_bs.pack(fill='x', padx=10, pady=2)
        tk.Label(row_bs, text="🇻🇪 Bs:", font=('Segoe UI', 10, 'bold'), bg='#e3f2fd', width=10, anchor='w').pack(side='left')
        self.lbl_total_bs = tk.Label(row_bs, text="Bs. 0,00", font=('Segoe UI', 12, 'bold'), bg='#e3f2fd', fg='#e65100')
        self.lbl_total_bs.pack(side='right')

        # COP
        row_cop = tk.Frame(totales_frame, bg='#e3f2fd')
        row_cop.pack(fill='x', padx=10, pady=(2, 8))
        tk.Label(row_cop, text="🇨🇴 COP:", font=('Segoe UI', 10, 'bold'), bg='#e3f2fd', width=10, anchor='w').pack(side='left')
        self.lbl_total_cop = tk.Label(row_cop, text="$0", font=('Segoe UI', 12, 'bold'), bg='#e3f2fd', fg='#1565c0')
        self.lbl_total_cop.pack(side='right')

        tk.Frame(fact_frame, bg=COLORS['border'], height=1).pack(fill='x', pady=8)

        # Monto Abonado
        row_abono = tk.Frame(fact_frame, bg='white')
        row_abono.pack(fill='x', pady=3)
        tk.Label(row_abono, text="Abonado (USD):", font=('Segoe UI', 10), bg='white', width=12, anchor='w').pack(side='left')
        self.entry_abonado = tk.Entry(row_abono, font=('Segoe UI', 10), width=10, relief='flat', bg='#e8f5e9',
                                     highlightthickness=1, highlightbackground=COLORS['success'], justify='right')
        self.entry_abonado.pack(side='right', ipady=2)
        self.entry_abonado.insert(0, '0.00')
        self.entry_abonado.bind('<KeyRelease>', lambda e: self.calcular_totales())

        # Saldo Pendiente
        row_saldo = tk.Frame(fact_frame, bg='white')
        row_saldo.pack(fill='x', pady=5)
        tk.Label(row_saldo, text="Saldo:", font=('Segoe UI', 10, 'bold'), bg='white', width=12, anchor='w').pack(side='left')
        self.lbl_saldo = tk.Label(row_saldo, text="$0.00", font=('Segoe UI', 12, 'bold'), bg='white', fg=COLORS['danger'])
        self.lbl_saldo.pack(side='right')

        # ============================================================
        # SELECCIÓN DE MONEDA Y FORMA DE PAGO
        # ============================================================
        pago_frame = tk.LabelFrame(fact_frame, text=" 💳 Opciones de Pago ", font=('Segoe UI', 9, 'bold'),
                                  bg='#f5f5f5', fg=COLORS['text'])
        pago_frame.pack(fill='x', pady=8)

        pago_inner = tk.Frame(pago_frame, bg='#f5f5f5')
        pago_inner.pack(fill='x', padx=10, pady=8)

        # Moneda de Pago
        row_moneda = tk.Frame(pago_inner, bg='#f5f5f5')
        row_moneda.pack(fill='x', pady=3)
        tk.Label(row_moneda, text="Moneda:", font=('Segoe UI', 10, 'bold'), bg='#f5f5f5', width=10, anchor='w').pack(side='left')
        self.combo_moneda = ttk.Combobox(row_moneda, font=('Segoe UI', 10), state='readonly', width=18)
        self.combo_moneda['values'] = ['🇺🇸 USD (Dólar)', '🇻🇪 Bs (Bolívares)', '🇨🇴 COP (Pesos)']
        self.combo_moneda.set('🇺🇸 USD (Dólar)')
        self.combo_moneda.pack(side='left')
        self.combo_moneda.bind('<<ComboboxSelected>>', lambda e: self.actualizar_total_moneda())

        # Forma de Pago
        row_forma = tk.Frame(pago_inner, bg='#f5f5f5')
        row_forma.pack(fill='x', pady=3)
        tk.Label(row_forma, text="Forma:", font=('Segoe UI', 10, 'bold'), bg='#f5f5f5', width=10, anchor='w').pack(side='left')
        self.combo_forma_pago = ttk.Combobox(row_forma, font=('Segoe UI', 10), state='readonly', width=18)
        self.combo_forma_pago['values'] = ['Efectivo', 'Tarjeta Débito', 'Tarjeta Crédito', 'Transferencia', 'Zelle/Pago Móvil', 'Mixto']
        self.combo_forma_pago.set('Efectivo')
        self.combo_forma_pago.pack(side='left')

        # Total a Pagar (según moneda seleccionada)
        tk.Frame(pago_inner, bg='#bdbdbd', height=1).pack(fill='x', pady=8)

        self.frame_total_pagar = tk.Frame(pago_inner, bg='#4caf50')
        self.frame_total_pagar.pack(fill='x', pady=3)

        tk.Label(self.frame_total_pagar, text="TOTAL A PAGAR:", font=('Segoe UI', 10, 'bold'),
                bg='#4caf50', fg='white').pack(side='left', padx=10, pady=8)
        self.lbl_total_pagar = tk.Label(self.frame_total_pagar, text="$0.00 USD",
                                        font=('Segoe UI', 16, 'bold'), bg='#4caf50', fg='white')
        self.lbl_total_pagar.pack(side='right', padx=10, pady=8)

        # ============================================================
        # BOTONES DE ACCIÓN
        # ============================================================
        btn_frame = tk.Frame(right_col, bg='white')
        btn_frame.pack(fill='x', padx=15, pady=15, side='bottom')

        tk.Button(btn_frame, text="💾 GUARDAR SOLICITUD", font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', cursor='hand2',
                 command=lambda: self.guardar_solicitud_completa(win)).pack(fill='x', pady=3, ipady=8)

        tk.Button(btn_frame, text="🧾 Imprimir Comprobante", font=('Segoe UI', 10),
                 bg=COLORS['info'], fg='white', relief='flat', cursor='hand2',
                 command=lambda: self.imprimir_comprobante()).pack(fill='x', pady=3, ipady=5)

        tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 10),
                 bg='#95a5a6', fg='white', relief='flat', cursor='hand2',
                 command=win.destroy).pack(fill='x', pady=3, ipady=5)

        # Guardar referencias
        self.sol_win = win
        self.sol_canvas = canvas

    def cargar_pruebas_disponibles(self, filtro=""):
        """Carga las pruebas disponibles en el treeview (excluyendo las ya seleccionadas)"""
        for item in self.tree_pruebas_disp.get_children():
            self.tree_pruebas_disp.delete(item)

        where = "WHERE Activo=True"
        if filtro:
            where += f" AND (NombrePrueba LIKE '%{filtro}%' OR CodigoPrueba LIKE '%{filtro}%')"

        # Obtener IDs de pruebas ya seleccionadas
        ids_seleccionados = []
        if hasattr(self, 'sol_pruebas_seleccionadas') and self.sol_pruebas_seleccionadas:
            ids_seleccionados = [p['id'] for p in self.sol_pruebas_seleccionadas]

        try:
            pruebas = db.query(f"SELECT PruebaID, CodigoPrueba, NombrePrueba, Precio FROM Pruebas {where} ORDER BY NombrePrueba")
            self.pruebas_data = {}
            for p in pruebas:
                # Excluir pruebas ya seleccionadas
                if p['PruebaID'] in ids_seleccionados:
                    continue

                precio = float(p.get('Precio') or 0)  # Convertir a float
                iid = self.tree_pruebas_disp.insert('', 'end', values=(
                    p['CodigoPrueba'] or '',
                    p['NombrePrueba'] or '',
                    f"${precio:,.2f}"
                ))
                self.pruebas_data[iid] = {'id': p['PruebaID'], 'codigo': p['CodigoPrueba'],
                                          'nombre': p['NombrePrueba'], 'precio': precio}
        except Exception as e:
            print(f"Error cargando pruebas: {e}")

    def filtrar_pruebas_disponibles(self):
        """Filtra las pruebas según el texto de búsqueda"""
        filtro = self.entry_buscar_prueba.get().strip()
        self.cargar_pruebas_disponibles(filtro)

    def agregar_prueba_sol(self):
        """Agrega una prueba seleccionada a la lista de la solicitud"""
        sel = self.tree_pruebas_disp.selection()
        if not sel:
            return

        pruebas_agregadas = False
        for item in sel:
            if item in self.pruebas_data:
                data = self.pruebas_data[item]
                # Agregar a la lista de seleccionadas
                self.tree_pruebas_sel.insert('', 'end', values=(
                    data['codigo'],
                    data['nombre'],
                    f"${data['precio']:,.2f}"
                ))
                self.sol_pruebas_seleccionadas.append(data)
                pruebas_agregadas = True

        # Actualizar lista de disponibles (para quitar las agregadas)
        if pruebas_agregadas:
            filtro = self.entry_buscar_prueba.get().strip() if hasattr(self, 'entry_buscar_prueba') else ""
            self.cargar_pruebas_disponibles(filtro)

        self.calcular_totales()

    def quitar_prueba_sol(self):
        """Quita una prueba de la lista de seleccionadas"""
        sel = self.tree_pruebas_sel.selection()
        if not sel:
            return

        for item in sel:
            codigo = str(self.tree_pruebas_sel.item(item)['values'][0])
            self.tree_pruebas_sel.delete(item)
            # Quitar de la lista interna (comparar como string para evitar desajuste de tipos)
            self.sol_pruebas_seleccionadas = [p for p in self.sol_pruebas_seleccionadas if str(p['codigo']) != codigo]

        # Actualizar lista de disponibles (para mostrar las pruebas removidas)
        filtro = self.entry_buscar_prueba.get().strip() if hasattr(self, 'entry_buscar_prueba') else ""
        self.cargar_pruebas_disponibles(filtro)

        self.calcular_totales()

    def calcular_totales(self):
        """Calcula subtotal, descuento, IVA, total y saldo"""
        # Subtotal = suma de precios de pruebas (convertir a float para evitar errores con Decimal)
        subtotal = float(sum(float(p['precio']) for p in self.sol_pruebas_seleccionadas))
        self.lbl_subtotal.config(text=f"${subtotal:,.2f}")

        # Descuento
        try:
            desc_pct = float(self.entry_descuento.get() or 0)
        except:
            desc_pct = 0
        desc_monto = subtotal * (desc_pct / 100)
        self.lbl_descuento.config(text=f"-${desc_monto:,.2f}")

        # Base imponible
        base = subtotal - desc_monto

        # IVA
        try:
            iva_pct = float(self.entry_iva.get() or 0)
        except:
            iva_pct = 0
        iva_monto = base * (iva_pct / 100)
        self.lbl_iva.config(text=f"+${iva_monto:,.2f}")

        # Total en USD
        total_usd = base + iva_monto

        # Obtener tasas de cambio
        try:
            tasa_bs = float(self.entry_tasa_bs.get() or 1)
        except:
            tasa_bs = 1
        try:
            tasa_cop = float(self.entry_tasa_cop.get() or 1)
        except:
            tasa_cop = 1

        # Calcular totales en cada moneda
        total_bs = total_usd * tasa_bs
        total_cop = total_usd * tasa_cop

        # Guardar totales para usar en otras funciones
        self.total_usd_actual = total_usd
        self.total_bs_actual = total_bs
        self.total_cop_actual = total_cop
        self.tasa_bs_actual = tasa_bs
        self.tasa_cop_actual = tasa_cop

        # Actualizar labels de totales
        self.lbl_total_usd.config(text=f"${total_usd:,.2f}")
        self.lbl_total_bs.config(text=f"Bs. {total_bs:,.2f}")
        self.lbl_total_cop.config(text=f"${total_cop:,.0f} COP")

        # Abonado y Saldo (en USD)
        try:
            abonado = float(self.entry_abonado.get() or 0)
        except:
            abonado = 0
        saldo = total_usd - abonado
        self.lbl_saldo.config(text=f"${saldo:,.2f}")

        # Cambiar color del saldo según si está pagado o no
        if saldo <= 0:
            self.lbl_saldo.config(fg=COLORS['success'])
        else:
            self.lbl_saldo.config(fg=COLORS['danger'])

        # Actualizar total según moneda seleccionada
        self.actualizar_total_moneda()

    def actualizar_total_moneda(self):
        """Actualiza el total a pagar según la moneda seleccionada"""
        try:
            moneda = self.combo_moneda.get()
            total_usd = getattr(self, 'total_usd_actual', 0)
            total_bs = getattr(self, 'total_bs_actual', 0)
            total_cop = getattr(self, 'total_cop_actual', 0)

            if 'USD' in moneda:
                self.lbl_total_pagar.config(text=f"${total_usd:,.2f} USD")
                self.frame_total_pagar.config(bg='#2e7d32')  # Verde oscuro
                self.lbl_total_pagar.config(bg='#2e7d32')
            elif 'Bs' in moneda:
                self.lbl_total_pagar.config(text=f"Bs. {total_bs:,.2f}")
                self.frame_total_pagar.config(bg='#e65100')  # Naranja
                self.lbl_total_pagar.config(bg='#e65100')
            elif 'COP' in moneda:
                self.lbl_total_pagar.config(text=f"${total_cop:,.0f} COP")
                self.frame_total_pagar.config(bg='#1565c0')  # Azul
                self.lbl_total_pagar.config(bg='#1565c0')

            # Actualizar también el label dentro del frame
            for widget in self.frame_total_pagar.winfo_children():
                if isinstance(widget, tk.Label) and 'TOTAL' in widget.cget('text'):
                    widget.config(bg=self.frame_total_pagar.cget('bg'))
        except:
            pass

    def buscar_paciente_sol(self):
        """Busca pacientes y muestra resultados para seleccionar"""
        filtro = self.entry_buscar_pac.get().strip()
        if not filtro:
            return

        try:
            pacientes = db.query(f"""
                SELECT TOP 10 PacienteID, NumeroDocumento, Nombres, Apellidos,
                       FechaNacimiento, Sexo, Telefono1
                FROM Pacientes
                WHERE Nombres LIKE '%{filtro}%' OR Apellidos LIKE '%{filtro}%'
                      OR NumeroDocumento LIKE '%{filtro}%'
                ORDER BY Apellidos, Nombres
            """)

            if not pacientes:
                messagebox.showinfo("Búsqueda", "No se encontraron pacientes")
                return

            if len(pacientes) == 1:
                self.seleccionar_paciente_sol(pacientes[0])
            else:
                # Mostrar ventana de selección
                self.mostrar_seleccion_paciente(pacientes)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def mostrar_seleccion_paciente(self, pacientes):
        """Muestra ventana para seleccionar paciente de los resultados"""
        win = tk.Toplevel(self.sol_win)
        win.title("Seleccionar Paciente")
        win.grab_set()
        win.focus_set()

        # Hacer ventana responsiva
        hacer_ventana_responsiva(win, 700, 400, min_ancho=600, min_alto=350)

        tk.Label(win, text="Seleccione un paciente:", font=('Segoe UI', 12, 'bold')).pack(pady=10)

        frame = tk.Frame(win)
        frame.pack(fill='both', expand=True, padx=10, pady=5)

        cols = ('Documento', 'Nombres', 'Apellidos', 'Teléfono')
        tree = ttk.Treeview(frame, columns=cols, show='headings')
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, width=150)

        vsb = ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        pac_map = {}
        for p in pacientes:
            iid = tree.insert('', 'end', values=(
                p['NumeroDocumento'] or '',
                p['Nombres'] or '', p['Apellidos'] or '', p['Telefono1'] or ''
            ))
            pac_map[iid] = p

        def seleccionar():
            sel = tree.selection()
            if sel:
                self.seleccionar_paciente_sol(pac_map[sel[0]])
                win.destroy()

        tree.bind('<Double-1>', lambda e: seleccionar())

        tk.Button(win, text="Seleccionar", font=('Segoe UI', 10), bg=COLORS['primary'], fg='white',
                 relief='flat', padx=20, command=seleccionar).pack(pady=10)

    def seleccionar_paciente_sol(self, paciente):
        """Establece el paciente seleccionado en la solicitud"""
        self.pac_id_seleccionado = paciente['PacienteID']

        # Actualizar la información mostrada
        nombre = f"{paciente['Nombres'] or ''} {paciente['Apellidos'] or ''}".strip()
        doc = paciente['NumeroDocumento'] or 'S/D'
        tel = paciente['Telefono1'] or 'S/T'

        edad = ""
        if paciente.get('FechaNacimiento'):
            try:
                fn = paciente['FechaNacimiento']
                hoy = datetime.now()
                edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
                edad = f" | {edad} años"
            except:
                pass

        sexo = paciente.get('Sexo') or ''
        if sexo:
            sexo = f" | {'Masculino' if sexo == 'M' else 'Femenino'}"

        info_text = f"👤 {nombre}  |  Doc: {doc}  |  Tel: {tel}{edad}{sexo}"

        self.lbl_pac_nombre.config(text=info_text, fg=COLORS['text'])
        self.entry_buscar_pac.delete(0, 'end')
        self.entry_buscar_pac.insert(0, nombre)

        # Verificar si el paciente tiene solicitudes del MISMO DÍA primero,
        # luego activas (últimas 48h) como fallback
        self.modo_solicitud = 'nueva'
        self.solicitud_existente_id = None

        if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
            try:
                # PRIORIDAD 1: Buscar solicitudes del MISMO DÍA
                solicitudes_hoy = self.gestor_solicitudes.buscar_solicitudes_mismo_dia(
                    self.pac_id_seleccionado
                )

                # PRIORIDAD 2: Buscar solicitudes activas (48h) si no hay del mismo día
                if not solicitudes_hoy:
                    solicitudes_hoy = self.gestor_solicitudes.buscar_solicitudes_paciente(
                        self.pac_id_seleccionado, solo_activas=True
                    )

                if solicitudes_hoy:
                    # Determinar si son del mismo día para el mensaje
                    from datetime import date
                    hoy = date.today()
                    son_de_hoy = False
                    for s in solicitudes_hoy:
                        f = s.get('FechaSolicitud')
                        if f and hasattr(f, 'date') and f.date() == hoy:
                            son_de_hoy = True
                            break

                    # Mostrar diálogo para elegir entre agregar a existente o crear nueva
                    dialogo = DialogoSolicitudExistente(
                        self.sol_win,
                        solicitudes_hoy,
                        nombre,
                        es_mismo_dia=son_de_hoy
                    )

                    if dialogo.resultado == 'agregar':
                        # Modo: agregar pruebas a solicitud existente
                        self.modo_solicitud = 'agregar'
                        self.solicitud_existente_id = dialogo.solicitud_seleccionada.get('SolicitudID')

                        # Actualizar UI para indicar modo agregar
                        num_sol = dialogo.solicitud_seleccionada.get('NumeroSolicitud', '')
                        self.lbl_numero.config(text=f"Agregando a: {num_sol}", fg='#f39c12')

                        # Cargar pruebas existentes de la solicitud para mostrar
                        pruebas_existentes = self.gestor_solicitudes.obtener_pruebas_solicitud(
                            self.solicitud_existente_id
                        )
                        if pruebas_existentes:
                            info_existentes = f"\n📋 Pruebas existentes ({len(pruebas_existentes)}): "
                            info_existentes += ", ".join([p.get('NombrePrueba', '')[:20] for p in pruebas_existentes[:3]])
                            if len(pruebas_existentes) > 3:
                                info_existentes += f"... y {len(pruebas_existentes) - 3} más"
                            self.lbl_pac_nombre.config(text=info_text + info_existentes)

                    elif dialogo.resultado == 'nueva':
                        # Modo: crear nueva solicitud
                        self.modo_solicitud = 'nueva'
                        self.solicitud_existente_id = None
                        self.lbl_numero.config(text="(Se generará al guardar)", fg='#7f8c8d')
                    else:
                        # Canceló el diálogo - limpiar selección
                        self.pac_id_seleccionado = None
                        self.lbl_pac_nombre.config(text="👤 Seleccione un paciente", fg='#7f8c8d')
                        self.entry_buscar_pac.delete(0, 'end')
                        return
            except Exception as e:
                print(f"Error verificando solicitudes activas: {e}")
                # En caso de error, continuar con modo nueva

    def guardar_solicitud_completa(self, win):
        """Guarda la solicitud completa con todos sus detalles"""
        # Validaciones
        if not self.pac_id_seleccionado:
            messagebox.showerror("Error", "Debe seleccionar un paciente")
            return

        if not self.sol_pruebas_seleccionadas:
            messagebox.showerror("Error", "Debe agregar al menos una prueba")
            return

        try:
            # VERIFICACIÓN FINAL: Si modo es 'nueva', revisar si ya hay solicitud del mismo día
            if self.modo_solicitud == 'nueva' and self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                solicitudes_hoy = self.gestor_solicitudes.buscar_solicitudes_mismo_dia(
                    self.pac_id_seleccionado
                )
                if solicitudes_hoy:
                    # Ofrecer última oportunidad de agregar en vez de duplicar
                    from datetime import date
                    nums = ", ".join([s.get('NumeroSolicitud', '') for s in solicitudes_hoy[:3]])
                    resp = messagebox.askyesnocancel(
                        "Paciente ya registrado hoy",
                        f"Este paciente ya tiene {len(solicitudes_hoy)} solicitud(es) hoy: {nums}\n\n"
                        f"¿Desea AGREGAR las pruebas a una solicitud existente?\n\n"
                        f"  SI = Agregar a solicitud existente (recomendado)\n"
                        f"  NO = Crear solicitud nueva de todas formas\n"
                        f"  Cancelar = Volver sin guardar",
                        icon='warning',
                        parent=win
                    )
                    if resp is None:
                        # Cancelar
                        return
                    elif resp:
                        # SI = Cambiar a modo agregar
                        # Seleccionar la primera solicitud del día
                        self.modo_solicitud = 'agregar'
                        self.solicitud_existente_id = solicitudes_hoy[0].get('SolicitudID')
                        num_sol = solicitudes_hoy[0].get('NumeroSolicitud', '')
                        self.lbl_numero.config(text=f"Agregando a: {num_sol}", fg='#f39c12')
                    # Si NO, continuar con modo 'nueva'

            # Calcular totales para mostrar en diálogo
            subtotal = sum(p['precio'] for p in self.sol_pruebas_seleccionadas)
            desc_pct = float(self.entry_descuento.get() or 0)
            desc_monto = subtotal * (desc_pct / 100)
            base = subtotal - desc_monto
            iva_pct = float(self.entry_iva.get() or 0)
            iva_monto = base * (iva_pct / 100)
            total = base + iva_monto
            abonado = float(self.entry_abonado.get() or 0)

            # Preparar lista de pruebas para el gestor
            pruebas_para_guardar = [
                {'id': p['id'], 'nombre': p['nombre'], 'precio': p['precio']}
                for p in self.sol_pruebas_seleccionadas
            ]

            # Verificar si usar el gestor de solicitudes (nuevo sistema)
            if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                # Determinar si es agregar a existente o crear nueva
                if self.modo_solicitud == 'agregar' and self.solicitud_existente_id:
                    # MODO: Agregar pruebas a solicitud existente
                    resultado = self._guardar_agregar_pruebas(win, pruebas_para_guardar, total)
                else:
                    # MODO: Crear nueva solicitud
                    resultado = self._guardar_nueva_solicitud(win, pruebas_para_guardar, total, desc_pct, iva_pct)
            else:
                # Fallback al método antiguo si el gestor no está disponible
                resultado = self._guardar_solicitud_legacy(win, pruebas_para_guardar, total, desc_pct, iva_pct, abonado)

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}")

    def _guardar_agregar_pruebas(self, win, pruebas, total):
        """Agrega pruebas a una solicitud existente usando el gestor"""
        # Verificar permisos
        if not self.gestor_solicitudes.tiene_permiso('agregar_pruebas'):
            messagebox.showerror("Acceso Denegado", "No tiene permisos para agregar pruebas")
            return False

        # Mostrar diálogo para elegir si generar documento adicional
        solicitud_info = self.gestor_solicitudes.obtener_solicitud(self.solicitud_existente_id)
        puede_facturar = self.gestor_solicitudes.tiene_permiso('generar_factura')

        dialogo = DialogoAgregarPruebas(win, solicitud_info, puede_facturar)

        if dialogo.resultado is None:
            return False  # Usuario canceló

        # Agregar las pruebas
        resultado = self.gestor_solicitudes.agregar_pruebas_solicitud(
            self.solicitud_existente_id,
            pruebas,
            recalcular_totales=True
        )

        if not resultado['exito']:
            messagebox.showerror("Error", resultado['mensaje'])
            return False

        nuevo_total = resultado.get('nuevo_total', total)

        # Generar documento si se seleccionó
        doc_mensaje = ""
        doc_result = None
        if dialogo.resultado == 'recibo':
            doc_result = self.gestor_solicitudes.generar_recibo(
                self.solicitud_existente_id,
                {'FormaPago': self.combo_forma_pago.get() if hasattr(self, 'combo_forma_pago') else 'Efectivo'}
            )
            if doc_result['exito']:
                doc_mensaje = f"\nRecibo generado: {doc_result['numero_recibo']}"
                self._generar_pdf_recibo(doc_result['numero_recibo'], self.solicitud_existente_id, doc_result.get('total', 0))
            else:
                doc_mensaje = f"\nAdvertencia: {doc_result['mensaje']}"

        elif dialogo.resultado == 'factura':
            doc_result = self.gestor_solicitudes.generar_factura(self.solicitud_existente_id)
            if doc_result['exito']:
                doc_mensaje = f"\nFactura generada: {doc_result['numero_factura']}"
            else:
                doc_mensaje = f"\nAdvertencia: {doc_result['mensaje']}"

        # Registrar ingreso en caja automaticamente
        if doc_result and doc_result.get('exito'):
            try:
                if VENTANA_ADMIN_DISPONIBLE:
                    from modulos.modulo_administrativo import GestorCajaChica
                    _gc = GestorCajaChica(db)
                    _caja = _gc.obtener_caja_abierta()
                    if _caja:
                        _fp_texto = self.combo_forma_pago.get() if hasattr(self, 'combo_forma_pago') else 'Efectivo'
                        _fp = db.query_one(f"SELECT FormaPagoID FROM [FormasPago] WHERE Nombre LIKE '%{_fp_texto}%' AND Activo=True")
                        _fp_id = _fp['FormaPagoID'] if _fp else 'Null'
                        _doc_tipo = 'Recibo' if dialogo.resultado == 'recibo' else 'Factura'
                        _doc_num = doc_result.get('numero_recibo') or doc_result.get('numero_factura', '')
                        _gc.registrar_movimiento(_caja['CajaID'], {
                            'Tipo': 'Ingreso',
                            'Categoria': 'Pago de solicitud',
                            'Descripcion': f'{_doc_tipo} {_doc_num}',
                            'Monto': nuevo_total,
                            'FormaPagoID': _fp_id,
                            'Referencia': _doc_num,
                            'FacturaID': doc_result.get('factura_id', 'Null'),
                        }, self.user.get('UsuarioID', 1))
            except Exception as _e_caja:
                print(f"Advertencia: No se pudo registrar en caja: {_e_caja}")

        # Mostrar mensaje de éxito
        messagebox.showinfo(
            "Éxito",
            f"{resultado['mensaje']}\n"
            f"Solicitud: {solicitud_info.get('NumeroSolicitud', '')}\n"
            f"Nuevo total: ${nuevo_total:,.2f}{doc_mensaje}"
        )

        win.destroy()
        self.cargar_solicitudes()
        return True

    def _guardar_nueva_solicitud(self, win, pruebas, total, desc_pct, iva_pct):
        """Crea una nueva solicitud usando el gestor"""
        # Verificar permisos
        if not self.gestor_solicitudes.tiene_permiso('crear_solicitud'):
            messagebox.showerror("Acceso Denegado", "No tiene permisos para crear solicitudes")
            return False

        # Mostrar diálogo para elegir tipo de documento
        puede_facturar = self.gestor_solicitudes.tiene_permiso('generar_factura')
        dialogo = DialogoTipoDocumento(win, total, puede_facturar)

        if dialogo.resultado is None:
            return False  # Usuario canceló

        # Preparar datos de la solicitud
        datos_solicitud = {
            'PacienteID': self.pac_id_seleccionado,
            'MedicoID': self.med_map.get(self.combo_medico.get()) if hasattr(self, 'med_map') else None,
            'TipoServicio': self.combo_tipo.get() if hasattr(self, 'combo_tipo') else 'Particular',
            'DiagnosticoPresuntivo': self.txt_diagnostico.get('1.0', 'end').strip() if hasattr(self, 'txt_diagnostico') else '',
            'Observaciones': self.txt_observaciones.get('1.0', 'end').strip() if hasattr(self, 'txt_observaciones') else '',
            'PorcentajeDescuento': desc_pct,
            'PorcentajeIVA': iva_pct,
        }

        # Crear la solicitud
        resultado = self.gestor_solicitudes.crear_solicitud(
            datos_solicitud,
            pruebas,
            self.config_numeracion
        )

        if not resultado['exito']:
            messagebox.showerror("Error", resultado['mensaje'])
            return False

        sol_id = resultado['solicitud_id']
        numero = resultado['numero']

        # Actualizar el label con el número generado
        self.lbl_numero.config(text=numero, fg=COLORS['primary'])

        # Generar documento según selección
        doc_mensaje = ""
        doc_result = None
        if dialogo.resultado == 'recibo':
            doc_result = self.gestor_solicitudes.generar_recibo(
                sol_id,
                {'FormaPago': dialogo.forma_pago}
            )
            if doc_result['exito']:
                doc_mensaje = f"\nRecibo generado: {doc_result['numero_recibo']}"
                self._generar_pdf_recibo(doc_result['numero_recibo'], sol_id, doc_result.get('total', 0))
            else:
                doc_mensaje = f"\nAdvertencia recibo: {doc_result['mensaje']}"

        elif dialogo.resultado == 'factura':
            doc_result = self.gestor_solicitudes.generar_factura(sol_id)
            if doc_result['exito']:
                doc_mensaje = f"\nFactura generada: {doc_result['numero_factura']}"
            else:
                doc_mensaje = f"\nAdvertencia factura: {doc_result['mensaje']}"

        # Registrar ingreso en caja automaticamente
        if doc_result and doc_result.get('exito'):
            try:
                if VENTANA_ADMIN_DISPONIBLE:
                    from modulos.modulo_administrativo import GestorCajaChica
                    _gc = GestorCajaChica(db)
                    _caja = _gc.obtener_caja_abierta()
                    if _caja:
                        _fp_texto = dialogo.forma_pago or 'Efectivo'
                        _fp = db.query_one(f"SELECT FormaPagoID FROM [FormasPago] WHERE Nombre LIKE '%{_fp_texto}%' AND Activo=True")
                        _fp_id = _fp['FormaPagoID'] if _fp else 'Null'
                        _doc_tipo = 'Recibo' if dialogo.resultado == 'recibo' else 'Factura'
                        _doc_num = doc_result.get('numero_recibo') or doc_result.get('numero_factura', '')
                        _gc.registrar_movimiento(_caja['CajaID'], {
                            'Tipo': 'Ingreso',
                            'Categoria': 'Pago de solicitud',
                            'Descripcion': f'{_doc_tipo} {_doc_num}',
                            'Monto': total,
                            'FormaPagoID': _fp_id,
                            'Referencia': _doc_num,
                            'FacturaID': doc_result.get('factura_id', 'Null'),
                        }, self.user.get('UsuarioID', 1))
            except Exception as _e_caja:
                print(f"Advertencia: No se pudo registrar en caja: {_e_caja}")

        # Mostrar mensaje de éxito
        abonado = float(self.entry_abonado.get() or 0) if hasattr(self, 'entry_abonado') else 0
        messagebox.showinfo(
            "Éxito",
            f"Solicitud {numero} guardada correctamente\n\n"
            f"Total: ${total:,.2f}\n"
            f"Abonado: ${abonado:,.2f}\n"
            f"Saldo: ${total - abonado:,.2f}{doc_mensaje}"
        )

        win.destroy()
        self.cargar_solicitudes()
        return True

    def _guardar_solicitud_legacy(self, win, pruebas, total, desc_pct, iva_pct, abonado):
        """Método legacy para guardar solicitud sin el gestor (fallback)"""
        # Mostrar diálogo para elegir tipo de documento
        tipo_doc = self._mostrar_dialogo_tipo_documento(win, total)
        if tipo_doc is None:
            return False  # Usuario canceló

        # Generar número de solicitud usando el configurador de numeración
        if self.config_numeracion:
            try:
                numero = self.config_numeracion.generar_numero_solicitud()
            except Exception as e:
                print(f"Error al generar número con configurador: {e}, usando método antiguo")
                count = db.count('Solicitudes') + 1
                numero = f"{datetime.now().strftime('%Y')}-{count:06d}"
        else:
            count = db.count('Solicitudes') + 1
            numero = f"{datetime.now().strftime('%Y')}-{count:06d}"

        # Actualizar el label con el número generado
        self.lbl_numero.config(text=numero, fg=COLORS['primary'])

        # Calcular totales
        subtotal = sum(p['precio'] for p in pruebas)
        desc_monto = subtotal * (desc_pct / 100)
        base = subtotal - desc_monto
        iva_monto = base * (iva_pct / 100)

        # Datos de la solicitud
        data = {
            'NumeroSolicitud': numero,
            'FechaSolicitud': datetime.now(),
            'HoraSolicitud': datetime.now().strftime('%H:%M:%S'),
            'PacienteID': self.pac_id_seleccionado,
            'MedicoID': self.med_map.get(self.combo_medico.get()) if hasattr(self, 'med_map') else None,
            'TipoServicio': self.combo_tipo.get() if hasattr(self, 'combo_tipo') else 'Particular',
            'EstadoSolicitud': self.combo_estado.get() if hasattr(self, 'combo_estado') else 'Pendiente',
            'DiagnosticoPresuntivo': self.txt_diagnostico.get('1.0', 'end').strip() if hasattr(self, 'txt_diagnostico') else '',
            'Observaciones': self.txt_observaciones.get('1.0', 'end').strip() if hasattr(self, 'txt_observaciones') else '',
            'PorcentajeDescuento': desc_pct,
            'MontoDescuento': desc_monto,
            'MontoIVA': iva_monto,
            'MontoNeto': base,
            'MontoTotal': total,
            'UsuarioRegistro': self.user.get('UsuarioID', 1),
            'FechaRegistro': datetime.now()
        }

        # Insertar solicitud
        db.insert('Solicitudes', data)

        # Obtener ID de la solicitud recién creada
        sol = db.query_one(f"SELECT SolicitudID FROM Solicitudes WHERE NumeroSolicitud='{numero}'")
        sol_id = sol['SolicitudID'] if sol else None

        if sol_id:
            # Insertar detalles de pruebas
            for prueba in pruebas:
                detalle = {
                    'SolicitudID': sol_id,
                    'PruebaID': prueba['id'],
                    'PrecioUnitario': prueba['precio'],
                    'Cantidad': 1,
                    'Subtotal': prueba['precio'],
                    'Estado': 'Pendiente'
                }
                db.insert('DetalleSolicitudes', detalle)

            # Generar documento según selección
            doc_mensaje = ""
            if tipo_doc == 'recibo':
                num_recibo = self._generar_recibo_legacy(sol_id, total)
                if num_recibo:
                    doc_mensaje = f"\n📄 Recibo generado: {num_recibo}"
                    self._generar_pdf_recibo(num_recibo, sol_id, total, pruebas)
            elif tipo_doc == 'factura':
                num_factura = self._generar_factura_legacy(sol_id, total, pruebas)
                if num_factura:
                    doc_mensaje = f"\n📄 Factura generada: {num_factura}"

        messagebox.showinfo(
            "Éxito",
            f"Solicitud {numero} guardada correctamente\n\n"
            f"Total: ${total:,.2f}\n"
            f"Abonado: ${abonado:,.2f}\n"
            f"Saldo: ${total - abonado:,.2f}{doc_mensaje}"
        )
        win.destroy()
        self.cargar_solicitudes()
        return True

    def _mostrar_dialogo_tipo_documento(self, parent, total):
        """Muestra diálogo para seleccionar tipo de documento (Recibo/Factura/Sin documento)"""
        # Si el diálogo del gestor está disponible, usarlo
        if GESTOR_SOLICITUDES_DISPONIBLE:
            try:
                dialogo = DialogoTipoDocumento(parent, total, puede_facturar=True)
                return dialogo.resultado
            except:
                pass  # Si falla, usar diálogo simple

        # Diálogo simple como fallback
        resultado = [None]  # Usar lista para poder modificar desde función interna

        dialog = tk.Toplevel(parent)
        dialog.title("Tipo de Documento")
        dialog.configure(bg='white')
        dialog.grab_set()
        dialog.focus_set()

        # Centrar
        ancho, alto = 450, 400
        x = (dialog.winfo_screenwidth() - ancho) // 2
        y = (dialog.winfo_screenheight() - alto) // 2
        dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        dialog.resizable(False, False)

        # Header
        header = tk.Frame(dialog, bg=COLORS['primary'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="Generar Documento de Pago",
                font=('Segoe UI', 12, 'bold'), bg=COLORS['primary'], fg='white').pack(pady=12)

        # Total
        total_frame = tk.Frame(dialog, bg='#e3f2fd')
        total_frame.pack(fill='x', padx=20, pady=15)
        tk.Label(total_frame, text="Total a Pagar:", font=('Segoe UI', 11), bg='#e3f2fd').pack(side='left', padx=10, pady=10)
        tk.Label(total_frame, text=f"${total:,.2f}", font=('Segoe UI', 16, 'bold'), bg='#e3f2fd', fg='#2e7d32').pack(side='right', padx=10, pady=10)

        # Opciones
        options_frame = tk.Frame(dialog, bg='white')
        options_frame.pack(fill='x', padx=20, pady=10)
        tk.Label(options_frame, text="Seleccione tipo de documento:", font=('Segoe UI', 10, 'bold'), bg='white').pack(anchor='w', pady=(0, 10))

        tipo_var = tk.StringVar(value='recibo')

        tk.Radiobutton(options_frame, text="📄 Recibo (Documento interno)",
                      variable=tipo_var, value='recibo', font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=3)
        tk.Radiobutton(options_frame, text="🧾 Factura Fiscal",
                      variable=tipo_var, value='factura', font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=3)
        tk.Radiobutton(options_frame, text="❌ Sin documento (Solo guardar solicitud)",
                      variable=tipo_var, value='sin_documento', font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=3)

        # Botones - usar side='bottom' para asegurar visibilidad
        btn_frame = tk.Frame(dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=20, pady=25)

        def aceptar():
            resultado[0] = tipo_var.get()
            dialog.destroy()

        def cancelar():
            resultado[0] = None
            dialog.destroy()

        btn_continuar = tk.Button(btn_frame, text="✅ GUARDAR", font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=25, pady=10,
                 cursor='hand2', command=aceptar)
        btn_continuar.pack(side='left', padx=10)

        btn_cancelar = tk.Button(btn_frame, text="❌ Cancelar", font=('Segoe UI', 11),
                 bg='#e74c3c', fg='white', relief='flat', padx=25, pady=10,
                 cursor='hand2', command=cancelar)
        btn_cancelar.pack(side='right', padx=10)

        dialog.wait_window()
        return resultado[0]

    def _generar_recibo_legacy(self, solicitud_id, total):
        """Genera un recibo para la solicitud (método legacy)"""
        try:
            # Verificar/crear tabla Recibos si no existe
            self._verificar_tabla_recibos()

            # Generar número de recibo
            anio = datetime.now().year
            result = db.query_one(f"SELECT MAX(NumeroRecibo) as Ultimo FROM Recibos WHERE NumeroRecibo LIKE 'REC-{anio}-%'")
            if result and result.get('Ultimo'):
                try:
                    numero = int(result['Ultimo'].split('-')[-1]) + 1
                except:
                    numero = 1
            else:
                numero = 1
            numero_recibo = f"REC-{anio}-{numero:06d}"

            # Obtener datos del paciente
            solicitud = db.query_one(f"SELECT PacienteID FROM Solicitudes WHERE SolicitudID = {solicitud_id}")
            paciente_id = solicitud.get('PacienteID') if solicitud else None

            # Insertar recibo
            forma_pago = self.combo_forma_pago.get() if hasattr(self, 'combo_forma_pago') else 'Efectivo'
            recibo_data = {
                'NumeroRecibo': numero_recibo,
                'SolicitudID': solicitud_id,
                'PacienteID': paciente_id,
                'FechaEmision': datetime.now(),
                'SubTotal': total,
                'Descuento': 0,
                'IVA': 0,
                'Total': total,
                'MontoAbonado': total,
                'FormaPago': forma_pago,
                'Observaciones': '',
                'UsuarioID': self.user.get('UsuarioID', 1),
                'Anulado': False
            }
            db.insert('Recibos', recibo_data)
            return numero_recibo
        except Exception as e:
            print(f"Error generando recibo: {e}")
            return None

    def _generar_pdf_recibo(self, numero_recibo, solicitud_id, total, pruebas_lista=None):
        """
        Genera un PDF con formato de ticket/recibo térmico.
        Incluye QR de verificación al final.
        """
        if not REPORTLAB_AVAILABLE:
            return

        try:
            from reportlab.lib.pagesizes import portrait
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
            from reportlab.lib import colors
            from reportlab.lib.units import cm, inch
            import tempfile, os

            # ── Tamaño ticket: ancho 80mm (226pt), alto variable ──────────────
            TICKET_W = 226  # 80 mm en puntos
            TICKET_H = 700  # alto generoso; se recorta automáticamente

            # ── Estilos ───────────────────────────────────────────────────────
            def estilo(name, **kw):
                base = dict(fontName='Helvetica', fontSize=7, leading=9,
                            spaceAfter=1, spaceBefore=1)
                base.update(kw)
                return ParagraphStyle(name, **base)

            s_lab    = estilo('lab',    fontSize=9,  fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=2)
            s_dir    = estilo('dir',    fontSize=6.5, alignment=TA_CENTER)
            s_titulo = estilo('titulo', fontSize=13, fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4, spaceBefore=4)
            s_label  = estilo('label',  fontSize=7,  fontName='Helvetica-Bold')
            s_valor  = estilo('valor',  fontSize=7)
            s_item_l = estilo('iteml',  fontSize=7)
            s_item_r = estilo('itemr',  fontSize=7,  alignment=TA_RIGHT)
            s_total  = estilo('total',  fontSize=8,  fontName='Helvetica-Bold', alignment=TA_RIGHT)
            s_qr_txt = estilo('qrtxt', fontSize=7,  fontName='Helvetica-Bold', alignment=TA_CENTER, spaceBefore=6)

            # ── Datos del laboratorio ─────────────────────────────────────────
            cfg = self.config_lab or {}
            nombre_lab  = cfg.get('NombreLaboratorio', 'LABORATORIO')
            direccion   = cfg.get('Direccion', '')
            telefono    = cfg.get('Telefono1', '')
            whatsapp    = cfg.get('WhatsApp', '')
            simbolo     = cfg.get('SimboloMoneda', '$')

            # ── Datos de la solicitud / paciente ──────────────────────────────
            sol = db.query_one(
                f"""SELECT s.NumeroSolicitud, s.FechaSolicitud,
                           p.NombreCompleto, p.Cedula, p.Telefono,
                           s.DiagnosticoPresuntivo
                    FROM Solicitudes s
                    LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                    WHERE s.SolicitudID = {solicitud_id}"""
            ) or {}

            num_muestra = sol.get('NumeroSolicitud', '')
            fecha_sol   = sol.get('FechaSolicitud', datetime.now())
            if hasattr(fecha_sol, 'strftime'):
                fecha_str = fecha_sol.strftime('%d/%m/%Y')
            else:
                fecha_str = str(fecha_sol)[:10]
            paciente    = sol.get('NombreCompleto', '')
            cedula      = sol.get('Cedula', '')
            telefono_p  = sol.get('Telefono', '')

            # ── Pruebas del detalle ───────────────────────────────────────────
            if pruebas_lista is None:
                filas_det = db.query(
                    f"""SELECT pr.NombrePrueba, ds.PrecioUnitario
                          FROM DetalleSolicitudes ds
                          LEFT JOIN Pruebas pr ON ds.PruebaID = pr.PruebaID
                         WHERE ds.SolicitudID = {solicitud_id}"""
                ) or []
            else:
                filas_det = [{'NombrePrueba': p.get('nombre', ''), 'PrecioUnitario': p.get('precio', 0)}
                             for p in pruebas_lista]

            # ── Armar story ───────────────────────────────────────────────────
            margen = 8
            story  = []

            # Encabezado laboratorio
            story.append(Paragraph(nombre_lab.upper(), s_lab))
            if direccion:
                story.append(Paragraph(direccion, s_dir))
            contacto_parts = []
            if telefono:
                contacto_parts.append(f"Teléfono: {telefono}")
            if whatsapp:
                contacto_parts.append(f"WhatsApp: {whatsapp}")
            if contacto_parts:
                story.append(Paragraph(" | ".join(contacto_parts), s_dir))

            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black, spaceAfter=3, spaceBefore=3))

            # Título
            story.append(Paragraph("RECIBO", s_titulo))

            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black, spaceAfter=3, spaceBefore=0))

            # Bloque de datos
            ancho_util = TICKET_W - 2 * margen
            col_etiq   = ancho_util * 0.38
            col_val    = ancho_util * 0.62

            def fila_dato(etiqueta, valor):
                return [Paragraph(etiqueta, s_label), Paragraph(str(valor), s_valor)]

            datos_tbl = [
                fila_dato("RECIBO N°:", numero_recibo),
                fila_dato("FECHA:",     fecha_str),
                fila_dato("N° MUESTRA:", num_muestra),
                fila_dato("C.I.:",      cedula),
                fila_dato("TELÉFONO:", telefono_p),
                fila_dato("PACIENTE:", paciente),
            ]
            tbl_datos = Table(datos_tbl, colWidths=[col_etiq, col_val])
            tbl_datos.setStyle(TableStyle([
                ('VALIGN',     (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING',(0, 0), (-1, -1), 0),
                ('RIGHTPADDING',(0,0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING',(0,0),(-1, -1), 1),
            ]))
            story.append(tbl_datos)

            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black, spaceAfter=3, spaceBefore=3))

            # Tabla de ítems
            col_desc  = ancho_util * 0.72
            col_precio= ancho_util * 0.28

            items_data = [[Paragraph('Descripción', s_label), Paragraph('Total', s_label)]]
            subtotal   = 0.0
            for fila in filas_det:
                nombre_item = fila.get('NombrePrueba') or fila.get('Descripcion', '')
                precio_item = float(fila.get('PrecioUnitario') or 0)
                subtotal   += precio_item
                items_data.append([
                    Paragraph(nombre_item, s_item_l),
                    Paragraph(f"{simbolo} {precio_item:,.2f}", s_item_r)
                ])

            tbl_items = Table(items_data, colWidths=[col_desc, col_precio])
            tbl_items.setStyle(TableStyle([
                ('LINEBELOW',   (0, 0), (-1, 0), 0.5, colors.black),
                ('VALIGN',      (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',(0, 0), (-1, -1), 0),
                ('TOPPADDING',  (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING',(0,0), (-1, -1), 2),
            ]))
            story.append(tbl_items)

            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black, spaceAfter=3, spaceBefore=3))

            # Totales
            totales_data = [
                [Paragraph('Exento:', s_item_l),  Paragraph(f"{simbolo} {subtotal:,.2f}", s_total)],
                [Paragraph('Sub-Total:', s_item_l),Paragraph(f"{simbolo} {subtotal:,.2f}", s_total)],
                [Paragraph('Total:', s_label),     Paragraph(f"{simbolo} {total:,.2f}", s_total)],
            ]
            tbl_totales = Table(totales_data, colWidths=[col_desc, col_precio])
            tbl_totales.setStyle(TableStyle([
                ('VALIGN',      (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING',(0, 0), (-1, -1), 0),
                ('TOPPADDING',  (0, 0), (-1, -1), 1),
                ('BOTTOMPADDING',(0,0), (-1, -1), 1),
                ('LINEABOVE',   (0, 2), (-1, 2), 0.8, colors.black),
            ]))
            story.append(tbl_totales)

            story.append(HRFlowable(width='100%', thickness=0.5, color=colors.black, spaceAfter=4, spaceBefore=4))

            # ── QR de verificación ────────────────────────────────────────────
            story.append(Paragraph("POR FAVOR ESCANEAR ESTE CODIGO QR", s_qr_txt))
            story.append(Spacer(1, 4))

            qr_agregado = False
            if FORMATO_PDF_DISPONIBLE and QRGenerator.disponible():
                try:
                    qr_rl = QRGenerator.generar_rl_image(
                        numero_recibo, fecha_str, paciente,
                        qr_size=1.4 * inch
                    )
                    if qr_rl:
                        # Centrar el QR con una tabla de una celda
                        tbl_qr = Table([[qr_rl]], colWidths=[ancho_util])
                        tbl_qr.setStyle(TableStyle([
                            ('ALIGN',  (0, 0), (-1, -1), 'CENTER'),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('LEFTPADDING',  (0, 0), (-1, -1), 0),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                            ('TOPPADDING',   (0, 0), (-1, -1), 0),
                            ('BOTTOMPADDING',(0, 0), (-1, -1), 0),
                        ]))
                        story.append(tbl_qr)
                        qr_agregado = True
                except Exception as eq:
                    print(f"QR recibo error: {eq}")

            if not qr_agregado:
                story.append(Paragraph(f"[{numero_recibo}]", s_qr_txt))

            story.append(Spacer(1, 6))

            # ── Generar PDF en temp ───────────────────────────────────────────
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf', prefix='recibo_')
            tmp.close()
            ruta_pdf = tmp.name

            doc = SimpleDocTemplate(
                ruta_pdf,
                pagesize=(TICKET_W, TICKET_H),
                leftMargin=margen, rightMargin=margen,
                topMargin=margen, bottomMargin=margen
            )
            doc.build(story)

            # Abrir PDF
            os.startfile(ruta_pdf)

        except Exception as e:
            print(f"Error generando PDF recibo: {e}")
            import traceback; traceback.print_exc()

    def _generar_factura_legacy(self, solicitud_id, total, pruebas):
        """Genera una factura para la solicitud (método legacy)"""
        try:
            # Generar número de factura
            anio = datetime.now().year
            result = db.query_one(f"SELECT MAX(NumeroFactura) as Ultimo FROM Facturas WHERE NumeroFactura LIKE 'FAC-{anio}-%'")
            if result and result.get('Ultimo'):
                try:
                    numero = int(result['Ultimo'].split('-')[-1]) + 1
                except:
                    numero = 1
            else:
                numero = 1
            numero_factura = f"FAC-{anio}-{numero:06d}"

            # Obtener datos del paciente
            solicitud = db.query_one(f"SELECT PacienteID FROM Solicitudes WHERE SolicitudID = {solicitud_id}")
            paciente_id = solicitud.get('PacienteID') if solicitud else None

            # Insertar factura
            factura_data = {
                'NumeroFactura': numero_factura,
                'FechaEmision': datetime.now(),
                'PacienteID': paciente_id,
                'SolicitudID': solicitud_id,
                'SubTotal': total,
                'MontoDescuento': 0,
                'TasaIVA': 16,
                'MontoIVA': 0,
                'MontoTotal': total,
                'EstadoPago': 'Pendiente',
                'MontoCobrado': 0,
                'SaldoPendiente': total,
                'UsuarioEmite': self.user.get('UsuarioID', 1),
                'FechaRegistro': datetime.now()
            }
            db.insert('Facturas', factura_data)

            # Obtener ID de la factura
            factura = db.query_one(f"SELECT FacturaID FROM Facturas WHERE NumeroFactura='{numero_factura}'")
            if factura:
                factura_id = factura['FacturaID']
                # Insertar detalles
                for prueba in pruebas:
                    detalle = {
                        'FacturaID': factura_id,
                        'PruebaID': prueba['id'],
                        'Descripcion': prueba.get('nombre', ''),
                        'Cantidad': 1,
                        'PrecioUnitario': prueba['precio'],
                        'SubTotal': prueba['precio']
                    }
                    db.insert('DetalleFacturas', detalle)

            return numero_factura
        except Exception as e:
            print(f"Error generando factura: {e}")
            return None

    def _verificar_tabla_recibos(self):
        """Verifica que existe la tabla Recibos y la crea si no existe"""
        try:
            # Intentar consultar la tabla
            db.query("SELECT TOP 1 ReciboID FROM Recibos")
        except:
            # La tabla no existe, crearla
            try:
                db.execute("""
                    CREATE TABLE Recibos (
                        ReciboID AUTOINCREMENT PRIMARY KEY,
                        NumeroRecibo TEXT(20),
                        SolicitudID INTEGER,
                        PacienteID INTEGER,
                        FechaEmision DATETIME,
                        SubTotal CURRENCY,
                        Descuento CURRENCY,
                        IVA CURRENCY,
                        Total CURRENCY,
                        MontoAbonado CURRENCY,
                        FormaPago TEXT(50),
                        Observaciones TEXT(255),
                        UsuarioID INTEGER,
                        Anulado BIT,
                        MotivoAnulacion TEXT(255),
                        FechaAnulacion DATETIME,
                        UsuarioAnula INTEGER
                    )
                """)
                print("Tabla Recibos creada exitosamente")
            except Exception as e:
                print(f"No se pudo crear tabla Recibos: {e}")

    def imprimir_comprobante(self):
        """Genera un comprobante simple de la solicitud"""
        if not self.pac_id_seleccionado:
            messagebox.showwarning("Aviso", "Complete la solicitud antes de imprimir")
            return

        # Obtener número del label o usar BORRADOR
        numero_texto = self.lbl_numero.cget('text')
        if numero_texto == "(Se generará al guardar)":
            numero = "BORRADOR - Sin guardar"
        else:
            numero = numero_texto

        # Calcular totales
        subtotal = sum(p['precio'] for p in self.sol_pruebas_seleccionadas)
        desc_pct = float(self.entry_descuento.get() or 0)
        desc_monto = subtotal * (desc_pct / 100)
        base = subtotal - desc_monto
        iva_pct = float(self.entry_iva.get() or 0)
        iva_monto = base * (iva_pct / 100)
        total = base + iva_monto
        abonado = float(self.entry_abonado.get() or 0)

        # Generar texto del comprobante
        comprobante = f"""
{'='*50}
        LABORATORIO CLÍNICO
           ANgesLAB
{'='*50}

Comprobante N°: {numero}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

Paciente: {self.entry_buscar_pac.get()}
{'='*50}

ESTUDIOS SOLICITADOS:
{'-'*50}
"""
        for p in self.sol_pruebas_seleccionadas:
            comprobante += f"  • {p['nombre'][:35]:35} ${p['precio']:>10,.2f}\n"

        comprobante += f"""
{'-'*50}
  Subtotal:                          ${subtotal:>10,.2f}
  Descuento ({desc_pct:.0f}%):                     -${desc_monto:>10,.2f}
  IVA ({iva_pct:.0f}%):                            ${iva_monto:>10,.2f}
{'='*50}
  TOTAL:                             ${total:>10,.2f}
  Abonado:                           ${abonado:>10,.2f}
  Saldo Pendiente:                   ${total - abonado:>10,.2f}
{'='*50}

Forma de Pago: {self.combo_forma_pago.get()}

        ¡Gracias por su preferencia!
"""

        # Mostrar comprobante
        win = tk.Toplevel(self.sol_win)
        win.title(f"Comprobante - {numero}")
        hacer_ventana_responsiva(win, 500, 600, min_ancho=400, min_alto=400)

        txt = tk.Text(win, font=('Courier New', 10), wrap='word')
        txt.pack(fill='both', expand=True, padx=10, pady=10)
        txt.insert('1.0', comprobante)
        txt.config(state='disabled')

        def guardar_txt():
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                initialfilename=f"Comprobante_{numero}.txt"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(comprobante)
                messagebox.showinfo("Éxito", f"Comprobante guardado en:\n{filename}")

        tk.Button(win, text="💾 Guardar como TXT", font=('Segoe UI', 10), bg=COLORS['primary'],
                 fg='white', relief='flat', command=guardar_txt).pack(pady=10)

    def ver_solicitud(self, event):
        """Muestra los detalles completos de una solicitud"""
        sel = self.tree_sol.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione una solicitud")
            return

        sol_id = self.tree_sol.item(sel[0])['values'][0]

        try:
            # Obtener datos de la solicitud
            solicitud = db.query_one(f"""
                SELECT s.*, p.Nombres & ' ' & p.Apellidos AS NombrePaciente,
                       p.NumeroDocumento, p.Telefono1,
                       m.Nombres & ' ' & m.Apellidos AS NombreMedico
                FROM (Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID)
                LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
                WHERE s.SolicitudID = {sol_id}
            """)

            if not solicitud:
                messagebox.showerror("Error", "Solicitud no encontrada")
                return

            # Obtener pruebas de la solicitud
            pruebas = db.query(f"""
                SELECT d.*, pr.NombrePrueba, pr.CodigoPrueba
                FROM DetalleSolicitudes d
                LEFT JOIN Pruebas pr ON d.PruebaID = pr.PruebaID
                WHERE d.SolicitudID = {sol_id}
            """)

            # Crear ventana de detalles
            win = tk.Toplevel(self.root)
            win.title(f"Solicitud: {solicitud.get('NumeroSolicitud', '')}")
            win.configure(bg='white')
            win.grab_set()

            # Hacer ventana responsiva
            hacer_ventana_responsiva(win, 700, 600, min_ancho=600, min_alto=500)

            # Header
            header = tk.Frame(win, bg=COLORS['primary'], height=60)
            header.pack(fill='x')
            header.pack_propagate(False)

            tk.Label(header, text=f"📋 Solicitud: {solicitud.get('NumeroSolicitud', '')}",
                    font=('Segoe UI', 14, 'bold'), bg=COLORS['primary'], fg='white').pack(pady=15)

            # Info del paciente
            info_frame = tk.Frame(win, bg='#f8f9fa')
            info_frame.pack(fill='x', padx=20, pady=15)

            fecha = solicitud.get('FechaSolicitud')
            fecha_str = fecha.strftime('%d/%m/%Y %H:%M') if fecha else 'N/A'

            tk.Label(info_frame, text=f"👤 Paciente: {solicitud.get('NombrePaciente', 'N/A')}",
                    font=('Segoe UI', 11), bg='#f8f9fa', anchor='w').pack(fill='x', padx=10, pady=2)
            tk.Label(info_frame, text=f"📄 Documento: {solicitud.get('NumeroDocumento', 'N/A')}  |  📞 Tel: {solicitud.get('Telefono1', 'N/A')}",
                    font=('Segoe UI', 10), bg='#f8f9fa', fg='#666', anchor='w').pack(fill='x', padx=10, pady=2)
            tk.Label(info_frame, text=f"📅 Fecha: {fecha_str}  |  🏷️ Estado: {solicitud.get('EstadoSolicitud', 'Pendiente')}",
                    font=('Segoe UI', 10), bg='#f8f9fa', fg='#666', anchor='w').pack(fill='x', padx=10, pady=2)
            if solicitud.get('NombreMedico'):
                tk.Label(info_frame, text=f"👨‍⚕️ Médico: {solicitud.get('NombreMedico')}",
                        font=('Segoe UI', 10), bg='#f8f9fa', fg='#666', anchor='w').pack(fill='x', padx=10, pady=2)

            # Lista de pruebas
            pruebas_header = tk.Frame(win, bg='white')
            pruebas_header.pack(fill='x', padx=20, pady=(15, 5))

            tk.Label(pruebas_header, text="🧪 Pruebas Solicitadas:", font=('Segoe UI', 11, 'bold'),
                    bg='white', anchor='w').pack(side='left')

            # Botones de modificar/eliminar pruebas (solo si solicitud es editable)
            estado_sol = solicitud.get('EstadoSolicitud', 'Pendiente')
            puede_editar_pruebas = estado_sol not in ('Completada', 'Entregada', 'Anulada')

            if puede_editar_pruebas:
                btn_eliminar_prueba = tk.Button(pruebas_header, text="🗑️ Eliminar Prueba(s)",
                    font=('Segoe UI', 9), bg=COLORS['danger'], fg='white',
                    relief='flat', padx=8, cursor='hand2', state='disabled')
                btn_eliminar_prueba.pack(side='right', padx=(5, 0))

                btn_modificar_prueba = tk.Button(pruebas_header, text="✏️ Modificar Precio",
                    font=('Segoe UI', 9), bg='#f39c12', fg='white',
                    relief='flat', padx=8, cursor='hand2', state='disabled')
                btn_modificar_prueba.pack(side='right', padx=(5, 0))

            tree_frame = tk.Frame(win, bg='white')
            tree_frame.pack(fill='both', expand=True, padx=20, pady=5)

            cols = ('Código', 'Prueba', 'Precio', 'Estado')
            tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=10,
                               selectmode='extended')
            for c in cols:
                tree.heading(c, text=c)
            tree.column('Código', width=80)
            tree.column('Prueba', width=300)
            tree.column('Precio', width=100)
            tree.column('Estado', width=100)

            vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=tree.yview)
            tree.configure(yscrollcommand=vsb.set)
            tree.pack(side='left', fill='both', expand=True)
            vsb.pack(side='right', fill='y')

            # Mapa de item_id -> datos de la prueba para referencia
            pruebas_map = {}
            for p in pruebas:
                precio = float(p.get('PrecioUnitario') or 0)
                iid = tree.insert('', 'end', values=(
                    p.get('CodigoPrueba', ''),
                    p.get('NombrePrueba', ''),
                    f"${precio:,.2f}",
                    p.get('Estado', 'Pendiente')
                ))
                pruebas_map[iid] = {
                    'detalle_id': p.get('DetalleID'),
                    'prueba_id': p.get('PruebaID'),
                    'codigo': p.get('CodigoPrueba', ''),
                    'nombre': p.get('NombrePrueba', ''),
                    'precio': precio,
                    'estado': p.get('Estado', 'Pendiente'),
                    'resultado': p.get('Resultado')
                }

            if puede_editar_pruebas:
                # Habilitar/deshabilitar botones según selección
                def on_tree_select(event):
                    sel = tree.selection()
                    if sel:
                        btn_eliminar_prueba.config(state='normal')
                        # Modificar solo si hay exactamente 1 seleccionada
                        if len(sel) == 1:
                            btn_modificar_prueba.config(state='normal')
                        else:
                            btn_modificar_prueba.config(state='disabled')
                    else:
                        btn_modificar_prueba.config(state='disabled')
                        btn_eliminar_prueba.config(state='disabled')

                tree.bind('<<TreeviewSelect>>', on_tree_select)

                def modificar_prueba_precio():
                    sel = tree.selection()
                    if not sel or len(sel) != 1:
                        return
                    item = sel[0]
                    data = pruebas_map.get(item)
                    if not data:
                        return

                    # Verificar permisos
                    if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                        if not self.gestor_solicitudes.tiene_permiso('modificar_pruebas'):
                            messagebox.showerror("Acceso Denegado", "No tiene permisos para modificar pruebas")
                            return

                    # Diálogo para nuevo precio
                    dlg = tk.Toplevel(win)
                    dlg.title("Modificar Precio")
                    dlg.configure(bg='white')
                    dlg.grab_set()
                    dlg.resizable(False, False)

                    # Centrar
                    dlg.update_idletasks()
                    x = win.winfo_x() + (win.winfo_width() // 2) - 175
                    y = win.winfo_y() + (win.winfo_height() // 2) - 80
                    dlg.geometry(f"350x160+{x}+{y}")

                    tk.Label(dlg, text=f"Prueba: {data['nombre']}", font=('Segoe UI', 10, 'bold'),
                            bg='white', wraplength=320).pack(padx=15, pady=(15, 5))
                    tk.Label(dlg, text=f"Precio actual: ${data['precio']:,.2f}", font=('Segoe UI', 10),
                            bg='white', fg='#666').pack(padx=15, pady=2)

                    precio_frame = tk.Frame(dlg, bg='white')
                    precio_frame.pack(padx=15, pady=5)
                    tk.Label(precio_frame, text="Nuevo precio: $", font=('Segoe UI', 10), bg='white').pack(side='left')
                    entry_precio = tk.Entry(precio_frame, font=('Segoe UI', 10), width=12, relief='flat',
                                           bg='#f8f9fa', highlightthickness=1, highlightbackground=COLORS['border'])
                    entry_precio.pack(side='left', ipady=3)
                    entry_precio.insert(0, f"{data['precio']:.2f}")
                    entry_precio.select_range(0, 'end')
                    entry_precio.focus_set()

                    def confirmar_modificar():
                        try:
                            nuevo_precio = float(entry_precio.get().replace(',', '.'))
                            if nuevo_precio < 0:
                                messagebox.showerror("Error", "El precio no puede ser negativo", parent=dlg)
                                return
                        except ValueError:
                            messagebox.showerror("Error", "Ingrese un precio válido", parent=dlg)
                            return

                        if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                            resultado = self.gestor_solicitudes.modificar_prueba_solicitud(
                                data['detalle_id'], sol_id, nuevo_precio)
                            if resultado['exito']:
                                # Actualizar treeview
                                tree.item(item, values=(data['codigo'], data['nombre'],
                                         f"${nuevo_precio:,.2f}", data['estado']))
                                pruebas_map[item]['precio'] = nuevo_precio
                                # Actualizar totales en la ventana
                                nuevo_total = resultado.get('nuevo_total')
                                if nuevo_total is not None:
                                    lbl_totales.config(text=f"TOTAL: ${nuevo_total:,.2f}")
                                dlg.destroy()
                                messagebox.showinfo("Éxito", resultado['mensaje'], parent=win)
                            else:
                                messagebox.showerror("Error", resultado['mensaje'], parent=dlg)
                        else:
                            # Fallback sin gestor
                            try:
                                db.update('DetalleSolicitudes', {
                                    'PrecioUnitario': nuevo_precio,
                                    'Subtotal': nuevo_precio
                                }, f"DetalleID = {data['detalle_id']}")
                                tree.item(item, values=(data['codigo'], data['nombre'],
                                         f"${nuevo_precio:,.2f}", data['estado']))
                                pruebas_map[item]['precio'] = nuevo_precio
                                dlg.destroy()
                                messagebox.showinfo("Éxito", "Precio modificado", parent=win)
                            except Exception as ex:
                                messagebox.showerror("Error", f"Error: {ex}", parent=dlg)

                    btn_dlg = tk.Frame(dlg, bg='white')
                    btn_dlg.pack(fill='x', padx=15, pady=10)
                    tk.Button(btn_dlg, text="Guardar", font=('Segoe UI', 9, 'bold'),
                             bg=COLORS['success'], fg='white', relief='flat', padx=15, pady=4,
                             cursor='hand2', command=confirmar_modificar).pack(side='left', padx=5)
                    tk.Button(btn_dlg, text="Cancelar", font=('Segoe UI', 9),
                             bg='#95a5a6', fg='white', relief='flat', padx=15, pady=4,
                             cursor='hand2', command=dlg.destroy).pack(side='right', padx=5)

                    entry_precio.bind('<Return>', lambda e: confirmar_modificar())

                def eliminar_pruebas_seleccionadas():
                    sel = tree.selection()
                    if not sel:
                        return

                    # Verificar permisos
                    if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                        if not self.gestor_solicitudes.tiene_permiso('eliminar_pruebas'):
                            messagebox.showerror("Acceso Denegado", "No tiene permisos para eliminar pruebas")
                            return

                    # Obtener datos de las pruebas seleccionadas
                    pruebas_a_eliminar = []
                    nombres = []
                    for item in sel:
                        data = pruebas_map.get(item)
                        if data:
                            pruebas_a_eliminar.append(data)
                            nombres.append(f"  - {data['nombre']}")

                    if not pruebas_a_eliminar:
                        return

                    # Verificar que no se eliminen todas
                    total_pruebas = len(tree.get_children())
                    if len(pruebas_a_eliminar) >= total_pruebas:
                        messagebox.showwarning("Aviso",
                            "No se pueden eliminar todas las pruebas.\nLa solicitud debe tener al menos una prueba.",
                            parent=win)
                        return

                    # Confirmar
                    msg = f"¿Eliminar {len(pruebas_a_eliminar)} prueba(s) de la solicitud?\n\n"
                    msg += "\n".join(nombres)
                    msg += "\n\nEsta acción no se puede deshacer."

                    if not messagebox.askyesno("Confirmar Eliminación", msg, icon='warning', parent=win):
                        return

                    detalle_ids = [p['detalle_id'] for p in pruebas_a_eliminar]

                    if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                        resultado = self.gestor_solicitudes.eliminar_pruebas_solicitud(detalle_ids, sol_id)
                        if resultado['exito']:
                            # Eliminar del treeview
                            for item in sel:
                                tree.delete(item)
                                if item in pruebas_map:
                                    del pruebas_map[item]
                            # Actualizar totales
                            nuevo_total = resultado.get('nuevo_total')
                            if nuevo_total is not None:
                                lbl_totales.config(text=f"TOTAL: ${nuevo_total:,.2f}")
                            btn_modificar_prueba.config(state='disabled')
                            btn_eliminar_prueba.config(state='disabled')
                            messagebox.showinfo("Éxito", resultado['mensaje'], parent=win)
                        else:
                            messagebox.showerror("Error", resultado['mensaje'], parent=win)
                    else:
                        # Fallback sin gestor
                        try:
                            for did in detalle_ids:
                                db.execute(f"DELETE FROM DetalleSolicitudes WHERE DetalleID = {did}")
                            for item in sel:
                                tree.delete(item)
                                if item in pruebas_map:
                                    del pruebas_map[item]
                            btn_modificar_prueba.config(state='disabled')
                            btn_eliminar_prueba.config(state='disabled')
                            messagebox.showinfo("Éxito", f"Se eliminaron {len(detalle_ids)} prueba(s)", parent=win)
                        except Exception as ex:
                            messagebox.showerror("Error", f"Error: {ex}", parent=win)

                btn_modificar_prueba.config(command=modificar_prueba_precio)
                btn_eliminar_prueba.config(command=eliminar_pruebas_seleccionadas)

                # Doble click para modificar precio
                tree.bind('<Double-1>', lambda e: modificar_prueba_precio())

            # Totales
            total_frame = tk.Frame(win, bg='#e8f5e9')
            total_frame.pack(fill='x', padx=20, pady=10)

            total = float(solicitud.get('MontoTotal') or 0)
            descuento = float(solicitud.get('MontoDescuento') or 0)
            iva = float(solicitud.get('MontoIVA') or 0)

            lbl_totales = tk.Label(total_frame,
                    text=f"Descuento: ${descuento:,.2f}  |  IVA: ${iva:,.2f}  |  TOTAL: ${total:,.2f}",
                    font=('Segoe UI', 12, 'bold'), bg='#e8f5e9', fg='#2e7d32')
            lbl_totales.pack(pady=10)

            # Botones
            btn_frame = tk.Frame(win, bg='white')
            btn_frame.pack(fill='x', padx=20, pady=15)

            tk.Button(btn_frame, text="✏️ Editar Solicitud", font=('Segoe UI', 10),
                     bg=COLORS['primary'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=lambda: [win.destroy(), self.editar_solicitud(sol_id)]).pack(side='left', padx=5)

            tk.Button(btn_frame, text="🗑️ Eliminar Solicitud", font=('Segoe UI', 10),
                     bg=COLORS['danger'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=lambda: [win.destroy(), self.eliminar_solicitud(sol_id)]).pack(side='left', padx=5)

            tk.Button(btn_frame, text="Cerrar", font=('Segoe UI', 10),
                     bg='#95a5a6', fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=win.destroy).pack(side='right', padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar solicitud: {e}")

    def _mostrar_menu_solicitud(self, event):
        """Muestra el menú contextual de solicitudes"""
        # Seleccionar el item bajo el cursor
        iid = self.tree_sol.identify_row(event.y)
        if iid:
            self.tree_sol.selection_set(iid)
            self.menu_solicitud.post(event.x_root, event.y_root)

    def editar_solicitud_seleccionada(self):
        """Edita la solicitud seleccionada en el treeview"""
        sel = self.tree_sol.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione una solicitud para editar")
            return

        sol_id = self.tree_sol.item(sel[0])['values'][0]
        self.editar_solicitud(sol_id)

    def editar_solicitud(self, solicitud_id):
        """Abre la ventana de edición de una solicitud existente"""
        try:
            # Verificar permisos
            if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                if not self.gestor_solicitudes.tiene_permiso('editar_solicitud'):
                    messagebox.showerror("Acceso Denegado", "No tiene permisos para editar solicitudes")
                    return

            # Obtener datos de la solicitud
            solicitud = db.query_one(f"""
                SELECT s.*, p.PacienteID, p.Nombres, p.Apellidos, p.NumeroDocumento, p.Telefono1
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.SolicitudID = {solicitud_id}
            """)

            if not solicitud:
                messagebox.showerror("Error", "Solicitud no encontrada")
                return

            # Verificar si la solicitud puede editarse
            estado = solicitud.get('EstadoSolicitud', '')
            if estado in ('Completada', 'Entregada', 'Anulada'):
                messagebox.showwarning("Aviso", f"No se puede editar una solicitud con estado '{estado}'")
                return

            # Crear ventana de edición
            win = tk.Toplevel(self.root)
            win.title(f"Editar Solicitud: {solicitud.get('NumeroSolicitud', '')}")
            win.configure(bg='white')
            win.grab_set()

            hacer_ventana_responsiva(win, 600, 500, min_ancho=500, min_alto=400)

            # Header
            header = tk.Frame(win, bg='#f39c12', height=50)
            header.pack(fill='x')
            header.pack_propagate(False)

            tk.Label(header, text=f"✏️ Editar Solicitud: {solicitud.get('NumeroSolicitud', '')}",
                    font=('Segoe UI', 12, 'bold'), bg='#f39c12', fg='white').pack(pady=12)

            # Contenido
            content = tk.Frame(win, bg='white')
            content.pack(fill='both', expand=True, padx=20, pady=15)

            # Info del paciente (solo lectura)
            nombre_pac = f"{solicitud.get('Nombres', '')} {solicitud.get('Apellidos', '')}".strip()
            tk.Label(content, text=f"👤 Paciente: {nombre_pac}", font=('Segoe UI', 10),
                    bg='white', fg='#666').pack(anchor='w', pady=5)

            # Estado
            tk.Label(content, text="Estado de la Solicitud:", font=('Segoe UI', 10, 'bold'),
                    bg='white').pack(anchor='w', pady=(15, 5))

            estado_var = tk.StringVar(value=solicitud.get('EstadoSolicitud', 'Pendiente'))
            combo_estado = ttk.Combobox(content, textvariable=estado_var, font=('Segoe UI', 10),
                                        state='readonly', width=30)
            combo_estado['values'] = ['Pendiente', 'En Proceso', 'Completada', 'Entregada', 'Anulada']
            combo_estado.pack(anchor='w', pady=5)

            # Observaciones
            tk.Label(content, text="Observaciones:", font=('Segoe UI', 10, 'bold'),
                    bg='white').pack(anchor='w', pady=(15, 5))

            txt_obs = tk.Text(content, font=('Segoe UI', 10), height=4, wrap='word',
                             relief='flat', bg='#f8f9fa', highlightthickness=1,
                             highlightbackground=COLORS['border'])
            txt_obs.pack(fill='x', pady=5)
            txt_obs.insert('1.0', solicitud.get('Observaciones', '') or '')

            # Diagnóstico
            tk.Label(content, text="Diagnóstico Presuntivo:", font=('Segoe UI', 10, 'bold'),
                    bg='white').pack(anchor='w', pady=(15, 5))

            txt_diag = tk.Text(content, font=('Segoe UI', 10), height=3, wrap='word',
                              relief='flat', bg='#f8f9fa', highlightthickness=1,
                              highlightbackground=COLORS['border'])
            txt_diag.pack(fill='x', pady=5)
            txt_diag.insert('1.0', solicitud.get('DiagnosticoPresuntivo', '') or '')

            def guardar_cambios():
                try:
                    nuevo_estado = estado_var.get()
                    nuevas_obs = txt_obs.get('1.0', 'end').strip()
                    nuevo_diag = txt_diag.get('1.0', 'end').strip()

                    # Actualizar en base de datos
                    db.update('Solicitudes', {
                        'EstadoSolicitud': nuevo_estado,
                        'Observaciones': nuevas_obs,
                        'DiagnosticoPresuntivo': nuevo_diag
                    }, f"SolicitudID = {solicitud_id}")

                    messagebox.showinfo("Éxito", "Solicitud actualizada correctamente")
                    win.destroy()
                    self.cargar_solicitudes()

                except Exception as e:
                    messagebox.showerror("Error", f"Error al guardar cambios: {e}")

            # Botones
            btn_frame = tk.Frame(win, bg='white')
            btn_frame.pack(fill='x', padx=20, pady=15)

            tk.Button(btn_frame, text="💾 Guardar Cambios", font=('Segoe UI', 10, 'bold'),
                     bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=guardar_cambios).pack(side='left', padx=5)

            tk.Button(btn_frame, text="Cancelar", font=('Segoe UI', 10),
                     bg='#95a5a6', fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=win.destroy).pack(side='right', padx=5)

        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir editor: {e}")

    def eliminar_solicitud_seleccionada(self):
        """Elimina la solicitud seleccionada en el treeview"""
        sel = self.tree_sol.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione una solicitud para eliminar")
            return

        sol_id = self.tree_sol.item(sel[0])['values'][0]
        numero = self.tree_sol.item(sel[0])['values'][1]
        self.eliminar_solicitud(sol_id, numero)

    def eliminar_solicitud(self, solicitud_id, numero_solicitud=None):
        """Elimina una solicitud con confirmación"""
        try:
            # Verificar permisos
            if self.gestor_solicitudes and GESTOR_SOLICITUDES_DISPONIBLE:
                if not self.gestor_solicitudes.tiene_permiso('anular_documento'):
                    messagebox.showerror("Acceso Denegado", "No tiene permisos para eliminar solicitudes.\nSolo los administradores pueden eliminar.")
                    return

            # Obtener datos de la solicitud si no se pasó el número
            if not numero_solicitud:
                sol = db.query_one(f"SELECT NumeroSolicitud FROM Solicitudes WHERE SolicitudID = {solicitud_id}")
                numero_solicitud = sol.get('NumeroSolicitud', f'ID:{solicitud_id}') if sol else f'ID:{solicitud_id}'

            # Verificar si tiene documentos asociados (facturas, recibos)
            facturas = db.query(f"SELECT FacturaID FROM Facturas WHERE SolicitudID = {solicitud_id}")
            recibos = []
            try:
                recibos = db.query(f"SELECT ReciboID FROM Recibos WHERE SolicitudID = {solicitud_id}")
            except:
                pass  # Tabla puede no existir

            advertencia = ""
            if facturas:
                advertencia += f"\n⚠️ Tiene {len(facturas)} factura(s) asociada(s)"
            if recibos:
                advertencia += f"\n⚠️ Tiene {len(recibos)} recibo(s) asociado(s)"

            # Confirmar eliminación
            mensaje = f"¿Está seguro de eliminar la solicitud {numero_solicitud}?{advertencia}\n\nEsta acción no se puede deshacer."

            if not messagebox.askyesno("Confirmar Eliminación", mensaje, icon='warning'):
                return

            # Si tiene documentos, preguntar si anular o eliminar
            if facturas or recibos:
                accion = messagebox.askyesnocancel(
                    "Documentos Asociados",
                    "La solicitud tiene documentos asociados.\n\n"
                    "¿Desea ANULAR la solicitud (recomendado) en lugar de eliminarla?\n\n"
                    "• Sí = Anular (mantiene historial)\n"
                    "• No = Eliminar todo\n"
                    "• Cancelar = No hacer nada"
                )

                if accion is None:  # Cancelar
                    return
                elif accion:  # Sí = Anular
                    db.update('Solicitudes', {
                        'EstadoSolicitud': 'Anulada',
                        'Observaciones': f"Anulada por usuario el {datetime.now().strftime('%d/%m/%Y %H:%M')}"
                    }, f"SolicitudID = {solicitud_id}")
                    messagebox.showinfo("Éxito", f"Solicitud {numero_solicitud} anulada correctamente")
                    self.cargar_solicitudes()
                    return

            # Eliminar detalles primero
            db.execute(f"DELETE FROM DetalleSolicitudes WHERE SolicitudID = {solicitud_id}")

            # Eliminar documentos asociados si existen
            try:
                db.execute(f"DELETE FROM DetalleFacturas WHERE FacturaID IN (SELECT FacturaID FROM Facturas WHERE SolicitudID = {solicitud_id})")
                db.execute(f"DELETE FROM Facturas WHERE SolicitudID = {solicitud_id}")
            except:
                pass

            try:
                db.execute(f"DELETE FROM Recibos WHERE SolicitudID = {solicitud_id}")
            except:
                pass

            # Eliminar la solicitud
            db.execute(f"DELETE FROM Solicitudes WHERE SolicitudID = {solicitud_id}")

            messagebox.showinfo("Éxito", f"Solicitud {numero_solicitud} eliminada correctamente")
            self.cargar_solicitudes()

        except Exception as e:
            messagebox.showerror("Error", f"Error al eliminar solicitud: {e}")

    # ============================================================
    # RESULTADOS
    # ============================================================

    def show_resultados(self):
        self.clear_content()
        self.set_title("📝 Captura y Validación de Resultados")

        # Frame principal directo en content (sin scrollable wrapper)
        main_frame = tk.Frame(self.content, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True)

        # COLUMNA IZQUIERDA - Búsqueda y lista de solicitudes
        left_frame = tk.Frame(main_frame, bg='white', width=350)
        left_frame.pack(side='left', fill='y', padx=(0, 10), pady=0)
        left_frame.pack_propagate(False)

        # Búsqueda
        search_frame = tk.Frame(left_frame, bg='white')
        search_frame.pack(fill='x', padx=15, pady=15)

        tk.Label(search_frame, text="🔍 Buscar Solicitud:", font=('Segoe UI', 11, 'bold'),
                bg='white').pack(anchor='w', pady=(0, 8))

        entry_frame = tk.Frame(search_frame, bg='white')
        entry_frame.pack(fill='x')

        self.entry_buscar_res = tk.Entry(entry_frame, font=('Segoe UI', 11), relief='flat',
                                        bg='#f8f9fa', highlightthickness=1, highlightbackground=COLORS['border'])
        self.entry_buscar_res.pack(side='left', fill='x', expand=True, ipady=6)
        self.entry_buscar_res.bind('<Return>', lambda e: self.buscar_solicitudes_resultado())
        self.entry_buscar_res.bind('<KeyRelease>', lambda e: self.buscar_solicitudes_resultado())

        # Lista de solicitudes pendientes
        tk.Label(left_frame, text="📋 Solicitudes Pendientes:", font=('Segoe UI', 10, 'bold'),
                bg='white').pack(anchor='w', padx=15, pady=(10, 5))

        list_frame = tk.Frame(left_frame, bg='white')
        list_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        cols = ('N° Solicitud', 'Paciente', 'Estado')
        self.tree_sol_res = ttk.Treeview(list_frame, columns=cols, show='headings', height=15)
        self.tree_sol_res.heading('N° Solicitud', text='N° Solicitud')
        self.tree_sol_res.heading('Paciente', text='Paciente')
        self.tree_sol_res.heading('Estado', text='Estado')
        self.tree_sol_res.column('N° Solicitud', width=100)
        self.tree_sol_res.column('Paciente', width=130)
        self.tree_sol_res.column('Estado', width=80)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_sol_res.yview)
        self.tree_sol_res.configure(yscrollcommand=vsb.set)
        self.tree_sol_res.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.tree_sol_res.bind('<<TreeviewSelect>>', self.cargar_pruebas_resultado)

        # Cargar solicitudes pendientes
        self.cargar_solicitudes_pendientes()

        # COLUMNA DERECHA - Detalle y captura de resultados
        right_frame = tk.Frame(main_frame, bg='white')
        right_frame.pack(side='left', fill='both', expand=True)

        # Header de información
        self.info_res_frame = tk.Frame(right_frame, bg=COLORS['primary'])
        self.info_res_frame.pack(fill='x')

        self.lbl_info_sol = tk.Label(self.info_res_frame, text="Seleccione una solicitud para capturar resultados",
                                     font=('Segoe UI', 12), bg=COLORS['primary'], fg='white')
        self.lbl_info_sol.pack(pady=15)

        # Frame para la tabla de pruebas y resultados
        self.pruebas_res_frame = tk.Frame(right_frame, bg='white')
        self.pruebas_res_frame.pack(fill='both', expand=True, padx=15, pady=15)

        # Instrucciones iniciales
        tk.Label(self.pruebas_res_frame, text="👆 Seleccione una solicitud de la lista\npara ver y capturar los resultados",
                font=('Segoe UI', 12), bg='white', fg=COLORS['text_light'], justify='center').pack(pady=100)

    def cargar_solicitudes_pendientes(self):
        """Carga las solicitudes pendientes de resultados"""
        for item in self.tree_sol_res.get_children():
            self.tree_sol_res.delete(item)

        try:
            solicitudes = db.query("""
                SELECT TOP 100 s.SolicitudID, s.NumeroSolicitud,
                       p.Nombres & ' ' & p.Apellidos AS Paciente,
                       s.EstadoSolicitud
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.EstadoSolicitud IN ('Pendiente', 'En Proceso')
                ORDER BY s.SolicitudID DESC
            """)

            self.sol_res_map = {}
            for s in solicitudes:
                iid = self.tree_sol_res.insert('', 'end', values=(
                    s['NumeroSolicitud'] or '',
                    (s['Paciente'] or 'N/A')[:20],
                    s['EstadoSolicitud'] or 'Pendiente'
                ))
                self.sol_res_map[iid] = s['SolicitudID']
        except Exception as e:
            print(f"Error cargando solicitudes: {e}")

    def buscar_solicitudes_resultado(self):
        """Filtra solicitudes por número o paciente"""
        filtro = self.entry_buscar_res.get().strip()

        for item in self.tree_sol_res.get_children():
            self.tree_sol_res.delete(item)

        where = "WHERE 1=1"
        if filtro:
            where = f"WHERE (s.NumeroSolicitud LIKE '%{filtro}%' OR p.Nombres LIKE '%{filtro}%' OR p.Apellidos LIKE '%{filtro}%')"

        try:
            solicitudes = db.query(f"""
                SELECT TOP 100 s.SolicitudID, s.NumeroSolicitud,
                       p.Nombres & ' ' & p.Apellidos AS Paciente,
                       s.EstadoSolicitud
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                {where}
                ORDER BY s.SolicitudID DESC
            """)

            self.sol_res_map = {}
            for s in solicitudes:
                iid = self.tree_sol_res.insert('', 'end', values=(
                    s['NumeroSolicitud'] or '',
                    (s['Paciente'] or 'N/A')[:20],
                    s['EstadoSolicitud'] or 'Pendiente'
                ))
                self.sol_res_map[iid] = s['SolicitudID']
        except Exception as e:
            print(f"Error buscando: {e}")

    def cargar_pruebas_resultado(self, event=None):
        """Carga las pruebas de la solicitud con sus parametros para capturar resultados"""
        sel = self.tree_sol_res.selection()
        if not sel:
            return

        sol_id = self.sol_res_map.get(sel[0])
        if not sol_id:
            return

        # Limpiar frame de pruebas
        for w in self.pruebas_res_frame.winfo_children():
            w.destroy()

        try:
            # Obtener info de la solicitud
            sol = db.query_one(f"""
                SELECT s.*, p.Nombres & ' ' & p.Apellidos AS Paciente,
                       p.FechaNacimiento, p.Sexo
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.SolicitudID = {sol_id}
            """)

            if not sol:
                return

            # Actualizar header
            edad = ""
            edad_valor = 0
            sexo_valor = sol.get('Sexo') or 'M'
            if sol.get('FechaNacimiento'):
                try:
                    fn = sol['FechaNacimiento']
                    hoy = datetime.now()
                    edad_valor = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
                    edad = f" | {edad_valor} anos"
                except:
                    pass

            sexo = f" | {'M' if sexo_valor == 'M' else 'F'}" if sexo_valor else ""

            self.lbl_info_sol.config(text=f"Solicitud: {sol['NumeroSolicitud']} | Paciente: {sol['Paciente'] or 'N/A'}{edad}{sexo}")

            # Guardar ID de solicitud actual
            self.sol_id_resultado = sol_id

            # Obtener pruebas de la solicitud
            pruebas = db.query(f"""
                SELECT d.DetalleID, d.PruebaID, d.Estado, d.Resultado, d.Observaciones,
                       p.CodigoPrueba, p.NombrePrueba
                FROM DetalleSolicitudes d
                LEFT JOIN Pruebas p ON d.PruebaID = p.PruebaID
                WHERE d.SolicitudID = {sol_id}
                ORDER BY p.NombrePrueba
            """)

            if not pruebas:
                tk.Label(self.pruebas_res_frame, text="No hay pruebas registradas para esta solicitud",
                        font=('Segoe UI', 11), bg='white', fg=COLORS['text_light']).pack(pady=50)
                return

            # Frame con scroll para las pruebas
            canvas = tk.Canvas(self.pruebas_res_frame, bg='white', highlightthickness=0)
            scrollbar = ttk.Scrollbar(self.pruebas_res_frame, orient='vertical', command=canvas.yview)
            scroll_frame = tk.Frame(canvas, bg='white')

            scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
            canvas.configure(yscrollcommand=scrollbar.set)

            # Ajustar ancho del frame interno al ancho del canvas
            def _on_canvas_configure(event):
                canvas.itemconfig(canvas_window, width=event.width)
            canvas.bind('<Configure>', _on_canvas_configure)

            canvas.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            # Scroll con rueda
            def on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
            canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

            # Guardar referencias a los campos de parametros
            self.resultado_entries = {}
            self.parametro_entries = {}

            for prueba in pruebas:
                detalle_id = prueba['DetalleID']
                prueba_id = prueba['PruebaID']

                # Frame contenedor de la prueba
                prueba_frame = tk.Frame(scroll_frame, bg='white', bd=1, relief='solid')
                prueba_frame.pack(fill='x', pady=5, padx=5)

                # Header de la prueba
                header_prueba = tk.Frame(prueba_frame, bg='#1976d2')
                header_prueba.pack(fill='x')

                tk.Label(header_prueba, text=f"  {prueba['CodigoPrueba']} - {prueba['NombrePrueba']}",
                        font=('Segoe UI', 10, 'bold'), bg='#1976d2', fg='white',
                        anchor='w').pack(side='left', fill='x', expand=True, pady=5, padx=5)

                estado_prueba = prueba.get('Estado') or 'Pendiente'
                color_estado = '#4caf50' if estado_prueba == 'Validado' else '#ff9800' if estado_prueba == 'Capturado' else '#9e9e9e'
                tk.Label(header_prueba, text=estado_prueba, font=('Segoe UI', 9, 'bold'),
                        bg=color_estado, fg='white', padx=10).pack(side='right', pady=5, padx=5)

                # =============================================================
                # FORMULARIO ESPECIAL: PRUEBA DE TOLERANCIA A LA GLUCOSA (GTT)
                # Si la prueba es GTT, mostrar panel especial en lugar del form
                # generico, con checkboxes de tiempos y carga glucosada.
                # =============================================================
                if GTT_DISPONIBLE and es_prueba_gtt(prueba):
                    gtt_panel = tk.Frame(prueba_frame, bg='#f3f8ff',
                                         highlightbackground='#90caf9', highlightthickness=1)
                    gtt_panel.pack(fill='x', padx=5, pady=8)

                    gtt_inner = tk.Frame(gtt_panel, bg='#f3f8ff')
                    gtt_inner.pack(padx=12, pady=10)

                    tk.Label(gtt_inner,
                             text="📊 Esta prueba utiliza el formulario especializado de\n"
                                  "     Curva de Glucemia con gráfica de tendencia.",
                             font=('Segoe UI', 9), bg='#f3f8ff',
                             fg='#1565c0', justify='left').pack(side='left', padx=(0, 20))

                    btn_gtt_frame = tk.Frame(gtt_panel, bg='#f3f8ff')
                    btn_gtt_frame.pack(pady=(0, 8))

                    def _abrir_gtt(did=detalle_id):
                        def _on_guardado():
                            self.cargar_pruebas_resultado()
                        abrir_formulario_gtt(self.root, db, did, on_guardado=_on_guardado)

                    tk.Button(btn_gtt_frame,
                              text="📈 Abrir Formulario GTT",
                              font=('Segoe UI', 10, 'bold'),
                              bg='#1565c0', fg='white', relief='flat',
                              padx=16, pady=7, cursor='hand2',
                              command=_abrir_gtt).pack(side='left', padx=6)

                    # Si ya tiene datos capturados, mostrar boton de imprimir
                    if estado_prueba in ('Capturado', 'Validado'):
                        def _imprimir_gtt(did=detalle_id):
                            opcion = mostrar_opciones_impresion_gtt(self.root)
                            if opcion is None:
                                return
                            incluir = (opcion == 'con_grafica')
                            config_lab = None
                            ruta_logo = None
                            bioanalista = None
                            if self.config_administrativa:
                                config_lab = self.config_administrativa.obtener_configuracion()
                                ruta_logo = self.config_administrativa.obtener_ruta_logo()
                            # Obtener bioanalista de area Quimica (AreaID=2)
                            try:
                                bioanalista = db.query_one(
                                    "SELECT * FROM Bioanalistas WHERE AreaID = 2 AND Activo = True"
                                )
                            except Exception:
                                pass
                            import tempfile
                            temp_dir = tempfile.gettempdir()
                            fname = os.path.join(temp_dir, f"GTT_{did}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")
                            try:
                                ok = generar_pdf_gtt(
                                    db=db, detalle_id=did, filename=fname,
                                    config_lab=config_lab, ruta_logo=ruta_logo,
                                    bioanalista=bioanalista,
                                    incluir_grafica=incluir
                                )
                                if ok:
                                    import subprocess
                                    subprocess.Popen([fname], shell=True)
                            except Exception as exc:
                                messagebox.showerror("Error PDF GTT",
                                                     f"No se pudo generar el PDF:\n{exc}",
                                                     parent=self.root)

                        tk.Button(btn_gtt_frame,
                                  text="🖨 Imprimir / PDF",
                                  font=('Segoe UI', 10),
                                  bg='#2e7d32', fg='white', relief='flat',
                                  padx=14, pady=7, cursor='hand2',
                                  command=_imprimir_gtt).pack(side='left', padx=6)

                    continue  # No cargar el formulario generico para GTT
                # =============================================================

                # Obtener parametros de la prueba con formula de calculo, seccion y tipo
                parametros = db.query(f"""
                    SELECT pp.ParametroID, pp.Secuencia,
                           par.NombreParametro, par.UnidadID, par.Observaciones as ValorRef,
                           par.FormulaCalculo, par.Seccion, par.TipoResultado
                    FROM ParametrosPrueba pp
                    INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID
                    WHERE pp.PruebaID = {prueba_id}
                    ORDER BY pp.Secuencia
                """)

                if parametros:
                    # Verificar si hay secciones definidas
                    tiene_secciones = any(p.get('Seccion') for p in parametros)

                    if not tiene_secciones:
                        # Header de parametros (sin secciones)
                        param_header = tk.Frame(prueba_frame, bg='#e3f2fd')
                        param_header.pack(fill='x')

                        tk.Label(param_header, text="Parámetro", font=('Segoe UI', 8, 'bold'),
                                bg='#e3f2fd', width=22, anchor='w').pack(side='left', padx=5, pady=3)
                        tk.Label(param_header, text="Resultado", font=('Segoe UI', 8, 'bold'),
                                bg='#e3f2fd', width=14).pack(side='left', padx=5, pady=3)
                        tk.Label(param_header, text="Unidad", font=('Segoe UI', 8, 'bold'),
                                bg='#e3f2fd', width=10).pack(side='left', padx=5, pady=3)
                        tk.Label(param_header, text="Valor de Referencia", font=('Segoe UI', 8, 'bold'),
                                bg='#e3f2fd', width=28, fg='#1565c0').pack(side='left', padx=5, pady=3)

                    self.parametro_entries[detalle_id] = []
                    seccion_actual = None

                    for param in parametros:
                        # Mostrar encabezado de seccion si cambia
                        seccion = param.get('Seccion') or ''
                        if tiene_secciones and seccion and seccion != seccion_actual:
                            seccion_actual = seccion
                            seccion_header = tk.Frame(prueba_frame, bg='#455a64')
                            seccion_header.pack(fill='x', pady=(5, 0))
                            tk.Label(seccion_header, text=f"  {seccion}", font=('Segoe UI', 9, 'bold'),
                                    bg='#455a64', fg='white', anchor='w').pack(fill='x', pady=3)
                        param_id = param['ParametroID']
                        formula = param.get('FormulaCalculo') or ''
                        es_calculado = bool(formula and formula.strip())

                        # Obtener unidad
                        unidad_texto = ""
                        if param.get('UnidadID'):
                            unidad = db.query_one(f"SELECT Simbolo FROM Unidades WHERE UnidadID = {param['UnidadID']}")
                            if unidad:
                                unidad_texto = unidad.get('Simbolo') or ''

                        # Obtener valor de referencia
                        valor_ref = param.get('ValorRef') or ''

                        # Obtener resultado guardado si existe
                        resultado_guardado = db.query_one(f"""
                            SELECT Valor FROM ResultadosParametros
                            WHERE DetalleID = {detalle_id} AND ParametroID = {param_id}
                        """)

                        # Fila del parametro
                        bg_row = '#e8f5e9' if es_calculado else 'white'
                        param_row = tk.Frame(prueba_frame, bg=bg_row)
                        param_row.pack(fill='x')

                        # Nombre del parametro (con indicador de calculado)
                        nombre_display = param['NombreParametro'] or ''
                        if es_calculado:
                            nombre_display = f"* {nombre_display}"
                        tk.Label(param_row, text=nombre_display,
                                font=('Segoe UI', 9, 'bold' if es_calculado else 'normal'),
                                bg=bg_row, width=22, anchor='w',
                                fg='#2e7d32' if es_calculado else 'black').pack(side='left', padx=5, pady=2)

                        # Campo de resultado (Combobox para TEXTO, Entry para numerico)
                        tipo_resultado = param.get('TipoResultado') or 'NUMERICO'

                        if tipo_resultado.upper() == 'TEXTO' and not es_calculado:
                            # Obtener opciones predefinidas para este parametro
                            opciones_param = []
                            try:
                                opts = db.query(f"""
                                    SELECT Valor FROM OpcionesParametro
                                    WHERE ParametroID = {param_id} AND Activo = True
                                    ORDER BY Frecuencia DESC, Orden ASC
                                """)
                                opciones_param = [o['Valor'] for o in opts] if opts else []
                            except:
                                pass

                            # Si no hay opciones, usar opciones genericas basadas en el nombre
                            if not opciones_param:
                                nombre_upper = (param['NombreParametro'] or '').upper()
                                seccion_upper = (param.get('Seccion') or '').upper()

                                # --- MICROBIOLOGIA / BACTERIOLOGIA ---
                                # Detectar si es un antibiotico en seccion de antibiograma
                                es_antibiograma = any(x in seccion_upper for x in [
                                    'ANTIBIOGRAMA', 'SENSIBILIDAD', 'ANTIBIOTICO', 'SUSCEPTIBILIDAD'
                                ])

                                if es_antibiograma:
                                    opciones_param = ['S', 'I', 'R', 'SENSIBLE', 'INTERMEDIO', 'RESISTENTE', 'SDD']
                                elif any(x in nombre_upper for x in ['TIPO DE MUESTRA', 'TIPO MUESTRA']):
                                    opciones_param = [
                                        'ORINA CHORRO MEDIO', 'ORINA CATETERIZADA', 'ORINA PUNCION SUPRAPUBICA',
                                        'SANGRE VENOSA', 'HECES',
                                        'SECRECION FARINGEA', 'SECRECION AMIGDALINA',
                                        'SECRECION OTICA', 'SECRECION NASAL',
                                        'SECRECION VAGINAL', 'SECRECION ENDOCERVICAL',
                                        'SECRECION URETRAL', 'SECRECION DE HERIDA',
                                        'SECRECION CONJUNTIVAL', 'SECRECION OCULAR',
                                        'ESPUTO', 'ASPIRADO BRONQUIAL', 'LAVADO BRONCOALVEOLAR',
                                        'LIQUIDO CEFALORRAQUIDEO', 'LIQUIDO PLEURAL',
                                        'LIQUIDO ASCITICO', 'LIQUIDO SINOVIAL', 'LIQUIDO PERICARDICO',
                                        'PUNTA DE CATETER', 'TEJIDO', 'BIOPSIA',
                                        'HISOPADO NASAL', 'HISOPADO RECTAL',
                                        'OTRO'
                                    ]
                                elif any(x in nombre_upper for x in ['METODO DE RECOLECCION', 'METODO RECOLECCION']):
                                    opciones_param = [
                                        'CHORRO MEDIO', 'CATETERIZADA', 'PUNCION SUPRAPUBICA',
                                        'BOLSA RECOLECTORA', 'SONDA VESICAL',
                                        'HISOPADO', 'ASPIRACION', 'PUNCION',
                                        'RECOLECCION ESPONTANEA'
                                    ]
                                elif any(x in nombre_upper for x in [
                                    'RESULTADO DEL CULTIVO', 'RESULTADO CULTIVO', 'CRECIMIENTO',
                                    'DESARROLLO BACTERIANO', 'RESULTADO FINAL', 'RESULTADO PRELIMINAR'
                                ]):
                                    opciones_param = [
                                        'POSITIVO', 'NEGATIVO',
                                        'SIN DESARROLLO BACTERIANO A LAS 24H',
                                        'SIN DESARROLLO BACTERIANO A LAS 48H',
                                        'SIN DESARROLLO BACTERIANO A LAS 72H',
                                        'SIN DESARROLLO BACTERIANO A LOS 5 DIAS',
                                        'SIN DESARROLLO BACTERIANO A LOS 7 DIAS',
                                        'DESARROLLO BACTERIANO POSITIVO',
                                        'FLORA MIXTA', 'FLORA NORMAL',
                                        'CONTAMINACION PROBABLE', 'EN INCUBACION'
                                    ]
                                elif any(x in nombre_upper for x in [
                                    'GERMEN AISLADO', 'SEGUNDO GERMEN', 'MICROORGANISMO',
                                    'AGENTE ETIOLOGICO', 'ORGANISMO AISLADO', 'BACTERIA AISLADA'
                                ]):
                                    opciones_param = [
                                        # Enterobacterias
                                        'Escherichia coli', 'Escherichia coli BLEE (+)',
                                        'Klebsiella pneumoniae', 'Klebsiella pneumoniae BLEE (+)',
                                        'Klebsiella oxytoca',
                                        'Proteus mirabilis', 'Proteus vulgaris',
                                        'Enterobacter cloacae', 'Enterobacter aerogenes',
                                        'Citrobacter freundii', 'Citrobacter koseri',
                                        'Serratia marcescens', 'Morganella morganii',
                                        'Providencia stuartii',
                                        # No fermentadores
                                        'Pseudomonas aeruginosa', 'Acinetobacter baumannii',
                                        'Stenotrophomonas maltophilia', 'Burkholderia cepacia',
                                        # Cocos Gram positivos
                                        'Staphylococcus aureus', 'Staphylococcus aureus MRSA',
                                        'Staphylococcus epidermidis', 'Staphylococcus saprophyticus',
                                        'Staphylococcus haemolyticus', 'Staphylococcus lugdunensis',
                                        'Enterococcus faecalis', 'Enterococcus faecium',
                                        'Streptococcus pyogenes (Grupo A)',
                                        'Streptococcus agalactiae (Grupo B)',
                                        'Streptococcus pneumoniae',
                                        'Streptococcus viridans',
                                        # Enteropatogenos
                                        'Salmonella spp.', 'Salmonella typhi', 'Salmonella paratyphi',
                                        'Shigella spp.', 'Shigella flexneri', 'Shigella sonnei',
                                        'Campylobacter jejuni', 'Campylobacter coli',
                                        'Yersinia enterocolitica', 'Vibrio cholerae',
                                        # Otros
                                        'Haemophilus influenzae', 'Moraxella catarrhalis',
                                        'Neisseria gonorrhoeae', 'Neisseria meningitidis',
                                        'Gardnerella vaginalis', 'Listeria monocytogenes',
                                        # Levaduras
                                        'Candida albicans', 'Candida tropicalis',
                                        'Candida glabrata', 'Candida parapsilosis', 'Candida spp.',
                                        # Resultado negativo
                                        'NO SE AISLO GERMEN', 'FLORA NORMAL'
                                    ]
                                elif any(x in nombre_upper for x in ['HONGO AISLADO', 'ESPECIE']):
                                    opciones_param = [
                                        # Levaduras
                                        'Candida albicans', 'Candida tropicalis',
                                        'Candida glabrata', 'Candida parapsilosis',
                                        'Candida krusei', 'Candida auris', 'Candida spp.',
                                        'Cryptococcus neoformans',
                                        # Dermatofitos
                                        'Trichophyton rubrum', 'Trichophyton mentagrophytes',
                                        'Trichophyton tonsurans',
                                        'Microsporum canis', 'Microsporum gypseum',
                                        'Epidermophyton floccosum',
                                        # Mohos
                                        'Aspergillus fumigatus', 'Aspergillus niger',
                                        'Aspergillus flavus', 'Aspergillus spp.',
                                        'Fusarium spp.', 'Mucor spp.', 'Rhizopus spp.',
                                        # Dimorficos
                                        'Histoplasma capsulatum', 'Paracoccidioides brasiliensis',
                                        'Sporothrix schenckii',
                                        'NO SE AISLO HONGO'
                                    ]
                                elif any(x in nombre_upper for x in [
                                    'RECUENTO DE COLONIAS', 'RECUENTO COLONIAS', 'UFC',
                                    'UNIDADES FORMADORAS'
                                ]):
                                    opciones_param = [
                                        '<1,000 UFC/mL', '1,000-10,000 UFC/mL',
                                        '10,000-50,000 UFC/mL', '50,000-100,000 UFC/mL',
                                        '>100,000 UFC/mL', 'INCONTABLES',
                                        '<15 UFC (Maki)', '>15 UFC (Maki)',
                                        'ESCASO DESARROLLO', 'MODERADO DESARROLLO',
                                        'ABUNDANTE DESARROLLO', 'NO APLICA'
                                    ]
                                elif 'RESULTADO BAAR' in nombre_upper or 'ZIEHL' in nombre_upper:
                                    opciones_param = [
                                        'NEGATIVO (No se observan BAAR en 100 campos)',
                                        'POSITIVO (+) 1-9 BAAR en 100 campos',
                                        'POSITIVO (++) 1-9 BAAR en 10 campos',
                                        'POSITIVO (+++) 1-9 BAAR por campo',
                                        'POSITIVO (++++) >9 BAAR por campo',
                                    ]
                                elif 'NUMERO DE BAAR' in nombre_upper or 'CAMPOS OBSERVADOS' in nombre_upper:
                                    opciones_param = [
                                        'No se observan BAAR', '1-9 BAAR en 100 campos',
                                        '1-9 BAAR en 10 campos', '1-9 BAAR por campo',
                                        '>9 BAAR por campo', '100 campos observados',
                                        '200 campos observados', '300 campos observados'
                                    ]
                                elif 'ELEMENTOS MICOTICOS' in nombre_upper or 'KOH' in nombre_upper:
                                    opciones_param = [
                                        'POSITIVO', 'NEGATIVO',
                                        'HIFAS SEPTADAS', 'HIFAS NO SEPTADAS',
                                        'PSEUDOHIFAS', 'ESPORAS', 'LEVADURAS GEMANTES',
                                        'LEVADURAS', 'HIFAS Y ESPORAS',
                                        'ARTROCONIDIAS', 'NO SE OBSERVAN ELEMENTOS MICOTICOS'
                                    ]
                                elif any(x in nombre_upper for x in [
                                    'COLORACION DE GRAM', 'COLORACION GRAM', 'GRAM',
                                    'MORFOLOGIA EN GRAM', 'BACTERIAS EN GRAM'
                                ]) and 'LEUCOCITO' not in nombre_upper and 'CELULA' not in nombre_upper:
                                    opciones_param = [
                                        'COCOS GRAM POSITIVOS EN RACIMOS',
                                        'COCOS GRAM POSITIVOS EN CADENAS',
                                        'COCOS GRAM POSITIVOS EN PARES',
                                        'COCOS GRAM NEGATIVOS',
                                        'DIPLOCOCOS GRAM NEGATIVOS INTRACELULARES',
                                        'DIPLOCOCOS GRAM NEGATIVOS EXTRACELULARES',
                                        'DIPLOCOCOS GRAM POSITIVOS',
                                        'BACILOS GRAM POSITIVOS',
                                        'BACILOS GRAM NEGATIVOS',
                                        'COCOBACILOS GRAM POSITIVOS',
                                        'COCOBACILOS GRAM NEGATIVOS',
                                        'BACILOS GRAM POSITIVOS ESPORULADOS',
                                        'LEVADURAS', 'PSEUDOHIFAS',
                                        'FLORA MIXTA', 'FLORA BACTERIANA ESCASA',
                                        'FLORA BACTERIANA MODERADA', 'FLORA BACTERIANA ABUNDANTE',
                                        'NO SE OBSERVAN MICROORGANISMOS'
                                    ]
                                elif any(x in nombre_upper for x in [
                                    'LEUCOCITOS EN GRAM', 'LEUCOCITOS FECALES', 'LEUCOCITO',
                                    'EOSINOFILO'
                                ]):
                                    opciones_param = [
                                        'NO SE OBSERVAN', 'ESCASOS (0-5 x campo)',
                                        'MODERADOS (5-15 x campo)', 'ABUNDANTES (>15 x campo)',
                                        'CAMPO CUBIERTO', '+', '++', '+++'
                                    ]
                                elif any(x in nombre_upper for x in [
                                    'CELULAS EPITELIALES', 'CELULAS CLAVE', 'CLUE CELLS'
                                ]):
                                    opciones_param = [
                                        'NO SE OBSERVAN', 'ESCASAS', 'MODERADAS', 'ABUNDANTES',
                                        'PRESENTES', 'AUSENTES'
                                    ]
                                elif 'ERITROCITOS' in nombre_upper:
                                    opciones_param = [
                                        'NO SE OBSERVAN', 'ESCASOS', 'MODERADOS', 'ABUNDANTES',
                                        '+', '++', '+++'
                                    ]
                                elif any(x in nombre_upper for x in [
                                    'LACTOBACILOS', 'FLORA DODERLEIN'
                                ]):
                                    opciones_param = [
                                        'ABUNDANTES (FLORA NORMAL)', 'MODERADOS',
                                        'ESCASOS', 'AUSENTES', 'DISMINUIDOS'
                                    ]
                                elif any(x in nombre_upper for x in ['LEVADURA', 'PSEUDOHIFA']):
                                    opciones_param = [
                                        'NO SE OBSERVAN', 'ESCASAS', 'MODERADAS', 'ABUNDANTES',
                                        'PRESENTES', 'AUSENTES', 'LEVADURAS GEMANTES'
                                    ]
                                elif 'TRICHOMONAS' in nombre_upper:
                                    opciones_param = [
                                        'NO SE OBSERVAN', 'PRESENTES', 'ESCASAS', 'ABUNDANTES'
                                    ]
                                elif 'SCORE DE NUGENT' in nombre_upper or 'NUGENT' in nombre_upper:
                                    opciones_param = [
                                        '0-3 FLORA NORMAL', '4-6 FLORA INTERMEDIA',
                                        '7-10 VAGINOSIS BACTERIANA'
                                    ]
                                elif any(x in nombre_upper for x in ['BUSQUEDA DE SALMONELLA', 'BUSQUEDA DE SHIGELLA', 'BUSQUEDA DE CAMPYLOBACTER']):
                                    opciones_param = [
                                        'NO SE AISLO', 'POSITIVO', 'NEGATIVO', 'EN PROCESO'
                                    ]
                                elif any(x in nombre_upper for x in ['SEROTIPO', 'SEROGRUPO']):
                                    opciones_param = [
                                        'Grupo A', 'Grupo B', 'Grupo C', 'Grupo D',
                                        'O:2', 'O:4', 'O:7', 'O:8', 'O:9',
                                        'PENDIENTE', 'NO TIPIFICABLE', 'NO APLICA'
                                    ]
                                elif 'BETA HEMOLISIS' in nombre_upper:
                                    opciones_param = [
                                        'POSITIVA (BETA HEMOLISIS)', 'NEGATIVA',
                                        'ALFA HEMOLISIS', 'GAMMA HEMOLISIS (NO HEMOLITICO)'
                                    ]
                                elif any(x in nombre_upper for x in ['TIPO DE HERIDA']):
                                    opciones_param = [
                                        'QUIRURGICA', 'TRAUMATICA', 'QUEMADURA',
                                        'ULCERA POR PRESION', 'ULCERA DIABETICA',
                                        'ULCERA VASCULAR', 'ABSCESO', 'MORDEDURA',
                                        'HERIDA PUNZANTE', 'OTRO'
                                    ]
                                elif any(x in nombre_upper for x in ['TIPO DE CATETER']):
                                    opciones_param = [
                                        'CENTRAL (SUBCLAVIO)', 'CENTRAL (YUGULAR)',
                                        'CENTRAL (FEMORAL)', 'PERIFERICO',
                                        'PICC', 'PORT-A-CATH', 'HICKMAN',
                                        'SONDA VESICAL', 'OTRO'
                                    ]
                                elif any(x in nombre_upper for x in ['FRASCO']):
                                    opciones_param = [
                                        'AEROBIO', 'ANAEROBIO', 'AEROBIO Y ANAEROBIO',
                                        'PEDIATRICO', 'MICOBACTERIAS'
                                    ]
                                elif 'PORTADOR SARM' in nombre_upper:
                                    opciones_param = [
                                        'POSITIVO (PORTADOR SARM)', 'NEGATIVO (NO PORTADOR)',
                                        'INDETERMINADO'
                                    ]
                                elif 'CALIDAD DE LA MUESTRA' in nombre_upper or 'MURRAY' in nombre_upper:
                                    opciones_param = [
                                        'GRUPO 1 - NO APTA (>25 Ep, <10 Leuc)',
                                        'GRUPO 2 - NO APTA (>25 Ep, 10-25 Leuc)',
                                        'GRUPO 3 - NO APTA (>25 Ep, >25 Leuc)',
                                        'GRUPO 4 - APTA (10-25 Ep, >25 Leuc)',
                                        'GRUPO 5 - APTA (<10 Ep, >25 Leuc)',
                                        'MUESTRA APTA PARA CULTIVO',
                                        'MUESTRA NO APTA (Solicitar nueva muestra)'
                                    ]
                                elif 'PH VAGINAL' in nombre_upper or 'PH' in nombre_upper:
                                    opciones_param = [
                                        '< 4.0', '4.0', '4.5', '5.0', '5.5', '6.0', '> 6.0'
                                    ]
                                elif 'WHIFF' in nombre_upper:
                                    opciones_param = ['POSITIVO', 'NEGATIVO']
                                elif 'MACROSCOPIA' in nombre_upper or 'MICROSCOPIA' in nombre_upper:
                                    opciones_param = [
                                        'COLONIAS LISAS', 'COLONIAS RUGOSAS', 'COLONIAS MUCOIDES',
                                        'COLONIAS PIGMENTADAS', 'COLONIAS HEMOLITICAS',
                                        'HIFAS SEPTADAS', 'HIFAS NO SEPTADAS',
                                        'CONIDIOS', 'ARTROCONIDIAS', 'MACROCONIDIAS',
                                        'MICROCONIDIAS'
                                    ]
                                elif any(x in nombre_upper for x in ['METODO DE IDENTIFICACION']):
                                    opciones_param = [
                                        'AUTOMATIZADO (VITEK 2)', 'AUTOMATIZADO (PHOENIX)',
                                        'AUTOMATIZADO (MICROSCAN)', 'BIOQUIMICAS CONVENCIONALES',
                                        'API 20E', 'API 20NE', 'API STAPH', 'API STREP',
                                        'CHROMAGAR', 'MALDI-TOF', 'PCR',
                                        'DIFUSION EN DISCO (KIRBY-BAUER)',
                                        'PRUEBA DE COAGULASA', 'PRUEBA DE CATALASA',
                                        'PRUEBA DE OXIDASA', 'AGLUTINACION EN LATEX',
                                        'TUBO GERMINAL'
                                    ]
                                elif any(x in nombre_upper for x in ['METODO', 'MEDIO DE CULTIVO', 'MEDIO']):
                                    opciones_param = [
                                        'AGAR SANGRE', 'AGAR MACCONKEY', 'AGAR CHOCOLATE',
                                        'AGAR MUELLER HINTON', 'CALDO TIOGLICOLATO',
                                        'AGAR SABOURAUD', 'AGAR MANITOL SALADO',
                                        'AGAR EMB', 'AGAR SS', 'AGAR CLED',
                                        'AGAR THAYER MARTIN', 'AGAR HEKTOEN',
                                        'AGAR XLD', 'AGAR TCBS',
                                        'CALDO SELENITO', 'CALDO BHI',
                                        'AGAR CHROMAGAR', 'AGAR MYCOSEL',
                                        'AUTOMATIZADO (VITEK)', 'BACT/ALERT', 'BACTEC',
                                        'DIFUSION EN DISCO (KIRBY-BAUER)',
                                        'SEMICUANTITATIVO (MAKI)', 'CUANTITATIVO'
                                    ]
                                elif any(x in nombre_upper for x in ['TIEMPO INCUBACION', 'INCUBACION', 'HORAS']):
                                    opciones_param = [
                                        '24 HORAS', '48 HORAS', '72 HORAS',
                                        '5 DIAS', '7 DIAS', '14 DIAS', '21 DIAS',
                                        '24-48 HORAS', '48-72 HORAS'
                                    ]
                                elif any(x in nombre_upper for x in ['TEMPERATURA']):
                                    opciones_param = ['25-30°C', '35-37°C', '42°C']
                                elif 'ASPECTO' in nombre_upper and seccion_upper in [
                                    'DATOS DE MUESTRA', 'RESULTADO DEL CULTIVO', ''
                                ]:
                                    opciones_param = [
                                        'CLARO', 'TURBIO', 'PURULENTO', 'SEROSO',
                                        'SEROPURULENTO', 'SANGUINOLENTO', 'HEMORRÁGICO',
                                        'MUCOSO', 'MUCOPURULENTO', 'FÉTIDO',
                                        'XANTOCROMICO', 'AMARILLENTO', 'VERDOSO'
                                    ]
                                elif 'CONSISTENCIA' in nombre_upper:
                                    opciones_param = [
                                        'FORMADA', 'BLANDA', 'SEMIBLANDA', 'PASTOSA',
                                        'LIQUIDA', 'MUCOSA', 'SANGUINOLENTA', 'ACUOSA'
                                    ]
                                elif 'INTERPRETACION' in nombre_upper or 'OBSERVACION' in nombre_upper:
                                    opciones_param = None  # Campo libre de texto (Entry, no Combobox)
                                # --- FIN MICROBIOLOGIA ---
                                elif 'COLOR' in nombre_upper:
                                    opciones_param = ['AMARILLO CLARO', 'AMARILLO', 'AMARILLO OSCURO', 'AMBAR', 'MARRON']
                                elif 'ASPECTO' in nombre_upper:
                                    opciones_param = ['CLARO', 'LIGERAMENTE TURBIO', 'TURBIO', 'MUY TURBIO']
                                elif any(x in nombre_upper for x in ['LEUCOCITO', 'ERITROCITO']):
                                    opciones_param = ['0-2 x campo', '2-4 x campo', '4-6 x campo', '6-8 x campo', '>10 x campo', 'ESCASOS', 'ABUNDANTES']
                                elif 'CONSISTENCIA' in nombre_upper:
                                    opciones_param = ['FORMADA', 'BLANDA', 'SEMIBLANDA', 'PASTOSA', 'LIQUIDA']
                                elif any(x in nombre_upper for x in ['PROTEINA', 'GLUCOSA', 'CETONA', 'BILIRRUBINA', 'NITRITO']):
                                    opciones_param = ['NEGATIVO', 'TRAZAS', '+', '++', '+++']
                                elif any(x in nombre_upper for x in ['BACTERIA', 'FLORA']):
                                    opciones_param = ['ESCASA', 'NORMAL', 'MODERADA', 'ABUNDANTE', 'MUY ABUNDANTE']
                                else:
                                    opciones_param = ['NEGATIVO', 'POSITIVO', 'NO SE OBSERVA', 'ESCASO', 'MODERADO', 'ABUNDANTE']

                            if opciones_param is None:
                                # Campo libre de texto (Interpretacion, Observaciones, etc.)
                                entry_param = tk.Entry(param_row, font=('Segoe UI', 9), width=30, relief='flat',
                                                       bg='#fafafa', highlightthickness=1, highlightbackground='#ddd')
                                entry_param.pack(side='left', padx=5, pady=2)
                                if resultado_guardado and resultado_guardado.get('Valor'):
                                    entry_param.insert(0, resultado_guardado['Valor'])
                            else:
                                entry_param = ttk.Combobox(param_row, font=('Segoe UI', 9), width=14,
                                                          values=opciones_param)
                                entry_param.pack(side='left', padx=5, pady=2)
                                if resultado_guardado and resultado_guardado.get('Valor'):
                                    entry_param.set(resultado_guardado['Valor'])
                        else:
                            # Campo numerico o calculado - usar Entry
                            entry_param = tk.Entry(param_row, font=('Segoe UI', 9), width=12, relief='flat',
                                                  bg='#c8e6c9' if es_calculado else '#fafafa',
                                                  highlightthickness=1, highlightbackground='#ddd')
                            entry_param.pack(side='left', padx=5, pady=2)
                            if resultado_guardado and resultado_guardado.get('Valor'):
                                entry_param.insert(0, resultado_guardado['Valor'])

                        # Unidad
                        tk.Label(param_row, text=unidad_texto, font=('Segoe UI', 9),
                                bg=bg_row, width=10, fg='#666').pack(side='left', padx=5, pady=2)

                        # Valor de referencia - más visible y completo
                        ref_display = valor_ref if valor_ref else '---'
                        tk.Label(param_row, text=ref_display,
                                font=('Segoe UI', 9, 'bold'), bg=bg_row, width=28, anchor='w',
                                fg='#1565c0').pack(side='left', padx=5, pady=2)

                        self.parametro_entries[detalle_id].append({
                            'param_id': param_id,
                            'entry': entry_param,
                            'nombre': param['NombreParametro'],
                            'formula': formula,
                            'es_calculado': es_calculado,
                            'valor_ref': valor_ref or ''
                        })

                    # Bind auto-calculo: al salir de un campo no calculado, recalcular los calculados
                    tiene_calculados = any(p.get('es_calculado') for p in self.parametro_entries[detalle_id])
                    if tiene_calculados:
                        for param_data in self.parametro_entries[detalle_id]:
                            if not param_data.get('es_calculado'):
                                param_data['entry'].bind('<FocusOut>',
                                    lambda e, d=detalle_id: self.calcular_parametros(d, silencioso=True))
                                param_data['entry'].bind('<Return>',
                                    lambda e, d=detalle_id: self.calcular_parametros(d, silencioso=True))
                                param_data['entry'].bind('<Tab>',
                                    lambda e, d=detalle_id: self.calcular_parametros(d, silencioso=True))

                    # Separador
                    tk.Frame(prueba_frame, height=1, bg='#e0e0e0').pack(fill='x', pady=5)

                    # Botones para esta prueba
                    btn_frame_prueba = tk.Frame(prueba_frame, bg='white')
                    btn_frame_prueba.pack(fill='x', pady=5, padx=5)

                    if tiene_calculados:
                        tk.Button(btn_frame_prueba, text="Calcular", font=('Segoe UI', 9, 'bold'),
                                 bg='#ff9800', fg='white', relief='flat', padx=15,
                                 cursor='hand2',
                                 command=lambda d=detalle_id: self.calcular_parametros(d)).pack(side='left', padx=3)

                    # Botón para cálculos automáticos del módulo (perfil lipídico, hematología, etc.)
                    if CALCULOS_AUTOMATICOS_DISPONIBLE:
                        tk.Button(btn_frame_prueba, text="Auto Calc", font=('Segoe UI', 9, 'bold'),
                                 bg='#9c27b0', fg='white', relief='flat', padx=12,
                                 cursor='hand2',
                                 command=lambda d=detalle_id: self.aplicar_calculos_automaticos_ui(d)).pack(side='left', padx=3)

                    tk.Button(btn_frame_prueba, text="Guardar", font=('Segoe UI', 9),
                             bg=COLORS['primary'], fg='white', relief='flat', padx=15,
                             cursor='hand2',
                             command=lambda d=detalle_id: self.guardar_resultados_parametros(d)).pack(side='left', padx=3)

                    tk.Button(btn_frame_prueba, text="Validar", font=('Segoe UI', 9),
                             bg=COLORS['success'], fg='white', relief='flat', padx=15,
                             cursor='hand2',
                             command=lambda d=detalle_id: self.validar_resultados_parametros(d)).pack(side='left', padx=3)

                else:
                    # Si no tiene parametros, mostrar campo simple
                    simple_row = tk.Frame(prueba_frame, bg='white')
                    simple_row.pack(fill='x', pady=5, padx=5)

                    tk.Label(simple_row, text="Resultado:", font=('Segoe UI', 9),
                            bg='white').pack(side='left', padx=5)

                    entry_simple = tk.Entry(simple_row, font=('Segoe UI', 10), width=40, relief='flat',
                                           bg='#fafafa', highlightthickness=1, highlightbackground='#ddd')
                    entry_simple.pack(side='left', padx=5, pady=5)
                    if prueba.get('Resultado'):
                        entry_simple.insert(0, prueba['Resultado'])

                    self.resultado_entries[detalle_id] = {'entry': entry_simple}

                    tk.Button(simple_row, text="Guardar", font=('Segoe UI', 9),
                             bg=COLORS['primary'], fg='white', relief='flat', padx=15,
                             cursor='hand2',
                             command=lambda d=detalle_id, e=entry_simple: self.guardar_resultado_prueba(d, e)).pack(side='left', padx=5)

            # Separador visual antes de botones
            tk.Frame(scroll_frame, height=2, bg=COLORS['primary']).pack(fill='x', pady=(15, 5), padx=5)

            # Botones generales (dentro del scroll para que siempre sean accesibles)
            btn_general = tk.Frame(scroll_frame, bg='white')
            btn_general.pack(fill='x', pady=10, padx=5)

            tk.Button(btn_general, text="💾 Guardar Todos", font=('Segoe UI', 10, 'bold'),
                     bg=COLORS['primary'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=self.guardar_todos_parametros).pack(side='left', padx=5)

            tk.Button(btn_general, text="✅ Validar Todos", font=('Segoe UI', 10, 'bold'),
                     bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=self.validar_todos_parametros).pack(side='left', padx=5)

            tk.Button(btn_general, text="🧾 Imprimir Resultados", font=('Segoe UI', 10),
                     bg=COLORS['info'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=self.imprimir_resultados).pack(side='right', padx=5)

            # Frame contenedor de envío
            envio_container = tk.Frame(scroll_frame, bg='#f5f5f5', relief='groove', bd=1)
            envio_container.pack(fill='x', pady=10, padx=5)

            tk.Label(envio_container, text="📤 Enviar / Exportar Resultados",
                    font=('Segoe UI', 10, 'bold'), bg='#f5f5f5').pack(anchor='w', padx=10, pady=(8, 5))

            # Fila 1: PDF e impresión
            btn_row1 = tk.Frame(envio_container, bg='#f5f5f5')
            btn_row1.pack(fill='x', padx=10, pady=3)

            tk.Button(btn_row1, text="🖨️ Imprimir PDF", font=('Segoe UI', 9),
                     bg='#1565C0', fg='white', relief='flat', padx=15, pady=6,
                     cursor='hand2', command=self._imprimir_resultado_directo).pack(side='left', padx=3)

            tk.Button(btn_row1, text="📄 Guardar PDF", font=('Segoe UI', 9),
                     bg='#7b1fa2', fg='white', relief='flat', padx=15, pady=6,
                     cursor='hand2', command=lambda: self.generar_pdf_resultados(guardar_como=True)).pack(side='left', padx=3)

            # Fila 2: Envío al paciente
            btn_row2 = tk.Frame(envio_container, bg='#f5f5f5')
            btn_row2.pack(fill='x', padx=10, pady=3)

            tk.Label(btn_row2, text="Paciente:", font=('Segoe UI', 9, 'bold'),
                    bg='#f5f5f5').pack(side='left', padx=(0, 5))

            tk.Button(btn_row2, text="📱 WhatsApp Paciente", font=('Segoe UI', 9),
                     bg='#25D366', fg='white', relief='flat', padx=15, pady=6,
                     cursor='hand2', command=self.enviar_whatsapp_resultado).pack(side='left', padx=3)

            tk.Button(btn_row2, text="📧 Email Paciente", font=('Segoe UI', 9),
                     bg='#EA4335', fg='white', relief='flat', padx=15, pady=6,
                     cursor='hand2', command=self.enviar_email_resultado).pack(side='left', padx=3)

            # Fila 3: Envío al médico
            btn_row3 = tk.Frame(envio_container, bg='#f5f5f5')
            btn_row3.pack(fill='x', padx=10, pady=(3, 8))

            tk.Label(btn_row3, text="Médico:", font=('Segoe UI', 9, 'bold'),
                    bg='#f5f5f5').pack(side='left', padx=(0, 12))

            tk.Button(btn_row3, text="🩺 WhatsApp Médico", font=('Segoe UI', 9),
                     bg='#0077B5', fg='white', relief='flat', padx=15, pady=6,
                     cursor='hand2', command=self.enviar_whatsapp_medico).pack(side='left', padx=3)

            tk.Button(btn_row3, text="📧 Email Médico", font=('Segoe UI', 9),
                     bg='#C62828', fg='white', relief='flat', padx=15, pady=6,
                     cursor='hand2', command=self.enviar_email_medico).pack(side='left', padx=3)

            # Espacio final para que el scroll no quede justo al borde
            tk.Frame(scroll_frame, height=20, bg='white').pack(fill='x')

        except Exception as e:
            tk.Label(self.pruebas_res_frame, text=f"Error: {e}",
                    font=('Segoe UI', 10), bg='white', fg=COLORS['danger']).pack(pady=50)

    def guardar_resultado_prueba(self, detalle_id, entry):
        """Guarda el resultado de una prueba individual"""
        resultado = entry.get().strip()
        if not resultado:
            messagebox.showwarning("Aviso", "Ingrese un resultado")
            return

        try:
            db.update('DetalleSolicitudes', {
                'Resultado': resultado,
                'Estado': 'Capturado',
                'FechaResultado': datetime.now(),
                'UsuarioResultado': self.user.get('UsuarioID', 1)
            }, f"DetalleID={detalle_id}")

            # Actualizar visual
            if detalle_id in self.resultado_entries:
                self.resultado_entries[detalle_id]['row'].config(bg='#fff3e0')
                self.resultado_entries[detalle_id]['lbl_estado'].config(text='Capturado', fg='orange')
                for w in self.resultado_entries[detalle_id]['row'].winfo_children():
                    if isinstance(w, tk.Label):
                        w.config(bg='#fff3e0')

            messagebox.showinfo("Éxito", "Resultado guardado")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar: {e}")

    def validar_resultado_prueba(self, detalle_id, entry):
        """Valida el resultado de una prueba individual"""
        resultado = entry.get().strip()
        if not resultado:
            messagebox.showwarning("Aviso", "Debe ingresar un resultado antes de validar")
            return

        try:
            db.update('DetalleSolicitudes', {
                'Resultado': resultado,
                'Estado': 'Validado',
                'FechaResultado': datetime.now(),
                'UsuarioResultado': self.user.get('UsuarioID', 1)
            }, f"DetalleID={detalle_id}")

            # Actualizar visual
            if detalle_id in self.resultado_entries:
                self.resultado_entries[detalle_id]['row'].config(bg='#e8f5e9')
                self.resultado_entries[detalle_id]['lbl_estado'].config(text='Validado', fg='green')
                for w in self.resultado_entries[detalle_id]['row'].winfo_children():
                    if isinstance(w, tk.Label):
                        w.config(bg='#e8f5e9')

            messagebox.showinfo("Éxito", "Resultado validado")
        except Exception as e:
            messagebox.showerror("Error", f"Error al validar: {e}")

    def guardar_todos_resultados(self):
        """Guarda todos los resultados ingresados"""
        count = 0
        for detalle_id, data in self.resultado_entries.items():
            resultado = data['entry'].get().strip()
            if resultado:
                try:
                    db.update('DetalleSolicitudes', {
                        'Resultado': resultado,
                        'Estado': 'Capturado',
                        'FechaResultado': datetime.now(),
                        'UsuarioResultado': self.user.get('UsuarioID', 1)
                    }, f"DetalleID={detalle_id}")
                    count += 1
                except:
                    pass

        if count > 0:
            messagebox.showinfo("Éxito", f"{count} resultados guardados")
            # Recargar
            self.cargar_pruebas_resultado()
        else:
            messagebox.showinfo("Info", "No hay resultados para guardar")

    def validar_todos_resultados(self):
        """Valida todos los resultados que tienen valor"""
        count = 0
        for detalle_id, data in self.resultado_entries.items():
            resultado = data['entry'].get().strip()
            if resultado:
                try:
                    db.update('DetalleSolicitudes', {
                        'Resultado': resultado,
                        'Estado': 'Validado',
                        'FechaResultado': datetime.now(),
                        'UsuarioResultado': self.user.get('UsuarioID', 1)
                    }, f"DetalleID={detalle_id}")
                    count += 1
                except:
                    pass

        if count > 0:
            # Actualizar estado de la solicitud
            try:
                db.update('Solicitudes', {'EstadoSolicitud': 'Completada'}, f"SolicitudID={self.sol_id_resultado}")
            except:
                pass

            messagebox.showinfo("Éxito", f"{count} resultados validados\nSolicitud marcada como Completada")
            # Recargar
            self.cargar_solicitudes_pendientes()
            self.cargar_pruebas_resultado()
        else:
            messagebox.showinfo("Info", "No hay resultados para validar")

    def calcular_parametros(self, detalle_id, silencioso=False):
        """Calcula automaticamente los parametros que tienen formula.

        Args:
            detalle_id: ID del detalle de solicitud
            silencioso: Si True, no muestra mensajes (para auto-calculo)
        """
        if detalle_id not in self.parametro_entries:
            return

        # Obtener todos los valores actuales
        valores = {}
        faltantes = []
        for param_data in self.parametro_entries[detalle_id]:
            nombre = param_data['nombre'].upper().replace(' ', '_').replace('.', '')
            valor_str = param_data['entry'].get().strip()
            try:
                valor = float(valor_str.replace(',', '.')) if valor_str else 0
                valores[nombre] = valor
                if valor == 0 and not param_data.get('es_calculado'):
                    faltantes.append(param_data['nombre'])
            except:
                valores[nombre] = 0

        # Calcular cada parametro con formula
        calculados = 0
        errores = []
        for param_data in self.parametro_entries[detalle_id]:
            if not param_data.get('es_calculado'):
                continue

            formula = param_data.get('formula', '')
            if not formula:
                continue

            try:
                # Reemplazar nombres de parametros por valores
                formula_eval = formula.upper()
                for nombre, valor in valores.items():
                    formula_eval = formula_eval.replace(nombre, str(valor))

                # Verificar division por cero antes de evaluar
                if '/0' in formula_eval or '/0.0' in formula_eval:
                    if not silencioso:
                        errores.append(f"{param_data['nombre']}: Division por cero")
                    continue

                # Evaluar la formula
                resultado = eval(formula_eval)

                # Verificar resultado valido
                if resultado is None or (isinstance(resultado, float) and (resultado != resultado)):  # NaN check
                    if not silencioso:
                        errores.append(f"{param_data['nombre']}: Resultado invalido")
                    continue

                # Redondear a 2 decimales
                resultado = round(resultado, 2)

                # Actualizar el campo
                param_data['entry'].delete(0, 'end')
                param_data['entry'].insert(0, str(resultado))

                # Actualizar el diccionario de valores para formulas dependientes
                nombre_param = param_data['nombre'].upper().replace(' ', '_').replace('.', '')
                valores[nombre_param] = resultado

                calculados += 1
            except ZeroDivisionError:
                if not silencioso:
                    errores.append(f"{param_data['nombre']}: Division por cero")
            except Exception as e:
                if not silencioso:
                    errores.append(f"{param_data['nombre']}: {str(e)[:30]}")

        # Ejecutar también los cálculos automáticos del módulo
        calculos_modulo = 0
        if CALCULOS_AUTOMATICOS_DISPONIBLE:
            calculos_modulo = self.aplicar_calculos_automaticos_ui(detalle_id, silencioso=True)
            calculados += calculos_modulo

        # Mostrar resultado solo si no es silencioso
        if not silencioso:
            if calculados > 0 and not errores:
                msg = f"{calculados} parámetros calculados"
                if calculos_modulo > 0:
                    msg += f"\n({calculos_modulo} del módulo de cálculos automáticos)"
                messagebox.showinfo("Cálculo", msg)
            elif calculados > 0 and errores:
                messagebox.showwarning("Cálculo", f"{calculados} parámetros calculados\n\nNo se pudieron calcular:\n" + "\n".join(errores[:5]))
            elif errores:
                messagebox.showwarning("Aviso", "Complete los valores base antes de calcular:\n" + "\n".join(faltantes[:5]) if faltantes else "No se pudo realizar el cálculo")

    def aplicar_calculos_automaticos_ui(self, detalle_id, silencioso=False):
        """
        Aplica los cálculos automáticos del módulo de cálculos a los campos de la UI.

        Args:
            detalle_id: ID del detalle de solicitud
            silencioso: Si True, no muestra mensajes

        Returns:
            Número de cálculos aplicados
        """
        if not CALCULOS_AUTOMATICOS_DISPONIBLE:
            return 0

        if detalle_id not in self.parametro_entries:
            return 0

        try:
            calculador = obtener_calculador()

            # Construir diccionario de valores desde los Entry widgets
            valores = {}
            param_entries_map = {}  # Mapeo de nombre normalizado a entry widget

            for param_data in self.parametro_entries[detalle_id]:
                nombre = param_data.get('nombre', '')
                if not nombre:
                    continue

                valor_str = param_data['entry'].get().strip()
                if not valor_str:
                    continue

                nombre_lower = nombre.lower().strip()
                valores[nombre_lower] = valor_str
                param_entries_map[nombre_lower] = param_data

                # También guardar con nombre normalizado
                nombre_norm = calculador.normalizar_nombre(nombre)
                if nombre_norm:
                    valores[nombre_norm] = valor_str
                    param_entries_map[nombre_norm] = param_data

            if not valores:
                return 0

            # Ejecutar cálculos
            resultados = calculador.ejecutar_calculos(valores)

            if not resultados:
                return 0

            # Aplicar resultados a los Entry widgets
            # IMPORTANTE: Un cálculo puede aplicarse a MÚLTIPLES parámetros
            # (ej: indice_ct_hdl aplica a "REL COLESTEROL / HDL" e "INDICE ATEROGENICO")
            calculos_aplicados = 0

            for nombre_calculo, valor_calculado in resultados.items():
                if valor_calculado is None:
                    continue

                # Buscar TODOS los Entry widgets destino que coincidan
                # (puede haber múltiples parámetros con el mismo nombre normalizado)
                for param_data in self.parametro_entries[detalle_id]:
                    nombre_param = param_data.get('nombre', '')
                    nombre_norm = calculador.normalizar_nombre(nombre_param)

                    # Verificar si este parámetro coincide con el cálculo
                    if nombre_norm == nombre_calculo:
                        # Actualizar el Entry widget
                        entry = param_data['entry']
                        valor_actual = entry.get().strip()

                        # Solo actualizar si está vacío o es un valor calculado
                        if not valor_actual or param_data.get('es_calculado'):
                            entry.delete(0, 'end')
                            entry.insert(0, str(valor_calculado))
                            calculos_aplicados += 1

            if not silencioso and calculos_aplicados > 0:
                messagebox.showinfo("Cálculos Automáticos",
                    f"{calculos_aplicados} valores calculados automáticamente:\n" +
                    "\n".join([f"  - {k}: {v}" for k, v in resultados.items() if v is not None][:10]))

            return calculos_aplicados

        except Exception as e:
            print(f"[CALC UI] Error: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def registrar_uso_valor(self, param_id, valor):
        """Registra el uso de un valor para aumentar su frecuencia en el dropdown"""
        if not valor:
            return
        try:
            valor_esc = valor.replace("'", "''")
            # Buscar si existe la opcion
            opcion = db.query_one(f"""
                SELECT OpcionID, Frecuencia FROM OpcionesParametro
                WHERE ParametroID = {param_id} AND Valor = '{valor_esc}'
            """)

            if opcion:
                # Incrementar frecuencia
                nueva_freq = (opcion.get('Frecuencia', 0) or 0) + 1
                db.execute(f"UPDATE OpcionesParametro SET Frecuencia = {nueva_freq} WHERE OpcionID = {opcion['OpcionID']}")
            else:
                # Crear nueva opcion con frecuencia 1
                max_orden = db.query_one(f"SELECT MAX(Orden) as m FROM OpcionesParametro WHERE ParametroID = {param_id}")
                orden = (max_orden.get('m', 0) or 0) + 1 if max_orden else 1
                db.execute(f"""
                    INSERT INTO OpcionesParametro (ParametroID, Valor, Orden, Frecuencia, Activo, FechaCreacion)
                    VALUES ({param_id}, '{valor_esc}', {orden}, 1, True, Now())
                """)
        except Exception as e:
            pass  # Silenciar errores de registro de uso

    @staticmethod
    def _calcular_alerta(valor_str, valor_ref):
        """Determina si un valor numerico esta fuera del rango de referencia.
        Returns: ('alto'|'bajo'|None, bool)"""
        import re as _re
        if not valor_ref or not valor_str:
            return None, False
        try:
            valor_num = float(str(valor_str).replace(',', '.').strip())
        except (ValueError, TypeError):
            return None, False

        def _p(s):
            """Parsea numero manejando separador de miles espanol.
            '4.000'->4000, '150.000'->150000, '4.5'->4.5, '0.800'->0.8"""
            s = str(s).strip().replace(',', '.')
            if '.' in s:
                partes = s.split('.')
                if (len(partes) == 2 and partes[0] not in ('', '0', '-0')
                        and len(partes[1]) == 3 and partes[1].isdigit()):
                    s = partes[0] + partes[1]  # "4.000"→"4000", "4.500"→"4500"
            return float(s)

        ref_str = str(valor_ref).strip()
        match = _re.search(r'([\d.,]+)\s*[-\u2013]\s*([\d.,]+)', ref_str)
        if match:
            try:
                ref_min = _p(match.group(1))
                ref_max = _p(match.group(2))
                if valor_num < ref_min:
                    return 'bajo', True
                elif valor_num > ref_max:
                    return 'alto', True
                return None, False
            except (ValueError, TypeError):
                pass
        match = _re.search(r'<\s*=?\s*([\d.,]+)', ref_str)
        if match:
            try:
                limite = _p(match.group(1))
                if valor_num > limite:
                    return 'alto', True
                return None, False
            except (ValueError, TypeError):
                pass
        match = _re.search(r'>\s*=?\s*([\d.,]+)', ref_str)
        if match:
            try:
                limite = _p(match.group(1))
                if valor_num < limite:
                    return 'bajo', True
                return None, False
            except (ValueError, TypeError):
                pass
        return None, False

    def guardar_resultados_parametros(self, detalle_id):
        """Guarda los resultados de todos los parametros de una prueba"""
        if detalle_id not in self.parametro_entries:
            return

        count = 0
        for param_data in self.parametro_entries[detalle_id]:
            param_id = param_data['param_id']
            valor = param_data['entry'].get().strip()

            if valor:
                try:
                    # Registrar uso del valor para mejorar sugerencias
                    self.registrar_uso_valor(param_id, valor)

                    valor_ref = param_data.get('valor_ref', '')
                    tipo_alerta, fuera_de_rango = self._calcular_alerta(valor, valor_ref)

                    # Capturar estado anterior para auditoría
                    estado_anterior = None
                    if self.auditoria:
                        estado_anterior = self.auditoria.antes_guardar_resultado(detalle_id, param_id)

                    campos = {
                        'Valor': valor,
                        'Estado': 'Capturado',
                        'FechaCaptura': datetime.now(),
                        'UsuarioCaptura': self.user.get('UsuarioID', 1),
                        'ValorReferencia': valor_ref,
                        'FueraDeRango': fuera_de_rango,
                        'TipoAlerta': tipo_alerta or '',
                    }

                    # Verificar si ya existe
                    existe = db.query_one(f"""
                        SELECT ResultadoParamID FROM ResultadosParametros
                        WHERE DetalleID = {detalle_id} AND ParametroID = {param_id}
                    """)

                    if existe:
                        db.update('ResultadosParametros', campos,
                                  f"DetalleID={detalle_id} AND ParametroID={param_id}")
                    else:
                        campos['DetalleID'] = detalle_id
                        campos['ParametroID'] = param_id
                        db.insert('ResultadosParametros', campos)

                    # Registrar en auditoría
                    if self.auditoria:
                        self.auditoria.despues_guardar_resultado(
                            detalle_id, param_id, valor, 'Capturado',
                            estado_anterior, 'GUARDAR'
                        )
                    count += 1
                except Exception as e:
                    if LOGGING_DISPONIBLE:
                        log_evento(f"Error guardando parametro: {e}", nivel='error', modulo='resultados')
                    else:
                        print(f"Error guardando parametro: {e}")

        # Actualizar estado del detalle
        if count > 0:
            try:
                db.update('DetalleSolicitudes', {
                    'Estado': 'Capturado',
                    'FechaResultado': datetime.now()
                }, f"DetalleID={detalle_id}")
            except:
                pass

            # Ejecutar cálculos automáticos
            calculos_realizados = self.ejecutar_calculos_automaticos(detalle_id)

            if calculos_realizados > 0:
                messagebox.showinfo("Éxito", f"{count} parámetros guardados\n{calculos_realizados} valores calculados automáticamente")
            else:
                messagebox.showinfo("Éxito", f"{count} parámetros guardados")

            self.cargar_pruebas_resultado()

    def ejecutar_calculos_automaticos(self, detalle_id):
        """
        Ejecuta los cálculos automáticos para una prueba.

        Args:
            detalle_id: ID del detalle de solicitud

        Returns:
            Número de cálculos realizados
        """
        if not CALCULOS_AUTOMATICOS_DISPONIBLE:
            print("[CALC] Modulo de calculos no disponible")
            return 0

        # Asegurar que existe el diccionario de entries
        if not hasattr(self, 'parametro_entries'):
            self.parametro_entries = {}

        try:
            calculador = obtener_calculador()

            # Obtener la prueba asociada al detalle
            detalle = db.query_one(f"""
                SELECT d.PruebaID, d.SolicitudID FROM DetalleSolicitudes d
                WHERE d.DetalleID = {detalle_id}
            """)

            if not detalle:
                print(f"[CALC] No se encontró detalle ID: {detalle_id}")
                return 0

            prueba_id = detalle['PruebaID']
            solicitud_id = detalle['SolicitudID']
            print(f"[CALC] Procesando prueba ID: {prueba_id}, solicitud ID: {solicitud_id}")

            # Obtener todos los parámetros de la prueba con sus valores actuales
            parametros = db.query(f"""
                SELECT pp.ParametroID, par.NombreParametro,
                       rp.Valor, rp.ResultadoParamID
                FROM ParametrosPrueba pp
                INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID
                LEFT JOIN ResultadosParametros rp ON rp.DetalleID = {detalle_id}
                    AND rp.ParametroID = pp.ParametroID
                WHERE pp.PruebaID = {prueba_id}
            """)

            if not parametros:
                print(f"[CALC] No se encontraron parámetros para prueba ID: {prueba_id}")
                return 0

            print(f"[CALC] Encontrados {len(parametros)} parámetros")

            # Construir diccionario de valores
            valores = {}
            param_map = {}  # Mapeo de nombre normalizado a ParametroID

            for param in parametros:
                nombre = param['NombreParametro']
                param_id = param['ParametroID']

                if not nombre:
                    continue

                nombre_lower = nombre.lower().strip()
                param_map[nombre_lower] = param_id

                # También guardar con nombre normalizado
                nombre_norm = calculador.normalizar_nombre(nombre)
                if nombre_norm:
                    param_map[nombre_norm] = param_id

                # Obtener valor del Entry widget si existe (más actualizado que la BD)
                valor = None
                if detalle_id in self.parametro_entries:
                    for param_data in self.parametro_entries[detalle_id]:
                        if param_data['param_id'] == param_id:
                            valor = param_data['entry'].get().strip()
                            break

                # Si no hay Entry, usar valor de la BD
                if not valor:
                    valor = param.get('Valor')

                if valor:
                    valores[nombre_lower] = valor
                    if nombre_norm:
                        valores[nombre_norm] = valor
                    print(f"[CALC]   - {nombre}: {valor} (norm: {nombre_norm})")

            print(f"[CALC] Valores cargados: {len(valores)}")

            # También obtener datos del paciente para cálculos que lo requieran
            paciente = db.query_one(f"""
                SELECT p.FechaNacimiento, p.Sexo, p.Peso, p.Talla
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.SolicitudID = {solicitud_id}
            """)

            if paciente:
                if paciente.get('Sexo'):
                    valores['sexo'] = paciente['Sexo']
                if paciente.get('Peso'):
                    valores['peso'] = paciente['Peso']
                if paciente.get('Talla'):
                    valores['talla'] = paciente['Talla']
                if paciente.get('FechaNacimiento'):
                    try:
                        fn = paciente['FechaNacimiento']
                        hoy = datetime.now()
                        edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
                        valores['edad'] = edad
                    except:
                        pass

            # Ejecutar cálculos
            print(f"[CALC] Ejecutando cálculos con {len(valores)} valores...")
            resultados = calculador.ejecutar_calculos(valores)

            print(f"[CALC] Resultados calculados: {resultados}")

            if not resultados:
                print("[CALC] No hay resultados para guardar")
                return 0

            # Guardar los resultados calculados
            # IMPORTANTE: Un cálculo puede aplicarse a MÚLTIPLES parámetros
            # (ej: indice_ct_hdl aplica a "REL COLESTEROL / HDL" e "INDICE ATEROGENICO")
            calculos_guardados = 0

            print(f"[CALC] Guardando {len(resultados)} resultados calculados...")

            for nombre_calculo, valor_calculado in resultados.items():
                if valor_calculado is None:
                    continue

                print(f"[CALC] Buscando destino(s) para: {nombre_calculo} = {valor_calculado}")

                # Buscar TODOS los parámetros destino que coincidan (puede haber múltiples)
                params_destino = []

                for param in parametros:
                    nombre_param = param['NombreParametro']
                    if not nombre_param:
                        continue

                    nombre_norm = calculador.normalizar_nombre(nombre_param)
                    if nombre_norm == nombre_calculo:
                        params_destino.append(param['ParametroID'])
                        print(f"[CALC]   Encontrado: {nombre_param} -> ID {param['ParametroID']}")

                if not params_destino:
                    print(f"[CALC]   NO encontrado destino para {nombre_calculo}")

                # Guardar en TODOS los parámetros destino encontrados
                for param_destino_id in params_destino:
                    try:
                        # Verificar si ya existe un resultado para este parámetro
                        existe = db.query_one(f"""
                            SELECT ResultadoParamID FROM ResultadosParametros
                            WHERE DetalleID = {detalle_id} AND ParametroID = {param_destino_id}
                        """)

                        valor_str = str(valor_calculado)

                        if existe:
                            # Solo actualizar si el campo está marcado como calculado o vacío
                            db.update('ResultadosParametros', {
                                'Valor': valor_str,
                                'Estado': 'Calculado',
                                'FechaCaptura': datetime.now(),
                                'UsuarioCaptura': self.user.get('UsuarioID', 1)
                            }, f"DetalleID={detalle_id} AND ParametroID={param_destino_id}")
                        else:
                            db.insert('ResultadosParametros', {
                                'DetalleID': detalle_id,
                                'ParametroID': param_destino_id,
                                'Valor': valor_str,
                                'Estado': 'Calculado',
                                'FechaCaptura': datetime.now(),
                                'UsuarioCaptura': self.user.get('UsuarioID', 1)
                            })

                        calculos_guardados += 1
                        print(f"[CALC]   GUARDADO: {nombre_calculo} = {valor_str}")

                        # Actualizar el Entry en la interfaz si existe
                        if detalle_id in self.parametro_entries:
                            for param_data in self.parametro_entries[detalle_id]:
                                if param_data['param_id'] == param_destino_id:
                                    entry = param_data['entry']
                                    entry.delete(0, tk.END)
                                    entry.insert(0, valor_str)
                                    try:
                                        entry.config(fg='#2196F3')  # Color azul para valores calculados
                                    except:
                                        pass
                                    break
                    except Exception as e:
                        print(f"[CALC] Error guardando cálculo {nombre_calculo}: {e}")

            print(f"[CALC] Total cálculos guardados: {calculos_guardados}")
            return calculos_guardados

        except Exception as e:
            print(f"Error en cálculos automáticos: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def ejecutar_calculos_solicitud_completa(self, solicitud_id):
        """
        Ejecuta los cálculos automáticos para toda una solicitud.
        Útil para cálculos que dependen de valores de múltiples pruebas.

        Args:
            solicitud_id: ID de la solicitud

        Returns:
            Número total de cálculos realizados
        """
        if not CALCULOS_AUTOMATICOS_DISPONIBLE:
            return 0

        try:
            # Obtener todos los detalles de la solicitud
            detalles = db.query(f"""
                SELECT DetalleID FROM DetalleSolicitudes
                WHERE SolicitudID = {solicitud_id}
            """)

            total_calculos = 0
            for detalle in detalles:
                calculos = self.ejecutar_calculos_automaticos(detalle['DetalleID'])
                total_calculos += calculos

            return total_calculos

        except Exception as e:
            print(f"Error en cálculos de solicitud completa: {e}")
            return 0

    def validar_resultados_parametros(self, detalle_id):
        """Valida los resultados de todos los parametros de una prueba"""
        if detalle_id not in self.parametro_entries:
            return

        # Primero guardar
        self.guardar_resultados_parametros(detalle_id)

        # Registrar validación masiva en auditoría
        if self.auditoria:
            self.auditoria.registrar_validacion_masiva(detalle_id)

        # Luego validar
        try:
            db.execute(f"""
                UPDATE ResultadosParametros SET Estado = 'Validado'
                WHERE DetalleID = {detalle_id}
            """)

            db.update('DetalleSolicitudes', {
                'Estado': 'Validado',
                'FechaResultado': datetime.now()
            }, f"DetalleID={detalle_id}")

            if LOGGING_DISPONIBLE:
                log_auditoria(self.user.get('UsuarioID'), 'VALIDAR_RESULTADO',
                              f"DetalleID={detalle_id} validado", modulo='resultados')

            messagebox.showinfo("Exito", "Resultados validados")
            self.cargar_pruebas_resultado()
        except Exception as e:
            messagebox.showerror("Error", f"Error al validar: {e}")

    def guardar_todos_parametros(self, silencioso=False):
        """Guarda todos los resultados de todos los parametros.
        Args:
            silencioso: Si True, no muestra messageboxes (usado internamente por validar_todos)
        """
        total = 0

        # Guardar parametros
        for detalle_id, params in self.parametro_entries.items():
            for param_data in params:
                param_id = param_data['param_id']
                valor = param_data['entry'].get().strip()

                if valor:
                    try:
                        existe = db.query_one(f"""
                            SELECT ResultadoParamID FROM ResultadosParametros
                            WHERE DetalleID = {detalle_id} AND ParametroID = {param_id}
                        """)

                        if existe:
                            db.update('ResultadosParametros', {
                                'Valor': valor,
                                'Estado': 'Capturado',
                                'FechaCaptura': datetime.now(),
                                'UsuarioCaptura': self.user.get('UsuarioID', 1)
                            }, f"DetalleID={detalle_id} AND ParametroID={param_id}")
                        else:
                            db.insert('ResultadosParametros', {
                                'DetalleID': detalle_id,
                                'ParametroID': param_id,
                                'Valor': valor,
                                'Estado': 'Capturado',
                                'FechaCaptura': datetime.now(),
                                'UsuarioCaptura': self.user.get('UsuarioID', 1)
                            })
                        total += 1
                    except:
                        pass

            # Actualizar estado del detalle
            if any(p['entry'].get().strip() for p in params):
                try:
                    db.update('DetalleSolicitudes', {
                        'Estado': 'Capturado',
                        'FechaResultado': datetime.now()
                    }, f"DetalleID={detalle_id}")
                except:
                    pass

        # Guardar resultados simples
        for detalle_id, data in self.resultado_entries.items():
            resultado = data['entry'].get().strip()
            if resultado:
                try:
                    db.update('DetalleSolicitudes', {
                        'Resultado': resultado,
                        'Estado': 'Capturado',
                        'FechaResultado': datetime.now()
                    }, f"DetalleID={detalle_id}")
                    total += 1
                except:
                    pass

        if total > 0:
            # Ejecutar cálculos automáticos para todos los detalles
            total_calculos = 0
            for detalle_id in self.parametro_entries.keys():
                calculos = self.ejecutar_calculos_automaticos(detalle_id)
                total_calculos += calculos

            if not silencioso:
                if total_calculos > 0:
                    messagebox.showinfo("Éxito", f"{total} resultados guardados\n{total_calculos} valores calculados automáticamente")
                else:
                    messagebox.showinfo("Éxito", f"{total} resultados guardados")

            self.cargar_pruebas_resultado()
        else:
            if not silencioso:
                messagebox.showinfo("Info", "No hay resultados para guardar")

    def validar_todos_parametros(self):
        """Valida todos los resultados de parametros y pruebas"""
        # Primero guardar todo (silencioso para evitar doble messagebox)
        self.guardar_todos_parametros(silencioso=True)

        # Validar parametros
        for detalle_id in self.parametro_entries.keys():
            try:
                db.execute(f"UPDATE ResultadosParametros SET Estado = 'Validado' WHERE DetalleID = {detalle_id}")
                db.update('DetalleSolicitudes', {'Estado': 'Validado'}, f"DetalleID={detalle_id}")
            except:
                pass

        # Validar resultados simples
        for detalle_id, data in self.resultado_entries.items():
            if data['entry'].get().strip():
                try:
                    db.update('DetalleSolicitudes', {'Estado': 'Validado'}, f"DetalleID={detalle_id}")
                except:
                    pass

        # Marcar solicitud como completada
        try:
            db.update('Solicitudes', {'EstadoSolicitud': 'Completada'}, f"SolicitudID={self.sol_id_resultado}")
        except:
            pass

        messagebox.showinfo("Exito", "Todos los resultados validados\nSolicitud marcada como Completada")
        self.cargar_solicitudes_pendientes()
        self.cargar_pruebas_resultado()

    def obtener_impresora_configurada(self, tipo='resultados'):
        """
        Obtiene la impresora configurada en la BD.

        Args:
            tipo: 'resultados' o 'informes'
        Returns:
            str: Nombre de la impresora o None
        """
        try:
            config = db.query_one("SELECT * FROM ConfiguracionLaboratorio")
            if config:
                campo = 'ImpresoraResultados' if tipo == 'resultados' else 'ImpresoraInformes'
                impresora = config.get(campo)
                if impresora:
                    return impresora
        except Exception:
            pass
        return None

    def imprimir_pdf_en_impresora(self, pdf_path, tipo='resultados'):
        """
        Muestra un diálogo para seleccionar impresora y envía el PDF a imprimir.
        """
        if not pdf_path or not os.path.exists(pdf_path):
            messagebox.showerror("Error", "No se encontró el archivo PDF para imprimir.")
            return False

        # Obtener lista de impresoras
        impresoras = []
        impresora_default = ""
        try:
            import win32print
            flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            lista = win32print.EnumPrinters(flags, None, 2)
            impresoras = [p['pPrinterName'] for p in lista]
            try:
                impresora_default = win32print.GetDefaultPrinter()
            except Exception:
                pass
        except ImportError:
            try:
                import subprocess
                result = subprocess.run(
                    ['wmic', 'printer', 'get', 'name'],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:
                        name = line.strip()
                        if name:
                            impresoras.append(name)
            except Exception:
                pass

        if not impresoras:
            messagebox.showerror("Error",
                "No se detectaron impresoras instaladas en el sistema.\n\n"
                "Instale una impresora y vuelva a intentar.")
            return False

        # Impresora configurada en BD
        impresora_configurada = self.obtener_impresora_configurada(tipo)

        # Crear diálogo de impresión
        win = tk.Toplevel(self.root)
        win.title("Imprimir Resultados")
        win.configure(bg='white')
        win.grab_set()
        win.focus_set()
        hacer_ventana_responsiva(win, 480, 340, min_ancho=400, min_alto=300)

        # Header
        header = tk.Frame(win, bg=COLORS['primary'], height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="Imprimir Documento", font=('Segoe UI', 14, 'bold'),
                bg=COLORS['primary'], fg='white').pack(pady=12)

        body = tk.Frame(win, bg='white')
        body.pack(fill='both', expand=True, padx=25, pady=15)

        # Archivo
        tk.Label(body, text="Archivo:", font=('Segoe UI', 9, 'bold'),
                bg='white', anchor='w').pack(fill='x')
        tk.Label(body, text=os.path.basename(pdf_path), font=('Segoe UI', 9),
                bg='#f5f5f5', fg='#555', relief='solid', bd=1,
                padx=8, pady=4, anchor='w').pack(fill='x', pady=(2, 12))

        # Selección de impresora
        tk.Label(body, text="Seleccione impresora:", font=('Segoe UI', 9, 'bold'),
                bg='white', anchor='w').pack(fill='x')

        combo_impresora = ttk.Combobox(body, values=impresoras, font=('Segoe UI', 10),
                                        state='readonly', height=10)
        combo_impresora.pack(fill='x', pady=(2, 5))

        # Seleccionar impresora por defecto: configurada > predeterminada > primera
        if impresora_configurada and impresora_configurada in impresoras:
            combo_impresora.set(impresora_configurada)
        elif impresora_default and impresora_default in impresoras:
            combo_impresora.set(impresora_default)
        elif impresoras:
            combo_impresora.current(0)

        # Info de impresora
        lbl_info = tk.Label(body, text="", font=('Segoe UI', 8), bg='white', fg='#888', anchor='w')
        lbl_info.pack(fill='x')

        def actualizar_info(event=None):
            sel = combo_impresora.get()
            textos = []
            if sel == impresora_default:
                textos.append("Predeterminada del sistema")
            if sel == impresora_configurada:
                textos.append(f"Configurada para {tipo}")
            lbl_info.config(text=" | ".join(textos) if textos else "")

        combo_impresora.bind('<<ComboboxSelected>>', actualizar_info)
        actualizar_info()

        # Opciones adicionales
        opciones_frame = tk.Frame(body, bg='white')
        opciones_frame.pack(fill='x', pady=(10, 0))

        # Copias
        tk.Label(opciones_frame, text="Copias:", font=('Segoe UI', 9, 'bold'),
                bg='white').pack(side='left')
        spin_copias = tk.Spinbox(opciones_frame, from_=1, to=10, width=5,
                                  font=('Segoe UI', 10), justify='center')
        spin_copias.pack(side='left', padx=10)

        # Calidad
        tk.Label(opciones_frame, text="Calidad:", font=('Segoe UI', 9, 'bold'),
                bg='white').pack(side='left', padx=(15, 0))
        combo_calidad = ttk.Combobox(opciones_frame, values=['Alta', 'Media', 'Borrador'],
                                      font=('Segoe UI', 9), state='readonly', width=10)
        combo_calidad.set('Alta')
        combo_calidad.pack(side='left', padx=5)

        # Botones
        btn_frame = tk.Frame(win, bg='white')
        btn_frame.pack(fill='x', padx=25, pady=(0, 20))

        def _configurar_calidad_impresora(impresora_nombre, calidad_texto, copias_num):
            """Configura la calidad de impresión de la impresora."""
            try:
                import win32print

                # Mapear calidad
                # DMRES_HIGH = -4, DMRES_MEDIUM = -3, DMRES_DRAFT = -1
                calidad_map = {'Alta': -4, 'Media': -3, 'Borrador': -1}
                calidad_valor = calidad_map.get(calidad_texto, -4)

                hprinter = win32print.OpenPrinter(impresora_nombre)
                try:
                    # Obtener configuración actual (DEVMODE)
                    devmode = win32print.GetPrinter(hprinter, 2)['pDevMode']

                    # Establecer calidad de impresión
                    devmode.PrintQuality = calidad_valor

                    # Establecer copias
                    devmode.Copies = copias_num

                    # Aplicar configuración
                    win32print.DocumentProperties(0, hprinter, impresora_nombre,
                                                   devmode, devmode, 0)

                    return devmode
                finally:
                    win32print.ClosePrinter(hprinter)
            except Exception:
                return None

        def ejecutar_impresion():
            impresora_sel = combo_impresora.get()
            if not impresora_sel:
                messagebox.showwarning("Aviso", "Seleccione una impresora.", parent=win)
                return

            copias = int(spin_copias.get())
            calidad = combo_calidad.get()
            win.destroy()

            try:
                import win32print
                import win32api

                # Configurar calidad alta en la impresora
                _configurar_calidad_impresora(impresora_sel, calidad, copias)

                impresora_anterior = win32print.GetDefaultPrinter()
                try:
                    win32print.SetDefaultPrinter(impresora_sel)
                    win32api.ShellExecute(0, 'print', pdf_path, None, '.', 0)
                finally:
                    try:
                        win32print.SetDefaultPrinter(impresora_anterior)
                    except Exception:
                        pass

                messagebox.showinfo("Imprimir",
                    f"Documento enviado a imprimir.\n\n"
                    f"Impresora: {impresora_sel}\n"
                    f"Calidad: {calidad}\n"
                    f"Copias: {copias}")

            except ImportError:
                try:
                    for _ in range(copias):
                        os.startfile(pdf_path, 'print')
                except Exception:
                    try:
                        os.startfile(pdf_path)
                        messagebox.showinfo("Imprimir",
                            "Se ha abierto el PDF.\n\nUse Ctrl+P para imprimir.")
                    except Exception:
                        webbrowser.open(pdf_path)
            except Exception as e:
                messagebox.showerror("Error", f"Error al imprimir:\n{str(e)}")

        def abrir_pdf():
            """Abre el PDF en el visor para vista previa."""
            try:
                os.startfile(pdf_path)
            except Exception:
                webbrowser.open(pdf_path)

        tk.Button(btn_frame, text="Imprimir", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', width=14, pady=6,
                 cursor='hand2', command=ejecutar_impresion).pack(side='left', padx=(0, 5))

        tk.Button(btn_frame, text="Vista Previa", font=('Segoe UI', 10),
                 bg=COLORS['info'], fg='white', relief='flat', width=14, pady=6,
                 cursor='hand2', command=abrir_pdf).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Cancelar", font=('Segoe UI', 10),
                 bg=COLORS['danger'], fg='white', relief='flat', width=14, pady=6,
                 cursor='hand2', command=win.destroy).pack(side='right')

        return True

    def imprimir_resultados(self):
        """Genera un reporte de resultados para imprimir"""
        try:
            sol = db.query_one(f"""
                SELECT s.*, p.Nombres & ' ' & p.Apellidos AS Paciente,
                       p.NumeroDocumento, p.FechaNacimiento, p.Sexo
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.SolicitudID = {self.sol_id_resultado}
            """)

            pruebas = db.query(f"""
                SELECT d.*, p.CodigoPrueba, p.NombrePrueba
                FROM DetalleSolicitudes d
                LEFT JOIN Pruebas p ON d.PruebaID = p.PruebaID
                WHERE d.SolicitudID = {self.sol_id_resultado}
                ORDER BY p.NombrePrueba
            """)

            if not sol or not pruebas:
                messagebox.showwarning("Aviso", "No hay datos para imprimir")
                return

            # Generar reporte
            reporte = f"""
{'='*60}
            LABORATORIO CLÍNICO - ANgesLAB
               INFORME DE RESULTADOS
{'='*60}

Solicitud N°: {sol['NumeroSolicitud']}
Fecha: {sol['FechaSolicitud'].strftime('%d/%m/%Y') if sol['FechaSolicitud'] else 'N/A'}

DATOS DEL PACIENTE:
  Nombre: {sol['Paciente'] or 'N/A'}
  Documento: {sol.get('NumeroDocumento') or 'N/A'}
  Sexo: {'Masculino' if sol.get('Sexo') == 'M' else 'Femenino' if sol.get('Sexo') == 'F' else 'N/A'}

{'='*60}
RESULTADOS:
{'-'*60}
"""
            for p in pruebas:
                estado = '✓' if p.get('Estado') == 'Validado' else '○'
                reporte += f"""
{estado} {p['NombrePrueba'] or 'N/A'}
   Código: {p['CodigoPrueba'] or 'N/A'}
   Resultado: {p.get('Resultado') or 'Pendiente'}
   Estado: {p.get('Estado') or 'Pendiente'}
"""

            reporte += f"""
{'-'*60}

Fecha de impresión: {datetime.now().strftime('%d/%m/%Y %H:%M')}

{'='*60}
"""

            # Mostrar ventana de impresión
            win = tk.Toplevel(self.root)
            win.title(f"Resultados - {sol['NumeroSolicitud']}")
            hacer_ventana_responsiva(win, 600, 700, min_ancho=500, min_alto=500)

            txt = tk.Text(win, font=('Courier New', 10), wrap='word')
            txt.pack(fill='both', expand=True, padx=10, pady=10)
            txt.insert('1.0', reporte)
            txt.config(state='disabled')

            def guardar():
                filename = filedialog.asksaveasfilename(
                    defaultextension=".txt",
                    filetypes=[("Text files", "*.txt")],
                    initialfilename=f"Resultados_{sol['NumeroSolicitud']}.txt"
                )
                if filename:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(reporte)
                    messagebox.showinfo("Éxito", f"Guardado en:\n{filename}")

            tk.Button(win, text="💾 Guardar como TXT", font=('Segoe UI', 10),
                     bg=COLORS['primary'], fg='white', relief='flat', command=guardar).pack(pady=10)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def generar_pdf_resultados(self, guardar_como=False):
        """Genera un PDF profesional con los resultados de la solicitud - Formato CMLab"""
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "La librería reportlab no está instalada.\nEjecute: pip install reportlab")
            return None

        try:
            # Obtener configuración administrativa
            config_lab = None
            ruta_logo = None
            if self.config_administrativa:
                config_lab = self.config_administrativa.obtener_configuracion()
                ruta_logo = self.config_administrativa.obtener_ruta_logo()

            # Obtener datos de la solicitud
            sol = db.query_one(f"""
                SELECT s.*, p.Nombres, p.Apellidos, p.NumeroDocumento,
                       p.FechaNacimiento, p.Sexo, p.Telefono1, p.Email,
                       m.Nombres & ' ' & m.Apellidos AS Medico
                FROM (Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID)
                LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
                WHERE s.SolicitudID = {self.sol_id_resultado}
            """)

            if not sol:
                messagebox.showwarning("Aviso", "No se encontró la solicitud")
                return None

            # Obtener pruebas con sus parámetros (incluye AreaID para firma bioanalista)
            pruebas = db.query(f"""
                SELECT d.DetalleID, d.PruebaID, d.Estado, p.CodigoPrueba, p.NombrePrueba, p.AreaID
                FROM DetalleSolicitudes d
                LEFT JOIN Pruebas p ON d.PruebaID = p.PruebaID
                WHERE d.SolicitudID = {self.sol_id_resultado}
                ORDER BY p.NombrePrueba
            """)

            # Obtener bioanalistas activos por área para las firmas
            bioanalistas_por_area = {}
            try:
                areas_ids = list(set(pr.get('AreaID') for pr in pruebas if pr.get('AreaID')))
                if areas_ids:
                    areas_str = ','.join(str(a) for a in areas_ids)
                    bios = db.query(
                        f"SELECT b.BioanalistaID, b.NombreCompleto, b.Cedula, b.NumeroRegistro, "
                        f"b.AreaID, b.RutaFirma, a.NombreArea "
                        f"FROM Bioanalistas b LEFT JOIN Areas a ON b.AreaID = a.AreaID "
                        f"WHERE b.AreaID IN ({areas_str}) AND b.Activo = True"
                    )
                    for bio in bios:
                        bioanalistas_por_area[bio['AreaID']] = bio
            except Exception:
                pass  # Si falla, usa fallback (NombreDirector)

            # Determinar ruta del archivo
            if guardar_como:
                num_sol = str(sol.get('NumeroSolicitud', 'Resultado')).replace('/', '-').replace('\\', '-')
                filename = filedialog.asksaveasfilename(
                    title="Guardar PDF de Resultados",
                    defaultextension=".pdf",
                    filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")],
                    initialfile=f"Resultados_{num_sol}.pdf"
                )
                if not filename:
                    return None
            else:
                # Crear archivo temporal
                temp_dir = tempfile.gettempdir()
                num_sol_safe = str(sol.get('NumeroSolicitud', 'Resultado')).replace('/', '-').replace('\\', '-').replace(':', '-')
                filename = os.path.join(temp_dir, f"Resultados_{num_sol_safe}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")

            # Determinar tamaño de página según configuración
            tamano_papel = config_lab.get('TamanoPapel', 'Carta') if config_lab else 'Carta'

            # Crear layout proporcional (calcula todas las dimensiones)
            if FORMATO_PDF_DISPONIBLE:
                layout = LayoutCalculator(tamano_papel, tiene_bioanalistas=bool(bioanalistas_por_area))
                page_size = layout.page_size
            else:
                # Fallback sin formato_pdf
                _tamanos = {'Oficio': legal, 'A4': A4, 'Media Carta': MEDIA_CARTA if FORMATO_PDF_DISPONIBLE else letter}
                page_size = _tamanos.get(tamano_papel, letter)
                layout = None

            # Determinar orientación (no aplica a Media Carta)
            if config_lab and config_lab.get('Orientacion') == 'Horizontal' and tamano_papel != 'Media Carta':
                page_size = landscape(page_size)
                if layout:
                    # Recalcular layout con dimensiones rotadas
                    layout = LayoutCalculator(tamano_papel, tiene_bioanalistas=bool(bioanalistas_por_area))
                    layout.page_size = page_size
                    layout.page_width = page_size[0]
                    layout.page_height = page_size[1]
                    layout._calcular_dimensiones()

            page_width, page_height = page_size

            # Márgenes desde layout proporcional
            if layout:
                left_margin = layout.margin_left
                right_margin = layout.margin_right
                top_margin = layout.margin_top
                bottom_margin = layout.margin_bottom
            else:
                left_margin = 0.5 * inch
                right_margin = 0.5 * inch
                top_margin = 0.4 * inch
                bottom_margin = 1.3 * inch if bioanalistas_por_area else 0.5 * inch

            # Preparar datos del paciente para el encabezado
            nombre_paciente = f"{sol.get('Nombres') or ''} {sol.get('Apellidos') or ''}".strip().upper() or 'N/A'
            fecha_sol = sol['FechaSolicitud'].strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'
            num_orden = sol.get('NumeroSolicitud') or 'N/A'
            cedula = sol.get('NumeroDocumento') or 'N/A'
            sexo = 'Masculino' if sol.get('Sexo') == 'M' else 'Femenino' if sol.get('Sexo') == 'F' else 'N/A'
            telefono_pac = sol.get('Telefono1') or ''
            medico = sol.get('Medico') or 'N/A'

            # Calcular edad
            edad_texto = '0 Años'
            if sol.get('FechaNacimiento'):
                try:
                    fn = sol['FechaNacimiento']
                    hoy = datetime.now()
                    edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
                    edad_texto = f"{edad} Años"
                except:
                    pass

            # Información del laboratorio
            nombre_lab = config_lab.get('NombreLaboratorio', 'LABORATORIO CLÍNICO') if config_lab else 'LABORATORIO CLÍNICO'
            direccion_lab = config_lab.get('Direccion', '') if config_lab else ''
            email_lab = config_lab.get('Email', '') if config_lab else ''
            telefono_lab = config_lab.get('Telefono1', '') if config_lab else ''
            telefono2_lab = config_lab.get('Telefono2', '') if config_lab else ''

            # Altura del encabezado (logo + info lab + datos paciente)
            header_height = layout.header_height if layout else 2.0 * inch

            # Función para dibujar el encabezado en cada página
            def draw_header(canvas, doc):
                canvas.saveState()

                # ===== PARTE SUPERIOR: Logo + Info del Laboratorio =====
                y_top = page_height - top_margin

                # Logo (izquierda) - dimensiones proporcionales
                logo_width = layout.logo_width if layout else 1.2 * inch
                logo_height = layout.logo_height if layout else 1.0 * inch
                logo_x = left_margin
                logo_y = y_top - logo_height - 0.1*inch

                if ruta_logo and os.path.exists(ruta_logo) and config_lab and config_lab.get('MostrarLogo'):
                    try:
                        canvas.drawImage(ruta_logo, logo_x, logo_y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
                    except:
                        pass

                # Información del laboratorio (derecha del logo)
                _info_offset = layout.info_lab_x_offset if layout else (logo_width + 0.3*inch)
                info_x = left_margin + _info_offset
                info_y = y_top - 0.15*inch

                # Limitar el ancho de texto si hay QR (reservar espacio derecho)
                _qr_reserva = (layout.qr_size + 0.2*inch) if (layout and QRGenerator.disponible()) else 0

                canvas.setFont('Helvetica-Bold', layout.font_lab_nombre if layout else 10)
                canvas.drawString(info_x, info_y, nombre_lab.upper())

                canvas.setFont('Helvetica', layout.font_lab_detalle if layout else 8)
                line_height = layout.info_line_height if layout else 11
                current_y = info_y - line_height

                if direccion_lab:
                    # Dividir dirección si es muy larga
                    max_chars = layout.max_chars_direccion if layout else 70
                    if len(direccion_lab) > max_chars:
                        canvas.drawString(info_x, current_y, direccion_lab[:max_chars])
                        current_y -= line_height
                        canvas.drawString(info_x, current_y, direccion_lab[max_chars:])
                    else:
                        canvas.drawString(info_x, current_y, direccion_lab)
                    current_y -= line_height

                if email_lab:
                    canvas.drawString(info_x, current_y, f"Correo: {email_lab}")
                    current_y -= line_height

                telefono_texto = ""
                if telefono_lab:
                    telefono_texto = f"Teléfono: {telefono_lab}"
                if telefono2_lab:
                    telefono_texto += f"  WhatsApp: {telefono2_lab}"
                if telefono_texto:
                    canvas.drawString(info_x, current_y, telefono_texto)
                    current_y -= line_height

                canvas.setFont('Helvetica-Oblique', layout.font_lab_pie if layout else 7)
                canvas.drawString(info_x, current_y, "Impreso por ANgesLAB - Sistema de Gestión de Laboratorio")

                # ===== QR DE VERIFICACIÓN (esquina superior derecha) =====
                if layout and FORMATO_PDF_DISPONIBLE:
                    dibujar_qr_en_header(canvas, layout, num_orden, fecha_sol, nombre_paciente)

                # ===== CUADRO DE DATOS DEL PACIENTE =====
                _box_y_off = layout.box_y_offset if layout else (logo_height + 0.35*inch)
                box_y = y_top - _box_y_off
                box_height = layout.box_height if layout else 0.7 * inch
                box_width = page_width - left_margin - right_margin

                # Dibujar el cuadro
                canvas.setStrokeColor(colors.black)
                canvas.setLineWidth(1)
                canvas.rect(left_margin, box_y - box_height, box_width, box_height)

                # Posiciones de columnas (proporcionales)
                col1_x = left_margin + (layout.box_col1_x if layout else 0.1*inch)
                col2_x = left_margin + (layout.box_col2_x if layout else 2.5*inch)
                col3_x = left_margin + (layout.box_col3_x if layout else 5.0*inch)
                _row_sp = layout.box_row_spacing if layout else 0.22*inch
                val_offset = layout.box_val_offset if layout else 0.55*inch
                _max_nom = layout.max_nombre_chars if layout else 35
                _max_med = layout.max_medico_chars if layout else 25
                _font_lbl = layout.font_pac_label if layout else 8
                _font_val = layout.font_pac_valor if layout else 8

                row1_y = box_y - 0.18*inch
                row2_y = row1_y - _row_sp
                row3_y = row2_y - _row_sp

                # Verificar si usamos 2 o 3 columnas
                _n_cols = layout.box_cols if layout else 3

                canvas.setFont('Helvetica-Bold', _font_lbl)

                if _n_cols == 3:
                    # ── Layout 3 columnas (Carta, A4, Oficio) ──
                    # Columna 1
                    canvas.drawString(col1_x, row1_y, "NOMBRE:")
                    canvas.drawString(col1_x, row2_y, "CÉDULA:")
                    canvas.drawString(col1_x, row3_y, "EDAD:")
                    # Columna 2
                    canvas.drawString(col2_x, row1_y, "GÉNERO:")
                    canvas.drawString(col2_x, row2_y, "MÉDICO:")
                    # Columna 3
                    canvas.drawString(col3_x, row1_y, "FECHA:")
                    canvas.drawString(col3_x, row2_y, "N° ORDEN:")
                    canvas.drawString(col3_x, row3_y, "TELÉFONO:")

                    # Valores
                    canvas.setFont('Helvetica', _font_val)
                    canvas.drawString(col1_x + val_offset, row1_y, nombre_paciente[:_max_nom])
                    canvas.drawString(col1_x + val_offset, row2_y, cedula)
                    canvas.drawString(col1_x + val_offset, row3_y, edad_texto)
                    canvas.drawString(col2_x + val_offset, row1_y, sexo)
                    canvas.drawString(col2_x + val_offset, row2_y, medico[:_max_med] if medico else '')
                    canvas.drawString(col3_x + val_offset, row1_y, fecha_sol)
                    canvas.drawString(col3_x + val_offset, row2_y, str(num_orden)[:20])
                    canvas.drawString(col3_x + val_offset, row3_y, telefono_pac[:15] if telefono_pac else '')

                else:
                    # ── Layout 2 columnas (Media Carta) ──
                    row4_y = row3_y - _row_sp
                    row5_y = row4_y - _row_sp
                    # Columna 1
                    canvas.drawString(col1_x, row1_y, "NOMBRE:")
                    canvas.drawString(col1_x, row2_y, "CÉDULA:")
                    canvas.drawString(col1_x, row3_y, "EDAD:")
                    canvas.drawString(col1_x, row4_y, "MÉDICO:")
                    # Columna 2
                    canvas.drawString(col2_x, row1_y, "FECHA:")
                    canvas.drawString(col2_x, row2_y, "N° ORDEN:")
                    canvas.drawString(col2_x, row3_y, "GÉNERO:")
                    canvas.drawString(col2_x, row4_y, "TELÉFONO:")

                    # Valores
                    canvas.setFont('Helvetica', _font_val)
                    canvas.drawString(col1_x + val_offset, row1_y, nombre_paciente[:_max_nom])
                    canvas.drawString(col1_x + val_offset, row2_y, cedula)
                    canvas.drawString(col1_x + val_offset, row3_y, edad_texto)
                    canvas.drawString(col1_x + val_offset, row4_y, medico[:_max_med] if medico else '')
                    canvas.drawString(col2_x + val_offset, row1_y, fecha_sol)
                    canvas.drawString(col2_x + val_offset, row2_y, str(num_orden)[:20])
                    canvas.drawString(col2_x + val_offset, row3_y, sexo)
                    canvas.drawString(col2_x + val_offset, row4_y, telefono_pac[:15] if telefono_pac else '')

                canvas.restoreState()

            # Función para dibujar el pie de página con firmas de bioanalistas
            def draw_footer(canvas, doc):
                canvas.saveState()

                footer_y = bottom_margin - 0.1*inch
                base_dir = os.path.dirname(os.path.abspath(__file__))

                # Obtener bioanalistas únicos de las áreas de esta solicitud
                bios_unicos = list(bioanalistas_por_area.values())

                if bios_unicos:
                    # Dibujar firmas de bioanalistas (proporcional al formato)
                    _max_firmas = layout.max_firmas if layout else 3
                    num_bios = min(len(bios_unicos), _max_firmas)
                    ancho_disponible = page_width - left_margin - right_margin
                    ancho_bloque = ancho_disponible / num_bios

                    _firma_w = layout.firma_img_width if layout else 1.2*inch
                    _firma_h = layout.firma_img_height if layout else 0.4*inch
                    _linea_w = layout.firma_linea_width if layout else 1.5*inch
                    _f_nombre = layout.font_bio_nombre if layout else 7
                    _f_detalle = layout.font_bio_detalle if layout else 6.5
                    _f_area = layout.font_bio_area if layout else 6

                    for idx, bio in enumerate(bios_unicos[:_max_firmas]):
                        bloque_x = left_margin + (idx * ancho_bloque) + (ancho_bloque / 2)

                        y_pos = footer_y + 0.9*inch

                        # Dibujar imagen de firma si existe
                        ruta_firma = bio.get('RutaFirma', '')
                        if ruta_firma:
                            ruta_abs_firma = os.path.join(base_dir, ruta_firma)
                            if os.path.exists(ruta_abs_firma):
                                try:
                                    canvas.drawImage(
                                        ruta_abs_firma,
                                        bloque_x - _firma_w/2,
                                        y_pos,
                                        width=_firma_w, height=_firma_h,
                                        preserveAspectRatio=True, mask='auto'
                                    )
                                    y_pos -= 0.05*inch
                                except Exception:
                                    pass

                        # Línea de firma
                        canvas.setStrokeColor(colors.grey)
                        canvas.setLineWidth(0.5)
                        canvas.line(bloque_x - _linea_w/2, y_pos, bloque_x + _linea_w/2, y_pos)

                        # Nombre del bioanalista
                        y_pos -= 0.12*inch
                        canvas.setFont('Helvetica-Bold', _f_nombre)
                        canvas.drawCentredString(bloque_x, y_pos, bio.get('NombreCompleto', ''))

                        # Cédula
                        y_pos -= 0.11*inch
                        canvas.setFont('Helvetica', _f_detalle)
                        canvas.drawCentredString(bloque_x, y_pos, f"C.I.: {bio.get('Cedula', '')}")

                        # Número de registro
                        y_pos -= 0.1*inch
                        canvas.drawCentredString(bloque_x, y_pos, f"Reg.: {bio.get('NumeroRegistro', '')}")

                        # Área
                        y_pos -= 0.1*inch
                        canvas.setFont('Helvetica-Oblique', _f_area)
                        area_nombre = bio.get('NombreArea', '')
                        if area_nombre:
                            canvas.drawCentredString(bloque_x, y_pos, f"Bioanalista - {area_nombre}")

                elif config_lab and config_lab.get('MostrarFirma'):
                    # Fallback: firma del Director (comportamiento original)
                    canvas.setFont('Helvetica', 7)
                    if config_lab.get('NombreDirector'):
                        canvas.drawRightString(page_width - right_margin, footer_y + 0.3*inch, config_lab['NombreDirector'])
                    if config_lab.get('TituloDirector'):
                        canvas.drawRightString(page_width - right_margin, footer_y + 0.15*inch, config_lab['TituloDirector'])

                canvas.restoreState()

            # Función combinada para header y footer
            def header_footer(canvas, doc):
                draw_header(canvas, doc)
                draw_footer(canvas, doc)

            # Crear el documento con template personalizado
            doc = BaseDocTemplate(filename, pagesize=page_size)

            # Frame para el contenido (después del encabezado)
            content_frame = Frame(
                left_margin,
                bottom_margin,
                page_width - left_margin - right_margin,
                page_height - top_margin - header_height - bottom_margin,
                id='content'
            )

            # Template de página
            page_template = PageTemplate(id='main', frames=[content_frame], onPage=header_footer)
            doc.addPageTemplates([page_template])

            styles = getSampleStyleSheet()
            elements = []

            # Estilos personalizados para formato CMLab (proporcionales)
            _ft_titulo = layout.font_titulo_prueba if layout else 11
            _ft_seccion = layout.font_seccion if layout else 9
            _sp_before = layout.space_before_titulo if layout else 12
            _sp_after = layout.space_after_titulo if layout else 8

            titulo_prueba_style = ParagraphStyle(
                'TituloPrueba',
                parent=styles['Heading2'],
                fontSize=_ft_titulo,
                fontName='Helvetica-Bold',
                alignment=TA_CENTER,
                spaceAfter=_sp_after,
                spaceBefore=_sp_before,
                textColor=colors.black
            )

            seccion_style = ParagraphStyle(
                'Seccion',
                parent=styles['Normal'],
                fontSize=_ft_seccion,
                fontName='Helvetica-Bold',
                alignment=TA_LEFT,
                spaceBefore=4,
                spaceAfter=2,
                textColor=colors.black
            )

            # Colores para antibiograma de microbiologia
            COLOR_SENSIBLE = colors.HexColor('#2e7d32')      # Verde
            COLOR_INTERMEDIO = colors.HexColor('#f57f17')     # Naranja/Amarillo
            COLOR_RESISTENTE = colors.HexColor('#c62828')     # Rojo
            COLOR_GERMEN = colors.HexColor('#b71c1c')         # Rojo oscuro
            COLOR_MICRO_HEADER = colors.HexColor('#1a237e')   # Azul oscuro
            COLOR_MICRO_SECCION = colors.HexColor('#455a64')  # Gris azulado

            # Procesar cada prueba
            for prueba in pruebas:
                detalle_id = prueba['DetalleID']
                prueba_id = prueba['PruebaID']
                nombre_prueba = (prueba.get('NombrePrueba') or '').upper()
                area_id = prueba.get('AreaID')

                # ==============================================================
                # GTT - PRUEBA DE TOLERANCIA A LA GLUCOSA
                # Formato especial con tabla de tiempos + grafica de curva
                # Genera elementos adicionales que se integran al PDF actual
                # (con grafica si el operador lo eligio previamente)
                # ==============================================================
                if GTT_DISPONIBLE and es_prueba_gtt(prueba):
                    try:
                        from modulos.gtt_reporte import (
                            TIEMPOS_DISPLAY, _generar_imagen_grafica,
                            COLOR_AZUL_OSCURO as GTT_AZUL, COLOR_AZUL_MEDIO as GTT_AZUL2,
                            COLOR_GRIS_CLARO as GTT_GRIS,
                            COLOR_ROJO as GTT_ROJO, COLOR_NARANJA as GTT_NARANJA,
                            COLOR_AZUL_BAJO as GTT_AZUL_BAJO, COLOR_VERDE as GTT_VERDE
                        )

                        # Recolectar valores GTT
                        codigos_gtt = ['GTT000', 'GTT001', 'GTT002', 'GTT003',
                                       'GTT004', 'GTT005', 'GTT006', 'GTT007', 'GTT008']
                        vals_gtt = {}
                        for cod in codigos_gtt:
                            par_gtt = db.query_one(
                                f"SELECT ParametroID FROM Parametros WHERE CodigoParametro = '{cod}'"
                            )
                            if not par_gtt:
                                continue
                            rp_gtt = db.query_one(
                                f"SELECT Valor, ValorReferencia, FueraDeRango, TipoAlerta "
                                f"FROM ResultadosParametros "
                                f"WHERE DetalleID = {detalle_id} AND ParametroID = {par_gtt['ParametroID']}"
                            )
                            if rp_gtt:
                                vals_gtt[cod] = rp_gtt

                        dosis_gtt = str((vals_gtt.get('GTT000') or {}).get('Valor') or '').strip()

                        # Titulo GTT
                        gtt_titulo_style = ParagraphStyle(
                            'TituloGTT_pdf', parent=styles['Heading1'],
                            fontSize=11, fontName='Helvetica-Bold',
                            alignment=TA_CENTER, spaceAfter=5, spaceBefore=8,
                            textColor=colors.white,
                            backColor=colors.HexColor('#1a237e'),
                            borderPadding=(6, 6, 6, 6),
                        )
                        elements.append(Paragraph(
                            "CURVA DE GLUCEMIA - TOLERANCIA A LA GLUCOSA", gtt_titulo_style
                        ))
                        elements.append(Spacer(1, 0.08*inch))

                        if dosis_gtt:
                            elements.append(Paragraph(
                                f"<b>Dosis de Carga Glucosada:</b> {dosis_gtt} g",
                                ParagraphStyle('DosisGTT', parent=styles['Normal'],
                                               fontSize=9, alignment=TA_CENTER,
                                               textColor=colors.HexColor('#1565c0'),
                                               spaceAfter=6)
                            ))

                        # Tabla resultados GTT (proporcional)
                        gtt_col_w = layout.gtt_col_widths if layout else [2.1*inch, 1.2*inch, 1.1*inch, 2.3*inch]
                        gtt_tabla = [['Tiempo', 'Resultado', 'Unidad', 'Valor de Referencia']]
                        gtt_estilos = []
                        gtt_row_idx = 1

                        for cod_t, etq_t, min_t, ref_t in TIEMPOS_DISPLAY:
                            rp_t = vals_gtt.get(cod_t)
                            if not rp_t:
                                continue
                            val_t = str(rp_t.get('Valor') or '').strip()
                            if not val_t:
                                continue
                            fuera_t = bool(rp_t.get('FueraDeRango'))
                            tipo_t = str(rp_t.get('TipoAlerta') or '')

                            gtt_tabla.append([etq_t, val_t, 'mg/dL', ref_t])

                            if fuera_t and 'Critico' in tipo_t:
                                gtt_estilos += [
                                    ('TEXTCOLOR', (1, gtt_row_idx), (1, gtt_row_idx), colors.HexColor('#c62828')),
                                    ('FONTNAME', (1, gtt_row_idx), (1, gtt_row_idx), 'Helvetica-Bold'),
                                    ('BACKGROUND', (0, gtt_row_idx), (-1, gtt_row_idx), colors.HexColor('#fff3e0')),
                                ]
                            elif fuera_t and 'Alto' in tipo_t:
                                gtt_estilos += [
                                    ('TEXTCOLOR', (1, gtt_row_idx), (1, gtt_row_idx), colors.HexColor('#e65100')),
                                    ('FONTNAME', (1, gtt_row_idx), (1, gtt_row_idx), 'Helvetica-Bold'),
                                ]
                            elif fuera_t:
                                gtt_estilos += [
                                    ('TEXTCOLOR', (1, gtt_row_idx), (1, gtt_row_idx), colors.HexColor('#1565c0')),
                                    ('FONTNAME', (1, gtt_row_idx), (1, gtt_row_idx), 'Helvetica-Bold'),
                                ]
                            else:
                                gtt_estilos += [
                                    ('TEXTCOLOR', (1, gtt_row_idx), (1, gtt_row_idx), colors.HexColor('#2e7d32')),
                                ]
                            gtt_row_idx += 1

                        if len(gtt_tabla) > 1:
                            gtt_t = Table(gtt_tabla, colWidths=gtt_col_w)
                            gtt_t.setStyle(TableStyle([
                                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, -1), 9),
                                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565c0')),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                                ('TOPPADDING', (0, 0), (-1, -1), 4),
                                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                                 [colors.white, colors.HexColor('#f5f5f5')]),
                                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                            ] + gtt_estilos))
                            elements.append(gtt_t)
                            elements.append(Spacer(1, 0.1*inch))

                        # Interpretacion
                        interp_gtt = str((vals_gtt.get('GTT007') or {}).get('Valor') or '').strip()
                        obs_gtt = str((vals_gtt.get('GTT008') or {}).get('Valor') or '').strip()
                        if interp_gtt:
                            elements.append(Paragraph(
                                f"<b>Interpretación:</b> {interp_gtt}",
                                ParagraphStyle('IntGTT', parent=styles['Normal'],
                                               fontSize=9, spaceAfter=3)
                            ))
                        if obs_gtt:
                            elements.append(Paragraph(
                                f"<b>Observaciones:</b> {obs_gtt}",
                                ParagraphStyle('ObsGTT', parent=styles['Normal'],
                                               fontSize=9, spaceAfter=3)
                            ))

                        # Grafica (siempre en el PDF general cuando hay datos)
                        img_gtt = _generar_imagen_grafica(vals_gtt, dosis_gtt)
                        if img_gtt:
                            gtt_grafica_w = layout.gtt_grafica_width if layout else ((page_width - left_margin - right_margin) - 0.3*inch)
                            gtt_grafica_h = layout.gtt_grafica_height if layout else 3.3 * inch
                            elements.append(Paragraph(
                                "Gráfica de la Curva de Glucemia",
                                ParagraphStyle('GTitGraf', parent=styles['Normal'],
                                               fontSize=9, fontName='Helvetica-Bold',
                                               textColor=colors.HexColor('#1565c0'),
                                               alignment=TA_CENTER, spaceBefore=6, spaceAfter=3)
                            ))
                            elements.append(RLImage(img_gtt,
                                                    width=gtt_grafica_w, height=gtt_grafica_h))
                            elements.append(Spacer(1, 0.06*inch))
                            elements.append(Paragraph(
                                "Ref. ADA: Basal <100 mg/dL normal; 2h <140 normal, "
                                "140-199 IGT, ≥200 Diabetes.",
                                ParagraphStyle('NotaGTT2', parent=styles['Normal'],
                                               fontSize=7, textColor=colors.grey,
                                               alignment=TA_CENTER)
                            ))

                    except Exception as _gtt_exc:
                        elements.append(Paragraph(
                            f"[Error generando sección GTT: {_gtt_exc}]",
                            styles['Normal']
                        ))
                    continue   # No usar el render generico para GTT

                # Obtener parámetros
                parametros = db.query(f"""
                    SELECT pp.ParametroID, par.NombreParametro, par.UnidadID,
                           par.Observaciones as ValorRef, par.Seccion
                    FROM ParametrosPrueba pp
                    INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID
                    WHERE pp.PruebaID = {prueba_id}
                    ORDER BY pp.Secuencia
                """)

                if not parametros:
                    continue

                # ================================================================
                # MICROBIOLOGIA / BACTERIOLOGIA (AreaID = 10)
                # Formato especial con antibiograma coloreado S/I/R
                # ================================================================
                if area_id == 10:
                    prueba_elements = []

                    # Titulo de la prueba con fondo azul oscuro
                    titulo_micro_style = ParagraphStyle(
                        'TituloMicro',
                        parent=styles['Heading2'],
                        fontSize=11,
                        fontName='Helvetica-Bold',
                        alignment=TA_CENTER,
                        spaceAfter=6,
                        spaceBefore=12,
                        textColor=colors.white,
                        backColor=COLOR_MICRO_HEADER,
                        borderPadding=(6, 6, 6, 6),
                    )
                    prueba_elements.append(Paragraph(nombre_prueba, titulo_micro_style))

                    # Clasificar parametros por seccion
                    secciones_micro = {}
                    for param in parametros:
                        resultado = db.query_one(f"""
                            SELECT Valor FROM ResultadosParametros
                            WHERE DetalleID = {detalle_id} AND ParametroID = {param['ParametroID']}
                        """)
                        valor = resultado.get('Valor') if resultado else ''
                        if valor is None:
                            valor = ''
                        valor_str = str(valor).strip()
                        if not valor_str:
                            continue

                        seccion = param.get('Seccion') or 'General'
                        if seccion not in secciones_micro:
                            secciones_micro[seccion] = []
                        secciones_micro[seccion].append({
                            'nombre': param['NombreParametro'] or '',
                            'valor': valor_str,
                            'valor_ref': param.get('ValorRef') or '',
                            'unidad_id': param.get('UnidadID'),
                        })

                    # Orden preferente de secciones
                    orden_secciones = [
                        'Tipo de Muestra', 'Datos de Muestra', 'Muestra',
                        'Cultivo', 'Resultado del Cultivo', 'Resultado',
                        'Identificacion', 'Identificacion del Germen', 'Germen Aislado',
                        'Recuento', 'Recuento de Colonias',
                        'Coloracion de Gram', 'Gram', 'Tincion de Gram',
                        'Antibiograma', 'Sensibilidad Antibiotica',
                        'Observaciones', 'General'
                    ]
                    secciones_ordenadas = []
                    for s in orden_secciones:
                        if s in secciones_micro:
                            secciones_ordenadas.append(s)
                    for s in secciones_micro:
                        if s not in secciones_ordenadas:
                            secciones_ordenadas.append(s)

                    tiene_contenido_micro = False

                    for seccion_nombre in secciones_ordenadas:
                        params_seccion = secciones_micro[seccion_nombre]
                        if not params_seccion:
                            continue
                        tiene_contenido_micro = True

                        seccion_upper = seccion_nombre.upper()
                        es_antibiograma = any(x in seccion_upper for x in [
                            'ANTIBIOGRAMA', 'SENSIBILIDAD', 'ANTIBIOTICO', 'SUSCEPTIBILIDAD'
                        ])

                        # Elementos de ESTA seccion (para KeepTogether por seccion, no por prueba completa)
                        seccion_elements = []

                        # Titulo de seccion con fondo gris azulado
                        seccion_micro_style = ParagraphStyle(
                            'SeccionMicro',
                            parent=styles['Normal'],
                            fontSize=9,
                            fontName='Helvetica-Bold',
                            alignment=TA_LEFT,
                            spaceBefore=8,
                            spaceAfter=3,
                            textColor=colors.white,
                            backColor=COLOR_MICRO_SECCION,
                            borderPadding=(4, 4, 4, 4),
                        )
                        seccion_elements.append(Paragraph(seccion_upper, seccion_micro_style))

                        if es_antibiograma:
                            # ---- TABLA DE ANTIBIOGRAMA con colores S/I/R ----
                            atb_header = [['Antibiotico', 'Resultado', 'Interpretacion']]
                            atb_col_widths = layout.atb_col_widths if layout else [3.0*inch, 1.5*inch, 2.0*inch]

                            atb_header_table = Table(atb_header, colWidths=atb_col_widths)
                            atb_header_table.setStyle(TableStyle([
                                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('FONTSIZE', (0, 0), (-1, 0), 9),
                                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
                                ('TOPPADDING', (0, 0), (-1, 0), 5),
                                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#263238')),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                            ]))
                            seccion_elements.append(atb_header_table)

                            atb_data = []
                            atb_colores = []  # (fila, color) para aplicar despues

                            for p in params_seccion:
                                valor_upper = p['valor'].upper().strip()
                                if valor_upper in ['S', 'SENSIBLE']:
                                    interpretacion = 'SENSIBLE'
                                    color_sir = COLOR_SENSIBLE
                                elif valor_upper in ['I', 'INTERMEDIO', 'SDD']:
                                    interpretacion = 'INTERMEDIO'
                                    color_sir = COLOR_INTERMEDIO
                                elif valor_upper in ['R', 'RESISTENTE']:
                                    interpretacion = 'RESISTENTE'
                                    color_sir = COLOR_RESISTENTE
                                else:
                                    interpretacion = p['valor']
                                    color_sir = colors.black

                                atb_data.append([
                                    '   ' + p['nombre'],
                                    p['valor'],
                                    interpretacion
                                ])
                                atb_colores.append(color_sir)

                            if atb_data:
                                atb_table = Table(atb_data, colWidths=atb_col_widths)
                                atb_style = [
                                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                                    ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                                    ('LEFTPADDING', (0, 0), (0, -1), 8),
                                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                                    ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
                                ]

                                # Aplicar colores por fila y fondo alterno
                                for idx, color_sir in enumerate(atb_colores):
                                    atb_style.append(('TEXTCOLOR', (1, idx), (2, idx), color_sir))
                                    atb_style.append(('FONTNAME', (1, idx), (2, idx), 'Helvetica-Bold'))
                                    if idx % 2 == 1:
                                        atb_style.append(('BACKGROUND', (0, idx), (-1, idx), colors.HexColor('#f5f5f5')))

                                atb_table.setStyle(TableStyle(atb_style))
                                seccion_elements.append(atb_table)

                        else:
                            # ---- SECCIONES NORMALES DE MICROBIOLOGIA ----
                            # (Datos de muestra, Gram, Germen, Recuento, etc.)
                            micro_data = []
                            micro_estilos_fila = []  # Para aplicar estilos especiales

                            for p in params_seccion:
                                nombre_upper = p['nombre'].upper()
                                es_germen = any(x in nombre_upper for x in [
                                    'GERMEN', 'MICROORGANISMO', 'AGENTE', 'BACTERIA',
                                    'ORGANISMO AISLADO', 'IDENTIFICACION'
                                ])
                                es_resultado_cultivo = any(x in nombre_upper for x in [
                                    'RESULTADO DEL CULTIVO', 'RESULTADO CULTIVO',
                                    'CRECIMIENTO', 'DESARROLLO BACTERIANO'
                                ])

                                unidad_texto = ""
                                if p.get('unidad_id'):
                                    unidad = db.query_one(f"SELECT Simbolo FROM Unidades WHERE UnidadID = {p['unidad_id']}")
                                    if unidad:
                                        unidad_texto = unidad.get('Simbolo') or ''

                                micro_data.append([
                                    '   ' + p['nombre'],
                                    p['valor'],
                                    unidad_texto,
                                    p['valor_ref']
                                ])
                                micro_estilos_fila.append({
                                    'es_germen': es_germen,
                                    'es_resultado_cultivo': es_resultado_cultivo
                                })

                            if micro_data:
                                micro_col_widths = layout.micro_col_widths if layout else [2.5*inch, 2.0*inch, 0.8*inch, 1.2*inch]
                                micro_table = Table(micro_data, colWidths=micro_col_widths)
                                micro_style = [
                                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                                    ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                                    ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                                    ('LEFTPADDING', (0, 0), (0, -1), 8),
                                    ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                                    ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#cccccc')),
                                ]

                                for idx, estilo in enumerate(micro_estilos_fila):
                                    if estilo['es_germen']:
                                        micro_style.append(('TEXTCOLOR', (1, idx), (1, idx), COLOR_GERMEN))
                                        micro_style.append(('FONTNAME', (0, idx), (1, idx), 'Helvetica-Bold'))
                                        micro_style.append(('FONTSIZE', (1, idx), (1, idx), 10))
                                    elif estilo['es_resultado_cultivo']:
                                        micro_style.append(('FONTNAME', (0, idx), (1, idx), 'Helvetica-Bold'))

                                micro_table.setStyle(TableStyle(micro_style))
                                seccion_elements.append(micro_table)

                        # Agregar los elementos de esta seccion al bloque de prueba
                        # Secciones pequenas (no antibiograma) se agrupan con KeepTogether
                        # Antibiogramas grandes se agregan directamente para permitir salto de pagina
                        if es_antibiograma and len(params_seccion) > 12:
                            # Antibiograma grande: header con KeepTogether, tabla suelta
                            if len(seccion_elements) > 1:
                                prueba_elements.append(KeepTogether([seccion_elements[0], seccion_elements[1]]))
                                for el in seccion_elements[2:]:
                                    prueba_elements.append(el)
                            else:
                                prueba_elements.extend(seccion_elements)
                        else:
                            # Seccion pequena: mantener todo junto
                            prueba_elements.append(KeepTogether(seccion_elements))

                    if tiene_contenido_micro:
                        prueba_elements.append(Spacer(1, 0.15*inch))
                        elements.extend(prueba_elements)

                    continue  # Saltar el renderizado generico

                # ================================================================
                # AREAS GENERICAS (no microbiologia)
                # ================================================================

                # Elementos de esta prueba (para mantenerlos juntos si es posible)
                prueba_elements = []

                # Título de la prueba centrado
                prueba_elements.append(Paragraph(nombre_prueba, titulo_prueba_style))

                # Encabezado de la tabla
                header_data = [['Descripción del Examen', 'Resultado', 'Unidad', 'Valores Referenciales']]

                # Anchos de columna (proporcionales al formato)
                col_widths = layout.col_widths if layout else [2.5*inch, 1.2*inch, 0.8*inch, 2.0*inch]

                _ft_hdr = layout.font_header_tabla if layout else 9
                header_table = Table(header_data, colWidths=col_widths)
                header_table.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), _ft_hdr),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TOPPADDING', (0, 0), (-1, 0), 6),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.white),
                ]))
                prueba_elements.append(header_table)

                # Datos de parámetros
                param_data = []
                seccion_actual = None

                for param in parametros:
                    # Obtener resultado primero para verificar si tiene valor
                    resultado = db.query_one(f"""
                        SELECT Valor FROM ResultadosParametros
                        WHERE DetalleID = {detalle_id} AND ParametroID = {param['ParametroID']}
                    """)
                    valor = resultado.get('Valor') if resultado else ''
                    if valor is None:
                        valor = ''

                    # IMPORTANTE: Solo incluir parámetros que tengan valor asignado
                    # Si no hay valor, saltar este parámetro (no aparece en el reporte)
                    valor_str = str(valor).strip()
                    if not valor_str:
                        continue  # No incluir parámetros sin valor en el reporte

                    # Verificar si hay cambio de sección
                    seccion = param.get('Seccion') or ''
                    if seccion and seccion != seccion_actual:
                        seccion_actual = seccion
                        # Agregar fila de sección
                        param_data.append([seccion.upper(), '', '', ''])

                    # Obtener unidad
                    unidad_texto = ""
                    if param.get('UnidadID'):
                        unidad = db.query_one(f"SELECT Simbolo FROM Unidades WHERE UnidadID = {param['UnidadID']}")
                        if unidad:
                            unidad_texto = unidad.get('Simbolo') or ''

                    valor_ref = param.get('ValorRef') or ''
                    nombre_param = '   ' + (param['NombreParametro'] or '')  # Indentación

                    param_data.append([
                        nombre_param,
                        valor_str,
                        unidad_texto,
                        valor_ref
                    ])

                # Filtrar filas de sección que quedaron sin parámetros después
                # (una sección es una fila donde resultado, unidad y referencia están vacíos)
                param_data_filtrado = []
                for i, row in enumerate(param_data):
                    es_seccion = row[1] == '' and row[2] == '' and row[3] == ''
                    if es_seccion:
                        # Verificar si hay al menos un parámetro después de esta sección
                        tiene_params = False
                        for j in range(i + 1, len(param_data)):
                            siguiente = param_data[j]
                            es_siguiente_seccion = siguiente[1] == '' and siguiente[2] == '' and siguiente[3] == ''
                            if es_siguiente_seccion:
                                break  # Llegamos a otra sección sin encontrar parámetros
                            tiene_params = True
                            break
                        if tiene_params:
                            param_data_filtrado.append(row)
                    else:
                        param_data_filtrado.append(row)

                # Solo agregar la prueba si tiene al menos un parámetro con valor
                # (no solo secciones vacías)
                tiene_resultados = any(row[1] != '' for row in param_data_filtrado)

                if param_data_filtrado and tiene_resultados:
                    param_table = Table(param_data_filtrado, colWidths=col_widths)

                    # Estilo base para datos (fuente proporcional)
                    _ft_datos = layout.font_datos_tabla if layout else 8
                    table_style = [
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), _ft_datos),
                        ('ALIGN', (1, 0), (1, -1), 'CENTER'),  # Resultado centrado
                        ('ALIGN', (2, 0), (2, -1), 'CENTER'),  # Unidad centrada
                        ('ALIGN', (3, 0), (3, -1), 'LEFT'),    # Valores ref a la izquierda
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (0, -1), 8),
                    ]

                    # Marcar filas de sección (negrita, sin indentación)
                    for i, row in enumerate(param_data_filtrado):
                        if row[1] == '' and row[2] == '' and row[3] == '':
                            # Es una fila de sección
                            table_style.append(('FONTNAME', (0, i), (0, i), 'Helvetica-Bold'))
                            table_style.append(('FONTSIZE', (0, i), (0, i), _ft_datos))

                    param_table.setStyle(TableStyle(table_style))
                    prueba_elements.append(param_table)

                    # Agregar espacio después de cada prueba
                    _sp_prueba = layout.space_after_prueba if layout else 0.15*inch
                    prueba_elements.append(Spacer(1, _sp_prueba))

                    # Intentar mantener la prueba junta
                    elements.append(KeepTogether(prueba_elements))

            # Pie de página con fecha de generación
            elements.append(Spacer(1, 0.3*inch))
            _ft_gen = layout.font_generado if layout else 7
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=_ft_gen,
                alignment=TA_CENTER,
                textColor=colors.grey
            )
            elements.append(Paragraph(f"Documento generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}", footer_style))
            elements.append(Paragraph("ANgesLAB - Sistema de Gestión de Laboratorio", footer_style))

            # Generar PDF
            doc.build(elements)

            if guardar_como:
                messagebox.showinfo("Éxito", f"PDF guardado en:\n{filename}")

            return filename

        except Exception as e:
            messagebox.showerror("Error", f"Error al generar PDF:\n{str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _imprimir_resultado_directo(self):
        """Genera el PDF de resultados y lo envía a la impresora configurada."""
        if not hasattr(self, 'sol_id_resultado') or not self.sol_id_resultado:
            messagebox.showwarning("Aviso", "Seleccione una solicitud primero.")
            return

        try:
            pdf_path = self.generar_pdf_resultados(guardar_como=False)
            if pdf_path:
                self.imprimir_pdf_en_impresora(pdf_path, tipo='resultados')
            else:
                messagebox.showerror("Error", "No se pudo generar el PDF de resultados.")
        except Exception as e:
            messagebox.showerror("Error", f"Error al imprimir resultados:\n{str(e)}")

    def enviar_whatsapp_resultado(self):
        """Envía el resultado por WhatsApp al paciente"""
        try:
            # Obtener datos del paciente
            sol = db.query_one(f"""
                SELECT s.NumeroSolicitud, p.Nombres, p.Apellidos, p.Telefono1
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.SolicitudID = {self.sol_id_resultado}
            """)

            if not sol:
                messagebox.showwarning("Aviso", "No se encontró la solicitud")
                return

            telefono = sol.get('Telefono1') or ''
            if not telefono:
                messagebox.showwarning("Aviso", "El paciente no tiene número de teléfono registrado.\n\nPor favor, actualice los datos del paciente.")
                return

            # Limpiar número de teléfono (solo dígitos)
            telefono_limpio = ''.join(filter(str.isdigit, telefono))

            # Si no tiene código de país, agregar el de Venezuela
            if len(telefono_limpio) == 10:
                telefono_limpio = '58' + telefono_limpio
            elif len(telefono_limpio) == 11 and telefono_limpio.startswith('0'):
                telefono_limpio = '58' + telefono_limpio[1:]

            # Generar PDF
            pdf_path = self.generar_pdf_resultados(guardar_como=False)
            if not pdf_path:
                return

            nombre_paciente = f"{sol.get('Nombres') or ''} {sol.get('Apellidos') or ''}".strip()

            # Crear mensaje
            mensaje = f"""Estimado/a {nombre_paciente},

Sus resultados de laboratorio (Solicitud N° {sol['NumeroSolicitud']}) están listos.

Por favor, revise el archivo PDF adjunto con sus resultados.

_ANgesLAB - Laboratorio Clínico_"""

            # Codificar mensaje para URL
            import urllib.parse
            mensaje_encoded = urllib.parse.quote(mensaje)

            # Abrir WhatsApp Web
            whatsapp_url = f"https://wa.me/{telefono_limpio}?text={mensaje_encoded}"
            webbrowser.open(whatsapp_url)

            # Mostrar instrucciones
            messagebox.showinfo("WhatsApp",
                f"Se ha abierto WhatsApp Web con el número:\n{telefono}\n\n"
                f"El PDF se ha guardado en:\n{pdf_path}\n\n"
                "Por favor, adjunte el PDF manualmente en la conversación de WhatsApp.")

        except Exception as e:
            messagebox.showerror("Error", f"Error al enviar por WhatsApp:\n{str(e)}")

    def enviar_email_resultado(self):
        """Envía el resultado por correo electrónico al paciente"""
        try:
            # Obtener datos del paciente
            sol = db.query_one(f"""
                SELECT s.NumeroSolicitud, p.Nombres, p.Apellidos, p.Email
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.SolicitudID = {self.sol_id_resultado}
            """)

            if not sol:
                messagebox.showwarning("Aviso", "No se encontró la solicitud")
                return

            email_paciente = sol.get('Email') or ''
            if not email_paciente:
                messagebox.showwarning("Aviso", "El paciente no tiene correo electrónico registrado.\n\nPor favor, actualice los datos del paciente.")
                return

            # Generar PDF primero
            pdf_path = self.generar_pdf_resultados(guardar_como=False)
            if not pdf_path:
                return

            nombre_paciente = f"{sol.get('Nombres') or ''} {sol.get('Apellidos') or ''}".strip()

            # Crear ventana de configuración de correo
            win = tk.Toplevel(self.root)
            win.title("Enviar Resultados por Email")
            win.configure(bg='white')
            win.grab_set()
            win.focus_set()
            hacer_ventana_responsiva(win, 550, 500, min_ancho=450, min_alto=400)

            tk.Label(win, text="Enviar Resultados por Email", font=('Segoe UI', 14, 'bold'),
                    bg='white', fg=COLORS['primary']).pack(pady=15)

            form = tk.Frame(win, bg='white')
            form.pack(fill='both', expand=True, padx=20)

            # Configuración del servidor SMTP
            tk.Label(form, text="Configuración del Servidor SMTP", font=('Segoe UI', 10, 'bold'),
                    bg='white', fg=COLORS['text']).pack(anchor='w', pady=(10, 5))

            smtp_frame = tk.Frame(form, bg='#f5f5f5', relief='solid', bd=1)
            smtp_frame.pack(fill='x', pady=5)

            # Servidor SMTP
            row1 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row1.pack(fill='x', padx=10, pady=5)
            tk.Label(row1, text="Servidor SMTP:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_servidor = tk.Entry(row1, font=('Segoe UI', 9), width=30)
            entry_servidor.insert(0, "smtp.gmail.com")
            entry_servidor.pack(side='left', padx=5)

            # Puerto
            row2 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row2.pack(fill='x', padx=10, pady=5)
            tk.Label(row2, text="Puerto:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_puerto = tk.Entry(row2, font=('Segoe UI', 9), width=10)
            entry_puerto.insert(0, "587")
            entry_puerto.pack(side='left', padx=5)

            # Email remitente
            row3 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row3.pack(fill='x', padx=10, pady=5)
            tk.Label(row3, text="Tu Email:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_email_from = tk.Entry(row3, font=('Segoe UI', 9), width=30)
            entry_email_from.pack(side='left', padx=5)

            # Contraseña
            row4 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row4.pack(fill='x', padx=10, pady=5)
            tk.Label(row4, text="Contraseña App:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_password = tk.Entry(row4, font=('Segoe UI', 9), width=30, show='*')
            entry_password.pack(side='left', padx=5)

            tk.Label(form, text="(Para Gmail, use una 'Contraseña de Aplicación')",
                    font=('Segoe UI', 8), bg='white', fg='gray').pack(anchor='w')

            # Datos del correo
            tk.Label(form, text="Datos del Correo", font=('Segoe UI', 10, 'bold'),
                    bg='white', fg=COLORS['text']).pack(anchor='w', pady=(15, 5))

            # Destinatario
            row5 = tk.Frame(form, bg='white')
            row5.pack(fill='x', pady=5)
            tk.Label(row5, text="Para:", font=('Segoe UI', 9), bg='white', width=10, anchor='w').pack(side='left')
            entry_email_to = tk.Entry(row5, font=('Segoe UI', 9), width=40)
            entry_email_to.insert(0, email_paciente)
            entry_email_to.pack(side='left', padx=5)

            # Asunto
            row6 = tk.Frame(form, bg='white')
            row6.pack(fill='x', pady=5)
            tk.Label(row6, text="Asunto:", font=('Segoe UI', 9), bg='white', width=10, anchor='w').pack(side='left')
            entry_asunto = tk.Entry(row6, font=('Segoe UI', 9), width=40)
            entry_asunto.insert(0, f"Resultados de Laboratorio - Solicitud N° {sol['NumeroSolicitud']}")
            entry_asunto.pack(side='left', padx=5)

            # Mensaje
            tk.Label(form, text="Mensaje:", font=('Segoe UI', 9), bg='white', anchor='w').pack(anchor='w', pady=(10, 5))
            txt_mensaje = tk.Text(form, font=('Segoe UI', 9), height=6, width=50)
            txt_mensaje.pack(fill='x', pady=5)
            txt_mensaje.insert('1.0', f"""Estimado/a {nombre_paciente},

Adjunto encontrará los resultados de sus análisis de laboratorio correspondientes a la Solicitud N° {sol['NumeroSolicitud']}.

Atentamente,
ANgesLAB - Laboratorio Clínico""")

            # PDF adjunto
            tk.Label(form, text=f"Archivo adjunto: {os.path.basename(pdf_path)}",
                    font=('Segoe UI', 8), bg='white', fg='gray').pack(anchor='w', pady=5)

            def enviar():
                try:
                    servidor = entry_servidor.get().strip()
                    puerto = int(entry_puerto.get().strip())
                    email_from = entry_email_from.get().strip()
                    password = entry_password.get()
                    email_to = entry_email_to.get().strip()
                    asunto = entry_asunto.get().strip()
                    mensaje = txt_mensaje.get('1.0', 'end').strip()

                    if not all([servidor, email_from, password, email_to, asunto]):
                        messagebox.showwarning("Aviso", "Complete todos los campos obligatorios")
                        return

                    # Crear mensaje
                    msg = MIMEMultipart()
                    msg['From'] = email_from
                    msg['To'] = email_to
                    msg['Subject'] = asunto

                    msg.attach(MIMEText(mensaje, 'plain'))

                    # Adjuntar PDF
                    with open(pdf_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition',
                                       f'attachment; filename="{os.path.basename(pdf_path)}"')
                        msg.attach(part)

                    # Enviar
                    with smtplib.SMTP(servidor, puerto) as server:
                        server.starttls()
                        server.login(email_from, password)
                        server.send_message(msg)

                    messagebox.showinfo("Éxito", f"Correo enviado exitosamente a:\n{email_to}")
                    win.destroy()

                except smtplib.SMTPAuthenticationError:
                    messagebox.showerror("Error", "Error de autenticación.\n\nPara Gmail:\n1. Active la verificación en 2 pasos\n2. Genere una 'Contraseña de aplicación'\n3. Use esa contraseña aquí")
                except Exception as e:
                    messagebox.showerror("Error", f"Error al enviar correo:\n{str(e)}")

            # Botones
            btn_frame = tk.Frame(win, bg='white')
            btn_frame.pack(pady=15)

            tk.Button(btn_frame, text="Enviar", font=('Segoe UI', 10, 'bold'),
                     bg=COLORS['success'], fg='white', relief='flat', width=12,
                     command=enviar).pack(side='left', padx=10)

            tk.Button(btn_frame, text="Cancelar", font=('Segoe UI', 10),
                     bg=COLORS['danger'], fg='white', relief='flat', width=12,
                     command=win.destroy).pack(side='left', padx=10)

        except Exception as e:
            messagebox.showerror("Error", f"Error:\n{str(e)}")

    def enviar_whatsapp_medico(self):
        """Envía el resultado por WhatsApp al médico de la solicitud"""
        try:
            # Obtener datos de la solicitud con el médico
            sol = db.query_one(f"""
                SELECT s.NumeroSolicitud, s.MedicoID,
                       p.Nombres & ' ' & p.Apellidos AS Paciente,
                       m.Nombres & ' ' & m.Apellidos AS NombreMedico,
                       m.Telefono1 AS TelefonoMedico, m.Email AS EmailMedico
                FROM (Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID)
                LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
                WHERE s.SolicitudID = {self.sol_id_resultado}
            """)

            if not sol:
                messagebox.showwarning("Aviso", "No se encontró la solicitud")
                return

            if not sol.get('MedicoID'):
                messagebox.showwarning("Aviso", "Esta solicitud no tiene un médico asignado.\n\nPor favor, asigne un médico a la solicitud.")
                return

            telefono_medico = sol.get('TelefonoMedico') or ''
            if not telefono_medico:
                messagebox.showwarning("Aviso", f"El médico {sol.get('NombreMedico', '')} no tiene número de teléfono registrado.\n\nPor favor, actualice los datos del médico.")
                return

            # Limpiar número de teléfono (solo dígitos)
            telefono_limpio = ''.join(filter(str.isdigit, telefono_medico))

            # Si no tiene código de país, agregar el de Venezuela
            if len(telefono_limpio) == 10:
                telefono_limpio = '58' + telefono_limpio
            elif len(telefono_limpio) == 11 and telefono_limpio.startswith('0'):
                telefono_limpio = '58' + telefono_limpio[1:]

            # Generar PDF
            pdf_path = self.generar_pdf_resultados(guardar_como=False)
            if not pdf_path:
                return

            nombre_paciente = sol.get('Paciente') or 'N/A'
            nombre_medico = sol.get('NombreMedico') or 'Dr.'

            # Crear mensaje
            mensaje = f"""Estimado/a Dr. {nombre_medico},

Le enviamos los resultados de laboratorio del paciente {nombre_paciente} (Solicitud N° {sol['NumeroSolicitud']}).

Por favor, revise el archivo PDF adjunto con los resultados.

_ANgesLAB - Laboratorio Clínico_"""

            # Codificar mensaje para URL
            import urllib.parse
            mensaje_encoded = urllib.parse.quote(mensaje)

            # Abrir WhatsApp Web
            whatsapp_url = f"https://wa.me/{telefono_limpio}?text={mensaje_encoded}"
            webbrowser.open(whatsapp_url)

            # Mostrar instrucciones
            messagebox.showinfo("WhatsApp - Médico",
                f"Se ha abierto WhatsApp Web con el número del médico:\n{telefono_medico}\n\n"
                f"Médico: {nombre_medico}\n"
                f"Paciente: {nombre_paciente}\n\n"
                f"El PDF se ha guardado en:\n{pdf_path}\n\n"
                "Por favor, adjunte el PDF manualmente en la conversación de WhatsApp.")

        except Exception as e:
            messagebox.showerror("Error", f"Error al enviar por WhatsApp al médico:\n{str(e)}")

    def enviar_email_medico(self):
        """Envía el resultado por correo electrónico al médico de la solicitud"""
        try:
            sol = db.query_one(f"""
                SELECT s.NumeroSolicitud, s.MedicoID,
                       p.Nombres & ' ' & p.Apellidos AS Paciente,
                       m.Nombres & ' ' & m.Apellidos AS NombreMedico,
                       m.Email AS EmailMedico
                FROM (Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID)
                LEFT JOIN Medicos m ON s.MedicoID = m.MedicoID
                WHERE s.SolicitudID = {self.sol_id_resultado}
            """)

            if not sol:
                messagebox.showwarning("Aviso", "No se encontró la solicitud")
                return

            if not sol.get('MedicoID'):
                messagebox.showwarning("Aviso", "Esta solicitud no tiene un médico asignado.\n\nPor favor, asigne un médico a la solicitud.")
                return

            email_medico = sol.get('EmailMedico') or ''
            if not email_medico:
                messagebox.showwarning("Aviso", f"El médico {sol.get('NombreMedico', '')} no tiene correo electrónico registrado.\n\nPor favor, actualice los datos del médico.")
                return

            # Generar PDF
            pdf_path = self.generar_pdf_resultados(guardar_como=False)
            if not pdf_path:
                return

            nombre_paciente = sol.get('Paciente') or 'N/A'
            nombre_medico = sol.get('NombreMedico') or 'Dr.'

            # Crear ventana de configuración de correo
            win = tk.Toplevel(self.root)
            win.title("Enviar Resultados al Médico por Email")
            win.configure(bg='white')
            win.grab_set()
            win.focus_set()
            hacer_ventana_responsiva(win, 550, 500, min_ancho=450, min_alto=400)

            tk.Label(win, text="Enviar Resultados al Médico", font=('Segoe UI', 14, 'bold'),
                    bg='white', fg=COLORS['primary']).pack(pady=15)

            form = tk.Frame(win, bg='white')
            form.pack(fill='both', expand=True, padx=20)

            # Configuración SMTP
            tk.Label(form, text="Configuración del Servidor SMTP", font=('Segoe UI', 10, 'bold'),
                    bg='white', fg=COLORS['text']).pack(anchor='w', pady=(10, 5))

            smtp_frame = tk.Frame(form, bg='#f5f5f5', relief='solid', bd=1)
            smtp_frame.pack(fill='x', pady=5)

            row1 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row1.pack(fill='x', padx=10, pady=5)
            tk.Label(row1, text="Servidor SMTP:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_servidor = tk.Entry(row1, font=('Segoe UI', 9), width=30)
            entry_servidor.insert(0, "smtp.gmail.com")
            entry_servidor.pack(side='left', padx=5)

            row2 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row2.pack(fill='x', padx=10, pady=5)
            tk.Label(row2, text="Puerto:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_puerto = tk.Entry(row2, font=('Segoe UI', 9), width=10)
            entry_puerto.insert(0, "587")
            entry_puerto.pack(side='left', padx=5)

            row3 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row3.pack(fill='x', padx=10, pady=5)
            tk.Label(row3, text="Tu Email:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_email_from = tk.Entry(row3, font=('Segoe UI', 9), width=30)
            entry_email_from.pack(side='left', padx=5)

            row4 = tk.Frame(smtp_frame, bg='#f5f5f5')
            row4.pack(fill='x', padx=10, pady=5)
            tk.Label(row4, text="Contraseña App:", font=('Segoe UI', 9), bg='#f5f5f5', width=15, anchor='w').pack(side='left')
            entry_password = tk.Entry(row4, font=('Segoe UI', 9), width=30, show='*')
            entry_password.pack(side='left', padx=5)

            tk.Label(form, text="(Para Gmail, use una 'Contraseña de Aplicación')",
                    font=('Segoe UI', 8), bg='white', fg='gray').pack(anchor='w')

            # Datos del correo
            tk.Label(form, text="Datos del Correo", font=('Segoe UI', 10, 'bold'),
                    bg='white', fg=COLORS['text']).pack(anchor='w', pady=(15, 5))

            row5 = tk.Frame(form, bg='white')
            row5.pack(fill='x', pady=5)
            tk.Label(row5, text="Para:", font=('Segoe UI', 9), bg='white', width=10, anchor='w').pack(side='left')
            entry_email_to = tk.Entry(row5, font=('Segoe UI', 9), width=40)
            entry_email_to.insert(0, email_medico)
            entry_email_to.pack(side='left', padx=5)

            row6 = tk.Frame(form, bg='white')
            row6.pack(fill='x', pady=5)
            tk.Label(row6, text="Asunto:", font=('Segoe UI', 9), bg='white', width=10, anchor='w').pack(side='left')
            entry_asunto = tk.Entry(row6, font=('Segoe UI', 9), width=40)
            entry_asunto.insert(0, f"Resultados de Laboratorio - Paciente: {nombre_paciente} - Solicitud N° {sol['NumeroSolicitud']}")
            entry_asunto.pack(side='left', padx=5)

            tk.Label(form, text="Mensaje:", font=('Segoe UI', 9), bg='white', anchor='w').pack(anchor='w', pady=(10, 5))
            txt_mensaje = tk.Text(form, font=('Segoe UI', 9), height=6, width=50)
            txt_mensaje.pack(fill='x', pady=5)
            txt_mensaje.insert('1.0', f"""Estimado/a Dr. {nombre_medico},

Adjunto encontrará los resultados de laboratorio del paciente {nombre_paciente} correspondientes a la Solicitud N° {sol['NumeroSolicitud']}.

Por favor, revise el archivo PDF adjunto.

Atentamente,
ANgesLAB - Laboratorio Clínico""")

            tk.Label(form, text=f"Archivo adjunto: {os.path.basename(pdf_path)}",
                    font=('Segoe UI', 8), bg='white', fg='gray').pack(anchor='w', pady=5)

            def enviar():
                try:
                    servidor = entry_servidor.get().strip()
                    puerto = int(entry_puerto.get().strip())
                    email_from = entry_email_from.get().strip()
                    password = entry_password.get()
                    email_to = entry_email_to.get().strip()
                    asunto = entry_asunto.get().strip()
                    mensaje = txt_mensaje.get('1.0', 'end').strip()

                    if not all([servidor, email_from, password, email_to, asunto]):
                        messagebox.showwarning("Aviso", "Complete todos los campos obligatorios")
                        return

                    msg = MIMEMultipart()
                    msg['From'] = email_from
                    msg['To'] = email_to
                    msg['Subject'] = asunto
                    msg.attach(MIMEText(mensaje, 'plain'))

                    with open(pdf_path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition',
                                       f'attachment; filename="{os.path.basename(pdf_path)}"')
                        msg.attach(part)

                    with smtplib.SMTP(servidor, puerto) as server:
                        server.starttls()
                        server.login(email_from, password)
                        server.send_message(msg)

                    messagebox.showinfo("Éxito", f"Correo enviado exitosamente al médico:\n{nombre_medico}\n({email_to})")
                    win.destroy()

                except smtplib.SMTPAuthenticationError:
                    messagebox.showerror("Error", "Error de autenticación.\n\nPara Gmail:\n1. Active la verificación en 2 pasos\n2. Genere una 'Contraseña de aplicación'\n3. Use esa contraseña aquí")
                except Exception as e:
                    messagebox.showerror("Error", f"Error al enviar correo:\n{str(e)}")

            btn_frame = tk.Frame(win, bg='white')
            btn_frame.pack(pady=15)

            tk.Button(btn_frame, text="Enviar", font=('Segoe UI', 10, 'bold'),
                     bg=COLORS['success'], fg='white', relief='flat', width=12,
                     command=enviar).pack(side='left', padx=10)

            tk.Button(btn_frame, text="Cancelar", font=('Segoe UI', 10),
                     bg=COLORS['danger'], fg='white', relief='flat', width=12,
                     command=win.destroy).pack(side='left', padx=10)

        except Exception as e:
            messagebox.showerror("Error", f"Error:\n{str(e)}")

    # ============================================================
    # HISTORIAL CLINICO
    # ============================================================

    def show_historial_clinico(self):
        """Vista principal del historial clinico de pacientes."""
        self.clear_content()
        self.set_title("📊 Historial Clínico")

        main_frame = tk.Frame(self.content, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True)

        # ====== COLUMNA IZQUIERDA - Busqueda de paciente (350px) ======
        left_frame = tk.Frame(main_frame, bg='white', width=350)
        left_frame.pack(side='left', fill='y', padx=(0, 10), pady=0)
        left_frame.pack_propagate(False)

        search_frame = tk.Frame(left_frame, bg='white')
        search_frame.pack(fill='x', padx=15, pady=15)

        tk.Label(search_frame, text="🔍 Buscar Paciente:",
                 font=('Segoe UI', 11, 'bold'), bg='white').pack(anchor='w', pady=(0, 8))

        entry_frame = tk.Frame(search_frame, bg='white')
        entry_frame.pack(fill='x')

        self.entry_buscar_hist = tk.Entry(
            entry_frame, font=('Segoe UI', 11), relief='flat',
            bg='#f8f9fa', highlightthickness=1,
            highlightbackground=COLORS['border']
        )
        self.entry_buscar_hist.pack(side='left', fill='x', expand=True, ipady=6)
        self.entry_buscar_hist.bind('<Return>', lambda e: self._buscar_pacientes_historial())
        self.entry_buscar_hist.bind('<KeyRelease>', lambda e: self._buscar_pacientes_historial())

        tk.Label(left_frame, text="👥 Pacientes:",
                 font=('Segoe UI', 10, 'bold'),
                 bg='white').pack(anchor='w', padx=15, pady=(10, 5))

        list_frame = tk.Frame(left_frame, bg='white')
        list_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        cols_pac = ('Documento', 'Nombre')
        self.tree_pac_hist = ttk.Treeview(
            list_frame, columns=cols_pac, show='headings', height=15
        )
        self.tree_pac_hist.heading('Documento', text='Documento')
        self.tree_pac_hist.heading('Nombre', text='Nombre')
        self.tree_pac_hist.column('Documento', width=100)
        self.tree_pac_hist.column('Nombre', width=210)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_pac_hist.yview)
        self.tree_pac_hist.configure(yscrollcommand=vsb.set)
        self.tree_pac_hist.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.tree_pac_hist.bind('<<TreeviewSelect>>', self._on_paciente_historial_seleccionado)

        self.pac_hist_map = {}
        self._cargar_pacientes_historial()

        # ====== COLUMNA DERECHA - Detalle del historial ======
        right_frame = tk.Frame(main_frame, bg='white')
        right_frame.pack(side='left', fill='both', expand=True)

        self.hist_info_frame = tk.Frame(right_frame, bg=COLORS['primary'])
        self.hist_info_frame.pack(fill='x')

        self.lbl_hist_paciente = tk.Label(
            self.hist_info_frame,
            text="Seleccione un paciente para ver su historial clínico",
            font=('Segoe UI', 12), bg=COLORS['primary'], fg='white'
        )
        self.lbl_hist_paciente.pack(pady=15)

        self.hist_content_frame = tk.Frame(right_frame, bg='white')
        self.hist_content_frame.pack(fill='both', expand=True)

        # Tabs
        self.hist_tabs_frame = tk.Frame(self.hist_content_frame, bg='#e2e8f0')
        self.hist_tabs_frame.pack(fill='x')

        self.hist_tab_buttons = {}
        self.hist_current_tab = None
        self.hist_paciente_id = None

        tabs = [
            ('resumen', '📊 Resumen'),
            ('historial', '📋 Historial'),
            ('comparativa', '🔀 Comparativa'),
            ('evolucion', '🔄 Evolución'),
            ('graficas', '📈 Gráficas'),
            ('ia_clinica', '🤖 IA Clínica'),
        ]
        for tab_key, tab_text in tabs:
            btn = tk.Button(
                self.hist_tabs_frame, text=tab_text,
                font=('Segoe UI', 10), bg='#e2e8f0', fg=COLORS['text'],
                relief='flat', padx=20, pady=8, cursor='hand2',
                command=lambda k=tab_key: self._cambiar_tab_historial(k)
            )
            btn.pack(side='left', padx=2, pady=2)
            self.hist_tab_buttons[tab_key] = btn

        self.hist_detail_frame = tk.Frame(self.hist_content_frame, bg='white')
        self.hist_detail_frame.pack(fill='both', expand=True, padx=15, pady=15)

        tk.Label(
            self.hist_detail_frame,
            text="👆 Seleccione un paciente de la lista\npara ver su historial clínico",
            font=('Segoe UI', 12), bg='white',
            fg=COLORS['text_light'], justify='center'
        ).pack(pady=100)

    def _cargar_pacientes_historial(self, filtro=""):
        """Carga la lista de pacientes en el panel izquierdo del historial."""
        for item in self.tree_pac_hist.get_children():
            self.tree_pac_hist.delete(item)

        filtro_safe = filtro.replace("'", "''")
        where = ""
        if filtro_safe:
            where = (f"WHERE Nombres LIKE '%{filtro_safe}%' "
                     f"OR Apellidos LIKE '%{filtro_safe}%' "
                     f"OR NumeroDocumento LIKE '%{filtro_safe}%'")
        try:
            data = db.query(
                f"SELECT TOP 100 PacienteID, NumeroDocumento, "
                f"Nombres & ' ' & Apellidos AS NombreCompleto "
                f"FROM Pacientes {where} "
                f"ORDER BY Apellidos, Nombres"
            )
            self.pac_hist_map = {}
            for r in (data or []):
                iid = self.tree_pac_hist.insert('', 'end', values=(
                    r.get('NumeroDocumento') or '',
                    (r.get('NombreCompleto') or 'N/A')[:30],
                ))
                self.pac_hist_map[iid] = r['PacienteID']
        except Exception as e:
            print(f"Error cargando pacientes historial: {e}")

    def _buscar_pacientes_historial(self):
        """Filtra pacientes por texto de busqueda."""
        filtro = self.entry_buscar_hist.get().strip()
        self._cargar_pacientes_historial(filtro)

    def _on_paciente_historial_seleccionado(self, event=None):
        """Cuando se selecciona un paciente, carga su historial."""
        sel = self.tree_pac_hist.selection()
        if not sel:
            return

        paciente_id = self.pac_hist_map.get(sel[0])
        if not paciente_id:
            return

        self.hist_paciente_id = paciente_id

        try:
            pac = db.query_one(
                f"SELECT Nombres & ' ' & Apellidos AS Nombre, "
                f"NumeroDocumento, FechaNacimiento, Sexo "
                f"FROM Pacientes WHERE PacienteID = {paciente_id}"
            )
            if pac:
                edad = ""
                if pac.get('FechaNacimiento'):
                    try:
                        fn = pac['FechaNacimiento']
                        hoy = datetime.now()
                        edad_val = hoy.year - fn.year - (
                            (hoy.month, hoy.day) < (fn.month, fn.day)
                        )
                        edad = f" | {edad_val} años"
                    except:
                        pass
                sexo = f" | {pac.get('Sexo', '')}" if pac.get('Sexo') else ""
                doc = f" | {pac.get('NumeroDocumento', '')}" if pac.get('NumeroDocumento') else ""
                self.lbl_hist_paciente.config(
                    text=f"{pac.get('Nombre', 'N/A')}{doc}{edad}{sexo}"
                )
        except:
            pass

        self._cambiar_tab_historial('resumen')

    def _cambiar_tab_historial(self, tab_key):
        """Cambia entre las sub-vistas del historial."""
        if not self.hist_paciente_id:
            return

        for key, btn in self.hist_tab_buttons.items():
            if key == tab_key:
                btn.config(bg=COLORS['primary'], fg='white',
                           font=('Segoe UI', 10, 'bold'))
            else:
                btn.config(bg='#e2e8f0', fg=COLORS['text'],
                           font=('Segoe UI', 10))

        self.hist_current_tab = tab_key

        for w in self.hist_detail_frame.winfo_children():
            w.destroy()

        if tab_key == 'resumen':
            self._render_historial_resumen()
        elif tab_key == 'historial':
            self._render_historial_cronologico()
        elif tab_key == 'comparativa':
            self._render_historial_comparativa()
        elif tab_key == 'evolucion':
            self._render_historial_evolucion()
        elif tab_key == 'graficas':
            self._render_historial_graficas()
        elif tab_key == 'ia_clinica':
            self._render_historial_ia_clinica()

    def _render_historial_resumen(self):
        """Renderiza la vista de resumen del paciente."""
        if not HISTORIAL_CLINICO_DISPONIBLE or not self.gestor_historial:
            tk.Label(self.hist_detail_frame,
                     text="Módulo de historial no disponible",
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['danger']).pack(pady=50)
            return

        result = self.gestor_historial.obtener_resumen_paciente(self.hist_paciente_id)

        if not result.get('exito'):
            tk.Label(self.hist_detail_frame,
                     text=result.get('mensaje', 'Error'),
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['danger']).pack(pady=50)
            return

        datos = result['datos']

        # Scrollable
        canvas = tk.Canvas(self.hist_detail_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.hist_detail_frame, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg='white')
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', _on_canvas_configure)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # Tarjetas KPI
        cards_frame = tk.Frame(scroll_frame, bg='white')
        cards_frame.pack(fill='x', pady=(0, 15))

        primera_visita_str = "---"
        if datos.get('primera_visita'):
            try:
                primera_visita_str = datos['primera_visita'].strftime('%d/%m/%Y')
            except:
                primera_visita_str = str(datos['primera_visita'])[:10]

        ultima_visita_str = "Sin visitas"
        if datos.get('ultima_visita'):
            try:
                ultima_visita_str = datos['ultima_visita'].strftime('%d/%m/%Y')
            except:
                ultima_visita_str = str(datos['ultima_visita'])[:10]

        stats = [
            ("\U0001f4cb", "Solicitudes", datos['total_solicitudes'], COLORS['primary']),
            ("\U0001f4c5", "Primera Visita", primera_visita_str, '#6366f1'),
            ("\U0001f4c5", "Última Visita", ultima_visita_str, COLORS['success']),
            ("\U0001f52c", "Parámetros", datos['total_parametros_capturados'], COLORS['warning']),
        ]

        for icon, label, value, color in stats:
            card = tk.Frame(cards_frame, bg='white', highlightbackground=COLORS['border'],
                            highlightthickness=1)
            card.pack(side='left', expand=True, fill='both', padx=6, pady=5)
            inner = tk.Frame(card, bg='white')
            inner.pack(padx=15, pady=12, fill='both', expand=True)
            tk.Label(inner, text=icon, font=('Segoe UI', 20), bg='white', fg=color).pack(anchor='w')
            tk.Label(inner, text=str(value), font=('Segoe UI', 16, 'bold'),
                     bg='white', fg=COLORS['text']).pack(anchor='w')
            tk.Label(inner, text=label, font=('Segoe UI', 9),
                     bg='white', fg=COLORS['text_light']).pack(anchor='w')
            tk.Frame(card, bg=color, height=3).pack(fill='x', side='bottom')

        # ====== Alertas (parametros fuera de rango) ======
        alertas = datos.get('alertas_recientes') or []
        if alertas:
            alerta_frame = tk.LabelFrame(scroll_frame,
                text=" \u26a0 Alertas - Parámetros Fuera de Rango (Última Solicitud) ",
                font=('Segoe UI', 11, 'bold'), bg='white', fg='#c62828')
            alerta_frame.pack(fill='x', pady=(5, 10), padx=5)

            # Encabezado tabla alertas
            ah_row = tk.Frame(alerta_frame, bg='#ffebee')
            ah_row.pack(fill='x', padx=8, pady=(5, 0))
            for txt, w in [("Parámetro", 20), ("Valor", 10), ("Unidad", 8), ("Referencia", 20), ("Estado", 6)]:
                tk.Label(ah_row, text=txt, font=('Segoe UI', 9, 'bold'),
                         bg='#ffebee', fg='#b71c1c', width=w, anchor='w').pack(side='left', padx=2, pady=3)

            for i, al in enumerate(alertas):
                es_critico = al.get('critico', False)
                bg_al = '#fff3e0' if es_critico else ('#fff5f5' if i % 2 == 0 else 'white')
                val_color_al = '#e65100' if es_critico else '#c62828'
                ar = tk.Frame(alerta_frame, bg=bg_al)
                ar.pack(fill='x', padx=8)
                nombre_txt = al.get('parametro', '')
                if es_critico:
                    nombre_txt = '\u26a0 ' + nombre_txt
                tk.Label(ar, text=nombre_txt, font=('Segoe UI', 9, 'bold' if es_critico else 'normal'),
                         bg=bg_al, width=22, anchor='w').pack(side='left', padx=2, pady=2)
                tk.Label(ar, text=al.get('valor', ''), font=('Segoe UI', 9, 'bold'),
                         bg=bg_al, fg=val_color_al, width=10, anchor='w').pack(side='left', padx=2, pady=2)
                tk.Label(ar, text=al.get('unidad', ''), font=('Segoe UI', 9),
                         bg=bg_al, fg='#666', width=8, anchor='w').pack(side='left', padx=2, pady=2)
                tk.Label(ar, text=al.get('referencia', ''), font=('Segoe UI', 9),
                         bg=bg_al, fg='#1565c0', width=18, anchor='w').pack(side='left', padx=2, pady=2)
                tipo_txt = "\u2b06 Alto" if al.get('tipo') == 'alto' else "\u2b07 Bajo"
                tipo_color = '#c62828' if al.get('tipo') == 'alto' else '#1565c0'
                tk.Label(ar, text=tipo_txt, font=('Segoe UI', 9, 'bold'),
                         bg=bg_al, fg=tipo_color, width=6).pack(side='left', padx=2, pady=2)

            tk.Label(alerta_frame, text="", bg='white').pack(pady=2)

        # ====== Alertas historicas (ultimas 5 solicitudes) ======
        if self.gestor_historial:
            alertas_hist = self.gestor_historial.obtener_alertas_historicas(
                self.hist_paciente_id, max_solicitudes=5
            )
            if alertas_hist:
                ah_frame = tk.LabelFrame(scroll_frame,
                    text=" 📜 Alertas Históricas (Últimas 5 Solicitudes) ",
                    font=('Segoe UI', 11, 'bold'), bg='white', fg='#7b1fa2')
                ah_frame.pack(fill='x', pady=(5, 10), padx=5)

                ah_head = tk.Frame(ah_frame, bg='#f3e5f5')
                ah_head.pack(fill='x', padx=8, pady=(5, 0))
                for txt, w in [("Parámetro", 20), ("Valor", 10), ("Unidad", 8), ("Ref.", 18), ("Estado", 7), ("Fecha", 11), ("Solicitud", 12)]:
                    tk.Label(ah_head, text=txt, font=('Segoe UI', 8, 'bold'),
                             bg='#f3e5f5', fg='#6a1b9a', width=w, anchor='w').pack(side='left', padx=2, pady=3)

                for i, al in enumerate(alertas_hist):
                    es_critico = al.get('critico', False)
                    bg_ah = '#fff3e0' if es_critico else ('#fce4ec' if al.get('tipo') == 'alto' else '#e8f5e9')
                    ar = tk.Frame(ah_frame, bg=bg_ah)
                    ar.pack(fill='x', padx=8)
                    nombre_ah = al.get('parametro', '')
                    if es_critico:
                        nombre_ah = '\u26a0 ' + nombre_ah
                    tk.Label(ar, text=nombre_ah, font=('Segoe UI', 8, 'bold' if es_critico else 'normal'),
                             bg=bg_ah, width=22, anchor='w').pack(side='left', padx=2, pady=2)
                    val_fg_ah = '#e65100' if es_critico else ('#c62828' if al.get('tipo') == 'alto' else '#1565c0')
                    tk.Label(ar, text=al.get('valor', ''), font=('Segoe UI', 8, 'bold'),
                             bg=bg_ah, fg=val_fg_ah, width=10, anchor='w').pack(side='left', padx=2, pady=2)
                    tk.Label(ar, text=al.get('unidad', ''), font=('Segoe UI', 8),
                             bg=bg_ah, fg='#666', width=8, anchor='w').pack(side='left', padx=2, pady=2)
                    tk.Label(ar, text=al.get('referencia', ''), font=('Segoe UI', 8),
                             bg=bg_ah, fg='#555', width=18, anchor='w').pack(side='left', padx=2, pady=2)
                    tipo_ah = "\u2b06 Alto" if al.get('tipo') == 'alto' else "\u2b07 Bajo"
                    tk.Label(ar, text=tipo_ah, font=('Segoe UI', 8, 'bold'),
                             bg=bg_ah, fg=val_fg_ah, width=7, anchor='w').pack(side='left', padx=2, pady=2)
                    fecha_ah = ''
                    if al.get('fecha'):
                        try:
                            fecha_ah = al['fecha'].strftime('%d/%m/%Y')
                        except:
                            fecha_ah = str(al['fecha'])[:10]
                    tk.Label(ar, text=fecha_ah, font=('Segoe UI', 8),
                             bg=bg_ah, width=11, anchor='w').pack(side='left', padx=2, pady=2)
                    tk.Label(ar, text=al.get('numero_solicitud', ''), font=('Segoe UI', 8),
                             bg=bg_ah, fg='#666', width=12, anchor='w').pack(side='left', padx=2, pady=2)
                tk.Label(ah_frame, text="", bg='white').pack(pady=2)

        # ====== Areas clinicas ======
        areas = datos.get('areas_clinicas') or []
        if areas:
            areas_frame = tk.LabelFrame(scroll_frame,
                text=" \U0001f3e5 Áreas Clínicas ",
                font=('Segoe UI', 11, 'bold'), bg='white', fg=COLORS['text'])
            areas_frame.pack(fill='x', pady=(5, 10), padx=5)

            areas_inner = tk.Frame(areas_frame, bg='white')
            areas_inner.pack(fill='x', padx=10, pady=8)

            for i, area in enumerate(areas):
                area_chip = tk.Frame(areas_inner, bg='#e3f2fd', highlightbackground='#90caf9',
                                     highlightthickness=1)
                area_chip.pack(side='left', padx=4, pady=3)
                tk.Label(area_chip,
                         text=f"  {area.get('NombreArea', '')}  ({area.get('Veces', 0)})  ",
                         font=('Segoe UI', 9, 'bold'), bg='#e3f2fd',
                         fg='#1565c0').pack(padx=4, pady=4)

        # ====== Tendencia global (comparando ultimas 2 solicitudes) ======
        try:
            tg = self.gestor_historial.obtener_tendencias_globales(self.hist_paciente_id)
            if tg.get('exito'):
                _color_map_tg = {
                    'mejorando':  ('#e8f5e9', '#2e7d32'),
                    'empeorando': ('#ffebee', '#c62828'),
                    'optimo':     ('#e8f5e9', '#1b5e20'),
                    'estable':    ('#eceff1', '#546e7a'),
                    'sin_datos':  ('#f5f5f5', '#9e9e9e'),
                }
                bg_tg, fg_tg = _color_map_tg.get(tg.get('tendencia_global', 'sin_datos'),
                                                   ('#f5f5f5', '#9e9e9e'))
                tg_frame = tk.Frame(scroll_frame, bg=bg_tg,
                                    highlightbackground=fg_tg, highlightthickness=1)
                tg_frame.pack(fill='x', pady=(5, 5), padx=5)
                tg_inner = tk.Frame(tg_frame, bg=bg_tg)
                tg_inner.pack(fill='x', padx=12, pady=7)
                tk.Label(tg_inner, text="Tendencia Global:",
                         font=('Segoe UI', 9, 'bold'),
                         bg=bg_tg, fg='#333').pack(side='left', padx=(0, 8))
                tk.Label(tg_inner, text=tg['icono_tendencia'],
                         font=('Segoe UI', 11, 'bold'),
                         bg=bg_tg, fg=fg_tg).pack(side='left', padx=(0, 20))
                alt  = tg.get('alterados_ultima', 0)
                tot  = tg.get('total_params_ultima', 0)
                mej  = tg.get('mejorando', 0)
                emp  = tg.get('empeorando', 0)
                alt_pen = tg.get('alterados_penultima', 0)
                stats_txt = f"Última solicitud: {alt} de {tot} parámetros fuera de rango"
                if alt_pen > 0 or mej or emp:
                    stats_txt += f"   \u2502   {mej} mejoraron, {emp} empeoraron vs. visita anterior"
                tk.Label(tg_inner, text=stats_txt, font=('Segoe UI', 9),
                         bg=bg_tg, fg='#555').pack(side='left')
        except Exception:
            pass

        # ====== Pruebas frecuentes ======
        if datos.get('pruebas_frecuentes'):
            freq_frame = tk.LabelFrame(scroll_frame,
                text=" \U0001f9ea Pruebas Más Frecuentes ",
                font=('Segoe UI', 11, 'bold'), bg='white', fg=COLORS['text'])
            freq_frame.pack(fill='x', pady=(5, 0), padx=5)

            for prueba in datos['pruebas_frecuentes']:
                row = tk.Frame(freq_frame, bg='white')
                row.pack(fill='x', padx=10, pady=3)
                tk.Label(row, text=prueba.get('NombrePrueba', ''),
                         font=('Segoe UI', 10), bg='white', anchor='w').pack(
                    side='left', fill='x', expand=True)
                tk.Label(row, text=f"{prueba.get('Veces', 0)} vez(es)",
                         font=('Segoe UI', 10, 'bold'), bg='white',
                         fg=COLORS['primary']).pack(side='right', padx=(0, 8))
                pid_fr = prueba.get('PruebaID')
                if pid_fr and IA_INTERPRETACION_DISPONIBLE:
                    def _ir_ia_fr(pid=pid_fr):
                        self._ir_a_ia_con_prueba(pid)
                    tk.Button(row, text="\U0001f916 IA",
                              font=('Segoe UI', 8), bg='#ede7f6', fg='#4a148c',
                              relief='flat', padx=6, pady=1, cursor='hand2',
                              command=_ir_ia_fr).pack(side='right', padx=2)

    def _render_historial_cronologico(self):
        """Renderiza la vista cronologica de solicitudes con filtros."""
        if not HISTORIAL_CLINICO_DISPONIBLE or not self.gestor_historial:
            tk.Label(self.hist_detail_frame,
                     text="Módulo de historial no disponible",
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['danger']).pack(pady=50)
            return

        # ====== Barra de filtros ======
        filtros_frame = tk.Frame(self.hist_detail_frame, bg='#f0f4f8',
                                  highlightbackground=COLORS['border'], highlightthickness=1)
        filtros_frame.pack(fill='x', pady=(0, 10))

        tk.Label(filtros_frame, text="\U0001f50d Filtros:",
                 font=('Segoe UI', 10, 'bold'), bg='#f0f4f8').pack(side='left', padx=(10, 5), pady=8)

        tk.Label(filtros_frame, text="Desde:", font=('Segoe UI', 9), bg='#f0f4f8').pack(side='left', padx=(10, 3))
        self._hist_filtro_desde = tk.Entry(filtros_frame, font=('Segoe UI', 9),
                                            width=12, relief='flat', bg='white',
                                            highlightthickness=1, highlightbackground=COLORS['border'])
        self._hist_filtro_desde.pack(side='left', padx=2, ipady=3)
        self._hist_filtro_desde.insert(0, "dd/mm/aaaa")
        self._hist_filtro_desde.config(fg='#999')
        self._hist_filtro_desde.bind('<FocusIn>', lambda e: self._hist_placeholder_clear(self._hist_filtro_desde, "dd/mm/aaaa"))
        self._hist_filtro_desde.bind('<FocusOut>', lambda e: self._hist_placeholder_set(self._hist_filtro_desde, "dd/mm/aaaa"))

        tk.Label(filtros_frame, text="Hasta:", font=('Segoe UI', 9), bg='#f0f4f8').pack(side='left', padx=(10, 3))
        self._hist_filtro_hasta = tk.Entry(filtros_frame, font=('Segoe UI', 9),
                                            width=12, relief='flat', bg='white',
                                            highlightthickness=1, highlightbackground=COLORS['border'])
        self._hist_filtro_hasta.pack(side='left', padx=2, ipady=3)
        self._hist_filtro_hasta.insert(0, "dd/mm/aaaa")
        self._hist_filtro_hasta.config(fg='#999')
        self._hist_filtro_hasta.bind('<FocusIn>', lambda e: self._hist_placeholder_clear(self._hist_filtro_hasta, "dd/mm/aaaa"))
        self._hist_filtro_hasta.bind('<FocusOut>', lambda e: self._hist_placeholder_set(self._hist_filtro_hasta, "dd/mm/aaaa"))

        tk.Label(filtros_frame, text="Área:", font=('Segoe UI', 9), bg='#f0f4f8').pack(side='left', padx=(10, 3))
        areas_pac = self.gestor_historial.obtener_areas_paciente(self.hist_paciente_id)
        area_nombres = ["Todas"] + [a.get('NombreArea', '') for a in areas_pac]
        self._hist_areas_map = {a.get('NombreArea', ''): a.get('AreaID') for a in areas_pac}

        self._hist_combo_area = ttk.Combobox(filtros_frame, font=('Segoe UI', 9),
                                              values=area_nombres, state='readonly', width=18)
        self._hist_combo_area.pack(side='left', padx=2)
        self._hist_combo_area.set("Todas")

        tk.Button(filtros_frame, text="Filtrar", font=('Segoe UI', 9, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat', padx=12,
                  cursor='hand2', command=self._aplicar_filtros_historial
                  ).pack(side='left', padx=(10, 3), pady=5)

        tk.Button(filtros_frame, text="Limpiar", font=('Segoe UI', 9),
                  bg='#e2e8f0', fg=COLORS['text'], relief='flat', padx=8,
                  cursor='hand2', command=self._limpiar_filtros_historial
                  ).pack(side='left', padx=3, pady=5)

        # Frame contenedor para resultados (se recarga con filtros)
        self._hist_cronologico_frame = tk.Frame(self.hist_detail_frame, bg='white')
        self._hist_cronologico_frame.pack(fill='both', expand=True)

        self._cargar_historial_cronologico()

    def _hist_placeholder_clear(self, entry, placeholder):
        """Limpia placeholder al enfocar."""
        if entry.get() == placeholder:
            entry.delete(0, 'end')
            entry.config(fg=COLORS['text'])

    def _hist_placeholder_set(self, entry, placeholder):
        """Restaura placeholder si esta vacio."""
        if not entry.get().strip():
            entry.insert(0, placeholder)
            entry.config(fg='#999')

    def _aplicar_filtros_historial(self):
        """Aplica filtros de fecha y area al historial cronologico."""
        self._cargar_historial_cronologico()

    def _limpiar_filtros_historial(self):
        """Limpia los filtros y recarga."""
        if hasattr(self, '_hist_filtro_desde'):
            self._hist_filtro_desde.delete(0, 'end')
            self._hist_filtro_desde.insert(0, "dd/mm/aaaa")
            self._hist_filtro_desde.config(fg='#999')
        if hasattr(self, '_hist_filtro_hasta'):
            self._hist_filtro_hasta.delete(0, 'end')
            self._hist_filtro_hasta.insert(0, "dd/mm/aaaa")
            self._hist_filtro_hasta.config(fg='#999')
        if hasattr(self, '_hist_combo_area'):
            self._hist_combo_area.set("Todas")
        self._cargar_historial_cronologico()

    def _cargar_historial_cronologico(self):
        """Carga el historial cronologico con filtros aplicados."""
        if not hasattr(self, '_hist_cronologico_frame'):
            return

        for w in self._hist_cronologico_frame.winfo_children():
            w.destroy()

        # Parsear filtros
        fecha_desde = None
        fecha_hasta = None
        area_id = None

        if hasattr(self, '_hist_filtro_desde'):
            txt = self._hist_filtro_desde.get().strip()
            if txt and txt != "dd/mm/aaaa":
                try:
                    fecha_desde = datetime.strptime(txt, '%d/%m/%Y')
                except ValueError:
                    pass

        if hasattr(self, '_hist_filtro_hasta'):
            txt = self._hist_filtro_hasta.get().strip()
            if txt and txt != "dd/mm/aaaa":
                try:
                    fecha_hasta = datetime.strptime(txt, '%d/%m/%Y')
                except ValueError:
                    pass

        if hasattr(self, '_hist_combo_area'):
            sel_area = self._hist_combo_area.get()
            if sel_area and sel_area != "Todas":
                area_id = self._hist_areas_map.get(sel_area)

        result = self.gestor_historial.obtener_historial_paciente(
            self.hist_paciente_id, fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta, area_id=area_id
        )

        if not result.get('exito') or not result.get('solicitudes'):
            msg = "No se encontraron solicitudes"
            if fecha_desde or fecha_hasta or area_id:
                msg += " con los filtros aplicados"
            tk.Label(self._hist_cronologico_frame,
                     text=msg,
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['text_light']).pack(pady=50)
            return

        # Contador de resultados
        n_sol = len(result['solicitudes'])
        tk.Label(self._hist_cronologico_frame,
                 text=f"{n_sol} solicitud(es) encontrada(s)",
                 font=('Segoe UI', 9), bg='white',
                 fg=COLORS['text_light']).pack(anchor='w', pady=(0, 5))

        # Scrollable
        canvas = tk.Canvas(self._hist_cronologico_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self._hist_cronologico_frame, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg='white')
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', _on_canvas_configure)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

        def _cargar_detalle_sol(d):
            """Carga los resultados de una solicitud de forma lazy."""
            if d._loaded:
                return
            d._loaded = True
            sol_data = d._sol_data
            for prueba in sol_data.get('pruebas', []):
                prueba_frame_h = tk.Frame(d, bg='#e3f2fd')
                prueba_frame_h.pack(fill='x', pady=(3, 0))

                p_lbl_frame = tk.Frame(prueba_frame_h, bg='#e3f2fd')
                p_lbl_frame.pack(fill='x')
                tk.Label(p_lbl_frame,
                         text=f"  {prueba.get('CodigoPrueba', '')} - "
                              f"{prueba.get('NombrePrueba', '')}",
                         font=('Segoe UI', 9, 'bold'), bg='#e3f2fd',
                         fg='#1976d2', anchor='w').pack(side='left', fill='x',
                         expand=True, pady=3, padx=5)

                # Boton rapido para ir a la evolucion de esta prueba
                prueba_id_btn = prueba.get('PruebaID')
                if prueba_id_btn:
                    def _ir_evolucion(pid=prueba_id_btn):
                        self._cambiar_tab_historial('evolucion')
                        if hasattr(self, 'combo_prueba_hist') and hasattr(self, '_hist_pruebas_map'):
                            target = next((k for k, v in self._hist_pruebas_map.items() if v == pid), None)
                            if target:
                                self.combo_prueba_hist.set(target)
                                self._ejecutar_evolucion_historial()
                    tk.Button(p_lbl_frame, text="\U0001f4c8 Ver Evol.",
                              font=('Segoe UI', 8), bg='#bbdefb', fg='#1565c0',
                              relief='flat', padx=6, cursor='hand2',
                              command=_ir_evolucion).pack(side='right', padx=5, pady=2)

                resultados = self.gestor_historial.obtener_resultados_detalle(
                    prueba['DetalleID']
                ) if self.gestor_historial else []
                seccion_actual = None
                for res in (resultados or []):
                    valor = res.get('Valor') or ''
                    if not str(valor).strip():
                        continue

                    seccion = res.get('Seccion') or ''
                    if seccion and seccion != seccion_actual:
                        seccion_actual = seccion
                        sec_frame = tk.Frame(d, bg='#455a64')
                        sec_frame.pack(fill='x', pady=(3, 0))
                        tk.Label(sec_frame, text=f"  {seccion}",
                                 font=('Segoe UI', 8, 'bold'),
                                 bg='#455a64', fg='white',
                                 anchor='w').pack(fill='x', pady=2)

                    fuera = res.get('FueraDeRango')
                    tipo_al = res.get('TipoAlerta') or ''
                    if fuera and tipo_al in ('CriticoAlto', 'CriticoBajo'):
                        row_bg = '#fff3e0'
                        val_fg = '#e65100'
                    elif fuera:
                        row_bg = '#fff8f8'
                        val_fg = '#c62828'
                    else:
                        row_bg = 'white'
                        val_fg = COLORS['text']

                    row = tk.Frame(d, bg=row_bg)
                    row.pack(fill='x')
                    tk.Label(row, text=f"   {res.get('NombreParametro', '')}",
                             font=('Segoe UI', 9), bg=row_bg,
                             width=22, anchor='w').pack(side='left', padx=5, pady=1)

                    valor_display = str(valor)
                    if fuera and tipo_al in ('CriticoAlto', 'CriticoBajo'):
                        indicador = ' \u26a0'
                    elif fuera:
                        indicador = ' \u2757'
                    else:
                        indicador = ''

                    tk.Label(row, text=valor_display + indicador,
                             font=('Segoe UI', 9, 'bold'), bg=row_bg,
                             width=14, anchor='w', fg=val_fg).pack(side='left', padx=5)
                    tk.Label(row, text=res.get('Unidad', ''),
                             font=('Segoe UI', 9), bg=row_bg,
                             width=10, fg='#666').pack(side='left', padx=5)
                    tk.Label(row, text=(res.get('ValorRef', '') or '---'),
                             font=('Segoe UI', 9), bg=row_bg,
                             width=25, fg='#1565c0', anchor='w').pack(side='left', padx=5)

        for sol in result['solicitudes']:
            sol_frame = tk.Frame(scroll_frame, bg='white', highlightbackground=COLORS['border'],
                                 highlightthickness=1)
            sol_frame.pack(fill='x', pady=5, padx=5)

            fecha_str = ''
            if sol.get('FechaSolicitud'):
                try:
                    fecha_str = sol['FechaSolicitud'].strftime('%d/%m/%Y')
                except:
                    fecha_str = str(sol['FechaSolicitud'])[:10]

            estado = sol.get('EstadoSolicitud', 'Pendiente')
            color_estado = {
                'Validado': '#4caf50', 'Completada': '#4caf50',
                'Entregada': '#2196f3',
                'Capturado': '#ff9800', 'En Proceso': '#ff9800',
                'Pendiente': '#9e9e9e',
            }.get(estado, '#9e9e9e')

            header = tk.Frame(sol_frame, bg='#f8f9fa')
            header.pack(fill='x')

            lbl_header = tk.Label(header,
                     text=f"  \u25b6  {sol.get('NumeroSolicitud', '')}  |  {fecha_str}",
                     font=('Segoe UI', 10, 'bold'), bg='#f8f9fa',
                     fg=COLORS['text'], anchor='w', cursor='hand2')
            lbl_header.pack(side='left', fill='x', expand=True, pady=8, padx=5)

            n_pruebas = len(sol.get('pruebas', []))
            tk.Label(header, text=f"{n_pruebas} prueba(s)",
                     font=('Segoe UI', 9), bg='#f8f9fa',
                     fg=COLORS['text_light']).pack(side='right', padx=5)

            tk.Label(header, text=f" {estado} ",
                     font=('Segoe UI', 9, 'bold'),
                     bg=color_estado, fg='white',
                     padx=8).pack(side='right', padx=10, pady=5)

            # Mostrar diagnostico presuntivo y observaciones si existen
            diag = str(sol.get('DiagnosticoPresuntivo') or '').strip()
            obs_s = str(sol.get('Observaciones') or '').strip()
            if diag or obs_s:
                ctx_frame = tk.Frame(sol_frame, bg='#fffde7',
                                     highlightbackground='#f9a825', highlightthickness=1)
                ctx_frame.pack(fill='x', padx=2)
                if diag:
                    tk.Label(ctx_frame,
                             text=f"  \U0001f4cb Dx: {diag}",
                             font=('Segoe UI', 8, 'italic'), bg='#fffde7',
                             fg='#5d4037', anchor='w').pack(fill='x', padx=6, pady=(3, 1))
                if obs_s:
                    tk.Label(ctx_frame,
                             text=f"  \U0001f4dd Obs: {obs_s}",
                             font=('Segoe UI', 8, 'italic'), bg='#fffde7',
                             fg='#5d4037', anchor='w').pack(fill='x', padx=6, pady=(1, 3))

            # Frame detalle (oculto inicialmente, carga lazy al expandir)
            detail = tk.Frame(sol_frame, bg='white')
            detail._loaded = False
            detail._sol_data = sol

            def _toggle_detail(lbl=lbl_header, d=detail):
                if d.winfo_manager():
                    d.pack_forget()
                    txt = lbl.cget('text')
                    lbl.config(text=txt.replace('\u25bc', '\u25b6'))
                else:
                    _cargar_detalle_sol(d)
                    d.pack(fill='x', padx=10, pady=(0, 10))
                    txt = lbl.cget('text')
                    lbl.config(text=txt.replace('\u25b6', '\u25bc'))

            lbl_header.bind('<Button-1>', lambda e, f=_toggle_detail: f())
            header.bind('<Button-1>', lambda e, f=_toggle_detail: f())

    def _render_historial_comparativa(self):
        """Renderiza la comparativa lado a lado de las 2 ultimas instancias de una prueba."""
        if not HISTORIAL_CLINICO_DISPONIBLE or not self.gestor_historial:
            tk.Label(self.hist_detail_frame,
                     text="Módulo de historial no disponible",
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['danger']).pack(pady=50)
            return

        # Selector de prueba
        selector_frame = tk.Frame(self.hist_detail_frame, bg='white')
        selector_frame.pack(fill='x', pady=(0, 10))

        tk.Label(selector_frame, text="Prueba a comparar:",
                 font=('Segoe UI', 10, 'bold'), bg='white').pack(side='left', padx=(0, 10))

        pruebas = self.gestor_historial.obtener_pruebas_con_resultados(self.hist_paciente_id)

        if not pruebas:
            tk.Label(self.hist_detail_frame,
                     text="No hay pruebas con resultados capturados",
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['text_light']).pack(pady=50)
            return

        prueba_nombres = [
            f"{p.get('CodigoPrueba', '')} - {p.get('NombrePrueba', '')}"
            f"  ({p.get('Veces', 0)}x)"
            for p in pruebas
        ]
        self._hist_comp_pruebas_map = {
            f"{p.get('CodigoPrueba', '')} - {p.get('NombrePrueba', '')}"
            f"  ({p.get('Veces', 0)}x)": p['PruebaID']
            for p in pruebas
        }

        self.combo_prueba_comp = ttk.Combobox(
            selector_frame, font=('Segoe UI', 10),
            values=prueba_nombres, state='readonly', width=45
        )
        self.combo_prueba_comp.pack(side='left', padx=5)

        tk.Button(selector_frame, text="Comparar",
                  font=('Segoe UI', 10, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat',
                  padx=15, cursor='hand2',
                  command=self._ejecutar_comparativa_historial
                  ).pack(side='left', padx=10)

        if IA_INTERPRETACION_DISPONIBLE:
            def _ir_ia_comp():
                seleccion = self.combo_prueba_comp.get()
                prueba_id_comp = self._hist_comp_pruebas_map.get(seleccion)
                if prueba_id_comp:
                    self._ir_a_ia_con_prueba(prueba_id_comp)
                else:
                    messagebox.showwarning("IA Clínica", "Seleccione una prueba primero.")
            tk.Button(selector_frame, text="\U0001f916 Analizar con IA",
                      font=('Segoe UI', 9),
                      bg='#ede7f6', fg='#4a148c', relief='flat',
                      padx=12, pady=5, cursor='hand2',
                      command=_ir_ia_comp).pack(side='left', padx=2)

        self.hist_comp_result_frame = tk.Frame(self.hist_detail_frame, bg='white')
        self.hist_comp_result_frame.pack(fill='both', expand=True)

        if prueba_nombres:
            self.combo_prueba_comp.set(prueba_nombres[0])
            self._ejecutar_comparativa_historial()

    def _ejecutar_comparativa_historial(self):
        """Ejecuta la comparativa y renderiza la tabla lado a lado."""
        if not hasattr(self, 'combo_prueba_comp'):
            return
        seleccion = self.combo_prueba_comp.get()
        prueba_id = self._hist_comp_pruebas_map.get(seleccion)
        if not prueba_id:
            return

        for w in self.hist_comp_result_frame.winfo_children():
            w.destroy()

        result = self.gestor_historial.obtener_comparativa(
            self.hist_paciente_id, prueba_id
        )

        if not result.get('exito'):
            tk.Label(self.hist_comp_result_frame,
                     text=result.get('mensaje', 'Sin resultados comparables.\n'
                                     'Se necesitan al menos 2 mediciones.'),
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['text_light'], justify='center').pack(pady=40)
            return

        # Scrollable
        canvas = tk.Canvas(self.hist_comp_result_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.hist_comp_result_frame, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg='white')
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        def _on_cc(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', _on_cc)
        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        def on_mw(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mw))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # Titulo
        tk.Label(scroll_frame,
                 text=f"Comparativa: {result.get('prueba_nombre', '')}",
                 font=('Segoe UI', 13, 'bold'), bg='white',
                 fg=COLORS['text']).pack(anchor='w', pady=(0, 5))

        # Fechas encabezado
        fecha_ant = result.get('fecha_anterior')
        fecha_rec = result.get('fecha_reciente')
        num_ant = result.get('numero_anterior', '')
        num_rec = result.get('numero_reciente', '')

        def _fmt(f):
            if not f:
                return '---'
            try:
                return f.strftime('%d/%m/%Y')
            except:
                return str(f)[:10]

        # Card de contexto de fechas
        ctx = tk.Frame(scroll_frame, bg='#e8f5e9', highlightbackground='#a5d6a7',
                       highlightthickness=1)
        ctx.pack(fill='x', pady=(0, 10), padx=3)

        if fecha_ant:
            tk.Label(ctx,
                     text=f"  Anterior:  {_fmt(fecha_ant)}  ({num_ant})",
                     font=('Segoe UI', 9), bg='#e8f5e9', fg='#2e7d32').pack(
                side='left', padx=15, pady=6)
        else:
            tk.Label(ctx, text="  Solo una medición disponible",
                     font=('Segoe UI', 9), bg='#e8f5e9', fg='#555').pack(
                side='left', padx=15, pady=6)

        tk.Label(ctx,
                 text=f"Reciente:  {_fmt(fecha_rec)}  ({num_rec})  ",
                 font=('Segoe UI', 9, 'bold'), bg='#e8f5e9', fg='#1b5e20').pack(
            side='right', padx=15, pady=6)

        # Encabezado de tabla
        th = tk.Frame(scroll_frame, bg='#1565c0')
        th.pack(fill='x', padx=3)
        col_specs = [
            ("Parámetro", 20, 'w'),
            ("Unidad", 8, 'w'),
            ("Referencia", 14, 'w'),
            (f"Anterior\n{_fmt(fecha_ant)}", 13, 'center'),
            (f"Reciente\n{_fmt(fecha_rec)}", 13, 'center'),
            ("\u0394%", 7, 'center'),
            ("Tend.", 6, 'center'),
            ("Estado", 9, 'center'),
        ]
        for txt, w, anchor in col_specs:
            tk.Label(th, text=txt, font=('Segoe UI', 9, 'bold'),
                     bg='#1565c0', fg='white', width=w, anchor=anchor,
                     justify='center').pack(side='left', padx=3, pady=5)

        # Filas de parametros
        seccion_actual = None
        parametros = result.get('parametros', [])

        for i, par in enumerate(parametros):
            seccion = par.get('seccion') or ''
            if seccion and seccion != seccion_actual:
                seccion_actual = seccion
                sec_r = tk.Frame(scroll_frame, bg='#455a64')
                sec_r.pack(fill='x', padx=3, pady=(4, 0))
                tk.Label(sec_r, text=f"  {seccion}",
                         font=('Segoe UI', 8, 'bold'),
                         bg='#455a64', fg='white', anchor='w').pack(fill='x', pady=2)

            fuera_r = par.get('fuera_rango_reciente', False)
            fuera_a = par.get('fuera_rango_anterior', False)
            tipo_r = par.get('tipo_alerta_reciente') or ''
            es_critico_r = tipo_r in ('CriticoAlto', 'CriticoBajo')

            if es_critico_r:
                row_bg = '#fff3e0'
            elif fuera_r:
                row_bg = '#fff8f8'
            elif i % 2 == 0:
                row_bg = '#fafafa'
            else:
                row_bg = 'white'

            row = tk.Frame(scroll_frame, bg=row_bg)
            row.pack(fill='x', padx=3)

            nombre = par.get('nombre', '')
            tk.Label(row, text=f"  {nombre}", font=('Segoe UI', 9),
                     bg=row_bg, width=20, anchor='w').pack(side='left', padx=3, pady=2)
            tk.Label(row, text=par.get('unidad', ''), font=('Segoe UI', 9),
                     bg=row_bg, fg='#666', width=8, anchor='w').pack(side='left', padx=3, pady=2)
            tk.Label(row, text=(par.get('valor_ref') or '---'), font=('Segoe UI', 9),
                     bg=row_bg, fg='#1565c0', width=14, anchor='w').pack(side='left', padx=3, pady=2)

            # Valor anterior
            val_ant = par.get('valor_anterior') or '---'
            ant_fg = '#c62828' if fuera_a else COLORS['text']
            tk.Label(row, text=val_ant, font=('Segoe UI', 9, 'bold' if fuera_a else 'normal'),
                     bg=row_bg, fg=ant_fg, width=13, anchor='center').pack(side='left', padx=3, pady=2)

            # Valor reciente
            val_rec = par.get('valor_reciente') or '---'
            if fuera_r and es_critico_r:
                rec_fg = '#e65100'
                rec_font = ('Segoe UI', 9, 'bold')
                rec_ind = ' \u26a0'
            elif fuera_r:
                rec_fg = '#c62828'
                rec_font = ('Segoe UI', 9, 'bold')
                tipo_lower_r = tipo_r.lower()
                rec_ind = ' \u2b06' if 'alto' in tipo_lower_r else ' \u2b07'
            else:
                rec_fg = COLORS['text']
                rec_font = ('Segoe UI', 9)
                rec_ind = ''
            tk.Label(row, text=val_rec + rec_ind, font=rec_font,
                     bg=row_bg, fg=rec_fg, width=13, anchor='center').pack(side='left', padx=3, pady=2)

            # Columna Δ% (variacion porcentual entre anterior y reciente)
            delta_txt = ''
            delta_fg = '#9e9e9e'
            try:
                v_ant_f = float(str(val_ant).replace(',', '.'))
                v_rec_f = float(str(val_rec).replace(',', '.'))
                if v_ant_f != 0:
                    delta = ((v_rec_f - v_ant_f) / abs(v_ant_f)) * 100
                    signo = '+' if delta >= 0 else ''
                    delta_txt = f"{signo}{delta:.1f}%"
                    if abs(delta) < 5:
                        delta_fg = '#9e9e9e'
                    elif abs(delta) < 20:
                        delta_fg = '#f59e0b'
                    else:
                        delta_fg = '#c62828' if fuera_r else '#1565c0'
            except (ValueError, TypeError):
                pass
            tk.Label(row, text=delta_txt, font=('Segoe UI', 8, 'bold'),
                     bg=row_bg, fg=delta_fg, width=7, anchor='center').pack(side='left', padx=3, pady=2)

            # Tendencia
            tend = par.get('tendencia') or {}
            icono_t = tend.get('icono', '\u2014')
            color_t = tend.get('color', '#9e9e9e')
            tk.Label(row, text=icono_t, font=('Segoe UI', 11, 'bold'),
                     bg=row_bg, fg=color_t, width=6, anchor='center').pack(side='left', padx=3, pady=2)

            # Estado legible
            dir_t = tend.get('direccion', '')
            fav_t = tend.get('favorable')
            if dir_t == 'sin_datos':
                estado_txt = '---'
                estado_fg = '#9e9e9e'
            elif dir_t == 'estable':
                estado_txt = 'Estable'
                estado_fg = '#9e9e9e'
            elif fav_t is True:
                estado_txt = 'Mejorando'
                estado_fg = '#2e7d32'
            elif fav_t is False:
                estado_txt = 'Empeorando'
                estado_fg = '#c62828'
            elif dir_t in ('subio', 'bajo'):
                estado_txt = 'Subió' if dir_t == 'subio' else 'Bajó'
                estado_fg = '#f59e0b'
            else:
                estado_txt = dir_t.capitalize()
                estado_fg = '#9e9e9e'

            tk.Label(row, text=estado_txt, font=('Segoe UI', 8, 'bold'),
                     bg=row_bg, fg=estado_fg, width=9, anchor='center').pack(side='left', padx=3, pady=2)

        # Leyenda
        ley = tk.Frame(scroll_frame, bg='#f0f4f8', highlightbackground=COLORS['border'],
                       highlightthickness=1)
        ley.pack(fill='x', pady=(12, 5), padx=3)
        tk.Label(ley, text="Leyenda:",
                 font=('Segoe UI', 9, 'bold'), bg='#f0f4f8').pack(anchor='w', padx=10, pady=(5, 2))
        leyendas = [
            ("\u2191 / \u2193 Verde", '#2e7d32', "Mejorando (acercándose al rango normal)"),
            ("\u2191 / \u2193 Rojo", '#c62828', "Empeorando (alejándose del rango normal)"),
            ("\u2191 / \u2193 Ámbar", '#f59e0b', "Cambio sin rango de referencia"),
            ("\u2192 Gris", '#9e9e9e', "Estable"),
            ("\u2014 Gris", '#9e9e9e', "Sin dato anterior para comparar"),
        ]
        for sym, col, desc in leyendas:
            lr = tk.Frame(ley, bg='#f0f4f8')
            lr.pack(fill='x', padx=10, pady=1)
            tk.Label(lr, text=sym, font=('Segoe UI', 9, 'bold'),
                     bg='#f0f4f8', fg=col, width=15, anchor='w').pack(side='left')
            tk.Label(lr, text=desc, font=('Segoe UI', 9),
                     bg='#f0f4f8', fg=COLORS['text_light']).pack(side='left', padx=5)
        tk.Label(ley, text="", bg='#f0f4f8').pack(pady=2)

    def _render_historial_evolucion(self):
        """Renderiza la vista de evolucion completa multi-punto."""
        if not HISTORIAL_CLINICO_DISPONIBLE or not self.gestor_historial:
            tk.Label(self.hist_detail_frame,
                     text="Módulo de historial no disponible",
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['danger']).pack(pady=50)
            return

        # Selector de prueba
        selector_frame = tk.Frame(self.hist_detail_frame, bg='white')
        selector_frame.pack(fill='x', pady=(0, 10))

        tk.Label(selector_frame, text="Seleccione una prueba:",
                 font=('Segoe UI', 10, 'bold'), bg='white').pack(side='left', padx=(0, 10))

        pruebas = self.gestor_historial.obtener_pruebas_con_resultados(self.hist_paciente_id)

        if not pruebas:
            tk.Label(self.hist_detail_frame,
                     text="No hay pruebas con resultados capturados",
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['text_light']).pack(pady=50)
            return

        prueba_nombres = [
            f"{p.get('CodigoPrueba', '')} - {p.get('NombrePrueba', '')}"
            for p in pruebas
        ]
        self._hist_pruebas_map = {
            f"{p.get('CodigoPrueba', '')} - {p.get('NombrePrueba', '')}": p['PruebaID']
            for p in pruebas
        }

        self.combo_prueba_hist = ttk.Combobox(
            selector_frame, font=('Segoe UI', 10),
            values=prueba_nombres, state='readonly', width=40
        )
        self.combo_prueba_hist.pack(side='left', padx=5)

        tk.Button(selector_frame, text="Ver Evolución",
                  font=('Segoe UI', 10, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat',
                  padx=15, cursor='hand2',
                  command=self._ejecutar_evolucion_historial
                  ).pack(side='left', padx=10)

        self.hist_comparativa_frame = tk.Frame(self.hist_detail_frame, bg='white')
        self.hist_comparativa_frame.pack(fill='both', expand=True)

        if prueba_nombres:
            self.combo_prueba_hist.set(prueba_nombres[0])
            self._ejecutar_evolucion_historial()

    def _ejecutar_evolucion_historial(self):
        """Ejecuta la evolucion completa y renderiza resultados multi-punto."""
        if not hasattr(self, 'combo_prueba_hist'):
            return
        seleccion = self.combo_prueba_hist.get()
        prueba_id = self._hist_pruebas_map.get(seleccion)
        if not prueba_id:
            return

        for w in self.hist_comparativa_frame.winfo_children():
            w.destroy()

        result = self.gestor_historial.obtener_evolucion_completa_prueba(
            self.hist_paciente_id, prueba_id
        )

        if not result.get('exito'):
            tk.Label(self.hist_comparativa_frame,
                     text=result.get('mensaje', 'Sin resultados'),
                     font=('Segoe UI', 11), bg='white',
                     fg=COLORS['text_light']).pack(pady=30)
            return

        mediciones = result.get('mediciones', [])
        parametros = result.get('parametros', [])

        # Scrollable
        canvas = tk.Canvas(self.hist_comparativa_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.hist_comparativa_frame, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg='white')
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)
        canvas.bind('<Configure>', _on_canvas_configure)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

        # Titulo
        tk.Label(scroll_frame,
                 text=f"Evolución: {result.get('prueba_nombre', '')}",
                 font=('Segoe UI', 13, 'bold'), bg='white',
                 fg=COLORS['text']).pack(anchor='w', pady=(0, 3))

        n_med = len(mediciones)
        tk.Label(scroll_frame,
                 text=f"{n_med} medición(es) registrada(s)",
                 font=('Segoe UI', 9), bg='white',
                 fg=COLORS['text_light']).pack(anchor='w', pady=(0, 12))

        # Iterar por cada parametro
        seccion_actual = None
        for param in parametros:
            seccion = param.get('seccion') or ''
            if seccion and seccion != seccion_actual:
                seccion_actual = seccion
                sec_row = tk.Frame(scroll_frame, bg='#455a64')
                sec_row.pack(fill='x', pady=(8, 0))
                tk.Label(sec_row, text=f"  {seccion}",
                         font=('Segoe UI', 9, 'bold'),
                         bg='#455a64', fg='white',
                         anchor='w').pack(fill='x', pady=3)

            valores = param.get('valores', [])
            tiene_valores = any(v.get('valor') for v in valores)
            if not tiene_valores:
                continue

            # Frame del parametro
            param_frame = tk.Frame(scroll_frame, bg='white',
                                    highlightbackground=COLORS['border'], highlightthickness=1)
            param_frame.pack(fill='x', pady=(5, 3), padx=3)

            # Header del parametro
            ph = tk.Frame(param_frame, bg='#e3f2fd')
            ph.pack(fill='x')
            nombre_txt = param.get('nombre', '')
            unidad_txt = f" ({param.get('unidad', '')})" if param.get('unidad') else ''
            ref_txt = f"  |  Ref: {param.get('valor_ref', '')}" if param.get('valor_ref') else ''
            tk.Label(ph, text=f"  {nombre_txt}{unidad_txt}{ref_txt}",
                     font=('Segoe UI', 10, 'bold'), bg='#e3f2fd',
                     fg='#1565c0', anchor='w').pack(fill='x', pady=5, padx=5)

            # Tabla de valores historicos
            th = tk.Frame(param_frame, bg='#f0f4f8')
            th.pack(fill='x')
            for txt, w in [("Fecha", 12), ("Solicitud", 14), ("Valor", 14), ("Tend.", 4), ("Estado", 8)]:
                tk.Label(th, text=txt, font=('Segoe UI', 8, 'bold'),
                         bg='#f0f4f8', fg=COLORS['text'], width=w,
                         anchor='w').pack(side='left', padx=3, pady=3)

            for i, val in enumerate(valores):
                if not val.get('valor'):
                    continue

                fuera_v = val.get('fuera_rango', False)
                tipo_alerta_v = val.get('tipo_alerta') or ''
                es_critico_v = tipo_alerta_v in ('CriticoAlto', 'CriticoBajo')

                if es_critico_v:
                    bg_v = '#fff3e0'
                elif fuera_v:
                    bg_v = '#fff8f8'
                elif i % 2 == 0:
                    bg_v = '#fafafa'
                else:
                    bg_v = 'white'

                vr = tk.Frame(param_frame, bg=bg_v)
                vr.pack(fill='x')

                fecha_str = ''
                if val.get('fecha'):
                    try:
                        fecha_str = val['fecha'].strftime('%d/%m/%Y')
                    except:
                        fecha_str = str(val['fecha'])[:10]

                tk.Label(vr, text=fecha_str, font=('Segoe UI', 9),
                         bg=bg_v, width=12, anchor='w').pack(side='left', padx=3, pady=1)
                tk.Label(vr, text=val.get('numero_solicitud', ''),
                         font=('Segoe UI', 9), bg=bg_v,
                         width=14, anchor='w', fg='#666').pack(side='left', padx=3, pady=1)

                tend = val.get('tendencia') or {}
                if fuera_v:
                    val_color = '#e65100' if es_critico_v else '#c62828'
                else:
                    val_color = tend.get('color', COLORS['text'])

                tk.Label(vr, text=str(val.get('valor', '')),
                         font=('Segoe UI', 9, 'bold'), bg=bg_v,
                         width=14, anchor='w', fg=val_color).pack(side='left', padx=3, pady=1)

                icono = tend.get('icono', '')
                icono_color = tend.get('color', '#9e9e9e')
                tk.Label(vr, text=icono, font=('Segoe UI', 11, 'bold'),
                         bg=bg_v, width=4, fg=icono_color).pack(side='left', padx=3, pady=1)

                # Indicador de estado fuera de rango
                if es_critico_v:
                    estado_txt = '\u26a0 Critico'
                    estado_fg = '#e65100'
                elif fuera_v and tipo_alerta_v == 'Alto':
                    estado_txt = '\u2b06 Alto'
                    estado_fg = '#c62828'
                elif fuera_v and tipo_alerta_v == 'Bajo':
                    estado_txt = '\u2b07 Bajo'
                    estado_fg = '#1565c0'
                elif fuera_v:
                    estado_txt = '\u2757 Fuera'
                    estado_fg = '#c62828'
                else:
                    estado_txt = ''
                    estado_fg = '#9e9e9e'
                tk.Label(vr, text=estado_txt, font=('Segoe UI', 8, 'bold'),
                         bg=bg_v, width=8, anchor='w', fg=estado_fg).pack(side='left', padx=3, pady=1)

            # Resumen estadistico
            resumen = param.get('resumen') or {}
            if resumen.get('total_mediciones', 0) > 0:
                rs = tk.Frame(param_frame, bg='#f5f5f5')
                rs.pack(fill='x', pady=(3, 0))

                tend_map = {
                    'mejorando': ('\u2191 Mejorando', '#2e7d32'),
                    'empeorando': ('\u2193 Empeorando', '#c62828'),
                    'estable': ('\u2192 Estable', '#9e9e9e'),
                    'subiendo': ('\u2191 Subiendo', '#f59e0b'),
                    'bajando': ('\u2193 Bajando', '#f59e0b'),
                    'fluctuante': ('\u2194 Fluctuante', '#7c3aed'),
                }
                tend_txt, tend_col = tend_map.get(
                    resumen.get('tendencia_general', ''), ('---', '#9e9e9e')
                )

                stats_parts = []
                if resumen.get('minimo') is not None:
                    stats_parts.append(f"Mín: {resumen['minimo']}")
                if resumen.get('maximo') is not None:
                    stats_parts.append(f"Máx: {resumen['maximo']}")
                if resumen.get('promedio') is not None:
                    stats_parts.append(f"Prom: {resumen['promedio']}")
                stats_parts.append(f"N: {resumen.get('total_mediciones', 0)}")
                stats_str = "  |  ".join(stats_parts)

                tk.Label(rs, text=f"  {stats_str}",
                         font=('Segoe UI', 9), bg='#f5f5f5',
                         fg=COLORS['text'], anchor='w').pack(side='left', padx=5, pady=4)
                tk.Label(rs, text=f"  Tendencia: {tend_txt}  ",
                         font=('Segoe UI', 9, 'bold'), bg='#f5f5f5',
                         fg=tend_col, anchor='e').pack(side='right', padx=5, pady=4)

        # Leyenda
        legend_frame = tk.Frame(scroll_frame, bg='#f0f4f8', highlightbackground=COLORS['border'],
                                highlightthickness=1)
        legend_frame.pack(fill='x', pady=(15, 5), padx=5)

        tk.Label(legend_frame, text="Leyenda de Tendencias:",
                 font=('Segoe UI', 9, 'bold'), bg='#f0f4f8').pack(anchor='w', padx=10, pady=(5, 2))

        legends = [
            ("\u2191 / \u2193 Verde", "#2e7d32", "Mejorando (acercándose al rango normal)"),
            ("\u2191 / \u2193 Rojo", "#c62828", "Empeorando (alejándose del rango normal)"),
            ("\u2191 / \u2193 Ámbar", "#f59e0b", "Cambio detectado (sin rango de referencia)"),
            ("\u2192 Gris", "#9e9e9e", "Estable (sin cambio significativo)"),
            ("\u2014 Gris", "#9e9e9e", "Sin datos previos para comparar"),
        ]

        for text, color, desc in legends:
            leg_row = tk.Frame(legend_frame, bg='#f0f4f8')
            leg_row.pack(fill='x', padx=10, pady=1)
            tk.Label(leg_row, text=text, font=('Segoe UI', 9, 'bold'),
                     bg='#f0f4f8', fg=color, width=15, anchor='w').pack(side='left')
            tk.Label(leg_row, text=desc, font=('Segoe UI', 9),
                     bg='#f0f4f8', fg=COLORS['text_light']).pack(side='left', padx=5)

        tk.Label(legend_frame, text="", bg='#f0f4f8').pack(pady=2)

    # ============================================================
    # HISTORIAL - TAB GRÁFICAS (matplotlib)
    # ============================================================

    def _render_historial_graficas(self):
        """Renderiza la pestaña de gráficas de evolución con matplotlib."""
        frame = self.hist_detail_frame

        if not GRAFICAS_HISTORIAL_DISPONIBLE:
            tk.Label(frame,
                     text="📈 Gráficas no disponibles\n\nInstale matplotlib:\npip install matplotlib",
                     font=('Segoe UI', 12), bg='white', fg=COLORS['text_light'],
                     justify='center').pack(pady=80)
            return

        # Panel selector
        ctrl = tk.Frame(frame, bg='white')
        ctrl.pack(fill='x', pady=(0, 10))

        tk.Label(ctrl, text="Prueba:", font=('Segoe UI', 10, 'bold'),
                 bg='white').pack(side='left', padx=(0, 8))

        self.hist_graf_prueba_var = tk.StringVar()
        self.hist_graf_prueba_combo = ttk.Combobox(
            ctrl, textvariable=self.hist_graf_prueba_var,
            state='readonly', width=40, font=('Segoe UI', 10)
        )
        self.hist_graf_prueba_combo.pack(side='left', padx=(0, 10))

        tk.Button(
            ctrl, text="📈 Generar Gráficas",
            font=('Segoe UI', 10, 'bold'),
            bg=COLORS['primary'], fg='white', relief='flat',
            padx=16, pady=6, cursor='hand2',
            command=self._ejecutar_graficas_historial
        ).pack(side='left', padx=(0, 6))

        self.btn_exportar_png = tk.Button(
            ctrl, text="💾 Exportar PNG",
            font=('Segoe UI', 10),
            bg='#e8f5e9', fg='#2e7d32', relief='flat',
            padx=12, pady=6, cursor='hand2',
            command=self._exportar_grafica_png,
            state='disabled'
        )
        self.btn_exportar_png.pack(side='left')

        # Cargar lista de pruebas
        self._cargar_pruebas_historial_combo(
            self.hist_graf_prueba_combo, '_hist_graf_prueba_map'
        )

        # Área de gráfica (canvas scrollable)
        self.hist_graf_area = tk.Frame(frame, bg='#f8f9fa',
                                        highlightbackground=COLORS['border'],
                                        highlightthickness=1)
        self.hist_graf_area.pack(fill='both', expand=True)

        tk.Label(
            self.hist_graf_area,
            text="Seleccione una prueba y pulse 'Generar Gráficas'",
            font=('Segoe UI', 11), bg='#f8f9fa', fg=COLORS['text_light']
        ).pack(pady=80)

        self._figura_actual = None

    def _cargar_pruebas_historial_combo(self, combo, map_attr):
        """Carga la lista de pruebas con resultados en un combobox."""
        if not self.hist_paciente_id or not HISTORIAL_CLINICO_DISPONIBLE:
            return
        try:
            pruebas = self.gestor_historial.obtener_pruebas_con_resultados(
                self.hist_paciente_id
            )
            nombres = []
            mapa = {}
            for p in pruebas:
                label = f"{p.get('CodigoPrueba', '')} — {p.get('NombrePrueba', '')}"
                nombres.append(label)
                mapa[label] = p.get('PruebaID')
            combo['values'] = nombres
            if nombres:
                combo.current(0)
            setattr(self, map_attr, mapa)
        except Exception as e:
            print(f"[graficas] Error cargando pruebas: {e}")

    def _ejecutar_graficas_historial(self):
        """Genera y muestra las gráficas matplotlib para la prueba seleccionada."""
        prueba_label = self.hist_graf_prueba_var.get()
        mapa = getattr(self, '_hist_graf_prueba_map', {})
        prueba_id = mapa.get(prueba_label)
        if not prueba_id:
            messagebox.showwarning("Gráficas", "Seleccione una prueba.")
            return

        # Limpiar área anterior
        for w in self.hist_graf_area.winfo_children():
            w.destroy()

        loading = tk.Label(self.hist_graf_area,
                           text="⏳ Generando gráficas...",
                           font=('Segoe UI', 11), bg='#f8f9fa',
                           fg=COLORS['primary'])
        loading.pack(pady=60)
        self.hist_graf_area.update()

        try:
            datos = self.gestor_historial.obtener_evolucion_completa_prueba(
                self.hist_paciente_id, prueba_id
            )
            loading.destroy()

            if not datos or not datos.get('mediciones'):
                tk.Label(self.hist_graf_area,
                         text="No hay datos suficientes para graficar\n(se requieren al menos 2 mediciones)",
                         font=('Segoe UI', 11), bg='#f8f9fa',
                         fg=COLORS['text_light']).pack(pady=60)
                return

            gestor_graf = GraficasHistorial()
            nombre_prueba = prueba_label.split(' — ')[-1] if ' — ' in prueba_label else prueba_label
            fig = gestor_graf.generar_panel_prueba(datos, titulo_prueba=nombre_prueba)

            if fig is None:
                tk.Label(self.hist_graf_area,
                         text="Esta prueba no tiene parámetros numéricos para graficar.",
                         font=('Segoe UI', 11), bg='#f8f9fa',
                         fg=COLORS['text_light']).pack(pady=60)
                return

            self._figura_actual = fig
            gestor_graf.incrustar_en_frame(self.hist_graf_area, fig, mostrar_toolbar=False)
            self.btn_exportar_png.config(state='normal')

        except Exception as e:
            for w in self.hist_graf_area.winfo_children():
                w.destroy()
            tk.Label(self.hist_graf_area,
                     text=f"Error al generar gráficas:\n{e}",
                     font=('Segoe UI', 10), bg='#f8f9fa',
                     fg='#c62828').pack(pady=40)

    def _exportar_grafica_png(self):
        """Exporta la gráfica actual como PNG."""
        if not self._figura_actual:
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension='.png',
            filetypes=[('PNG Image', '*.png'), ('Todos los archivos', '*.*')],
            title='Exportar gráfica como PNG'
        )
        if ruta:
            gestor = GraficasHistorial()
            if gestor.exportar_png(self._figura_actual, ruta):
                messagebox.showinfo("Exportar PNG", f"Gráfica guardada en:\n{ruta}")
            else:
                messagebox.showerror("Error", "No se pudo exportar la gráfica.")

    # ============================================================
    # HISTORIAL - TAB IA CLÍNICA
    # ============================================================

    def _render_historial_ia_clinica(self):
        """Renderiza la pestaña de interpretación clínica con IA."""
        from tkinter.scrolledtext import ScrolledText

        frame = self.hist_detail_frame

        if not IA_INTERPRETACION_DISPONIBLE:
            tk.Label(frame,
                     text="🤖 Módulo de IA no disponible",
                     font=('Segoe UI', 12), bg='white',
                     fg=COLORS['text_light']).pack(pady=60)
            return

        # Panel de control superior
        ctrl = tk.Frame(frame, bg='white')
        ctrl.pack(fill='x', pady=(0, 8))

        # Fila 1: selector de prueba + botones
        fila1 = tk.Frame(ctrl, bg='white')
        fila1.pack(fill='x', pady=(0, 6))

        tk.Label(fila1, text="Prueba:", font=('Segoe UI', 10, 'bold'),
                 bg='white').pack(side='left', padx=(0, 8))

        self.hist_ia_prueba_var = tk.StringVar()
        self.hist_ia_prueba_combo = ttk.Combobox(
            fila1, textvariable=self.hist_ia_prueba_var,
            state='readonly', width=38, font=('Segoe UI', 10)
        )
        self.hist_ia_prueba_combo.pack(side='left', padx=(0, 10))

        tk.Button(
            fila1, text="🤖 Analizar con IA",
            font=('Segoe UI', 10, 'bold'),
            bg=COLORS['primary'], fg='white', relief='flat',
            padx=16, pady=6, cursor='hand2',
            command=self._ejecutar_ia_clinica
        ).pack(side='left', padx=(0, 6))

        tk.Button(
            fila1, text="⚙️ Config. IA",
            font=('Segoe UI', 9),
            bg='#f3f4f6', fg=COLORS['text'], relief='flat',
            padx=10, pady=6, cursor='hand2',
            command=self._abrir_config_ia
        ).pack(side='left', padx=(0, 6))

        # Fila 2: indicadores de estado de proveedores
        fila2 = tk.Frame(ctrl, bg='white')
        fila2.pack(fill='x')

        tk.Label(fila2, text="Proveedores:", font=('Segoe UI', 9),
                 bg='white', fg=COLORS['text_light']).pack(side='left', padx=(0, 8))

        self.lbl_estado_reglas = tk.Label(
            fila2, text="✅ Reglas locales", font=('Segoe UI', 9),
            bg='#e8f5e9', fg='#2e7d32', padx=6, pady=2, relief='flat'
        )
        self.lbl_estado_reglas.pack(side='left', padx=3)

        self.lbl_estado_ollama = tk.Label(
            fila2, text="⏳ Ollama...", font=('Segoe UI', 9),
            bg='#f3f4f6', fg=COLORS['text_light'], padx=6, pady=2
        )
        self.lbl_estado_ollama.pack(side='left', padx=3)

        self.lbl_estado_claude = tk.Label(
            fila2, text="⏳ Claude IA...", font=('Segoe UI', 9),
            bg='#f3f4f6', fg=COLORS['text_light'], padx=6, pady=2
        )
        self.lbl_estado_claude.pack(side='left', padx=3)

        # Botones de exportación (deshabilitados hasta tener resultado)
        fila_export = tk.Frame(ctrl, bg='white')
        fila_export.pack(fill='x', pady=(6, 0))

        self.btn_ia_pdf = tk.Button(
            fila_export, text="📄 Exportar PDF",
            font=('Segoe UI', 9),
            bg='#fff3e0', fg='#e65100', relief='flat',
            padx=12, pady=5, cursor='hand2',
            command=self._generar_pdf_ia_clinica,
            state='disabled'
        )
        self.btn_ia_pdf.pack(side='left', padx=(0, 6))

        self.btn_ia_print = tk.Button(
            fila_export, text="🖨️ Imprimir",
            font=('Segoe UI', 9),
            bg='#e3f2fd', fg='#1565c0', relief='flat',
            padx=12, pady=5, cursor='hand2',
            command=self._imprimir_interpretacion_ia,
            state='disabled'
        )
        self.btn_ia_print.pack(side='left', padx=(0, 6))

        self.btn_ia_copiar = tk.Button(
            fila_export, text="\U0001f4cb Copiar texto",
            font=('Segoe UI', 9),
            bg='#e8f5e9', fg='#2e7d32', relief='flat',
            padx=12, pady=5, cursor='hand2',
            command=self._copiar_texto_ia,
            state='disabled'
        )
        self.btn_ia_copiar.pack(side='left')

        self.lbl_ia_timestamp = tk.Label(
            fila_export, text="",
            font=('Segoe UI', 8, 'italic'), bg='white',
            fg=COLORS['text_light']
        )
        self.lbl_ia_timestamp.pack(side='right', padx=(10, 0))

        # Separador
        tk.Frame(frame, bg=COLORS['border'], height=1).pack(fill='x', pady=6)

        # Área de texto con resultado de IA
        self.ia_texto_result = ScrolledText(
            frame, font=('Segoe UI', 10),
            bg='white', fg=COLORS['text'],
            relief='flat', wrap='word',
            state='disabled', padx=12, pady=8
        )
        self.ia_texto_result.pack(fill='both', expand=True)

        # Configurar tags de estilo para el texto enriquecido
        self.ia_texto_result.tag_configure('titulo',
            font=('Segoe UI', 13, 'bold'), foreground='#1a237e')
        self.ia_texto_result.tag_configure('seccion',
            font=('Segoe UI', 11, 'bold'), foreground='#1565c0',
            spacing1=10, spacing3=4)
        self.ia_texto_result.tag_configure('seccion_ia',
            font=('Segoe UI', 11, 'bold'), foreground='#4a148c',
            spacing1=10, spacing3=4)
        self.ia_texto_result.tag_configure('normal',
            font=('Segoe UI', 10), foreground=COLORS['text'])
        self.ia_texto_result.tag_configure('alerta',
            font=('Segoe UI', 10, 'bold'), foreground='#c62828',
            background='#fff8f8')
        self.ia_texto_result.tag_configure('critico',
            font=('Segoe UI', 10, 'bold'), foreground='white',
            background='#c62828')
        self.ia_texto_result.tag_configure('ia',
            font=('Segoe UI', 10, 'italic'), foreground='#37474f',
            background='#f3e5f5', lmargin1=12, lmargin2=12)
        self.ia_texto_result.tag_configure('disclaimer',
            font=('Segoe UI', 9, 'italic'), foreground='#757575',
            background='#fffde7', spacing1=8)
        self.ia_texto_result.tag_configure('obs',
            font=('Segoe UI', 9, 'italic'), foreground='#5d4037',
            background='#fffde7', lmargin1=8, lmargin2=8)

        # Mensaje inicial
        self.ia_texto_result.config(state='normal')
        self.ia_texto_result.insert('end',
            "Seleccione una prueba y pulse 'Analizar con IA' para generar\n"
            "la interpretación clínica de los resultados del paciente.\n\n"
            "El sistema usa un motor de reglas clínicas local (siempre disponible)\n"
            "y puede enriquecerse con Ollama (LLM local) o Claude IA (online)\n"
            "si están configurados.", 'normal')
        self.ia_texto_result.config(state='disabled')

        # Cargar combo de pruebas
        self._cargar_pruebas_historial_combo(
            self.hist_ia_prueba_combo, '_hist_ia_prueba_map'
        )

        # Verificar estado proveedores en hilo
        self._verificar_estado_proveedores_ia()

        # Referencia a resultado de IA para PDF/print
        self._ia_resultado_actual = None
        self._ia_prueba_nombre_actual = ''

    def _verificar_estado_proveedores_ia(self):
        """Actualiza los indicadores de estado de los proveedores de IA (en hilo)."""
        if not IA_INTERPRETACION_DISPONIBLE:
            return
        import threading

        def _check():
            try:
                cfg_mgr = ConfigIA()
                config = cfg_mgr.leer()
                interp = InterpretadorClinico(config)
                estado = interp.estado_proveedores()
                # Actualizar UI en hilo principal
                self.root.after(0, self._actualizar_labels_proveedores, estado)
            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()

    def _actualizar_labels_proveedores(self, estado):
        """Callback para actualizar labels de proveedores IA desde el hilo principal."""
        try:
            # Ollama
            if estado.get('ollama'):
                self.lbl_estado_ollama.config(
                    text="✅ Ollama activo", bg='#e8f5e9', fg='#2e7d32')
            else:
                self.lbl_estado_ollama.config(
                    text="⭕ Ollama inactivo", bg='#f3f4f6', fg='#9e9e9e')

            # Claude
            if estado.get('claude'):
                self.lbl_estado_claude.config(
                    text="✅ Claude IA online", bg='#ede7f6', fg='#4a148c')
            elif estado.get('internet'):
                self.lbl_estado_claude.config(
                    text="🔑 Claude (sin API key)", bg='#fff8e1', fg='#e65100')
            else:
                self.lbl_estado_claude.config(
                    text="🌐 Sin internet", bg='#f3f4f6', fg='#9e9e9e')
        except Exception:
            pass

    def _ejecutar_ia_clinica(self):
        """Ejecuta el análisis de IA clínica sobre la prueba seleccionada."""
        prueba_label = self.hist_ia_prueba_var.get()
        mapa = getattr(self, '_hist_ia_prueba_map', {})
        prueba_id = mapa.get(prueba_label)
        if not prueba_id:
            messagebox.showwarning("IA Clínica", "Seleccione una prueba.")
            return

        # Mostrar estado de carga
        self.ia_texto_result.config(state='normal')
        self.ia_texto_result.delete('1.0', 'end')
        self.ia_texto_result.insert('end', "⏳ Analizando resultados...\n\n"
            "Esto puede tardar unos segundos si se usa IA online.", 'normal')
        self.ia_texto_result.config(state='disabled')
        self.ia_texto_result.update()

        try:
            # Preparar datos (operacion local rapida - se hace en hilo principal)
            datos_ia = self.gestor_historial.preparar_datos_para_ia(
                self.hist_paciente_id, prueba_id
            )

            if not datos_ia.get('resultados_actuales'):
                self.ia_texto_result.config(state='normal')
                self.ia_texto_result.delete('1.0', 'end')
                self.ia_texto_result.insert('end',
                    "No se encontraron resultados capturados para esta prueba.", 'normal')
                self.ia_texto_result.config(state='disabled')
                return

            nombre_prueba = datos_ia.get('prueba_info', {}).get('NombrePrueba', prueba_label)
            self._ia_prueba_nombre_actual = nombre_prueba
            self._ia_paciente_info_actual = datos_ia.get('paciente_info', {})

            # Obtener configuracion
            cfg_mgr = ConfigIA()
            config = cfg_mgr.leer()

            # Si el proveedor requiere red (ollama/claude), ejecutar en hilo
            proveedor = config.get('proveedor_ia', 'reglas')
            if proveedor in ('ollama', 'claude'):
                import threading
                threading.Thread(
                    target=self._ejecutar_ia_en_hilo,
                    args=(config, datos_ia, nombre_prueba),
                    daemon=True
                ).start()
            else:
                # Solo reglas locales: rapido, ejecutar directo
                self._ejecutar_ia_directo(config, datos_ia, nombre_prueba)

        except Exception as e:
            self.ia_texto_result.config(state='normal')
            self.ia_texto_result.delete('1.0', 'end')
            self.ia_texto_result.insert('end',
                f"Error al ejecutar análisis de IA:\n{e}", 'alerta')
            self.ia_texto_result.config(state='disabled')

    def _ejecutar_ia_directo(self, config, datos_ia, nombre_prueba):
        """Ejecuta la interpretación de IA de forma síncrona (para reglas locales)."""
        interp = InterpretadorClinico(config)
        resultado = interp.interpretar_completo(
            area_id=datos_ia.get('area_id'),
            resultados_parametros=datos_ia.get('resultados_actuales', []),
            paciente_info=datos_ia.get('paciente_info', {}),
            prueba_nombre=nombre_prueba,
            historial_previo=datos_ia.get('historial_evolucion', {})
        )
        self._mostrar_resultado_ia(interp, resultado, nombre_prueba)

    def _ejecutar_ia_en_hilo(self, config, datos_ia, nombre_prueba):
        """Ejecuta la interpretación de IA en hilo secundario (para Ollama/Claude)."""
        try:
            interp = InterpretadorClinico(config)
            resultado = interp.interpretar_completo(
                area_id=datos_ia.get('area_id'),
                resultados_parametros=datos_ia.get('resultados_actuales', []),
                paciente_info=datos_ia.get('paciente_info', {}),
                prueba_nombre=nombre_prueba,
                historial_previo=datos_ia.get('historial_evolucion', {})
            )
            # Actualizar UI en hilo principal
            self.root.after(0, self._mostrar_resultado_ia, interp, resultado, nombre_prueba)
        except Exception as e:
            self.root.after(0, self._mostrar_error_ia, str(e))

    def _mostrar_resultado_ia(self, interp, resultado, nombre_prueba):
        """Renderiza el resultado de IA en el widget de texto (siempre en hilo principal)."""
        try:
            self._ia_resultado_actual = resultado

            partes = interp.formatear_reporte_texto(
                resultado, prueba_nombre=nombre_prueba,
                fecha=datetime.now()
            )

            self.ia_texto_result.config(state='normal')
            self.ia_texto_result.delete('1.0', 'end')

            # Mostrar contexto clínico de la solicitud si existe
            pac_info = getattr(self, '_ia_paciente_info_actual', {})
            diag = str(pac_info.get('DiagnosticoPresuntivo', '') or '').strip()
            obs = str(pac_info.get('ObservacionesSolicitud', '') or '').strip()
            if diag or obs:
                self.ia_texto_result.insert('end', "\U0001f4cb CONTEXTO CLÍNICO DE LA SOLICITUD\n", 'seccion')
                if diag:
                    self.ia_texto_result.insert('end', f"  Dx presuntivo: {diag}\n", 'obs')
                if obs:
                    self.ia_texto_result.insert('end', f"  Observaciones: {obs}\n", 'obs')
                self.ia_texto_result.insert('end', "\n", 'normal')

            for texto, tag in partes:
                self.ia_texto_result.insert('end', texto, tag)

            self.ia_texto_result.config(state='disabled')
            self.ia_texto_result.see('1.0')

            # Habilitar botones de exportación y utilidades
            self.btn_ia_pdf.config(state='normal')
            self.btn_ia_print.config(state='normal')
            if hasattr(self, 'btn_ia_copiar'):
                self.btn_ia_copiar.config(state='normal')
            if hasattr(self, 'lbl_ia_timestamp'):
                prov = resultado.get('proveedor_usado', 'reglas')
                prov_lbl = {'reglas': 'Reglas locales', 'ollama': 'Ollama', 'claude': 'Claude IA'}.get(prov, prov)
                self.lbl_ia_timestamp.config(
                    text=f"Analizado: {datetime.now().strftime('%H:%M:%S')}  \u2502  Motor: {prov_lbl}"
                )
        except Exception as e:
            self._mostrar_error_ia(str(e))

    def _mostrar_error_ia(self, mensaje_error):
        """Muestra un error de IA en el widget de texto."""
        try:
            self.ia_texto_result.config(state='normal')
            self.ia_texto_result.delete('1.0', 'end')
            self.ia_texto_result.insert('end',
                f"Error al ejecutar análisis de IA:\n{mensaje_error}", 'alerta')
            self.ia_texto_result.config(state='disabled')
        except Exception:
            pass

    def _generar_pdf_ia_clinica(self):
        """Genera un PDF con la interpretación clínica de IA."""
        if not self._ia_resultado_actual:
            messagebox.showwarning("PDF", "Primero ejecute el análisis de IA.")
            return
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("PDF",
                "ReportLab no está instalado. Instale con: pip install reportlab")
            return

        ruta = filedialog.asksaveasfilename(
            defaultextension='.pdf',
            filetypes=[('PDF', '*.pdf'), ('Todos los archivos', '*.*')],
            title='Guardar interpretación clínica como PDF'
        )
        if not ruta:
            return

        try:
            self._crear_pdf_interpretacion_ia(ruta)
            messagebox.showinfo("PDF exportado",
                f"Reporte clínico con IA guardado en:\n{ruta}")
        except Exception as e:
            messagebox.showerror("Error PDF", f"No se pudo generar el PDF:\n{e}")

    def _crear_pdf_interpretacion_ia(self, ruta_pdf):
        """Crea el PDF de interpretación clínica con ReportLab."""
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors as rl_colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, Image as RLImage, KeepTogether
        )
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        import io as _io

        interp_result = self._ia_resultado_actual
        nombre_prueba = self._ia_prueba_nombre_actual
        paciente_id = self.hist_paciente_id

        # --- Datos de laboratorio ---
        lab_nombre = "Laboratorio Clínico"
        lab_sub = ""
        try:
            cfg_admin = self.db.query_one(
                "SELECT TOP 1 NombreLaboratorio, RazonSocial FROM ConfiguracionLaboratorio"
            )
            if cfg_admin:
                lab_nombre = cfg_admin.get('NombreLaboratorio', 'Laboratorio Clínico') or 'Laboratorio Clínico'
                lab_sub = cfg_admin.get('RazonSocial', '') or ''
        except Exception:
            pass

        # --- Datos del paciente ---
        pac_nombre = 'N/A'
        pac_doc = ''
        pac_edad = ''
        pac_sexo = ''
        try:
            pac = self.db.query_one(
                f"SELECT Nombres & ' ' & Apellidos AS NombreCompleto, "
                f"NumeroDocumento, FechaNacimiento, Sexo "
                f"FROM Pacientes WHERE PacienteID = {paciente_id}"
            )
            if pac:
                pac_nombre = pac.get('NombreCompleto', 'N/A') or 'N/A'
                pac_doc = str(pac.get('NumeroDocumento', '') or '')
                pac_sexo = str(pac.get('Sexo', '') or '')
                fn = pac.get('FechaNacimiento')
                if fn:
                    try:
                        hoy = datetime.now()
                        edad_v = hoy.year - fn.year - (
                            (hoy.month, hoy.day) < (fn.month, fn.day))
                        pac_edad = f"{edad_v} años"
                    except Exception:
                        pass
        except Exception:
            pass

        # --- Estilos ---
        styles = getSampleStyleSheet()
        st_titulo = ParagraphStyle('ia_titulo',
            fontName='Helvetica-Bold', fontSize=16,
            textColor=rl_colors.HexColor('#1a237e'), alignment=TA_CENTER,
            spaceAfter=4)
        st_subtitulo = ParagraphStyle('ia_sub',
            fontName='Helvetica', fontSize=11,
            textColor=rl_colors.HexColor('#1565c0'), alignment=TA_CENTER,
            spaceAfter=2)
        st_seccion = ParagraphStyle('ia_sec',
            fontName='Helvetica-Bold', fontSize=11,
            textColor=rl_colors.HexColor('#1565c0'),
            spaceBefore=12, spaceAfter=4)
        st_normal = ParagraphStyle('ia_norm',
            fontName='Helvetica', fontSize=10,
            textColor=rl_colors.HexColor('#37474f'),
            leading=15, spaceAfter=3)
        st_alerta = ParagraphStyle('ia_alerta',
            fontName='Helvetica-Bold', fontSize=10,
            textColor=rl_colors.HexColor('#c62828'), spaceAfter=2)
        st_ia = ParagraphStyle('ia_ia',
            fontName='Helvetica-Oblique', fontSize=10,
            textColor=rl_colors.HexColor('#37474f'),
            backColor=rl_colors.HexColor('#f3e5f5'),
            borderPadding=(4, 8, 4, 8), leading=16, spaceAfter=6)
        st_disclaimer = ParagraphStyle('ia_disc',
            fontName='Helvetica-Oblique', fontSize=8,
            textColor=rl_colors.HexColor('#757575'),
            backColor=rl_colors.HexColor('#fffde7'),
            borderPadding=(4, 6, 4, 6), spaceBefore=10, leading=13)
        st_lab = ParagraphStyle('ia_lab',
            fontName='Helvetica-Bold', fontSize=14,
            textColor=rl_colors.HexColor('#1a237e'), alignment=TA_CENTER)
        st_info_pac = ParagraphStyle('ia_pac',
            fontName='Helvetica', fontSize=10,
            textColor=rl_colors.HexColor('#212121'),
            leading=16, spaceAfter=4)

        # --- Documento ---
        doc = SimpleDocTemplate(
            ruta_pdf, pagesize=letter,
            leftMargin=2*cm, rightMargin=2*cm,
            topMargin=2.5*cm, bottomMargin=2.5*cm
        )
        historia = []

        # Header laboratorio
        historia.append(Paragraph(lab_nombre, st_lab))
        if lab_sub:
            historia.append(Paragraph(lab_sub, st_subtitulo))
        historia.append(HRFlowable(width='100%', thickness=2,
                                    color=rl_colors.HexColor('#1565c0')))
        historia.append(Spacer(1, 0.3*cm))

        historia.append(Paragraph(
            f"INFORME DE INTERPRETACIÓN CLÍNICA — {nombre_prueba.upper()}", st_titulo))
        historia.append(Paragraph(
            f"Fecha de emisión: {datetime.now().strftime('%d/%m/%Y %H:%M')}", st_subtitulo))
        historia.append(Spacer(1, 0.4*cm))

        # Info paciente (tabla)
        data_pac = [
            ['Paciente:', pac_nombre, 'Documento:', pac_doc],
            ['Edad:', pac_edad, 'Sexo:', pac_sexo],
        ]
        tbl_pac = Table(data_pac, colWidths=[3.5*cm, 7.5*cm, 3*cm, 4*cm])
        tbl_pac.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), rl_colors.HexColor('#212121')),
            ('BACKGROUND', (0, 0), (-1, -1), rl_colors.HexColor('#e3f2fd')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1),
             [rl_colors.HexColor('#e3f2fd'), rl_colors.HexColor('#f5f5f5')]),
            ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#90caf9')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        historia.append(tbl_pac)

        # Contexto clínico de la solicitud (DiagnosticoPresuntivo y Observaciones)
        pac_info_ia = getattr(self, '_ia_paciente_info_actual', {})
        diag_pdf = str(pac_info_ia.get('DiagnosticoPresuntivo', '') or '').strip()
        obs_pdf = str(pac_info_ia.get('ObservacionesSolicitud', '') or '').strip()
        if diag_pdf or obs_pdf:
            st_ctx = ParagraphStyle('ia_ctx',
                fontName='Helvetica-Oblique', fontSize=9,
                textColor=rl_colors.HexColor('#5d4037'),
                backColor=rl_colors.HexColor('#fffde7'),
                borderPadding=(4, 8, 4, 8), leading=14, spaceAfter=4,
                spaceBefore=4)
            ctx_lines = []
            if diag_pdf:
                ctx_lines.append(f"<b>Dx presuntivo:</b> {diag_pdf}")
            if obs_pdf:
                ctx_lines.append(f"<b>Observaciones:</b> {obs_pdf}")
            historia.append(Paragraph("<br/>".join(ctx_lines), st_ctx))
        historia.append(Spacer(1, 0.5*cm))

        # Resumen ejecutivo
        historia.append(Paragraph("RESUMEN", st_seccion))
        historia.append(Paragraph(
            interp_result.get('resumen_ejecutivo', ''), st_normal))

        # Parámetros alterados
        params = interp_result.get('parametros_alterados', [])
        if params:
            historia.append(Paragraph("PARÁMETROS ALTERADOS", st_seccion))
            data_p = [['Parámetro', 'Valor', 'Unidad', 'Referencia', 'Estado']]
            for p in params:
                data_p.append([
                    p.get('nombre', ''),
                    str(p.get('valor', '')),
                    p.get('unidad', ''),
                    p.get('referencia', 'N/D'),
                    p.get('estado', '').upper(),
                ])
            col_w = [5.5*cm, 2.5*cm, 2.5*cm, 4*cm, 3*cm]
            tbl_p = Table(data_p, colWidths=col_w)
            tbl_p.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), rl_colors.HexColor('#1565c0')),
                ('TEXTCOLOR', (0, 0), (-1, 0), rl_colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, rl_colors.HexColor('#bdbdbd')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1),
                 [rl_colors.HexColor('#fff8f8'), rl_colors.HexColor('#ffffff')]),
                ('TEXTCOLOR', (4, 1), (4, -1), rl_colors.HexColor('#c62828')),
                ('FONTNAME', (4, 1), (4, -1), 'Helvetica-Bold'),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            historia.append(tbl_p)
            historia.append(Spacer(1, 0.3*cm))

        # Análisis por reglas
        obs_reglas = interp_result.get('interpretacion_reglas', [])
        if obs_reglas:
            historia.append(Paragraph("ANÁLISIS CLÍNICO (MOTOR LOCAL)", st_seccion))
            for obs in obs_reglas:
                historia.append(Paragraph(f"• {obs}", st_normal))
            historia.append(Spacer(1, 0.3*cm))

        # Interpretación IA
        ia_texto = interp_result.get('interpretacion_ia', '')
        proveedor = interp_result.get('proveedor_usado', 'reglas')
        if ia_texto:
            label_prov = 'OLLAMA (LLM LOCAL)' if proveedor == 'ollama' else 'CLAUDE IA (ONLINE)'
            historia.append(Paragraph(
                f"INTERPRETACIÓN AVANZADA — {label_prov}", st_seccion))
            # Dividir por párrafos para mejor renderizado
            for linea in ia_texto.split('\n'):
                if linea.strip():
                    historia.append(Paragraph(linea.strip(), st_ia))
            historia.append(Spacer(1, 0.3*cm))

        # Gráfica de evolución (si disponible)
        if GRAFICAS_HISTORIAL_DISPONIBLE and self.hist_paciente_id:
            try:
                mapa = getattr(self, '_hist_ia_prueba_map', {})
                prueba_label = self.hist_ia_prueba_var.get() if hasattr(self, 'hist_ia_prueba_var') else ''
                prueba_id = mapa.get(prueba_label)
                if prueba_id:
                    datos_ev = self.gestor_historial.obtener_evolucion_completa_prueba(
                        self.hist_paciente_id, prueba_id
                    )
                    if datos_ev and datos_ev.get('mediciones') and len(datos_ev['mediciones']) > 1:
                        gestor_graf = GraficasHistorial()
                        fig = gestor_graf.generar_panel_prueba(
                            datos_ev, titulo_prueba=nombre_prueba)
                        if fig:
                            img_bytes = gestor_graf.figura_a_imagen_bytes(fig, dpi=130)
                            if img_bytes:
                                historia.append(
                                    Paragraph("EVOLUCIÓN HISTÓRICA", st_seccion))
                                img_buf = _io.BytesIO(img_bytes)
                                rl_img = RLImage(img_buf, width=17*cm,
                                                  height=9*cm, kind='proportional')
                                historia.append(rl_img)
                                historia.append(Spacer(1, 0.3*cm))
            except Exception as e:
                print(f"[PDF IA] Error insertando gráfica: {e}")

        # Disclaimer
        from modulos.ia_interpretacion import DISCLAIMER as IA_DISCLAIMER
        historia.append(HRFlowable(width='100%', thickness=1,
                                    color=rl_colors.HexColor('#bdbdbd')))
        historia.append(Paragraph(f"⚠️ {IA_DISCLAIMER}", st_disclaimer))

        doc.build(historia)

    def _imprimir_interpretacion_ia(self):
        """Imprime la interpretación clínica generando un PDF temporal."""
        if not self._ia_resultado_actual:
            messagebox.showwarning("Imprimir", "Primero ejecute el análisis de IA.")
            return
        import tempfile
        import os
        try:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tf:
                ruta_tmp = tf.name
            self._crear_pdf_interpretacion_ia(ruta_tmp)
            os.startfile(ruta_tmp, 'print')
        except Exception as e:
            messagebox.showerror("Error al imprimir",
                f"No se pudo generar el documento para impresión:\n{e}")

    def _abrir_config_ia(self):
        """Abre el diálogo de configuración del motor de IA."""
        if not IA_INTERPRETACION_DISPONIBLE:
            return

        dlg = tk.Toplevel(self.root)
        dlg.title("Configuración IA Clínica")
        dlg.geometry("520x380")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.configure(bg='white')

        tk.Label(dlg, text="🤖 Configuración — IA Clínica",
                 font=('Segoe UI', 13, 'bold'), bg='white',
                 fg='#1a237e').pack(pady=(20, 5))
        tk.Label(dlg, text="Configure el proveedor de inteligencia artificial para interpretación",
                 font=('Segoe UI', 9), bg='white', fg='#757575').pack(pady=(0, 15))

        # Leer config actual
        cfg_mgr = ConfigIA()
        config_actual = cfg_mgr.leer()

        form = tk.Frame(dlg, bg='white', padx=30)
        form.pack(fill='x')

        def lbl(texto):
            tk.Label(form, text=texto, font=('Segoe UI', 10, 'bold'),
                     bg='white', anchor='w').pack(fill='x', pady=(8, 2))

        def campo(valor_default='', ancho=45):
            e = tk.Entry(form, font=('Segoe UI', 10), width=ancho,
                         relief='flat', bg='#f8f9fa',
                         highlightthickness=1,
                         highlightbackground=COLORS['border'])
            e.pack(fill='x', ipady=5)
            if valor_default:
                e.insert(0, valor_default)
            return e

        lbl("Proveedor de IA:")
        var_prov = tk.StringVar(value=config_actual.get('proveedor_ia', 'reglas'))
        frame_prov = tk.Frame(form, bg='white')
        frame_prov.pack(fill='x', pady=2)
        for val, txt in [('reglas', '✅ Solo reglas locales'),
                          ('ollama', '🦙 Ollama (LLM local)'),
                          ('claude', '🌐 Claude IA (online)')]:
            tk.Radiobutton(frame_prov, text=txt, variable=var_prov, value=val,
                           font=('Segoe UI', 10), bg='white').pack(side='left', padx=8)

        lbl("URL de Ollama:")
        e_ollama = campo(config_actual.get('ollama_url', 'http://localhost:11434'))

        lbl("Modelo Ollama:")
        e_modelo = campo(config_actual.get('ollama_modelo', 'llama3.2'), ancho=25)

        lbl("Claude API Key (sk-ant-...):")
        e_apikey = campo(config_actual.get('claude_api_key', ''))
        e_apikey.config(show='*')

        # Botones
        btns = tk.Frame(dlg, bg='white')
        btns.pack(pady=20)

        def guardar():
            nueva_config = {
                'proveedor_ia': var_prov.get(),
                'ollama_url': e_ollama.get().strip(),
                'ollama_modelo': e_modelo.get().strip() or 'llama3.2',
                'claude_api_key': e_apikey.get().strip(),
                'ia_activa': True,
            }
            cfg_mgr.guardar(nueva_config)
            messagebox.showinfo("Configuración", "Configuración guardada correctamente.",
                                parent=dlg)
            dlg.destroy()
            self._verificar_estado_proveedores_ia()

        tk.Button(btns, text="💾 Guardar",
                  font=('Segoe UI', 10, 'bold'),
                  bg=COLORS['primary'], fg='white', relief='flat',
                  padx=20, pady=8, cursor='hand2',
                  command=guardar).pack(side='left', padx=8)
        tk.Button(btns, text="Cancelar",
                  font=('Segoe UI', 10),
                  bg='#f3f4f6', fg=COLORS['text'], relief='flat',
                  padx=20, pady=8, cursor='hand2',
                  command=dlg.destroy).pack(side='left', padx=8)

    def _copiar_texto_ia(self):
        """Copia el texto del resultado de IA al portapapeles del sistema."""
        try:
            texto = self.ia_texto_result.get('1.0', 'end').strip()
            if not texto:
                return
            self.root.clipboard_clear()
            self.root.clipboard_append(texto)
            self.root.update()
            # Feedback visual temporal en el boton
            if hasattr(self, 'btn_ia_copiar'):
                self.btn_ia_copiar.config(text="\u2713 Copiado!")
                self.root.after(1800, lambda: self.btn_ia_copiar.config(
                    text="\U0001f4cb Copiar texto") if hasattr(self, 'btn_ia_copiar') else None)
        except Exception as e:
            messagebox.showerror("Error al copiar",
                f"No se pudo copiar al portapapeles:\n{e}")

    def _ir_a_ia_con_prueba(self, prueba_id):
        """Navega a la pestaña de IA Clínica y preselecciona la prueba indicada."""
        self._cambiar_tab_historial('ia_clinica')
        # Dar tiempo al render y luego seleccionar la prueba en el combo
        def _seleccionar():
            if hasattr(self, '_hist_ia_prueba_map') and hasattr(self, 'hist_ia_prueba_combo'):
                target = next(
                    (k for k, v in self._hist_ia_prueba_map.items() if v == prueba_id),
                    None
                )
                if target:
                    self.hist_ia_prueba_combo.set(target)
        self.root.after(50, _seleccionar)

    # ============================================================
    # REPORTES
    # ============================================================

    def show_reportes(self):
        self.clear_content()
        self.set_title("📈 Reportes y Estadísticas")

        # Configurar contenido scrollable
        scrollable = self.setup_scrollable_content()

        frame = tk.Frame(scrollable, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        reportes = [
            ("📊", "Solicitudes por Período", "Reporte de solicitudes en un rango de fechas", self.reporte_solicitudes, COLORS['primary']),
            ("👥", "Listado de Pacientes", "Exportar listado completo de pacientes", self.reporte_pacientes, COLORS['info']),
            ("🧪", "Catálogo de Pruebas", "Listado de todas las pruebas disponibles", self.reporte_pruebas, COLORS['warning']),
            ("🩺", "Listado de Médicos", "Directorio de médicos referentes", self.reporte_medicos, COLORS['danger']),
            ("📈", "Estadísticas Generales", "Resumen estadístico del sistema", self.reporte_estadisticas, COLORS['success']),
        ]

        for icon, titulo, desc, cmd, color in reportes:
            card = tk.Frame(frame, bg='#f8f9fa', relief='flat')
            card.pack(fill='x', pady=8, ipady=5)

            left = tk.Frame(card, bg='#f8f9fa')
            left.pack(side='left', fill='y', padx=15, pady=10)

            tk.Label(left, text=icon, font=('Segoe UI', 24), bg='#f8f9fa', fg=color).pack(side='left', padx=(0, 15))

            info = tk.Frame(left, bg='#f8f9fa')
            info.pack(side='left')
            tk.Label(info, text=titulo, font=('Segoe UI', 12, 'bold'), bg='#f8f9fa', fg=COLORS['text']).pack(anchor='w')
            tk.Label(info, text=desc, font=('Segoe UI', 10), bg='#f8f9fa', fg=COLORS['text_light']).pack(anchor='w')

            tk.Button(card, text="Generar", font=('Segoe UI', 10),
                     bg=color, fg='white', relief='flat', padx=20, pady=5,
                     cursor='hand2', command=cmd).pack(side='right', padx=15, pady=10)

    def reporte_solicitudes(self):
        try:
            data = db.query("""
                SELECT s.NumeroSolicitud, s.FechaSolicitud, p.Nombres & ' ' & p.Apellidos AS Paciente,
                       s.EstadoSolicitud, s.MontoTotal
                FROM Solicitudes s LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                ORDER BY s.FechaSolicitud DESC
            """)
            self.exportar_csv(data, "Reporte_Solicitudes", ['NumeroSolicitud', 'FechaSolicitud', 'Paciente', 'EstadoSolicitud', 'MontoTotal'])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reporte_pacientes(self):
        try:
            data = db.query("SELECT NumeroDocumento, Nombres, Apellidos, Telefono1, Email FROM Pacientes ORDER BY Apellidos")
            self.exportar_csv(data, "Reporte_Pacientes", ['NumeroDocumento', 'Nombres', 'Apellidos', 'Telefono1', 'Email'])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reporte_pruebas(self):
        try:
            data = db.query("""
                SELECT p.CodigoPrueba, p.NombrePrueba, a.NombreArea, IIF(p.Activo, 'Sí', 'No') AS Activo
                FROM Pruebas p LEFT JOIN Areas a ON p.AreaID = a.AreaID
                ORDER BY p.NombrePrueba
            """)
            self.exportar_csv(data, "Catalogo_Pruebas", ['CodigoPrueba', 'NombrePrueba', 'NombreArea', 'Activo'])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reporte_medicos(self):
        try:
            data = db.query("SELECT CodigoMedico, Nombres, Apellidos, Especialidad, Telefono1, Email FROM Medicos ORDER BY Apellidos")
            self.exportar_csv(data, "Directorio_Medicos", ['CodigoMedico', 'Nombres', 'Apellidos', 'Especialidad', 'Telefono1', 'Email'])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def reporte_estadisticas(self):
        try:
            stats = f"""
ESTADÍSTICAS GENERALES - ANgesLAB
Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}
{'='*50}

Total de Pacientes: {db.count('Pacientes'):,}
Total de Médicos: {db.count('Medicos'):,}
Total de Pruebas: {db.count('Pruebas'):,}
Total de Solicitudes: {db.count('Solicitudes'):,}
Total de Áreas: {db.count('Areas'):,}
Total de Gérmenes: {db.count('Germenes'):,}
Total de Antimicrobianos: {db.count('Antimicrobianos'):,}
            """
            messagebox.showinfo("Estadísticas Generales", stats)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def exportar_csv(self, data, nombre, campos):
        if not data:
            messagebox.showinfo("Info", "No hay datos para exportar")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfilename=f"{nombre}_{datetime.now().strftime('%Y%m%d')}.csv"
        )

        if filename:
            try:
                with open(filename, 'w', encoding='utf-8-sig') as f:
                    f.write(';'.join(campos) + '\n')
                    for row in data:
                        values = []
                        for c in campos:
                            val = row.get(c, '')
                            if isinstance(val, datetime):
                                val = val.strftime('%d/%m/%Y')
                            values.append(str(val or ''))
                        f.write(';'.join(values) + '\n')
                messagebox.showinfo("Éxito", f"Reporte exportado:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    # ============================================================
    # ADMINISTRACIÓN DE PARÁMETROS
    # ============================================================

    def show_parametros(self):
        """Sección de administración de parámetros de pruebas"""
        if not self.es_admin():
            messagebox.showwarning("Acceso Denegado", "Esta función requiere nivel Administrador")
            return
        self.clear_content()
        self.set_title("🔧 Administración de Parámetros")

        # Configurar contenido scrollable
        scrollable = self.setup_scrollable_content()

        # Frame principal dividido en dos paneles
        main_frame = tk.Frame(scrollable, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True)

        # Panel izquierdo - Lista de Pruebas
        left_panel = tk.Frame(main_frame, bg='white', width=350)
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="📋 Pruebas", font=('Segoe UI', 12, 'bold'),
                bg='white', fg=COLORS['text']).pack(anchor='w', padx=15, pady=10)

        # Búsqueda de pruebas
        search_frame = tk.Frame(left_panel, bg='white')
        search_frame.pack(fill='x', padx=10, pady=5)

        self.search_prueba_param = tk.Entry(search_frame, font=('Segoe UI', 10))
        self.search_prueba_param.pack(side='left', fill='x', expand=True, ipady=5)
        self.search_prueba_param.bind('<KeyRelease>', lambda e: self.filtrar_pruebas_param())

        # Lista de pruebas
        tree_frame = tk.Frame(left_panel, bg='white')
        tree_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.tree_pruebas_param = ttk.Treeview(tree_frame, columns=('ID', 'Codigo', 'Nombre'), show='headings', height=20)
        self.tree_pruebas_param.heading('ID', text='ID')
        self.tree_pruebas_param.heading('Codigo', text='Código')
        self.tree_pruebas_param.heading('Nombre', text='Nombre')
        self.tree_pruebas_param.column('ID', width=40)
        self.tree_pruebas_param.column('Codigo', width=70)
        self.tree_pruebas_param.column('Nombre', width=200)

        scroll_pruebas = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree_pruebas_param.yview)
        self.tree_pruebas_param.configure(yscrollcommand=scroll_pruebas.set)

        self.tree_pruebas_param.pack(side='left', fill='both', expand=True)
        scroll_pruebas.pack(side='right', fill='y')

        self.tree_pruebas_param.bind('<<TreeviewSelect>>', self.cargar_parametros_prueba)

        # Panel derecho - Parámetros de la prueba seleccionada
        right_panel = tk.Frame(main_frame, bg='white')
        right_panel.pack(side='right', fill='both', expand=True)

        # Título del panel derecho
        self.lbl_prueba_seleccionada = tk.Label(right_panel, text="Seleccione una prueba",
                font=('Segoe UI', 12, 'bold'), bg='white', fg=COLORS['text'])
        self.lbl_prueba_seleccionada.pack(anchor='w', padx=15, pady=10)

        # Toolbar de parámetros
        toolbar_param = tk.Frame(right_panel, bg='white')
        toolbar_param.pack(fill='x', padx=15, pady=5)

        tk.Button(toolbar_param, text="➕ Nuevo Parámetro", font=('Segoe UI', 9),
                 bg=COLORS['success'], fg='white', relief='flat', padx=10, pady=5,
                 cursor='hand2', command=self.nuevo_parametro).pack(side='left', padx=2)

        tk.Button(toolbar_param, text="✏️ Editar", font=('Segoe UI', 9),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=10, pady=5,
                 cursor='hand2', command=self.editar_parametro).pack(side='left', padx=2)

        tk.Button(toolbar_param, text="🗑️ Eliminar", font=('Segoe UI', 9),
                 bg=COLORS['danger'], fg='white', relief='flat', padx=10, pady=5,
                 cursor='hand2', command=self.eliminar_parametro).pack(side='left', padx=2)

        tk.Button(toolbar_param, text="📥 Agregar Existente", font=('Segoe UI', 9),
                 bg=COLORS['info'], fg='white', relief='flat', padx=10, pady=5,
                 cursor='hand2', command=self.agregar_parametro_existente).pack(side='left', padx=2)

        tk.Button(toolbar_param, text="⬆⬇ Reordenar", font=('Segoe UI', 9),
                 bg=COLORS['warning'], fg='white', relief='flat', padx=10, pady=5,
                 cursor='hand2', command=self.reordenar_parametros).pack(side='left', padx=2)

        # Separador
        tk.Frame(toolbar_param, bg=COLORS['border'], width=2).pack(side='left', fill='y', padx=10, pady=2)

        # Botón de Perfiles
        tk.Button(toolbar_param, text="📦 GESTIONAR PERFILES", font=('Segoe UI', 9, 'bold'),
                 bg='#8e44ad', fg='white', relief='flat', padx=15, pady=5,
                 cursor='hand2', command=self.gestionar_perfiles).pack(side='left', padx=2)

        # Lista de parámetros
        param_frame = tk.Frame(right_panel, bg='white')
        param_frame.pack(fill='both', expand=True, padx=15, pady=10)

        columns_param = ('Sec', 'ID', 'Código', 'Nombre', 'Tipo', 'Referencia', 'Sección')
        self.tree_params = ttk.Treeview(param_frame, columns=columns_param, show='headings')

        self.tree_params.heading('Sec', text='#')
        self.tree_params.heading('ID', text='ID')
        self.tree_params.heading('Código', text='Código')
        self.tree_params.heading('Nombre', text='Nombre')
        self.tree_params.heading('Tipo', text='Tipo')
        self.tree_params.heading('Referencia', text='Valor Referencia')
        self.tree_params.heading('Sección', text='Sección')

        self.tree_params.column('Sec', width=35)
        self.tree_params.column('ID', width=40)
        self.tree_params.column('Código', width=100)
        self.tree_params.column('Nombre', width=180)
        self.tree_params.column('Tipo', width=80)
        self.tree_params.column('Referencia', width=150)
        self.tree_params.column('Sección', width=120)

        scroll_params = ttk.Scrollbar(param_frame, orient='vertical', command=self.tree_params.yview)
        self.tree_params.configure(yscrollcommand=scroll_params.set)

        self.tree_params.pack(side='left', fill='both', expand=True)
        scroll_params.pack(side='right', fill='y')

        # Cargar pruebas
        self.cargar_lista_pruebas_param()

    def cargar_lista_pruebas_param(self, filtro=""):
        """Carga la lista de pruebas"""
        for item in self.tree_pruebas_param.get_children():
            self.tree_pruebas_param.delete(item)

        where = "WHERE Activo = True"
        if filtro:
            where += f" AND (NombrePrueba LIKE '%{filtro}%' OR CodigoPrueba LIKE '%{filtro}%')"

        pruebas = db.query(f"""
            SELECT PruebaID, CodigoPrueba, NombrePrueba
            FROM Pruebas {where}
            ORDER BY NombrePrueba
        """)

        for p in pruebas:
            self.tree_pruebas_param.insert('', 'end', values=(
                p['PruebaID'],
                p['CodigoPrueba'] or '',
                p['NombrePrueba'] or ''
            ))

    def filtrar_pruebas_param(self):
        """Filtra la lista de pruebas"""
        filtro = self.search_prueba_param.get().strip()
        self.cargar_lista_pruebas_param(filtro)

    def cargar_parametros_prueba(self, event=None):
        """Carga los parámetros de la prueba seleccionada"""
        sel = self.tree_pruebas_param.selection()
        if not sel:
            return

        valores = self.tree_pruebas_param.item(sel[0])['values']
        self.prueba_id_seleccionada = valores[0]
        nombre_prueba = valores[2]

        self.lbl_prueba_seleccionada.config(text=f"📋 Parámetros de: {nombre_prueba}")

        # Limpiar lista de parámetros
        for item in self.tree_params.get_children():
            self.tree_params.delete(item)

        # Cargar parámetros
        parametros = db.query(f"""
            SELECT pp.Secuencia, pp.ParametroID, par.CodigoParametro, par.NombreParametro,
                   par.TipoResultado, par.Observaciones, par.Seccion
            FROM ParametrosPrueba pp
            INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID
            WHERE pp.PruebaID = {self.prueba_id_seleccionada}
            ORDER BY pp.Secuencia
        """)

        for p in parametros:
            self.tree_params.insert('', 'end', values=(
                p['Secuencia'] or '',
                p['ParametroID'],
                p['CodigoParametro'] or '',
                p['NombreParametro'] or '',
                p['TipoResultado'] or '',
                p['Observaciones'] or '',
                p['Seccion'] or ''
            ))

    def nuevo_parametro(self):
        """Abre formulario para crear nuevo parámetro"""
        if not hasattr(self, 'prueba_id_seleccionada'):
            messagebox.showwarning("Aviso", "Seleccione primero una prueba")
            return

        self.form_parametro(None)

    def editar_parametro(self):
        """Edita el parámetro seleccionado"""
        sel = self.tree_params.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un parámetro para editar")
            return

        param_id = self.tree_params.item(sel[0])['values'][1]
        self.form_parametro(param_id)

    def eliminar_parametro(self):
        """Elimina el parámetro de la prueba"""
        sel = self.tree_params.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione un parámetro para eliminar")
            return

        if not messagebox.askyesno("Confirmar", "¿Desea eliminar este parámetro de la prueba?"):
            return

        param_id = self.tree_params.item(sel[0])['values'][1]

        try:
            db.execute(f"DELETE FROM ParametrosPrueba WHERE PruebaID={self.prueba_id_seleccionada} AND ParametroID={param_id}")
            messagebox.showinfo("Éxito", "Parámetro eliminado de la prueba")
            self.cargar_parametros_prueba()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def form_parametro(self, param_id=None):
        """Formulario para crear/editar parámetro"""
        win = tk.Toplevel(self.root)
        win.title("Nuevo Parámetro" if not param_id else "Editar Parámetro")
        win.grab_set()
        win.focus_set()
        win.configure(bg='white')

        # Hacer ventana responsiva
        hacer_ventana_responsiva(win, 500, 650, min_ancho=450, min_alto=550)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Datos del Parámetro", font=('Segoe UI', 14, 'bold'),
                bg='white').pack(anchor='w', pady=(0, 15))

        # Campos
        campos = [
            ("Código:", "codigo"),
            ("Nombre:", "nombre"),
            ("Tipo Resultado:", "tipo"),
            ("Valor Referencia:", "referencia"),
            ("Sección:", "seccion"),
            ("Fórmula (opcional):", "formula"),
        ]

        entries = {}
        for label, key in campos:
            tk.Label(frame, text=label, font=('Segoe UI', 10), bg='white', anchor='w').pack(fill='x', pady=(10, 2))

            if key == "tipo":
                entry = ttk.Combobox(frame, font=('Segoe UI', 10), values=['NUMERICO', 'TEXTO'], state='readonly')
                entry.set('NUMERICO')
            else:
                entry = tk.Entry(frame, font=('Segoe UI', 10))

            entry.pack(fill='x', ipady=5)
            entries[key] = entry

        # Opciones para tipo TEXTO
        tk.Label(frame, text="Opciones (para tipo TEXTO, separar con comas):",
                font=('Segoe UI', 10), bg='white', anchor='w').pack(fill='x', pady=(10, 2))
        entries['opciones'] = tk.Entry(frame, font=('Segoe UI', 10))
        entries['opciones'].pack(fill='x', ipady=5)

        # Cargar datos si es edición
        if param_id:
            param = db.query_one(f"""
                SELECT * FROM Parametros WHERE ParametroID = {param_id}
            """)
            if param:
                entries['codigo'].insert(0, param.get('CodigoParametro') or '')
                entries['nombre'].insert(0, param.get('NombreParametro') or '')
                entries['tipo'].set(param.get('TipoResultado') or 'NUMERICO')
                entries['referencia'].insert(0, param.get('Observaciones') or '')
                entries['seccion'].insert(0, param.get('Seccion') or '')
                entries['formula'].insert(0, param.get('FormulaCalculo') or '')

                # Cargar opciones
                opciones = db.query(f"SELECT Valor FROM OpcionesParametro WHERE ParametroID={param_id} ORDER BY Orden")
                if opciones:
                    entries['opciones'].insert(0, ', '.join([o['Valor'] for o in opciones]))

        def guardar():
            codigo = entries['codigo'].get().strip()
            nombre = entries['nombre'].get().strip()
            tipo = entries['tipo'].get()
            referencia = entries['referencia'].get().strip()
            seccion = entries['seccion'].get().strip()
            formula = entries['formula'].get().strip()
            opciones_str = entries['opciones'].get().strip()

            if not codigo or not nombre:
                messagebox.showwarning("Aviso", "Código y Nombre son obligatorios")
                return

            try:
                if param_id:
                    # Actualizar
                    db.update('Parametros', {
                        'CodigoParametro': codigo,
                        'NombreParametro': nombre,
                        'TipoResultado': tipo,
                        'Observaciones': referencia,
                        'Seccion': seccion,
                        'FormulaCalculo': formula if formula else None
                    }, f"ParametroID={param_id}")
                    new_param_id = param_id
                else:
                    # Crear nuevo
                    db.insert('Parametros', {
                        'CodigoParametro': codigo,
                        'NombreParametro': nombre,
                        'TipoResultado': tipo,
                        'Observaciones': referencia,
                        'Seccion': seccion,
                        'FormulaCalculo': formula if formula else None,
                        'Activo': True
                    })
                    # Obtener ID del nuevo parámetro
                    nuevo = db.query_one(f"SELECT MAX(ParametroID) as ID FROM Parametros")
                    new_param_id = nuevo['ID']

                    # Asignar a la prueba
                    max_sec = db.query_one(f"SELECT MAX(Secuencia) as s FROM ParametrosPrueba WHERE PruebaID={self.prueba_id_seleccionada}")
                    nueva_sec = (max_sec['s'] or 0) + 1

                    db.insert('ParametrosPrueba', {
                        'PruebaID': self.prueba_id_seleccionada,
                        'ParametroID': new_param_id,
                        'Secuencia': nueva_sec,
                        'Obligatorio': True
                    })

                # Guardar opciones si es tipo TEXTO
                if tipo == 'TEXTO' and opciones_str:
                    # Eliminar opciones anteriores
                    db.execute(f"DELETE FROM OpcionesParametro WHERE ParametroID={new_param_id}")

                    # Crear nuevas opciones
                    opciones = [o.strip() for o in opciones_str.split(',') if o.strip()]
                    for i, op in enumerate(opciones, 1):
                        db.insert('OpcionesParametro', {
                            'ParametroID': new_param_id,
                            'Valor': op,
                            'Orden': i,
                            'Frecuencia': 0,
                            'Activo': True
                        })

                messagebox.showinfo("Éxito", "Parámetro guardado correctamente")
                win.destroy()
                self.cargar_parametros_prueba()

            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Separador
        tk.Frame(frame, bg=COLORS['border'], height=2).pack(fill='x', pady=(20, 10))

        # Botones grandes y visibles
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill='x', pady=10)

        btn_guardar = tk.Button(btn_frame, text="💾  GUARDAR PARÁMETRO", font=('Segoe UI', 12, 'bold'),
                 bg='#27ae60', fg='white', relief='flat', padx=25, pady=12,
                 cursor='hand2', activebackground='#219a52', command=guardar)
        btn_guardar.pack(side='left', padx=10)

        btn_cancelar = tk.Button(btn_frame, text="❌  CANCELAR", font=('Segoe UI', 12, 'bold'),
                 bg='#e74c3c', fg='white', relief='flat', padx=25, pady=12,
                 cursor='hand2', activebackground='#c0392b', command=win.destroy)
        btn_cancelar.pack(side='left', padx=10)

        # Efecto hover en botones
        def on_enter_guardar(e):
            btn_guardar.config(bg='#219a52')
        def on_leave_guardar(e):
            btn_guardar.config(bg='#27ae60')
        def on_enter_cancelar(e):
            btn_cancelar.config(bg='#c0392b')
        def on_leave_cancelar(e):
            btn_cancelar.config(bg='#e74c3c')

        btn_guardar.bind('<Enter>', on_enter_guardar)
        btn_guardar.bind('<Leave>', on_leave_guardar)
        btn_cancelar.bind('<Enter>', on_enter_cancelar)
        btn_cancelar.bind('<Leave>', on_leave_cancelar)

    def agregar_parametro_existente(self):
        """Permite agregar un parámetro existente a la prueba"""
        if not hasattr(self, 'prueba_id_seleccionada'):
            messagebox.showwarning("Aviso", "Seleccione primero una prueba")
            return

        win = tk.Toplevel(self.root)
        win.title("Agregar Parámetro Existente")
        win.grab_set()
        win.focus_set()
        hacer_ventana_responsiva(win, 600, 500, min_ancho=450, min_alto=400)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Buscar Parámetro:", font=('Segoe UI', 11, 'bold'),
                bg='white').pack(anchor='w', pady=(0, 10))

        # Búsqueda
        search_frame = tk.Frame(frame, bg='white')
        search_frame.pack(fill='x', pady=5)

        entry_buscar = tk.Entry(search_frame, font=('Segoe UI', 10))
        entry_buscar.pack(side='left', fill='x', expand=True, ipady=5)

        # Lista de parámetros disponibles
        tree_frame = tk.Frame(frame, bg='white')
        tree_frame.pack(fill='both', expand=True, pady=10)

        columns = ('ID', 'Código', 'Nombre', 'Tipo')
        tree_disponibles = ttk.Treeview(tree_frame, columns=columns, show='headings')

        tree_disponibles.heading('ID', text='ID')
        tree_disponibles.heading('Código', text='Código')
        tree_disponibles.heading('Nombre', text='Nombre')
        tree_disponibles.heading('Tipo', text='Tipo')

        tree_disponibles.column('ID', width=50)
        tree_disponibles.column('Código', width=120)
        tree_disponibles.column('Nombre', width=250)
        tree_disponibles.column('Tipo', width=100)

        scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree_disponibles.yview)
        tree_disponibles.configure(yscrollcommand=scroll.set)

        tree_disponibles.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        def cargar_parametros_disponibles(filtro=""):
            for item in tree_disponibles.get_children():
                tree_disponibles.delete(item)

            where = "WHERE Activo = True"
            if filtro:
                where += f" AND (NombreParametro LIKE '%{filtro}%' OR CodigoParametro LIKE '%{filtro}%')"

            # Excluir los que ya están asignados
            where += f" AND ParametroID NOT IN (SELECT ParametroID FROM ParametrosPrueba WHERE PruebaID={self.prueba_id_seleccionada})"

            params = db.query(f"""
                SELECT ParametroID, CodigoParametro, NombreParametro, TipoResultado
                FROM Parametros {where}
                ORDER BY NombreParametro
            """)

            for p in params:
                tree_disponibles.insert('', 'end', values=(
                    p['ParametroID'],
                    p['CodigoParametro'] or '',
                    p['NombreParametro'] or '',
                    p['TipoResultado'] or ''
                ))

        entry_buscar.bind('<KeyRelease>', lambda e: cargar_parametros_disponibles(entry_buscar.get().strip()))

        def agregar_seleccionado():
            sel = tree_disponibles.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleccione un parámetro")
                return

            param_id = tree_disponibles.item(sel[0])['values'][0]

            try:
                max_sec = db.query_one(f"SELECT MAX(Secuencia) as s FROM ParametrosPrueba WHERE PruebaID={self.prueba_id_seleccionada}")
                nueva_sec = (max_sec['s'] or 0) + 1

                db.insert('ParametrosPrueba', {
                    'PruebaID': self.prueba_id_seleccionada,
                    'ParametroID': param_id,
                    'Secuencia': nueva_sec,
                    'Obligatorio': True
                })

                messagebox.showinfo("Éxito", "Parámetro agregado a la prueba")
                win.destroy()
                self.cargar_parametros_prueba()

            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Botones
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill='x', pady=10)

        tk.Button(btn_frame, text="➕ Agregar Seleccionado", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=agregar_seleccionado).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Cerrar", font=('Segoe UI', 10),
                 bg=COLORS['text_light'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=win.destroy).pack(side='left', padx=5)

        cargar_parametros_disponibles()

    def reordenar_parametros(self):
        """Permite reordenar los parámetros de la prueba"""
        if not hasattr(self, 'prueba_id_seleccionada'):
            messagebox.showwarning("Aviso", "Seleccione primero una prueba")
            return

        win = tk.Toplevel(self.root)
        win.title("Reordenar Parámetros")
        win.grab_set()
        win.focus_set()
        hacer_ventana_responsiva(win, 450, 500, min_ancho=350, min_alto=400)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Arrastre para reordenar o use los botones:",
                font=('Segoe UI', 11), bg='white').pack(anchor='w', pady=(0, 10))

        # Lista de parámetros
        list_frame = tk.Frame(frame, bg='white')
        list_frame.pack(fill='both', expand=True)

        listbox = tk.Listbox(list_frame, font=('Segoe UI', 10), height=15)
        scroll = ttk.Scrollbar(list_frame, orient='vertical', command=listbox.yview)
        listbox.configure(yscrollcommand=scroll.set)

        listbox.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        # Cargar parámetros
        parametros = db.query(f"""
            SELECT pp.ParametroPruebaID, pp.Secuencia, par.NombreParametro
            FROM ParametrosPrueba pp
            INNER JOIN Parametros par ON pp.ParametroID = par.ParametroID
            WHERE pp.PruebaID = {self.prueba_id_seleccionada}
            ORDER BY pp.Secuencia
        """)

        param_ids = []
        for p in parametros:
            listbox.insert('end', f"{p['Secuencia']:2}. {p['NombreParametro']}")
            param_ids.append(p['ParametroPruebaID'])

        # Botones de movimiento
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill='x', pady=10)

        def mover_arriba():
            sel = listbox.curselection()
            if not sel or sel[0] == 0:
                return
            idx = sel[0]
            # Intercambiar en listbox
            text = listbox.get(idx)
            listbox.delete(idx)
            listbox.insert(idx - 1, text)
            listbox.selection_set(idx - 1)
            # Intercambiar en lista de IDs
            param_ids[idx], param_ids[idx - 1] = param_ids[idx - 1], param_ids[idx]

        def mover_abajo():
            sel = listbox.curselection()
            if not sel or sel[0] == listbox.size() - 1:
                return
            idx = sel[0]
            text = listbox.get(idx)
            listbox.delete(idx)
            listbox.insert(idx + 1, text)
            listbox.selection_set(idx + 1)
            param_ids[idx], param_ids[idx + 1] = param_ids[idx + 1], param_ids[idx]

        tk.Button(btn_frame, text="⬆ Subir", font=('Segoe UI', 10),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=5,
                 cursor='hand2', command=mover_arriba).pack(side='left', padx=5)

        tk.Button(btn_frame, text="⬇ Bajar", font=('Segoe UI', 10),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=5,
                 cursor='hand2', command=mover_abajo).pack(side='left', padx=5)

        def guardar_orden():
            try:
                for i, pp_id in enumerate(param_ids, 1):
                    db.execute(f"UPDATE ParametrosPrueba SET Secuencia = {i} WHERE ParametroPruebaID = {pp_id}")

                messagebox.showinfo("Éxito", "Orden guardado correctamente")
                win.destroy()
                self.cargar_parametros_prueba()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(btn_frame, text="💾 Guardar Orden", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=15, pady=5,
                 cursor='hand2', command=guardar_orden).pack(side='right', padx=5)

    # ============================================================
    # GESTIÓN DE PERFILES
    # ============================================================

    def gestionar_perfiles(self):
        """Abre la ventana de gestión de perfiles"""
        win = tk.Toplevel(self.root)
        win.title("📦 Gestión de Perfiles")
        win.grab_set()
        win.focus_set()
        win.configure(bg=COLORS['bg'])

        # Hacer ventana responsiva
        hacer_ventana_responsiva(win, 900, 600, min_ancho=700, min_alto=500)

        # Frame principal
        main_frame = tk.Frame(win, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        # Panel izquierdo - Lista de Perfiles
        left_panel = tk.Frame(main_frame, bg='white', width=300)
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="📦 Perfiles", font=('Segoe UI', 12, 'bold'),
                bg='white', fg=COLORS['text']).pack(anchor='w', padx=15, pady=10)

        # Toolbar de perfiles
        toolbar_perfiles = tk.Frame(left_panel, bg='white')
        toolbar_perfiles.pack(fill='x', padx=10, pady=5)

        btn_nuevo_perfil = tk.Button(toolbar_perfiles, text="➕ Nuevo", font=('Segoe UI', 9),
                 bg=COLORS['success'], fg='white', relief='flat', padx=8, pady=3,
                 cursor='hand2')
        btn_nuevo_perfil.pack(side='left', padx=2)

        btn_editar_perfil = tk.Button(toolbar_perfiles, text="✏️ Editar", font=('Segoe UI', 9),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=8, pady=3,
                 cursor='hand2')
        btn_editar_perfil.pack(side='left', padx=2)

        btn_eliminar_perfil = tk.Button(toolbar_perfiles, text="🗑️ Eliminar", font=('Segoe UI', 9),
                 bg=COLORS['danger'], fg='white', relief='flat', padx=8, pady=3,
                 cursor='hand2')
        btn_eliminar_perfil.pack(side='left', padx=2)

        # Lista de perfiles
        tree_frame_perfiles = tk.Frame(left_panel, bg='white')
        tree_frame_perfiles.pack(fill='both', expand=True, padx=10, pady=5)

        tree_perfiles = ttk.Treeview(tree_frame_perfiles, columns=('ID', 'Codigo', 'Nombre'), show='headings', height=15)
        tree_perfiles.heading('ID', text='ID')
        tree_perfiles.heading('Codigo', text='Código')
        tree_perfiles.heading('Nombre', text='Nombre')
        tree_perfiles.column('ID', width=35)
        tree_perfiles.column('Codigo', width=70)
        tree_perfiles.column('Nombre', width=160)

        scroll_perfiles = ttk.Scrollbar(tree_frame_perfiles, orient='vertical', command=tree_perfiles.yview)
        tree_perfiles.configure(yscrollcommand=scroll_perfiles.set)

        tree_perfiles.pack(side='left', fill='both', expand=True)
        scroll_perfiles.pack(side='right', fill='y')

        # Panel derecho - Pruebas del perfil
        right_panel = tk.Frame(main_frame, bg='white')
        right_panel.pack(side='right', fill='both', expand=True)

        lbl_perfil_sel = tk.Label(right_panel, text="Seleccione un perfil",
                font=('Segoe UI', 12, 'bold'), bg='white', fg=COLORS['text'])
        lbl_perfil_sel.pack(anchor='w', padx=15, pady=10)

        # Toolbar de pruebas en perfil
        toolbar_pruebas = tk.Frame(right_panel, bg='white')
        toolbar_pruebas.pack(fill='x', padx=15, pady=5)

        btn_agregar_prueba = tk.Button(toolbar_pruebas, text="➕ Agregar Prueba", font=('Segoe UI', 9),
                 bg=COLORS['success'], fg='white', relief='flat', padx=10, pady=5,
                 cursor='hand2')
        btn_agregar_prueba.pack(side='left', padx=2)

        btn_quitar_prueba = tk.Button(toolbar_pruebas, text="➖ Quitar Prueba", font=('Segoe UI', 9),
                 bg=COLORS['danger'], fg='white', relief='flat', padx=10, pady=5,
                 cursor='hand2')
        btn_quitar_prueba.pack(side='left', padx=2)

        # Lista de pruebas en el perfil
        tree_frame_pruebas = tk.Frame(right_panel, bg='white')
        tree_frame_pruebas.pack(fill='both', expand=True, padx=15, pady=10)

        tree_pruebas_perfil = ttk.Treeview(tree_frame_pruebas,
            columns=('Orden', 'ID', 'Codigo', 'Nombre', 'Area'), show='headings')
        tree_pruebas_perfil.heading('Orden', text='#')
        tree_pruebas_perfil.heading('ID', text='ID')
        tree_pruebas_perfil.heading('Codigo', text='Código')
        tree_pruebas_perfil.heading('Nombre', text='Nombre Prueba')
        tree_pruebas_perfil.heading('Area', text='Área')
        tree_pruebas_perfil.column('Orden', width=35)
        tree_pruebas_perfil.column('ID', width=40)
        tree_pruebas_perfil.column('Codigo', width=80)
        tree_pruebas_perfil.column('Nombre', width=250)
        tree_pruebas_perfil.column('Area', width=120)

        scroll_pruebas_perfil = ttk.Scrollbar(tree_frame_pruebas, orient='vertical', command=tree_pruebas_perfil.yview)
        tree_pruebas_perfil.configure(yscrollcommand=scroll_pruebas_perfil.set)

        tree_pruebas_perfil.pack(side='left', fill='both', expand=True)
        scroll_pruebas_perfil.pack(side='right', fill='y')

        # Variable para almacenar el perfil seleccionado
        perfil_seleccionado = {'id': None}

        def cargar_perfiles():
            for item in tree_perfiles.get_children():
                tree_perfiles.delete(item)

            perfiles = db.query("SELECT PerfilID, CodigoPerfil, NombrePerfil FROM Perfiles WHERE Activo=True ORDER BY NombrePerfil")
            for p in perfiles:
                tree_perfiles.insert('', 'end', values=(
                    p['PerfilID'],
                    p['CodigoPerfil'] or '',
                    p['NombrePerfil'] or ''
                ))

        def cargar_pruebas_perfil(event=None):
            sel = tree_perfiles.selection()
            if not sel:
                return

            valores = tree_perfiles.item(sel[0])['values']
            perfil_seleccionado['id'] = valores[0]
            nombre_perfil = valores[2]

            lbl_perfil_sel.config(text=f"📋 Pruebas del perfil: {nombre_perfil}")

            # Limpiar lista
            for item in tree_pruebas_perfil.get_children():
                tree_pruebas_perfil.delete(item)

            # Cargar pruebas del perfil (sintaxis Access con paréntesis)
            pruebas = db.query(f"""
                SELECT pp.Secuencia, pr.PruebaID, pr.CodigoPrueba, pr.NombrePrueba, a.NombreArea
                FROM (PruebasEnPerfil pp
                INNER JOIN Pruebas pr ON pp.PruebaID = pr.PruebaID)
                LEFT JOIN Areas a ON pr.AreaID = a.AreaID
                WHERE pp.PerfilID = {perfil_seleccionado['id']}
                ORDER BY pp.Secuencia
            """)

            for p in pruebas:
                tree_pruebas_perfil.insert('', 'end', values=(
                    p['Secuencia'] or '',
                    p['PruebaID'],
                    p['CodigoPrueba'] or '',
                    p['NombrePrueba'] or '',
                    p['NombreArea'] or ''
                ))

        def nuevo_perfil():
            self.form_perfil(None, cargar_perfiles)

        def editar_perfil():
            sel = tree_perfiles.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleccione un perfil para editar")
                return
            perfil_id = tree_perfiles.item(sel[0])['values'][0]
            self.form_perfil(perfil_id, cargar_perfiles)

        def eliminar_perfil():
            sel = tree_perfiles.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleccione un perfil para eliminar")
                return

            if not messagebox.askyesno("Confirmar", "¿Desea eliminar este perfil?"):
                return

            perfil_id = tree_perfiles.item(sel[0])['values'][0]
            try:
                db.execute(f"DELETE FROM PruebasEnPerfil WHERE PerfilID={perfil_id}")
                db.execute(f"DELETE FROM Perfiles WHERE PerfilID={perfil_id}")
                messagebox.showinfo("Éxito", "Perfil eliminado")
                cargar_perfiles()
                lbl_perfil_sel.config(text="Seleccione un perfil")
                for item in tree_pruebas_perfil.get_children():
                    tree_pruebas_perfil.delete(item)
            except Exception as e:
                messagebox.showerror("Error", str(e))

        def agregar_prueba_perfil():
            if not perfil_seleccionado['id']:
                messagebox.showwarning("Aviso", "Seleccione primero un perfil")
                return
            self.seleccionar_prueba_para_perfil(perfil_seleccionado['id'], cargar_pruebas_perfil)

        def quitar_prueba_perfil():
            if not perfil_seleccionado['id']:
                messagebox.showwarning("Aviso", "Seleccione primero un perfil")
                return

            sel = tree_pruebas_perfil.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleccione una prueba para quitar")
                return

            if not messagebox.askyesno("Confirmar", "¿Desea quitar esta prueba del perfil?"):
                return

            prueba_id = tree_pruebas_perfil.item(sel[0])['values'][1]
            try:
                db.execute(f"DELETE FROM PruebasEnPerfil WHERE PerfilID={perfil_seleccionado['id']} AND PruebaID={prueba_id}")
                messagebox.showinfo("Éxito", "Prueba quitada del perfil")
                cargar_pruebas_perfil()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Asignar comandos a botones
        btn_nuevo_perfil.config(command=nuevo_perfil)
        btn_editar_perfil.config(command=editar_perfil)
        btn_eliminar_perfil.config(command=eliminar_perfil)
        btn_agregar_prueba.config(command=agregar_prueba_perfil)
        btn_quitar_prueba.config(command=quitar_prueba_perfil)

        # Bind selección
        tree_perfiles.bind('<<TreeviewSelect>>', cargar_pruebas_perfil)

        # Cargar perfiles
        cargar_perfiles()

    def form_perfil(self, perfil_id, callback):
        """Formulario para crear/editar perfil"""
        win = tk.Toplevel(self.root)
        win.title("Nuevo Perfil" if not perfil_id else "Editar Perfil")
        win.configure(bg='white')
        win.grab_set()
        win.focus_set()
        hacer_ventana_responsiva(win, 400, 300, min_ancho=350, min_alto=250)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Datos del Perfil", font=('Segoe UI', 14, 'bold'),
                bg='white').pack(anchor='w', pady=(0, 15))

        # Código
        tk.Label(frame, text="Código:", font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=(10, 2))
        entry_codigo = tk.Entry(frame, font=('Segoe UI', 10))
        entry_codigo.pack(fill='x', ipady=5)

        # Nombre
        tk.Label(frame, text="Nombre:", font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=(10, 2))
        entry_nombre = tk.Entry(frame, font=('Segoe UI', 10))
        entry_nombre.pack(fill='x', ipady=5)

        # Descripción
        tk.Label(frame, text="Descripción:", font=('Segoe UI', 10), bg='white').pack(anchor='w', pady=(10, 2))
        entry_desc = tk.Entry(frame, font=('Segoe UI', 10))
        entry_desc.pack(fill='x', ipady=5)

        # Cargar datos si es edición
        if perfil_id:
            perfil = db.query_one(f"SELECT * FROM Perfiles WHERE PerfilID={perfil_id}")
            if perfil:
                entry_codigo.insert(0, perfil.get('CodigoPerfil') or '')
                entry_nombre.insert(0, perfil.get('NombrePerfil') or '')
                entry_desc.insert(0, perfil.get('Descripcion') or '')

        def guardar():
            codigo = entry_codigo.get().strip()
            nombre = entry_nombre.get().strip()
            desc = entry_desc.get().strip()

            if not codigo or not nombre:
                messagebox.showwarning("Aviso", "Código y Nombre son obligatorios")
                return

            try:
                if perfil_id:
                    db.update('Perfiles', {
                        'CodigoPerfil': codigo,
                        'NombrePerfil': nombre,
                        'Descripcion': desc
                    }, f"PerfilID={perfil_id}")
                else:
                    db.insert('Perfiles', {
                        'CodigoPerfil': codigo,
                        'NombrePerfil': nombre,
                        'Descripcion': desc,
                        'Activo': True
                    })

                messagebox.showinfo("Éxito", "Perfil guardado correctamente")
                win.destroy()
                if callback:
                    callback()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Botones
        tk.Frame(frame, bg=COLORS['border'], height=2).pack(fill='x', pady=(20, 10))

        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill='x', pady=10)

        tk.Button(btn_frame, text="💾 GUARDAR", font=('Segoe UI', 11, 'bold'),
                 bg='#27ae60', fg='white', relief='flat', padx=20, pady=8,
                 cursor='hand2', command=guardar).pack(side='left', padx=5)

        tk.Button(btn_frame, text="❌ CANCELAR", font=('Segoe UI', 11, 'bold'),
                 bg='#e74c3c', fg='white', relief='flat', padx=20, pady=8,
                 cursor='hand2', command=win.destroy).pack(side='left', padx=5)

    def seleccionar_prueba_para_perfil(self, perfil_id, callback):
        """Ventana para seleccionar pruebas y agregar al perfil"""
        win = tk.Toplevel(self.root)
        win.title("Agregar Pruebas al Perfil")
        win.configure(bg='white')
        win.grab_set()
        win.focus_set()
        hacer_ventana_responsiva(win, 600, 500, min_ancho=450, min_alto=400)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        tk.Label(frame, text="Buscar Prueba:", font=('Segoe UI', 11, 'bold'),
                bg='white').pack(anchor='w', pady=(0, 10))

        # Búsqueda
        entry_buscar = tk.Entry(frame, font=('Segoe UI', 10))
        entry_buscar.pack(fill='x', ipady=5, pady=(0, 10))

        # Lista de pruebas
        tree_frame = tk.Frame(frame, bg='white')
        tree_frame.pack(fill='both', expand=True)

        columns = ('ID', 'Codigo', 'Nombre', 'Area')
        tree_disponibles = ttk.Treeview(tree_frame, columns=columns, show='headings')

        tree_disponibles.heading('ID', text='ID')
        tree_disponibles.heading('Codigo', text='Código')
        tree_disponibles.heading('Nombre', text='Nombre')
        tree_disponibles.heading('Area', text='Área')

        tree_disponibles.column('ID', width=40)
        tree_disponibles.column('Codigo', width=80)
        tree_disponibles.column('Nombre', width=280)
        tree_disponibles.column('Area', width=120)

        scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=tree_disponibles.yview)
        tree_disponibles.configure(yscrollcommand=scroll.set)

        tree_disponibles.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')

        def cargar_pruebas(filtro=""):
            for item in tree_disponibles.get_children():
                tree_disponibles.delete(item)

            where = "WHERE pr.Activo = True"
            if filtro:
                where += f" AND (pr.NombrePrueba LIKE '%{filtro}%' OR pr.CodigoPrueba LIKE '%{filtro}%')"

            # Excluir las que ya están en el perfil
            where += f" AND pr.PruebaID NOT IN (SELECT PruebaID FROM PruebasEnPerfil WHERE PerfilID={perfil_id})"

            pruebas = db.query(f"""
                SELECT pr.PruebaID, pr.CodigoPrueba, pr.NombrePrueba, a.NombreArea
                FROM Pruebas pr
                LEFT JOIN Areas a ON pr.AreaID = a.AreaID
                {where}
                ORDER BY pr.NombrePrueba
            """)

            for p in pruebas:
                tree_disponibles.insert('', 'end', values=(
                    p['PruebaID'],
                    p['CodigoPrueba'] or '',
                    p['NombrePrueba'] or '',
                    p['NombreArea'] or ''
                ))

        entry_buscar.bind('<KeyRelease>', lambda e: cargar_pruebas(entry_buscar.get().strip()))

        def agregar_seleccionada():
            sel = tree_disponibles.selection()
            if not sel:
                messagebox.showwarning("Aviso", "Seleccione una prueba")
                return

            prueba_id = tree_disponibles.item(sel[0])['values'][0]

            try:
                # Obtener siguiente secuencia
                max_sec = db.query_one(f"SELECT MAX(Secuencia) as s FROM PruebasEnPerfil WHERE PerfilID={perfil_id}")
                nueva_sec = (max_sec['s'] or 0) + 1 if max_sec else 1

                db.insert('PruebasEnPerfil', {
                    'PerfilID': perfil_id,
                    'PruebaID': prueba_id,
                    'Secuencia': nueva_sec
                })

                messagebox.showinfo("Éxito", "Prueba agregada al perfil")
                cargar_pruebas(entry_buscar.get().strip())
                if callback:
                    callback()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        # Botones
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill='x', pady=10)

        tk.Button(btn_frame, text="➕ Agregar Seleccionada", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=agregar_seleccionada).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Cerrar", font=('Segoe UI', 10),
                 bg=COLORS['text_light'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=win.destroy).pack(side='left', padx=5)

        cargar_pruebas()

    # ============================================================
    # MÓDULO ADMINISTRATIVO
    # ============================================================

    def show_caja(self):
        """Vista de Caja Chica"""
        if not self.ventana_admin:
            messagebox.showerror("Error", "Módulo administrativo no disponible.\n"
                                "Ejecute: scripts/crear_tablas_administrativo.py")
            return
        self.ventana_admin.show_caja(self)

    def show_dashboard_financiero(self):
        """Dashboard Financiero"""
        if not self.ventana_admin:
            messagebox.showerror("Error", "Módulo administrativo no disponible.\n"
                                "Ejecute: scripts/crear_tablas_administrativo.py")
            return
        self.ventana_admin.show_dashboard_financiero(self)

    def show_cuentas_cobrar(self):
        """Cuentas por Cobrar"""
        if not self.ventana_admin:
            messagebox.showerror("Error", "Módulo administrativo no disponible.\n"
                                "Ejecute: scripts/crear_tablas_administrativo.py")
            return
        self.ventana_admin.show_cuentas_cobrar(self)

    def show_cuentas_pagar(self):
        """Cuentas por Pagar"""
        if not self.ventana_admin:
            messagebox.showerror("Error", "Módulo administrativo no disponible.\n"
                                "Ejecute: scripts/crear_tablas_administrativo.py")
            return
        self.ventana_admin.show_cuentas_pagar(self)

    def show_gastos(self):
        """Control de Gastos"""
        if not self.ventana_admin:
            messagebox.showerror("Error", "Módulo administrativo no disponible.\n"
                                "Ejecute: scripts/crear_tablas_administrativo.py")
            return
        self.ventana_admin.show_gastos(self)

    # ============================================================
    # MÓDULO VETERINARIO
    # ============================================================

    def show_pacientes_vet(self):
        """Lista de pacientes veterinarios"""
        if not self.gestor_vet:
            messagebox.showerror("Error", "Módulo veterinario no disponible")
            return

        self.clear_content()
        self.set_title("🐕 Pacientes Veterinarios")

        scrollable = self.setup_scrollable_content()

        # Toolbar
        toolbar = tk.Frame(scrollable, bg=COLORS['bg'])
        toolbar.pack(fill='x', pady=(0, 15))

        tk.Button(toolbar, text="➕ Nuevo Paciente", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['primary'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.form_paciente_vet).pack(side='left', padx=(0, 15))

        tk.Label(toolbar, text="🔍", font=('Segoe UI', 12), bg=COLORS['bg']).pack(side='left')
        self.search_pac_vet = tk.Entry(toolbar, font=('Segoe UI', 11), width=30, relief='flat',
                                       bg='white', highlightthickness=1, highlightbackground=COLORS['border'])
        self.search_pac_vet.pack(side='left', padx=5, ipady=6)
        self.search_pac_vet.bind('<Return>', lambda e: self.buscar_pacientes_vet())

        tk.Button(toolbar, text="Buscar", font=('Segoe UI', 10), bg=COLORS['success'],
                 fg='white', relief='flat', padx=15, cursor='hand2',
                 command=self.buscar_pacientes_vet).pack(side='left', padx=5)

        tk.Button(toolbar, text="🔄 Refrescar", font=('Segoe UI', 10), bg='#95a5a6',
                 fg='white', relief='flat', padx=10, cursor='hand2',
                 command=lambda: self.cargar_pacientes_vet()).pack(side='left', padx=5)

        # Lista
        list_frame = tk.Frame(scrollable, bg='white')
        list_frame.pack(fill='both', expand=True)

        cols = ('ID', 'Código', 'Nombre', 'Especie', 'Raza', 'Propietario', 'Teléfono', 'Fecha Reg.')
        self.tree_pac_vet = ttk.Treeview(list_frame, columns=cols, show='headings')

        widths = [50, 90, 120, 80, 100, 150, 100, 90]
        for c, w in zip(cols, widths):
            self.tree_pac_vet.heading(c, text=c)
            self.tree_pac_vet.column(c, width=w)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_pac_vet.yview)
        self.tree_pac_vet.configure(yscrollcommand=vsb.set)

        self.tree_pac_vet.pack(side='left', fill='both', expand=True, padx=(10,0), pady=10)
        vsb.pack(side='right', fill='y', pady=10, padx=(0,10))

        self.tree_pac_vet.bind('<Double-1>', self.editar_paciente_vet)

        self.cargar_pacientes_vet()

    def cargar_pacientes_vet(self, filtro=""):
        for item in self.tree_pac_vet.get_children():
            self.tree_pac_vet.delete(item)
        try:
            data = self.gestor_vet.buscar_pacientes(filtro)
            for r in data:
                self.tree_pac_vet.insert('', 'end', values=(
                    r['PacienteVetID'],
                    r['CodigoPaciente'] or '',
                    r['NombreMascota'] or '',
                    r['Especie'] or '',
                    r['Raza'] or '',
                    r['NombrePropietario'] or '',
                    r['TelefonoPropietario'] or '',
                    r['FechaRegistro'].strftime('%d/%m/%Y') if r.get('FechaRegistro') else ''
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buscar_pacientes_vet(self):
        self.cargar_pacientes_vet(self.search_pac_vet.get().strip())

    def editar_paciente_vet(self, event=None):
        sel = self.tree_pac_vet.selection()
        if sel:
            vals = self.tree_pac_vet.item(sel[0], 'values')
            if vals:
                self.form_paciente_vet(int(vals[0]))

    def form_paciente_vet(self, paciente_id=None):
        """Formulario para crear/editar paciente veterinario"""
        win = tk.Toplevel(self.root)
        win.title("Editar Paciente Vet" if paciente_id else "Nuevo Paciente Veterinario")
        win.grab_set()
        win.focus_set()
        win.configure(bg='white')

        hacer_ventana_responsiva(win, 600, 650, min_ancho=500, min_alto=550)

        # Header
        header = tk.Frame(win, bg='#0d9488', height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="🐕 " + ("Editar" if paciente_id else "Nuevo") + " Paciente Veterinario",
                font=('Segoe UI', 14, 'bold'), bg='#0d9488', fg='white').pack(pady=12)

        # Frame con scroll
        container = tk.Frame(win, bg='white')
        container.pack(fill='both', expand=True)

        canvas = tk.Canvas(container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=canvas.yview)
        frame = tk.Frame(canvas, bg='white')

        frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=frame, anchor='nw', width=570)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True, padx=15)
        scrollbar.pack(side='right', fill='y')

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
        canvas.bind_all('<MouseWheel>', on_mousewheel)

        entries = {}

        # === SECCION MASCOTA ===
        sec_mascota = tk.LabelFrame(frame, text=" Datos de la Mascota ", font=('Segoe UI', 10, 'bold'),
                                     bg='white', fg='#0d9488')
        sec_mascota.pack(fill='x', pady=(10, 5), padx=10)

        # Nombre*
        row = tk.Frame(sec_mascota, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Nombre*:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['nombre'] = tk.Entry(row, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                     highlightthickness=1, highlightbackground=COLORS['border'])
        entries['nombre'].pack(side='left', fill='x', expand=True, ipady=5)

        # Especie* y Raza
        row = tk.Frame(sec_mascota, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Especie*:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['especie'] = ttk.Combobox(row, font=('Segoe UI', 10), width=12, values=ESPECIES, state='readonly')
        entries['especie'].pack(side='left', ipady=3, padx=(0, 15))
        tk.Label(row, text="Raza:", font=('Segoe UI', 10), bg='white', width=6, anchor='w').pack(side='left')
        entries['raza'] = ttk.Combobox(row, font=('Segoe UI', 10), width=18)
        entries['raza'].pack(side='left', ipady=3)

        # Actualizar razas al cambiar especie
        def actualizar_razas(event=None):
            especie = entries['especie'].get()
            if especie and VETERINARIO_DISPONIBLE:
                entries['raza']['values'] = RAZAS.get(especie, [])
                entries['raza'].set('')
        entries['especie'].bind('<<ComboboxSelected>>', actualizar_razas)

        # Sexo, Peso y Color
        row = tk.Frame(sec_mascota, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Sexo:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['sexo'] = ttk.Combobox(row, font=('Segoe UI', 10), width=10, values=['M - Macho', 'H - Hembra'], state='readonly')
        entries['sexo'].pack(side='left', ipady=3, padx=(0, 15))
        tk.Label(row, text="Peso (kg):", font=('Segoe UI', 10), bg='white', width=8, anchor='w').pack(side='left')
        entries['peso'] = tk.Entry(row, font=('Segoe UI', 11), width=8, relief='flat', bg='#f8f9fa',
                                   highlightthickness=1, highlightbackground=COLORS['border'])
        entries['peso'].pack(side='left', ipady=5)

        row = tk.Frame(sec_mascota, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Color:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['color'] = tk.Entry(row, font=('Segoe UI', 11), width=20, relief='flat', bg='#f8f9fa',
                                    highlightthickness=1, highlightbackground=COLORS['border'])
        entries['color'].pack(side='left', ipady=5, padx=(0, 15))
        tk.Label(row, text="F.Nac:", font=('Segoe UI', 10), bg='white', width=6, anchor='w').pack(side='left')
        entries['fecha_nac'] = tk.Entry(row, font=('Segoe UI', 11), width=12, relief='flat', bg='#f8f9fa',
                                        highlightthickness=1, highlightbackground=COLORS['border'])
        entries['fecha_nac'].pack(side='left', ipady=5)
        tk.Label(row, text="(DD/MM/AAAA)", font=('Segoe UI', 8), bg='white', fg='gray').pack(side='left', padx=3)

        # === SECCION PROPIETARIO ===
        sec_prop = tk.LabelFrame(frame, text=" Datos del Propietario ", font=('Segoe UI', 10, 'bold'),
                                  bg='white', fg='#0d9488')
        sec_prop.pack(fill='x', pady=(10, 5), padx=10)

        row = tk.Frame(sec_prop, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Nombre*:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['propietario'] = tk.Entry(row, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                          highlightthickness=1, highlightbackground=COLORS['border'])
        entries['propietario'].pack(side='left', fill='x', expand=True, ipady=5)

        row = tk.Frame(sec_prop, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Teléfono:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['telefono'] = tk.Entry(row, font=('Segoe UI', 11), width=18, relief='flat', bg='#f8f9fa',
                                       highlightthickness=1, highlightbackground=COLORS['border'])
        entries['telefono'].pack(side='left', ipady=5, padx=(0, 15))
        tk.Label(row, text="Email:", font=('Segoe UI', 10), bg='white', width=6, anchor='w').pack(side='left')
        entries['email'] = tk.Entry(row, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                    highlightthickness=1, highlightbackground=COLORS['border'])
        entries['email'].pack(side='left', fill='x', expand=True, ipady=5)

        row = tk.Frame(sec_prop, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Dirección:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['direccion'] = tk.Entry(row, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                        highlightthickness=1, highlightbackground=COLORS['border'])
        entries['direccion'].pack(side='left', fill='x', expand=True, ipady=5)

        # Veterinario remitente
        row = tk.Frame(sec_prop, bg='white')
        row.pack(fill='x', pady=4, padx=10)
        tk.Label(row, text="Vet. Remitente:", font=('Segoe UI', 10), bg='white', width=14, anchor='w').pack(side='left')
        entries['vet_remitente'] = tk.Entry(row, font=('Segoe UI', 11), relief='flat', bg='#f8f9fa',
                                            highlightthickness=1, highlightbackground=COLORS['border'])
        entries['vet_remitente'].pack(side='left', fill='x', expand=True, ipady=5)

        # Cargar datos si es edición
        if paciente_id:
            pac = self.gestor_vet.obtener_paciente(paciente_id)
            if pac:
                entries['nombre'].insert(0, pac.get('NombreMascota') or '')
                if pac.get('Especie'):
                    entries['especie'].set(pac['Especie'])
                    actualizar_razas()
                if pac.get('Raza'):
                    entries['raza'].set(pac['Raza'])
                if pac.get('Sexo'):
                    entries['sexo'].set('M - Macho' if pac['Sexo'] == 'M' else 'H - Hembra')
                if pac.get('Peso'):
                    entries['peso'].insert(0, str(pac['Peso']))
                if pac.get('Color'):
                    entries['color'].insert(0, pac['Color'])
                if pac.get('FechaNacimiento'):
                    try:
                        entries['fecha_nac'].insert(0, pac['FechaNacimiento'].strftime('%d/%m/%Y'))
                    except:
                        pass
                entries['propietario'].insert(0, pac.get('NombrePropietario') or '')
                entries['telefono'].insert(0, pac.get('TelefonoPropietario') or '')
                entries['email'].insert(0, pac.get('EmailPropietario') or '')
                entries['direccion'].insert(0, pac.get('DireccionPropietario') or '')
                entries['vet_remitente'].insert(0, pac.get('VeterinarioRemitente') or '')

        # Botones
        btn_frame = tk.Frame(frame, bg='white')
        btn_frame.pack(fill='x', pady=15, padx=10)

        def guardar():
            nombre = entries['nombre'].get().strip()
            especie = entries['especie'].get().strip()
            propietario = entries['propietario'].get().strip()

            if not nombre:
                messagebox.showwarning("Aviso", "Ingrese el nombre de la mascota")
                return
            if not especie:
                messagebox.showwarning("Aviso", "Seleccione la especie")
                return
            if not propietario:
                messagebox.showwarning("Aviso", "Ingrese el nombre del propietario")
                return

            datos = {
                'NombreMascota': nombre,
                'Especie': especie,
                'Raza': entries['raza'].get().strip() or None,
                'Sexo': entries['sexo'].get()[0] if entries['sexo'].get() else None,
                'Color': entries['color'].get().strip() or None,
                'NombrePropietario': propietario,
                'TelefonoPropietario': entries['telefono'].get().strip() or None,
                'EmailPropietario': entries['email'].get().strip() or None,
                'DireccionPropietario': entries['direccion'].get().strip() or None,
                'VeterinarioRemitente': entries['vet_remitente'].get().strip() or None,
            }

            # Peso
            peso_str = entries['peso'].get().strip()
            if peso_str:
                try:
                    datos['Peso'] = float(peso_str)
                except ValueError:
                    messagebox.showwarning("Aviso", "Peso debe ser un número")
                    return

            # Fecha nacimiento
            fecha_str = entries['fecha_nac'].get().strip()
            if fecha_str:
                try:
                    datos['FechaNacimiento'] = datetime.strptime(fecha_str, '%d/%m/%Y')
                except ValueError:
                    messagebox.showwarning("Aviso", "Fecha de nacimiento inválida (DD/MM/AAAA)")
                    return

            try:
                self.gestor_vet.guardar_paciente(datos, paciente_id)
                messagebox.showinfo("Éxito", "Paciente guardado correctamente")
                canvas.unbind_all('<MouseWheel>')
                win.destroy()
                if hasattr(self, 'tree_pac_vet'):
                    self.cargar_pacientes_vet()
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(btn_frame, text="💾 Guardar", font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=25, pady=8,
                 cursor='hand2', command=guardar).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Cancelar", font=('Segoe UI', 10),
                 bg=COLORS['text_light'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=lambda: [canvas.unbind_all('<MouseWheel>'), win.destroy()]).pack(side='left', padx=5)

    # ============================================================
    # VET - SOLICITUDES
    # ============================================================

    def show_solicitudes_vet(self):
        """Lista de solicitudes veterinarias"""
        if not self.gestor_vet:
            messagebox.showerror("Error", "Módulo veterinario no disponible")
            return

        self.clear_content()
        self.set_title("📋 Solicitudes Veterinarias")

        scrollable = self.setup_scrollable_content()

        toolbar = tk.Frame(scrollable, bg=COLORS['bg'])
        toolbar.pack(fill='x', pady=(0, 15))

        tk.Button(toolbar, text="➕ Nueva Solicitud", font=('Segoe UI', 10, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=self.form_solicitud_vet).pack(side='left', padx=(0, 10))

        tk.Label(toolbar, text="🔍", font=('Segoe UI', 12), bg=COLORS['bg']).pack(side='left')
        self.search_sol_vet = tk.Entry(toolbar, font=('Segoe UI', 11), width=30, relief='flat',
                                       bg='white', highlightthickness=1, highlightbackground=COLORS['border'])
        self.search_sol_vet.pack(side='left', padx=5, ipady=6)
        self.search_sol_vet.bind('<Return>', lambda e: self.buscar_solicitudes_vet())

        tk.Button(toolbar, text="Buscar", font=('Segoe UI', 10), bg=COLORS['success'],
                 fg='white', relief='flat', padx=15, cursor='hand2',
                 command=self.buscar_solicitudes_vet).pack(side='left', padx=5)

        list_frame = tk.Frame(scrollable, bg='white')
        list_frame.pack(fill='both', expand=True)

        cols = ('ID', 'Número', 'Fecha', 'Mascota', 'Especie', 'Propietario', 'Estado', 'Total')
        self.tree_sol_vet = ttk.Treeview(list_frame, columns=cols, show='headings')

        widths = [50, 110, 90, 120, 80, 150, 90, 80]
        for c, w in zip(cols, widths):
            self.tree_sol_vet.heading(c, text=c)
            self.tree_sol_vet.column(c, width=w)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_sol_vet.yview)
        self.tree_sol_vet.configure(yscrollcommand=vsb.set)

        self.tree_sol_vet.pack(side='left', fill='both', expand=True, padx=(10,0), pady=10)
        vsb.pack(side='right', fill='y', pady=10, padx=(0,10))

        self.tree_sol_vet.bind('<Double-1>', self.ver_solicitud_vet)

        self.cargar_solicitudes_vet()

    def cargar_solicitudes_vet(self, filtro=""):
        for item in self.tree_sol_vet.get_children():
            self.tree_sol_vet.delete(item)
        try:
            data = self.gestor_vet.buscar_solicitudes(filtro)
            for r in data:
                self.tree_sol_vet.insert('', 'end', values=(
                    r['SolicitudVetID'],
                    r['NumeroSolicitud'] or '',
                    r['FechaSolicitud'].strftime('%d/%m/%Y') if r.get('FechaSolicitud') else '',
                    r['NombreMascota'] or 'N/A',
                    r['Especie'] or '',
                    r['NombrePropietario'] or 'N/A',
                    r['EstadoSolicitud'] or 'Pendiente',
                    f"${r['MontoTotal']:,.2f}" if r.get('MontoTotal') else '$0.00'
                ))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def buscar_solicitudes_vet(self):
        self.cargar_solicitudes_vet(self.search_sol_vet.get().strip())

    def ver_solicitud_vet(self, event=None):
        sel = self.tree_sol_vet.selection()
        if not sel:
            return
        vals = self.tree_sol_vet.item(sel[0], 'values')
        if vals:
            sol_id = int(vals[0])
            self._mostrar_detalle_solicitud_vet(sol_id)

    def _mostrar_detalle_solicitud_vet(self, sol_id):
        """Muestra detalles de una solicitud veterinaria"""
        sol = self.gestor_vet.obtener_solicitud(sol_id)
        if not sol:
            messagebox.showwarning("Aviso", "No se encontró la solicitud")
            return

        win = tk.Toplevel(self.root)
        win.title(f"Solicitud {sol['NumeroSolicitud']}")
        win.grab_set()
        hacer_ventana_responsiva(win, 600, 500, min_ancho=500, min_alto=400)
        win.configure(bg='white')

        # Header
        header = tk.Frame(win, bg='#0d9488', height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text=f"📋 Solicitud {sol['NumeroSolicitud']}",
                font=('Segoe UI', 14, 'bold'), bg='#0d9488', fg='white').pack(pady=12)

        info = tk.Frame(win, bg='white')
        info.pack(fill='x', padx=20, pady=10)

        labels = [
            ("Mascota:", sol.get('NombreMascota') or 'N/A'),
            ("Especie:", sol.get('Especie') or 'N/A'),
            ("Raza:", sol.get('Raza') or 'N/A'),
            ("Propietario:", sol.get('NombrePropietario') or 'N/A'),
            ("Fecha:", sol['FechaSolicitud'].strftime('%d/%m/%Y %H:%M') if sol.get('FechaSolicitud') else 'N/A'),
            ("Estado:", sol.get('EstadoSolicitud') or 'Pendiente'),
        ]

        for label, valor in labels:
            row = tk.Frame(info, bg='white')
            row.pack(fill='x', pady=2)
            tk.Label(row, text=label, font=('Segoe UI', 10, 'bold'), bg='white', width=14, anchor='w').pack(side='left')
            tk.Label(row, text=valor, font=('Segoe UI', 10), bg='white', anchor='w').pack(side='left')

        # Pruebas
        tk.Label(win, text="Pruebas:", font=('Segoe UI', 11, 'bold'), bg='white').pack(anchor='w', padx=20, pady=(10, 5))

        detalles = self.gestor_vet.obtener_detalles_solicitud(sol_id)
        for d in detalles:
            estado_color = '#4caf50' if d.get('Estado') == 'Validado' else '#ff9800' if d.get('Estado') == 'Capturado' else '#9e9e9e'
            row = tk.Frame(win, bg='white')
            row.pack(fill='x', padx=20, pady=2)
            tk.Label(row, text=f"  - {d['NombrePrueba']}", font=('Segoe UI', 10), bg='white').pack(side='left')
            tk.Label(row, text=d.get('Estado') or 'Pendiente', font=('Segoe UI', 9, 'bold'),
                    bg=estado_color, fg='white', padx=8).pack(side='right')

        tk.Button(win, text="Cerrar", font=('Segoe UI', 10), bg=COLORS['text_light'], fg='white',
                 relief='flat', padx=20, pady=8, cursor='hand2', command=win.destroy).pack(pady=15)

    def form_solicitud_vet(self):
        """Formulario para crear solicitud veterinaria"""
        if not self.gestor_vet:
            messagebox.showerror("Error", "Módulo veterinario no disponible")
            return

        win = tk.Toplevel(self.root)
        win.title("Nueva Solicitud Veterinaria")
        win.configure(bg=COLORS['bg'])
        win.grab_set()
        win.focus_set()

        hacer_ventana_responsiva(win, 800, 600, min_ancho=700, min_alto=500)

        # Header
        header = tk.Frame(win, bg='#0d9488', height=50)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="📋 NUEVA SOLICITUD VETERINARIA",
                font=('Segoe UI', 14, 'bold'), bg='#0d9488', fg='white').pack(pady=12)

        main = tk.Frame(win, bg=COLORS['bg'])
        main.pack(fill='both', expand=True, padx=15, pady=10)

        # Sección paciente
        sec_pac = tk.LabelFrame(main, text=" Seleccionar Paciente ", font=('Segoe UI', 10, 'bold'),
                                 bg='white', fg='#0d9488')
        sec_pac.pack(fill='x', pady=(0, 10))

        search_frame = tk.Frame(sec_pac, bg='white')
        search_frame.pack(fill='x', padx=10, pady=8)

        tk.Label(search_frame, text="Buscar:", font=('Segoe UI', 10), bg='white').pack(side='left')
        entry_buscar_pac = tk.Entry(search_frame, font=('Segoe UI', 10), width=25, relief='flat',
                                    bg='#f8f9fa', highlightthickness=1, highlightbackground=COLORS['border'])
        entry_buscar_pac.pack(side='left', padx=5, ipady=4)

        # Lista de pacientes
        pac_list_frame = tk.Frame(sec_pac, bg='white')
        pac_list_frame.pack(fill='x', padx=10, pady=(0, 8))

        pac_cols = ('ID', 'Nombre', 'Especie', 'Propietario')
        tree_pac = ttk.Treeview(pac_list_frame, columns=pac_cols, show='headings', height=4)
        for c in pac_cols:
            tree_pac.heading(c, text=c)
        tree_pac.column('ID', width=50)
        tree_pac.column('Nombre', width=120)
        tree_pac.column('Especie', width=80)
        tree_pac.column('Propietario', width=150)
        tree_pac.pack(fill='x')

        paciente_seleccionado = {'id': None, 'especie': None}

        def cargar_pacs(filtro=""):
            for item in tree_pac.get_children():
                tree_pac.delete(item)
            data = self.gestor_vet.buscar_pacientes(filtro)
            for r in data:
                tree_pac.insert('', 'end', values=(
                    r['PacienteVetID'], r['NombreMascota'] or '', r['Especie'] or '', r['NombrePropietario'] or ''
                ))

        def on_search(event=None):
            cargar_pacs(entry_buscar_pac.get().strip())

        entry_buscar_pac.bind('<KeyRelease>', on_search)

        lbl_pac_sel = tk.Label(sec_pac, text="Ningún paciente seleccionado", font=('Segoe UI', 10, 'bold'),
                               bg='white', fg=COLORS['danger'])
        lbl_pac_sel.pack(padx=10, pady=(0, 8))

        def on_pac_select(event=None):
            sel = tree_pac.selection()
            if sel:
                vals = tree_pac.item(sel[0], 'values')
                paciente_seleccionado['id'] = int(vals[0])
                paciente_seleccionado['especie'] = vals[2]
                lbl_pac_sel.config(text=f"Seleccionado: {vals[1]} ({vals[2]}) - {vals[3]}", fg=COLORS['success'])

        tree_pac.bind('<<TreeviewSelect>>', on_pac_select)

        cargar_pacs()

        # Sección pruebas
        sec_pruebas = tk.LabelFrame(main, text=" Seleccionar Pruebas ", font=('Segoe UI', 10, 'bold'),
                                     bg='white', fg='#0d9488')
        sec_pruebas.pack(fill='x', pady=(0, 10))

        pruebas_disponibles = self.gestor_vet.obtener_pruebas_disponibles()
        pruebas_vars = {}

        for prueba in pruebas_disponibles:
            var = tk.BooleanVar(value=False)
            pruebas_vars[prueba['PruebaVetID']] = var
            row = tk.Frame(sec_pruebas, bg='white')
            row.pack(fill='x', padx=15, pady=3)
            tk.Checkbutton(row, text=f"{prueba['CodigoPrueba']} - {prueba['NombrePrueba']} ({prueba['Categoria']})",
                          font=('Segoe UI', 10), bg='white', variable=var, activebackground='white').pack(side='left')

        # Observaciones
        row_obs = tk.Frame(main, bg=COLORS['bg'])
        row_obs.pack(fill='x', pady=5)
        tk.Label(row_obs, text="Observaciones:", font=('Segoe UI', 10), bg=COLORS['bg']).pack(anchor='w')
        entry_obs = tk.Entry(row_obs, font=('Segoe UI', 10), relief='flat', bg='white',
                             highlightthickness=1, highlightbackground=COLORS['border'])
        entry_obs.pack(fill='x', ipady=5)

        # Botones
        btn_frame = tk.Frame(main, bg=COLORS['bg'])
        btn_frame.pack(fill='x', pady=10)

        def crear():
            if not paciente_seleccionado['id']:
                messagebox.showwarning("Aviso", "Seleccione un paciente")
                return

            pruebas_sel = [pid for pid, var in pruebas_vars.items() if var.get()]
            if not pruebas_sel:
                messagebox.showwarning("Aviso", "Seleccione al menos una prueba")
                return

            try:
                sol_id = self.gestor_vet.crear_solicitud(paciente_seleccionado['id'], pruebas_sel)
                if sol_id:
                    # Guardar observaciones si hay
                    obs = entry_obs.get().strip()
                    if obs:
                        self.gestor_vet.db.update('SolicitudesVet', {'Observaciones': obs}, f"SolicitudVetID = {sol_id}")

                    messagebox.showinfo("Éxito", f"Solicitud creada exitosamente")
                    win.destroy()
                    if hasattr(self, 'tree_sol_vet'):
                        self.cargar_solicitudes_vet()
                else:
                    messagebox.showerror("Error", "No se pudo crear la solicitud")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        tk.Button(btn_frame, text="💾 Crear Solicitud", font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['success'], fg='white', relief='flat', padx=25, pady=8,
                 cursor='hand2', command=crear).pack(side='left', padx=5)

        tk.Button(btn_frame, text="Cancelar", font=('Segoe UI', 10),
                 bg=COLORS['text_light'], fg='white', relief='flat', padx=15, pady=8,
                 cursor='hand2', command=win.destroy).pack(side='left', padx=5)

    # ============================================================
    # VET - RESULTADOS
    # ============================================================

    def show_resultados_vet(self):
        """Captura de resultados veterinarios con valores de referencia por especie"""
        if not self.gestor_vet:
            messagebox.showerror("Error", "Módulo veterinario no disponible")
            return

        self.clear_content()
        self.set_title("📊 Resultados Veterinarios")

        main_frame = tk.Frame(self.content, bg=COLORS['bg'])
        main_frame.pack(fill='both', expand=True)

        # COLUMNA IZQUIERDA - Lista de solicitudes
        left_frame = tk.Frame(main_frame, bg='white', width=350)
        left_frame.pack(side='left', fill='y', padx=(0, 10), pady=0)
        left_frame.pack_propagate(False)

        # Búsqueda
        search_frame = tk.Frame(left_frame, bg='white')
        search_frame.pack(fill='x', padx=15, pady=15)

        tk.Label(search_frame, text="🔍 Buscar Solicitud:", font=('Segoe UI', 11, 'bold'),
                bg='white').pack(anchor='w', pady=(0, 8))

        self.entry_buscar_res_vet = tk.Entry(search_frame, font=('Segoe UI', 11), relief='flat',
                                             bg='#f8f9fa', highlightthickness=1, highlightbackground=COLORS['border'])
        self.entry_buscar_res_vet.pack(fill='x', ipady=6)
        self.entry_buscar_res_vet.bind('<KeyRelease>', lambda e: self.buscar_solicitudes_resultado_vet())

        tk.Label(left_frame, text="📋 Solicitudes Pendientes:", font=('Segoe UI', 10, 'bold'),
                bg='white').pack(anchor='w', padx=15, pady=(10, 5))

        list_frame = tk.Frame(left_frame, bg='white')
        list_frame.pack(fill='both', expand=True, padx=15, pady=(0, 15))

        cols = ('N° Solicitud', 'Mascota', 'Especie')
        self.tree_sol_res_vet = ttk.Treeview(list_frame, columns=cols, show='headings', height=15)
        self.tree_sol_res_vet.heading('N° Solicitud', text='N° Solicitud')
        self.tree_sol_res_vet.heading('Mascota', text='Mascota')
        self.tree_sol_res_vet.heading('Especie', text='Especie')
        self.tree_sol_res_vet.column('N° Solicitud', width=100)
        self.tree_sol_res_vet.column('Mascota', width=100)
        self.tree_sol_res_vet.column('Especie', width=80)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree_sol_res_vet.yview)
        self.tree_sol_res_vet.configure(yscrollcommand=vsb.set)
        self.tree_sol_res_vet.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        self.tree_sol_res_vet.bind('<<TreeviewSelect>>', self.cargar_pruebas_resultado_vet)

        self.cargar_solicitudes_pendientes_vet()

        # COLUMNA DERECHA - Captura de resultados
        right_frame = tk.Frame(main_frame, bg='white')
        right_frame.pack(side='left', fill='both', expand=True)

        self.info_res_frame_vet = tk.Frame(right_frame, bg='#0d9488')
        self.info_res_frame_vet.pack(fill='x')

        self.lbl_info_sol_vet = tk.Label(self.info_res_frame_vet,
                                         text="Seleccione una solicitud para capturar resultados",
                                         font=('Segoe UI', 12), bg='#0d9488', fg='white')
        self.lbl_info_sol_vet.pack(pady=15)

        self.pruebas_res_frame_vet = tk.Frame(right_frame, bg='white')
        self.pruebas_res_frame_vet.pack(fill='both', expand=True, padx=15, pady=15)

        tk.Label(self.pruebas_res_frame_vet, text="👆 Seleccione una solicitud de la lista\npara ver y capturar los resultados",
                font=('Segoe UI', 12), bg='white', fg=COLORS['text_light'], justify='center').pack(pady=100)

    def cargar_solicitudes_pendientes_vet(self):
        for item in self.tree_sol_res_vet.get_children():
            self.tree_sol_res_vet.delete(item)
        try:
            solicitudes = self.gestor_vet.solicitudes_pendientes()
            self.sol_res_map_vet = {}
            for s in solicitudes:
                iid = self.tree_sol_res_vet.insert('', 'end', values=(
                    s['NumeroSolicitud'] or '',
                    (s['NombreMascota'] or 'N/A')[:20],
                    s['Especie'] or ''
                ))
                self.sol_res_map_vet[iid] = s['SolicitudVetID']
        except Exception as e:
            print(f"Error cargando solicitudes vet: {e}")

    def buscar_solicitudes_resultado_vet(self):
        filtro = self.entry_buscar_res_vet.get().strip()
        for item in self.tree_sol_res_vet.get_children():
            self.tree_sol_res_vet.delete(item)
        try:
            if filtro:
                solicitudes = self.gestor_vet.buscar_solicitudes(filtro)
            else:
                solicitudes = self.gestor_vet.solicitudes_pendientes()

            self.sol_res_map_vet = {}
            for s in solicitudes:
                nombre = s.get('NombreMascota') or 'N/A'
                especie = s.get('Especie') or ''
                iid = self.tree_sol_res_vet.insert('', 'end', values=(
                    s.get('NumeroSolicitud') or '',
                    nombre[:20],
                    especie
                ))
                self.sol_res_map_vet[iid] = s.get('SolicitudVetID') or s.get('SolicitudVetID')
        except Exception as e:
            print(f"Error buscando: {e}")

    def cargar_pruebas_resultado_vet(self, event=None):
        """Carga las pruebas de una solicitud vet con parametros y valores de referencia por especie"""
        sel = self.tree_sol_res_vet.selection()
        if not sel:
            return

        sol_id = self.sol_res_map_vet.get(sel[0])
        if not sol_id:
            return

        # Limpiar frame
        for w in self.pruebas_res_frame_vet.winfo_children():
            w.destroy()

        try:
            sol = self.gestor_vet.obtener_solicitud(sol_id)
            if not sol:
                return

            self.sol_id_resultado_vet = sol_id
            especie = sol.get('Especie') or ''

            # Header info
            edad = ""
            if sol.get('FechaNacimiento'):
                try:
                    fn = sol['FechaNacimiento']
                    hoy = datetime.now()
                    anios = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
                    edad = f" | {anios} años"
                except:
                    pass

            sexo = sol.get('Sexo') or ''
            sexo_txt = f" | {'Macho' if sexo == 'M' else 'Hembra'}" if sexo else ""
            peso_txt = f" | {sol['Peso']}kg" if sol.get('Peso') else ""

            self.lbl_info_sol_vet.config(
                text=f"{sol['NumeroSolicitud']} | {sol['NombreMascota'] or 'N/A'} ({especie}){sexo_txt}{peso_txt}{edad} | Prop: {sol.get('NombrePropietario') or 'N/A'}"
            )

            detalles = self.gestor_vet.obtener_detalles_solicitud(sol_id)
            if not detalles:
                tk.Label(self.pruebas_res_frame_vet, text="No hay pruebas registradas",
                        font=('Segoe UI', 11), bg='white', fg=COLORS['text_light']).pack(pady=50)
                return

            # Frame con scroll
            canvas = tk.Canvas(self.pruebas_res_frame_vet, bg='white', highlightthickness=0)
            scrollbar = ttk.Scrollbar(self.pruebas_res_frame_vet, orient='vertical', command=canvas.yview)
            scroll_frame = tk.Frame(canvas, bg='white')

            scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
            canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
            canvas.configure(yscrollcommand=scrollbar.set)

            def _on_canvas_configure(event):
                canvas.itemconfig(canvas_window, width=event.width)
            canvas.bind('<Configure>', _on_canvas_configure)

            canvas.pack(side='left', fill='both', expand=True)
            scrollbar.pack(side='right', fill='y')

            def on_mousewheel(event):
                canvas.yview_scroll(int(-1*(event.delta/120)), 'units')
            canvas.bind('<Enter>', lambda e: canvas.bind_all('<MouseWheel>', on_mousewheel))
            canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

            self.parametro_entries_vet = {}

            for detalle in detalles:
                detalle_id = detalle['DetalleVetID']
                prueba_id = detalle['PruebaVetID']

                # Frame de la prueba
                prueba_frame = tk.Frame(scroll_frame, bg='white', bd=1, relief='solid')
                prueba_frame.pack(fill='x', pady=5, padx=5)

                # Header prueba
                header_prueba = tk.Frame(prueba_frame, bg='#0d9488')
                header_prueba.pack(fill='x')

                tk.Label(header_prueba, text=f"  {detalle['NombrePrueba']}",
                        font=('Segoe UI', 10, 'bold'), bg='#0d9488', fg='white',
                        anchor='w').pack(side='left', fill='x', expand=True, pady=5, padx=5)

                estado_prueba = detalle.get('Estado') or 'Pendiente'
                color_estado = '#4caf50' if estado_prueba == 'Validado' else '#ff9800' if estado_prueba == 'Capturado' else '#9e9e9e'
                tk.Label(header_prueba, text=estado_prueba, font=('Segoe UI', 9, 'bold'),
                        bg=color_estado, fg='white', padx=10).pack(side='right', pady=5, padx=5)

                # Encabezado de parametros
                param_header = tk.Frame(prueba_frame, bg='#e0f2f1')
                param_header.pack(fill='x')
                tk.Label(param_header, text="Parámetro", font=('Segoe UI', 8, 'bold'),
                        bg='#e0f2f1', width=22, anchor='w').pack(side='left', padx=5, pady=3)
                tk.Label(param_header, text="Resultado", font=('Segoe UI', 8, 'bold'),
                        bg='#e0f2f1', width=14).pack(side='left', padx=5, pady=3)
                tk.Label(param_header, text="Unidad", font=('Segoe UI', 8, 'bold'),
                        bg='#e0f2f1', width=10).pack(side='left', padx=5, pady=3)
                tk.Label(param_header, text=f"Ref. {especie}", font=('Segoe UI', 8, 'bold'),
                        bg='#e0f2f1', width=18, fg='#00695c').pack(side='left', padx=5, pady=3)
                tk.Label(param_header, text="Estado", font=('Segoe UI', 8, 'bold'),
                        bg='#e0f2f1', width=8).pack(side='left', padx=5, pady=3)

                # Parametros
                parametros = self.gestor_vet.obtener_parametros_prueba(prueba_id)
                self.parametro_entries_vet[detalle_id] = []

                for param in parametros:
                    param_id = param['ParametroVetID']
                    es_calculado = bool(param.get('EsCalculado'))
                    nombre_param = param['NombreParametro'] or ''

                    # Valor de referencia por especie
                    ref_texto = self.gestor_vet.obtener_referencia(nombre_param, especie)

                    # Resultado guardado
                    resultado_guardado = self.gestor_vet.obtener_resultado(detalle_id, param_id)

                    bg_row = '#e8f5e9' if es_calculado else 'white'
                    param_row = tk.Frame(prueba_frame, bg=bg_row)
                    param_row.pack(fill='x')

                    nombre_display = f"* {nombre_param}" if es_calculado else nombre_param
                    tk.Label(param_row, text=nombre_display,
                            font=('Segoe UI', 9, 'bold' if es_calculado else 'normal'),
                            bg=bg_row, width=22, anchor='w',
                            fg='#2e7d32' if es_calculado else 'black').pack(side='left', padx=5, pady=2)

                    entry_param = tk.Entry(param_row, font=('Segoe UI', 9), width=12, relief='flat',
                                          bg='#c8e6c9' if es_calculado else '#fafafa',
                                          highlightthickness=1, highlightbackground='#ddd')
                    entry_param.pack(side='left', padx=5, pady=2)
                    if resultado_guardado and resultado_guardado.get('Valor'):
                        entry_param.insert(0, resultado_guardado['Valor'])

                    tk.Label(param_row, text=param.get('Unidad') or '', font=('Segoe UI', 9),
                            bg=bg_row, width=10, fg='#666').pack(side='left', padx=5, pady=2)

                    tk.Label(param_row, text=ref_texto,
                            font=('Segoe UI', 9, 'bold'), bg=bg_row, width=18, anchor='w',
                            fg='#00695c').pack(side='left', padx=5, pady=2)

                    # Indicador de estado (se actualiza al evaluar)
                    lbl_estado = tk.Label(param_row, text="", font=('Segoe UI', 9, 'bold'),
                                         bg=bg_row, width=8)
                    lbl_estado.pack(side='left', padx=5, pady=2)

                    # Evaluar si ya hay valor
                    if resultado_guardado and resultado_guardado.get('Valor'):
                        estado_val = self.gestor_vet.evaluar_resultado(nombre_param, especie, resultado_guardado['Valor'])
                        if estado_val == 'bajo':
                            lbl_estado.config(text="↓ BAJO", fg='#1565c0')
                        elif estado_val == 'alto':
                            lbl_estado.config(text="↑ ALTO", fg='#c62828')
                        elif estado_val == 'normal':
                            lbl_estado.config(text="✓ OK", fg='#2e7d32')

                    self.parametro_entries_vet[detalle_id].append({
                        'param_id': param_id,
                        'entry': entry_param,
                        'nombre': nombre_param,
                        'es_calculado': es_calculado,
                        'lbl_estado': lbl_estado,
                    })

                # Auto-calculo al cambiar valores
                tiene_calculados = any(p.get('es_calculado') for p in self.parametro_entries_vet[detalle_id])
                if tiene_calculados:
                    for param_data in self.parametro_entries_vet[detalle_id]:
                        if not param_data.get('es_calculado'):
                            param_data['entry'].bind('<FocusOut>',
                                lambda e, d=detalle_id: self._calcular_vet(d))
                            param_data['entry'].bind('<Tab>',
                                lambda e, d=detalle_id: self._calcular_vet(d))

                # Botones
                tk.Frame(prueba_frame, height=1, bg='#e0e0e0').pack(fill='x', pady=5)

                btn_frame_prueba = tk.Frame(prueba_frame, bg='white')
                btn_frame_prueba.pack(fill='x', pady=5, padx=5)

                if tiene_calculados:
                    tk.Button(btn_frame_prueba, text="Calcular", font=('Segoe UI', 9, 'bold'),
                             bg='#ff9800', fg='white', relief='flat', padx=15, cursor='hand2',
                             command=lambda d=detalle_id: self._calcular_vet(d)).pack(side='left', padx=3)

                tk.Button(btn_frame_prueba, text="Guardar", font=('Segoe UI', 9),
                         bg=COLORS['primary'], fg='white', relief='flat', padx=15, cursor='hand2',
                         command=lambda d=detalle_id: self.guardar_resultados_vet(d)).pack(side='left', padx=3)

                tk.Button(btn_frame_prueba, text="Validar", font=('Segoe UI', 9),
                         bg=COLORS['success'], fg='white', relief='flat', padx=15, cursor='hand2',
                         command=lambda d=detalle_id: self.validar_resultados_vet(d)).pack(side='left', padx=3)

            # Botones generales
            tk.Frame(scroll_frame, height=2, bg='#0d9488').pack(fill='x', pady=(15, 5), padx=5)

            btn_general = tk.Frame(scroll_frame, bg='white')
            btn_general.pack(fill='x', pady=10, padx=5)

            tk.Button(btn_general, text="💾 Guardar Todos", font=('Segoe UI', 10, 'bold'),
                     bg=COLORS['primary'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=self.guardar_todos_vet).pack(side='left', padx=5)

            tk.Button(btn_general, text="✅ Validar Todos", font=('Segoe UI', 10, 'bold'),
                     bg=COLORS['success'], fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=self.validar_todos_vet).pack(side='left', padx=5)

            tk.Button(btn_general, text="📄 Generar PDF", font=('Segoe UI', 10),
                     bg='#7b1fa2', fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=lambda: self.generar_pdf_resultado_vet(guardar_como=True)).pack(side='right', padx=5)

            tk.Button(btn_general, text="🖨️ Imprimir PDF", font=('Segoe UI', 10),
                     bg='#1565C0', fg='white', relief='flat', padx=20, pady=8,
                     cursor='hand2', command=lambda: self.generar_pdf_resultado_vet(guardar_como=False)).pack(side='right', padx=5)

        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _calcular_vet(self, detalle_id):
        """Ejecuta calculos automaticos para hematologia vet"""
        if detalle_id not in self.parametro_entries_vet:
            return

        # Primero guardar valores actuales en memoria
        valores = {}
        for p in self.parametro_entries_vet[detalle_id]:
            val = p['entry'].get().strip()
            if val and not p.get('es_calculado'):
                try:
                    valores[p['nombre']] = float(val)
                except:
                    pass

        hematies = valores.get('Hematies')
        hemoglobina = valores.get('Hemoglobina')
        hematocrito = valores.get('Hematocrito')

        for p in self.parametro_entries_vet[detalle_id]:
            if not p.get('es_calculado'):
                continue

            resultado = None
            if p['nombre'] == 'VCM' and hematocrito and hematies and hematies > 0:
                resultado = round((hematocrito / hematies) * 10, 1)
            elif p['nombre'] == 'HCM' and hemoglobina and hematies and hematies > 0:
                resultado = round((hemoglobina / hematies) * 10, 1)
            elif p['nombre'] == 'CHCM' and hemoglobina and hematocrito and hematocrito > 0:
                resultado = round((hemoglobina / hematocrito) * 100, 1)

            if resultado is not None:
                p['entry'].delete(0, 'end')
                p['entry'].insert(0, str(resultado))

        # Actualizar indicadores de estado
        sol = self.gestor_vet.obtener_solicitud(self.sol_id_resultado_vet)
        especie = sol.get('Especie') or '' if sol else ''
        for p in self.parametro_entries_vet[detalle_id]:
            val = p['entry'].get().strip()
            if val:
                estado_val = self.gestor_vet.evaluar_resultado(p['nombre'], especie, val)
                if estado_val == 'bajo':
                    p['lbl_estado'].config(text="↓ BAJO", fg='#1565c0')
                elif estado_val == 'alto':
                    p['lbl_estado'].config(text="↑ ALTO", fg='#c62828')
                elif estado_val == 'normal':
                    p['lbl_estado'].config(text="✓ OK", fg='#2e7d32')
                else:
                    p['lbl_estado'].config(text="")

    def guardar_resultados_vet(self, detalle_id):
        """Guarda resultados de una prueba vet"""
        if detalle_id not in self.parametro_entries_vet:
            return

        count = 0
        for param_data in self.parametro_entries_vet[detalle_id]:
            valor = param_data['entry'].get().strip()
            if valor:
                if self.gestor_vet.guardar_resultado(detalle_id, param_data['param_id'], valor,
                                                     self.usuario_id_vet):
                    count += 1

        if count > 0:
            try:
                self.gestor_vet.db.update('DetalleSolicitudesVet', {
                    'Estado': 'Capturado'
                }, f"DetalleVetID = {detalle_id}")
            except:
                pass

            # Ejecutar calculos automaticos
            calc = self.gestor_vet.ejecutar_calculos_hematologia(detalle_id)
            if calc > 0:
                messagebox.showinfo("Éxito", f"{count} parámetros guardados\n{calc} valores calculados automáticamente")
            else:
                messagebox.showinfo("Éxito", f"{count} parámetros guardados")

            self.cargar_pruebas_resultado_vet()

    @property
    def usuario_id_vet(self):
        return self.user.get('UsuarioID', 1)

    def validar_resultados_vet(self, detalle_id):
        """Valida resultados de una prueba vet"""
        # Primero guardar
        self.guardar_resultados_vet(detalle_id)
        if self.gestor_vet.validar_resultados(detalle_id):
            messagebox.showinfo("Éxito", "Resultados validados")
            self.cargar_pruebas_resultado_vet()

    def guardar_todos_vet(self):
        """Guarda todos los resultados vet"""
        if not hasattr(self, 'parametro_entries_vet'):
            return
        total = 0
        for detalle_id in self.parametro_entries_vet:
            for p in self.parametro_entries_vet[detalle_id]:
                valor = p['entry'].get().strip()
                if valor:
                    if self.gestor_vet.guardar_resultado(detalle_id, p['param_id'], valor, self.usuario_id_vet):
                        total += 1
            try:
                self.gestor_vet.db.update('DetalleSolicitudesVet', {'Estado': 'Capturado'}, f"DetalleVetID = {detalle_id}")
            except:
                pass
            self.gestor_vet.ejecutar_calculos_hematologia(detalle_id)

        if total > 0:
            messagebox.showinfo("Éxito", f"{total} parámetros guardados en total")
            self.cargar_pruebas_resultado_vet()

    def validar_todos_vet(self):
        """Valida todos los resultados vet"""
        self.guardar_todos_vet()
        if not hasattr(self, 'parametro_entries_vet'):
            return
        for detalle_id in self.parametro_entries_vet:
            self.gestor_vet.validar_resultados(detalle_id)

        # Actualizar estado de la solicitud
        try:
            self.gestor_vet.db.update('SolicitudesVet', {'EstadoSolicitud': 'Completado'},
                                      f"SolicitudVetID = {self.sol_id_resultado_vet}")
        except:
            pass

        messagebox.showinfo("Éxito", "Todos los resultados validados")
        self.cargar_pruebas_resultado_vet()

    # ============================================================
    # VET - PDF
    # ============================================================

    def generar_pdf_resultado_vet(self, guardar_como=False):
        """Genera PDF de resultados veterinarios con valores de referencia por especie"""
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Error", "La librería reportlab no está instalada.\nEjecute: pip install reportlab")
            return None

        if not hasattr(self, 'sol_id_resultado_vet'):
            messagebox.showwarning("Aviso", "Seleccione una solicitud primero")
            return None

        try:
            sol = self.gestor_vet.obtener_solicitud(self.sol_id_resultado_vet)
            if not sol:
                messagebox.showwarning("Aviso", "No se encontró la solicitud")
                return None

            especie = sol.get('Especie') or ''

            # Configuración administrativa
            config_lab = None
            ruta_logo = None
            if self.config_administrativa:
                config_lab = self.config_administrativa.obtener_configuracion()
                ruta_logo = self.config_administrativa.obtener_ruta_logo()

            # Ruta del archivo
            if guardar_como:
                num_sol = str(sol.get('NumeroSolicitud', 'VET')).replace('/', '-').replace('\\', '-')
                filename = filedialog.asksaveasfilename(
                    title="Guardar PDF Veterinario",
                    defaultextension=".pdf",
                    filetypes=[("Archivos PDF", "*.pdf")],
                    initialfile=f"VET_{num_sol}.pdf"
                )
                if not filename:
                    return None
            else:
                import tempfile
                temp_dir = tempfile.gettempdir()
                num_sol_safe = str(sol.get('NumeroSolicitud', 'VET')).replace('/', '-').replace('\\', '-').replace(':', '-')
                filename = os.path.join(temp_dir, f"VET_{num_sol_safe}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf")

            page_size = letter
            if config_lab and config_lab.get('TamanoPapel') == 'Oficio':
                page_size = legal

            page_width, page_height = page_size

            # Pre-consultar bioanalistas activos para sección VET (para calcular márgenes)
            bioanalistas_vet_precarga = []
            try:
                bioanalistas_vet_precarga = db.query(
                    "SELECT b.BioanalistaID FROM Bioanalistas b WHERE b.Activo = True"
                )
            except Exception:
                pass

            left_margin = 0.5 * inch
            right_margin = 0.5 * inch
            top_margin = 0.4 * inch
            bottom_margin = 1.3 * inch if bioanalistas_vet_precarga else 0.5 * inch

            # Datos del paciente
            nombre_mascota = (sol.get('NombreMascota') or 'N/A').upper()
            nombre_prop = (sol.get('NombrePropietario') or 'N/A').upper()
            fecha_sol = sol['FechaSolicitud'].strftime('%d/%m/%Y') if sol.get('FechaSolicitud') else 'N/A'
            num_orden = sol.get('NumeroSolicitud') or 'N/A'
            raza = sol.get('Raza') or 'N/A'
            sexo = 'Macho' if sol.get('Sexo') == 'M' else 'Hembra' if sol.get('Sexo') == 'H' else 'N/A'
            peso = f"{sol['Peso']} kg" if sol.get('Peso') else 'N/A'
            vet_remitente = sol.get('VeterinarioRemitente') or 'N/A'

            edad_texto = 'N/A'
            if sol.get('FechaNacimiento'):
                try:
                    fn = sol['FechaNacimiento']
                    hoy = datetime.now()
                    edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))
                    edad_texto = f"{edad} Años"
                except:
                    pass

            nombre_lab = config_lab.get('NombreLaboratorio', 'LABORATORIO CLÍNICO') if config_lab else 'LABORATORIO CLÍNICO'
            direccion_lab = config_lab.get('Direccion', '') if config_lab else ''
            email_lab = config_lab.get('Email', '') if config_lab else ''
            telefono_lab = config_lab.get('Telefono1', '') if config_lab else ''

            header_height = 2.3 * inch

            def draw_header(canvas_pdf, doc):
                canvas_pdf.saveState()
                y_top = page_height - top_margin

                # Logo
                if ruta_logo and os.path.exists(ruta_logo) and config_lab and config_lab.get('MostrarLogo'):
                    try:
                        canvas_pdf.drawImage(ruta_logo, left_margin, y_top - 1.1*inch, width=1.2*inch, height=1.0*inch,
                                           preserveAspectRatio=True, mask='auto')
                    except:
                        pass

                # Info lab
                info_x = left_margin + 1.5*inch
                info_y = y_top - 0.15*inch
                canvas_pdf.setFont('Helvetica-Bold', 10)
                canvas_pdf.drawString(info_x, info_y, nombre_lab.upper())
                canvas_pdf.setFont('Helvetica', 8)
                if direccion_lab:
                    canvas_pdf.drawString(info_x, info_y - 11, direccion_lab[:70])
                if email_lab:
                    canvas_pdf.drawString(info_x, info_y - 22, f"Correo: {email_lab}")
                if telefono_lab:
                    canvas_pdf.drawString(info_x, info_y - 33, f"Teléfono: {telefono_lab}")

                canvas_pdf.setFont('Helvetica-Bold', 9)
                canvas_pdf.drawString(info_x, info_y - 48, "SECCIÓN VETERINARIA")

                # Cuadro datos paciente
                box_y = y_top - 1.2*inch
                box_height = 0.9 * inch
                box_width = page_width - left_margin - right_margin

                canvas_pdf.setStrokeColor(colors.black)
                canvas_pdf.setLineWidth(1)
                canvas_pdf.rect(left_margin, box_y - box_height, box_width, box_height)

                col1_x = left_margin + 0.1*inch
                col2_x = left_margin + 3.5*inch

                row1_y = box_y - 0.15*inch
                row2_y = row1_y - 0.18*inch
                row3_y = row2_y - 0.18*inch
                row4_y = row3_y - 0.18*inch

                canvas_pdf.setFont('Helvetica-Bold', 8)
                canvas_pdf.drawString(col1_x, row1_y, "MASCOTA:")
                canvas_pdf.drawString(col1_x, row2_y, "ESPECIE:")
                canvas_pdf.drawString(col1_x, row3_y, "SEXO:")
                canvas_pdf.drawString(col1_x, row4_y, "PROPIETARIO:")

                canvas_pdf.drawString(col2_x, row1_y, "N° ORDEN:")
                canvas_pdf.drawString(col2_x, row2_y, "RAZA:")
                canvas_pdf.drawString(col2_x, row3_y, "PESO:")
                canvas_pdf.drawString(col2_x, row4_y, "VETERINARIO:")

                val_off1 = 0.85*inch
                val_off2 = 0.85*inch

                canvas_pdf.setFont('Helvetica', 8)
                canvas_pdf.drawString(col1_x + val_off1, row1_y, nombre_mascota[:30])
                canvas_pdf.drawString(col1_x + val_off1, row2_y, especie)
                canvas_pdf.drawString(col1_x + val_off1, row3_y, sexo)
                canvas_pdf.drawString(col1_x + val_off1, row4_y, nombre_prop[:30])

                canvas_pdf.drawString(col2_x + val_off2, row1_y, str(num_orden)[:20])
                canvas_pdf.drawString(col2_x + val_off2, row2_y, raza)
                canvas_pdf.drawString(col2_x + val_off2, row3_y, peso)
                canvas_pdf.drawString(col2_x + val_off2, row4_y, vet_remitente[:25])

                # Fecha derecha
                canvas_pdf.drawString(page_width - right_margin - 1.5*inch, row1_y, f"FECHA: {fecha_sol}")
                canvas_pdf.drawString(page_width - right_margin - 1.5*inch, row2_y, f"EDAD: {edad_texto}")

                canvas_pdf.restoreState()

            # Obtener bioanalistas activos para la sección VET
            bioanalistas_vet = []
            try:
                bioanalistas_vet = db.query(
                    "SELECT b.BioanalistaID, b.NombreCompleto, b.Cedula, b.NumeroRegistro, "
                    "b.RutaFirma, a.NombreArea "
                    "FROM Bioanalistas b LEFT JOIN Areas a ON b.AreaID = a.AreaID "
                    "WHERE b.Activo = True ORDER BY b.NombreCompleto"
                )
            except Exception:
                pass

            def draw_footer(canvas_pdf, doc):
                canvas_pdf.saveState()
                footer_y = bottom_margin - 0.1*inch
                canvas_pdf.setFont('Helvetica-Oblique', 7)
                canvas_pdf.drawString(left_margin, footer_y, f"Impreso por ANgesLAB - Sección Veterinaria | {datetime.now().strftime('%d/%m/%Y %H:%M')}")

                base_dir = os.path.dirname(os.path.abspath(__file__))

                if bioanalistas_vet:
                    # Dibujar firmas de bioanalistas (hasta 3 lado a lado, alineadas a la derecha)
                    num_bios = min(len(bioanalistas_vet), 3)
                    ancho_bloque = 2.2 * inch
                    start_x = page_width - right_margin - (num_bios * ancho_bloque)

                    for idx, bio in enumerate(bioanalistas_vet[:3]):
                        bloque_x = start_x + (idx * ancho_bloque) + (ancho_bloque / 2)
                        y_pos = footer_y + 0.9*inch

                        # Imagen de firma
                        ruta_firma = bio.get('RutaFirma', '')
                        if ruta_firma:
                            ruta_abs_firma = os.path.join(base_dir, ruta_firma)
                            if os.path.exists(ruta_abs_firma):
                                try:
                                    firma_w = 1.2*inch
                                    firma_h = 0.4*inch
                                    canvas_pdf.drawImage(
                                        ruta_abs_firma,
                                        bloque_x - firma_w/2, y_pos,
                                        width=firma_w, height=firma_h,
                                        preserveAspectRatio=True, mask='auto'
                                    )
                                    y_pos -= 0.05*inch
                                except Exception:
                                    pass

                        # Línea
                        canvas_pdf.setStrokeColor(colors.grey)
                        canvas_pdf.setLineWidth(0.5)
                        linea_w = 1.5*inch
                        canvas_pdf.line(bloque_x - linea_w/2, y_pos, bloque_x + linea_w/2, y_pos)

                        y_pos -= 0.12*inch
                        canvas_pdf.setFont('Helvetica-Bold', 7)
                        canvas_pdf.drawCentredString(bloque_x, y_pos, bio.get('NombreCompleto', ''))

                        y_pos -= 0.11*inch
                        canvas_pdf.setFont('Helvetica', 6.5)
                        canvas_pdf.drawCentredString(bloque_x, y_pos, f"C.I.: {bio.get('Cedula', '')}")

                        y_pos -= 0.1*inch
                        canvas_pdf.drawCentredString(bloque_x, y_pos, f"Reg.: {bio.get('NumeroRegistro', '')}")

                        y_pos -= 0.1*inch
                        canvas_pdf.setFont('Helvetica-Oblique', 6)
                        canvas_pdf.drawCentredString(bloque_x, y_pos, "Bioanalista")

                elif config_lab and config_lab.get('MostrarFirma'):
                    # Fallback: firma del Director
                    if config_lab.get('NombreDirector'):
                        canvas_pdf.setFont('Helvetica', 7)
                        canvas_pdf.drawRightString(page_width - right_margin, footer_y + 0.3*inch, config_lab['NombreDirector'])
                    if config_lab.get('TituloDirector'):
                        canvas_pdf.drawRightString(page_width - right_margin, footer_y + 0.15*inch, config_lab['TituloDirector'])

                canvas_pdf.restoreState()

            def header_footer(canvas_pdf, doc):
                draw_header(canvas_pdf, doc)
                draw_footer(canvas_pdf, doc)

            doc = BaseDocTemplate(filename, pagesize=page_size)

            content_frame = Frame(
                left_margin,
                bottom_margin,
                page_width - left_margin - right_margin,
                page_height - top_margin - header_height - bottom_margin,
                id='content'
            )

            page_template = PageTemplate(id='main', frames=[content_frame], onPage=header_footer)
            doc.addPageTemplates([page_template])

            styles = getSampleStyleSheet()
            elements = []

            titulo_prueba_style = ParagraphStyle(
                'TituloPruebaVet', parent=styles['Heading2'],
                fontSize=11, fontName='Helvetica-Bold', alignment=TA_CENTER,
                spaceAfter=8, spaceBefore=12, textColor=colors.black
            )

            # Procesar pruebas
            detalles = self.gestor_vet.obtener_detalles_solicitud(self.sol_id_resultado_vet)

            for detalle in detalles:
                detalle_id = detalle['DetalleVetID']
                prueba_id = detalle['PruebaVetID']
                nombre_prueba = (detalle.get('NombrePrueba') or '').upper()

                parametros = self.gestor_vet.obtener_parametros_prueba(prueba_id)
                if not parametros:
                    continue

                prueba_elements = []
                prueba_elements.append(Paragraph(nombre_prueba, titulo_prueba_style))

                header_data = [['Descripción', 'Resultado', 'Unidad', f'Ref. {especie}']]
                col_widths = [2.5*inch, 1.2*inch, 0.8*inch, 2.0*inch]

                header_table = Table(header_data, colWidths=col_widths)
                header_table.setStyle(TableStyle([
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('TOPPADDING', (0, 0), (-1, 0), 6),
                ]))
                prueba_elements.append(header_table)

                param_data = []
                for param in parametros:
                    resultado = self.gestor_vet.obtener_resultado(detalle_id, param['ParametroVetID'])
                    valor = resultado.get('Valor') if resultado else ''
                    if valor is None:
                        valor = ''
                    valor_str = str(valor).strip()
                    if not valor_str:
                        continue

                    unidad = param.get('Unidad') or ''
                    ref_texto = self.gestor_vet.obtener_referencia(param['NombreParametro'], especie)
                    nombre_p = '   ' + (param['NombreParametro'] or '')

                    param_data.append([nombre_p, valor_str, unidad, ref_texto])

                if param_data:
                    param_table = Table(param_data, colWidths=col_widths)
                    table_style = [
                        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 0), (-1, -1), 8),
                        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
                        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                        ('TOPPADDING', (0, 0), (-1, -1), 3),
                        ('LEFTPADDING', (0, 0), (0, -1), 8),
                    ]

                    # Marcar valores fuera de rango
                    for i, row in enumerate(param_data):
                        nombre_clean = row[0].strip()
                        estado = self.gestor_vet.evaluar_resultado(nombre_clean, especie, row[1])
                        if estado == 'alto':
                            table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.red))
                            table_style.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))
                        elif estado == 'bajo':
                            table_style.append(('TEXTCOLOR', (1, i), (1, i), colors.blue))
                            table_style.append(('FONTNAME', (1, i), (1, i), 'Helvetica-Bold'))

                    param_table.setStyle(TableStyle(table_style))
                    prueba_elements.append(param_table)

                    try:
                        elements.append(KeepTogether(prueba_elements))
                    except:
                        elements.extend(prueba_elements)

                    elements.append(Spacer(1, 0.2*inch))

            if not elements:
                messagebox.showwarning("Aviso", "No hay resultados para generar el PDF")
                return None

            doc.build(elements)

            if not guardar_como:
                # Abrir PDF directamente
                try:
                    os.startfile(filename)
                except:
                    webbrowser.open(filename)

            messagebox.showinfo("Éxito", f"PDF generado:\n{filename}")
            return filename

        except Exception as e:
            messagebox.showerror("Error", f"Error generando PDF: {e}")
            return None

    # ============================================================
    # CONFIGURACIÓN
    # ============================================================

    def show_config(self):
        """Abre la ventana completa de configuración"""
        try:
            from modulos.ventana_configuracion_completa import abrir_ventana_configuracion_completa
            abrir_ventana_configuracion_completa(
                self.root,
                db,
                self.user,
                callback_actualizar=self.recargar_configuracion
            )
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir configuración:\n{e}")
            import traceback
            traceback.print_exc()

    # ── Red LAN ─────────────────────────────────────────────────────────────

    def show_config_red_lan(self):
        """Ventana de configuración de base de datos en red LAN."""
        win = tk.Toplevel(self.root)
        win.title("🌐 Configuración Red LAN")
        win.grab_set()
        win.configure(bg='white')
        hacer_ventana_responsiva(win, 540, 320, min_ancho=480, min_alto=260)

        tk.Frame(win, bg='#1565c0', height=50).pack(fill='x')
        tk.Label(win, text="🌐 Configuración Base de Datos en Red",
                 font=('Segoe UI', 13, 'bold'), bg='#1565c0', fg='white').place(x=0, y=10, relwidth=1)

        frame = tk.Frame(win, bg='white')
        frame.pack(fill='both', expand=True, padx=25, pady=20)

        tk.Label(frame, text="Ruta de la base de datos (local o UNC):",
                 font=('Segoe UI', 10, 'bold'), bg='white').pack(anchor='w')
        tk.Label(frame, text="Ejemplo LAN: \\\\SERVIDOR\\compartido\\ANgesLAB.accdb",
                 font=('Segoe UI', 8), bg='white', fg='#555').pack(anchor='w', pady=(0, 6))

        entry_ruta = tk.Entry(frame, font=('Segoe UI', 10), relief='flat', bg='#f8f9fa',
                              highlightthickness=1, highlightbackground='#bbb')
        entry_ruta.pack(fill='x', ipady=6)
        entry_ruta.insert(0, db.db_path)

        def examinar():
            from tkinter.filedialog import askopenfilename
            ruta = askopenfilename(title="Seleccionar base de datos",
                                   filetypes=[("Access DB", "*.accdb *.mdb")])
            if ruta:
                entry_ruta.delete(0, 'end')
                entry_ruta.insert(0, ruta)

        btn_row = tk.Frame(frame, bg='white')
        btn_row.pack(fill='x', pady=(10, 0))
        tk.Button(btn_row, text="📂 Examinar", font=('Segoe UI', 9),
                  bg='#78909c', fg='white', relief='flat', padx=10,
                  command=examinar).pack(side='left')

        tk.Label(frame,
                 text="⚠️  Reinicie la aplicación para que el cambio tenga efecto.",
                 font=('Segoe UI', 8, 'italic'), bg='white', fg='#e65100').pack(anchor='w', pady=(14, 0))

        def guardar():
            nueva = entry_ruta.get().strip()
            if not nueva:
                messagebox.showerror("Error", "La ruta no puede estar vacía", parent=win)
                return
            Database.guardar_ruta_db(nueva)
            messagebox.showinfo("Guardado",
                                "Ruta guardada.\nReinicie ANgesLAB para conectar a la nueva base de datos.",
                                parent=win)
            win.destroy()

        btn_f = tk.Frame(win, bg='white')
        btn_f.pack(fill='x', padx=25, pady=(0, 15))
        tk.Button(btn_f, text="❌ Cancelar", font=('Segoe UI', 10),
                  bg='#95a5a6', fg='white', relief='flat', padx=15, pady=6,
                  command=win.destroy).pack(side='right', padx=5)
        tk.Button(btn_f, text="💾 Guardar", font=('Segoe UI', 10, 'bold'),
                  bg='#1565c0', fg='white', relief='flat', padx=15, pady=6,
                  command=guardar).pack(side='right')

    def show_config_old(self):
        """Versión antigua de configuración (respaldo)"""
        self.clear_content()
        self.set_title("⚙️ Configuración")

        frame = tk.Frame(self.content, bg='white')
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Info del sistema
        tk.Label(frame, text="Información del Sistema", font=('Segoe UI', 14, 'bold'),
                bg='white').pack(anchor='w', pady=(0, 15))

        info = [
            ("Versión:", "1.0.0"),
            ("Base de datos:", "ANgesLAB.accdb"),
            ("Usuario:", self.user.get('NombreCompleto', 'N/A')),
            ("Rol:", self.user.get('NombreUsuario', 'N/A')),
        ]

        for label, value in info:
            row = tk.Frame(frame, bg='white')
            row.pack(fill='x', pady=3)
            tk.Label(row, text=label, font=('Segoe UI', 10, 'bold'), bg='white', width=15, anchor='w').pack(side='left')
            tk.Label(row, text=value, font=('Segoe UI', 10), bg='white').pack(side='left')

        # Estadísticas
        tk.Label(frame, text="Estadísticas de la Base de Datos", font=('Segoe UI', 14, 'bold'),
                bg='white').pack(anchor='w', pady=(30, 15))

        stats = [
            ("Pacientes:", db.count('Pacientes')),
            ("Médicos:", db.count('Medicos')),
            ("Pruebas:", db.count('Pruebas')),
            ("Solicitudes:", db.count('Solicitudes')),
            ("Áreas:", db.count('Areas')),
        ]

        for label, value in stats:
            row = tk.Frame(frame, bg='white')
            row.pack(fill='x', pady=3)
            tk.Label(row, text=label, font=('Segoe UI', 10, 'bold'), bg='white', width=15, anchor='w').pack(side='left')
            tk.Label(row, text=f"{value:,}", font=('Segoe UI', 10), bg='white').pack(side='left')

        # Sección de configuraciones
        tk.Label(frame, text="Configuraciones del Sistema", font=('Segoe UI', 14, 'bold'),
                bg='white').pack(anchor='w', pady=(30, 15))

        # Estado de módulos
        modulos_estado = [
            ("Módulo reportlab (PDF)", REPORTLAB_AVAILABLE),
            ("Módulo de numeración", CONFIG_NUMERACION_DISPONIBLE),
            ("Módulo administrativo", CONFIG_ADMINISTRATIVA_DISPONIBLE),
        ]

        for modulo, disponible in modulos_estado:
            row = tk.Frame(frame, bg='white')
            row.pack(fill='x', pady=3)
            tk.Label(row, text=modulo, font=('Segoe UI', 10, 'bold'), bg='white', width=25, anchor='w').pack(side='left')
            estado_text = "✓ Disponible" if disponible else "✗ No disponible"
            color = COLORS['success'] if disponible else COLORS['danger']
            tk.Label(row, text=estado_text, font=('Segoe UI', 10), bg='white', fg=color).pack(side='left')

        # Botón de configuración de numeración
        if CONFIG_NUMERACION_DISPONIBLE:
            tk.Label(frame, text="", bg='white').pack(pady=10)  # Espaciador

            btn_config_numeracion = tk.Button(
                frame,
                text="⚙️ Configurar Numeración de Solicitudes",
                font=('Segoe UI', 11, 'bold'),
                bg=COLORS['primary'],
                fg='white',
                relief='flat',
                padx=20,
                pady=12,
                cursor='hand2',
                command=self._abrir_config_numeracion
            )
            btn_config_numeracion.pack(anchor='w', pady=5)

            tk.Label(
                frame,
                text="Configure el tipo de numeración de solicitudes (Diaria, Anual o Continua)",
                font=('Segoe UI', 9),
                bg='white',
                fg=COLORS['text_light']
            ).pack(anchor='w', padx=20)

        # Botón de configuración administrativa
        if CONFIG_ADMINISTRATIVA_DISPONIBLE:
            tk.Label(frame, text="", bg='white').pack(pady=5)  # Espaciador

            btn_config_admin = tk.Button(
                frame,
                text="🏢 Configuración Administrativa del Laboratorio",
                font=('Segoe UI', 11, 'bold'),
                bg=COLORS['success'],
                fg='white',
                relief='flat',
                padx=20,
                pady=12,
                cursor='hand2',
                command=self._abrir_config_administrativa
            )
            btn_config_admin.pack(anchor='w', pady=5)

            tk.Label(
                frame,
                text="Configure información del laboratorio, logo, impresión, precios y más",
                font=('Segoe UI', 9),
                bg='white',
                fg=COLORS['text_light']
            ).pack(anchor='w', padx=20)

    def _abrir_config_numeracion(self):
        """Abre la ventana de configuración de numeración"""
        try:
            abrir_ventana_config_numeracion(self.root, db)
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir configuración de numeración:\n{e}")

    def _abrir_config_administrativa(self):
        """Abre la ventana de configuración administrativa"""
        try:
            abrir_ventana_config_administrativa(self.root, db, callback_guardar=self.recargar_configuracion)
        except Exception as e:
            messagebox.showerror("Error", f"Error al abrir configuración administrativa:\n{e}")

    def logout(self):
        if messagebox.askyesno("Cerrar Sesión", "¿Desea cerrar la sesión?"):
            self.root.destroy()
            main()

    def run(self):
        self.root.mainloop()

# ============================================================
# PUNTO DE ENTRADA
# ============================================================

def _asegurar_usuario_admin():
    """Asegura que exista al menos un usuario administrador y migra seguridad."""
    import time
    from modulos.seguridad_db import SeguridadContrasenas

    def _obtener_campos_tabla():
        """Obtiene la lista de campos de la tabla Usuarios."""
        try:
            rs = db.execute("SELECT TOP 1 * FROM Usuarios")[0]
            campos = []
            for i in range(rs.Fields.Count):
                campos.append(rs.Fields[i].Name)
            return campos
        except:
            return []

    def _crear_columna_segura(nombre_col, tipo_col):
        """Crea una columna cerrando y reabriendo la conexion para evitar locks."""
        campos = _obtener_campos_tabla()
        if nombre_col in campos:
            return True  # Ya existe

        # Cerrar conexion actual para liberar locks en la tabla
        try:
            db.close()
        except:
            pass
        time.sleep(0.5)

        # Abrir nueva conexion y ejecutar ALTER TABLE
        import win32com.client
        exito = False
        try:
            conn_temp = win32com.client.Dispatch("ADODB.Connection")
            conn_temp.Open(f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={db.db_path};")
            try:
                conn_temp.Execute(f"ALTER TABLE [Usuarios] ADD COLUMN [{nombre_col}] {tipo_col}")
                exito = True
            except Exception as e1:
                # Intentar con tipo TEXT(255) como alternativa
                try:
                    conn_temp.Execute(f"ALTER TABLE [Usuarios] ADD COLUMN [{nombre_col}] TEXT(255)")
                    exito = True
                except Exception as e2:
                    # Intentar con MEMO como ultima alternativa
                    try:
                        conn_temp.Execute(f"ALTER TABLE [Usuarios] ADD COLUMN [{nombre_col}] MEMO")
                        exito = True
                    except Exception as e3:
                        print(f"Error creando columna {nombre_col}: {e3}")
            conn_temp.Close()
        except Exception as ec:
            print(f"Error en conexion temporal para {nombre_col}: {ec}")

        time.sleep(0.5)
        # Reconectar la conexion principal
        try:
            db.conn = None  # Forzar reconexion
            db.connect()
        except:
            pass

        return exito

    try:
        # Paso 1: Asegurar campo Nivel
        try:
            campos = _obtener_campos_tabla()
            if 'Nivel' not in campos:
                _crear_columna_segura('Nivel', "TEXT(20)")
            db.execute("UPDATE [Usuarios] SET [Nivel] = 'Administrador' WHERE [Nivel] IS NULL")
        except:
            pass

        # Paso 2: Asegurar columnas de hash de contrasena
        hash_creado = _crear_columna_segura('PasswordHash', 'TEXT(255)')
        salt_creado = _crear_columna_segura('PasswordSalt', 'TEXT(255)')

        # Verificar que las columnas existen realmente
        campos = _obtener_campos_tabla()
        tiene_hash = 'PasswordHash' in campos
        tiene_salt = 'PasswordSalt' in campos

        if not tiene_hash or not tiene_salt:
            print(f"ADVERTENCIA: No se pudieron crear columnas de seguridad.")
            print(f"  PasswordHash: {'OK' if tiene_hash else 'FALTA'}")
            print(f"  PasswordSalt: {'OK' if tiene_salt else 'FALTA'}")
            print(f"  El login funcionara con contrasenas en texto plano.")
            # Aun asi, asegurar que exista al menos un admin
            total = db.count('Usuarios')
            if total == 0:
                try:
                    db.insert('Usuarios', {
                        'NombreCompleto': 'Administrador',
                        'NombreUsuario': 'admin',
                        'Password': 'admin123',
                        'Nivel': 'Administrador',
                        'Activo': True
                    })
                except:
                    pass
            return

        # Paso 3: Crear usuarios iniciales o migrar existentes
        # NOTA: La contraseña del desarrollador se lee de variable de entorno
        # ANGESLAB_DEV_PWD. Si no está definida, se genera una aleatoria.
        _dev_pwd = os.environ.get('ANGESLAB_DEV_PWD', '')
        if not _dev_pwd:
            _dev_pwd = SeguridadContrasenas.generar_password_temporal()

        total = db.count('Usuarios')
        if total == 0:
            # BD vacia: crear developer y admin con contraseñas seguras
            dev_hash, dev_salt = SeguridadContrasenas.hash_password(_dev_pwd)
            db.insert('Usuarios', {
                'NombreCompleto': 'Desarrollador ANgesLAB',
                'NombreUsuario': 'developer',
                'Password': '',
                'PasswordHash': dev_hash,
                'PasswordSalt': dev_salt,
                'Nivel': 'Desarrollador',
                'Activo': True
            })
            admin_hash, admin_salt = SeguridadContrasenas.hash_password('admin123')
            db.insert('Usuarios', {
                'NombreCompleto': 'Administrador',
                'NombreUsuario': 'admin',
                'Password': '',
                'PasswordHash': admin_hash,
                'PasswordSalt': admin_salt,
                'Nivel': 'Administrador',
                'Activo': True
            })
        else:
            # BD con usuarios: asegurar developer y migrar contrasenas

            # Verificar que exista usuario Desarrollador
            try:
                dev_existe = db.query_one(
                    "SELECT [UsuarioID], [PasswordHash] FROM [Usuarios] WHERE [NombreUsuario]='developer'"
                )
                if not dev_existe:
                    dev_hash, dev_salt = SeguridadContrasenas.hash_password(_dev_pwd)
                    db.insert('Usuarios', {
                        'NombreCompleto': 'Desarrollador ANgesLAB',
                        'NombreUsuario': 'developer',
                        'Password': '',
                        'PasswordHash': dev_hash,
                        'PasswordSalt': dev_salt,
                        'Nivel': 'Desarrollador',
                        'Activo': True
                    })
                else:
                    # Verificar que tenga hash y migrar a PBKDF2 si es legacy
                    ph = dev_existe.get('PasswordHash', '') or ''
                    if not ph:
                        dev_hash, dev_salt = SeguridadContrasenas.hash_password(_dev_pwd)
                        db.execute(
                            f"UPDATE [Usuarios] SET [PasswordHash]='{dev_hash}', "
                            f"[PasswordSalt]='{dev_salt}', [Password]='', "
                            f"[Nivel]='Desarrollador', [Activo]=True "
                            f"WHERE [UsuarioID]={dev_existe['UsuarioID']}"
                        )
            except Exception as ed:
                print(f"Advertencia creando desarrollador: {ed}")

            # Migrar contrasenas en texto plano a hash
            try:
                usuarios_sin_hash = db.query(
                    "SELECT [UsuarioID], [Password] FROM [Usuarios] "
                    "WHERE ([PasswordHash] IS NULL OR [PasswordHash] = '')"
                )
                for u in (usuarios_sin_hash or []):
                    pwd_plano = u.get('Password', '')
                    if pwd_plano:
                        pwd_hash, pwd_salt = SeguridadContrasenas.hash_password(pwd_plano)
                        db.execute(
                            f"UPDATE [Usuarios] SET [PasswordHash]='{pwd_hash}', "
                            f"[PasswordSalt]='{pwd_salt}', [Password]='' "
                            f"WHERE [UsuarioID]={u['UsuarioID']}"
                        )
            except Exception as em:
                print(f"Advertencia migracion contrasenas: {em}")

            # Mapear nivel Operador -> Recepcion
            try:
                db.execute("UPDATE [Usuarios] SET [Nivel]='Recepcion' WHERE [Nivel]='Operador'")
            except:
                pass

    except Exception as e:
        print(f"Advertencia: No se pudo verificar usuario admin: {e}")

def main():
    # Mostrar splash screen primero
    try:
        from modulos.splash_screen import mostrar_splash
        mostrar_splash(duracion=3500)
    except Exception as e:
        print(f"Splash omitido: {e}")

    _asegurar_usuario_admin()
    login = LoginWindow()
    user = login.run()
    if user:
        app = MainApplication(user)
        app.run()

if __name__ == "__main__":
    main()

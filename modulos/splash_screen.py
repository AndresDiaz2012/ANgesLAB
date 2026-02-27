"""
Splash Screen Futurista para ANgesLAB
=====================================
Pantalla de presentacion con imagen de laboratorio y efecto zoom.
Diseno que transmite confianza, seguridad y profesionalismo.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import tkinter as tk
import math
import time
import os

# Importar PIL para la imagen
try:
    from PIL import Image as PILImage, ImageTk, ImageEnhance, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class SplashScreen:
    """
    Pantalla de presentacion con imagen de laboratorio y efecto zoom.
    """

    COLORS = {
        'bg_dark': '#0f172a',
        'bg_gradient': '#1e293b',
        'primary': '#0891b2',
        'secondary': '#06b6d4',
        'accent': '#0d9488',
        'white': '#ffffff',
        'gray_light': '#94a3b8',
        'gray_dark': '#475569',
    }

    def __init__(self, duration=4000):
        self.duration = duration
        self.root = tk.Tk()
        self.root.withdraw()

        # Ventana mas grande para mostrar bien la imagen
        self.width = 650
        self.height = 500

        # Centrar
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = (screen_h - self.height) // 2

        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=self.COLORS['bg_dark'])

        # Canvas principal
        self.canvas = tk.Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg=self.COLORS['bg_dark'],
            highlightthickness=0
        )
        self.canvas.pack(fill='both', expand=True)

        # Variables de animacion
        self.zoom_level = 1.0
        self.image_frames = []
        self.current_frame = 0
        self.lab_image = None
        self.lab_image_id = None

        # Altura de la seccion de imagen (parte superior)
        self.image_height = 320

        # Crear elementos
        self._crear_fondo()
        self._cargar_imagen_laboratorio()
        self._crear_logo()
        self._crear_barra_progreso()
        self._crear_texto_carga()

        self.root.deiconify()
        self.root.update()

    def _crear_fondo(self):
        """Crea el fondo oscuro con gradiente."""
        # Fondo inferior (donde va el logo y barra)
        for i in range(20):
            y1 = self.image_height + i * ((self.height - self.image_height) // 20)
            y2 = self.image_height + (i + 1) * ((self.height - self.image_height) // 20)
            intensity = int(15 + i * 0.5)
            color = f'#{intensity:02x}{intensity+3:02x}{intensity+8:02x}'
            self.canvas.create_rectangle(0, y1, self.width, y2, fill=color, outline='')

        # Linea separadora brillante
        self.canvas.create_line(
            50, self.image_height, self.width - 50, self.image_height,
            fill=self.COLORS['primary'], width=2
        )

    def _cargar_imagen_laboratorio(self):
        """Carga la imagen del laboratorio y prepara frames para zoom."""
        if not PIL_AVAILABLE:
            self._crear_fondo_alternativo()
            return

        try:
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            img_path = os.path.join(base_path, 'fondo.png')

            if not os.path.exists(img_path):
                self._crear_fondo_alternativo()
                return

            # Cargar imagen original
            original = PILImage.open(img_path)

            # Mejorar colores
            original = ImageEnhance.Contrast(original).enhance(1.3)
            original = ImageEnhance.Color(original).enhance(1.4)
            original = ImageEnhance.Brightness(original).enhance(1.05)

            # Preparar frames de zoom (de alejado a acercado)
            num_frames = 60
            self.image_frames = []

            for i in range(num_frames):
                # Zoom progresivo de 1.0 a 1.5
                zoom = 1.0 + (i / num_frames) * 0.5

                # Calcular recorte para zoom
                ow, oh = original.size
                new_w = int(ow / zoom)
                new_h = int(oh / zoom)

                # Centrar el recorte
                left = (ow - new_w) // 2
                top = (oh - new_h) // 2
                right = left + new_w
                bottom = top + new_h

                # Recortar y redimensionar
                frame = original.crop((left, top, right, bottom))
                frame = frame.resize((self.width, self.image_height), PILImage.Resampling.LANCZOS)

                # Agregar vignette sutil
                frame = self._agregar_vignette(frame)

                self.image_frames.append(ImageTk.PhotoImage(frame))

            # Mostrar primer frame
            if self.image_frames:
                self.lab_image_id = self.canvas.create_image(
                    self.width // 2, self.image_height // 2,
                    image=self.image_frames[0], anchor='center'
                )

        except Exception as e:
            print(f"Error cargando imagen: {e}")
            self._crear_fondo_alternativo()

    def _agregar_vignette(self, img):
        """Agrega efecto vignette a la imagen."""
        # Crear mascara de vignette
        w, h = img.size
        vignette = PILImage.new('RGBA', (w, h), (0, 0, 0, 0))

        from PIL import ImageDraw
        draw = ImageDraw.Draw(vignette)

        # Oscurecer bordes
        for i in range(40):
            alpha = int(80 * (40 - i) / 40)
            draw.rectangle([i, i, w-i, h-i], outline=(15, 23, 42, alpha), width=1)

        # Combinar
        img_rgba = img.convert('RGBA')
        result = PILImage.alpha_composite(img_rgba, vignette)
        return result.convert('RGB')

    def _crear_fondo_alternativo(self):
        """Fondo alternativo si no hay imagen."""
        # Gradiente cyan en la parte superior
        for i in range(self.image_height):
            ratio = i / self.image_height
            r = int(15 + 20 * ratio)
            g = int(23 + 40 * ratio)
            b = int(42 + 60 * ratio)
            self.canvas.create_line(0, i, self.width, i, fill=f'#{r:02x}{g:02x}{b:02x}')

        # Texto alternativo
        self.canvas.create_text(
            self.width // 2, self.image_height // 2,
            text="LABORATORIO CLINICO",
            font=('Segoe UI', 24, 'bold'),
            fill=self.COLORS['primary']
        )

    def _crear_logo(self):
        """Crea el logo ANgesLAB en la parte inferior."""
        logo_y = self.image_height + 50

        # Nombre principal
        self.logo_text = self.canvas.create_text(
            self.width // 2, logo_y,
            text="",
            font=('Segoe UI', 38, 'bold'),
            fill=self.COLORS['white']
        )

        # Linea decorativa
        self.logo_line = self.canvas.create_line(
            self.width // 2, logo_y + 30,
            self.width // 2, logo_y + 30,
            fill=self.COLORS['primary'], width=3
        )

        # Subtitulo
        self.subtitle = self.canvas.create_text(
            self.width // 2, logo_y + 50,
            text="",
            font=('Segoe UI', 12),
            fill=self.COLORS['gray_light']
        )

    def _crear_barra_progreso(self):
        """Crea la barra de progreso."""
        bar_width = 350
        bar_height = 4
        self.bar_x1 = (self.width - bar_width) // 2
        self.bar_y1 = self.height - 60
        self.bar_width = bar_width
        self.bar_height = bar_height

        # Fondo de la barra
        self.canvas.create_rectangle(
            self.bar_x1, self.bar_y1,
            self.bar_x1 + bar_width, self.bar_y1 + bar_height,
            fill=self.COLORS['gray_dark'], outline=''
        )

        # Barra de progreso
        self.progress_bar = self.canvas.create_rectangle(
            self.bar_x1, self.bar_y1,
            self.bar_x1, self.bar_y1 + bar_height,
            fill=self.COLORS['primary'], outline=''
        )

        # Brillo
        self.progress_glow = self.canvas.create_rectangle(
            self.bar_x1, self.bar_y1 - 1,
            self.bar_x1, self.bar_y1 + bar_height + 1,
            fill=self.COLORS['secondary'], outline=''
        )

    def _crear_texto_carga(self):
        """Crea textos de estado."""
        self.loading_text = self.canvas.create_text(
            self.width // 2, self.height - 35,
            text="Iniciando...",
            font=('Segoe UI', 10),
            fill=self.COLORS['gray_light']
        )

        self.percent_text = self.canvas.create_text(
            self.bar_x1 + self.bar_width + 15, self.bar_y1 + 2,
            text="0%",
            font=('Segoe UI', 9),
            fill=self.COLORS['primary'],
            anchor='w'
        )

        # Copyright
        self.canvas.create_text(
            self.width // 2, self.height - 12,
            text="2024-2026 ANgesLAB Solutions | v1.0",
            font=('Segoe UI', 8),
            fill=self.COLORS['gray_dark']
        )

    def _animar_zoom(self, elapsed):
        """Anima el efecto de zoom en la imagen."""
        if not self.image_frames or not self.lab_image_id:
            return

        # Calcular frame actual basado en el tiempo
        progress = min(1.0, elapsed / self.duration)
        frame_idx = int(progress * (len(self.image_frames) - 1))
        frame_idx = min(frame_idx, len(self.image_frames) - 1)

        if frame_idx != self.current_frame:
            self.current_frame = frame_idx
            self.canvas.itemconfig(self.lab_image_id, image=self.image_frames[frame_idx])

    def _animar_logo(self, elapsed):
        """Anima la aparicion del logo."""
        logo_text = "ANgesLAB"
        subtitle_text = "Sistema de Laboratorio Clinico"

        # Logo aparece despues de 800ms
        if elapsed > 800:
            progress = min(1.0, (elapsed - 800) / 600)
            chars = int(len(logo_text) * progress)
            self.canvas.itemconfig(self.logo_text, text=logo_text[:chars])

            # Linea se expande
            line_w = int(120 * progress)
            cx = self.width // 2
            logo_y = self.image_height + 50
            self.canvas.coords(self.logo_line, cx - line_w, logo_y + 30, cx + line_w, logo_y + 30)

        # Subtitulo despues de 1400ms
        if elapsed > 1400:
            progress = min(1.0, (elapsed - 1400) / 500)
            chars = int(len(subtitle_text) * progress)
            self.canvas.itemconfig(self.subtitle, text=subtitle_text[:chars])

    def _animar_progreso(self, elapsed):
        """Anima la barra de progreso."""
        progress = min(1.0, elapsed / self.duration)
        bar_end = self.bar_x1 + int(self.bar_width * progress)

        self.canvas.coords(
            self.progress_bar,
            self.bar_x1, self.bar_y1,
            bar_end, self.bar_y1 + self.bar_height
        )

        # Glow que se mueve
        glow_pos = self.bar_x1 + int(self.bar_width * progress * (0.5 + 0.5 * math.sin(elapsed / 80)))
        glow_w = 40
        self.canvas.coords(
            self.progress_glow,
            max(self.bar_x1, glow_pos - glow_w // 2), self.bar_y1 - 1,
            min(bar_end, glow_pos + glow_w // 2), self.bar_y1 + self.bar_height + 1
        )

        # Porcentaje
        self.canvas.itemconfig(self.percent_text, text=f"{int(progress * 100)}%")

        # Texto de estado
        if progress < 0.25:
            text = "Inicializando componentes..."
        elif progress < 0.50:
            text = "Cargando modulos..."
        elif progress < 0.75:
            text = "Preparando interfaz..."
        elif progress < 0.95:
            text = "Conectando base de datos..."
        else:
            text = "Listo!"
        self.canvas.itemconfig(self.loading_text, text=text)

    def _animation_loop(self, start_time):
        """Loop principal de animacion."""
        elapsed = int((time.time() - start_time) * 1000)

        if elapsed < self.duration:
            self._animar_zoom(elapsed)
            self._animar_logo(elapsed)
            self._animar_progreso(elapsed)
            self.root.after(16, lambda: self._animation_loop(start_time))
        else:
            self._fade_out()

    def _fade_out(self):
        """Efecto de desvanecimiento."""
        try:
            for alpha in [0.8, 0.6, 0.4, 0.2, 0.0]:
                self.root.attributes('-alpha', alpha)
                self.root.update()
                time.sleep(0.03)
        except:
            pass
        finally:
            self.root.destroy()

    def run(self):
        """Ejecuta el splash screen."""
        start_time = time.time()
        self._animation_loop(start_time)
        self.root.mainloop()


class SplashScreenSimple:
    """Version simplificada del splash."""

    COLORS = {
        'bg': '#0f172a',
        'primary': '#0891b2',
        'white': '#ffffff',
        'gray': '#94a3b8',
    }

    def __init__(self, duration=2500):
        self.duration = duration
        self.root = tk.Tk()
        self.root.withdraw()

        self.width = 500
        self.height = 350

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = (screen_h - self.height) // 2

        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg=self.COLORS['bg'])

        frame = tk.Frame(self.root, bg=self.COLORS['bg'])
        frame.pack(expand=True, fill='both', padx=40, pady=40)

        tk.Label(frame, text="ANgesLAB", font=('Segoe UI', 36, 'bold'),
                bg=self.COLORS['bg'], fg=self.COLORS['white']).pack(pady=(40, 10))

        tk.Label(frame, text="Sistema de Laboratorio Clinico", font=('Segoe UI', 12),
                bg=self.COLORS['bg'], fg=self.COLORS['gray']).pack(pady=(5, 30))

        self.progress_frame = tk.Frame(frame, bg=self.COLORS['gray'], height=4)
        self.progress_frame.pack(fill='x', pady=10)
        self.progress_frame.pack_propagate(False)

        self.progress_bar = tk.Frame(self.progress_frame, bg=self.COLORS['primary'], height=4)
        self.progress_bar.place(x=0, y=0, relheight=1.0, width=0)

        self.loading_label = tk.Label(frame, text="Cargando...", font=('Segoe UI', 9),
                                      bg=self.COLORS['bg'], fg=self.COLORS['gray'])
        self.loading_label.pack()

        self.root.deiconify()
        self.root.update()

    def run(self):
        start = time.time()
        bar_width = self.progress_frame.winfo_width()

        while True:
            elapsed = (time.time() - start) * 1000
            if elapsed >= self.duration:
                break

            progress = elapsed / self.duration
            self.progress_bar.place(width=int(bar_width * progress))

            if progress < 0.5:
                self.loading_label.config(text="Cargando modulos...")
            elif progress < 0.8:
                self.loading_label.config(text="Preparando interfaz...")
            else:
                self.loading_label.config(text="Listo!")

            self.root.update()
            time.sleep(0.016)

        self.root.destroy()


def mostrar_splash(duracion=4000, simple=False):
    """Funcion helper para mostrar el splash screen."""
    try:
        if simple:
            splash = SplashScreenSimple(duracion)
        else:
            splash = SplashScreen(duracion)
        splash.run()
    except Exception as e:
        print(f"Error en splash screen: {e}")


if __name__ == "__main__":
    mostrar_splash(duracion=4500)
    print("Splash completado!")

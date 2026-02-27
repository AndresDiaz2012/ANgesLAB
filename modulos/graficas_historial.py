# -*- coding: utf-8 -*-
"""
graficas_historial.py - Generacion de graficas de evolucion de parametros clinicos.

Usa matplotlib embebido en tkinter via FigureCanvasTkAgg.
Las graficas muestran la evolucion temporal de cada parametro con:
- Linea azul de valores del paciente
- Banda verde semitransparente para el rango de referencia
- Puntos rojos para valores fuera de rango
"""

import io
import re
from datetime import datetime

# Matplotlib con guard - si no esta instalado, se deshabilita la funcionalidad
try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    import matplotlib.ticker as ticker
    MATPLOTLIB_DISPONIBLE = True
except ImportError:
    MATPLOTLIB_DISPONIBLE = False

# Numpy para calculos estadisticos en graficas (opcional)
try:
    import numpy as np
    NUMPY_DISPONIBLE = True
except ImportError:
    NUMPY_DISPONIBLE = False


# ============================================================
# PALETA DE COLORES CONSISTENTE CON EL SISTEMA
# ============================================================

COLOR_LINEA = '#1565c0'          # Azul principal - valores del paciente
COLOR_PUNTO_NORMAL = '#1565c0'   # Azul - puntos dentro del rango
COLOR_PUNTO_ALTO = '#c62828'     # Rojo - puntos sobre el rango (alto)
COLOR_PUNTO_BAJO = '#1976d2'     # Azul oscuro - puntos bajo el rango
COLOR_RANGO_BAND = '#a5d6a7'     # Verde claro - banda de referencia
COLOR_RANGO_LINE = '#4caf50'     # Verde - bordes de la banda de referencia
COLOR_FONDO = '#ffffff'          # Blanco - fondo del grafico
COLOR_GRILLA = '#e0e0e0'         # Gris muy claro - grilla
COLOR_TITULO = '#1a237e'         # Azul indigo - titulos
COLOR_TEXTO = '#37474f'          # Gris oscuro - texto ejes


def _parsear_rango_referencia(valor_referencia_str):
    """
    Parsea una cadena de rango de referencia y retorna (min_val, max_val).
    Soporta formatos: "min - max", "< val", "> val", "<= val", ">= val",
    "hasta val", "minimo val".
    Retorna (None, None) si no se puede parsear.
    """
    if not valor_referencia_str:
        return None, None

    ref = str(valor_referencia_str).strip()

    # Formato "min - max" o "min-max"
    m = re.match(r'^([\d,.]+)\s*[-–]\s*([\d,.]+)', ref)
    if m:
        try:
            vmin = float(m.group(1).replace(',', '.'))
            vmax = float(m.group(2).replace(',', '.'))
            return vmin, vmax
        except ValueError:
            pass

    # Formato "< valor" o "<= valor"
    m = re.match(r'^<=?\s*([\d,.]+)', ref)
    if m:
        try:
            return 0, float(m.group(1).replace(',', '.'))
        except ValueError:
            pass

    # Formato "> valor" o ">= valor"
    m = re.match(r'^>=?\s*([\d,.]+)', ref)
    if m:
        try:
            return float(m.group(1).replace(',', '.')), None
        except ValueError:
            pass

    return None, None


def _parsear_valor_numerico(valor_str):
    """Intenta convertir un valor a float. Retorna None si no es numerico."""
    if valor_str is None:
        return None
    try:
        return float(str(valor_str).replace(',', '.').strip())
    except (ValueError, TypeError):
        return None


def _parsear_fecha(fecha_val):
    """Convierte varios formatos de fecha a datetime. Retorna None si falla."""
    if fecha_val is None:
        return None
    if isinstance(fecha_val, datetime):
        return fecha_val
    if hasattr(fecha_val, 'year'):  # date object
        return datetime(fecha_val.year, fecha_val.month, fecha_val.day)
    fecha_str = str(fecha_val).strip()
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(fecha_str, fmt)
        except (ValueError, TypeError):
            continue
    # Intentar truncando la cadena para formatos parciales (ej: '2026-02-24 10:30:00.000')
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(fecha_str[:19], fmt)
        except (ValueError, TypeError):
            continue
    return None


# ============================================================
# CLASE PRINCIPAL
# ============================================================

class GraficasHistorial:
    """
    Generador de graficas de evolucion de parametros clinicos para historial.
    Requiere matplotlib instalado (MATPLOTLIB_DISPONIBLE = True).
    """

    # Estilo matplotlib global aplicado una vez
    _estilo_aplicado = False

    def __init__(self):
        if MATPLOTLIB_DISPONIBLE and not GraficasHistorial._estilo_aplicado:
            try:
                plt.rcParams.update({
                    'font.family': 'Segoe UI',
                    'font.size': 9,
                    'axes.titlesize': 10,
                    'axes.titleweight': 'bold',
                    'axes.labelsize': 9,
                    'axes.spines.top': False,
                    'axes.spines.right': False,
                    'axes.grid': True,
                    'grid.alpha': 0.4,
                    'grid.linestyle': '--',
                    'figure.facecolor': COLOR_FONDO,
                    'axes.facecolor': COLOR_FONDO,
                })
                GraficasHistorial._estilo_aplicado = True
            except Exception:
                pass  # No critico si el estilo no aplica

    # ----------------------------------------------------------
    # GRAFICA INDIVIDUAL DE UN PARAMETRO
    # ----------------------------------------------------------

    def generar_grafica_parametro(self, valores_lista, nombre_param, unidad='',
                                   valor_referencia_str=None, titulo_superior=None):
        """
        Genera una Figure matplotlib para un parametro con su evolucion temporal.

        Args:
            valores_lista: List[dict] con keys:
                           'fecha' (str/datetime), 'valor' (str/num),
                           'fuera_rango' (str: 'alto'/'bajo'/None),
                           'solicitud_num' (str, opcional)
            nombre_param: Nombre del parametro (str)
            unidad: Simbolo de unidad (str, ej: 'mg/dL')
            valor_referencia_str: Rango de referencia como texto (str)
            titulo_superior: Titulo extra sobre la grafica (str, opcional)

        Returns:
            matplotlib.figure.Figure o None si matplotlib no disponible
        """
        if not MATPLOTLIB_DISPONIBLE:
            return None

        # Filtrar solo valores numericos con fecha valida
        puntos = []
        for v in valores_lista:
            fecha = _parsear_fecha(v.get('fecha'))
            valor = _parsear_valor_numerico(v.get('valor'))
            if fecha is not None and valor is not None:
                puntos.append({
                    'fecha': fecha,
                    'valor': valor,
                    'fuera_rango': v.get('fuera_rango') or v.get('FueraDeRango') or None,
                    'solicitud': str(v.get('solicitud_num', '')),
                })
        puntos.sort(key=lambda x: x['fecha'])

        fig = Figure(figsize=(7, 3.2), dpi=96, facecolor=COLOR_FONDO)
        ax = fig.add_subplot(111)

        if not puntos:
            ax.text(0.5, 0.5, 'Sin datos numéricos suficientes\npara graficar',
                    ha='center', va='center', fontsize=10, color='#9e9e9e',
                    transform=ax.transAxes)
            ax.set_title(nombre_param, color=COLOR_TITULO, pad=8)
            fig.tight_layout()
            return fig

        fechas = [p['fecha'] for p in puntos]
        valores = [p['valor'] for p in puntos]

        # Banda de referencia
        ref_min, ref_max = _parsear_rango_referencia(valor_referencia_str)
        if ref_min is not None or ref_max is not None:
            y_band_min = ref_min if ref_min is not None else min(valores) * 0.8
            y_band_max = ref_max if ref_max is not None else max(valores) * 1.2
            ax.axhspan(y_band_min, y_band_max,
                       facecolor=COLOR_RANGO_BAND, alpha=0.35, label='Rango ref.',
                       zorder=1)
            if ref_min is not None:
                ax.axhline(y=ref_min, color=COLOR_RANGO_LINE, linewidth=0.8,
                           linestyle='--', alpha=0.7, zorder=2)
            if ref_max is not None:
                ax.axhline(y=ref_max, color=COLOR_RANGO_LINE, linewidth=0.8,
                           linestyle='--', alpha=0.7, zorder=2)

        # Linea de evolucion
        ax.plot(fechas, valores, color=COLOR_LINEA, linewidth=2,
                marker='o', markersize=5, zorder=4, label=nombre_param)

        # Puntos coloreados segun estado
        for p in puntos:
            fr = str(p['fuera_rango']).lower() if p['fuera_rango'] else ''
            if 'alto' in fr or 'critico' in fr:
                color_punto = COLOR_PUNTO_ALTO
                marker_edge = '#b71c1c'
            elif 'bajo' in fr:
                color_punto = COLOR_PUNTO_BAJO
                marker_edge = '#0d47a1'
            else:
                color_punto = COLOR_PUNTO_NORMAL
                marker_edge = '#0d47a1'
            ax.plot(p['fecha'], p['valor'], 'o',
                    color=color_punto, markeredgecolor=marker_edge,
                    markersize=7, zorder=5)

        # Formato del eje X segun rango de fechas
        if len(fechas) > 1:
            rango_dias = (max(fechas) - min(fechas)).days
            if rango_dias <= 30:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, rango_dias // 6)))
            elif rango_dias <= 365:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %Y'))
                ax.xaxis.set_major_locator(mdates.MonthLocator())
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%Y'))
                ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
        else:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'))

        fig.autofmt_xdate(rotation=40, ha='right')

        # Etiqueta eje Y
        ylabel = nombre_param
        if unidad:
            ylabel = f'{nombre_param} ({unidad})'
        ax.set_ylabel(ylabel, color=COLOR_TEXTO, fontsize=8)

        # Titulo
        titulo = nombre_param
        if titulo_superior:
            titulo = f'{titulo_superior} — {nombre_param}'
        ax.set_title(titulo, color=COLOR_TITULO, pad=8, fontsize=10, fontweight='bold')

        # Leyenda compacta si hay banda de referencia
        if ref_min is not None or ref_max is not None:
            ref_label = 'Ref: '
            if ref_min is not None and ref_max is not None:
                ref_label += f'{ref_min} - {ref_max}'
            elif ref_max is not None:
                ref_label += f'< {ref_max}'
            elif ref_min is not None:
                ref_label += f'> {ref_min}'
            if unidad:
                ref_label += f' {unidad}'
            ax.text(0.02, 0.97, ref_label, transform=ax.transAxes,
                    fontsize=7.5, color='#2e7d32', va='top', ha='left',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white',
                              edgecolor='#4caf50', alpha=0.8))

        ax.tick_params(colors=COLOR_TEXTO, labelsize=8)
        ax.grid(True, alpha=0.3, linestyle='--', color=COLOR_GRILLA)

        fig.tight_layout(pad=1.2)
        return fig

    # ----------------------------------------------------------
    # PANEL MULTIPANEL (varios parametros de una prueba)
    # ----------------------------------------------------------

    def generar_panel_prueba(self, datos_evolucion_completa, titulo_prueba=''):
        """
        Genera una Figure con subplots para cada parametro numerico de la prueba.

        Args:
            datos_evolucion_completa: dict devuelto por
                GestorHistorialClinico.obtener_evolucion_completa_prueba()
            titulo_prueba: Nombre de la prueba para el titulo general

        Returns:
            matplotlib.figure.Figure o None
        """
        if not MATPLOTLIB_DISPONIBLE:
            return None

        parametros = datos_evolucion_completa.get('parametros', {})
        mediciones = datos_evolucion_completa.get('mediciones', [])

        if not parametros or not mediciones:
            return None

        # Filtrar solo parametros con valores numericos
        params_numericos = []
        for param_id, info in parametros.items():
            valores = info.get('valores', [])
            tiene_numerico = any(
                _parsear_valor_numerico(v.get('valor')) is not None
                for v in valores
            )
            if tiene_numerico:
                params_numericos.append((param_id, info))

        if not params_numericos:
            return None

        n = len(params_numericos)
        ncols = 2 if n > 1 else 1
        nrows = (n + ncols - 1) // ncols

        alto_por_fila = 2.8
        fig = Figure(
            figsize=(12, max(3, nrows * alto_por_fila + 0.8)),
            dpi=96,
            facecolor=COLOR_FONDO
        )

        if titulo_prueba:
            fig.suptitle(f'Evolución: {titulo_prueba}',
                         fontsize=12, fontweight='bold',
                         color=COLOR_TITULO, y=0.98)

        for idx, (param_id, info) in enumerate(params_numericos):
            ax = fig.add_subplot(nrows, ncols, idx + 1)

            nombre = info.get('nombre', f'Param {param_id}')
            unidad = info.get('unidad', '')
            valores_lista = info.get('valores', [])

            # Reconstruir lista con fechas de mediciones
            puntos_graf = []
            for v in valores_lista:
                fecha = _parsear_fecha(v.get('fecha'))
                valor = _parsear_valor_numerico(v.get('valor'))
                if fecha is not None and valor is not None:
                    puntos_graf.append({
                        'fecha': fecha,
                        'valor': valor,
                        'fuera_rango': v.get('fuera_rango') or v.get('FueraDeRango'),
                    })

            puntos_graf.sort(key=lambda x: x['fecha'])

            if not puntos_graf:
                ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center',
                        fontsize=9, color='#9e9e9e', transform=ax.transAxes)
                ax.set_title(nombre, color=COLOR_TITULO, fontsize=9)
                continue

            fechas = [p['fecha'] for p in puntos_graf]
            valores = [p['valor'] for p in puntos_graf]

            # Banda referencia
            ref_str = info.get('valor_referencia') or (
                valores_lista[0].get('valor_referencia') if valores_lista else None
            )
            ref_min, ref_max = _parsear_rango_referencia(ref_str)

            if ref_min is not None or ref_max is not None:
                y_low = ref_min if ref_min is not None else min(valores) * 0.8
                y_high = ref_max if ref_max is not None else max(valores) * 1.2
                ax.axhspan(y_low, y_high,
                           facecolor=COLOR_RANGO_BAND, alpha=0.3, zorder=1)
                if ref_min is not None:
                    ax.axhline(ref_min, color=COLOR_RANGO_LINE,
                               linewidth=0.7, linestyle='--', alpha=0.6, zorder=2)
                if ref_max is not None:
                    ax.axhline(ref_max, color=COLOR_RANGO_LINE,
                               linewidth=0.7, linestyle='--', alpha=0.6, zorder=2)

            ax.plot(fechas, valores, color=COLOR_LINEA,
                    linewidth=1.8, zorder=4)

            for p in puntos_graf:
                fr = str(p['fuera_rango']).lower() if p['fuera_rango'] else ''
                cp = COLOR_PUNTO_ALTO if ('alto' in fr or 'critico' in fr) else (
                    COLOR_PUNTO_BAJO if 'bajo' in fr else COLOR_PUNTO_NORMAL
                )
                ax.plot(p['fecha'], p['valor'], 'o',
                        color=cp, markersize=5, zorder=5)

            # Formato fechas compacto
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%y'))
            ax.xaxis.set_major_locator(
                ticker.MaxNLocator(nbins=5, integer=True)
            )
            for tick_label in ax.get_xticklabels():
                tick_label.set_rotation(35)
                tick_label.set_ha('right')

            titulo_ax = f'{nombre}'
            if unidad:
                titulo_ax += f' ({unidad})'
            ax.set_title(titulo_ax, color=COLOR_TITULO,
                         fontsize=8.5, fontweight='bold', pad=4)
            ax.tick_params(colors=COLOR_TEXTO, labelsize=7)
            ax.grid(True, alpha=0.3, linestyle='--', color=COLOR_GRILLA)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        fig.tight_layout(rect=[0, 0, 1, 0.96] if titulo_prueba else [0, 0, 1, 1],
                         pad=1.5, h_pad=2.0, w_pad=1.5)
        return fig

    # ----------------------------------------------------------
    # INCRUSTAR EN FRAME TKINTER
    # ----------------------------------------------------------

    def incrustar_en_frame(self, parent_frame, figura, mostrar_toolbar=False):
        """
        Incrusta una Figure matplotlib en un frame tkinter.

        Args:
            parent_frame: Frame tkinter contenedor
            figura: matplotlib.figure.Figure
            mostrar_toolbar: bool - mostrar barra de navegacion

        Returns:
            tuple (canvas_widget, canvas_obj) o (None, None) si falla
        """
        if not MATPLOTLIB_DISPONIBLE or figura is None:
            return None, None

        try:
            import tkinter as tk
            from tkinter import ttk

            canvas = FigureCanvasTkAgg(figura, master=parent_frame)
            canvas.draw()
            widget = canvas.get_tk_widget()
            widget.pack(fill='both', expand=True)

            if mostrar_toolbar:
                toolbar_frame = tk.Frame(parent_frame, bg='white')
                toolbar_frame.pack(fill='x')
                NavigationToolbar2Tk(canvas, toolbar_frame)

            return widget, canvas
        except Exception as e:
            print(f"[GraficasHistorial] Error al incrustar grafica: {e}")
            return None, None

    # ----------------------------------------------------------
    # EXPORTAR FIGURA COMO BYTES (para PDF reportlab)
    # ----------------------------------------------------------

    def figura_a_imagen_bytes(self, figura, formato='PNG', dpi=150):
        """
        Convierte una Figure matplotlib a bytes para embeber en PDF reportlab.

        Args:
            figura: matplotlib.figure.Figure
            formato: 'PNG' o 'JPEG'
            dpi: resolucion de exportacion

        Returns:
            bytes o None si falla
        """
        if not MATPLOTLIB_DISPONIBLE or figura is None:
            return None
        try:
            buf = io.BytesIO()
            figura.savefig(buf, format=formato.lower(), dpi=dpi,
                           bbox_inches='tight', facecolor=COLOR_FONDO)
            buf.seek(0)
            return buf.read()
        except Exception as e:
            print(f"[GraficasHistorial] Error al exportar figura: {e}")
            return None

    # ----------------------------------------------------------
    # EXPORTAR FIGURA COMO ARCHIVO PNG
    # ----------------------------------------------------------

    def exportar_png(self, figura, ruta_archivo):
        """
        Guarda la figura como PNG en disco.

        Returns:
            bool: True si exitoso
        """
        if not MATPLOTLIB_DISPONIBLE or figura is None:
            return False
        try:
            figura.savefig(ruta_archivo, format='png', dpi=150,
                           bbox_inches='tight', facecolor=COLOR_FONDO)
            return True
        except Exception as e:
            print(f"[GraficasHistorial] Error al exportar PNG: {e}")
            return False


# ============================================================
# FUNCION DE CONVENIENCIA
# ============================================================

def crear_gestor_graficas():
    """Crea una instancia de GraficasHistorial si matplotlib esta disponible."""
    if not MATPLOTLIB_DISPONIBLE:
        return None
    return GraficasHistorial()


def cerrar_figura(figura):
    """Cierra una figura matplotlib para liberar memoria."""
    if MATPLOTLIB_DISPONIBLE and figura is not None:
        try:
            plt.close(figura)
        except Exception:
            pass

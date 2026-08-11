# -*- coding: utf-8 -*-
"""
================================================================================
GESTION DE IMPRESORAS POR ROL - ANgesLAB
================================================================================
El laboratorio trabaja con varias impresoras a la vez (una laser para informes,
una fiscal o de matriz para facturas, una termica para recibos y otra de
etiquetas). Este modulo asigna una impresora a cada rol y envia cada documento
a la que le corresponde.

Roles definidos:
    resultados   - informes de resultados, hojas de trabajo
    facturacion  - facturas, notas de credito/debito
    recibos      - recibos de caja (ticket 80 mm)
    etiquetas    - etiquetas de tubos (rollo 80 mm)

Las cotizaciones son un caso aparte: se imprimen en hoja completa igual que un
informe, asi que el usuario elige si salen por la impresora de facturacion (por
defecto) o por la de resultados. Ver ROLES_COTIZACION mas abajo.

Es perfectamente valido asignar la misma impresora fisica a varios roles: cada
trabajo se envia igual, de forma independiente.

Como se imprime (y por que no con SetDefaultPrinter)
----------------------------------------------------
Cambiar la impresora predeterminada del sistema para imprimir y restaurarla
despues es una carrera: ShellExecute('print') es asincrono, asi que si se
imprime un recibo y una etiqueta casi a la vez, el segundo trabajo puede salir
por la impresora del primero. Ademas, si el PDF esta asociado a Microsoft Edge
(lo habitual en Windows 11) los verbos 'print' y 'printto' ni siquiera estan
registrados y no se imprime nada.

Por eso se intenta en este orden:

  1. GDI directo: se rasteriza el PDF con PyMuPDF y se envia pagina por pagina
     al contexto de dispositivo de la impresora indicada. Funciona con
     cualquier impresora instalada, sin dialogos y sin tocar nada global.
  2. Verbo 'printto' del shell, que recibe el nombre de la impresora.
  3. Impresora predeterminada temporal, serializado con un lock (ultimo
     recurso, solo si el sistema no ofrece nada mejor).

Si todo falla, el llamador abre el PDF en pantalla para que no se pierda el
documento.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import os
import logging
import threading
import time

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.impresoras')
except Exception:
    _log = logging.getLogger('angeslab.impresoras')
    _log.addHandler(logging.NullHandler())


# ══════════════════════════════════════════════════════════════════════════
#  Definicion de roles
# ══════════════════════════════════════════════════════════════════════════
ROLES = {
    'resultados': {
        'etiqueta': 'Resultados e informes',
        'ayuda': 'Informes, hojas de trabajo e interpretaciones (y cotizaciones '
                 'si así se configura)',
        'columna': 'ImpresoraResultados',
        'columna_directo': 'ImpresoraResultadosDirecto',
        'directo_defecto': False,
    },
    'facturacion': {
        'etiqueta': 'Facturación',
        'ayuda': 'Facturas y notas de crédito/débito',
        'columna': 'ImpresoraFacturacion',
        'columna_directo': 'ImpresoraFacturacionDirecto',
        'directo_defecto': False,
    },
    'recibos': {
        'etiqueta': 'Recibos de caja',
        'ayuda': 'Ticket de 80 mm que se entrega al paciente',
        'columna': 'ImpresoraRecibos',
        'columna_directo': 'ImpresoraRecibosDirecto',
        'directo_defecto': False,
    },
    'etiquetas': {
        'etiqueta': 'Etiquetas de muestras',
        'ayuda': 'Rollo de 80 mm para identificar los tubos',
        'columna': 'ImpresoraEtiquetas',
        'columna_directo': 'ImpresoraEtiquetasDirecto',
        'directo_defecto': False,
    },
}

# Orden estable para la interfaz de configuración
ORDEN_ROLES = ('resultados', 'facturacion', 'recibos', 'etiquetas')

# Nombres alternativos que usan las llamadas existentes del sistema
ALIAS_ROLES = {
    'informes': 'resultados',
    'resultado': 'resultados',
    'hoja_trabajo': 'resultados',
    'ia': 'resultados',
    'cotizacion': 'facturacion',
    'cotizaciones': 'facturacion',
    'presupuesto': 'facturacion',
    'presupuestos': 'facturacion',
    'factura': 'facturacion',
    'nota_credito': 'facturacion',
    'nota_debito': 'facturacion',
    'recibo': 'recibos',
    'etiqueta': 'etiquetas',
}

# ── Cotizaciones: rol configurable ─────────────────────────────────────────
# La cotización es un documento comercial, pero se imprime en hoja completa
# igual que un informe. Muchos laboratorios tienen la impresora de facturación
# reservada para papel fiscal o matriz de puntos, así que se permite mandar
# las cotizaciones por la impresora de resultados.
ALIAS_COTIZACION = ('cotizacion', 'cotizaciones', 'presupuesto', 'presupuestos')
ROLES_COTIZACION = ('facturacion', 'resultados')
ROL_COTIZACIONES_DEFECTO = 'facturacion'
COLUMNA_ROL_COTIZACIONES = 'RolCotizaciones'


def es_alias_cotizacion(rol):
    """True si el nombre corresponde a una cotización/presupuesto."""
    return str(rol or '').strip().lower() in ALIAS_COTIZACION


def normalizar_rol(rol):
    """Traduce un alias al nombre canónico del rol. None si no se reconoce."""
    if not rol:
        return None
    r = str(rol).strip().lower()
    r = ALIAS_ROLES.get(r, r)
    return r if r in ROLES else None


# ══════════════════════════════════════════════════════════════════════════
#  Impresoras instaladas en el sistema
# ══════════════════════════════════════════════════════════════════════════
def listar_impresoras():
    """
    Devuelve (lista_de_nombres, impresora_predeterminada).

    Nunca lanza excepción: si no se puede consultar el sistema devuelve
    ([], '').
    """
    nombres, predeterminada = [], ''
    try:
        import win32print
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        nombres = [p['pPrinterName'] for p in win32print.EnumPrinters(flags, None, 2)]
        try:
            predeterminada = win32print.GetDefaultPrinter()
        except Exception:
            pass
    except Exception:
        try:
            import subprocess
            r = subprocess.run(['wmic', 'printer', 'get', 'name'],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                nombres = [l.strip() for l in r.stdout.strip().splitlines()[1:]
                           if l.strip()]
        except Exception:
            pass
    return nombres, predeterminada


# ══════════════════════════════════════════════════════════════════════════
#  Envío del documento a una impresora concreta
# ══════════════════════════════════════════════════════════════════════════
# Serializa el respaldo que cambia la impresora predeterminada
_lock_impresion = threading.Lock()

# Margen para que el visor de PDF lea la predeterminada antes de restaurarla
_ESPERA_RESTAURAR = 4.0


# Resolución máxima a la que se rasteriza; por encima el consumo de memoria
# crece sin mejora visible en papel
_DPI_MAXIMO = 300


def _imprimir_gdi(ruta, impresora, copias=1):
    """
    Rasteriza el PDF y lo envía al contexto de dispositivo de la impresora.

    Es el método preferido: no usa verbos del shell ni la impresora
    predeterminada, así que cada rol imprime en la suya sin interferencias.

    Returns True si el documento se envió al spooler.
    """
    try:
        import fitz                      # PyMuPDF
        import win32ui
        import win32con
        from PIL import Image, ImageWin
    except ImportError as e:
        _log.debug("Impresión GDI no disponible: %s", e)
        return False

    doc = None
    try:
        doc = fitz.open(ruta)
        if doc.page_count == 0:
            return False

        for _ in range(max(1, int(copias or 1))):
            hdc = win32ui.CreateDC()
            hdc.CreatePrinterDC(impresora)
            try:
                # Área imprimible y resolución reales de la impresora
                ancho_disp = hdc.GetDeviceCaps(win32con.HORZRES)
                alto_disp = hdc.GetDeviceCaps(win32con.VERTRES)
                dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX) or 203
                dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY) or 203
                escala = min(_DPI_MAXIMO / dpi_x, _DPI_MAXIMO / dpi_y, 1.0)

                hdc.StartDoc(os.path.basename(ruta))
                try:
                    for pagina in doc:
                        hdc.StartPage()
                        matriz = fitz.Matrix(dpi_x / 72.0 * escala,
                                             dpi_y / 72.0 * escala)
                        pix = pagina.get_pixmap(matrix=matriz, alpha=False)
                        img = Image.frombytes('RGB', (pix.width, pix.height),
                                              pix.samples)

                        # Tamaño real de la página en píxeles de la impresora
                        ancho_real = pagina.rect.width / 72.0 * dpi_x
                        alto_real = pagina.rect.height / 72.0 * dpi_y
                        # Solo se reduce si no cabe: nunca se amplía, para que
                        # un ticket de 80 mm no salga estirado en una hoja A4
                        factor = min(ancho_disp / ancho_real,
                                     alto_disp / alto_real, 1.0)
                        w_dest = max(1, int(ancho_real * factor))
                        h_dest = max(1, int(alto_real * factor))
                        x = max(0, (ancho_disp - w_dest) // 2)  # centrado
                        ImageWin.Dib(img).draw(hdc.GetHandleOutput(),
                                               (x, 0, x + w_dest, h_dest))
                        hdc.EndPage()
                    hdc.EndDoc()
                except Exception:
                    try:
                        hdc.AbortDoc()
                    except Exception:
                        pass
                    raise
            finally:
                try:
                    hdc.DeleteDC()
                except Exception:
                    pass
        return True

    except Exception as e:
        _log.warning("Impresión GDI falló en '%s': %s", impresora, e)
        return False
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def _imprimir_printto(ruta, impresora):
    """Imprime con el verbo 'printto' (no toca la impresora predeterminada)."""
    try:
        import win32api
        win32api.ShellExecute(0, 'printto', ruta, f'"{impresora}"', '.', 0)
        return True
    except Exception as e:
        _log.debug("printto falló en '%s': %s", impresora, e)
        return False


def _imprimir_predeterminada(ruta, impresora):
    """
    Respaldo: fija la impresora como predeterminada, imprime y la restaura.

    Se ejecuta en un hilo aparte y bajo lock para que dos trabajos
    simultáneos no se pisen la configuración global.
    """
    def _tarea():
        with _lock_impresion:
            anterior = None
            try:
                import win32print
                import win32api
                try:
                    anterior = win32print.GetDefaultPrinter()
                except Exception:
                    anterior = None
                win32print.SetDefaultPrinter(impresora)
                win32api.ShellExecute(0, 'print', ruta, None, '.', 0)
                # El visor necesita leer la predeterminada antes de restaurarla
                time.sleep(_ESPERA_RESTAURAR)
            except Exception as e:
                _log.error("No se pudo imprimir en '%s': %s", impresora, e)
            finally:
                if anterior:
                    try:
                        import win32print
                        win32print.SetDefaultPrinter(anterior)
                    except Exception:
                        pass

    threading.Thread(target=_tarea, name='ANgesLAB-Impresion',
                     daemon=True).start()
    return True


def enviar_a_impresora(ruta, impresora, copias=1):
    """
    Envía un PDF a una impresora concreta.

    Returns True si el trabajo se pudo encolar.
    """
    if not ruta or not os.path.exists(ruta):
        _log.error("Archivo inexistente: %s", ruta)
        return False
    if not impresora:
        return False

    copias = max(1, int(copias or 1))

    # 1) GDI directo: la vía fiable, sin diálogos ni estado global
    if _imprimir_gdi(ruta, impresora, copias):
        _log.info("Documento enviado a '%s' (GDI): %s", impresora,
                  os.path.basename(ruta))
        return True

    # 2) Verbo 'printto' del shell
    if all(_imprimir_printto(ruta, impresora) for _ in range(copias)):
        _log.info("Documento enviado a '%s' (printto): %s", impresora,
                  os.path.basename(ruta))
        return True

    # 3) Último recurso: impresora predeterminada temporal
    if _imprimir_predeterminada(ruta, impresora):
        _log.info("Documento enviado a '%s' (predeterminada): %s", impresora,
                  os.path.basename(ruta))
        return True

    return False


def abrir_documento(ruta):
    """Abre el PDF en el visor del sistema (vista previa / respaldo)."""
    try:
        os.startfile(ruta)
        return True
    except Exception:
        try:
            import webbrowser
            webbrowser.open(ruta)
            return True
        except Exception:
            return False


# ══════════════════════════════════════════════════════════════════════════
#  Gestor de asignaciones
# ══════════════════════════════════════════════════════════════════════════
class GestorImpresoras:
    """Lee y guarda qué impresora atiende cada rol."""

    def __init__(self, db):
        self.db = db
        self._cache = None
        self._rol_cotizaciones = ROL_COTIZACIONES_DEFECTO

    def invalidar_cache(self):
        self._cache = None

    def asignaciones(self, refrescar=False):
        """
        Devuelve {rol: {'impresora': str, 'directo': bool}} para los 4 roles.

        Un rol sin impresora asignada queda con cadena vacía.
        """
        if self._cache is not None and not refrescar:
            return self._cache

        config = {}
        try:
            config = self.db.query_one(
                "SELECT * FROM ConfiguracionLaboratorio") or {}
        except Exception as e:
            _log.warning("No se pudo leer la configuración de impresoras: %s", e)

        salida = {}
        for rol in ORDEN_ROLES:
            info = ROLES[rol]
            valor = config.get(info['columna'])
            directo = config.get(info['columna_directo'])
            salida[rol] = {
                'impresora': (valor or '').strip() if valor else '',
                'directo': info['directo_defecto'] if directo is None
                           else bool(directo),
            }

        # Destino elegido para las cotizaciones (facturación o resultados)
        elegido = (config.get(COLUMNA_ROL_COTIZACIONES) or '').strip().lower()
        self._rol_cotizaciones = (elegido if elegido in ROLES_COTIZACION
                                  else ROL_COTIZACIONES_DEFECTO)

        self._cache = salida
        return salida

    def rol_cotizaciones(self):
        """Rol por el que salen las cotizaciones: 'facturacion' o 'resultados'."""
        self.asignaciones()          # asegura que la configuración esté leída
        return self._rol_cotizaciones

    def _resolver_rol(self, rol):
        """
        Nombre canónico del rol, aplicando la preferencia de cotizaciones.

        Una cotización va al rol configurado; si ese rol no tiene impresora
        asignada se usa el otro, para que el documento salga igual en vez de
        quedarse sin destino.
        """
        if es_alias_cotizacion(rol):
            asig = self.asignaciones()
            preferido = self._rol_cotizaciones
            if asig.get(preferido, {}).get('impresora'):
                return preferido
            alterno = ('resultados' if preferido == 'facturacion'
                       else 'facturacion')
            if asig.get(alterno, {}).get('impresora'):
                _log.info("Cotización enviada al rol '%s': '%s' no tiene "
                          "impresora asignada", alterno, preferido)
                return alterno
            return preferido
        return normalizar_rol(rol)

    def impresora_de(self, rol):
        """Nombre de la impresora asignada al rol, o '' si no hay."""
        r = self._resolver_rol(rol)
        if not r:
            return ''
        return self.asignaciones().get(r, {}).get('impresora', '')

    def es_directo(self, rol):
        """True si el rol debe imprimir sin mostrar el diálogo."""
        r = self._resolver_rol(rol)
        if not r:
            return False
        asig = self.asignaciones().get(r, {})
        return bool(asig.get('directo')) and bool(asig.get('impresora'))

    def imprimir(self, ruta, rol, copias=1):
        """
        Envía el documento a la impresora del rol.

        Returns True si se encoló; False si el rol no tiene impresora
        asignada o el envío falló (el llamador decide el respaldo).
        """
        impresora = self.impresora_de(rol)
        if not impresora:
            return False
        return enviar_a_impresora(ruta, impresora, copias)

    def guardar(self, asignaciones, rol_cotizaciones=None):
        """
        Persiste las asignaciones.

        asignaciones: {rol: {'impresora': str, 'directo': bool}}
        Se permite repetir la misma impresora en varios roles.
        rol_cotizaciones: 'facturacion' o 'resultados'; None deja el actual.
        """
        campos = []
        for rol, datos in (asignaciones or {}).items():
            r = normalizar_rol(rol)
            if not r:
                continue
            info = ROLES[r]
            nombre = (datos.get('impresora') or '').strip()
            if nombre:
                campos.append(
                    f"[{info['columna']}] = '{nombre.replace(chr(39), chr(39)*2)}'")
            else:
                campos.append(f"[{info['columna']}] = NULL")
            campos.append(
                f"[{info['columna_directo']}] = "
                f"{'True' if datos.get('directo') else 'False'}")

        if rol_cotizaciones is not None:
            destino = str(rol_cotizaciones).strip().lower()
            if destino in ROLES_COTIZACION:
                campos.append(f"[{COLUMNA_ROL_COTIZACIONES}] = '{destino}'")

        if not campos:
            return False
        try:
            self.db.execute("UPDATE ConfiguracionLaboratorio SET "
                            + ', '.join(campos))
            self.invalidar_cache()
            return True
        except Exception as e:
            _log.error("No se pudieron guardar las impresoras: %s", e)
            return False


# ══════════════════════════════════════════════════════════════════════════
#  Atajo de alto nivel
# ══════════════════════════════════════════════════════════════════════════
def imprimir_documento(db, ruta, rol, copias=1, abrir_si_falla=True):
    """
    Imprime en la impresora del rol; si no hay ninguna asignada abre el PDF.

    Returns 'impreso', 'abierto' o 'error'.
    """
    if not ruta or not os.path.exists(ruta):
        return 'error'
    try:
        gestor = GestorImpresoras(db)
        if gestor.imprimir(ruta, rol, copias):
            return 'impreso'
    except Exception as e:
        _log.error("Error imprimiendo (%s): %s", rol, e)
    if abrir_si_falla and abrir_documento(ruta):
        return 'abierto'
    return 'error'


def crear_gestor_impresoras(db):
    """Factory del gestor de impresoras."""
    return GestorImpresoras(db)

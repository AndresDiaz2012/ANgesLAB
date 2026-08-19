# -*- coding: utf-8 -*-
"""
================================================================================
GESTION DE IMPRESORAS POR ROL - ANgesLAB
================================================================================
El laboratorio trabaja con varias impresoras a la vez (una laser para informes,
otra para cotizaciones, una fiscal o de matriz para facturas, una termica para
recibos y otra de etiquetas). Este modulo asigna una impresora a cada rol y
envia cada documento a la que le corresponde, con sus propias opciones de
papel, calidad y copias.

Roles definidos:
    resultados   - informes de resultados, hojas de trabajo, interpretaciones
    cotizaciones - cotizaciones y presupuestos
    facturacion  - facturas, notas de credito/debito
    recibos      - recibos de caja (ticket 80 mm)
    etiquetas    - etiquetas de tubos (rollo 80 mm)

Es perfectamente valido asignar la misma impresora fisica a varios roles: cada
trabajo se envia igual, de forma independiente.

Como se imprime (y por que no con SetDefaultPrinter)
----------------------------------------------------
Cambiar la impresora predeterminada del sistema para imprimir y restaurarla
despues es una carrera: ShellExecute('print') es asincrono, asi que si se
imprime un recibo y una etiqueta casi a la vez, el segundo trabajo puede salir
por la impresora del primero. Ademas, si el PDF esta asociado a Edge o a
Acrobat, el verbo 'print' se limita a abrir el visor y dejar el documento en
pantalla: el sistema no imprime nada, imprime el visor (o no imprime).

Por eso se imprime asi:

  1. GDI directo (unica via normal): se abre el DEVMODE de la impresora, se le
     aplican las opciones del rol (papel, orientacion, calidad, bandeja), se
     rasteriza el PDF con PyMuPDF y se envia pagina por pagina al contexto de
     dispositivo. Funciona con cualquier impresora instalada, sin dialogos,
     sin visores y sin tocar nada global. Devuelve el numero de trabajo del
     spooler, que queda registrado en el log.
  2. Verbo 'printto' del shell: solo como respaldo si el equipo no tiene
     PyMuPDF/pywin32 completos.

Si todo falla el llamador se entera (estado 'fallo_impresion' o
'sin_impresora') y decide si abre el PDF en pantalla, pero siempre avisando:
abrir el visor NO es imprimir.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import os
import json
import logging
import threading

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
        'ayuda': 'Informes de resultados, hojas de trabajo e interpretaciones',
        'columna': 'ImpresoraResultados',
        'columna_directo': 'ImpresoraResultadosDirecto',
        'directo_defecto': True,
        'papel': 'hoja',
    },
    'hojas_trabajo': {
        'etiqueta': 'Hojas de trabajo',
        'ayuda': 'Hojas de bancada del día, en horizontal, para anotar a mano',
        'columna': 'ImpresoraHojasTrabajo',
        'columna_directo': 'ImpresoraHojasTrabajoDirecto',
        'directo_defecto': True,
        'papel': 'hoja',
    },
    'cotizaciones': {
        'etiqueta': 'Cotizaciones',
        'ayuda': 'Cotizaciones y presupuestos para el paciente',
        'columna': 'ImpresoraCotizaciones',
        'columna_directo': 'ImpresoraCotizacionesDirecto',
        'directo_defecto': True,
        'papel': 'hoja',
    },
    'facturacion': {
        'etiqueta': 'Facturación',
        'ayuda': 'Facturas y notas de crédito/débito',
        'columna': 'ImpresoraFacturacion',
        'columna_directo': 'ImpresoraFacturacionDirecto',
        'directo_defecto': True,
        'papel': 'hoja',
    },
    'recibos': {
        'etiqueta': 'Recibos de caja',
        'ayuda': 'Ticket de 80 mm que se entrega al paciente',
        'columna': 'ImpresoraRecibos',
        'columna_directo': 'ImpresoraRecibosDirecto',
        'directo_defecto': True,
        'papel': 'rollo',
    },
    'etiquetas': {
        'etiqueta': 'Etiquetas de muestras',
        'ayuda': 'Rollo de 80 mm para identificar los tubos',
        'columna': 'ImpresoraEtiquetas',
        'columna_directo': 'ImpresoraEtiquetasDirecto',
        'directo_defecto': True,
        'papel': 'rollo',
    },
}

# Orden estable para la interfaz de configuración
ORDEN_ROLES = ('resultados', 'hojas_trabajo', 'cotizaciones',
               'facturacion', 'recibos', 'etiquetas')

# Nombres alternativos que usan las llamadas existentes del sistema
ALIAS_ROLES = {
    'informes': 'resultados',
    'resultado': 'resultados',
    'informe': 'resultados',
    'ia': 'resultados',
    'interpretacion': 'resultados',
    'cotizacion': 'cotizaciones',
    'presupuesto': 'cotizaciones',
    'presupuestos': 'cotizaciones',
    'factura': 'facturacion',
    'facturas': 'facturacion',
    'nota_credito': 'facturacion',
    'nota_debito': 'facturacion',
    'recibo': 'recibos',
    'etiqueta': 'etiquetas',
    'hoja_trabajo': 'hojas_trabajo',
    'hoja de trabajo': 'hojas_trabajo',
    'hojas de trabajo': 'hojas_trabajo',
    'hoja': 'hojas_trabajo',
    'hojas': 'hojas_trabajo',
    'bancada': 'hojas_trabajo',
    'trabajo': 'hojas_trabajo',
}

# Columna donde se guardan las opciones de papel/calidad de cada rol (JSON)
COLUMNA_OPCIONES = 'OpcionesImpresoras'

# ── Cotizaciones: respaldo cuando no tienen impresora propia ────────────────
# Antes las cotizaciones no tenían rol propio y salían por facturación o por
# resultados según esta preferencia. Ahora tienen su propia impresora; esta
# opción se conserva como respaldo para las instalaciones que aún no la han
# asignado, para que ninguna cotización se quede sin destino.
ALIAS_COTIZACION = ('cotizacion', 'cotizaciones', 'presupuesto', 'presupuestos')
ROLES_COTIZACION = ('facturacion', 'resultados')
ROL_COTIZACIONES_DEFECTO = 'facturacion'
COLUMNA_ROL_COTIZACIONES = 'RolCotizaciones'

# ── Respaldo entre roles ───────────────────────────────────────────────────
# Un rol añadido después de instalar no tiene impresora propia en los
# laboratorios que ya venían trabajando. Antes de dejar el documento sin
# destino (que acaba en el visor de PDF, o sea sin imprimir), se recurre al
# rol indicado aquí. En cuanto el rol tiene su impresora asignada, manda la
# suya. Las hojas de trabajo salían por la de resultados desde siempre, así
# que ese es su respaldo natural.
ROLES_RESPALDO = {
    'hojas_trabajo': ('resultados',),
}


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
#  Opciones de impresión por rol
# ══════════════════════════════════════════════════════════════════════════
# escala:
#   'ajustar' - reduce la página si no cabe, nunca la amplía (hoja completa)
#   'real'    - tamaño real, sin tocar (recibos y etiquetas térmicas)
#   'llenar'  - amplía o reduce hasta ocupar el área imprimible (etiquetas
#               cuyo PDF es más pequeño que la etiqueta física)
ESCALAS = ('ajustar', 'real', 'llenar')
CALIDADES = ('alta', 'media', 'borrador')
ORIENTACIONES = ('vertical', 'horizontal')

# DMRES_HIGH / DMRES_MEDIUM / DMRES_DRAFT
_CALIDAD_DM = {'alta': -4, 'media': -3, 'borrador': -1}
_ORIENTACION_DM = {'vertical': 1, 'horizontal': 2}

OPCIONES_DEFECTO = {
    'copias': 1,
    'calidad': 'alta',
    'orientacion': 'vertical',
    'escala': 'ajustar',
    'papel': 0,      # DMPAPER_*; 0 = el que tenga configurado la impresora
    'bandeja': 0,    # DMBIN_*;   0 = la que tenga configurada la impresora
}

# Los roles de rollo salen a tamaño real: escalar un ticket de 80 mm para que
# "quepa" en la hoja lo deja ilegible
OPCIONES_DEFECTO_ROL = {
    'recibos': {'escala': 'real'},
    'etiquetas': {'escala': 'real'},
    # La hoja de trabajo se genera en landscape (modulos/hojas_trabajo.py).
    # Si se imprime con la orientación vertical de los informes, el driver
    # pone la hoja de pie y la página horizontal se encoge para caber: sale
    # una franja diminuta e ilegible en medio del papel.
    'hojas_trabajo': {'orientacion': 'horizontal'},
}


def opciones_defecto(rol):
    """Opciones iniciales de un rol (copia nueva, editable sin efectos)."""
    datos = dict(OPCIONES_DEFECTO)
    datos.update(OPCIONES_DEFECTO_ROL.get(rol, {}))
    return datos


def normalizar_opciones(rol, datos):
    """Devuelve las opciones del rol saneadas, sin valores imposibles."""
    base = opciones_defecto(rol)
    if not isinstance(datos, dict):
        return base
    try:
        base['copias'] = max(1, min(99, int(datos.get('copias') or 1)))
    except Exception:
        pass
    calidad = str(datos.get('calidad') or '').strip().lower()
    if calidad in CALIDADES:
        base['calidad'] = calidad
    orientacion = str(datos.get('orientacion') or '').strip().lower()
    if orientacion in ORIENTACIONES:
        base['orientacion'] = orientacion
    escala = str(datos.get('escala') or '').strip().lower()
    if escala in ESCALAS:
        base['escala'] = escala
    for campo in ('papel', 'bandeja'):
        try:
            base[campo] = int(datos.get(campo) or 0)
        except Exception:
            pass
    return base


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


# ── Impresoras que no sacan papel ──────────────────────────────────────────
# «Microsoft Print to PDF» suele ser la predeterminada de Windows, así que en
# cuanto una función se quedaba sin impresora propia el documento acababa ahí:
# el usuario veía abrirse un cuadro de «guardar PDF» y creía que el programa se
# negaba a imprimir. Estas nunca se ofrecen como opción por defecto.
_VIRTUALES = (
    'print to pdf', 'xps document writer', 'onenote', 'fax',
    'adobe pdf', 'pdfcreator', 'cutepdf', 'dopdf', 'bullzip', 'foxit',
    'pdf24', 'nitro pdf', 'clipboard', 'sendtokindle', 'send to kindle',
    'microsoft print to', 'guardar como pdf', 'save as pdf',
)


def es_impresora_virtual(nombre):
    """True si la impresora genera un archivo en vez de imprimir en papel."""
    n = str(nombre or '').strip().lower()
    if not n:
        return False
    return any(marca in n for marca in _VIRTUALES)


def elegir_impresora_sugerida(nombres, predeterminada=''):
    """
    Impresora que conviene proponer cuando no hay ninguna asignada.

    Prefiere la predeterminada de Windows, pero solo si imprime de verdad;
    si no, la primera física de la lista. Devuelve '' si no hay ninguna.
    """
    nombres = list(nombres or [])
    if predeterminada and predeterminada in nombres \
            and not es_impresora_virtual(predeterminada):
        return predeterminada
    for n in nombres:
        if not es_impresora_virtual(n):
            return n
    return nombres[0] if nombres else ''


# Banderas de estado del spooler que impiden o entorpecen la impresión
_ESTADOS_IMPRESORA = (
    (0x00000002, 'Error'),
    (0x00000008, 'Papel atascado'),
    (0x00000010, 'Sin papel'),
    (0x00000040, 'Problema de papel'),
    (0x00000080, 'Sin conexión'),
    (0x00001000, 'No disponible'),
    (0x00040000, 'Sin tinta / tóner'),
    (0x00100000, 'Requiere intervención'),
    (0x00400000, 'Tapa abierta'),
    (0x00000001, 'En pausa'),
    (0x00020000, 'Tinta / tóner bajo'),
    (0x00000400, 'Imprimiendo'),
    (0x00000200, 'Ocupada'),
)

# Attributes: casilla «Usar impresora sin conexión» de Windows
_ATRIBUTO_OFFLINE = 0x00000400

# Estas banderas impiden que salga el papel; el resto son informativas
_MASCARA_BLOQUEO = (0x00000002 | 0x00000008 | 0x00000010 | 0x00000040 |
                    0x00000080 | 0x00001000 | 0x00040000 | 0x00100000 |
                    0x00400000)


def estado_impresora(nombre):
    """
    Consulta el spooler y describe cómo está una impresora.

    Returns dict con:
        existe    - la impresora está instalada
        texto     - descripción corta para mostrar en pantalla
        lista     - True si puede imprimir ahora mismo
        bloqueada - True si hay un problema que impide imprimir
        trabajos  - trabajos pendientes en su cola
    """
    salida = {'nombre': nombre or '', 'existe': False, 'texto': 'No asignada',
              'lista': False, 'bloqueada': False, 'trabajos': 0}
    if not nombre:
        return salida
    try:
        import win32print
    except Exception:
        # Sin pywin32 no se puede consultar, pero tampoco se puede afirmar
        # que esté mal: se asume utilizable y ya avisará el envío
        salida.update({'existe': True, 'texto': 'Estado desconocido',
                       'lista': True})
        return salida

    try:
        h = win32print.OpenPrinter(nombre)
    except Exception:
        salida['texto'] = 'No instalada en este equipo'
        return salida

    try:
        info = win32print.GetPrinter(h, 2)
        estado = int(info.get('Status', 0) or 0)
        atributos = int(info.get('Attributes', 0) or 0)
        salida['existe'] = True
        salida['trabajos'] = int(info.get('cJobs', 0) or 0)

        motivos = [txt for bit, txt in _ESTADOS_IMPRESORA if estado & bit]
        if atributos & _ATRIBUTO_OFFLINE:
            motivos.insert(0, 'Marcada «sin conexión» en Windows')
            salida['bloqueada'] = True
        if estado & _MASCARA_BLOQUEO:
            salida['bloqueada'] = True

        if motivos:
            salida['texto'] = ' · '.join(motivos[:2])
        else:
            salida['texto'] = 'Lista'
        if salida['trabajos']:
            salida['texto'] += f" ({salida['trabajos']} en cola)"
        salida['lista'] = not salida['bloqueada']
    except Exception as e:
        _log.debug("No se pudo leer el estado de '%s': %s", nombre, e)
        salida.update({'existe': True, 'texto': 'Estado desconocido',
                       'lista': True})
    finally:
        try:
            win32print.ClosePrinter(h)
        except Exception:
            pass
    return salida


def motor_disponible():
    """
    True si el equipo puede imprimir por GDI (la vía real de impresión).

    Si devuelve False solo queda el respaldo por shell, que en la práctica
    termina abriendo el visor de PDF en vez de imprimir.
    """
    try:
        import fitz          # noqa: F401  (PyMuPDF)
        import win32ui       # noqa: F401
        import win32print    # noqa: F401
        from PIL import ImageWin  # noqa: F401
        return True
    except Exception as e:
        _log.debug("Motor de impresión GDI no disponible: %s", e)
        return False


def diagnostico_motor():
    """Lista de librerías que faltan para poder imprimir, vacía si está todo."""
    faltan = []
    for modulo, paquete in (('fitz', 'PyMuPDF'), ('win32print', 'pywin32'),
                            ('win32ui', 'pywin32'), ('PIL', 'Pillow')):
        try:
            __import__(modulo)
        except Exception:
            if paquete not in faltan:
                faltan.append(paquete)
    return faltan


# ══════════════════════════════════════════════════════════════════════════
#  Envío del documento a una impresora concreta
# ══════════════════════════════════════════════════════════════════════════
# Resolución máxima a la que se rasteriza; por encima el consumo de memoria
# crece sin mejora visible en papel
_DPI_MAXIMO = 300

# Serializa el acceso al DEVMODE de una misma impresora
_lock_devmode = threading.Lock()


def _preparar_devmode(impresora, opciones):
    """
    DEVMODE de la impresora con las opciones del rol aplicadas.

    Returns (devmode, driver) o (None, None) si no se pudo preparar; en ese
    caso se imprime con la configuración que tenga la impresora.
    """
    try:
        import win32print
        import win32con
    except Exception:
        return None, None

    opciones = opciones or {}
    try:
        with _lock_devmode:
            h = win32print.OpenPrinter(impresora)
            try:
                info = win32print.GetPrinter(h, 2)
                dm = info['pDevMode']
                driver = info.get('pDriverName') or 'winspool'
                if dm is None:
                    return None, None

                campos = 0
                # Las copias se hacen repitiendo el documento (ver mas abajo):
                # dejar aqui un valor > 1 las multiplicaria dos veces
                dm.Copies = 1
                campos |= win32con.DM_COPIES

                calidad = _CALIDAD_DM.get(
                    str(opciones.get('calidad') or 'alta').lower())
                if calidad:
                    dm.PrintQuality = calidad
                    campos |= win32con.DM_PRINTQUALITY

                orientacion = _ORIENTACION_DM.get(
                    str(opciones.get('orientacion') or 'vertical').lower())
                if orientacion:
                    dm.Orientation = orientacion
                    campos |= win32con.DM_ORIENTATION

                try:
                    papel = int(opciones.get('papel') or 0)
                except Exception:
                    papel = 0
                if papel > 0:
                    dm.PaperSize = papel
                    campos |= win32con.DM_PAPERSIZE

                try:
                    bandeja = int(opciones.get('bandeja') or 0)
                except Exception:
                    bandeja = 0
                if bandeja > 0:
                    dm.DefaultSource = bandeja
                    campos |= win32con.DM_DEFAULTSOURCE

                dm.Fields = dm.Fields | campos
                # El driver valida y completa lo que no admita
                win32print.DocumentProperties(
                    0, h, impresora, dm, dm,
                    win32con.DM_IN_BUFFER | win32con.DM_OUT_BUFFER)
                return dm, driver
            finally:
                try:
                    win32print.ClosePrinter(h)
                except Exception:
                    pass
    except Exception as e:
        _log.debug("No se pudo preparar el DEVMODE de '%s': %s", impresora, e)
        return None, None


def _crear_dc(impresora, devmode, driver):
    """Contexto de dispositivo de la impresora, con DEVMODE si se pudo."""
    import win32ui
    if devmode is not None:
        try:
            import win32gui
            handle = win32gui.CreateDC(driver or 'winspool', impresora, devmode)
            if handle:
                return win32ui.CreateDCFromHandle(handle)
        except Exception as e:
            _log.debug("CreateDC con DEVMODE falló en '%s': %s", impresora, e)
    dc = win32ui.CreateDC()
    dc.CreatePrinterDC(impresora)
    return dc


def _factor_escala(escala, ancho_disp, alto_disp, ancho_real, alto_real):
    """Cuánto hay que escalar la página para el modo de escala pedido."""
    if ancho_real <= 0 or alto_real <= 0:
        return 1.0
    ajuste = min(ancho_disp / ancho_real, alto_disp / alto_real)
    if escala == 'real':
        # Tamaño físico exacto; solo se reduce si literalmente no cabe
        return min(1.0, ajuste)
    if escala == 'llenar':
        return ajuste
    # 'ajustar': reduce si no cabe, nunca amplía
    return min(ajuste, 1.0)


def _imprimir_gdi(ruta, impresora, copias=1, opciones=None, titulo=None):
    """
    Rasteriza el PDF y lo envía al contexto de dispositivo de la impresora.

    Es el método real de impresión: no usa verbos del shell, no abre ningún
    visor y no toca la impresora predeterminada, así que cada rol imprime en
    la suya sin interferencias.

    Returns (True, id_del_ultimo_trabajo) o (False, mensaje_de_error).
    """
    try:
        import fitz                      # PyMuPDF
        import win32con
        from PIL import Image, ImageWin
    except ImportError as e:
        return False, f"Falta una librería de impresión: {e}"

    opciones = normalizar_opciones(None, opciones or {})
    escala_modo = opciones.get('escala', 'ajustar')
    devmode, driver = _preparar_devmode(impresora, opciones)
    nombre_trabajo = titulo or os.path.basename(ruta)

    doc = None
    ultimo_trabajo = 0
    try:
        doc = fitz.open(ruta)
        if doc.page_count == 0:
            return False, "El PDF no tiene páginas"

        for _ in range(max(1, int(copias or 1))):
            hdc = _crear_dc(impresora, devmode, driver)
            try:
                # Área imprimible y resolución reales de la impresora
                ancho_disp = hdc.GetDeviceCaps(win32con.HORZRES)
                alto_disp = hdc.GetDeviceCaps(win32con.VERTRES)
                dpi_x = hdc.GetDeviceCaps(win32con.LOGPIXELSX) or 203
                dpi_y = hdc.GetDeviceCaps(win32con.LOGPIXELSY) or 203
                # No se rasteriza por encima de _DPI_MAXIMO: más resolución
                # solo gasta memoria, no mejora el papel
                factor_dpi = min(_DPI_MAXIMO / dpi_x, _DPI_MAXIMO / dpi_y, 1.0)

                trabajo = hdc.StartDoc(nombre_trabajo)
                try:
                    for pagina in doc:
                        hdc.StartPage()
                        matriz = fitz.Matrix(dpi_x / 72.0 * factor_dpi,
                                             dpi_y / 72.0 * factor_dpi)
                        pix = pagina.get_pixmap(matrix=matriz, alpha=False)
                        img = Image.frombytes('RGB', (pix.width, pix.height),
                                              pix.samples)

                        # Tamaño real de la página en píxeles de la impresora
                        ancho_real = pagina.rect.width / 72.0 * dpi_x
                        alto_real = pagina.rect.height / 72.0 * dpi_y
                        factor = _factor_escala(escala_modo,
                                                ancho_disp, alto_disp,
                                                ancho_real, alto_real)
                        w_dest = max(1, int(ancho_real * factor))
                        h_dest = max(1, int(alto_real * factor))
                        # El rollo se ancla a la izquierda (el cabezal empieza
                        # ahí); la hoja completa se centra
                        x = 0 if escala_modo == 'real' else \
                            max(0, (ancho_disp - w_dest) // 2)
                        ImageWin.Dib(img).draw(hdc.GetHandleOutput(),
                                               (x, 0, x + w_dest, h_dest))
                        hdc.EndPage()
                    hdc.EndDoc()
                    try:
                        ultimo_trabajo = int(trabajo or 0)
                    except Exception:
                        ultimo_trabajo = 0
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
        return True, ultimo_trabajo

    except Exception as e:
        _log.warning("Impresión GDI falló en '%s': %s", impresora, e)
        return False, str(e)
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def _imprimir_printto(ruta, impresora):
    """
    Respaldo por shell cuando el equipo no tiene el motor GDI completo.

    Depende de que el visor de PDF instalado registre el verbo 'printto'.
    Con Edge o con algunos Acrobat recientes no está registrado y lo único
    que ocurre es que se abre el documento en pantalla, por eso es el último
    recurso y no la vía normal.
    """
    try:
        import win32api
        win32api.ShellExecute(0, 'printto', ruta, f'"{impresora}"', '.', 0)
        return True
    except Exception as e:
        _log.debug("printto falló en '%s': %s", impresora, e)
        return False


def enviar_documento(ruta, impresora, copias=1, opciones=None, titulo=None):
    """
    Envía un PDF a una impresora concreta y explica qué pasó.

    Returns dict:
        ok        - True si el trabajo entró al spooler
        metodo    - 'gdi' | 'printto' | ''
        trabajo   - número de trabajo del spooler (0 si no se conoce)
        impresora - nombre de la impresora
        error     - motivo del fallo cuando ok es False
    """
    salida = {'ok': False, 'metodo': '', 'trabajo': 0,
              'impresora': impresora or '', 'error': ''}

    if not ruta or not os.path.exists(ruta):
        salida['error'] = "No se encontró el archivo a imprimir"
        _log.error("Archivo inexistente: %s", ruta)
        return salida
    if not impresora:
        salida['error'] = "No hay impresora asignada"
        return salida

    copias = max(1, int(copias or 1))

    # Aviso previo: si el spooler ya dice que la impresora está mal, el
    # trabajo se encola igual pero se deja constancia del motivo
    estado = estado_impresora(impresora)
    if not estado['existe']:
        salida['error'] = f"La impresora «{impresora}» no está instalada en este equipo"
        return salida
    if estado['bloqueada']:
        _log.warning("La impresora '%s' reporta: %s", impresora, estado['texto'])

    # 1) GDI directo: la vía real de impresión
    ok, detalle = _imprimir_gdi(ruta, impresora, copias, opciones, titulo)
    if ok:
        salida.update({'ok': True, 'metodo': 'gdi', 'trabajo': detalle})
        _log.info("Documento enviado a '%s' (GDI, trabajo %s): %s",
                  impresora, detalle, os.path.basename(ruta))
        if estado['bloqueada']:
            salida['aviso'] = estado['texto']
        return salida
    salida['error'] = str(detalle)

    # 2) Respaldo por shell (equipos sin PyMuPDF/pywin32 completos)
    if all(_imprimir_printto(ruta, impresora) for _ in range(copias)):
        salida.update({'ok': True, 'metodo': 'printto', 'error': ''})
        _log.info("Documento enviado a '%s' (printto): %s", impresora,
                  os.path.basename(ruta))
        return salida

    _log.error("No se pudo imprimir en '%s': %s", impresora, salida['error'])
    return salida


def enviar_a_impresora(ruta, impresora, copias=1, opciones=None, titulo=None):
    """Compatibilidad: envía el documento y devuelve solo True/False."""
    return enviar_documento(ruta, impresora, copias, opciones, titulo)['ok']


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
#  Página de prueba
# ══════════════════════════════════════════════════════════════════════════
def generar_pagina_prueba(rol=None, impresora='', laboratorio='', carpeta=None):
    """
    Crea un PDF de prueba con el tamaño típico del rol.

    Sirve para confirmar que la impresora responde, que el papel entra
    derecho y que la escala configurada es la correcta.

    Returns la ruta del PDF, o None si no se pudo generar.
    """
    try:
        import fitz
    except Exception as e:
        _log.warning("No se puede generar la página de prueba: %s", e)
        return None

    from datetime import datetime

    r = normalizar_rol(rol) or 'resultados'
    es_rollo = ROLES[r].get('papel') == 'rollo'
    # 80 mm de ancho para rollo; carta para hoja completa
    ancho, alto = (226.8, 400.0) if es_rollo else (612.0, 792.0)
    margen = 10 if es_rollo else 45

    try:
        doc = fitz.open()
        pagina = doc.new_page(width=ancho, height=alto)

        # Marco del área útil: si algún borde sale cortado, el papel o la
        # escala están mal configurados
        pagina.draw_rect(fitz.Rect(margen, margen, ancho - margen, alto - margen),
                         color=(0.1, 0.35, 0.7), width=1)

        y = margen + 22
        tam_tit = 11 if es_rollo else 16
        pagina.insert_text((margen + 8, y), "ANgesLAB", fontsize=tam_tit,
                           fontname='helv', color=(0.1, 0.35, 0.7))
        y += tam_tit + 4
        pagina.insert_text((margen + 8, y), "PÁGINA DE PRUEBA",
                           fontsize=tam_tit - 3, fontname='hebo')
        y += tam_tit + 8

        lineas = [
            f"Función: {ROLES[r]['etiqueta']}",
            f"Impresora: {impresora or '(no indicada)'}",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        ]
        if laboratorio:
            lineas.insert(0, f"Laboratorio: {laboratorio}")
        for linea in lineas:
            pagina.insert_text((margen + 8, y), linea[:60], fontsize=8,
                               fontname='helv')
            y += 12

        y += 6
        pagina.insert_text((margen + 8, y),
                           "Si lee este texto completo y el marco no sale",
                           fontsize=7, fontname='helv')
        y += 10
        pagina.insert_text((margen + 8, y),
                           "cortado, la impresora está bien configurada.",
                           fontsize=7, fontname='helv')
        y += 18

        # Regla de 1 cm: permite comprobar que no hay escalado indebido
        pagina.insert_text((margen + 8, y), "Regla (1 cm por marca):",
                           fontsize=7, fontname='helv')
        y += 8
        x = margen + 8
        limite = ancho - margen - 8
        i = 0
        while x <= limite:
            largo = 10 if i % 5 else 16
            pagina.draw_line(fitz.Point(x, y), fitz.Point(x, y + largo),
                             width=0.7)
            x += 28.35            # 1 cm en puntos
            i += 1
        pagina.draw_line(fitz.Point(margen + 8, y), fitz.Point(min(x - 28.35, limite), y),
                         width=0.7)

        # Escala de grises: comprueba tinta/tóner
        y += 34
        pagina.insert_text((margen + 8, y), "Tinta:", fontsize=7, fontname='helv')
        x = margen + 45
        for tono in (0.0, 0.25, 0.5, 0.75):
            if x + 22 > limite:
                break
            pagina.draw_rect(fitz.Rect(x, y - 7, x + 20, y + 3),
                             color=None, fill=(tono, tono, tono))
            x += 24

        destino = carpeta or os.environ.get('TEMP') or os.getcwd()
        ruta = os.path.join(destino, f"angeslab_prueba_{r}.pdf")
        doc.save(ruta)
        doc.close()
        return ruta
    except Exception as e:
        _log.error("No se pudo generar la página de prueba: %s", e)
        return None


# ══════════════════════════════════════════════════════════════════════════
#  Gestor de asignaciones
# ══════════════════════════════════════════════════════════════════════════
class GestorImpresoras:
    """Lee y guarda qué impresora atiende cada rol y con qué opciones."""

    def __init__(self, db):
        self.db = db
        self._cache = None
        self._opciones = {}
        self._rol_cotizaciones = ROL_COTIZACIONES_DEFECTO
        self._columnas_ok = False

    def _asegurar_columnas(self):
        """
        Crea en ConfiguracionLaboratorio las columnas de impresoras que falten.

        El guardado manda un solo UPDATE con todas las columnas a la vez, así
        que si falta una sola (la de un rol añadido en una versión posterior,
        por ejemplo) Access rechaza la sentencia entera y no se guarda NINGUNA
        impresora. El usuario solo veía que sus asignaciones no aguantaban, sin
        pista de por qué.
        """
        if self._columnas_ok:
            return
        columnas = []
        for rol in ORDEN_ROLES:
            columnas.append((ROLES[rol]['columna'], 'TEXT(255)'))
            columnas.append((ROLES[rol]['columna_directo'], 'BIT'))
        columnas.append((COLUMNA_OPCIONES, 'MEMO'))
        columnas.append((COLUMNA_ROL_COTIZACIONES, 'TEXT(20)'))

        for col, tipo in columnas:
            try:
                self.db.query_one(
                    f"SELECT TOP 1 [{col}] FROM ConfiguracionLaboratorio")
                continue
            except Exception:
                pass
            try:
                self.db.execute(
                    f"ALTER TABLE ConfiguracionLaboratorio "
                    f"ADD COLUMN [{col}] {tipo}")
                _log.info("Columna de impresoras creada: %s", col)
            except Exception as e:
                _log.warning("No se pudo crear la columna '%s': %s", col, e)
        self._columnas_ok = True

    def invalidar_cache(self):
        self._cache = None
        self._opciones = {}

    def asignaciones(self, refrescar=False):
        """
        Devuelve {rol: {'impresora': str, 'directo': bool}} para todos los roles.

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

        # Las columnas BIT que Access crea con ALTER TABLE nacen en False, no
        # en NULL, asi que un valor por defecto True jamas se aplicaria. Se usa
        # OpcionesImpresoras como marca de «esto ya se configuro alguna vez»:
        # mientras siga vacia mandan los valores de fabrica de cada rol.
        sin_configurar = not (config.get(COLUMNA_OPCIONES) or '').strip() \
            if config else True

        salida = {}
        for rol in ORDEN_ROLES:
            info = ROLES[rol]
            valor = config.get(info['columna'])
            directo = config.get(info['columna_directo'])
            salida[rol] = {
                'impresora': (valor or '').strip() if valor else '',
                'directo': info['directo_defecto']
                           if (directo is None or sin_configurar)
                           else bool(directo),
            }

        # Respaldo para instalaciones que aún no asignaron impresora propia
        # a las cotizaciones
        elegido = (config.get(COLUMNA_ROL_COTIZACIONES) or '').strip().lower()
        self._rol_cotizaciones = (elegido if elegido in ROLES_COTIZACION
                                  else ROL_COTIZACIONES_DEFECTO)

        self._opciones = self._leer_opciones(config)
        self._cache = salida
        return salida

    @staticmethod
    def _leer_opciones(config):
        """Opciones por rol guardadas como JSON; siempre devuelve algo usable."""
        crudo = config.get(COLUMNA_OPCIONES) if config else None
        datos = {}
        if crudo:
            try:
                datos = json.loads(crudo) or {}
            except Exception as e:
                _log.warning("Opciones de impresión ilegibles, se usan las "
                             "de fábrica: %s", e)
                datos = {}
        return {rol: normalizar_opciones(rol, datos.get(rol))
                for rol in ORDEN_ROLES}

    def opciones_de(self, rol):
        """
        Opciones de papel/orientación/calidad/copias del rol.

        Se toman siempre del rol pedido, nunca del rol de respaldo: el
        respaldo solo decide POR QUÉ IMPRESORA sale el papel, mientras que
        estas opciones describen el documento. Una hoja de trabajo que salga
        por la impresora de resultados sigue siendo horizontal; heredar el
        vertical de los informes la imprimía encogida y de lado.
        """
        self.asignaciones()
        r = normalizar_rol(rol)
        if not r:
            return dict(OPCIONES_DEFECTO)
        return dict(self._opciones.get(r) or opciones_defecto(r))

    def todas_las_opciones(self):
        """Copia de las opciones de todos los roles."""
        self.asignaciones()
        return {rol: dict(self._opciones.get(rol) or opciones_defecto(rol))
                for rol in ORDEN_ROLES}

    def rol_cotizaciones(self):
        """Rol de respaldo para cotizaciones: 'facturacion' o 'resultados'."""
        self.asignaciones()          # asegura que la configuración esté leída
        return self._rol_cotizaciones

    def _candidatos_respaldo(self, rol):
        """Roles a los que recurre `rol` mientras no tenga impresora propia."""
        if rol == 'cotizaciones':
            # El respaldo de las cotizaciones lo elige el laboratorio
            preferido = self._rol_cotizaciones
            alterno = ('resultados' if preferido == 'facturacion'
                       else 'facturacion')
            return (preferido, alterno)
        return ROLES_RESPALDO.get(rol, ())

    def _resolver_rol(self, rol):
        """
        Nombre canónico del rol al que sale realmente el documento.

        Cada función sale por su propia impresora. Si todavía no tiene
        ninguna asignada se recurre a su rol de respaldo (ver ROLES_RESPALDO
        y RolCotizaciones), para que el documento salga igual en vez de
        quedarse sin destino y acabar en el visor de PDF.
        """
        r = normalizar_rol(rol)
        if not r:
            return None

        asig = self.asignaciones()
        if asig.get(r, {}).get('impresora'):
            return r

        for candidato in self._candidatos_respaldo(r):
            if asig.get(candidato, {}).get('impresora'):
                _log.info("«%s» sale por el rol de respaldo '%s'", r, candidato)
                return candidato
        return r

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

    def imprimir(self, ruta, rol, copias=None, titulo=None):
        """
        Envía el documento a la impresora del rol con sus opciones.

        Returns dict de enviar_documento; 'ok' es False si el rol no tiene
        impresora asignada o el envío falló (el llamador decide el respaldo).
        """
        impresora = self.impresora_de(rol)
        if not impresora:
            return {'ok': False, 'metodo': '', 'trabajo': 0, 'impresora': '',
                    'error': 'sin_impresora'}
        opciones = self.opciones_de(rol)
        n = copias if copias else opciones.get('copias', 1)
        return enviar_documento(ruta, impresora, n, opciones, titulo)

    def imprimir_prueba(self, rol, laboratorio=''):
        """Genera y envía una página de prueba por el rol indicado."""
        impresora = self.impresora_de(rol)
        if not impresora:
            return {'ok': False, 'error': 'sin_impresora', 'impresora': '',
                    'metodo': '', 'trabajo': 0}
        ruta = generar_pagina_prueba(rol, impresora, laboratorio)
        if not ruta:
            return {'ok': False, 'impresora': impresora, 'metodo': '',
                    'trabajo': 0,
                    'error': 'No se pudo generar la página de prueba '
                             '(falta PyMuPDF)'}
        opciones = dict(self.opciones_de(rol))
        opciones['copias'] = 1
        return enviar_documento(ruta, impresora, 1, opciones,
                                'ANgesLAB - Página de prueba')

    def guardar(self, asignaciones, rol_cotizaciones=None, opciones=None):
        """
        Persiste las asignaciones y las opciones de cada rol.

        asignaciones: {rol: {'impresora': str, 'directo': bool}}
        opciones: {rol: {'copias','calidad','orientacion','escala','papel'}}
        Se permite repetir la misma impresora en varios roles.
        rol_cotizaciones: rol de respaldo; None deja el actual.
        """
        self._asegurar_columnas()
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

        if opciones is not None:
            limpias = {rol: normalizar_opciones(rol, (opciones or {}).get(rol))
                       for rol in ORDEN_ROLES}
            texto = json.dumps(limpias, ensure_ascii=False)
            campos.append(
                f"[{COLUMNA_OPCIONES}] = '{texto.replace(chr(39), chr(39)*2)}'")

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
# Estados que devuelve imprimir_documento()
IMPRESO = 'impreso'                    # el trabajo entró al spooler
SIN_IMPRESORA = 'sin_impresora'        # el rol no tiene impresora asignada
FALLO_IMPRESION = 'fallo_impresion'    # hay impresora pero rechazó el trabajo
ABIERTO = 'abierto'                    # solo se abrió en pantalla
ERROR = 'error'                        # ni siquiera se pudo abrir


def imprimir_documento(db, ruta, rol, copias=None, abrir_si_falla=True,
                       titulo=None, detalle=None):
    """
    Imprime en la impresora del rol.

    Si el rol no tiene impresora o la impresión falla, abre el PDF en pantalla
    (cuando abrir_si_falla) pero el estado devuelto deja claro que NO se
    imprimió, para que la interfaz pueda avisar en vez de dar por bueno que
    salió el papel.

    Args:
        detalle: dict opcional donde se copia el resultado completo del envío
                 (impresora, método, número de trabajo, error).

    Returns 'impreso' | 'sin_impresora' | 'fallo_impresion' | 'abierto' | 'error'
    """
    if not ruta or not os.path.exists(ruta):
        return ERROR

    resultado = {'ok': False, 'error': 'sin_impresora', 'impresora': '',
                 'metodo': '', 'trabajo': 0}
    try:
        resultado = GestorImpresoras(db).imprimir(ruta, rol, copias, titulo)
    except Exception as e:
        _log.error("Error imprimiendo (%s): %s", rol, e, exc_info=True)
        resultado = {'ok': False, 'error': str(e), 'impresora': '',
                     'metodo': '', 'trabajo': 0}

    if isinstance(detalle, dict):
        detalle.clear()
        detalle.update(resultado)

    if resultado.get('ok'):
        return IMPRESO

    if abrir_si_falla:
        abrir_documento(ruta)
    if resultado.get('error') == 'sin_impresora':
        return SIN_IMPRESORA
    return FALLO_IMPRESION


def se_imprimio(estado):
    """True solo si el documento llegó de verdad a la impresora."""
    return estado == IMPRESO


def crear_gestor_impresoras(db):
    """Factory del gestor de impresoras."""
    return GestorImpresoras(db)

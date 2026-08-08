# -*- coding: utf-8 -*-
"""
ENVIO POR WHATSAPP CON ADJUNTO AUTOMATICO - ANgesLAB
=====================================================
Abre la conversacion del destinatario y adjunta el PDF de resultados
automaticamente, sin pasos manuales.

Estrategia (en orden):
  1. WhatsApp Desktop (protocolo whatsapp://) + portapapeles + teclado.
     El PDF se copia al portapapeles como archivo (CF_HDROP), se abre el
     chat, se pega el archivo, se pega el mensaje como pie de foto y se
     envia con Enter.
  2. WhatsApp Web (wa.me). El PDF queda copiado en el portapapeles, de
     modo que solo hace falta pegarlo con Ctrl+V en la conversacion.

Configuracion: config_whatsapp.json en la raiz de la aplicacion.
"""

import os
import json
import time
import struct
import webbrowser
import urllib.parse

try:
    import win32clipboard
    import win32con
    import win32gui
    import ctypes
    WIN32_DISPONIBLE = True
except ImportError:
    WIN32_DISPONIBLE = False

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.whatsapp')
except Exception:
    import logging
    _log = logging.getLogger('angeslab.whatsapp')
    _log.addHandler(logging.NullHandler())


CODIGO_PAIS_DEFECTO = '58'   # Venezuela

RUTA_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config_whatsapp.json')

CONFIG_DEFECTO = {
    'metodo': 'auto',            # auto | desktop | web
    'codigo_pais': CODIGO_PAIS_DEFECTO,
    'autoenviar': True,          # pulsar Enter para enviar sin intervencion
    'espera_apertura': 15.0,     # seg. maximos esperando la ventana de WhatsApp
    'espera_chat': 3.0,          # seg. tras abrir el chat antes de pegar
    'espera_adjunto': 3.5,       # seg. tras pegar el archivo (vista previa)
    'espera_envio': 1.2,         # seg. tras escribir el pie antes de Enter
}


# ======================================================================
# Configuracion
# ======================================================================
class ConfigWhatsApp:
    """Lee/escribe config_whatsapp.json con valores por defecto seguros."""

    def __init__(self, ruta=None):
        self.ruta = ruta or RUTA_CONFIG
        self.datos = dict(CONFIG_DEFECTO)
        self.cargar()

    def cargar(self):
        try:
            if os.path.exists(self.ruta):
                with open(self.ruta, 'r', encoding='utf-8') as f:
                    guardado = json.load(f)
                if isinstance(guardado, dict):
                    self.datos.update(guardado)
        except Exception as e:
            _log.warning("No se pudo leer config_whatsapp.json: %s", e)
        return self.datos

    def guardar(self):
        try:
            with open(self.ruta, 'w', encoding='utf-8') as f:
                json.dump(self.datos, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            _log.warning("No se pudo guardar config_whatsapp.json: %s", e)
            return False

    def get(self, clave, defecto=None):
        valor = self.datos.get(clave, defecto)
        return CONFIG_DEFECTO.get(clave, defecto) if valor is None else valor


# ======================================================================
# Normalizacion y validacion de numeros
# ======================================================================
# Reglas por pais: longitud de la parte nacional y prefijos moviles.
# WhatsApp solo funciona con lineas moviles, por eso se distinguen.
REGLAS_PAIS = {
    '58':  {'pais': 'Venezuela',   'largo': 10, 'moviles': ('412', '414', '416', '424', '426')},
    '57':  {'pais': 'Colombia',    'largo': 10, 'moviles': ('3',)},
    '1':   {'pais': 'EEUU/Canada', 'largo': 10, 'moviles': ()},
    '34':  {'pais': 'Espana',      'largo': 9,  'moviles': ('6', '7')},
    '51':  {'pais': 'Peru',        'largo': 9,  'moviles': ('9',)},
    '56':  {'pais': 'Chile',       'largo': 9,  'moviles': ('9',)},
    '52':  {'pais': 'Mexico',      'largo': 10, 'moviles': ()},
    '54':  {'pais': 'Argentina',   'largo': 10, 'moviles': ()},
    '55':  {'pais': 'Brasil',      'largo': 11, 'moviles': ()},
    '593': {'pais': 'Ecuador',     'largo': 9,  'moviles': ('9',)},
    '507': {'pais': 'Panama',      'largo': 8,  'moviles': ('6',)},
    '506': {'pais': 'Costa Rica',  'largo': 8,  'moviles': ('6', '7', '8')},
}

# Ordenados de mas largo a mas corto para no confundir +1 con +51
_CODIGOS_CONOCIDOS = tuple(sorted(REGLAS_PAIS, key=len, reverse=True))


def _separar_codigo_pais(digitos, codigo_pais, era_internacional):
    """Devuelve (codigo_pais, parte_nacional) a partir de los digitos."""
    cp = codigo_pais
    if digitos.startswith(cp):
        return cp, digitos[len(cp):]
    if era_internacional:
        for k in _CODIGOS_CONOCIDOS:
            if digitos.startswith(k):
                return k, digitos[len(k):]
        return None, digitos
    return cp, digitos


def normalizar_telefono(telefono, codigo_pais=CODIGO_PAIS_DEFECTO):
    """Convierte un telefono a formato internacional (solo digitos).

    Corrige los formatos que WhatsApp rechaza con "el numero no esta
    registrado" aunque la linea si tenga WhatsApp:
      '+58+584147204006' -> '584147204006'  (codigo de pais duplicado)
      '+5804121234567'   -> '584121234567'  (0 de tronco sobrante)
      '0412-123.45.67'   -> '584121234567'
      '4121234567'       -> '584121234567'

    Devuelve None si no quedan digitos suficientes.
    """
    if not telefono:
        return None

    texto = str(telefono).strip()
    era_internacional = texto.startswith('+') or texto.startswith('00')
    digitos = ''.join(ch for ch in texto if ch.isdigit())
    if not digitos:
        return None
    if texto.startswith('00'):
        digitos = digitos[2:]

    cp = ''.join(ch for ch in str(codigo_pais or '') if ch.isdigit()) or CODIGO_PAIS_DEFECTO

    # Codigo de pais repetido al inicio: 5858412... -> 58412...
    while len(digitos) > len(cp) * 2 and digitos.startswith(cp + cp):
        digitos = digitos[len(cp):]

    cc, nacional = _separar_codigo_pais(digitos, cp, era_internacional)
    if cc is None:
        # Pais desconocido en formato internacional: se respeta tal cual
        return digitos if len(digitos) >= 8 else None

    largo = REGLAS_PAIS.get(cc, {}).get('largo', 0)

    # Limpiar ceros de tronco y codigos de pais incrustados en la parte nacional
    for _ in range(4):
        antes = nacional
        if nacional.startswith('0'):
            nacional = nacional.lstrip('0')
        if nacional.startswith(cc) and (not largo or len(nacional) > largo):
            nacional = nacional[len(cc):]
        if nacional == antes:
            break

    if len(nacional) < 6:
        return None
    return cc + nacional


def validar_numero_whatsapp(telefono, codigo_pais=CODIGO_PAIS_DEFECTO):
    """Comprueba si el numero puede tener WhatsApp.

    Devuelve (valido, motivo). 'motivo' explica en castellano por que no
    sirve, para poder avisar antes de abrir WhatsApp.
    """
    numero = normalizar_telefono(telefono, codigo_pais)
    if not numero:
        return False, "El numero esta incompleto."

    cc, nacional = None, None
    for k in _CODIGOS_CONOCIDOS:
        if numero.startswith(k):
            cc, nacional = k, numero[len(k):]
            break

    if cc is None:
        return (len(numero) >= 8), ("" if len(numero) >= 8 else "El numero esta incompleto.")

    regla = REGLAS_PAIS[cc]
    largo = regla['largo']

    if len(nacional) < largo:
        faltan = largo - len(nacional)
        return False, (f"Faltan {faltan} digito(s): en {regla['pais']} el numero "
                       f"debe tener {largo} digitos sin el 0 inicial.")
    if len(nacional) > largo:
        sobran = len(nacional) - largo
        return False, (f"Sobran {sobran} digito(s): en {regla['pais']} el numero "
                       f"debe tener {largo} digitos sin el 0 inicial.")

    moviles = regla.get('moviles') or ()
    if moviles and not nacional.startswith(moviles):
        return False, (f"Parece un numero fijo. WhatsApp solo funciona con "
                       f"celulares ({', '.join('0' + m for m in moviles)}...).")

    return True, ""


def telefono_valido(telefono, codigo_pais=CODIGO_PAIS_DEFECTO):
    return validar_numero_whatsapp(telefono, codigo_pais)[0]


def formatear_para_mostrar(telefono_internacional):
    """Devuelve '+58 412 1234567' a partir de '584121234567'."""
    if not telefono_internacional:
        return ''
    d = ''.join(ch for ch in str(telefono_internacional) if ch.isdigit())
    if not d:
        return ''

    for cp in _CODIGOS_CONOCIDOS:
        if d.startswith(cp) and len(d) > len(cp) + 3:
            resto = d[len(cp):]
            return f"+{cp} {resto[:3]} {resto[3:]}"
    return '+' + d


# ======================================================================
# Enviador
# ======================================================================
class EnviadorWhatsApp:
    """Envia un documento por WhatsApp adjuntandolo automaticamente."""

    # Codigos de tecla virtuales
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_RETURN = 0x0D
    VK_MENU = 0x12          # ALT
    KEYEVENTF_KEYUP = 0x0002

    def __init__(self, config=None):
        self.config = config if isinstance(config, ConfigWhatsApp) else ConfigWhatsApp()

    # ------------------------------------------------------------------
    # Disponibilidad
    # ------------------------------------------------------------------
    @staticmethod
    def whatsapp_desktop_instalado():
        """True si el protocolo whatsapp:// esta registrado en el sistema."""
        if os.name != 'nt':
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'whatsapp'):
                return True
        except Exception:
            return False

    def automatizacion_disponible(self):
        return WIN32_DISPONIBLE and os.name == 'nt' and self.whatsapp_desktop_instalado()

    # ------------------------------------------------------------------
    # Portapapeles
    # ------------------------------------------------------------------
    @staticmethod
    def copiar_archivo_al_portapapeles(rutas):
        """Copia uno o varios archivos al portapapeles como CF_HDROP.

        Equivale a hacer Ctrl+C sobre el archivo en el Explorador, por lo
        que WhatsApp lo reconoce como adjunto al pegar.
        """
        if not WIN32_DISPONIBLE:
            return False
        if isinstance(rutas, str):
            rutas = [rutas]
        rutas = [os.path.abspath(r) for r in rutas if r and os.path.exists(r)]
        if not rutas:
            return False

        try:
            # Estructura DROPFILES: pFiles(DWORD) + pt(2 LONG) + fNC(BOOL) + fWide(BOOL)
            cabecera = struct.pack('=IiiII', 20, 0, 0, 0, 1)
            lista = ('\0'.join(rutas) + '\0\0').encode('utf-16-le')

            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_HDROP, cabecera + lista)
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            _log.warning("No se pudo copiar el archivo al portapapeles: %s", e)
            return False

    @staticmethod
    def copiar_texto_al_portapapeles(texto):
        if not WIN32_DISPONIBLE:
            return False
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, str(texto))
            finally:
                win32clipboard.CloseClipboard()
            return True
        except Exception as e:
            _log.warning("No se pudo copiar el texto al portapapeles: %s", e)
            return False

    # ------------------------------------------------------------------
    # Teclado
    # ------------------------------------------------------------------
    def _tecla(self, vk, arriba=False):
        ctypes.windll.user32.keybd_event(vk, 0,
                                         self.KEYEVENTF_KEYUP if arriba else 0, 0)

    def _pegar(self):
        self._tecla(self.VK_CONTROL)
        self._tecla(self.VK_V)
        time.sleep(0.05)
        self._tecla(self.VK_V, arriba=True)
        self._tecla(self.VK_CONTROL, arriba=True)

    def _enter(self):
        self._tecla(self.VK_RETURN)
        time.sleep(0.05)
        self._tecla(self.VK_RETURN, arriba=True)

    # ------------------------------------------------------------------
    # Ventana de WhatsApp
    # ------------------------------------------------------------------
    @staticmethod
    def _buscar_ventana_whatsapp():
        """Devuelve el hwnd de la ventana principal de WhatsApp, o None."""
        encontrada = []

        def _callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return True
                titulo = (win32gui.GetWindowText(hwnd) or '').strip()
                if titulo.lower().startswith('whatsapp'):
                    encontrada.append(hwnd)
                    return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(_callback, None)
        except Exception:
            pass
        return encontrada[0] if encontrada else None

    def _esperar_ventana(self, segundos):
        limite = time.time() + max(1.0, float(segundos))
        while time.time() < limite:
            hwnd = self._buscar_ventana_whatsapp()
            if hwnd:
                return hwnd
            time.sleep(0.4)
        return None

    def _activar_ventana(self, hwnd):
        """Trae la ventana al frente sorteando el bloqueo de foco de Windows."""
        try:
            # Un pulso de ALT libera la restriccion de SetForegroundWindow
            self._tecla(self.VK_MENU)
            self._tecla(self.VK_MENU, arriba=True)

            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.4)
            return win32gui.GetForegroundWindow() == hwnd
        except Exception as e:
            _log.warning("No se pudo activar la ventana de WhatsApp: %s", e)
            return False

    # ------------------------------------------------------------------
    # Envio
    # ------------------------------------------------------------------
    def enviar_documento(self, telefono, ruta_archivo, mensaje='',
                         autoenviar=None, codigo_pais=None):
        """Abre el chat y adjunta el documento automaticamente.

        Devuelve dict:
          exito     -> se pudo completar la operacion
          enviado   -> el mensaje se envio solo (sin intervencion)
          metodo    -> 'desktop' | 'web'
          telefono  -> numero internacional usado
          mensaje   -> texto descriptivo para el usuario
        """
        cp = codigo_pais or self.config.get('codigo_pais', CODIGO_PAIS_DEFECTO)
        numero = normalizar_telefono(telefono, cp)

        if not numero:
            return {'exito': False, 'enviado': False, 'metodo': None,
                    'telefono': None,
                    'mensaje': 'El numero de telefono no es valido.'}

        if not ruta_archivo or not os.path.exists(ruta_archivo):
            return {'exito': False, 'enviado': False, 'metodo': None,
                    'telefono': numero,
                    'mensaje': 'No se encontro el PDF de resultados.'}

        metodo = str(self.config.get('metodo', 'auto')).lower()
        if metodo in ('auto', 'desktop') and self.automatizacion_disponible():
            resultado = self._enviar_desktop(numero, ruta_archivo, mensaje, autoenviar)
            if resultado['exito'] or metodo == 'desktop':
                return resultado
            _log.info("Automatizacion de WhatsApp Desktop fallida, se usa WhatsApp Web")

        return self._enviar_web(numero, ruta_archivo, mensaje)

    # -- WhatsApp Desktop ----------------------------------------------
    def _enviar_desktop(self, numero, ruta_archivo, mensaje, autoenviar=None):
        if autoenviar is None:
            autoenviar = bool(self.config.get('autoenviar', True))

        # 1. El PDF va al portapapeles antes de abrir el chat
        if not self.copiar_archivo_al_portapapeles(ruta_archivo):
            return {'exito': False, 'enviado': False, 'metodo': 'desktop',
                    'telefono': numero,
                    'mensaje': 'No se pudo copiar el PDF al portapapeles.'}

        # 2. Abrir la conversacion (sin texto: el mensaje va como pie del PDF)
        try:
            os.startfile(f"whatsapp://send?phone={numero}")
        except Exception as e:
            _log.warning("No se pudo abrir WhatsApp Desktop: %s", e)
            return {'exito': False, 'enviado': False, 'metodo': 'desktop',
                    'telefono': numero,
                    'mensaje': f'No se pudo abrir WhatsApp Desktop: {e}'}

        # 3. Esperar y enfocar la ventana
        hwnd = self._esperar_ventana(self.config.get('espera_apertura', 15.0))
        if not hwnd:
            return {'exito': False, 'enviado': False, 'metodo': 'desktop',
                    'telefono': numero,
                    'mensaje': 'No se detecto la ventana de WhatsApp Desktop.'}

        if not self._activar_ventana(hwnd):
            return {'exito': False, 'enviado': False, 'metodo': 'desktop',
                    'telefono': numero,
                    'mensaje': 'No se pudo poner WhatsApp en primer plano.'}

        # 4. Dar tiempo a que cargue la conversacion
        time.sleep(float(self.config.get('espera_chat', 3.0)))

        # 5. Pegar el PDF -> se abre la vista previa del adjunto
        self._pegar()
        time.sleep(float(self.config.get('espera_adjunto', 3.5)))

        # 6. Pegar el mensaje como pie del documento
        if mensaje:
            if self.copiar_texto_al_portapapeles(mensaje):
                self._pegar()
                time.sleep(float(self.config.get('espera_envio', 1.2)))

        # 7. Enviar
        if autoenviar:
            self._enter()
            time.sleep(0.6)
            return {'exito': True, 'enviado': True, 'metodo': 'desktop',
                    'telefono': numero,
                    'mensaje': 'Resultados enviados por WhatsApp con el PDF adjunto.'}

        return {'exito': True, 'enviado': False, 'metodo': 'desktop',
                'telefono': numero,
                'mensaje': 'PDF adjuntado en WhatsApp. Pulse Enter para enviarlo.'}

    # -- WhatsApp Web ---------------------------------------------------
    def _enviar_web(self, numero, ruta_archivo, mensaje):
        copiado = self.copiar_archivo_al_portapapeles(ruta_archivo)
        url = f"https://wa.me/{numero}"
        if mensaje:
            url += f"?text={urllib.parse.quote(mensaje)}"
        try:
            webbrowser.open(url)
        except Exception as e:
            return {'exito': False, 'enviado': False, 'metodo': 'web',
                    'telefono': numero,
                    'mensaje': f'No se pudo abrir WhatsApp Web: {e}'}

        if copiado:
            texto = ('Se abrio WhatsApp Web.\n\n'
                     'El PDF ya esta copiado: pulse Ctrl+V en la conversacion '
                     'y luego Enter para enviarlo.')
        else:
            texto = ('Se abrio WhatsApp Web.\n\n'
                     f'Adjunte manualmente el PDF:\n{ruta_archivo}')

        return {'exito': True, 'enviado': False, 'metodo': 'web',
                'telefono': numero, 'mensaje': texto}


# ======================================================================
# Factory
# ======================================================================
def crear_enviador_whatsapp(config=None):
    return EnviadorWhatsApp(config)


# Alias corto
crear_enviador = crear_enviador_whatsapp

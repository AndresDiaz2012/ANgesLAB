# -*- coding: utf-8 -*-
"""
================================================================================
PORTAL DE RESULTADOS POR CODIGO QR - ANgesLAB
================================================================================
Permite que el paciente escanee un codigo QR (impreso en la etiqueta del tubo
y en el recibo de caja) y consulte desde su telefono:

  - Si sus resultados ya estan listos
  - Que pruebas estan validadas y cuales siguen en proceso
  - Descargar / visualizar el PDF de resultados (cuando esta validado)

Arquitectura
------------
El sistema es 100% de escritorio, sin nube. Este modulo levanta un servidor
HTTP liviano dentro de la propia aplicacion:

    QR  ->  http://<IP-del-equipo>:8770/r/<token>

El telefono del paciente debe poder alcanzar esa direccion:
  * En la red WiFi del laboratorio funciona directamente.
  * Para acceso desde fuera, el laboratorio configura una URL publica
    (dominio o IP fija + redireccion de puerto) en 'url_publica'.

Si el portal esta desactivado, el QR degrada a texto informativo legible
(mismo comportamiento historico de formato_pdf.QRGenerator).

Seguridad / privacidad
----------------------
  - El token es aleatorio (10 caracteres, alfabeto sin caracteres ambiguos)
    y solo identifica una solicitud. No es adivinable.
  - Por defecto el paciente debe confirmar su numero de documento (o los
    ultimos 4 digitos) antes de ver el PDF. Sin esa confirmacion la pagina
    solo muestra datos enmascarados.
  - El enlace al PDF va firmado con HMAC-SHA256 y un secreto local.
  - Los tokens expiran (90 dias por defecto).

Configuracion: config_portal.json en la raiz de la aplicacion.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import os
import io
import json
import socket
import hmac
import hashlib
import secrets
import logging
import threading
import urllib.parse
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

try:
    from modulos.logging_config import obtener_logger
    _log = obtener_logger('angeslab.portal')
except Exception:
    _log = logging.getLogger('angeslab.portal')
    _log.addHandler(logging.NullHandler())

try:
    import qrcode
    from qrcode.constants import ERROR_CORRECT_M
    QR_DISPONIBLE = True
except ImportError:
    QR_DISPONIBLE = False

try:
    from PIL import Image as PILImage
    PIL_DISPONIBLE = True
except ImportError:
    PIL_DISPONIBLE = False

try:
    from reportlab.lib.utils import ImageReader
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False


RUTA_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'config_portal.json')

CONFIG_DEFECTO = {
    'activo': True,             # levantar el mini-servidor al iniciar la app
    'puerto': 8770,             # puerto TCP del portal
    'url_publica': '',          # ej. https://resultados.milab.com  (vacio = IP LAN)
    'dias_validez': 90,         # vigencia del token del QR
    'requiere_documento': True, # pedir cedula antes de mostrar el PDF
    'secreto': '',              # se genera solo la primera vez (firma HMAC)
}

# Alfabeto sin caracteres ambiguos (0/O, 1/I/l)
_ALFABETO_TOKEN = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
_LARGO_TOKEN = 10

# Estados de DetalleSolicitudes que se consideran "resultado listo"
_ESTADOS_LISTO = ('validado', 'completada', 'completado', 'entregada')
# Estados de DetalleSolicitudes con resultado cargado pero sin validar
_ESTADOS_EN_PROCESO = ('capturado', 'calculado')
# Estados de la solicitud completa que habilitan la descarga del PDF
_ESTADOS_SOLICITUD_LISTA = ('completada', 'entregada', 'validada')


# ══════════════════════════════════════════════════════════════════════════
#  Configuracion
# ══════════════════════════════════════════════════════════════════════════
class ConfigPortal:
    """Lee y escribe config_portal.json."""

    @staticmethod
    def cargar():
        cfg = dict(CONFIG_DEFECTO)
        try:
            if os.path.exists(RUTA_CONFIG):
                with open(RUTA_CONFIG, 'r', encoding='utf-8') as f:
                    cfg.update(json.load(f) or {})
        except Exception as e:
            _log.warning("config_portal.json ilegible: %s", e)

        # Generar secreto de firma la primera vez
        if not cfg.get('secreto'):
            cfg['secreto'] = secrets.token_hex(32)
            ConfigPortal.guardar(cfg)
        return cfg

    @staticmethod
    def guardar(cfg):
        try:
            with open(RUTA_CONFIG, 'w', encoding='utf-8') as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            _log.error("No se pudo guardar config_portal.json: %s", e)
            return False


def ip_lan():
    """Detecta la IP del equipo en la red local (sin enviar trafico real)."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return '127.0.0.1'
    finally:
        if s:
            try:
                s.close()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════
#  Conexion propia para el hilo del servidor
# ══════════════════════════════════════════════════════════════════════════
class ConexionPortal:
    """
    Conexion ADODB independiente para el hilo HTTP.

    Los objetos COM de pywin32 no se pueden compartir entre hilos, asi que
    cada peticion abre su propia conexion tras CoInitialize().
    Expone la misma interfaz minima que Database (query / query_one).
    """

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self._co_ok = False

    def __enter__(self):
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        self._co_ok = True
        self.conn = win32com.client.Dispatch('ADODB.Connection')
        self.conn.Open(
            f"Provider=Microsoft.ACE.OLEDB.12.0;Data Source={self.db_path};")
        return self

    def __exit__(self, *exc):
        try:
            if self.conn:
                self.conn.Close()
        except Exception:
            pass
        self.conn = None
        if self._co_ok:
            try:
                import pythoncom
                pythoncom.CoUninitialize()
            except Exception:
                pass
            self._co_ok = False
        return False

    def execute(self, sql):
        return self.conn.Execute(sql)

    def query(self, sql):
        rs = self.conn.Execute(sql)[0]
        filas = []
        while not rs.EOF:
            filas.append({rs.Fields[i].Name: rs.Fields[i].Value
                          for i in range(rs.Fields.Count)})
            rs.MoveNext()
        return filas

    def query_one(self, sql):
        filas = self.query(sql)
        return filas[0] if filas else None


def _fecha_access(dt):
    """Literal de fecha/hora para Jet/ACE SQL."""
    return '#' + dt.strftime('%m/%d/%Y %H:%M:%S') + '#'


def _naive(dt):
    """
    Normaliza una fecha a datetime naive.

    ADODB devuelve pywintypes.datetime, que trae tzinfo y no se puede
    comparar contra datetime.now(). Devuelve None si no es una fecha.
    """
    if not hasattr(dt, 'year'):
        return None
    try:
        return datetime(dt.year, dt.month, dt.day,
                        getattr(dt, 'hour', 0), getattr(dt, 'minute', 0),
                        getattr(dt, 'second', 0))
    except Exception:
        return None


def _solo_digitos(txt):
    return ''.join(ch for ch in str(txt or '') if ch.isdigit())


# ══════════════════════════════════════════════════════════════════════════
#  Gestor de tokens y URLs
# ══════════════════════════════════════════════════════════════════════════
class GestorPortalResultados:
    """Crea y resuelve los tokens que viajan dentro del codigo QR."""

    def __init__(self, db):
        self.db = db
        self.cfg = ConfigPortal.cargar()
        self._tabla_ok = False

    # ---------------------------------------------------------------- tabla
    def asegurar_tabla(self):
        """Crea la tabla AccesosQR si no existe."""
        if self._tabla_ok:
            return True
        try:
            self.db.query_one("SELECT TOP 1 AccesoID FROM [AccesosQR]")
            self._tabla_ok = True
            return True
        except Exception:
            pass
        try:
            self.db.execute(
                "CREATE TABLE [AccesosQR] ("
                " AccesoID AUTOINCREMENT PRIMARY KEY,"
                " Token TEXT(32),"
                " SolicitudID LONG,"
                " FechaCreacion DATETIME,"
                " FechaExpira DATETIME,"
                " Vistas LONG,"
                " UltimaVista DATETIME,"
                " Activo BIT)"
            )
            try:
                self.db.execute(
                    "CREATE UNIQUE INDEX idxTokenQR ON [AccesosQR] (Token)")
            except Exception:
                pass
            self._tabla_ok = True
            _log.info("Tabla AccesosQR creada")
            return True
        except Exception as e:
            _log.error("No se pudo crear AccesosQR: %s", e)
            return False

    # --------------------------------------------------------------- tokens
    def obtener_token(self, solicitud_id, crear=True):
        """
        Devuelve el token vigente de una solicitud; lo crea si hace falta.
        Retorna None si la tabla no esta disponible.
        """
        if not self.asegurar_tabla():
            return None

        sid = int(solicitud_id)
        try:
            fila = self.db.query_one(
                f"SELECT TOP 1 Token, FechaExpira FROM [AccesosQR] "
                f"WHERE SolicitudID={sid} AND Activo=True "
                f"ORDER BY AccesoID DESC")
            if fila and fila.get('Token'):
                exp = _naive(fila.get('FechaExpira'))
                if exp is None or exp > datetime.now():
                    return fila['Token']
        except Exception as e:
            _log.warning("Lectura de token fallida (sol %s): %s", sid, e)

        if not crear:
            return None

        token = ''.join(secrets.choice(_ALFABETO_TOKEN)
                        for _ in range(_LARGO_TOKEN))
        ahora = datetime.now()
        expira = ahora + timedelta(days=int(self.cfg.get('dias_validez', 90)))
        try:
            self.db.execute(
                f"UPDATE [AccesosQR] SET Activo=False WHERE SolicitudID={sid}")
        except Exception:
            pass
        try:
            self.db.execute(
                "INSERT INTO [AccesosQR] "
                "(Token, SolicitudID, FechaCreacion, FechaExpira, Vistas, Activo) "
                f"VALUES ('{token}', {sid}, {_fecha_access(ahora)}, "
                f"{_fecha_access(expira)}, 0, True)")
            return token
        except Exception as e:
            _log.error("No se pudo crear token para solicitud %s: %s", sid, e)
            return None

    def solicitud_de_token(self, token):
        """Resuelve un token -> SolicitudID. None si no existe o expiro."""
        if not token:
            return None
        tk = ''.join(ch for ch in str(token).upper()
                     if ch in _ALFABETO_TOKEN)[:32]
        if not tk:
            return None
        try:
            fila = self.db.query_one(
                f"SELECT TOP 1 SolicitudID, FechaExpira, Activo "
                f"FROM [AccesosQR] WHERE Token='{tk}'")
        except Exception:
            return None
        if not fila or not fila.get('Activo'):
            return None
        exp = _naive(fila.get('FechaExpira'))
        if exp is not None and exp < datetime.now():
            return None
        return int(fila['SolicitudID'])

    def registrar_vista(self, token):
        tk = ''.join(ch for ch in str(token or '').upper()
                     if ch in _ALFABETO_TOKEN)[:32]
        if not tk:
            return
        try:
            self.db.execute(
                f"UPDATE [AccesosQR] SET Vistas=Nz(Vistas,0)+1, "
                f"UltimaVista={_fecha_access(datetime.now())} "
                f"WHERE Token='{tk}'")
        except Exception:
            pass

    # ----------------------------------------------------------------- URLs
    def base_url(self):
        """URL base del portal (publica si esta configurada, si no la LAN)."""
        publica = (self.cfg.get('url_publica') or '').strip().rstrip('/')
        if publica:
            if not publica.startswith(('http://', 'https://')):
                publica = 'http://' + publica
            return publica
        return f"http://{ip_lan()}:{int(self.cfg.get('puerto', 8770))}"

    def url_solicitud(self, solicitud_id):
        """URL completa que se codifica en el QR. None si no hay token."""
        token = self.obtener_token(solicitud_id)
        if not token:
            return None
        return f"{self.base_url()}/r/{token}"

    def firma_pdf(self, token):
        """Clave HMAC que autoriza la descarga del PDF."""
        secreto = (self.cfg.get('secreto') or '').encode('utf-8')
        return hmac.new(secreto, f"pdf|{token}".encode('utf-8'),
                        hashlib.sha256).hexdigest()[:16]

    # ------------------------------------------------------ contenido del QR
    def contenido_qr(self, solicitud_id, numero_solicitud='', fecha='',
                     paciente='', cedula='', nombre_lab='', estado=''):
        """
        Contenido a codificar en el QR.

        Si el portal esta activo devuelve la URL de consulta (al escanear el
        telefono abre la pagina). Si no, devuelve el texto informativo clasico
        para que el QR siga siendo util sin servidor.
        """
        if self.cfg.get('activo'):
            url = self.url_solicitud(solicitud_id)
            if url:
                return url

        hash_ver = hashlib.sha256(
            f"{numero_solicitud}|{fecha}|{paciente}".encode('utf-8')
        ).hexdigest()[:12].upper()
        estado_qr = ('RESULTADOS LISTOS'
                     if (estado or '').strip().lower() in _ESTADOS_SOLICITUD_LISTA
                     else 'EN PROCESO')
        lineas = []
        if nombre_lab:
            lineas.append(nombre_lab)
        lineas.append(f"Orden: {numero_solicitud}")
        lineas.append(f"Paciente: {paciente}")
        if cedula:
            lineas.append(f"C.I.: {cedula}")
        lineas.append(f"Fecha: {fecha}")
        lineas.append(f"Estado: {estado_qr}")
        lineas.append(f"Verificacion: {hash_ver}")
        return '\n'.join(lineas)

    # --------------------------------------------------------------- estado
    def estado_solicitud(self, solicitud_id, conn=None):
        """
        Resumen del estado de una solicitud para mostrar al paciente.

        Returns dict con: encontrada, numero, fecha, paciente, documento,
        estado_solicitud, listo, anulada, total, listas, pruebas[].
        """
        origen = conn or self.db
        sid = int(solicitud_id)
        sol = origen.query_one(
            f"SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud, "
            f"s.EstadoSolicitud, s.FechaEntrega, s.FechaPrometida, "
            f"p.Nombres, p.Apellidos, p.NumeroDocumento "
            f"FROM [Solicitudes] AS s "
            f"LEFT JOIN [Pacientes] AS p ON s.PacienteID = p.PacienteID "
            f"WHERE s.SolicitudID={sid}")
        if not sol:
            return {'encontrada': False}

        detalles = origen.query(
            f"SELECT pr.NombrePrueba, pr.CodigoPrueba, ds.Estado "
            f"FROM [DetalleSolicitudes] AS ds "
            f"LEFT JOIN [Pruebas] AS pr ON ds.PruebaID = pr.PruebaID "
            f"WHERE ds.SolicitudID={sid} "
            f"ORDER BY pr.NombrePrueba") or []

        pruebas = []
        listas = 0
        for d in detalles:
            est = (d.get('Estado') or '').strip().lower()
            if est in _ESTADOS_LISTO:
                etiqueta, ok = 'Listo', True
                listas += 1
            elif est in _ESTADOS_EN_PROCESO:
                etiqueta, ok = 'En proceso', False
            else:
                etiqueta, ok = 'Pendiente', False
            pruebas.append({
                'nombre': d.get('NombrePrueba') or d.get('CodigoPrueba') or '-',
                'etiqueta': etiqueta,
                'listo': ok,
            })

        estado_sol = (sol.get('EstadoSolicitud') or '').strip()
        anulada = estado_sol.lower() == 'anulada'
        total = len(pruebas)
        listo = (not anulada) and total > 0 and (
            estado_sol.lower() in _ESTADOS_SOLICITUD_LISTA or listas == total)

        fecha = sol.get('FechaSolicitud')
        fecha_str = fecha.strftime('%d/%m/%Y') if hasattr(fecha, 'strftime') \
            else str(fecha or '')[:10]
        entrega = sol.get('FechaEntrega') or sol.get('FechaPrometida')
        entrega_str = entrega.strftime('%d/%m/%Y') if hasattr(entrega, 'strftime') \
            else ''

        nombre = f"{sol.get('Nombres') or ''} {sol.get('Apellidos') or ''}".strip()
        return {
            'encontrada': True,
            'solicitud_id': sid,
            'numero': sol.get('NumeroSolicitud') or f"SOL-{sid}",
            'fecha': fecha_str,
            'fecha_entrega': entrega_str,
            'paciente': nombre,
            'documento': sol.get('NumeroDocumento') or '',
            'estado_solicitud': estado_sol,
            'listo': listo,
            'anulada': anulada,
            'total': total,
            'listas': listas,
            'pruebas': pruebas,
        }


# ══════════════════════════════════════════════════════════════════════════
#  Generacion de imagenes QR
# ══════════════════════════════════════════════════════════════════════════
def qr_disponible():
    return QR_DISPONIBLE and PIL_DISPONIBLE


def qr_imagen(contenido, size_px=200):
    """Genera un PNG del QR y lo devuelve como BytesIO. None si falla."""
    if not qr_disponible() or not contenido:
        return None
    try:
        qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_M,
                           box_size=6, border=2)
        qr.add_data(contenido)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size_px, size_px), PILImage.NEAREST)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        return buf
    except Exception as e:
        _log.warning("QR no generado: %s", e)
        return None


def qr_imagereader(contenido, size_px=200):
    """QR listo para canvas.drawImage() de ReportLab. None si falla."""
    buf = qr_imagen(contenido, size_px)
    if buf is None:
        return None
    if REPORTLAB_DISPONIBLE:
        try:
            return ImageReader(buf)
        except Exception:
            return None
    return buf


# ══════════════════════════════════════════════════════════════════════════
#  Servidor HTTP del portal
# ══════════════════════════════════════════════════════════════════════════
_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
     background:#eef2f6;color:#1f2937;padding:16px;line-height:1.5}
.wrap{max-width:520px;margin:0 auto}
.card{background:#fff;border-radius:14px;padding:20px;margin-bottom:14px;
      box-shadow:0 1px 3px rgba(0,0,0,.10)}
.lab{text-align:center;font-size:15px;font-weight:700;color:#0f172a}
.sub{text-align:center;font-size:12px;color:#64748b;margin-top:2px}
.estado{text-align:center;padding:18px 12px;border-radius:12px;margin:4px 0 14px}
.ok{background:#dcfce7;color:#14532d}
.proc{background:#fef3c7;color:#78350f}
.anul{background:#fee2e2;color:#7f1d1d}
.estado .big{font-size:20px;font-weight:800;display:block}
.estado .small{font-size:13px;margin-top:4px;display:block}
.row{display:flex;justify-content:space-between;padding:7px 0;
     border-bottom:1px solid #f1f5f9;font-size:14px}
.row:last-child{border-bottom:none}
.row .k{color:#64748b}
.row .v{font-weight:600;text-align:right}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.5px;color:#64748b;
   margin-bottom:8px}
.tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px}
.tag.si{background:#dcfce7;color:#14532d}
.tag.no{background:#f1f5f9;color:#64748b}
.btn{display:block;width:100%;text-align:center;background:#0891b2;color:#fff;
     text-decoration:none;padding:14px;border-radius:10px;font-weight:700;
     font-size:15px;border:none;cursor:pointer}
.btn:active{background:#0e7490}
input[type=text]{width:100%;padding:12px;border:1px solid #cbd5e1;
     border-radius:10px;font-size:16px;margin-bottom:10px}
.err{background:#fee2e2;color:#7f1d1d;padding:10px;border-radius:8px;
     font-size:13px;margin-bottom:10px}
.nota{font-size:11px;color:#94a3b8;text-align:center;margin-top:14px}
"""


def _esc(txt):
    """Escapa HTML."""
    return (str(txt or '')
            .replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def _enmascarar(nombre):
    """'Juan Carlos Perez' -> 'Juan C. P.'"""
    partes = [p for p in str(nombre or '').split() if p]
    if not partes:
        return '-'
    return partes[0] + ''.join(f" {p[0]}." for p in partes[1:])


def _pagina(titulo, cuerpo):
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<meta name='robots' content='noindex,nofollow'>"
        f"<title>{_esc(titulo)}</title><style>{_CSS}</style></head>"
        f"<body><div class='wrap'>{cuerpo}</div></body></html>"
    )


class _Handler(BaseHTTPRequestHandler):
    server_version = 'ANgesLAB-Portal'
    portal = None  # inyectado por ServidorPortal

    # Silenciar el log a stderr de http.server
    def log_message(self, fmt, *args):
        _log.debug("portal %s - %s", self.address_string(), fmt % args)

    # ------------------------------------------------------------- helpers
    def _responder(self, cuerpo, codigo=200, tipo='text/html; charset=utf-8',
                   extra=None):
        datos = cuerpo if isinstance(cuerpo, bytes) else cuerpo.encode('utf-8')
        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(datos)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(datos)
        except Exception:
            pass

    def _error(self, mensaje, codigo=404):
        self._responder(_pagina('No disponible', (
            "<div class='card'>"
            "<div class='estado anul'><span class='big'>No disponible</span>"
            f"<span class='small'>{_esc(mensaje)}</span></div>"
            "<p class='nota'>Comuniquese con el laboratorio si necesita ayuda.</p>"
            "</div>")), codigo)

    def _ruta(self):
        p = urllib.parse.urlparse(self.path)
        partes = [s for s in p.path.split('/') if s]
        return partes, urllib.parse.parse_qs(p.query)

    # ---------------------------------------------------------------- GET
    def do_GET(self):
        partes, params = self._ruta()

        if not partes:
            return self._responder(_pagina('Portal de resultados', (
                "<div class='card'>"
                f"<div class='lab'>{_esc(self.portal.nombre_lab)}</div>"
                "<div class='sub'>Portal de consulta de resultados</div>"
                "<div class='estado proc' style='margin-top:14px'>"
                "<span class='big'>Escanee su codigo QR</span>"
                "<span class='small'>Encuentrelo en su recibo o en la "
                "etiqueta de su muestra</span></div></div>")))

        if partes[0] == 'favicon.ico':
            return self._responder(b'', 204, 'image/x-icon')

        if partes[0] != 'r' or len(partes) < 2:
            return self._error('La direccion no es valida.')

        token = partes[1]
        if len(partes) >= 3 and partes[2] == 'pdf':
            return self._servir_pdf(token, (params.get('k') or [''])[0])

        return self._servir_estado(token)

    # --------------------------------------------------------------- POST
    def do_POST(self):
        partes, _ = self._ruta()
        if not partes or partes[0] != 'r' or len(partes) < 2:
            return self._error('La direccion no es valida.')

        try:
            largo = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            largo = 0
        cuerpo = self.rfile.read(min(largo, 4096)).decode('utf-8', 'replace') \
            if largo > 0 else ''
        campos = urllib.parse.parse_qs(cuerpo)
        documento = (campos.get('documento') or [''])[0]
        return self._servir_estado(partes[1], documento_ingresado=documento)

    # ------------------------------------------------------------- paginas
    def _servir_estado(self, token, documento_ingresado=None):
        portal = self.portal
        try:
            with ConexionPortal(portal.db_path) as conn:
                gestor = GestorPortalResultados(conn)
                sid = gestor.solicitud_de_token(token)
                if sid is None:
                    return self._error(
                        'El codigo QR no es valido o ya expiro.')
                gestor.registrar_vista(token)
                info = gestor.estado_solicitud(sid, conn=conn)
        except Exception as e:
            _log.error("Portal: error consultando estado: %s", e, exc_info=True)
            return self._error('No se pudo consultar en este momento.', 500)

        if not info.get('encontrada'):
            return self._error('La solicitud no existe.')

        esperado = _solo_digitos(info['documento'])
        # Si la ficha no tiene documento registrado no hay nada que verificar
        requiere = bool(portal.cfg.get('requiere_documento', True)) and bool(esperado)
        verificado = not requiere
        error_doc = ''
        if requiere and documento_ingresado is not None:
            recibido = _solo_digitos(documento_ingresado)
            if recibido and (
                    recibido == esperado or
                    (len(recibido) >= 4 and esperado.endswith(recibido))):
                verificado = True
            else:
                error_doc = 'El numero de documento no coincide.'

        # ── Bloque de estado ──────────────────────────────────────────────
        if info['anulada']:
            clase, grande, chico = ('anul', 'Solicitud anulada',
                                    'Consulte en el laboratorio.')
        elif info['listo']:
            clase, grande, chico = ('ok', 'Resultados listos',
                                    'Ya puede ver y descargar su informe.')
        else:
            pend = info['total'] - info['listas']
            clase, grande = 'proc', 'En proceso'
            chico = (f"{info['listas']} de {info['total']} pruebas listas"
                     if info['total'] else 'Su muestra esta en analisis.')
            if info['fecha_entrega']:
                chico += f" &bull; Entrega estimada: {_esc(info['fecha_entrega'])}"
            if pend <= 0 and info['total']:
                chico = 'Pendiente de validacion por el bioanalista.'

        nombre = info['paciente'] if verificado else _enmascarar(info['paciente'])

        html = [
            "<div class='card'>",
            f"<div class='lab'>{_esc(portal.nombre_lab)}</div>",
            "<div class='sub'>Consulta de resultados</div></div>",
            "<div class='card'>",
            f"<div class='estado {clase}'><span class='big'>{grande}</span>"
            f"<span class='small'>{chico}</span></div>",
            f"<div class='row'><span class='k'>Orden</span>"
            f"<span class='v'>{_esc(info['numero'])}</span></div>",
            f"<div class='row'><span class='k'>Paciente</span>"
            f"<span class='v'>{_esc(nombre)}</span></div>",
            f"<div class='row'><span class='k'>Fecha</span>"
            f"<span class='v'>{_esc(info['fecha'])}</span></div>",
            "</div>",
        ]

        # ── Detalle de pruebas ────────────────────────────────────────────
        if info['pruebas']:
            html.append("<div class='card'><h2>Pruebas solicitadas</h2>")
            for p in info['pruebas']:
                cls = 'si' if p['listo'] else 'no'
                html.append(
                    f"<div class='row'><span class='k'>{_esc(p['nombre'])}</span>"
                    f"<span class='v'><span class='tag {cls}'>"
                    f"{_esc(p['etiqueta'])}</span></span></div>")
            html.append("</div>")

        # ── Acceso al PDF ─────────────────────────────────────────────────
        if info['listo'] and not info['anulada']:
            if verificado:
                clave = gestor_firma(portal.cfg, token)
                html.append(
                    "<div class='card'>"
                    f"<a class='btn' href='/r/{_esc(token)}/pdf?k={clave}'>"
                    "Ver / descargar resultados (PDF)</a>"
                    "<p class='nota'>Este informe es confidencial. "
                    "Su interpretacion corresponde a su medico tratante.</p>"
                    "</div>")
            else:
                html.append(
                    "<div class='card'><h2>Verifique su identidad</h2>")
                if error_doc:
                    html.append(f"<div class='err'>{_esc(error_doc)}</div>")
                html.append(
                    f"<form method='post' action='/r/{_esc(token)}'>"
                    "<input type='text' name='documento' inputmode='numeric' "
                    "autocomplete='off' placeholder='Cedula o ultimos 4 digitos'>"
                    "<button class='btn' type='submit'>Ver mis resultados</button>"
                    "</form>"
                    "<p class='nota'>Pedimos este dato para proteger la "
                    "confidencialidad de su informe.</p></div>")

        html.append("<p class='nota'>ANgesLAB &bull; Consulta generada "
                    f"{datetime.now().strftime('%d/%m/%Y %H:%M')}</p>")
        self._responder(_pagina('Resultados ' + info['numero'], ''.join(html)))

    def _servir_pdf(self, token, clave):
        portal = self.portal
        if not hmac.compare_digest(str(clave or ''),
                                   gestor_firma(portal.cfg, token)):
            return self._error('Enlace no autorizado.', 403)

        try:
            with ConexionPortal(portal.db_path) as conn:
                gestor = GestorPortalResultados(conn)
                sid = gestor.solicitud_de_token(token)
                if sid is None:
                    return self._error('El codigo QR no es valido o ya expiro.')
                info = gestor.estado_solicitud(sid, conn=conn)
                if not info.get('listo') or info.get('anulada'):
                    return self._error(
                        'Sus resultados todavia no estan disponibles.', 409)

                from modulos.envio_resultados import GeneradorPDF
                ruta = GeneradorPDF(conn).generar_pdf_resultados(sid)

            with open(ruta, 'rb') as f:
                datos = f.read()
            try:
                os.remove(ruta)
            except Exception:
                pass
        except Exception as e:
            _log.error("Portal: error generando PDF: %s", e, exc_info=True)
            return self._error('No se pudo generar el informe.', 500)

        nombre = f"Resultados_{info['numero']}.pdf".replace(' ', '_')
        self._responder(datos, 200, 'application/pdf',
                        {'Content-Disposition': f'inline; filename="{nombre}"'})


def gestor_firma(cfg, token):
    """HMAC del enlace al PDF (independiente de la conexion a la BD)."""
    secreto = (cfg.get('secreto') or '').encode('utf-8')
    return hmac.new(secreto, f"pdf|{token}".encode('utf-8'),
                    hashlib.sha256).hexdigest()[:16]


class ServidorPortal:
    """Mini servidor HTTP en un hilo daemon."""

    def __init__(self, db_path, cfg=None, nombre_lab='LABORATORIO'):
        self.db_path = db_path
        self.cfg = cfg or ConfigPortal.cargar()
        self.nombre_lab = nombre_lab
        self.httpd = None
        self.hilo = None

    @property
    def activo(self):
        return self.httpd is not None

    def iniciar(self):
        if self.httpd:
            return True
        puerto = int(self.cfg.get('puerto', 8770))
        handler = type('_HandlerPortal', (_Handler,), {'portal': self})
        try:
            self.httpd = ThreadingHTTPServer(('0.0.0.0', puerto), handler)
        except OSError as e:
            _log.error("Portal: puerto %s no disponible (%s)", puerto, e)
            self.httpd = None
            return False
        self.httpd.daemon_threads = True
        self.hilo = threading.Thread(target=self.httpd.serve_forever,
                                     name='ANgesLAB-Portal', daemon=True)
        self.hilo.start()
        _log.info("Portal de resultados escuchando en puerto %s", puerto)
        return True

    def detener(self):
        if not self.httpd:
            return
        try:
            self.httpd.shutdown()
            self.httpd.server_close()
        except Exception:
            pass
        self.httpd = None
        self.hilo = None
        _log.info("Portal de resultados detenido")


# ══════════════════════════════════════════════════════════════════════════
#  Singleton de la aplicacion
# ══════════════════════════════════════════════════════════════════════════
_servidor = None


def iniciar_portal(db, nombre_lab='LABORATORIO'):
    """
    Levanta el portal si esta activo en configuracion.
    Retorna el ServidorPortal o None. Nunca lanza excepcion.
    """
    global _servidor
    try:
        cfg = ConfigPortal.cargar()
        if not cfg.get('activo'):
            return None
        if _servidor and _servidor.activo:
            return _servidor
        ruta = getattr(db, 'db_path', None)
        if not ruta or not os.path.exists(ruta):
            _log.warning("Portal: ruta de BD no disponible")
            return None
        _servidor = ServidorPortal(ruta, cfg, nombre_lab)
        return _servidor if _servidor.iniciar() else None
    except Exception as e:
        _log.error("Portal: no se pudo iniciar (%s)", e)
        return None


def detener_portal():
    global _servidor
    if _servidor:
        _servidor.detener()
        _servidor = None


def portal_en_ejecucion():
    return bool(_servidor and _servidor.activo)


def crear_gestor_portal(db):
    """Factory del gestor de tokens."""
    return GestorPortalResultados(db)

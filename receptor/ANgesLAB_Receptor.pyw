# -*- coding: utf-8 -*-
"""
================================================================================
ANgesLAB RECEPTOR - la mitad que imprime, en la sede que toma las muestras
================================================================================
Vigila una carpeta sincronizada y manda al papel cada informe que aparece.

    Sede A (procesa)                     Sede B (toma muestras)
    ----------------                     ----------------------
    valida el resultado
    pulsa «Enviar a sede»
        |                                 ESTE programa, vigilando
        v                                        |
    PDF a la carpeta  --- Drive/OneDrive --->  lo ve llegar
                                                 |
                                             imprime  ->  papel

Esta sede NO tiene ANgesLAB ni base de datos. Este programa solo sabe mirar
una carpeta e imprimir: no puede consultar ni modificar ningun resultado. Esa
limitacion es la garantia de que el informe no se altera de camino, y por eso
el circuito se hace con archivos y no dando acceso remoto a la base.

QUE HACE CON CADA ARCHIVO

    1. Espera a que deje de crecer. El emisor escribe como .tmp y renombra al
       terminar, asi que el PDF nunca deberia verse a medias; pero una carpeta
       sincronizada puede entregar el archivo mientras baja, y una hoja en
       blanco no se nota hasta que el paciente reclama.
    2. Lo imprime.
    3. Lo MUEVE a impresos/AAAA-MM/. Nunca se borra nada: si una hoja sale
       mal, el PDF sigue ahi para repetirla.
    4. Si la impresion falla, va a errores/ y queda anotado en el registro.
       No se reintenta en bucle: un atasco de papel repetido cien veces llena
       la cola y no arregla nada.

POR QUE NO SE BORRA Y SE LLEVA REGISTRO

Porque quien atiende en la sede B no tiene forma de comprobar nada: no ve la
base, no ve el historial, solo el papel que sale. El registro y la carpeta de
impresos son lo unico con lo que puede responder a "este resultado nunca
llego".

QUE NECESITA PARA FUNCIONAR

    modulos/impresoras.py      el motor de impresion del propio ANgesLAB
    modulos/logging_config.py  del que depende el anterior
    PyMuPDF y pywin32          las librerias que usa ese motor

Se reutiliza el motor de ANgesLAB en vez de escribir otro: es el que ya esta
probado contra estas impresoras, y dos motores distintos acabarian sacando el
mismo informe de dos maneras.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# El motor de impresion vive en modulos/, un nivel por encima
_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAIZ = os.path.dirname(_AQUI)
for _p in (_RAIZ, _AQUI):
    if _p not in sys.path:
        sys.path.insert(0, _p)

CONFIG = os.path.join(_AQUI, 'receptor_config.json')
REGISTRO = os.path.join(_AQUI, 'receptor.log')

# Cada cuanto se mira la carpeta. Cinco segundos es imperceptible para quien
# espera el papel y no castiga al disco ni a la sincronizacion.
INTERVALO = 5.0

# Un archivo se considera completo cuando su tamano no cambia entre dos
# lecturas separadas por esto.
ESPERA_ESTABLE = 1.5


def _ahora():
    return datetime.now().strftime('%d/%m/%Y %H:%M:%S')


def cargar_config():
    try:
        with open(CONFIG, encoding='utf-8') as f:
            d = json.load(f)
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return {'carpeta': '', 'impresora': '', 'copias': 1, 'arranque': False}


def guardar_config(datos):
    try:
        with open(CONFIG, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def anotar(texto):
    """Una linea en el registro. Es lo unico con lo que la sede B responde."""
    try:
        with open(REGISTRO, 'a', encoding='utf-8') as f:
            f.write('%s  %s\n' % (_ahora(), texto))
    except Exception:
        pass


def esta_completo(ruta):
    """
    True si el archivo ya no crece.

    Con una carpeta sincronizada el archivo puede aparecer mientras todavia
    se esta descargando. Imprimirlo entonces saca una hoja en blanco o
    cortada, y nadie se entera hasta que el paciente reclama.
    """
    try:
        t1 = os.path.getsize(ruta)
    except OSError:
        return False
    time.sleep(ESPERA_ESTABLE)
    try:
        return os.path.getsize(ruta) == t1 and t1 > 0
    except OSError:
        return False


def carpeta_destino(base, sub):
    """impresos/AAAA-MM o errores/, creada si hace falta."""
    if sub == 'impresos':
        ruta = os.path.join(base, 'impresos', datetime.now().strftime('%Y-%m'))
    else:
        ruta = os.path.join(base, sub)
    os.makedirs(ruta, exist_ok=True)
    return ruta


def mover(ruta, destino):
    """
    Mueve sin pisar: si ya existe uno con ese nombre se le anade la hora.

    Un mismo paciente puede recibir dos veces el mismo informe -una
    correccion, una reimpresion- y machacar el anterior borraria la prueba de
    que el primero se imprimio.
    """
    nombre = os.path.basename(ruta)
    final = os.path.join(destino, nombre)
    if os.path.exists(final):
        raiz, ext = os.path.splitext(nombre)
        final = os.path.join(destino, '%s_%s%s'
                             % (raiz, datetime.now().strftime('%H%M%S'), ext))
    os.replace(ruta, final)
    return final


class Receptor:
    """El bucle que vigila e imprime. No toca la interfaz: le manda avisos."""

    def __init__(self, avisos):
        self.avisos = avisos
        self._parar = threading.Event()
        self._hilo = None
        self.impresos = 0
        self.fallidos = 0

    def activo(self):
        return self._hilo is not None and self._hilo.is_alive()

    def arrancar(self, carpeta, impresora, copias=1):
        if self.activo():
            return
        self._parar.clear()
        self._hilo = threading.Thread(
            target=self._bucle, args=(carpeta, impresora, int(copias or 1)),
            daemon=True)
        self._hilo.start()

    def detener(self):
        self._parar.set()

    def _aviso(self, texto, clase='info'):
        self.avisos.put((clase, texto))
        anotar(texto)

    def _bucle(self, carpeta, impresora, copias):
        self._aviso('Vigilando %s' % carpeta, 'ok')
        try:
            from modulos.impresoras import enviar_documento
        except Exception as e:
            self._aviso('No se pudo cargar el motor de impresion: %s' % e,
                        'error')
            self.avisos.put(('fin', ''))
            return

        while not self._parar.is_set():
            try:
                if not os.path.isdir(carpeta):
                    # Caso corriente: Drive aun no monto la unidad, o no hay
                    # red. Se avisa y se sigue esperando, no se muere.
                    self._aviso('La carpeta no esta disponible, esperando...',
                                'aviso')
                    self._parar.wait(INTERVALO * 4)
                    continue

                pendientes = sorted(
                    n for n in os.listdir(carpeta)
                    if n.lower().endswith('.pdf')
                    and os.path.isfile(os.path.join(carpeta, n)))

                for nombre in pendientes:
                    if self._parar.is_set():
                        break
                    ruta = os.path.join(carpeta, nombre)
                    if not esta_completo(ruta):
                        continue
                    self._imprimir_uno(ruta, nombre, carpeta, impresora,
                                       copias, enviar_documento)
            except Exception as e:
                self._aviso('Fallo vigilando la carpeta: %s' % e, 'error')

            self._parar.wait(INTERVALO)

        self._aviso('Detenido', 'aviso')
        self.avisos.put(('fin', ''))

    def _imprimir_uno(self, ruta, nombre, carpeta, impresora, copias, enviar):
        try:
            estado = enviar(ruta, impresora, copias=copias,
                            titulo='ANgesLAB %s' % nombre)
        except Exception as e:
            estado = {'ok': False, 'error': str(e)}

        ok = bool(estado.get('ok')) if isinstance(estado, dict) else bool(estado)
        if ok:
            destino = mover(ruta, carpeta_destino(carpeta, 'impresos'))
            self.impresos += 1
            self._aviso('IMPRESO  %s' % nombre, 'ok')
            self.avisos.put(('contador', ''))
            return destino

        motivo = (estado.get('error') if isinstance(estado, dict) else '') \
            or 'la impresora no acepto el documento'
        try:
            mover(ruta, carpeta_destino(carpeta, 'errores'))
        except Exception:
            pass
        self.fallidos += 1
        # No se reintenta: un atasco repetido cien veces llena la cola y no
        # arregla nada. Queda en errores/ para repetirlo a mano.
        self._aviso('FALLO    %s  ->  %s' % (nombre, motivo), 'error')
        self.avisos.put(('contador', ''))
        return None


class Ventana:
    COLOR = {'ok': '#15803d', 'error': '#b91c1c', 'aviso': '#b45309',
             'info': '#334155'}

    def __init__(self, raiz):
        self.raiz = raiz
        self.cfg = cargar_config()
        self.avisos = queue.Queue()
        self.receptor = Receptor(self.avisos)

        raiz.title('ANgesLAB Receptor')
        raiz.geometry('760x520')
        raiz.minsize(640, 440)

        tk.Label(raiz, text='ANgesLAB Receptor',
                 font=('Segoe UI', 14, 'bold'), bg='#0891b2', fg='white',
                 pady=10).pack(fill='x')
        tk.Label(raiz, text='Imprime los informes que llegan de la sede central',
                 font=('Segoe UI', 9), fg='#475569').pack(pady=(6, 10))

        cfg = ttk.LabelFrame(raiz, text=' Configuración ', padding=12)
        cfg.pack(fill='x', padx=14)
        cfg.columnconfigure(1, weight=1)

        ttk.Label(cfg, text='Carpeta vigilada:').grid(row=0, column=0,
                                                      sticky='w', pady=4)
        self.var_carpeta = tk.StringVar(value=self.cfg.get('carpeta', ''))
        ttk.Entry(cfg, textvariable=self.var_carpeta).grid(
            row=0, column=1, sticky='ew', padx=8)
        ttk.Button(cfg, text='Elegir...', command=self._elegir).grid(row=0,
                                                                     column=2)

        ttk.Label(cfg, text='Impresora:').grid(row=1, column=0, sticky='w',
                                               pady=4)
        nombres, predeterminada = self._impresoras()
        self.combo = ttk.Combobox(cfg, state='readonly', values=nombres)
        self.combo.grid(row=1, column=1, sticky='ew', padx=8)
        # La guardada manda; si no hay, la predeterminada del equipo, que es
        # donde el personal espera que salga el papel.
        if self.cfg.get('impresora') in nombres:
            self.combo.set(self.cfg['impresora'])
        elif predeterminada in nombres:
            self.combo.set(predeterminada)
        elif nombres:
            self.combo.current(0)

        ttk.Label(cfg, text='Copias:').grid(row=2, column=0, sticky='w', pady=4)
        self.var_copias = tk.StringVar(value=str(self.cfg.get('copias', 1)))
        ttk.Spinbox(cfg, from_=1, to=5, width=5,
                    textvariable=self.var_copias).grid(row=2, column=1,
                                                       sticky='w', padx=8)

        self.var_arranque = tk.BooleanVar(value=bool(self.cfg.get('arranque')))
        ttk.Checkbutton(cfg, text='Empezar a vigilar al abrir el programa',
                        variable=self.var_arranque).grid(row=3, column=1,
                                                         sticky='w', padx=8,
                                                         pady=(6, 0))

        barra = tk.Frame(raiz)
        barra.pack(fill='x', padx=14, pady=10)
        self.btn = tk.Button(barra, text='▶  Empezar a vigilar',
                             font=('Segoe UI', 11, 'bold'), bg='#059669',
                             fg='white', relief='flat', padx=18, pady=8,
                             cursor='hand2', command=self._alternar)
        self.btn.pack(side='left')
        self.lbl_estado = tk.Label(barra, text='Detenido',
                                   font=('Segoe UI', 10, 'bold'), fg='#64748b')
        self.lbl_estado.pack(side='left', padx=14)
        self.lbl_cuenta = tk.Label(barra, text='', font=('Segoe UI', 9),
                                   fg='#475569')
        self.lbl_cuenta.pack(side='right')

        reg = ttk.LabelFrame(raiz, text=' Registro ', padding=8)
        reg.pack(fill='both', expand=True, padx=14, pady=(0, 14))
        self.txt = tk.Text(reg, font=('Consolas', 9), wrap='none',
                           state='disabled', bg='#f8fafc')
        barra_v = ttk.Scrollbar(reg, command=self.txt.yview)
        self.txt.configure(yscrollcommand=barra_v.set)
        barra_v.pack(side='right', fill='y')
        self.txt.pack(fill='both', expand=True)
        for clase, color in self.COLOR.items():
            self.txt.tag_configure(clase, foreground=color)

        raiz.protocol('WM_DELETE_WINDOW', self._cerrar)
        self.raiz.after(200, self._vaciar_avisos)
        self._escribir('info', 'Listo. Elija la carpeta y la impresora.')
        if self.var_arranque.get() and self.var_carpeta.get():
            self.raiz.after(600, self._alternar)

    # ------------------------------------------------------------------
    @staticmethod
    def _impresoras():
        """
        (nombres, predeterminada). Nunca lanza: sin impresoras el programa
        tiene que abrir igual para que se vea por que no imprime.
        """
        try:
            # Devuelve una tupla, no una lista: desempaquetarla mal metia la
            # lista entera como si fuera un nombre de impresora.
            from modulos.impresoras import listar_impresoras
            nombres, predeterminada = listar_impresoras()
            return list(nombres or []), predeterminada or ''
        except Exception:
            try:
                import win32print
                flags = (win32print.PRINTER_ENUM_LOCAL
                         | win32print.PRINTER_ENUM_CONNECTIONS)
                nombres = [p[2] for p in win32print.EnumPrinters(flags)]
                return nombres, win32print.GetDefaultPrinter()
            except Exception:
                return [], ''

    def _elegir(self):
        d = filedialog.askdirectory(parent=self.raiz,
                                    title='Carpeta que llega de la sede central',
                                    initialdir=self.var_carpeta.get() or None)
        if d:
            self.var_carpeta.set(d)

    def _escribir(self, clase, texto):
        self.txt.configure(state='normal')
        self.txt.insert('end', '%s  %s\n' % (_ahora(), texto), clase)
        self.txt.see('end')
        self.txt.configure(state='disabled')

    def _alternar(self):
        if self.receptor.activo():
            self.receptor.detener()
            self.btn.configure(text='Deteniendo...', state='disabled')
            return

        carpeta = self.var_carpeta.get().strip()
        impresora = self.combo.get().strip()
        if not carpeta:
            messagebox.showwarning('Falta la carpeta',
                                   'Elija la carpeta que llega de la sede central.',
                                   parent=self.raiz)
            return
        if not impresora:
            messagebox.showwarning('Falta la impresora',
                                   'Elija en qué impresora salen los informes.',
                                   parent=self.raiz)
            return

        self.cfg = {'carpeta': carpeta, 'impresora': impresora,
                    'copias': int(self.var_copias.get() or 1),
                    'arranque': bool(self.var_arranque.get())}
        guardar_config(self.cfg)

        self.receptor.arrancar(carpeta, impresora, self.cfg['copias'])
        self.btn.configure(text='■  Detener', bg='#b91c1c')
        self.lbl_estado.configure(text='Vigilando', fg='#15803d')

    def _vaciar_avisos(self):
        try:
            while True:
                clase, texto = self.avisos.get_nowait()
                if clase == 'fin':
                    self.btn.configure(text='▶  Empezar a vigilar',
                                       bg='#059669', state='normal')
                    self.lbl_estado.configure(text='Detenido', fg='#64748b')
                elif clase == 'contador':
                    self.lbl_cuenta.configure(
                        text='impresos: %d    con fallo: %d'
                             % (self.receptor.impresos, self.receptor.fallidos))
                else:
                    self._escribir(clase, texto)
        except queue.Empty:
            pass
        self.raiz.after(300, self._vaciar_avisos)

    def _cerrar(self):
        if self.receptor.activo():
            if not messagebox.askyesno(
                    'Salir',
                    'El receptor está vigilando. Si sale, los informes que '
                    'lleguen no se imprimirán.\n\n¿Salir de todas formas?',
                    parent=self.raiz):
                return
            self.receptor.detener()
        self.cfg['arranque'] = bool(self.var_arranque.get())
        guardar_config(self.cfg)
        self.raiz.destroy()


def main():
    raiz = tk.Tk()
    Ventana(raiz)
    raiz.mainloop()


if __name__ == '__main__':
    main()

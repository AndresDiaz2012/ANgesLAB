# -*- coding: utf-8 -*-
"""
================================================================================
PANEL DE IMPRESORAS POR FUNCION - ANgesLAB
================================================================================
Widget reutilizable para asignar una impresora a cada funcion del laboratorio
(resultados, cotizaciones, facturacion, recibos, etiquetas), fijar sus opciones
de papel y probarla.

Existe como modulo aparte porque el panel hace falta en dos ventanas distintas
(Configuracion Completa y Configuracion Administrativa). Cuando cada ventana
tenia su propia copia, las dos escribian las mismas columnas con criterios
distintos y una pisaba a la otra: el documento acababa saliendo por la
impresora equivocada. Con un solo panel compartido eso no puede repetirse.

Uso:

    panel = PanelImpresoras(contenedor, db, con_boton_guardar=True)
    panel.pack(fill='x')
    ...
    panel.guardar()          # persiste asignaciones y opciones

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox

from modulos.impresoras import (
    ROLES, ORDEN_ROLES, ROLES_COTIZACION, ROL_COTIZACIONES_DEFECTO,
    COLUMNA_ROL_COTIZACIONES, GestorImpresoras, listar_impresoras,
    estado_impresora, normalizar_opciones, opciones_defecto,
    generar_pagina_prueba, enviar_documento, motor_disponible,
    diagnostico_motor, es_impresora_virtual,
)

_log = logging.getLogger('angeslab.panel_impresoras')

SIN_ASIGNAR = '(sin asignar)'

# Etiquetas de la interfaz para los valores internos
ETIQUETAS_CALIDAD = {'alta': 'Alta', 'media': 'Media', 'borrador': 'Borrador'}
ETIQUETAS_ORIENTACION = {'vertical': 'Vertical', 'horizontal': 'Horizontal'}
ETIQUETAS_ESCALA = {
    'ajustar': 'Ajustar a la página (no amplía)',
    'real': 'Tamaño real (rollo / térmica)',
    'llenar': 'Llenar el área imprimible',
}
ETIQUETAS_ROL_COTIZACION = {
    'facturacion': 'Impresora de facturación',
    'resultados': 'Impresora de resultados',
}
# DMPAPER_*: 0 deja el papel que ya tenga configurado la impresora
PAPELES = (
    (0, 'El de la impresora'),
    (1, 'Carta  (8.5 x 11 pulg)'),
    (9, 'A4  (210 x 297 mm)'),
    (5, 'Oficio / Legal  (8.5 x 14 pulg)'),
    (11, 'A5  (148 x 210 mm)'),
    (256, 'Personalizado del driver'),
)


class PanelImpresoras(ttk.Frame):
    """Asignación de impresora, opciones de papel y prueba para cada función."""

    def __init__(self, parent, db, con_boton_guardar=True,
                 al_guardar=None, mostrar_titulo=True):
        """
        Args:
            parent: contenedor tkinter
            db: conexión a la base de datos
            con_boton_guardar: dibuja su propio botón «Guardar impresoras».
                Póngalo en False si la ventana ya tiene un guardado global que
                llamará a guardar().
            al_guardar: función a llamar después de guardar con éxito
            mostrar_titulo: dibuja el encabezado de la sección
        """
        super().__init__(parent)
        self.db = db
        self._al_guardar = al_guardar
        self._con_boton_guardar = con_boton_guardar

        self.combos = {}
        self.vars_directo = {}
        self.lbls_estado = {}
        self._opciones = {rol: opciones_defecto(rol) for rol in ORDEN_ROLES}
        self._impresoras_disponibles = []

        self._construir(mostrar_titulo)
        self.cargar()

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _construir(self, mostrar_titulo):
        if mostrar_titulo:
            ttk.Label(self, text="Impresoras por Función:",
                      font=('Segoe UI', 11, 'bold')).pack(anchor='w',
                                                          pady=(0, 2))
            ttk.Label(self,
                      text="Asigne una impresora a cada función. Puede repetir "
                           "la misma impresora en varias: cada documento se "
                           "envía por separado a la que le corresponda.",
                      foreground='#64748b', justify='left').pack(anchor='w',
                                                                 pady=(0, 8))

        # Sin PyMuPDF/pywin32 el sistema no imprime: solo abre el visor
        if not motor_disponible():
            faltan = ', '.join(diagnostico_motor()) or 'PyMuPDF'
            ttk.Label(
                self,
                text=("⚠ Este equipo no puede imprimir directamente: falta "
                      f"{faltan}. Mientras tanto los documentos solo se abren "
                      "en el visor de PDF.\n   Instale las librerías con:  "
                      "pip install -r requirements.txt"),
                foreground='#b45309', justify='left').pack(anchor='w',
                                                           pady=(0, 8))

        self.frame_filas = ttk.Frame(self)
        self.frame_filas.pack(anchor='w', fill='x')
        self._construir_filas()

        acciones = ttk.Frame(self)
        acciones.pack(anchor='w', fill='x', pady=(8, 0))
        ttk.Button(acciones, text="🔄 Detectar impresoras",
                   command=self.refrescar).pack(side='left')
        if self._con_boton_guardar:
            ttk.Button(acciones, text="💾 Guardar impresoras",
                       command=self._guardar_desde_boton).pack(side='left',
                                                               padx=6)
        self.lbl_resumen = ttk.Label(acciones, text="", foreground='#64748b')
        self.lbl_resumen.pack(side='left', padx=10)

        # ── Respaldo de las cotizaciones ──────────────────────────────────
        cot = ttk.Frame(self)
        cot.pack(anchor='w', fill='x', pady=(12, 0))
        ttk.Label(cot, text="Si Cotizaciones no tiene impresora propia, "
                            "salen por:").pack(side='left')
        self.var_rol_cotizaciones = tk.StringVar(
            value=ETIQUETAS_ROL_COTIZACION[ROL_COTIZACIONES_DEFECTO])
        ttk.Combobox(cot, textvariable=self.var_rol_cotizaciones,
                     values=list(ETIQUETAS_ROL_COTIZACION.values()),
                     state='readonly', width=30).pack(side='left', padx=8)

        ttk.Label(self,
                  text="«Directo» (activado de fábrica) envía el documento a "
                       "esa impresora sin preguntar nada: ni margenes, ni "
                       "selección de impresora.\nDesmárquelo solo si prefiere "
                       "que esa función muestre el diálogo de impresión cada "
                       "vez.\n«Opciones» define papel, orientación, calidad, "
                       "escala y copias de esa función. Si una función se deja "
                       "sin impresora,\nel sistema la pedirá en el momento de "
                       "imprimir.",
                  foreground='#94a3b8', justify='left').pack(anchor='w',
                                                             pady=(10, 0))

    def _construir_filas(self):
        """Dibuja una fila por función: impresora, directo, estado, acciones."""
        for hijo in self.frame_filas.winfo_children():
            hijo.destroy()
        self.combos.clear()
        self.vars_directo.clear()
        self.lbls_estado.clear()

        nombres, predeterminada = listar_impresoras()
        self._impresoras_disponibles = nombres
        valores = [SIN_ASIGNAR] + nombres

        for texto, col in (('Función', 0), ('Impresora', 1), ('Directo', 2),
                           ('Estado', 3)):
            ttk.Label(self.frame_filas, text=texto,
                      font=('Segoe UI', 9, 'bold')).grid(
                          row=0, column=col, sticky='w',
                          padx=(8 if col else 0, 0))

        for i, rol in enumerate(ORDEN_ROLES, start=1):
            info = ROLES[rol]
            ttk.Label(self.frame_filas, text=info['etiqueta']).grid(
                row=i, column=0, sticky='w', pady=3)

            combo = ttk.Combobox(self.frame_filas, values=valores,
                                 state='readonly', width=36)
            combo.set(SIN_ASIGNAR)
            combo.grid(row=i, column=1, sticky='w', padx=8, pady=3)
            combo.bind('<<ComboboxSelected>>',
                       lambda _e, r=rol: self.refrescar_estado(r))
            self.combos[rol] = combo

            var = tk.BooleanVar(value=info['directo_defecto'])
            ttk.Checkbutton(self.frame_filas, variable=var).grid(
                row=i, column=2, sticky='w')
            self.vars_directo[rol] = var

            lbl = ttk.Label(self.frame_filas, text='—', width=26,
                            foreground='#94a3b8')
            lbl.grid(row=i, column=3, sticky='w', padx=(8, 0))
            self.lbls_estado[rol] = lbl

            acciones = ttk.Frame(self.frame_filas)
            acciones.grid(row=i, column=4, sticky='w', padx=(6, 0))
            ttk.Button(acciones, text='⚙ Opciones', width=11,
                       command=lambda r=rol: self.editar_opciones(r)
                       ).pack(side='left')
            ttk.Button(acciones, text='🖨 Probar', width=10,
                       command=lambda r=rol: self.probar(r)
                       ).pack(side='left', padx=4)

            ttk.Label(self.frame_filas, text=info['ayuda'],
                      foreground='#94a3b8').grid(row=i, column=5, sticky='w',
                                                 padx=(10, 0))
            self.refrescar_estado(rol)

        if hasattr(self, 'lbl_resumen'):
            self.lbl_resumen.config(
                text=(f"{len(nombres)} impresora(s) detectada(s)"
                      + (f" · predeterminada: {predeterminada}"
                         if predeterminada else ''))
                if nombres else "No se detectaron impresoras instaladas.")

    # ------------------------------------------------------------------
    # Estado y refresco
    # ------------------------------------------------------------------
    def refrescar_estado(self, rol):
        """Consulta el spooler y pinta cómo está la impresora de ese rol."""
        lbl = self.lbls_estado.get(rol)
        combo = self.combos.get(rol)
        if lbl is None or combo is None:
            return
        nombre = combo.get()
        if not nombre or nombre == SIN_ASIGNAR:
            lbl.config(text='Sin asignar', foreground='#94a3b8')
            return
        if es_impresora_virtual(nombre):
            # Asignar aquí «Microsoft Print to PDF» equivale a no imprimir:
            # el documento se queda en un archivo y nunca sale en papel
            lbl.config(text='No imprime: genera PDF', foreground='#d97706')
            return
        info = estado_impresora(nombre)
        if not info['existe']:
            color = '#dc2626'
        elif info['bloqueada']:
            color = '#d97706'
        else:
            color = '#16a34a'
        lbl.config(text=info['texto'][:30], foreground=color)

    def refrescar(self):
        """Vuelve a leer las impresoras del sistema conservando la selección."""
        seleccion = {rol: c.get() for rol, c in self.combos.items()}
        directos = {rol: v.get() for rol, v in self.vars_directo.items()}
        self._construir_filas()
        for rol, combo in self.combos.items():
            valor = seleccion.get(rol, SIN_ASIGNAR)
            if valor not in combo['values'] and valor != SIN_ASIGNAR:
                # Una impresora desconectada no se pierde de la configuración
                combo['values'] = list(combo['values']) + [valor]
            combo.set(valor)
            self.vars_directo[rol].set(directos.get(rol, False))
            self.refrescar_estado(rol)

    # ------------------------------------------------------------------
    # Carga y guardado
    # ------------------------------------------------------------------
    def cargar(self):
        """Refleja en la interfaz lo que hay guardado en la base de datos."""
        try:
            gestor = GestorImpresoras(self.db)
            asignaciones = gestor.asignaciones(refrescar=True)
            self._opciones = gestor.todas_las_opciones()
            rol_cot = gestor.rol_cotizaciones()
        except Exception as e:
            _log.warning("No se pudo leer la configuración de impresoras: %s", e)
            asignaciones = {}
            rol_cot = ROL_COTIZACIONES_DEFECTO

        self.var_rol_cotizaciones.set(
            ETIQUETAS_ROL_COTIZACION.get(rol_cot,
                                         ETIQUETAS_ROL_COTIZACION[
                                             ROL_COTIZACIONES_DEFECTO]))

        for rol in ORDEN_ROLES:
            combo = self.combos.get(rol)
            if combo is None:
                continue
            datos = asignaciones.get(rol) or {}
            guardada = (datos.get('impresora') or '').strip()
            if guardada:
                # Se muestra aunque ya no exista, para no perder la asignación
                if guardada not in combo['values']:
                    combo['values'] = list(combo['values']) + [guardada]
                combo.set(guardada)
            else:
                combo.set(SIN_ASIGNAR)
            self.vars_directo[rol].set(
                bool(datos.get('directo', ROLES[rol]['directo_defecto'])))
            self.refrescar_estado(rol)

    def recolectar(self):
        """Asignaciones tal como están en pantalla."""
        salida = {}
        for rol in ORDEN_ROLES:
            combo = self.combos.get(rol)
            if combo is None:
                continue
            valor = combo.get()
            salida[rol] = {
                'impresora': '' if valor == SIN_ASIGNAR else valor,
                'directo': bool(self.vars_directo[rol].get()),
            }
        return salida

    def recolectar_opciones(self):
        """Opciones de papel/calidad de cada función, saneadas."""
        return {rol: normalizar_opciones(rol, self._opciones.get(rol))
                for rol in ORDEN_ROLES}

    def rol_cotizaciones(self):
        """Rol de respaldo elegido para las cotizaciones."""
        etiqueta = self.var_rol_cotizaciones.get()
        for rol, texto in ETIQUETAS_ROL_COTIZACION.items():
            if texto == etiqueta:
                return rol
        return ROL_COTIZACIONES_DEFECTO

    def guardar(self):
        """Persiste asignaciones, respaldo de cotizaciones y opciones."""
        try:
            return GestorImpresoras(self.db).guardar(
                self.recolectar(), self.rol_cotizaciones(),
                self.recolectar_opciones())
        except Exception as e:
            _log.error("No se pudieron guardar las impresoras: %s", e)
            return False

    def _guardar_desde_boton(self):
        """Guardado con confirmación, para el botón propio del panel."""
        if self.guardar():
            asignadas = sum(1 for d in self.recolectar().values()
                            if d['impresora'])
            messagebox.showinfo(
                "Impresoras",
                f"Configuración guardada.\n\n"
                f"{asignadas} de {len(ORDEN_ROLES)} funciones tienen impresora "
                "asignada.", parent=self.winfo_toplevel())
            if self._al_guardar:
                try:
                    self._al_guardar()
                except Exception as e:
                    _log.warning("Error en el callback de guardado: %s", e)
        else:
            messagebox.showerror(
                "Impresoras", "No se pudo guardar la configuración de "
                "impresoras.", parent=self.winfo_toplevel())

    # ------------------------------------------------------------------
    # Opciones de papel / calidad
    # ------------------------------------------------------------------
    def editar_opciones(self, rol):
        """Diálogo de papel, orientación, calidad, escala y copias."""
        actuales = normalizar_opciones(rol, self._opciones.get(rol))
        info = ROLES[rol]
        raiz = self.winfo_toplevel()

        win = tk.Toplevel(raiz)
        win.title(f"Opciones de impresión · {info['etiqueta']}")
        win.transient(raiz)
        win.resizable(False, False)
        cuerpo = ttk.Frame(win, padding=16)
        cuerpo.pack(fill='both', expand=True)

        ttk.Label(cuerpo, text=info['etiqueta'],
                  font=('Segoe UI', 11, 'bold')).grid(row=0, column=0,
                                                      columnspan=2, sticky='w')
        ttk.Label(cuerpo, text=info['ayuda'], foreground='#64748b').grid(
            row=1, column=0, columnspan=2, sticky='w', pady=(0, 12))

        def _combo(fila, etiqueta, valores, actual, ancho=30):
            ttk.Label(cuerpo, text=etiqueta).grid(row=fila, column=0,
                                                  sticky='w', pady=4)
            var = tk.StringVar(value=actual)
            ttk.Combobox(cuerpo, textvariable=var, values=valores,
                         state='readonly', width=ancho).grid(
                             row=fila, column=1, sticky='w', padx=8, pady=4)
            return var

        var_papel = _combo(2, 'Papel:', [t for _, t in PAPELES],
                           dict(PAPELES).get(actuales['papel'],
                                             'El de la impresora'))
        var_orient = _combo(3, 'Orientación:',
                            list(ETIQUETAS_ORIENTACION.values()),
                            ETIQUETAS_ORIENTACION[actuales['orientacion']])
        var_calidad = _combo(4, 'Calidad:', list(ETIQUETAS_CALIDAD.values()),
                             ETIQUETAS_CALIDAD[actuales['calidad']])
        var_escala = _combo(5, 'Escala:', list(ETIQUETAS_ESCALA.values()),
                            ETIQUETAS_ESCALA[actuales['escala']])

        ttk.Label(cuerpo, text='Copias por documento:').grid(row=6, column=0,
                                                             sticky='w', pady=4)
        spin_copias = ttk.Spinbox(cuerpo, from_=1, to=20, width=6)
        spin_copias.set(actuales['copias'])
        spin_copias.grid(row=6, column=1, sticky='w', padx=8, pady=4)

        ttk.Label(cuerpo,
                  text="«Tamaño real» es lo correcto para tickets y etiquetas: "
                       "evita que el\nsistema estire un rollo de 80 mm hasta el "
                       "tamaño de una hoja.",
                  foreground='#94a3b8', justify='left').grid(
                      row=7, column=0, columnspan=2, sticky='w', pady=(10, 0))

        def _aceptar():
            papel = next((cod for cod, txt in PAPELES
                          if txt == var_papel.get()), 0)
            orientacion = next((k for k, v in ETIQUETAS_ORIENTACION.items()
                                if v == var_orient.get()), 'vertical')
            calidad = next((k for k, v in ETIQUETAS_CALIDAD.items()
                            if v == var_calidad.get()), 'alta')
            escala = next((k for k, v in ETIQUETAS_ESCALA.items()
                           if v == var_escala.get()), 'ajustar')
            try:
                copias = int(spin_copias.get())
            except Exception:
                copias = 1
            self._opciones[rol] = normalizar_opciones(rol, {
                'papel': papel, 'orientacion': orientacion,
                'calidad': calidad, 'escala': escala, 'copias': copias,
                'bandeja': actuales.get('bandeja', 0),
            })
            win.destroy()

        botones = ttk.Frame(cuerpo)
        botones.grid(row=8, column=0, columnspan=2, sticky='e', pady=(14, 0))
        ttk.Button(botones, text='Aceptar', command=_aceptar).pack(side='left')
        ttk.Button(botones, text='Cancelar',
                   command=win.destroy).pack(side='left', padx=6)

        win.grab_set()

    # ------------------------------------------------------------------
    # Página de prueba
    # ------------------------------------------------------------------
    def probar(self, rol):
        """Manda una página de prueba por la impresora de esa función."""
        raiz = self.winfo_toplevel()
        combo = self.combos.get(rol)
        impresora = combo.get() if combo else ''
        if not impresora or impresora == SIN_ASIGNAR:
            messagebox.showwarning(
                "Página de prueba",
                f"Asigne primero una impresora a «{ROLES[rol]['etiqueta']}».",
                parent=raiz)
            return

        faltan = diagnostico_motor()
        if faltan:
            messagebox.showerror(
                "Página de prueba",
                "Este equipo no puede imprimir directamente.\n\n"
                f"Falta instalar: {', '.join(faltan)}\n\n"
                "Ejecute:  pip install -r requirements.txt", parent=raiz)
            return

        if not messagebox.askyesno(
                "Página de prueba",
                f"Se enviará una página de prueba a:\n\n{impresora}\n\n"
                f"Función: {ROLES[rol]['etiqueta']}\n\n¿Continuar?",
                parent=raiz):
            return

        # Se prueba con lo que hay en pantalla aunque no se haya guardado, para
        # poder ajustar y volver a probar sin dar vueltas
        opciones = dict(normalizar_opciones(rol, self._opciones.get(rol)))
        opciones['copias'] = 1

        ruta = generar_pagina_prueba(rol, impresora, self._nombre_laboratorio())
        if not ruta:
            messagebox.showerror("Página de prueba",
                                 "No se pudo generar la página de prueba.",
                                 parent=raiz)
            return

        resultado = enviar_documento(ruta, impresora, 1, opciones,
                                     'ANgesLAB - Página de prueba')
        self.refrescar_estado(rol)
        if resultado['ok']:
            detalle = (f"\nTrabajo n° {resultado['trabajo']}"
                       if resultado.get('trabajo') else '')
            aviso = (f"\n\nOjo: la impresora reporta «{resultado['aviso']}»."
                     if resultado.get('aviso') else '')
            messagebox.showinfo(
                "Página de prueba",
                f"Enviada a {impresora}.{detalle}{aviso}\n\n"
                "Si no sale el papel, revise la cola de impresión de Windows.",
                parent=raiz)
        else:
            messagebox.showerror(
                "Página de prueba",
                f"No se pudo imprimir en {impresora}.\n\n"
                f"Motivo: {resultado.get('error') or 'desconocido'}",
                parent=raiz)

    def _nombre_laboratorio(self):
        """Nombre del laboratorio para la página de prueba (vacío si falla)."""
        try:
            cfg = self.db.query_one(
                "SELECT NombreLaboratorio FROM ConfiguracionLaboratorio") or {}
            return (cfg.get('NombreLaboratorio') or '').strip()
        except Exception:
            return ''

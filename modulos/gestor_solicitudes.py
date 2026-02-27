# -*- coding: utf-8 -*-
"""
Gestor de Solicitudes - ANgesLAB
================================================================================
Módulo centralizado para la gestión de solicitudes de laboratorio.

Funcionalidades:
- Buscar solicitudes activas de un paciente
- Crear nuevas solicitudes con transacciones
- Agregar pruebas a solicitudes existentes
- Generar recibos o facturas según selección
- Control de permisos por rol

Copyright 2024-2025 ANgesLAB Solutions
================================================================================
"""

from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
import tkinter as tk
from tkinter import ttk, messagebox

# Importar ControlAcceso si está disponible
try:
    from modulos.modulo_administrativo import ControlAcceso
    CONTROL_ACCESO_DISPONIBLE = True
except ImportError:
    CONTROL_ACCESO_DISPONIBLE = False


# ============================================================================
# PERMISOS POR ROL
# ============================================================================

PERMISOS_SOLICITUDES = {
    'Desarrollador': {
        'crear_solicitud': True,
        'agregar_pruebas': True,
        'modificar_pruebas': True,
        'eliminar_pruebas': True,
        'generar_recibo': True,
        'generar_factura': True,
        'anular_documento': True,
        'ver_historial': True,
        'editar_solicitud': True,
    },
    'Admin': {
        'crear_solicitud': True,
        'agregar_pruebas': True,
        'modificar_pruebas': True,
        'eliminar_pruebas': True,
        'generar_recibo': True,
        'generar_factura': True,
        'anular_documento': True,
        'ver_historial': True,
        'editar_solicitud': True,
    },
    'Administrador': {
        'crear_solicitud': True,
        'agregar_pruebas': True,
        'modificar_pruebas': True,
        'eliminar_pruebas': True,
        'generar_recibo': True,
        'generar_factura': True,
        'anular_documento': True,
        'ver_historial': True,
        'editar_solicitud': True,
    },
    'Facturador': {
        'crear_solicitud': True,
        'agregar_pruebas': True,
        'modificar_pruebas': True,
        'eliminar_pruebas': True,
        'generar_recibo': True,
        'generar_factura': True,
        'anular_documento': False,
        'ver_historial': True,
        'editar_solicitud': True,
    },
    'Recepcion': {
        'crear_solicitud': True,
        'agregar_pruebas': True,
        'modificar_pruebas': False,
        'eliminar_pruebas': False,
        'generar_recibo': True,
        'generar_factura': False,
        'anular_documento': False,
        'ver_historial': True,
        'editar_solicitud': False,
    },
    'Bioanalista': {
        'crear_solicitud': False,
        'agregar_pruebas': False,
        'modificar_pruebas': False,
        'eliminar_pruebas': False,
        'generar_recibo': False,
        'generar_factura': False,
        'anular_documento': False,
        'ver_historial': True,
        'editar_solicitud': False,
    },
    'Consulta': {
        'crear_solicitud': False,
        'agregar_pruebas': False,
        'modificar_pruebas': False,
        'eliminar_pruebas': False,
        'generar_recibo': False,
        'generar_factura': False,
        'anular_documento': False,
        'ver_historial': True,
        'editar_solicitud': False,
    },
}


# ============================================================================
# CLASE PRINCIPAL: GESTOR DE SOLICITUDES
# ============================================================================

class GestorSolicitudes:
    """
    Gestor centralizado para toda la lógica de solicitudes.

    Attributes:
        db: Conexión a la base de datos
        usuario: Diccionario con datos del usuario actual
        control_acceso: Instancia de ControlAcceso para verificar permisos
    """

    # Tiempo máximo para considerar una solicitud como "activa" (horas)
    HORAS_SOLICITUD_ACTIVA = 48

    def __init__(self, db, usuario_actual=None):
        """
        Inicializa el gestor de solicitudes.

        Args:
            db: Objeto de conexión a la base de datos
            usuario_actual: Dict con datos del usuario (UsuarioID, NombreUsuario, Nivel, etc.)
        """
        self.db = db
        self.usuario = usuario_actual or {}

        # Inicializar control de acceso si está disponible
        if CONTROL_ACCESO_DISPONIBLE:
            self.control_acceso = ControlAcceso(db)
        else:
            self.control_acceso = None

        # Asegurar que existe la tabla Recibos
        self._verificar_tabla_recibos()

    # -------------------------------------------------------------------------
    # VERIFICACIÓN DE PERMISOS
    # -------------------------------------------------------------------------

    def tiene_permiso(self, accion):
        """
        Verifica si el usuario actual tiene permiso para una acción.

        Args:
            accion: Nombre de la acción (crear_solicitud, generar_factura, etc.)

        Returns:
            True si tiene permiso, False en caso contrario
        """
        # Si no hay usuario, denegar
        if not self.usuario:
            return False

        # Obtener nivel/rol del usuario
        nivel = self.usuario.get('Nivel', 'Consulta')

        # Si es Desarrollador, Admin o Administrador, permitir todo
        if nivel in ('Desarrollador', 'Admin', 'Administrador'):
            return True

        # Buscar en permisos predefinidos
        permisos_rol = PERMISOS_SOLICITUDES.get(nivel, PERMISOS_SOLICITUDES['Consulta'])
        return permisos_rol.get(accion, False)

    def verificar_permiso_con_mensaje(self, accion, mensaje_error=None):
        """
        Verifica permiso y muestra mensaje si no tiene acceso.

        Returns:
            True si tiene permiso, False si no (y muestra mensaje)
        """
        if self.tiene_permiso(accion):
            return True

        if mensaje_error is None:
            mensaje_error = f"No tiene permisos para: {accion.replace('_', ' ')}"

        messagebox.showwarning("Acceso Denegado", mensaje_error)
        return False

    # -------------------------------------------------------------------------
    # BÚSQUEDA DE SOLICITUDES
    # -------------------------------------------------------------------------

    def buscar_solicitudes_paciente(self, paciente_id, solo_activas=True):
        """
        Busca solicitudes de un paciente.

        Args:
            paciente_id: ID del paciente
            solo_activas: Si True, solo retorna solicitudes de las últimas 48h
                         que no estén completadas/anuladas

        Returns:
            Lista de diccionarios con las solicitudes encontradas
        """
        if not paciente_id:
            return []

        try:
            if solo_activas:
                # Calcular fecha límite
                fecha_limite = datetime.now() - timedelta(hours=self.HORAS_SOLICITUD_ACTIVA)
                fecha_str = fecha_limite.strftime('#%m/%d/%Y %H:%M:%S#')

                sql = f"""
                    SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud,
                           s.HoraSolicitud, s.EstadoSolicitud, s.MontoTotal,
                           s.PorcentajeDescuento, s.MontoDescuento, s.MontoIVA,
                           (SELECT COUNT(*) FROM DetalleSolicitudes d WHERE d.SolicitudID = s.SolicitudID) AS CantidadPruebas
                    FROM Solicitudes s
                    WHERE s.PacienteID = {paciente_id}
                    AND s.FechaSolicitud >= {fecha_str}
                    AND s.EstadoSolicitud NOT IN ('Completada', 'Entregada', 'Anulada')
                    ORDER BY s.FechaSolicitud DESC, s.SolicitudID DESC
                """
            else:
                sql = f"""
                    SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud,
                           s.HoraSolicitud, s.EstadoSolicitud, s.MontoTotal,
                           s.PorcentajeDescuento, s.MontoDescuento, s.MontoIVA,
                           (SELECT COUNT(*) FROM DetalleSolicitudes d WHERE d.SolicitudID = s.SolicitudID) AS CantidadPruebas
                    FROM Solicitudes s
                    WHERE s.PacienteID = {paciente_id}
                    ORDER BY s.FechaSolicitud DESC, s.SolicitudID DESC
                """

            return self.db.query(sql)

        except Exception as e:
            print(f"Error buscando solicitudes del paciente: {e}")
            return []

    def buscar_solicitudes_mismo_dia(self, paciente_id):
        """
        Busca solicitudes de un paciente creadas HOY (mismo día).
        Incluye todos los estados excepto Anulada.

        Args:
            paciente_id: ID del paciente

        Returns:
            Lista de diccionarios con las solicitudes del día
        """
        if not paciente_id:
            return []

        try:
            hoy = datetime.now().strftime('#%m/%d/%Y#')

            sql = f"""
                SELECT s.SolicitudID, s.NumeroSolicitud, s.FechaSolicitud,
                       s.HoraSolicitud, s.EstadoSolicitud, s.MontoTotal,
                       s.PorcentajeDescuento, s.MontoDescuento, s.MontoIVA,
                       (SELECT COUNT(*) FROM DetalleSolicitudes d WHERE d.SolicitudID = s.SolicitudID) AS CantidadPruebas
                FROM Solicitudes s
                WHERE s.PacienteID = {paciente_id}
                AND s.FechaSolicitud >= {hoy}
                AND s.EstadoSolicitud <> 'Anulada'
                ORDER BY s.FechaSolicitud DESC, s.SolicitudID DESC
            """
            return self.db.query(sql)

        except Exception as e:
            print(f"Error buscando solicitudes del mismo día: {e}")
            return []

    def obtener_solicitud(self, solicitud_id):
        """
        Obtiene los datos completos de una solicitud.

        Args:
            solicitud_id: ID de la solicitud

        Returns:
            Dict con los datos de la solicitud o None si no existe
        """
        try:
            sql = f"""
                SELECT s.*,
                       p.Nombres & ' ' & p.Apellidos AS NombrePaciente,
                       p.NumeroDocumento AS DocumentoPaciente
                FROM Solicitudes s
                LEFT JOIN Pacientes p ON s.PacienteID = p.PacienteID
                WHERE s.SolicitudID = {solicitud_id}
            """
            return self.db.query_one(sql)
        except Exception as e:
            print(f"Error obteniendo solicitud: {e}")
            return None

    def obtener_pruebas_solicitud(self, solicitud_id):
        """
        Obtiene las pruebas de una solicitud.

        Args:
            solicitud_id: ID de la solicitud

        Returns:
            Lista de dicts con las pruebas
        """
        try:
            sql = f"""
                SELECT d.DetalleID, d.PruebaID, d.PrecioUnitario, d.Cantidad,
                       d.Subtotal, d.Estado, d.Resultado,
                       p.CodigoPrueba, p.NombrePrueba
                FROM DetalleSolicitudes d
                LEFT JOIN Pruebas p ON d.PruebaID = p.PruebaID
                WHERE d.SolicitudID = {solicitud_id}
                ORDER BY p.NombrePrueba
            """
            return self.db.query(sql)
        except Exception as e:
            print(f"Error obteniendo pruebas de solicitud: {e}")
            return []

    # -------------------------------------------------------------------------
    # CREACIÓN Y MODIFICACIÓN DE SOLICITUDES
    # -------------------------------------------------------------------------

    def crear_solicitud(self, datos_solicitud, pruebas, config_numeracion=None):
        """
        Crea una nueva solicitud con sus pruebas.

        Args:
            datos_solicitud: Dict con datos de la solicitud
                - PacienteID (requerido)
                - MedicoID (opcional)
                - TipoServicio (opcional)
                - DiagnosticoPresuntivo (opcional)
                - Observaciones (opcional)
                - PorcentajeDescuento (opcional, default 0)
                - PorcentajeIVA (opcional, default 16)
            pruebas: Lista de dicts con {id, nombre, precio}
            config_numeracion: Configurador de numeración (opcional)

        Returns:
            Dict con {exito: bool, solicitud_id: int, numero: str, mensaje: str}
        """
        if not self.tiene_permiso('crear_solicitud'):
            return {
                'exito': False,
                'solicitud_id': None,
                'numero': None,
                'mensaje': 'No tiene permisos para crear solicitudes'
            }

        if not datos_solicitud.get('PacienteID'):
            return {
                'exito': False,
                'solicitud_id': None,
                'numero': None,
                'mensaje': 'Debe especificar un paciente'
            }

        if not pruebas:
            return {
                'exito': False,
                'solicitud_id': None,
                'numero': None,
                'mensaje': 'Debe agregar al menos una prueba'
            }

        try:
            # Generar número de solicitud
            if config_numeracion:
                try:
                    numero = config_numeracion.generar_numero_solicitud()
                except Exception as e:
                    print(f"Error generando número con configurador: {e}")
                    numero = self._generar_numero_solicitud_fallback()
            else:
                numero = self._generar_numero_solicitud_fallback()

            # Calcular totales
            subtotal = sum(float(p.get('precio', 0)) for p in pruebas)
            desc_pct = float(datos_solicitud.get('PorcentajeDescuento', 0))
            desc_monto = subtotal * (desc_pct / 100)
            base = subtotal - desc_monto
            iva_pct = float(datos_solicitud.get('PorcentajeIVA', 16))
            iva_monto = base * (iva_pct / 100)
            total = base + iva_monto

            # Datos de la solicitud
            data = {
                'NumeroSolicitud': numero,
                'FechaSolicitud': datetime.now(),
                'HoraSolicitud': datetime.now().strftime('%H:%M:%S'),
                'PacienteID': datos_solicitud['PacienteID'],
                'MedicoID': datos_solicitud.get('MedicoID'),
                'TipoServicio': datos_solicitud.get('TipoServicio', 'Particular'),
                'EstadoSolicitud': 'Pendiente',
                'DiagnosticoPresuntivo': datos_solicitud.get('DiagnosticoPresuntivo', ''),
                'Observaciones': datos_solicitud.get('Observaciones', ''),
                'PorcentajeDescuento': desc_pct,
                'MontoDescuento': desc_monto,
                'MontoIVA': iva_monto,
                'MontoNeto': base,
                'MontoTotal': total,
                'UsuarioRegistro': self.usuario.get('UsuarioID', 1),
                'FechaRegistro': datetime.now()
            }

            # Insertar solicitud
            self.db.insert('Solicitudes', data)

            # Obtener ID de la solicitud recién creada
            sol = self.db.query_one(f"SELECT SolicitudID FROM Solicitudes WHERE NumeroSolicitud='{numero}'")
            if not sol:
                raise Exception("No se pudo recuperar la solicitud creada")

            sol_id = sol['SolicitudID']

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
                self.db.insert('DetalleSolicitudes', detalle)

            return {
                'exito': True,
                'solicitud_id': sol_id,
                'numero': numero,
                'mensaje': f'Solicitud {numero} creada exitosamente',
                'total': total
            }

        except Exception as e:
            return {
                'exito': False,
                'solicitud_id': None,
                'numero': None,
                'mensaje': f'Error al crear solicitud: {str(e)}'
            }

    def agregar_pruebas_solicitud(self, solicitud_id, pruebas, recalcular_totales=True):
        """
        Agrega pruebas a una solicitud existente.

        Args:
            solicitud_id: ID de la solicitud
            pruebas: Lista de dicts con {id, nombre, precio}
            recalcular_totales: Si True, recalcula los totales de la solicitud

        Returns:
            Dict con {exito: bool, mensaje: str, nuevo_total: float}
        """
        if not self.tiene_permiso('agregar_pruebas'):
            return {
                'exito': False,
                'mensaje': 'No tiene permisos para agregar pruebas',
                'nuevo_total': None
            }

        if not solicitud_id:
            return {
                'exito': False,
                'mensaje': 'ID de solicitud no válido',
                'nuevo_total': None
            }

        if not pruebas:
            return {
                'exito': False,
                'mensaje': 'No hay pruebas para agregar',
                'nuevo_total': None
            }

        try:
            # Verificar que la solicitud existe y no está cerrada
            solicitud = self.obtener_solicitud(solicitud_id)
            if not solicitud:
                return {
                    'exito': False,
                    'mensaje': 'Solicitud no encontrada',
                    'nuevo_total': None
                }

            if solicitud.get('EstadoSolicitud') in ('Completada', 'Entregada', 'Anulada'):
                return {
                    'exito': False,
                    'mensaje': f"No se pueden agregar pruebas a una solicitud {solicitud.get('EstadoSolicitud')}",
                    'nuevo_total': None
                }

            # Obtener pruebas existentes para evitar duplicados
            pruebas_existentes = self.obtener_pruebas_solicitud(solicitud_id)
            ids_existentes = {p['PruebaID'] for p in pruebas_existentes}

            pruebas_agregadas = 0
            pruebas_duplicadas = 0

            for prueba in pruebas:
                if prueba['id'] in ids_existentes:
                    pruebas_duplicadas += 1
                    continue

                detalle = {
                    'SolicitudID': solicitud_id,
                    'PruebaID': prueba['id'],
                    'PrecioUnitario': prueba['precio'],
                    'Cantidad': 1,
                    'Subtotal': prueba['precio'],
                    'Estado': 'Pendiente'
                }
                self.db.insert('DetalleSolicitudes', detalle)
                pruebas_agregadas += 1
                ids_existentes.add(prueba['id'])

            nuevo_total = None
            if recalcular_totales and pruebas_agregadas > 0:
                nuevo_total = self._recalcular_totales_solicitud(solicitud_id)

            mensaje = f'Se agregaron {pruebas_agregadas} prueba(s)'
            if pruebas_duplicadas > 0:
                mensaje += f' ({pruebas_duplicadas} ya existían)'

            return {
                'exito': True,
                'mensaje': mensaje,
                'nuevo_total': nuevo_total,
                'pruebas_agregadas': pruebas_agregadas,
                'pruebas_duplicadas': pruebas_duplicadas
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Error al agregar pruebas: {str(e)}',
                'nuevo_total': None
            }

    def modificar_prueba_solicitud(self, detalle_id, solicitud_id, nuevo_precio):
        """
        Modifica el precio de una prueba en una solicitud existente.

        Args:
            detalle_id: ID del detalle (DetalleID)
            solicitud_id: ID de la solicitud
            nuevo_precio: Nuevo precio unitario

        Returns:
            Dict con {exito: bool, mensaje: str, nuevo_total: float}
        """
        if not self.tiene_permiso('modificar_pruebas'):
            return {
                'exito': False,
                'mensaje': 'No tiene permisos para modificar pruebas',
                'nuevo_total': None
            }

        try:
            # Verificar que la solicitud no esté cerrada
            solicitud = self.obtener_solicitud(solicitud_id)
            if not solicitud:
                return {'exito': False, 'mensaje': 'Solicitud no encontrada', 'nuevo_total': None}

            if solicitud.get('EstadoSolicitud') in ('Completada', 'Entregada', 'Anulada'):
                return {
                    'exito': False,
                    'mensaje': f"No se puede modificar una solicitud {solicitud.get('EstadoSolicitud')}",
                    'nuevo_total': None
                }

            # Actualizar precio
            self.db.update('DetalleSolicitudes', {
                'PrecioUnitario': nuevo_precio,
                'Subtotal': nuevo_precio
            }, f"DetalleID = {detalle_id}")

            # Recalcular totales
            nuevo_total = self._recalcular_totales_solicitud(solicitud_id)

            return {
                'exito': True,
                'mensaje': 'Prueba modificada correctamente',
                'nuevo_total': nuevo_total
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Error al modificar prueba: {str(e)}',
                'nuevo_total': None
            }

    def eliminar_pruebas_solicitud(self, detalle_ids, solicitud_id):
        """
        Elimina una o varias pruebas de una solicitud existente.

        Args:
            detalle_ids: Lista de DetalleID a eliminar
            solicitud_id: ID de la solicitud

        Returns:
            Dict con {exito: bool, mensaje: str, nuevo_total: float}
        """
        if not self.tiene_permiso('eliminar_pruebas'):
            return {
                'exito': False,
                'mensaje': 'No tiene permisos para eliminar pruebas',
                'nuevo_total': None
            }

        if not detalle_ids:
            return {'exito': False, 'mensaje': 'No se seleccionaron pruebas', 'nuevo_total': None}

        try:
            # Verificar que la solicitud no esté cerrada
            solicitud = self.obtener_solicitud(solicitud_id)
            if not solicitud:
                return {'exito': False, 'mensaje': 'Solicitud no encontrada', 'nuevo_total': None}

            if solicitud.get('EstadoSolicitud') in ('Completada', 'Entregada', 'Anulada'):
                return {
                    'exito': False,
                    'mensaje': f"No se pueden eliminar pruebas de una solicitud {solicitud.get('EstadoSolicitud')}",
                    'nuevo_total': None
                }

            # Verificar que no quede sin pruebas
            pruebas_actuales = self.obtener_pruebas_solicitud(solicitud_id)
            if len(pruebas_actuales) <= len(detalle_ids):
                return {
                    'exito': False,
                    'mensaje': 'No se pueden eliminar todas las pruebas. La solicitud debe tener al menos una prueba.',
                    'nuevo_total': None
                }

            # Verificar que no tengan resultados cargados
            for did in detalle_ids:
                for p in pruebas_actuales:
                    if p.get('DetalleID') == did and p.get('Resultado'):
                        return {
                            'exito': False,
                            'mensaje': f"La prueba '{p.get('NombrePrueba', '')}' ya tiene resultados cargados y no puede eliminarse.",
                            'nuevo_total': None
                        }

            # Eliminar las pruebas
            eliminadas = 0
            for did in detalle_ids:
                self.db.execute(f"DELETE FROM DetalleSolicitudes WHERE DetalleID = {did}")
                eliminadas += 1

            # Recalcular totales
            nuevo_total = self._recalcular_totales_solicitud(solicitud_id)

            return {
                'exito': True,
                'mensaje': f'Se eliminaron {eliminadas} prueba(s) correctamente',
                'nuevo_total': nuevo_total,
                'eliminadas': eliminadas
            }

        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Error al eliminar pruebas: {str(e)}',
                'nuevo_total': None
            }

    def _recalcular_totales_solicitud(self, solicitud_id):
        """
        Recalcula los totales de una solicitud basándose en sus pruebas.

        Returns:
            Nuevo total de la solicitud
        """
        try:
            # Obtener solicitud actual
            solicitud = self.obtener_solicitud(solicitud_id)
            if not solicitud:
                return None

            # Sumar precios de todas las pruebas
            pruebas = self.obtener_pruebas_solicitud(solicitud_id)
            subtotal = sum(float(p.get('PrecioUnitario', 0) or 0) for p in pruebas)

            # Aplicar descuento existente
            desc_pct = float(solicitud.get('PorcentajeDescuento', 0) or 0)
            desc_monto = subtotal * (desc_pct / 100)
            base = subtotal - desc_monto

            # Aplicar IVA (obtener de la solicitud original o usar 16%)
            # Nota: MontoIVA / (MontoNeto o base anterior) * 100 para recuperar el %
            monto_neto_anterior = float(solicitud.get('MontoNeto', 0) or 0)
            monto_iva_anterior = float(solicitud.get('MontoIVA', 0) or 0)
            if monto_neto_anterior > 0:
                iva_pct = (monto_iva_anterior / monto_neto_anterior) * 100
            else:
                iva_pct = 16.0

            iva_monto = base * (iva_pct / 100)
            total = base + iva_monto

            # Actualizar solicitud
            self.db.update('Solicitudes', {
                'MontoDescuento': desc_monto,
                'MontoIVA': iva_monto,
                'MontoNeto': base,
                'MontoTotal': total
            }, f"SolicitudID = {solicitud_id}")

            return total

        except Exception as e:
            print(f"Error recalculando totales: {e}")
            return None

    def _generar_numero_solicitud_fallback(self):
        """Genera número de solicitud usando método simple."""
        try:
            count = self.db.count('Solicitudes') + 1
            return f"{datetime.now().strftime('%Y')}-{count:06d}"
        except:
            return f"{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # -------------------------------------------------------------------------
    # GENERACIÓN DE DOCUMENTOS (RECIBO / FACTURA)
    # -------------------------------------------------------------------------

    def generar_recibo(self, solicitud_id, datos_adicionales=None):
        """
        Genera un recibo para una solicitud.

        Args:
            solicitud_id: ID de la solicitud
            datos_adicionales: Dict con datos adicionales del recibo
                - FormaPago (opcional)
                - Observaciones (opcional)
                - MontoAbonado (opcional)

        Returns:
            Dict con {exito: bool, recibo_id: int, numero_recibo: str, mensaje: str}
        """
        if not self.tiene_permiso('generar_recibo'):
            return {
                'exito': False,
                'recibo_id': None,
                'numero_recibo': None,
                'mensaje': 'No tiene permisos para generar recibos'
            }

        try:
            # Obtener solicitud
            solicitud = self.obtener_solicitud(solicitud_id)
            if not solicitud:
                return {
                    'exito': False,
                    'recibo_id': None,
                    'numero_recibo': None,
                    'mensaje': 'Solicitud no encontrada'
                }

            datos = datos_adicionales or {}

            # Generar número de recibo
            numero_recibo = self._generar_numero_recibo()

            # Crear recibo
            recibo_data = {
                'NumeroRecibo': numero_recibo,
                'SolicitudID': solicitud_id,
                'PacienteID': solicitud.get('PacienteID'),
                'FechaEmision': datetime.now(),
                'SubTotal': solicitud.get('MontoNeto', 0),
                'Descuento': solicitud.get('MontoDescuento', 0),
                'IVA': solicitud.get('MontoIVA', 0),
                'Total': solicitud.get('MontoTotal', 0),
                'MontoAbonado': datos.get('MontoAbonado', solicitud.get('MontoTotal', 0)),
                'FormaPago': datos.get('FormaPago', 'Efectivo'),
                'Observaciones': datos.get('Observaciones', ''),
                'UsuarioID': self.usuario.get('UsuarioID', 1),
                'Anulado': False
            }

            self.db.insert('Recibos', recibo_data)

            # Obtener ID del recibo
            recibo = self.db.query_one(f"SELECT ReciboID FROM Recibos WHERE NumeroRecibo='{numero_recibo}'")
            recibo_id = recibo['ReciboID'] if recibo else None

            return {
                'exito': True,
                'recibo_id': recibo_id,
                'numero_recibo': numero_recibo,
                'mensaje': f'Recibo {numero_recibo} generado exitosamente',
                'total': solicitud.get('MontoTotal', 0)
            }

        except Exception as e:
            return {
                'exito': False,
                'recibo_id': None,
                'numero_recibo': None,
                'mensaje': f'Error al generar recibo: {str(e)}'
            }

    def generar_factura(self, solicitud_id, datos_factura=None, facturacion_fiscal=None):
        """
        Genera una factura fiscal para una solicitud.

        Args:
            solicitud_id: ID de la solicitud
            datos_factura: Dict con datos adicionales de la factura
            facturacion_fiscal: Instancia de FacturacionFiscal (opcional)

        Returns:
            Dict con {exito: bool, factura_id: int, numero_factura: str, mensaje: str}
        """
        if not self.tiene_permiso('generar_factura'):
            return {
                'exito': False,
                'factura_id': None,
                'numero_factura': None,
                'mensaje': 'No tiene permisos para generar facturas'
            }

        try:
            # Obtener solicitud
            solicitud = self.obtener_solicitud(solicitud_id)
            if not solicitud:
                return {
                    'exito': False,
                    'factura_id': None,
                    'numero_factura': None,
                    'mensaje': 'Solicitud no encontrada'
                }

            # Obtener pruebas de la solicitud
            pruebas = self.obtener_pruebas_solicitud(solicitud_id)

            # Preparar detalles para facturación
            detalles = []
            for p in pruebas:
                detalles.append({
                    'prueba_id': p['PruebaID'],
                    'descripcion': p.get('NombrePrueba', ''),
                    'precio': float(p.get('PrecioUnitario', 0) or 0),
                    'cantidad': int(p.get('Cantidad', 1) or 1),
                    'descuento': 0
                })

            datos = datos_factura or {}

            # Usar módulo de facturación fiscal si está disponible
            if facturacion_fiscal:
                try:
                    datos_fact = {
                        'paciente_id': solicitud.get('PacienteID'),
                        'solicitud_id': solicitud_id,
                        'descuento_porcentaje': float(solicitud.get('PorcentajeDescuento', 0) or 0),
                        'es_exonerada': datos.get('es_exonerada', False),
                        'tipo': datos.get('tipo', 'Contado'),
                        'condicion_pago': datos.get('condicion_pago', 'Contado'),
                        'observaciones': datos.get('observaciones', '')
                    }

                    factura_id, numero_factura = facturacion_fiscal.crear_factura(
                        datos_fact,
                        detalles,
                        self.usuario.get('UsuarioID', 1)
                    )

                    return {
                        'exito': True,
                        'factura_id': factura_id,
                        'numero_factura': numero_factura,
                        'mensaje': f'Factura {numero_factura} generada exitosamente',
                        'total': solicitud.get('MontoTotal', 0)
                    }

                except Exception as e:
                    return {
                        'exito': False,
                        'factura_id': None,
                        'numero_factura': None,
                        'mensaje': f'Error en facturación fiscal: {str(e)}'
                    }

            # Facturación simple si no hay módulo fiscal
            numero_factura = self._generar_numero_factura_simple()

            factura_data = {
                'NumeroFactura': numero_factura,
                'FechaEmision': datetime.now(),
                'PacienteID': solicitud.get('PacienteID'),
                'SolicitudID': solicitud_id,
                'SubTotal': solicitud.get('MontoNeto', 0),
                'MontoDescuento': solicitud.get('MontoDescuento', 0),
                'TasaIVA': 16,
                'MontoIVA': solicitud.get('MontoIVA', 0),
                'MontoTotal': solicitud.get('MontoTotal', 0),
                'EstadoPago': 'Pendiente',
                'MontoCobrado': 0,
                'SaldoPendiente': solicitud.get('MontoTotal', 0),
                'UsuarioEmite': self.usuario.get('UsuarioID', 1),
                'FechaRegistro': datetime.now()
            }

            self.db.insert('Facturas', factura_data)

            factura = self.db.query_one(f"SELECT FacturaID FROM Facturas WHERE NumeroFactura='{numero_factura}'")
            factura_id = factura['FacturaID'] if factura else None

            # Insertar detalles
            if factura_id:
                for item in detalles:
                    detalle = {
                        'FacturaID': factura_id,
                        'PruebaID': item['prueba_id'],
                        'Descripcion': item['descripcion'],
                        'Cantidad': item['cantidad'],
                        'PrecioUnitario': item['precio'],
                        'SubTotal': item['precio'] * item['cantidad']
                    }
                    self.db.insert('DetalleFacturas', detalle)

            return {
                'exito': True,
                'factura_id': factura_id,
                'numero_factura': numero_factura,
                'mensaje': f'Factura {numero_factura} generada exitosamente',
                'total': solicitud.get('MontoTotal', 0)
            }

        except Exception as e:
            return {
                'exito': False,
                'factura_id': None,
                'numero_factura': None,
                'mensaje': f'Error al generar factura: {str(e)}'
            }

    def _generar_numero_recibo(self):
        """Genera un número de recibo único."""
        try:
            anio = datetime.now().year
            result = self.db.query_one(f"""
                SELECT MAX(NumeroRecibo) as Ultimo
                FROM Recibos
                WHERE NumeroRecibo LIKE 'REC-{anio}-%'
            """)

            if result and result['Ultimo']:
                try:
                    numero = int(result['Ultimo'].split('-')[-1]) + 1
                except:
                    numero = 1
            else:
                numero = 1

            return f"REC-{anio}-{numero:06d}"
        except:
            return f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _generar_numero_factura_simple(self):
        """Genera un número de factura simple."""
        try:
            anio = datetime.now().year
            result = self.db.query_one(f"""
                SELECT MAX(NumeroFactura) as Ultimo
                FROM Facturas
                WHERE NumeroFactura LIKE 'FAC-{anio}-%'
            """)

            if result and result['Ultimo']:
                try:
                    numero = int(result['Ultimo'].split('-')[-1]) + 1
                except:
                    numero = 1
            else:
                numero = 1

            return f"FAC-{anio}-{numero:06d}"
        except:
            return f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # -------------------------------------------------------------------------
    # ANULACIÓN DE DOCUMENTOS
    # -------------------------------------------------------------------------

    def anular_recibo(self, recibo_id, motivo):
        """
        Anula un recibo.

        Args:
            recibo_id: ID del recibo
            motivo: Motivo de la anulación

        Returns:
            Dict con {exito: bool, mensaje: str}
        """
        if not self.tiene_permiso('anular_documento'):
            return {
                'exito': False,
                'mensaje': 'No tiene permisos para anular documentos'
            }

        try:
            self.db.update('Recibos', {
                'Anulado': True,
                'MotivoAnulacion': motivo,
                'FechaAnulacion': datetime.now(),
                'UsuarioAnula': self.usuario.get('UsuarioID', 1)
            }, f"ReciboID = {recibo_id}")

            return {
                'exito': True,
                'mensaje': 'Recibo anulado exitosamente'
            }
        except Exception as e:
            return {
                'exito': False,
                'mensaje': f'Error al anular recibo: {str(e)}'
            }

    # -------------------------------------------------------------------------
    # VERIFICACIÓN Y CREACIÓN DE TABLA RECIBOS
    # -------------------------------------------------------------------------

    def _verificar_tabla_recibos(self):
        """Verifica que existe la tabla Recibos y la crea si no existe."""
        try:
            # Intentar consultar la tabla
            self.db.query("SELECT TOP 1 * FROM Recibos")
        except:
            # La tabla no existe, intentar crearla
            try:
                self._crear_tabla_recibos()
            except Exception as e:
                print(f"Advertencia: No se pudo crear tabla Recibos: {e}")

    def _crear_tabla_recibos(self):
        """Crea la tabla Recibos si no existe."""
        # Nota: Access/ADODB no soporta CREATE TABLE de forma estándar
        # Este método intentará agregar los campos si la tabla existe pero faltan columnas
        try:
            # Crear tabla con campos básicos
            sql_create = """
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
            """
            self.db.execute(sql_create)
            print("Tabla Recibos creada exitosamente")
        except Exception as e:
            # Si falla el CREATE, puede que ya exista parcialmente
            # Intentar agregar columnas faltantes
            columnas = [
                ("NumeroRecibo", "TEXT(20)"),
                ("SolicitudID", "INTEGER"),
                ("PacienteID", "INTEGER"),
                ("FechaEmision", "DATETIME"),
                ("SubTotal", "CURRENCY"),
                ("Descuento", "CURRENCY"),
                ("IVA", "CURRENCY"),
                ("Total", "CURRENCY"),
                ("MontoAbonado", "CURRENCY"),
                ("FormaPago", "TEXT(50)"),
                ("Observaciones", "TEXT(255)"),
                ("UsuarioID", "INTEGER"),
                ("Anulado", "BIT"),
                ("MotivoAnulacion", "TEXT(255)"),
                ("FechaAnulacion", "DATETIME"),
                ("UsuarioAnula", "INTEGER"),
            ]

            for col_name, col_type in columnas:
                try:
                    self.db.execute(f"ALTER TABLE Recibos ADD COLUMN {col_name} {col_type}")
                except:
                    pass  # Columna ya existe


# ============================================================================
# DIÁLOGOS DE UI
# ============================================================================

class DialogoSolicitudExistente:
    """
    Diálogo que se muestra cuando un paciente tiene solicitudes activas.
    Permite elegir entre agregar a una existente o crear una nueva.
    Si es del mismo día, muestra advertencia más enfática.
    """

    def __init__(self, parent, solicitudes, paciente_nombre, es_mismo_dia=False):
        """
        Args:
            parent: Ventana padre
            solicitudes: Lista de solicitudes activas del paciente
            paciente_nombre: Nombre del paciente
            es_mismo_dia: Si True, indica que hay solicitudes del mismo día
        """
        self.resultado = None  # 'nueva', 'agregar', o None si cancela
        self.solicitud_seleccionada = None
        self.es_mismo_dia = es_mismo_dia

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Paciente con Solicitudes del Día" if es_mismo_dia else "Solicitudes Existentes")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        # Centrar ventana
        self._centrar_ventana(600, 530)

        self._crear_ui(solicitudes, paciente_nombre)

        # Esperar hasta que se cierre
        self.dialog.wait_window()

    def _centrar_ventana(self, ancho, alto):
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

    def _crear_ui(self, solicitudes, paciente_nombre):
        if self.es_mismo_dia:
            color_header = '#e67e22'
            titulo = "Paciente YA Registrado Hoy"
        else:
            color_header = '#3498db'
            titulo = "Solicitudes Activas"

        # Header
        header = tk.Frame(self.dialog, bg=color_header, height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text=titulo,
                font=('Segoe UI', 14, 'bold'), bg=color_header, fg='white').pack(pady=15)

        # Mensaje
        msg_frame = tk.Frame(self.dialog, bg='white')
        msg_frame.pack(fill='x', padx=20, pady=15)

        if self.es_mismo_dia:
            # Advertencia prominente para solicitudes del mismo día
            aviso_frame = tk.Frame(msg_frame, bg='#fff3cd', relief='solid', bd=1)
            aviso_frame.pack(fill='x', pady=(0, 10))

            tk.Label(aviso_frame,
                    text=f"El paciente {paciente_nombre} ya tiene solicitud(es) registrada(s) HOY.",
                    font=('Segoe UI', 10, 'bold'), bg='#fff3cd', fg='#856404',
                    wraplength=520, justify='left').pack(padx=10, pady=(8, 2), anchor='w')
            tk.Label(aviso_frame,
                    text="Se recomienda AGREGAR las pruebas a la solicitud existente\n"
                         "para mantener el orden del diario. Si necesita un nuevo\n"
                         "documento de pago, puede generar una nueva factura/recibo\n"
                         "sin alterar el correlativo de la solicitud.",
                    font=('Segoe UI', 9), bg='#fff3cd', fg='#856404',
                    wraplength=520, justify='left').pack(padx=10, pady=(0, 8), anchor='w')
        else:
            tk.Label(msg_frame,
                    text=f"El paciente {paciente_nombre} tiene solicitud(es) activa(s):",
                    font=('Segoe UI', 10), bg='white', fg='#2c3e50',
                    wraplength=520, justify='left').pack(anchor='w')

        # Lista de solicitudes
        list_frame = tk.Frame(self.dialog, bg='white')
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)

        cols = ('N° Solicitud', 'Fecha', 'Estado', 'Pruebas', 'Total')
        self.tree = ttk.Treeview(list_frame, columns=cols, show='headings', height=5)

        self.tree.heading('N° Solicitud', text='N° Solicitud')
        self.tree.heading('Fecha', text='Fecha')
        self.tree.heading('Estado', text='Estado')
        self.tree.heading('Pruebas', text='Pruebas')
        self.tree.heading('Total', text='Total')

        self.tree.column('N° Solicitud', width=120)
        self.tree.column('Fecha', width=100)
        self.tree.column('Estado', width=80)
        self.tree.column('Pruebas', width=60)
        self.tree.column('Total', width=80)

        vsb = ttk.Scrollbar(list_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side='left', fill='both', expand=True)
        vsb.pack(side='right', fill='y')

        # Poblar lista
        self.solicitudes_map = {}
        for sol in solicitudes:
            fecha = sol.get('FechaSolicitud')
            if fecha:
                fecha_str = fecha.strftime('%d/%m/%Y %H:%M') if hasattr(fecha, 'strftime') else str(fecha)[:16]
            else:
                fecha_str = ''

            total = sol.get('MontoTotal', 0) or 0

            iid = self.tree.insert('', 'end', values=(
                sol.get('NumeroSolicitud', ''),
                fecha_str,
                sol.get('EstadoSolicitud', ''),
                sol.get('CantidadPruebas', 0),
                f"${total:,.2f}"
            ))
            self.solicitudes_map[iid] = sol

        # Seleccionar primera por defecto
        if self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])

        # Botones - usar side='bottom' para asegurar visibilidad
        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=20, pady=20)

        # Botón principal: Agregar (resaltado cuando es mismo día)
        tk.Button(btn_frame, text="✅ Agregar Pruebas a Seleccionada",
                 font=('Segoe UI', 10, 'bold'), bg='#27ae60', fg='white',
                 relief='flat', padx=15, pady=10, cursor='hand2',
                 command=self._agregar_existente).pack(side='left', padx=5)

        # Botón secundario: Crear nueva (con confirmación si es mismo día)
        tk.Button(btn_frame, text="➕ Nueva Solicitud",
                 font=('Segoe UI', 10), bg='#95a5a6' if self.es_mismo_dia else '#3498db',
                 fg='white', relief='flat', padx=15, pady=10, cursor='hand2',
                 command=self._crear_nueva).pack(side='left', padx=5)

        tk.Button(btn_frame, text="❌ Cancelar",
                 font=('Segoe UI', 10), bg='#e74c3c', fg='white',
                 relief='flat', padx=15, pady=10, cursor='hand2',
                 command=self._cancelar).pack(side='right', padx=5)

    def _agregar_existente(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Seleccione una solicitud")
            return

        self.resultado = 'agregar'
        self.solicitud_seleccionada = self.solicitudes_map.get(sel[0])
        self.dialog.destroy()

    def _crear_nueva(self):
        # Si es del mismo día, pedir confirmación extra
        if self.es_mismo_dia:
            confirmar = messagebox.askyesno(
                "Confirmar Nueva Solicitud",
                "Este paciente ya tiene solicitud(es) del día de hoy.\n\n"
                "Crear una nueva solicitud generará un nuevo correlativo.\n"
                "Se recomienda agregar pruebas a la solicitud existente.\n\n"
                "¿Desea crear una solicitud nueva de todas formas?",
                icon='warning',
                parent=self.dialog
            )
            if not confirmar:
                return

        self.resultado = 'nueva'
        self.solicitud_seleccionada = None
        self.dialog.destroy()

    def _cancelar(self):
        self.resultado = None
        self.solicitud_seleccionada = None
        self.dialog.destroy()


class DialogoTipoDocumento:
    """
    Diálogo para seleccionar el tipo de documento (Recibo o Factura).
    """

    def __init__(self, parent, total, puede_facturar=True):
        """
        Args:
            parent: Ventana padre
            total: Monto total de la solicitud
            puede_facturar: Si el usuario tiene permisos para generar facturas
        """
        self.resultado = None  # 'recibo', 'factura', 'sin_documento', o None si cancela
        self.forma_pago = 'Efectivo'
        self.monto_abonado = total

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Tipo de Documento")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        self._centrar_ventana(450, 420)
        self._crear_ui(total, puede_facturar)

        self.dialog.wait_window()

    def _centrar_ventana(self, ancho, alto):
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

    def _crear_ui(self, total, puede_facturar):
        # Header
        header = tk.Frame(self.dialog, bg='#3498db', height=50)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="Generar Documento de Pago",
                font=('Segoe UI', 12, 'bold'), bg='#3498db', fg='white').pack(pady=12)

        # Total
        total_frame = tk.Frame(self.dialog, bg='#e3f2fd')
        total_frame.pack(fill='x', padx=20, pady=15)

        tk.Label(total_frame, text="Total a Pagar:",
                font=('Segoe UI', 11), bg='#e3f2fd').pack(side='left', padx=10, pady=10)
        tk.Label(total_frame, text=f"${total:,.2f}",
                font=('Segoe UI', 16, 'bold'), bg='#e3f2fd', fg='#2e7d32').pack(side='right', padx=10, pady=10)

        # Opciones de documento
        options_frame = tk.Frame(self.dialog, bg='white')
        options_frame.pack(fill='x', padx=20, pady=10)

        tk.Label(options_frame, text="Seleccione tipo de documento:",
                font=('Segoe UI', 10, 'bold'), bg='white').pack(anchor='w', pady=(0, 10))

        self.tipo_var = tk.StringVar(value='recibo')

        tk.Radiobutton(options_frame, text="Recibo (Documento interno)",
                      variable=self.tipo_var, value='recibo',
                      font=('Segoe UI', 10), bg='white',
                      activebackground='white').pack(anchor='w', pady=2)

        factura_state = 'normal' if puede_facturar else 'disabled'
        factura_text = "Factura Fiscal (SENIAT)" if puede_facturar else "Factura Fiscal (Sin permisos)"

        tk.Radiobutton(options_frame, text=factura_text,
                      variable=self.tipo_var, value='factura',
                      font=('Segoe UI', 10), bg='white',
                      activebackground='white', state=factura_state).pack(anchor='w', pady=2)

        tk.Radiobutton(options_frame, text="Sin documento (Solo guardar solicitud)",
                      variable=self.tipo_var, value='sin_documento',
                      font=('Segoe UI', 10), bg='white',
                      activebackground='white').pack(anchor='w', pady=2)

        # Forma de pago
        pago_frame = tk.Frame(self.dialog, bg='white')
        pago_frame.pack(fill='x', padx=20, pady=10)

        tk.Label(pago_frame, text="Forma de Pago:",
                font=('Segoe UI', 10), bg='white').pack(side='left')

        self.combo_pago = ttk.Combobox(pago_frame, font=('Segoe UI', 10), width=20, state='readonly')
        self.combo_pago['values'] = ['Efectivo', 'Transferencia', 'Tarjeta', 'Pago Móvil', 'Mixto']
        self.combo_pago.set('Efectivo')
        self.combo_pago.pack(side='right')

        # Botones - usar side='bottom' para asegurar visibilidad
        btn_frame = tk.Frame(self.dialog, bg='white')
        btn_frame.pack(side='bottom', fill='x', padx=20, pady=25)

        tk.Button(btn_frame, text="✅ GUARDAR",
                 font=('Segoe UI', 11, 'bold'), bg='#27ae60', fg='white',
                 relief='flat', padx=25, pady=10, cursor='hand2',
                 command=self._generar).pack(side='left', padx=10)

        tk.Button(btn_frame, text="❌ Cancelar",
                 font=('Segoe UI', 11), bg='#e74c3c', fg='white',
                 relief='flat', padx=25, pady=10, cursor='hand2',
                 command=self._cancelar).pack(side='right', padx=10)

    def _generar(self):
        self.resultado = self.tipo_var.get()
        self.forma_pago = self.combo_pago.get()
        self.dialog.destroy()

    def _cancelar(self):
        self.resultado = None
        self.dialog.destroy()


class DialogoAgregarPruebas:
    """
    Diálogo para agregar pruebas a una solicitud existente.
    Pregunta si se debe generar un nuevo documento de pago.
    """

    def __init__(self, parent, solicitud, puede_facturar=True):
        """
        Args:
            parent: Ventana padre
            solicitud: Dict con datos de la solicitud existente
            puede_facturar: Si el usuario tiene permisos para generar facturas
        """
        self.resultado = None  # 'sin_documento', 'recibo', 'factura', o None si cancela

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Documento para Pruebas Adicionales")
        self.dialog.configure(bg='white')
        self.dialog.grab_set()
        self.dialog.focus_set()

        # Centrar ventana - tamaño amplio
        ancho, alto = 500, 450
        x = (self.dialog.winfo_screenwidth() - ancho) // 2
        y = (self.dialog.winfo_screenheight() - alto) // 2
        self.dialog.geometry(f"{ancho}x{alto}+{x}+{y}")
        self.dialog.resizable(False, False)

        self._crear_ui(solicitud, puede_facturar)
        self.dialog.wait_window()

    def _crear_ui(self, solicitud, puede_facturar):
        # PRIMERO crear botones al fondo (se empaquetan primero)
        btn_frame = tk.Frame(self.dialog, bg='#f0f0f0', height=70)
        btn_frame.pack(side='bottom', fill='x')
        btn_frame.pack_propagate(False)

        btn_confirmar = tk.Button(btn_frame, text="✅ CONFIRMAR",
                 font=('Segoe UI', 12, 'bold'), bg='#27ae60', fg='white',
                 relief='flat', padx=30, pady=12, cursor='hand2',
                 command=self._continuar)
        btn_confirmar.pack(side='left', padx=20, pady=15)

        btn_cancelar = tk.Button(btn_frame, text="❌ CANCELAR",
                 font=('Segoe UI', 12), bg='#e74c3c', fg='white',
                 relief='flat', padx=30, pady=12, cursor='hand2',
                 command=self._cancelar)
        btn_cancelar.pack(side='right', padx=20, pady=15)

        # Header
        header = tk.Frame(self.dialog, bg='#f39c12', height=60)
        header.pack(side='top', fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="📄 Documento para Pruebas Adicionales",
                font=('Segoe UI', 14, 'bold'), bg='#f39c12', fg='white').pack(pady=15)

        # Contenido principal
        content = tk.Frame(self.dialog, bg='white')
        content.pack(fill='both', expand=True, padx=25, pady=20)

        # Info de solicitud
        numero = solicitud.get('NumeroSolicitud', 'N/A') if solicitud else 'N/A'
        tk.Label(content,
                text=f"Agregando pruebas a solicitud: {numero}",
                font=('Segoe UI', 11), bg='white', fg='#2c3e50').pack(anchor='w', pady=(0, 20))

        # Pregunta
        tk.Label(content, text="¿Generar nuevo documento de pago?",
                font=('Segoe UI', 11, 'bold'), bg='white').pack(anchor='w', pady=(0, 15))

        # Opciones
        self.tipo_var = tk.StringVar(value='sin_documento')

        tk.Radiobutton(content, text="📋 Solo agregar pruebas (sin documento adicional)",
                      variable=self.tipo_var, value='sin_documento',
                      font=('Segoe UI', 11), bg='white',
                      activebackground='white').pack(anchor='w', pady=8)

        tk.Radiobutton(content, text="🧾 Generar recibo adicional",
                      variable=self.tipo_var, value='recibo',
                      font=('Segoe UI', 11), bg='white',
                      activebackground='white').pack(anchor='w', pady=8)

        factura_state = 'normal' if puede_facturar else 'disabled'
        tk.Radiobutton(content, text="📄 Generar factura adicional",
                      variable=self.tipo_var, value='factura',
                      font=('Segoe UI', 11), bg='white',
                      activebackground='white', state=factura_state).pack(anchor='w', pady=8)

    def _continuar(self):
        self.resultado = self.tipo_var.get()
        self.dialog.destroy()

    def _cancelar(self):
        self.resultado = None
        self.dialog.destroy()


# ============================================================================
# FUNCIÓN DE AYUDA PARA INTEGRACIÓN
# ============================================================================

def crear_gestor_solicitudes(db, usuario):
    """
    Función de ayuda para crear una instancia del gestor de solicitudes.

    Args:
        db: Objeto de conexión a la base de datos
        usuario: Dict con datos del usuario actual

    Returns:
        Instancia de GestorSolicitudes
    """
    return GestorSolicitudes(db, usuario)

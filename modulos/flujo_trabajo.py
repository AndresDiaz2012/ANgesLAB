"""
================================================================================
MODULO DE FLUJO DE TRABAJO - ANgesLAB
================================================================================
Gestiona el flujo de trabajo de solicitudes en el laboratorio clinico.
Controla los estados y transiciones de:
- Solicitudes
- Pruebas Solicitadas
- Muestras
- Resultados

Flujo Principal:
RECEPCION -> LABORATORIO -> RESULTADOS -> ENTREGA

Autor: Sistema ANgesLAB
================================================================================
"""

from datetime import datetime, timedelta
from enum import Enum
from modulos.config_numeracion import ConfiguradorNumeracion

# ============================================================================
# ESTADOS Y TRANSICIONES
# ============================================================================

class EstadoSolicitud(Enum):
    """Estados posibles de una solicitud"""
    REGISTRADA = 'Registrada'
    PAGADA = 'Pagada'
    EN_PROCESO = 'EnProceso'
    EN_ANALISIS = 'EnAnalisis'
    COMPLETADA = 'Completada'
    VALIDADA = 'Validada'
    ENTREGADA = 'Entregada'
    CANCELADA = 'Cancelada'


class EstadoPrueba(Enum):
    """Estados posibles de una prueba solicitada"""
    PENDIENTE = 'Pendiente'
    RECIBIDA = 'Recibida'
    EN_PROCESO = 'EnProceso'
    COMPLETADA = 'Completada'
    VALIDADA = 'Validada'


class EstadoMuestra(Enum):
    """Estados de muestras"""
    PENDIENTE = 'Pendiente'
    RECIBIDA = 'Recibida'
    EN_ANALISIS = 'EnAnalisis'
    PROCESADA = 'Procesada'
    RECHAZADA = 'Rechazada'


# Transiciones permitidas para solicitudes
TRANSICIONES_SOLICITUD = {
    EstadoSolicitud.REGISTRADA: [EstadoSolicitud.PAGADA, EstadoSolicitud.CANCELADA],
    EstadoSolicitud.PAGADA: [EstadoSolicitud.EN_PROCESO, EstadoSolicitud.CANCELADA],
    EstadoSolicitud.EN_PROCESO: [EstadoSolicitud.EN_ANALISIS, EstadoSolicitud.CANCELADA],
    EstadoSolicitud.EN_ANALISIS: [EstadoSolicitud.COMPLETADA],
    EstadoSolicitud.COMPLETADA: [EstadoSolicitud.VALIDADA],
    EstadoSolicitud.VALIDADA: [EstadoSolicitud.ENTREGADA],
    EstadoSolicitud.ENTREGADA: [],
    EstadoSolicitud.CANCELADA: []
}

# Transiciones permitidas para pruebas
TRANSICIONES_PRUEBA = {
    EstadoPrueba.PENDIENTE: [EstadoPrueba.RECIBIDA],
    EstadoPrueba.RECIBIDA: [EstadoPrueba.EN_PROCESO],
    EstadoPrueba.EN_PROCESO: [EstadoPrueba.COMPLETADA],
    EstadoPrueba.COMPLETADA: [EstadoPrueba.VALIDADA],
    EstadoPrueba.VALIDADA: []
}


# ============================================================================
# CLASE PRINCIPAL DE FLUJO DE TRABAJO
# ============================================================================

class FlujoTrabajo:
    """
    Gestiona el flujo de trabajo del laboratorio
    """

    def __init__(self, db):
        self.db = db
        # Inicializar configurador de numeración
        try:
            self.config_numeracion = ConfiguradorNumeracion(db)
        except Exception as e:
            print(f"Advertencia: No se pudo inicializar configurador de numeración: {e}")
            self.config_numeracion = None

    # -------------------------------------------------------------------------
    # GESTION DE SOLICITUDES
    # -------------------------------------------------------------------------

    def crear_solicitud(self, paciente_id, usuario_id, medico_id=None, prioridad='Normal', observaciones=''):
        """
        Crea una nueva solicitud

        Args:
            paciente_id: ID del paciente
            usuario_id: ID del usuario que registra
            medico_id: ID del medico (opcional)
            prioridad: Normal o Urgente
            observaciones: Notas adicionales

        Returns:
            tuple (solicitud_id, numero_solicitud)
        """
        # Generar numero de solicitud
        numero = self._generar_numero_solicitud()

        sql = f"""
            INSERT INTO Solicitudes
            (NumeroSolicitud, PacienteID, MedicoID, FechaSolicitud, FechaEntrega,
             EstadoSolicitud, Prioridad, Observaciones, UsuarioRegistro)
            VALUES
            ('{numero}', {paciente_id}, {medico_id if medico_id else 'NULL'},
             Now(), DateAdd('d', 1, Now()), 'Registrada', '{prioridad}',
             '{observaciones.replace("'", "''")}', {usuario_id})
        """

        self.db.execute(sql)

        # Obtener ID de la solicitud creada
        result = self.db.query_one(f"SELECT MAX(SolicitudID) as ID FROM Solicitudes WHERE NumeroSolicitud = '{numero}'")
        solicitud_id = result.get('ID') if result else None

        # Registrar en historial
        self._registrar_historial(solicitud_id, 'Solicitud creada', usuario_id)

        return solicitud_id, numero

    def _generar_numero_solicitud(self):
        """
        Genera numero de solicitud unico según la configuración establecida.

        Soporta tres modos:
        - DIARIA: Formato AAAAMMDD-NNNNNN (reseteo automático diario)
        - ANUAL: Formato AAAA-NNNNNN (reseteo automático anual) - por defecto
        - CINCO_ANIOS: Formato NNNNNN (reseteo manual cada 5 años)

        Returns:
            str: Número de solicitud generado
        """
        # Intentar usar el nuevo sistema de configuración
        if self.config_numeracion:
            try:
                return self.config_numeracion.generar_numero_solicitud()
            except Exception as e:
                print(f"Error en configurador de numeración, usando sistema legado: {e}")

        # Fallback al sistema legado (formato AAAA-NNNNNN)
        anio = datetime.now().strftime('%Y')

        result = self.db.query_one(f"""
            SELECT MAX(NumeroSolicitud) as Ultimo
            FROM Solicitudes
            WHERE NumeroSolicitud LIKE '{anio}-%'
        """)

        if result and result.get('Ultimo'):
            ultimo_num = int(result['Ultimo'].split('-')[1])
            nuevo_num = ultimo_num + 1
        else:
            nuevo_num = 1

        return f"{anio}-{nuevo_num:06d}"

    def agregar_prueba(self, solicitud_id, prueba_id, usuario_id):
        """
        Agrega una prueba a la solicitud

        Args:
            solicitud_id: ID de la solicitud
            prueba_id: ID de la prueba a agregar
            usuario_id: ID del usuario

        Returns:
            ID de la prueba solicitada
        """
        sql = f"""
            INSERT INTO DetalleSolicitudes
            (SolicitudID, PruebaID, Estado, FechaRegistro, UsuarioRegistro)
            VALUES
            ({solicitud_id}, {prueba_id}, 'Pendiente', Now(), {usuario_id})
        """

        self.db.execute(sql)

        result = self.db.query_one(f"""
            SELECT MAX(DetalleID) as ID
            FROM DetalleSolicitudes
            WHERE SolicitudID = {solicitud_id} AND PruebaID = {prueba_id}
        """)

        # Crear registros de resultados vacios para los parametros
        self._crear_resultados_vacios(result.get('ID'), prueba_id)

        return result.get('ID') if result else None

    def _crear_resultados_vacios(self, prueba_solicitada_id, prueba_id):
        """Crea registros de resultados vacios para cada parametro de la prueba"""
        parametros = self.db.query(f"""
            SELECT pp.ParametroID, p.UnidadID
            FROM ParametrosPrueba pp
            INNER JOIN Parametros p ON pp.ParametroID = p.ParametroID
            WHERE pp.PruebaID = {prueba_id}
            ORDER BY pp.Orden
        """)

        for param in parametros:
            self.db.execute(f"""
                INSERT INTO ResultadosParametros
                (DetalleID, ParametroID, UnidadID, FechaCreacion)
                VALUES
                ({prueba_solicitada_id}, {param['ParametroID']},
                 {param['UnidadID'] if param.get('UnidadID') else 'NULL'}, Now())
            """)

    def remover_prueba(self, prueba_solicitada_id, usuario_id):
        """Remueve una prueba de la solicitud"""
        # Verificar que no tenga resultados ingresados
        resultados = self.db.query_one(f"""
            SELECT COUNT(*) as Cuenta
            FROM ResultadosParametros
            WHERE DetalleID = {prueba_solicitada_id}
            AND (ValorNumerico IS NOT NULL OR ValorTexto IS NOT NULL)
        """)

        if resultados and resultados.get('Cuenta', 0) > 0:
            raise Exception("No se puede eliminar una prueba con resultados ingresados")

        # Eliminar resultados vacios
        self.db.execute(f"DELETE FROM ResultadosParametros WHERE DetalleID = {prueba_solicitada_id}")

        # Eliminar prueba solicitada
        self.db.execute(f"DELETE FROM DetalleSolicitudes WHERE DetalleID = {prueba_solicitada_id}")

        return True

    # -------------------------------------------------------------------------
    # CAMBIOS DE ESTADO
    # -------------------------------------------------------------------------

    def cambiar_estado_solicitud(self, solicitud_id, nuevo_estado, usuario_id, comentario=''):
        """
        Cambia el estado de una solicitud

        Args:
            solicitud_id: ID de la solicitud
            nuevo_estado: Nuevo estado (string o EstadoSolicitud)
            usuario_id: ID del usuario que realiza el cambio
            comentario: Comentario opcional

        Returns:
            True si el cambio fue exitoso
        """
        if isinstance(nuevo_estado, EstadoSolicitud):
            nuevo_estado = nuevo_estado.value

        # Obtener estado actual
        solicitud = self.db.query_one(f"SELECT EstadoSolicitud FROM Solicitudes WHERE SolicitudID = {solicitud_id}")
        if not solicitud:
            raise Exception("Solicitud no encontrada")

        estado_actual = solicitud.get('EstadoSolicitud')

        # Validar transicion
        try:
            estado_enum_actual = EstadoSolicitud(estado_actual)
            estado_enum_nuevo = EstadoSolicitud(nuevo_estado)

            if estado_enum_nuevo not in TRANSICIONES_SOLICITUD.get(estado_enum_actual, []):
                raise Exception(f"Transicion no permitida de {estado_actual} a {nuevo_estado}")
        except ValueError:
            pass  # Si no es un estado del enum, permitir

        # Actualizar estado
        self.db.execute(f"""
            UPDATE Solicitudes
            SET EstadoSolicitud = '{nuevo_estado}',
                FechaUltimaModificacion = Now()
            WHERE SolicitudID = {solicitud_id}
        """)

        # Registrar en historial
        self._registrar_historial(
            solicitud_id,
            f"Estado cambiado de {estado_actual} a {nuevo_estado}. {comentario}",
            usuario_id
        )

        return True

    def cambiar_estado_prueba(self, prueba_solicitada_id, nuevo_estado, usuario_id):
        """
        Cambia el estado de una prueba solicitada

        Args:
            prueba_solicitada_id: ID de la prueba solicitada
            nuevo_estado: Nuevo estado (string o EstadoPrueba)
            usuario_id: ID del usuario

        Returns:
            True si el cambio fue exitoso
        """
        if isinstance(nuevo_estado, EstadoPrueba):
            nuevo_estado = nuevo_estado.value

        campos_fecha = {
            'Recibida': 'FechaRecepcion',
            'EnProceso': 'FechaInicio',
            'Completada': 'FechaRealizacion',
            'Validada': 'FechaValidacion'
        }

        campo_fecha = campos_fecha.get(nuevo_estado, '')
        fecha_sql = f", {campo_fecha} = Now()" if campo_fecha else ""

        usuario_campo = {
            'Recibida': 'UsuarioRecepcion',
            'Completada': 'UsuarioRealizo',
            'Validada': 'UsuarioValido'
        }

        campo_usuario = usuario_campo.get(nuevo_estado, '')
        usuario_sql = f", {campo_usuario} = {usuario_id}" if campo_usuario else ""

        self.db.execute(f"""
            UPDATE DetalleSolicitudes
            SET Estado = '{nuevo_estado}'{fecha_sql}{usuario_sql}
            WHERE DetalleID = {prueba_solicitada_id}
        """)

        # Verificar si todas las pruebas estan completas para actualizar solicitud
        self._verificar_completitud_solicitud(prueba_solicitada_id, usuario_id)

        return True

    def _verificar_completitud_solicitud(self, prueba_solicitada_id, usuario_id):
        """Verifica si todas las pruebas estan completas y actualiza la solicitud"""
        # Obtener solicitud
        ps = self.db.query_one(f"SELECT SolicitudID FROM DetalleSolicitudes WHERE DetalleID = {prueba_solicitada_id}")
        if not ps:
            return

        solicitud_id = ps['SolicitudID']

        # Contar pruebas pendientes
        pendientes = self.db.query_one(f"""
            SELECT COUNT(*) as Cuenta
            FROM DetalleSolicitudes
            WHERE SolicitudID = {solicitud_id}
            AND Estado NOT IN ('Completada', 'Validada')
        """)

        # Si no hay pendientes, marcar solicitud como completada
        if pendientes and pendientes.get('Cuenta', 0) == 0:
            solicitud = self.db.query_one(f"SELECT EstadoSolicitud FROM Solicitudes WHERE SolicitudID = {solicitud_id}")
            if solicitud and solicitud.get('EstadoSolicitud') in ['EnProceso', 'EnAnalisis']:
                self.cambiar_estado_solicitud(solicitud_id, 'Completada', usuario_id, 'Todas las pruebas completadas')

    # -------------------------------------------------------------------------
    # REGISTRO DE RESULTADOS
    # -------------------------------------------------------------------------

    def registrar_resultado(self, resultado_id, valor, usuario_id, es_numerico=True, valor_referencia=None):
        """
        Registra un resultado de laboratorio

        Args:
            resultado_id: ID del resultado
            valor: Valor del resultado
            usuario_id: ID del usuario que registra
            es_numerico: True si el valor es numerico
            valor_referencia: Valor de referencia (opcional)

        Returns:
            True si el registro fue exitoso
        """
        if es_numerico:
            campo_valor = f"ValorNumerico = {valor}"
        else:
            campo_valor = f"ValorTexto = '{str(valor).replace(chr(39), chr(39)+chr(39))}'"

        referencia_sql = f", ValorReferencia = '{valor_referencia}'" if valor_referencia else ""

        self.db.execute(f"""
            UPDATE ResultadosParametros
            SET {campo_valor},
                FechaResultado = Now(),
                UsuarioResultado = {usuario_id}
                {referencia_sql}
            WHERE ResultadoID = {resultado_id}
        """)

        # Evaluar si esta fuera de rango
        self._evaluar_rango_resultado(resultado_id)

        return True

    def _evaluar_rango_resultado(self, resultado_id):
        """Evalua si un resultado esta fuera de rango"""
        resultado = self.db.query_one(f"""
            SELECT r.ValorNumerico, r.ParametroID,
                   vr.ValorMinimo, vr.ValorMaximo, vr.ValorCriticoBajo, vr.ValorCriticoAlto
            FROM ResultadosParametros r
            LEFT JOIN ValoresReferencia vr ON r.ParametroID = vr.ParametroID
            WHERE r.ResultadoID = {resultado_id}
        """)

        if not resultado or resultado.get('ValorNumerico') is None:
            return

        valor = float(resultado['ValorNumerico'])
        fuera_rango = False
        tipo_alerta = None

        # Verificar criticos primero
        if resultado.get('ValorCriticoBajo') and valor < resultado['ValorCriticoBajo']:
            fuera_rango = True
            tipo_alerta = 'CriticoBajo'
        elif resultado.get('ValorCriticoAlto') and valor > resultado['ValorCriticoAlto']:
            fuera_rango = True
            tipo_alerta = 'CriticoAlto'
        # Verificar rango normal
        elif resultado.get('ValorMinimo') and valor < resultado['ValorMinimo']:
            fuera_rango = True
            tipo_alerta = 'Bajo'
        elif resultado.get('ValorMaximo') and valor > resultado['ValorMaximo']:
            fuera_rango = True
            tipo_alerta = 'Alto'

        if fuera_rango:
            self.db.execute(f"""
                UPDATE ResultadosParametros
                SET FueraDeRango = True, TipoAlerta = '{tipo_alerta}'
                WHERE ResultadoID = {resultado_id}
            """)

    # -------------------------------------------------------------------------
    # RECEPCION DE MUESTRAS
    # -------------------------------------------------------------------------

    def recibir_muestras(self, solicitud_id, usuario_id, observaciones=''):
        """
        Registra la recepcion de muestras para una solicitud

        Args:
            solicitud_id: ID de la solicitud
            usuario_id: ID del usuario que recibe
            observaciones: Observaciones sobre las muestras

        Returns:
            True si la recepcion fue exitosa
        """
        # Actualizar todas las pruebas a estado Recibida
        self.db.execute(f"""
            UPDATE DetalleSolicitudes
            SET Estado = 'Recibida',
                FechaRecepcion = Now(),
                UsuarioRecepcion = {usuario_id}
            WHERE SolicitudID = {solicitud_id}
            AND Estado = 'Pendiente'
        """)

        # Actualizar estado de solicitud
        self.cambiar_estado_solicitud(solicitud_id, 'EnProceso', usuario_id, f'Muestras recibidas. {observaciones}')

        return True

    def rechazar_muestra(self, prueba_solicitada_id, motivo, usuario_id):
        """
        Rechaza una muestra por problemas de calidad

        Args:
            prueba_solicitada_id: ID de la prueba
            motivo: Motivo del rechazo
            usuario_id: ID del usuario

        Returns:
            True si el rechazo fue registrado
        """
        self.db.execute(f"""
            UPDATE DetalleSolicitudes
            SET Estado = 'MuestraRechazada',
                Observaciones = 'RECHAZADA: {motivo.replace("'", "''")}'
            WHERE DetalleID = {prueba_solicitada_id}
        """)

        # Obtener solicitud para registrar en historial
        ps = self.db.query_one(f"SELECT SolicitudID FROM DetalleSolicitudes WHERE DetalleID = {prueba_solicitada_id}")
        if ps:
            self._registrar_historial(ps['SolicitudID'], f'Muestra rechazada: {motivo}', usuario_id)

        return True

    # -------------------------------------------------------------------------
    # VALIDACION DE RESULTADOS
    # -------------------------------------------------------------------------

    def validar_resultados(self, solicitud_id, usuario_id, comentarios=''):
        """
        Valida todos los resultados de una solicitud

        Args:
            solicitud_id: ID de la solicitud
            usuario_id: ID del supervisor que valida
            comentarios: Comentarios de validacion

        Returns:
            True si la validacion fue exitosa
        """
        # Verificar que todas las pruebas esten completas
        pendientes = self.db.query_one(f"""
            SELECT COUNT(*) as Cuenta
            FROM DetalleSolicitudes
            WHERE SolicitudID = {solicitud_id}
            AND Estado NOT IN ('Completada', 'Validada')
        """)

        if pendientes and pendientes.get('Cuenta', 0) > 0:
            raise Exception(f"Hay {pendientes['Cuenta']} pruebas sin completar")

        # Validar todas las pruebas
        self.db.execute(f"""
            UPDATE DetalleSolicitudes
            SET Estado = 'Validada',
                FechaValidacion = Now(),
                UsuarioValido = {usuario_id}
            WHERE SolicitudID = {solicitud_id}
            AND Estado = 'Completada'
        """)

        # Cambiar estado de solicitud
        self.cambiar_estado_solicitud(solicitud_id, 'Validada', usuario_id, comentarios)

        return True

    # -------------------------------------------------------------------------
    # ENTREGA DE RESULTADOS
    # -------------------------------------------------------------------------

    def registrar_entrega(self, solicitud_id, usuario_id, receptor='Paciente', documento_receptor=''):
        """
        Registra la entrega de resultados al paciente

        Args:
            solicitud_id: ID de la solicitud
            usuario_id: ID del usuario que entrega
            receptor: Quien recibe (Paciente, Familiar, Otro)
            documento_receptor: Documento de quien recibe

        Returns:
            True si la entrega fue registrada
        """
        self.db.execute(f"""
            UPDATE Solicitudes
            SET FechaEntrega = Now(),
                RecibidoPor = '{receptor}',
                DocumentoReceptor = '{documento_receptor}'
            WHERE SolicitudID = {solicitud_id}
        """)

        self.cambiar_estado_solicitud(
            solicitud_id, 'Entregada', usuario_id,
            f'Entregado a: {receptor} ({documento_receptor})'
        )

        return True

    # -------------------------------------------------------------------------
    # HISTORIAL Y AUDITORIA
    # -------------------------------------------------------------------------

    def _registrar_historial(self, solicitud_id, accion, usuario_id):
        """Registra una accion en el historial de la solicitud"""
        try:
            self.db.execute(f"""
                INSERT INTO HistorialSolicitudes
                (SolicitudID, Accion, FechaAccion, UsuarioID)
                VALUES
                ({solicitud_id}, '{accion.replace("'", "''")}', Now(), {usuario_id})
            """)
        except:
            pass  # Tabla puede no existir

    def obtener_historial(self, solicitud_id):
        """Obtiene el historial de una solicitud"""
        try:
            return self.db.query(f"""
                SELECT h.*, u.NombreUsuario
                FROM HistorialSolicitudes h
                LEFT JOIN Usuarios u ON h.UsuarioID = u.UsuarioID
                WHERE h.SolicitudID = {solicitud_id}
                ORDER BY h.FechaAccion DESC
            """)
        except:
            return []

    # -------------------------------------------------------------------------
    # CONSULTAS DE ESTADO
    # -------------------------------------------------------------------------

    def obtener_solicitudes_pendientes(self, area_id=None):
        """
        Obtiene solicitudes pendientes de procesar

        Args:
            area_id: Filtrar por area (opcional)

        Returns:
            Lista de solicitudes pendientes
        """
        where_area = ""
        if area_id:
            where_area = f"""
                AND s.SolicitudID IN (
                    SELECT DISTINCT d.SolicitudID
                    FROM DetalleSolicitudes d
                    INNER JOIN Pruebas p ON d.PruebaID = p.PruebaID
                    WHERE p.AreaID = {area_id}
                )
            """

        return self.db.query(f"""
            SELECT s.*, p.Nombres + ' ' + p.Apellidos as NombrePaciente,
                   p.NumeroDocumento,
                   (SELECT COUNT(*) FROM DetalleSolicitudes WHERE SolicitudID = s.SolicitudID) as TotalPruebas,
                   (SELECT COUNT(*) FROM DetalleSolicitudes WHERE SolicitudID = s.SolicitudID AND Estado = 'Completada') as PruebasCompletadas
            FROM Solicitudes s
            INNER JOIN Pacientes p ON s.PacienteID = p.PacienteID
            WHERE s.EstadoSolicitud IN ('Pagada', 'EnProceso', 'EnAnalisis')
            {where_area}
            ORDER BY s.Prioridad DESC, s.FechaSolicitud
        """)

    def obtener_pruebas_por_area(self, area_id, estado=None):
        """
        Obtiene pruebas pendientes por area

        Args:
            area_id: ID del area
            estado: Filtrar por estado (opcional)

        Returns:
            Lista de pruebas
        """
        where_estado = f"AND d.Estado = '{estado}'" if estado else "AND d.Estado IN ('Recibida', 'EnProceso')"

        return self.db.query(f"""
            SELECT d.*, pr.NombrePrueba, s.NumeroSolicitud,
                   pac.Nombres + ' ' + pac.Apellidos as NombrePaciente
            FROM DetalleSolicitudes d
            INNER JOIN Pruebas pr ON d.PruebaID = pr.PruebaID
            INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID
            INNER JOIN Pacientes pac ON s.PacienteID = pac.PacienteID
            WHERE pr.AreaID = {area_id}
            {where_estado}
            ORDER BY s.Prioridad DESC, d.FechaRegistro
        """)

    def obtener_estadisticas_dia(self, fecha=None):
        """
        Obtiene estadisticas del dia

        Args:
            fecha: Fecha a consultar (default: hoy)

        Returns:
            dict con estadisticas
        """
        if fecha is None:
            fecha = datetime.now().date()

        fecha_str = fecha.strftime('%m/%d/%Y')

        stats = {}

        # Total de solicitudes
        result = self.db.query_one(f"""
            SELECT COUNT(*) as Total FROM Solicitudes
            WHERE DATEVALUE(FechaSolicitud) = #{fecha_str}#
        """)
        stats['total_solicitudes'] = result.get('Total', 0) if result else 0

        # Por estado
        estados = self.db.query(f"""
            SELECT EstadoSolicitud, COUNT(*) as Cantidad
            FROM Solicitudes
            WHERE DATEVALUE(FechaSolicitud) = #{fecha_str}#
            GROUP BY EstadoSolicitud
        """)
        stats['por_estado'] = {e['EstadoSolicitud']: e['Cantidad'] for e in estados}

        # Pruebas realizadas
        result = self.db.query_one(f"""
            SELECT COUNT(*) as Total FROM DetalleSolicitudes d
            INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID
            WHERE DATEVALUE(s.FechaSolicitud) = #{fecha_str}#
        """)
        stats['total_pruebas'] = result.get('Total', 0) if result else 0

        # Pruebas completadas
        result = self.db.query_one(f"""
            SELECT COUNT(*) as Total FROM DetalleSolicitudes d
            INNER JOIN Solicitudes s ON d.SolicitudID = s.SolicitudID
            WHERE DATEVALUE(s.FechaSolicitud) = #{fecha_str}#
            AND d.Estado IN ('Completada', 'Validada')
        """)
        stats['pruebas_completadas'] = result.get('Total', 0) if result else 0

        return stats


# ============================================================================
# EJEMPLO DE USO
# ============================================================================

if __name__ == "__main__":
    print("Modulo de Flujo de Trabajo - ANgesLAB")
    print("=" * 50)

    print("\nEstados de Solicitud:")
    for estado in EstadoSolicitud:
        transiciones = [t.value for t in TRANSICIONES_SOLICITUD.get(estado, [])]
        print(f"  {estado.value} -> {', '.join(transiciones) or 'Final'}")

    print("\nEstados de Prueba:")
    for estado in EstadoPrueba:
        transiciones = [t.value for t in TRANSICIONES_PRUEBA.get(estado, [])]
        print(f"  {estado.value} -> {', '.join(transiciones) or 'Final'}")

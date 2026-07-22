# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE EQUIPOS - ANgesLAB
================================================================================
Gestión de equipos de laboratorio, mantenimientos y calibraciones.
Inspirado en SICOEXC (frmequipos, frmbuscarequipos).

Funcionalidades:
- CRUD de equipos de laboratorio
- Registro de mantenimientos preventivos y correctivos
- Registro de calibraciones
- Alertas de mantenimiento vencido
- Historial por equipo

Tablas requeridas (creadas por ventana_administrativa.py):
- Equipos
- MantenimientosEquipo

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import logging
from datetime import datetime, date, timedelta

_log = logging.getLogger("angeslab.equipos")


class GestorEquipos:
    """Gestión de equipos de laboratorio."""

    # Estados de equipo
    ESTADO_OPERATIVO = 'Operativo'
    ESTADO_MANTENIMIENTO = 'En Mantenimiento'
    ESTADO_FUERA_SERVICIO = 'Fuera de Servicio'
    ESTADO_BAJA = 'Dado de Baja'

    # Tipos de mantenimiento
    MANT_PREVENTIVO = 'Preventivo'
    MANT_CORRECTIVO = 'Correctivo'
    MANT_CALIBRACION = 'Calibracion'

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD Equipos
    # ------------------------------------------------------------------

    def crear_equipo(self, datos: dict) -> int:
        """
        Registra un nuevo equipo.

        Args:
            datos: dict con Nombre, Marca, Modelo, NumeroSerie,
                   AreaID, FechaAdquisicion, ProximoMantenimiento,
                   FrecuenciaMantenimientoDias, Ubicacion, Observaciones
        """
        nombre = (datos.get('Nombre') or '').strip()
        if not nombre:
            raise ValueError("El nombre del equipo es obligatorio")

        fecha_hoy = datetime.now()

        cols = ['Nombre', 'Estado', 'FechaRegistro', 'Activo']
        vals = [
            f"'{nombre.replace(chr(39), chr(39)*2)}'",
            f"'{self.ESTADO_OPERATIVO}'",
            f"#{fecha_hoy.strftime('%m/%d/%Y %H:%M:%S')}#",
            "True",
        ]

        for campo in ('Marca', 'Modelo', 'NumeroSerie', 'Ubicacion', 'Observaciones'):
            val = datos.get(campo)
            if val:
                cols.append(campo)
                vals.append(f"'{str(val).strip().replace(chr(39), chr(39)*2)}'")

        for campo in ('AreaID', 'FrecuenciaMantenimientoDias'):
            val = datos.get(campo)
            if val is not None:
                cols.append(campo)
                vals.append(str(int(val)))

        for campo in ('FechaAdquisicion', 'ProximoMantenimiento'):
            val = datos.get(campo)
            if val:
                if isinstance(val, (date, datetime)):
                    cols.append(campo)
                    vals.append(f"#{val.strftime('%m/%d/%Y')}#")

        sql = (
            f"INSERT INTO [Equipos] ([{'], ['.join(cols)}]) "
            f"VALUES ({', '.join(vals)})"
        )
        self.db.execute(sql)

        row = self.db.query_one(
            "SELECT TOP 1 EquipoID FROM [Equipos] "
            f"WHERE Nombre='{nombre.replace(chr(39), chr(39)*2)}' "
            "ORDER BY EquipoID DESC"
        )
        equipo_id = (row or {}).get('EquipoID', 0)
        _log.info("Equipo creado: %s (ID=%s)", nombre, equipo_id)
        return equipo_id

    def actualizar_equipo(self, equipo_id: int, datos: dict):
        """Actualiza datos de un equipo."""
        sets = []
        for campo in ('Nombre', 'Marca', 'Modelo', 'NumeroSerie', 'Ubicacion',
                       'Observaciones', 'Estado'):
            val = datos.get(campo)
            if val is not None:
                sets.append(f"[{campo}]='{str(val).strip().replace(chr(39), chr(39)*2)}'")

        for campo in ('AreaID', 'FrecuenciaMantenimientoDias'):
            val = datos.get(campo)
            if val is not None:
                sets.append(f"[{campo}]={int(val)}")

        for campo in ('FechaAdquisicion', 'ProximoMantenimiento'):
            val = datos.get(campo)
            if val and isinstance(val, (date, datetime)):
                sets.append(f"[{campo}]=#{val.strftime('%m/%d/%Y')}#")

        if datos.get('Activo') is not None:
            sets.append(f"[Activo]={datos['Activo']}")

        if sets:
            self.db.execute(
                f"UPDATE [Equipos] SET {', '.join(sets)} WHERE EquipoID={int(equipo_id)}"
            )

    def obtener_equipo(self, equipo_id: int) -> dict:
        return self.db.query_one(
            f"SELECT * FROM [Equipos] WHERE EquipoID={int(equipo_id)}"
        ) or {}

    def listar_equipos(self, area_id: int = None, estado: str = None,
                        solo_activos: bool = True, busqueda: str = None) -> list:
        """Lista equipos con filtros."""
        where = []
        if solo_activos:
            where.append("Activo=True")
        if area_id:
            where.append(f"AreaID={int(area_id)}")
        if estado:
            where.append(f"Estado='{estado}'")
        if busqueda:
            term = busqueda.replace("'", "''").replace("%", "").replace("_", "")
            where.append(f"(Nombre LIKE '%{term}%' OR Marca LIKE '%{term}%' OR Modelo LIKE '%{term}%')")

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        return self.db.query(
            f"SELECT * FROM [Equipos] {where_sql} ORDER BY Nombre"
        ) or []

    def dar_baja(self, equipo_id: int, motivo: str = ''):
        """Da de baja un equipo."""
        self.db.execute(
            f"UPDATE [Equipos] SET Estado='{self.ESTADO_BAJA}', Activo=False, "
            f"Observaciones=Observaciones & ' | BAJA: {motivo.replace(chr(39), chr(39)*2)}' "
            f"WHERE EquipoID={int(equipo_id)}"
        )

    # ------------------------------------------------------------------
    # Mantenimientos y Calibraciones
    # ------------------------------------------------------------------

    def registrar_mantenimiento(self, equipo_id: int, datos: dict) -> int:
        """
        Registra un mantenimiento o calibración.

        Args:
            datos: dict con TipoMantenimiento, Descripcion, FechaRealizado,
                   RealizadoPor, Costo, Observaciones, ProximoMantenimiento
        """
        tipo = datos.get('TipoMantenimiento', self.MANT_PREVENTIVO)
        fecha = datos.get('FechaRealizado', datetime.now())
        if isinstance(fecha, str):
            fecha = datetime.now()

        cols = ['EquipoID', 'TipoMantenimiento', 'FechaRealizado']
        vals = [
            str(int(equipo_id)),
            f"'{tipo}'",
            f"#{fecha.strftime('%m/%d/%Y %H:%M:%S')}#",
        ]

        for campo in ('Descripcion', 'RealizadoPor', 'Observaciones'):
            val = datos.get(campo)
            if val:
                cols.append(campo)
                vals.append(f"'{str(val).strip().replace(chr(39), chr(39)*2)}'")

        costo = datos.get('Costo')
        if costo is not None:
            cols.append('Costo')
            vals.append(str(float(costo)))

        sql = (
            f"INSERT INTO [MantenimientosEquipo] ([{'], ['.join(cols)}]) "
            f"VALUES ({', '.join(vals)})"
        )
        self.db.execute(sql)

        # Actualizar equipo: último mantenimiento y próximo
        sets_equipo = [
            f"UltimoMantenimiento=#{fecha.strftime('%m/%d/%Y')}#",
            f"Estado='{self.ESTADO_OPERATIVO}'",
        ]
        prox = datos.get('ProximoMantenimiento')
        if prox and isinstance(prox, (date, datetime)):
            sets_equipo.append(f"ProximoMantenimiento=#{prox.strftime('%m/%d/%Y')}#")
        else:
            # Calcular próximo según frecuencia
            equipo = self.obtener_equipo(equipo_id)
            freq = int(equipo.get('FrecuenciaMantenimientoDias', 0))
            if freq > 0:
                prox_fecha = fecha + timedelta(days=freq)
                sets_equipo.append(f"ProximoMantenimiento=#{prox_fecha.strftime('%m/%d/%Y')}#")

        self.db.execute(
            f"UPDATE [Equipos] SET {', '.join(sets_equipo)} "
            f"WHERE EquipoID={int(equipo_id)}"
        )

        row = self.db.query_one(
            "SELECT TOP 1 MantenimientoID FROM [MantenimientosEquipo] "
            f"WHERE EquipoID={int(equipo_id)} ORDER BY MantenimientoID DESC"
        )
        mant_id = (row or {}).get('MantenimientoID', 0)
        _log.info("Mantenimiento registrado: equipo=%s, tipo=%s (ID=%s)",
                   equipo_id, tipo, mant_id)
        return mant_id

    def obtener_historial_mantenimiento(self, equipo_id: int) -> list:
        """Historial de mantenimientos de un equipo."""
        return self.db.query(
            f"SELECT * FROM [MantenimientosEquipo] "
            f"WHERE EquipoID={int(equipo_id)} "
            f"ORDER BY FechaRealizado DESC"
        ) or []

    # ------------------------------------------------------------------
    # Alertas
    # ------------------------------------------------------------------

    def obtener_alertas_mantenimiento(self, dias_anticipacion: int = 7) -> list:
        """Equipos con mantenimiento vencido o próximo a vencer."""
        fecha_limite = (date.today() + timedelta(days=dias_anticipacion)).strftime('%m/%d/%Y')
        fecha_hoy = date.today().strftime('%m/%d/%Y')

        sql = (
            f"SELECT EquipoID, Nombre, Marca, Modelo, Estado, "
            f"ProximoMantenimiento, UltimoMantenimiento, "
            f"IIF(ProximoMantenimiento < #{fecha_hoy}#, 'VENCIDO', 'PROXIMO') AS EstadoMant "
            f"FROM [Equipos] "
            f"WHERE Activo=True AND ProximoMantenimiento IS NOT NULL "
            f"AND ProximoMantenimiento <= #{fecha_limite}# "
            f"ORDER BY ProximoMantenimiento ASC"
        )
        return self.db.query(sql) or []

    # ------------------------------------------------------------------
    # Resumen
    # ------------------------------------------------------------------

    def resumen_equipos(self) -> dict:
        """Resumen del estado de equipos."""
        sql = (
            "SELECT Estado, COUNT(*) AS Total "
            "FROM [Equipos] WHERE Activo=True GROUP BY Estado"
        )
        por_estado = self.db.query(sql) or []

        total = sum(int(r.get('Total', 0)) for r in por_estado)
        alertas = self.obtener_alertas_mantenimiento()

        return {
            'total_equipos': total,
            'por_estado': por_estado,
            'alertas_mantenimiento': len(alertas),
            'alertas': alertas,
        }


# ============================================================================
# FACTORY
# ============================================================================

def crear_gestor_equipos(db):
    """Crea una instancia del gestor de equipos."""
    return GestorEquipos(db)

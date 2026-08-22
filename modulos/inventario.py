# -*- coding: utf-8 -*-
"""
================================================================================
MODULO DE INVENTARIO - ANgesLAB
================================================================================
Gestion de reactivos, insumos consumibles y control de stock.

Funcionalidades:
- CRUD de productos/insumos/reactivos
- Control de stock con alertas de minimo
- Movimientos de inventario (entrada, salida, ajuste)
- Alertas de vencimiento proximo
- Costos y valorizacion de inventario
- Vinculacion con proveedores

Tablas DB reales:
- Productos (ProductoID, CodigoProducto, NombreProducto, TipoProducto, etc.)
- MovimientosInventario (MovimientoID, ProductoID, TipoMovimiento, etc.)
- Proveedores (ProveedorID, RazonSocial, etc.)

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP

_log = logging.getLogger("angeslab.inventario")


# ============================================================================
# GESTOR DE INVENTARIO
# ============================================================================

class GestorInventario:
    """Gestion completa de productos, reactivos y stock del laboratorio."""

    # Tipos de producto
    TIPO_REACTIVO = 'Reactivo'
    TIPO_CONSUMIBLE = 'Consumible'
    TIPO_MATERIAL = 'Material'
    TIPOS_VALIDOS = (TIPO_REACTIVO, TIPO_CONSUMIBLE, TIPO_MATERIAL)

    # Tipos de movimiento
    MOV_ENTRADA = 'Entrada'
    MOV_SALIDA = 'Salida'
    MOV_AJUSTE = 'Ajuste'
    MOV_DEVOLUCION = 'Devolucion'

    # Dias para alerta de vencimiento proximo
    DIAS_ALERTA_VENCIMIENTO = 30

    def __init__(self, db):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD de Productos
    # ------------------------------------------------------------------

    def crear_insumo(self, datos: dict) -> int:
        """
        Crea un nuevo producto/insumo/reactivo en tabla Productos.

        Args:
            datos: dict con Nombre, Codigo, Tipo, UnidadMedida, StockActual,
                   StockMinimo, CostoUnitario, Ubicacion, Observaciones, etc.

        Returns:
            ProductoID del registro creado
        """
        nombre = (datos.get('Nombre') or '').strip()
        if not nombre:
            raise ValueError("El nombre del producto es obligatorio")

        tipo = datos.get('Tipo', self.TIPO_REACTIVO)

        campos = {
            'NombreProducto': nombre,
            'TipoProducto': tipo,
            'UnidadMedida': datos.get('UnidadMedida') or datos.get('Unidad') or 'Und',
            'ExistenciaActual': float(datos.get('StockActual', 0)),
            'ExistenciaMinima': float(datos.get('StockMinimo', 0)),
            'UltimoPrecioCompra': float(datos.get('CostoUnitario', 0)),
            'Activo': True,
            'FechaCreacion': datetime.now(),
        }

        codigo = (datos.get('Codigo') or '').strip()
        if codigo:
            campos['CodigoProducto'] = codigo

        desc = (datos.get('Ubicacion') or datos.get('Descripcion') or '').strip()
        if desc:
            campos['Descripcion'] = desc

        presentacion = (datos.get('Presentacion') or '').strip()
        if presentacion:
            campos['Presentacion'] = presentacion

        self.db.execute(self._build_insert('Productos', campos))

        # Recuperar el ID generado
        row = self.db.query_one(
            "SELECT TOP 1 ProductoID FROM [Productos] "
            f"WHERE NombreProducto='{nombre.replace(chr(39), chr(39)*2)}' "
            "ORDER BY ProductoID DESC"
        )
        producto_id = (row or {}).get('ProductoID', 0)
        _log.info("Producto creado: %s (ID=%s)", nombre, producto_id)
        return producto_id

    def actualizar_insumo(self, producto_id: int, datos: dict):
        """Actualiza datos de un producto existente."""
        # Mapeo de nombres logicos a columnas reales
        map_texto = {
            'Nombre': 'NombreProducto',
            'Codigo': 'CodigoProducto',
            'Tipo': 'TipoProducto',
            'UnidadMedida': 'UnidadMedida',
            'Ubicacion': 'Descripcion',
            'Presentacion': 'Presentacion',
        }
        map_num = {
            'StockMinimo': 'ExistenciaMinima',
            'CostoUnitario': 'UltimoPrecioCompra',
        }

        sets = []
        for dato_key, col in map_texto.items():
            val = datos.get(dato_key)
            if val is not None:
                sets.append(f"[{col}]='{str(val).strip().replace(chr(39), chr(39)*2)}'")

        for dato_key, col in map_num.items():
            val = datos.get(dato_key)
            if val is not None:
                sets.append(f"[{col}]={float(val)}")

        if datos.get('Activo') is not None:
            sets.append(f"[Activo]={datos['Activo']}")

        if not sets:
            return

        sql = f"UPDATE [Productos] SET {', '.join(sets)} WHERE ProductoID={int(producto_id)}"
        self.db.execute(sql)
        _log.info("Producto actualizado: ID=%s", producto_id)

    def desactivar_insumo(self, producto_id: int):
        """Desactiva un producto (no lo elimina)."""
        self.db.execute(
            f"UPDATE [Productos] SET Activo=False WHERE ProductoID={int(producto_id)}"
        )

    def obtener_insumo(self, producto_id: int) -> dict:
        """Obtiene datos completos de un producto."""
        return self.db.query_one(
            f"SELECT * FROM [Productos] WHERE ProductoID={int(producto_id)}"
        ) or {}

    def listar_insumos(self, tipo: str = None, solo_activos: bool = True,
                        area_id: int = None, busqueda: str = None) -> list:
        """
        Lista productos con filtros opcionales.

        Retorna dicts con claves normalizadas para compatibilidad con la UI:
        ProductoID, CodigoProducto, NombreProducto, TipoProducto,
        ExistenciaActual, ExistenciaMinima, UltimoPrecioCompra, Descripcion
        """
        where = []
        if solo_activos:
            where.append("p.Activo=True")
        if tipo:
            where.append(f"p.TipoProducto='{tipo}'")
        if busqueda:
            term = busqueda.replace("'", "''").replace("%", "").replace("_", "")
            where.append(f"(p.NombreProducto LIKE '%{term}%' OR p.CodigoProducto LIKE '%{term}%')")

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        sql = (
            f"SELECT p.* "
            f"FROM [Productos] AS p "
            f"{where_sql} "
            f"ORDER BY p.NombreProducto"
        )
        return self.db.query(sql) or []

    # ------------------------------------------------------------------
    # Control de Stock y Movimientos
    # ------------------------------------------------------------------

    def registrar_movimiento(self, producto_id: int, tipo_mov: str,
                              cantidad: float, motivo: str = '',
                              lote: str = None, usuario: str = None,
                              costo_unitario: float = None) -> int:
        """
        Registra un movimiento de inventario y actualiza stock.

        Args:
            producto_id: ID del producto
            tipo_mov: Entrada, Salida, Ajuste, Devolucion
            cantidad: Cantidad (positiva)
            motivo: Descripcion del movimiento
            lote: Numero de lote (opcional)
            usuario: Nombre del usuario que registra
            costo_unitario: Costo por unidad en este movimiento

        Returns:
            MovimientoID
        """
        cantidad = abs(float(cantidad))
        if cantidad == 0:
            raise ValueError("La cantidad no puede ser cero")

        # Obtener stock actual
        producto = self.obtener_insumo(producto_id)
        if not producto:
            raise ValueError(f"Producto no encontrado: {producto_id}")

        stock_anterior = float(producto.get('ExistenciaActual', 0) or 0)

        # Calcular nuevo stock
        if tipo_mov in (self.MOV_ENTRADA, self.MOV_DEVOLUCION):
            stock_nuevo = stock_anterior + cantidad
        elif tipo_mov == self.MOV_SALIDA:
            stock_nuevo = stock_anterior - cantidad
            if stock_nuevo < 0:
                _log.warning("Stock negativo para producto %s: %s", producto_id, stock_nuevo)
        elif tipo_mov == self.MOV_AJUSTE:
            stock_nuevo = cantidad  # Ajuste establece el valor absoluto
        else:
            raise ValueError(f"Tipo de movimiento invalido: {tipo_mov}")

        # Registrar movimiento en MovimientosInventario
        campos_mov = {
            'ProductoID': int(producto_id),
            'TipoMovimiento': tipo_mov,
            'Cantidad': cantidad,
            'ExistenciaAnterior': stock_anterior,
            'ExistenciaNueva': stock_nuevo,
            'FechaMovimiento': datetime.now(),
            'Motivo': (motivo or '').replace("'", "''"),
        }
        if lote:
            campos_mov['Lote'] = lote.replace("'", "''")
        if usuario:
            campos_mov['UsuarioRegistra'] = str(usuario).replace("'", "''")
        if costo_unitario is not None:
            campos_mov['CostoUnitario'] = float(costo_unitario)
            campos_mov['CostoTotal'] = float(costo_unitario) * cantidad

        self.db.execute(self._build_insert('MovimientosInventario', campos_mov))

        # Actualizar stock en Productos
        sets = [f"ExistenciaActual={stock_nuevo}"]
        if costo_unitario is not None and tipo_mov == self.MOV_ENTRADA:
            sets.append(f"UltimoPrecioCompra={float(costo_unitario)}")
        self.db.execute(
            f"UPDATE [Productos] SET {', '.join(sets)} WHERE ProductoID={int(producto_id)}"
        )

        _log.info("Movimiento %s: producto=%s, cant=%s, stock: %s->%s",
                   tipo_mov, producto_id, cantidad, stock_anterior, stock_nuevo)

        row = self.db.query_one(
            "SELECT TOP 1 MovimientoID FROM [MovimientosInventario] "
            f"WHERE ProductoID={int(producto_id)} ORDER BY MovimientoID DESC"
        )
        return (row or {}).get('MovimientoID', 0)

    def obtener_movimientos(self, producto_id: int = None,
                             fecha_desde: date = None,
                             fecha_hasta: date = None,
                             tipo_mov: str = None) -> list:
        """Lista movimientos de inventario con filtros."""
        where = []
        if producto_id:
            where.append(f"m.ProductoID={int(producto_id)}")
        if fecha_desde:
            where.append(f"m.FechaMovimiento >= #{fecha_desde.strftime('%m/%d/%Y')}#")
        if fecha_hasta:
            where.append(f"m.FechaMovimiento < #{(fecha_hasta + timedelta(days=1)).strftime('%m/%d/%Y')}#")
        if tipo_mov:
            where.append(f"m.TipoMovimiento='{tipo_mov}'")

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        sql = (
            f"SELECT m.*, p.NombreProducto, p.UnidadMedida "
            f"FROM [MovimientosInventario] AS m "
            f"INNER JOIN [Productos] AS p ON m.ProductoID = p.ProductoID "
            f"{where_sql} "
            f"ORDER BY m.FechaMovimiento DESC"
        )
        return self.db.query(sql) or []

    # ------------------------------------------------------------------
    # Alertas
    # ------------------------------------------------------------------

    def obtener_alertas_stock_bajo(self) -> list:
        """Retorna productos cuyo stock esta por debajo del minimo."""
        sql = (
            "SELECT ProductoID, NombreProducto, TipoProducto, UnidadMedida, "
            "ExistenciaActual, ExistenciaMinima, UltimoPrecioCompra "
            "FROM [Productos] "
            "WHERE Activo=True AND ExistenciaActual <= ExistenciaMinima "
            "AND ExistenciaMinima > 0 "
            "ORDER BY (ExistenciaActual / IIF(ExistenciaMinima=0, 1, ExistenciaMinima)) ASC"
        )
        return self.db.query(sql) or []

    def obtener_alertas_vencimiento(self, dias: int = None) -> list:
        """Retorna productos con fecha de vencimiento proxima o pasada."""
        dias = dias or self.DIAS_ALERTA_VENCIMIENTO
        fecha_limite = (date.today() + timedelta(days=dias)).strftime('%m/%d/%Y')
        fecha_hoy = date.today().strftime('%m/%d/%Y')

        sql = (
            f"SELECT ProductoID, NombreProducto, Lote, FechaVencimiento, "
            f"ExistenciaActual, UnidadMedida, "
            f"IIF(FechaVencimiento < #{fecha_hoy}#, 'VENCIDO', 'POR VENCER') AS EstadoVenc "
            f"FROM [Productos] "
            f"WHERE Activo=True AND FechaVencimiento IS NOT NULL "
            f"AND FechaVencimiento <= #{fecha_limite}# "
            f"ORDER BY FechaVencimiento ASC"
        )
        return self.db.query(sql) or []

    def obtener_todas_alertas(self) -> dict:
        """Retorna todas las alertas de inventario consolidadas."""
        stock_bajo = self.obtener_alertas_stock_bajo()
        vencimiento = self.obtener_alertas_vencimiento()
        return {
            'stock_bajo': stock_bajo,
            'vencimiento': vencimiento,
            'total_alertas': len(stock_bajo) + len(vencimiento),
        }

    # ------------------------------------------------------------------
    # Reportes y Valorizacion
    # ------------------------------------------------------------------

    def valorizacion_inventario(self) -> dict:
        """Calcula el valor total del inventario."""
        sql = (
            "SELECT TipoProducto, COUNT(*) AS Items, "
            "SUM(ExistenciaActual) AS UnidadesTotales, "
            "SUM(ExistenciaActual * IIF(UltimoPrecioCompra IS NULL, 0, UltimoPrecioCompra)) AS ValorTotal "
            "FROM [Productos] "
            "WHERE Activo=True "
            "GROUP BY TipoProducto"
        )
        filas = self.db.query(sql) or []
        total_valor = sum(float(f.get('ValorTotal', 0) or 0) for f in filas)
        total_items = sum(int(f.get('Items', 0) or 0) for f in filas)

        return {
            'por_tipo': filas,
            'total_items': total_items,
            'valor_total': total_valor,
        }

    def resumen_consumo(self, fecha_desde: date = None,
                         fecha_hasta: date = None) -> list:
        """Resumen de consumo (salidas) por producto en un periodo."""
        if not fecha_desde:
            fecha_desde = date.today().replace(day=1)
        if not fecha_hasta:
            fecha_hasta = date.today()

        sql = (
            f"SELECT p.ProductoID, p.NombreProducto, p.UnidadMedida, p.TipoProducto, "
            f"SUM(m.Cantidad) AS TotalConsumido, "
            f"COUNT(m.MovimientoID) AS NumMovimientos "
            f"FROM [MovimientosInventario] AS m "
            f"INNER JOIN [Productos] AS p ON m.ProductoID = p.ProductoID "
            f"WHERE m.TipoMovimiento='Salida' "
            f"AND m.FechaMovimiento >= #{fecha_desde.strftime('%m/%d/%Y')}# "
            f"AND m.FechaMovimiento < #{(fecha_hasta + timedelta(days=1)).strftime('%m/%d/%Y')}# "
            f"GROUP BY p.ProductoID, p.NombreProducto, p.UnidadMedida, p.TipoProducto "
            f"ORDER BY SUM(m.Cantidad) DESC"
        )
        return self.db.query(sql) or []

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_insert(self, tabla: str, campos: dict) -> str:
        """Construye INSERT INTO con formateo Access."""
        cols = []
        vals = []
        for k, v in campos.items():
            cols.append(f"[{k}]")
            if v is None:
                vals.append("NULL")
            elif isinstance(v, bool):
                vals.append("True" if v else "False")
            elif isinstance(v, (int, float, Decimal)):
                vals.append(str(v))
            elif isinstance(v, datetime):
                vals.append(f"#{v.strftime('%m/%d/%Y %H:%M:%S')}#")
            elif isinstance(v, date):
                vals.append(f"#{v.strftime('%m/%d/%Y')}#")
            else:
                vals.append(f"'{str(v).replace(chr(39), chr(39)*2)}'")
        return f"INSERT INTO [{tabla}] ({', '.join(cols)}) VALUES ({', '.join(vals)})"


# ============================================================================
# FACTORY
# ============================================================================

def crear_gestor_inventario(db):
    """Crea una instancia del gestor de inventario."""
    return GestorInventario(db)

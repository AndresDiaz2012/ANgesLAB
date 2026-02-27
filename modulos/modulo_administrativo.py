# -*- coding: utf-8 -*-
"""
Módulo Administrativo - Lógica de Negocio
ANgesLAB - Sistema de Gestión de Laboratorio Clínico

Clases:
- ControlAcceso: RBAC (permisos por rol/usuario)
- GestorCajaChica: Apertura/cierre de caja y movimientos
- GestorCuentasPorCobrar: Cartera de clientes
- GestorCuentasPorPagar: Deudas con proveedores
- GestorGastos: Registro y control de gastos
- ResumenFinanciero: Dashboard e indicadores

Copyright © 2024-2025 ANgesLAB Solutions
"""

from datetime import datetime, date, timedelta


class ControlAcceso:
    """Control de acceso basado en roles (RBAC)."""

    def __init__(self, db):
        self.db = db
        self._cache = {}
        self._tablas_disponibles = None

    def _tablas_existen(self):
        """Verifica si las tablas RBAC están disponibles."""
        if self._tablas_disponibles is not None:
            return self._tablas_disponibles
        try:
            self.db.query("SELECT TOP 1 * FROM [Roles]")
            self.db.query("SELECT TOP 1 * FROM [PermisosModulo]")
            self.db.query("SELECT TOP 1 * FROM [UsuarioRol]")
            self._tablas_disponibles = True
        except:
            self._tablas_disponibles = False
        return self._tablas_disponibles

    def tiene_permiso(self, usuario_id, modulo, tipo='PuedeVer'):
        """Verifica si el usuario tiene un permiso específico.

        Args:
            usuario_id: ID del usuario
            modulo: Nombre del módulo (caja_chica, facturacion, etc.)
            tipo: PuedeVer, PuedeCrear, PuedeEditar, PuedeEliminar, PuedeExportar

        Returns:
            True si tiene permiso, True si tablas no existen (compatibilidad)
        """
        if not self._tablas_existen():
            return True

        cache_key = f"{usuario_id}_{modulo}_{tipo}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            sql = (
                f"SELECT p.{tipo} FROM [PermisosModulo] p "
                f"INNER JOIN [UsuarioRol] ur ON p.RolID = ur.RolID "
                f"WHERE ur.UsuarioID = {usuario_id} AND ur.Activo = True "
                f"AND p.NombreModulo = '{modulo}' "
                f"ORDER BY p.{tipo} DESC"
            )
            resultado = self.db.query_one(sql)
            tiene = bool(resultado and resultado.get(tipo))
            self._cache[cache_key] = tiene
            return tiene
        except:
            return True

    def obtener_permisos_modulo(self, usuario_id, modulo):
        """Retorna dict completo de permisos para un módulo."""
        if not self._tablas_existen():
            return {
                'PuedeVer': True, 'PuedeCrear': True, 'PuedeEditar': True,
                'PuedeEliminar': True, 'PuedeExportar': True
            }
        try:
            sql = (
                f"SELECT p.PuedeVer, p.PuedeCrear, p.PuedeEditar, p.PuedeEliminar, p.PuedeExportar "
                f"FROM [PermisosModulo] p "
                f"INNER JOIN [UsuarioRol] ur ON p.RolID = ur.RolID "
                f"WHERE ur.UsuarioID = {usuario_id} AND ur.Activo = True "
                f"AND p.NombreModulo = '{modulo}'"
            )
            resultado = self.db.query_one(sql)
            if resultado:
                return {k: bool(v) for k, v in resultado.items()}
            return {
                'PuedeVer': False, 'PuedeCrear': False, 'PuedeEditar': False,
                'PuedeEliminar': False, 'PuedeExportar': False
            }
        except:
            return {
                'PuedeVer': True, 'PuedeCrear': True, 'PuedeEditar': True,
                'PuedeEliminar': True, 'PuedeExportar': True
            }

    def asignar_rol(self, usuario_id, rol_id):
        """Asigna un rol a un usuario."""
        existente = self.db.query_one(
            f"SELECT UsuarioRolID FROM [UsuarioRol] "
            f"WHERE UsuarioID={usuario_id} AND RolID={rol_id}"
        )
        if existente:
            self.db.update('UsuarioRol', {'Activo': True},
                          f"UsuarioID={usuario_id} AND RolID={rol_id}")
        else:
            self.db.insert('UsuarioRol', {
                'UsuarioID': usuario_id, 'RolID': rol_id, 'Activo': True
            })
        self._cache.clear()

    def remover_rol(self, usuario_id, rol_id):
        """Desactiva un rol de un usuario."""
        self.db.update('UsuarioRol', {'Activo': False},
                      f"UsuarioID={usuario_id} AND RolID={rol_id}")
        self._cache.clear()

    def crear_rol(self, nombre, descripcion, nivel_acceso):
        """Crea un nuevo rol."""
        self.db.insert('Roles', {
            'NombreRol': nombre,
            'Descripcion': descripcion,
            'NivelAcceso': nivel_acceso,
            'Activo': True
        })

    def actualizar_permisos(self, rol_id, modulo, permisos):
        """Actualiza permisos de un rol para un módulo.

        Args:
            permisos: dict con PuedeVer, PuedeCrear, etc.
        """
        existente = self.db.query_one(
            f"SELECT PermisoID FROM [PermisosModulo] "
            f"WHERE RolID={rol_id} AND NombreModulo='{modulo}'"
        )
        if existente:
            self.db.update('PermisosModulo', permisos,
                          f"RolID={rol_id} AND NombreModulo='{modulo}'")
        else:
            permisos['RolID'] = rol_id
            permisos['NombreModulo'] = modulo
            self.db.insert('PermisosModulo', permisos)
        self._cache.clear()

    def listar_roles(self):
        """Lista todos los roles activos."""
        try:
            return self.db.query("SELECT * FROM [Roles] WHERE Activo=True ORDER BY NivelAcceso DESC")
        except:
            return []

    def listar_usuarios_con_roles(self):
        """Lista usuarios con sus roles asignados."""
        try:
            return self.db.query(
                "SELECT u.UsuarioID, u.NombreCompleto, u.NombreUsuario, "
                "r.NombreRol, r.NivelAcceso, ur.Activo "
                "FROM ([Usuarios] u LEFT JOIN [UsuarioRol] ur ON u.UsuarioID = ur.UsuarioID) "
                "LEFT JOIN [Roles] r ON ur.RolID = r.RolID "
                "ORDER BY u.NombreCompleto"
            )
        except:
            return []


class GestorCajaChica:
    """Gestión de caja chica: apertura, cierre y movimientos."""

    def __init__(self, db):
        self.db = db

    def obtener_caja_abierta(self):
        """Retorna la caja abierta del día actual, o None."""
        try:
            hoy = datetime.now().strftime('%m/%d/%Y')
            return self.db.query_one(
                f"SELECT * FROM [CajaChica] WHERE Estado='Abierta' "
                f"AND FechaApertura >= #{hoy}#"
            )
        except:
            return None

    def abrir_caja(self, monto_apertura, efectivo_inicial, usuario_id):
        """Abre una nueva caja. Retorna (exito, mensaje)."""
        caja_abierta = self.obtener_caja_abierta()
        if caja_abierta:
            return False, "Ya existe una caja abierta para hoy"

        try:
            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            self.db.execute(
                f"INSERT INTO [CajaChica] (FechaApertura, MontoApertura, EfectivoInicial, "
                f"TotalIngresos, TotalEgresos, Diferencia, Estado, UsuarioApertura) "
                f"VALUES ({fecha}, {monto_apertura}, {efectivo_inicial}, 0, 0, 0, 'Abierta', {usuario_id})"
            )
            return True, "Caja abierta exitosamente"
        except Exception as e:
            return False, f"Error al abrir caja: {e}"

    def cerrar_caja(self, caja_id, efectivo_final, observaciones, usuario_id):
        """Cierra la caja y calcula el cuadre."""
        try:
            caja = self.db.query_one(f"SELECT * FROM [CajaChica] WHERE CajaID={caja_id}")
            if not caja:
                return False, "Caja no encontrada"
            if caja.get('Estado') != 'Abierta':
                return False, "La caja no está abierta"

            esperado = float(caja.get('EfectivoInicial', 0) or 0) + \
                       float(caja.get('TotalIngresos', 0) or 0) - \
                       float(caja.get('TotalEgresos', 0) or 0)
            diferencia = float(efectivo_final) - esperado

            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            obs_safe = str(observaciones).replace("'", "''") if observaciones else ''
            self.db.execute(
                f"UPDATE [CajaChica] SET FechaCierre={fecha}, EfectivoFinal={efectivo_final}, "
                f"Diferencia={diferencia}, Estado='Cerrada', UsuarioCierre={usuario_id}, "
                f"Observaciones='{obs_safe}' WHERE CajaID={caja_id}"
            )
            return True, f"Caja cerrada. Diferencia: {diferencia:.2f}"
        except Exception as e:
            return False, f"Error al cerrar caja: {e}"

    def registrar_movimiento(self, caja_id, datos, usuario_id):
        """Registra un movimiento (Ingreso/Egreso) en la caja.

        Args:
            datos: dict con Tipo, Categoria, Descripcion, Monto, FormaPagoID, Referencia, FacturaID
        """
        try:
            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')
            monto = float(datos.get('Monto', 0))
            tipo = datos.get('Tipo', 'Ingreso')
            categoria = str(datos.get('Categoria', '')).replace("'", "''")
            descripcion = str(datos.get('Descripcion', '')).replace("'", "''")
            forma_pago_id = datos.get('FormaPagoID', 'Null')
            referencia = str(datos.get('Referencia', '')).replace("'", "''")
            factura_id = datos.get('FacturaID', 'Null')

            self.db.execute(
                f"INSERT INTO [MovimientosCaja] (CajaID, Fecha, Tipo, Categoria, Descripcion, "
                f"Monto, FormaPagoID, Referencia, FacturaID, UsuarioID, Anulado) "
                f"VALUES ({caja_id}, {fecha}, '{tipo}', '{categoria}', '{descripcion}', "
                f"{monto}, {forma_pago_id}, '{referencia}', {factura_id}, {usuario_id}, False)"
            )

            # Actualizar totales de la caja
            if tipo == 'Ingreso':
                self.db.execute(
                    f"UPDATE [CajaChica] SET TotalIngresos = TotalIngresos + {monto} "
                    f"WHERE CajaID={caja_id}"
                )
            else:
                self.db.execute(
                    f"UPDATE [CajaChica] SET TotalEgresos = TotalEgresos + {monto} "
                    f"WHERE CajaID={caja_id}"
                )

            return True, "Movimiento registrado"
        except Exception as e:
            return False, f"Error al registrar movimiento: {e}"

    def anular_movimiento(self, movimiento_id, motivo):
        """Anula un movimiento y revierte el efecto en la caja."""
        try:
            mov = self.db.query_one(
                f"SELECT * FROM [MovimientosCaja] WHERE MovimientoID={movimiento_id}"
            )
            if not mov:
                return False, "Movimiento no encontrado"
            if mov.get('Anulado'):
                return False, "El movimiento ya está anulado"

            motivo_safe = str(motivo).replace("'", "''")
            self.db.execute(
                f"UPDATE [MovimientosCaja] SET Anulado=True, "
                f"MotivoAnulacion='{motivo_safe}' WHERE MovimientoID={movimiento_id}"
            )

            monto = float(mov.get('Monto', 0) or 0)
            caja_id = mov.get('CajaID')
            if mov.get('Tipo') == 'Ingreso':
                self.db.execute(
                    f"UPDATE [CajaChica] SET TotalIngresos = TotalIngresos - {monto} "
                    f"WHERE CajaID={caja_id}"
                )
            else:
                self.db.execute(
                    f"UPDATE [CajaChica] SET TotalEgresos = TotalEgresos - {monto} "
                    f"WHERE CajaID={caja_id}"
                )
            return True, "Movimiento anulado"
        except Exception as e:
            return False, f"Error al anular movimiento: {e}"

    def obtener_movimientos_caja(self, caja_id):
        """Lista movimientos de una caja."""
        try:
            return self.db.query(
                f"SELECT m.*, fp.Nombre as FormaPago FROM [MovimientosCaja] m "
                f"LEFT JOIN [FormasPago] fp ON m.FormaPagoID = fp.FormaPagoID "
                f"WHERE m.CajaID={caja_id} ORDER BY m.Fecha DESC"
            )
        except:
            return []

    def obtener_resumen_caja(self, caja_id):
        """Resumen de la caja con desglose por forma de pago."""
        try:
            caja = self.db.query_one(f"SELECT * FROM [CajaChica] WHERE CajaID={caja_id}")
            desglose = self.db.query(
                f"SELECT fp.Nombre, m.Tipo, SUM(m.Monto) as Total "
                f"FROM [MovimientosCaja] m "
                f"LEFT JOIN [FormasPago] fp ON m.FormaPagoID = fp.FormaPagoID "
                f"WHERE m.CajaID={caja_id} AND m.Anulado=False "
                f"GROUP BY fp.Nombre, m.Tipo"
            )
            return {'caja': caja, 'desglose': desglose}
        except:
            return {'caja': None, 'desglose': []}


class GestorCuentasPorCobrar:
    """Gestión de cuentas por cobrar (cartera de clientes)."""

    def __init__(self, db):
        self.db = db

    def crear_cuenta_desde_factura(self, factura_id):
        """Crea una cuenta por cobrar vinculada a una factura."""
        try:
            factura = self.db.query_one(
                f"SELECT * FROM [Facturas] WHERE FacturaID={factura_id}"
            )
            if not factura:
                return False, "Factura no encontrada"

            monto = float(factura.get('MontoTotal', 0) or factura.get('Total', 0) or 0)
            paciente_id = factura.get('PacienteID', 'Null')
            nombre = str(factura.get('NombrePaciente', '')).replace("'", "''")

            fecha_emision = datetime.now()
            fecha_venc = fecha_emision + timedelta(days=30)
            fe = fecha_emision.strftime('#%m/%d/%Y %H:%M:%S#')
            fv = fecha_venc.strftime('#%m/%d/%Y#')

            self.db.execute(
                f"INSERT INTO [CuentasPorCobrar] (FacturaID, PacienteID, NombrePaciente, "
                f"FechaEmision, FechaVencimiento, MontoOriginal, MontoCobrado, SaldoPendiente, "
                f"DiasVencida, Estado) "
                f"VALUES ({factura_id}, {paciente_id}, '{nombre}', {fe}, {fv}, "
                f"{monto}, 0, {monto}, 0, 'Pendiente')"
            )
            return True, "Cuenta por cobrar creada"
        except Exception as e:
            return False, f"Error al crear cuenta: {e}"

    def registrar_cobro(self, cuenta_id, monto, forma_pago_id, referencia='', registrar_en_caja=True):
        """Registra un cobro parcial o total."""
        try:
            cuenta = self.db.query_one(
                f"SELECT * FROM [CuentasPorCobrar] WHERE CuentaCobrarID={cuenta_id}"
            )
            if not cuenta:
                return False, "Cuenta no encontrada"

            saldo = float(cuenta.get('SaldoPendiente', 0) or 0)
            monto = float(monto)
            if monto > saldo:
                return False, f"El monto ({monto:.2f}) excede el saldo pendiente ({saldo:.2f})"

            cobrado = float(cuenta.get('MontoCobrado', 0) or 0) + monto
            nuevo_saldo = saldo - monto
            estado = 'Cobrada' if nuevo_saldo <= 0 else 'Parcial'

            self.db.execute(
                f"UPDATE [CuentasPorCobrar] SET MontoCobrado={cobrado}, "
                f"SaldoPendiente={nuevo_saldo}, Estado='{estado}' "
                f"WHERE CuentaCobrarID={cuenta_id}"
            )

            # Registrar en caja si hay caja abierta
            if registrar_en_caja:
                gestor_caja = GestorCajaChica(self.db)
                caja = gestor_caja.obtener_caja_abierta()
                if caja:
                    gestor_caja.registrar_movimiento(caja['CajaID'], {
                        'Tipo': 'Ingreso',
                        'Categoria': 'Cobro de factura',
                        'Descripcion': f"Cobro CxC #{cuenta_id}",
                        'Monto': monto,
                        'FormaPagoID': forma_pago_id,
                        'Referencia': referencia,
                        'FacturaID': cuenta.get('FacturaID', 'Null')
                    }, 0)

            return True, f"Cobro registrado. Saldo pendiente: {nuevo_saldo:.2f}"
        except Exception as e:
            return False, f"Error al registrar cobro: {e}"

    def listar_cuentas(self, estado=None, paciente=None, solo_vencidas=False):
        """Lista cuentas por cobrar con filtros."""
        try:
            sql = "SELECT * FROM [CuentasPorCobrar] WHERE 1=1"
            if estado:
                estado_safe = str(estado).replace("'", "''")
                sql += f" AND Estado='{estado_safe}'"
            if paciente:
                paciente_safe = str(paciente).replace("'", "''").replace("%", "").replace("_", "")
                sql += f" AND NombrePaciente LIKE '%{paciente_safe}%'"
            if solo_vencidas:
                hoy = datetime.now().strftime('#%m/%d/%Y#')
                sql += f" AND FechaVencimiento < {hoy} AND Estado <> 'Cobrada'"
            sql += " ORDER BY FechaEmision DESC"
            cuentas = self.db.query(sql)

            # Actualizar días vencidos
            hoy = datetime.now()
            for c in cuentas:
                fv = c.get('FechaVencimiento')
                if fv and c.get('Estado') != 'Cobrada':
                    try:
                        if isinstance(fv, str):
                            fv = datetime.strptime(fv, '%m/%d/%Y')
                        dias = (hoy - fv).days
                        c['DiasVencida'] = max(0, dias)
                    except:
                        pass
            return cuentas
        except:
            return []

    def obtener_resumen_cartera(self):
        """Resumen aging: vigente, 30, 60, 90, +90 días."""
        try:
            cuentas = self.db.query(
                "SELECT * FROM [CuentasPorCobrar] WHERE Estado <> 'Cobrada'"
            )
            resumen = {
                'vigente': 0, '30_dias': 0, '60_dias': 0,
                '90_dias': 0, 'mas_90': 0, 'total': 0
            }
            hoy = datetime.now()
            for c in cuentas:
                saldo = float(c.get('SaldoPendiente', 0) or 0)
                resumen['total'] += saldo
                fv = c.get('FechaVencimiento')
                dias = 0
                if fv:
                    try:
                        if isinstance(fv, str):
                            fv = datetime.strptime(fv, '%m/%d/%Y')
                        dias = (hoy - fv).days
                    except:
                        pass

                if dias <= 0:
                    resumen['vigente'] += saldo
                elif dias <= 30:
                    resumen['30_dias'] += saldo
                elif dias <= 60:
                    resumen['60_dias'] += saldo
                elif dias <= 90:
                    resumen['90_dias'] += saldo
                else:
                    resumen['mas_90'] += saldo

            return resumen
        except:
            return {
                'vigente': 0, '30_dias': 0, '60_dias': 0,
                '90_dias': 0, 'mas_90': 0, 'total': 0
            }


class GestorCuentasPorPagar:
    """Gestión de cuentas por pagar (proveedores)."""

    def __init__(self, db):
        self.db = db

    def crear_cuenta(self, datos):
        """Crea una nueva cuenta por pagar."""
        try:
            monto = float(datos.get('MontoOriginal', 0))
            proveedor = str(datos.get('ProveedorNombre', '')).replace("'", "''")
            rif = str(datos.get('ProveedorRIF', '')).replace("'", "''")
            doc = str(datos.get('NumeroDocumento', '')).replace("'", "''")
            cat_id = datos.get('CategoriaGastoID', 'Null')
            obs = str(datos.get('Observaciones', '')).replace("'", "''")

            fecha_emision = datetime.now()
            dias_venc = int(datos.get('DiasVencimiento', 30))
            fecha_venc = fecha_emision + timedelta(days=dias_venc)
            fe = fecha_emision.strftime('#%m/%d/%Y %H:%M:%S#')
            fv = fecha_venc.strftime('#%m/%d/%Y#')

            self.db.execute(
                f"INSERT INTO [CuentasPorPagar] (ProveedorNombre, ProveedorRIF, NumeroDocumento, "
                f"FechaEmision, FechaVencimiento, MontoOriginal, MontoPagado, SaldoPendiente, "
                f"CategoriaGastoID, Estado, Observaciones) "
                f"VALUES ('{proveedor}', '{rif}', '{doc}', {fe}, {fv}, "
                f"{monto}, 0, {monto}, {cat_id}, 'Pendiente', '{obs}')"
            )
            return True, "Cuenta por pagar creada"
        except Exception as e:
            return False, f"Error al crear cuenta: {e}"

    def registrar_pago(self, cuenta_id, monto, forma_pago_id, referencia=''):
        """Registra un pago parcial o total a un proveedor."""
        try:
            cuenta = self.db.query_one(
                f"SELECT * FROM [CuentasPorPagar] WHERE CuentaPagarID={cuenta_id}"
            )
            if not cuenta:
                return False, "Cuenta no encontrada"

            saldo = float(cuenta.get('SaldoPendiente', 0) or 0)
            monto = float(monto)
            if monto > saldo:
                return False, f"El monto ({monto:.2f}) excede el saldo ({saldo:.2f})"

            pagado = float(cuenta.get('MontoPagado', 0) or 0) + monto
            nuevo_saldo = saldo - monto
            estado = 'Pagada' if nuevo_saldo <= 0 else 'Parcial'

            self.db.execute(
                f"UPDATE [CuentasPorPagar] SET MontoPagado={pagado}, "
                f"SaldoPendiente={nuevo_saldo}, Estado='{estado}' "
                f"WHERE CuentaPagarID={cuenta_id}"
            )

            # Registrar egreso en caja si hay caja abierta
            gestor_caja = GestorCajaChica(self.db)
            caja = gestor_caja.obtener_caja_abierta()
            if caja:
                gestor_caja.registrar_movimiento(caja['CajaID'], {
                    'Tipo': 'Egreso',
                    'Categoria': 'Pago a proveedor',
                    'Descripcion': f"Pago CxP #{cuenta_id} - {cuenta.get('ProveedorNombre', '')}",
                    'Monto': monto,
                    'FormaPagoID': forma_pago_id,
                    'Referencia': referencia,
                }, 0)

            return True, f"Pago registrado. Saldo pendiente: {nuevo_saldo:.2f}"
        except Exception as e:
            return False, f"Error al registrar pago: {e}"

    def listar_cuentas(self, estado=None, proveedor=None):
        """Lista cuentas por pagar con filtros."""
        try:
            sql = "SELECT cp.*, cg.Nombre as CategoriaGasto FROM [CuentasPorPagar] cp " \
                  "LEFT JOIN [CategoriaGastos] cg ON cp.CategoriaGastoID = cg.CategoriaID WHERE 1=1"
            if estado:
                estado_safe = str(estado).replace("'", "''")
                sql += f" AND cp.Estado='{estado_safe}'"
            if proveedor:
                prov_safe = str(proveedor).replace("'", "''").replace("%", "").replace("_", "")
                sql += f" AND cp.ProveedorNombre LIKE '%{prov_safe}%'"
            sql += " ORDER BY cp.FechaEmision DESC"
            return self.db.query(sql)
        except:
            return []

    def obtener_resumen(self):
        """Resumen de cuentas por pagar."""
        try:
            cuentas = self.db.query(
                "SELECT * FROM [CuentasPorPagar] WHERE Estado <> 'Pagada'"
            )
            total = sum(float(c.get('SaldoPendiente', 0) or 0) for c in cuentas)
            por_vencer = 0
            vencidas = 0
            hoy = datetime.now()
            for c in cuentas:
                saldo = float(c.get('SaldoPendiente', 0) or 0)
                fv = c.get('FechaVencimiento')
                if fv:
                    try:
                        if isinstance(fv, str):
                            fv = datetime.strptime(fv, '%m/%d/%Y')
                        if fv < hoy:
                            vencidas += saldo
                        else:
                            por_vencer += saldo
                    except:
                        por_vencer += saldo
            return {'total': total, 'por_vencer': por_vencer, 'vencidas': vencidas, 'cantidad': len(cuentas)}
        except:
            return {'total': 0, 'por_vencer': 0, 'vencidas': 0, 'cantidad': 0}


class GestorGastos:
    """Gestión de gastos del laboratorio."""

    def __init__(self, db):
        self.db = db

    def registrar_gasto(self, datos, usuario_id):
        """Registra un gasto. Si hay caja abierta, crea movimiento egreso."""
        try:
            monto = float(datos.get('Monto', 0))
            cat_id = datos.get('CategoriaGastoID', 'Null')
            descripcion = str(datos.get('Descripcion', '')).replace("'", "''")
            forma_pago_id = datos.get('FormaPagoID', 'Null')
            referencia = str(datos.get('Referencia', '')).replace("'", "''")
            beneficiario = str(datos.get('BeneficiarioNombre', '')).replace("'", "''")
            beneficiario_rif = str(datos.get('BeneficiarioRIF', '')).replace("'", "''")

            fecha = datetime.now().strftime('#%m/%d/%Y %H:%M:%S#')

            # Verificar si hay caja abierta
            gestor_caja = GestorCajaChica(self.db)
            caja = gestor_caja.obtener_caja_abierta()
            caja_id = caja['CajaID'] if caja else 'Null'

            self.db.execute(
                f"INSERT INTO [Gastos] (Fecha, CategoriaGastoID, Descripcion, Monto, "
                f"FormaPagoID, Referencia, BeneficiarioNombre, BeneficiarioRIF, "
                f"CajaID, UsuarioID, Anulado) "
                f"VALUES ({fecha}, {cat_id}, '{descripcion}', {monto}, "
                f"{forma_pago_id}, '{referencia}', '{beneficiario}', '{beneficiario_rif}', "
                f"{caja_id}, {usuario_id}, False)"
            )

            # Registrar en caja si está abierta
            if caja:
                cat_nombre = ''
                if cat_id != 'Null':
                    cat = self.db.query_one(
                        f"SELECT Nombre FROM [CategoriaGastos] WHERE CategoriaID={cat_id}"
                    )
                    cat_nombre = cat.get('Nombre', '') if cat else ''

                gestor_caja.registrar_movimiento(caja['CajaID'], {
                    'Tipo': 'Egreso',
                    'Categoria': cat_nombre or 'Gasto',
                    'Descripcion': descripcion,
                    'Monto': monto,
                    'FormaPagoID': forma_pago_id,
                    'Referencia': referencia,
                }, usuario_id)

            return True, "Gasto registrado"
        except Exception as e:
            return False, f"Error al registrar gasto: {e}"

    def anular_gasto(self, gasto_id, motivo):
        """Anula un gasto."""
        try:
            gasto = self.db.query_one(f"SELECT * FROM [Gastos] WHERE GastoID={gasto_id}")
            if not gasto:
                return False, "Gasto no encontrado"
            if gasto.get('Anulado'):
                return False, "El gasto ya está anulado"

            motivo_safe = str(motivo).replace("'", "''")
            self.db.execute(
                f"UPDATE [Gastos] SET Anulado=True, MotivoAnulacion='{motivo_safe}' "
                f"WHERE GastoID={gasto_id}"
            )
            return True, "Gasto anulado"
        except Exception as e:
            return False, f"Error al anular gasto: {e}"

    def _validar_fecha(self, fecha):
        """Valida que una fecha tenga formato correcto MM/DD/YYYY o sea un objeto datetime."""
        if isinstance(fecha, (datetime, date)):
            return fecha.strftime('%m/%d/%Y')
        fecha_str = str(fecha).strip()
        # Solo permitir digitos y separadores de fecha
        import re
        if re.match(r'^\d{1,2}/\d{1,2}/\d{4}$', fecha_str):
            return fecha_str
        return None

    def listar_gastos(self, fecha_desde=None, fecha_hasta=None, categoria_id=None):
        """Lista gastos con filtros."""
        try:
            sql = (
                "SELECT g.*, cg.Nombre as CategoriaGasto, fp.Nombre as FormaPago "
                "FROM ([Gastos] g LEFT JOIN [CategoriaGastos] cg ON g.CategoriaGastoID = cg.CategoriaID) "
                "LEFT JOIN [FormasPago] fp ON g.FormaPagoID = fp.FormaPagoID "
                "WHERE g.Anulado=False"
            )
            if fecha_desde:
                fd = self._validar_fecha(fecha_desde)
                if fd:
                    sql += f" AND g.Fecha >= #{fd}#"
            if fecha_hasta:
                fh = self._validar_fecha(fecha_hasta)
                if fh:
                    sql += f" AND g.Fecha <= #{fh}#"
            if categoria_id:
                sql += f" AND g.CategoriaGastoID={int(categoria_id)}"
            sql += " ORDER BY g.Fecha DESC"
            return self.db.query(sql)
        except:
            return []

    def resumen_gastos_por_categoria(self, fecha_desde=None, fecha_hasta=None):
        """Resumen de gastos agrupados por categoría."""
        try:
            sql = (
                "SELECT cg.Nombre, SUM(g.Monto) as Total, COUNT(*) as Cantidad "
                "FROM [Gastos] g "
                "LEFT JOIN [CategoriaGastos] cg ON g.CategoriaGastoID = cg.CategoriaID "
                "WHERE g.Anulado=False"
            )
            if fecha_desde:
                fd = self._validar_fecha(fecha_desde)
                if fd:
                    sql += f" AND g.Fecha >= #{fd}#"
            if fecha_hasta:
                fh = self._validar_fecha(fecha_hasta)
                if fh:
                    sql += f" AND g.Fecha <= #{fh}#"
            sql += " GROUP BY cg.Nombre ORDER BY SUM(g.Monto) DESC"
            return self.db.query(sql)
        except:
            return []

    def listar_categorias(self):
        """Lista categorías de gastos activas."""
        try:
            return self.db.query("SELECT * FROM [CategoriaGastos] WHERE Activo=True ORDER BY Nombre")
        except:
            return []


class ResumenFinanciero:
    """Dashboard financiero y reportes de resumen."""

    def __init__(self, db):
        self.db = db

    def resumen_diario(self, fecha=None):
        """Resumen financiero del día."""
        if not fecha:
            fecha = datetime.now().strftime('%m/%d/%Y')
        try:
            ingresos = self.db.query(
                f"SELECT SUM(Monto) as Total FROM [MovimientosCaja] "
                f"WHERE Tipo='Ingreso' AND Anulado=False AND Fecha >= #{fecha}#"
            )
            egresos = self.db.query(
                f"SELECT SUM(Monto) as Total FROM [MovimientosCaja] "
                f"WHERE Tipo='Egreso' AND Anulado=False AND Fecha >= #{fecha}#"
            )
            total_ingresos = float((ingresos[0].get('Total') if ingresos else None) or 0)
            total_egresos = float((egresos[0].get('Total') if egresos else None) or 0)

            return {
                'fecha': fecha,
                'ingresos': total_ingresos,
                'egresos': total_egresos,
                'saldo': total_ingresos - total_egresos
            }
        except:
            return {'fecha': fecha, 'ingresos': 0, 'egresos': 0, 'saldo': 0}

    def resumen_mensual(self, anio=None, mes=None):
        """Resumen financiero del mes."""
        if not anio:
            anio = datetime.now().year
        if not mes:
            mes = datetime.now().month
        fecha_inicio = f"{mes:02d}/01/{anio}"
        if mes == 12:
            fecha_fin = f"01/01/{anio + 1}"
        else:
            fecha_fin = f"{mes + 1:02d}/01/{anio}"

        try:
            ingresos = self.db.query(
                f"SELECT SUM(Monto) as Total FROM [MovimientosCaja] "
                f"WHERE Tipo='Ingreso' AND Anulado=False "
                f"AND Fecha >= #{fecha_inicio}# AND Fecha < #{fecha_fin}#"
            )
            egresos = self.db.query(
                f"SELECT SUM(Monto) as Total FROM [MovimientosCaja] "
                f"WHERE Tipo='Egreso' AND Anulado=False "
                f"AND Fecha >= #{fecha_inicio}# AND Fecha < #{fecha_fin}#"
            )
            total_ingresos = float((ingresos[0].get('Total') if ingresos else None) or 0)
            total_egresos = float((egresos[0].get('Total') if egresos else None) or 0)

            return {
                'anio': anio, 'mes': mes,
                'ingresos': total_ingresos,
                'egresos': total_egresos,
                'saldo': total_ingresos - total_egresos
            }
        except:
            return {'anio': anio, 'mes': mes, 'ingresos': 0, 'egresos': 0, 'saldo': 0}

    def resumen_periodo(self, fecha_desde, fecha_hasta):
        """Resumen financiero de un período arbitrario."""
        try:
            ingresos = self.db.query(
                f"SELECT SUM(Monto) as Total FROM [MovimientosCaja] "
                f"WHERE Tipo='Ingreso' AND Anulado=False "
                f"AND Fecha >= #{fecha_desde}# AND Fecha <= #{fecha_hasta}#"
            )
            egresos = self.db.query(
                f"SELECT SUM(Monto) as Total FROM [MovimientosCaja] "
                f"WHERE Tipo='Egreso' AND Anulado=False "
                f"AND Fecha >= #{fecha_desde}# AND Fecha <= #{fecha_hasta}#"
            )
            total_ingresos = float((ingresos[0].get('Total') if ingresos else None) or 0)
            total_egresos = float((egresos[0].get('Total') if egresos else None) or 0)

            return {
                'desde': fecha_desde, 'hasta': fecha_hasta,
                'ingresos': total_ingresos,
                'egresos': total_egresos,
                'saldo': total_ingresos - total_egresos
            }
        except:
            return {
                'desde': fecha_desde, 'hasta': fecha_hasta,
                'ingresos': 0, 'egresos': 0, 'saldo': 0
            }

    def estado_cartera(self):
        """Estado de cartera (cuentas por cobrar y pagar)."""
        cxc = GestorCuentasPorCobrar(self.db)
        cxp = GestorCuentasPorPagar(self.db)
        return {
            'cuentas_cobrar': cxc.obtener_resumen_cartera(),
            'cuentas_pagar': cxp.obtener_resumen()
        }

    def indicadores_clave(self):
        """Indicadores clave del negocio."""
        try:
            resumen_dia = self.resumen_diario()
            resumen_mes = self.resumen_mensual()
            cartera = self.estado_cartera()

            # Caja actual
            gestor_caja = GestorCajaChica(self.db)
            caja = gestor_caja.obtener_caja_abierta()

            return {
                'ingresos_hoy': resumen_dia['ingresos'],
                'egresos_hoy': resumen_dia['egresos'],
                'saldo_hoy': resumen_dia['saldo'],
                'ingresos_mes': resumen_mes['ingresos'],
                'egresos_mes': resumen_mes['egresos'],
                'saldo_mes': resumen_mes['saldo'],
                'cxc_total': cartera['cuentas_cobrar']['total'],
                'cxp_total': cartera['cuentas_pagar']['total'],
                'caja_abierta': caja is not None,
                'caja_estado': caja.get('Estado', 'Sin caja') if caja else 'Sin caja',
            }
        except:
            return {
                'ingresos_hoy': 0, 'egresos_hoy': 0, 'saldo_hoy': 0,
                'ingresos_mes': 0, 'egresos_mes': 0, 'saldo_mes': 0,
                'cxc_total': 0, 'cxp_total': 0,
                'caja_abierta': False, 'caja_estado': 'Sin caja',
            }

    def desglose_ingresos_por_forma_pago(self, fecha_desde=None, fecha_hasta=None):
        """Desglose de ingresos por forma de pago."""
        try:
            sql = (
                "SELECT fp.Nombre, SUM(m.Monto) as Total, COUNT(*) as Cantidad "
                "FROM [MovimientosCaja] m "
                "LEFT JOIN [FormasPago] fp ON m.FormaPagoID = fp.FormaPagoID "
                "WHERE m.Tipo='Ingreso' AND m.Anulado=False"
            )
            if fecha_desde:
                sql += f" AND m.Fecha >= #{fecha_desde}#"
            if fecha_hasta:
                sql += f" AND m.Fecha <= #{fecha_hasta}#"
            sql += " GROUP BY fp.Nombre ORDER BY SUM(m.Monto) DESC"
            return self.db.query(sql)
        except:
            return []

    def listar_formas_pago(self):
        """Lista formas de pago activas."""
        try:
            return self.db.query("SELECT * FROM [FormasPago] WHERE Activo=True ORDER BY Nombre")
        except:
            return []

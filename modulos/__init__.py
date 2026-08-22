# -*- coding: utf-8 -*-
"""
================================================================================
MODULOS ANgesLAB v2.0
================================================================================
Sistema de Gestion de Laboratorio Clinico

Modulos principales (importados con try/except por ANgesLAB.pyw):
- seguridad_db: Hash de contrasenas, validadores
- calculos_automaticos: Formulas clinicas automaticas (incluye aliases de microbiologia)
- config_numeracion / ventana_config_numeracion: Numeracion de documentos
- config_administrativa / ventana_config_administrativa: Configuracion del lab
- gestor_solicitudes: Gestion centralizada de solicitudes
- ventana_administrativa / modulo_administrativo: Modulo contable/financiero
- ventana_configuracion_completa: Ventana unificada de configuracion
- facturacion_fiscal: Facturacion SENIAT Venezuela
- veterinario: Modulo veterinario (Felino/Canino/Bovino)
- historial_clinico: Historial clinico y comparativas
- splash_screen: Pantalla de inicio

Modulos auxiliares:
- utilidades_db: Utilidades de mantenimiento de BD
- envio_resultados: Envio de resultados por email/PDF
- whatsapp_envio: Envio por WhatsApp con el PDF adjuntado automaticamente
- antibioticos_restricciones: Aplicabilidad de antibioticos por edad y gestacion
- impresoras: Asignacion de impresora por rol y envio directo por GDI
- cotizaciones: Cotizaciones/presupuestos y su conversion a solicitud
- portal_resultados: Portal web de consulta con QR
- tasas_cambio: Tasas BCV y conversion multi-moneda
- ia_interpretacion / graficas_historial: Apoyo clinico en el historial

Nota: en la limpieza de 2026-08 se eliminaron cinco modulos que ningun archivo
importaba (reportes_resultados, plantillas_reportes, form_inf_config,
flujo_trabajo y reportes_especificaciones). Siguen disponibles en el historial
de git si alguna vez se quieren reactivar.

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

__version__ = "2.0.0"
__author__ = "ANgesLAB Solutions"

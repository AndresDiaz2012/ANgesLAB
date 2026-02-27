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

Modulos auxiliares (disponibles para uso futuro):
- reportes_resultados: Generacion de reportes por area
- plantillas_reportes: Plantillas de reportes en HTML (incluye R40-R43 Microbiologia)
- form_inf_config: Configuracion de formularios de impresion (incluye Form_Inf_Microbiologia)
- flujo_trabajo: Gestion del flujo de trabajo
- utilidades_db: Utilidades de mantenimiento de BD
- reportes_especificaciones: Reportes segun especificaciones tecnicas
- envio_resultados: Envio de resultados por email/PDF

Copyright 2024-2026 ANgesLAB Solutions
================================================================================
"""

__version__ = "2.0.0"
__author__ = "ANgesLAB Solutions"

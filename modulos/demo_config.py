# -*- coding: utf-8 -*-
"""
ANgesLAB - Configuracion del Modo Demo
=======================================
Modulo de restricciones y configuracion para la version demo comercial.
Este archivo NO modifica ningun archivo de produccion.

Copyright (c) 2024-2026 ANgesLAB Solutions
"""

import json
from datetime import datetime, date, timedelta
from pathlib import Path


# ==============================================================================
# CONSTANTES DE DEMO
# ==============================================================================

DEMO_VERSION = "1.0.0-DEMO"
DEMO_EXPIRY_DAYS = 15
DEMO_MAX_PACIENTES = 5
DEMO_MAX_SOLICITUDES = 10

# Datos de contacto de ventas
DEMO_CONTACTO_TELEFONO = "+574147204006"
DEMO_CONTACTO_EMAIL = "diabel92@hotmail.com"
DEMO_CONTACT_INFO = f"Tel: {DEMO_CONTACTO_TELEFONO} | Email: {DEMO_CONTACTO_EMAIL}"

DEMO_PURCHASE_MSG = (
    "Esta es una VERSION DEMO de ANgesLAB.\n\n"
    "Para adquirir la licencia completa sin restricciones:\n"
    f"  Telefono: {DEMO_CONTACTO_TELEFONO}\n"
    f"  Email:    {DEMO_CONTACTO_EMAIL}\n\n"
    "La version completa incluye:\n"
    "  - Pacientes y solicitudes ilimitadas\n"
    "  - Modulos administrativos y financieros\n"
    "  - Configuracion completa del laboratorio\n"
    "  - Exportacion y respaldo de datos\n"
    "  - Soporte tecnico por 12 meses\n"
    "  - Actualizaciones gratuitas"
)

# Archivo de estado de la demo
DEMO_STATE_FILENAME = "demo_state.json"


# ==============================================================================
# CLASE PRINCIPAL DE CONFIGURACION DEMO
# ==============================================================================

class DemoConfig:
    """
    Singleton que gestiona el estado y restricciones de la version demo.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.base_dir = Path(__file__).parent.parent
        self.state_file = self.base_dir / DEMO_STATE_FILENAME
        self._state = self._load_state()

    def _load_state(self):
        """Carga el estado de la demo desde disco. Si no existe, lo crea."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if 'first_launch' in data:
                    return data
            except Exception:
                pass

        state = {
            'first_launch': date.today().isoformat(),
            'launch_count': 1,
        }
        self._save_state(state)
        return state

    def _save_state(self, state):
        """Escribe el estado en disco."""
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Demo: No se pudo guardar estado: {e}")

    def increment_launch_count(self):
        """Incrementa el contador de arranques y persiste."""
        self._state['launch_count'] = self._state.get('launch_count', 0) + 1
        self._save_state(self._state)

    @property
    def first_launch_date(self):
        try:
            return date.fromisoformat(self._state['first_launch'])
        except Exception:
            return date.today()

    @property
    def days_remaining(self):
        elapsed = (date.today() - self.first_launch_date).days
        remaining = DEMO_EXPIRY_DAYS - elapsed
        return max(0, remaining)

    @property
    def is_expired(self):
        return self.days_remaining <= 0

    @property
    def expiry_date(self):
        return self.first_launch_date + timedelta(days=DEMO_EXPIRY_DAYS)

    def check_patient_limit(self, db):
        """
        Verifica si se puede registrar un nuevo paciente.
        Los pacientes pre-cargados (DEMO%) no cuentan contra el limite.

        Returns:
            (permitido: bool, mensaje: str)
        """
        try:
            total = db.count('Pacientes', "NumeroDocumento NOT LIKE 'DEMO%'")
        except Exception:
            total = db.count('Pacientes')

        if total >= DEMO_MAX_PACIENTES:
            msg = (
                f"Limite de la version demo alcanzado ({DEMO_MAX_PACIENTES} pacientes).\n\n"
                f"Para registrar pacientes ilimitados, adquiera\n"
                f"la licencia completa de ANgesLAB.\n\n"
                f"{DEMO_CONTACT_INFO}"
            )
            return False, msg
        return True, ""

    def check_solicitud_limit(self, db):
        """
        Verifica si se puede crear una nueva solicitud.
        Las solicitudes pre-cargadas (DEMO%) no cuentan contra el limite.

        Returns:
            (permitido: bool, mensaje: str)
        """
        try:
            total = db.count('Solicitudes', "NumeroSolicitud NOT LIKE 'DEMO%'")
        except Exception:
            total = db.count('Solicitudes')

        if total >= DEMO_MAX_SOLICITUDES:
            msg = (
                f"Limite de la version demo alcanzado ({DEMO_MAX_SOLICITUDES} solicitudes).\n\n"
                f"Para crear solicitudes ilimitadas, adquiera\n"
                f"la licencia completa de ANgesLAB.\n\n"
                f"{DEMO_CONTACT_INFO}"
            )
            return False, msg
        return True, ""

    def get_banner_text(self):
        """Texto para la banda de demo en la UI."""
        if self.is_expired:
            return (
                f"  DEMO EXPIRADA - Contacte {DEMO_CONTACTO_EMAIL} "
                f"o llame al {DEMO_CONTACTO_TELEFONO} para adquirir la version completa"
            )
        return (
            f"  VERSION DEMO  |  Vence: {self.expiry_date.strftime('%d/%m/%Y')}  "
            f"({self.days_remaining} dias restantes)  |  {DEMO_CONTACT_INFO}"
        )

    def get_watermark_text(self):
        return "DEMO"


# Instancia global de acceso rapido
demo_config = DemoConfig()

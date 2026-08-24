"""
ContaEC - Esquemas de Sub-Cuentas
Cuentas creadas por un usuario (owner) para sus empleados con acceso
limitado a módulos específicos de la aplicación.
"""
from uuid import UUID
from datetime import datetime

import json
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

# Módulos disponibles para asignar a una sub-cuenta
AVAILABLE_MODULES = [
    {"key": "dashboard", "label": "Panel principal"},
    {"key": "facturacion", "label": "Facturación y comprobantes"},
    {"key": "clientes", "label": "Clientes"},
    {"key": "proveedores", "label": "Proveedores"},
    {"key": "inventario", "label": "Inventario y almacenes"},
    {"key": "compras", "label": "Compras y cuentas por pagar"},
    {"key": "contabilidad", "label": "Contabilidad"},
    {"key": "presupuestos", "label": "Presupuestos"},
    {"key": "proyectos", "label": "Proyectos"},
    {"key": "crm", "label": "CRM"},
    {"key": "rh", "label": "Recursos Humanos"},
    {"key": "integraciones", "label": "Integraciones y ecommerce"},
    {"key": "pos", "label": "Punto de venta (POS)"},
    {"key": "bi", "label": "Business Intelligence"},
    {"key": "ml_ai", "label": "ML / IA"},
    {"key": "sri", "label": "Catálogos SRI"},
    {"key": "configuracion", "label": "Configuración"},
]


class SubAccountCreate(BaseModel):
    """Esquema para crear una sub-cuenta"""
    email: EmailStr = Field(..., description="Correo electrónico de la sub-cuenta")
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nombre completo del empleado",
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Contraseña temporal (se enviará por correo)",
    )
    allowed_modules: list[str] = Field(
        default_factory=list,
        description="Módulos permitidos (vacío = acceso total)",
    )


class SubAccountUpdate(BaseModel):
    """Esquema para actualizar una sub-cuenta"""
    full_name: str | None = Field(None, min_length=2, max_length=255)
    allowed_modules: list[str] | None = Field(None, description="Módulos permitidos")
    is_active: bool | None = Field(None, description="Activar/desactivar la cuenta")
    password: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Nueva contraseña temporal (opcional)",
    )


class SubAccountResponse(BaseModel):
    """Esquema de respuesta para una sub-cuenta"""
    id: UUID = Field(..., description="ID de la sub-cuenta")
    email: str = Field(..., description="Correo electrónico")
    full_name: str = Field(..., description="Nombre completo")
    is_active: bool = Field(..., description="Cuenta activa")
    parent_user_id: UUID = Field(..., description="ID del usuario que la creó")
    allowed_modules: list[str] = Field(
        default_factory=list,
        description="Módulos permitidos",
    )
    must_change_password: bool = Field(..., description="Debe cambiar contraseña")
    created_at: datetime = Field(..., description="Fecha de creación")
    email_warning: str | None = Field(
        None,
        description="Advertencia sobre el envío de correo (ej: SMTP no configurado)",
    )

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @model_validator(mode='before')
    @classmethod
    def parse_allowed_modules(cls, data):
        """Convierte allowed_modules de JSON string a list si es necesario.
        
        La BD almacena allowed_modules como JSON string (ej: '["facturacion","clientes"]'),
        pero el esquema Pydantic espera list[str]. Tambien maneja None -> [].
        """
        def _parse(val):
            if val is None:
                return []
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    return parsed if isinstance(parsed, list) else []
                except (json.JSONDecodeError, TypeError):
                    return []
            return []

        if hasattr(data, 'allowed_modules'):
            data.allowed_modules = _parse(data.allowed_modules)
        elif isinstance(data, dict):
            data['allowed_modules'] = _parse(data.get('allowed_modules'))
        return data

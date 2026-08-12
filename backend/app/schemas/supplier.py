"""
ContaEC - Esquemas Pydantic de Proveedor
Schemas para creación, actualización y respuesta de proveedores
con tipos de identificación según catálogos del SRI (Tabla 7)
"""
from uuid import UUID
import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class SupplierCreate(BaseModel):
    """Esquema para crear un nuevo proveedor"""
    company_id: str = Field(
        ...,
        description="ID de la empresa a la que pertenece el proveedor",
    )
    tipo_identificacion: str = Field(
        ...,
        max_length=2,
        description="Tipo de identificación SRI: 04=RUC, 05=Cédula, 06=Pasaporte, 08=Exterior",
        examples=["04"],
    )
    identificacion: str = Field(
        ...,
        max_length=20,
        description="Número de identificación (RUC, cédula, pasaporte, etc.)",
        examples=["1791234567001"],
    )
    razon_social: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Razón social o nombre completo del proveedor",
        examples=["DISTRIBUIDORA ABC S.A."],
    )
    nombre_comercial: str | None = Field(
        None,
        max_length=255,
        description="Nombre comercial del proveedor",
    )
    direccion: str | None = Field(
        None,
        max_length=500,
        description="Dirección del proveedor",
    )
    email: EmailStr | None = Field(
        None,
        max_length=255,
        description="Correo electrónico del proveedor",
    )
    telefono: str | None = Field(
        None,
        max_length=20,
        description="Número de teléfono del proveedor",
    )
    contacto_nombre: str | None = Field(
        None,
        max_length=200,
        description="Nombre del contacto principal",
    )
    contacto_telefono: str | None = Field(
        None,
        max_length=20,
        description="Teléfono del contacto principal",
    )
    forma_pago_habitual: str = Field(
        default="01",
        max_length=2,
        description="Código de forma de pago habitual según Tabla 23 del SRI",
    )
    plazo_credito_dias: int = Field(
        default=0,
        ge=0,
        description="Plazo de crédito habitual en días (0 = contado)",
    )
    retencion_iva_codigo: str | None = Field(
        None,
        max_length=2,
        description="Código de retención de IVA habitual según Tabla 19 del SRI",
    )
    retencion_iva_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de retención de IVA habitual",
    )
    retencion_renta_codigo: str | None = Field(
        None,
        max_length=3,
        description="Código de retención de Renta habitual según Tabla 20 del SRI",
    )
    retencion_renta_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de retención de Renta habitual",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales sobre el proveedor",
    )

    @field_validator("tipo_identificacion")
    @classmethod
    def validate_tipo_identificacion(cls, v: str) -> str:
        """Valida que el tipo de identificación sea válido según Tabla 7 del SRI"""
        validos = {"04", "05", "06", "08"}
        if v not in validos:
            raise ValueError(
                f"Tipo de identificación inválido: {v}. "
                f"Válidos: 04 (RUC), 05 (Cédula), 06 (Pasaporte), 08 (Exterior)"
            )
        return v

    @field_validator("identificacion")
    @classmethod
    def validate_identificacion(cls, v: str) -> str:
        """Validación básica del número de identificación"""
        v = v.strip()
        if not v:
            raise ValueError("La identificación no puede estar vacía")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validación básica del formato de correo electrónico"""
        if v is not None and v.strip():
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v.strip()):
                raise ValueError("Formato de correo electrónico inválido")
            return v.strip()
        return v


class SupplierUpdate(BaseModel):
    """Esquema para actualizar un proveedor"""
    tipo_identificacion: str | None = Field(
        None,
        max_length=2,
        description="Tipo de identificación SRI",
    )
    identificacion: str | None = Field(
        None,
        max_length=20,
        description="Número de identificación",
    )
    razon_social: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Razón social o nombre completo",
    )
    nombre_comercial: str | None = Field(
        None,
        max_length=255,
        description="Nombre comercial",
    )
    direccion: str | None = Field(
        None,
        max_length=500,
        description="Dirección",
    )
    email: EmailStr | None = Field(
        None,
        max_length=255,
        description="Correo electrónico",
    )
    telefono: str | None = Field(
        None,
        max_length=20,
        description="Número de teléfono",
    )
    contacto_nombre: str | None = Field(
        None,
        max_length=200,
        description="Nombre del contacto principal",
    )
    contacto_telefono: str | None = Field(
        None,
        max_length=20,
        description="Teléfono del contacto principal",
    )
    forma_pago_habitual: str | None = Field(
        None,
        max_length=2,
        description="Código de forma de pago habitual",
    )
    plazo_credito_dias: int | None = Field(
        None,
        ge=0,
        description="Plazo de crédito en días",
    )
    retencion_iva_codigo: str | None = Field(
        None,
        max_length=2,
        description="Código de retención de IVA",
    )
    retencion_iva_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de retención de IVA",
    )
    retencion_renta_codigo: str | None = Field(
        None,
        max_length=3,
        description="Código de retención de Renta",
    )
    retencion_renta_porcentaje: Decimal | None = Field(
        None,
        ge=0,
        description="Porcentaje de retención de Renta",
    )
    observaciones: str | None = Field(
        None,
        description="Observaciones adicionales",
    )
    is_active: bool | None = Field(
        None,
        description="Indica si el proveedor está activo",
    )

    @field_validator("tipo_identificacion")
    @classmethod
    def validate_tipo_identificacion(cls, v: str | None) -> str | None:
        """Valida que el tipo de identificación sea válido"""
        if v is not None and v not in {"04", "05", "06", "08"}:
            raise ValueError(
                f"Tipo de identificación inválido: {v}. "
                f"Válidos: 04, 05, 06, 08"
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validación básica del formato de correo electrónico"""
        if v is not None and v.strip():
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v.strip()):
                raise ValueError("Formato de correo electrónico inválido")
            return v.strip()
        return v


class SupplierResponse(BaseModel):
    """Esquema de respuesta para un proveedor"""
    id: UUID = Field(..., description="ID único del proveedor")
    company_id: UUID = Field(..., description="ID de la empresa")
    tipo_identificacion: str = Field(..., description="Tipo de identificación SRI")
    identificacion: str = Field(..., description="Número de identificación")
    razon_social: str = Field(..., description="Razón social o nombre completo")
    nombre_comercial: str | None = Field(None, description="Nombre comercial")
    direccion: str | None = Field(None, description="Dirección")
    email: EmailStr | None = Field(None, description="Correo electrónico")
    telefono: str | None = Field(None, description="Número de teléfono")
    contacto_nombre: str | None = Field(None, description="Nombre del contacto")
    contacto_telefono: str | None = Field(None, description="Teléfono del contacto")
    forma_pago_habitual: str = Field(..., description="Forma de pago habitual")
    plazo_credito_dias: int = Field(..., description="Plazo de crédito en días")
    retencion_iva_codigo: str | None = Field(None, description="Código retención IVA")
    retencion_iva_porcentaje: Decimal | None = Field(None, description="% retención IVA")
    retencion_renta_codigo: str | None = Field(None, description="Código retención Renta")
    retencion_renta_porcentaje: Decimal | None = Field(None, description="% retención Renta")
    observaciones: str | None = Field(None, description="Observaciones")
    is_active: bool = Field(..., description="Indica si está activo")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

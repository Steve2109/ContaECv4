"""
ContaEC - Esquemas Pydantic de Plantilla de Correo Electrónico
Schemas para creación, actualización, respuesta y envío de plantillas
"""
from uuid import UUID
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EmailTemplateCreate(BaseModel):
    """Esquema para crear una nueva plantilla de correo"""
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre descriptivo de la plantilla",
        examples=["Factura Estándar"],
    )
    tipo: str = Field(
        ...,
        max_length=50,
        description="Tipo de plantilla: factura, nota_credito, nota_debito, proforma, general",
        examples=["factura"],
    )
    asunto: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Asunto del correo (soporta variables {{variable}})",
        examples=["Factura Electrónica #{{secuencial}} - {{empresa_razon_social}}"],
    )
    cuerpo_html: str = Field(
        ...,
        min_length=1,
        description="Cuerpo del correo en HTML (soporta variables {{variable}})",
    )
    cuerpo_texto: str | None = Field(
        None,
        description="Cuerpo del correo en texto plano (opcional)",
    )
    is_default: bool = Field(
        default=False,
        description="Indica si es la plantilla por defecto para su tipo",
    )

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str) -> str:
        """Valida que el tipo de plantilla sea válido"""
        validos = {"factura", "nota_credito", "nota_debito", "proforma", "general"}
        if v not in validos:
            raise ValueError(
                f"Tipo de plantilla inválido: {v}. "
                f"Válidos: factura, nota_credito, nota_debito, proforma, general"
            )
        return v


class EmailTemplateUpdate(BaseModel):
    """Esquema para actualizar una plantilla de correo"""
    nombre: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nombre descriptivo de la plantilla",
    )
    tipo: str | None = Field(
        None,
        max_length=50,
        description="Tipo de plantilla",
    )
    asunto: str | None = Field(
        None,
        min_length=1,
        max_length=500,
        description="Asunto del correo",
    )
    cuerpo_html: str | None = Field(
        None,
        min_length=1,
        description="Cuerpo del correo en HTML",
    )
    cuerpo_texto: str | None = Field(
        None,
        description="Cuerpo del correo en texto plano",
    )
    is_default: bool | None = Field(
        None,
        description="Indica si es la plantilla por defecto",
    )
    is_active: bool | None = Field(
        None,
        description="Indica si la plantilla está activa",
    )

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v: str | None) -> str | None:
        """Valida que el tipo de plantilla sea válido"""
        if v is not None and v not in {"factura", "nota_credito", "nota_debito", "proforma", "general"}:
            raise ValueError(
                f"Tipo de plantilla inválido: {v}. "
                f"Válidos: factura, nota_credito, nota_debito, proforma, general"
            )
        return v


class EmailTemplateResponse(BaseModel):
    """Esquema de respuesta para una plantilla de correo"""
    id: UUID = Field(..., description="ID único de la plantilla")
    user_id: UUID = Field(..., description="ID del usuario propietario")
    nombre: str = Field(..., description="Nombre de la plantilla")
    tipo: str = Field(..., description="Tipo de plantilla")
    asunto: str = Field(..., description="Asunto del correo")
    cuerpo_html: str = Field(..., description="Cuerpo HTML del correo")
    cuerpo_texto: str | None = Field(None, description="Cuerpo texto plano")
    is_default: bool = Field(..., description="Es plantilla por defecto")
    is_active: bool = Field(..., description="Está activa")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class EmailTemplatePreviewRequest(BaseModel):
    """Esquema para previsualizar una plantilla con datos de ejemplo"""
    sample_data: dict[str, str] = Field(
        default_factory=dict,
        description="Datos de ejemplo para reemplazar variables {{variable}}",
        examples=[{"empresa_razon_social": "Mi Empresa S.A.", "secuencial": "000000001"}],
    )


class EmailTemplateCustomPreviewRequest(BaseModel):
    """Esquema para previsualizar HTML/asunto sin necesidad de guardar la plantilla"""
    cuerpo_html: str = Field(
        ...,
        min_length=1,
        description="Cuerpo HTML a previsualizar",
    )
    asunto: str = Field(
        ...,
        min_length=1,
        description="Asunto a previsualizar",
    )
    sample_data: dict[str, str] = Field(
        default_factory=dict,
        description="Datos de ejemplo para reemplazar variables {{variable}}",
    )


class EmailSendRequest(BaseModel):
    """Esquema para enviar un correo usando una plantilla"""
    comprobante_id: str = Field(
        ...,
        description="ID del comprobante electrónico a enviar",
    )
    template_id: str = Field(
        ...,
        description="ID de la plantilla a utilizar",
    )
    to_email: str | None = Field(
        None,
        max_length=255,
        description="Correo destino (si no se especifica, usa el del cliente del comprobante)",
    )

"""
ContaEC - Esquemas Pydantic de Perfil SMTP
Schemas para creación, actualización, respuesta y prueba de perfiles SMTP
"""
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ==========================================
# Enums validados
# ==========================================

VALID_PROVIDER_TYPES = {"GMAIL", "ZOHO", "OFFICE365", "OUTLOOK", "YAHOO", "CUSTOM"}
VALID_PROTOCOLS = {"SMTP", "SMTP_SSL", "STARTTLS"}


# ==========================================
# Create Schema
# ==========================================

class SMTPProfileCreate(BaseModel):
    """Esquema para crear un nuevo perfil SMTP"""
    nombre: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Nombre descriptivo del perfil (ej: Gmail Personal, Zoho Empresa)",
        examples=["Gmail Personal"],
    )
    provider_type: str = Field(
        default="CUSTOM",
        max_length=20,
        description="Tipo de proveedor: GMAIL, ZOHO, OFFICE365, OUTLOOK, YAHOO, CUSTOM",
        examples=["GMAIL"],
    )
    host: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Servidor SMTP (ej: smtp.gmail.com)",
        examples=["smtp.gmail.com"],
    )
    port: int = Field(
        default=587,
        ge=1,
        le=65535,
        description="Puerto del servidor SMTP",
        examples=[587],
    )
    username: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Usuario del servidor SMTP (generalmente el correo electrónico)",
        examples=["miempresa@gmail.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Contraseña del servidor SMTP (se cifrará automáticamente)",
    )
    use_ssl: bool = Field(
        default=True,
        description="Usar SSL para la conexión SMTP",
    )
    use_tls: bool = Field(
        default=True,
        description="Usar TLS para la conexión SMTP",
    )
    protocol: str = Field(
        default="STARTTLS",
        max_length=20,
        description="Protocolo de conexión: SMTP, SMTP_SSL, STARTTLS",
        examples=["STARTTLS"],
    )
    imap_host: str | None = Field(
        None,
        max_length=255,
        description="Servidor IMAP (opcional)",
        examples=["imap.gmail.com"],
    )
    imap_port: int | None = Field(
        None,
        ge=1,
        le=65535,
        description="Puerto del servidor IMAP",
        examples=[993],
    )
    pop3_host: str | None = Field(
        None,
        max_length=255,
        description="Servidor POP3 (opcional)",
        examples=["pop.gmail.com"],
    )
    pop3_port: int | None = Field(
        None,
        ge=1,
        le=65535,
        description="Puerto del servidor POP3",
        examples=[995],
    )
    is_default: bool = Field(
        default=False,
        description="Establecer como perfil por defecto",
    )
    daily_limit: int = Field(
        default=500,
        ge=1,
        le=10000,
        description="Límite diario de envíos",
    )

    @field_validator("provider_type")
    @classmethod
    def validate_provider_type(cls, v: str) -> str:
        """Valida que el tipo de proveedor sea válido"""
        v_upper = v.upper()
        if v_upper not in VALID_PROVIDER_TYPES:
            raise ValueError(
                f"Tipo de proveedor inválido: {v}. "
                f"Válidos: {', '.join(sorted(VALID_PROVIDER_TYPES))}"
            )
        return v_upper

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str) -> str:
        """Valida que el protocolo sea válido"""
        v_upper = v.upper()
        if v_upper not in VALID_PROTOCOLS:
            raise ValueError(
                f"Protocolo inválido: {v}. "
                f"Válidos: {', '.join(sorted(VALID_PROTOCOLS))}"
            )
        return v_upper


# ==========================================
# Update Schema
# ==========================================

class SMTPProfileUpdate(BaseModel):
    """Esquema para actualizar un perfil SMTP"""
    nombre: str | None = Field(
        None,
        min_length=1,
        max_length=200,
        description="Nombre descriptivo del perfil",
    )
    provider_type: str | None = Field(
        None,
        max_length=20,
        description="Tipo de proveedor",
    )
    host: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Servidor SMTP",
    )
    port: int | None = Field(
        None,
        ge=1,
        le=65535,
        description="Puerto del servidor SMTP",
    )
    username: str | None = Field(
        None,
        min_length=1,
        max_length=255,
        description="Usuario SMTP",
    )
    password: str | None = Field(
        None,
        min_length=1,
        description="Contraseña SMTP (se cifrará automáticamente)",
    )
    use_ssl: bool | None = Field(
        None,
        description="Usar SSL",
    )
    use_tls: bool | None = Field(
        None,
        description="Usar TLS",
    )
    protocol: str | None = Field(
        None,
        max_length=20,
        description="Protocolo de conexión",
    )
    imap_host: str | None = Field(
        None,
        max_length=255,
        description="Servidor IMAP",
    )
    imap_port: int | None = Field(
        None,
        ge=1,
        le=65535,
        description="Puerto IMAP",
    )
    pop3_host: str | None = Field(
        None,
        max_length=255,
        description="Servidor POP3",
    )
    pop3_port: int | None = Field(
        None,
        ge=1,
        le=65535,
        description="Puerto POP3",
    )
    is_default: bool | None = Field(
        None,
        description="Establecer como perfil por defecto",
    )
    is_active: bool | None = Field(
        None,
        description="Activar/desactivar perfil",
    )
    daily_limit: int | None = Field(
        None,
        ge=1,
        le=10000,
        description="Límite diario de envíos",
    )

    @field_validator("provider_type")
    @classmethod
    def validate_provider_type(cls, v: str | None) -> str | None:
        """Valida que el tipo de proveedor sea válido"""
        if v is not None:
            v_upper = v.upper()
            if v_upper not in VALID_PROVIDER_TYPES:
                raise ValueError(
                    f"Tipo de proveedor inválido: {v}. "
                    f"Válidos: {', '.join(sorted(VALID_PROVIDER_TYPES))}"
                )
            return v_upper
        return v

    @field_validator("protocol")
    @classmethod
    def validate_protocol(cls, v: str | None) -> str | None:
        """Valida que el protocolo sea válido"""
        if v is not None:
            v_upper = v.upper()
            if v_upper not in VALID_PROTOCOLS:
                raise ValueError(
                    f"Protocolo inválido: {v}. "
                    f"Válidos: {', '.join(sorted(VALID_PROTOCOLS))}"
                )
            return v_upper
        return v


# ==========================================
# Response Schema
# ==========================================

class SMTPProfileResponse(BaseModel):
    """Esquema de respuesta para un perfil SMTP"""
    id: UUID = Field(..., description="ID único del perfil")
    user_id: UUID = Field(..., description="ID del usuario propietario")
    nombre: str = Field(..., description="Nombre descriptivo del perfil")
    provider_type: str = Field(..., description="Tipo de proveedor SMTP")
    host: str = Field(..., description="Servidor SMTP")
    port: int = Field(..., description="Puerto SMTP")
    username: str = Field(..., description="Usuario SMTP")
    use_ssl: bool = Field(..., description="Usa SSL")
    use_tls: bool = Field(..., description="Usa TLS")
    protocol: str = Field(..., description="Protocolo de conexión")
    imap_host: str | None = Field(None, description="Servidor IMAP")
    imap_port: int | None = Field(None, description="Puerto IMAP")
    pop3_host: str | None = Field(None, description="Servidor POP3")
    pop3_port: int | None = Field(None, description="Puerto POP3")
    is_default: bool = Field(..., description="Es perfil por defecto")
    is_active: bool = Field(..., description="Está activo")
    daily_limit: int = Field(..., description="Límite diario de envíos")
    sent_today: int = Field(..., description="Correos enviados hoy")
    last_sent_at: datetime | None = Field(None, description="Último envío")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


# ==========================================
# Test Connection Schemas
# ==========================================

class SMTPTestRequest(BaseModel):
    """Esquema para probar la conexión SMTP de un perfil"""
    to_email: str | None = Field(
        None,
        max_length=255,
        description="Correo destino para la prueba (si no se especifica, usa el username del perfil)",
    )


class SMTPTestResponse(BaseModel):
    """Esquema de respuesta para la prueba de conexión SMTP"""
    success: bool = Field(..., description="Indica si la conexión fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo del resultado")

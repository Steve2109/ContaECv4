"""
ContaEC - Esquemas de autenticación
Pydantic schemas para login, registro, tokens y actualización de usuario
"""
import json
from uuid import UUID
import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# ==========================================
# Validación de contraseña segura
# ==========================================

def validate_strong_password(value: str) -> str:
    """
    Valida que la contraseña cumpla con la normativa de seguridad.

    Requisitos:
    - Mínimo 8 caracteres
    - Al menos una letra mayúscula
    - Al menos una letra minúscula
    - Al menos un número
    - Al menos un símbolo especial
    """
    if len(value) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    if not re.search(r"[A-Z]", value):
        raise ValueError("La contraseña debe contener al menos una letra mayúscula")
    if not re.search(r"[a-z]", value):
        raise ValueError("La contraseña debe contener al menos una letra minúscula")
    if not re.search(r"\d", value):
        raise ValueError("La contraseña debe contener al menos un número")
    if not re.search(r"[^A-Za-z0-9\s]", value):
        raise ValueError("La contraseña debe contener al menos un símbolo especial (ej: @, #, $, %)")
    return value


# ==========================================
# Autenticación
# ==========================================

class UserLogin(BaseModel):
    """Esquema para inicio de sesión"""
    email: EmailStr = Field(
        ...,
        description="Correo electrónico del usuario",
        examples=["usuario@contaec.com"],
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Contraseña del usuario",
    )


class UserRegister(BaseModel):
    """Esquema para registro de nuevo usuario"""
    email: EmailStr = Field(
        ...,
        description="Correo electrónico del usuario",
        examples=["usuario@contaec.com"],
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Nombre completo del usuario",
        examples=["Juan Pérez"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Contraseña del usuario (mínimo 8 caracteres)",
    )
    confirm_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Confirmación de la contraseña",
    )
    phone: str | None = Field(
        None,
        max_length=20,
        description="Número de teléfono",
        examples=["+593 99 123 4567"],
    )
    license_type: str = Field(
        default="monthly",
        description="Tipo de licencia: monthly, quarterly, semiannual, annual",
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Valida que la contraseña cumpla con los requisitos de seguridad"""
        return validate_strong_password(v)

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Valida que las contraseñas coincidan"""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v

    @field_validator("license_type")
    @classmethod
    def validate_license_type(cls, v: str) -> str:
        """Valida que el tipo de licencia sea válido"""
        valid_types = {"monthly", "quarterly", "semiannual", "annual"}
        if v not in valid_types:
            raise ValueError(f"Tipo de licencia inválido. Opciones válidas: {valid_types}")
        return v


# ==========================================
# Tokens
# ==========================================

class Token(BaseModel):
    """Esquema de respuesta con tokens JWT"""
    access_token: str = Field(
        ...,
        description="Token de acceso JWT",
    )
    refresh_token: str = Field(
        ...,
        description="Token de refresco JWT",
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo de token",
    )
    expires_in: int = Field(
        default=3600,
        description="Tiempo de expiración del token en segundos",
    )


class TokenData(BaseModel):
    """Esquema de datos del payload del token JWT"""
    sub: str | None = Field(
        None,
        description="ID del usuario (subject del token)",
    )
    type: str | None = Field(
        None,
        description="Tipo de token (access/refresh)",
    )
    exp: datetime | None = Field(
        None,
        description="Fecha de expiración del token",
    )


class RefreshTokenRequest(BaseModel):
    """Esquema para solicitud de refresco de token"""
    refresh_token: str = Field(
        ...,
        description="Token de refresco JWT",
    )


# ==========================================
# Respuestas de Usuario
# ==========================================

class UserResponse(BaseModel):
    """Esquema de respuesta con datos del usuario (sin datos sensibles)"""
    id: UUID = Field(..., description="ID único del usuario")
    email: str = Field(..., description="Correo electrónico")
    full_name: str = Field(..., description="Nombre completo")
    is_active: bool = Field(..., description="Indica si el usuario está activo")
    is_admin: bool = Field(..., description="Indica si el usuario es administrador")
    must_change_password: bool = Field(
        False,
        description="Indica si el usuario debe cambiar su contraseña en el próximo inicio de sesión",
    )
    is_subaccount: bool = Field(
        False,
        description="Indica si la cuenta es una sub-cuenta con acceso limitado",
    )
    parent_user_id: UUID | None = Field(
        None,
        description="ID del usuario que creó la sub-cuenta",
    )
    allowed_modules: list[str] = Field(
        default_factory=list,
        description="Módulos permitidos de la sub-cuenta (vacío = todos)",
    )
    phone: str | None = Field(None, description="Número de teléfono")

    @field_validator("allowed_modules", mode="before")
    @classmethod
    def parse_allowed_modules(cls, v):
        """Convierte el JSON string almacenado en BD a lista"""
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, TypeError):
                # Fallback: lista separada por comas
                return [m.strip() for m in v.split(",") if m.strip()]
        return []
    language: str = Field("es_EC", description="Idioma preferido")
    theme: str = Field("light", description="Tema de la interfaz")
    license_type: str = Field("monthly", description="Tipo de licencia")
    license_start_date: datetime | None = Field(None, description="Inicio de licencia")
    license_end_date: datetime | None = Field(None, description="Fin de licencia")
    is_trial: bool = Field(False, description="Indica si está en período de prueba")
    trial_start_date: datetime | None = Field(None, description="Inicio del período de prueba")
    trial_end_date: datetime | None = Field(None, description="Fin del período de prueba")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)


class UserUpdate(BaseModel):
    """Esquema para actualización de datos del usuario"""
    full_name: str | None = Field(
        None,
        min_length=2,
        max_length=255,
        description="Nombre completo del usuario",
    )
    phone: str | None = Field(
        None,
        max_length=20,
        description="Número de teléfono",
    )
    language: str | None = Field(
        None,
        description="Idioma preferido (es_EC, en_US)",
    )
    theme: str | None = Field(
        None,
        description="Tema de la interfaz (light, dark, system)",
    )

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Valida que el idioma sea soportado"""
        if v is not None and v not in ("es_EC", "en_US"):
            raise ValueError("Idioma no soportado. Opciones: es_EC, en_US")
        return v

    @field_validator("theme")
    @classmethod
    def validate_theme(cls, v: str | None) -> str | None:
        """Valida que el tema sea válido"""
        if v is not None and v not in ("light", "dark", "system"):
            raise ValueError("Tema no válido. Opciones: light, dark, system")
        return v


class ForgotPasswordRequest(BaseModel):
    """Solicitud de recuperación de contraseña desde el panel de inicio de sesión.

    Se piden 1-2 datos de validación (nombre completo y/o teléfono) además del
    correo registrado para evitar que terceros soliciten contraseñas ajenas.
    """
    email: EmailStr = Field(..., description="Correo electrónico registrado")
    full_name: str | None = Field(
        None,
        min_length=2,
        max_length=255,
        description="Nombre completo del usuario (dato de validación)",
    )
    phone: str | None = Field(
        None,
        max_length=20,
        description="Teléfono del usuario (dato de validación)",
    )


class ForcePasswordChange(BaseModel):
    """Cambio de contraseña obligatorio tras iniciar sesión con una contraseña temporal."""
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Nueva contraseña (mínimo 8 caracteres)",
    )
    confirm_new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Confirmación de la nueva contraseña",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Valida que la nueva contraseña cumpla con los requisitos de seguridad"""
        return validate_strong_password(v)

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Valida que las contraseñas coincidan"""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v


class AdminResetPassword(BaseModel):
    """Restablecimiento de contraseña por parte del administrador."""
    temporary_password: str | None = Field(
        None,
        min_length=8,
        max_length=128,
        description="Contraseña temporal. Si se omite, el sistema genera una automáticamente.",
    )
    send_email: bool = Field(
        True,
        description="Enviar la contraseña temporal por correo al cliente",
    )


class PasswordChange(BaseModel):
    """Esquema para cambio de contraseña"""
    current_password: str = Field(
        ...,
        min_length=6,
        max_length=128,
        description="Contraseña actual del usuario",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Nueva contraseña (mínimo 8 caracteres)",
    )
    confirm_new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Confirmación de la nueva contraseña",
    )

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Valida que la nueva contraseña cumpla con los requisitos de seguridad"""
        return validate_strong_password(v)

    @field_validator("confirm_new_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        """Valida que las nuevas contraseñas coincidan"""
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v

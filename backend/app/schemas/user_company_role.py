"""
ContaEC - Esquemas de Roles de Usuario por Empresa
Pydantic schemas para asignación, actualización y consulta de roles
"""
from uuid import UUID
import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.user_company_role import CompanyRole


# ==========================================
# Creación de Rol
# ==========================================

class UserRoleCreate(BaseModel):
    """Esquema para asignar un rol a un usuario en una empresa"""
    user_id: str = Field(
        ...,
        description="ID del usuario al que se asigna el rol",
    )
    company_id: str = Field(
        ...,
        description="ID de la empresa en la que se asigna el rol",
    )
    role: str = Field(
        ...,
        description="Rol a asignar (owner, admin, accountant, viewer, sales, hr_manager)",
        examples=["accountant"],
    )
    permissions: dict[str, bool] | None = Field(
        None,
        description=(
            "Permisos granulares para el rol. "
            "Si no se especifica, se usan los permisos por defecto del rol. "
            "Ejemplo: {\"can_create_invoices\": true, \"can_approve\": false}"
        ),
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Valida que el rol sea uno de los valores permitidos"""
        valid_roles = [r.value for r in CompanyRole]
        if v not in valid_roles:
            raise ValueError(
                f"Rol inválido. Valores permitidos: {', '.join(valid_roles)}"
            )
        return v


# ==========================================
# Actualización de Rol
# ==========================================

class UserRoleUpdate(BaseModel):
    """Esquema para actualizar un rol o permisos de un usuario en una empresa"""
    role: str | None = Field(
        None,
        description="Nuevo rol a asignar",
        examples=["admin"],
    )
    permissions: dict[str, bool] | None = Field(
        None,
        description="Permisos granulares actualizados",
    )
    is_active: bool | None = Field(
        None,
        description="Estado activo de la asignación de rol",
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
        """Valida que el rol sea uno de los valores permitidos"""
        if v is not None:
            valid_roles = [r.value for r in CompanyRole]
            if v not in valid_roles:
                raise ValueError(
                    f"Rol inválido. Valores permitidos: {', '.join(valid_roles)}"
                )
        return v


# ==========================================
# Respuesta de Rol
# ==========================================

class UserRoleResponse(BaseModel):
    """Esquema de respuesta con datos del rol de usuario en una empresa"""
    id: UUID = Field(..., description="ID único de la asignación de rol")
    user_id: UUID = Field(..., description="ID del usuario")
    company_id: UUID = Field(..., description="ID de la empresa")
    role: str = Field(..., description="Rol del usuario en la empresa")
    permissions: dict[str, bool] | None = Field(
        None,
        description="Permisos granulares del rol",
    )
    is_active: bool = Field(..., description="Estado activo de la asignación")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

    @classmethod
    def from_model(cls, obj) -> "UserRoleResponse":
        """
        Crea una instancia de UserRoleResponse desde un modelo UserCompanyRole,
        deserializando el campo permissions de JSON string a dict.
        """
        perms = None
        if obj.permissions:
            try:
                perms = json.loads(obj.permissions)
            except (json.JSONDecodeError, TypeError):
                perms = obj.get_permissions()
        else:
            perms = obj.get_permissions()

        return cls(
            id=str(obj.id),
            user_id=str(obj.user_id),
            company_id=str(obj.company_id),
            role=obj.role,
            permissions=perms,
            is_active=obj.is_active,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


# ==========================================
# Verificación de Permiso
# ==========================================

class PermissionCheck(BaseModel):
    """Esquema para verificar si un usuario tiene un permiso específico"""
    permission_name: str = Field(
        ...,
        description="Nombre del permiso a verificar (ej: can_create_invoices)",
        examples=["can_create_invoices"],
    )
    has_permission: bool = Field(
        ...,
        description="Indica si el usuario tiene el permiso solicitado",
    )


# ==========================================
# Información de Rol con detalles de empresa
# ==========================================

class UserRoleWithCompanyResponse(BaseModel):
    """Esquema de respuesta que incluye información de la empresa junto con el rol"""
    id: UUID = Field(..., description="ID único de la asignación de rol")
    user_id: UUID = Field(..., description="ID del usuario")
    company_id: UUID = Field(..., description="ID de la empresa")
    company_name: str | None = Field(None, description="Razón social de la empresa")
    company_ruc: str | None = Field(None, description="RUC de la empresa")
    role: str = Field(..., description="Rol del usuario en la empresa")
    permissions: dict[str, bool] | None = Field(
        None,
        description="Permisos granulares del rol",
    )
    is_active: bool = Field(..., description="Estado activo de la asignación")
    created_at: datetime = Field(..., description="Fecha de creación")
    updated_at: datetime = Field(..., description="Fecha de actualización")

    model_config = ConfigDict(from_attributes=True, str_strip_whitespace=True)

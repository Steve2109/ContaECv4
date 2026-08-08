"""
ContaEC - Endpoints de Roles de Usuario por Empresa
Asignación de roles, verificación de permisos y gestión de accesos por empresa
"""
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.security import get_current_user
from app.models.user import User
from app.models.company import Company
from app.models.user_company_role import (
    CompanyRole,
    DEFAULT_PERMISSIONS,
    UserCompanyRole,
)
from app.schemas.user_company_role import (
    PermissionCheck,
    UserRoleCreate,
    UserRoleResponse,
    UserRoleUpdate,
    UserRoleWithCompanyResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/user-roles", tags=["Roles por Empresa"])


# ==========================================
# Helpers
# ==========================================

async def _get_user_role_in_company(
    db: AsyncSession,
    user_id: str,
    company_id: str,
) -> UserCompanyRole | None:
    """Obtiene el rol de un usuario en una empresa específica"""
    result = await db.execute(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == user_id,
            UserCompanyRole.company_id == company_id,
            UserCompanyRole.is_active == True,  # noqa: E712
        )
    )
    return result.scalars().first()


async def _is_owner_or_admin_in_company(
    db: AsyncSession,
    user_id: str,
    company_id: str,
) -> bool:
    """Verifica si un usuario es owner o admin en una empresa"""
    role = await _get_user_role_in_company(db, user_id, company_id)
    if role and role.role in (CompanyRole.OWNER.value, CompanyRole.ADMIN.value):
        return True
    return False


# ==========================================
# Endpoints
# ==========================================

@router.get("/company/{company_id}", response_model=list[UserRoleResponse])
async def list_company_users(
    company_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar todos los usuarios y sus roles en una empresa.
    Solo accesible para usuarios con rol owner o admin en la empresa,
    o para administradores del sistema.
    """
    # Verificar permisos: admin del sistema o owner/admin en la empresa
    if not current_user.is_admin:
        has_access = await _is_owner_or_admin_in_company(
            db, str(current_user.id), str(company_id)
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para ver los roles de esta empresa. "
                       "Se requiere rol de owner o admin.",
            )

    # Verificar que la empresa existe
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada",
        )

    # Obtener todos los roles de la empresa
    result = await db.execute(
        select(UserCompanyRole).where(UserCompanyRole.company_id == str(company_id))
    )
    roles = result.scalars().all()
    return [UserRoleResponse.from_model(r) for r in roles]


@router.get("/my-roles", response_model=list[UserRoleWithCompanyResponse])
async def get_my_roles(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener los roles del usuario actual en todas las empresas.
    Incluye información de la empresa (razón social, RUC).
    """
    result = await db.execute(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == str(current_user.id),
            UserCompanyRole.is_active == True,  # noqa: E712
        )
    )
    roles = result.scalars().all()

    responses = []
    for role in roles:
        perms = None
        if role.permissions:
            try:
                perms = json.loads(role.permissions)
            except (json.JSONDecodeError, TypeError):
                perms = role.get_permissions()
        else:
            perms = role.get_permissions()

        # Obtener información de la empresa desde la relación
        company_name = None
        company_ruc = None
        if role.company:
            company_name = role.company.razon_social
            company_ruc = role.company.ruc

        responses.append(
            UserRoleWithCompanyResponse(
                id=str(role.id),
                user_id=str(role.user_id),
                company_id=str(role.company_id),
                company_name=company_name,
                company_ruc=company_ruc,
                role=role.role,
                permissions=perms,
                is_active=role.is_active,
                created_at=role.created_at,
                updated_at=role.updated_at,
            )
        )

    return responses


@router.post("", response_model=UserRoleResponse, status_code=status.HTTP_201_CREATED)
async def assign_role(
    role_data: UserRoleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Asignar un rol a un usuario en una empresa.
    Solo accesible para usuarios con rol owner o admin en la empresa,
    o para administradores del sistema.
    """
    # Verificar permisos
    if not current_user.is_admin:
        has_access = await _is_owner_or_admin_in_company(
            db, str(current_user.id), role_data.company_id
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para asignar roles en esta empresa. "
                       "Se requiere rol de owner o admin.",
            )

    # Verificar que la empresa existe
    result = await db.execute(
        select(Company).where(Company.id == role_data.company_id)
    )
    if not result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada",
        )

    # Verificar que el usuario destino existe
    result = await db.execute(
        select(User).where(User.id == role_data.user_id)
    )
    target_user = result.scalars().first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    # Verificar que no exista ya una asignación para este usuario en esta empresa
    existing = await _get_user_role_in_company(db, role_data.user_id, role_data.company_id)
    # Buscar también inactivas
    result = await db.execute(
        select(UserCompanyRole).where(
            UserCompanyRole.user_id == role_data.user_id,
            UserCompanyRole.company_id == role_data.company_id,
        )
    )
    existing_any = result.scalars().first()

    if existing_any and existing_any.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario ya tiene un rol asignado en esta empresa. "
                   "Use PUT para actualizar el rol existente.",
        )

    # Si existe una asignación inactiva, reactivarla con el nuevo rol
    if existing_any and not existing_any.is_active:
        existing_any.role = role_data.role
        existing_any.is_active = True
        if role_data.permissions is not None:
            existing_any.set_permissions(role_data.permissions)
        else:
            existing_any.set_permissions(
                DEFAULT_PERMISSIONS.get(CompanyRole(role_data.role), {})
            )
        await db.flush()
        logger.info(
            f"Rol reactivado: usuario {role_data.user_id} -> "
            f"{role_data.role} en empresa {role_data.company_id}"
        )
        return UserRoleResponse.from_model(existing_any)

    # Crear nueva asignación
    permissions_json = None
    if role_data.permissions is not None:
        permissions_json = json.dumps(role_data.permissions)
    else:
        permissions_json = json.dumps(
            DEFAULT_PERMISSIONS.get(CompanyRole(role_data.role), {})
        )

    new_role = UserCompanyRole(
        user_id=role_data.user_id,
        company_id=role_data.company_id,
        role=role_data.role,
        permissions=permissions_json,
        is_active=True,
    )
    db.add(new_role)
    await db.flush()

    logger.info(
        f"Nuevo rol asignado: usuario {role_data.user_id} -> "
        f"{role_data.role} en empresa {role_data.company_id}"
    )
    return UserRoleResponse.from_model(new_role)


@router.put("/{role_id}", response_model=UserRoleResponse)
async def update_role(
    role_id: UUID,
    role_data: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Actualizar el rol o permisos de un usuario en una empresa.
    Solo accesible para usuarios con rol owner o admin en la empresa,
    o para administradores del sistema.
    """
    # Obtener la asignación de rol existente
    result = await db.execute(
        select(UserCompanyRole).where(UserCompanyRole.id == str(role_id))
    )
    existing_role = result.scalars().first()
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación de rol no encontrada",
        )

    # Verificar permisos
    if not current_user.is_admin:
        has_access = await _is_owner_or_admin_in_company(
            db, str(current_user.id), existing_role.company_id
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para actualizar roles en esta empresa. "
                       "Se requiere rol de owner o admin.",
            )

    # Solo un owner puede cambiar el rol de otro owner
    if (
        existing_role.role == CompanyRole.OWNER.value
        and role_data.role is not None
        and role_data.role != CompanyRole.OWNER.value
    ):
        # Verificar que quien hace el cambio es owner de la empresa
        current_role = await _get_user_role_in_company(
            db, str(current_user.id), existing_role.company_id
        )
        if not current_role or current_role.role != CompanyRole.OWNER.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un owner puede cambiar el rol de otro owner.",
            )

    # Actualizar campos
    update_data = role_data.model_dump(exclude_unset=True)

    if "role" in update_data and update_data["role"] is not None:
        existing_role.role = update_data["role"]
        # Si se cambia el rol y no se especifican permisos, usar los del nuevo rol
        if "permissions" not in update_data:
            existing_role.set_permissions(
                DEFAULT_PERMISSIONS.get(CompanyRole(update_data["role"]), {})
            )

    if "permissions" in update_data and update_data["permissions"] is not None:
        existing_role.set_permissions(update_data["permissions"])

    if "is_active" in update_data and update_data["is_active"] is not None:
        existing_role.is_active = update_data["is_active"]

    await db.flush()
    logger.info(f"Rol actualizado: {role_id}")
    return UserRoleResponse.from_model(existing_role)


@router.delete("/{role_id}")
async def remove_role(
    role_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Eliminar la asignación de rol de un usuario en una empresa.
    Solo accesible para usuarios con rol owner o admin en la empresa,
    o para administradores del sistema.
    No se puede eliminar el último owner de una empresa.
    """
    # Obtener la asignación de rol existente
    result = await db.execute(
        select(UserCompanyRole).where(UserCompanyRole.id == str(role_id))
    )
    existing_role = result.scalars().first()
    if not existing_role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignación de rol no encontrada",
        )

    # Verificar permisos
    if not current_user.is_admin:
        has_access = await _is_owner_or_admin_in_company(
            db, str(current_user.id), existing_role.company_id
        )
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para eliminar roles en esta empresa. "
                       "Se requiere rol de owner o admin.",
            )

    # No permitir eliminar al último owner de una empresa
    if existing_role.role == CompanyRole.OWNER.value:
        result = await db.execute(
            select(UserCompanyRole).where(
                UserCompanyRole.company_id == existing_role.company_id,
                UserCompanyRole.role == CompanyRole.OWNER.value,
                UserCompanyRole.is_active == True,  # noqa: E712
                UserCompanyRole.id != str(role_id),
            )
        )
        other_owners = result.scalars().all()
        if not other_owners:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se puede eliminar al último owner de la empresa. "
                       "Asigne otro owner primero.",
            )

    # Eliminar la asignación
    await db.delete(existing_role)
    await db.flush()

    logger.info(f"Rol eliminado: {role_id}")
    return {"message": "Rol eliminado exitosamente."}


@router.get("/check-permission", response_model=PermissionCheck)
async def check_permission(
    company_id: str = Query(..., description="ID de la empresa"),
    permission_name: str = Query(..., description="Nombre del permiso a verificar"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verificar si el usuario actual tiene un permiso específico en una empresa.
    Los administradores del sistema tienen todos los permisos.
    """
    company_id = validate_uuid(company_id, "company_id")
    # Los admin del sistema tienen todos los permisos
    if current_user.is_admin:
        return PermissionCheck(
            permission_name=permission_name,
            has_permission=True,
        )

    # Buscar el rol del usuario en la empresa
    role = await _get_user_role_in_company(db, str(current_user.id), company_id)
    if not role:
        return PermissionCheck(
            permission_name=permission_name,
            has_permission=False,
        )

    has_perm = role.has_permission(permission_name)
    return PermissionCheck(
        permission_name=permission_name,
        has_permission=has_perm,
    )

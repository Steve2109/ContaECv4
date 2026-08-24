"""
ContaEC - Endpoints de Sub-Cuentas
Un usuario (owner) crea cuentas para sus empleados y selecciona los módulos
a los que cada sub-cuenta puede acceder. La contraseña temporal se envía
por correo y el empleado debe cambiarla en su primer inicio de sesión.
"""
import json
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, get_password_hash
from app.core.email_service import send_temporary_password_email
from app.core.config import get_settings
from app.core.validation import validate_uuid
from app.models.user import User
from app.schemas.subaccounts import (
    AVAILABLE_MODULES,
    SubAccountCreate,
    SubAccountResponse,
    SubAccountUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sub-accounts", tags=["Sub-Cuentas"])

# Módulos válidos (keys de AVAILABLE_MODULES)
VALID_MODULES = {m["key"] for m in AVAILABLE_MODULES}


def _serialize_modules(modules: list[str] | None) -> str | None:
    """Serializa la lista de módulos a JSON string para la BD (None = todos)."""
    if not modules:
        return None
    valid = [m for m in modules if m in VALID_MODULES]
    return json.dumps(valid)


async def _get_subaccount_for_parent(
    db: AsyncSession,
    parent: User,
    sub_id: str,
) -> User:
    """Obtiene una sub-cuenta verificando que pertenece al usuario actual"""
    sub_id = validate_uuid(sub_id, "sub_id")
    result = await db.execute(
        select(User).where(
            User.id == sub_id,
            User.parent_user_id == parent.id,
            User.is_subaccount == True,  # noqa: E712
        )
    )
    sub = result.scalars().first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sub-cuenta no encontrada.",
        )
    return sub


@router.post("", response_model=SubAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_subaccount(
    data: SubAccountCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Crear una sub-cuenta para un empleado.

    Solo cuentas principales (no sub-cuentas) pueden crear sub-cuentas.
    La contraseña temporal se envía por correo al empleado.
    """
    if current_user.is_subaccount:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Una sub-cuenta no puede crear otras sub-cuentas.",
        )

    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este correo electrónico.",
        )

    sub = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        phone=None,
        language=current_user.language or "es_EC",
        theme=current_user.theme or "light",
        license_type=current_user.license_type,
        is_active=True,
        is_admin=False,
        is_subaccount=True,
        parent_user_id=current_user.id,
        allowed_modules=_serialize_modules(data.allowed_modules),
        must_change_password=True,
        # La sub-cuenta hereda la vigencia de la licencia de la cuenta principal
        is_trial=current_user.is_trial,
        trial_start_date=current_user.trial_start_date,
        trial_end_date=current_user.trial_end_date,
        license_start_date=current_user.license_start_date,
        license_end_date=current_user.license_end_date,
    )
    db.add(sub)
    await db.flush()

    logger.info(
        f"Sub-cuenta creada: {sub.email} por {current_user.email}, "
        f"módulos={data.allowed_modules or ['*']}"
    )

    background_tasks.add_task(
        send_temporary_password_email,
        to_email=sub.email,
        full_name=sub.full_name or sub.email,
        temporary_password=data.password,
        motivo="subcuenta",
    )

    response = SubAccountResponse.model_validate(sub)

    # Verificar si el SMTP está configurado para enviar el correo
    _settings = get_settings()
    if not _settings.SMTP_ENABLED or not _settings.SMTP_HOST or not _settings.SMTP_USER:
        response.email_warning = (
            "El correo SMTP del sistema no esta configurado. "
            "La contrasena temporal NO fue enviada por correo. "
            "Comunique la contrasena manualmente al empleado o "
            "configure SMTP en Configuracion > Correo."
        )

    return response


@router.get("", response_model=list[SubAccountResponse])
async def list_subaccounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar las sub-cuentas creadas por el usuario actual"""
    result = await db.execute(
        select(User)
        .where(
            User.parent_user_id == current_user.id,
            User.is_subaccount == True,  # noqa: E712
        )
        .order_by(User.created_at.desc())
    )
    subs = result.scalars().all()
    return [SubAccountResponse.model_validate(s) for s in subs]


@router.patch("/{sub_id}", response_model=SubAccountResponse)
async def update_subaccount(
    sub_id: str,
    data: SubAccountUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar módulos, estado o contraseña de una sub-cuenta"""
    sub = await _get_subaccount_for_parent(db, current_user, sub_id)

    if data.full_name is not None:
        sub.full_name = data.full_name
    if data.allowed_modules is not None:
        sub.allowed_modules = _serialize_modules(data.allowed_modules)
    if data.is_active is not None:
        sub.is_active = data.is_active
    if data.password:
        sub.hashed_password = get_password_hash(data.password)
        sub.must_change_password = True
        background_tasks.add_task(
            send_temporary_password_email,
            to_email=sub.email,
            full_name=sub.full_name or sub.email,
            temporary_password=data.password,
            motivo="subcuenta",
        )

    await db.flush()
    return SubAccountResponse.model_validate(sub)


@router.delete("/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_subaccount(
    sub_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Desactivar (eliminar) una sub-cuenta"""
    sub = await _get_subaccount_for_parent(db, current_user, sub_id)
    sub.is_active = False
    await db.flush()
    logger.info(f"Sub-cuenta desactivada: {sub.email}")

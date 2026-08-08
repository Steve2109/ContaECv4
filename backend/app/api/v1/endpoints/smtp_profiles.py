"""
ContaEC - Endpoints de Perfiles SMTP
CRUD de perfiles SMTP, prueba de conexión y gestión de límites diarios
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.email_service import EmailServiceError, send_test_email
from app.core.encryption import decrypt_field, encrypt_field
from app.core.config import get_settings
from app.core.security import get_current_user
from app.models.smtp_profile import SMTPProfile, SmtpConnectionProtocol, SmtpProviderType
from app.models.user import User
from app.schemas.smtp_profile import (
    SMTPProfileCreate,
    SMTPProfileResponse,
    SMTPProfileUpdate,
    SMTPTestRequest,
    SMTPTestResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/smtp-profiles", tags=["Perfiles SMTP"])

settings = get_settings()


# ==========================================
# Helper Functions
# ==========================================

async def _get_profile_or_404(
    profile_id: str,
    current_user: User,
    db: AsyncSession,
) -> SMTPProfile:
    """Obtiene un perfil SMTP verificando propiedad del usuario"""
    result = await db.execute(
        select(SMTPProfile).where(SMTPProfile.id == profile_id)
    )
    profile = result.scalars().first()

    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil SMTP no encontrado.",
        )

    if profile.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a este perfil SMTP.",
        )

    return profile


def _determine_use_ssl(protocol: str, use_ssl: bool, use_tls: bool) -> bool:
    """
    Determina si se debe usar SSL basado en el protocolo.
    SMTP_SSL => SSL directo (puerto 465)
    STARTTLS => TLS después de conectar (puerto 587)
    SMTP => Sin cifrado (puerto 25)
    """
    if protocol == SmtpConnectionProtocol.SMTP_SSL:
        return True
    elif protocol == SmtpConnectionProtocol.STARTTLS:
        return False
    else:  # SMTP plain
        return use_ssl


# ==========================================
# Endpoints CRUD
# ==========================================

@router.post("", response_model=SMTPProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_smtp_profile(
    data: SMTPProfileCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un nuevo perfil SMTP"""
    # Si is_default=True, quitar default de otros perfiles del usuario
    if data.is_default:
        result = await db.execute(
            select(SMTPProfile).where(
                SMTPProfile.user_id == current_user.id,
                SMTPProfile.is_default == True,
            )
        )
        for existing in result.scalars().all():
            existing.is_default = False

    # Si es el primer perfil del usuario, establecerlo como default
    existing_result = await db.execute(
        select(SMTPProfile).where(SMTPProfile.user_id == current_user.id)
    )
    existing_profiles = existing_result.scalars().all()
    is_first = len(existing_profiles) == 0

    # Cifrar la contraseña
    encrypted_password = encrypt_field(data.password, settings.ENCRYPTION_KEY)

    profile = SMTPProfile(
        user_id=current_user.id,
        nombre=data.nombre,
        provider_type=data.provider_type,
        host=data.host,
        port=data.port,
        username=data.username,
        password=encrypted_password,
        use_ssl=data.use_ssl,
        use_tls=data.use_tls,
        protocol=data.protocol,
        imap_host=data.imap_host,
        imap_port=data.imap_port,
        pop3_host=data.pop3_host,
        pop3_port=data.pop3_port,
        is_default=data.is_default or is_first,
        daily_limit=data.daily_limit,
    )
    db.add(profile)
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="smtp_profile",
        entity_id=profile.id,
        description=f"Perfil SMTP creado: {data.nombre} ({data.provider_type})",
        ip_address=request.client.host if request.client else None,
    )

    return SMTPProfileResponse.model_validate(profile)


@router.get("", response_model=list[SMTPProfileResponse])
async def list_smtp_profiles(
    is_active: bool | None = None,
    provider_type: str | None = None,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar perfiles SMTP del usuario"""
    query = select(SMTPProfile).where(
        SMTPProfile.user_id == current_user.id,
    )

    if is_active is not None:
        query = query.where(SMTPProfile.is_active == is_active)

    if provider_type:
        query = query.where(SMTPProfile.provider_type == provider_type.upper())

    query = query.order_by(
        SMTPProfile.is_default.desc(),
        SMTPProfile.nombre,
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    profiles = result.scalars().all()

    return [SMTPProfileResponse.model_validate(p) for p in profiles]


@router.put("/{profile_id}", response_model=SMTPProfileResponse)
async def update_smtp_profile(
    profile_id: str,
    data: SMTPProfileUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un perfil SMTP"""
    profile_id = validate_uuid(profile_id, "profile_id")
    profile = await _get_profile_or_404(profile_id, current_user, db)

    # Si se establece como default, quitar default de otros perfiles
    if data.is_default:
        existing_result = await db.execute(
            select(SMTPProfile).where(
                SMTPProfile.user_id == current_user.id,
                SMTPProfile.is_default == True,
                SMTPProfile.id != profile_id,
            )
        )
        for existing in existing_result.scalars().all():
            existing.is_default = False

    update_data = data.model_dump(exclude_unset=True)

    # Cifrar la contraseña si se está actualizando
    if "password" in update_data and update_data["password"] is not None:
        update_data["password"] = encrypt_field(
            update_data["password"], settings.ENCRYPTION_KEY
        )

    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="smtp_profile",
        entity_id=profile.id,
        description=f"Perfil SMTP actualizado: {profile.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return SMTPProfileResponse.model_validate(profile)


@router.delete("/{profile_id}")
async def delete_smtp_profile(
    profile_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un perfil SMTP (eliminación física)"""
    profile_id = validate_uuid(profile_id, "profile_id")
    profile = await _get_profile_or_404(profile_id, current_user, db)

    was_default = profile.is_default
    profile_name = profile.nombre

    await db.delete(profile)
    await db.flush()

    # Si era el perfil por defecto, establecer otro como default
    if was_default:
        result = await db.execute(
            select(SMTPProfile).where(
                SMTPProfile.user_id == current_user.id,
                SMTPProfile.is_active == True,
            ).order_by(SMTPProfile.created_at).limit(1)
        )
        new_default = result.scalars().first()
        if new_default:
            new_default.is_default = True
            await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="smtp_profile",
        entity_id=profile_id,
        description=f"Perfil SMTP eliminado: {profile_name}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Perfil SMTP eliminado exitosamente."}


# ==========================================
# Test Connection
# ==========================================

@router.post("/{profile_id}/test", response_model=SMTPTestResponse)
async def test_smtp_connection(
    profile_id: str,
    data: SMTPTestRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Probar la conexión SMTP de un perfil"""
    profile_id = validate_uuid(profile_id, "profile_id")
    profile = await _get_profile_or_404(profile_id, current_user, db)

    # Descifrar la contraseña
    try:
        smtp_password = decrypt_field(profile.password, settings.ENCRYPTION_KEY)
    except Exception as e:
        return SMTPTestResponse(
            success=False,
            message=f"No se pudo descifrar la contraseña del perfil: {str(e)}",
        )

    # Determinar si usar SSL basado en el protocolo
    use_ssl = _determine_use_ssl(profile.protocol, profile.use_ssl, profile.use_tls)

    # Destino de prueba
    to_email = data.to_email or profile.username

    try:
        result = await send_test_email(
            smtp_host=profile.host,
            smtp_port=profile.port,
            smtp_user=profile.username,
            smtp_password=smtp_password,
            smtp_ssl=use_ssl,
            to_email=to_email,
        )

        # Audit log
        await log_action(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            action="TEST",
            entity_type="smtp_profile",
            entity_id=profile.id,
            description=f"Prueba de conexión SMTP exitosa para perfil: {profile.nombre}",
            ip_address=request.client.host if request.client else None,
        )

        return SMTPTestResponse(success=True, message=result.get("message", "Conexión exitosa"))

    except EmailServiceError as e:
        # Audit log (fallida)
        await log_action(
            db=db,
            user_id=current_user.id,
            user_email=current_user.email,
            action="TEST",
            entity_type="smtp_profile",
            entity_id=profile.id,
            description=f"Prueba de conexión SMTP fallida para perfil: {profile.nombre}",
            ip_address=request.client.host if request.client else None,
        )

        return SMTPTestResponse(success=False, message=str(e))

    except Exception as e:
        return SMTPTestResponse(
            success=False,
            message=f"Error inesperado al probar la conexión: {str(e)}",
        )


# ==========================================
# Set Default Profile
# ==========================================

@router.put("/{profile_id}/set-default", response_model=SMTPProfileResponse)
async def set_default_smtp_profile(
    profile_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Establecer un perfil SMTP como el perfil por defecto"""
    profile_id = validate_uuid(profile_id, "profile_id")
    profile = await _get_profile_or_404(profile_id, current_user, db)

    if not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede establecer como default un perfil inactivo.",
        )

    # Quitar default de otros perfiles
    result = await db.execute(
        select(SMTPProfile).where(
            SMTPProfile.user_id == current_user.id,
            SMTPProfile.is_default == True,
            SMTPProfile.id != profile_id,
        )
    )
    for existing in result.scalars().all():
        existing.is_default = False

    profile.is_default = True
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="smtp_profile",
        entity_id=profile.id,
        description=f"Perfil SMTP establecido como default: {profile.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return SMTPProfileResponse.model_validate(profile)


# ==========================================
# Reset Daily Counter
# ==========================================

@router.put("/{profile_id}/reset-counter", response_model=SMTPProfileResponse)
async def reset_daily_counter(
    profile_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reiniciar el contador diario de envíos de un perfil SMTP"""
    profile_id = validate_uuid(profile_id, "profile_id")
    profile = await _get_profile_or_404(profile_id, current_user, db)

    profile.sent_today = 0
    await db.flush()

    # Audit log
    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="smtp_profile",
        entity_id=profile.id,
        description=f"Contador diario reiniciado para perfil: {profile.nombre}",
        ip_address=request.client.host if request.client else None,
    )

    return SMTPProfileResponse.model_validate(profile)

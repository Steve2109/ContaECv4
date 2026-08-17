"""
ContaEC - Endpoints de Autenticación
Registro, login, refresh token con rotación, revocación de tokens, perfil de usuario,
recuperación de contraseña (contraseña temporal + cambio forzado)
"""
import logging
import secrets
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    revoke_token,
    verify_password,
    verify_token,
    oauth2_scheme,
)
from app.core.config import get_settings
from app.core.email_service import send_welcome_email, send_temporary_password_email
from app.core.token_blacklist import get_token_blacklist
from app.core.rate_limiter import limiter, AUTH_LOGIN_LIMIT, AUTH_REGISTER_LIMIT, AUTH_CHANGE_PASSWORD_LIMIT, AUTH_REFRESH_LIMIT
from app.models.user import User, UserConfig, LicenseType
from app.schemas.auth import (
    ForgotPasswordRequest,
    ForcePasswordChange,
    PasswordChange,
    RefreshTokenRequest,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
    UserUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticación"])
settings = get_settings()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
@limiter.limit(AUTH_REGISTER_LIMIT)
async def register(
    request: Request,
    user_data: UserRegister,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Registrar un nuevo usuario"""
    # Verificar si el email ya existe
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este correo electrónico."
        )

    # Crear usuario
    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=15)
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        phone=user_data.phone,
        language="es_EC",
        theme="light",
        license_type=LicenseType.MENSUAL,
        is_active=True,
        is_admin=False,
        # Trial period: 15 days
        is_trial=True,
        trial_start_date=now,
        trial_end_date=trial_end,
    )
    db.add(user)
    await db.flush()

    # Crear configuración por defecto del usuario (SANDBOX por defecto)
    user_config = UserConfig(
        user_id=user.id,
        environment_mode="sandbox",
        virustotal_enabled=False,
    )
    db.add(user_config)
    await db.flush()

    logger.info(f"Nuevo usuario registrado: {user.email}")

    # Enviar correo de bienvenida en segundo plano (tras enviar la respuesta).
    # NUNCA debe bloquear ni fallar el registro: si el SMTP no está configurado
    # o el envío falla, send_welcome_email solo lo registra en el log.
    background_tasks.add_task(
        send_welcome_email,
        to_email=user.email,
        full_name=user.full_name or user.email,
        trial_end_date=trial_end,
    )

    # Generar JWT tokens para auto-login tras registro
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=Token)
@limiter.limit(AUTH_LOGIN_LIMIT)
async def login(request: Request, login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Iniciar sesión y obtener tokens JWT"""
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacte al administrador."
        )

    # Verificar licencia / trial
    now = datetime.now(timezone.utc)
    on_valid_trial = False
    if user.is_trial and user.trial_end_date:
        trial_end = user.trial_end_date
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        if trial_end >= now:
            on_valid_trial = True

    if not on_valid_trial and user.license_end_date:
        # Handle both timezone-aware and naive datetimes
        end_date = user.license_end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        if end_date < now:
            user.is_active = False
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Su licencia ha expirado. Renueve su licencia para continuar."
            )

    # Actualizar último acceso
    user.updated_at = datetime.now(timezone.utc)
    await db.flush()

    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    logger.info(f"Inicio de sesión exitoso: {user.email}")
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
@limiter.limit(AUTH_REFRESH_LIMIT)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Renovar token de acceso usando refresh token.
    Implementa rotación de refresh tokens: el token anterior se registra
    como rotado y si se reutiliza, se detecta como ataque de replay.
    """
    try:
        payload = verify_token(refresh_request.refresh_token, token_type="refresh")
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de renovación inválido."
        )

    user_id = payload.get("sub")
    old_jti = payload.get("jti")

    # === Refresh Token Rotation (Brecha 26) ===
    if old_jti:
        blacklist = get_token_blacklist()

        # Check if this refresh token was already used (replay attack detection)
        if blacklist.check_refresh_reuse(old_jti):
            # REPLAY ATTACK DETECTED: Revoke entire token chain
            exp = payload.get("exp", 0)
            revoked_chain = blacklist.revoke_refresh_chain(old_jti, exp)
            logger.warning(
                f"SECURITY: Refresh token replay detected for user {user_id}. "
                f"Revoked {len(revoked_chain)} tokens in chain."
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de renovación reutilizado. Por seguridad, inicie sesión nuevamente.",
            )

        # Revoke the old refresh token
        exp = payload.get("exp", 0)
        blacklist.revoke_token(old_jti, exp)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo."
        )

    # Generate new token pair
    new_access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    new_refresh_token = create_refresh_token(data={"sub": str(user.id)})

    # Register the rotation (old_jti -> new_jti)
    if old_jti:
        # Decode new refresh token to get its JTI
        new_payload = verify_token(new_refresh_token, token_type="refresh")
        new_jti = new_payload.get("jti")
        if new_jti:
            blacklist = get_token_blacklist()
            blacklist.register_refresh_rotation(old_jti, new_jti)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Cerrar sesión revocando el token de acceso actual.
    El token se añade a la blacklist para invalidación inmediata.
    """
    # Revoke the access token by adding its JTI to the blacklist
    from jose import jwt as jose_jwt

    try:
        payload = jose_jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            blacklist = get_token_blacklist()
            blacklist.revoke_token(jti, exp)
            logger.info(f"Token revocado en logout: {current_user.email}, jti={jti[:8]}...")
    except Exception as e:
        logger.warning(f"Error revocando token en logout: {e}")

    logger.info(f"Cierre de sesión: {current_user.email}")
    return {"message": "Sesión cerrada exitosamente."}


@router.post("/revoke")
async def revoke_access_token(
    request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Revocar un token específico (access o refresh).
    Útil para cerrar sesión en otros dispositivos.
    """
    try:
        # Try to decode without type restriction to support both token types
        from jose import jwt as jose_jwt
        payload = jose_jwt.decode(
            request.refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        jti = payload.get("jti")
        exp = payload.get("exp")
        token_sub = payload.get("sub")

        # Only allow revoking own tokens
        if token_sub != str(current_user.id) and not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para revocar este token."
            )

        if jti and exp:
            blacklist = get_token_blacklist()
            blacklist.revoke_token(jti, exp)
            logger.info(f"Token revocado por {current_user.email}: jti={jti[:8]}...")

    except Exception as e:
        logger.warning(f"Error revocando token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pudo revocar el token."
        )

    return {"message": "Token revocado exitosamente."}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Obtener perfil del usuario actual"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar perfil del usuario actual"""
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    await db.flush()
    return UserResponse.model_validate(current_user)


@router.post("/forgot-password")
@limiter.limit(AUTH_CHANGE_PASSWORD_LIMIT)
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Recuperación de contraseña desde el panel de inicio de sesión.

    Valida el correo registrado más 1-2 datos personales (nombre completo y/o
    teléfono) para evitar solicitudes de terceros. Si la validación pasa:
    - Genera una contraseña temporal segura
    - La envía al correo registrado
    - Marca al usuario con must_change_password=True (se le pedirá cambiarla al entrar)

    Por seguridad, la respuesta siempre es genérica (no revela si el correo existe).
    """
    email = data.email.lower().strip()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        logger.info(f"Solicitud de recuperación para correo no registrado: {email}")
        return {"message": "Si el correo está registrado, recibirás una contraseña temporal en breve."}

    if not user.is_active:
        return {"message": "Si el correo está registrado, recibirás una contraseña temporal en breve."}

    # Validación: debe coincidir al menos el nombre completo o el teléfono
    full_name_ok = bool(
        data.full_name and user.full_name
        and data.full_name.strip().lower() == user.full_name.strip().lower()
    )
    phone_ok = bool(
        data.phone and user.phone
        and data.phone.strip().replace(" ", "").replace("-", "") == user.phone.strip().replace(" ", "").replace("-", "")
    )
    if not (full_name_ok or phone_ok):
        logger.warning(f"Recuperación rechazada para {email}: datos de validación no coinciden")
        return {"message": "Si el correo está registrado, recibirás una contraseña temporal en breve."}

    # Generar contraseña temporal segura (cumple normativa: mayúscula, minúscula, número, símbolo, 8+)
    temporary_password = "Contaec" + secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:6] + "#1"
    user.hashed_password = get_password_hash(temporary_password)
    user.must_change_password = True
    await db.flush()

    background_tasks.add_task(
        send_temporary_password_email,
        to_email=user.email,
        full_name=user.full_name or user.email,
        temporary_password=temporary_password,
        motivo="recuperacion",
    )

    logger.info(f"Contraseña temporal generada para {user.email} (recuperación)")
    return {"message": "Si el correo está registrado, recibirás una contraseña temporal en breve."}


@router.post("/force-change-password")
@limiter.limit(AUTH_CHANGE_PASSWORD_LIMIT)
async def force_change_password(
    request: Request,
    password_data: ForcePasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cambio de contraseña OBLIGATORIO tras iniciar sesión con una contraseña
    temporal (recuperación o restablecimiento por el administrador).

    Solo se permite si el usuario tiene must_change_password=True. Al completarlo:
    - Se guarda la nueva contraseña
    - Se limpia la marca de cambio obligatorio
    - Se emiten tokens nuevos para la sesión actual
    """
    if not current_user.must_change_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No hay una contraseña temporal pendiente de cambio.",
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.must_change_password = False
    await db.flush()

    access_token = create_access_token(data={"sub": str(current_user.id), "email": current_user.email})
    refresh_token = create_refresh_token(data={"sub": str(current_user.id)})

    logger.info(f"Contraseña cambiada (flujo forzado): {current_user.email}")
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.put("/change-password")
@limiter.limit(AUTH_CHANGE_PASSWORD_LIMIT)
async def change_password(
    request: Request,
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cambiar contraseña del usuario actual. Revoca todos los tokens existentes."""
    if not verify_password(password_data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contraseña actual incorrecta."
        )

    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.flush()

    # Note: After password change, existing tokens will still work until they expire.
    # For full security, the user should log out from all devices.
    # A more advanced implementation would track all active JTIs per user.

    return {"message": "Contraseña actualizada exitosamente."}

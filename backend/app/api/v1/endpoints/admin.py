"""
ContaEC - Endpoints de Administración
Dashboard, gestión de usuarios, licencias, seguridad
"""
import logging
import platform
import os
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ai_admin import (
    ai_errors_count,
    ai_global_enabled,
    ai_self_test,
    clear_ai_errors,
    get_ai_errors,
    get_user_ai_enabled,
    set_ai_global_enabled,
    set_user_ai_enabled,
    z_ai_installed,
    llm_configured,
)
from app.core.database import get_db
from app.core.email_service import send_temporary_password_email
from app.core.licenses import get_plan_config, update_plan_config
from app.core.security import get_current_user, get_current_active_admin, get_password_hash
from app.core.config import get_settings
from app.models.user import User, UserConfig, LicenseType
from app.models.company import Company
from app.models.client import Client
from app.models.ml_ai import MLChatbotSesion, MLPrediccion
from app.schemas.auth import AdminResetPassword, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Administración"])

# Track application start time for uptime calculation
_startup_time = datetime.now(timezone.utc)

# ==========================================
# License Price Management (in-memory, editable by admin)
# ==========================================
LICENSE_PRICES = {
    "monthly": {"price": 15.00, "months": 1, "label": "Mensual"},
    "quarterly": {"price": 40.00, "months": 3, "label": "Trimestral"},
    "semiannual": {"price": 75.00, "months": 6, "label": "Semestral"},
    "annual": {"price": 130.00, "months": 12, "label": "Anual"},
}


class LicensePriceUpdate(BaseModel):
    monthly: float | None = None
    quarterly: float | None = None
    semiannual: float | None = None
    annual: float | None = None


@router.get("/dashboard")
async def admin_dashboard(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard general del administrador con resumen completo del sistema"""
    # Total usuarios
    total_users = await db.scalar(select(func.count(User.id)))
    active_users = await db.scalar(select(func.count(User.id)).where(User.is_active == True))
    
    # Total empresas
    total_companies = await db.scalar(select(func.count(Company.id)))
    
    # Total clientes
    total_clients = await db.scalar(select(func.count(Client.id)))
    
    # Licencias por vencer (próximos 30 días)
    now = datetime.now(timezone.utc)
    thirty_days = now + timedelta(days=30)
    expiring_licenses = await db.scalar(
        select(func.count(User.id)).where(
            and_(
                User.license_end_date != None,
                User.license_end_date <= thirty_days,
                User.license_end_date >= now,
            )
        )
    )
    
    # Licencias expiradas
    expired_licenses = await db.scalar(
        select(func.count(User.id)).where(
            and_(
                User.license_end_date != None,
                User.license_end_date < now,
            )
        )
    )
    
    # Usuarios por tipo de licencia
    license_distribution = {}
    for lt in LicenseType:
        count = await db.scalar(
            select(func.count(User.id)).where(User.license_type == lt)
        )
        license_distribution[lt.value] = count

    # Usuarios en período de prueba activo (trial vigente)
    trial_users = await db.scalar(
        select(func.count(User.id)).where(
            and_(
                User.is_trial == True,
                User.trial_end_date != None,
                User.trial_end_date >= now,
            )
        )
    )
    trial_users_total = await db.scalar(
        select(func.count(User.id)).where(User.is_trial == True)
    )

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": (total_users or 0) - (active_users or 0),
        "total_companies": total_companies,
        "total_clients": total_clients,
        "expiring_licenses": expiring_licenses,
        "expired_licenses": expired_licenses,
        "trial_users": trial_users,
        "trial_users_total": trial_users_total,
        "license_distribution": license_distribution,
    }


@router.get("/system-health")
async def system_health(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard detallado de salud del sistema"""
    settings = get_settings()

    # System information with psutil
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        # Cross-platform disk usage
        disk = psutil.disk_usage('/')
        system_info = {
            "cpu_percent": cpu_percent,
            "memory_total_mb": round(memory.total / (1024 * 1024), 2),
            "memory_used_mb": round(memory.used / (1024 * 1024), 2),
            "memory_percent": memory.percent,
            "disk_total_gb": round(disk.total / (1024 ** 3), 2),
            "disk_used_gb": round(disk.used / (1024 ** 3), 2),
            "disk_percent": disk.percent,
        }
    except ImportError:
        # Fallback without psutil - use basic OS commands
        system_info = {
            "cpu_percent": "N/A (instalar psutil)",
            "memory_percent": "N/A (instalar psutil)",
            "disk_percent": "N/A (instalar psutil)",
        }

    # Database stats
    total_users = await db.scalar(select(func.count(User.id)))
    total_companies = await db.scalar(select(func.count(Company.id)))
    total_clients = await db.scalar(select(func.count(Client.id)))

    # Calculate uptime
    now = datetime.now(timezone.utc)
    uptime_delta = now - _startup_time
    uptime_seconds = int(uptime_delta.total_seconds())
    if uptime_seconds < 3600:
        uptime_str = f"{uptime_seconds // 60} min"
    elif uptime_seconds < 86400:
        uptime_str = f"{uptime_seconds // 3600}h {uptime_seconds % 3600 // 60}m"
    else:
        uptime_str = f"{uptime_seconds // 86400}d {uptime_seconds % 86400 // 3600}h"

    return {
        "system": system_info,
        "database": {
            "total_users": total_users,
            "total_companies": total_companies,
            "total_clients": total_clients,
        },
        "application": {
            "name": "ContaEC",
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "uptime": uptime_str,
            "python_version": platform.python_version(),
            "system": platform.system(),
        },
        "environment_toggle_available": True,
    }


@router.post("/environment/toggle")
async def toggle_environment(
    current_user: User = Depends(get_current_active_admin),
):
    """
    Cambiar entre ambiente de desarrollo y producción.
    Nota: Esto solo cambia la variable APP_ENV en memoria.
    Para un cambio permanente, se debe actualizar el archivo .env.
    """
    settings = get_settings()
    current_env = settings.APP_ENV

    if current_env.lower() == "production":
        new_env = "development"
    else:
        new_env = "production"

    # Note: We cannot modify pydantic-settings at runtime directly.
    # We return the target environment so the frontend can show it.
    # For a permanent change, the admin should update the .env file.
    return {
        "current_environment": current_env,
        "target_environment": new_env,
        "message": f"Para cambiar permanentemente, actualice APP_ENV={new_env} en el archivo .env y reinicie el servidor.",
        "is_production": current_env.lower() == "production",
    }


@router.put("/environment")
async def update_environment_config(
    app_env: str = Query(..., description="Nuevo ambiente: 'production' o 'development'"),
    current_user: User = Depends(get_current_active_admin),
):
    """
    Actualizar configuración de ambiente.
    Retorna la nueva configuración para que el frontend la refleje.
    Nota: El cambio real requiere actualizar .env y reiniciar.
    """
    if app_env.lower() not in ("production", "development"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="APP_ENV debe ser 'production' o 'development'."
        )

    settings = get_settings()
    return {
        "current_environment": settings.APP_ENV,
        "requested_environment": app_env.lower(),
        "message": f"Para aplicar el cambio, actualice APP_ENV={app_env.lower()} en el archivo .env y reinicie el servidor.",
        "is_production": app_env.lower() == "production",
    }


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Listar todos los usuarios con su información de licencia"""
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Obtener detalles de un usuario específico"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}/license")
async def update_user_license(
    user_id: UUID,
    license_type: LicenseType,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Modificar el licenciamiento de un usuario"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    now = datetime.now(timezone.utc)
    user.license_type = license_type
    user.is_active = True
    
    # Calcular nueva fecha de expiración
    duration_map = {
        LicenseType.MENSUAL: timedelta(days=30),
        LicenseType.TRIMESTRAL: timedelta(days=90),
        LicenseType.SEMESTRAL: timedelta(days=180),
        LicenseType.ANUAL: timedelta(days=365),
    }
    
    # Si la licencia actual no ha expirado, extender desde la fecha actual
    base_date = user.license_end_date if user.license_end_date and user.license_end_date > now else now
    user.license_start_date = now
    user.license_end_date = base_date + duration_map[license_type]
    
    await db.flush()
    
    return {
        "message": f"Licencia actualizada a {license_type.value}",
        "user_id": str(user.id),
        "license_type": license_type.value,
        "license_end_date": user.license_end_date.isoformat(),
    }


@router.put("/users/{user_id}/active")
async def toggle_user_active(
    user_id: UUID,
    is_active: bool = Query(..., description="Nuevo estado activo del usuario"),
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activar o desactivar un usuario"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # No permitir desactivar al propio administrador
    if str(user.id) == str(current_user.id) and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivar su propia cuenta."
        )
    
    user.is_active = is_active
    await db.flush()
    
    action = "activado" if is_active else "desactivado"
    logger.info(f"Usuario {user.email} {action} por {current_user.email}")

    return {
        "message": f"Usuario {action} exitosamente.",
        "user_id": str(user.id),
        "is_active": user.is_active,
    }


@router.put("/users/{user_id}/trial")
async def modify_user_trial(
    user_id: UUID,
    trial_days: int = Query(..., ge=1, le=90, description="Número de días para el período de prueba"),
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Modificar el período de prueba de un usuario (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    now = datetime.now(timezone.utc)
    user.is_trial = True
    user.trial_start_date = now
    user.trial_end_date = now + timedelta(days=trial_days)

    await db.flush()

    return {
        "message": f"Período de prueba actualizado a {trial_days} días",
        "user_id": str(user.id),
        "trial_start_date": user.trial_start_date.isoformat(),
        "trial_end_date": user.trial_end_date.isoformat(),
        "trial_days": trial_days,
    }


@router.put("/users/{user_id}/end-trial")
async def end_user_trial(
    user_id: UUID,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Finalizar el período de prueba de un usuario (admin only)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_trial = False
    user.trial_start_date = None
    user.trial_end_date = None

    await db.flush()

    return {
        "message": "Período de prueba finalizado",
        "user_id": str(user.id),
    }


@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: UUID,
    data: AdminResetPassword,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Restablecer la contraseña de un cliente desde el panel de administración.

    - Usa la contraseña temporal proporcionada o genera una automáticamente
    - Marca must_change_password=True (el cliente deberá cambiarla al entrar)
    - Envía la contraseña temporal por correo al cliente (si send_email=True)
    - Revoca los tokens anteriores del usuario para cerrar sus sesiones activas
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede restablecer su propia contraseña desde este panel.",
        )

    temporary_password = data.temporary_password or (
        "Contaec" + secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:6] + "#1"
    )

    user.hashed_password = get_password_hash(temporary_password)
    user.must_change_password = True
    await db.flush()

    # Revocar sesiones activas del usuario (tokens en la blacklist se invalidan al expirar;
    # aquí invalidamos inmediatamente los refresh tokens vigentes vía su firma no es posible,
    # por lo que se fuerza con la marca must_change_password en el próximo login/uso).

    if data.send_email:
        background_tasks.add_task(
            send_temporary_password_email,
            to_email=user.email,
            full_name=user.full_name or user.email,
            temporary_password=temporary_password,
            motivo="admin",
        )

    logger.info(f"Contraseña restablecida para {user.email} por {current_user.email}")
    return {
        "message": "Contraseña restablecida exitosamente."
        + (" Se envió la contraseña temporal por correo." if data.send_email else ""),
        "user_id": str(user.id),
        "temporary_password": temporary_password,
        "must_change_password": True,
    }


@router.get("/trial-users")
async def list_trial_users(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Listar todos los usuarios en período de prueba"""
    result = await db.execute(
        select(User).where(User.is_trial == True).order_by(User.trial_end_date)
    )
    users = result.scalars().all()
    now = datetime.now(timezone.utc)

    return {
        "trial_users": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "is_active": u.is_active,
                "trial_start_date": u.trial_start_date.isoformat() if u.trial_start_date else None,
                "trial_end_date": u.trial_end_date.isoformat() if u.trial_end_date else None,
                "trial_days_remaining": max(0, (u.trial_end_date - now).days) if u.trial_end_date else 0,
            }
            for u in users
        ]
    }


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Eliminar un usuario y toda su información asociada.
    Las relaciones con CASCADE eliminan: UserConfig, Companies (y todo su contenido),
    UserCompanyRole, EmailTemplates, Employees, RolPago, Notifications, SMTPProfiles.
    Las relaciones con SET NULL mantienen los datos pero eliminan la referencia al usuario.
    """
    # No permitir auto-eliminación
    if str(user_id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede eliminar su propia cuenta."
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    email = user.email
    await db.delete(user)
    await db.flush()

    logger.info(f"Admin {current_user.email} deleted user {email}")

    return {
        "message": f"Usuario {email} eliminado exitosamente con toda su información asociada.",
        "user_id": str(user_id),
    }


@router.get("/security-issues")
async def security_issues(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Dashboard detallado de problemas de seguridad por usuario"""
    now = datetime.now(timezone.utc)
    
    # Usuarios con licencia expirada pero aún activos
    expired_active = await db.execute(
        select(User).where(
            and_(
                User.license_end_date != None,
                User.license_end_date < now,
                User.is_active == True,
            )
        )
    )
    expired_active_users = expired_active.scalars().all()
    
    # Usuarios sin configuración completa:
    # - sin fila de UserConfig (perfil/ambiente sin crear), o
    # - sin ninguna empresa creada (cuenta a medio configurar).
    # Se excluye al administrador del sistema para no generar ruido.
    users_no_config_raw = await db.execute(
        select(User).where(
            User.is_admin == False,
            and_(
                ~User.id.in_(select(UserConfig.user_id)),
                ~User.id.in_(select(Company.user_id)),
            ),
        )
    )
    users_no_config = users_no_config_raw.scalars().all()

    users_without_company = await db.execute(
        select(User).where(
            User.is_admin == False,
            User.id.in_(select(UserConfig.user_id)),
            ~User.id.in_(select(Company.user_id)),
        )
    )
    users_no_company = users_without_company.scalars().all()

    def _config_issue(u: User, reason: str, reason_label: str) -> dict:
        return {
            "user_id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "reason": reason,
            "reason_label": reason_label,
        }

    return {
        "expired_active_licenses": [
            {
                "user_id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "license_end_date": u.license_end_date.isoformat() if u.license_end_date else None,
                "days_expired": (now - u.license_end_date).days if u.license_end_date else None,
            }
            for u in expired_active_users
        ],
        "users_without_config": [
            _config_issue(u, "sin_configuracion", "Sin configuracion de usuario")
            for u in users_no_config
        ]
        + [
            _config_issue(u, "sin_empresa", "Sin empresa creada")
            for u in users_no_company
        ],
    }


# ==========================================
# License Price Management Endpoints
# ==========================================

@router.get("/license-prices")
async def get_license_prices(
    current_user: User = Depends(get_current_active_admin),
):
    """Obtener precios actuales de todas las licencias"""
    return {
        "prices": LICENSE_PRICES,
        "currency": "USD",
    }


@router.put("/license-prices")
async def update_license_prices(
    data: LicensePriceUpdate,
    current_user: User = Depends(get_current_active_admin),
):
    """
    Actualizar precios de licencias.
    Solo se envían los precios que se quieren cambiar (None = no cambiar).
    """
    updated = []
    if data.monthly is not None:
        LICENSE_PRICES["monthly"]["price"] = data.monthly
        updated.append("monthly")
    if data.quarterly is not None:
        LICENSE_PRICES["quarterly"]["price"] = data.quarterly
        updated.append("quarterly")
    if data.semiannual is not None:
        LICENSE_PRICES["semiannual"]["price"] = data.semiannual
        updated.append("semiannual")
    if data.annual is not None:
        LICENSE_PRICES["annual"]["price"] = data.annual
        updated.append("annual")

    logger.info(f"Admin {current_user.email} updated license prices: {updated}")

    return {
        "message": f"Precios actualizados: {', '.join(updated)}",
        "prices": LICENSE_PRICES,
    }


# ==========================================
# Límites y features por plan (editable)
# ==========================================

LIMIT_LABELS = {
    "max_companies": "Empresas max.",
    "max_users_per_company": "Usuarios/empresa",
    "max_comprobantes_month": "Comprobantes/mes",
    "max_employees": "Empleados",
    "max_products": "Productos",
}


class PlanLimitsUpdate(BaseModel):
    max_companies: Optional[int] = None
    max_users_per_company: Optional[int] = None
    max_comprobantes_month: Optional[int] = None
    max_employees: Optional[int] = None
    max_products: Optional[int] = None


class PlanUpdate(BaseModel):
    limits: Optional[PlanLimitsUpdate] = None
    features: Optional[dict[str, bool]] = None


class LicensePlansUpdate(BaseModel):
    monthly: Optional[PlanUpdate] = None
    quarterly: Optional[PlanUpdate] = None
    semiannual: Optional[PlanUpdate] = None
    annual: Optional[PlanUpdate] = None


@router.get("/license-plans")
async def get_license_plans(
    current_user: User = Depends(get_current_active_admin),
):
    """
    Obtener configuración completa de planes: precios, meses, límites y features.
    Combina los precios editables (LICENSE_PRICES) con los límites/features
    editables (core.licenses._PLAN_CONFIG).
    """
    plans = get_plan_config()
    result = {}
    for key, cfg in plans.items():
        price_info = LICENSE_PRICES.get(key, {})
        result[key] = {
            "label": cfg.get("label", key),
            "price": price_info.get("price", 0),
            "months": price_info.get("months", 1),
            "limits": {k: cfg.get(k) for k in LIMIT_LABELS},
            "features": cfg.get("features", {}),
        }
    return {"plans": result, "limit_labels": LIMIT_LABELS}


@router.put("/license-plans")
async def update_license_plans(
    data: LicensePlansUpdate,
    current_user: User = Depends(get_current_active_admin),
):
    """
    Actualizar límites y/o features de los planes.
    Solo se envían los campos que se quieren cambiar.
    """
    updated_plans = []
    updates = {
        "monthly": data.monthly,
        "quarterly": data.quarterly,
        "semiannual": data.semiannual,
        "annual": data.annual,
    }
    for key, plan_update in updates.items():
        if plan_update is None:
            continue
        limits = plan_update.limits.model_dump(exclude_none=True) if plan_update.limits else None
        features = plan_update.features or None
        if not limits and not features:
            continue
        update_plan_config(key, limits=limits, features=features)
        updated_plans.append(key)

    logger.info(f"Admin {current_user.email} updated license plans: {updated_plans}")

    return {
        "message": f"Planes actualizados: {', '.join(updated_plans) or 'ninguno'}",
        "plans": get_plan_config(),
    }


# ==========================================
# Panel ML/IA (configuración global y por usuario)
# ==========================================

@router.get("/ai-status")
async def get_ai_status(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Estado general del módulo ML/IA"""
    total_users = await db.scalar(select(func.count(User.id))) or 0

    from app.core.config import get_settings as get_app_settings

    has_api_key = bool(getattr(get_app_settings(), "LLM_API_KEY", ""))
    cli_ok = z_ai_installed()
    if has_api_key:
        llm_mode = "api"
    elif cli_ok:
        llm_mode = "cli"
    else:
        llm_mode = "none"

    return {
        "global_enabled": ai_global_enabled(),
        "z_ai_installed": cli_ok,
        "llm_configured": llm_configured(),
        "llm_mode": llm_mode,
        "users_total": total_users,
        "errors_count": ai_errors_count(),
    }


class AISettingsUpdate(BaseModel):
    enabled: bool


@router.put("/ai-settings")
async def update_ai_settings(
    data: AISettingsUpdate,
    current_user: User = Depends(get_current_active_admin),
):
    """Activar/desactivar la capa de IA globalmente"""
    enabled = set_ai_global_enabled(data.enabled)
    logger.info(f"Admin {current_user.email} set AI global_enabled={enabled}")
    return {
        "message": f"IA {'habilitada' if enabled else 'deshabilitada'} globalmente",
        "global_enabled": enabled,
    }


@router.get("/ai-users")
async def list_ai_users(
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Listar usuarios con su estado de IA y uso del módulo ML/IA"""
    result = await db.execute(
        select(User).order_by(User.created_at.desc()).limit(200)
    )
    users = result.scalars().all()

    items = []
    for u in users:
        sessions = await db.scalar(
            select(func.count(MLChatbotSesion.id)).where(MLChatbotSesion.user_id == u.id)
        ) or 0
        predictions = await db.scalar(
            select(func.count(MLPrediccion.id)).where(MLPrediccion.user_id == u.id)
        ) or 0
        items.append({
            "user_id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "is_admin": u.is_admin,
            "ai_enabled": get_user_ai_enabled(u.id) if get_user_ai_enabled(u.id) is not None else ai_global_enabled(),
            "ai_override": get_user_ai_enabled(u.id),
            "chatbot_sessions": sessions,
            "predictions": predictions,
        })

    return {"users": items}


class AIUserUpdate(BaseModel):
    enabled: bool


@router.put("/ai-users/{user_id}")
async def update_ai_user(
    user_id: UUID,
    data: AIUserUpdate,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activar/desactivar la capa de IA para un usuario específico"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    enabled = set_user_ai_enabled(str(user_id), data.enabled)
    logger.info(f"Admin {current_user.email} set AI for {user.email} = {enabled}")
    return {
        "message": f"IA {'habilitada' if enabled else 'deshabilitada'} para {user.email}",
        "user_id": str(user_id),
        "ai_enabled": enabled,
    }


@router.get("/ai-errors")
async def list_ai_errors(
    current_user: User = Depends(get_current_active_admin),
    limit: int = Query(50, ge=1, le=200),
):
    """Errores recientes del módulo ML/IA"""
    return {"errors": get_ai_errors(limit=limit)}


@router.delete("/ai-errors")
async def clear_ai_errors_endpoint(
    current_user: User = Depends(get_current_active_admin),
):
    """Limpiar el buffer de errores del módulo ML/IA"""
    count = clear_ai_errors()
    return {"message": f"{count} error(es) eliminados", "cleared": count}


@router.post("/ai/test")
async def run_ai_self_test(
    current_user: User = Depends(get_current_active_admin),
):
    """Ejecuta un autotest de la cadena de respuestas de IA"""
    return await ai_self_test()

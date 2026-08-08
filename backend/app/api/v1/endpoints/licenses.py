"""
ContaEC - Endpoints de Licencias
Renovación, verificación, límites por tier, enlace de pago por WhatsApp
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, validate_uuid
from app.core.security import get_current_user
from app.core.licenses import (
    LICENSE_TIERS,
    get_tier_limits,
    has_feature,
    get_license_limits,
    get_feature_label,
    get_minimum_tier_for_feature,
)
from app.models.user import User, LicenseType
from app.models.company import Company
from app.models.comprobante import Comprobante
from app.models.user_company_role import UserCompanyRole
from app.schemas.auth import UserResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/licenses", tags=["Licencias"])

# ==========================================
# Precios por tier de licencia
# ==========================================

LICENSE_PRICES = {
    LicenseType.MENSUAL: {"price": 15.00, "months": 1, "label": "Mensual"},
    LicenseType.TRIMESTRAL: {"price": 40.00, "months": 3, "label": "Trimestral"},
    LicenseType.SEMESTRAL: {"price": 75.00, "months": 6, "label": "Semestral"},
    LicenseType.ANUAL: {"price": 130.00, "months": 12, "label": "Anual"},
}

# Teléfono de soporte para WhatsApp
WHATSAPP_NUMBER = "593960068866"


@router.get("/status")
async def get_license_status(
    current_user: User = Depends(get_current_user),
):
    """
    Obtener estado de la licencia del usuario actual.

    Prioriza el trial sobre la licencia: si el usuario está en trial activo,
    ese es el estado principal. Si el trial expiró, se muestra la licencia.
    """
    now = datetime.now(timezone.utc)

    # === TRIAL INFO (prioritario) ===
    is_trial = current_user.is_trial or False
    trial_days_remaining = None
    trial_start_date_str = None
    trial_end_date_str = None
    trial_active = False

    if is_trial and current_user.trial_end_date:
        trial_end = current_user.trial_end_date
        if trial_end.tzinfo is None:
            trial_end = trial_end.replace(tzinfo=timezone.utc)
        trial_end_date_str = trial_end.isoformat()

        if current_user.trial_start_date:
            trial_start = current_user.trial_start_date
            if trial_start.tzinfo is None:
                trial_start = trial_start.replace(tzinfo=timezone.utc)
            trial_start_date_str = trial_start.isoformat()

        if trial_end >= now:
            trial_days_remaining = (trial_end - now).days
            trial_active = True
        else:
            trial_days_remaining = 0
            trial_active = False

    # === LICENSE INFO ===
    license_days_remaining = None
    license_start_date_str = None
    license_end_date_str = None
    license_expired = False
    license_active = False

    if current_user.license_end_date:
        end_date = current_user.license_end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        license_end_date_str = end_date.isoformat()

        if current_user.license_start_date:
            start_date = current_user.license_start_date
            if start_date.tzinfo is None:
                start_date = start_date.replace(tzinfo=timezone.utc)
            license_start_date_str = start_date.isoformat()

        if end_date >= now:
            license_days_remaining = (end_date - now).days
            license_active = True
        else:
            license_days_remaining = 0
            license_expired = True

    # === ESTADO CONSOLIDADO ===
    # Si el trial está activo, ese es el estado principal
    # Si el trial expiró pero hay licencia, se muestra la licencia
    # Si no hay trial ni licencia, se muestra sin licencia
    effective_is_active = trial_active or license_active
    effective_is_expired = not effective_is_active and (license_expired or (is_trial and not trial_active))
    effective_days_remaining = None

    if trial_active:
        effective_days_remaining = trial_days_remaining
    elif license_active:
        effective_days_remaining = license_days_remaining

    # Incluir límites del tier
    tier_info = get_tier_limits(current_user.license_type) if current_user.license_type else None

    return {
        # Estado consolidado
        "is_active": effective_is_active,
        "is_expired": effective_is_expired,
        "days_remaining": effective_days_remaining,

        # Info de licencia
        "license_type": current_user.license_type if current_user.license_type else None,
        "license_start_date": license_start_date_str,
        "license_end_date": license_end_date_str,
        "license_days_remaining": license_days_remaining,
        "license_active": license_active,
        "license_expired": license_expired,

        # Info de trial
        "is_trial": is_trial,
        "trial_start_date": trial_start_date_str,
        "trial_end_date": trial_end_date_str,
        "trial_days_remaining": trial_days_remaining,
        "trial_active": trial_active,

        # Límites del tier
        "tier_limits": tier_info,
    }


@router.get("/options")
async def get_license_options():
    """Obtener opciones de licenciamiento disponibles con precios y features"""
    return {
        "options": [
            {
                "type": lt.value,
                "price": info["price"],
                "months": info["months"],
                "label": info["label"],
                "limits": LICENSE_TIERS.get(lt, {}),
            }
            for lt, info in LICENSE_PRICES.items()
        ],
        "currency": "USD",
        "contact_whatsapp": WHATSAPP_NUMBER,
    }


@router.get("/tiers")
async def get_license_tiers():
    """Obtener detalles completos de los tiers de licencia con límites y features"""
    return {
        "tiers": {
            lt.value: {
                "price": LICENSE_PRICES[lt]["price"],
                "months": LICENSE_PRICES[lt]["months"],
                "label": LICENSE_PRICES[lt]["label"],
                **LICENSE_TIERS[lt],
            }
            for lt in LicenseType
        }
    }


@router.get("/check-limit/{limit_type}")
async def check_license_limit(
    limit_type: str,
    company_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verificar si el usuario ha alcanzado un límite de su licencia.
    
    limit_type: 'companies', 'users', 'comprobantes', 'employees', 'products'
    company_id: Requerido para límites por empresa (users, comprobantes, employees, products)
    """
    company_id = clean_company_id(company_id)
    tier = get_tier_limits(current_user.license_type)
    
    if limit_type == "companies":
        max_allowed = tier.get("max_companies", 1)
        result = await db.execute(
            select(func.count(Company.id)).where(Company.user_id == current_user.id)
        )
        current_count = result.scalar() or 0
        
        return {
            "limit_type": "companies",
            "max": max_allowed,
            "current": current_count,
            "available": max(0, max_allowed - current_count),
            "is_at_limit": current_count >= max_allowed,
        }
    
    elif limit_type == "users" and company_id:
        max_allowed = tier.get("max_users_per_company", 2)
        result = await db.execute(
            select(func.count(UserCompanyRole.id)).where(
                UserCompanyRole.company_id == company_id,
                UserCompanyRole.is_active == True,
            )
        )
        current_count = result.scalar() or 0
        
        return {
            "limit_type": "users",
            "company_id": company_id,
            "max": max_allowed,
            "current": current_count,
            "available": max(0, max_allowed - current_count),
            "is_at_limit": current_count >= max_allowed,
        }
    
    elif limit_type == "comprobantes" and company_id:
        max_allowed = tier.get("max_comprobantes_month", 50)
        now = datetime.now(timezone.utc)
        first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = await db.execute(
            select(func.count(Comprobante.id)).where(
                Comprobante.company_id == company_id,
                Comprobante.created_at >= first_of_month,
            )
        )
        current_count = result.scalar() or 0
        
        return {
            "limit_type": "comprobantes",
            "company_id": company_id,
            "max": max_allowed,
            "current": current_count,
            "available": max(0, max_allowed - current_count),
            "is_at_limit": current_count >= max_allowed,
            "period": first_of_month.strftime("%Y-%m"),
        }
    
    elif limit_type == "employees" and company_id:
        max_allowed = tier.get("max_employees", 5)
        from app.models.employee import Employee
        result = await db.execute(
            select(func.count(Employee.id)).where(
                Employee.company_id == company_id,
                Employee.is_active == True,
            )
        )
        current_count = result.scalar() or 0
        
        return {
            "limit_type": "employees",
            "company_id": company_id,
            "max": max_allowed,
            "current": current_count,
            "available": max(0, max_allowed - current_count),
            "is_at_limit": current_count >= max_allowed,
        }
    
    elif limit_type == "products" and company_id:
        max_allowed = tier.get("max_products", 100)
        from app.models.product import Product
        result = await db.execute(
            select(func.count(Product.id)).where(
                Product.company_id == company_id,
                Product.is_active == True,
            )
        )
        current_count = result.scalar() or 0
        
        return {
            "limit_type": "products",
            "company_id": company_id,
            "max": max_allowed,
            "current": current_count,
            "available": max(0, max_allowed - current_count),
            "is_at_limit": current_count >= max_allowed,
        }
    
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Tipo de límite inválido o company_id faltante. Válidos: companies, users (requiere company_id), comprobantes (requiere company_id), employees (requiere company_id), products (requiere company_id)"
        )


@router.get("/feature/{feature_name}")
async def check_feature_access(
    feature_name: str,
    current_user: User = Depends(get_current_user),
):
    """Verificar si el tier de licencia actual tiene acceso a un feature"""
    has_access = has_feature(current_user.license_type, feature_name)
    
    if not has_access:
        tier = get_tier_limits(current_user.license_type)
        # Find minimum tier that has this feature
        min_tier = None
        for lt, tier_info in LICENSE_TIERS.items():
            if tier_info.get("features", {}).get(feature_name, False):
                min_tier = lt.value
                break
        
        return {
            "feature": feature_name,
            "has_access": False,
            "current_tier": current_user.license_type.value if current_user.license_type else None,
            "minimum_tier_required": min_tier,
            "message": f"Su plan actual no incluye {feature_name}. Actualice a {min_tier or 'un plan superior'} para acceder." if min_tier else f"Feature '{feature_name}' no encontrado.",
        }
    
    return {
        "feature": feature_name,
        "has_access": True,
        "current_tier": current_user.license_type.value if current_user.license_type else None,
    }


@router.post("/renew-whatsapp")
async def renew_via_whatsapp(
    license_type: LicenseType,
    current_user: User = Depends(get_current_user),
):
    """
    Generar enlace de WhatsApp para renovación de licencia.
    El usuario selecciona la opción y se conecta con WhatsApp.
    """
    info = LICENSE_PRICES[license_type]
    tier = LICENSE_TIERS[license_type]
    
    message = (
        f"Hola, quiero renovar mi licencia de ContaEC\n"
        f"• Plan: {info['label']}\n"
        f"• Precio: ${info['price']:.2f} USD\n"
        f"• Duración: {info['months']} mes(es)\n"
        f"• Empresas: {tier['max_companies']}\n"
        f"• Usuarios/Empresa: {tier['max_users_per_company']}\n"
        f"• Mi correo: {current_user.email}"
    )
    
    # Formato de enlace de WhatsApp
    whatsapp_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={message}"
    
    return {
        "whatsapp_url": whatsapp_url,
        "license_type": license_type.value,
        "price": info["price"],
        "label": info["label"],
        "limits": tier,
        "message": message,
    }


@router.get("/check-expiry")
async def check_license_expiry(
    current_user: User = Depends(get_current_user),
):
    """
    Verificar si la licencia está próxima a expirar.
    Retorna alerta si faltan 15 días o menos.
    """
    if not current_user.license_end_date:
        return {
            "alert": True,
            "message": "No tiene una licencia activa. Adquiera una para continuar usando ContaEC.",
            "days_remaining": 0,
        }
    
    now = datetime.now(timezone.utc)
    end_date = current_user.license_end_date
    if end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)
    days_remaining = (end_date - now).days
    
    alert = False
    message = None
    
    if days_remaining <= 0:
        alert = True
        message = "Su licencia ha expirado. Renueve para continuar usando ContaEC."
    elif days_remaining <= 15:
        alert = True
        message = f"Su licencia expira en {days_remaining} días. Renueve a tiempo para evitar interrupciones."
    elif days_remaining <= 30:
        message = f"Su licencia expira en {days_remaining} días."
    
    return {
        "alert": alert,
        "message": message,
        "days_remaining": days_remaining,
        "license_end_date": current_user.license_end_date.isoformat(),
    }

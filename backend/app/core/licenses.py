"""
ContaEC - Configuración centralizada de licencias
Define límites y features por tipo de licencia en un solo lugar
"""
import copy
from datetime import datetime, timezone
from typing import Optional

from app.models.user import User, LicenseType


# ==========================================
# Límites y features por tier de licencia
# ==========================================

LICENSE_TIERS = {
    LicenseType.MENSUAL: {
        "max_companies": 1,
        "max_users_per_company": 2,
        "max_comprobantes_month": 50,
        "max_employees": 5,
        "max_products": 100,
        "features": {
            "electronic_invoicing": True,
            "proformas": True,
            "basic_accounting": True,
            "inventory": True,
            "pos": False,
            "multi_warehouse": False,
            "payroll": False,
            "budgets": False,
            "crm": False,
            "projects": False,
            "banking_integration": False,
            "ecommerce_integration": False,
            "ml_predictions": False,
            "api_access": False,
            "custom_reports": False,
            "priority_support": False,
        },
    },
    LicenseType.TRIMESTRAL: {
        "max_companies": 2,
        "max_users_per_company": 5,
        "max_comprobantes_month": 200,
        "max_employees": 15,
        "max_products": 500,
        "features": {
            "electronic_invoicing": True,
            "proformas": True,
            "basic_accounting": True,
            "inventory": True,
            "pos": True,
            "multi_warehouse": False,
            "payroll": True,
            "budgets": False,
            "crm": False,
            "projects": False,
            "banking_integration": True,
            "ecommerce_integration": False,
            "ml_predictions": False,
            "api_access": False,
            "custom_reports": False,
            "priority_support": False,
        },
    },
    LicenseType.SEMESTRAL: {
        "max_companies": 5,
        "max_users_per_company": 10,
        "max_comprobantes_month": 500,
        "max_employees": 50,
        "max_products": 2000,
        "features": {
            "electronic_invoicing": True,
            "proformas": True,
            "basic_accounting": True,
            "inventory": True,
            "pos": True,
            "multi_warehouse": True,
            "payroll": True,
            "budgets": True,
            "crm": True,
            "projects": True,
            "banking_integration": True,
            "ecommerce_integration": True,
            "ml_predictions": True,
            "api_access": False,
            "custom_reports": True,
            "priority_support": False,
        },
    },
    LicenseType.ANUAL: {
        "max_companies": 999,  # Prácticamente ilimitado
        "max_users_per_company": 999,
        "max_comprobantes_month": 9999,
        "max_employees": 999,
        "max_products": 99999,
        "features": {
            "electronic_invoicing": True,
            "proformas": True,
            "basic_accounting": True,
            "inventory": True,
            "pos": True,
            "multi_warehouse": True,
            "payroll": True,
            "budgets": True,
            "crm": True,
            "projects": True,
            "banking_integration": True,
            "ecommerce_integration": True,
            "ml_predictions": True,
            "api_access": True,
            "custom_reports": True,
            "priority_support": True,
        },
    },
}

# Límites específicos para período trial
TRIAL_LIMITS = {
    "max_companies": 1,
    "max_users_per_company": 2,
    "max_comprobantes_month": 50,
    "max_employees": 5,
    "max_products": 100,
}


# ==========================================
# Configuración editable de planes (admin)
# ==========================================
# Copia mutable de LICENSE_TIERS que el administrador puede ajustar desde el
# panel de administración (PUT /admin/license-plans). Se mantiene en memoria
# como los precios (LICENSE_PRICES); los límites aplicados al usuario siempre
# se leen desde aquí, de modo que el cambio surte efecto de inmediato.
_PLAN_CONFIG = copy.deepcopy(LICENSE_TIERS)

# Nombre legible por plan (usado por el endpoint de administración)
PLAN_LABELS = {
    LicenseType.MENSUAL: "Mensual",
    LicenseType.TRIMESTRAL: "Trimestral",
    LicenseType.SEMESTRAL: "Semestral",
    LicenseType.ANUAL: "Anual",
}


def _as_enum(plan_key: str) -> LicenseType:
    """Convierte una key de plan (str) a LicenseType"""
    if isinstance(plan_key, LicenseType):
        return plan_key
    return LicenseType(plan_key)


def get_plan_config(plan_key: Optional[str] = None) -> dict:
    """
    Obtener la configuración actual (límites + features) de los planes.

    Args:
        plan_key: Key del plan ('monthly', 'quarterly', 'semiannual', 'annual').
                  Si es None, devuelve todos los planes.

    Returns:
        Configuración del/los plan(es) (copia, para no mutar el store)
    """
    if plan_key is None:
        return {
            lt.value: copy.deepcopy(_PLAN_CONFIG[lt]) | {"label": PLAN_LABELS[lt]}
            for lt in LicenseType
        }
    lt = _as_enum(plan_key)
    return copy.deepcopy(_PLAN_CONFIG[lt]) | {"label": PLAN_LABELS[lt]}


def update_plan_config(
    plan_key: str,
    limits: Optional[dict] = None,
    features: Optional[dict] = None,
) -> dict:
    """
    Actualizar límites y/o features de un plan.

    Args:
        plan_key: Key del plan a actualizar
        limits: Dict con los límites a cambiar (valores enteros >= 0)
        features: Dict con los features a activar/desactivar (bool)

    Returns:
        Configuración actualizada del plan
    """
    lt = _as_enum(plan_key)
    cfg = _PLAN_CONFIG[lt]

    if limits:
        for k, v in limits.items():
            if k in cfg and isinstance(v, (int, float)) and not isinstance(v, bool):
                cfg[k] = max(0, int(v))

    if features:
        for k, v in features.items():
            if k in cfg.get("features", {}) and isinstance(v, bool):
                cfg["features"][k] = v

    return copy.deepcopy(cfg) | {"label": PLAN_LABELS[lt]}


def get_tier_limits(license_type: Optional[LicenseType]) -> dict:
    """
    Obtener los límites y features para un tipo de licencia.
    Lee de la configuración editable (puede ser ajustada por el admin).

    Args:
        license_type: Tipo de licencia (LicenseType enum)

    Returns:
        Diccionario con límites y features del tier
    """
    if license_type is None:
        return _PLAN_CONFIG[LicenseType.MENSUAL]
    return _PLAN_CONFIG.get(license_type, _PLAN_CONFIG[LicenseType.MENSUAL])


def get_license_limits(user: User) -> dict:
    """
    Obtener límites aplicables para un usuario según su estado de licencia.
    Prioriza el trial activo sobre la licencia.

    Args:
        user: Objeto User del usuario

    Returns:
        Diccionario con los límites aplicables
    """
    now = datetime.now(timezone.utc)

    # Verificar si está en trial activo
    is_trial_active = (
        user.is_trial
        and user.trial_end_date
        and user.trial_end_date > now
    )

    if is_trial_active:
        return TRIAL_LIMITS.copy()

    # Obtener límites según tipo de licencia (copia profunda para que los
    # consumidores no puedan mutar la configuración editable del admin)
    return copy.deepcopy(get_tier_limits(user.license_type))


def has_feature(license_type: Optional[LicenseType], feature: str) -> bool:
    """
    Verificar si un tipo de licencia tiene acceso a un feature específico.

    Args:
        license_type: Tipo de licencia
        feature: Nombre del feature a verificar

    Returns:
        True si el feature está disponible, False en caso contrario
    """
    tier = get_tier_limits(license_type)
    return tier.get("features", {}).get(feature, False)


def get_feature_label(feature: str) -> str:
    """
    Obtener nombre legible para un feature.

    Args:
        feature: Key del feature

    Returns:
        Nombre en español del feature
    """
    FEATURE_LABELS = {
        'electronic_invoicing': 'Facturación Electrónica',
        'basic_accounting': 'Contabilidad Básica',
        'inventory': 'Inventario',
        'proformas': 'Proformas',
        'pos': 'Punto de Venta (POS)',
        'payroll': 'Nómina (RRHH)',
        'banking_integration': 'Integración Bancaria',
        'multi_warehouse': 'Multi-Almacén',
        'budgets': 'Presupuestos',
        'projects': 'Proyectos',
        'crm': 'CRM',
        'ml_predictions': 'ML / IA',
        'ecommerce_integration': 'E-commerce',
        'custom_reports': 'Reportes Personalizados',
        'api_access': 'API Access',
        'priority_support': 'Soporte Prioritario',
    }
    return FEATURE_LABELS.get(feature, feature)


def get_minimum_tier_for_feature(feature: str) -> Optional[LicenseType]:
    """
    Obtener el tier mínimo requerido para acceder a un feature.

    Args:
        feature: Nombre del feature

    Returns:
        LicenseType mínimo requerido, o None si el feature no existe
    """
    for license_type in [LicenseType.MENSUAL, LicenseType.TRIMESTRAL,
                         LicenseType.SEMESTRAL, LicenseType.ANUAL]:
        tier = LICENSE_TIERS[license_type]
        if tier.get("features", {}).get(feature, False):
            return license_type
    return None
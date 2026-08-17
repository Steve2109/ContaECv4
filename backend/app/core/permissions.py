"""
ContaEC - Dependencias de permisos por módulo

Permite restringir el acceso de las sub-cuentas (cuentas creadas por un
usuario para sus empleados) a módulos específicos de la aplicación.

Reglas:
- Administradores del sistema y cuentas principales (no sub-cuentas):
  acceso total.
- Sub-cuenta sin `allowed_modules` (lista vacía): acceso total.
- Sub-cuenta con módulos definidos: solo puede acceder a los routers
  cuyo módulo esté en su lista.
"""
import json
import logging

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


def effective_owner_id(user: User):
    """
    Devuelve el ID del usuario efectivo para el acceso a datos.

    - Cuenta principal / admin: su propio ID.
    - Sub-cuenta: el ID de la cuenta principal que la creó (las sub-cuentas
      trabajan sobre las empresas de su cuenta principal).
    """
    if user.is_subaccount and user.parent_user_id:
        return user.parent_user_id
    return user.id


def _get_allowed_modules(user: User) -> list[str]:
    """Devuelve la lista de módulos permitidos de una sub-cuenta ([] = todos)."""
    if not user.allowed_modules:
        return []
    try:
        parsed = json.loads(user.allowed_modules)
        if isinstance(parsed, list):
            return [str(m).strip() for m in parsed if str(m).strip()]
    except (json.JSONDecodeError, TypeError):
        return [m.strip() for m in str(user.allowed_modules).split(",") if m.strip()]
    return []


def require_modules(*modules: str):
    """
    Factory de dependencia: exige que el usuario tenga acceso a al menos uno
    de los módulos indicados (si es sub-cuenta con restricciones).
    """
    async def checker(current_user: User = Depends(get_current_user)) -> None:
        if current_user.is_admin or not current_user.is_subaccount:
            return
        allowed = _get_allowed_modules(current_user)
        if not allowed:
            return  # Sin restricciones = acceso total
        if not any(m in allowed for m in modules):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para acceder a este módulo. "
                       "Contacte al administrador de su cuenta.",
            )

    return checker

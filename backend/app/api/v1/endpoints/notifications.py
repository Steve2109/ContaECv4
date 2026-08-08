"""
ContaEC - Endpoints de Notificaciones del Sistema
CRUD de notificaciones generales, marcado de leídas, conteo de no leídas
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user, get_current_active_admin
from app.models.notification import (
    Notification,
    NotificationCategory,
    NotificationPriority,
    NotificationType,
)
from app.models.user import User
from app.schemas.notification import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notificaciones"])


# ==========================================
# Funciones auxiliares
# ==========================================

def _build_user_notification_filter(user_id: str, company_ids: list[str] | None = None):
    """
    Construye el filtro SQL para obtener notificaciones visibles para un usuario.

    Un usuario ve notificaciones que:
    1. Están dirigidas directamente a él (user_id = su id)
    2. Son de su empresa sin usuario específico (user_id IS NULL AND company_id IN sus empresas)
    3. Son globales (company_id IS NULL AND user_id IS NULL)
    """
    conditions = [
        Notification.user_id == user_id,  # Dirigidas al usuario
    ]

    if company_ids:
        conditions.append(
            # Dirigidas a toda la empresa (sin usuario específico)
            (Notification.user_id.is_(None)) & (Notification.company_id.in_(company_ids))
        )

    # Globales (sin empresa ni usuario específico)
    conditions.append(
        (Notification.company_id.is_(None)) & (Notification.user_id.is_(None))
    )

    return or_(*conditions)


async def _get_notification_or_404(
    db: AsyncSession,
    notification_id: str,
) -> Notification:
    """Obtiene una notificación por ID o lanza 404"""
    result = await db.execute(
        select(Notification).where(Notification.id == notification_id)
    )
    notification = result.scalars().first()
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada.",
        )
    return notification


# ==========================================
# Endpoints
# ==========================================

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    type: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    is_read: bool | None = None,
    is_active: bool | None = True,
    company_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar notificaciones para el usuario actual con conteo de no leídas"""
    company_id = clean_company_id(company_id)
    # Obtener IDs de empresas del usuario
    from app.models.company import Company
    company_result = await db.execute(
        select(Company.id).where(Company.user_id == current_user.id, Company.is_active == True)
    )
    company_ids = [str(cid) for cid in company_result.scalars().all()]

    # Filtro base: notificaciones visibles para el usuario
    user_filter = _build_user_notification_filter(current_user.id, company_ids)

    # Consulta principal
    query = select(Notification).where(user_filter)

    # Filtros opcionales
    if type:
        query = query.where(Notification.type == type)
    if category:
        query = query.where(Notification.category == category)
    if priority:
        query = query.where(Notification.priority == priority)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    if is_active is not None:
        query = query.where(Notification.is_active == is_active)
    if company_id:
        query = query.where(Notification.company_id == company_id)

    # Filtrar notificaciones expiradas
    now = datetime.now(timezone.utc)
    query = query.where(
        or_(
            Notification.expires_at.is_(None),
            Notification.expires_at > now,
        )
    )

    # Ordenar por prioridad y fecha
    query = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    notifications = result.scalars().all()

    # Conteo de no leídas
    unread_query = select(func.count(Notification.id)).where(
        user_filter,
        Notification.is_read == False,
        Notification.is_active == True,
        or_(
            Notification.expires_at.is_(None),
            Notification.expires_at > now,
        ),
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar() or 0

    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(n) for n in notifications],
        unread_count=unread_count,
    )


@router.get("/unread-count")
async def get_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener el conteo de notificaciones no leídas para el usuario actual"""
    from app.models.company import Company
    company_result = await db.execute(
        select(Company.id).where(Company.user_id == current_user.id, Company.is_active == True)
    )
    company_ids = [str(cid) for cid in company_result.scalars().all()]

    user_filter = _build_user_notification_filter(current_user.id, company_ids)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(func.count(Notification.id)).where(
            user_filter,
            Notification.is_read == False,
            Notification.is_active == True,
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > now,
            ),
        )
    )
    count = result.scalar() or 0

    return {"unread_count": count}


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    data: NotificationCreate,
    request: Request,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva notificación (solo administradores)"""
    data.user_id = clean_uuid_param(data.user_id, "user_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    # Validar tipo
    valid_types = {t.value for t in NotificationType}
    if data.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de notificación inválido: {data.type}. Valores permitidos: {', '.join(valid_types)}",
        )

    # Validar categoría
    valid_categories = {c.value for c in NotificationCategory}
    if data.category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Categoría inválida: {data.category}. Valores permitidos: {', '.join(valid_categories)}",
        )

    # Validar prioridad
    valid_priorities = {p.value for p in NotificationPriority}
    if data.priority not in valid_priorities:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Prioridad inválida: {data.priority}. Valores permitidos: {', '.join(valid_priorities)}",
        )

    # Validar que company_id exista si se proporciona
    if data.company_id:
        from app.models.company import Company
        company_result = await db.execute(
            select(Company).where(Company.id == data.company_id)
        )
        if not company_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa no encontrada.",
            )

    # Validar que user_id exista si se proporciona
    if data.user_id:
        user_result = await db.execute(
            select(User).where(User.id == data.user_id)
        )
        if not user_result.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado.",
            )

    notification = Notification(
        company_id=data.company_id,
        user_id=data.user_id,
        type=data.type,
        category=data.category,
        title=data.title,
        message=data.message,
        priority=data.priority,
        action_url=data.action_url,
        action_label=data.action_label,
        expires_at=data.expires_at,
    )
    db.add(notification)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="notification",
        entity_id=notification.id,
        description=f"Notificación creada: {notification.title}",
        ip_address=request.client.host if request.client else None,
    )

    return NotificationResponse.model_validate(notification)


@router.put("/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marcar todas las notificaciones del usuario actual como leídas"""
    from app.models.company import Company
    company_result = await db.execute(
        select(Company.id).where(Company.user_id == current_user.id, Company.is_active == True)
    )
    company_ids = [str(cid) for cid in company_result.scalars().all()]

    user_filter = _build_user_notification_filter(current_user.id, company_ids)
    now = datetime.now(timezone.utc)

    # Obtener todas las no leídas activas no expiradas
    result = await db.execute(
        select(Notification).where(
            user_filter,
            Notification.is_read == False,
            Notification.is_active == True,
            or_(
                Notification.expires_at.is_(None),
                Notification.expires_at > now,
            ),
        )
    )
    notifications = result.scalars().all()

    count = 0
    for notification in notifications:
        notification.is_read = True
        count += 1

    await db.flush()

    return {"message": f"Se marcaron {count} notificaciones como leídas.", "marked_count": count}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Marcar una notificación como leída"""
    notification_id = validate_uuid(notification_id, "notification_id")
    notification = await _get_notification_or_404(db, notification_id)

    # Verificar que el usuario tenga acceso a esta notificación
    from app.models.company import Company
    company_result = await db.execute(
        select(Company.id).where(Company.user_id == current_user.id, Company.is_active == True)
    )
    company_ids = [str(cid) for cid in company_result.scalars().all()]

    if not _user_can_see_notification(notification, current_user.id, company_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para acceder a esta notificación.",
        )

    notification.is_read = True
    await db.flush()

    return NotificationResponse.model_validate(notification)


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: str,
    data: NotificationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una notificación (is_read, is_active)"""
    notification_id = validate_uuid(notification_id, "notification_id")
    notification = await _get_notification_or_404(db, notification_id)

    # Verificar permisos: solo admin o el propio usuario pueden actualizar
    if not current_user.is_admin:
        from app.models.company import Company
        company_result = await db.execute(
            select(Company.id).where(Company.user_id == current_user.id, Company.is_active == True)
        )
        company_ids = [str(cid) for cid in company_result.scalars().all()]

        if not _user_can_see_notification(notification, current_user.id, company_ids):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para modificar esta notificación.",
            )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notification, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="notification",
        entity_id=notification.id,
        description=f"Notificación actualizada: {notification.title}",
        ip_address=request.client.host if request.client else None,
    )

    return NotificationResponse.model_validate(notification)


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    request: Request,
    current_user: User = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una notificación (solo administradores)"""
    notification_id = validate_uuid(notification_id, "notification_id")
    notification = await _get_notification_or_404(db, notification_id)

    # Soft delete: marcar como inactiva
    notification.is_active = False
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="notification",
        entity_id=notification.id,
        description=f"Notificación eliminada: {notification.title}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Notificación eliminada exitosamente."}


# ==========================================
# Función auxiliar de permisos
# ==========================================

def _user_can_see_notification(
    notification: Notification,
    user_id: str,
    company_ids: list[str],
) -> bool:
    """Verifica si un usuario puede ver una notificación dada"""
    # Dirigida directamente al usuario
    if notification.user_id == user_id:
        return True

    # Dirigida a la empresa del usuario (sin usuario específico)
    if notification.user_id is None and notification.company_id in company_ids:
        return True

    # Notificación global (sin empresa ni usuario)
    if notification.company_id is None and notification.user_id is None:
        return True

    return False

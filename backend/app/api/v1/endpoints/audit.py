"""
ContaEC - Endpoints de Auditoría
Consulta de registros de auditoría, estadísticas y exportación
"""
import csv
import io
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.user import User
from app.schemas.audit_log import AuditLogResponse, AuditStatsResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/audit", tags=["Auditoría"])


@router.get("", response_model=list[AuditLogResponse])
async def list_audit_logs(
    user_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar registros de auditoría con filtros opcionales.

    Solo administradores pueden ver todos los registros.
    Usuarios normales solo ven sus propios registros.
    """
    user_id = clean_uuid_param(user_id, "user_id")
    query = select(AuditLog)

    # Si no es admin, solo ver sus propios registros
    if not current_user.is_admin:
        query = query.where(AuditLog.user_id == current_user.id)

    # Filtros opcionales
    if user_id:
        if not current_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden filtrar por usuario",
            )
        query = query.where(AuditLog.user_id == user_id)

    if action:
        query = query.where(AuditLog.action == action)

    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)

    if date_from:
        query = query.where(AuditLog.created_at >= date_from)

    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    # Ordenar por fecha descendente y paginar
    query = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [AuditLogResponse.model_validate(log) for log in logs]


@router.get("/stats", response_model=AuditStatsResponse)
async def get_audit_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener estadísticas de auditoría.

    Solo disponible para administradores.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ver estadísticas de auditoría",
        )

    # Total de acciones
    total_result = await db.execute(select(func.count(AuditLog.id)))
    total_actions = total_result.scalar() or 0

    # Acciones por tipo
    actions_by_type_result = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .group_by(AuditLog.action)
    )
    actions_by_type = {row[0]: row[1] for row in actions_by_type_result}

    # Acciones por tipo de entidad
    actions_by_entity_result = await db.execute(
        select(AuditLog.entity_type, func.count(AuditLog.id))
        .group_by(AuditLog.entity_type)
    )
    actions_by_entity = {row[0]: row[1] for row in actions_by_entity_result}

    # Logins en las últimas 24 horas
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    recent_logins_result = await db.execute(
        select(func.count(AuditLog.id)).where(
            and_(
                AuditLog.action == "LOGIN",
                AuditLog.created_at >= yesterday,
            )
        )
    )
    recent_logins = recent_logins_result.scalar() or 0

    return AuditStatsResponse(
        total_actions=total_actions,
        actions_by_type=actions_by_type,
        actions_by_entity=actions_by_entity,
        recent_logins=recent_logins,
    )


@router.get("/export")
async def export_audit_logs(
    format: str = Query("csv", description="Formato de exportación: csv o excel"),
    user_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Exportar registros de auditoría a CSV.

    Solo disponible para administradores.
    """
    user_id = clean_uuid_param(user_id, "user_id")
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden exportar registros de auditoría",
        )

    query = select(AuditLog)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if date_from:
        query = query.where(AuditLog.created_at >= date_from)
    if date_to:
        query = query.where(AuditLog.created_at <= date_to)

    query = query.order_by(AuditLog.created_at.desc()).limit(5000)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Generar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Usuario ID", "Email", "Acción", "Tipo Entidad",
        "ID Entidad", "Descripción", "IP", "Fecha"
    ])
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id or "",
            log.user_email or "",
            log.action,
            log.entity_type,
            log.entity_id or "",
            log.description,
            log.ip_address or "",
            log.created_at.isoformat() if log.created_at else "",
        ])

    output.seek(0)
    filename = f"audit_logs_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

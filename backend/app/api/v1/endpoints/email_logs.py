"""
ContaEC - Endpoints de Log de Envío de Correos
CRUD de email logs, reintentos y estadísticas de envío
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.email_log import EmailLog, EmailLogEstado, EmailLogTipo
from app.models.user import User
from app.schemas.email_log import (
    EmailLogCreate,
    EmailLogResponse,
    EmailLogRetryRequest,
    EmailLogStats,
    EmailLogUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/email-logs", tags=["Logs de Correo"])


# ==========================================
# Funciones auxiliares
# ==========================================

async def _get_log_or_404(
    log_id: str,
    current_user: User,
    db: AsyncSession,
) -> EmailLog:
    """Obtiene un log verificando que pertenezca al usuario"""
    result = await db.execute(
        select(EmailLog).where(EmailLog.id == log_id)
    )
    log = result.scalars().first()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log de correo no encontrado.",
        )

    if log.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene acceso a este log.",
        )

    return log


# ==========================================
# Endpoints CRUD
# ==========================================

@router.get("", response_model=list[EmailLogResponse])
async def list_email_logs(
    tipo: str | None = None,
    estado: str | None = None,
    comprobante_id: str | None = None,
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    skip: int = Query(0, ge=0, description="Número de registros a saltar"),
    limit: int = Query(100, ge=1, le=500, description="Número máximo de registros"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Listar logs de envío de correo del usuario.

    **Parámetros:**
    - `tipo`: Filtrar por tipo de correo
    - `estado`: Filtrar por estado (pendiente, enviado, fallido, etc.)
    - `comprobante_id`: Filtrar por comprobante asociado
    - `fecha_desde`: Filtrar desde fecha
    - `fecha_hasta`: Filtrar hasta fecha
    """
    comprobante_id = clean_uuid_param(comprobante_id, "comprobante_id")
    query = select(EmailLog).where(
        EmailLog.user_id == current_user.id,
    )

    if tipo:
        query = query.where(EmailLog.tipo == tipo)

    if estado:
        query = query.where(EmailLog.estado == estado)

    if comprobante_id:
        query = query.where(EmailLog.comprobante_id == comprobante_id)

    if fecha_desde:
        query = query.where(EmailLog.created_at >= fecha_desde)

    if fecha_hasta:
        query = query.where(EmailLog.created_at <= fecha_hasta)

    query = query.order_by(EmailLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [EmailLogResponse.model_validate(log) for log in logs]


@router.get("/stats", response_model=EmailLogStats)
async def get_email_logs_stats(
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener estadísticas de envío de correos.

    **Retorna:**
    - Total de correos
    - Enviados, fallidos, pendientes
    - Tasa de éxito (%)
    """
    query = select(EmailLog).where(EmailLog.user_id == current_user.id)

    if fecha_desde:
        query = query.where(EmailLog.created_at >= fecha_desde)
    if fecha_hasta:
        query = query.where(EmailLog.created_at <= fecha_hasta)

    result = await db.execute(query)
    logs = result.scalars().all()

    total = len(logs)
    enviados = sum(1 for log in logs if log.estado == EmailLogEstado.ENVIADO)
    fallidos = sum(1 for log in logs if log.estado == EmailLogEstado.FALLIDO)
    pendientes = sum(1 for log in logs if log.estado == EmailLogEstado.PENDIENTE)

    tasa_exito = (enviados / total * 100) if total > 0 else 0.0

    return EmailLogStats(
        total=total,
        enviados=enviados,
        fallidos=fallidos,
        pendientes=pendientes,
        tasa_exito=tasa_exito,
    )


@router.get("/{log_id}", response_model=EmailLogUpdate)
async def get_email_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un log de correo específico"""
    log_id = validate_uuid(log_id, "log_id")
    log = await _get_log_or_404(db, log_id, current_user)
    return EmailLogUpdate.model_validate(log)


@router.post("/{log_id}/retry")
async def retry_email_send(
    log_id: str,
    data: EmailLogRetryRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Solicitar reintento de envío de correo.

    Solo se puede reintentar si:
    - El estado es pendiente, fallido o reintentando
    - Número de intentos < max_intentos
    - La fecha de próximo intento ya pasó (si existe)
    """
    log_id = validate_uuid(log_id, "log_id")
    log = await _get_log_or_404(db, log_id, current_user)

    if not log.puede_reintentar:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo no cumple las condiciones para reintentar. "
                   f"Estado actual: {log.estado}, Intentos: {log.intentos}/{log.max_intentos}",
        )

    # Actualizar para reintento
    log.estado = EmailLogEstado.REINTENTANDO
    log.intentos += 1
    log.proximo_intento = datetime.now(timezone.utc)  # Intentar inmediatamente

    await db.commit()

    logger.info(f"Reintento de correo solicitado: log_id={log_id}, intento={log.intentos}")

    return {
        "message": "Reintento de correo programado exitosamente",
        "log_id": log_id,
        "intentos": log.intentos,
        "max_intentos": log.max_intentos,
    }


@router.delete("/{log_id}")
async def delete_email_log(
    log_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un log de correo"""
    log_id = validate_uuid(log_id, "log_id")
    log = await _get_log_or_404(db, log_id, current_user)

    await db.delete(log)
    await db.commit()

    return {"message": "Log de correo eliminado exitosamente"}


@router.get("/bulk/stats", response_model=dict)
async def get_bulk_email_stats(
    fecha_desde: datetime | None = None,
    fecha_hasta: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Obtener estadísticas detalladas por tipo de correo.

    **Retorna:**
    - breakdown por tipo (comprobante, proforma, etc.)
    - breakdown por estado
    - tendencia diaria
    """
    # Por tipo
    tipo_query = select(
        EmailLog.tipo,
        func.count(EmailLog.id).label("total"),
        func.sum(func.case(
            (EmailLog.estado == EmailLogEstado.ENVIADO, 1),
            else_=0
        )).label("enviados"),
    ).where(EmailLog.user_id == current_user.id)

    if fecha_desde:
        tipo_query = tipo_query.where(EmailLog.created_at >= fecha_desde)
    if fecha_hasta:
        tipo_query = tipo_query.where(EmailLog.created_at <= fecha_hasta)

    tipo_query = tipo_query.group_by(EmailLog.tipo)
    tipo_result = await db.execute(tipo_query)
    por_tipo = {row.tipo: {"total": row.total, "enviados": row.enviados or 0} for row in tipo_result}

    # Por estado
    estado_query = select(
        EmailLog.estado,
        func.count(EmailLog.id).label("total"),
    ).where(EmailLog.user_id == current_user.id)

    if fecha_desde:
        estado_query = estado_query.where(EmailLog.created_at >= fecha_desde)
    if fecha_hasta:
        estado_query = estado_query.where(EmailLog.created_at <= fecha_hasta)

    estado_query = estado_query.group_by(EmailLog.estado)
    estado_result = await db.execute(estado_query)
    por_estado = {row.estado: row.total for row in estado_result}

    return {
        "por_tipo": por_tipo,
        "por_estado": por_estado,
    }
"""
ContaEC - Endpoints de CRM (Customer Relationship Management)
CRUD de pipelines, etapas, leads, oportunidades, actividades, segmentos y automatizaciones
"""
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_action
from app.core.database import get_db
from app.core.validation import clean_company_id, clean_uuid_param, validate_uuid
from app.core.security import get_current_user
from app.models.client import Client
from app.models.company import Company
from app.models.crm import (
    ActivityStatus,
    ActivityType,
    AutomationTriggerType,
    CRMActivity,
    CRMAutomation,
    CRMContactSegment,
    CRMContactSegmentMember,
    CRMLead,
    CRMOpportunity,
    CRMPipeline,
    CRMPipelineStage,
    LeadSource,
    LeadStatus,
    OpportunityStatus,
    SegmentType,
)
from app.models.user import User
from app.schemas.crm import (
    CRMActivityCreate,
    CRMActivityResponse,
    CRMActivityUpdate,
    CRMAutomationCreate,
    CRMAutomationResponse,
    CRMAutomationUpdate,
    CRMContactSegmentCreate,
    CRMContactSegmentMemberResponse,
    CRMContactSegmentResponse,
    CRMContactSegmentUpdate,
    CRMLeadCreate,
    CRMLeadResponse,
    CRMLeadUpdate,
    CRMOpportunityCreate,
    CRMOpportunityResponse,
    CRMOpportunityUpdate,
    CRMPipelineCreate,
    CRMPipelineResponse,
    CRMPipelineStageCreate,
    CRMPipelineStageResponse,
    CRMPipelineStageUpdate,
    CRMPipelineUpdate,
    CRMStats,
    OpportunityStageChange,
    OpportunityWithDetails,
    PipelineWithStages,
    SegmentAddClientsRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crm", tags=["CRM Avanzado"])


# ==========================================
# Funciones auxiliares
# ==========================================

async def _get_company_for_user(
    db: AsyncSession,
    company_id: str,
    user_id: str,
) -> Company:
    """Obtiene una empresa verificando que pertenezca al usuario actual"""
    result = await db.execute(
        select(Company).where(
            Company.id == company_id,
            Company.user_id == user_id,
            Company.is_active == True,
        )
    )
    company = result.scalars().first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa no encontrada o no pertenece al usuario actual.",
        )
    return company


# ==========================================
# 1. CRM Stats
# ==========================================

@router.get("/stats", response_model=CRMStats)
async def get_crm_stats(
    company_id: str = Query(..., description="ID de la empresa"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener estadísticas generales del CRM"""
    company_id = validate_uuid(company_id, "company_id")
    await _get_company_for_user(db, company_id, current_user.id)

    # Total leads
    total_leads_result = await db.execute(
        select(func.count(CRMLead.id)).where(
            CRMLead.company_id == company_id,
        )
    )
    total_leads = total_leads_result.scalar() or 0

    # Total opportunities
    total_opps_result = await db.execute(
        select(func.count(CRMOpportunity.id)).where(
            CRMOpportunity.company_id == company_id,
        )
    )
    total_opportunities = total_opps_result.scalar() or 0

    # Won opportunities
    won_opps_result = await db.execute(
        select(func.count(CRMOpportunity.id)).where(
            CRMOpportunity.company_id == company_id,
            CRMOpportunity.status == OpportunityStatus.GANADA.value,
        )
    )
    won_opportunities = won_opps_result.scalar() or 0

    # Lost opportunities
    lost_opps_result = await db.execute(
        select(func.count(CRMOpportunity.id)).where(
            CRMOpportunity.company_id == company_id,
            CRMOpportunity.status == OpportunityStatus.PERDIDA.value,
        )
    )
    lost_opportunities = lost_opps_result.scalar() or 0

    # Conversion rate
    closed_total = won_opportunities + lost_opportunities
    conversion_rate = (
        Decimal(str(won_opportunities)) / Decimal(str(closed_total)) * Decimal("100")
        if closed_total > 0
        else Decimal("0")
    ).quantize(Decimal("0.01"))

    # Pipeline value (sum of open opportunity estimated_amount)
    pipeline_value_result = await db.execute(
        select(func.coalesce(func.sum(CRMOpportunity.estimated_amount), 0)).where(
            CRMOpportunity.company_id == company_id,
            CRMOpportunity.status == OpportunityStatus.ABIERTA.value,
        )
    )
    pipeline_value = pipeline_value_result.scalar() or Decimal("0")

    # Weighted pipeline (estimated_amount * probability / 100 for open opps)
    weighted_result = await db.execute(
        select(
            func.coalesce(
                func.sum(
                    CRMOpportunity.estimated_amount * CRMOpportunity.probability / 100
                ),
                0,
            )
        ).where(
            CRMOpportunity.company_id == company_id,
            CRMOpportunity.status == OpportunityStatus.ABIERTA.value,
        )
    )
    weighted_pipeline = weighted_result.scalar() or Decimal("0")

    return CRMStats(
        total_leads=total_leads,
        total_opportunities=total_opportunities,
        won_opportunities=won_opportunities,
        lost_opportunities=lost_opportunities,
        conversion_rate=conversion_rate,
        pipeline_value=pipeline_value,
        weighted_pipeline=weighted_pipeline,
    )


# ==========================================
# 2. CRUD Pipelines
# ==========================================

@router.post("/pipelines", response_model=CRMPipelineResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(
    data: CRMPipelineCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un nuevo pipeline de ventas"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    pipeline = CRMPipeline(
        company_id=data.company_id,
        name=data.name,
        description=data.description,
        is_default=data.is_default if data.is_default is not None else False,
        order=data.order or 0,
    )

    db.add(pipeline)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="crm_pipeline",
        entity_id=pipeline.id,
        description=f"Pipeline creado: {pipeline.name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMPipelineResponse.model_validate(pipeline)


@router.get("/pipelines", response_model=list[CRMPipelineResponse])
async def list_pipelines(
    company_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar pipelines con filtros"""
    company_id = clean_company_id(company_id)
    query = (
        select(CRMPipeline)
        .join(Company, CRMPipeline.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(CRMPipeline.company_id == company_id)

    query = query.order_by(CRMPipeline.order, CRMPipeline.created_at).offset(skip).limit(limit)

    result = await db.execute(query)
    pipelines = result.scalars().all()
    return [CRMPipelineResponse.model_validate(p) for p in pipelines]


@router.get("/pipelines/{pipeline_id}", response_model=PipelineWithStages)
async def get_pipeline(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un pipeline por ID con sus etapas"""
    pipeline_id = validate_uuid(pipeline_id, "pipeline_id")
    result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == pipeline_id)
    )
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline no encontrado.",
        )
    await _get_company_for_user(db, pipeline.company_id, current_user.id)
    return PipelineWithStages.model_validate(pipeline)


@router.put("/pipelines/{pipeline_id}", response_model=CRMPipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    data: CRMPipelineUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un pipeline"""
    pipeline_id = validate_uuid(pipeline_id, "pipeline_id")
    result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == pipeline_id)
    )
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline no encontrado.",
        )
    await _get_company_for_user(db, pipeline.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pipeline, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="crm_pipeline",
        entity_id=pipeline.id,
        description=f"Pipeline actualizado: {pipeline.name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMPipelineResponse.model_validate(pipeline)


@router.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un pipeline"""
    pipeline_id = validate_uuid(pipeline_id, "pipeline_id")
    result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == pipeline_id)
    )
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline no encontrado.",
        )
    await _get_company_for_user(db, pipeline.company_id, current_user.id)

    await db.delete(pipeline)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="crm_pipeline",
        entity_id=pipeline_id,
        description=f"Pipeline eliminado: {pipeline.name}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Pipeline eliminado exitosamente."}


# ==========================================
# 3. Pipeline Stages
# ==========================================

@router.get("/pipelines/{pipeline_id}/stages", response_model=list[CRMPipelineStageResponse])
async def list_stages(
    pipeline_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar etapas de un pipeline"""
    pipeline_id = validate_uuid(pipeline_id, "pipeline_id")
    result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == pipeline_id)
    )
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline no encontrado.",
        )
    await _get_company_for_user(db, pipeline.company_id, current_user.id)

    query = (
        select(CRMPipelineStage)
        .where(CRMPipelineStage.pipeline_id == pipeline_id)
        .order_by(CRMPipelineStage.order, CRMPipelineStage.created_at)
    )

    result = await db.execute(query)
    stages = result.scalars().all()
    return [CRMPipelineStageResponse.model_validate(s) for s in stages]


@router.post("/pipelines/{pipeline_id}/stages", response_model=CRMPipelineStageResponse, status_code=status.HTTP_201_CREATED)
async def create_stage(
    pipeline_id: str,
    data: CRMPipelineStageCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una etapa en un pipeline"""
    pipeline_id = validate_uuid(pipeline_id, "pipeline_id")
    result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == pipeline_id)
    )
    pipeline = result.scalars().first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline no encontrado.",
        )
    await _get_company_for_user(db, pipeline.company_id, current_user.id)

    stage = CRMPipelineStage(
        pipeline_id=pipeline_id,
        name=data.name,
        order=data.order or 0,
        probability_percentage=data.probability_percentage if data.probability_percentage is not None else 0,
        color=data.color,
    )

    db.add(stage)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="crm_pipeline_stage",
        entity_id=stage.id,
        description=f"Etapa creada en pipeline {pipeline.name}: {stage.name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMPipelineStageResponse.model_validate(stage)


@router.put("/pipelines/stages/{stage_id}", response_model=CRMPipelineStageResponse)
async def update_stage(
    stage_id: str,
    data: CRMPipelineStageUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una etapa de pipeline"""
    stage_id = validate_uuid(stage_id, "stage_id")
    result = await db.execute(
        select(CRMPipelineStage).where(CRMPipelineStage.id == stage_id)
    )
    stage = result.scalars().first()
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Etapa no encontrada.",
        )

    # Verify ownership through pipeline
    pipeline_result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == stage.pipeline_id)
    )
    pipeline = pipeline_result.scalars().first()
    await _get_company_for_user(db, pipeline.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(stage, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="crm_pipeline_stage",
        entity_id=stage.id,
        description=f"Etapa actualizada: {stage.name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMPipelineStageResponse.model_validate(stage)


@router.delete("/pipelines/stages/{stage_id}")
async def delete_stage(
    stage_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una etapa de pipeline"""
    stage_id = validate_uuid(stage_id, "stage_id")
    result = await db.execute(
        select(CRMPipelineStage).where(CRMPipelineStage.id == stage_id)
    )
    stage = result.scalars().first()
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Etapa no encontrada.",
        )

    pipeline_result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == stage.pipeline_id)
    )
    pipeline = pipeline_result.scalars().first()
    await _get_company_for_user(db, pipeline.company_id, current_user.id)

    await db.delete(stage)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="crm_pipeline_stage",
        entity_id=stage_id,
        description=f"Etapa eliminada: {stage.name}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Etapa eliminada exitosamente."}


# ==========================================
# 4. CRUD Leads
# ==========================================

@router.post("/leads", response_model=CRMLeadResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    data: CRMLeadCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un nuevo lead"""
    data.client_id = clean_uuid_param(data.client_id, "client_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Validate source if provided
    if data.source:
        valid_sources = {s.value for s in LeadSource}
        if data.source not in valid_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fuente inválida: {data.source}. Debe ser uno de: {', '.join(valid_sources)}",
            )

    # Validate status if provided
    if data.status:
        valid_statuses = {s.value for s in LeadStatus}
        if data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {data.status}. Debe ser uno de: {', '.join(valid_statuses)}",
            )

    lead = CRMLead(
        company_id=data.company_id,
        client_id=data.client_id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        source=data.source or LeadSource.OTHER.value,
        status=data.status or LeadStatus.NUEVO.value,
        assigned_to=data.assigned_to,
        estimated_value=data.estimated_value or Decimal("0"),
        notes=data.notes,
        last_contact_date=data.last_contact_date,
        next_follow_up=data.next_follow_up,
    )

    db.add(lead)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="crm_lead",
        entity_id=lead.id,
        description=f"Lead creado: {lead.first_name} {lead.last_name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMLeadResponse.model_validate(lead)


@router.get("/leads", response_model=list[CRMLeadResponse])
async def list_leads(
    company_id: str | None = None,
    status: str | None = None,
    source: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar leads con filtros"""
    company_id = clean_company_id(company_id)
    query = (
        select(CRMLead)
        .join(Company, CRMLead.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(CRMLead.company_id == company_id)
    if status:
        query = query.where(CRMLead.status == status)
    if source:
        query = query.where(CRMLead.source == source)

    query = query.order_by(CRMLead.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    leads = result.scalars().all()
    return [CRMLeadResponse.model_validate(l) for l in leads]


@router.get("/leads/{lead_id}", response_model=CRMLeadResponse)
async def get_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un lead por ID"""
    lead_id = validate_uuid(lead_id, "lead_id")
    result = await db.execute(
        select(CRMLead).where(CRMLead.id == lead_id)
    )
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead no encontrado.",
        )
    await _get_company_for_user(db, lead.company_id, current_user.id)
    return CRMLeadResponse.model_validate(lead)


@router.put("/leads/{lead_id}", response_model=CRMLeadResponse)
async def update_lead(
    lead_id: str,
    data: CRMLeadUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un lead"""
    lead_id = validate_uuid(lead_id, "lead_id")
    result = await db.execute(
        select(CRMLead).where(CRMLead.id == lead_id)
    )
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead no encontrado.",
        )
    await _get_company_for_user(db, lead.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate source if provided
    if "source" in update_data and update_data["source"] is not None:
        valid_sources = {s.value for s in LeadSource}
        if update_data["source"] not in valid_sources:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fuente inválida: {update_data['source']}",
            )

    # Validate status if provided
    if "status" in update_data and update_data["status"] is not None:
        valid_statuses = {s.value for s in LeadStatus}
        if update_data["status"] not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {update_data['status']}",
            )

    for field, value in update_data.items():
        setattr(lead, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="crm_lead",
        entity_id=lead.id,
        description=f"Lead actualizado: {lead.first_name} {lead.last_name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMLeadResponse.model_validate(lead)


@router.delete("/leads/{lead_id}")
async def delete_lead(
    lead_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un lead"""
    lead_id = validate_uuid(lead_id, "lead_id")
    result = await db.execute(
        select(CRMLead).where(CRMLead.id == lead_id)
    )
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead no encontrado.",
        )
    await _get_company_for_user(db, lead.company_id, current_user.id)

    await db.delete(lead)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="crm_lead",
        entity_id=lead_id,
        description=f"Lead eliminado: {lead.first_name} {lead.last_name}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Lead eliminado exitosamente."}


# ==========================================
# 5. Convert Lead to Opportunity
# ==========================================

@router.post("/leads/{lead_id}/convert", response_model=CRMOpportunityResponse, status_code=status.HTTP_201_CREATED)
async def convert_lead_to_opportunity(
    lead_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Convertir un lead en oportunidad de venta"""
    lead_id = validate_uuid(lead_id, "lead_id")
    result = await db.execute(
        select(CRMLead).where(CRMLead.id == lead_id)
    )
    lead = result.scalars().first()
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lead no encontrado.",
        )
    await _get_company_for_user(db, lead.company_id, current_user.id)

    if lead.converted_to_opportunity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este lead ya ha sido convertido a oportunidad.",
        )

    # Get default pipeline or first available
    pipeline_result = await db.execute(
        select(CRMPipeline).where(
            CRMPipeline.company_id == lead.company_id,
        ).order_by(CRMPipeline.is_default.desc(), CRMPipeline.order)
    )
    pipeline = pipeline_result.scalars().first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No existe un pipeline para esta empresa. Cree uno primero.",
        )

    # Get first stage of pipeline
    stage_result = await db.execute(
        select(CRMPipelineStage).where(
            CRMPipelineStage.pipeline_id == pipeline.id,
        ).order_by(CRMPipelineStage.order)
    )
    stage = stage_result.scalars().first()
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El pipeline no tiene etapas. Cree al menos una etapa primero.",
        )

    # Create opportunity
    opportunity = CRMOpportunity(
        company_id=lead.company_id,
        lead_id=lead.id,
        client_id=lead.client_id,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        name=f"{lead.first_name} {lead.last_name} - Oportunidad",
        estimated_amount=lead.estimated_value,
        probability=stage.probability_percentage,
        status=OpportunityStatus.ABIERTA.value,
        assigned_to=lead.assigned_to,
    )

    # Mark lead as converted
    lead.converted_to_opportunity = True
    lead.status = LeadStatus.GANADO.value

    db.add(opportunity)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CONVERT",
        entity_type="crm_lead",
        entity_id=lead.id,
        description=(
            f"Lead convertido a oportunidad: {lead.first_name} {lead.last_name} -> "
            f"Oportunidad: {opportunity.name}"
        ),
        ip_address=request.client.host if request.client else None,
    )

    return CRMOpportunityResponse.model_validate(opportunity)


# ==========================================
# 6. CRUD Opportunities
# ==========================================

@router.post("/opportunities", response_model=CRMOpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(
    data: CRMOpportunityCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva oportunidad"""
    data.pipeline_id = clean_uuid_param(data.pipeline_id, "pipeline_id")
    data.stage_id = clean_uuid_param(data.stage_id, "stage_id")
    data.lead_id = clean_uuid_param(data.lead_id, "lead_id")
    data.client_id = clean_uuid_param(data.client_id, "client_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Validate pipeline_id
    pipeline_result = await db.execute(
        select(CRMPipeline).where(CRMPipeline.id == data.pipeline_id)
    )
    pipeline = pipeline_result.scalars().first()
    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pipeline no encontrado.",
        )

    # Validate stage_id belongs to pipeline
    stage_result = await db.execute(
        select(CRMPipelineStage).where(
            CRMPipelineStage.id == data.stage_id,
            CRMPipelineStage.pipeline_id == data.pipeline_id,
        )
    )
    stage = stage_result.scalars().first()
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La etapa no pertenece al pipeline indicado.",
        )

    # Validate status if provided
    if data.status:
        valid_statuses = {s.value for s in OpportunityStatus}
        if data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {data.status}. Debe ser uno de: {', '.join(valid_statuses)}",
            )

    opportunity = CRMOpportunity(
        company_id=data.company_id,
        lead_id=data.lead_id,
        client_id=data.client_id,
        pipeline_id=data.pipeline_id,
        stage_id=data.stage_id,
        name=data.name,
        description=data.description,
        estimated_amount=data.estimated_amount or Decimal("0"),
        probability=data.probability if data.probability is not None else stage.probability_percentage,
        expected_close_date=data.expected_close_date,
        status=data.status or OpportunityStatus.ABIERTA.value,
        assigned_to=data.assigned_to,
    )

    db.add(opportunity)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="crm_opportunity",
        entity_id=opportunity.id,
        description=f"Oportunidad creada: {opportunity.name} (${opportunity.estimated_amount})",
        ip_address=request.client.host if request.client else None,
    )

    return CRMOpportunityResponse.model_validate(opportunity)


@router.get("/opportunities", response_model=list[CRMOpportunityResponse])
async def list_opportunities(
    company_id: str | None = None,
    status: str | None = None,
    pipeline_id: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar oportunidades con filtros"""
    pipeline_id = clean_uuid_param(pipeline_id, "pipeline_id")
    company_id = clean_company_id(company_id)
    query = (
        select(CRMOpportunity)
        .join(Company, CRMOpportunity.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(CRMOpportunity.company_id == company_id)
    if status:
        query = query.where(CRMOpportunity.status == status)
    if pipeline_id:
        query = query.where(CRMOpportunity.pipeline_id == pipeline_id)

    query = query.order_by(CRMOpportunity.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    opportunities = result.scalars().all()
    return [CRMOpportunityResponse.model_validate(o) for o in opportunities]


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityWithDetails)
async def get_opportunity(
    opportunity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una oportunidad por ID con detalles"""
    opportunity_id = validate_uuid(opportunity_id, "opportunity_id")
    result = await db.execute(
        select(CRMOpportunity).where(CRMOpportunity.id == opportunity_id)
    )
    opportunity = result.scalars().first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidad no encontrada.",
        )
    await _get_company_for_user(db, opportunity.company_id, current_user.id)

    # Build enriched response
    opp_data = CRMOpportunityResponse.model_validate(opportunity)

    # Lead name
    lead_name = None
    if opportunity.lead_id:
        lead_result = await db.execute(
            select(CRMLead).where(CRMLead.id == opportunity.lead_id)
        )
        lead = lead_result.scalars().first()
        if lead:
            lead_name = f"{lead.first_name} {lead.last_name}"

    # Client name
    client_name = None
    if opportunity.client_id:
        client_result = await db.execute(
            select(Client).where(Client.id == opportunity.client_id)
        )
        client = client_result.scalars().first()
        if client:
            client_name = client.razon_social

    # Stage info
    stage_name = opportunity.stage.name if opportunity.stage else None
    stage_color = opportunity.stage.color if opportunity.stage else None

    # Pipeline name
    pipeline_name = opportunity.pipeline.name if opportunity.pipeline else None

    # Weighted amount
    weighted_amount = (
        opportunity.estimated_amount * Decimal(str(opportunity.probability)) / Decimal("100")
    ).quantize(Decimal("0.01"))

    return OpportunityWithDetails(
        **opp_data.model_dump(),
        lead_name=lead_name,
        client_name=client_name,
        stage_name=stage_name,
        stage_color=stage_color,
        pipeline_name=pipeline_name,
        weighted_amount=weighted_amount,
    )


@router.put("/opportunities/{opportunity_id}", response_model=CRMOpportunityResponse)
async def update_opportunity(
    opportunity_id: str,
    data: CRMOpportunityUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una oportunidad"""
    opportunity_id = validate_uuid(opportunity_id, "opportunity_id")
    result = await db.execute(
        select(CRMOpportunity).where(CRMOpportunity.id == opportunity_id)
    )
    opportunity = result.scalars().first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidad no encontrada.",
        )
    await _get_company_for_user(db, opportunity.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate status if provided
    if "status" in update_data and update_data["status"] is not None:
        valid_statuses = {s.value for s in OpportunityStatus}
        if update_data["status"] not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {update_data['status']}",
            )

    # Validate stage belongs to pipeline if both changed
    if "stage_id" in update_data:
        pipeline_id = update_data.get("pipeline_id", opportunity.pipeline_id)
        stage_result = await db.execute(
            select(CRMPipelineStage).where(
                CRMPipelineStage.id == update_data["stage_id"],
                CRMPipelineStage.pipeline_id == pipeline_id,
            )
        )
        stage = stage_result.scalars().first()
        if not stage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La etapa no pertenece al pipeline indicado.",
            )

    for field, value in update_data.items():
        setattr(opportunity, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="crm_opportunity",
        entity_id=opportunity.id,
        description=f"Oportunidad actualizada: {opportunity.name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMOpportunityResponse.model_validate(opportunity)


@router.delete("/opportunities/{opportunity_id}")
async def delete_opportunity(
    opportunity_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una oportunidad"""
    opportunity_id = validate_uuid(opportunity_id, "opportunity_id")
    result = await db.execute(
        select(CRMOpportunity).where(CRMOpportunity.id == opportunity_id)
    )
    opportunity = result.scalars().first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidad no encontrada.",
        )
    await _get_company_for_user(db, opportunity.company_id, current_user.id)

    await db.delete(opportunity)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="crm_opportunity",
        entity_id=opportunity_id,
        description=f"Oportunidad eliminada: {opportunity.name}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Oportunidad eliminada exitosamente."}


# ==========================================
# 7. Move Opportunity to Stage
# ==========================================

@router.put("/opportunities/{opportunity_id}/stage", response_model=CRMOpportunityResponse)
async def move_opportunity_stage(
    opportunity_id: str,
    data: OpportunityStageChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mover una oportunidad a una etapa diferente del pipeline"""
    data.stage_id = clean_uuid_param(data.stage_id, "stage_id")
    opportunity_id = validate_uuid(opportunity_id, "opportunity_id")
    result = await db.execute(
        select(CRMOpportunity).where(CRMOpportunity.id == opportunity_id)
    )
    opportunity = result.scalars().first()
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oportunidad no encontrada.",
        )
    await _get_company_for_user(db, opportunity.company_id, current_user.id)

    # Validate stage belongs to pipeline
    stage_result = await db.execute(
        select(CRMPipelineStage).where(
            CRMPipelineStage.id == data.stage_id,
            CRMPipelineStage.pipeline_id == opportunity.pipeline_id,
        )
    )
    new_stage = stage_result.scalars().first()
    if not new_stage:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La etapa no pertenece al pipeline de esta oportunidad.",
        )

    old_stage_id = opportunity.stage_id
    opportunity.stage_id = data.stage_id
    opportunity.probability = new_stage.probability_percentage

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="STAGE_CHANGE",
        entity_type="crm_opportunity",
        entity_id=opportunity.id,
        description=(
            f"Oportunidad movida de etapa: {opportunity.name} -> "
            f"nueva etapa: {new_stage.name}"
        ),
        ip_address=request.client.host if request.client else None,
    )

    return CRMOpportunityResponse.model_validate(opportunity)


# ==========================================
# 8. CRUD Activities
# ==========================================

@router.post("/activities", response_model=CRMActivityResponse, status_code=status.HTTP_201_CREATED)
async def create_activity(
    data: CRMActivityCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva actividad"""
    data.opportunity_id = clean_uuid_param(data.opportunity_id, "opportunity_id")
    data.lead_id = clean_uuid_param(data.lead_id, "lead_id")
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Validate type
    valid_types = {t.value for t in ActivityType}
    if data.type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo inválido: {data.type}. Debe ser uno de: {', '.join(valid_types)}",
        )

    # Validate status if provided
    if data.status:
        valid_statuses = {s.value for s in ActivityStatus}
        if data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {data.status}. Debe ser uno de: {', '.join(valid_statuses)}",
            )

    activity = CRMActivity(
        company_id=data.company_id,
        opportunity_id=data.opportunity_id,
        lead_id=data.lead_id,
        user_id=current_user.id,
        type=data.type,
        subject=data.subject,
        description=data.description,
        scheduled_at=data.scheduled_at,
        status=data.status or ActivityStatus.PENDIENTE.value,
        result=data.result,
    )

    db.add(activity)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="crm_activity",
        entity_id=activity.id,
        description=f"Actividad creada: {activity.subject} ({activity.type})",
        ip_address=request.client.host if request.client else None,
    )

    return CRMActivityResponse.model_validate(activity)


@router.get("/activities", response_model=list[CRMActivityResponse])
async def list_activities(
    company_id: str | None = None,
    opportunity_id: str | None = None,
    lead_id: str | None = None,
    type: str | None = None,
    status: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar actividades con filtros"""
    opportunity_id = clean_uuid_param(opportunity_id, "opportunity_id")
    lead_id = clean_uuid_param(lead_id, "lead_id")
    company_id = clean_company_id(company_id)
    query = (
        select(CRMActivity)
        .join(Company, CRMActivity.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(CRMActivity.company_id == company_id)
    if opportunity_id:
        query = query.where(CRMActivity.opportunity_id == opportunity_id)
    if lead_id:
        query = query.where(CRMActivity.lead_id == lead_id)
    if type:
        query = query.where(CRMActivity.type == type)
    if status:
        query = query.where(CRMActivity.status == status)

    query = query.order_by(CRMActivity.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    activities = result.scalars().all()
    return [CRMActivityResponse.model_validate(a) for a in activities]


@router.get("/activities/{activity_id}", response_model=CRMActivityResponse)
async def get_activity(
    activity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una actividad por ID"""
    activity_id = validate_uuid(activity_id, "activity_id")
    result = await db.execute(
        select(CRMActivity).where(CRMActivity.id == activity_id)
    )
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada.",
        )
    await _get_company_for_user(db, activity.company_id, current_user.id)
    return CRMActivityResponse.model_validate(activity)


@router.put("/activities/{activity_id}", response_model=CRMActivityResponse)
async def update_activity(
    activity_id: str,
    data: CRMActivityUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una actividad"""
    activity_id = validate_uuid(activity_id, "activity_id")
    result = await db.execute(
        select(CRMActivity).where(CRMActivity.id == activity_id)
    )
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada.",
        )
    await _get_company_for_user(db, activity.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate type if provided
    if "type" in update_data and update_data["type"] is not None:
        valid_types = {t.value for t in ActivityType}
        if update_data["type"] not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo inválido: {update_data['type']}",
            )

    # Validate status if provided
    if "status" in update_data and update_data["status"] is not None:
        valid_statuses = {s.value for s in ActivityStatus}
        if update_data["status"] not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido: {update_data['status']}",
            )

    # If marking as completed, set completed_at
    if (
        "status" in update_data
        and update_data["status"] == ActivityStatus.COMPLETADA.value
        and activity.status != ActivityStatus.COMPLETADA.value
    ):
        activity.completed_at = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(activity, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="crm_activity",
        entity_id=activity.id,
        description=f"Actividad actualizada: {activity.subject}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMActivityResponse.model_validate(activity)


@router.delete("/activities/{activity_id}")
async def delete_activity(
    activity_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una actividad"""
    activity_id = validate_uuid(activity_id, "activity_id")
    result = await db.execute(
        select(CRMActivity).where(CRMActivity.id == activity_id)
    )
    activity = result.scalars().first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Actividad no encontrada.",
        )
    await _get_company_for_user(db, activity.company_id, current_user.id)

    await db.delete(activity)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="crm_activity",
        entity_id=activity_id,
        description=f"Actividad eliminada: {activity.subject}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Actividad eliminada exitosamente."}


# ==========================================
# 9. CRUD Segments
# ==========================================

@router.post("/segments", response_model=CRMContactSegmentResponse, status_code=status.HTTP_201_CREATED)
async def create_segment(
    data: CRMContactSegmentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear un nuevo segmento de contactos"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Validate type if provided
    if data.type:
        valid_types = {t.value for t in SegmentType}
        if data.type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo inválido: {data.type}. Debe ser uno de: {', '.join(valid_types)}",
            )

    rules_json = json.dumps(data.rules) if data.rules else None
    rfm_score_json = json.dumps(data.rfm_score) if data.rfm_score else None

    segment = CRMContactSegment(
        company_id=data.company_id,
        name=data.name,
        description=data.description,
        type=data.type or SegmentType.MANUAL.value,
        rules=rules_json,
        rfm_score=rfm_score_json,
        color=data.color,
    )

    db.add(segment)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="crm_contact_segment",
        entity_id=segment.id,
        description=f"Segmento creado: {segment.name} ({segment.type})",
        ip_address=request.client.host if request.client else None,
    )

    return CRMContactSegmentResponse.model_validate(segment)


@router.get("/segments", response_model=list[CRMContactSegmentResponse])
async def list_segments(
    company_id: str | None = None,
    type: str | None = None,
    is_active: bool | None = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar segmentos con filtros"""
    company_id = clean_company_id(company_id)
    query = (
        select(CRMContactSegment)
        .join(Company, CRMContactSegment.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(CRMContactSegment.company_id == company_id)
    if type:
        query = query.where(CRMContactSegment.type == type)
    if is_active is not None:
        query = query.where(CRMContactSegment.is_active == is_active)

    query = query.order_by(CRMContactSegment.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    segments = result.scalars().all()
    return [CRMContactSegmentResponse.model_validate(s) for s in segments]


@router.get("/segments/{segment_id}", response_model=CRMContactSegmentResponse)
async def get_segment(
    segment_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener un segmento por ID"""
    segment_id = validate_uuid(segment_id, "segment_id")
    result = await db.execute(
        select(CRMContactSegment).where(CRMContactSegment.id == segment_id)
    )
    segment = result.scalars().first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento no encontrado.",
        )
    await _get_company_for_user(db, segment.company_id, current_user.id)
    return CRMContactSegmentResponse.model_validate(segment)


@router.put("/segments/{segment_id}", response_model=CRMContactSegmentResponse)
async def update_segment(
    segment_id: str,
    data: CRMContactSegmentUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar un segmento"""
    segment_id = validate_uuid(segment_id, "segment_id")
    result = await db.execute(
        select(CRMContactSegment).where(CRMContactSegment.id == segment_id)
    )
    segment = result.scalars().first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento no encontrado.",
        )
    await _get_company_for_user(db, segment.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate type if provided
    if "type" in update_data and update_data["type"] is not None:
        valid_types = {t.value for t in SegmentType}
        if update_data["type"] not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo inválido: {update_data['type']}",
            )

    # Serialize JSON fields
    if "rules" in update_data and update_data["rules"] is not None:
        update_data["rules"] = json.dumps(update_data["rules"])
    if "rfm_score" in update_data and update_data["rfm_score"] is not None:
        update_data["rfm_score"] = json.dumps(update_data["rfm_score"])

    for field, value in update_data.items():
        setattr(segment, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="crm_contact_segment",
        entity_id=segment.id,
        description=f"Segmento actualizado: {segment.name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMContactSegmentResponse.model_validate(segment)


@router.delete("/segments/{segment_id}")
async def delete_segment(
    segment_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar un segmento"""
    segment_id = validate_uuid(segment_id, "segment_id")
    result = await db.execute(
        select(CRMContactSegment).where(CRMContactSegment.id == segment_id)
    )
    segment = result.scalars().first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento no encontrado.",
        )
    await _get_company_for_user(db, segment.company_id, current_user.id)

    await db.delete(segment)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="crm_contact_segment",
        entity_id=segment_id,
        description=f"Segmento eliminado: {segment.name}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Segmento eliminado exitosamente."}


# ==========================================
# 10. Add Clients to Segment
# ==========================================

@router.post("/segments/{segment_id}/add-clients", response_model=CRMContactSegmentResponse)
async def add_clients_to_segment(
    segment_id: str,
    data: SegmentAddClientsRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Agregar clientes a un segmento"""
    for _uid in (data.client_ids or []):
        clean_uuid_param(_uid, "client_id")
    segment_id = validate_uuid(segment_id, "segment_id")
    result = await db.execute(
        select(CRMContactSegment).where(CRMContactSegment.id == segment_id)
    )
    segment = result.scalars().first()
    if not segment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Segmento no encontrado.",
        )
    await _get_company_for_user(db, segment.company_id, current_user.id)

    # Get existing member client_ids
    existing_result = await db.execute(
        select(CRMContactSegmentMember.client_id).where(
            CRMContactSegmentMember.segment_id == segment_id,
        )
    )
    existing_client_ids = {row[0] for row in existing_result.all()}

    added_count = 0
    for client_id in data.client_ids:
        if client_id not in existing_client_ids:
            member = CRMContactSegmentMember(
                segment_id=segment_id,
                client_id=client_id,
            )
            db.add(member)
            added_count += 1

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="ADD_CLIENTS",
        entity_type="crm_contact_segment",
        entity_id=segment_id,
        description=f"Clientes agregados al segmento {segment.name}: {added_count} nuevos",
        ip_address=request.client.host if request.client else None,
    )

    # Re-fetch to get updated members
    result = await db.execute(
        select(CRMContactSegment).where(CRMContactSegment.id == segment_id)
    )
    segment = result.scalars().first()
    return CRMContactSegmentResponse.model_validate(segment)


# ==========================================
# 11. CRUD Automations
# ==========================================

@router.post("/automations", response_model=CRMAutomationResponse, status_code=status.HTTP_201_CREATED)
async def create_automation(
    data: CRMAutomationCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Crear una nueva automatización"""
    data.company_id = validate_uuid(data.company_id, "company_id")
    await _get_company_for_user(db, data.company_id, current_user.id)

    # Validate trigger_type
    valid_triggers = {t.value for t in AutomationTriggerType}
    if data.trigger_type not in valid_triggers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de disparador inválido: {data.trigger_type}. Debe ser uno de: {', '.join(valid_triggers)}",
        )

    conditions_json = json.dumps(data.trigger_conditions) if data.trigger_conditions else None
    actions_json = json.dumps(data.actions) if data.actions else None

    automation = CRMAutomation(
        company_id=data.company_id,
        name=data.name,
        trigger_type=data.trigger_type,
        trigger_conditions=conditions_json,
        actions=actions_json,
        is_active=data.is_active if data.is_active is not None else True,
    )

    db.add(automation)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="CREATE",
        entity_type="crm_automation",
        entity_id=automation.id,
        description=f"Automatización creada: {automation.name} ({automation.trigger_type})",
        ip_address=request.client.host if request.client else None,
    )

    return CRMAutomationResponse.model_validate(automation)


@router.get("/automations", response_model=list[CRMAutomationResponse])
async def list_automations(
    company_id: str | None = None,
    trigger_type: str | None = None,
    is_active: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Listar automatizaciones con filtros"""
    company_id = clean_company_id(company_id)
    query = (
        select(CRMAutomation)
        .join(Company, CRMAutomation.company_id == Company.id)
        .where(Company.user_id == current_user.id)
    )

    if company_id:
        await _get_company_for_user(db, company_id, current_user.id)
        query = query.where(CRMAutomation.company_id == company_id)
    if trigger_type:
        query = query.where(CRMAutomation.trigger_type == trigger_type)
    if is_active is not None:
        query = query.where(CRMAutomation.is_active == is_active)

    query = query.order_by(CRMAutomation.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    automations = result.scalars().all()
    return [CRMAutomationResponse.model_validate(a) for a in automations]


@router.get("/automations/{automation_id}", response_model=CRMAutomationResponse)
async def get_automation(
    automation_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtener una automatización por ID"""
    automation_id = validate_uuid(automation_id, "automation_id")
    result = await db.execute(
        select(CRMAutomation).where(CRMAutomation.id == automation_id)
    )
    automation = result.scalars().first()
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automatización no encontrada.",
        )
    await _get_company_for_user(db, automation.company_id, current_user.id)
    return CRMAutomationResponse.model_validate(automation)


@router.put("/automations/{automation_id}", response_model=CRMAutomationResponse)
async def update_automation(
    automation_id: str,
    data: CRMAutomationUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Actualizar una automatización"""
    automation_id = validate_uuid(automation_id, "automation_id")
    result = await db.execute(
        select(CRMAutomation).where(CRMAutomation.id == automation_id)
    )
    automation = result.scalars().first()
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automatización no encontrada.",
        )
    await _get_company_for_user(db, automation.company_id, current_user.id)

    update_data = data.model_dump(exclude_unset=True)

    # Validate trigger_type if provided
    if "trigger_type" in update_data and update_data["trigger_type"] is not None:
        valid_triggers = {t.value for t in AutomationTriggerType}
        if update_data["trigger_type"] not in valid_triggers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de disparador inválido: {update_data['trigger_type']}",
            )

    # Serialize JSON fields
    if "trigger_conditions" in update_data and update_data["trigger_conditions"] is not None:
        update_data["trigger_conditions"] = json.dumps(update_data["trigger_conditions"])
    if "actions" in update_data and update_data["actions"] is not None:
        update_data["actions"] = json.dumps(update_data["actions"])

    for field, value in update_data.items():
        setattr(automation, field, value)

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="UPDATE",
        entity_type="crm_automation",
        entity_id=automation.id,
        description=f"Automatización actualizada: {automation.name}",
        ip_address=request.client.host if request.client else None,
    )

    return CRMAutomationResponse.model_validate(automation)


@router.delete("/automations/{automation_id}")
async def delete_automation(
    automation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Eliminar una automatización"""
    automation_id = validate_uuid(automation_id, "automation_id")
    result = await db.execute(
        select(CRMAutomation).where(CRMAutomation.id == automation_id)
    )
    automation = result.scalars().first()
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automatización no encontrada.",
        )
    await _get_company_for_user(db, automation.company_id, current_user.id)

    await db.delete(automation)
    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="DELETE",
        entity_type="crm_automation",
        entity_id=automation_id,
        description=f"Automatización eliminada: {automation.name}",
        ip_address=request.client.host if request.client else None,
    )

    return {"message": "Automatización eliminada exitosamente."}


# ==========================================
# 12. Manually Trigger Automation
# ==========================================

@router.post("/automations/{automation_id}/trigger", response_model=CRMAutomationResponse)
async def trigger_automation(
    automation_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ejecutar manualmente una automatización"""
    automation_id = validate_uuid(automation_id, "automation_id")
    result = await db.execute(
        select(CRMAutomation).where(CRMAutomation.id == automation_id)
    )
    automation = result.scalars().first()
    if not automation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Automatización no encontrada.",
        )
    await _get_company_for_user(db, automation.company_id, current_user.id)

    if not automation.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La automatización está desactivada. Actívela primero.",
        )

    # Update trigger stats
    automation.last_triggered_at = datetime.now(timezone.utc)
    automation.trigger_count += 1

    await db.flush()

    await log_action(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        action="TRIGGER",
        entity_type="crm_automation",
        entity_id=automation.id,
        description=(
            f"Automatización ejecutada manualmente: {automation.name} "
            f"(total ejecuciones: {automation.trigger_count})"
        ),
        ip_address=request.client.host if request.client else None,
    )

    return CRMAutomationResponse.model_validate(automation)
